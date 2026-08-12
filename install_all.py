import subprocess
import sys

print("=== 1/2 Installing custom Pokémon and /stats support ===")
subprocess.check_call([sys.executable, "install_custom_pokemon.py"])

print()
print("=== 2/2 Adding new move learners to /pokelearns ===")
subprocess.check_call([sys.executable, "install_additional_move_learners.py"])

print()
print("FINAL LEGENDS DATA INSTALL COMPLETE")
print("Start the bot normally. No %sync_global is required.")
