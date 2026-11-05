import random

import discord
from discord import app_commands
from discord.ext import commands

from luck_utils import apply_luck_modifier, format_luck_check


LUCK_CHECK_TAGLINE = "Roll a 1D100 Luck Check, with input for Luck Skill modifier"


class LuckCheckCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="roll_luck_check",
        description=LUCK_CHECK_TAGLINE,
    )
    @app_commands.describe(
        luck_modifier="Luck Skill modifier; must be a multiple of 5 from 0 to 100."
    )
    async def roll_luck_check(
        self,
        interaction: discord.Interaction,
        luck_modifier: app_commands.Range[int, 0, 100] = 0,
    ):
        if luck_modifier % 5:
            await interaction.response.send_message(
                "Luck Modifier must be a multiple of 5 (0, 5, 10 ... 100).",
                ephemeral=True,
            )
            return

        d100_roll = random.randint(1, 100)
        total = apply_luck_modifier(d100_roll, luck_modifier)
        calculation = format_luck_check(d100_roll, luck_modifier)
        await interaction.response.send_message(f"🍀 **{calculation}**")


    @app_commands.command(
        name="roll_death_save",
        description="Roll a 1D100 Death Save using a Luck or Vitality Modifier.",
    )
    @app_commands.describe(
        modifier="Luck or Vitality Modifier; must be a multiple of 5 from 0 to 100."
    )
    async def roll_death_save(
        self,
        interaction: discord.Interaction,
        modifier: app_commands.Range[int, 0, 100] = 0,
    ):
        if modifier % 5:
            await interaction.response.send_message(
                "Luck or Vitality Modifier must be a multiple of 5 (0, 5, 10 ... 100).",
                ephemeral=True,
            )
            return

        d100_roll = random.randint(1, 100)
        total = apply_luck_modifier(d100_roll, modifier)
        calculation = f"Death Save Roll {d100_roll} + Luck or Vitality Modifier {modifier} = {total}"
        if total >= 95:
            outcome = "You regain consciousness at 1 HP!"
        elif total > 55:
            outcome = "Success!"
        else:
            outcome = "Failure! You receive one Pain Penalty."
        await interaction.response.send_message(f"🍀 **{calculation}**\n{outcome}")


async def setup(bot):
    await bot.add_cog(LuckCheckCog(bot))
