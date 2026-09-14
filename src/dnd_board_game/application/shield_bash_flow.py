"""Resolve supplied Shield Bash dice deterministically; the UI generates enemy rolls."""

from dataclasses import dataclass, replace

from dnd_board_game.combat.garran_features import (
    ShieldBashResolution,
    resolve_shield_bash,
)
from dnd_board_game.combat.session import CombatState
from dnd_board_game.world import BoardState


@dataclass(frozen=True)
class ShieldBashFlow:
    target_id: str
    stage: str = "contest"
    attacker_roll: int | None = None
    defender_roll: int | None = None
    damage_roll: int | None = None
    result: ShieldBashResolution | None = None


def submit_shield_bash_rolls(
    pending: ShieldBashFlow,
    state: CombatState,
    board: BoardState,
    *,
    attacker_roll: int | None = None,
    defender_roll: int | None = None,
    damage_roll: int | None = None,
) -> ShieldBashFlow:
    count = 1 + (dict(state.shared_mana.pending_boosts).get("damage", 0) if state.shared_mana else 0)
    values = (
        ((attacker_roll, 20), (defender_roll, 20))
        if pending.stage == "contest"
        else ((damage_roll, 6 * count),)
    )
    if pending.stage not in {"contest", "damage"}:
        raise ValueError("Wynik Uderzenia tarczą już czeka na potwierdzenie.")
    if any(
        type(value) is not int or not 1 <= value <= sides for value, sides in values
    ):
        raise ValueError("Podaj naturalny wynik każdej wymaganej kości w jej zakresie.")
    if pending.stage == "damage" and damage_roll < count:
        raise ValueError(f"Suma {count}k6 jest za mała.")
    if pending.stage == "contest":
        pending = replace(
            pending, attacker_roll=attacker_roll, defender_roll=defender_roll
        )
    result = resolve_shield_bash(
        state,
        board=board,
        target_id=pending.target_id,
        attacker_roll=pending.attacker_roll,
        defender_roll=pending.defender_roll,
        damage_roll=damage_roll if pending.stage == "damage" else count,
    )
    if pending.stage == "contest" and result.succeeded:
        return replace(pending, stage="damage")
    return replace(pending, stage="result", result=result, damage_roll=damage_roll)
