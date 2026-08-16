import json
import re
import unicodedata
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from maneuverCog import maneuver_text, send_chunks


def normalize(text: str) -> str:
    text = (text or "").replace("’", "\'").replace("‘", "\'").replace("–", "-").replace("—", "-")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return re.sub(r"\s+", " ", text)


class ArmorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with Path("armor_data.json").open("r", encoding="utf-8") as f:
            self.armor = json.load(f)
        with Path("maneuver_data.json").open("r", encoding="utf-8") as f:
            maneuver_data = json.load(f)

        self.special = {}
        self.lookup = {}
        for name, data in self.armor.items():
            self.lookup[normalize(name)] = ("standard", name, data)

        for entry in maneuver_data["weapons"]:
            if entry.get("kind") != "Armor":
                continue
            self.special[entry["name"]] = entry
            for alias in [entry["name"]] + entry.get("aliases", []):
                self.lookup[normalize(alias)] = ("special", entry["name"], entry)

    async def armor_autocomplete(self, interaction: discord.Interaction, current: str):
        query = normalize(current)
        names = list(self.armor) + list(self.special)
        return [
            app_commands.Choice(name=name[:100], value=name)
            for name in names if query in normalize(name)
        ][:25]

    @app_commands.command(name="armor", description="Look up Legends armor.")
    @app_commands.describe(name="Armor name")
    @app_commands.autocomplete(name=armor_autocomplete)
    async def armor_command(self, interaction: discord.Interaction, name: str):
        result = self.lookup.get(normalize(name))
        if not result:
            await interaction.response.send_message("Armor not found.", ephemeral=True)
            return

        kind, display_name, data = result
        if kind == "standard":
            embed = discord.Embed(title=display_name)
            embed.add_field(name="Description", value=data["Description"] or "—", inline=False)
            embed.add_field(name="Traits", value=data["Traits"] or "None.", inline=False)
            await interaction.response.send_message(embed=embed)
            return

        blocks = [f"# {display_name}\n{data.get('details', '').strip()}"]
        maneuvers = data.get("maneuvers", [])
        if maneuvers:
            blocks.append("## Maneuver" if len(maneuvers) == 1 else "## Maneuvers")
            blocks.extend(maneuver_text(m) for m in maneuvers)
        await send_chunks(interaction, blocks)


async def setup(bot):
    await bot.add_cog(ArmorCog(bot))
