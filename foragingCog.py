import json
import random
import re
import unicodedata
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from luck_utils import apply_luck_modifier, format_luck_check
from maneuverCog import maneuver_text, send_chunks
from vehicleCog import vehicle_module_blocks


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "foraging_data.json"
with DATA_FILE.open("r", encoding="utf-8") as f:
    FORAGING_DATA = json.load(f)

FORAGING_TABLES = FORAGING_DATA["locations"]
SUBTABLES = FORAGING_DATA["subtables"]
SUBTABLE_ALIASES = FORAGING_DATA.get("subtable_aliases", {})
VERY_RARE_CATEGORIES = FORAGING_DATA.get(
    "very_rare_categories", ["Mega Stone", "Z-Crystal", "Terasta Shard", "Crest"]
)

LOCATION_CHOICES = [
    app_commands.Choice(name=name, value=name)
    for name in [
        "Wooded Trail",
        "Desert",
        "Mountain",
        "Urbanized",
        "Tundra",
        "Jungle",
        "Cave",
        "Shoreline",
        "Space",
    ]
]

# Foraging-result labels that intentionally differ from the canonical lookup name.
# These mappings only affect the result-detail button; they do not add aliases or
# new records to any existing item/equipment command.
ITEM_LOOKUP_OVERRIDES = {
    "regular ingredients": "Regular Ingredient",
    "gourmet ingredients": "Gourmet Ingredient",
    "musical instrument": "Musical Instruments [Various]",
}
WEAPON_LOOKUP_OVERRIDES = {
    "stave": "Nunchaku and Staves",
    "short bow": "Bows and Crossbows",
    "hand axe": "Axes",
}
SHOP_LOOKUP_OVERRIDES = {
    "ammunition": "Solid Ammunition Pack",
}


QUANTITY_RANGE_RE = re.compile(r"^(\d+)-(\d+)x\s+(.+)$", re.I)
QUANTITY_FIXED_RE = re.compile(r"^(\d+)x\s+(.+)$", re.I)
QUANTITY_PREFIX_RE = re.compile(r"^x(\d+)\s+(.+)$", re.I)
LUCK_RESULT_RE = re.compile(r"^(\d+)\+\s*Luck Check:\s*\[SUBTABLE\]\s*(.+)$", re.I)
SCRAP_RE = re.compile(
    r"^Scrap\s*\(Worth between ₽([\d,]+)-₽([\d,]+) at random\)$", re.I
)


def normalize(text: str) -> str:
    text = (text or "").replace("’", "'").replace("‘", "'").replace("–", "-").replace("—", "-")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return re.sub(r"\s+", " ", text)


def table_label(level: int) -> str:
    return "Six+ successes" if level == 6 else f"{level} success" + ("" if level == 1 else "es")


def tables_for_successes(successes: int):
    # Preserve the original /roll_foraging cadence exactly.
    return [] if successes <= 0 else list(range(min(successes, 6), 0, -2))


def calculate_rare_luck_check(luck_modifier, d100_roll=None):
    """Return the natural D100 and capped total for a valid Luck Modifier."""
    if luck_modifier < 0 or luck_modifier > 100 or luck_modifier % 5:
        raise ValueError("Luck Modifier must be a multiple of 5 from 0 to 100.")
    base = random.randint(1, 100) if d100_roll is None else int(d100_roll)
    return base, apply_luck_modifier(base, luck_modifier)


def canonical_subtable_name(name: str) -> str:
    name = (name or "").strip()
    return SUBTABLE_ALIASES.get(name, name)


