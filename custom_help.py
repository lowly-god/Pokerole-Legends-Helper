from discord.ext import commands
from discord import app_commands


HELP_CATEGORIES = [
    ("Pokémon Reference", [
        ("stats", "Display a Pokémon's stats"),
        ("poke_learns", "Display the Moves a Pokémon can learn"),
        ("move", "Display a Pokémon Move's traits"),
        ("ability", "Display an Ability's traits"),
        ("metronome", "Get a random Move from a list of all Moves (with a few options)"),
    ]),
    ("Human Reference", [
        ("perk", "Display a human Perk's traits"),
        ("weapon", "Display a Weapon or Combat Skill and its Maneuvers"),
        ("maneuver", "Display an individual human Maneuver"),
        ("armor", "Display an Armor's traits and its Maneuver if relevant"),
        ("accessory", "Display an Accessory's traits and Maneuver if relevant"),
        ("tools", "Display a Tool and its traits"),
    ]),
    ("General Reference", [
        ("rank_up", "Display Rank-Up requirements and benefits."),
        ("nature", "Display information about a Nature"),
        ("status", "Display information about a Status Condition"),
        ("weather", "Display information about a Weather-Type"),
        ("terrain", "Display information about a Terrain-Type"),
        ("field_type", "Display the effects of a Field-Type"),
        ("item", "Display an Item's traits and price. Use %item for categories."),
        ("effect", "Display information about common effects or terms"),
        ("training_rules", "Display Pokémon Training rules, Training Point costs and rewards"),
        ("crafting_pokeballs", "Display Poké Ball crafting rules and recipes"),
        ("crafting_healing_items", "Display Healing Item crafting rules and recipes"),
        ("cooking", "Display Cooking rules and recipes"),
        ("catching_rules", "Display rules for catching wild Pokémon"),
        ("colosseum_rules", "Display rules for participating in the Colosseum Challenge"),
        ("stabling", "Display Pokémon Stabling options"),
        ("stamina", "Display Stamina Point rules and example uses"),
        ("standards_of_living", "Display Standards of Living costs, benefits and negatives"),
    ]),
    ("Encounter and NPCs", [
        ("encounter_pokemon", "Generate one or more Pokémon"),
        ("encounter_biome", "Generate a Pokémon from a specific biome"),
        ("encounter_region", "Generate a Pokémon from a specific region"),
        ("encounter_human", "Generate a human NPC based on various statblocks"),
        ("human_npc", "Display a human NPC's statblock"),
        ("encounter_table", "Display a curated, rollable encounter table for a specific biome"),
        ("roll_foraging", "Roll an Insight + Nature check to see what you find on the foraging table"),
        ("quest", "Generate a simple quest-hook"),
    ]),
    ("Shops", [
        ("shop", "Display the stock of a specific shop"),
        ("roll_shop", "Roll 1D10 on the shop table and display stock for the rolled shop"),
    ]),
    ("Utilities", [
        ("roll", "Roll a single D6 by default. You can change the number of dice and/or the number of sides"),
        ("roll_training_session", "Roll a Pokémon training session"),
        ("roll_nature", "Roll 1D100 for a Pokémon's Nature."),
        ("settings", "Change the settings"),
        ("get_pokerole_legends", "Here you'll find the latest version of the Pokerole Legends Rules Supplement, Legends Roll20 Sheets, PNGs for Legends Pokémon and more"),
        ("invite", "Get an invite link for the bot"),
        ("feedback", "Send feedback, suggestions or bug reports straight to my creator"),
        ("discord", "Join the Pokérole Legends Discord server"),
        ("donate", "Show your love and support"),
    ]),
]

