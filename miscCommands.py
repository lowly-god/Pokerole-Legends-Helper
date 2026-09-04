import string
import json
import re
from pathlib import Path
from typing import List

import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import Choice
import csv

statuses = [
    'Burn 1', 'Burn 2', 'Burn 3', 'Paralysis', 'Frostbite 1', 'Frostbite 2', 'Frostbite 3',
    'Poison', 'Badly Poisoned', 'Sleep', 'Flinched', 'Confused', 'Disabled', 'In Love', 'Blocked',
    'Charmed', 'Disarmed', 'Exhausted', 'Leeched', 'Petrified', 'Hyper Mode', 'Shadow Boost'
]
weathers = [
    'Sunny Weather',
    'Harsh Sunlight Weather',
    'Rain Weather',
    'Typhoon Weather',
    'Sandstorm Weather',
    'Strong Wind Weather',
    'Hail Weather',
    'Snowy Weather',
    'Acid Rain Weather',
    'Midnight Weather',
    'Dense Fog',
]
terrains = [
    'Electric Terrain',
    'Grassy Terrain',
    'Misty Terrain',
    'Psychic Terrain',
    'Shadow Terrain',
    'Snowy Terrain',
]
natures = [
    'Adamant',
    'Bashful',
    'Bold',
    'Brave',
    'Calm',
    'Careful',
    'Docile',
    'Gentle',
    'Hardy',
    'Hasty',
    'Impish',
    'Jolly',
    'Lax',
    'Lonely',
    'Mild',
    'Modest',
    'Naive',
    'Naughty',
    'Quiet',
    'Quirky',
    'Rash',
    'Relaxed',
    'Sassy',
    'Serious',
    'Timid'
]

# Legends 3.0 nature mechanics
NATURE_DETAILS = {'Adamant': ('1-4', '+1 Maximum Strength, -1 Maximum Special', 4), 'Bashful': ('5-8', 'Neutral', 6), 'Bold': ('9-12', '+1 Maximum Vitality, -1 Maximum Strength', 9), 'Brave': ('13-16', '+1 Maximum Strength, -1 Maximum Dexterity', 9), 'Calm': ('17-20', '+1 Maximum Insight, -1 Maximum Strength', 8), 'Careful': ('21-24', '+1 Maximum Insight, -1 Maximum Special', 5), 'Docile': ('25-28', 'Neutral', 7), 'Gentle': ('29-32', '+1 Maximum Insight, -1 Maximum Vitality', 10), 'Hardy': ('33-36', 'Neutral', 9), 'Hasty': ('37-40', '+1 Maximum Dexterity, -1 Maximum Vitality', 7), 'Impish': ('41-44', '+1 Maximum Vitality, -1 Maximum Special', 7), 'Jolly': ('45-48', '+1 Maximum Dexterity, -1 Maximum Special', 10), 'Lax': ('49-52', '+1 Maximum Vitality, -1 Maximum Insight', 8), 'Lonely': ('53-56', '+1 Maximum Strength, -1 Maximum Vitality', 5), 'Mild': ('57-60', '+1 Maximum Special, -1 Maximum Vitality', 8), 'Modest': ('61-64', '+1 Maximum Special, -1 Maximum Strength', 10), 'Naive': ('65-68', '+1 Maximum Dexterity, -1 Maximum Insight', 7), 'Naughty': ('69-72', '+1 Maximum Strength, -1 Maximum Insight', 6), 'Quiet': ('73-76', '+1 Maximum Special, -1 Maximum Dexterity', 5), 'Quirky': ('77-80', 'Neutral', 9), 'Rash': ('81-84', '+1 Maximum Special, -1 Maximum Insight', 6), 'Relaxed': ('85-88', '+1 Maximum Vitality, -1 Maximum Dexterity', 8), 'Sassy': ('89-92', '+1 Maximum Insight, -1 Maximum Dexterity', 7), 'Serious': ('93-96', 'Neutral', 4), 'Timid': ('97-100', '+1 Maximum Dexterity, -1 Maximum Strength', 4)}

