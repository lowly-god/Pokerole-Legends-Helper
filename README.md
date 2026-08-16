# PokeRole-Helper
Where pokerole-helper bot lives

---
- Note: March 25, 2024 - All of the init and generation code is in PokeRole-Helper.py.
If you're looking to modify the code, be warned that it's only loosely organized.
---

Command organization:

Base stuff and core Pokémon reference/encounter commands
 - PokeRole-Helper.py
 - PokeDictionary.txt (for poke autocorrect)
 - MoveDictionary.txt
 - AbilityDictionary.txt

Dungeon Generation

Quest Generation
 - questCog.py
 - pmd_quest_text.py (random lines from the pmd games)
 
Dice (/roll and %roll)
 - diceCog.py
  
Database for reference stuff
 - dbhelper.py

Misc/other
 - miscCommands.py
 - custom_help.py
