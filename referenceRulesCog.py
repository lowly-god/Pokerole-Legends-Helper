import json
import discord
from discord import app_commands
from discord.ext import commands


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

    @app_commands.command(name="colosseumrules", description="Display the Legends Colosseum rules.")
    async def colosseumrules(self, interaction: discord.Interaction):
        await self.send_reference(interaction, "colosseumrules", "Colosseum Rules")

    @app_commands.command(name="standardsofliving", description="Display Standards of Living costs and effects.")
    async def standardsofliving(self, interaction: discord.Interaction):
        await self.send_reference(interaction, "standardsofliving", "Standards of Living")

    @app_commands.command(name="stabling", description="Display Pokémon stabling options.")
    async def stabling(self, interaction: discord.Interaction):
        await self.send_reference(interaction, "stabling", "Stabling")

async def setup(bot):
    await bot.add_cog(ReferenceRulesCog(bot))
