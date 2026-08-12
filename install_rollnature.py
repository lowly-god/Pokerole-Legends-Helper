from pathlib import Path
import re

BOT_FILE = Path("PokeRole-Helper.py")

if not BOT_FILE.exists():
    raise SystemExit("PokeRole-Helper.py was not found. Run this installer from the main bot folder.")

text = BOT_FILE.read_text(encoding="utf-8")

if "'natureRollCog'" in text or '"natureRollCog"' in text:
    print("natureRollCog is already installed.")
    raise SystemExit(0)

pattern = re.compile(r"^cogs\s*=\s*\[(.*?)\]\s*$", re.MULTILINE)
match = pattern.search(text)

if not match:
    raise SystemExit("Could not find the cogs = [...] line in PokeRole-Helper.py.")

inside = match.group(1)

if "'custom_help'" in inside:
    new_inside = inside.replace("'custom_help'", "'natureRollCog', 'custom_help'")
elif '"custom_help"' in inside:
    new_inside = inside.replace('"custom_help"', "'natureRollCog', \"custom_help\"")
else:
    new_inside = inside.rstrip() + ", 'natureRollCog'"

new_text = text[:match.start(1)] + new_inside + text[match.end(1):]

backup = Path("PokeRole-Helper.py.before_rollnature.bak")
if not backup.exists():
    backup.write_text(text, encoding="utf-8")

BOT_FILE.write_text(new_text, encoding="utf-8")

print("Installed natureRollCog.")
print("Restart the bot, then run %sync_global in Discord.")