def parse_subtable_reference(text: str):
    """Return (subtable name, roll_count, result_multiplier) or None."""
    text = (text or "").strip()
    if not text.lower().startswith("[subtable]"):
        return None
    body = text[len("[SUBTABLE]"):].strip()
    roll_count = 1
    result_multiplier = 1

    if re.search(r"\(roll twice\)\s*$", body, flags=re.I):
        body = re.sub(r"\s*\(roll twice\)\s*$", "", body, flags=re.I).strip()
        roll_count = 2

    mult_match = re.search(r"\(result x(\d+)\)\s*$", body, flags=re.I)
    if mult_match:
        result_multiplier = int(mult_match.group(1))
        body = re.sub(r"\s*\(result x\d+\)\s*$", "", body, flags=re.I).strip()

    return body, roll_count, result_multiplier


def parse_quantity(text: str):
    """Resolve quantity prefixes. Returns (quantity, underlying authored name)."""
    text = (text or "").strip()
    match = QUANTITY_RANGE_RE.match(text)
    if match:
        low, high, name = int(match.group(1)), int(match.group(2)), match.group(3).strip()
        return random.randint(low, high), name
    match = QUANTITY_FIXED_RE.match(text)
    if match:
        return int(match.group(1)), match.group(2).strip()
    match = QUANTITY_PREFIX_RE.match(text)
    if match:
        return int(match.group(1)), match.group(2).strip()
    return 1, text


def make_find(base_name: str, quantity: int = 1, source=None, scrap_value=None):
    if scrap_value is not None:
        display = f"Scrap — Worth ₽{scrap_value:,}"
    elif quantity > 1:
        display = f"{quantity}x {base_name}"
    else:
        display = base_name
    return {
        "name": base_name,
        "quantity": quantity,
        "display": display,
        "source": list(source or []),
        "scrap_value": scrap_value,
    }


def resolve_leaf(text: str, multiplier: int = 1, source=None):
    text = (text or "").strip()
    scrap_match = SCRAP_RE.match(text)
    if scrap_match:
        low = int(scrap_match.group(1).replace(",", ""))
        high = int(scrap_match.group(2).replace(",", ""))
        value = random.randint(low, high)
        return [make_find("Scrap", 1, source=source, scrap_value=value)]

    quantity, base_name = parse_quantity(text)
    quantity *= max(1, int(multiplier))
    return [make_find(base_name, quantity, source=source)]


def resolve_subtable(name: str, multiplier: int = 1, depth: int = 0):
    """Roll one supplied subtable recursively and return resolved finds."""
    if depth > 12:
        raise RuntimeError("Foraging subtable recursion exceeded safe depth.")

    name = canonical_subtable_name(name)

    # Preserve the old 'very rare Item' mechanic exactly: choose one of the four
    # rare categories equally, then choose uniformly inside that category.
    if name == "Very Rare Item":
        category = random.choice(VERY_RARE_CATEGORIES)
        finds = resolve_subtable(category, multiplier=multiplier, depth=depth + 1)
        for find in finds:
            find["source"].insert(0, f"Very Rare Item → {category}")
        return finds

    entries = SUBTABLES.get(name)
    if not entries:
        raise KeyError(f'Foraging subtable "{name}" was not found.')

    roll = random.randint(1, len(entries))
    chosen = entries[roll - 1]
    source = [f"{name} d{len(entries)}: {roll}"]

    nested = parse_subtable_reference(chosen)
    if nested:
        nested_name, roll_count, nested_multiplier = nested
        results = []
        for _ in range(roll_count):
            rolled = resolve_subtable(
                nested_name,
                multiplier=multiplier * nested_multiplier,
                depth=depth + 1,
            )
            for find in rolled:
                find["source"] = source + find["source"]
            results.extend(rolled)
        return results

    return resolve_leaf(chosen, multiplier=multiplier, source=source)


def resolve_result(raw: str):
    """Resolve a normal foraging result. Luck Check results are handled separately."""
    nested = parse_subtable_reference(raw)
    if nested:
        name, roll_count, multiplier = nested
        results = []
        for _ in range(roll_count):
            results.extend(resolve_subtable(name, multiplier=multiplier))
        return results
    return resolve_leaf(raw)


def format_find_list(finds):
    return "; ".join(find["display"] for find in finds)


