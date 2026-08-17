import random
import discord
from discord import app_commands
from discord.ext import commands

from luck_utils import apply_luck_modifier, format_luck_check

FORAGING_TABLES = {1: ['Oran Berry', 'Red Apricorn', 'Pecha Berry', 'Chesto Berry', 'Cheri Berry', 'Blue Apricorn', 'Persim Berry', 'Aspear Berry', 'Pink Apricorn', 'Tiny Bamboo Shoot'], 2: ['Chesto Berry', 'Red Apricorn', 'Rawst Berry', 'Sitrus Berry', 'Cyan Apricorn', '5x Poke Food Ingredients', 'Energy Root', 'Gray Apricorn', 'Big Bamboo Shoot', 'Green Apricorn'], 3: ['Green Apricorn', 'Lum Berry', 'Sitrus Berry', 'White Apricorn', 'Energy Root', 'Gray Apricorn', 'Cyan Apricorn', '3x Meal Ingredients (Rations)', 'Energy Root', 'Big Mushroom'], 4: ['Pink Apricorn', 'Blue Apricorn', 'Honey', 'Lum Berry', 'Vitality Herb', 'Sitrus Berry', 'Stardust', 'Gray Apricorn', 'Revival Herb', 'Black Apricorn'], 5: ['Green Apricorn', 'White Apricorn', 'Evolutionary Stone', '5x Gourmet Poke Food Ingredients', 'Big Mushroom', 'Revival Herb', 'Energy Root', 'Type Boosting Held Item', 'Black Apricorn', 'Nugget'], 6: ['Cyan Apricorn', 'Nature Mint', 'Evolutionary Item', 'Star Piece', 'Black Apricorn', 'Revival Herb', 'Vitality Herb', 'Random Held Item', 'Balm Mushroom', '90+ Luck Check to find very rare Item']}
EVOLUTION_STONES = ['Fire Stone', 'Thunder Stone', 'Water Stone', 'Ice Stone', 'Leaf Stone', 'Moon Stone', 'Sun Stone', 'Toxin Stone', 'Precious Stone', 'Brave Stone', 'Desert Rose', 'Amber Onyx', 'Feather Stone', 'Shiny Stone', 'Dusk Stone', 'Dawn Stone', 'Adamantite Stone', 'Link Stone', 'Rune Stone']
EVOLUTION_ITEMS = ['Auspicious Armor', 'Black Augurite', 'Chipped Pot', 'Corrupted Drive', 'Cracked Pot', 'Deep Sea Scale', 'Deep Sea Tooth', 'Dragon Scale', 'Dubious Disc', 'Electirizer', 'Galarica Cuff', 'Galarica Wreath', "King's Rock", 'Magmarizer', 'Malicious Armor', 'Masterpiece Teacup', 'Metal Alloy', 'Metal Coat', 'Oval Stone', 'Peat Block', 'Prism Scale', 'Protector', 'Razor Claw', 'Razor Fang', 'Reaper Cloth', 'Sachet', 'Satellite Parts', 'Sweets [Various]', 'Sweet Apple', 'Syrupy Apple', 'Tarnished Scale', 'Tart Apple', 'Unremarkable Teacup', 'Upgrade', 'Whipped Dream']
TYPE_BOOSTING_HELD_ITEMS = ['Black Belt', 'Black Glasses', 'Charcoal', 'Draco Plate', 'Dragon Fang', 'Dread Plate', 'Earth Plate', 'Fairy Feather', 'Fist Plate', 'Flame Plate', 'Hard Stone', 'Insect Plate', 'Iron Plate', 'Magnet', 'Meadow Plate', 'Metal Coat', 'Mind Plate', 'Miracle Seed', 'Mystic Water', 'Never Melt Ice', 'Odd Incense', 'Pixie Plate', 'Poison Barb', 'Rock Incense', 'Rose Incense', 'Sea Incense', 'Sharp Beak', 'Silk Scarf', 'Silver Powder', 'Sky Plate', 'Soft Sand', 'Spell Tag', 'Splash Plate', 'Spooky Plate', 'Stone Plate', 'Toxic Plate', 'Twisted Spoon', 'Wave Incense']
NATURE_MINTS = ['Adamant Mint', 'Bold Mint', 'Brave Mint', 'Calm Mint', 'Careful Mint', 'Gentle Mint', 'Hasty Mint', 'Impish Mint', 'Jolly Mint', 'Lax Mint', 'Lonely Mint', 'Mild Mint', 'Modest Mint', 'Naive Mint', 'Naughty Mint', 'Quiet Mint', 'Rash Mint', 'Relaxed Mint', 'Sassy Mint', 'Serious Mint', 'Timid Mint']
HELD_ITEMS = ['Ability Shield', 'Air Balloon', 'Amulet Coin', 'Assault Vest', 'Big Root', 'Binding Band', 'Black Sludge', 'Blue Scarf', 'Blunder Policy', 'Bone Dice', 'Energy Booster', 'Bright Powder', 'Choice Band', 'Choice Scarf', 'Choice Specs', 'Cleanse Tag', 'Clear Amulet', 'Corroded Rock', 'Covert Cloak', 'Damp Rock', 'Deep Sea Scale', 'Deep Sea Tooth', 'Destiny Knot', 'Eject Button', 'Eject Pack', 'Everstone', 'Eviolite', 'Expert Belt', 'Flame Orb', 'Float Stone', 'Fluffy Blanket', 'Focus Band', 'Focus Sash', 'Full Incense', 'Green Scarf', 'Grip Claw', 'Heat Rock', 'Heavy-Duty Boots', 'Hypnotist’s Pendulum', 'Icy Rock', 'Iron Ball', "King's Rock", 'Lagging Tail', 'Lax Incense', 'Leek', 'Leftovers', 'Life Orb', 'Light Ball', 'Light Clay', 'Loaded Dice', 'Luck Incense', 'Lucky Egg', 'Lucky Punch', 'Macho Brace', 'Metal Powder', 'Metronome', 'Muscle Band', 'Obsidian Rock', 'Pink Scarf', 'Power Weight', 'Power Bracer', 'Power Belt', 'Power Lens', 'Power Band', 'Power Anklet', 'Protective Pads', 'Punching Gloves', 'Pure Incense', 'Quick Claw', 'Quick Powder', 'Razor Claw', 'Razor Fang', 'Red Card', 'Red Scarf', 'Ring Target', 'Rocky Helmet', 'Room Service', 'Safety Goggles', 'Scope Lens', 'Shed Shell', 'Shell Bell', 'Smoke Ball', 'Smooth Rock', 'Soothe Bell', 'Sticky Barb', 'Terrain Extender', 'Thick Club', 'Throat Spray', 'Toxic Orb', 'Utility Umbrella', 'Weakness Policy', 'Wide Lens', 'Wise Glasses', 'Yellow Scarf', 'Zoom Lens']
RARE_ITEM_TABLES = {'Mega Stone': ['(Alolan) Hatterenite',
                '(Hissuian) Zoroarkite',
                '(Orrean) Miloticite',
                '(Ruskovan) Garchompite',
                'Abomasite',
                'Absolite',
                'Absolite Z',
                'Accelgorite',
                'Aerodactylite',
                'Aggronite',
                'Alakazite',
                'Altarianite',
                'Ampharosite',
                'Arbokinite',
                'Ariadosite',
                'Audinite',
                'Azumarillite',
                'Banettite',
                'Barbaracite',
                'Baxcalibrite',
                'Beedrillite',
                'Blastoisinite',
                'Blazikenite',
                'Blisseyite',
                'Bravialite',
                'Butterfreeite',
                'Cameruptite',
                'Chandelurite',
                'Charizardite X',
                'Charizardite Y',
                'Chesnaughtite',
                'Chimechite',
                'Cinccinite',
                'Clawitzerite',
                'Clefablite',
                'Crabominite',
                'Crobatite',
                'Delphoxite',
                'Dragalgite',
                'Dragoninite',
                'Drampanite',
                'Dunborosite',
                'Elektrossite',
                'Emboarite',
                'Escavalierite',
                'Excadrite',
                'Falinksite',
                'Fauxpunnite',
                'Feraligite',
                'Floettite',
                'Froslassite',
                'Galladite',
                'Garchompite',
                'Garchompite Z',
                'Gardevoirite',
                'Gengarite',
                'Glalitite',
                'Glimmoranite',
                'Golisopite',
                'Golurkite',
                'Greninjite',
                'Gyaradosite',
                'Hawluchinite',
                'Heracronite',
                'Houndoominite',
                'Hydrappicite',
                'Indeedeerite',
                'Infernapetite',
                'Inteleonite',
                'Kangaskhanite',
                'Kinglerite',
                'Ledianite',
                'Lokixite',
                'Lopunnite',
                'Lucarionite',
                'Lucarionite Z',
                'Ludicolonite',
                'Lunatonite',
                'Lurantisite',
                'Machamptite',
                'Magnezonite',
                'Malamarite',
                'Manectite',
                'Mauseholdite',
                'Mawilite',
                'Medichamite',
                'Meganiumite',
                'Meowsicite',
                'Metagrossite',
                'Mightyenite',
                'Miloticite',
                'Mismagisite',
                'Parasectite',
                'Pidgeotite',
                'Pinsirite',
                'Pyroarite',
                'Raichunite X',
                'Raichunite Y',
                'Sablenite',
                'Salamencite',
                'Salazzlite',
                'Sceptilite',
                'Scizorite',
                'Scolipite',
                'Scovillainite',
                'Scraftinite',
                'Serpiorite',
                'Sharpedonite',
                'Skarmorite',
                'Slowbronite',
                'Slowkingite',
                'Solrockite',
                'Staraptite',
                'Starminite',
                'Steelixite',
                'Swampertite',
                'Tatsugirinite',
                'Tyranitarite',
                'Venusaurite',
                'Victreebelite',
                'Voodoomite',
                'Weavilite',
                'Weezingtite',
                'Wobbuffetite',
                'Xatunite',
                'Yanmegarite',
                'Zorarkite'],
 'Z-Crystal': ['Buginium-Z',
               'Darkinium-Z',
               'Dragonium-Z',
               'Electrium-Z',
               'Fairium-Z',
               'Fightinium-Z',
               'Firium-Z',
               'Flyinium-Z',
               'Ghostium-Z',
               'Grassium-Z',
               'Groundium-Z',
               'Icium-Z',
               'Normalium-Z',
               'Poisonium-Z',
               'Psychium-Z',
               'Rockium-Z',
               'Steelium-Z',
               'Waterium-Z'],
 'Terasta Shard': ['Terasta Bug',
                   'Terasta Dark',
                   'Terasta Dragon',
                   'Terasta Electric',
                   'Terasta Fairy',
                   'Terasta Fighting',
                   'Terasta Fire',
                   'Terasta Flying',
                   'Terasta Ghost',
                   'Terasta Grass',
                   'Terasta Ground',
                   'Terasta Ice',
                   'Terasta Poison',
                   'Terasta Psychic',
                   'Terasta Rock',
                   'Terasta Steel',
                   'Terasta Water'],
 'Crest': ['Bastiodon Crest',
           'Boltund Crest',
           'Castform Crest',
           'Champeon Crest',
           'Cofagrigus Crest',
           'Cryogonal Crest',
           'Darmanitan Crest',
           'Dedenne Crest',
           'Delcatty Crest',
           'Drakeon Crest',
           'Drifblim Crest',
           'Druddigon Crest',
           'Dusknoir Crest',
           'Dusteon Crest',
           'Eevoleon Crest',
           'Electrode Crest',
           'Empoleon Crest',
           'Espeon Crest',
           'Faerry Crest',
           'Fearow Crest',
           'Flareon Crest',
           'Flygon Crest',
           'Furret Crest',
           'Garbodor / Garbocean Crest',
           'Gigalith Crest',
           'Glaceon Crest',
           'Glaveon Crest',
           'Gothitelle Crest',
           'Hawlucha Crest',
           'Hypno Crest',
           'Jolteon Crest',
           'Kleavor Crest',
           'Lanturn Crest',
           'Leafeon Crest',
           'Luvdisc Crest',
           'Luxray Crest',
           'Magcargo Crest',
           'Mummeon Crest',
           'Nimbeon Crest',
           'Noctowl Crest',
           'Noxeon Crest',
           'Oricorio Crest',
           'Orreon Crest',
           'Pangoro Crest',
           'Papilleon Crest',
           'Probopass Crest',
           'Rampardos Crest',
           'Relicanth Crest',
           'Reuniclus Crest',
           'Roserade Crest',
           'Samurott Crest',
           'Sawsbuck Crest',
           'Seraphish Crest',
           'Seviper Crest',
           'Shiinotic Crest',
           'Simipour Crest',
           'Simipsych Crest',
           'Simisage Crest',
           'Simisear Crest',
           'Simisnear Crest',
           'Simistrike Crest',
           'Skuntank Crest',
           'Spiritomb Crest',
           'Sunflora Crest',
           'Swalot Crest',
           'Sylveon Crest',
           'Thievul Crest',
           'Torterra Crest',
           'Typhlosion Crest',
           'Umbreon Crest',
           'Vaporeon Crest',
           'Vespiquen Crest',
           'Whiscash Crest',
           'Wyrdeer Crest',
           'Zangoose Crest',
           'Zoroark Crest']}

