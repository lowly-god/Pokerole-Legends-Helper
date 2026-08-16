import asyncio
import csv
import json
import os
import pickle
import random
import re
import typing
from typing import Literal, List
import sys
import traceback

import discord
import discord.ext.commands
import unicodedata
from discord.ext import commands
from discord import app_commands, ui
from discord.app_commands import Choice
from discord.ui import Button
from dotenv import load_dotenv
from symspellpy import SymSpell, Verbosity
# can be replaced when/if i ever convert to nosql
import requests
from numpy.random import choice
from bisect import bisect

from dbhelper import Database
from statsExtra import pokemon_extra_stats_text
from machineLearnsets import machine_moves_section

# for my testing environment
dev_env = (True if len(sys.argv) > 1 else False)
test_guilds = [669326419641237509]  # , 709299031968579625]
SLASH_COMMANDS = []

load_dotenv()

if not dev_env:
    print("POKEROLE_TOKEN set:", bool(os.getenv('POKEROLE_TOKEN')))
    print("DISCORD_TOKEN set:", bool(os.getenv('DISCORD_TOKEN')))

    token = os.getenv('POKEROLE_TOKEN') or os.getenv('DISCORD_TOKEN')
else:
    token = os.getenv('BETA_TOKEN')

cmd_prefix = ('./' if dev_env else '%')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=cmd_prefix, intents=intents)

# note that 'custom help' needs to load last
cogs = ['diceCog', 'miscCommands', 'questCog', 'maneuverCog', 'fieldtypeCog', 'natureRollCog', 'foragingCog', 'perkCog', 'armorCog', 'accessoriesCog', 'toolsCog', 'shopCog', 'humanNpcCog', 'rankUpCog', 'encounterTableCog', 'referenceRulesCog', 'trainingReferenceCog', 'craftingReferenceCog', 'custom_help']

# TODO: compress more of the data in working memory
#   ++PokeLearns ranks complete
#   Need:
#   --PokeLearns moves (probably index the movelist and change all moves in pokelearns to an index?)

# settings {channel : [(shiny_chance, int), (ability, int), (secondary, int), (hidden, int),
# (show_encounter_move_desc, 0)]}
pokebotsettings = dict()

# pokemon moves
pkmnMoves = dict()
pkmnWeather = dict()
database: Database = None


def _load_moved_lookup_names(filename):
    names = set()
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        for name, data in payload.items():
            names.add(name.casefold())
            for alias in data.get('Aliases', []):
                names.add(alias.casefold())
    except Exception:
        pass
    return names


ACCESSORY_LOOKUP_NAMES = _load_moved_lookup_names('accessories_data.json')
TOOL_LOOKUP_NAMES = _load_moved_lookup_names('tools_data.json')
MOVED_ITEM_LOOKUP_NAMES = ACCESSORY_LOOKUP_NAMES | TOOL_LOOKUP_NAMES
restartError = True

base_regions = ['Kanto', 'Johto', 'Hoenn', 'Sinnoh', 'Unova', 'Kalos', 'Alola', 'Galar']
custom_regions = ['Orrelborous', "Islas Lluvia De'estrellas"]
regions = base_regions + custom_regions

with open(os.path.join(os.path.dirname(__file__), 'encounter_biomes.json'), 'r', encoding='utf-8') as biome_file:
    encounter_biomes = json.load(biome_file)

_biome_names = list(encounter_biomes)
_islas_biome_start = _biome_names.index('Subtropical Forest')
_orrelborous_biome_names = _biome_names[:_islas_biome_start]
_islas_biome_names = [name for name in _biome_names[_islas_biome_start:] if name != 'AREA UNKNOWN']

def _combine_biome_pools(biome_names):
    return list(dict.fromkeys(
        pokemon
        for biome_name in biome_names
        for pokemon in encounter_biomes[biome_name]
    ))

custom_region_pools = {
    'Orrelborous': _combine_biome_pools(_orrelborous_biome_names),
    "Islas Lluvia De'estrellas": _combine_biome_pools(_islas_biome_names),
}

ranks_v3 = ['Starter', 'Rookie', 'Standard', 'Advanced', 'Expert', 'Ace', 'Master', 'Champion']



# LEGENDS_UB_ALIASES
POKEMON_ALIASES = {
    "UB-01 Symbiont": "Nihilego",
    "UB-02 Absorption": "Buzzwole",
    "UB-02 Absorbtion": "Buzzwole",
    "UB-03 Beauty": "Pheromosa",
    "UB-04 Lightning": "Xurkitree",
    "UB-04 Lighting": "Xurkitree",
    "UB-05 Blaster": "Celesteela",
    "UB-06 Blade": "Kartana",
    "UB-07 Glutton": "Guzzlord",
    "UB-08 Adhesive": "Poipole",
    "UB-09 Stinger": "Naganadel",
    "UB-10 Assembly": "Stakataka",
    "UB-11 Burst": "Blacephalon",
    "Tatsugiri (Mega Form)": "Tatsugiri (Curly Mega Form)",
}
_POKEMON_ALIAS_KEYS = {k.casefold(): v for k, v in POKEMON_ALIASES.items()}


def resolve_pokemon_alias(name):
    return _POKEMON_ALIAS_KEYS.get(str(name).casefold(), name)


def rank_dist(version="v3.0"):
    # Legends Helper is v3-only. Keep the optional parameter for compatibility
    # with existing callers, but always use the v3 rank distribution.
    return random.choice([ranks_v3[0]] * 2 + [ranks_v3[1]] * 5 + [ranks_v3[2]] * 7 +
                         [ranks_v3[3]] * 2 + [ranks_v3[3], ranks_v3[4]])


rankBias_v3 = [1, 2, 3, 5, 7, 9, 10, 11]
natures = ['Hardy (9)', 'Lonely (5)', 'Brave (9)', 'Adamant (4)', 'Naughty (6)',
           'Bold (9)', 'Docile (7)', 'Relaxed (8)', 'Impish (7)',
           'Lax (8)', 'Timid (4)', 'Hasty (7)', 'Serious (4)', 'Jolly (10)',
           'Naive (7)', 'Modest (10)', 'Mild (8)', 'Quiet (5)', 'Bashful (6)',
           'Rash (6)', 'Calm (8)', 'Gentle (10)', 'Sassy (7)', 'Careful (5)', 'Quirky (9)']

bot.socials = [('Tough', 1), ('Cool', 1), ('Beauty', 1), ('Clever', 1), ('Cute', 1)]
bot.skills = [('Brawl', 0), ('Channel', 0), ('Clash', 0), ('Evasion', 0),
              ('Alert', 0), ('Athletic', 0), ('Nature', 0), ('Stealth', 0),
              ('Allure', 0), ('Etiquette', 0), ('Intimidate', 0), ('Perform', 0),
              ('Aura', 0), ('Luck', 0), ('Empathy', 0)]

types = ['normal', 'fire', 'water', 'grass', 'electric', 'ice', 'fighting', 'poison', 'ground',
         'flying', 'psychic', 'bug', 'rock', 'ghost', 'dark', 'dragon', 'steel', 'fairy']


def _load_metronome_excluded_move_names():
    """Load source-authored Z-Moves and Unique Moves for /metronome exclude_silly."""
    names = set()
    move_dir = os.path.join(os.path.dirname(__file__), 'pokerole_data', 'v3.0', 'Moves')
    try:
        for filename in os.listdir(move_dir):
            if not filename.endswith('.json'):
                continue
            with open(os.path.join(move_dir, filename), 'r', encoding='utf-8') as f:
                data = json.load(f)
            attributes = data.get('Attributes', {}) or {}
            if attributes.get('ZMove') or attributes.get('Unique'):
                names.add(data.get('Name', filename[:-5]))
    except Exception as exc:
        print(f'Could not build Metronome exclusion list: {exc}')
    return names

METRONOME_SILLY_EXCLUDED_MOVES = _load_metronome_excluded_move_names()

# v3 total attributes at a rank (base/social)
# attributes are limited by poke
attributeAmount_v3 = (0, 2, 4, 6, 8, 10, 11, 12)
# total skill points at a rank
skillAmount_v3 = (5, 10, 14, 17, 19, 21, 23, 25)
# highest any single skill can be
limit_v3 = (1, 2, 3, 4, 5, 5, 6, 6)

# Number of moves added beyond Insight in v3 encounters.
num_moves_v3 = 3

# lists are global...
#   pokemon list:
# {listName : [list] }
#   item list:
# {listName : [ 'i', [chance, item1, item2], [chance2, item3, item4], ... ]
pkmnLists = dict()

pokecap = re.compile(r'(^|[-( ])\s*([a-zA-Z])')
alpha_str = re.compile(r'[^\w_, \-]+')

# add the dictionaries
poke_dict = SymSpell()
poke_dict.load_dictionary('PokeDictionary.txt', 0, 1, separator='$')

move_dict = SymSpell()
move_dict.load_dictionary('MoveDictionary.txt', 0, 1, separator='$')

ability_dict = SymSpell()
ability_dict.load_dictionary('AbilityDictionary.txt', 0, 1, separator='$')

# github stuff for updating the lists
github_base = 'https://raw.githubusercontent.com/XShadeSlayerXx/PokeRole-Discord.py-Base/master/'
extra_files = [  # assuming UTF-8
    'nature.csv',
    'weather.csv'
]


