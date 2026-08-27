from pathlib import Path
import re

MISC = Path("miscCommands.py")
WEATHER = Path("weather.csv")

if not MISC.exists():
    raise SystemExit("miscCommands.py was not found. Run this from the main bot folder.")

misc_text = MISC.read_text(encoding="utf-8")

# Backups
misc_backup = Path("miscCommands.py.before_weather_update.bak")
weather_backup = Path("weather.csv.before_legends_update.bak")

if not misc_backup.exists():
    misc_backup.write_text(misc_text, encoding="utf-8")
if WEATHER.exists() and not weather_backup.exists():
    weather_backup.write_text(WEATHER.read_text(encoding="utf-8"), encoding="utf-8")

new_weathers = """weathers = [
    'Sunny Weather',
    'Harsh Sunlight Weather',
    'Rain Weather',
    'Typhoon Weather',
    'Sandstorm Weather',
    'Strong Wind Weather',
    'Hail Weather',
    'Acid Rain Weather',
    'Midnight Weather',
    'Dense Fog',
]"""

pattern = re.compile(r"weathers\s*=\s*\[.*?\]\s*\n", re.S)
match = pattern.search(misc_text)
if not match:
    raise SystemExit("Could not find the weathers = [...] list in miscCommands.py.")

misc_text = misc_text[:match.start()] + new_weathers + "\n" + misc_text[match.end():]
MISC.write_text(misc_text, encoding="utf-8")

weather_csv = 'Sunny Weather,"A bright sunlight shines through the arena. It’s hot, you feel thirsty and tired, the light is hurting your eyes","All damaging Fire-Type Moves gain +1 Damage Dice. All Water-Type Moves get -1 Damage Dice (except Scald and Hydro Steam). No one can be affected by the Frostbite Status Condition. Moves that become Complete Heal in Rain, Acid Rain, Hail or Midnight Weather will Heal for 1HP. Morning Sun becomes Complete Heal."\nHarsh Sunlight Weather,"A harsh sunlight creates extreme heat through the battlefield, there is lava on the floor and some objects just burst into flames. You might need special equipment to go through this weather.","All damaging Fire-Type Moves gain +1 Damage Dice. All Water-Type Moves fail to be executed. Add 2 dice to any Roll of Chance Dice to Burn a Foe. No one can be affected by the Frostbite Status Condition. Midnight, Acid Rain, Sunny, Rain, Sandstorm and Hail Weather conditions fail to activate through any means."\nRain Weather,A heavy downpour. You are soaking wet. There’s deep puddles and it feels like this will grow into a raging storm any second,All damaging Water-Type Moves gain +1 Damage Dice. All Fire-Type moves get their total Damage reduced by 1. Moves that become Complete Heal with Sunny weather will only restore 1 HP instead. Reduce by 3 the number of successes you need to heal a Burn Status Condition.\nTyphoon Weather,"A great torrent quickly floods the field, in just a matter of seconds everything is underwater and you struggle to stay afloat trough the crashing waves around.","All Water-Type Moves gain +1 Damage Dice. All Fire-Type Moves fail to be executed. No one can be affected by the Burn Status Condition. Moves that become Complete Heal with Sunny Weather will not restore any HP. Sunny, Rain, Sandstorm and Hail Weather conditions fail to activate through any means."\nSandstorm Weather,"A raging wind is blowing sand all over. You can barely open your eyes, it’s had to breath and little sharp rocks pierce your skin.","Deal 1 Damage to all non Rock, Ground or Steel Type Active Combatants on the field at the end of the Round. Increase 1 Point to the Special Defense of all Rock-Type Pokémon in the field. Moves that become Complete Heal with Sunny, Rain, Hail, Midnight, or Acid Rain Weather will only restore 1 HP instead."\nStrong Wind Weather,"Strong wind currents lift and swirl everything in the air, from a tiny pebble to a giant truck. You are either being swept around or falling straight to the floor at a great speed.","All Flying-Type Moves gain +1 Damage Dice. (Does not stack with Wind Move Bonus). All Wind Moves gain +1 Damage Dice. (Does not stack with Flying-Type Bonus). Electric, Ice and Rock-Type Moves deal neutral Damage to Flying-Type Pokémon. The effects of the Move Tailwind last for 8 Rounds. Pokémon attempting to set other Weather-Types must have higher current Will than the Pokémon that set Strong Wind Weather. In the case of it being a natural effect, other Weather-Types fail to activate by any means."\nHail Weather,"Heavy ice shards are falling from the sky. It’s cold, it’s snowy and one of those ice pieces may fall right in your head.","Deal 1 damage to all non Ice-Type Active Combatants on the field at the end of the Round. Increase 1 Point to the Defense of all Ice Pokémon in the field. Moves that become Complete Heal with Sunny, Sandstorm, or Acid Rain weather will only restore 1 HP instead."\nAcid Rain Weather,,"Deal 1 Damage to non Poison and Steel-Type Active Combatants at the end of the Round. All Damaging Poison-Type Moves gain +1 Damage Dice. Moves that become Complete Heal in Hail, Rain or Sunny Weather will Heal for 1HP."\nMidnight Weather,,All Dark and Ghost-Type Moves gain +1 Damage Dice. Moves that become Complete Heal in Sunny Weather will heal for 1HP. Moonlight becomes Complete Heal. All damaging Moves with the keywords “Night” and “Moon” gain +2 Damage Dice (This does not stack with the +1 Damage for Ghost and Dark-Type Moves).\nDense Fog,Reduced Visibilty,"All Active Combatants have -2 Accuracy. Sound Moves, Psychic and Ghost-Type Moves, and Moves and Maneuvers that use the Aura Skill ignore this Accuracy penalty. The Move Defog always ends this Weather Effect."\n'
WEATHER.write_text(weather_csv, encoding="utf-8")

print("Weather update installed.")
print("Updated miscCommands.py weather choices.")
print("Replaced weather.csv with the Legends weather data.")
print("Restart the bot, then run %sync_global.")
