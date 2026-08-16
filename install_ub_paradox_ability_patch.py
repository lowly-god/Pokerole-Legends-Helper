from pathlib import Path
import json
import re
import shutil
import unicodedata

ROOT = Path(".")
POKEDEX_DIR = ROOT / "pokerole_data" / "v3.0" / "Pokedex"
DB_FILE = ROOT / "pokerole_v3.db"

BOT_CANDIDATES = [
    ROOT / "PokeRole-Helper.py",
    ROOT / "PokeRole_Helper.py",
]
BOT_FILE = next((p for p in BOT_CANDIDATES if p.exists()), None)

if BOT_FILE is None:
    raise SystemExit("Could not find PokeRole-Helper.py in the main bot folder.")
if not POKEDEX_DIR.exists():
    raise SystemExit("Could not find pokerole_data/v3.0/Pokedex.")

BACKUP_DIR = ROOT / "ub_paradox_patch_backups"
BACKUP_DIR.mkdir(exist_ok=True)


def norm(value):
    value = unicodedata.normalize("NFKD", str(value))
    value = value.encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]", "", value)


def load_pokedex():
    data = {}
    paths = {}
    key = {}
    for path in POKEDEX_DIR.glob("*.json"):
        try:
            info = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        name = info.get("Name")
        if name:
            data[name] = info
            paths[name] = path
            key[norm(name)] = name
    return data, paths, key


pokemon, pokemon_paths, pokemon_key = load_pokedex()


def find_name(name):
    if name in pokemon:
        return name
    return pokemon_key.get(norm(name))


def require(name):
    found = find_name(name)
    if not found:
        raise SystemExit(f"Required Pokémon not found: {name}")
    return found


def backup_json(name):
    path = pokemon_paths[name]
    backup = BACKUP_DIR / (path.name + ".bak")
    if not backup.exists():
        shutil.copy2(path, backup)


