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

class CraftingReferenceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("crafting_reference_data.json", "r", encoding="utf-8") as f:
            self.data = json.load(f)

    async def send_reference(self, interaction, key, title):
        chunks = split_text(title, self.data[key])
        await interaction.response.send_message(chunks[0])
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk)

    @app_commands.command(name="cooking", description="Display Cooking rules and recipes")
    async def cooking(self, interaction: discord.Interaction):
        await self.send_reference(interaction, "cooking", "Cooking")

    @app_commands.command(name="crafting_pokeballs", description="Display Poké Ball crafting rules and recipes")
    async def craftingpokeballs(self, interaction: discord.Interaction):
        await self.send_reference(interaction, "craftingpokeballs", "Crafting Poké Balls")

    @app_commands.command(name="crafting_healing_items", description="Display Healing Item crafting rules and recipes")
    async def craftinghealingitems(self, interaction: discord.Interaction):
        await self.send_reference(interaction, "craftinghealingitems", "Crafting Healing Items")

async def setup(bot):
    await bot.add_cog(CraftingReferenceCog(bot))
