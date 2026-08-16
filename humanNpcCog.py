import itertools
import json
import random
import re
import unicodedata
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands


DATA_FILE = Path(__file__).with_name("human_npc_data.json")
PERK_FILE = Path(__file__).with_name("perk_data.json")
ARMOR_FILE = Path(__file__).with_name("armor_data.json")
MANEUVER_FILE = Path(__file__).with_name("maneuver_data.json")
RANKUP_FILE = Path(__file__).with_name("rankup_data.json")

RANKS = ["Starter", "Rookie", "Standard", "Advanced", "Expert", "Ace", "Master", "Champion"]
PERK_TIERS = [
    "Starter / Rookie / Standard",
    "Advanced / Expert",
    "Ace / Master / Champion",
]
SOCIALS = ["Tough", "Cool", "Beauty", "Clever", "Cute"]
# Human-facing skills used by the Legends combat/maneuver data.
HUMAN_SKILLS = [
    "Aura", "Brawl", "Channel", "Weapons",
    "Alert", "Athletic", "Crafts", "Empathy", "Etiquette", "Evasion",
    "Lore", "Medicine", "Nature", "Perform", "Stealth", "Technology",
    "Allure", "Intimidate",
]

# /encounter_human uses the Legends rank progression explicitly rather than
# reusing trainer/pokemon total-pool parsing. Human NPC templates already
# contain their Starter main-attribute spread, so Starter adds 0 Main points.
# Templates do not carry an age, so generated NPCs use the Adult Starter
# social baseline: all Social Attributes begin at 1, then 4 Starter points
# are distributed before rank bonuses are applied.
HUMAN_RANK_RULES = {
    "Starter":  {"main": 0,  "social": 0,  "skills": 5,  "skill_limit": 1, "stamina": 5},
    "Rookie":   {"main": 2,  "social": 2,  "skills": 10, "skill_limit": 2, "stamina": 8},
    "Standard": {"main": 4,  "social": 4,  "skills": 14, "skill_limit": 3, "stamina": 10},
    "Advanced": {"main": 6,  "social": 6,  "skills": 17, "skill_limit": 4, "stamina": 12},
    "Expert":   {"main": 8,  "social": 8,  "skills": 19, "skill_limit": 5, "stamina": 14},
    "Ace":      {"main": 10, "social": 10, "skills": 21, "skill_limit": 5, "stamina": 16},
    "Master":   {"main": 11, "social": 11, "skills": 23, "skill_limit": 6, "stamina": 17},
    "Champion": {"main": 12, "social": 12, "skills": 25, "skill_limit": 6, "stamina": 18},
}
STARTER_ADULT_SOCIAL_POINTS = 4


def normalize(text):
    text = (text or "").replace("’", "'").replace("‘", "'").replace("–", "-").replace("—", "-")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    text = text.replace("'", "")
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return re.sub(r"\s+", " ", text)


def pips(value, cap):
    cap = max(value, cap)
    return "⬤" * value + "⭘" * max(0, cap - value)


def split_chunks(text, limit=1900):
    if len(text) <= limit:
        return [text]
    chunks = []
    current = ""
    for line in text.splitlines(True):
        if current and len(current) + len(line) > limit:
            chunks.append(current.rstrip())
            current = ""
        if len(line) > limit:
            while len(line) > limit:
                take = limit - len(current)
                current += line[:take]
                line = line[take:]
                chunks.append(current.rstrip())
                current = ""
        current += line
    if current.strip():
        chunks.append(current.rstrip())
    return chunks or ["Nothing found."]


def _extract_total(benefits, phrase, default=0):
    # e.g. "(Total Main Attribute Points 10)" or "(Total of 21 Skill Points)"
    for line in benefits:
        if phrase.casefold() in line.casefold():
            nums = re.findall(r"\d+", line)
            if nums:
                return int(nums[-1])
    return default


def _extract_skill_limit(benefits, default=1):
    for line in benefits:
        if "Skill Limit" in line:
            m = re.search(r"Skill Limit\s+(\d+)", line)
            if m:
                return int(m.group(1))
    return default


