import json
import os
import re

_pokemon_meta_cache = {}

STANDARD_ATTACK_TYPES = [
    "Normal", "Fire", "Water", "Grass", "Electric", "Ice", "Fighting",
    "Poison", "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost",
    "Dark", "Dragon", "Steel", "Fairy"
]

TYPE_SUPER = {
    "Normal": set(),
    "Fire": {"Grass", "Ice", "Bug", "Steel"},
    "Water": {"Fire", "Ground", "Rock"},
    "Grass": {"Water", "Ground", "Rock"},
    "Electric": {"Water", "Flying"},
    "Ice": {"Grass", "Ground", "Flying", "Dragon"},
    "Fighting": {"Normal", "Ice", "Rock", "Dark", "Steel"},
    "Poison": {"Grass", "Fairy"},
    "Ground": {"Fire", "Electric", "Poison", "Rock", "Steel"},
    "Flying": {"Grass", "Fighting", "Bug"},
    "Psychic": {"Fighting", "Poison"},
    "Bug": {"Grass", "Psychic", "Dark"},
    "Rock": {"Fire", "Ice", "Flying", "Bug"},
    "Ghost": {"Psychic", "Ghost"},
    "Dark": {"Psychic", "Ghost"},
    "Dragon": {"Dragon"},
    "Steel": {"Ice", "Rock", "Fairy"},
    "Fairy": {"Fighting", "Dragon", "Dark"},
}

TYPE_RESISTED = {
    "Normal": {"Rock", "Steel"},
    "Fire": {"Fire", "Water", "Rock", "Dragon"},
    "Water": {"Water", "Grass", "Dragon"},
    "Grass": {"Fire", "Grass", "Poison", "Flying", "Bug", "Dragon", "Steel"},
    "Electric": {"Electric", "Grass", "Dragon"},
    "Ice": {"Fire", "Water", "Ice", "Steel"},
    "Fighting": {"Poison", "Flying", "Psychic", "Bug", "Fairy"},
    "Poison": {"Poison", "Ground", "Rock", "Ghost"},
    "Ground": {"Grass", "Bug"},
    "Flying": {"Electric", "Rock", "Steel"},
    "Psychic": {"Psychic", "Steel"},
    "Bug": {"Fire", "Fighting", "Poison", "Flying", "Ghost", "Steel", "Fairy"},
    "Rock": {"Fighting", "Ground", "Steel"},
    "Ghost": {"Dark"},
    "Dark": {"Fighting", "Dark", "Fairy"},
    "Dragon": {"Steel"},
    "Steel": {"Fire", "Water", "Electric", "Steel"},
    "Fairy": {"Fire", "Poison", "Steel"},
}

TYPE_IMMUNE = {
    "Normal": {"Ghost"},
    "Fire": set(),
    "Water": set(),
    "Grass": set(),
    "Electric": {"Ground"},
    "Ice": set(),
    "Fighting": {"Ghost"},
    "Poison": {"Steel"},
    "Ground": {"Flying"},
    "Flying": set(),
    "Psychic": {"Dark"},
    "Bug": set(),
    "Rock": set(),
    "Ghost": {"Normal"},
    "Dark": set(),
    "Dragon": {"Fairy"},
    "Steel": set(),
    "Fairy": set(),
}


def _load_pokemon_meta(version):
    if version in _pokemon_meta_cache:
        return _pokemon_meta_cache[version]

    result = {}
    folder = os.path.join("pokerole_data", version, "Pokedex")

    try:
        filenames = os.listdir(folder)
    except OSError:
        _pokemon_meta_cache[version] = result
        return result

    for filename in filenames:
        if not filename.lower().endswith(".json"):
            continue

        path = os.path.join(folder, filename)
        try:
            with open(path, "r", encoding="utf-8") as f:
                info = json.load(f)
            name = info.get("Name")
            if name:
                result[name.casefold()] = info
        except Exception:
            # One malformed/custom entry should not break /stats globally.
            continue

    _pokemon_meta_cache[version] = result
    return result


def _number_text(value):
    if value is None or value == "":
        return None
    try:
        return f"{float(value):g}"
    except (TypeError, ValueError):
        return str(value)




def _feet_inches_text(value):
    """Render decimal feet as conventional feet/inches with padded inches, e.g. 4.67 -> 4'08"."""
    if value is None or value == "":
        return None
    try:
        decimal_feet = float(value)
    except (TypeError, ValueError):
        return str(value)

    feet = int(decimal_feet)
    inches = int(round((decimal_feet - feet) * 12))
    if inches >= 12:
        feet += inches // 12
        inches %= 12
    return f"{feet}'{inches:02d}\""


