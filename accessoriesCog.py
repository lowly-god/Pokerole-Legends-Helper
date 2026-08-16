import json
import re
import unicodedata
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from maneuverCog import maneuver_text, send_chunks


def normalize(text: str) -> str:
    text = (text or '').replace('’', "'").replace('‘', "'").replace('–', '-').replace('—', '-')
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().casefold()
    text = re.sub(r'[^a-z0-9]+', ' ', text).strip()
    return re.sub(r'\s+', ' ', text)


class AccessoriesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with Path('accessories_data.json').open('r', encoding='utf-8') as f:
            self.static = json.load(f)
        with Path('maneuver_data.json').open('r', encoding='utf-8') as f:
            maneuver_data = json.load(f)

        self.lookup = {}
        self.choices = []

        for name, entry in self.static.items():
            record = {'type': 'static', 'name': name, 'data': entry}
            self.choices.append(name)
            for alias in [name] + entry.get('Aliases', []):
                self.lookup[normalize(alias)] = record

        for entry in maneuver_data['weapons']:
            if entry.get('kind') != 'Accessory':
                continue
            name = entry['name']
            record = {'type': 'maneuver', 'name': name, 'data': entry}
            self.choices.append(name)
            for alias in [name] + entry.get('aliases', []):
                self.lookup[normalize(alias)] = record

        self.choices = sorted(dict.fromkeys(self.choices), key=str.casefold)

    async def autocomplete(self, interaction: discord.Interaction, current: str):
        query = normalize(current)
        matches = [n for n in self.choices if query in normalize(n)]
        return [app_commands.Choice(name=n[:100], value=n) for n in matches[:25]]

    @app_commands.command(name='accessory', description="Display an Accessory's traits and Maneuver if relevant")
    @app_commands.describe(name='Accessory or augmentation name')
    @app_commands.autocomplete(name=autocomplete)
    async def accessories(self, interaction: discord.Interaction, name: str):
        record = self.lookup.get(normalize(name))
        if not record:
            await interaction.response.send_message('Accessory not found.', ephemeral=True)
            return

        if record['type'] == 'static':
            data = record['data']
            embed = discord.Embed(title=record['name'])
            if data.get('Description'):
                embed.add_field(name='Description', value=data['Description'], inline=False)
            if data.get('Traits'):
                embed.add_field(name='Traits', value=data['Traits'], inline=False)
            await interaction.response.send_message(embed=embed)
            return

        data = record['data']
        blocks = [f"# {data['name']}\n{data.get('details', '').strip()}"]
        maneuvers = data.get('maneuvers', [])
        if maneuvers:
            blocks.append('## Maneuver' if len(maneuvers) == 1 else '## Maneuvers')
            blocks.extend(maneuver_text(m) for m in maneuvers)
        await send_chunks(interaction, blocks)


async def setup(bot):
    await bot.add_cog(AccessoriesCog(bot))
