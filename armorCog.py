import json
import discord
from discord import app_commands
from discord.ext import commands

class ArmorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("armor_data.json", "r", encoding="utf-8") as f:
            self.armor = json.load(f)

    async def armor_autocomplete(self, interaction: discord.Interaction, current: str):
        current = current.lower()
        return [
            app_commands.Choice(name=name, value=name)
            for name in self.armor
            if current in name.lower()
        ][:25]

    @app_commands.command(name="armor", description="Look up Legends armor.")
    @app_commands.describe(name="Armor name")
    @app_commands.autocomplete(name=armor_autocomplete)
    async def armor_command(self, interaction: discord.Interaction, name: str):
        data = self.armor.get(name)
        if not data:
            await interaction.response.send_message("Armor not found.", ephemeral=True)
            return
        embed = discord.Embed(title=name)
        embed.add_field(name="Description", value=data["Description"] or "—", inline=False)
        embed.add_field(name="Traits", value=data["Traits"] or "None.", inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(ArmorCog(bot))
