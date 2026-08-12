from pathlib import Path
import json
import re
import unicodedata
import difflib

ROOT = Path(".")
POKEDEX_DIR = ROOT / "pokerole_data" / "v3.0" / "Pokedex"
MOVES_DIR = ROOT / "pokerole_data" / "v3.0" / "Moves"
RULES_FILE = ROOT / "additional_move_learners.json"
DB_FILE = ROOT / "pokerole_v3.db"

for required in (POKEDEX_DIR, MOVES_DIR, RULES_FILE):
    if not required.exists():
        raise SystemExit(f"Missing required file/folder: {required}")

rules = json.loads(RULES_FILE.read_text(encoding="utf-8"))


def norm(text):
    text = unicodedata.normalize("NFKD", str(text))
    text = text.encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]", "", text)


def load_json_dir(folder):
    by_name = {}
    paths = {}
    for path in folder.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        name = data.get("Name")
        if name:
            by_name[name] = data
            paths[name] = path
    return by_name, paths


pokemon, pokemon_paths = load_json_dir(POKEDEX_DIR)
moves, _ = load_json_dir(MOVES_DIR)
move_key = {norm(name): name for name in moves}
poke_key = {norm(name): name for name in pokemon}

# Common spelling issues in the supplied learner lists.
ALIASES = {
    "perserker": "Perrserker",
    "carvannah": "Carvanha",
    "ninckit": "Nickit",
    "zweilious": "Zweilous",
    "zweilios": "Zweilous",
    "morepeko": "Morpeko",
    "mabostiff": "Mabosstiff",
    "masbostiff": "Mabosstiff",
    "mimkyu": "Mimikyu",
    "spirtomb": "Spiritomb",
    "octilary": "Octillery",
    "amphaross": "Ampharos",
    "zapdoss": "Zapdos",
    "moltress": "Moltres",
    "fenzadipiti": "Fezandipiti",
    "snoruntv": "Snorunt",
    "galceon": "Glaceon",
    "darmantian": "Darmanitan",
    "vanilite": "Vanillite",
    "vanilish": "Vanillish",
    "vaniluxe": "Vanilluxe",
    "cryognal": "Cryogonal",
    "abomisnow": "Abomasnow",
    "driflbim": "Drifblim",
    "difloon": "Drifloon",
    "gourgiest": "Gourgeist",
    "garbodour": "Garbodor",
    "garbododor": "Garbodor",
    "overqwill": "Overqwil",
    "overqil": "Overqwil",
    "naganedel": "Naganadel",
    "exegutor": "Exeggutor",
    "cresalia": "Cresselia",
    "claydoll": "Claydol",
    "oranaguru": "Oranguru",
    "silveon": "Sylveon",
    "altarria": "Altaria",
    "luminion": "Lumineon",
    "diance": "Diancie",
    "hydraple": "Hydrapple",
    "bouncesweet": "Bounsweet",
    "jarafarig": "Girafarig",
    "dolliv": "Dolliv",
    "graffaiai": "Grafaiai",
    "frilish": "Frillish",
    "keckleon": "Kecleon",
    "chancy": "Chansey",
    "venosaur": "Venusaur",
    "cottony": "Cottonee",
    "gossifluer": "Gossifleur",
    "arbolivia": "Arboliva",
    "wishcash": "Whiscash",
    "carnevine": "Carnivine",
    "maraenie": "Mareanie",
    "garboceon": "Garbocean",
    "dottle": "Dottler",
    "medite": "Meditite",
    "grimsnarl": "Grimmsnarl",
    "mrrhyme": "Mr. Rime",
    "mrryme": "Mr. Rime",
    "regigas": "Regigigas",
    "typplosion": "Typhlosion",
    "poygon": "Porygon",
    "poygon2": "Porygon 2",
    "porygonz": "Porygon-Z",
    "porygon2": "Porygon 2",
    "porygon3": "Porygon 3",
    "scizzor": "Scizor",
    "flechinder": "Fletchinder",
    "tailow": "Taillow",
    "squawkibilly": "Squawkabilly",
    "wattrel": "Wattrel",
    "revavroom": "Revavroom",
    "mareani": "Mareanie",
    "rhyperion": "Rhyperior",
    "duoblade": "Doublade",
    "duraludon": "Duraludon",
    "alieyahn": "Aileyahn",
    "quilfish": "Qwilfish",
    "quillfish": "Qwilfish",
    "overquil": "Overqwil",
    "nihilago": "Nihilego",
    "girdurr": "Gurdurr",
    "bayleaf": "Bayleef",
    "farigiraph": "Farigiraf",
    "scornovillain": "Scovillain",
    "daschbun": "Dachsbun",
    "elektrike": "Electrike",
    "woshien": "Wo-Chien",
    "ogerpon": "Ogerpon",
}

