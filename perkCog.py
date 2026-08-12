import json
import discord
from discord import app_commands
from discord.ext import commands

class PerkCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("perk_data.json", "r", encoding="utf-8") as f:
            self.perks = json.load(f)

    async def perk_autocomplete(self, interaction: discord.Interaction, current: str):
        current = current.lower()
        return [
            app_commands.Choice(name=name, value=name)
            for name in self.perks
            if current in name.lower()
        ][:25]

    @app_commands.command(name="perk", description="Look up a Legends Perk.")
    @app_commands.describe(name="Perk name")
    @app_commands.autocomplete(name=perk_autocomplete)
    async def perk(self, interaction: discord.Interaction, name: str):
        data = self.perks.get(name)
        if not data:
            await interaction.response.send_message("Perk not found.", ephemeral=True)
            return
        embed = discord.Embed(title=name)
        embed.add_field(name="Rank", value=data["Rank"], inline=False)
        embed.add_field(name="Description", value=data["Description"] or "—", inline=False)
        embed.add_field(name="Effect", value=data["Effect"] or "—", inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(PerkCog(bot))
