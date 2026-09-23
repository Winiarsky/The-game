"""Physical dice required by rune-card variants."""
from __future__ import annotations
from .session import CombatState


def shield_bash_dice(state: CombatState) -> tuple[int, ...]:
    boosts = dict(state.shared_mana.pending_boosts) if state.shared_mana else {}
    return (6,) + (6,) * boosts.get("damage", 0) + (4,) * boosts.get("damage_d4", 0)


def second_wind_dice(state: CombatState) -> tuple[int, ...]:
    return (10, 4) if state.shared_mana and state.shared_mana.runes and dict(state.shared_mana.pending_boosts).get("heal_d4") else (10,)


def dice_label(dice: tuple[int, ...]) -> str:
    from collections import Counter
    return " + ".join(f"{count}k{sides}" for sides, count in Counter(dice).items())
