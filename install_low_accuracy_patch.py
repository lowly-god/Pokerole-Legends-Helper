from pathlib import Path
import json
import re
import shutil

ROOT = Path(".")
MOVES_DIR = ROOT / "pokerole_data" / "v3.0" / "Moves"
DB_FILE = ROOT / "pokerole_v3.db"
BACKUP_DIR = ROOT / "low_accuracy_patch_backups"

if not MOVES_DIR.exists():
    raise SystemExit(
        "Could not find pokerole_data/v3.0/Moves. "
        "Put this installer in the bot's main folder."
    )

BACKUP_DIR.mkdir(exist_ok=True)

# Handles common variants:
# Low Accuracy 2
# Low Accuracy: 2
# Low Accuracy -2
# Low Accuracy x2
# low accuracy 2
PATTERN = re.compile(
    r"\bLow\s+Accuracy\s*(?::\s*)?(?:x\s*)?-?\s*(\d+)\b",
    re.IGNORECASE
)

def replace_in_value(value):
    replacements = 0

    if isinstance(value, str):
        def repl(match):
            nonlocal replacements
            replacements += 1
            return f"Accuracy -{match.group(1)}"
        return PATTERN.sub(repl, value), replacements

    if isinstance(value, list):
        new_list = []
        for item in value:
            new_item, count = replace_in_value(item)
            replacements += count
            new_list.append(new_item)
        return new_list, replacements

    if isinstance(value, dict):
        new_dict = {}
        for key, item in value.items():
            new_item, count = replace_in_value(item)
            replacements += count
            new_dict[key] = new_item
        return new_dict, replacements

    return value, 0


changed_moves = []
total_replacements = 0

for path in sorted(MOVES_DIR.glob("*.json")):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Skipping unreadable JSON: {path.name} ({exc})")
        continue

    updated, count = replace_in_value(data)

    if not count:
        continue

    backup_path = BACKUP_DIR / path.name
    if not backup_path.exists():
        shutil.copy2(path, backup_path)

    path.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    move_name = data.get("Name", path.stem)
    changed_moves.append((move_name, count))
    total_replacements += count


# /move and related commands use the rebuilt v3 database.
if changed_moves and DB_FILE.exists():
    DB_FILE.unlink()

report = ROOT / "low_accuracy_patch_report.txt"
with report.open("w", encoding="utf-8") as f:
    f.write("LOW ACCURACY -> ACCURACY PATCH REPORT\n")
    f.write("=====================================\n\n")
    f.write(f"Moves changed: {len(changed_moves)}\n")
    f.write(f"Text replacements: {total_replacements}\n\n")
    for name, count in changed_moves:
        f.write(f"{name}: {count}\n")

print()
print("LOW ACCURACY TERMINOLOGY PATCH COMPLETE")
print("---------------------------------------")
print(f"Moves changed: {len(changed_moves)}")
print(f"Text replacements made: {total_replacements}")
print()

if changed_moves:
    print("Changed moves:")
    for name, count in changed_moves:
        suffix = "change" if count == 1 else "changes"
        print(f"  {name} ({count} {suffix})")
    print()
    print("pokerole_v3.db removed so the move data rebuilds on next normal startup.")
else:
    print("No remaining 'Low Accuracy X' text was found.")
    print("No database rebuild was required.")

print()
print("A report was written to low_accuracy_patch_report.txt")
print("No %sync_global is required.")
