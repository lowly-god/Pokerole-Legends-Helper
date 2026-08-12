from pathlib import Path
import re, shutil

bot_file = Path("PokeRole-Helper.py")
if not bot_file.exists():
    raise SystemExit("PokeRole-Helper.py not found. Run this from the main bot folder.")

text = bot_file.read_text(encoding="utf-8")
backup = Path("PokeRole-Helper.py.before_shops.bak")
if not backup.exists():
    shutil.copy2(bot_file, backup)

if "'shopCog'" in text or '"shopCog"' in text:
    print("shopCog is already installed.")
    raise SystemExit(0)

match = re.search(r"^cogs\s*=\s*\[(.*?)\]\s*$", text, re.MULTILINE)
if not match:
    raise SystemExit("Could not find cogs = [...] in PokeRole-Helper.py.")

inside = match.group(1)
if "'custom_help'" in inside:
    inside = inside.replace("'custom_help'", "'shopCog', 'custom_help'")
elif '"custom_help"' in inside:
    inside = inside.replace('"custom_help"', "'shopCog', \"custom_help\"")
else:
    inside = inside.rstrip() + ", 'shopCog'"

text = text[:match.start(1)] + inside + text[match.end(1):]
bot_file.write_text(text, encoding="utf-8")

print("Installed shopCog.")
print("Restart the bot, then run %sync_global.")