def save(name):
    pokemon_paths[name].write_text(
        json.dumps(pokemon[name], ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def set_hidden(name, ability):
    name = require(name)
    backup_json(name)
    pokemon[name]["HiddenAbility"] = ability
    save(name)


def replace_ability(name, old_ability, new_ability):
    name = require(name)
    backup_json(name)
    data = pokemon[name]
    fields = ("Ability1", "Ability2", "HiddenAbility", "EventAbilities")
    replaced = False
    for field in fields:
        if norm(data.get(field, "")) == norm(old_ability):
            data[field] = new_ability
            replaced = True
    if not replaced:
        for field in ("Ability1", "Ability2"):
            if not data.get(field):
                data[field] = new_ability
                replaced = True
                break
    save(name)
    return replaced


def set_primary(name, ability):
    name = require(name)
    backup_json(name)
    pokemon[name]["Ability1"] = ability
    save(name)


def add_move(name, move, rank):
    name = require(name)
    backup_json(name)
    data = pokemon[name]
    moves = data.setdefault("Moves", [])
    if any(norm(entry.get("Name", "")) == norm(move) for entry in moves):
        return False
    moves.append({"Learned": rank, "Name": move})
    save(name)
    return True


POKEMON_ALIASES = {
    "UB-01 Symbiont": "Nihilego",
    "UB-02 Absorption": "Buzzwole",
    "UB-02 Absorbtion": "Buzzwole",
    "UB-03 Beauty": "Pheromosa",
    "UB-04 Lightning": "Xurkitree",
    "UB-04 Lighting": "Xurkitree",
    "UB-05 Blaster": "Celesteela",
    "UB-06 Blade": "Kartana",
    "UB-07 Glutton": "Guzzlord",
    "UB-08 Adhesive": "Poipole",
    "UB-09 Stinger": "Naganadel",
    "UB-10 Assembly": "Stakataka",
    "UB-11 Burst": "Blacephalon",
}

UB_HIDDEN = {
    "Nihilego": "Corrosion",
    "Buzzwole": "Iron Fist",
    "Pheromosa": "Queenly Majesty",
    "Xurkitree": "Electric Surge",
    "Celesteela": "Mega Launcher",
    "Kartana": "Sharpness",
    "Guzzlord": "Gluttony",
    "Poipole": "Neuroforce",
    "Naganadel": "Neuroforce",
    "Stakataka": "Solid Rock",
    "Blacephalon": "Reckless",
}

UB_MOVES = {
    "Nihilego": [
        ("Parasitize", "Standard"),
        ("Virus Pulse", "Advanced"),
        ("Cosmic Corrosion", "Ace"),
    ],
    "Buzzwole": [
        ("Parasitize", "Standard"),
        ("Fisticuffs", "Advanced"),
        ("Bulk Breaker", "Ace"),
    ],
    "Pheromosa": [("Chic Chop", "Ace")],
    "Xurkitree": [
        ("Electro Whip", "Expert"),
        ("Tesla Shock", "Ace"),
    ],
    "Celesteela": [("Dual Cannon", "Ace")],
    "Kartana": [
        ("Vorpal Blade", "Expert"),
        ("Paper Cutter", "Ace"),
    ],
    "Guzzlord": [("Devouring Abyss", "Ace")],
    "Poipole": [("Virus Pulse", "Advanced")],
    "Naganadel": [
        ("Imperial Majesty", "Advanced"),
        ("Virus Pulse", "Advanced"),
        ("Neurotoxin Needle", "Ace"),
    ],
    "Stakataka": [("Blockade Barrage", "Ace")],
    "Blacephalon": [
        ("Uncontrolled Burn Off", "Advanced"),
        ("Mind Blown", "Ace"),
    ],
}

PARADOX_HIDDEN = {
    "Great Tusk": "Rock Head",
    "Scream Tail": "Prankster",
    "Brute Bonnet": "Poison Heal",
    "Flutter Mane": "Perish Body",
    "Slither Wing": "Fluffy",
    "Sandy Shocks": "Steelworker",
    "Roaring Moon": "Veil of Night",
    "Iron Treads": "Surge Surfer",
    "Iron Bundle": "Polished Coat",
    "Iron Hands": "Iron Fist",
    "Iron Jugulis": "Triple Threat",
    "Iron Moth": "Battery",
    "Iron Thorns": "Prime Fury",
    "Iron Valiant": "Download",
}

# Smeargle ability-source adjustments.
smeargle = require("Smeargle")
backup_json(smeargle)
smeargle_data = pokemon[smeargle]
for field in ("Ability1", "Ability2", "HiddenAbility", "EventAbilities"):
    if norm(smeargle_data.get(field, "")) == norm("Own Tempo"):
        smeargle_data[field] = "Blank Canvas"
smeargle_data["HiddenAbility"] = "Masterpiece"
save(smeargle)

# Ability-document replacement/addition notes.
replace_ability("Corsola", "Hustle", "Coral Guard")
set_hidden("Corsola (Galarian Form)", "Coral Guard")
set_hidden("Cursola", "Coral Guard")

for name in ("Pansage", "Simisage", "Pansear", "Simisear", "Panpour", "Simipour"):
    set_hidden(name, "Elemental Boost")

replace_ability("Octillery", "Moody", "Ink Spray")
replace_ability("Grafaiai", "Unburden", "Ink Spray")

for name in (
    "Dugtrio",
    "Hydreigon",
    "Magneton",
    "Magnezone",
    "Dugtrio (Alolan Form)",
    "Dodrio",
    "Wugtrio",
    "Exeggutor",
    "Exeggutor (Alolan Form)",
):
    set_hidden(name, "Triple Threat")

set_hidden("Grimer", "Toxin Tax")
set_hidden("Muk", "Toxin Tax")
set_hidden("Tyrantrum", "Tyrant")
set_primary("Tyranitar (Mega Form)", "Tyrant")

for name, ability in UB_HIDDEN.items():
    set_hidden(name, ability)

for name, ability in PARADOX_HIDDEN.items():
    set_hidden(name, ability)

added_moves = 0
skipped_duplicates = 0
for name, entries in UB_MOVES.items():
    for move, rank in entries:
        if add_move(name, move, rank):
            added_moves += 1
        else:
            skipped_duplicates += 1


# Patch command-level aliases so UB names point to canonical Pokémon data.
bot_backup = BACKUP_DIR / (BOT_FILE.name + ".bak")
if not bot_backup.exists():
    shutil.copy2(BOT_FILE, bot_backup)

bot = BOT_FILE.read_text(encoding="utf-8")

alias_marker = "# LEGENDS_UB_ALIASES"
alias_code = '''
# LEGENDS_UB_ALIASES
POKEMON_ALIASES = {
    "UB-01 Symbiont": "Nihilego",
    "UB-02 Absorption": "Buzzwole",
    "UB-02 Absorbtion": "Buzzwole",
    "UB-03 Beauty": "Pheromosa",
    "UB-04 Lightning": "Xurkitree",
    "UB-04 Lighting": "Xurkitree",
    "UB-05 Blaster": "Celesteela",
    "UB-06 Blade": "Kartana",
    "UB-07 Glutton": "Guzzlord",
    "UB-08 Adhesive": "Poipole",
    "UB-09 Stinger": "Naganadel",
    "UB-10 Assembly": "Stakataka",
    "UB-11 Burst": "Blacephalon",
}
_POKEMON_ALIAS_KEYS = {k.casefold(): v for k, v in POKEMON_ALIASES.items()}


def resolve_pokemon_alias(name):
    return _POKEMON_ALIAS_KEYS.get(str(name).casefold(), name)


'''

if alias_marker not in bot:
    marker = "def rank_dist("
    pos = bot.find(marker)
    if pos == -1:
        raise SystemExit("Could not safely locate rank_dist() in PokeRole-Helper.py.")
    bot = bot[:pos] + alias_code + bot[pos:]


def patch_function_start(text, signature, variable):
    marker = signature + "\n"
    pos = text.find(marker)
    if pos == -1:
        return text, False

    start = pos + len(marker)
    insertion = f"    {variable} = resolve_pokemon_alias({variable})\n"
    window = text[start:start + 250]
    if insertion.strip() in window:
        return text, True

    if text.startswith("    global database\n", start):
        start += len("    global database\n")

    return text[:start] + insertion + text[start:], True


for signature, variable in (
    ("async def pkmnstatshelper(poke: str, version: str):", "poke"),
    ("async def pkmnlearnshelper(poke: str, rank: ensure_rank = 'Master', version: str = \"v3.0\"):", "poke"),
    ("async def move_aggregator_tmp(poke: str, rank: str, denote_moves: bool = False, version: str = \"v3.0\") -> dict:", "poke"),
    ("async def getPokemonAbilities(pkmn, version=\"v3.0\"):", "pkmn"),
    ("async def pkmn_stat_msg_helper(pokemon, found, version: str):", "pokemon"),
):
    bot, ok = patch_function_start(bot, signature, variable)
    if not ok:
        raise SystemExit(f"Could not safely patch function: {signature}")


autocomplete_start = bot.find("async def pokemon_autocomplete(")
autocomplete_end = bot.find("\nasync def ability_autocomplete(", autocomplete_start)
if autocomplete_start == -1 or autocomplete_end == -1:
    raise SystemExit("Could not safely locate pokemon_autocomplete().")

section = bot[autocomplete_start:autocomplete_end]
autocomplete_marker = "# LEGENDS_UB_ALIAS_AUTOCOMPLETE"
if autocomplete_marker not in section:
    target = "        result = [x[0] for x in database.custom_query(query, version=version)]\n"
    replacement = target + (
        "        # LEGENDS_UB_ALIAS_AUTOCOMPLETE\n"
        "        alias_result = [name for name in POKEMON_ALIASES "
        "if current.casefold() in name.casefold()]\n"
        "        result = list(dict.fromkeys(alias_result + result))[:25]\n"
    )
    if target not in section:
        raise SystemExit("Could not safely patch Pokémon autocomplete result.")
    section = section.replace(target, replacement, 1)
    bot = bot[:autocomplete_start] + section + bot[autocomplete_end:]

compile(bot, str(BOT_FILE), "exec")
BOT_FILE.write_text(bot, encoding="utf-8")

if DB_FILE.exists():
    DB_FILE.unlink()

print()
print("ULTRA BEAST / PARADOX / ABILITY PATCH COMPLETE")
print("---------------------------------------------")
for alias, canonical in POKEMON_ALIASES.items():
    if "Absorbtion" not in alias and "Lighting" not in alias:
        print(f"{alias} -> {canonical}")
print()
print(f"New UB move assignments added: {added_moves}")
print(f"Already-present UB move assignments skipped: {skipped_duplicates}")
print(f"Ultra Beast Hidden Abilities updated: {len(UB_HIDDEN)}")
print(f"Paradox Hidden Abilities updated: {len(PARADOX_HIDDEN)}")
print("Ability-document replacement notes applied.")
print("pokerole_v3.db removed so it will rebuild next startup.")
print()
print("Restore PokeRole-Helper.py as the startup file and start the bot.")
print("No %sync_global is required.")
