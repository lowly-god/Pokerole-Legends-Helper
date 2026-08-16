import json
import re
import time
from pathlib import Path

import requests

SHOWDOWN_URL = "https://raw.githubusercontent.com/smogon/pokemon-showdown/refs/heads/master/data/learnsets.ts"

# Versioned cache because the older helper stored only each Pokémon's newest
# machine generation and therefore discarded the historical HM information
# needed by this version.
CACHE_FILE = Path("machine_learnsets_cache_v3.json")
CACHE_MAX_AGE = 7 * 24 * 60 * 60

_loaded = None


# Last core-series generation in which each move was actually an HM.
#
# Gen 6 / ORAS:
#   Cut, Fly, Surf, Strength, Waterfall, Rock Smash, Dive
#
# Gen 4:
#   Defog (DPPt), Whirlpool (HGSS), Rock Climb (DPPt/HGSS)
#
# Gen 3:
#   Flash
LEGACY_HM_LAST_GEN = {
    "cut": 6,
    "fly": 6,
    "surf": 6,
    "strength": 6,
    "waterfall": 6,
    "rocksmash": 6,
    "dive": 6,
    "defog": 4,
    "whirlpool": 4,
    "rockclimb": 4,
    "flash": 3,
}


# Manual Tutor additions used by the Legends ruleset. These are kept outside
# the Showdown cache so a cache refresh cannot remove the custom compatibility.
MANUAL_TUTOR_ADDITIONS = {
    "appletun": {"belch"},
    "flapple": {"bugbite"},
}


# Complete Sword/Shield TR00-TR99 move set.
# These are separated from ordinary Gen 8 machine moves so /poke_learns can
# display TM and TR as different acquisition methods.
GEN8_TR_MOVES = {
    "swordsdance", "bodyslam", "flamethrower", "hydropump", "surf",
    "icebeam", "blizzard", "lowkick", "thunderbolt", "thunder",
    "earthquake", "psychic", "agility", "focusenergy", "metronome",
    "fireblast", "waterfall", "amnesia", "leechlife", "triattack",
    "substitute", "reversal", "sludgebomb", "spikes", "outrage",
    "psyshock", "endure", "sleeptalk", "megahorn", "batonpass",
    "encore", "irontail", "crunch", "shadowball", "futuresight",
    "uproar", "heatwave", "taunt", "trick", "superpower",
    "skillswap", "blazekick", "hypervoice", "overheat", "cosmicpower",
    "muddywater", "irondefense", "dragonclaw", "bulkup", "calmmind",
    "leafblade", "dragondance", "gyroball", "closecombat", "toxicspikes",
    "flareblitz", "aurasphere", "poisonjab", "darkpulse", "seedbomb",
    "xscissor", "bugbuzz", "dragonpulse", "powergem", "focusblast",
    "energyball", "bravebird", "earthpower", "nastyplot", "zenheadbutt",
    "flashcannon", "leafstorm", "powerwhip", "gunkshot", "ironhead",
    "stoneedge", "stealthrock", "grassknot", "sludgewave", "heavyslam",
    "electroball", "foulplay", "storedpower", "allyswitch", "scald",
    "workup", "wildcharge", "drillrun", "heatcrash", "hurricane",
    "playrough", "venomdrench", "dazzlinggleam", "darkestlariat",
    "highhorsepower", "throatchop", "pollenpuff", "psychicfangs",
    "liquidation", "bodypress",
}


def _to_id(text):
    return re.sub(r"[^a-z0-9]", "", str(text).casefold())


def _parse_showdown(text):
    """Return species -> move -> source generations by method.

    Pokémon Showdown learnset strings use source letters. For this helper we
    retain:
      M = machine (TM/TR/HM depending on game)
      T = Move Tutor

    Keeping every generation allows us to split modern TM, Gen 8 TR, Tutor,
    and legacy HM compatibility independently.
    """
    species_data = {}
    current = None
    in_learnset = False

    species_re = re.compile(r"^\s*([a-z0-9]+):\s*\{\s*$")
    move_re = re.compile(r'^\s*([a-z0-9]+):\s*\[(.*?)\],?\s*$')

    for line in text.splitlines():
        if not in_learnset:
            match = species_re.match(line)
            if match and not line.startswith("\t\t"):
                current = match.group(1)
                continue

            if current and re.match(r"^\s*learnset:\s*\{\s*$", line):
                in_learnset = True
                species_data[current] = {}
            continue

        if re.match(r"^\s*\},?\s*$", line):
            in_learnset = False
            current = None
            continue

        match = move_re.match(line)
        if not match or not current:
            continue

        move_id = match.group(1)
        sources = re.findall(r'"([^"]+)"', match.group(2))

        methods = {"M": [], "T": []}
        for source in sources:
            m = re.match(r"^(\d+)([MT])", source)
            if not m:
                continue
            generation = int(m.group(1))
            method = m.group(2)
            methods[method].append(generation)

        methods = {
            method: sorted(set(gens))
            for method, gens in methods.items()
            if gens
        }

        if methods:
            species_data[current][move_id] = methods

    return {
        species_id: moves
        for species_id, moves in species_data.items()
        if moves
    }