def _metric_height_text(value):
    """Render height in metres, or centimetres for sub-metre Pokémon."""
    if value is None or value == "":
        return None
    try:
        meters = float(value)
    except (TypeError, ValueError):
        return str(value)

    if 0 < meters < 1:
        centimeters = meters * 100
        return f"{_number_text(centimeters)} cm"
    return f"{_number_text(meters)} m"


def _size_weight(meta):
    height = meta.get("Height") or {}
    weight = meta.get("Weight") or {}

    meters = _metric_height_text(height.get("Meters")) if isinstance(height, dict) else None
    feet = _feet_inches_text(height.get("Feet")) if isinstance(height, dict) else None
    kilograms = _number_text(weight.get("Kilograms")) if isinstance(weight, dict) else None
    pounds = _number_text(weight.get("Pounds")) if isinstance(weight, dict) else None

    size_parts = [part for part in (meters, feet) if part is not None]
    weight_parts = []
    if kilograms is not None:
        weight_parts.append(f"{kilograms} kg")
    if pounds is not None:
        weight_parts.append(f"{pounds} lb")

    return (
        " / ".join(size_parts) if size_parts else "Unknown",
        " / ".join(weight_parts) if weight_parts else "Unknown"
    )


def _type_matchups(type1, type2=""):
    defenders = [
        str(ptype).capitalize()
        for ptype in (type1, type2)
        if ptype
    ]

    weaknesses = []
    resistances = []
    immunities = []

    for attack_type in STANDARD_ATTACK_TYPES:
        # Immunity overrides any weakness/resistance contributed by the other type.
        if any(defender in TYPE_IMMUNE[attack_type] for defender in defenders):
            immunities.append(attack_type)
            continue

        level = 0
        for defender in defenders:
            if defender in TYPE_SUPER[attack_type]:
                level += 1
            elif defender in TYPE_RESISTED[attack_type]:
                level -= 1

        if level > 0:
            weaknesses.append((level, attack_type))
        elif level < 0:
            resistances.append((-level, attack_type))

    weaknesses.sort(key=lambda item: (-item[0], STANDARD_ATTACK_TYPES.index(item[1])))
    resistances.sort(key=lambda item: (-item[0], STANDARD_ATTACK_TYPES.index(item[1])))

    def format_levels(entries):
        if not entries:
            return "None"

        grouped = {}
        for level, attack_type in entries:
            grouped.setdefault(level, []).append(attack_type)

        return " ".join(
            f"{level}x " + " ".join(grouped[level])
            for level in sorted(grouped, reverse=True)
        )

    return (
        format_levels(weaknesses),
        format_levels(resistances),
        " ".join(immunities) if immunities else "None"
    )


def pokemon_extra_stats_text(pokemon, type1, type2, version):
    meta = _load_pokemon_meta(version).get(str(pokemon).casefold(), {})

    species = meta.get("DexCategory") or "Unknown"
    size, weight = _size_weight(meta)
    weaknesses, resistances, immunities = _type_matchups(type1, type2)
    mega_stone = meta.get("MegaStone")

    output = (
        f"**Size**: {size}\n"
        f"**Weight**: {weight}\n"
        f"**Species**: {species}\n"
        f"**Weaknesses**: {weaknesses}\n"
        f"**Resistances**: {resistances}\n"
        f"**Immunities**: {immunities}\n"
    )
    if mega_stone:
        output += f"**Mega Stone**: {mega_stone}\n"
    return output


def _is_progression_form(meta):
    """True for stat blocks reached through Mega Evolution or a reversible transformation."""
    for evo in meta.get("Evolutions", []) or []:
        if not isinstance(evo, dict):
            continue
        if evo.get("From") and str(evo.get("Kind") or "") in {"Mega", "Form", "Transform"}:
            return True
    return False


def pokemon_other_forms(pokemon, version):
    """Return static sibling forms that share this Pokémon's Pokédex number.

    Mega/form-transformation targets are intentionally excluded because they are
    displayed by the progression section instead.
    """
    all_meta = _load_pokemon_meta(version)
    meta = all_meta.get(str(pokemon).casefold(), {})
    if not meta or _is_progression_form(meta):
        return []

    number = meta.get("Number")
    if number in (None, ""):
        return []

    current_name = str(meta.get("Name") or pokemon)
    forms = []
    for candidate in all_meta.values():
        name = str(candidate.get("Name") or "")
        if not name or name.casefold() == current_name.casefold():
            continue
        if candidate.get("Number") != number:
            continue
        if _is_progression_form(candidate):
            continue
        forms.append(name)

    return sorted(dict.fromkeys(forms), key=str.casefold)