class ResultDetailButton(discord.ui.Button):
    def __init__(self, cog, target, label):
        super().__init__(
            label=(f"View {label}")[:80],
            style=discord.ButtonStyle.secondary,
        )
        self.cog = cog
        self.target = target

    async def callback(self, interaction: discord.Interaction):
        await self.cog.send_detail(interaction, self.target)


class ForagingResultView(discord.ui.View):
    def __init__(self, cog, finds, owner_id=None, luck_dc=None, luck_subtable=None):
        super().__init__(timeout=300)
        self.cog = cog
        self.owner_id = owner_id
        self.luck_dc = luck_dc
        self.luck_subtable = luck_subtable

        seen = set()
        for find in finds:
            target = cog.detail_target(find["name"])
            if not target:
                continue
            key = (target["kind"], target["name"])
            if key in seen:
                continue
            seen.add(key)
            self.add_item(ResultDetailButton(cog, target, target.get("label", find["name"])))
            if len(self.children) >= 20:
                break

        if luck_dc is not None and luck_subtable:
            self.luck_select = discord.ui.Select(
                placeholder="Choose Luck Modifier to roll 1D100",
                min_values=1,
                max_values=1,
                options=[
                    discord.SelectOption(label=f"Luck Modifier {modifier}", value=str(modifier))
                    for modifier in range(0, 101, 5)
                ],
            )
            self.luck_select.callback = self.select_luck_modifier
            self.add_item(self.luck_select)

    async def select_luck_modifier(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Only the player who made this Foraging check can roll its Luck Check.",
                ephemeral=True,
            )
            return

        modifier = int(self.luck_select.values[0])
        base, total = calculate_rare_luck_check(modifier)

        self.luck_select.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

        lines = [
            "## 🍀 Rare Item Luck Check",
            f"**{format_luck_check(base, modifier)}**",
        ]
        finds = []
        if total >= self.luck_dc:
            finds = resolve_subtable(self.luck_subtable)
            lines.append(f"**SUCCESS!** — {format_find_list(finds)}")
        else:
            lines.append(f"Failed ({self.luck_dc}+ required).")

        result_view = ForagingResultView(self.cog, finds) if finds else None
        if result_view and result_view.children:
            await interaction.response.send_message("\n".join(lines), view=result_view, ephemeral=False)
        else:
            await interaction.response.send_message("\n".join(lines), ephemeral=False)


