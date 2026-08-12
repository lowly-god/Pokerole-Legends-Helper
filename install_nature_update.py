from pathlib import Path
import re

FILE = Path("miscCommands.py")
if not FILE.exists():
    raise SystemExit("miscCommands.py was not found. Run this from the main Pokerole Legends Helper folder.")

text = FILE.read_text(encoding="utf-8")
backup = Path("miscCommands.py.before_nature_update.bak")
if not backup.exists():
    backup.write_text(text, encoding="utf-8")

NATURE_DETAILS = {'Adamant': {'roll': '1-4', 'modifier': '+1 Maximum Strength, -1 Maximum Special', 'confidence': 4}, 'Bashful': {'roll': '5-8', 'modifier': 'Neutral', 'confidence': 6}, 'Bold': {'roll': '9-12', 'modifier': '+1 Maximum Vitality, -1 Maximum Strength', 'confidence': 9}, 'Brave': {'roll': '13-16', 'modifier': '+1 Maximum Strength, -1 Maximum Dexterity', 'confidence': 9}, 'Calm': {'roll': '17-20', 'modifier': '+1 Maximum Insight, -1 Maximum Strength', 'confidence': 8}, 'Careful': {'roll': '21-24', 'modifier': '+1 Maximum Insight, -1 Maximum Special', 'confidence': 5}, 'Docile': {'roll': '25-28', 'modifier': 'Neutral', 'confidence': 7}, 'Gentle': {'roll': '29-32', 'modifier': '+1 Maximum Insight, -1 Maximum Vitality', 'confidence': 10}, 'Hardy': {'roll': '33-36', 'modifier': 'Neutral', 'confidence': 9}, 'Hasty': {'roll': '37-40', 'modifier': '+1 Maximum Dexterity, -1 Maximum Vitality', 'confidence': 7}, 'Impish': {'roll': '41-44', 'modifier': '+1 Maximum Vitality, -1 Maximum Special', 'confidence': 7}, 'Jolly': {'roll': '45-48', 'modifier': '+1 Maximum Dexterity, -1 Maximum Special', 'confidence': 10}, 'Lax': {'roll': '49-52', 'modifier': '+1 Maximum Vitality, -1 Maximum Insight', 'confidence': 8}, 'Lonely': {'roll': '53-56', 'modifier': '+1 Maximum Strength, -1 Maximum Vitality', 'confidence': 5}, 'Mild': {'roll': '57-60', 'modifier': '+1 Maximum Special, -1 Maximum Vitality', 'confidence': 8}, 'Modest': {'roll': '61-64', 'modifier': '+1 Maximum Special, -1 Maximum Strength', 'confidence': 10}, 'Naive': {'roll': '65-68', 'modifier': '+1 Maximum Dexterity, -1 Maximum Insight', 'confidence': 7}, 'Naughty': {'roll': '69-72', 'modifier': '+1 Maximum Strength, -1 Maximum Insight', 'confidence': 6}, 'Quiet': {'roll': '73-76', 'modifier': '+1 Maximum Special, -1 Maximum Dexterity', 'confidence': 5}, 'Quirky': {'roll': '77-80', 'modifier': 'Neutral', 'confidence': 9}, 'Rash': {'roll': '81-84', 'modifier': '+1 Maximum Special, -1 Maximum Insight', 'confidence': 6}, 'Relaxed': {'roll': '85-88', 'modifier': '+1 Maximum Vitality, -1 Maximum Dexterity', 'confidence': 8}, 'Sassy': {'roll': '89-92', 'modifier': '+1 Maximum Insight, -1 Maximum Dexterity', 'confidence': 7}, 'Serious': {'roll': '93-96', 'modifier': 'Neutral', 'confidence': 4}, 'Timid': {'roll': '97-100', 'modifier': '+1 Maximum Dexterity, -1 Maximum Strength', 'confidence': 4}}

# Insert/replace the data block immediately after the existing natures list.
block = "\n# Legends 3.0 nature mechanics\nNATURE_DETAILS = " + repr(NATURE_DETAILS) + "\n"

if "# Legends 3.0 nature mechanics" in text:
    text = re.sub(
        r'\n# Legends 3\.0 nature mechanics\nNATURE_DETAILS = .*?\n(?=effects = \[)',
        block,
        text,
        flags=re.S
    )
else:
    marker = "]\neffects = ["
    if marker not in text:
        raise SystemExit("Could not locate the natures/effects section in miscCommands.py.")
    text = text.replace(marker, "]" + block + "effects = [", 1)

old = """        if nature == '':
            #list all nature
            for k, v in list(self.nature.items()):
                output += f'**{k}**{naturerepl}\\t-*{v[0]}*\\n'
        else:
            #list a single nature description
            nature = nature.title()
            if nature in self.nature:
                effect = self.nature[nature][1]
                output = f'**{nature}**\\n*{self.nature[nature][0]}*{naturerepl}\\n{effect}'
            else:
                output = f'`{nature}` wasn\\'t found in the nature list:{naturerepl}'\\
                          + naturerepl.join([str(k) for k in self.nature.keys()])
"""

new = """        if nature == '':
            # list all natures with their Legends mechanical information
            for k, v in list(self.nature.items()):
                details = NATURE_DETAILS.get(k, {})
                roll = details.get('roll', '?')
                modifier = details.get('modifier', 'Unknown')
                confidence = details.get('confidence', '?')
                output += (
                    f'**{k}** ({roll})\\n'
                    f'\\t-*{v[0]}*\\n'
                    f'\\t- {modifier} | **Confidence {confidence}**\\n'
                )
        else:
            # list a single nature description plus Legends mechanics
            nature = nature.title()
            if nature in self.nature:
                effect = self.nature[nature][1]
                details = NATURE_DETAILS.get(nature, {})
                roll = details.get('roll', '?')
                modifier = details.get('modifier', 'Unknown')
                confidence = details.get('confidence', '?')
                output = (
                    f'**{nature}**  |  Roll **{roll}**\\n'
                    f'*{self.nature[nature][0]}*\\n\\n'
                    f'**Maximum Attributes:** {modifier}\\n'
                    f'**Confidence:** {confidence}\\n\\n'
                    f'{effect}'
                )
            else:
                output = f'`{nature}` wasn\\'t found in the nature list:{naturerepl}'\\
                          + naturerepl.join([str(k) for k in self.nature.keys()])
"""

if old not in text:
    if "Maximum Attributes:" in text and "NATURE_DETAILS" in text:
        print("Nature display patch appears to already be installed.")
        FILE.write_text(text, encoding="utf-8")
        raise SystemExit(0)
    raise SystemExit("Could not find the expected nature_func block. Your miscCommands.py may differ from the current helper.")

text = text.replace(old, new, 1)
FILE.write_text(text, encoding="utf-8")

print("Nature update installed successfully.")
print("Backup created:", backup)
print("Restart the bot. No database rebuild is needed.")
