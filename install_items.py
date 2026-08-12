from pathlib import Path
import shutil

src = Path("Pokerole_Legends_Items") / "Items"
# Also support running with the Items folder directly beside this installer.
if not src.exists():
    src = Path("Items")

dest = Path("pokerole_data") / "v3.0" / "Items"
if not dest.exists():
    raise SystemExit("Could not find pokerole_data\\v3.0\\Items. Run this from the main bot folder.")

backup = Path("pokerole_data") / "v3.0" / "Items_before_legends_backup"
backup.mkdir(exist_ok=True)

count = 0
updated = 0
added = 0
for file in src.glob("*.json"):
    target = dest / file.name
    if target.exists():
        backup_target = backup / file.name
        if not backup_target.exists():
            shutil.copy2(target, backup_target)
        updated += 1
    else:
        added += 1
    shutil.copy2(file, target)
    count += 1

print(f"Installed {count} Legends item files ({updated} updated, {added} added).")
print("Next: delete pokerole_v3.db, then restart the bot.")
