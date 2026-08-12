import json
import re
import unicodedata
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

DATA_FILE = Path(__file__).with_name("fieldtype_data.json")


def normalize(text: str) -> str:
    text = (text or "").replace("’", "'").replace("‘", "'").replace("–", "-").replace("—", "-")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return re.sub(r"\s+", " ", text)


async def send_chunks(interaction: discord.Interaction, blocks):
    chunks = []
    current = ""
    for block in blocks:
        block = block.strip() + "\n\n"
        if current and len(current) + len(block) > 1900:
            chunks.append(current.rstrip())
            current = ""
        if len(block) > 1900:
            if current:
                chunks.append(current.rstrip())
                current = ""
            for i in range(0, len(block), 1850):
                chunks.append(block[i:i+1850].rstrip())
        else:
            current += block
    if current.strip():
        chunks.append(current.rstrip())

    await interaction.response.send_message(chunks[0] if chunks else "Nothing found.")
    for chunk in chunks[1:]:
        await interaction.followup.send(chunk)


class FieldTypeLookup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with DATA_FILE.open("r", encoding="utf-8") as f:
            self.data = json.load(f)

        self.lookup = {}
        for field in self.data["field_types"]:
            for alias in [field["name"]] + field.get("aliases", []):
                self.lookup[normalize(alias)] = field

    async def fieldtype_autocomplete(self, interaction: discord.Interaction, current: str):
        query = normalize(current)
        matches = []
        seen = set()
        for pass_contains in (False, True):
            for field in self.data["field_types"]:
                name = field["name"]
                aliases = [name] + field.get("aliases", [])
                normalized = [normalize(x) for x in aliases]
                matched = any((query in n if pass_contains else n.startswith(query)) for n in normalized)
                if matched and name not in seen:
                    seen.add(name)
                    matches.append(app_commands.Choice(name=name[:100], value=name))
                    if len(matches) >= 25:
                        return matches
        return matches

    @app_commands.command(
        name="fieldtype",
        description="Look up the effects of a Field-Type."
    )
    @app_commands.describe(name="Field-Type name")
    @app_commands.autocomplete(name=fieldtype_autocomplete)
    async def fieldtype(self, interaction: discord.Interaction, name: str):
        field = self.lookup.get(normalize(name))
        if not field:
            await interaction.response.send_message(
                f'Field-Type "{name}" was not found.',
                ephemeral=True
            )
            return

        blocks = [f"# {field['name']}"]
        order = ["General Effects", "Abilities Affected", "Moves Affected", "Changing The Field-Type"]

        for section in order:
            items = field["sections"].get(section, [])
            if not items:
                continue
            blocks.append(f"## {section}")
            for item in items:
                blocks.append(f"• {item}")

        await send_chunks(interaction, blocks)


async def setup(bot):
    await bot.add_cog(FieldTypeLookup(bot))
