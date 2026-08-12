from pathlib import Path
import json
import re
import shutil
import unicodedata
from difflib import get_close_matches

ROOT = Path(".")
BOT_FILE = ROOT / "PokeRole-Helper.py"
DBHELPER = ROOT / "dbhelper.py"
POKEDEX_DIR = ROOT / "pokerole_data" / "v3.0" / "Pokedex"
RECORDS_FILE = ROOT / "custom_pokemon_records.json"
STATS_EXTRA = ROOT / "statsExtra.py"
DB_FILE = ROOT / "pokerole_v3.db"

MAX_LEARNSET_MOVES = 64

for required in (BOT_FILE, DBHELPER, POKEDEX_DIR, RECORDS_FILE, STATS_EXTRA):
    if not required.exists():
        raise SystemExit(f"Missing required file/folder: {required}")

records = json.loads(RECORDS_FILE.read_text(encoding="utf-8"))


def safe_slug(value):
    value = "".join(
        c for c in unicodedata.normalize("NFD", value)
        if unicodedata.category(c) != "Mn"
    )
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value


def load_pokedex():
    by_name = {}
    by_path = {}
    for path in POKEDEX_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        name = data.get("Name")
        if name:
            by_name[name] = data
            by_path[name] = path
    return by_name, by_path


existing, existing_paths = load_pokedex()
original_existing_names = set(existing)

# Backups.
backup_dir = ROOT / "custom_pokemon_backups"
backup_dir.mkdir(exist_ok=True)

for source in (BOT_FILE, DBHELPER):
    dest = backup_dir / (source.name + ".before_custom_pokemon.bak")
    if not dest.exists():
        shutil.copy2(source, dest)


def name_key(s):
    return re.sub(r"[^a-z0-9]", "", s.casefold())


def find_existing_name(name):
    """Resolve a base species/form without changing genuinely custom names."""
    if not name:
        return None
    if name in existing:
        return name

    keyed = {name_key(n): n for n in existing}
    if name_key(name) in keyed:
        return keyed[name_key(name)]

    # Zygarde has percentage-labelled stock forms rather than a plain "Zygarde".
    prefix = [n for n in existing if n.casefold().startswith(name.casefold() + " ")]
    if prefix:
        return prefix[0]

    matches = get_close_matches(name, list(existing), n=1, cutoff=0.91)
    return matches[0] if matches else None


record_by_name = {r["name"]: r for r in records}

# If a source form name points at one tiny spelling difference in a stock species,
# use the stock species spelling. The records file already normalizes known cases,
# but this makes the installer resilient to future additions.
for r in records:
    hint = r.get("base_hint")
    if hint and hint not in record_by_name:
        resolved = find_existing_name(hint)
        if resolved:
            r["base_hint"] = re.sub(r"\s+\([^)]* Form\)$", "", resolved)


# Determine numbers before writing anything.
numeric_numbers = []
for d in existing.values():
    try:
        numeric_numbers.append(int(d.get("Number")))
    except Exception:
        pass
next_number = max(numeric_numbers or [1025]) + 1

assigned_numbers = {}

# Existing/edit entries keep their number.
for r in records:
    if r.get("edit"):
        found = find_existing_name(r["name"])
        if not found:
            raise SystemExit(f'Could not find existing Pokémon to edit: {r["name"]}')
        assigned_numbers[r["name"]] = int(existing[found]["Number"])


def root_name(name):
    return re.sub(r"\s+\([^)]* Form\)$", "", name).strip()


def number_for_existing_hint(hint):
    found = find_existing_name(hint)
    if found:
        try:
            return int(existing[found]["Number"])
        except Exception:
            return None
    return None


# Assign plain new species first.
for r in records:
    name = r["name"]
    if name in assigned_numbers:
        continue
    is_form = bool(re.search(r"\([^)]* Form\)$", name))
    if not is_form:
        if name in existing:
            assigned_numbers[name] = int(existing[name]["Number"])
        else:
            assigned_numbers[name] = next_number
            next_number += 1

