import json
import random
from collections import Counter, defaultdict

import discord
from discord import app_commands
from discord.ext import commands


def money(price):
    return "₽N/A" if str(price).upper() == "N/A" else f"₽{int(price):,}"


def line_for(item, quantity=None):
    qty = f"{quantity}x " if quantity and quantity > 1 else ""
    effect = item.get("effect", "")
    suffix = f" — {effect}" if effect else ""
    return f"**{qty}{item['name']}** — {money(item['price'])}{suffix}"


def chunk_lines(lines, max_chars=3600):
    chunks = []
    current = []
    length = 0
    for line in lines:
        add = len(line) + 1
        if current and length + add > max_chars:
            chunks.append(current)
            current = []
            length = 0
        current.append(line)
        length += add
    if current:
        chunks.append(current)
    return chunks


class ShopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        with open("shop_data.json", "r", encoding="utf-8") as f:
            payload = json.load(f)
        self.shops = payload["shops"]
        self.roll_map = payload["roll_map"]

    async def shop_autocomplete(self, interaction: discord.Interaction, current: str):
        current = current.lower()
        names = list(self.shops.keys())
        return [
            app_commands.Choice(name=name, value=name)
            for name in names if current in name.lower()
        ][:25]

    def generate(self, shop_name):
        cfg = self.shops[shop_name]
        mode = cfg["mode"]
        sections = []

        if mode == "full":
            grouped = defaultdict(list)
            for item in cfg["stock"]:
                grouped[item.get("category", "Stock")].append(item)
            for cat, entries in grouped.items():
                sections.append((cat, [line_for(x) for x in entries]))

        elif mode == "random":
            count = random.randint(cfg["min"], cfg["max"])
            chosen = random.sample(cfg["pool"], min(count, len(cfg["pool"])))
            sections.append((f"Random Stock ({len(chosen)})", [line_for(x) for x in chosen]))

        elif mode == "ball_random":
            rolls = [random.choice(cfg["pool"]) for _ in range(cfg["count"])]
            counts = Counter(x["name"] for x in rolls)
            lookup = {x["name"]: x for x in cfg["pool"]}
            lines = [line_for(lookup[name], qty) for name, qty in counts.items()]
            sections.append((f"Random Stock ({cfg['count']} Balls Total)", lines))

        elif mode == "herbalist":
            sections.append(("General Items", [line_for(x) for x in cfg["stock"]]))
            n = min(cfg.get("special_count", 2), len(cfg.get("special_pool", [])))
            chosen = random.sample(cfg.get("special_pool", []), n)
            sections.append(("Special Items", [line_for(x) for x in chosen]))

        elif mode == "mixed_special":
            grouped = defaultdict(list)
            for item in cfg["stock"]:
                grouped[item.get("category", "Stock")].append(item)
            for cat, entries in grouped.items():
                sections.append((cat, [line_for(x) for x in entries]))
            n = random.randint(cfg["special_min"], cfg["special_max"])
            chosen = random.sample(cfg["special_pool"], min(n, len(cfg["special_pool"])))
            sections.append((f"Special Weapons and Equipment ({len(chosen)})", [line_for(x) for x in chosen]))

        elif mode == "curiosity":
            # Keep the normal random-item stock unchanged.
            n = random.randint(cfg["min"], cfg["max"])
            chosen = random.sample(cfg["pool"], min(n, len(cfg["pool"])))
            sections.append((f"General Items ({len(chosen)})", [line_for(x) for x in chosen]))

            # Special stock is exactly two items: either two distinct Crests,
            # or one special item plus one Crest. Display them together.
            special_lines = []
            crest_pool = cfg.get("crest_pool", [])
            special_pool = cfg.get("special_pool", [])
            roll_two_crests = bool(crest_pool) and (not special_pool or random.choice((True, False)))
            if roll_two_crests:
                crests = random.sample(crest_pool, min(2, len(crest_pool)))
                special_lines.extend(line_for(x) for x in crests)
            else:
                if special_pool:
                    special_lines.append(line_for(random.choice(special_pool)))
                if crest_pool:
                    special_lines.append(line_for(random.choice(crest_pool)))
            if special_lines:
                sections.append(("Special Items", special_lines))

        elif mode == "travelling":
            sections.append(("Regular Wares", [line_for(x) for x in cfg["stock"]]))
            chosen = random.sample(cfg["pool"], min(cfg["count"], len(cfg["pool"])))
            sections.append(("Random Wares (4)", [line_for(x) for x in chosen]))

        return sections

    def embeds_for_shop(self, shop_name):
        sections = self.generate(shop_name)
        embeds = []
        first = True
        for section_name, lines in sections:
            for idx, chunk in enumerate(chunk_lines(lines)):
                title = shop_name if first else f"{shop_name} (cont.)"
                embed = discord.Embed(title=title, description="\n".join(chunk))
                embed.set_author(name=section_name if idx == 0 else f"{section_name} (cont.)")
                embeds.append(embed)
                first = False
        if not embeds:
            embeds.append(discord.Embed(title=shop_name, description="No stock found."))
        footer = self.shops[shop_name].get("footer")
        if footer and embeds:
            embeds[-1].set_footer(text=footer)
        return embeds

    async def send_embeds(self, interaction, embeds, intro=None):
        # Discord supports max 10 embeds per message.
        first_batch = embeds[:10]
        await interaction.response.send_message(content=intro, embeds=first_batch)
        rest = embeds[10:]
        while rest:
            await interaction.followup.send(embeds=rest[:10])
            rest = rest[10:]

    @app_commands.command(name="shop", description="Display the stock of a Legends shop.")
    @app_commands.describe(shop="Choose a shop")
    @app_commands.autocomplete(shop=shop_autocomplete)
    async def shop(self, interaction: discord.Interaction, shop: str):
        if shop not in self.shops:
            await interaction.response.send_message("Shop not found.", ephemeral=True)
            return
        embeds = self.embeds_for_shop(shop)
        await self.send_embeds(interaction, embeds)

    @app_commands.command(name="rollshop", description="Roll 1d10 on the Legends shop table.")
    async def rollshop(self, interaction: discord.Interaction):
        roll = random.randint(1, 10)
        result = self.roll_map[str(roll)]

        if roll == 10:
            embed = discord.Embed(
                title="🎲 Roll Shop — 10",
                description="**Players choose a shop.**\nUse `/shop` to choose which merchant appears."
            )
            await interaction.response.send_message(embed=embed)
            return

        all_embeds = []
        for shop_name in result:
            all_embeds.extend(self.embeds_for_shop(shop_name))

        intro = f"🎲 **Shop Roll: {roll}** — " + " + ".join(result)
        await self.send_embeds(interaction, all_embeds, intro=intro)


async def setup(bot):
    await bot.add_cog(ShopCog(bot))