def pokemon_other_forms_text(pokemon, version):
    forms = pokemon_other_forms(pokemon, version)
    if not forms:
        return ""
    return f"**Other Forms**: {', '.join(forms)}\n"


def pokemon_pokedex_text(pokemon, version):
    meta = _load_pokemon_meta(version).get(str(pokemon).casefold(), {})
    description = str(meta.get("DexDescription") or "").strip()
    if not description:
        return ""
    description = re.sub(r"\s+", " ", description)
    return f"**Pokedex**: {description}\n"



def pokemon_additional_hidden_abilities(pokemon, version):
    meta = _load_pokemon_meta(version).get(str(pokemon).casefold(), {})
    values = meta.get("AdditionalHiddenAbilities", [])
    if isinstance(values, str):
        values = [x.strip() for x in values.split(";") if x.strip()]
    return list(values or [])


def _clean_progression_phrase(text):
    """Turn authored evolution wording into compact /stats display wording."""
    text = str(text or "").strip().rstrip(".")
    if not text:
        return ""

    # Keep the author's actual requirements, but shorten the repetitive
    # "Evolution" wording used in the data files.
    replacements = [
        (r"\bFast level Evolution\b", "Fast Speed"),
        (r"\bMedium level Evolution\b", "Medium Speed"),
        (r"\bSlow level Evolution\b", "Slow Speed"),
        (r"\bFast level evolution\b", "Fast Speed"),
        (r"\bMedium level evolution\b", "Medium Speed"),
        (r"\bSlow level evolution\b", "Slow Speed"),
        (r"\bFast Evolution\b", "Fast Speed"),
        (r"\bMedium Evolution\b", "Medium Speed"),
        (r"\bSlow Evolution\b", "Slow Speed"),
        (r"\bFast evolution\b", "Fast Speed"),
        (r"\bMedium evolution\b", "Medium Speed"),
        (r"\bSlow evolution\b", "Slow Speed"),
        (r"\bUse ([^;]+?)\b", r"via \1"),
    ]
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    text = re.sub(r"\s+OR\s+", " or ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*;\s*", ", ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\bwhile Holding\b", "while holding", text)
    text = re.sub(r"\bor Complete\b", "or complete", text)
    text = re.sub(r"\band Play\b", "and play", text)
    text = re.sub(r"\bor Medium\b", "or Medium", text)

    # After "or", make repeated "via" wording read naturally.
    text = re.sub(r"\bor via\b", "or via", text, flags=re.IGNORECASE)
    return text


def _progression_method(evo):
    kind = str(evo.get("Kind") or "").strip()

    if kind == "Level":
        # Special-authored level methods carry conditions that cannot always
        # be reconstructed from the structured fields alone.
        authored = str(evo.get("DisplayMethod") or evo.get("Special") or "").strip()
        if authored:
            return _clean_progression_phrase(authored)

        speed = str(evo.get("Speed") or "").strip()
        text = f"{speed} Speed" if speed else "Level Evolution"
        conditions = []
        if evo.get("Gender"):
            conditions.append(f"{evo['Gender']} only")
        if evo.get("Move"):
            conditions.append(f"while knowing {evo['Move']}")
        if evo.get("Item"):
            conditions.append(f"while holding {evo['Item']}")
        if evo.get("Region"):
            conditions.append(f"while in {evo['Region']}")
        if conditions:
            if conditions[0].endswith("only"):
                text = f"{conditions[0]}, {text}"
                conditions = conditions[1:]
            if conditions:
                text += " " + " ".join(conditions)
        return text

    if kind == "Stone":
        authored = str(evo.get("DisplayMethod") or "").strip()
        # Preserve explicitly-authored alternate methods.
        if " OR " in authored.upper():
            return _clean_progression_phrase(authored)
        item = evo.get("Item") or evo.get("Stone") or "Evolution Stone"
        text = f"via {item}"
        if evo.get("Region"):
            text += f" in {evo['Region']}"
        if evo.get("Gender"):
            text = f"{evo['Gender']} only, {text}"
        return text

    if kind == "Item":
        authored = str(evo.get("DisplayMethod") or "").strip()
        if " OR " in authored.upper():
            return _clean_progression_phrase(authored)
        item = evo.get("Item") or "required item"
        return f"via {item}"

    if kind == "Trade":
        item = evo.get("Item")
        if item == "Link Stone":
            return "via Trade or Link Stone"
        if item:
            return f"via Trade while holding {item}"
        return "via Trade"

    if kind == "Stat":
        stat = evo.get("Stat") or "Stat"
        value = evo.get("Value")
        return f"via {stat} {value}" if value not in (None, "", -1) else f"via {stat} requirement"

    if kind == "Mega":
        if evo.get("Item"):
            return f"using {evo['Item']}"
        special = str(evo.get("Special") or evo.get("DisplayMethod") or "").strip()
        if special:
            cleaned = _clean_progression_phrase(special)
            cleaned = re.sub(r"^Mega Evolution\s+", "", cleaned, flags=re.IGNORECASE)
            return cleaned
        return ""

    if kind in {"Form", "Transform"}:
        if evo.get("Item"):
            return f"using {evo['Item']}"
        if evo.get("Ability") and str(evo.get("Ability")).casefold() != "ability":
            return f"by activating {evo['Ability']}"
        if evo.get("Move"):
            return f"using {evo['Move']}"
        special = str(evo.get("Special") or evo.get("DisplayMethod") or "").strip()
        if special:
            return _clean_progression_phrase(special)
        return ""

    special = str(evo.get("Special") or evo.get("DisplayMethod") or "").strip()
    if special:
        return _clean_progression_phrase(special)
    return ""


