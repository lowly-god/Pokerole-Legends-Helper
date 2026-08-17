import json
import random
import re
import discord
from discord import app_commands
from discord.ext import commands


class EncounterTableCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("encounter_tables.json", "r", encoding="utf-8") as f:
            self.tables = json.load(f)

    async def table_autocomplete(self, interaction: discord.Interaction, current: str):
        current = current.casefold()
        return [app_commands.Choice(name=name, value=name) for name in self.tables if current in name.casefold()][:25]

    async def _send_chunks(self, interaction, title, lines):
        chunks=[]; current=f"## {title}\n"
        for line in lines:
            addition=line+"\n"
            if len(current)+len(addition)>1950:
                chunks.append(current.rstrip()); current=f"## {title} (cont.)\n"+addition
            else: current+=addition
        if current.strip(): chunks.append(current.rstrip())
        await interaction.response.send_message(chunks[0])
        for chunk in chunks[1:]: await interaction.followup.send(chunk)

    @app_commands.command(name="encounter_table", description="Display or roll a curated encounter table for a specific biome")
    @app_commands.describe(
        table="Choose the encounter table.",
        roll="Roll one result instead of displaying the entire table?",
        exclude="Roll while excluding numbers, ranges, or encounter-name text (e.g. 2, 5-7, Rock Fall)."
    )
    @app_commands.autocomplete(table=table_autocomplete)
    async def encounter_table(self, interaction: discord.Interaction, table: str, roll: bool=False, exclude: str|None=None):
        data=self.tables.get(table)
        if not data:
            await interaction.response.send_message("Encounter table not found.", ephemeral=True); return

        # Exclude retains the old subcommand behavior and implies a roll.
        if exclude:
            excluded_numbers=set(); excluded_text=[]
            for token in [p.strip() for p in exclude.split(',') if p.strip()]:
                m=re.fullmatch(r"(\d+)\s*-\s*(\d+)", token)
                if m:
                    a,b=map(int,m.groups()); excluded_numbers.update(range(min(a,b),max(a,b)+1))
                elif token.isdigit(): excluded_numbers.add(int(token))
                else: excluded_text.append(token.casefold())
            available=[e for e in data['entries'] if e['roll'] not in excluded_numbers and not any(t in e['text'].casefold() for t in excluded_text)]
            if not available:
                await interaction.response.send_message("Those exclusions remove every result from this table. Remove at least one exclusion and try again.", ephemeral=True); return
            entry=random.choice(available)
            lines=[f"🎲 **Rolled from {len(available)} remaining result(s) → {entry['roll']}**", f"**{entry['roll']}. {entry['text']}**", "", f"Excluded for this roll: `{exclude}`"]
            await self._send_chunks(interaction, f"{table} Encounter — Exclusions Applied", lines); return

        if roll:
            entry=random.choice(data['entries'])
            await self._send_chunks(interaction, f"{table} Encounter", [f"🎲 **1D{data['die']} → {entry['roll']}**", f"**{entry['roll']}. {entry['text']}**"]); return

        lines=[f"**1D{data['die']} Encounter Table**",""]+[f"**{e['roll']}.** {e['text']}" for e in data['entries']]
        await self._send_chunks(interaction, f"{table} Encounter Table", lines)


async def setup(bot):
    await bot.add_cog(EncounterTableCog(bot))
