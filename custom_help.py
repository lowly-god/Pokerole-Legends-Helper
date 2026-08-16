from discord.ext import commands
from discord import app_commands


CATEGORY_ORDER = {
    'Pokémon Reference': [
        'stats', 'pokelearns', 'move', 'ability', 'item', 'status', 'weather',
        'nature', 'effect', 'metronome', 'habitat', 'forms'
    ],
    'Legends Reference': [
        'rankup', 'perk', 'weapon', 'maneuver', 'armor', 'accessories', 'tools',
        'fieldtype', 'encountertable', 'foraging', 'training', 'crafting'
    ],
    'Encounters & NPCs': [
        'encounter', 'encounter_biome', 'encounter_region', 'encounter_human',
        'human_npc', 'quest'
    ],
    'Shops': ['shop', 'rollshop'],
    'Utilities': [
        'roll', 'rollnature', 'settings', 'feedback', 'docs', 'donate', 'invite',
        'getpokerolelegends'
    ],
}


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _walk_app_commands(self):
        """Yield current application commands, including commands added after this cog loads."""
        def recurse(commands_in):
            for command in commands_in:
                if isinstance(command, app_commands.Group):
                    yield from recurse(command.commands)
                else:
                    yield command
        yield from recurse(self.bot.tree.get_commands())

    def _command_map(self):
        result = {}
        # Prefix/hybrid commands are useful as a fallback for commands that do not
        # have a standalone app-command object.
        for command in self.bot.walk_commands():
            if command.hidden:
                continue
            result.setdefault(command.name.casefold(), command)
        # Prefer the slash-command definition when both exist.
        for command in self._walk_app_commands():
            result[command.name.casefold()] = command
        return result

    @staticmethod
    def _description(command):
        if isinstance(command, app_commands.Command):
            return (command.description or 'No description.').strip()
        text = command.brief or command.help or 'No description.'
        return text.strip().splitlines()[0]

    @staticmethod
    def _signature(command):
        if isinstance(command, app_commands.Command):
            pieces = [f'/{command.name}']
            for param in command.parameters:
                token = f'<{param.name}>' if param.required else f'[{param.name}]'
                pieces.append(token)
            return ' '.join(pieces)

        pieces = [f'/{command.name}']
        for name, param in command.clean_params.items():
            if param.default is param.empty:
                pieces.append(f'<{name}>')
            else:
                pieces.append(f'[{name}]')
        return ' '.join(pieces)

    async def _send_chunks(self, ctx, text):
        while text:
            if len(text) <= 1950:
                await ctx.send(text)
                return
            split = text.rfind('\n', 0, 1950)
            if split < 1:
                split = 1950
            await ctx.send(text[:split])
            text = text[split:].lstrip('\n')

    @commands.hybrid_command(name='help', description='Show the bot command list or help for one command.')
    async def help(self, ctx, *, which: str = None):
        commands_now = self._command_map()

        if which:
            key = which.strip().lstrip('/%').casefold()
            command = commands_now.get(key)
            if command is None:
                await ctx.send(f'`{which}` is not a current command. Use `/help` to see the command list.')
                return
            await self._send_chunks(
                ctx,
                f'**{self._signature(command)}**\n{self._description(command)}'
            )
            return

        used = set()
        sections = []
        for category, names in CATEGORY_ORDER.items():
            rows = []
            for name in names:
                command = commands_now.get(name.casefold())
                if command is None:
                    continue
                used.add(name.casefold())
                rows.append(f'`/{command.name}` — {self._description(command)}')
            if rows:
                sections.append(f'**{category}**\n' + '\n'.join(rows))

        # Never let a newly added public command disappear from help simply because
        # the category table has not been updated yet.
        other = []
        for key, command in sorted(commands_now.items(), key=lambda item: item[0]):
            if key in used or key == 'help':
                continue
            other.append(f'`/{command.name}` — {self._description(command)}')
        if other:
            sections.append('**Other Commands**\n' + '\n'.join(other))

        await self._send_chunks(
            ctx,
            '\n\n'.join(sections) + '\n\nUse `/help <command>` for details.'
        )


async def setup(bot):
    bot.remove_command('help')
    await bot.add_cog(Help(bot))