def _pretty_mega_name(name):
    """Render internal '(Mega ... Form)' stat-block names naturally."""
    name = str(name or "").strip()

    # Standard: Charizard (Mega X Form) -> Mega Charizard X
    match = re.fullmatch(r"(.+?) \(Mega(?: ([^)]+?))? Form\)", name)
    if match:
        base = match.group(1)
        qualifier = (match.group(2) or "").strip()
        return f"Mega {base}" + (f" {qualifier}" if qualifier else "")

    # Tatsugiri uses '(Curly Mega Form)' rather than '(Mega Curly Form)'.
    match = re.fullmatch(r"(.+?) \((.+?) Mega Form\)", name)
    if match:
        return f"Mega {match.group(1)} {match.group(2)}"

    return name


def pokemon_progression_text(pokemon, version):
    meta = _load_pokemon_meta(version).get(str(pokemon).casefold(), {})
    evolutions = meta.get("Evolutions", []) or []

    groups = {
        "normal_to": [], "normal_from": [],
        "mega_to": [], "mega_from": [],
        "transform_to": [], "transform_from": [],
    }
    transform_kinds = {"Form", "Transform"}

    for evo in evolutions:
        kind = str(evo.get("Kind") or "")
        if kind == "Mega":
            prefix = "mega"
        elif kind in transform_kinds:
            prefix = "transform"
        else:
            prefix = "normal"

        if evo.get("To"):
            groups[f"{prefix}_to"].append((evo["To"], _progression_method(evo)))
        if evo.get("From"):
            groups[f"{prefix}_from"].append((evo["From"], _progression_method(evo)))

    def collapse(rows):
        ordered = []
        by_name = {}
        for name, method in rows:
            if name not in by_name:
                by_name[name] = []
                ordered.append(name)
            clean = str(method or "").strip().rstrip(".")
            if clean and clean not in by_name[name]:
                by_name[name].append(clean)

        result = []
        for name in ordered:
            methods = by_name[name]
            method = " or ".join(methods)
            result.append((name, method))
        return result

    for key in groups:
        groups[key] = collapse(groups[key])

    def format_group(label, rows, mega=False):
        if not rows:
            return ""

        entries = []
        for name, method in rows:
            display_name = _pretty_mega_name(name) if mega else str(name)
            if method:
                entries.append(f"{display_name}, {method}.")
            else:
                entries.append(f"{display_name}.")
        return f"**{label}**: " + " ".join(entries) + "\n"

    output = ""
    output += format_group("Evolves Into", groups["normal_to"])
    output += format_group("Evolves From", groups["normal_from"])
    output += format_group("Mega Evolves Into", groups["mega_to"], mega=True)
    output += format_group("Mega Evolves From", groups["mega_from"], mega=True)
    output += format_group("Transforms Into", groups["transform_to"])
    output += format_group("Transforms From", groups["transform_from"])
    return output
