from pathlib import Path
import json
import re

item_dir = Path("pokerole_data") / "v3.0" / "Items"


# Normalize legacy aliases before deleting duplicates. Canonical Mega Stone
# records keep their cleaner canonical descriptions where available, while
# inheriting the numeric price from the older misspelled priced record.
canonical_item_renames = {
    'Alakazamite': 'Alakazite',
    'Altarionite': 'Altarianite',
    'Amphorosite': 'Ampharosite',
    'Banetite': 'Banettite',
    'Beedrilite': 'Beedrillite',
    'Blastoisonite': 'Blastoisinite',
    'Kangaskahnite': 'Kangaskhanite',
    'Salamancite': 'Salamencite',
    'Mewtownite X': 'Mewtwonite X',
    'Mewtownite Y': 'Mewtwonite Y',
}

def _slug_item_name(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

for old_name, new_name in canonical_item_renames.items():
    old_path = item_dir / f'{old_name}.json'
    new_path = item_dir / f'{new_name}.json'
    if not old_path.exists():
        continue
    try:
        with old_path.open('r', encoding='utf-8') as f:
            old_data = json.load(f)
        if new_path.exists():
            with new_path.open('r', encoding='utf-8') as f:
                new_data = json.load(f)
        else:
            new_data = dict(old_data)
        old_price = str(old_data.get('TrainerPrice', '')).strip()
        if old_price and old_price.lower() not in {'n/a', 'not for sale', 'none'}:
            new_data['TrainerPrice'] = old_price
        new_data['Name'] = new_name
        new_data['_id'] = _slug_item_name(new_name)
        with new_path.open('w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
            f.write('\n')
        old_path.unlink()
        print(f'Normalized item source: {old_name} -> {new_name}')
    except Exception as exc:
        print(f'Could not normalize {old_name}: {exc}')

for filename in (
    'Garbocean Crest.json',
    'Manaphy Crest.json',
    'Power Increasers [Various].json',
    'Power Increasers.json',
    'Fishing Rod.json',
    'Greatball.json',
    'Pokeball.json',
    'Ultraball.json',
    'Masterball.json',
    'Never-Melt Ice.json',
    'Kings Rock.json',
    'Bugium-Z.json',
    'Darkium-Z.json',
    'Buginium Z.json',
    'Darkinium Z.json',
    'Dragonium Z.json',
    'Electrium Z.json',
    'Fairium Z.json',
    'Fightinium Z.json',
    'Firium Z.json',
    'Flyinium Z.json',
    'Ghostium Z.json',
    'Grassium Z.json',
    'Groundium Z.json',
    'Icium Z.json',
    'Poisonium Z.json',
    'Psychium Z.json',
    'Rockium Z.json',
    'Steelium Z.json',
    'Waterium Z.json',
    'Normalium Z.json',
    'Alakazamite.json',
    'Altarionite.json',
    'Amphorosite.json',
    'Banetite.json',
    'Beedrilite.json',
    'Blastoisonite.json',
    'Kangaskahnite.json',
    'Salamancite.json',
    'Mewtownite X.json',
    'Mewtownite Y.json',
    'Telekenis - TM.json',
    'Telekenis - TR.json',
    'Telekenis - HM.json',
    'TM - Telekenis.json',
    'TR - Telekenis.json',
    'HM - Telekenis.json',
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