# save and load functions
def save_obj(obj: object, name: str):
    with open(name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def load_obj(name):
    with open(name + '.pkl', 'rb') as f:
        return pickle.load(f)


# list of dictionary files
files = [('pkmnLists', pkmnLists), ('pokebotsettings', pokebotsettings)]


def cleanup_legacy_crest_item_files():
    """Remove obsolete duplicate Crest JSON files left by older patches."""
    item_dir = os.path.join('pokerole_data', 'v3.0', 'Items')
    for filename in ('Garbocean Crest.json', 'Manaphy Crest.json'):
        path = os.path.join(item_dir, filename)
        if os.path.isfile(path):
            os.remove(path)
            print(f'Removed obsolete duplicate Crest source: {filename}')


@bot.event
async def on_ready():
    global pkmnLists
    global pokebotsettings
    global database
    global restartError
    global SLASH_COMMANDS

    if not await checkFilesExist(extra_files):
        await init_extra_files()

    for cog in cogs:
        await bot.load_extension(cog)

    cleanup_legacy_crest_item_files()
    database = Database()

    print(f'{bot.user} has connected to Discord!')
    print(f'Servers: {len(bot.guilds)}')
    for guild in sorted(bot.guilds, key=lambda g: g.name.lower()):
        print(f' - {guild.name}')

    await bot.change_presence(activity=discord.Game(name='Bzzzt! Spiritomb!'))

    if not hasattr(bot, 'appinfo'):
        bot.appinfo = await bot.application_info()

    random.seed()

    # load the files
    for file in files:
        # check if saved data exists
        if os.path.isfile('{0}.pkl'.format(file[0])):
            # save the data if the file exists
            try:
                file[1].update(load_obj(file[0]))
            except:
                file[1] = load_obj(file[0])
            print(file[0] + ' info loaded!')
            # store the newly loaded data into a backup
            save_obj(file[1], file[0] + "_backup")
        else:
            print('file ' + file[0] + ' not found, creating file')
            tempf = open(file[0] + ".pkl", "w")
            tempf.close()
            save_obj(file[1], file[0])

    # Migrate any settings saved by older builds. Version selection no longer
    # exists; every guild/user is permanently v3.0.
    for place in list(pokebotsettings):
        await instantiateSettings(place)

    # tree init
    for command in SLASH_COMMANDS:
        bot.tree.add_command(command)

    # This command was added after the existing production global command set was
    # already registered. Ensure it is installed once without requiring a manual
    # %sync_global invocation.
    await ensure_get_pokerole_legends_registered()

    # Production uses global application commands only. Older versions of the bot
    # exposed sync_test, which copied every global command into a test guild and
    # could leave a second guild-scoped copy registered in Discord. Clean those
    # stale guild registrations once, then leave the global commands untouched.
    await cleanup_stale_guild_slash_commands()

    if not dev_env:
        await bot.appinfo.owner.send(f'Connected Successfully')
    bot.user_settings = pokebotsettings
    restartError = False


#######
# sync commands

SLASH_GUILD_CLEANUP_MARKER = '.slash_guild_duplicates_cleaned_v1'
GETPOKEROLELEGENDS_COMMAND = 'get_pokerole_legends'


async def ensure_get_pokerole_legends_registered():
    """Register the Legends supplement command if Discord does not have it yet.

    Global commands normally only change when sync_global is run. This small startup
    migration makes this particular new command self-installing without syncing on
    every restart.
    """
    if dev_env:
        return

    try:
        registered = await bot.tree.fetch_commands()
        registered_names = {command.name for command in registered}
        if GETPOKEROLELEGENDS_COMMAND in registered_names:
            print('Slash command /get_pokerole_legends is already registered globally.')
            return

        synced = await bot.tree.sync()
        synced_names = {command.name for command in synced}
        if GETPOKEROLELEGENDS_COMMAND in synced_names:
            print('Registered global slash command: /get_pokerole_legends')
        else:
            print('Global slash sync completed, but /get_pokerole_legends was not returned by Discord.')
    except Exception as exc:
        print(f'Failed to register /get_pokerole_legends: {exc}')


async def cleanup_stale_guild_slash_commands():
    """Remove old guild-scoped copies of the bot's global slash commands once.

    This bot does not intentionally define any guild-only application commands in
    production. Previous use of sync_test could leave a full copied command tree
    registered to a guild, which Discord can show alongside the global commands.
    """
    if dev_env or os.path.isfile(SLASH_GUILD_CLEANUP_MARKER):
        return

    try:
        global_commands = await bot.tree.fetch_commands()
        global_by_name = {command.name: command for command in global_commands}
        global_names = set(global_by_name)
        cleaned_any = False

        def command_signature(command):
            # Compare the Discord-side command metadata that can actually become
            # stale between a global registration and an old guild registration.
            options = []
            for option in getattr(command, 'options', []) or []:
                options.append((
                    getattr(option, 'name', None),
                    str(getattr(option, 'type', None)),
                    getattr(option, 'description', None),
                    bool(getattr(option, 'required', False)),
                ))
            return (getattr(command, 'description', None), tuple(options))

        for guild in bot.guilds:
            guild_obj = discord.Object(id=guild.id)
            guild_commands = await bot.tree.fetch_commands(guild=guild_obj)
            if not guild_commands:
                continue

            names = [command.name for command in guild_commands]
            duplicates = sorted(name for name in names if name in global_names)
            stale_only = sorted(name for name in names if name not in global_names)

            print(f'Stale guild slash commands found in {guild.name} ({guild.id}): {len(names)}')
            if duplicates:
                print(' - Duplicate global copies: ' + ', '.join(duplicates))
                for guild_command in guild_commands:
                    global_command = global_by_name.get(guild_command.name)
                    if global_command is None:
                        continue
                    if command_signature(guild_command) == command_signature(global_command):
                        print(f'   {guild_command.name}: registered metadata matches global copy')
                    else:
                        print(f'   {guild_command.name}: registered metadata DIFFERS from global copy')
                        if getattr(guild_command, 'description', None) != getattr(global_command, 'description', None):
                            print(f'     guild description: {getattr(guild_command, "description", "")}')
                            print(f'     global description: {getattr(global_command, "description", "")}')
                        guild_options = [getattr(o, 'name', None) for o in (getattr(guild_command, 'options', []) or [])]
                        global_options = [getattr(o, 'name', None) for o in (getattr(global_command, 'options', []) or [])]
                        if guild_options != global_options:
                            print(f'     guild options: {guild_options}')
                            print(f'     global options: {global_options}')
            if stale_only:
                print(' - Other stale guild commands: ' + ', '.join(stale_only))

            # There are no intentional guild-only slash commands in production, so
            # syncing an empty guild tree safely removes all stale/test registrations.
            bot.tree.clear_commands(guild=guild_obj)
            await bot.tree.sync(guild=guild_obj)
            print(f'Cleared stale guild slash commands from {guild.name}.')
            cleaned_any = True

        with open(SLASH_GUILD_CLEANUP_MARKER, 'w', encoding='utf-8') as marker:
            marker.write('Guild-scoped slash command cleanup completed.\n')

        if cleaned_any:
            print('Slash command duplicate cleanup complete. Global commands were kept.')
        else:
            print('Slash command audit complete: no guild-scoped commands were registered.')
    except Exception as exc:
        # Do not create the marker on failure so the bot can retry next startup.
        print(f'Slash command duplicate cleanup failed: {exc}')


@commands.is_owner()
@bot.command(name='sync_global', hidden=True)
async def sync_commands(ctx):
    local_names = sorted(command.name for command in bot.tree.get_commands())
    print(f'Local global slash commands before sync ({len(local_names)}): {", ".join(local_names)}')

    synced = await bot.tree.sync()
    synced_names = sorted(command.name for command in synced)
    print(f'Discord global slash commands after sync ({len(synced_names)}): {", ".join(synced_names)}')

    await ctx.message.add_reaction('\N{HIBISCUS}')
    await ctx.send(
        f'Synced {len(synced_names)} global slash commands.\n'
        f'`{", ".join(synced_names)}`'
    )


#######
# converters


def ensure_rank(arg: str) -> str:
    arg = arg.title()
    if arg not in ranks_v3 and arg not in ['Base', 'Random']:
        raise commands.errors.ConversionError(f'{arg} is not a valid rank.')
    return arg


def pkmn_cap(arg: str) -> str:
    return re.sub(pokecap, lambda p: p.group(0).upper(), arg)


#######
# helper functions

def lookup_poke(arg: str) -> str:
    suggestion = poke_dict.lookup(arg, Verbosity.CLOSEST, max_edit_distance=2,
                                  include_unknown=True)[0]
    return suggestion.term


def lookup_move(arg: str) -> str:
    suggestion = move_dict.lookup(arg, Verbosity.CLOSEST, max_edit_distance=2,
                                  include_unknown=True)[0]
    return suggestion.term


def lookup_ability(arg: str) -> str:
    suggestion = ability_dict.lookup(arg, Verbosity.CLOSEST, max_edit_distance=2,
                                     include_unknown=True)[0]
    return suggestion.term


async def send_big_msg(ctx, arg: str, codify: bool = False, view: ui.View = None):
    # due to hybrid commands, sometimes slash messages can end up here
    if not view:
        # discord likes an empty dict more than None on an initial message
        view = ui.View()
    if isinstance(ctx, discord.Interaction):
        await send_big_slash_msg(ctx, arg, codify, view=view)
        return
    arg += '\n'
    if codify:
        arg = arg.replace('`', '')  # remove all backticks since they're irrelevant
        arg = arg.replace('*__', '-')
        arg = arg.replace('__', '')
        arg = arg.replace('*', '')
    while arg != '' and arg != []:
        try:
            last_newline = arg.rindex('\n', 5, 1990)
        except:
            last_newline = 1990
        if codify:
            msg = f'```{arg[:last_newline]}```'
        else:
            msg = arg[:last_newline]
        next_arg = arg[last_newline + 1:]
        if len(next_arg) != 0:
            await ctx.send(msg)
        else:
            await ctx.send(msg, view=view)
        # plus 1 to go over the '\n'
        arg = next_arg


async def send_big_slash_msg(inter, arg: str, codify: bool = False, offset: int = 0, view: ui.View = None):
    if not view:
        # discord likes an empty dict more than None on an initial message
        view = ui.View()
    arg += '\n'
    which = True
    if codify:
        arg = arg.replace('`', '')  # remove all backticks since they're irrelevant
        arg = arg.replace('*__', '-')
        arg = arg.replace('__', '')
        arg = arg.replace('*', '')
    while arg != '' and arg != []:
        try:
            last_newline = arg.rindex('\n', 5, 1990)
        except:
            last_newline = 1990
        if codify:
            msg = f'```{arg[offset:last_newline]}```'
        else:
            msg = arg[offset:last_newline]
        next_arg = arg[last_newline + 1:]
        if len(next_arg) != 0:
            if which:
                await inter.response.send_message(msg)
                which = not which
                offset = 0
            else:
                await inter.followup.send(msg)
        else:
            if which:
                await inter.response.send_message(msg, view=view)
                view.message = await inter.original_response()
                which = not which
                offset = 0
            else:
                view.message = await inter.followup.send(msg, view=view)
        # plus 1 to go over the '\n'
        arg = next_arg


async def getGuilds(ctx):
    if hasattr(ctx, "guild") and ctx.guild:
        guild = ctx.guild.id
    elif hasattr(ctx, "user") and ctx.user:
        guild = ctx.user.id
    else:
        guild = ctx.author.id
    if guild not in pokebotsettings:
        await instantiateSettings(guild)
    return guild


def pokesFromList(listname: str) -> list:
    output = []
    # skip the 'i' or 'p'
    for lists in pkmnLists[listname][1:]:
        # skip the percentage
        for poke in lists[1:]:
            output.append(poke)
    return output


def getStatus(statustype: str) -> str:
    statustype = statustype.split()[0].lower()
    if statustype in ['burn', 'burned']:
        return '🔥'  # '\N{FIRE}'
    elif statustype in ['badly', 'poison', 'poisoned']:
        return '🟢'  # '\N{GREEN_CIRCLE}'
    elif statustype in ['love', 'infatuation']:
        return '❤️'  # '\N{HEART}'
    elif statustype in ['paralyzed', 'paralysis']:
        return '⚡'  # '\N{ZAP}'
    elif statustype == 'frozen':
        return '❄️'  # '\N{SNOWFLAKE}'
    elif statustype == 'confused':
        return '💫'  # '\N{SPARKLES}'
    elif statustype == 'leech':
        return '🌱'  # '\N{SEEDLING}'
    return '🗡️'  # '\N{DAGGER}'



async def getPokemonAbilities(pkmn, version="v3.0"):
    pkmn = resolve_pokemon_alias(pkmn)
    query = f'SELECT ability, ability2, abilityhidden, abilityevent FROM pkmnStats WHERE name="{pkmn}"'
    query = database.custom_query(query, version=version)[0]
    ability = list(query)
    while '' in ability:
        ability.remove('')
    ability_expanded = [(await pkmnabilitieshelper(x, version=version)) for x in ability]

    output = ''
    for name, (effect, desc) in zip(ability, ability_expanded):
        output += f'**{name}:** {effect}\n'
        if desc != "":
            output += f'*{desc}*\n'
        output += '\n'

    return output[:-2]  # -2 to remove the trailing \n 's


#######
# decorators

def dev():
    def predicate(ctx):
        return dev_env

    return commands.check(predicate)


#######

async def send_owner_msg(msg='', fp=None):
    tmp = await bot.application_info()
    if fp:
        await tmp.owner.send(msg, file=discord.File(fp))
    else:
        await tmp.owner.send(msg)


@commands.is_owner()
@bot.command(name='restart', hidden=True)
async def restart(ctx):
    await ctx.message.add_reaction('\N{HIBISCUS}')
    await bot.close()


@commands.is_owner()
@bot.command(name='guilds', hidden=True)
async def guildcheck(ctx):
    # once the bot hits 75 servers I want to verify it
    # I'm curious of the growth
    await ctx.send(f'Currently in {len(bot.guilds)} guilds.')


# @commands.is_owner()
# @bot.command(name = 'checkdata', hidden = True)
# async def integrityChecks(ctx, which : typing.Optional[int] = 0):
#     #0 is all, 1 is stats, 2 is moves, 3 is learnables, 4 is habitats
#
#     #stats first
#     errors = []
#     if which in [0,1]:
#         if len(pkmnStats) == 0:
#             await instantiatePkmnStatList()
#         for pokemon, stats in list(pkmnStats.items()):
#             newName = pkmn_cap(pokemon)
#             if pokemon != newName:
#                 errors.append((pokemon, ' stats name mismatch'))
#             try:
#                 await pkmnlearnshelper(newName)
#             except:
#                 errors.append((newName, ' not found stats -> learnables'))
#             #check abilities
#             for x in range(15,18):
#                 if stats[x] != '':
#                     try:
#                         await pkmnabilitieshelper(stats[x])
#                     except:
#                         errors.append((pokemon, f' ability {stats[x]}'))
#
#     #moves next
#     if which in [0,2]:
#         if len(pkmnMoves) == 0:
#             await instantiatePkmnMoveList()
#         for move, info in list(pkmnMoves.items()):
#             if move.title() != move:
#                 errors.append((move, ' move name mismatch'))
#
#     #learnables now
#     if which in [0,3]:
#         if len(pkmnLearns) == 0:
#             await instantiatePkmnLearnsList()
#         for pokemon, stats in list(pkmnLearns.items()):
#             newName = pkmn_cap(pokemon)
#             if pokemon != newName:
#                 errors.append((pokemon, ' learn name mismatch'))
#             try:
#                 await pkmnstatshelper(newName)
#             except:
#                 errors.append((newName, ' not found learnables -> stats'))
#             for move in stats[::2]:
#                 try:
#                     await pkmnmovehelper(move)
#                 except:
#                     errors.append((pokemon, f' move {move} not found'))
#
#     msg = '\n'.join([f'{x} {y}' for x,y in errors if not x.startswith('Delta')])
#     #print(msg)
#     if ctx is not None:
#         await send_big_msg(ctx, msg)
#     else:
#         print(msg)

async def checkFilesExist(filenames: list):
    for file in filenames:
        if not os.path.exists(file):
            return False
    return True


async def init_extra_files():
    print('Downloading missing extra .csv files...')
    for file in extra_files:
        r = requests.get(github_base + file)
        with open(file, 'w', encoding='UTF-8') as f:
            r = r.text.replace('\r\n', '\n')
            f.write(r)
    print('Redownloaded the necessary extra .csv files')


@commands.is_owner()
@bot.command(name='updateLists', hidden=True)
async def reloadLists(ctx):
    global database
    for cog in cogs:
        await bot.unload_extension(cog)

    # Legends Helper is built around a customized local v3.0 dataset. Do not
    # pull pokerole_data from upstream: doing so can replace campaign data and
    # silently undo local patches. Rebuild only the v3
    # SQLite cache from the v3 JSON bundled with this bot.
    database.reloadLists("v3.0")

    for cog in cogs:
        await bot.load_extension(cog)
    await ctx.message.add_reaction('\N{CYCLONE}')


@commands.is_owner()
@bot.command(name='updateSettings', hidden=True)
async def updateSettings(ctx):
    try:
        for place in pokebotsettings:
            await instantiateSettings(place)
    except:
        tmp = traceback.format_exc(limit=3)
        await send_owner_msg(msg=tmp)


@commands.is_owner()
@bot.command(name='devQuery', hidden=True)
async def query(ctx, *, msg=''):
    guild = await getGuilds(ctx)
    version = version_converter[pokebotsettings[guild][11]]
    try:
        if len(msg.split()) == 1:
            returned = database.custom_query(f"PRAGMA table_info({msg})", version=version)
            await ctx.send(', '.join([x[1] for x in returned]))
            return
        elif msg == '':
            returned = database.custom_query(
                'SELECT name FROM sqlite_master WHERE type="table" AND name NOT LIKE "SQLITE_%"', version=version)
            await ctx.send(', '.join([x[0] for x in returned]))
            return
        returned = database.custom_query(msg, version=version)
        if returned is None:
            await ctx.send('Error: no results')
            return
        if len(returned[0]) == 1:
            returned = ', '.join([x[0] for x in returned])
        else:
            returned = ', '.join([f'**{str(x[0])}**: {list(x[1:])}' for x in returned])
        await send_big_msg(ctx, returned)
    except:
        try:
            surplus = returned
        except:
            surplus = ''
        await ctx.send('Error: Bad or Empty Request\n' + str(surplus))


@commands.is_owner()
@bot.command(name='whoLearns', hidden=True)
async def checkLearnables(ctx, *, msg=''):
    move = lookup_move(msg.title())
    query = 'SELECT name FROM pkmnLearns where '
    query += ' or '.join([f'move{x}="{move}"' for x in range(64)])
    guild = await getGuilds(ctx)
    version = version_converter[pokebotsettings[guild][11]]
    returned = database.custom_query(query, version=version)
    if not returned:
        returned = 'None'
    else:
        returned = ', '.join([x[0] for x in returned])
    await send_big_msg(ctx, f'__{move}__:\n{returned}')


#######



@bot.tree.command(
    name='get_pokerole_legends',
    description="Get the latest Pokérole Legends rules, Roll20 sheets, Pokémon PNGs, and more"
)
async def get_pokerole_legends(interaction: discord.Interaction):
    await interaction.response.send_message('https://github.com/lowly-god/Pokerole-Legends/tree/main')

#######
# auto-completes

async def types_autocomplete(
        interaction: discord.Interaction,
        current: str
) -> List[Choice[str]]:
    return [
        app_commands.Choice(name=m_type, value=m_type)
        for m_type in types if current.lower() in m_type.lower()
    ]


async def metronome_type_autocomplete(
        interaction: discord.Interaction,
        current: str
) -> List[Choice[str]]:
    rows = database.custom_query('SELECT DISTINCT type FROM pkmnMoves ORDER BY type', version='v3.0')
    options = [row[0] for row in rows if row and row[0]] + ['Support']
    seen = set()
    filtered = []
    for name in options:
        key = name.casefold()
        if key in seen or current.casefold() not in key:
            continue
        seen.add(key)
        filtered.append(app_commands.Choice(name=name, value=name))
    return filtered[:25]


async def ranks_autocomplete(
        interaction: discord.Interaction,
        current: str
) -> List[Choice[str]]:
    await getGuilds(interaction)
    return [
        app_commands.Choice(name=m_type, value=m_type)
        for m_type in ranks_v3 if current.lower() in m_type.lower()
    ]



async def move_autocomplete(
        interaction: discord.Interaction,
        current: str
) -> List[Choice[str]]:
    if len(current) < 2:
        return {}
    else:
        guild = await getGuilds(interaction)
        version = version_converter[pokebotsettings[guild][11]]
        query = f'SELECT name FROM pkmnMoves WHERE lower(name) LIKE "%{current}%"' \
                f' LIMIT 25'
        result = [x[0] for x in database.custom_query(query, version=version)]

        return [
            app_commands.Choice(name=m_list, value=m_list)
            for m_list in result
        ]

async def item_autocomplete(
        interaction: discord.Interaction,
        current: str
) -> List[Choice[str]]:
    if len(current) < 2:
        return {}
    else:
        guild = await getGuilds(interaction)
        version = version_converter[pokebotsettings[guild][11]]
        query = f'SELECT name FROM pkmnItems WHERE lower(name) LIKE "%{current}%"' \
                f' LIMIT 75'
        result = [
            x[0] for x in database.custom_query(query, version=version)
            if x[0].casefold() not in MOVED_ITEM_LOOKUP_NAMES
        ][:25]
        return [
            app_commands.Choice(name=m_list, value=m_list)
            for m_list in result
        ]

def strip_accents(s):
    return alpha_str.sub("", ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').replace(" ", "-"))

async def pokemon_autocomplete(
        interaction: discord.Interaction,
        current: str
) -> List[Choice[str]]:
    if len(current) < 2:
        return {}
    else:
        guild = await getGuilds(interaction)
        version = version_converter[pokebotsettings[guild][11]]
        query = f'SELECT name FROM pkmnStats WHERE clean_name LIKE "%{strip_accents(current)}%"' \
                f' AND generation BETWEEN 1 AND 10 LIMIT 25'
        result = [x[0] for x in database.custom_query(query, version=version)]
        # LEGENDS_UB_ALIAS_AUTOCOMPLETE
        alias_result = [name for name in POKEMON_ALIASES if current.casefold() in name.casefold()]
        result = list(dict.fromkeys(alias_result + result))[:25]

        return [
            app_commands.Choice(name=m_list, value=m_list)
            for m_list in result
        ]


async def ability_autocomplete(
        interaction: discord.Interaction,
        current: str
) -> List[Choice[str]]:
    if len(current) < 2:
        return {}
    else:
        guild = await getGuilds(interaction)
        version = version_converter[pokebotsettings[guild][11]]
        query = f'SELECT name FROM pkmnAbilities WHERE lower(name) LIKE "%{current}%"' \
                f' LIMIT 25'
        result = [x[0] for x in database.custom_query(query, version=version)]

        return [
            app_commands.Choice(name=m_list, value=m_list)
            for m_list in result
        ]


#######
# for methods that have buttons

class Timeout_View(discord.ui.View):
    async def on_timeout(self) -> None:
        if hasattr(self, "message"):
            await self.message.edit(view=None)


#######

version_converter = ["v3.0", "v3.0"]


# [ability1, ability2, ability3, shiny, show_move_desc, show ability desc, the item list used in encounter,
# display lists pokemon by rank or odds, book version to use]
async def instantiateSettings(where: str):
    # Index 11 is retained only for backwards compatibility with old settings
    # pickles. Legends Helper is v3-only, so it is always pinned to v3 (1).
    defaults = [50, 49, 1, .00012, True, True, False, True, False, 0, False, 1]
    if where not in pokebotsettings:
        pokebotsettings[where] = defaults.copy()
    else:
        size = len(pokebotsettings[where])
        pokebotsettings[where] += defaults[size:]
        pokebotsettings[where][11] = 1
    save_obj(pokebotsettings, 'pokebotsettings')


def print_settings(guild):
    temp = pokebotsettings[guild]
    if temp[9] == 0:
        pre_evo = 'Same Rank'
    elif temp[9] == 1:
        pre_evo = 'No'
    else:
        pre_evo = 'Lower Rank'
    if temp[7]:
        odds = 'Rank'
    else:
        odds = 'Odds'
    version = "v3.0"
    return (f'Current settings:\nPokerole version: **{version}**\n'
            f'(Ability1/Ability2/AbilityHidden)\n**{temp[0], temp[1], temp[2]}**\n'
            f'Shiny chance: {temp[3]} out of 1, **{temp[3] * 100}%**\n'
            f'Allow previous evolution moves in `/encounter_pokemon`? **{pre_evo}**\n'
            f'Display `/encounter_pokemon` text in a code block format: **{temp[10]}\n**'
            f'Show move descriptions in /encounter_pokemon: **{temp[4]}**\n'
            f'Show ability description in /encounter_pokemon: **{temp[5]}**\n'
            f'Items in /encounter_pokemon? **{temp[6]}**\n'
            f'display_list by odds or rank? **{odds}**\n'
            f'arbitrary encounter random_rolls? **{temp[8]}**\n'
            f'\n"/help settings" for help')


@commands.has_permissions(manage_channels=True)
@bot.command(name='settings', aliases=['setting'],
             help='/settings <setting_name> [value]\n'
                  'e.g. /settings ability_one_chance 50\n'
                  'List: (ability_one_chance value)\n'
                  '(ability_two_chance value)\n'
                  '(ability_hidden_chance value)\n'
                  '(shiny_chance value)\n'
                  '(pre_evo_moves Yes/No/Lower)\n'
                  '(code_block True/False)\n'
                  '(show_move_description True/False)\n'
                  '(show_ability_description True/False)\n'
                  '(encounter_item <listname>)\n'
                  '(display_list Rank/Odds)\n'
                  '(random_rolls True/False)')
async def settings(ctx, setting='', value=''):
    msg = ''
    try:
        guild = ctx.guild.id
    except:
        guild = ctx.user.id
    try:
        pokebotsettings[guild]
    except:
        await instantiateSettings(guild)
    try:
        if setting == 'ability_one_chance':
            pokebotsettings[guild][0] = float(value)
        elif setting == 'ability_two_chance':
            pokebotsettings[guild][1] = float(value)
        elif setting == 'ability_hidden_chance':
            pokebotsettings[guild][2] = float(value)
        elif setting == 'shiny_chance':
            pokebotsettings[guild][3] = float(value)
    except:
        await ctx.send(
            'This setting may be any real number, set it to 0 to disable the chance (write it as 50, not 50%)')
    if setting == 'show_move_description' or setting[0:9] == 'show_move':
        if value[0].lower() == 't':
            pokebotsettings[guild][4] = True
        elif value[0].lower() == 'f':
            pokebotsettings[guild][4] = False
        else:
            await ctx.send('Setting "show_move_description" may only be True or False')
    elif setting == 'show_ability_description' or setting == 'show_ability':
        if value[0].lower() == 't':
            pokebotsettings[guild][5] = True
        elif value[0].lower() == 'f':
            pokebotsettings[guild][5] = False
        else:
            await ctx.send('Setting "show_ability_description" may only be True or False')
    elif setting == 'encounter_item' or setting == 'item':
        if value in pkmnLists and pkmnLists[value][0] == 'i':
            pokebotsettings[guild][6] = value
        else:
            pokebotsettings[guild][6] = False
            msg += f'{value} not found in the custom item list. Capitalization matters, is it misspelled?\n' \
                   f'Default set to False (no items).\n'
    elif setting == 'display_list':
        if not value[0].lower() == 'r':  # set it to show odds
            pokebotsettings[guild][7] = False
        else:  # set it to show rank
            pokebotsettings[guild][7] = True
    elif setting == 'random_rolls':
        if value[0].lower() == 't':
            pokebotsettings[guild][8] = True
        elif value[0].lower() == 'f':
            pokebotsettings[guild][8] = False
    elif setting in ['pre_evo_moves', 'pre_evo', 'evo_moves']:
        if value[0].lower() in ['y', 't', 's']:
            pokebotsettings[guild][9] = 0  # new behaviour
        elif value[0].lower() in ['n', 'f', 'd']:
            pokebotsettings[guild][9] = 1  # old behaviour
        elif value[0].lower() == 'l':
            pokebotsettings[guild][9] = 2  # lower rank pre-evo
        else:
            await ctx.send('Setting "pre_evo_moves" may be True, False, or Lower (Rank Pre-Evo Moves)')
    elif setting in ['code', 'block', 'code_block']:
        if value[0].lower() in ['y', 't']:
            pokebotsettings[guild][10] = True
        else:
            pokebotsettings[guild][10] = False
    await ctx.send(msg + print_settings(guild))
    save_obj(pokebotsettings, 'pokebotsettings')


@commands.has_permissions(manage_channels=True)
@app_commands.command(
    name='settings',
    description='Change the settings'
)
@app_commands.describe(
    ability_one_chance="Chance for a generated Pokémon to have its first ability (out of 100 total)",
    ability_two_chance="Chance for a generated Pokémon to have its second ability (out of 100 total)",
    ability_hidden_chance="Chance for a generated Pokémon to have its hidden ability (out of 100 total)",
    shiny_chance="Chance for a generated Pokémon to be shiny (out of 100 total)",
    previous_evolution_moves="Should Pokémon generate with moves from their previous evolutions?",
    code_block_format="Display generated Pokémon in a `code block`?",
    show_move_description="Expand move descriptions by default in generated Pokémon?",
    show_ability_description="Expand ability descriptions by default in generated Pokémon?",
    item_list_in_encounter="Which item list should be used in encounters? (type 'False' to clear)",
    display_lists_by="Choose to display specific lists by Rank or Odds",
    random_rolls_in_encounter="Have 4 suggested rolls for Accuracy and Damage in encounters?"
)
@app_commands.choices(
    # this looks like the wrong order but it's correct
    previous_evolution_moves=[
        Choice(name='Yes', value=0),
        Choice(name='No', value=1),
        Choice(name='Yes, but from 1 rank lower', value=2),
    ],
    code_block_format=[
        Choice(name='Yes', value=1),
        Choice(name='No', value=0),
    ],
    show_move_description=[
        Choice(name='Yes', value=1),
        Choice(name='No', value=0),
    ],
    show_ability_description=[
        Choice(name='Yes', value=1),
        Choice(name='No', value=0),
    ],
    display_lists_by=[
        Choice(name='Rank', value=1),
        Choice(name='Odds', value=0),
    ],
    random_rolls_in_encounter=[
        Choice(name='Yes', value=1),
        Choice(name='No', value=0),
    ]
)
async def settings_slash(
        inter: discord.Interaction,
        ability_one_chance: app_commands.Range[float, 0, 100] = None,
        ability_two_chance: app_commands.Range[float, 0, 100] = None,
        ability_hidden_chance: app_commands.Range[float, 0, 100] = None,
        shiny_chance: app_commands.Range[float, 0, 100] = None,
        previous_evolution_moves: int = None,
        code_block_format: int = None,
        show_move_description: int = None,
        show_ability_description: int = None,
        item_list_in_encounter: str = None,
        display_lists_by: int = None,
        random_rolls_in_encounter: int = None
):
    # ensure the guild id exists
    await getGuilds(inter)
    try:
        guild = inter.guild.id
    except:
        guild = inter.user.id
    if ability_one_chance: pokebotsettings[guild][0] = ability_one_chance
    if ability_two_chance: pokebotsettings[guild][1] = ability_two_chance
    if ability_hidden_chance: pokebotsettings[guild][2] = ability_hidden_chance
    if shiny_chance: pokebotsettings[guild][3] = shiny_chance
    if show_move_description: pokebotsettings[guild][4] = bool(show_move_description)
    if show_ability_description: pokebotsettings[guild][5] = bool(show_ability_description)
    if item_list_in_encounter: pokebotsettings[guild][6] = item_list_in_encounter
    if display_lists_by: pokebotsettings[guild][7] = bool(display_lists_by)
    if random_rolls_in_encounter: pokebotsettings[guild][8] = bool(random_rolls_in_encounter)
    if previous_evolution_moves: pokebotsettings[guild][9] = previous_evolution_moves
    if code_block_format: pokebotsettings[guild][10] = bool(code_block_format)
    pokebotsettings[guild][11] = 1

    await inter.response.send_message(print_settings(guild))
    save_obj(pokebotsettings, 'pokebotsettings')


SLASH_COMMANDS.append(settings_slash)


#######

@commands.is_owner()
@bot.command(name='update_settings', hidden=True)
async def update_settings(ctx):
    for key, val in pokebotsettings.items():
        await instantiateSettings(key)
        for value in range(len(val)):
            pokebotsettings[key][value] = val[value]
    save_obj(pokebotsettings, 'pokebotsettings')
    await ctx.send('Good to go')


# def reformatList(listname):
#     if len(pkmnLists[listname]) == 0:
#         del pkmnLists[listname]
#         return
#     #the first element should be either 'i' or 'p'
#     if pkmnLists[listname][0] not in ['i', 'p']:
#         temp = pkmnLists[listname][:]
#         pkmnLists[listname] = [None, None] #two slots
#         pkmnLists[listname][0] = ('p' if lookup_poke(temp[0]) in pkmnStats else 'i')
#         pkmnLists[listname][1] = [100] + [x for x in temp]
#     #fix directly for item lists, such that
#     #['i', [40, (i1, i2, i3)], [60, (i4, i5, i6)]] --> ['i', [40, i1, i2, i3], ...]
#     if pkmnLists[listname][0] == 'i':
#         for i in range(1,len(pkmnLists[listname][1:])+1):
#             if isinstance(pkmnLists[listname][i][1], str):
#                 continue
#             pkmnLists[listname][i] = [pkmnLists[listname][i][0]] + [x for x in pkmnLists[listname][i][1]]


# @commands.is_owner()
# @bot.command(name = 'update_lists', hidden = True)
# async def update_lists(ctx):
#     if len(pkmnStats) == 0:
#         await instantiatePkmnStatList()
#     for key, val in list(pkmnLists.items()):
#         # print('before: ',key, val)
#         reformatList(key)
#         # if key in pkmnLists:
#         #     print('after: ',key, pkmnLists[key])
#     await ctx.send('Done')
#     save_obj(pkmnLists, 'pkmnLists')

#######

# TODO: re-add 'list access' if anyone complains


    # if len(pkmnLists.keys()) < len(areListsBroken) - 1:
    #    await bot.appinfo.owner.send(f'{listname} {which} {pokelist}')


###

#######

# returns a random Pokémon or item from given list
def pkmn_random_driver(listname: str, giveList=False) -> str:
    if listname not in pkmnLists:
        return 'There was not a list with this name.\n'
    # remove the leading 'i' or 'p'
    temp = pkmnLists[listname][1:]
    which = 0
    rand = random.randrange(1, 101) - int(temp[0][0])
    while rand > 0 and which < len(temp):
        which += 1
        if which == len(temp):
            # if the list is 80% pokemon/items, 20% nothing
            return 'None'
        rand -= int(temp[which][0])
    if giveList:
        return temp[which][1:]  # remove the percentage
    else:
        return random.choice(temp[which][1:])


#######

#######

async def pkmnitemhelper(item, version: str):
    global database
    try:
        return list(database.query_table('pkmnItems', 'name', item, version=version)[0])[2:]
    except:
        raise KeyError(f'{item} wasn\'t recognized as an item.')


@bot.hybrid_command(name='item', aliases=['items', 'i'], description="Display an Item's traits and price. Use %item for categories.", help="Display an Item's traits and price. Use %item for categories.")
@app_commands.autocomplete(itemname=item_autocomplete)
async def pkmn_search_item(ctx, itemname: str = ''):
    global database
    guild = await getGuilds(ctx)
    version = version_converter[pokebotsettings[guild][11]]
    itemname = pkmn_cap(itemname)
    if itemname != '':
        folded_item = itemname.casefold()
        if folded_item in ACCESSORY_LOOKUP_NAMES:
            await ctx.send(f'{itemname} has moved to `/accessory`.')
            return
        if folded_item in TOOL_LOOKUP_NAMES or folded_item == 'tools':
            await ctx.send(f'{itemname} has moved to `/tools`.')
            return
        try:
            found = await pkmnitemhelper(itemname, version=version)
        except:
            await ctx.send(f'{itemname} wasn\'t found in the item list.')
            return
        try:
            output = f'__{itemname}__\n'

            if found[0] != '':
                order = ['Description', 'For Types', 'For Pokémon', 'Boost', 'Value', 'Cures', 'Consumable',
                         'Health Restored', 'Trainer Price', 'PMD Price']
                # this is an actual item
                # Preserve the authored capitalization of item effect text and do not italicize it.
                output += f'{found[0]}\n'
                for name in range(1, len(order)):
                    if found[name] != '' and found[name] is not None:
                        value = found[name]
                        # Trainer prices are stored as numeric data; add the Pokédollar symbol for display.
                        if order[name] == 'Trainer Price' and str(value).strip().isdigit():
                            value = f'₽{str(value).strip()}'
                        output += f'**{order[name]}**: {value}\n'
            else:
                # this is a category
                temp = database.custom_query(f'SELECT name FROM pkmnItems WHERE category="{itemname}"')
                temp = [x[0] for x in temp if x[0].casefold() not in MOVED_ITEM_LOOKUP_NAMES]
                for x in temp:
                    output += f' - {x}\n'
            await ctx.send(output)
        except:
            await ctx.send(f'{itemname} wasn\'t found in the item list.\n*Unknown Error Occurred?*')
    else:
        await ctx.send(
            'To look up an item; autocomplete will suggest valid names.\n'
            'Human equipment references are split into `/weapon`, `/armor`, `/accessory`, and `/tools`.'
        )


# SLASH_COMMANDS.append(pkmn_search_item)

#######


async def pkmnDictRanks(pokemon: list, version: str) -> dict:
    level = dict()
    for poke in pokemon:
        try:
            rank = (await pkmnstatshelper(poke, version=version))[20]
        except:
            try:
                # its either nidoran or oricorio or wormadam
                # try the cleaned search first
                tmppoke = random.choice(database.clean_query(poke, version=version))
                rank = (await pkmnstatshelper(tmppoke, version=version))[20]
            except:
                try:
                    #then check pokelists
                    tmppoke = random.choice(random.choice(pkmnLists[poke.lower()][1:])[1:])
                    rank = (await pkmnstatshelper(tmppoke, version=version))[20]
                except:
                    pass
        if rank not in level:
            level[rank] = []
        level[rank].append(poke)
    return level


async def pkmnRankDisplay(title: str, pokemon: typing.Union[list, dict], version: str) -> str:
    if isinstance(pokemon, list):
        pokemon = await pkmnDictRanks(pokemon, version=version)
    output = title + '\n'
    for rank in ranks_v3:
        if rank in pokemon:
            output += f'**{rank}**\n{"  |  ".join(pokemon[rank])}\n'
    return output



#######

async def pkmnabilitieshelper(ability, version: str):
    global database
    try:
        return list(database.query_table('pkmnAbilities', 'name', ability, version=version)[0])[1:]
    except:
        raise KeyError(f'{ability} wasn\'t recognized as an ability.')


@bot.command(name='ability', aliases=['a'], help="Display an Ability's traits")
async def pkmn_search_ability(ctx, *, abilityname: pkmn_cap):
    guild = await getGuilds(ctx)
    version = version_converter[pokebotsettings[guild][11]]
    try:
        try:
            found = await pkmnabilitieshelper(abilityname, version=version)
        except:
            abilityname = lookup_ability(abilityname)
            found = await pkmnabilitieshelper(abilityname, version=version)

        output = f'**{abilityname}:** {found[0]}'
        if found[1] != '':
            output += f'\n*{found[1]}*'

        await ctx.send(output)
    except:
        await ctx.send(f'{abilityname} wasn\'t found in the ability list.')


@app_commands.command(
    name='ability',
    description="Display an Ability's traits"
)
@app_commands.describe(ability="Which ability?")
@app_commands.autocomplete(ability=ability_autocomplete)
async def pkmn_search_ability(inter, *, ability: str):
    ability = pkmn_cap(ability)
    guild = await getGuilds(inter)
    version = version_converter[pokebotsettings[guild][11]]
    try:
        try:
            found = await pkmnabilitieshelper(ability, version=version)
        except:
            ability = lookup_ability(ability)
            found = await pkmnabilitieshelper(ability, version=version)

        output = f'**{ability}:** {found[0]}'
        if found[1] != '':
            output += f'\n*{found[1]}*'

        await inter.response.send_message(output)
    except:
        await inter.response.send_message(f'{ability} wasn\'t found in the ability list.')


SLASH_COMMANDS.append(pkmn_search_ability)


#######

async def pkmnmovehelper(move, version: str):
    global database
    found = list(database.query_table('pkmnMoves', 'name', move, version=version)[0])[1:]

    # v3 move data sometimes uses "Physical" as the Damage1 label.
    # In Legends, physical damage uses Strength; Special is already correct.
    # Normalize it here so /move and every other move consumer use Strength.
    if found[3] and str(found[3]).strip().lower() == "physical":
        found[3] = "Strength"

    return found


async def move_backend(movename, version: str):
    try:
        movename = movename.title()
        try:
            found = await pkmnmovehelper(movename, version=version)
        except:
            movename = lookup_move(movename)
            found = await pkmnmovehelper(movename, version=version)

        output = f'__{movename}__\n'
        if not found[4]:  # there is no second damage mod, use the power
            pwr2 = f' + {found[2]}' if found[2] != 0 else ''
        else:  # use the damage mod
            pwr2 = f' + {found[4]}'
        if found[9] != "":
            output += f'*{found[9]}*\n'
        output += f'**Type**: {found[0].capitalize()}'
        output += f' -- **{found[1].capitalize()}**\n'
        output += f'**Target**: {found[7]}'
        output += f' -- **Power**: {found[2]}\n'
        output += f'**Damage Dice**: {(found[3] or "None")}{pwr2}\n'
        output += f'**Accuracy Dice**: {(found[5] or "None")} + {(found[6] or "None")}\n'
        output += f'**Effect**: {found[8]}'

        return output
    except:
        return f'{movename} wasn\'t found in the move list.'


@bot.command(name='move', aliases=['m'], help="Display a Pokémon Move's traits")
async def pkmn_search_move(ctx, *, movename: pkmn_cap):
    guild = await getGuilds(ctx)
    version = version_converter[pokebotsettings[guild][11]]
    await ctx.send(await move_backend(movename, version=version))


@app_commands.command(
    name='move',
    description="Display a Pokémon Move's traits"
)
@app_commands.describe(move="Which move?")
@app_commands.autocomplete(move=move_autocomplete)
async def pkmn_search_move_slash(inter, *, move: str):
    move = pkmn_cap(move)
    guild = await getGuilds(inter)
    version = version_converter[pokebotsettings[guild][11]]
    await inter.response.send_message(await move_backend(move, version=version))


SLASH_COMMANDS.append(pkmn_search_move_slash)


async def metronome_backend(type, lower, higher, version: str, exclude_silly: bool = False):
    clauses = []
    params = []

    def _as_int(value):
        if value is None or value == '':
            return None
        return int(value)

    lower = _as_int(lower)
    higher = _as_int(higher)
    if lower is not None and higher is not None and lower > higher:
        lower, higher = higher, lower

    if lower is not None and higher is not None:
        clauses.append('power BETWEEN ? AND ?')
        params.extend([lower, higher])
    elif lower is not None:
        clauses.append('power = ?')
        params.append(lower)
    elif higher is not None:
        # max_power by itself really is a maximum, not an exact power.
        clauses.append('power <= ?')
        params.append(higher)

    if type:
        requested = str(type).strip()
        if requested.casefold() == 'support':
            clauses.append('LOWER(pwrtype) LIKE ?')
            params.append('%support%')
        else:
            clauses.append('LOWER(type) = ?')
            params.append(requested.casefold())

    if exclude_silly:
        clauses.append('LOWER(type) != ?')
        params.append('shadow')
        if METRONOME_SILLY_EXCLUDED_MOVES:
            placeholders = ','.join('?' for _ in METRONOME_SILLY_EXCLUDED_MOVES)
            clauses.append(f'name NOT IN ({placeholders})')
            params.extend(sorted(METRONOME_SILLY_EXCLUDED_MOVES))

    query = 'SELECT name FROM pkmnMoves'
    if clauses:
        query += ' WHERE ' + ' AND '.join(clauses)
    query += ' ORDER BY RANDOM() LIMIT 1'
    result = database.custom_query(query, version=version, params=params)
    return result[0][0] if result else None


@bot.command(name='metronome' ,
             aliases=['mtr'],
             help="""
             Simulates a random move. Comes with options to limit the scope.
             
             %metronome
                Randomly select any move.
             
             %metronome 1
                Select any move with power 1.
             
             %metronome 2<5
                Any move between power 2 and 5 (inclusive)
             
             %metronome dragon
                Any dragon type move. `support` instead of a type would give a random support move.""")
async def metronome(ctx, *, parameters: str = ''):
    guild = await getGuilds(ctx)
    version = version_converter[pokebotsettings[guild][11]]
    parameters = parameters.replace(' ', '')
    power = None
    max_power = None
    if parameters == '':
        pass
    elif '<' in parameters:
        tmp = parameters.split('<')
        power = tmp[0]
        max_power = tmp[1]
    elif parameters.isdigit():
        power = parameters
    type = None if (parameters == '' or parameters.isdigit() or '<' in parameters) else parameters
    move = await metronome_backend(type=type, lower=power, higher=max_power, version=version)

    try:
        if move is None:
            raise LookupError('No matching move')
        await pkmn_search_move(ctx=ctx, movename=move)
    except Exception:
        await ctx.send(
            f'`{parameters}` was not recognized as a valid type (grass, water, etc) or power level (1, 2, 3 < 5, etc).\n'
            f'*(This message self-destructs in 15 seconds)*',
            delete_after=15)


@app_commands.command(
    name='metronome',
    description='Get a random Move from a list of all Moves (with a few options)'
)
@app_commands.describe(
    move_type="Want a specific move typing?",
    power="Power for the move? (exact if max_power isn't provided, inclusive otherwise)",
    max_power="Maximum power on a move? (inclusive)",
    private="Display the Move in a private message? (Default: False)",
    exclude_silly="Exclude Shadow-Type Moves, Moves with the Unique keyword, and Z-Moves? (Default: No)"
)
@app_commands.choices(
    private=[
        Choice(name='Yes', value=1),
        Choice(name='No', value=0),
    ],
    exclude_silly=[
        Choice(name='Yes', value=1),
        Choice(name='No', value=0),
    ]
)
@app_commands.autocomplete(move_type=metronome_type_autocomplete)
async def metronome_slash(
        inter,
        move_type: str = None,
        power: app_commands.Range[int, 0, 10] = None,
        max_power: app_commands.Range[int, 0, 10] = None,
        private: int = 0,
        exclude_silly: int = 0):
    private = bool(private)
    exclude_silly = bool(exclude_silly)
    guild = await getGuilds(inter)
    version = version_converter[pokebotsettings[guild][11]]
    if power is not None and max_power is not None and power > max_power:
        power, max_power = max_power, power
    move = await metronome_backend(type=move_type, lower=power, higher=max_power, version=version, exclude_silly=exclude_silly)
    if move is None:
        filters = []
        if move_type:
            filters.append(f'type `{move_type}`')
        if power is not None and max_power is not None:
            filters.append(f'Power {power}-{max_power}')
        elif power is not None:
            filters.append(f'Power {power}')
        elif max_power is not None:
            filters.append(f'Power ≤ {max_power}')
        detail = ' with ' + ' and '.join(filters) if filters else ''
        await inter.response.send_message(f'No moves were found{detail}.', ephemeral=True)
        return
    move_text = await move_backend(movename=move, version=version)
    await inter.response.send_message(move_text, ephemeral=private)


SLASH_COMMANDS.append(metronome_slash)


#####

async def pkmnstatshelper(poke: str, version: str):
    global database
    poke = resolve_pokemon_alias(poke)
    try:
        tmp = list(database.query_table('pkmnStats', 'name', poke, version=version)[0])
    except:
        raise KeyError(poke)
    tmp = [f'#{tmp[0]}'] + tmp[3:]
    return tmp


async def pkmn_stat_msg_helper(pokemon, found, version: str):
    pokemon = resolve_pokemon_alias(pokemon)
    for x in range(4, 14, 2):
        found[x + 1] = "⭘" * (int(found[x + 1]) - int(found[x]))
        found[x] = "⬤" * int(found[x])

    output = f'{found[0]} __{pokemon.title()}__\n'
    output += f'**Suggested Rank**: {found[20]}\n'
    output += f'**Type**: {found[1].capitalize()}'
    if found[2] == '':
        output += '\n'
    else:
        output += f' / {found[2].capitalize()}\n'
    output += pokemon_extra_stats_text(pokemon, found[1], found[2], version)
    exStats = [f'`({len(found[x])}/{len(found[x]) + len(found[x + 1])})`' for x in range(4, 14, 2)]
    output += f'**Base HP**: {found[3]}\n'
    output += f'**Strength**: {found[4]}{found[5]} {exStats[0]}\n'
    output += f'**Dexterity**: {found[6]}{found[7]} {exStats[1]}\n'
    output += f'**Vitality**: {found[8]}{found[9]} {exStats[2]}\n'
    output += f'**Special**: {found[10]}{found[11]} {exStats[3]}\n'
    output += f'**Insight**: {found[12]}{found[13]} {exStats[4]}\n'
    output += f'**Ability**: {found[14]}'
    if found[15] != '':  # secondary
        output += f' / {found[15]}'
    if found[16] != '':  # hidden
        output += f' ({found[16]})'
    if found[17] != '':  # event
        output += f' <{found[17]}>'
    output += '\n'
    output += f'**Can Evolve**: {"Yes" if str(found[18]) == "1" else "No"}\n'
    output += f'**Other Forms**: {(found[19] or "No")}\n'

    buttons = Timeout_View()

    b_moves = Button(
        style=discord.ButtonStyle.blurple,
        label='Moves'
    )

    async def on_move_button(inter):
        moves = await pkmnlearnshelper(pokemon, version=version)

        output = f'__{pokemon.title()}__\n'
        for x in moves.keys():
            output += f'**{x}**\n' + '  |  '.join(moves[x]) + '\n'
        output += _machine_moves_text(pokemon)

        b_moves.disabled = True
        await inter.response.edit_message(view=buttons)
        for chunk in _split_pokelearns_text(output):
            await inter.followup.send(chunk)

    b_moves.callback = on_move_button
    buttons.add_item(b_moves)

    b_abilities = Button(
        style=discord.ButtonStyle.green,
        label='Abilities'
    )

    async def on_ability_button(inter):
        b_abilities.disabled = True
        await inter.response.edit_message(view=buttons)
        await inter.followup.send(await getPokemonAbilities(pokemon, version=version))

    b_abilities.callback = on_ability_button
    buttons.add_item(b_abilities)

    b_forms = Button(
        style=discord.ButtonStyle.gray,
        label='Forms'
    )

    async def on_form_button(inter):
        b_forms.disabled = True
        await inter.response.edit_message(view=buttons)
        output = await form_helper(pokemon, version=version)
        if '\n' in output:
            await inter.followup.send(await form_helper(pokemon, version=version))

    b_forms.callback = on_form_button
    buttons.add_item(b_forms)

    return output, buttons


@bot.command(name='stats', aliases=['s', 'info'], help='List a Pokémon\'s stats. '
                                                       'Emote on the message to expand the abilities!')
async def pkmn_search_stats(ctx, *, pokemon: pkmn_cap):
    guild = await getGuilds(ctx)
    version = version_converter[pokebotsettings[guild][11]]
    try:
        found = (await pkmnstatshelper(pokemon, version=version))[:]
    except:
        pokemon = lookup_poke(pokemon)
        found = (await pkmnstatshelper(pokemon, version=version))[:]
    output, buttons = await pkmn_stat_msg_helper(pokemon, found, version=version)

    buttons.message = await ctx.send(output, view=buttons)


@app_commands.command(
    name='stats',
    description="Display a Pokémon's stats"
)
@app_commands.describe(pokemon="Which Pokémon?")
@app_commands.autocomplete(pokemon=pokemon_autocomplete)
async def pkmn_search_stats_slash(inter, *, pokemon: str):
    pokemon = pkmn_cap(pokemon)
    guild = await getGuilds(inter)
    version = version_converter[pokebotsettings[guild][11]]
    try:
        found = (await pkmnstatshelper(pokemon, version=version))[:]
    except:
        pokemon = lookup_poke(pokemon)
        found = (await pkmnstatshelper(pokemon, version=version))[:]
    output, buttons = await pkmn_stat_msg_helper(pokemon, found, version=version)

    await inter.response.send_message(output, view=buttons)
    buttons.message = await inter.original_response()


SLASH_COMMANDS.append(pkmn_search_stats_slash)


#####

def _split_pokelearns_text(text, limit=1900):
    if len(text) <= limit:
        return [text]
    chunks = []
    current = ""
    for line in text.splitlines(True):
        if len(current) + len(line) <= limit:
            current += line
            continue
        if current:
            chunks.append(current.rstrip())
            current = ""
        # Move-list lines can themselves be very long; split on the normal separator.
        if len(line) > limit and "  |  " in line:
            parts = line.strip().split("  |  ")
            for part in parts:
                addition = part if not current else "  |  " + part
                if len(current) + len(addition) > limit:
                    chunks.append(current.rstrip())
                    current = part
                else:
                    current += addition
            current += "\n"
        else:
            current = line
    if current:
        chunks.append(current.rstrip())
    return chunks


def _machine_moves_text(pokemon):
    try:
        return machine_moves_section(resolve_pokemon_alias(pokemon))
    except Exception as exc:
        print(f"Could not build TM/TR/HM section for {pokemon}: {exc}")
        return ""


async def pkmnlearnshelper(poke: str, rank: ensure_rank = 'Master', version: str = "v3.0"):
    global database
    poke = resolve_pokemon_alias(poke)
    which_ranks = ranks_v3
    try:
        found = list(database.query_table('pkmnLearns', 'name', poke, version=version)[0][2:])
    except (IndexError, TypeError):
        raise KeyError(poke)
    # truncate the list to just the valid members
    try:
        found = found[:found.index(None)]
    except:
        pass
    # works if the ranks are 'starter', etc, or numbers
    try:
        found[1::2] = [which_ranks[x] for x in found[1::2]]
    except:
        pass
    done = False
    moves = dict()
    for x in range(0, len(found), 2):
        if done:
            break
        if found[x + 1] not in moves:
            if rank == 'Master' or which_ranks.index(found[x + 1]) <= which_ranks.index(rank):
                moves[found[x + 1]] = [found[x]]
            else:
                done = True
        else:
            moves[found[x + 1]].append(found[x])
    return moves


# returns the moves of a pokemon + all it's devolutions
async def move_aggregator_tmp(poke: str, rank: str, denote_moves: bool = False, version: str = "v3.0") -> dict:
    poke = resolve_pokemon_alias(poke)
    movelist = {}  # init final dict
    allPokes = [poke]
    result = False
    depth = -1
    while result is not None:
        query = f'SELECT previous FROM pkmnEvo WHERE name="{allPokes[-1]}"'
        result = database.custom_query(query, multiple=False, version=version)
        if result:
            allPokes.append(result[0])
    for pkmn in allPokes:
        depth += 1
        tmp = await pkmnlearnshelper(pkmn, rank)
        for x, y in list(tmp.items()):
            if x in movelist:
                for name in y:
                    if denote_moves and depth != 0 and name not in movelist[x]:
                        movelist[x].add(r'\*' + name)
                    else:
                        movelist[x].add(name)
            else:
                if denote_moves and depth != 0:
                    movelist[x] = set([r'\*' + z for z in y])
                else:
                    movelist[x] = set(y)
    return movelist


@bot.command(name='poke_learns',
             aliases=['canlearn', 'pl', 'moves', 'learnset'],
             help='Display the Moves a Pokémon can learn')
async def pkmn_search_learns(ctx, *, pokemon: pkmn_cap):
    # known moves is insight + 2
    guild = await getGuilds(ctx)
    version = version_converter[pokebotsettings[guild][11]]
    try:
        try:
            moves = await pkmnlearnshelper(pokemon, version=version)
        except:
            pokemon = lookup_poke(pokemon)
            moves = await pkmnlearnshelper(pokemon, version=version)
        output = f'__{pokemon.title()}__\n'

        for x in moves.keys():
            output += f'**{x}**\n' + '  |  '.join(moves[x]) + '\n'
        output += _machine_moves_text(pokemon)

        for chunk in _split_pokelearns_text(output):
            await ctx.send(chunk)

        # TODO: add a select menu for the ranks?
        # when they select a rank, add another select menu for specific moves from the message?
        # should be relatively easy with a .replace('*'), .split('\n'), .index(rank), (rank+1).split(' | ')
        #   could probably store the moves in the custom_id for quick lookup ngl
        #
        # this one sends a message for the move and stores the follow-up's message id.
        #
        # future move lookups would edit the followup message, with an extra newline between moves.


    except:
        msg = f'{pokemon} wasn\'t found in the pokeLearns list.'
        if pokemon in pkmnLists:
            msg += '\nDid you mean: ' + ', '.join(pkmnLists[pokemon]) + '?'
        await ctx.send(msg)


@app_commands.command(
    name='poke_learns',
    description='Display the Moves a Pokémon can learn'
)
@app_commands.describe(
    pokemon="Which Pokémon?",
    previous_evo_moves="Show moves from previous evolutions?"
)
@app_commands.choices(
    previous_evo_moves=[
        Choice(name='Yes', value=1),
        Choice(name='No', value=0),
    ]
)
@app_commands.autocomplete(pokemon=pokemon_autocomplete)
async def pkmn_search_learns_slash(inter, *, pokemon: str, previous_evo_moves: int = 0):
    # Acknowledge the slash command immediately. Machine/Tutor data may need
    # to populate its cache from the web, which can exceed Discord's ~3 second
    # initial interaction-response window.
    await inter.response.defer()

    previous_evo_moves = bool(previous_evo_moves)
    # known moves is insight + 2
    pokemon = pkmn_cap(pokemon)
    guild = await getGuilds(inter)
    version = version_converter[pokebotsettings[guild][11]]
    try:
        try:
            if not previous_evo_moves:
                moves = await pkmnlearnshelper(pokemon, version=version)
            else:
                moves = await move_aggregator_tmp(pokemon, 'Master', denote_moves=previous_evo_moves, version=version)
        except:
            pokemon = lookup_poke(pokemon)
            if not previous_evo_moves:
                moves = await pkmnlearnshelper(pokemon, version=version)
            else:
                moves = await move_aggregator_tmp(pokemon, 'Master', denote_moves=previous_evo_moves, version=version)

        output = f'__{pokemon.title()}__\n'

        for x in moves.keys():
            output += f'**{x}**\n' + '  |  '.join(moves[x]) + '\n'

        # machine_moves_section may fetch/refresh its Showdown cache.
        # Run that synchronous work in a thread so the Discord event loop
        # remains responsive to other commands.
        output += await asyncio.to_thread(_machine_moves_text, pokemon)

        chunks = _split_pokelearns_text(output)
        for chunk in chunks:
            await inter.followup.send(chunk)

    except Exception:
        traceback.print_exc()
        msg = f'{pokemon} wasn\'t found in the pokeLearns list.'
        if pokemon in pkmnLists:
            msg += '\nDid you mean: ' + ', '.join(pkmnLists[pokemon]) + '?'
        await inter.followup.send(msg)


SLASH_COMMANDS.append(pkmn_search_learns_slash)


#####

# returns the moves of a pokemon + all it's devolutions
async def move_aggregator(poke: str, rank: str, version: str) -> dict:
    movelist = {}  # init final dict
    allPokes = [poke]
    result = False
    while result is not None:
        query = f'SELECT previous FROM pkmnEvo WHERE name="{allPokes[-1]}"'
        result = database.custom_query(query, multiple=False, version=version)
        if result:
            allPokes.append(result[0])
    for pkmn in allPokes:
        tmp = await pkmnlearnshelper(pkmn, rank, version=version)
        for x, y in list(tmp.items()):
            if x in movelist:
                for name in y:
                    movelist[x].add(name)
            else:
                movelist[x] = set(y)
    return movelist


async def calcStats(rank: str, attr: list, maxAttr: list,
                    movelist=None, additionalIns: int = 0,
                    additionalVit: int = 0, version: str = version_converter[0]) -> (list, list, list, int):
    """Allocate encounter stats using the exact cumulative rank progression.

    v3 uses cumulative Main/Social bonuses of 0/2/4/6/8/10/11/12 and
    cumulative Skill Points of 5/10/14/17/19/21/23/25. Skill points are
    applied rank-by-rank so each step obeys that rank's Skill Limit.
    """
    if movelist is None:
        movelist = {}

    rank_index = ranks_v3.index(rank)
    rank_names = ranks_v3
    attribute_amounts = attributeAmount_v3
    skill_amounts = skillAmount_v3
    skill_limits = limit_v3
    bias_amt = rankBias_v3[rank_index]
    extra_social = 0

    bhp = int(attr[0])
    attributes = [int(value) for value in attr[1:]]
    base_attributes = list(attributes)
    maxattr = [int(value) for value in maxAttr[1:]]
    socials = [(name, int(value)) for name, value in bot.socials]
    skills = [(name, int(value)) for name, value in bot.skills]

    additionalIns = max(0, int(additionalIns or 0))
    additionalVit = max(0, int(additionalVit or 0))
    if additionalVit and len(attributes) > 2:
        allowed_vit = max(0, maxattr[2] - attributes[2])
        applied_vit = min(additionalVit, allowed_vit)
        attributes[2] += applied_vit
        additionalVit = applied_vit

    attr_names = ['STRENGTH', 'DEXTERITY', 'VITALITY', 'SPECIAL', 'INSIGHT']
    social_names = ['TOUGH', 'COOL', 'BEAUTY', 'CLEVER', 'CUTE']
    skill_names = [name.upper() for name, _ in skills]

    attr_weights = [1.0] * len(attributes)
    social_weights = [1.0] * len(socials)
    # Preserve the original encounter preference for core combat skills and
    # Alert, while the new Aura/Luck/Empathy skills remain valid candidates.
    skill_weights = [float(max(1, bias_amt // 2)) if i < 5 else 1.0 for i in range(len(skills))]

    def _contains_token(value, token):
        text = str(value or '').upper()
        return token in re.split(r'[^A-Z]+', text)

    if movelist:
        # Smart-stat encounters reserve any already-selected extra Insight for
        # their move count and allocate the remaining Main points elsewhere.
        if len(attr_weights) > 2:
            attr_weights[2] += bias_amt * 2

        for _, desc in list(movelist.items()):
            try:
                fields = list(desc)
            except TypeError:
                continue

            # Damage/Accuracy fields can contain alternatives (e.g.
            # Strength / Special), so inspect tokens rather than exact strings.
            for field_index in (3, 4, 5):
                if field_index >= len(fields):
                    continue
                value = fields[field_index]
                for idx, name in enumerate(attr_names):
                    if idx < len(attr_weights) and _contains_token(value, name):
                        attr_weights[idx] += bias_amt
                for idx, name in enumerate(social_names):
                    if _contains_token(value, name):
                        social_weights[idx] += bias_amt

            if len(fields) > 6:
                value = fields[6]
                for idx, name in enumerate(skill_names):
                    if _contains_token(value, name):
                        skill_weights[idx] += bias_amt

    # Main Attributes. Human/Pokémon rank-up bonuses are cumulative; for smart
    # stats, Insight already spent on the selected move count is reserved here.
    main_total = attribute_amounts[rank_index]
    reserved = additionalVit + (additionalIns if movelist else 0)
    points_remaining = max(0, main_total - reserved)
    active_indices = list(range(len(attributes)))
    if movelist and len(active_indices) >= 5:
        active_indices = active_indices[:-1]  # selected moves already fixed Insight

    while points_remaining > 0:
        candidates = [i for i in active_indices if attributes[i] < maxattr[i]]
        if not candidates:
            break
        chosen = random.choices(candidates, weights=[max(0.01, attr_weights[i]) for i in candidates], k=1)[0]
        attributes[chosen] += 1
        points_remaining -= 1
    leftover = points_remaining

    # Social Attributes use the same cumulative rank bonus as Main Attributes.
    # They are not constrained by the Skill Limit; their ordinary cap is 5.
    social_points = attribute_amounts[rank_index] + extra_social
    while social_points > 0:
        candidates = [i for i, (_, value) in enumerate(socials) if value < 5]
        if not candidates:
            break
        chosen = random.choices(candidates, weights=[max(0.01, social_weights[i]) for i in candidates], k=1)[0]
        name, value = socials[chosen]
        socials[chosen] = (name, value + 1)
        social_points -= 1

    # Build minimum Evasion/Clash targets from the Pokémon's natural stat
    # profile. Fast/dexterous Pokémon almost always cap Evasion; strong, bulky
    # or slow Pokémon almost always cap Clash. Everyone else still gets a
    # useful 1-2 point floor where the current rank's Skill Limit permits it.
    final_skill_limit = skill_limits[rank_index]
    str_base = base_attributes[0] if len(base_attributes) > 0 else 0
    dex_base = base_attributes[1] if len(base_attributes) > 1 else 0
    vit_base = base_attributes[2] if len(base_attributes) > 2 else 0
    str_cap = maxattr[0] if len(maxattr) > 0 else str_base
    dex_cap = maxattr[1] if len(maxattr) > 1 else dex_base
    vit_cap = maxattr[2] if len(maxattr) > 2 else vit_base

    dexterous_profile = (
        dex_base >= max(str_base, vit_base)
        or dex_cap >= max(str_cap, vit_cap) + 1
    )
    clash_profile = (
        str_base >= dex_base + 1
        or vit_base >= dex_base + 1
        or str_cap >= dex_cap + 1
        or vit_cap >= dex_cap + 1
        or bhp >= 6
    )

    def _ordinary_skill_floor():
        if final_skill_limit <= 1:
            return final_skill_limit
        return 2 if random.random() < 0.85 else 1

    evasion_target = _ordinary_skill_floor()
    if dexterous_profile and final_skill_limit > 0:
        evasion_target = (
            final_skill_limit if random.random() < 0.90
            else max(evasion_target, final_skill_limit - 1)
        )

    clash_target = _ordinary_skill_floor()
    if clash_profile and final_skill_limit > 0:
        clash_target = (
            final_skill_limit if random.random() < 0.90
            else max(clash_target, final_skill_limit - 1)
        )

    skill_index = {name.upper(): i for i, (name, _) in enumerate(skills)}
    priority_targets = {}
    if 'EVASION' in skill_index:
        priority_targets[skill_index['EVASION']] = evasion_target
    if 'CLASH' in skill_index:
        priority_targets[skill_index['CLASH']] = clash_target

    # Skill Points must be gained in rank order so Starter's 5 points obey
    # Limit 1, Rookie's next 5 obey Limit 2, and so on. Priority skills reserve
    # their points first at each newly unlocked limit, then the ordinary smart
    # weighted spread spends the remainder. Exact totals are preserved.
    previous_total = 0
    for step_index in range(rank_index + 1):
        step_total = skill_amounts[step_index]
        gain = step_total - previous_total
        previous_total = step_total
        step_limit = skill_limits[step_index]

        for skill_i, final_target in priority_targets.items():
            name, value = skills[skill_i]
            required_now = max(0, min(final_target, step_limit) - value)
            reserved = min(gain, required_now)
            if reserved:
                skills[skill_i] = (name, value + reserved)
                gain -= reserved

        for _ in range(gain):
            candidates = [i for i, (_, value) in enumerate(skills) if value < step_limit]
            if not candidates:
                raise RuntimeError(
                    f'Unable to allocate all skill points for {rank_names[step_index]}'
                )
            chosen = random.choices(
                candidates,
                weights=[max(0.01, skill_weights[i]) for i in candidates],
                k=1,
            )[0]
            name, value = skills[chosen]
            skills[chosen] = (name, value + 1)

    if sum(value for _, value in skills) != skill_amounts[rank_index]:
        raise RuntimeError(
            f'Pokémon skill allocation mismatch for {rank}: '
            f'{sum(value for _, value in skills)} != {skill_amounts[rank_index]}'
        )

    return [bhp] + attributes, socials, skills, leftover


async def pkmn_encounter(ctx, number: int, rank: str, pokelist: list,
                         exact_rank: bool = False, boss: bool = False, guild=None,
                         condense=False, version_override=None):
    if guild is None:
        guild = await getGuilds(ctx)
    view_buttons = []
    msg = ''
    rankrandom = False
    rankbase = False
    # rank = rank.title()
    if rank == 'Random':
        rank = random.choice(ranks_v3)
        rankrandom = True
    if rank == 'Base':
        rankbase = True

    # Legends Helper is v3-only; keep version_override for compatibility with existing callers.
    version = 'v3.0'
    which_ranks = ranks_v3
    base_num_moves = num_moves_v3


    tempList = []
    for name in pokelist:
        name = name.strip()
        if name in pkmnLists:
            y = pkmn_random_driver(name, giveList=True)
            if y == 'None' or y == ['None']:
                return '...but nothing was there. *(Rolled an empty %)*\n'
            for poke in y:
                tempList.append(poke)
        else:
            tempList.append(name)
            # pokelist = [x.strip().title() for x in pokelist.split(',')]
            # if len(pokelist)==1:
            #    pokelist = [x.strip().title() for x in pokelist[0].split(' ')]
    pokelist = [pkmn_cap(item) for item in tempList]
    random.shuffle(pokelist)

    if number > 6:
        msg += 'Can only create up to 6 pokes at once due to size\n'
        number = 6
    elif number < 1:
        number = 1

    if len(pokelist) == 0:
        return 'Need at least one Pokémon in the list!'

    # exceptions for master rank: 6 extra social, HP + 2, DEF/S.DEF + 2

    for pokeamount in range(number):
        if not exact_rank:
            # get a poke from the list
            nextpoke = random.choice(pokelist)
            # get the attributes
            try:
                statlist = await pkmnstatshelper(nextpoke, version=version)
            except:
                # name is a typo
                nextpoke = lookup_poke(nextpoke)
                statlist = await pkmnstatshelper(nextpoke, version=version)
            if rankbase:
                # 20 is suggested rank
                rank = statlist[20].title()
        else:
            foundrank = None
            nextpoke = None
            while len(pokelist) > 1 and foundrank != rank:
                if nextpoke:
                    pokelist.remove(nextpoke)
                # get a poke from the list
                nextpoke = random.choice(pokelist)
                # get the attributes
                try:
                    statlist = await pkmnstatshelper(nextpoke, version=version)
                except:
                    # name is a typo
                    nextpoke = lookup_poke(nextpoke)
                    statlist = await pkmnstatshelper(nextpoke, version=version)
                foundrank = statlist[20].title()

        # to differentiate between naturally learned moves at an evolution
        naturalMoves = await pkmnlearnshelper(nextpoke, rank, version=version)
        # get all potential moves, up to the rank
        try:  # does the setting exist...
            setting = pokebotsettings[guild][9]
        except:
            await instantiateSettings(guild)
            setting = pokebotsettings[guild][9]
        if setting == 0:  # all moves at rank from poke and pre evos
            movelist = await move_aggregator(nextpoke, rank, version=version)
        if setting == 1:  # previous behaviour
            movelist = naturalMoves.copy()
        elif setting == 2:  # previous evos at lower rank
            newrank = which_ranks.index(rank.title())
            if newrank != 0:
                newrank -= 1
            newrank = which_ranks[newrank]
            movelist = await move_aggregator(nextpoke, newrank, version=version)
        naturalMoves = [item for sublist in list(naturalMoves.values()) for item in sublist]

        # 3/4/6/8/10/12 == b.hp/str/dex/vit/spe/ins
        attributes = [int(statlist[3])] + [int(statlist[x]) for x in range(4, 13, 2)]

        baseattr = [x for x in attributes]
        maxattr = [0] + [int(statlist[x]) for x in range(5, 14, 2)]

        # numVitality = 0
        if boss:  # we need insight for # of moves
            attrNum = len(baseattr)
            numMoves = baseattr[5]
            rank_attribute_amounts = attributeAmount_v3
            for _ in range(rank_attribute_amounts[which_ranks.index(rank.title())]):
                randnum = random.random()
                # if randnum < 1/(attrNum*2) and baseattr[3] + numVitality < maxattr[3]: #chance for vitality
                #     numVitality += 1
                #     continue
                if randnum < 1 / attrNum:  # chance for insight
                    numMoves += 1
                if numMoves == maxattr[5]:
                    break
            numMoves += base_num_moves
        else:  # generate stats randomly
            attributes, socials, skills, _ = await calcStats(rank, attributes, maxattr, version=version)
            numMoves = attributes[5] + base_num_moves  # insight + 2 (or 3 if in v3)

        # todo: guarantee a (attacking?) move from the pokemon's rank

        # cut the movelist down to this number
        newMoves = []
        # flatten, then convert to a set and back to remove duplicates
        movelist = list(set([item for sublist in list(movelist.values()) for item in set(sublist)]))
        for _ in range(numMoves):
            if len(movelist) == 0:  # usually legendaries
                break
            temp = random.choice(movelist)
            newMoves.append(temp)
            movelist.remove(temp)

        move_descs = {}
        for move in newMoves:
            move_descs[move] = await pkmnmovehelper(move, version=version)

        if boss:  # allocate stats since we didn't before (and adjust insight accordingly)
            insightAdded = numMoves - base_num_moves - baseattr[5]
            attributes, socials, skills, leftover = await calcStats(rank, baseattr, maxattr,
                                                                    move_descs, insightAdded,
                                                                    version=version)  # , numVitality)
            attributes[5] += insightAdded
            lowerBound = maxattr[5] - attributes[5]
            extraPoints = min(leftover, lowerBound)
            attributes[5] += extraPoints

            for _ in range(extraPoints):  # repeated loop, yeah, yeah, i know
                if len(movelist) == 0:
                    break
                temp = random.choice(movelist)
                newMoves.append(temp)
                movelist.remove(temp)
                move_descs[temp] = await pkmnmovehelper(temp, version=version)
        movelist = newMoves

        # base 14, second 15, hidden 16, event 17
        totalchance = pokebotsettings[guild][0] + pokebotsettings[guild][1] + pokebotsettings[guild][2]
        if totalchance <= 0:
            # If every chance setting is zero, safely fall back to the primary Ability.
            ability = statlist[14]
            randomnum = None
        else:
            randomnum = random.random()
        if totalchance > 0 and pokebotsettings[guild][2] / totalchance >= randomnum and statlist[16] != '':
            # hidden, succeeded the low roll
            ability = statlist[16]
        elif totalchance > 0 and pokebotsettings[guild][1] / totalchance >= randomnum and statlist[15] != '':
            # secondary, failed the hidden
            ability = statlist[15]
        else:
            # basic, failed the other checks
            ability = statlist[14]

        if pokebotsettings[guild][6] != False:
            item = pkmn_random_driver(pokebotsettings[guild][6])
        else:
            item = 'None'
        # calculate hp (base hp + vitality)
        attributes[0] = attributes[0] + attributes[3]

        # combine all the info into a dict()

        allAttr = {'STRENGTH': attributes[1], 'DEXTERITY': attributes[2], 'VITALITY': attributes[3],
                   'SPECIAL': attributes[4], 'INSIGHT': attributes[5], '': 0, None: 0, 'WILL': 0,
                   'MISSING HAPPINESS': 0, 'MISING BEAUTY': 0, 'HAPPINESS': 0}
        for skill in skills:
            allAttr.update({skill[0].upper(): skill[1]})
        for social in socials:
            allAttr.update({social[0].upper(): social[1]})

        abilitytext = ''
        if pokebotsettings[guild][5]:
            try:
                abilitytext = await pkmnabilitieshelper(ability, version=version)
            except:
                pass

        # then combine it into a msg

        gender = statlist[21]
        if gender == '':
            gender = 'M' if random.random() < .5 else 'F'

        # if there's only one pokemon generated then skip this
        if number != 1:
            msg += f'**{pokeamount + 1}**.\n\n'
        msg += f'__{nextpoke}__' \
               f' ({gender})' \
               f'  |  **{rank}**'
        msg += f'  |  {random.choice(natures)}'
        msg += (f'  |  ***SHINY***' if pokebotsettings[guild][3] >= random.random() else f'')

        msg += f'\n**Type**: {statlist[1]}{"" if statlist[2] == "" else "/" + statlist[2]}\n'

        # ability
        msg += f'**Ability:** {ability}\n'

        # item
        if pokebotsettings[guild][6]:
            msg += f'**Item:** {item}\n'

        # ⬤⦿⭘
        just = 0
        fullattr = [0]
        totalNums = [0]
        for attr in range(1, len(attributes)):
            a = int(baseattr[attr])
            b = int(attributes[attr])
            c = int(maxattr[attr])
            if c > just:
                just = c
            baseattr[attr] = '⬤' * a
            attributes[attr] = '⦿' * (b - a)
            maxattr[attr] = '⭘' * (c - b)
            totalNums.append(f' `({b}/{c})`')
            fullattr.append(baseattr[attr] + attributes[attr] + maxattr[attr])
            d = int(socials[attr - 1][1])
            socials[attr - 1] = (socials[attr - 1][0], '⬤' * d + '⭘' * (5 - d))
        just += 12
        bonus_hp = 2 if rank == ['Master', 'Champion'] else 0
        msg += f'**Total HP:** {attributes[0]}'
        if bonus_hp > 0:
            msg += f' + {bonus_hp} (Master Rank)'
        msg += '\n'
        msg += ('**Str:** ' + fullattr[1] + totalNums[1]).ljust(just) + f' -- **{socials[0][0]}:**  {socials[0][1]}\n'
        msg += ('**Dex:** ' + fullattr[2] + totalNums[2]).ljust(just) + f' -- **{socials[1][0]}:**  {socials[1][1]}\n'
        msg += ('**Vit:** ' + fullattr[3] + totalNums[3]).ljust(just) + f' -- **{socials[2][0]}:**  {socials[2][1]}\n'
        msg += ('**Spe:** ' + fullattr[4] + totalNums[4]).ljust(just) + f' -- **{socials[3][0]}:**  {socials[3][1]}\n'
        msg += ('**Ins:** ' + fullattr[5] + totalNums[5]).ljust(just) + f' -- **{socials[4][0]}:**  {socials[4][1]}\n'

        msg += '\n'

        # Display every encounter skill. v3 Legends adds Aura, Luck and
        # Empathy to the usual Pokémon encounter skill list.
        for x in range(0, len(skills), 4):
            row = skills[x:x + 4]
            for y, skill in enumerate(row):
                msg += f'**{skill[0]}:**'.ljust(11) + ' ' + str(skill[1]) + (' - ' if y != len(row) - 1 else '')
            msg += '\n'

        enc_view = Timeout_View()

        if not condense:
            if pokebotsettings[guild][5] and abilitytext != '':
                msg += f'\n**{ability}**: {abilitytext[0]}\n'
                if abilitytext[1] != '':
                    msg += f'*{abilitytext[1]}*\n'
        else:
            enc_abilities = Button(
                style=discord.ButtonStyle.blurple,
                label=ability,
                custom_id=f'ability({ability})'
            )

            async def on_enc_ability_button(inter):
                enc_abilities.disabled = True
                await inter.response.edit_message(view=enc_view)
                ablty = await pkmnabilitieshelper(ability, version=version)
                tmp_msg = f'**{ability}:** {abilitytext[0]}\n*{abilitytext[1]}*'
                await inter.followup.send(tmp_msg)

            enc_abilities.callback = on_enc_ability_button
            enc_view.add_item(enc_abilities)

        if item != 'None':
            try:
                temp = await pkmnitemhelper(item, version=version)
                msg += f'**{item}**: {temp[0]}\n'
            except:
                msg += f'**{item}**: ???\n'

        msg += '\n*Moves*:\n'

        if pokebotsettings[guild][4]:
            # add the moves + their desc
            for x in movelist:
                if not condense:
                    try:
                        # found = await pkmnmovehelper(x)
                        found = move_descs[x]
                        if found[8][-9:-1] == 'Accuracy':
                            try:
                                accMod = int(found[8][-11])
                            except:
                                accMod = 0
                        else:
                            accMod = 0
                        # todo: differentiate between damaging STAB, non-damaging STAB, and add + after the STAB dmg array
                        if x.title() not in naturalMoves:
                            msg += '*'
                        if found[4]:
                            powermod2 = f' + {found[4]}'
                        else:
                            powermod2 = ''
                        msg += f'__{x.title()}__\n'
                        if found[9] != "":
                            msg += f'*{found[9]}*\n'
                        msg += f'**Type**: {found[0].capitalize()}'
                        msg += f' -- **{found[1].capitalize()}**\n'
                        msg += f'**Target**: {found[7]}'
                        msg += f' -- **Power**: {found[2]}\n'
                        numRolls = 4

                        try:
                            dmgBase = allAttr[found[3].upper()] if found[3].upper() in allAttr else 0
                            if '/' in found[3]:
                                splitfirst = found[3][:found[3].index("/")].upper()
                                tmp1 = allAttr[splitfirst] if splitfirst in allAttr else 0
                                splitsecond = found[3][found[3].index("/")+1:].upper()
                                tmp2 = allAttr[splitsecond] if splitsecond in allAttr else 0
                                dmgBase = tmp1 if tmp1 >= tmp2 else tmp2

                            dmgBase2 = allAttr[found[4].upper()] if found[4].upper() in allAttr else 0
                            if '/' in found[4]:
                                splitfirst = found[4][:found[4].index("/")].upper()
                                tmp3 = allAttr[splitfirst] if splitfirst in allAttr else 0
                                splitsecond = found[4][found[4].index("/")+1:].upper()
                                tmp4 = allAttr[splitsecond] if splitsecond in allAttr else 0
                                dmgBase2 = tmp3 if tmp3 >= tmp4 else tmp4

                            totalDmg = dmgBase + dmgBase2 + int(found[2])
                            dmgArray = [sum([random.randint(0, 1) for _ in range(totalDmg)]) for _ in range(numRolls)]
                        except:
                            totalDmg = 0
                            dmgArray = ''
                        try:
                            accBase = allAttr[found[5].upper()] if found[5].upper() in allAttr else 0
                            if '/' in found[5]:
                                splitfirst = found[5][:found[5].index("/")].upper()
                                tmp1 = allAttr[splitfirst] if splitfirst in allAttr else 0
                                splitsecond = found[5][found[5].index("/")+1:].upper()
                                tmp2 = allAttr[splitsecond] if splitsecond in allAttr else 0
                                accBase = tmp1 if tmp1 >= tmp2 else tmp2

                            accBase2 = allAttr[found[6].upper()] if found[6].upper() in allAttr else 0
                            if '/' in found[6]:
                                splitfirst = found[6][:found[6].index("/")].upper()
                                tmp1 = allAttr[splitfirst] if splitfirst in allAttr else 0
                                splitsecond = found[6][found[6].index("/")+1:].upper()
                                tmp2 = allAttr[splitsecond] if splitsecond in allAttr else 0
                                accBase2 = tmp1 if tmp1 >= tmp2 else tmp2

                            totalAcc = accBase + accBase2
                            accArray = [sum([random.randint(0, 1) for _ in range(totalAcc)]) - accMod for _ in
                                        range(numRolls)]
                        except:
                            totalAcc = 0
                            accArray = ''

                        if found[1].capitalize() != 'Support':
                            msg += f'**Dmg Dice**: {(found[3] or "None")}{powermod2}' \
                                   f' + {found[2]} = {totalDmg}'
                            msg += f'{" (+1 STAB)" if found[0].capitalize() in (statlist[1], statlist[2]) else ""}'
                            msg += f' {dmgArray}\n' if pokebotsettings[guild][8] else '\n'
                        else:
                            msg += f'**Dmg Dice**: None\n'
                        msg += f'**Acc Dice**: {(found[5] or "None")} + {(found[6] or "None")} = '
                        try:
                            msg += f'{totalAcc}'
                            msg += f" - {accMod} Successes" if accMod != 0 else ""
                        except:
                            msg += '???'
                        msg += f' {accArray}\n' if pokebotsettings[guild][8] else '\n'
                        msg += f'**Effect**: {found[8]}\n\n'
                    except:
                        msg += f'__{x.title()}__\n\n'
                else:  # elif condense
                    found = move_descs[x]
                    # Focus Energy - Normal/Support/Self
                    msg += f'**{x.title()}** - {found[0].title()}/{found[1].title()}/{found[7]}\n'

                    if found[8][-9:-1] == 'Accuracy':
                        try:
                            accTmp = int(found[8][-11])
                            accMod = f' (-{accTmp} Success'
                            if accTmp != 1:
                                accMod += 'es)'
                            else:
                                accMod += ')'
                        except:
                            accMod = ''
                    else:
                        accMod = ''
                    stab = f'{" (+1 STAB)" if found[0].capitalize() in (statlist[1], statlist[2]) else ""}'
                    def _pool_value(field):
                        field = str(field or '').strip()
                        if not field:
                            return 0
                        values = []
                        for token in field.split('/'):
                            values.append(allAttr.get(token.strip().upper(), 0))
                        return max(values) if values else 0

                    try:
                        totalDmg = str(_pool_value(found[3]) + _pool_value(found[4]) + int(found[2]))
                    except Exception:
                        totalDmg = None
                    try:
                        totalAcc = str(_pool_value(found[5]) + _pool_value(found[6]))
                    except Exception:
                        totalAcc = "???"
                    # A: 4 (-2 Successes) | D: 6 (+1 STAB)
                    if totalDmg:
                        msg += f'A: {totalAcc}{accMod} | D: {totalDmg}{stab}\n'
                    else:
                        msg += f'A: {totalAcc}{accMod}\n'

                    # (effect text here)
                    msg += found[8] + '\n\n'

                    class Move_Button(ui.Button):
                        def __init__(self, acc='???', dmg='', **kwargs):
                            super().__init__(**kwargs)
                            self.acc = f' = {acc}'
                            if dmg not in ('' or '0'):
                                self.dmg = f' = {dmg}'
                            else:
                                self.dmg = ''

                        async def getMove(self):
                            tmp_move = await move_backend(self.label.title(), version=version)
                            final_move = ''

                            dmg_at = tmp_move.find('Damage')
                            dmg_at = tmp_move.find('\n', dmg_at + 1)
                            final_move += tmp_move[:dmg_at]
                            final_move += self.dmg

                            acc_at = tmp_move.find('Accuracy')
                            acc_at = tmp_move.find('\n', acc_at + 1)
                            final_move += tmp_move[dmg_at:acc_at]
                            final_move += self.acc

                            final_move += tmp_move[acc_at:]

                            return final_move

                        async def callback(self, inter):
                            self.disabled = True
                            await inter.response.edit_message(view=enc_view)
                            await inter.followup.send(await self.getMove())

                    # create and add the button
                    enc_move = Move_Button(
                        style=discord.ButtonStyle.green,
                        label=x.title(),
                        acc=f'{totalAcc}{accMod}',
                        dmg=f'{totalDmg}{stab}' if totalDmg and found[1].title() != "Support" else ''
                    )

                    # view_buttons.append(enc_move)
                    enc_view.add_item(enc_move)
        else:
            for x in movelist:
                msg += f'__{x.title()}__\n'
    # for button in view_buttons:
    #     enc_view.add_item(button)

    if condense:
        return msg, enc_view
    else:
        return msg


#####

async def pkmn_search_encounter(ctx, number: typing.Optional[int] = 1,
                                numberMax: typing.Optional[int] = None,
                                rank: typing.Optional[ensure_rank] = 'Base',
                                *, pokelist: (lambda x: x.split(', ')),
                                boss=False, condense=False,
                                version_override=None):
    guild = await getGuilds(ctx)
    if numberMax is not None:
        number = random.randint(number, numberMax)
    if condense:
        msg, view = await pkmn_encounter(
            ctx, number, rank, pokelist, boss=boss, guild=guild,
            condense=True, version_override=version_override
        )
    else:
        msg = await pkmn_encounter(
            ctx, number, rank, pokelist, boss=boss, guild=guild,
            version_override=version_override
        )
        view = None
    codify = bool(pokebotsettings[guild][10])
    await send_big_msg(ctx, msg, codify=codify, view=view)




@app_commands.command(
    name='encounter_pokemon',
    description='Generate one or more Pokémon'
)
@app_commands.describe(
    pokemon="Which Pokémon? Leave blank for a random Pokémon at the selected rank.",
    number="How many? (up to 6)",
    rank="What rank? (Default: No change)",
    condense_info="Condense ability and moves for a smaller message",
    smart_stats="Use the improved stat distribution? (Default: True)"
)
@app_commands.choices(
    smart_stats=[
        Choice(name='Yes', value=1),
        Choice(name='No', value=0),
    ],
    condense_info=[
        Choice(name='Yes', value=1),
        Choice(name='No', value=0),
    ]
)
@app_commands.autocomplete(pokemon=pokemon_autocomplete, rank=ranks_autocomplete)
async def smart_pkmn_search_slash(inter,
                                  number: app_commands.Range[int, 1, 6] = 1,
                                  rank: str = 'Base',
                                  condense_info: int = 0,
                                  smart_stats: int = 1,
                                  *, pokemon: str = ''):
    smart_stats = bool(smart_stats)
    condense_info = bool(condense_info)
    guild = await getGuilds(inter)
    version = version_converter[pokebotsettings[guild][11]]
    codify = bool(pokebotsettings[guild][10])

    if pokemon == '':
        if rank == 'Base':
            rank = rank_dist(version=version)
        elif rank == 'Champion':
            await inter.response.send_message(
                'Since there are no Pokémon who naturally have the Champion rank, '
                'a random Pokémon cannot be generated from this pool.',
                ephemeral=True
            )
            return

        query = (
            f'SELECT name FROM pkmnStats WHERE rank="{rank}" '
            f'AND generation BETWEEN 1 AND 10 ORDER BY RANDOM() LIMIT {number}'
        )
        results = database.custom_query(query, version=version)
        if not results:
            await inter.response.send_message(
                f'No {rank} Pokémon were found.', ephemeral=True
            )
            return

        msg = ''
        view = None
        for count, (pkm,) in enumerate(results):
            if count:
                msg += f'\t**{count + 1}**\n\n'
            if condense_info:
                tmp_msg, view = await pkmn_encounter(
                    ctx=inter, number=1, rank=rank.title(), pokelist=[pkm],
                    boss=smart_stats, guild=guild, condense=True
                )
                msg += tmp_msg
            else:
                msg += await pkmn_encounter(
                    ctx=inter, number=1, rank=rank.title(), pokelist=[pkm],
                    boss=smart_stats, guild=guild
                )
        await send_big_msg(ctx=inter, arg=msg, codify=codify, view=view)
        return

    await pkmn_search_encounter(
        ctx=inter, number=number, numberMax=number, rank=rank.title(),
        pokelist=pokemon.split(', '), boss=smart_stats, condense=condense_info
    )

    #     on_click = img_msg.create_click_listener(timeout = 300)
    #
    #     @on_click.matching_id('moves')
    #     async def on_button(inter):
    #         moveset = ''
    #         for mv in moves:
    #             moveset += await move_backend(mv) + '\n\n'
    #         await img_msg.edit(view = None)
    #         await img_msg.response.send_message(content = moveset)


SLASH_COMMANDS.append(smart_pkmn_search_slash)



async def encounter_biome_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete all biome names; Discord only permits 25 results at once."""
    def search_key(value):
        # Treat spaces, hyphens and underscores as cosmetic so searches such as
        # "sub tropical" still match "Subtropical Forest".
        return re.sub(r'[\s_-]+', '', value.casefold().strip())

    current_key = search_key(current)
    names = list(encounter_biomes)
    if current_key:
        names = [name for name in names if current_key in search_key(name)]
        names.sort(key=lambda name: (not search_key(name).startswith(current_key), name.casefold()))
    else:
        # Discord shows at most 25 autocomplete results. Keep the two Islas
        # biomes and AREA UNKNOWN visible in the initial picker, then fill the
        # remaining slots alphabetically.
        priority = ['Subtropical Forest', 'Volcanic', 'AREA UNKNOWN']
        names = [name for name in priority if name in encounter_biomes] + sorted(
            [name for name in names if name not in priority], key=str.casefold
        )
    return [Choice(name=name, value=name) for name in names[:25]]


async def send_named_pool_encounter(inter, pool, rank, condense_info=0, smart_stats=1,
                                    search_label='area'):
    """Roll one Pokémon from a named pool and use the normal v3 encounter generator."""
    if not pool:
        await inter.response.send_message(
            f'No Pokémon are configured for {search_label}.', ephemeral=True
        )
        return

    smart_stats = bool(smart_stats)
    condense_info = bool(condense_info)
    guild = await getGuilds(inter)
    codify = bool(pokebotsettings[guild][10])
    pkm = random.choice(pool)
    view = None

    if condense_info:
        msg, view = await pkmn_encounter(
            ctx=inter, number=1, rank=rank.title(), pokelist=[pkm],
            boss=smart_stats, guild=guild, condense=True, version_override='v3.0'
        )
    else:
        msg = await pkmn_encounter(
            ctx=inter, number=1, rank=rank.title(), pokelist=[pkm],
            boss=smart_stats, guild=guild, version_override='v3.0'
        )

    await send_big_msg(ctx=inter, arg=msg, codify=codify, view=view)



@app_commands.command(
    name='encounter_biome',
    description='Generate a Pokémon from a specific biome'
)
@app_commands.describe(
    biome='Which biome?',
    rank='What rank?',
    condense_info='Condense ability and moves for a smaller message',
    smart_stats='Use the improved stat distribution? (Default: True)'
)
@app_commands.choices(
    rank=[Choice(name=x, value=x) for x in ranks_v3],
    smart_stats=[Choice(name='Yes', value=1), Choice(name='No', value=0)],
    condense_info=[Choice(name='Yes', value=1), Choice(name='No', value=0)]
)
@app_commands.autocomplete(biome=encounter_biome_autocomplete)
async def smart_biome_search_slash(inter,
                                   biome: str,
                                   rank: str,
                                   condense_info: int = 0,
                                   smart_stats: int = 1):
    pool = encounter_biomes.get(biome)
    if pool is None:
        await inter.response.send_message('That biome was not found.', ephemeral=True)
        return
    await send_named_pool_encounter(
        inter, pool, rank, condense_info, smart_stats,
        search_label=f'the {biome} biome'
    )



SLASH_COMMANDS.append(smart_biome_search_slash)

@app_commands.command(
    name='encounter_region',
    description='Generate a Pokémon from a specific region'
)
@app_commands.describe(
    region="Which region?",
    rank="What rank? (Default: No change)",
    smart_stats="Use the improved stat distribution? (Default: True)"
)
@app_commands.choices(
    region=[Choice(name=x, value=x) for x in regions],
    rank=[Choice(name=x, value=x) for x in ["Base"] + ranks_v3],
    smart_stats=[
        Choice(name='Yes', value=1),
        Choice(name='No', value=0),
    ]
)
async def smart_region_search_slash(inter,
                                    region: str,
                                    rank: str = 'Base',
                                    smart_stats: int = 1):
    if region in custom_region_pools:
        await send_named_pool_encounter(
            inter, custom_region_pools[region], rank,
            0, smart_stats, search_label=region
        )
        return

    number = 1
    smart_stats = bool(smart_stats)
    guild = await getGuilds(inter)
    version = version_converter[pokebotsettings[guild][11]]
    codify = bool(pokebotsettings[guild][10])

    if rank == 'Base':
        rank = rank_dist(version=version)
    elif rank == 'Champion':
        await inter.response.send_message(
            'Since there are no Pokémon who naturally have the Champion rank, '
            'a random Pokémon cannot be generated from this pool.',
            ephemeral=True
        )
        return

    region_number = base_regions.index(region) + 1
    query = (
        f'SELECT name FROM pkmnStats WHERE rank="{rank}" '
        f'AND generation="{region_number}" ORDER BY RANDOM() LIMIT {number}'
    )
    result = database.custom_query(query, version=version)
    if not result:
        await inter.response.send_message(
            f'No {rank} Pokémon were found for {region}.', ephemeral=True
        )
        return
    pkm = result[0][0]

    msg = await pkmn_encounter(
        ctx=inter, number=1, rank=rank.title(), pokelist=[pkm],
        boss=smart_stats, guild=guild
    )
    await send_big_msg(ctx=inter, arg=msg, codify=codify)


SLASH_COMMANDS.append(smart_region_search_slash)


#####

async def form_helper(name, version: str):
    query = f'SELECT name FROM pkmnStats WHERE name LIKE "%{name}%" ' \
            f'AND generation BETWEEN 1 AND 10'
    result = database.custom_query(query, version=version)
    if len(result) > 20:
        msg = f'Too many results with `{name}`. Try a longer string?'
    elif len(result) == 0:
        msg = f'No Pokémon with `{name}` were found. Try a shorter string?'
    else:
        msg = '- ' + '\n- '.join([x[0] for x in result])
    return msg



#####

#####

FEEDBACK_OWNER_ID = 360919685887164428
FEEDBACK_OWNER_NAME = "xx_lowly_xx"


class Feedback_Modal(ui.Modal):
    def __init__(self, reply_func: discord.Interaction.response, title="???"):
        super().__init__(title=title)
        self.reply_func = reply_func

    text = ui.TextInput(label="Response")

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        update_message = "~~" + interaction.message.content + "~~"
        await interaction.response.edit_message(content=update_message, view=None)
        await self.reply_func(f"*{self.title}...*\n{FEEDBACK_OWNER_NAME}: " + self.children[0].value)


class Feedback_Button(ui.View):
    def __init__(self, send_modal):
        super().__init__(timeout=None)
        self.modal = send_modal

    @ui.button(label="Click to respond", style=discord.ButtonStyle.green)
    async def butn(self, interaction, button):
        await interaction.response.send_modal(self.modal)


@bot.hybrid_command(name='feedback',
                    aliases=['fb', 'report', 'typo', 'bug'],
                    description='Send feedback, suggestions or bug reports straight to my creator',
                    help='Send feedback, suggestions or bug reports straight to my creator')
# @app_commands.command(name = 'feedback')
async def feedback(ctx: discord.Interaction, *, info: str):
    reply_func = None
    which_user = "???: "
    if hasattr(ctx.interaction, "response"):
        await ctx.interaction.response.send_message('Feedback received, thank you!')
        reply_func = ctx.interaction.followup.send
        which_user = ctx.interaction.user.name
    else:
        await ctx.message.add_reaction('\N{HIBISCUS}')
        reply_func = ctx.reply
        which_user = ctx.author.name
    modal = Feedback_Modal(reply_func=reply_func, title=info[:45])
    butn = Feedback_Button(send_modal=modal)
    feedback_owner = await bot.fetch_user(FEEDBACK_OWNER_ID)
    await feedback_owner.send(which_user + ": " + info, view=butn)


@bot.hybrid_command(name='donate', description='Show your love and support', help='Show your love and support')
async def donate(ctx):
    link = r'https://ko-fi.com/lowlygod'
    await ctx.send(link)


@bot.hybrid_command(name='invite', aliases=['inv'], description='Get an invite link for the bot', help='Get an invite link for the bot')
async def invite(ctx):
    link = r'https://discord.com/oauth2/authorize?client_id=1536204111723241472'
    await ctx.send(link)


#####

# error handling:



if not dev_env:
    @bot.event
    async def on_command_error(ctx, error):
        global restartError
        msg = f"Error:\n{str(error)}\n*(This message self-destructs in 15 seconds)*"
        if restartError:
            msg += f'\n*Restarting... please give me a minute*'
        await ctx.send(msg, delete_after=15)

# if not dev_env:
#     @bot.event
#     async def on_raw_reaction_add(payload):
#         user = payload.user_id
#         if user == bot.user.id:
#             return
#         channel = await bot.fetch_channel(payload.channel_id)
#         message = await channel.fetch_message(payload.message_id)
#         if len(message.reactions) != 1 or message.reactions[0].count != 1:
#             return
#         if message.author != bot.user or message.content[0] != '#':
#             return
#         msg = message.content
#         try:
#             pkmn = msg[7:msg.find('\n')-2]
#             query = f'SELECT ability, ability2, abilityhidden, abilityevent FROM pkmnStats WHERE name="{pkmn}"'
#             query = database.custom_query(query)[0]
#             ability = list(query)
#             while '' in ability:
#                 ability.remove('')
#             ability_expanded = [(await pkmnabilitieshelper(x)) for x in ability]
#
#             output = ''
#             for name, (effect, desc) in zip(ability, ability_expanded):
#                 output += f'**{name}:** {effect}\n'
#                 if desc != "":
#                     output += f'*{desc}*\n'
#                 output += '\n'
#
#             await channel.send(output[:-2]) #-2 to remove the trailing \n 's
#
#         except:
#             pass

#####

# for cog in cogs:
#     await bot.load_extension(cog)

# todo: add all slash commands? or like at least test them
#   omit the guild parameter for global sync
# tree.add_command( CMD() )
# await tree.sync( guild = discord.Object( id = GUILD_ID) )

bot.big_msg = send_big_msg
bot.dictionary = lookup_poke
bot.rank_dist = rank_dist

bot.run(token)