def table_label(level): return "Six+ successes" if level == 6 else f"{level} success" + ("" if level == 1 else "es")
def tables_for_successes(successes): return [] if successes <= 0 else list(range(min(successes,6),0,-2))
def resolve_find(result):
    pools={"Evolutionary Stone":EVOLUTION_STONES,"Evolutionary Item":EVOLUTION_ITEMS,"Type Boosting Held Item":TYPE_BOOSTING_HELD_ITEMS,"Nature Mint":NATURE_MINTS,"Random Held Item":HELD_ITEMS}
    return random.choice(pools[result]) if result in pools else result


def roll_rare_item():
    category = random.choice(list(RARE_ITEM_TABLES))
    return category, random.choice(RARE_ITEM_TABLES[category])


def calculate_rare_luck_check(luck_modifier, d100_roll=None):
    """Return the natural D100 and capped total for a valid Luck Modifier."""
    if luck_modifier < 0 or luck_modifier > 100 or luck_modifier % 5:
        raise ValueError("Luck Modifier must be a multiple of 5 from 0 to 100.")
    base = random.randint(1, 100) if d100_roll is None else int(d100_roll)
    return base, apply_luck_modifier(base, luck_modifier)


class RareLuckCheckView(discord.ui.View):
    """Owner-only Luck Modifier selector for a rare Foraging result.

    A fixed select is used instead of a free-text modal because valid modifiers
    are only 0..100 in steps of 5. This also avoids Discord's generic
    sensitive/password warning on modal text inputs. The actual Luck Check
    result is posted publicly to the channel.
    """
    def __init__(self, owner_id):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.luck_select = discord.ui.Select(
            placeholder="Choose Luck Modifier to roll 1D100",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=f"Luck Modifier {modifier}",
                    value=str(modifier),
                )
                for modifier in range(0, 101, 5)
            ],
        )
        self.luck_select.callback = self.select_luck_modifier
        self.add_item(self.luck_select)

    async def select_luck_modifier(self, interaction: discord.Interaction):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Only the player who made this Foraging check can roll its Luck Check.",
                ephemeral=True,
            )
            return

        modifier = int(self.luck_select.values[0])
        base, total = calculate_rare_luck_check(modifier)

        self.luck_select.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

        lines = [
            "## 🍀 Rare Item Luck Check",
            f"**{format_luck_check(base, modifier)}**",
        ]
        if total >= 90:
            category, item = roll_rare_item()
            lines.append(f"**SUCCESS!** — {item} ({category})")
        else:
            lines.append("Failed (90+ required).")

        # Explicitly public: everyone in the channel can see the roll/result.
        await interaction.response.send_message("\n".join(lines), ephemeral=False)


