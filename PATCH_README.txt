Pokérole Legends Helper — Botfixes(4) Cumulative Patch

Install:
1. Extract this patch into the Pokérole Legends Helper bot folder, preserving paths and overwriting files.
2. Run: python install_botfixes4.py
3. Restart the bot.

Source of truth for this revision: NewestPastchTruth.zip

This revision keeps all changes in that source and adds:
- /encounter_table remains one command. With only `table`, it displays the entire table.
  Optional `roll` rolls one result; optional `exclude` excludes specified results and rolls one result.
- Startup now detects and replaces Discord's stale global /encounter_table subcommand registration.
  The guild slash-command cleanup is also rerun once using a new v2 marker.
- Colosseum main headers are bold; subheaders are underlined.
- Power Increasers and Power Increasers [Various] are removed defensively:
  source JSON deletion, /item lookup/autocomplete/category filtering, and shop data cleanup.
- Macho Brace price is ₽10000 in both item data and merchant pools.
- Luck Modifier is 1D100 + modifier, capped at 100, and visibly displays the calculation.
- Added /roll_luck_check with the same multiple-of-5 Luck Modifier rule and capped calculation.
- /roll_luck_check is inserted directly below /roll in the Utilities section of /help.