# Region abbreviations from the user's key.
REGION_FORMS = {
    "A": ["Alolan"],
    "G": ["Galarian"],
    "J": ["Johtonian"],
    "U": ["Unovan"],
    "O": ["Orrean"],
    "R": ["Ruskovan"],
    "I": ["Islas Lluvia De'estrellas", "Islas Lluvia De’estrellas"],
    "S": ["Sinnohnian"],
    "P": ["Paldean"],
    # Ambiguous in the source key. Try the regional form first, then base/origin.
    "K": ["Kantonian", "Kalosian"],
    "H": ["Hisuian", "Hoennian"],
}

ORIGIN_RANGES = [
    (1, 151, "Kantonian"),
    (152, 251, "Johtonian"),
    (252, 386, "Hoennian"),
    (387, 493, "Sinnohnian"),
    (494, 649, "Unovan"),
    (650, 721, "Kalosian"),
    (722, 809, "Alolan"),
    (810, 905, "Galarian"),
    (906, 9999, "Paldean"),
]


def exactish(name):
    if name in pokemon:
        return name
    k = norm(name)
    if k in poke_key:
        return poke_key[k]
    alias = ALIASES.get(k)
    if alias:
        ak = norm(alias)
        if ak in poke_key:
            return poke_key[ak]
    return None


def corrected_base_name(name):
    """Correct a species spelling without accidentally choosing a form."""
    k = norm(name)
    alias = ALIASES.get(k)
    if alias:
        return alias
    return name


def root_name(name):
    return re.sub(r"\s+\([^)]* Form\)$", "", name).strip()


def base_forms(base):
    """Return every existing form when no unsuffixed species entry exists."""
    base = corrected_base_name(base)
    exact = exactish(base)
    if exact:
        return [exact]

    bk = norm(base)
    candidates = [
        name for name in pokemon
        if norm(root_name(name)) == bk
    ]
    if candidates:
        return sorted(candidates)

    # Strong typo correction against roots.
    roots = {}
    for name in pokemon:
        roots.setdefault(norm(root_name(name)), root_name(name))
    close = difflib.get_close_matches(bk, list(roots), n=1, cutoff=0.88)
    if close:
        corrected = roots[close[0]]
        exact = exactish(corrected)
        if exact:
            return [exact]
        return sorted(
            name for name in pokemon
            if norm(root_name(name)) == norm(corrected)
        )
    return []


def dex_number(name):
    try:
        return int(pokemon[name].get("Number"))
    except Exception:
        return None


def origin_region(name):
    num = dex_number(name)
    if num is None:
        return None
    for lo, hi, region in ORIGIN_RANGES:
        if lo <= num <= hi:
            return region
    return None