effects = [
    'Accuracy +/-X',
    'Active Combatant',
    'Aura Move',
    'Basic Heal',
    'Beam Move',
    'Bite Move',
    'Blocks',
    'Chance Dice',
    'Charge Move',
    'Clash',
    'Complete Heal',
    'Copy Move',
    'Cover',
    'Critical Failure',
    'Cure Status',
    'Cutter Move',
    'Dance Move',
    'Darkness Move',
    'Double Action',
    'Drain Move',
    'Duration',
    'Entry Hazard',
    'Evade',
    'Explosive Move',
    'Field-Type',
    'Fist Move',
    'Force Field',
    'High Critical',
    'Ignore Defenses',
    'Kick Move',
    'Late Reaction',
    'Lethal',
    'Light Move',
    'Luck Check',
    'Lunar Move',
    'Minor Heal',
    'Move Targets',
    'Must Recharge',
    'Never Miss',
    'Ongoing Damage',
    'Overheat',
    'Out of Range while Charging',
    'Physical Move',
    'Powder Move',
    'Projectile Move',
    'Pulse Move',
    'Rampage',
    'Ranged',
    'Reaction',
    'Reckless Switch',
    'Recoil',
    'Retaliatory Move',
    'Set Damage',
    'Shield Move',
    'Solar Move',
    'Sound Move',
    'Special Move',
    'STAB',
    'Successive Actions',
    'Support Move',
    'Switcher Move',
    'Terrain',
    'Triple Action',
    'Unique',
    'Weather',
    'Wind Move',
    'Z-Move',
]

version_converter = ["v3.0", "v3.0"]

async def send_msg(context, msg, *, view=None):
    # discord.py 2.6.x does not accept an explicit None as an interaction
    # View. Omit the keyword entirely unless there is an actual View.
    if isinstance(context, discord.Interaction):
        if view is None:
            await context.response.send_message(msg)
        else:
            await context.response.send_message(msg, view=view)
    else:
        if view is None:
            await context.send(msg)
        else:
            await context.send(msg, view=view)


_MOVE_KEYWORD_EXCLUSIONS = {'Physical Move', 'Special Move', 'Support Move'}
_TERRAIN_MOVE_NAMES = {
    'Electric Terrain', 'Grassy Terrain', 'Misty Terrain',
    'Psychic Terrain', 'Snowy Terrain', 'Shadow Terrain',
}
_SETTING_WEATHER_RE = re.compile(
    r'(?i)\b(?:activate|start|starts|started|set|sets|summon|summons|call|calls|create|creates)\b'
    r'[^.\n]{0,100}\bweather\b'
)
_SETTING_TERRAIN_RE = re.compile(
    r'(?i)\b(?:activate|start|starts|started|set|sets|summon|summons|call|calls|create|creates)\b'
    r'[^.\n]{0,100}\bterrain\b'
)


def _effect_tokens(effect_text):
    text = str(effect_text or '').strip()
    if not text:
        return []
    tokens = []
    for part in text.split('. '):
        part = part.strip().rstrip('.')
        if part:
            tokens.append(part)
    return tokens


def _has_keyword_token(effect_text, keyword):
    wanted = keyword.casefold()
    for token in _effect_tokens(effect_text):
        folded = token.casefold()
        if folded == wanted or folded.startswith(wanted + ' for '):
            return True
    return False


def _iter_json_records(directory):
    directory = Path(directory)
    if not directory.is_dir():
        return
    for path in directory.glob('*.json'):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            continue
        yield str(data.get('Name') or path.stem), str(data.get('Effect') or '')


def _iter_maneuver_records():
    maneuver_path = Path('maneuver_data.json')
    if not maneuver_path.is_file():
        return
    try:
        data = json.loads(maneuver_path.read_text(encoding='utf-8'))
    except Exception:
        return

    seen = set()

    def walk(value):
        if isinstance(value, dict):
            if 'name' in value and 'effect' in value:
                key = (str(value['name']), str(value.get('effect') or ''))
                if key not in seen:
                    seen.add(key)
                    yield key
            for nested in value.values():
                yield from walk(nested)
        elif isinstance(value, list):
            for nested in value:
                yield from walk(nested)

    yield from walk(data)


def linked_keyword_names(effect_name):
    """Return (moves, maneuvers) carrying an /effect keyword."""
    if effect_name.endswith(' Move') and effect_name not in _MOVE_KEYWORD_EXCLUSIONS:
        move_keyword = effect_name
        maneuver_keyword = effect_name[:-5] + ' Maneuver'
    elif effect_name.endswith(' Maneuver'):
        move_keyword = None
        maneuver_keyword = effect_name
    else:
        return [], []

    moves = set()
    if move_keyword:
        for name, effect_text in _iter_json_records(Path('pokerole_data') / 'v3.0' / 'Moves') or []:
            if _has_keyword_token(effect_text, move_keyword):
                moves.add(name)

    maneuvers = set()
    for name, effect_text in _iter_maneuver_records() or []:
        if _has_keyword_token(effect_text, maneuver_keyword):
            maneuvers.add(name)

    return (
        sorted(moves, key=str.casefold),
        sorted(maneuvers, key=str.casefold),
    )


