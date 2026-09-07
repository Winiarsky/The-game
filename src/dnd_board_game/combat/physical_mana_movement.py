"""Movement cost reminders; physical cards and payments remain at the table."""

from dataclasses import dataclass
from typing import Sequence

from dnd_board_game.actors import Faction
from dnd_board_game.actors.resources import uses_physical_mana
from dnd_board_game.rules import ActiveEffect, EffectDuration, apply_active_effect

from .session import CombatState, current_actor
from .spells import grid_distance_feet

MOVEMENT_DECLARATION = "mana_ordinary_movement"


@dataclass(frozen=True, slots=True)
class ManaMovementNotice:
    cost: int
    started: bool
    steadfast: bool

    @property
    def label(self) -> str:
        if self.started:
            return "Ruch: bez kolejnej dopłaty"
        suffix = " · Nieustępliwość" if self.steadfast else ""
        return (
            f"Ruch: {self.cost} dowolne many{suffix}" if self.cost == 2 else "Ruch: 1 dowolna mana"
        )

    @property
    def description(self) -> str:
        if self.started:
            return (
                f"Ruch już rozpoczęty. Ustalony koszt many: {self.cost}. "
                "Dalsze odcinki nie wymagają kolejnej many."
            )
        reason = "Nieustępliwość: Garran sąsiaduje z przeciwnikiem. " if self.steadfast else ""
        payment = "2 dowolne many" if self.cost == 2 else "1 dowolną manę"
        return (
            f"{reason}Przy rozpoczęciu zwykłego ruchu wydaj {payment} raz na turę, "
            "nie za każde pole. Podgląd i anulowanie nie kosztują many."
        )

    def as_payload(self) -> dict[str, object]:
        return {
            "cost": self.cost,
            "started": self.started,
            "steadfast": self.steadfast,
            "label": self.label,
            "description": self.description,
        }


def movement_mana_notice(
    state: CombatState, effects: Sequence[ActiveEffect]
) -> ManaMovementNotice | None:
    actor = current_actor(state)
    if not uses_physical_mana(actor):
        return None
    declared = next(
        (e for e in effects if e.actor_id == str(actor.id) and e.kind == MOVEMENT_DECLARATION),
        None,
    )
    if declared is not None:
        return ManaMovementNotice(declared.value, True, declared.value == 2)
    adjacent_enemy = str(actor.id) == "garran" and any(
        other.faction not in {actor.faction, Faction.NEUTRAL}
        and not other.is_defeated()
        and grid_distance_feet(actor.position, other.position) <= 5
        for other in state.actors
    )
    return ManaMovementNotice(2 if adjacent_enemy else 1, False, adjacent_enemy)


def declare_ordinary_movement(
    state: CombatState, effects: tuple[ActiveEffect, ...]
) -> tuple[ActiveEffect, ...]:
    """Remember the first committed ordinary movement, never a payment balance.

    Call after validating a real movement or confirming its opportunity attacks.
    Forced/ability movement and mere previews must not call this function.
    """
    notice = movement_mana_notice(state, effects)
    if notice is None or notice.started:
        return effects
    actor_id = str(current_actor(state).id)
    declaration = ActiveEffect(
        id=f"{MOVEMENT_DECLARATION}:{actor_id}",
        actor_id=actor_id,
        kind=MOVEMENT_DECLARATION,
        object_id=f"physical_mana:{MOVEMENT_DECLARATION}",
        label=f"Zwykły ruch rozpoczęty · koszt tej tury: {notice.cost}",
        value=notice.cost,
        duration=EffectDuration.UNTIL_TURN_END,
    )
    return apply_active_effect(effects, declaration).active_effects