class Foraging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.item_lookup = {}
        self.weapon_lookup = {}
        self.armor_lookup = {}
        self.accessory_lookup = {}
        self.tool_lookup = {}
        self.shop_lookup = {}
        self.vehicle_module_lookup = {}
        self.apricorn_details = {}
        self._load_detail_sources()

    def _load_detail_sources(self):
        # /item source data, including homebrew item records.
        for path in (BASE_DIR / "pokerole_data").glob("**/Items/*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            name = data.get("Name")
            if name:
                self.item_lookup.setdefault(normalize(name), (name, data))

        # Weapon + maneuver-linked equipment data.
        try:
            maneuver_data = json.loads((BASE_DIR / "maneuver_data.json").read_text(encoding="utf-8"))
        except Exception:
            maneuver_data = {"weapons": []}
        for entry in maneuver_data.get("weapons", []):
            kind = entry.get("kind")
            if kind == "Armor":
                lookup = self.armor_lookup
            elif kind == "Accessory":
                lookup = self.accessory_lookup
            elif kind == "Tool":
                lookup = self.tool_lookup
            else:
                lookup = self.weapon_lookup
            for alias in [entry.get("name", "")] + entry.get("aliases", []):
                if alias:
                    lookup[normalize(alias)] = (entry["name"], entry, "maneuver")

        # Static armor/accessory/tool command data.
        for filename, lookup in [
            ("armor_data.json", self.armor_lookup),
            ("accessories_data.json", self.accessory_lookup),
            ("tools_data.json", self.tool_lookup),
        ]:
            try:
                data = json.loads((BASE_DIR / filename).read_text(encoding="utf-8"))
            except Exception:
                continue
            for name, entry in data.items():
                aliases = [name] + entry.get("Aliases", [])
                for alias in aliases:
                    lookup.setdefault(normalize(alias), (name, entry, "static"))

        # Vehicle Equipment Module reference data.
        try:
            vehicle_data = json.loads((BASE_DIR / "vehicle_data.json").read_text(encoding="utf-8"))
        except Exception:
            vehicle_data = {"modules": []}
        for module in vehicle_data.get("modules", []):
            for alias in [module.get("name", "")] + module.get("aliases", []):
                if alias:
                    self.vehicle_module_lookup[normalize(alias)] = module

        # Shop-only authored equipment/supplies that have no lookup command.
        try:
            shops = json.loads((BASE_DIR / "shop_data.json").read_text(encoding="utf-8")).get("shops", {})
        except Exception:
            shops = {}
        for shop_name, shop in shops.items():
            if not isinstance(shop, dict):
                continue
            for pool_name in ("stock", "special_pool", "random_wares"):
                for entry in shop.get(pool_name, []):
                    name = entry.get("name")
                    if name:
                        self.shop_lookup.setdefault(normalize(name), (name, entry, shop_name))

        # Apricorns are real crafting resources but intentionally do not have /item records.
        try:
            crafting = json.loads((BASE_DIR / "crafting_reference_data.json").read_text(encoding="utf-8"))
            text = crafting.get("craftingpokeballs", "")
            for color in ["Red", "Blue", "Cyan", "Pink", "Green", "White", "Gray", "Black"]:
                name = f"{color} Apricorn"
                match = re.search(
                    rf"^{re.escape(name)}:\n(.*?)(?=\n\n[A-Z][^\n]+:|\n\nHow to craft them:|$)",
                    text,
                    flags=re.M | re.S,
                )
                if match:
                    self.apricorn_details[normalize(name)] = (name, match.group(1).strip())
        except Exception:
            pass

    def detail_target(self, result_name: str):
        name = (result_name or "").strip()
        key = normalize(name)

        if key in ITEM_LOOKUP_OVERRIDES:
            canonical = ITEM_LOOKUP_OVERRIDES[key]
            item = self.item_lookup.get(normalize(canonical))
            if item:
                return {"kind": "item", "name": item[0], "data": item[1], "label": canonical}

        if key in WEAPON_LOOKUP_OVERRIDES:
            canonical = WEAPON_LOOKUP_OVERRIDES[key]
            weapon = self.weapon_lookup.get(normalize(canonical))
            if weapon:
                return {"kind": "weapon", "name": weapon[0], "data": weapon[1], "label": name}

        if key in SHOP_LOOKUP_OVERRIDES:
            canonical = SHOP_LOOKUP_OVERRIDES[key]
            shop = self.shop_lookup.get(normalize(canonical))
            if shop:
                return {"kind": "shop", "name": shop[0], "data": shop[1], "shop": shop[2], "label": name}

        item = self.item_lookup.get(key)
        if item:
            return {"kind": "item", "name": item[0], "data": item[1], "label": item[0]}

        weapon = self.weapon_lookup.get(key)
        if weapon:
            return {"kind": "weapon", "name": weapon[0], "data": weapon[1], "label": name}

        armor = self.armor_lookup.get(key)
        if armor:
            return {"kind": "armor", "name": armor[0], "data": armor[1], "record_type": armor[2], "label": name}

        accessory = self.accessory_lookup.get(key)
        if accessory:
            return {"kind": "accessory", "name": accessory[0], "data": accessory[1], "record_type": accessory[2], "label": name}

        tool = self.tool_lookup.get(key)
        if tool:
            return {"kind": "tool", "name": tool[0], "data": tool[1], "record_type": tool[2], "label": name}

        apricorn = self.apricorn_details.get(key)
        if apricorn:
            return {"kind": "apricorn", "name": apricorn[0], "data": apricorn[1], "label": apricorn[0]}

        vehicle_module = self.vehicle_module_lookup.get(key)
        if vehicle_module:
            return {
                "kind": "vehicle_module",
                "name": vehicle_module["name"],
                "data": vehicle_module,
                "label": name,
            }

        shop = self.shop_lookup.get(key)
        if shop:
            return {"kind": "shop", "name": shop[0], "data": shop[1], "shop": shop[2], "label": name}

        return None

    @staticmethod
    def _format_item(target):
        data = target["data"]
        name = target["name"]
        lines = [f"__{name}__"]
        if data.get("Description"):
            lines.append(str(data["Description"]))
        fields = [
            ("Rank", "Rank"),
            ("ForTypes", "For Types"),
            ("ForPokemon", "For Pokémon"),
            ("Boost", "Boost"),
            ("Value", "Value"),
            ("Cures", "Cures"),
            ("OneUse", "Consumable"),
            ("HealthRestored", "Health Restored"),
            ("TrainerPrice", "Trainer Price"),
            ("PMDPrice", "PMD Price"),
        ]
        for key, label in fields:
            value = data.get(key)
            if value in (None, ""):
                continue
            if key == "OneUse":
                value = "Yes" if bool(value) else "No"
            if key == "TrainerPrice" and str(value).strip().isdigit():
                value = f"₽{value}"
            lines.append(f"**{label}**: {value}")
        return "\n".join(lines)

    @staticmethod
    def _weapon_blocks(target):
        weapon = target["data"]
        blocks = [
            f"# {weapon['name']}\n"
            f"**Category:** {weapon['kind']}\n\n"
            f"{weapon.get('details', '')}".strip()
        ]
        basic = [m for m in weapon.get("maneuvers", []) if m.get("tier") == "Basic"]
        advanced = [m for m in weapon.get("maneuvers", []) if m.get("tier") == "Advanced"]
        unique = [m for m in weapon.get("maneuvers", []) if m.get("tier") == "Unique"]
        other = [m for m in weapon.get("maneuvers", []) if m not in basic and m not in advanced and m not in unique]
        if basic:
            blocks.append("## Basic Maneuvers")
            blocks.extend(maneuver_text(m) for m in basic)
        if advanced:
            blocks.append("## Advanced Maneuvers")
            blocks.extend(maneuver_text(m) for m in advanced)
        if unique:
            blocks.append("## Maneuver")
            blocks.extend(maneuver_text(m) for m in unique)
        if other:
            blocks.append("## Maneuvers")
            blocks.extend(maneuver_text(m) for m in other)
        return blocks

    async def send_detail(self, interaction: discord.Interaction, target):
        kind = target["kind"]
        if kind == "item":
            await interaction.response.send_message(self._format_item(target))
            return

        if kind == "weapon":
            await send_chunks(interaction, self._weapon_blocks(target))
            return

        if kind in {"armor", "accessory", "tool"}:
            data = target["data"]
            if target.get("record_type") == "maneuver":
                blocks = [f"# {target['name']}\n{data.get('details', '').strip()}"]
                maneuvers = data.get("maneuvers", [])
                if maneuvers:
                    blocks.append("## Maneuver" if len(maneuvers) == 1 else "## Maneuvers")
                    blocks.extend(maneuver_text(m) for m in maneuvers)
                await send_chunks(interaction, blocks)
                return
            embed = discord.Embed(title=target["name"])
            if data.get("Description"):
                embed.add_field(name="Description", value=data["Description"], inline=False)
            if data.get("Traits"):
                embed.add_field(name="Traits", value=data["Traits"], inline=False)
            await interaction.response.send_message(embed=embed)
            return

        if kind == "apricorn":
            await interaction.response.send_message(f"__{target['name']}__\n{target['data']}")
            return

        if kind == "vehicle_module":
            await send_chunks(interaction, vehicle_module_blocks(target["data"]))
            return

        if kind == "shop":
            data = target["data"]
            embed = discord.Embed(title=target["name"])
            embed.add_field(name="Category", value=data.get("category") or "—", inline=False)
            if data.get("effect"):
                embed.add_field(name="Description", value=data["effect"], inline=False)
            price = data.get("price")
            if price not in (None, ""):
                price_text = f"₽{price}" if str(price).replace(",", "").isdigit() else str(price)
                embed.add_field(name="Listed Price", value=price_text, inline=False)
            embed.set_footer(text=f"Existing shop data: {target.get('shop', 'Unknown shop')}")
            await interaction.response.send_message(embed=embed)
            return

        await interaction.response.send_message("No detail view is available for this result.", ephemeral=True)

    @app_commands.command(
        name="roll_foraging",
        description="Roll Insight + Nature on a selected foraging table",
    )
    @app_commands.describe(
        dice="Number of d6s in the Insight + Nature pool",
        location="Environment/location table to forage from",
    )
    @app_commands.choices(location=LOCATION_CHOICES)
    async def roll_foraging(
        self,
        interaction: discord.Interaction,
        dice: app_commands.Range[int, 1, 50],
        location: app_commands.Choice[str],
    ):
        location_name = location.value
        location_tables = FORAGING_TABLES.get(location_name)
        if not location_tables:
            await interaction.response.send_message("That foraging table was not found.", ephemeral=True)
            return

        rolls = [random.randint(1, 6) for _ in range(dice)]
        successes = sum(r >= 4 for r in rolls)
        disp = ", ".join(f"**{r}**" if r >= 4 else str(r) for r in rolls)
        blocks = [
            f"## 🌿 Foraging Check — {location_name}",
            f"**Dice Pool:** {dice}d6 (Insight + Nature)",
            f"**Rolls:** {disp}",
            f"**Successes:** **{successes}**",
        ]
        if not successes:
            blocks.append("\nNo successes — nothing useful was found.")
            await interaction.response.send_message("\n".join(blocks))
            return

        levels = tables_for_successes(successes)
        blocks.append("\n**Foraging Rolls:** " + ", ".join(table_label(x) for x in levels))
        all_finds = []
        pending_luck = None

        for level in levels:
            table = location_tables[str(level)]
            d10 = random.randint(1, 10)
            raw = table[d10 - 1]
            luck_match = LUCK_RESULT_RE.match(raw)
            if luck_match:
                dc = int(luck_match.group(1))
                subtable_name = canonical_subtable_name(luck_match.group(2).strip())
                pending_luck = (dc, subtable_name)
                blocks.append(
                    f"\n### {table_label(level)} Table\n"
                    f"🎲 **d10: {d10}** — 🍀 **{dc}+ Luck Check required** → {subtable_name}\n"
                    "Choose your Luck Modifier below (0 to 100 in multiples of 5) to roll 1D100."
                )
                continue

            try:
                finds = resolve_result(raw)
            except Exception as exc:
                # Do not hide malformed authored table data if it somehow reaches runtime.
                blocks.append(
                    f"\n### {table_label(level)} Table\n"
                    f"🎲 **d10: {d10}** — {raw}\n"
                    f"⚠️ Could not resolve this result: {exc}"
                )
                continue

            all_finds.extend(finds)
            blocks.append(
                f"\n### {table_label(level)} Table\n"
                f"🎲 **d10: {d10}** — {format_find_list(finds)}"
            )

        luck_dc = pending_luck[0] if pending_luck else None
        luck_subtable = pending_luck[1] if pending_luck else None
        view = ForagingResultView(
            self,
            all_finds,
            owner_id=interaction.user.id,
            luck_dc=luck_dc,
            luck_subtable=luck_subtable,
        )
        if view.children:
            await interaction.response.send_message("\n".join(blocks), view=view)
        else:
            await interaction.response.send_message("\n".join(blocks))


async def setup(bot):
    await bot.add_cog(Foraging(bot))
