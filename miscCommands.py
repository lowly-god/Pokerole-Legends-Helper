import string
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
    'Acid Rain Weather',
    'Midnight Weather',
    'Fog/Darkness',
    'Muddy',
    'On Fire!',
    'Electric Poles'
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

effects = ['Physical Move', 'Special Move', 'Support Move', 'Accuracy -X', 'Basic Heal', 'Bite Move', 'Blocks', 'Chance Dice', 'Charge Move', 'Copy Move', 'Cutter Move', 'Double Action', 'Entry Hazard', 'Fist Move', 'Force Field', 'High Critical', 'Ignore Defenses', 'Late Reaction', 'Lethal', 'Must Recharge', 'Never Miss', 'Ongoing Damage', 'Out of Range while Charging', 'Powder Move', 'Projectile Move', 'Rampage', 'Ranged', 'Reaction', 'Recoil', 'Shield Move', 'Sound Move', 'Successive Actions', 'Switcher Move', 'Unique', 'Wind Move']

version_converter = ["v3.0", "v3.0"]

async def send_msg(context, msg):
    if isinstance(context, discord.Interaction):
        await context.response.send_message(msg)
    else:
        await context.send(msg)

class Misc(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.weather = dict()
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
        choices = [name for name in self.effects if current.casefold() in name.casefold()]
        return [app_commands.Choice(name=name, value=name) for name in choices[:25]]

    async def instantiateWeather(self):
        # 0 is name, 1 is description, 2 is effect
        with open('weather.csv', 'r', encoding = "UTF-8") as file:
            reader = csv.reader(file)
            for row in reader:
                self.weather[row[0]] = row[1:]

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
            for row in reader:
                self.effects[row[0]] = row[1]

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
                effect = self.weather[weather][1].replace('. ', '.'+weatherrepl)
                output = f'**{weather}**:\n*{self.weather[weather][0]}*{weatherrepl}{effect}'
            else:
                output = f'`{weather}` wasn\'t found in the weather list:{weatherrepl}'\
                         + weatherrepl.join([str(k) for k in self.weather.keys()])
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
            #list all effects
            for k, v in list(self.effects.items()):
                output += f'**{k}**{effectrepl}{v}\n'
        else:
            #list a single effect description
            requested = effect.strip().casefold()
            canonical = next((name for name in self.effects if name.casefold() == requested), None)
            if canonical is not None:
                effect = canonical
                effect2 = self.effects[effect].replace('. ', '.'+effectrepl)
                #output = f'**{effect}**:\n*{self.effects[effect]}*{effectrepl}{effect2}'
                output = f'**{effect}**:{effectrepl}{effect2}'
            else:
                output = f'`{effect}` wasn\'t found in the effect list:{effectrepl}'\
                         + effectrepl.join([str(k) for k in self.effects.keys()])
        await send_msg(ctx, output)


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