def _z_move_names():
    moves = set()
    for name, effect_text in _iter_json_records(Path('pokerole_data') / 'v3.0' / 'Moves') or []:
        if _has_keyword_token(effect_text, 'Z-Move'):
            moves.add(name)
    return sorted(moves, key=str.casefold)


def _weather_setters():
    moves, abilities, maneuvers = set(), set(), set()
    for name, effect_text in _iter_json_records(Path('pokerole_data') / 'v3.0' / 'Moves') or []:
        if _SETTING_WEATHER_RE.search(effect_text):
            moves.add(name)
    for name, effect_text in _iter_json_records(Path('pokerole_data') / 'v3.0' / 'Abilities') or []:
        if _SETTING_WEATHER_RE.search(effect_text):
            abilities.add(name)
    for name, effect_text in _iter_maneuver_records() or []:
        if _SETTING_WEATHER_RE.search(effect_text):
            maneuvers.add(name)
    return (
        sorted(moves, key=str.casefold),
        sorted(abilities, key=str.casefold),
        sorted(maneuvers, key=str.casefold),
    )


def _terrain_setters():
    moves, abilities, maneuvers = set(), set(), set()
    for name, effect_text in _iter_json_records(Path('pokerole_data') / 'v3.0' / 'Moves') or []:
        if name in _TERRAIN_MOVE_NAMES or _SETTING_TERRAIN_RE.search(effect_text):
            moves.add(name)
    for name, effect_text in _iter_json_records(Path('pokerole_data') / 'v3.0' / 'Abilities') or []:
        if _SETTING_TERRAIN_RE.search(effect_text):
            abilities.add(name)
    for name, effect_text in _iter_maneuver_records() or []:
        if _SETTING_TERRAIN_RE.search(effect_text):
            maneuvers.add(name)
    return (
        sorted(moves, key=str.casefold),
        sorted(abilities, key=str.casefold),
        sorted(maneuvers, key=str.casefold),
    )


def _linked_effect_chunks(title, sections, limit=1900):
    lines = [f'**{title}**']
    has_any = False
    for heading, entries in sections:
        if not entries:
            continue
        has_any = True
        lines.append(f'**{heading}**')
        lines.extend(entries)
    if not has_any:
        lines.append('No linked entries were found.')

    chunks = []
    current = ''
    for line in lines:
        addition = line if not current else '\n' + line
        if current and len(current) + len(addition) > limit:
            chunks.append(current)
            current = line
        else:
            current += addition
    if current:
        chunks.append(current)
    return chunks


class EffectLinksView(discord.ui.View):
    def __init__(self, label, title, sections):
        super().__init__(timeout=180)
        self.title = title
        self.sections = sections
        button = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label=label,
        )
        button.callback = self.show_links
        self.add_item(button)

    async def show_links(self, interaction):
        chunks = _linked_effect_chunks(self.title, self.sections)
        await interaction.response.send_message(chunks[0])
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk)


def effect_keyword_view(effect_name):
    if effect_name == 'Z-Move':
        moves = _z_move_names()
        return EffectLinksView(
            'View All Z-Moves',
            'Z-Moves',
            [('Moves', moves)],
        )

    if effect_name == 'Weather':
        moves, abilities, maneuvers = _weather_setters()
        return EffectLinksView(
            'View Weather Setters',
            'Weather Setters',
            [('Moves', moves), ('Abilities', abilities), ('Maneuvers', maneuvers)],
        )

    if effect_name == 'Terrain':
        moves, abilities, maneuvers = _terrain_setters()
        return EffectLinksView(
            'View Terrain Setters',
            'Terrain Setters',
            [('Moves', moves), ('Abilities', abilities), ('Maneuvers', maneuvers)],
        )

    moves, maneuvers = linked_keyword_names(effect_name)
    if not moves and not maneuvers:
        return None
    if moves and maneuvers:
        label = 'View Linked Moves/Maneuvers'
    elif maneuvers:
        label = 'View Linked Maneuvers'
    else:
        label = 'View Linked Moves'
    return EffectLinksView(
        label,
        f'{effect_name} — Linked Entries',
        [('Moves', moves), ('Maneuvers', maneuvers)],
    )


