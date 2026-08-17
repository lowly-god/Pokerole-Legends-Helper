def apply_luck_modifier(d100_roll: int, luck_modifier: int) -> int:
    """Return a Luck Check total: 1D100 + Luck Modifier, capped at 100."""
    return min(100, d100_roll + luck_modifier)


def format_luck_check(d100_roll: int, luck_modifier: int) -> str:
    """Format the visible calculation used by Luck Checks."""
    total = apply_luck_modifier(d100_roll, luck_modifier)
    return f"Luck Check Roll {d100_roll} + Luck Modifier {luck_modifier} = {total}"
