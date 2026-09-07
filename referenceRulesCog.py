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


CATCHING_RULE_SECTIONS = [
    """**Catching Rules**

__Required Successes by Rank__
Starter: 3.
Rookie: 4.
Standard: 6.
Advanced: 8.
Expert: 9.
Ace: 10.

__Seal Check Bonus Dice__
Trainer Crits their Throw (Dexterity + Athletics) Check: 1 Bonus Success.
Target Pokémon is at half HP: 1 Bonus Success.
Target Pokémon is at 1 HP: 2 Bonus Successes.
Target Pokémon has a Status Condition: 1 Bonus Success per Status Condition.

__Fainted Pokémon__
All Bonuses are removed. Only the base Seal Check Dice Pool is used.
The captured Pokémon's Happiness and Loyalty are reduced to 0.

__Happiness and Loyalty Reductions__
If a Captured Pokémon is on 1 HP, reduce its Happiness and Loyalty by 1.
If a Captured Pokémon is suffering from any Status Conditions reduce its Happiness and Loyalty by 1 for each Status Condition.
If there where more Active Combatants on the capturing Trainer's side reduce its Happiness and Loyalty by 1.

__Encounter Luck Checks__
Use /roll_luck_check: If this Roll is above 90 the Pokémon has its Hidden Ability! (In addition to its regular one(s).
Use /roll_luck_check: If this Roll is above 95 the Pokémon is Shiny!
Use /roll_nature: This Roll determines the Pokémon's Nature. However, if you have 3 or more Points in Luck, you may choose to re-roll it once.""",
    """**Poke Balls**

__Standard Balls:__
Poke Ball (4d6)
Great Ball (6d6)
Ultra Ball (8d6)
Premier Ball (5d6)

__Artisan Balls:__
All "Artisan Balls" have a base Seal Check of 4d6.
Aurora Ball (+3d6 if used on Ice-Type Pokémon)
Dive Ball (+3d6 if used on Water-Type or Pokémon found underwater)
Fast Ball (+3d6 if used on "fast" Pokémon)
Fae Ball (+3d6 if used on Fairy-Type Pokémon)
Feather Ball (+3d6 if used on Flying-Type or Levitating Pokémon)
Level Ball (+1d6 for each Rank the Pokémon is below your Trainer Rank)
Love Ball (+3d6 if used on a Pokémon who has the In Love Status Condition)
Lure Ball (+3d6 if used when Fishing)
Moon Ball (+3d6 if used on Pokémon that Evolve by Moonstone)
Nest Ball (+3d6 if used on Pokémon who are on their first Stage of Evolution, and aren't fully Evolved)
Net Ball (+3d6 if used on Bug-Type Pokémon)
Repeat Ball (+3d6 if used on a Pokémon species you have caught before)
Tech Ball (+3d6 if used on "inorganic" Pokémon)
Dawn Ball (+3d6 if used in the morning or bright locations)
Dusk Ball (+3d6 if used at night or in dark locations)
Quick Ball (+3d6 if used before a Battle or in social encounters)
Friend Ball (+2d6 caught Pokémon gains +1 base Happiness and Loyalty)
Heavy Ball (+1d6 for each 50lbs above 200lbs up to max of +10)
Timer Ball (+1d6 per rounds in battle up to max of +10)
Luxury Ball (+4d6 caught Pokémon regains +1 additional Will Point each day)""",
    """__Other Balls:__
Beast Ball (9d6 if used on Ultra Beasts, 2d6 if used on other Pokémon)
Cherish Ball (8d6, caught Pokémon gains +2 base Happiness and Loyalty)
Dark Ball (4d6, or Current Will + Intimidate, caught Pokémon becomes Shadow-Type)
Neura Ball (4d6, or if Trainer has Neural Augmentation they may roll Current Will + Empathy)
Park Ball (7d6, only given out during special events)
Safari Ball (7d6, only given out at the Safari Zone)
Sport Ball (7d6, only given out during Pokémon catching contests)
Master Ball (Guaranteed capture)""",
]


def split_sections(sections, max_chars=1900):
    """Pack complete authored sections into Discord-safe messages."""
    chunks = []
    current = ""

    for section in sections:
        section = section.strip()
        if len(section) > max_chars:
            raise ValueError(
                "A catching-rules section exceeds Discord's safe message size; "
                "split the authored section deliberately rather than truncating it."
            )

        addition = section if not current else "\\n\\n" + section
        if current and len(current) + len(addition) > max_chars:
            chunks.append(current)
            current = section
        else:
            current += addition

    if current:
        chunks.append(current)
    return chunks


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


    @app_commands.command(name="catching_rules", description="Display rules for catching wild Pokémon")
    async def catching_rules(self, interaction: discord.Interaction):
        chunks = split_sections(CATCHING_RULE_SECTIONS)
        await interaction.response.send_message(chunks[0])
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk)



async def setup(bot):
    await bot.add_cog(ReferenceRulesCog(bot))
