from pathlib import Path
import json
import re

item_dir = Path("pokerole_data") / "v3.0" / "Items"
normalized_count = 0
removed_count = 0
error_count = 0

canonical_item_renames = {
    'Alakazamite': 'Alakazite', 'Altarionite': 'Altarianite',
    'Amphorosite': 'Ampharosite', 'Banetite': 'Banettite',
    'Beedrilite': 'Beedrillite', 'Blastoisonite': 'Blastoisinite',
    'Kangaskahnite': 'Kangaskhanite', 'Salamancite': 'Salamencite',
    'Mewtownite X': 'Mewtwonite X', 'Mewtownite Y': 'Mewtwonite Y',
}


def _slug_item_name(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


for old_name, new_name in canonical_item_renames.items():
    old_path = item_dir / f'{old_name}.json'
    new_path = item_dir / f'{new_name}.json'
    if not old_path.exists():
        continue
    try:
        old_data = json.loads(old_path.read_text(encoding='utf-8'))
        new_data = json.loads(new_path.read_text(encoding='utf-8')) if new_path.exists() else dict(old_data)
        old_price = str(old_data.get('TrainerPrice', '')).strip()
        if old_price and old_price.lower() not in {'n/a', 'not for sale', 'none'}:
            new_data['TrainerPrice'] = old_price
        new_data['Name'] = new_name
        new_data['_id'] = _slug_item_name(new_name)
        new_path.write_text(json.dumps(new_data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        old_path.unlink()
        normalized_count += 1
    except Exception as exc:
        error_count += 1
        print(f'Could not normalize {old_name}: {exc}')

obsolete_files = (
    'Garbocean Crest.json', 'Manaphy Crest.json',
    'Power Increasers [Various].json', 'Power Increasers.json',
    'Fishing Rod.json', 'Greatball.json', 'Pokeball.json', 'Ultraball.json',
    'Masterball.json', 'Never-Melt Ice.json', 'Kings Rock.json',
    'Bugium-Z.json', 'Darkium-Z.json', 'Buginium Z.json', 'Darkinium Z.json',
    'Dragonium Z.json', 'Electrium Z.json', 'Fairium Z.json', 'Fightinium Z.json',
    'Firium Z.json', 'Flyinium Z.json', 'Ghostium Z.json', 'Grassium Z.json',
    'Groundium Z.json', 'Icium Z.json', 'Poisonium Z.json', 'Psychium Z.json',
    'Rockium Z.json', 'Steelium Z.json', 'Waterium Z.json', 'Normalium Z.json',
    'Alakazamite.json', 'Altarionite.json', 'Amphorosite.json', 'Banetite.json',
    'Beedrilite.json', 'Blastoisonite.json', 'Kangaskahnite.json',
    'Salamancite.json', 'Mewtownite X.json', 'Mewtownite Y.json',
    'Telekenis - TM.json', 'Telekenis - TR.json', 'Telekenis - HM.json',
    'TM - Telekenis.json', 'TR - Telekenis.json', 'HM - Telekenis.json',
)
for filename in obsolete_files:
    path = item_dir / filename
    if path.exists():
        try:
            path.unlink()
            removed_count += 1
        except Exception as exc:
            error_count += 1
            print(f'Could not remove {filename}: {exc}')

hm_only_moves = {
    'Cut', 'Defog', 'Dive', 'Flash', 'Fly', 'Magma Drift', 'Rock Climb',
    'Rock Smash', 'Strength', 'Surf', 'Teleport', 'Waterfall', 'Whirlpool',
}
for move_name in hm_only_moves:
    for suffix in ('TM', 'TR'):
        path = item_dir / f'{move_name} - {suffix}.json'
        if path.exists():
            try:
                path.unlink()
                removed_count += 1
            except Exception as exc:
                error_count += 1
                print(f'Could not remove {path.name}: {exc}')

if item_dir.is_dir():
    for path in item_dir.glob("*.json"):
        if re.match(r"^(?:TM|TR|HM) - .+\.json$", path.name, flags=re.I):
            try:
                path.unlink()
                removed_count += 1
            except Exception as exc:
                error_count += 1
                print(f'Could not remove {path.name}: {exc}')

cleanup_marker = Path(".slash_guild_duplicates_cleaned_v2")
if cleanup_marker.exists():
    cleanup_marker.unlink()

summary = f"Botfixes cleanup complete: normalized {normalized_count}, removed {removed_count} obsolete file(s)"
if error_count:
    summary += f", {error_count} error(s)"
print(summary + ". Restart the bot so the v3.0 database refreshes from the patched JSON.")
