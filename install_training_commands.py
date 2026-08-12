from pathlib import Path
import re
import shutil

BOT_FILE = Path("PokeRole-Helper.py")
if not BOT_FILE.exists():
    raise SystemExit("PokeRole-Helper.py not found. Run this from the main bot folder.")

text = BOT_FILE.read_text(encoding="utf-8")

backup = Path("PokeRole-Helper.py.before_training_commands.bak")
if not backup.exists():
    shutil.copy2(BOT_FILE, backup)

if "'trainingReferenceCog'" not in text and '"trainingReferenceCog"' not in text:
    match = re.search(r"^cogs\s*=\s*\[(.*?)\]\s*$", text, re.MULTILINE)
    if not match:
        raise SystemExit("Could not find cogs = [...] in PokeRole-Helper.py.")

    inside = match.group(1)

    if "'custom_help'" in inside:
        inside = inside.replace(
            "'custom_help'",
            "'trainingReferenceCog', 'custom_help'"
        )
    elif '"custom_help"' in inside:
        inside = inside.replace(
            '"custom_help"',
            "'trainingReferenceCog', \"custom_help\""
        )
    else:
        inside = inside.rstrip() + ", 'trainingReferenceCog'"

    text = text[:match.start(1)] + inside + text[match.end(1):]
    BOT_FILE.write_text(text, encoding="utf-8")

print("Installed trainingReferenceCog.")
print("Restart the bot, then run %sync_global.")
