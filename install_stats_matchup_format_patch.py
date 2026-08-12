from pathlib import Path
import shutil

TARGET = Path("statsExtra.py")

if not TARGET.exists():
    raise SystemExit(
        "statsExtra.py was not found. Put this installer in the bot's main folder."
    )

text = TARGET.read_text(encoding="utf-8")

backup = Path("statsExtra.py.before_matchup_format_patch.bak")
if not backup.exists():
    shutil.copy2(TARGET, backup)

changed = 0

replacements = [
    ('parts.append(f"{level}x " + ", ".join(groups[level]))',
     'parts.append(f"{level}x " + " ".join(groups[level]))'),
    ('return " | ".join(parts)',
     'return " ".join(parts)'),
    ('", ".join(immunities) if immunities else "None"',
     '" ".join(immunities) if immunities else "None"'),
    ('f"{level}x " + ", ".join(grouped[level])',
     'f"{level}x " + " ".join(grouped[level])'),
    ('return " | ".join(',
     'return " ".join('),
]

for old, new in replacements:
    if old in text:
        text = text.replace(old, new)
        changed += 1

if changed == 0:
    if '", ".join' not in text and '" | ".join' not in text:
        print("Formatting already appears to be updated. No changes needed.")
        raise SystemExit(0)
    raise SystemExit(
        "Could not safely find the matchup formatting code in statsExtra.py. "
        "No changes were written."
    )

compile(text, str(TARGET), "exec")
TARGET.write_text(text, encoding="utf-8")

print()
print("STATS MATCHUP FORMAT PATCH COMPLETE")
print("---------------------------------")
print("Weaknesses, Resistances and Immunities now use spaces only.")
print()
print("Example:")
print("Resistances: 2x Normal Flying 1x Ice Psychic Bug Rock Dragon Fairy")
print()
print("No database rebuild and no %sync_global are required.")
print("Restore PokeRole-Helper.py as the startup file and start the bot normally.")
