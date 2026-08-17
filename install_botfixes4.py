from pathlib import Path
import re

item_dir = Path("pokerole_data") / "v3.0" / "Items"

for filename in (
    "Power Increasers [Various].json",
    "Power Increasers.json",
    "Garbocean Crest.json",
    "Manaphy Crest.json",
):
    path = item_dir / filename
    if path.exists():
        path.unlink()
        print(f"Removed obsolete item file: {path}")

# HM-designated moves must not survive as TM/TR items from earlier patches.
hm_only_moves = {
    'Cut', 'Defog', 'Dive', 'Flash', 'Fly', 'Magma Drift', 'Rock Climb',
    'Rock Smash', 'Strength', 'Surf', 'Teleport', 'Waterfall', 'Whirlpool',
}
for move_name in hm_only_moves:
    for suffix in ('TM', 'TR'):
        path = item_dir / f'{move_name} - {suffix}.json'
        if path.exists():
            path.unlink()
            print(f'Removed HM-conflicting machine item file: {path}')

# Remove every deprecated prefix-format machine item left behind by older
# installs. Current machine names are "Move Name - TM/TR/HM".
if item_dir.is_dir():
    for path in item_dir.glob("*.json"):
        if re.match(r"^(?:TM|TR|HM) - .+\.json$", path.name, flags=re.I):
            path.unlink()
            print(f"Removed obsolete machine item file: {path}")

# Force the one-time guild slash-command cleanup to run again after this patch.
cleanup_marker = Path(".slash_guild_duplicates_cleaned_v2")
if cleanup_marker.exists():
    cleanup_marker.unlink()
    print(f"Removed stale slash cleanup marker: {cleanup_marker}")

print(
    "Botfixes cleanup complete. Restart the bot so its v3.0 database refreshes "
    "from the patched JSON and Discord refreshes the patched slash-command shape."
)