class HumanNPCView(discord.ui.View):
    def __init__(self, cog, npc_name):
        super().__init__(timeout=300)
        self.cog = cog
        self.npc_name = npc_name

    async def _send(self, interaction, text):
        chunks = split_chunks(text)
        await interaction.response.send_message(chunks[0])
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk)

    @discord.ui.button(label="Perks", style=discord.ButtonStyle.blurple)
    async def perks(self, interaction: discord.Interaction, button: discord.ui.Button):
        npc = self.cog.npcs[self.npc_name]
        blocks = [f"__{self.npc_name} — Likely Perks__"]
        for tier in PERK_TIERS:
            names = npc.get("perk_tiers", {}).get(tier, [])
            if names:
                blocks.append(f"**{tier}:**\n" + " / ".join(names))
        await self._send(interaction, "\n\n".join(blocks))

    @discord.ui.button(label="Weapons", style=discord.ButtonStyle.green)
    async def weapons(self, interaction: discord.Interaction, button: discord.ui.Button):
        npc = self.cog.npcs[self.npc_name]
        await self._send(
            interaction,
            f"__{self.npc_name} — Likely Weapons / Combat Styles__\n" +
            " / ".join(npc.get("weapons", []))
        )

    @discord.ui.button(label="Maneuvers", style=discord.ButtonStyle.gray)
    async def maneuvers(self, interaction: discord.Interaction, button: discord.ui.Button):
        npc = self.cog.npcs[self.npc_name]
        await self._send(
            interaction,
            f"__{self.npc_name} — Likely Non-Weapon Maneuvers__\n" +
            " / ".join(npc.get("maneuvers", []))
        )

    @discord.ui.button(label="Armor", style=discord.ButtonStyle.gray)
    async def armor(self, interaction: discord.Interaction, button: discord.ui.Button):
        npc = self.cog.npcs[self.npc_name]
        await self._send(
            interaction,
            f"__{self.npc_name} — Likely Armor__\n" +
            " / ".join(npc.get("armor", []))
        )


class HumanNPCCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        self.npcs = payload["npcs"]
        self.rank_order = payload.get("rank_order", RANKS)

        self.perks = json.loads(PERK_FILE.read_text(encoding="utf-8"))
        self.armor_data = json.loads(ARMOR_FILE.read_text(encoding="utf-8"))
        self.maneuver_data = json.loads(MANEUVER_FILE.read_text(encoding="utf-8"))
        self.rankup_data = json.loads(RANKUP_FILE.read_text(encoding="utf-8"))

        self.armor_lookup = {normalize(name): name for name in self.armor_data}
        # Common source-text variants.
        self.armor_lookup.update({
            normalize("Adventurers Clothes"): "Adventurer’s Clothes",
            normalize("Adventures Clothes"): "Adventurer’s Clothes",
            normalize("Chainmail"): "Chain Mail",
        })

        self.weapon_lookup = {}
        for weapon in self.maneuver_data["weapons"]:
            for alias in [weapon["name"]] + weapon.get("aliases", []):
                self.weapon_lookup[normalize(alias)] = weapon

        self.maneuver_lookup = {}
        for maneuver in self.maneuver_data["maneuvers"]:
            for alias in [maneuver["name"]] + maneuver.get("aliases", []):
                self.maneuver_lookup[normalize(alias)] = maneuver

        # Keep /encounter_human independent from older rankup-data wording.
        # These are the exact cumulative point totals for generated human NPCs.
        self.rank_rules = {rank: dict(HUMAN_RANK_RULES[rank]) for rank in RANKS}

    async def npc_autocomplete(self, interaction: discord.Interaction, current: str):
        query = normalize(current)
        results = []
        for name in self.npcs:
            if query in normalize(name):
                results.append(app_commands.Choice(name=name[:100], value=name))
            if len(results) >= 25:
                break
        return results

    def _resolve_armor(self, name):
        return self.armor_lookup.get(normalize(name))

    def _resolve_weapon(self, name):
        n = normalize(name)
        if n in self.weapon_lookup:
            return self.weapon_lookup[n]

        # Source templates use a few broad/singular style labels.
        keyword_map = [
            (("great axe", "great weapon"), "Great Weapons"),
            (("long bow", "bow", "crossbow"), "Bows and Crossbows"),
            (("short blade", "dagger", "knife"), "Daggers, Knives and Short Blades"),
            (("polearm", "halberd", "spear"), "Halberds, Spears and Polearms"),
            (("mace", "hammer", "flail", "club"), "Clubs, Flails, Hammers and Maces"),
            (("throwing star", "kunai"), "Kunai, Throwing Darts and Throwing Stars"),
            (("nunchaku", "stave", "staff"), "Nunchaku and Staves"),
            (("aura",), "Aura Combat Skill"),
            (("channelling", "channeling"), "Channelling Combat Skill"),
            (("unarmed",), "Unarmed Combat Skill"),
            (("improvised",), "Improvised Weapons"),
            (("energy weapon",), "Energy Weapons"),
            (("firearm", "gun"), "Firearms"),
            (("axe",), "Axes"),
            (("sword",), "Swords"),
            (("shield",), "Shields"),
            (("blowpipe",), "Blowpipes"),
        ]
        for words, canonical in keyword_map:
            if any(word in n for word in words):
                return self.weapon_lookup.get(normalize(canonical))
        return None

    def _resolve_maneuver_name(self, name):
        n = normalize(name)
        if n in self.maneuver_lookup:
            return self.maneuver_lookup[n]["name"]

        # Apostrophe/source spelling variants.
        alias = {
            normalize("Fighters Cunning"): "Fighter’s Cunning",
            normalize("Paladins Protection"): "Paladin’s Protection",
            normalize("Duellists Swagger"): "Duellist's Swagger",
        }.get(n)
        if alias:
            return alias
        return name

    def _eligible_perks(self, npc, rank):
        idx = RANKS.index(rank)
        if idx <= RANKS.index("Standard"):
            tiers = PERK_TIERS[:1]
        elif idx <= RANKS.index("Expert"):
            tiers = PERK_TIERS[:2]
        else:
            tiers = PERK_TIERS

        eligible = []
        for tier in tiers:
            for name in npc.get("perk_tiers", {}).get(tier, []):
                if name not in eligible:
                    eligible.append(name)
        return eligible

    def _perk_count(self, rank):
        idx = RANKS.index(rank)
        if idx < RANKS.index("Rookie"):
            return 0
        if idx < RANKS.index("Advanced"):
            return 1
        if idx < RANKS.index("Ace"):
            return 2
        return 3

    def _nonweapon_count(self, rank):
        return self._perk_count(rank)

    def _advanced_count(self, rank):
        idx = RANKS.index(rank)
        if idx < RANKS.index("Advanced"):
            return 0
        if idx < RANKS.index("Ace"):
            return 1
        return 2

    def _rank_cap_bonus(self, rank, stat_names, base_stats):
        # /encounter_human only applies the requested point gains. Rank-specific
        # cap-breaking benefits (Ace/Master/Champion) are intentionally ignored.
        return {name: base_stats[name]["max"] for name in stat_names}

    def _allocate_main(self, npc, rank):
        stat_names = ["Strength", "Dexterity", "Vitality", "Special", "Insight"]
        base_stats = npc["stats"]
        values = {name: base_stats[name]["base"] for name in stat_names}
        caps = self._rank_cap_bonus(rank, stat_names, base_stats)
        points = self.rank_rules[rank]["main"]

        while points > 0:
            candidates = [name for name in stat_names if values[name] < caps[name]]
            if not candidates:
                break
            weights = []
            for name in candidates:
                # Favor stats the template is already built around while still
                # allowing variation between generated NPCs.
                headroom = caps[name] - values[name]
                weight = max(1, base_stats[name]["base"] * 2 + headroom)
                if name == "Vitality":
                    weight += 1
                weights.append(weight)
            chosen = random.choices(candidates, weights=weights, k=1)[0]
            values[chosen] += 1
            points -= 1
        return values, caps

    def _allocate_socials(self, rank):
        values = {name: 1 for name in SOCIALS}
        # Adult NPCs receive the Starter base Social pool, then all cumulative
        # Social Attribute points earned through the requested rank.
        points = STARTER_ADULT_SOCIAL_POINTS + self.rank_rules[rank]["social"]
        while points > 0:
            candidates = [name for name in SOCIALS if values[name] < 5]
            if not candidates:
                break
            chosen = random.choice(candidates)
            values[chosen] += 1
            points -= 1
        return values

    def _skill_biases(self, selected_weapons, selected_nonweapon):
        weights = {name: 1 for name in HUMAN_SKILLS}
        for weapon in selected_weapons:
            n = normalize(weapon["name"])
            if "aura combat" in n:
                weights["Aura"] += 8
            elif "channelling combat" in n:
                weights["Channel"] += 8
            elif "unarmed combat" in n:
                weights["Brawl"] += 8
            else:
                weights["Weapons"] += 7

        for name in selected_nonweapon:
            m = self.maneuver_lookup.get(normalize(name))
            if not m:
                continue
            text = " ".join(v.get("accuracy", "") for v in m.get("variants", []))
            upper = text.upper()
            for skill in HUMAN_SKILLS:
                if skill.upper() in upper:
                    weights[skill] += 3

        weights["Alert"] += 2
        weights["Evasion"] += 2
        return weights

    def _allocate_skills(self, rank, selected_weapons, selected_nonweapon):
        values = {name: 0 for name in HUMAN_SKILLS}
        total = self.rank_rules[rank]["skills"]
        limit = self.rank_rules[rank]["skill_limit"]
        weights = self._skill_biases(selected_weapons, selected_nonweapon)

        while total > 0:
            candidates = [name for name in HUMAN_SKILLS if values[name] < limit]
            if not candidates:
                break
            chosen = random.choices(
                candidates,
                weights=[weights[name] for name in candidates],
                k=1
            )[0]
            values[chosen] += 1
            total -= 1
        return values

    def _weapon_candidates(self, npc):
        out = []
        seen = set()
        for raw in npc.get("weapons", []):
            weapon = self._resolve_weapon(raw)
            if weapon and weapon["name"] not in seen:
                seen.add(weapon["name"])
                out.append(weapon)
        return out

    def _choose_weapons(self, npc, rank):
        candidates = self._weapon_candidates(npc)
        if not candidates:
            return []

        need_advanced = self._advanced_count(rank)
        combos = []
        for size in (1, 2):
            if len(candidates) < size:
                continue
            for combo in itertools.combinations(candidates, size):
                advanced_names = {
                    m["name"]
                    for weapon in combo
                    for m in weapon.get("maneuvers", [])
                    if m.get("tier") == "Advanced"
                }
                if len(advanced_names) >= need_advanced:
                    combos.append(combo)

        if combos:
            return list(random.choice(combos))

        count = random.randint(1, min(2, len(candidates)))
        return random.sample(candidates, count)

    def _choose_nonweapon(self, npc, rank):
        count = self._nonweapon_count(rank)
        if count <= 0:
            return []
        names = []
        for raw in npc.get("maneuvers", []):
            name = self._resolve_maneuver_name(raw)
            if name not in names:
                names.append(name)
        return random.sample(names, min(count, len(names)))

    def _choose_equipment_and_moves(self, npc, rank):
        armor_choices = []
        for raw in npc.get("armor", []):
            resolved = self._resolve_armor(raw)
            if resolved and resolved not in armor_choices:
                armor_choices.append(resolved)
        armor = random.choice(armor_choices) if armor_choices else (
            random.choice(npc.get("armor", [])) if npc.get("armor") else "None"
        )

        weapons = self._choose_weapons(npc, rank)

        basic = []
        advanced_pool = []
        for weapon in weapons:
            for maneuver in weapon.get("maneuvers", []):
                if maneuver.get("tier") == "Basic" and maneuver["name"] not in basic:
                    basic.append(maneuver["name"])
                elif maneuver.get("tier") == "Advanced" and maneuver["name"] not in advanced_pool:
                    advanced_pool.append(maneuver["name"])

        adv_count = self._advanced_count(rank)
        advanced = random.sample(advanced_pool, min(adv_count, len(advanced_pool)))
        nonweapon = self._choose_nonweapon(npc, rank)
        return armor, weapons, basic, advanced, nonweapon

    def _base_text(self, npc):
        lines = [
            f"__{npc['name']}__",
            f"**Archetype:** {npc['archetype']}",
            f"**Base HP:** {npc['base_hp']}",
        ]
        for name in ["Strength", "Dexterity", "Vitality", "Special", "Insight"]:
            st = npc["stats"][name]
            lines.append(f"**{name}:** {pips(st['base'], st['max'])}")
        if npc.get("loot"):
            lines.append(f"**Potential Loot:** {' / '.join(npc['loot'])}")
        return "\n".join(lines)

    def _encounter_text(self, npc, rank):
        armor, weapons, basic, advanced, nonweapon = self._choose_equipment_and_moves(npc, rank)
        attrs, attr_caps = self._allocate_main(npc, rank)
        socials = self._allocate_socials(rank)
        skills = self._allocate_skills(rank, weapons, nonweapon)

        perk_pool = self._eligible_perks(npc, rank)
        perk_count = self._perk_count(rank)
        perks = random.sample(perk_pool, min(perk_count, len(perk_pool)))

        hp = npc["base_hp"] + attrs["Vitality"]

        lines = [
            f"__{rank} {npc['name']}__",
            f"**Archetype:** {npc['archetype']}",
            f"**HP:** {hp}",
            f"**Stamina Points:** {self.rank_rules[rank]['stamina']}",
            "",
            "**Main Attributes**",
        ]
        for name in ["Strength", "Dexterity", "Vitality", "Special", "Insight"]:
            lines.append(
                f"**{name}:** {pips(attrs[name], attr_caps[name])} `({attrs[name]}/{attr_caps[name]})`"
            )

        lines.extend(["", "**Social Attributes**"])
        for name in SOCIALS:
            lines.append(f"**{name}:** {pips(socials[name], 5)} `({socials[name]}/5)`")

        nonzero_skills = [f"{name} {value}" for name, value in skills.items() if value]
        lines.extend([
            "",
            "**Skills**",
            " / ".join(nonzero_skills) if nonzero_skills else "None",
            "",
            f"**Armor:** {armor}",
            f"**Weapons:** {' / '.join(w['name'] for w in weapons) if weapons else 'None'}",
        ])

        maneuver_parts = []
        if basic:
            maneuver_parts.append("**Basic Weapon Maneuvers:** " + " / ".join(basic))
        if advanced:
            maneuver_parts.append("**Advanced Techniques:** " + " / ".join(advanced))
        if nonweapon:
            maneuver_parts.append("**Non-Weapon Maneuvers:** " + " / ".join(nonweapon))
        if maneuver_parts:
            lines.extend([""] + maneuver_parts)

        lines.extend([
            "",
            f"**Perks:** {' / '.join(perks) if perks else 'None'}",
        ])
        if npc.get("loot"):
            lines.append(f"**Potential Loot:** {' / '.join(npc['loot'])}")
        return "\n".join(lines)

    @app_commands.command(name="human_npc", description="Display a Legends human NPC statblock.")
    @app_commands.describe(npc="Human NPC type")
    @app_commands.autocomplete(npc=npc_autocomplete)
    async def human_npc(self, interaction: discord.Interaction, npc: str):
        data = self.npcs.get(npc)
        if not data:
            # tolerant case/punctuation lookup
            key = next((name for name in self.npcs if normalize(name) == normalize(npc)), None)
            data = self.npcs.get(key) if key else None
        if not data:
            await interaction.response.send_message("Human NPC not found.", ephemeral=True)
            return
        await interaction.response.send_message(
            self._base_text(data),
            view=HumanNPCView(self, data["name"])
        )

    @app_commands.command(name="encounter_human", description="Generate a ranked Legends human NPC.")
    @app_commands.describe(npc="Human NPC type", rank="Required NPC rank")
    @app_commands.autocomplete(npc=npc_autocomplete)
    @app_commands.choices(rank=[app_commands.Choice(name=r, value=r) for r in RANKS])
    async def encounter_human(self, interaction: discord.Interaction, npc: str, rank: str):
        data = self.npcs.get(npc)
        if not data:
            key = next((name for name in self.npcs if normalize(name) == normalize(npc)), None)
            data = self.npcs.get(key) if key else None
        if not data:
            await interaction.response.send_message("Human NPC not found.", ephemeral=True)
            return
        if rank not in RANKS:
            await interaction.response.send_message("Invalid rank.", ephemeral=True)
            return

        text = self._encounter_text(data, rank)
        chunks = split_chunks(text)
        await interaction.response.send_message(chunks[0])
        for chunk in chunks[1:]:
            await interaction.followup.send(chunk)


async def setup(bot):
    await bot.add_cog(HumanNPCCog(bot))