HELP_TAGLINES = {name: description for _, rows in HELP_CATEGORIES for name, description in rows}


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _command_map(self):
        result = {}
        for command in self.bot.walk_commands():
            if not command.hidden:
                result.setdefault(command.name.casefold(), command)
        for command in self.bot.tree.get_commands():
            result[command.name.casefold()] = command
        return result

    @staticmethod
    def _signature(command):
        if isinstance(command, app_commands.Group):
            return f"/{command.name} <subcommand>"
        if isinstance(command, app_commands.Command):
            pieces = [f"/{command.name}"]
            for param in command.parameters:
                pieces.append(f"<{param.name}>" if param.required else f"[{param.name}]")
            return " ".join(pieces)
        pieces = [f"/{command.name}"]
        for name, param in command.clean_params.items():
            pieces.append(f"<{name}>" if param.default is param.empty else f"[{name}]")
        return " ".join(pieces)

    def _detail(self, command):
        tagline = HELP_TAGLINES.get(
            command.name,
            getattr(command, "description", None) or getattr(command, "help", None) or "No description."
        )
        lines = [f"**{self._signature(command)}**", tagline.strip().splitlines()[0]]

        if isinstance(command, app_commands.Group):
            lines.append("\n**Subcommands:**")
            for subcommand in command.commands:
                lines.append(f"• `/{command.name} {subcommand.name}` — {subcommand.description}")
                for param in subcommand.parameters:
                    required = "required" if param.required else "optional"
                    lines.append(
                        f"  - `{param.name}` ({required}): {param.description or 'No additional guidance.'}"
                    )
        elif isinstance(command, app_commands.Command) and command.parameters:
            lines.append("\n**Options:**")
            for param in command.parameters:
                required = "required" if param.required else "optional"
                lines.append(
                    f"• `{param.name}` ({required}): {param.description or 'No additional guidance.'}"
                )
        return "\n".join(lines)

    async def _send_chunks(self, ctx, text):
        while text:
            if len(text) <= 1950:
                await ctx.send(text)
                return
            split = text.rfind("\n", 0, 1950)
            if split < 1:
                split = 1950
            await ctx.send(text[:split])
            text = text[split:].lstrip("\n")

    @commands.hybrid_command(
        name="help",
        description="Show the bot command list or detailed help for one command."
    )
    @app_commands.describe(
        command="Enter a command name for detailed usage, for example: encounter_table or metronome"
    )
    async def help(self, ctx, *, command: str = None):
        commands_now = self._command_map()
        if command:
            parts = command.strip().lstrip("/%").split()
            key = parts[0].casefold()
            found = commands_now.get(key)
            if found is None:
                await ctx.send(f"`{command}` is not a current command. Use `/help` to see the command list.")
                return
            if len(parts) > 1 and isinstance(found, app_commands.Group):
                sub_name = parts[1].casefold()
                sub = next((sub for sub in found.commands if sub.name.casefold() == sub_name), None)
                if sub is None:
                    await ctx.send(f"`/{found.name} {parts[1]}` is not a current subcommand. Use `/help {found.name}` for the available subcommands.")
                    return
                signature_parts = [f"/{found.name} {sub.name}"]
                for param in sub.parameters:
                    signature_parts.append(f"<{param.name}>" if param.required else f"[{param.name}]")
                lines = [f"**{' '.join(signature_parts)}**", sub.description]
                if sub.parameters:
                    lines.append("\n**Options:**")
                    for param in sub.parameters:
                        required = "required" if param.required else "optional"
                        lines.append(f"• `{param.name}` ({required}): {param.description or 'No additional guidance.'}")
                await self._send_chunks(ctx, "\n".join(lines))
                return
            await self._send_chunks(ctx, self._detail(found))
            return

        sections = []
        for category, rows in HELP_CATEGORIES:
            entries = [f"`/{name}` — {description}" for name, description in rows]
            sections.append(f"**{category}**\n" + "\n".join(entries))
        await self._send_chunks(
            ctx,
            "\n\n".join(sections) + "\n\nUse `/help <command>` for details."
        )


async def setup(bot):
    bot.remove_command("help")
    await bot.add_cog(Help(bot))
