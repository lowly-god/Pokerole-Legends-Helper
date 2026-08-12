import csv
import random

import discord
from discord import app_commands
from discord.ext import commands


NATURE_TABLE = [(1, 4, 'Adamant', '+1 Maximum Strength, -1 Maximum Special', 4), (5, 8, 'Bashful', 'Neutral', 6), (9, 12, 'Bold', '+1 Maximum Vitality, -1 Maximum Strength', 9), (13, 16, 'Brave', '+1 Maximum Strength, -1 Maximum Dexterity', 9), (17, 20, 'Calm', '+1 Maximum Insight, -1 Maximum Strength', 8), (21, 24, 'Careful', '+1 Maximum Insight, -1 Maximum Special', 5), (25, 28, 'Docile', 'Neutral', 7), (29, 32, 'Gentle', '+1 Maximum Insight, -1 Maximum Vitality', 10), (33, 36, 'Hardy', 'Neutral', 9), (37, 40, 'Hasty', '+1 Maximum Dexterity, -1 Maximum Vitality', 7), (41, 44, 'Impish', '+1 Maximum Vitality, -1 Maximum Special', 7), (45, 48, 'Jolly', '+1 Maximum Dexterity, -1 Maximum Special', 10), (49, 52, 'Lax', '+1 Maximum Vitality, -1 Maximum Insight', 8), (53, 56, 'Lonely', '+1 Maximum Strength, -1 Maximum Vitality', 5), (57, 60, 'Mild', '+1 Maximum Special, -1 Maximum Vitality', 8), (61, 64, 'Modest', '+1 Maximum Special, -1 Maximum Strength', 10), (65, 68, 'Naive', '+1 Maximum Dexterity, -1 Maximum Insight', 7), (69, 72, 'Naughty', '+1 Maximum Strength, -1 Maximum Insight', 6), (73, 76, 'Quiet', '+1 Maximum Special, -1 Maximum Dexterity', 5), (77, 80, 'Quirky', 'Neutral', 9), (81, 84, 'Rash', '+1 Maximum Special, -1 Maximum Insight', 6), (85, 88, 'Relaxed', '+1 Maximum Vitality, -1 Maximum Dexterity', 8), (89, 92, 'Sassy', '+1 Maximum Insight, -1 Maximum Dexterity', 7), (93, 96, 'Serious', 'Neutral', 4), (97, 100, 'Timid', '+1 Maximum Dexterity, -1 Maximum Strength', 4)]


class NatureRoll(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def load_nature_text(self):
        data = {}
        try:
            with open("nature.csv", "r", encoding="UTF-8") as file:
                reader = csv.reader(file)
                for row in reader:
                    if not row:
                        continue
                    name = row[0]
                    keywords = row[1] if len(row) > 1 else ""
                    description = row[2] if len(row) > 2 else ""
                    data[name] = {
                        "keywords": keywords,
                        "description": description,
                    }
        except FileNotFoundError:
            pass
        return data

    @app_commands.command(
        name="rollnature",
        description="Roll 1d100 for a Pokémon Nature."
    )
    async def rollnature(self, interaction: discord.Interaction):
        roll = random.randint(1, 100)

        selected = None
        for low, high, name, modifier, confidence in NATURE_TABLE:
            if low <= roll <= high:
                selected = (low, high, name, modifier, confidence)
                break

        low, high, name, modifier, confidence = selected

        nature_text = self.load_nature_text().get(name, {})
        keywords = nature_text.get("keywords", "")

        output = (
            f"🎲 **Nature Roll: {roll}**\n"
            f"# {name}\n"
        )

        if keywords:
            output += f"*{keywords}*\n\n"

        output += (
            f"**Roll Range:** {low}–{high}\n"
            f"**Maximum Attributes:** {modifier}\n"
            f"**Confidence:** {confidence}"
        )

        await interaction.response.send_message(output)


async def setup(bot):
    await bot.add_cog(NatureRoll(bot))
