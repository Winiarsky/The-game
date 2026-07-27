from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from dnd_board_game.actions import ActionResourceResolver
from dnd_board_game.actors import ActorId
from dnd_board_game.combat import (
    ActionEconomyCost,
    ActiveCombatEffect,
    CombatState,
    SummonDefinition,
    SummonedCreatureState,
    actor_spell_cast_validation,
    add_summoned_creature,
    current_actor,
    legal_summon_positions,
    remove_summons,
    summon_actor,
)
from dnd_board_game.rules import (
    EffectDuration,
    EffectSource,
    EffectSourceType,
    apply_active_effect,
)
from dnd_board_game.world import BoardState, Coordinate

from .player_combat_resource_flow import (
    concentration_effects_for_actor,
    remove_concentration_effects,
)


class SummonActionSpec(Protocol):
    id: str
    action_type: str
    label: str
    range_feet: int
    spell_level: int
    action_cost: ActionEconomyCost
    summon: SummonDefinition | None


@dataclass(frozen=True, slots=True)
class PendingSummon:
    caster_id: str
    action_id: str
    cast_level: int
    legal_positions: tuple[Coordinate, ...]

    def as_payload(self) -> dict[str, object]:
        return {
            "caster_id": self.caster_id,
            "action_id": self.action_id,
            "cast_level": self.cast_level,
            "legal_positions": [
                {"col": position.col, "row": position.row}
                for position in self.legal_positions
            ],
        }


@dataclass(frozen=True, slots=True)
class SummoningTransition:
    state: CombatState
    active_effects: tuple[ActiveCombatEffect, ...]
    pending: PendingSummon | None
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]
    removed_actor_ids: tuple[str, ...] = ()


