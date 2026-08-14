from pathlib import Path
import csv
import re
import shutil

STATUS_FILE = Path("status_v3.csv")
MISC_FILE = Path("miscCommands.py")

if not STATUS_FILE.exists():
    raise SystemExit("status_v3.csv was not found. Run this from the main Pokerole Legends Helper folder.")
if not MISC_FILE.exists():
    raise SystemExit("miscCommands.py was not found. Run this from the main Pokerole Legends Helper folder.")

# Backups
status_backup = Path("status_v3.csv.before_legends_statuses.bak")
misc_backup = Path("miscCommands.py.before_legends_statuses.bak")

if not status_backup.exists():
    shutil.copy2(STATUS_FILE, status_backup)
if not misc_backup.exists():
    shutil.copy2(MISC_FILE, misc_backup)

# Read and preserve all unrelated current statuses.
with STATUS_FILE.open("r", encoding="UTF-8", newline="") as f:
    rows = list(csv.reader(f))

replace_names = {
    "1st Degree Burn",
    "2nd Degree Burn",
    "3rd Degree Burn",
    "Burn 1",
    "Burn 2",
    "Burn 3",
    "Frozen Solid",
    "Frostbite 1",
    "Frostbite 2",
    "Frostbite 3",
    "Charmed",
    "Disarmed",
    "Exhausted",
    "Leeched",
    "Petrified",
    "Ongoing Damage",
}

rows = [row for row in rows if row and row[0] not in replace_names]

new_rows = [
    [
        "Burn 1",
        "The character is suffering from a minor but painful burn.",
        "Effect: Strength is reduced by 1.",
        "End of Round: Suffer 1 Damage."
    ],
    [
        "Burn 2",
        "The character is suffering from a severe burn.",
        "Effect: Strength is reduced by 1.",
        "End of Round: Suffer 2 Lethal Damage."
    ],
    [
        "Burn 3",
        "The character is suffering from an extreme burn.",
        "Effect: Strength is reduced by 1.",
        "End of Round: Suffer 3 Lethal Damage."
    ],
    [
        "Charmed",
        "",
        "Effect: Characters suffering from the Charmed Status act in the interest of the one who Charmed them.",
        "Allegiance: While Charmed, characters are treated as being an Ally to the one who Charmed them.",
        "Resist: Before taking an Action, roll current Will DC6. These are cumulative rolls.",
        "Help: Another Character may use an Action to give a Charmed Ally 2 Bonus Dice to their Resist Roll.",
        "Example: A character under the Storyteller’s control inflicts Charmed on a player controlled character. The player controlled character might attack one of their allies, recall a Pokémon or spend Actions in any other way that is commanded by the Storyteller controlled character, until they meet the resist DC, whereupon they may act normally again."
    ],
    [
        "Disarmed",
        "",
        "Effect: Human Active Combatants drop their Weapon(s). Pokémon drop their Held Item.",
        "Recovery: An Active Combatant may spend an Action to re-equip their Weapon or Held Item.",
        "Dropped Item: Other Active Combatants may also pick it up while it is dropped."
    ],
    [
        "Exhausted",
        "",
        "Effect: For each Level of Exhaustion a character suffers, they have -1 successes to all their rolls.",
        "Severe Exhaustion: If a character has 3 or more Levels of Exhaustion they take 1 point of Lethal Damage for each day that they do not rectify this, taking one additional Damage for each Level above 3.",
        "Recovery: Recover 1 Level of Exhaustion by eating and drinking properly and having a decent sleep in a safe location, or by other means at the Storyteller’s discretion, such as a Pokémon’s Moves."
    ],
    [
        "Frostbite 1",
        "Replaces the Frozen Status Condition.",
        "Effect: Special is reduced by 1.",
        "End of Round: Suffer 1 Damage."
    ],
    [
        "Frostbite 2",
        "Replaces the Frozen Status Condition.",
        "Effect: Special is reduced by 1.",
        "End of Round: Suffer 2 Lethal Damage."
    ],
    [
        "Frostbite 3",
        "Replaces the Frozen Status Condition.",
        "Effect: Special is reduced by 1.",
        "End of Round: Suffer 3 Lethal Damage."
    ],
    [
        "Leeched",
        "",
        "End of Round: Lose 1 HP.",
        "Drain: The Foe that caused the Leeched Status heals 1 HP."
    ],
    [
        "Petrified",
        "",
        "End of Round: Dexterity is reduced by 1.",
        "Zero Dexterity: If a Character reaches 0 Dexterity from this Status, they take Damage equal to their remaining HP +1."
    ],
    [
        "Ongoing Damage",
        "",
        "Effect: At the end of the Round, Roll 2 Dice of Typeless Damage against the Target. (Multiple sources of Ongoing Damage will not stack, only one source may be active at a time. The first source takes priority over the latter ones)."
    ],
]

rows.extend(new_rows)

with STATUS_FILE.open("w", encoding="UTF-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerows(rows)

# Keep the legacy hard-coded status list consistent too, even though v3 autocomplete
# reads directly from status_v3.csv.
text = MISC_FILE.read_text(encoding="utf-8")

new_statuses = """statuses = [
    'Burn 1',
    'Burn 2',
    'Burn 3',
    'Paralysis',
    'Frostbite 1',
    'Frostbite 2',
    'Frostbite 3',
    'Poison',
    'Badly Poisoned',
    'Sleep',
    'Flinched',
    'Confused',
    'Disabled',
    'In Love',
    'Blocked',
    'Charmed',
    'Disarmed',
    'Exhausted',
    'Leeched',
    'Petrified',
    'Ongoing Damage'
]"""

pattern = re.compile(r"statuses\s*=\s*\[.*?\]\s*\n", re.S)
match = pattern.search(text)
if not match:
    raise SystemExit("Updated status_v3.csv, but could not find statuses = [...] in miscCommands.py.")

text = text[:match.start()] + new_statuses + "\n" + text[match.end():]
MISC_FILE.write_text(text, encoding="utf-8")

print("Legends 3.0 statuses installed.")
print("Removed: 1st/2nd/3rd Degree Burn and Frozen Solid.")
print("Added/updated: Burn 1-3, Frostbite 1-3, Charmed, Disarmed, Exhausted, Leeched, Petrified, Ongoing Damage.")
print("Restart the bot. No database rebuild or %sync_global is required.")