# Assign forms to their base species/custom species where possible.
shared_form_roots = {}
for r in records:
    name = r["name"]
    if name in assigned_numbers:
        continue

    hint = r.get("base_hint")
    num = None

    if hint:
        # Custom base record first.
        if hint in assigned_numbers:
            num = assigned_numbers[hint]
        elif hint in record_by_name and hint not in assigned_numbers:
            # It may be processed later; let root handling deal with it.
            pass
        else:
            num = number_for_existing_hint(hint)

    root = root_name(name)
    if num is None and root in assigned_numbers:
        num = assigned_numbers[root]
    if num is None:
        num = number_for_existing_hint(root)

    # Forms such as Noxial (Endothermic Form) have no unsuffixed base statblock.
    # Keep their forms together under one new Pokédex number.
    if num is None and root in shared_form_roots:
        num = shared_form_roots[root]
    if num is None:
        num = next_number
        next_number += 1
        shared_form_roots[root] = num

    assigned_numbers[name] = num


# Work out form IDs without colliding with pre-existing forms on the same number.
used_form_indices = {}
for d in existing.values():
    dexid = str(d.get("DexID", ""))
    m = re.search(r"F(\d+)$", dexid)
    if not m:
        continue
    try:
        number = int(d.get("Number"))
    except Exception:
        continue
    used_form_indices.setdefault(number, set()).add(int(m.group(1)))


def new_form_dexid(number):
    used = used_form_indices.setdefault(number, set())
    index = 1
    while index in used:
        index += 1
    used.add(index)
    return f"{number:04d}F{index}"


def source_for_inheritance(record):
    """Pick the most appropriate existing/custom form to inherit metadata/moves."""
    name = record["name"]

    if name == "Combee (Swarm Form)":
        return "Combee (Male Form)"

    # Mega regional forms should inherit that regional form, not standard species.
    m = re.match(r"^(.+?) \(Mega (.+?) Form\)$", name)
    if m:
        species, modifier = m.groups()
        if modifier not in {"X", "Y", "Z"}:
            candidate = f"{species} ({modifier} Form)"
            if candidate in record_by_name or candidate in existing:
                return candidate

    if name.endswith(" (Mega Eternal Flower Form)"):
        return name.replace(" (Mega Eternal Flower Form)", " (Eternal Flower Form)")

    hint = record.get("base_hint")
    if hint:
        if hint in record_by_name or hint in existing:
            return hint
        found = find_existing_name(hint)
        if found:
            return found

    root = root_name(name)
    if root in record_by_name or root in existing:
        return root
    found = find_existing_name(root)
    if found:
        return found
    return None


# Build a staging map so forms can inherit from custom bases regardless of source order.
staged = {}

def extract_from_name(text):
    if not text:
        return None
    text = text.strip()
    # Conditions usually follow in parentheses.
    base = re.sub(r"\s*\([^)]*\)\s*$", "", text).strip()
    base = base.replace("K. Growlithe", "Growlithe")
    return base or None


def parse_eevee_targets(text):
    if not text:
        return []
    targets = []
    # Only use this for the Eevee edit, where the field is explicitly a list of targets.
    for name, condition in re.findall(r"([^,]+?)\s*\(([^)]+)\)\s*(?:,|$)", text):
        name = name.strip()
        condition = condition.strip().lstrip("*")
        if not name:
            continue
        targets.append({
            "To": name,
            "Kind": "Special",
            "Special": condition
        })
    return targets