def _format_effect_description(description):
    """Preserve authored paragraph and bullet formatting in /effect output."""
    text = str(description or '').strip()
    if not text:
        return '-'
    if '\n' in text:
        return text
    return f'- {text}'


class Misc(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.weather = dict()
        self.terrain = dict()
        self.status_v3 = dict()
        self.nature = dict()
        self.effects = dict()

    async def getGuilds(self, ctx):
        if hasattr(ctx, "guild") and ctx.guild:
            guild = ctx.guild.id
        elif hasattr(ctx, "user") and ctx.user:
            guild = ctx.user.id
        else:
            guild = ctx.author.id
        if guild not in self.bot.user_settings:
            raise KeyError("User has no settings.")
        return guild

    async def status_autocomplete(
            self,
            interaction: discord.Interaction,
            current: str
    ) -> List[Choice[str]]:
        result = self.status_v3
        if len(result) == 0:
            await self.instantiateStatus()
        # if there's not enough info then don't filter
        if len(current) < 1:
            return [
                app_commands.Choice(name=m_list, value=m_list)
                for m_list in result.keys()
            ]
        return [
            app_commands.Choice(name=m_list, value=m_list)
            for m_list in result.keys() if current.lower() in m_list.lower()
        ]

    async def effect_autocomplete(
            self,
            interaction: discord.Interaction,
            current: str
    ) -> List[Choice[str]]:
        if len(self.effects) == 0:
            await self.instantiateEffects()
        choices = sorted(
            (name for name in self.effects if current.casefold() in name.casefold()),
            key=str.casefold,
        )
        # Discord limits autocomplete responses to 25 choices. Keeping the
        # filtered set alphabetized makes /effect predictable; typing narrows
        # the list when more than 25 effects exist.
        return [app_commands.Choice(name=name, value=name) for name in choices[:25]]

    async def instantiateWeather(self):
        # 0 is name, 1 is description, 2 is effect
        with open('weather.csv', 'r', encoding = "UTF-8") as file:
            reader = csv.reader(file)
            for row in reader:
                self.weather[row[0]] = row[1:]

    async def instantiateTerrain(self):
        # 0 is name, 1 is description, 2 is effect
        with open('terrain.csv', 'r', encoding = "UTF-8") as file:
            reader = csv.reader(file)
            for row in reader:
                self.terrain[row[0]] = row[1:]

    async def instantiateStatus(self):
        with open('status_v3.csv', 'r', encoding='UTF-8') as file:
            reader = csv.reader(file)
            for row in reader:
                self.status_v3[row[0]] = row[1:]

    async def instantiateNature(self):
        with open('nature.csv', 'r', encoding = "UTF-8") as file:
            reader = csv.reader(file)
            for row in reader:
                self.nature[row[0]] = row[1:]

    async def instantiateEffects(self):
        with open('effects_v3.csv', 'r', encoding='UTF-8') as file:
            reader = csv.reader(file)
            rows = [row for row in reader if row]
        # Keep one canonical alphabetical order for autocomplete, full lists,
        # and not-found suggestions.
        self.effects = {
            row[0]: row[1]
            for row in sorted(rows, key=lambda row: row[0].casefold())
        }

    # @commands.command(name = 'weather',
    #              aliases = ['w'],
    #              help = 'Quick reference for the weather.\n'
    #                     'Type `%weather` for a list of all weather types, or'
    #                     'type `%weather sunny day` for example for an in-depth explanation.')
    async def weather_func(self, ctx, *, weather = ''):
        if len(self.weather) == 0:
            await self.instantiateWeather()
        output = ''
        weatherrepl = '\n- '
        if weather == '':
            #list all weather
            for k, v in list(self.weather.items()):
                output += f'**{k}**{weatherrepl}*{v[0]}*\n'
        else:
            #list a single weather description
            weather = weather.title()
            if f'{weather} Weather' in self.weather:
                weather += ' Weather'
            if weather in self.weather:
                # Start a new bullet for each weather rule, but keep a parenthetical
                # note attached to the rule immediately before it.
                effect = re.sub(r'\. (?=[^(])', '.' + weatherrepl, self.weather[weather][1])
                output = f'**{weather}**:\n*{self.weather[weather][0]}*{weatherrepl}{effect}'
            else:
                output = f'`{weather}` wasn\'t found in the weather list:{weatherrepl}'\
                         + weatherrepl.join([str(k) for k in self.weather.keys()])
        await send_msg(ctx, output)

    async def terrain_func(self, ctx, *, terrain = ''):
        if len(self.terrain) == 0:
            await self.instantiateTerrain()
        output = ''
        terrainrepl = '\n- '
        if terrain == '':
            #list all terrain types
            for k, v in list(self.terrain.items()):
                output += f'**{k}**{terrainrepl}*{v[0]}*\n'
        else:
            #list a single terrain description
            terrain = terrain.title()
            if f'{terrain} Terrain' in self.terrain:
                terrain += ' Terrain'
            if terrain in self.terrain:
                # Match /weather formatting: each rule begins on its own bullet.
                effect = re.sub(r'\. (?=[^(])', '.' + terrainrepl, self.terrain[terrain][1])
                output = f'**{terrain}**:\n*{self.terrain[terrain][0]}*{terrainrepl}{effect}'
            else:
                output = f'`{terrain}` wasn\'t found in the terrain list:{terrainrepl}'\
                         + terrainrepl.join([str(k) for k in self.terrain.keys()])
        await send_msg(ctx, output)


    # @commands.command(name = 'status',
    #                   help = 'Quick reference for statuses.\n'
    #                          'Type `%status` for a list of all statuses, or'
    #                          'type `%status burn` for example for an in-depth explanation.')
    async def status_func(self, ctx, *, status=''):
        status_dict = self.status_v3
        if len(status_dict) == 0:
            await self.instantiateStatus()
        output = ''
        statusrepl = '\n- '
        if status == '':
            #list all status
            for k, v in list(status_dict.items()):
                output += f'**{k}**{statusrepl}*{v[0]}*\n'
        else:
            #list a single status description
            status = string.capwords(status)
            if status == 'Burn':
                status += ' 1'
            if status in status_dict:
                effect = ''
                for stat in status_dict[status][1:]:
                    if ":" in stat:
                        effect += f'{statusrepl}__{stat.replace(":","__:", 1)}'
                    else:
                        effect += f'{statusrepl}{stat}'
                # effect = statusrepl.join(status_dict[status][1:])
                output = f'**{status}**\n*{status_dict[status][0]}*{effect}'
            else:
                output = f'`{status}` wasn\'t found in the status list:{statusrepl}' \
                         + statusrepl.join([str(k) for k in status_dict.keys()])
        await send_msg(ctx, output)


    # @commands.command(name = 'nature',
    #              aliases = ['n'],
    #              help = 'Quick reference for natures.\n'
    #                     'Type `%nature` for a list of all natures, or'
    #                     'type `%nature bold` for example for an in-depth explanation.')
    async def nature_func(self, ctx, *, nature = ''):
        if len(self.nature) == 0:
            await self.instantiateNature()
        output = ''
        naturerepl = '\n'
        if nature == '':
            # list all natures with Legends mechanical information
            for k, v in list(self.nature.items()):
                roll, modifier, confidence = NATURE_DETAILS.get(k, ('?', 'Unknown', '?'))
                output += (
                    f'**{k}** (Roll {roll})\n'
                    f'\t-*{v[0]}*\n'
                    f'\t-{modifier}\n'
                    f'\t-Confidence: {confidence}\n'
                )
        else:
            # list a single nature description with Legends mechanics
            nature = nature.title()
            if nature in self.nature:
                effect = self.nature[nature][1]
                roll, modifier, confidence = NATURE_DETAILS.get(nature, ('?', 'Unknown', '?'))
                output = (
                    f'**{nature}**  |  Roll **{roll}**\n'
                    f'*{self.nature[nature][0]}*\n\n'
                    f'**Maximum Attributes:** {modifier}\n'
                    f'**Confidence:** {confidence}\n\n'
                    f'{effect}'
                )
            else:
                output = f'`{nature}` wasn\'t found in the nature list:{naturerepl}'\
                         + naturerepl.join([str(k) for k in self.nature.keys()])
        await send_msg(ctx, output)

    async def effect_func(self, ctx, *, effect = ''):
        if len(self.effects) == 0:
            await self.instantiateEffects()
        output = ''
        effectrepl = '\n- '
        if effect == '':
            # The full reference is now too large for one Discord message.
            entries = [
                f'**{k}**\n{_format_effect_description(v)}'
                for k, v in sorted(self.effects.items(), key=lambda item: item[0].casefold())
            ]
            chunks = []
            current = ''
            for entry in entries:
                addition = entry if not current else '\n' + entry
                if current and len(current) + len(addition) > 1900:
                    chunks.append(current)
                    current = entry
                else:
                    current += addition
            if current:
                chunks.append(current)

            for index, chunk in enumerate(chunks):
                if index == 0:
                    await send_msg(ctx, chunk)
                elif isinstance(ctx, discord.Interaction):
                    await ctx.followup.send(chunk)
                else:
                    await ctx.send(chunk)
            return
        else:
            #list a single effect description
            requested = effect.strip().casefold()
            canonical = next((name for name in self.effects if name.casefold() == requested), None)
            if canonical is not None:
                effect = canonical
                output = f'**{effect}**:\n{_format_effect_description(self.effects[effect])}'
                view = effect_keyword_view(effect)

                # A single /effect entry may exceed Discord's 2000-character
                # content limit. Split it on authored line boundaries while
                # preserving Markdown/subheaders, then attach any linked-entry
                # button only to the first chunk.
                if len(output) > 1900:
                    chunks = []
                    current = ''
                    for line in output.splitlines():
                        addition = line if not current else '\n' + line
                        if current and len(current) + len(addition) > 1900:
                            chunks.append(current)
                            current = line
                        else:
                            current += addition
                    if current:
                        chunks.append(current)

                    for index, chunk in enumerate(chunks):
                        chunk_view = view if index == 0 else None
                        if index == 0:
                            await send_msg(ctx, chunk, view=chunk_view)
                        elif isinstance(ctx, discord.Interaction):
                            await ctx.followup.send(chunk)
                        else:
                            await ctx.send(chunk)
                    return
            else:
                output = f'`{effect}` wasn\'t found in the effect list:{effectrepl}'\
                         + effectrepl.join(sorted((str(k) for k in self.effects.keys()), key=str.casefold))
                view = None
        await send_msg(ctx, output, view=view)


    @commands.hybrid_command(
        name = 'status',
        description = "Display information about a Status Condition",
        help = 'Quick reference for statuses.\n'
             'Type `%status` for a list of all statuses, or'
             'type `%status burn` for example for an in-depth explanation.'
    )
    @app_commands.describe(
        status = "Which status?"
    )
    @app_commands.autocomplete(status=status_autocomplete)
    async def slash_status(self, inter : discord.Interaction, *, status : str):
        await self.status_func(ctx=inter, status=status)


    @commands.hybrid_command(
        name = 'weather',
        description = "Display information about a Weather-Type",
        help = 'Quick reference for the weather.\n'
            'Type `%weather` for a list of all weather types, or'
            'type `%weather sunny day` for example for an in-depth explanation.'
    )
    @app_commands.describe(
        weather = "Which weather?"
    )
    @app_commands.choices(
        weather = [
            Choice(name = x, value = x) for x in list(weathers)
        ]
    )
    async def slash_weather(self, inter, *, weather : str):
        await self.weather_func(ctx = inter, weather = weather)


    @commands.hybrid_command(
        name = 'terrain',
        description = "Display information about a Terrain-Type",
        help = 'Quick reference for terrain.\n'
            'Type `%terrain` for a list of all terrain types, or'
            'type `%terrain psychic` for example for an in-depth explanation.'
    )
    @app_commands.describe(
        terrain = "Which terrain?"
    )
    @app_commands.choices(
        terrain = [
            Choice(name = x, value = x) for x in list(terrains)
        ]
    )
    async def slash_terrain(self, inter, *, terrain : str):
        await self.terrain_func(ctx = inter, terrain = terrain)


    @commands.hybrid_command(
        name = 'nature',
        description = "Display information about a Nature",
        help = 'Quick reference for natures.\n'
            'Type `%nature` for a list of all natures, or'
            'type `%nature bold` for example for an in-depth explanation.'
    )
    @app_commands.describe(
        nature = "Which nature?"
    )
    @app_commands.choices(
        nature = [
            Choice(name = x, value = x) for x in list(natures)
        ]
    )
    async def slash_nature(self, inter, *, nature : str):
        await self.nature_func(ctx = inter, nature = nature)


    @commands.hybrid_command(
        name = 'effect',
        description = "Display information about common effects or terms",
        help = 'A quick reference for the effect boxes.'
    )
    @app_commands.describe(
        effect = "Which effect?"
    )
    @app_commands.autocomplete(effect=effect_autocomplete)
    async def slash_effect(self, inter, *, effect : str):
        await self.effect_func(ctx = inter, effect = effect)


async def setup(bot):
    await bot.add_cog(Misc(bot))