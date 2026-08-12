import json
import discord
from discord import app_commands
from discord.ext import commands

class EncounterTableCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("encounter_tables.json", "r", encoding="utf-8") as f:
            self.tables = json.load(f)

    async def table_autocomplete(self, interaction: discord.Interaction, current: str):
        current = current.lower()
        return [
            app_commands.Choice(name=name, value=name)
            for name in self.tables
            if current in name.lower()
        ][:25]

    @app_commands.command(
        name="encountertable",
        description="Display a Legends random encounter table."
    )
    @app_commands.describe(table="Choose an encounter table")
    @app_commands.autocomplete(table=table_autocomplete)
    async def encountertable(self, interaction: discord.Interaction, table: str):
        data = self.tables.get(table)
        if not data:
            await interaction.response.send_message("Encounter table not found.", ephemeral=True)
            return

        lines = [f"**{entry['roll']}.** {entry['text']}" for entry in data["entries"]]
        title = f"{table} — 1D{data['die']}"

        # Discord message text has a 2000-char limit. Send the table over as many
        # messages as needed, keeping entries intact where possible.
        chunks = []
        current = f"## {title}\n"
        for line in lines:
            addition = line + "\n"
            if len(current) + len(addition) > 1950 and current.strip():
                chunks.append(current.rstrip())
                current = f"## {title} (cont.)\n" + addition
            else:
                current += addition
        if current.strip():
            chunks.append(current.rstrip())

        await interaction.response.send_message(chunks[0])
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk)

async def setup(bot):
    await bot.add_cog(EncounterTableCog(bot))