# First pass creates JSON dictionaries with explicit source values.
for r in records:
    name = r["name"]
    source_name = find_existing_name(name) if r.get("edit") else None
    old = existing.get(source_name, {}) if source_name else existing.get(name, {})

    number = assigned_numbers[name]
    is_form = bool(re.search(r"\([^)]* Form\)$", name))

    if old:
        dexid = str(old.get("DexID", ""))
    elif is_form:
        dexid = new_form_dexid(number)
    else:
        dexid = f"{number:04d}"

    def take(field, fallback=None):
        value = r.get(field)
        if value is None or value == "":
            return old.get(field, fallback)
        return value

    evolutions = list(old.get("Evolutions", [])) if r.get("edit") else []

    explicit_from = extract_from_name(r.get("evolves_from"))
    if explicit_from:
        evolutions.append({
            "From": explicit_from,
            "Kind": "Special",
            "Special": r.get("evolves_from")
        })

    if r.get("edit") and name == "Eevee":
        # Keep Eevee's stock evolution data and add the source document's additional targets.
        existing_targets = {
            e.get("To") for e in evolutions if isinstance(e, dict) and e.get("To")
        }
        for evo in parse_eevee_targets(r.get("evolution_text")):
            if evo["To"] not in existing_targets:
                evolutions.append(evo)
                existing_targets.add(evo["To"])

    data = {
        "Number": number,
        "DexID": dexid,
        "Name": name,
        "Type1": take("Type1", ""),
        "Type2": take("Type2", ""),
        "BaseHP": take("BaseHP", 3),
        "Strength": take("Strength", 1),
        "MaxStrength": take("MaxStrength", 3),
        "Dexterity": take("Dexterity", 1),
        "MaxDexterity": take("MaxDexterity", 3),
        "Vitality": take("Vitality", 1),
        "MaxVitality": take("MaxVitality", 3),
        "Special": take("Special", 1),
        "MaxSpecial": take("MaxSpecial", 3),
        "Insight": take("Insight", 1),
        "MaxInsight": take("MaxInsight", 3),
        "Ability1": take("Ability1", ""),
        "Ability2": take("Ability2", ""),
        "HiddenAbility": take("HiddenAbility", ""),
        "EventAbilities": take("EventAbilities", ""),
        "RecommendedRank": take("RecommendedRank", "Standard"),
        "GenderType": old.get("GenderType", ""),
        "Legendary": old.get("Legendary", False),
        "GoodStarter": old.get("GoodStarter", False),
        "_id": old.get("_id") if r.get("edit") and old.get("_id") else safe_slug(name),
        "DexCategory": take("DexCategory", None),
        "Height": take("Height", None),
        "Weight": take("Weight", None),
        "DexDescription": take("DexDescription", None),
        "Evolutions": evolutions,
        "Image": old.get("Image", ""),
        "Moves": list(r.get("Moves") or []),
    }
    staged[name] = data


# Second pass: inherit omitted metadata and learnsets.
def get_stage_or_existing(name):
    if not name:
        return None
    if name in staged:
        return staged[name]
    if name in existing:
        return existing[name]
    found = find_existing_name(name)
    return existing.get(found) if found else None


for r in records:
    name = r["name"]
    data = staged[name]
    inherit_name = source_for_inheritance(r)
    parent = get_stage_or_existing(inherit_name)

    if parent:
        for field in (
            "DexCategory", "Height", "Weight", "DexDescription",
            "GenderType", "Legendary", "GoodStarter"
        ):
            if data.get(field) in (None, "", {}):
                data[field] = parent.get(field)

        if not data["Moves"]:
            data["Moves"] = list(parent.get("Moves", []))

        # Mega forms have a meaningful previous form for move aggregation/forms.
        if "Mega " in name and not data["Evolutions"]:
            data["Evolutions"] = [{
                "From": parent.get("Name", inherit_name),
                "Kind": "Mega",
                "Item": ""
            }]

    if not data.get("DexCategory"):
        data["DexCategory"] = "Unknown Pokémon"
    if not data.get("Height"):
        data["Height"] = {"Meters": 0.0, "Feet": 0.0}
    if not data.get("Weight"):
        data["Weight"] = {"Kilograms": 0.0, "Pounds": 0.0}
    if data.get("DexDescription") is None:
        data["DexDescription"] = ""


