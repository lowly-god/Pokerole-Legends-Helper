import json
import re
import unicodedata
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

from maneuverCog import send_chunks


DATA_FILE = Path(__file__).with_name('vehicle_data.json')


def normalize(text: str) -> str:
    text = (text or '').replace('’', "'").replace('‘', "'").replace('–', '-').replace('—', '-')
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().casefold()
    text = re.sub(r'[^a-z0-9]+', ' ', text).strip()
    return re.sub(r'\s+', ' ', text)


def vehicle_command_text(command, include_source=False):
    out = f"**{command['name']}**\n"
    if include_source:
        if command.get('module'):
            out += f"**Equipment Module:** {command['module']}\n"
        else:
            out += "**Source:** General Vehicle Command\n"
    out += (
        f"**Type:** {command.get('type') or '—'} — {command.get('category') or '—'}\n"
        f"**Target:** {command.get('target') or '—'} — **Power:** {command.get('power') or '—'}\n"
        f"**Accuracy Dice:** {command.get('accuracy') or '—'}\n"
        f"**Effect:** {command.get('effect') or '—'}\n"
        f"**Requires:** {command.get('requires') or '—'}\n"
    )
    return out


def vehicle_module_blocks(module):
    header = [f"# {module['name']}", "**Category:** Equipment Module"]
    if module.get('description'):
        header.extend(['', module['description']])
    for key, label in [
        ('requires', 'Requires'),
        ('traits', 'Traits'),
        ('benefit', 'Benefit'),
        ('negative', 'Negative'),
    ]:
        if module.get(key):
            header.append(f"**{label}:** {module[key]}")

    blocks = ['\n'.join(header)]
    commands_list = module.get('commands', [])
    if commands_list:
        blocks.append('## Commands')
        blocks.extend(vehicle_command_text(command) for command in commands_list)
    return blocks


class VehicleReference(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with DATA_FILE.open('r', encoding='utf-8') as f:
            self.data = json.load(f)

        self.module_lookup = {}
        self.module_choices = []
        self.command_lookup = {}
        self.command_choices = []

        for module in self.data.get('modules', []):
            self.module_choices.append(module['name'])
            for alias in [module['name']] + module.get('aliases', []):
                self.module_lookup[normalize(alias)] = module
            for command in module.get('commands', []):
                self.command_choices.append(command['name'])
                self.command_lookup[normalize(command['name'])] = command

        for command in self.data.get('general_commands', []):
            self.command_choices.append(command['name'])
            self.command_lookup[normalize(command['name'])] = command

    @staticmethod
    def _autocomplete(source_names, current):
        query = normalize(current)
        results = []
        seen = set()
        for contains in (False, True):
            for name in source_names:
                n = normalize(name)
                matched = query in n if contains else n.startswith(query)
                if matched and name not in seen:
                    seen.add(name)
                    results.append(app_commands.Choice(name=name[:100], value=name))
                    if len(results) >= 25:
                        return results
        return results

    async def module_autocomplete(self, interaction: discord.Interaction, current: str):
        return self._autocomplete(self.module_choices, current)

    async def command_autocomplete(self, interaction: discord.Interaction, current: str):
        return self._autocomplete(self.command_choices, current)

    @app_commands.command(
        name='equipment_module',
        description='Display a Vehicle Equipment Module and its related Commands',
    )
    @app_commands.describe(name='Equipment Module name')
    @app_commands.autocomplete(name=module_autocomplete)
    async def equipment_module(self, interaction: discord.Interaction, name: str):
        module = self.module_lookup.get(normalize(name))
        if not module:
            await interaction.response.send_message(
                f'Equipment Module "{name}" was not found.',
                ephemeral=True,
            )
            return
        await send_chunks(interaction, vehicle_module_blocks(module))

    @app_commands.command(
        name='vehicle_commands',
        description='Display an individual Vehicle Command',
    )
    @app_commands.describe(name='Vehicle Command name')
    @app_commands.autocomplete(name=command_autocomplete)
    async def vehicle_commands(self, interaction: discord.Interaction, name: str):
        command = self.command_lookup.get(normalize(name))
        if not command:
            await interaction.response.send_message(
                f'Vehicle Command "{name}" was not found.',
                ephemeral=True,
            )
            return
        await send_chunks(interaction, [vehicle_command_text(command, include_source=True)])


async def setup(bot):
    await bot.add_cog(VehicleReference(bot))
