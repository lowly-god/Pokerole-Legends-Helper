POKEROLE LEGENDS HELPER — ITEM / HM / MOVE TUTOR / FORAGING FIX
Baseline: HMFullBotTruth.zip

Install:
1. Extract over the bot folder.
2. Run: python install_botfixes4.py
3. Restart the bot so pokerole_v3.db rebuilds from the cleaned item JSON.

Highlights:
- Removes duplicate/obsolete item sources, including legacy prefix-format TM/TR records.
- Keeps the priced Legends Z-Crystal format, including Buginium-Z/Darkinium-Z, and normalizes Normalium-Z to match. Canonical Mega Stone spellings are kept while legacy numeric prices are transferred onto them.
- Removes generic Fishing Rod (Old/Good/Super Rod remain).
- HM /item descriptions include out-of-battle effects.
- Move Tutor default roll = tutor services only.
- Move Tutor Display All Stock = TM/TR/HM machine catalogue only.
- Fixes ordinary /foraging results crashing from view=None.
- See Item_Duplicate_Audit_HMFullBotTruth.txt for the full duplicate audit.


- Normalizes Normalium Z to Normalium-Z at ₽10000 and adds it everywhere the standard type Z-Crystals are used (item data, Precious Stone Merchant, Travelling Merchant, rare Foraging).
- Corrects the ten legacy misspelled canonical Mega Stone names while preserving their existing numeric prices.
- Keeps the spaced Poké Ball item names (Poke Ball, Great Ball, Ultra Ball, Master Ball) and the cleaner established duplicate-cleanup naming choices.