# Write all 355 entries. Existing exact-name entries are intentionally overwritten
# when the source document defines them.
written = []
for r in records:
    name = r["name"]
    data = staged[name]

    target = existing_paths.get(name)
    if r.get("edit"):
        found = find_existing_name(name)
        target = existing_paths.get(found)
    if target is None:
        target = POKEDEX_DIR / f"{name}.json"

    # Back up any existing exact file before overwriting it.
    if target.exists():
        backup_target = backup_dir / (target.name + ".bak")
        if not backup_target.exists():
            shutil.copy2(target, backup_target)

    target.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    written.append((name, target.name, len(data["Moves"])))


# Patch dbhelper.py: stock schema only has room for 28 moves.
dbtext = DBHELPER.read_text(encoding="utf-8")

if "MAX_LEARNSET_MOVES = 64" not in dbtext:
    insertion = "MAX_LEARNSET_MOVES = 64\n\n"
    marker = "table_names = {"
    pos = dbtext.find(marker)
    if pos == -1:
        raise SystemExit("Could not patch dbhelper.py: table_names marker missing.")
    dbtext = dbtext[:pos] + insertion + dbtext[pos:]

dbtext = dbtext.replace(
    "[f', move{x} text, rank{x} integer' for x in range(28)]",
    "[f', move{x} text, rank{x} integer' for x in range(MAX_LEARNSET_MOVES)]"
)

old_padding = """                    moves += [None] * (58 - len(moves))  # pad value to number of moves maximum
                    tmp = ','.join('?' * 58)
"""
new_padding = """                    max_learnset_values = 2 + (MAX_LEARNSET_MOVES * 2)
                    if len(moves) > max_learnset_values:
                        raise ValueError(
                            f"{tmp_info['Name']} has more than {MAX_LEARNSET_MOVES} moves"
                        )
                    moves += [None] * (max_learnset_values - len(moves))
                    tmp = ','.join('?' * max_learnset_values)
"""
if old_padding in dbtext:
    dbtext = dbtext.replace(old_padding, new_padding)
elif "max_learnset_values = 2 + (MAX_LEARNSET_MOVES * 2)" not in dbtext:
    raise SystemExit("Could not patch dbhelper.py learnset padding safely.")

compile(dbtext, str(DBHELPER), "exec")
DBHELPER.write_text(dbtext, encoding="utf-8")


# Patch PokeRole-Helper.py:
# 1) Preserve/ensure the user's current /stats expansion.
# 2) Let owner-only whoLearns inspect all 64 learnset columns too.
bottext = BOT_FILE.read_text(encoding="utf-8")

stats_import = "from statsExtra import pokemon_extra_stats_text\n"
if stats_import not in bottext:
    marker = "from dbhelper import Database\n"
    if marker in bottext:
        bottext = bottext.replace(marker, marker + stats_import, 1)
    else:
        bottext = stats_import + bottext

stats_call = "    output += pokemon_extra_stats_text(pokemon, found[1], found[2], version)\n"
if stats_call not in bottext:
    type_block = (
        "    if found[2] == '':\n"
        "        output += '\\n'\n"
        "    else:\n"
        "        output += f' / {found[2].capitalize()}\\n'\n"
    )
    if type_block not in bottext:
        raise SystemExit("Could not safely add the /stats extra-details call.")
    bottext = bottext.replace(type_block, type_block + stats_call, 1)

bottext = bottext.replace(
    "[f'move{x}=\"{move}\"' for x in range(28)]",
    "[f'move{x}=\"{move}\"' for x in range(64)]"
)

compile(bottext, str(BOT_FILE), "exec")
BOT_FILE.write_text(bottext, encoding="utf-8")


# The database MUST be rebuilt because both Pokémon rows and the learnset schema changed.
if DB_FILE.exists():
    DB_FILE.unlink()

print()
print("CUSTOM POKEMON INSTALL COMPLETE")
print("--------------------------------")
print(f"Processed: {len(records)} source statblocks")
print(f"Pokédex JSON files written/updated: {len(written)}")
print(f"Largest learnset: {max((m for _, _, m in written), default=0)} moves")
print("Learnset capacity expanded to: 64 moves per Pokémon")
print("pokerole_v3.db removed so it will rebuild on next startup.")
print()
print("Restart the bot normally.")
print("No %sync_global is required.")
