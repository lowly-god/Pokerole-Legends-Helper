import json
import re
import unicodedata
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


def normalize(text: str) -> str:
    text = (text or '').replace('’', "'").replace('‘', "'").replace('–', '-').replace('—', '-')
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().casefold()
    text = re.sub(r'[^a-z0-9]+', ' ', text).strip()
    return re.sub(r'\s+', ' ', text)


class ToolsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with Path('tools_data.json').open('r', encoding='utf-8') as f:
            self.tools = json.load(f)
        self.lookup = {}
        for name, entry in self.tools.items():
            for alias in [name] + entry.get('Aliases', []):
                self.lookup[normalize(alias)] = (name, entry)

    async def autocomplete(self, interaction: discord.Interaction, current: str):
        query = normalize(current)
        names = [name for name in self.tools if query in normalize(name)]
        return [app_commands.Choice(name=n[:100], value=n) for n in names[:25]]

    @app_commands.command(name='tools', description='Display a Tool and its traits')
    @app_commands.describe(name='Tool name')
    @app_commands.autocomplete(name=autocomplete)
    async def tools_command(self, interaction: discord.Interaction, name: str):
        result = self.lookup.get(normalize(name))
        if not result:
            await interaction.response.send_message('Tool not found.', ephemeral=True)
            return
        display_name, data = result
        embed = discord.Embed(title=display_name)
        if data.get('Description'):
            embed.add_field(name='Description', value=data['Description'], inline=False)
        if data.get('Traits'):
            embed.add_field(name='Traits', value=data['Traits'], inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(ToolsCog(bot))
