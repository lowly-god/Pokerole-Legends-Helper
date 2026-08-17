from pathlib import Path

for rel in [
    "pokerole_data/v3.0/Items/Power Increasers [Various].json",
    "pokerole_data/v3.0/Items/Power Increasers.json",
]:
    p = Path(rel)
    if p.exists():
        p.unlink()
        print(f"Removed obsolete item file: {rel}")
print("Botfixes(4) cleanup complete. Restart the bot so its v3.0 database refreshes from the patched JSON.")
