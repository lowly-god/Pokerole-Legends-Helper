from pathlib import Path
import re
import shutil

BOT_FILE = Path("PokeRole-Helper.py")
if not BOT_FILE.exists():
    raise SystemExit("PokeRole-Helper.py was not found. Run this from the main bot folder.")

text = BOT_FILE.read_text(encoding="utf-8")
backup = Path("PokeRole-Helper.py.before_encountertables.bak")
if not backup.exists():
    shutil.copy2(BOT_FILE, backup)

# 1) Change bot presence.
old_presence_patterns = [
    "discord.Game(name='with wild pokemon!')",
    'discord.Game(name="with wild pokemon!")',
    "discord.Game(name='with Wild Pokemon')",
    'discord.Game(name="with Wild Pokemon")',
    "discord.Game(name='with wild pokemon')",
    'discord.Game(name="with wild pokemon")',
]
presence_changed = False
for old in old_presence_patterns:
    if old in text:
        text = text.replace(old, "discord.Game(name='Bzzzt! Spiritomb!')")
        presence_changed = True

# Fallback: specifically replace the Game name on the change_presence line.
if not presence_changed:
    new_text, n = re.subn(
        r"(await\s+bot\.change_presence\s*\(\s*activity\s*=\s*discord\.Game\s*\(\s*name\s*=\s*)['\\\"][^'\\\"]*wild pokemon!?['\\\"](\s*\)\s*\))",
        r"\1'Bzzzt! Spiritomb!'\2",
        text,
        flags=re.IGNORECASE
    )
    if n:
        text = new_text
        presence_changed = True

# 2) Remove old /rank hybrid command while leaving rank helpers/constants used elsewhere intact.
rank_pattern = re.compile(
    r"(?ms)^@bot\.hybrid_command\(\s*\n"
    r"\s*name\s*=\s*['\"]rank['\"].*?"
    r"(?=^@(?:bot|app_commands|commands)\.|^async\s+def\s+|^def\s+|\Z)"
)
text, rank_removed = rank_pattern.subn("", text, count=1)

# 3) Add encounter table cog before custom_help.
if "'encounterTableCog'" not in text and '"encounterTableCog"' not in text:
    match = re.search(r"^cogs\s*=\s*\[(.*?)\]\s*$", text, re.MULTILINE)
    if not match:
        raise SystemExit("Could not find cogs = [...] in PokeRole-Helper.py.")

    inside = match.group(1)
    if "'custom_help'" in inside:
        inside = inside.replace("'custom_help'", "'encounterTableCog', 'custom_help'")
    elif '"custom_help"' in inside:
        inside = inside.replace('"custom_help"', "'encounterTableCog', \"custom_help\"")
    else:
        inside = inside.rstrip() + ", 'encounterTableCog'"

    text = text[:match.start(1)] + inside + text[match.end(1):]

BOT_FILE.write_text(text, encoding="utf-8")

print("Encounter table update installed.")
print(f"Bot status changed: {'yes' if presence_changed else 'NOT FOUND - check presence line manually'}")
print(f"Old /rank command removed: {'yes' if rank_removed else 'NOT FOUND - it may already be removed'}")
print("Restart the bot, then run %sync_global.")
