POKEROLE LEGENDS HELPER PATCH
Baseline: LegendsFullBot.zip

Changes:
- Startup legacy-item cleanup now runs before cogs/database creation, preventing
  the old cleanup -> second database rebuild cycle.
- Startup cleanup no longer prints hundreds of per-file deletion messages. It
  emits one compact summary only when work was actually performed.
- Extension loading is idempotent on repeated on_ready events.
- Full Legends HM set is recognized:
  Cut, Defog, Dive, Flash, Fly, Magma Drift, Rock Climb, Rock Smash, Strength,
  Surf, Teleport, Waterfall, Whirlpool.
- 369 current Pokédex records that already learn one of those moves now have
  explicit HM pools (469 HM compatibility entries total).
- machineLearnsets dynamically adds all full-set HM moves already present in a
  Pokémon's authored move list, so future records are covered too.
- custom_pokemon_records.json and install_custom_pokemon.py preserve HM pools
  if the custom-Pokémon installer is rerun.
- install_botfixes4.py cleanup output is compact rather than per-file spam.

Install:
Extract over the full bot and run:
  python install_botfixes4.py
Then restart the bot.
