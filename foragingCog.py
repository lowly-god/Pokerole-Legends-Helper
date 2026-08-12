import random

import discord
from discord import app_commands
from discord.ext import commands


FORAGING_TABLES = {
    1: [
        "Oran Berry",
        "Red Apricorn",
        "Pecha Berry",
        "Chesto Berry",
        "Cheri Berry",
        "Blue Apricorn",
        "Persim Berry",
        "Aspear Berry",
        "Pink Apricorn",
        "Tiny Bamboo Shoot",
    ],
    2: [
        "Chesto Berry",
        "Red Apricorn",
        "Rawst Berry",
        "Sitrus Berry",
        "Cyan Apricorn",
        "5x Poke Food Ingredients",
        "Energy Root",
        "Gray Apricorn",
        "Big Bamboo Shoot",
        "Green Apricorn",
    ],
    3: [
        "Green Apricorn",
        "Lum Berry",
        "Sitrus Berry",
        "White Apricorn",
        "Energy Root",
        "Gray Apricorn",
        "Cyan Apricorn",
        "3x Meal Ingredients (Rations)",
        "Energy Root",
        "Big Mushroom",
    ],
    4: [
        "Pink Apricorn",
        "Blue Apricorn",
        "Honey",
        "Lum Berry",
        "Vitality Herb",
        "Sitrus Berry",
        "Stardust",
        "Gray Apricorn",
        "Revival Herb",
        "Black Apricorn",
    ],
    5: [
        "Green Apricorn",
        "White Apricorn",
        "Evolutionary Stone",
        "5x Gourmet Poke Food Ingredients",
        "Big Mushroom",
        "Revival Herb",
        "Energy Root",
        "Type Boosting Held Item",
        "Black Apricorn",
        "Nugget",
    ],
    6: [
        "Cyan Apricorn",
        "Nature Mint",
        "Evolutionary Item",
        "Star Piece",
        "Black Apricorn",
        "Revival Herb",
        "Vitality Herb",
        "Random Held Item",
        "Balm Mushroom",
        "90+ Luck Check to find very rare Item",
    ],
}


def table_label(level: int) -> str:
    return "Six+ successes" if level == 6 else f"{level} success" + ("" if level == 1 else "es")


def tables_for_successes(successes: int):
    """
    Roll the table equal to the result, then every second table below it:
    6+ -> 6, 4, 2
    5  -> 5, 3, 1
    4  -> 4, 2
    3  -> 3, 1
    2  -> 2
    1  -> 1
    """
    if successes <= 0:
        return []

    top = min(successes, 6)
    return list(range(top, 0, -2))


class Foraging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="foraging",
        description="Make an Insight + Nature foraging check."
    )
    @app_commands.describe(
        dice="Number of d6s in the Insight + Nature pool"
    )
    async def foraging(
        self,
        interaction: discord.Interaction,
        dice: app_commands.Range[int, 1, 50]
    ):
        rolls = [random.randint(1, 6) for _ in range(dice)]
        successes = sum(1 for roll in rolls if roll >= 4)

        roll_display = ", ".join(
            f"**{roll}**" if roll >= 4 else str(roll)
            for roll in rolls
        )

        blocks = [
            "## 🌿 Foraging Check",
            f"**Dice Pool:** {dice}d6 (Insight + Nature)",
            f"**Rolls:** {roll_display}",
            f"**Successes:** **{successes}**",
        ]

        if successes == 0:
            blocks.append("\nNo successes — nothing useful was found.")
            await interaction.response.send_message("\n".join(blocks))
            return

        table_levels = tables_for_successes(successes)
        blocks.append(
            "\n**Foraging Rolls:** " +
            ", ".join(table_label(level) for level in table_levels)
        )

        rare_luck_triggered = False

        for level in table_levels:
            d10 = random.randint(1, 10)
            result = FORAGING_TABLES[level][d10 - 1]

            blocks.append(
                f"\n### {table_label(level)} Table\n"
                f"🎲 **d10: {d10}** — {result}"
            )

            # The rare-item Luck Check only applies when the character got 6+
            # successes and rolls 10 on the Six+ table.
            if successes >= 6 and level == 6 and d10 == 10:
                luck = random.randint(1, 100)
                rare_luck_triggered = True
                if luck >= 90:
                    blocks.append(
                        f"🍀 **Rare Item Luck Check: {luck}** — **SUCCESS!**\n"
                        "Find a very rare item (Curiosity Trader item, Z-Crystal, "
                        "Mega Stone, etc., at the Storyteller's discretion)."
                    )
                else:
                    blocks.append(
                        f"🍀 **Rare Item Luck Check: {luck}** — Failed (90+ required)."
                    )

        await interaction.response.send_message("\n".join(blocks))


async def setup(bot):
    await bot.add_cog(Foraging(bot))