def _download():
    response = requests.get(SHOWDOWN_URL, timeout=30)
    response.raise_for_status()
    return _parse_showdown(response.text)


def _load_cache():
    try:
        raw = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None

    # Ensure this is the v2/full-history structure.
    if not isinstance(raw, dict):
        return None

    for moves in raw.values():
        if not isinstance(moves, dict):
            return None
        for source_map in moves.values():
            if not isinstance(source_map, dict):
                return None
            if any(method not in {"M", "T"} for method in source_map):
                return None
        break

    return raw


def _save_cache(data):
    try:
        CACHE_FILE.write_text(
            json.dumps(data, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def _get_data():
    global _loaded
    if _loaded is not None:
        return _loaded

    cached = _load_cache()
    cache_fresh = False
    try:
        cache_fresh = (
            CACHE_FILE.exists()
            and (time.time() - CACHE_FILE.stat().st_mtime) < CACHE_MAX_AGE
        )
    except OSError:
        pass

    if cached and cache_fresh:
        _loaded = cached
        return _loaded

    try:
        _loaded = _download()
        _save_cache(_loaded)
        return _loaded
    except Exception as exc:
        if cached:
            _loaded = cached
            return _loaded

        print(f"Could not load TM/TR/Tutor/HM learnsets from Pokémon Showdown: {exc}")
        _loaded = {}
        return _loaded


def _showdown_form_id(name):
    """Convert an official Pokerole form name into Showdown's species id.

    Returns None for forms that cannot safely be identified as an official
    Showdown form. Crucially, CUSTOM regional forms do NOT fall back to their
    ordinary base species.
    """
    name = str(name).strip()

    replacements = {
        "alolanform": "alola",
        "galarianform": "galar",
        "hisuianform": "hisui",
        "paldeanform": "paldea",
        "therianform": "therian",
        "originform": "origin",
        "attackform": "attack",
        "defenseform": "defense",
        "speedform": "speed",
        "skyform": "sky",
        "schoolform": "school",
        "midnightform": "midnight",
        "duskform": "dusk",
        "dawnwingsform": "dawnwings",
        "duskmaneform": "duskmane",
        "ultraform": "ultra",
        "crownedform": "crowned",
        "heroform": "hero",
        "bloodmoonform": "bloodmoon",
        "pauform": "pau",
        "pompomform": "pompom",
        "sensuform": "sensu",
        "bailestyleform": "baile",
        "washform": "wash",
        "heat form": "heat",
        "frostform": "frost",
        "fanform": "fan",
        "mowform": "mow",
    }

    direct = _to_id(name)
    transformed = direct
    for old, new in replacements.items():
        transformed = transformed.replace(_to_id(old), _to_id(new))

    return transformed


def _resolve_species_id(pokemon, data):
    """Resolve only an ACTUAL official species/form.

    No ordinary base-species fallback is used for custom Pokémon or custom
    regional forms. This is what prevents e.g. Gardevoir (Johtonian Form)
    from inheriting normal Gardevoir's TM list.
    """
    name = str(pokemon).strip()

    # Normal Mega forms are the same Pokémon transformed and can use the
    # ordinary species machine list. But compound custom regional Megas such
    # as "(Mega Johtonian Form)" must NOT inherit the base species list.
    mega = re.search(r"\((Mega(?:\s+[^)]*)?)\s+Form\)$", name, flags=re.I)
    if mega:
        inner = mega.group(1).strip()

        if inner.casefold() == "mega":
            base = re.sub(
                r"\s*\(Mega\s+Form\)$",
                "",
                name,
                flags=re.I,
            ).strip()
            base_id = _to_id(base)
            return base_id if base_id in data else None

        # Mega X/Y forms are official and can use the base species.
        if inner.casefold() in {"mega x", "mega y"}:
            base = re.sub(
                r"\s*\(Mega\s+[XY]\s+Form\)$",
                "",
                name,
                flags=re.I,
            ).strip()
            base_id = _to_id(base)
            return base_id if base_id in data else None

        # Anything else in the Mega suffix is custom/regional.
        return None

    # Exact ordinary species or exact official form only.
    candidate = _showdown_form_id(name)
    if candidate in data:
        return candidate

    # Do NOT fall back to the text before "(... Form)".
    return None


def _move_name_map():
    result = {}
    folder = Path("pokerole_data") / "v3.0" / "Moves"

    try:
        paths = folder.glob("*.json")
    except Exception:
        return result

    for path in paths:
        try:
            info = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        name = info.get("Name")
        if name:
            result[_to_id(name)] = name

    return result


def _display_names(move_ids):
    move_names = _move_name_map()
    names = [
        move_names[move_id]
        for move_id in move_ids
        if move_id in move_names
    ]
    return sorted(dict.fromkeys(names), key=str.casefold)


def get_machine_moves(pokemon):
    """Return separated TM, TR, Tutor and HM learnsets for an official Pokémon.

    TM:
        Machine moves from the Pokémon/form's most recent generation with
        official machine compatibility. In Gen 8, TR moves are removed from
        this bucket and shown under TR instead.

    TR:
        Sword/Shield TR compatibility, using exact Gen 8 machine sources
        intersected with the official TR00-TR99 move set.

    Tutor:
        Tutor moves from the most recent generation in which that exact
        Pokémon/form has tutor-source learnset data.

    HM:
        Historical HM compatibility from the last generation where each move
        was actually an HM.
    """
    data = _get_data()
    species_id = _resolve_species_id(pokemon, data)

    empty = {
        "generation": None,
        "tm": [],
        "tr": [],
        "tutor": [],
        "hm": [],
    }

    if not species_id:
        return empty

    move_sources = data.get(species_id, {})
    if not move_sources:
        return empty

    machine_gens = [
        gen
        for source_map in move_sources.values()
        for gen in source_map.get("M", [])
    ]
    latest_machine_gen = max(machine_gens) if machine_gens else None

    tm_ids = set()
    tr_ids = set()
    tutor_ids = set()
    hm_ids = set()

    # Latest official machine list -> TM, except actual Gen 8 TRs.
    if latest_machine_gen is not None:
        for move_id, source_map in move_sources.items():
            gens = source_map.get("M", [])
            if latest_machine_gen not in gens:
                continue

            if latest_machine_gen == 8 and move_id in GEN8_TR_MOVES:
                tr_ids.add(move_id)
            else:
                tm_ids.add(move_id)

    # Keep Gen 8 TR compatibility even for Pokémon that later appeared in Gen 9.
    for move_id, source_map in move_sources.items():
        if move_id in GEN8_TR_MOVES and 8 in source_map.get("M", []):
            tr_ids.add(move_id)

    # Most recent tutor generation for this exact Pokémon/form.
    tutor_gens = [
        gen
        for source_map in move_sources.values()
        for gen in source_map.get("T", [])
    ]
    latest_tutor_gen = max(tutor_gens) if tutor_gens else None

    if latest_tutor_gen is not None:
        for move_id, source_map in move_sources.items():
            if latest_tutor_gen in source_map.get("T", []):
                tutor_ids.add(move_id)

    # Legends-specific Tutor compatibility. These additions are intentionally
    # applied after the official cache so they survive future cache refreshes.
    tutor_ids.update(MANUAL_TUTOR_ADDITIONS.get(species_id, set()))

    # Historical HMs from the last generation each move was an HM.
    for hm_move_id, last_hm_gen in LEGACY_HM_LAST_GEN.items():
        source_map = move_sources.get(hm_move_id, {})
        if last_hm_gen in source_map.get("M", []):
            hm_ids.add(hm_move_id)

    return {
        "generation": latest_machine_gen,
        "tm": _display_names(tm_ids),
        "tr": _display_names(tr_ids),
        "tutor": _display_names(tutor_ids),
        "hm": _display_names(hm_ids),
    }


def machine_moves_section(pokemon):
    learnsets = get_machine_moves(pokemon)

    sections = []

    if learnsets["tm"]:
        sections.append(
            "**TM**\n" + "  |  ".join(learnsets["tm"])
        )

    if learnsets["tr"]:
        sections.append(
            "**TR**\n" + "  |  ".join(learnsets["tr"])
        )

    if learnsets["tutor"]:
        sections.append(
            "**Tutor**\n" + "  |  ".join(learnsets["tutor"])
        )

    if learnsets["hm"]:
        sections.append(
            "**HM**\n" + "  |  ".join(learnsets["hm"])
        )

    if not sections:
        return ""

    return "\n".join(sections) + "\n"
