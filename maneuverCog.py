import json
import re
import unicodedata
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


DATA_FILE = Path(__file__).with_name("maneuver_data.json")


def normalize(text: str) -> str:
    text = (text or "").replace("’", "'").replace("‘", "'").replace("–", "-").replace("—", "-")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return re.sub(r"\s+", " ", text)


def maneuver_text(m, include_source=False):
    out = f"**{m['name']}**"
    if include_source:
        out += f" — *{m['source']}*"
        if m.get("tier"):
            out += f" ({m['tier']})"
    out += "\n"
    if m.get("description"):
        out += f"*{m['description']}*\n"
    out += (
        f"**Type:** {m['type']} — {m['category']}\n"
        f"**Target:** {m['target']} — **Power:** {m['power']}\n"
        f"**Accuracy Dice:** {m['accuracy']}\n"
    )
    effect = m.get("effect", "")
    out += f"**Effect:** {effect if effect else '—'}\n"
    if m.get("notes"):
        out += f"**{m['notes']}**\n"
    return out


async def send_chunks(interaction: discord.Interaction, blocks):
    chunks = []
    current = ""

    for block in blocks:
        block = block.strip() + "\n\n"
        if len(block) > 1900:
            # Fallback split for unusually long source text.
            pieces = [block[i:i + 1850] for i in range(0, len(block), 1850)]
        else:
            pieces = [block]

        for piece in pieces:
            if current and len(current) + len(piece) > 1900:
                chunks.append(current.rstrip())
                current = ""
            current += piece

    if current.strip():
        chunks.append(current.rstrip())

    if not chunks:
        chunks = ["Nothing found."]

    await interaction.response.send_message(chunks[0])
    for chunk in chunks[1:]:
        await interaction.followup.send(chunk)


class ManeuverLookup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with DATA_FILE.open("r", encoding="utf-8") as f:
            self.data = json.load(f)

        self.weapon_lookup = {}
        self.weapon_choices = []

        for weapon in self.data["weapons"]:
            if weapon.get("kind") in {"Armor", "Accessory", "Tool"}:
                continue
            self.weapon_choices.append(weapon["name"])
            for alias in [weapon["name"]] + weapon.get("aliases", []):
                self.weapon_lookup[normalize(alias)] = weapon

        self.maneuver_lookup = {}
        self.maneuver_choices = []

        for maneuver in self.data["maneuvers"]:
            self.maneuver_choices.append(maneuver["name"])
            for alias in [maneuver["name"]] + maneuver.get("aliases", []):
                self.maneuver_lookup[normalize(alias)] = maneuver

    async def weapon_autocomplete(self, interaction: discord.Interaction, current: str):
        query = normalize(current)
        matches = []
        seen = set()

        # Prefix matches first, then contains matches.
        for pass_contains in (False, True):
            for weapon in self.data["weapons"]:
                if weapon.get("kind") in {"Armor", "Accessory", "Tool"}:
                    continue
                name = weapon["name"]
                names = [name] + weapon.get("aliases", [])
                normalized = [normalize(x) for x in names]

                matched = any(
                    (query in n if pass_contains else n.startswith(query))
                    for n in normalized
                )
                if matched and name not in seen:
                    seen.add(name)
                    matches.append(app_commands.Choice(name=name[:100], value=name))
                    if len(matches) >= 25:
                        return matches
        return matches

    async def maneuver_autocomplete(self, interaction: discord.Interaction, current: str):
        query = normalize(current)
        matches = []
        seen = set()

        for pass_contains in (False, True):
            for maneuver in self.data["maneuvers"]:
                name = maneuver["name"]
                normalized = normalize(name)
                matched = query in normalized if pass_contains else normalized.startswith(query)
                if matched and name not in seen:
                    seen.add(name)
                    matches.append(app_commands.Choice(name=name[:100], value=name))
                    if len(matches) >= 25:
                        return matches
        return matches

    @app_commands.command(
        name="weapon",
        description="Look up a weapon or combat skill."
    )
    @app_commands.describe(name="Weapon or combat skill")
    @app_commands.autocomplete(name=weapon_autocomplete)
    async def weapon(self, interaction: discord.Interaction, name: str):
        weapon = self.weapon_lookup.get(normalize(name))
        if not weapon:
            await interaction.response.send_message(
                f'Weapon/combat skill "{name}" was not found.',
                ephemeral=True
            )
            return

        blocks = [
            f"# {weapon['name']}\n"
            f"**Category:** {weapon['kind']}\n\n"
            f"{weapon.get('details', '')}".strip()
        ]

        basic = [m for m in weapon.get("maneuvers", []) if m.get("tier") == "Basic"]
        advanced = [m for m in weapon.get("maneuvers", []) if m.get("tier") == "Advanced"]
        unique = [m for m in weapon.get("maneuvers", []) if m.get("tier") == "Unique"]
        other = [
            m for m in weapon.get("maneuvers", [])
            if m not in basic and m not in advanced and m not in unique
        ]

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

        await send_chunks(interaction, blocks)

    @app_commands.command(
        name="maneuver",
        description="Look up an individual human combat maneuver."
    )
    @app_commands.describe(name="Maneuver name")
    @app_commands.autocomplete(name=maneuver_autocomplete)
    async def maneuver(self, interaction: discord.Interaction, name: str):
        maneuver = self.maneuver_lookup.get(normalize(name))
        if not maneuver:
            await interaction.response.send_message(
                f'Maneuver "{name}" was not found.',
                ephemeral=True
            )
            return

        variants = maneuver["variants"]
        blocks = [f"# {maneuver['name']}"]

        if len(variants) == 1:
            blocks.append(maneuver_text(variants[0], include_source=True))
        else:
            sources = ", ".join(v["source"] for v in variants)
            blocks.append(f"**Available from:** {sources}")
            for variant in variants:
                blocks.append(maneuver_text(variant, include_source=True))

        await send_chunks(interaction, blocks)


async def setup(bot):
    await bot.add_cog(ManeuverLookup(bot))