class SummoningFlowService:
    """Prepare and resolve one data-driven concentration summon."""

    def __init__(self) -> None:
        self._resources = ActionResourceResolver()

    def prepare(
        self,
        *,
        board: BoardState,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        action: SummonActionSpec,
        cast_level: int | None = None,
    ) -> SummoningTransition:
        caster = current_actor(state)
        definition = _summon_definition(action)
        validation = actor_spell_cast_validation(
            caster,
            action.id,
            cast_level=cast_level,
        )
        if validation is None or not validation.valid:
            raise ValueError(
                " ".join(validation.errors)
                if validation is not None
                else "Aktor nie zna tego czaru."
            )
        positions = legal_summon_positions(
            board,
            state,
            caster,
            range_feet=action.range_feet,
        )
        if not positions:
            raise ValueError("Brak wolnego, widocznego pola dla przywołania.")
        pending = PendingSummon(
            caster_id=str(caster.id),
            action_id=action.id,
            cast_level=validation.cast_level,
            legal_positions=positions,
        )
        return SummoningTransition(
            state=state,
            active_effects=active_effects,
            pending=pending,
            message_title="Przywołanie",
            message_body=(
                f"{caster.name} przygotowuje {action.label}. "
                "Wybierz podświetlone wolne pole."
            ),
            event_type="ui_combat_summon_started",
            event_payload=(
                ("caster_id", str(caster.id)),
                ("spell_id", action.id),
                ("cast_level", validation.cast_level),
                ("legal_positions", len(positions)),
            ),
        )

    def confirm(
        self,
        *,
        board: BoardState,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        action: SummonActionSpec,
        pending: PendingSummon,
        position: Coordinate,
    ) -> SummoningTransition:
        caster = current_actor(state)
        if str(caster.id) != pending.caster_id or action.id != pending.action_id:
            raise ValueError("Oczekujące przywołanie nie należy do aktywnego aktora.")
        definition = _summon_definition(action)
        current_positions = legal_summon_positions(
            board,
            state,
            caster,
            range_feet=action.range_feet,
        )
        if position not in pending.legal_positions or position not in current_positions:
            raise ValueError("Wybrane pole nie jest już legalne dla przywołania.")
        validation = actor_spell_cast_validation(
            caster,
            action.id,
            cast_level=pending.cast_level,
        )
        if validation is None or not validation.valid:
            raise ValueError(
                " ".join(validation.errors)
                if validation is not None
                else "Aktor nie zna tego czaru."
            )
        resource_use = self._resources.consume_action_and_source_resource(
            state,
            caster,
            spell_level=action.spell_level,
            spell_id=action.id,
            cast_level=pending.cast_level,
            action_cost=action.action_cost,
        )
        previous_concentration = concentration_effects_for_actor(
            active_effects,
            str(caster.id),
        )
        updated_effects = remove_concentration_effects(
            active_effects,
            str(caster.id),
        )
        updated_state, removed = remove_summons(
            resource_use.state,
            owner_actor_id=caster.id,
        )
        removed_ids = {str(summon.actor_id) for summon in removed}
        updated_effects = tuple(
            effect
            for effect in updated_effects
            if effect.actor_id not in removed_ids
            and effect.target_actor_id not in removed_ids
            and effect.source_actor_id not in removed_ids
        )
        sequence = 1 + sum(
            1
            for actor in state.actors
            if str(actor.id).startswith(f"summon:{caster.id}:{action.id}:")
        )
        actor_id = ActorId(f"summon:{caster.id}:{action.id}:{sequence}")
        effect_id = f"concentration_summon:{caster.id}:{actor_id}:{action.id}"
        summoned = SummonedCreatureState(
            actor_id=actor_id,
            owner_actor_id=caster.id,
            spell_id=action.id,
            definition=definition,
            concentration_effect_id=effect_id,
        )
        actor = summon_actor(
            definition,
            actor_id=actor_id,
            owner=caster,
            position=position,
        )
        updated_state = add_summoned_creature(updated_state, summoned, actor)
        effect = ActiveCombatEffect(
            id=effect_id,
            actor_id=str(caster.id),
            kind="concentration_summon",
            label=action.label,
            object_id=f"spell:{action.id}",
            value=0,
            source_actor_id=str(caster.id),
            target_actor_id=str(actor_id),
            source=EffectSource(EffectSourceType.SPELL, action.id, action.label),
            duration=EffectDuration.CONCENTRATION,
            stacking_key=f"concentration:{caster.id}",
            spell_level=pending.cast_level,
        )
        updated_effects = apply_active_effect(updated_effects, effect).active_effects
        ended_text = (
            " Poprzednia koncentracja zakończona: "
            f"{', '.join(item.label for item in previous_concentration)}."
            if previous_concentration
            else ""
        )
        message = (
            f"{caster.name} przywołuje {definition.name} na polu "
            f"({position.col}, {position.row}); istota działa zaraz po przywołującym."
            f"{ended_text}"
        )
        return SummoningTransition(
            state=updated_state,
            active_effects=updated_effects,
            pending=None,
            message_title="Przywołanie",
            message_body=message,
            event_type="ui_combat_summon_confirmed",
            event_payload=(
                ("caster_id", str(caster.id)),
                ("spell_id", action.id),
                ("cast_level", pending.cast_level),
                ("summoned_actor_id", str(actor_id)),
                ("position", [position.col, position.row]),
            ),
            removed_actor_ids=tuple(sorted(removed_ids)),
        )

    def cancel(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        pending: PendingSummon,
    ) -> SummoningTransition:
        return SummoningTransition(
            state=state,
            active_effects=active_effects,
            pending=None,
            message_title="Przywołanie",
            message_body="Anulowano przywołanie. Akcja i slot nie zostały zużyte.",
            event_type="ui_combat_summon_cancelled",
            event_payload=(
                ("caster_id", pending.caster_id),
                ("spell_id", pending.action_id),
            ),
        )


def remove_orphaned_summons(
    state: CombatState,
    active_effects: tuple[ActiveCombatEffect, ...],
) -> tuple[CombatState, tuple[ActiveCombatEffect, ...], tuple[SummonedCreatureState, ...]]:
    effect_ids = {effect.id for effect in active_effects}
    defeated_actor_ids = {
        actor.id for actor in state.actors if actor.is_defeated()
    }
    orphaned = tuple(
        summon
        for summon in state.summoned_creatures
        if summon.concentration_effect_id not in effect_ids
        or summon.actor_id in defeated_actor_ids
    )
    orphaned_effect_ids = {
        summon.concentration_effect_id for summon in orphaned
    }
    active_effects = tuple(
        effect for effect in active_effects if effect.id not in orphaned_effect_ids
    )
    updated_state = state
    removed: list[SummonedCreatureState] = []
    for summon in orphaned:
        updated_state, current_removed = remove_summons(
            updated_state,
            owner_actor_id=summon.owner_actor_id,
            spell_id=summon.spell_id,
        )
        removed.extend(current_removed)
    removed_ids = {str(summon.actor_id) for summon in removed}
    updated_effects = tuple(
        effect
        for effect in active_effects
        if effect.actor_id not in removed_ids
        and effect.target_actor_id not in removed_ids
        and effect.source_actor_id not in removed_ids
    )
    return updated_state, updated_effects, tuple(removed)


def _summon_definition(action: SummonActionSpec) -> SummonDefinition:
    if action.action_type != "summon" or action.summon is None:
        raise ValueError("Ta akcja nie jest czarem przywołania.")
    return action.summon
