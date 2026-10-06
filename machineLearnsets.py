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

# Legends HM set. In addition to historical canonical HMs, Legends treats
# Magma Drift and Teleport as HMs. Any Pokémon that already learns one of these
# moves in its authored move list is considered HM-compatible with it.
ALL_HM_MOVE_IDS = {
    "cut", "defog", "dive", "flash", "fly", "magmadrift", "rockclimb",
    "rocksmash", "strength", "surf", "teleport", "waterfall", "whirlpool",
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


# Moves introduced as campaign TR/TM items by the Legends Rules Expansion.
# For these items, TM and TR are alternate item formats for the same
# combined TM / TR / Tutor compatibility pool shown on each Pokémon.
LEGENDS_EXPANSION_MACHINE_MOVE_IDS = {
    "accelerock",
    "acid",
    "acidarmor",
    "acupressure",
    "aquaring",
    "aromatherapy",
    "aromaticmist",
    "assist",
    "autotomize",
    "boomburst",
    "bulletpunch",
    "camouflage",
    "charge",
    "conversion",
    "conversion2",
    "copycat",
    "crushclaw",
    "discharge",
    "doublekick",
    "dragonrush",
    "endeavor",
    "extrasensory",
    "extremespeed",
    "feintattack",
    "firelash",
    "firstimpression",
    "flail",
    "flamewheel",
    "focusenergy",
    "followme",
    "gravity",
    "growth",
    "hardpress",
    "haze",
    "headcharge",
    "headlongrush",
    "headsmash",
    "healingwish",
    "hornleech",
    "hypnosis",
    "icehammer",
    "iceshard",
    "ingrain",
    "jetpunch",
    "kinesis",
    "laserfocus",
    "lastresort",
    "lockon",
    "luckychant",
    "meanlook",
    "mefirst",
    "meteormash",
    "mirrorcoat",
    "mirrormove",
    "mist",
    "moonblast",
    "morningsun",
    "mudbomb",
    "mudslap",
    "mudsport",
    "mysticalpower",
    "nightslash",
    "painsplit",
    "partingshot",
    "petaldance",
    "poisonfang",
    "psychicnoise",
    "pursuit",
    "quiverdance",
    "ragepowder",
    "recover",
    "rockthrow",
    "selfdestruct",
    "shadowpunch",
    "sing",
    "skyattack",
    "slash",
    "snowscape",
    "soak",
    "sonicboom",
    "spiderweb",
    "stickyweb",
    "supercellslam",
    "superfang",
    "supersonic",
    "synchronoise",
    "tailglow",
    "temperflare",
    "terrainpulse",
    "toxicthread",
    "triattack",
    "upperhand",
    "vicegrip",
    "vorpalblade",
    "watersport",
    "wavecrash",
    "wingattack",
    "wish",
    "wrap",
}


# Legends-specific compatibility removals. Keep these outside the downloaded
# Showdown cache so a cache refresh cannot silently restore intentionally
# removed TM/TR/Tutor compatibility. Prefix matching deliberately applies to
# the named species' official forms as well (e.g. Galarian Stunfisk, Therian
# Landorus, Zygarde forms).
MACHINE_MOVE_DENYLIST = {
    "stompingtantrum": {
        "onix", "arbok", "amoonguss", "stunfisk", "landorus", "zygarde",
        "wiglett", "wugtrio", "orthworm", "cursola", "eelektross",
    },
}


def _machine_move_is_denied(pokemon_name, move_id):
    species_id = _to_id(pokemon_name)
    denied_species = MACHINE_MOVE_DENYLIST.get(_to_id(move_id), set())
    return any(
        species_id == base_id or species_id.startswith(base_id)
        for base_id in denied_species
    )


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
    """Return separated TM, TR, Tutor and HM learnsets.

    Curated campaign records marked AuthoritativeMachinePools bypass canonical
    Showdown merging and use their authored TMTRTutor/HM pools exactly.
    Unmarked Pokémon keep the existing dynamic canonical + authored behavior.
    """
    record = _load_current_pokedex_record(pokemon)

    # Exact curated override used by the campaign move-pool document.
    if record and record.get("AuthoritativeMachinePools"):
        teachable_ids = set(_authoritative_machine_pool_ids(record, "tm") or set())
        hm_ids = set(_authoritative_machine_pool_ids(record, "hm") or set())

        # TM/TR/Tutor must never duplicate natural Rank Up moves. HM is exempt.
        rank_up_ids = set()
        for entry in record.get("Moves", []):
            if not isinstance(entry, dict):
                continue
            name = entry.get("Name") or entry.get("Move")
            if name:
                rank_up_ids.add(_to_id(name))
        teachable_ids.difference_update(rank_up_ids)

        # Keep Legends HMs in the dedicated HM section only.
        teachable_ids.difference_update(ALL_HM_MOVE_IDS)

        # Legends-specific compatibility removals still override curated data.
        for denied_move_id in MACHINE_MOVE_DENYLIST:
            if _machine_move_is_denied(pokemon, denied_move_id):
                teachable_ids.discard(denied_move_id)
                hm_ids.discard(denied_move_id)

        return {
            "generation": None,
            "tm": _display_names(teachable_ids),
            "tr": [],
            "tutor": [],
            "hm": _display_names(hm_ids),
        }

    data = _get_data()
    species_id = _resolve_species_id(pokemon, data)

    latest_machine_gen = None
    tm_ids = set()
    tr_ids = set()
    tutor_ids = set()
    hm_ids = set()

    if species_id:
        move_sources = data.get(species_id, {})
        if move_sources:
            machine_gens = [
                gen
                for source_map in move_sources.values()
                for gen in source_map.get("M", [])
            ]
            latest_machine_gen = max(machine_gens) if machine_gens else None

            if latest_machine_gen is not None:
                for move_id, source_map in move_sources.items():
                    gens = source_map.get("M", [])
                    if latest_machine_gen not in gens:
                        continue
                    if latest_machine_gen == 8 and move_id in GEN8_TR_MOVES:
                        tr_ids.add(move_id)
                    else:
                        tm_ids.add(move_id)

            for move_id, source_map in move_sources.items():
                if move_id in GEN8_TR_MOVES and 8 in source_map.get("M", []):
                    tr_ids.add(move_id)

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

            tutor_ids.update(MANUAL_TUTOR_ADDITIONS.get(species_id, set()))

            for hm_move_id, last_hm_gen in LEGACY_HM_LAST_GEN.items():
                source_map = move_sources.get(hm_move_id, {})
                if last_hm_gen in source_map.get("M", []):
                    hm_ids.add(hm_move_id)

    # Explicit authored pools always apply, even when the Pokémon/form has no
    # official Showdown identifier.
    if record:
        tm_ids.update(_explicit_machine_move_ids(record, "tm"))
        tr_ids.update(_explicit_machine_move_ids(record, "tr"))
        tutor_ids.update(_explicit_machine_move_ids(record, "tutor"))
        hm_ids.update(_explicit_machine_move_ids(record, "hm"))

    # Legends HMs are a separate acquisition pool.
    tm_ids.difference_update(ALL_HM_MOVE_IDS)
    tr_ids.difference_update(ALL_HM_MOVE_IDS)
    tutor_ids.difference_update(ALL_HM_MOVE_IDS)

    # A move already learned naturally should not be offered again through a
    # TM, TR, or Tutor pool. HMs are intentionally exempt from this rule.
    if record:
        rank_up_ids = set()
        machine_labels = {
            alias
            for aliases in _EXPLICIT_MACHINE_KEY_ALIASES.values()
            for alias in aliases
        }
        for entry in record.get("Moves", []):
            if not isinstance(entry, dict):
                continue
            learned = _normalise_field_key(entry.get("Learned", ""))
            name = entry.get("Name") or entry.get("Move")
            if name and learned not in machine_labels:
                rank_up_ids.add(_to_id(name))

        tm_ids.difference_update(rank_up_ids)
        tr_ids.difference_update(rank_up_ids)
        tutor_ids.difference_update(rank_up_ids)

    # Apply Legends-specific compatibility removals after merging every source.
    for denied_move_id in MACHINE_MOVE_DENYLIST:
        if _machine_move_is_denied(pokemon, denied_move_id):
            tm_ids.discard(denied_move_id)
            tr_ids.discard(denied_move_id)
            tutor_ids.discard(denied_move_id)
            hm_ids.discard(denied_move_id)

    # Avoid displaying the same teachable move in multiple acquisition pools.
    tr_ids.difference_update(tm_ids)
    tutor_ids.difference_update(tm_ids)
    tutor_ids.difference_update(tr_ids)

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

    # Display TM, TR and Tutor compatibility as one learn pool. Keep the
    # underlying compatibility/item data separate so /item, shops and machine
    # handling continue to distinguish TMs and TRs normally.
    teachable = sorted(
        dict.fromkeys(learnsets["tm"] + learnsets["tr"] + learnsets["tutor"]),
        key=str.casefold,
    )
    if teachable:
        sections.append(
            "**TM / TR / Tutor**\n" + "  |  ".join(teachable)
        )

    if learnsets["hm"]:
        sections.append(
            "**HM**\n" + "  |  ".join(learnsets["hm"])
        )

    if not sections:
        return ""

    return "\n".join(sections) + "\n"

# ---------------------------------------------------------------------------
# Dynamic machine-item compatibility lookup used by the /item "Teachable To"
# button. This deliberately reads the current Pokédex JSON at button-click
# time so later TM/TR/Tutor/HM list additions take effect without regenerating
# a static reverse index.
# ---------------------------------------------------------------------------

# Regional variants remain distinct in /item -> Teachable To. All other
# parenthetical forms collapse to the base species for display, while Mega
# forms are omitted entirely. This keeps the output useful without listing
# battle/gimmick/gender transformations as separate Pokémon.
_REGIONAL_FORM_LABELS = {
    "alolan": "Alolan",
    "galarian": "Galarian",
    "hisuian": "Hisuian",
    "paldean": "Paldean",
    "kantonian": "Kantonian",
    "johtonian": "Johtonian",
    "hoennian": "Hoennian",
    "sinnohan": "Sinnohan",
    "unovan": "Unovan",
    "kalosian": "Kalosian",
    "orrean": "Orrean",
    "ruskovan": "Ruskovan",
    "orrelborous": "Orrelborous",
    "islas lluvia de estrellas": "Islas Lluvia De’estrellas",
}


# Custom forms explicitly approved to remain distinct in /item -> Teachable To.
# These are checked before the generic non-regional form collapse rule.
_DISTINCT_TEACHABLE_FORMS = {
    "Alakazam (Delta Form)",
    "Azelf (Toxic Chain Form)",
    "Capsiwisp (Dessicated Form)",
    "Capsiwisp (Hydrated Form)",
    "Hypno (Delta Form)",
    "Latias (Toxic Chain Form)",
    "Latios (Toxic Chain Form)",
    "Mesprit (Toxic Chain Form)",
    "Muk (Delta Form)",
    "Noxial (Endothermic Form)",
    "Noxial (Exothermic Form)",
    "Polteageist (Delta Form)",
    "Sharpedo (Hull-Biter Form)",
    "Silvally (Improved RKS System Form)",
    "Spectrelec (Aerodactyl Form)",
    "Spectrelec (Kabutops Form)",
    "Tangrowth (Delta Form)",
    "Tapu Bulu (Corrupted Form)",
    "Tapu Fini (Corrupted Form)",
    "Tapu Koko (Corrupted Form)",
    "Tapu Lele (Corrupted Form)",
    "Trevenant (Frostmourn Form)",
    "Unown (Prime Form)",
    "Unown (Swarm Form)",
    "Uxie (Toxic Chain Form)",
}
_DISTINCT_TEACHABLE_FORMS_BY_KEY = {
    name.casefold(): name for name in _DISTINCT_TEACHABLE_FORMS
}


def _regional_key(text):
    # Make straight/curly apostrophes and accents/punctuation irrelevant for
    # matching authored region labels such as Islas Lluvia De’estrellas.
    value = str(text).casefold().replace("’", "'")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def _teachable_display_name(pokemon_name):
    """Return the compact display name used by Teachable To.

    Mega forms are omitted. Regional forms are retained as one regional entry.
    Every other form/gender/state collapses to the base Pokémon name.
    """
    name = str(pokemon_name).strip()
    if not name:
        return None

    form_parts = re.findall(r"\(([^)]*)\)", name)
    if any(re.search(r"\bmega\b", part, flags=re.I) for part in form_parts):
        return None

    distinct_name = _DISTINCT_TEACHABLE_FORMS_BY_KEY.get(name.casefold())
    if distinct_name:
        return distinct_name

    base = re.split(r"\s*\(", name, maxsplit=1)[0].strip()
    if not form_parts:
        return base

    normalised_parts = [_regional_key(part) for part in form_parts]
    for region_key, display in _REGIONAL_FORM_LABELS.items():
        key = _regional_key(region_key)
        if any(re.search(rf"(?:^| )\b{re.escape(key)}\b(?: |$)", part) for part in normalised_parts):
            return f"{base} ({display} Form)"

    return base



def _load_current_pokedex_record(pokemon_name):
    """Load the current authored Pokédex record for a displayed Pokémon name."""
    folder = Path("pokerole_data") / "v3.0" / "Pokedex"
    direct = folder / f"{pokemon_name}.json"
    if direct.is_file():
        try:
            return json.loads(direct.read_text(encoding="utf-8"))
        except Exception:
            pass
    for path in folder.glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if str(record.get("Name", "")).casefold() == str(pokemon_name).casefold():
            return record
    return None


_EXPLICIT_MACHINE_KEY_ALIASES = {
    "tm": {"tm", "tms", "tmmoves", "tmlist", "technicalmachines"},
    "tr": {"tr", "trs", "trmoves", "trlist", "technicalrecords"},
    "tutor": {"tutor", "tutors", "tutormoves", "tutorlist", "movetutor", "movetutors"},
    "hm": {"hm", "hms", "hmmoves", "hmlist", "hiddenmachines"},
}


def _normalise_field_key(text):
    return re.sub(r"[^a-z0-9]", "", str(text).casefold())


def _move_ids_from_explicit_value(value):
    """Extract move ids from common list/string/dict shapes."""
    result = set()

    if value is None:
        return result

    if isinstance(value, str):
        # Support comma, pipe, semicolon and newline separated authored lists.
        parts = re.split(r"\s*(?:\||,|;|\n)\s*", value)
        for part in parts:
            if part.strip():
                result.add(_to_id(part))
        return result

    if isinstance(value, (list, tuple, set)):
        for entry in value:
            result.update(_move_ids_from_explicit_value(entry))
        return result

    if isinstance(value, dict):
        # Common move-entry shape: {"Name": "Move"}.
        for key in ("Name", "Move", "name", "move"):
            if key in value and isinstance(value[key], str):
                result.add(_to_id(value[key]))
                return result
        # Otherwise accept values from a nested authored list container.
        for nested in value.values():
            result.update(_move_ids_from_explicit_value(nested))
        return result

    return result


def _authoritative_machine_pool_ids(record, method):
    """Read the exact curated machine pools authored on a Pokédex record.

    Records with AuthoritativeMachinePools=true use TMTRTutor as one combined
    TM/TR/Tutor compatibility pool and HM as an exact, separate HM pool. This
    bypasses Showdown/canonical merging so curated campaign learnsets remain
    the source of truth.
    """
    if not isinstance(record, dict) or not record.get("AuthoritativeMachinePools"):
        return None

    method = str(method).casefold()
    if method in {"tm", "tr", "tutor"}:
        return _move_ids_from_explicit_value(record.get("TMTRTutor", []))
    if method == "hm":
        # Exact authored HM list only. Do not auto-add rank-up HMs in
        # authoritative mode; the document's HM pool is the source of truth.
        return _move_ids_from_explicit_value(record.get("HM", []))
    return set()


def _explicit_machine_move_ids(record, method):
    """Read future authored TM/TR/Tutor/HM lists from a Pokédex record.

    This accepts several sensible field spellings (e.g. TM, TMs, TM Moves,
    TMList) and also recognises move entries whose Learned value is TM/TR/etc.
    """
    method = str(method).casefold()
    aliases = _EXPLICIT_MACHINE_KEY_ALIASES.get(method, {method})
    result = set()

    # Direct top-level lists and common nested list containers.
    for key, value in record.items():
        normal = _normalise_field_key(key)
        if normal in aliases:
            result.update(_move_ids_from_explicit_value(value))
        elif normal in {"machinemoves", "machinemove", "movelists", "movelearnsets", "machinelearnsets"} and isinstance(value, dict):
            for nested_key, nested_value in value.items():
                if _normalise_field_key(nested_key) in aliases:
                    result.update(_move_ids_from_explicit_value(nested_value))

    # Also support normal move entries tagged with an acquisition method.
    moves = record.get("Moves", [])
    if isinstance(moves, list):
        for entry in moves:
            if not isinstance(entry, dict):
                continue
            learned = _normalise_field_key(entry.get("Learned", ""))
            name = entry.get("Name") or entry.get("Move")
            if learned in aliases and name:
                result.add(_to_id(name))

            # Legends HMs work as an additional field-use permission. If a
            # Pokémon already learns one of the full Legends HM move set in its
            # ordinary rank learnpool, include that move in its HM pool too.
            if method == "hm" and name:
                move_id = _to_id(name)
                if move_id in ALL_HM_MOVE_IDS:
                    result.add(move_id)

    return result


def _official_can_learn_machine_move(species_id, move_id, method, data):
    """Fast one-move equivalent of get_machine_moves for reverse lookup."""
    move_sources = data.get(species_id, {})
    if not move_sources:
        return False

    method = str(method).casefold()
    source_map = move_sources.get(move_id, {})

    if method == "tm":
        machine_gens = [
            gen
            for sources in move_sources.values()
            for gen in sources.get("M", [])
        ]
        if not machine_gens:
            return False
        latest_machine_gen = max(machine_gens)
        if latest_machine_gen not in source_map.get("M", []):
            return False
        if latest_machine_gen == 8 and move_id in GEN8_TR_MOVES:
            return False
        return True

    if method == "tr":
        return move_id in GEN8_TR_MOVES and 8 in source_map.get("M", [])

    if method == "tutor":
        if move_id in MANUAL_TUTOR_ADDITIONS.get(species_id, set()):
            return True
        tutor_gens = [
            gen
            for sources in move_sources.values()
            for gen in sources.get("T", [])
        ]
        return bool(tutor_gens and max(tutor_gens) in source_map.get("T", []))

    if method == "hm":
        last_hm_gen = LEGACY_HM_LAST_GEN.get(move_id)
        return bool(last_hm_gen and last_hm_gen in source_map.get("M", []))

    return False


def get_teachable_pokemon(move_name, method):
    """Return current Pokédex names compatible with a machine item.

    The lookup is intentionally dynamic: every click rereads current Pokédex
    records and merges explicit authored lists with official compatibility.

    Legends Rules Expansion TM/TR items use the combined TM / TR / Tutor pool
    shown on a Pokémon's statblock. This makes the matching TM and TR versions
    of one expansion move teachable to the same Pokémon.
    """
    target_id = _to_id(move_name)
    method = str(method).casefold()
    data = _get_data()
    learners = []

    pokedex_dir = Path("pokerole_data") / "v3.0" / "Pokedex"
    if not pokedex_dir.is_dir():
        return learners

    expansion_machine = (
        method in {"tm", "tr"}
        and target_id in LEGENDS_EXPANSION_MACHINE_MOVE_IDS
    )

    machine_labels = {
        alias
        for aliases in _EXPLICIT_MACHINE_KEY_ALIASES.values()
        for alias in aliases
    }

    for path in pokedex_dir.glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        pokemon_name = record.get("Name")
        if not pokemon_name:
            continue

        if _machine_move_is_denied(pokemon_name, target_id):
            continue

        if expansion_machine:
            # Curated campaign records already define one authoritative
            # TM/TR/Tutor pool. TM and TR item variants both use that pool.
            authoritative = _authoritative_machine_pool_ids(record, "tm")
            if authoritative is not None:
                compatible_ids = set(authoritative)

                # Match statblock behavior: natural Rank Up moves are not
                # repeated in the teachable pool, while HMs stay separate.
                rank_up_ids = set()
                for entry in record.get("Moves", []):
                    if not isinstance(entry, dict):
                        continue
                    name = entry.get("Name") or entry.get("Move")
                    if name:
                        rank_up_ids.add(_to_id(name))

                compatible_ids.difference_update(rank_up_ids)
                compatible_ids.difference_update(ALL_HM_MOVE_IDS)

                if target_id in compatible_ids:
                    learners.append(str(pokemon_name))
                continue

            # Uncurated Pokémon use the same combined pool that their statblock
            # displays: any current TM, TR, or Tutor compatibility qualifies.
            compatible = any(
                target_id in _explicit_machine_move_ids(record, source)
                for source in ("tm", "tr", "tutor")
            )

            if not compatible:
                species_id = _resolve_species_id(pokemon_name, data)
                if species_id:
                    compatible = any(
                        _official_can_learn_machine_move(
                            species_id, target_id, source, data
                        )
                        for source in ("tm", "tr", "tutor")
                    )

            if compatible:
                # Apply the same no-rank-up-duplication rule used by
                # get_machine_moves for TM/TR/Tutor pools.
                rank_up_ids = set()
                for entry in record.get("Moves", []):
                    if not isinstance(entry, dict):
                        continue
                    learned = _normalise_field_key(entry.get("Learned", ""))
                    name = entry.get("Name") or entry.get("Move")
                    if name and learned not in machine_labels:
                        rank_up_ids.add(_to_id(name))

                if (
                    target_id not in rank_up_ids
                    and target_id not in ALL_HM_MOVE_IDS
                ):
                    learners.append(str(pokemon_name))
            continue

        authoritative = _authoritative_machine_pool_ids(record, method)
        if authoritative is not None:
            if target_id in authoritative:
                # Curated TM/TR/Tutor pools are one combined compatibility
                # pool, while HM remains exact and separate.
                learners.append(str(pokemon_name))
            continue

        explicit = _explicit_machine_move_ids(record, method)
        if target_id in explicit:
            learners.append(str(pokemon_name))
            continue

        species_id = _resolve_species_id(pokemon_name, data)
        if species_id and _official_can_learn_machine_move(
            species_id, target_id, method, data
        ):
            learners.append(str(pokemon_name))

    display_learners = []
    for learner in learners:
        display = _teachable_display_name(learner)
        if display:
            display_learners.append(display)

    return sorted(dict.fromkeys(display_learners), key=str.casefold)


def get_move_type(move_name):
    """Return the authored type of a move, or an empty string if unavailable."""
    target = _to_id(move_name)
    folder = Path("pokerole_data") / "v3.0" / "Moves"
    if not folder.is_dir():
        return ""

    for path in folder.glob("*.json"):
        try:
            info = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if _to_id(info.get("Name", "")) == target:
            return str(info.get("Type", ""))
    return ""
