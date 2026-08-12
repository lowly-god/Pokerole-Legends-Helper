import json
import discord
from discord import app_commands
from discord.ext import commands

RANK_CHOICES = [
    app_commands.Choice(name="Starter", value="Starter"),
    app_commands.Choice(name="Rookie", value="Rookie"),
    app_commands.Choice(name="Standard", value="Standard"),
    app_commands.Choice(name="Advanced", value="Advanced"),
    app_commands.Choice(name="Expert", value="Expert"),
    app_commands.Choice(name="Ace", value="Ace"),
    app_commands.Choice(name="Master", value="Master"),
    app_commands.Choice(name="Champion", value="Champion"),
]

class RankUpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("rankup_data.json", "r", encoding="utf-8") as f:
            self.ranks = json.load(f)

    @app_commands.command(name="rankup", description="Show rank-up requirements and benefits.")
    @app_commands.describe(rank="Choose a Rank")
    @app_commands.choices(rank=RANK_CHOICES)
    async def rankup(self, interaction: discord.Interaction, rank: app_commands.Choice[str]):
        data = self.ranks[rank.value]

        embed = discord.Embed(title=f"{rank.value} Rank")

        embed.add_field(
            name="Training Points to Rank Up",
            value=str(data["Training Points Required"]),
            inline=False
        )

        benefits = "\n".join(f"• {line}" for line in data["Benefits"])
        embed.add_field(
            name="Rank Benefits",
            value=benefits,
            inline=False
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(RankUpCog(bot))
