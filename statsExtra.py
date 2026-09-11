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
    """Render decimal feet as conventional feet/inches, e.g. 4.52 -> 4'06"."""
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
    return f"{feet}'{inches}\""

def _size_weight(meta):
    height = meta.get("Height") or {}
    weight = meta.get("Weight") or {}

    feet = _feet_inches_text(height.get("Feet")) if isinstance(height, dict) else None
    pounds = _number_text(weight.get("Pounds")) if isinstance(weight, dict) else None

    return (
        feet if feet is not None else "Unknown",
        f"{pounds} lb" if pounds is not None else "Unknown"
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


def _progression_method(evo):
    authored = str(evo.get("DisplayMethod") or "").strip()
    if authored:
        return authored.rstrip(".") + "."

    kind = str(evo.get("Kind") or "")
    if kind == "Level":
        speed = str(evo.get("Speed") or "").strip()
        text = f"{speed} Evolution" if speed else "Level Evolution"
        if evo.get("Gender"):
            text = f"{evo['Gender']} only. {text}"
        if evo.get("Move"):
            text += f" while knowing {evo['Move']}"
        if evo.get("Item"):
            text += f" while holding {evo['Item']}"
        if evo.get("Region"):
            text += f" while in {evo['Region']}"
        special = str(evo.get("Special") or "").strip()
        if special and special.casefold() not in text.casefold():
            text += f"; {special}"
        return text.rstrip(".") + "."
    if kind == "Stone":
        return f"Use {evo.get('Item') or evo.get('Stone') or 'Evolution Stone'}."
    if kind == "Item":
        return f"Use {evo.get('Item') or 'required item'}."
    if kind == "Trade":
        return f"Trade or Use {evo['Item']}." if evo.get("Item") == "Link Stone" else (
            f"Trade with {evo['Item']}." if evo.get("Item") else "Trade."
        )
    if kind == "Stat":
        stat = evo.get("Stat") or "Stat"
        value = evo.get("Value")
        return f"{stat} {value}." if value not in (None, "", -1) else f"{stat} requirement."
    if kind == "Mega":
        if evo.get("Item"):
            return f"Mega Evolution using {evo['Item']}."
        if evo.get("Special"):
            return str(evo['Special']).rstrip(".") + "."
        return "Mega Evolution."
    if kind in {"Form", "Transform"}:
        if evo.get("Item"):
            return f"Use {evo['Item']}."
        if evo.get("Ability"):
            return f"Activate {evo['Ability']}."
        if evo.get("Move"):
            return f"Use {evo['Move']}."
        if evo.get("Special"):
            return str(evo['Special']).rstrip(".") + "."
        return "Transform."
    if evo.get("Special"):
        return str(evo["Special"]).rstrip(".") + "."
    return "Special requirement."


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
        if kind == "Mega": prefix = "mega"
        elif kind in transform_kinds: prefix = "transform"
        else: prefix = "normal"
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
            if method not in by_name[name]:
                by_name[name].append(method)
        result=[]
        for name in ordered:
            methods=by_name[name]
            method = " OR ".join(m.rstrip(".") for m in methods) + "." if methods else ""
            result.append((name,method))
        return result

    for key in groups:
        groups[key] = collapse(groups[key])

    def format_group(label, rows):
        if not rows:
            return ""
        entries = []
        for name, method in rows:
            clean_method = str(method or "").strip().rstrip(".")
            entries.append(f"{name}, {clean_method}" if clean_method else name)
        return f"**{label}**: " + "; ".join(entries) + "\n"

    output = ""
    output += format_group("Evolves Into", groups["normal_to"])
    output += format_group("Evolves From", groups["normal_from"])
    output += format_group("Mega Evolves Into", groups["mega_to"])
    output += format_group("Mega Evolves From", groups["mega_from"])
    output += format_group("Transforms Into", groups["transform_to"])
    output += format_group("Transforms From", groups["transform_from"])
    return output
