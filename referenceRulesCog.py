import json
import discord
from discord import app_commands
from discord.ext import commands


STAMINA_TEXT = """You can use this Stamina system to run downtime, or keep track of how many activities a player character may perform throughout a given period of time. Stamina Points may be spent per day, week, or month depending on what is currently happening in your adventure.

Stamina Points are usually fully restored each time a character rests for the night successfully. If the character is suffering from any levels of Exhaustion they will only restore half their full amount (rounded down). A character may expend more Stamina Points than they have, but will take a level of Exhaustion for each point over their limit that they spend.

Note: Stamina recovery is greatly affected by a character’s “Standard of Living” (for more try /standards_of_living).

Stamina Points gained at each Rank:
• Starter Rank: 4 Stamina Points.
• Rookie Rank: 3 Stamina Points.
• Standard Rank: 2 Stamina Points.
• Advanced Rank: 2 Stamina Points.
• Expert Rank: 1 Stamina Point.
• Master Rank: 1 Stamina Point.
• Champion Rank: 1 Stamina Point.

How Stamina Points Are Used:
Stamina Points may be used to complete downtime activities, or Actions in a given day etc.
The Storyteller will set a Stamina Cost for the action or activity. The player will pay the cost in Stamina Points, and potentially roll a skill check for the Action or activities, also set by the Storyteller. The point cost should reflect the time it would take and difficulty of the action or activity.

Example daily uses and their Stamina Point costs:
• Tending to crops / Pokémon: Cost 2.
• A days work at a cafe: Cost 3.
• Going on a date: Cost 2.
• Researching a topic: Cost 2.
• Hiking up a mountain: 4.
• Going foraging: Cost 2.
• Doing a Training Session: Cost 2.

Example weekly uses and their Stamina Point costs:
• Exploring and charting an area: Cost 25.
• Travelling by foot over land: Cost 30.
• Conducting investigations on a group: Cost 22.
• Working 5 days at the Pokémon Center: Cost 26.
• Fortifying a castle’s defenses: Cost 38.
• Crafting 3 Poke Balls each night: Cost 15.
• Searching for a specific Pokémon: Cost 20.

Example monthly uses and their Stamina Point costs:
• Making a voyage on a sailing ship: Cost 150.
• Collecting resources: Cost 100.
• Working at a Pokémon Center: Cost 120.
• Performing duties as a Gym Leader: Cost 85.
• Practicing your part for a show: Cost 60.
• Honing your swordsmanship: 75.
• Repairing a damaged space ship: 110."""


def split_text(title, text, max_chars=1900):
    paragraphs = text.split("\n\n")
    chunks = []
    current = f"## {title}\n"
    for para in paragraphs:
        block = para.strip() + "\n\n"
        if len(current) + len(block) > max_chars and current.strip():
            chunks.append(current.rstrip())
            current = f"## {title} (cont.)\n" + block
        else:
            current += block
    if current.strip():
        chunks.append(current.rstrip())
    return chunks


class ReferenceRulesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("reference_data.json", "r", encoding="utf-8") as f:
            self.data = json.load(f)

    async def send_reference(self, interaction, key, title):
        chunks = split_text(title, self.data[key])
        await interaction.response.send_message(chunks[0])
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk)

    @app_commands.command(name="colosseum_rules", description="Display rules for participating in the Colosseum Challenge")
    async def colosseumrules(self, interaction: discord.Interaction):
        await self.send_reference(interaction, "colosseumrules", "Colosseum Rules")

    @app_commands.command(name="standards_of_living", description="Display Standards of Living costs, benefits and negatives")
    async def standardsofliving(self, interaction: discord.Interaction):
        await self.send_reference(interaction, "standardsofliving", "Standards of Living")

    @app_commands.command(name="stabling", description="Display Pokémon Stabling options")
    async def stabling(self, interaction: discord.Interaction):
        await self.send_reference(interaction, "stabling", "Stabling")

    @app_commands.command(name="stamina", description="Display Stamina Point rules and example uses")
    async def stamina(self, interaction: discord.Interaction):
        chunks = split_text("Stamina Points", STAMINA_TEXT)
        await interaction.response.send_message(chunks[0])
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk)


async def setup(bot):
    await bot.add_cog(ReferenceRulesCog(bot))
