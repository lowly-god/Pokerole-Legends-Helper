from pathlib import Path

for rel in [
    "pokerole_data/v3.0/Items/Power Increasers [Various].json",
    "pokerole_data/v3.0/Items/Power Increasers.json",
]:
    p = Path(rel)
    if p.exists():
        p.unlink()
        print(f"Removed obsolete item file: {rel}")

# Force the one-time guild slash-command cleanup to run again after this patch,
# in case an older guild-scoped /encounter_table registration still exists.
cleanup_marker = Path(".slash_guild_duplicates_cleaned_v2")
if cleanup_marker.exists():
    cleanup_marker.unlink()
    print(f"Removed stale slash cleanup marker: {cleanup_marker}")

print(
    "Botfixes cleanup complete. Restart the bot so its v3.0 database refreshes "
    "from the patched JSON and Discord refreshes the patched slash-command shape."
)
