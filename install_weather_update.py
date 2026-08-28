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
    'Snowy Weather',
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

weather_csv = Path("weather_v3.csv").read_text(encoding="utf-8")
WEATHER.write_text(weather_csv, encoding="utf-8")

print("Weather update installed.")
print("Updated miscCommands.py weather choices.")
print("Replaced weather.csv with the Legends weather data.")
print("Restart the bot, then run %sync_global.")
