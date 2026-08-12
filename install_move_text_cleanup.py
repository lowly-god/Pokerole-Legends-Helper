from pathlib import Path
import json
import re
import shutil

ROOT = Path(".")
MOVES_DIR = ROOT / "pokerole_data" / "v3.0" / "Moves"
DB_FILE = ROOT / "pokerole_v3.db"
BACKUP_DIR = ROOT / "move_text_cleanup_backups"

if not MOVES_DIR.exists():
    raise SystemExit(
        "Could not find pokerole_data/v3.0/Moves. "
        "Put this installer in the bot's main /home/container folder."
    )

BACKUP_DIR.mkdir(exist_ok=True)

# ------------------------------------------------------------------
# 1. LOW ACCURACY -> ACCURACY -X
# ------------------------------------------------------------------
LOW_ACCURACY = re.compile(
    r"\bLow\s+Accuracy\s*(?::\s*)?(?:x\s*)?-?\s*(\d+)\b",
    re.IGNORECASE,
)

# ------------------------------------------------------------------
# 2. REDUNDANT TARGETING TEXT
#
# IMPORTANT:
# - ONLY the move JSON's Effect field is cleaned.
# - Target is NEVER modified.
# - Description is NEVER modified.
# - Only a LEADING targeting instruction is removed.
# ------------------------------------------------------------------

TARGET_PREFIX_PATTERNS = [
    # Very common stock-data forms.
    r"Single\s+Target\.\s*",
    r"Single\s+Target\s+(?=\S)",

    r"Target\s+Self\.\s*",
    r"Target\s+All\s+Foes\s+in\s+Range\.\s*",
    r"Target\s+all\s+foes\s+in\s+Range\.\s*",
    r"Target\s+all\s+Foes\s+in\s+Range\.\s*",
    r"Target\s+All\s+Allies\s+in\s+Range\.\s*",
    r"Target\s+One\s+Ally\.\s*",
    r"Target\s+User\s+and\s+Allies\s+in\s+Range\.\s*",
    r"Target\s+Random\s+Foe\.\s*",
    r"Target\s+Battlefield\.\s*",
    r"Target\s+the\s+Battlefield\.\s*",
    r"Target\s+battlefield\.\s*",
    r"Target\s+Allies\s+in\s+Range\.\s*",
    r"Target\s+Max\s+Self\.\s*",

    # Side-of-field target lines.
    r"Target\s+Foe'?s\s+Side\s+of\s+the\s+Field\.\s*",
    r"Target'?s\s+Foe'?s\s+Side\s+of\s+the\s+Field\.\s*",
    r"Target\s+User'?s\s+side\s+of\s+the\s+Field\.\s*",
    r"Target\s+the\s+User'?s\s+side\s+of\s+the\s+field\.\s*",

    # Compound target labels.
    r"\*?Target\s+User\s+or\s+Target\s+one\s+Ally\.\s*",
    r"Target\s+Self\s*/\s*Target\s+One\s+Ally\.\s*",

    # Older wording which means the same thing.
    r"Targets\s+All\s+Foes\s+in\s+Range\.\s*",
    r"All\s+Foes\s+in\s+Range\.\s*",
    r"All\s+foes\s+in\s+range\.\s*",
    r"Area\s+Move\.\s*",
    r"Area\s+Attack\.\s*",
    r"Battlefield\.\s*",

    # Dynamax wording found in the stock data.
    r"Target\s+all\s+foes\s+in\s+Range\s+or\s+a\s+Single\s+Max\s+Target\.\s*",
]

TARGET_PREFIX = re.compile(
    r"^\s*(?:" + "|".join(f"(?:{p})" for p in TARGET_PREFIX_PATTERNS) + r")",
    re.IGNORECASE,
)


def clean_low_accuracy(value):
    if not isinstance(value, str):
        return value, 0

    count = 0

    def repl(match):
        nonlocal count
        count += 1
        return f"Accuracy -{match.group(1)}"

    return LOW_ACCURACY.sub(repl, value), count


def clean_effect(effect):
    if not isinstance(effect, str):
        return effect, 0

    original = effect
    # There should normally only be one target prefix, but loop in case old
    # data contains two redundant labels back-to-back.
    while True:
        updated = TARGET_PREFIX.sub("", effect, count=1)
        if updated == effect:
            break
        effect = updated.lstrip()

    # Clean whitespace left by removed labels without altering punctuation
    # or any actual mechanical wording.
    effect = re.sub(r"[ \t]{2,}", " ", effect).strip()

    return effect, int(effect != original)


changed_moves = []
low_accuracy_total = 0
target_cleanup_total = 0

for path in sorted(MOVES_DIR.glob("*.json")):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"Skipping unreadable JSON: {path.name} ({exc})")
        continue

    original = json.dumps(data, ensure_ascii=False, sort_keys=True)

    # Low Accuracy wording may occur in Effect or other mechanical text, so
    # process all string values while preserving keys and structure.
    def recurse(value):
        nonlocal_placeholder = None
        if isinstance(value, str):
            return clean_low_accuracy(value)
        if isinstance(value, list):
            new = []
            count = 0
            for item in value:
                item2, c = recurse(item)
                new.append(item2)
                count += c
            return new, count
        if isinstance(value, dict):
            new = {}
            count = 0
            for k, item in value.items():
                item2, c = recurse(item)
                new[k] = item2
                count += c
            return new, count
        return value, 0

    data, low_count = recurse(data)

    # Target cleanup is intentionally ONLY Effect.
    new_effect, target_count = clean_effect(data.get("Effect", ""))
    data["Effect"] = new_effect

    updated = json.dumps(data, ensure_ascii=False, sort_keys=True)
    if updated == original:
        continue

    backup_path = BACKUP_DIR / path.name
    if not backup_path.exists():
        shutil.copy2(path, backup_path)

    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    move_name = data.get("Name", path.stem)
    changed_moves.append((move_name, low_count, target_count))
    low_accuracy_total += low_count
    target_cleanup_total += target_count


if changed_moves and DB_FILE.exists():
    DB_FILE.unlink()


report = ROOT / "move_text_cleanup_report.txt"
with report.open("w", encoding="utf-8") as f:
    f.write("MOVE TEXT CLEANUP REPORT\n")
    f.write("========================\n\n")
    f.write(f"Moves changed: {len(changed_moves)}\n")
    f.write(f"Low Accuracy replacements: {low_accuracy_total}\n")
    f.write(f"Redundant Effect target labels removed: {target_cleanup_total}\n\n")
    for name, low_count, target_count in changed_moves:
        bits = []
        if low_count:
            bits.append(f"Accuracy wording x{low_count}")
        if target_count:
            bits.append("Effect target label removed")
        f.write(f"{name}: {', '.join(bits)}\n")


print()
print("MOVE TEXT CLEANUP COMPLETE")
print("--------------------------")
print(f"Moves changed: {len(changed_moves)}")
print(f"'Low Accuracy X' replacements: {low_accuracy_total}")
print(f"Redundant target labels removed from Effect: {target_cleanup_total}")
print()
print("Target fields were NOT changed.")
print("Move descriptions were NOT changed.")
print("All other Effect text was preserved.")
print()

if changed_moves:
    print("pokerole_v3.db removed so move data rebuilds on next normal startup.")
else:
    print("No matching text remained; no database rebuild was required.")

print()
print("Detailed report: move_text_cleanup_report.txt")
print("No %sync_global is required.")
