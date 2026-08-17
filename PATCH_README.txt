Pokerole Legends Helper — Botfixes(4) Patch

1. Extract this patch into the Pokerole Legends Helper bot folder, preserving paths and overwriting files.
2. Run: python install_botfixes4.py
3. Restart the bot. The source fingerprint system will rebuild the v3.0 SQLite cache from the patched JSON.

Baseline/source of truth: Pokerole Legends Helper(3).zip

Follow-up fixes:
- Me First Damage1 formatting: Same As Copied Move +1.
- Remaining maneuver Accuracy pool tokens use title capitalization (Aura, Medicine, Crafts, Evasion, Varies).
- /foraging option is now Luck Modifier; it must be a multiple of 5 from 0-100 and sets the minimum possible D100 result rather than being added to the roll.