class Foraging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="foraging", description="Roll an Insight + Nature check to see what you find on the foraging table")
    @app_commands.describe(dice="Number of d6s in the Insight + Nature pool")
    async def foraging(self, interaction: discord.Interaction, dice: app_commands.Range[int, 1, 50]):
        rolls = [random.randint(1, 6) for _ in range(dice)]
        successes = sum(r >= 4 for r in rolls)
        disp = ', '.join(f"**{r}**" if r >= 4 else str(r) for r in rolls)
        blocks = [
            "## 🌿 Foraging Check",
            f"**Dice Pool:** {dice}d6 (Insight + Nature)",
            f"**Rolls:** {disp}",
            f"**Successes:** **{successes}**",
        ]
        if not successes:
            blocks.append("\nNo successes — nothing useful was found.")
            await interaction.response.send_message('\n'.join(blocks))
            return

        levels = tables_for_successes(successes)
        blocks.append("\n**Foraging Rolls:** " + ', '.join(table_label(x) for x in levels))
        needs_rare_luck_check = False

        for level in levels:
            d10 = random.randint(1, 10)
            raw = FORAGING_TABLES[level][d10 - 1]
            result = resolve_find(raw)
            blocks.append(f"\n### {table_label(level)} Table\n🎲 **d10: {d10}** — {result}")
            if level == 6 and d10 == 10:
                needs_rare_luck_check = True
                blocks.append(
                    "🍀 **Rare Item Luck Check required.** Choose your Luck Modifier below "
                    "(0 to 100 in multiples of 5) to roll 1D100."
                )

        if needs_rare_luck_check:
            view = RareLuckCheckView(interaction.user.id)
            await interaction.response.send_message('\n'.join(blocks), view=view)
        else:
            await interaction.response.send_message('\n'.join(blocks))


async def setup(bot):
    await bot.add_cog(Foraging(bot))
