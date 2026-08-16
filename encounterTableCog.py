import json
import random
import re
import discord
from discord import app_commands
from discord.ext import commands


class EncounterTableCog(commands.Cog):
    encounter_table = app_commands.Group(
        name="encounter_table",
        description="Display a curated, rollable encounter table for a specific biome"
    )

    def __init__(self, bot):
        self.bot = bot
        with open("encounter_tables.json", "r", encoding="utf-8") as f:
            self.tables = json.load(f)

    async def table_autocomplete(self, interaction: discord.Interaction, current: str):
        current = current.casefold()
        return [
            app_commands.Choice(name=name, value=name)
            for name in self.tables
            if current in name.casefold()
        ][:25]

    async def _send_chunks(self, interaction, title, lines):
        chunks = []
        current = f"## {title}\n"
        for line in lines:
            addition = line + "\n"
            if len(current) + len(addition) > 1950:
                chunks.append(current.rstrip())
                current = f"## {title} (cont.)\n" + addition
            else:
                current += addition
        if current.strip():
            chunks.append(current.rstrip())
        await interaction.response.send_message(chunks[0])
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk)

    @encounter_table.command(
        name="roll",
        description="Choose a table and roll its correct die (for example 1D10 or 1D12)."
    )
    @app_commands.describe(
        table="Choose the encounter table to roll; the bot automatically uses that table's die size."
    )
    @app_commands.autocomplete(table=table_autocomplete)
    async def roll(self, interaction: discord.Interaction, table: str):
        data = self.tables.get(table)
        if not data:
            await interaction.response.send_message("Encounter table not found.", ephemeral=True)
            return

        entry = random.choice(data["entries"])
        lines = [
            f"🎲 **1D{data['die']} → {entry['roll']}**",
            f"**{entry['roll']}. {entry['text']}**",
            "",
            "Use `/encounter_table exclude` when some results have already been used and should not be rolled again."
        ]
        await self._send_chunks(interaction, f"{table} Encounter", lines)

    @encounter_table.command(
        name="exclude",
        description="Roll a table while excluding encounters that have already been used."
    )
    @app_commands.describe(
        table="Choose the encounter table to roll.",
        exclude="Exclude roll numbers, ranges, or encounter-name text; e.g. 2, 5-7, Rock Fall"
    )
    @app_commands.autocomplete(table=table_autocomplete)
    async def exclude(self, interaction: discord.Interaction, table: str, exclude: str):
        data = self.tables.get(table)
        if not data:
            await interaction.response.send_message("Encounter table not found.", ephemeral=True)
            return

        excluded_numbers = set()
        excluded_text = []
        for token in [part.strip() for part in exclude.split(",") if part.strip()]:
            match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", token)
            if match:
                first, last = map(int, match.groups())
                low, high = sorted((first, last))
                excluded_numbers.update(range(low, high + 1))
            elif token.isdigit():
                excluded_numbers.add(int(token))
            else:
                excluded_text.append(token.casefold())

        available = []
        for entry in data["entries"]:
            if entry["roll"] in excluded_numbers:
                continue
            if any(term in entry["text"].casefold() for term in excluded_text):
                continue
            available.append(entry)

        if not available:
            await interaction.response.send_message(
                "Those exclusions remove every result from this table. Remove at least one exclusion and try again.",
                ephemeral=True
            )
            return

        entry = random.choice(available)
        lines = [
            f"🎲 **Rolled from {len(available)} remaining result(s) → {entry['roll']}**",
            f"**{entry['roll']}. {entry['text']}**",
            "",
            f"Excluded for this roll: `{exclude}`",
            "Tip: exclusions can be roll numbers (`2`), ranges (`5-7`), encounter-name text (`Rock Fall`), or a comma-separated mix."
        ]
        await self._send_chunks(interaction, f"{table} Encounter — Exclusions Applied", lines)


async def setup(bot):
    await bot.add_cog(EncounterTableCog(bot))