def regional_candidates(base, form_names):
    # First normalize typo in the base species itself.
    base = corrected_base_name(base)
    base_options = base_forms(base)
    roots = {root_name(x) for x in base_options} or {base}

    matches = []
    for root in roots:
        for region in form_names:
            candidate = exactish(f"{root} ({region} Form)")
            if candidate:
                matches.append(candidate)

            # Handles compound custom forms such as
            # Toxtricity (Orrean Smouldering Form).
            for name in pokemon:
                if norm(root_name(name)) != norm(root):
                    continue
                inside = re.search(r"\(([^)]*)\)", name)
                if inside and region.casefold() in inside.group(1).casefold():
                    matches.append(name)

    # Preserve order, remove dupes.
    return list(dict.fromkeys(matches))


def resolve_token(raw):
    s = re.sub(r"\s+", " ", raw.strip().strip(".")).strip()
    if not s or s == "???":
        return []

    # Source notation for male Combee.
    if norm(s) == norm("(Male) Combee"):
        target = exactish("Combee (Male Form)")
        return [target] if target else []

    # A few source labels refer unambiguously to an existing named form.
    explicit_labels = {
        norm("Unown Swarm"): "Unown (Swarm Form)",
        # The learner document says O. Electivire, while the supplied custom
        # Pokédex defines this variant as Alolan Electivire.
        norm("O. Electivire"): "Electivire (Alolan Form)",
    }
    if norm(s) in explicit_labels:
        target = exactish(explicit_labels[norm(s)])
        return [target] if target else []

    # Pa'u Oricorio is written "P. Oricorio" in the Psychic move list.
    if norm(s) == norm("P. Oricorio"):
        target = exactish("Oricorio (Pa'u Form)")
        return [target] if target else []

    # Full-word form prefixes.
    for prefix, form in (
        ("Corrupted ", "Corrupted"),
        ("Rift ", "Rift"),
        ("Delta ", "Delta"),
        ("Toxic Chain ", "Toxic Chain"),
        ("Hull-Biter ", "Hull-Biter"),
        ("Galarian ", "Galarian"),
        ("Alolan ", "Alolan"),
        ("Hisuian ", "Hisuian"),
    ):
        if s.casefold().startswith(prefix.casefold()):
            base = s[len(prefix):].strip()
            roots = base_forms(base)
            root = root_name(roots[0]) if roots else base
            candidate = exactish(f"{root} ({form} Form)")
            return [candidate] if candidate else []

    # Region abbreviation.
    m = re.match(r"^([A-Za-z])\.\s*(.+)$", s)
    if m:
        abbr = m.group(1).upper()
        base = m.group(2).strip()

        forms = REGION_FORMS.get(abbr, [])
        matches = regional_candidates(base, forms)
        if matches:
            return matches

        # If the abbreviation names the Pokémon's native region,
        # the bot normally stores that form without a regional suffix.
        plain = base_forms(base)
        if plain:
            native = origin_region(plain[0])
            if native in forms:
                return [x for x in plain if "(" not in x or "Mega" not in x]

        # Unknown E. notation appears for Zangoose/Seviper in the source;
        # neither has such a form in this Pokédex, so use the ordinary species.
        if abbr == "E" and plain:
            return plain

        return []

    # Direct exact / typo-corrected match.
    direct = exactish(s)
    if direct:
        return [direct]

    # Generic species whose bot data consists only of named forms
    # (Toxtricity, Urshifu, Oricorio, Basculegion, etc.).
    return base_forms(s)


def parse_tokens(learner_text):
    # Fix three places where a period was used between species instead of a comma.
    learner_text = learner_text.replace("Regirock. Ogrepon", "Regirock, Ogerpon")
    learner_text = learner_text.replace("G. Scrafty. Kirlia", "G. Scrafty, Kirlia")
    learner_text = learner_text.replace("Tangrowth. Roserade", "Tangrowth, Roserade")
    learner_text = learner_text.replace("G, Rapidash", "G. Rapidash")
    return [x.strip() for x in learner_text.split(",") if x.strip()]


def already_has_move(data, move_name):
    mk = norm(move_name)
    for entry in data.get("Moves", []):
        if norm(entry.get("Name", "")) == mk:
            return True
    return False


