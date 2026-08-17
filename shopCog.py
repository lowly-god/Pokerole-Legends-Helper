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

    @staticmethod
    def _rollable(items):
        """Return shop entries that have an actual Trainer Price."""
        return [
            item for item in items
            if str(item.get("price", "")).strip().upper() != "N/A"
        ]

    def generate(self, shop_name):
        cfg = self.shops[shop_name]
        mode = cfg["mode"]
        sections = []

        if mode == "full":
            grouped = defaultdict(list)
            for item in self._rollable(cfg["stock"]):
                grouped[item.get("category", "Stock")].append(item)
            for cat, entries in grouped.items():
                sections.append((cat, [line_for(x) for x in entries]))

        elif mode == "random":
            pool = self._rollable(cfg["pool"])
            count = random.randint(cfg["min"], cfg["max"])
            chosen = random.sample(pool, min(count, len(pool)))
            sections.append((f"Random Stock ({len(chosen)})", [line_for(x) for x in chosen]))

        elif mode == "precious_random":
            pool = self._rollable(cfg["pool"])
            total = random.randint(cfg["min"], cfg["max"])
            by_category = defaultdict(list)
            for item in pool:
                by_category[item.get("category", "Stock")].append(item)

            gems = by_category.get("Gems", [])
            evo_stones = by_category.get("Evolutionary Stones", [])
            mega_stones = by_category.get("Mega Stones", [])
            z_crystals = by_category.get("Z-Crystals", [])
            terasta_shards = by_category.get("Terasta Shards", [])

            chosen = []

            # Every Precious Stone Merchant carries exactly one Gem.
            if gems:
                chosen.extend(random.sample(gems, 1))

            # Evolution Stones scale upward with the overall stock roll.
            # 7-8 items: 1-2; 9-10 items: 2; 11-12 items: 2-3.
            if total <= 8:
                evo_count = random.randint(1, 2)
            elif total <= 10:
                evo_count = 2
            else:
                evo_count = random.randint(2, 3)
            chosen.extend(random.sample(evo_stones, min(evo_count, len(evo_stones))))

            # Low-stock merchants carry either a Z-Crystal or Terasta Shard.
            # As stock rises, both categories become represented.
            if total <= 8:
                available_specials = [
                    category for category in (z_crystals, terasta_shards) if category
                ]
                if available_specials:
                    chosen.extend(random.sample(random.choice(available_specials), 1))
            elif total == 9:
                if z_crystals and terasta_shards and random.choice((True, False)):
                    chosen.extend(random.sample(z_crystals, 1))
                    chosen.extend(random.sample(terasta_shards, 1))
                else:
                    available_specials = [
                        category for category in (z_crystals, terasta_shards) if category
                    ]
                    if available_specials:
                        chosen.extend(random.sample(random.choice(available_specials), 1))
            else:
                if z_crystals:
                    chosen.extend(random.sample(z_crystals, 1))
                if terasta_shards:
                    chosen.extend(random.sample(terasta_shards, 1))

            # Fill all remaining slots with Mega Stones.
            remaining = max(0, total - len(chosen))
            chosen.extend(random.sample(mega_stones, min(remaining, len(mega_stones))))

            sections.append((
                f"Random Stock ({len(chosen)})",
                [line_for(x) for x in chosen]
            ))

        elif mode == "ball_random":
            pool = self._rollable(cfg["pool"])
            total = random.randint(cfg["min"], cfg["max"])
            if not pool:
                sections.append(("Random Stock", []))
            else:
                # At least six different Ball types. Use multiples to fill the
                # 15-20 total stock, with no more than five of any one type.
                distinct_min = min(6, len(pool), total)
                distinct_max = min(12, len(pool), total)
                distinct_count = random.randint(distinct_min, distinct_max)
                chosen_types = random.sample(pool, distinct_count)
                counts = {item["name"]: 1 for item in chosen_types}
                lookup = {item["name"]: item for item in chosen_types}
                remaining = total - distinct_count

                while remaining > 0:
                    candidates = [name for name, qty in counts.items() if qty < 5]
                    if not candidates:
                        # This should never happen with the current 15-20 stock
                        # size, but prevents an infinite loop if the table changes.
                        break
                    name = random.choice(candidates)
                    counts[name] += 1
                    remaining -= 1

                lines = [line_for(lookup[name], qty) for name, qty in counts.items()]
                sections.append((f"Random Stock ({sum(counts.values())} Balls Total)", lines))

        elif mode == "herbalist":
            stock = self._rollable(cfg["stock"])
            sections.append(("General Items", [line_for(x) for x in stock]))
            pool = self._rollable(cfg.get("special_pool", []))
            if pool:
                n = random.randint(cfg.get("special_min", 1), cfg.get("special_max", 2))
                chosen = random.sample(pool, min(n, len(pool)))
                sections.append(("Special Items", [line_for(x) for x in chosen]))

        elif mode == "mixed_special":
            grouped = defaultdict(list)
            for item in self._rollable(cfg["stock"]):
                grouped[item.get("category", "Stock")].append(item)
            for cat, entries in grouped.items():
                sections.append((cat, [line_for(x) for x in entries]))

            pool = self._rollable(cfg.get("special_pool", []))
            if pool:
                n = random.randint(cfg["special_min"], cfg["special_max"])
                chosen = random.sample(pool, min(n, len(pool)))
                sections.append(("Special Items", [line_for(x) for x in chosen]))

        elif mode == "curiosity":
            pool = self._rollable(cfg["pool"])
            n = random.randint(cfg["min"], cfg["max"])
            chosen = random.sample(pool, min(n, len(pool)))
            sections.append((f"General Items ({len(chosen)})", [line_for(x) for x in chosen]))

            # Exactly two special-table results:
            #   - one Special Item + one Crest, OR
            #   - two distinct Crests.
            crest_pool = self._rollable(cfg.get("crest_pool", []))
            special_pool = self._rollable(cfg.get("special_pool", []))
            special_lines = []

            if len(crest_pool) >= 2 and special_pool:
                if random.choice((True, False)):
                    special_lines.extend(line_for(x) for x in random.sample(crest_pool, 2))
                else:
                    special_lines.append(line_for(random.choice(special_pool)))
                    special_lines.append(line_for(random.choice(crest_pool)))
            elif len(crest_pool) >= 2:
                special_lines.extend(line_for(x) for x in random.sample(crest_pool, 2))
            elif crest_pool and special_pool:
                special_lines.append(line_for(random.choice(special_pool)))
                special_lines.append(line_for(crest_pool[0]))
            elif crest_pool:
                special_lines.extend(line_for(crest_pool[0]) for _ in range(2))
            elif len(special_pool) >= 2:
                # Defensive fallback only if a future table removes all Crests.
                special_lines.extend(line_for(x) for x in random.sample(special_pool, 2))

            if special_lines:
                sections.append(("Special Items", special_lines))

        elif mode == "travelling":
            stock = self._rollable(cfg["stock"])
            sections.append(("Regular Wares", [line_for(x) for x in stock]))
            pool = self._rollable(cfg["pool"])
            chosen = random.sample(pool, min(cfg["count"], len(pool)))
            sections.append((f"Random Wares ({len(chosen)})", [line_for(x) for x in chosen]))

        return sections

    def all_stock(self, shop_name):
        """Return every item a merchant can potentially stock, without rolling."""
        cfg = self.shops[shop_name]
        candidates = []
        for key in ("stock", "pool", "special_pool", "crest_pool"):
            value = cfg.get(key, [])
            if isinstance(value, list):
                candidates.extend(value)

        # Keep one copy of identical stock entries while preserving authored order.
        unique = []
        seen = set()
        for item in self._rollable(candidates):
            marker = (
                item.get("name"), str(item.get("price", "")),
                item.get("effect", ""), item.get("category", "Stock")
            )
            if marker in seen:
                continue
            seen.add(marker)
            unique.append(item)

        grouped = defaultdict(list)
        for item in unique:
            grouped[item.get("category", "Stock")].append(item)
        return [(cat, [line_for(x) for x in entries]) for cat, entries in grouped.items()]

    def embeds_for_shop(self, shop_name, display_all_stock=False):
        sections = self.all_stock(shop_name) if display_all_stock else self.generate(shop_name)
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

    @staticmethod
    def _embed_batches(embeds, max_count=10, max_chars=5800):
        """Batch embeds within Discord's per-message limits.

        Discord permits at most 10 embeds in one message and at most 6000
        aggregate embed characters. Keep a small safety margin for titles,
        authors and footers.
        """
        batches = []
        current = []
        current_chars = 0

        for embed in embeds:
            try:
                embed_chars = len(embed)
            except Exception:
                data = embed.to_dict()
                embed_chars = sum(
                    len(str(value))
                    for key, value in data.items()
                    if key in {"title", "description", "author", "footer", "fields"}
                )

            if current and (
                len(current) >= max_count
                or current_chars + embed_chars > max_chars
            ):
                batches.append(current)
                current = []
                current_chars = 0

            current.append(embed)
            current_chars += embed_chars

        if current:
            batches.append(current)
        return batches

    async def send_embeds(self, interaction, embeds, intro=None):
        batches = self._embed_batches(embeds)
        if not batches:
            await interaction.response.send_message(content=intro or "No stock found.")
            return

        await interaction.response.send_message(content=intro, embeds=batches[0])
        for batch in batches[1:]:
            await interaction.followup.send(embeds=batch)

    @app_commands.command(name="shop", description="Display the stock of a specific shop")
    @app_commands.describe(
        shop="Choose a shop",
        display_all_stock="Display All Stock instead of rolling the merchant's normal stock table",
    )
    @app_commands.autocomplete(shop=shop_autocomplete)
    async def shop(
        self,
        interaction: discord.Interaction,
        shop: str,
        display_all_stock: bool = False,
    ):
        if shop not in self.shops:
            await interaction.response.send_message("Shop not found.", ephemeral=True)
            return
        embeds = self.embeds_for_shop(shop, display_all_stock=display_all_stock)
        await self.send_embeds(interaction, embeds)

    @app_commands.command(name="roll_shop", description="Roll 1D10 on the shop table and display stock for the rolled shop")
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
