from pathlib import Path
import re

BOT_FILE = Path("PokeRole-Helper.py")

if not BOT_FILE.exists():
    raise SystemExit("PokeRole-Helper.py was not found. Run this installer from the main bot folder.")

text = BOT_FILE.read_text(encoding="utf-8")

if "'maneuverCog'" in text or '"maneuverCog"' in text:
    print("maneuverCog is already present in the bot's cog list. Nothing to change.")
    raise SystemExit(0)

pattern = re.compile(r"^cogs\s*=\s*\[(.*?)\]\s*$", re.MULTILINE)
match = pattern.search(text)

if not match:
    raise SystemExit("Could not find the cogs = [...] line in PokeRole-Helper.py.")

inside = match.group(1)

# custom_help is documented by the original bot as needing to load last.
if "'custom_help'" in inside:
    new_inside = inside.replace("'custom_help'", "'maneuverCog', 'custom_help'")
elif '"custom_help"' in inside:
    new_inside = inside.replace('"custom_help"', "'maneuverCog', \"custom_help\"")
else:
    new_inside = inside.rstrip() + ", 'maneuverCog'"

new_text = text[:match.start(1)] + new_inside + text[match.end(1):]

backup = BOT_FILE.with_suffix(".py.before_maneuvers.bak")
backup.write_text(text, encoding="utf-8")
BOT_FILE.write_text(new_text, encoding="utf-8")

print("Installed maneuverCog into PokeRole-Helper.py.")
print(f"Backup created: {backup.name}")
print("Restart the bot, then run %sync_global in Discord.")