def add_move(name, move_name, rank):
    data = pokemon[name]
    if already_has_move(data, move_name):
        return False, "duplicate"

    data.setdefault("Moves", []).append({
        "Learned": rank,
        "Name": move_name
    })
    pokemon_paths[name].write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return True, "added"


# Cache original move ownership for the broad "all Pokémon that learn X" rules.
original_move_owners = {}
for trigger in ("Leech Seed", "Ingrain"):
    owners = []
    for name, data in pokemon.items():
        if already_has_move(data, trigger):
            owners.append(name)
    original_move_owners[trigger] = owners


added = 0
duplicates = 0
unresolved = []
missing_moves = []
targets_by_move = {}


def broad_targets(learner_text):
    low = learner_text.casefold()

    if "all dragon types" in low:
        return [
            name for name, data in pokemon.items()
            if data.get("Type1") == "Dragon" or data.get("Type2") == "Dragon"
        ]

    if "all fire-types" in low or "all fire types" in low:
        return [
            name for name, data in pokemon.items()
            if data.get("Type1") == "Fire" or data.get("Type2") == "Fire"
        ]

    normalized = norm(learner_text)
    if norm("All Pokémon that normally learn Leech Seed") in normalized:
        return original_move_owners["Leech Seed"]

    if norm("All Pokémon that learn Ingrain") in normalized:
        return original_move_owners["Ingrain"]

    if "all ancient paradox" in low:
        # The stock Pokédex identifies canonical Paradox Pokémon by category.
        return [
            name for name, data in pokemon.items()
            if data.get("DexCategory") == "Paradox Pokémon"
            and not name.startswith("Iron ")
        ]

    if "all future paradox" in low:
        return [
            name for name, data in pokemon.items()
            if data.get("DexCategory") == "Paradox Pokémon"
            and name.startswith("Iron ")
        ]

    return None


for rule in rules:
    move_from_source = rule["Move"]
    canonical_move = move_key.get(norm(move_from_source))
    if not canonical_move:
        missing_moves.append(move_from_source)
        continue

    broad = broad_targets(rule["Learners"])
    if broad is not None:
        targets = broad
    else:
        targets = []
        for token in parse_tokens(rule["Learners"]):
            if token.strip().strip(".") == "???":
                continue
            resolved = resolve_token(token)
            if not resolved:
                unresolved.append({
                    "Move": canonical_move,
                    "Rank": rule["Rank"],
                    "SourceName": token
                })
            else:
                targets.extend(resolved)

    targets = list(dict.fromkeys(targets))
    targets_by_move[canonical_move] = targets

    for target in targets:
        changed, reason = add_move(target, canonical_move, rule["Rank"])
        if changed:
            added += 1
        else:
            duplicates += 1


# Force DB rebuild because /pokelearns is generated from these JSON files.
if DB_FILE.exists():
    DB_FILE.unlink()

report = {
    "RulesProcessed": len(rules),
    "MoveAssignmentsAdded": added,
    "ExistingDuplicateAssignmentsSkipped": duplicates,
    "UnresolvedSourceNames": unresolved,
    "MissingMoveDefinitions": missing_moves,
    "ResolvedTargetCounts": {
        move: len(targets) for move, targets in targets_by_move.items()
    }
}

Path("additional_move_learners_install_report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print()
print("ADDITIONAL /POKELEARNS UPDATE COMPLETE")
print("--------------------------------------")
print(f"Move rules processed: {len(rules)}")
print(f"New move assignments added: {added}")
print(f"Existing duplicate assignments skipped: {duplicates}")
print(f"Unresolved source names skipped: {len(unresolved)}")
print(f"Missing move definitions: {len(missing_moves)}")
print()
print("A detailed report was written to:")
print("additional_move_learners_install_report.json")
print()
print("pokerole_v3.db was removed so /pokelearns rebuilds on next startup.")
