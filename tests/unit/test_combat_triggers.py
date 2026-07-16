from dataclasses import replace

import pytest

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    ActorTrigger,
    Faction,
    TriggerEffectKind,
    TriggerEventType,
)
from dnd_board_game.combat import (
    InitiativeEntry,
    InitiativeOrder,
    current_actor,
    resolve_actor_trigger_events,
    resolve_combat_trigger_events,
    resolve_combat_triggers,
    start_combat,
)
from dnd_board_game.application import CombatTurnFinalizationService
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    EffectEvent,
    EffectEventType,
    resolve_d20_roll,
)
from dnd_board_game.world import Coordinate


def _trigger(event_type: EffectEventType, value: int = 3) -> ActorTrigger:
    return ActorTrigger(
        id=f"trigger_{event_type.value}",
        label="Runiczna osłona",
        event_type=TriggerEventType(event_type.value),
        effect_kind=TriggerEffectKind.GRANT_TEMP_HP,
        value=value,
    )


def _actor(
    actor_id: str,
    faction: Faction,
    *,
    triggers: tuple[ActorTrigger, ...] = (),
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=faction,
        ability_scores=AbilityScores(),
        triggers=triggers,
    )


def _state(hero: Actor, enemy: Actor):
    order = InitiativeOrder(
        (
            InitiativeEntry(
                hero,
                resolve_d20_roll(D20RollInput(D20RollRequest(), 20)),
                0,
                0,
            ),
            InitiativeEntry(
                enemy,
                resolve_d20_roll(D20RollInput(D20RollRequest(), 10)),
                0,
                1,
            ),
        )
    )
    return start_combat((hero, enemy), order)


@pytest.mark.parametrize(
    "event_type",
    (
        EffectEventType.ATTACK_HIT,
        EffectEventType.DAMAGE_TAKEN,
        EffectEventType.ACTOR_MOVED,
        EffectEventType.TURN_START,
        EffectEventType.TURN_END,
        EffectEventType.SHORT_REST_COMPLETED,
        EffectEventType.LONG_REST_COMPLETED,
        EffectEventType.ENCOUNTER_ENDED,
    ),
)
def test_shared_event_contract_can_activate_actor_trigger(event_type: EffectEventType) -> None:
    hero = _actor("hero", Faction.ALLY, triggers=(_trigger(event_type),))
    enemy = _actor("enemy", Faction.ENEMY)

    resolution = resolve_combat_triggers(
        _state(hero, enemy),
        EffectEvent(event_type, actor_id="hero", target_actor_id="enemy"),
    )

    updated = next(actor for actor in resolution.state.actors if str(actor.id) == "hero")
    assert updated.temp_hp == 3
    assert resolution.activations[0].trigger.event_type.value == event_type.value


def test_temp_hp_trigger_keeps_higher_existing_value_and_defeated_owner_does_not_trigger() -> None:
    trigger = _trigger(EffectEventType.DAMAGE_TAKEN, 3)
    hero = replace(_actor("hero", Faction.ALLY, triggers=(trigger,)), temp_hp=5)
    enemy = _actor("enemy", Faction.ENEMY)

    unchanged = resolve_combat_triggers(
        _state(hero, enemy),
        EffectEvent(EffectEventType.DAMAGE_TAKEN, actor_id="hero"),
    )
    defeated = resolve_combat_triggers(
        _state(replace(hero, hp=0), enemy),
        EffectEvent(EffectEventType.DAMAGE_TAKEN, actor_id="hero"),
    )

    assert unchanged.activations[0].changed is False
    assert unchanged.activations[0].current_temp_hp == 5
    assert defeated.activations == ()


def test_turn_finalization_resolves_end_and_next_start_triggers() -> None:
    hero = _actor(
        "hero",
        Faction.ALLY,
        triggers=(_trigger(EffectEventType.TURN_END, 1),),
    )
    enemy = _actor(
        "enemy",
        Faction.ENEMY,
        triggers=(_trigger(EffectEventType.TURN_START, 2),),
    )

    transition = CombatTurnFinalizationService().finish_active_turn(
        state=_state(hero, enemy),
        active_effects=(),
    )

    assert transition is not None
    assert current_actor(transition.state).id == enemy.id
    assert [actor.temp_hp for actor in transition.state.actors] == [1, 2]
    assert [item.owner_actor_id for item in transition.trigger_activations] == [
        "hero",
        "enemy",
    ]


def test_ordered_event_batch_uses_state_produced_by_previous_trigger() -> None:
    hero = _actor(
        "hero",
        Faction.ALLY,
        triggers=(
            _trigger(EffectEventType.ATTACK_HIT, 2),
            _trigger(EffectEventType.DAMAGE_TAKEN, 5),
        ),
    )
    enemy = _actor("enemy", Faction.ENEMY)

    resolution = resolve_combat_trigger_events(
        _state(hero, enemy),
        (
            EffectEvent(EffectEventType.ATTACK_HIT, actor_id="hero"),
            EffectEvent(EffectEventType.DAMAGE_TAKEN, actor_id="hero"),
        ),
    )

    updated = next(actor for actor in resolution.state.actors if actor.id == hero.id)
    assert updated.temp_hp == 5
    assert [activation.previous_temp_hp for activation in resolution.activations] == [0, 2]


def test_actor_event_batch_supports_rest_events_without_combat_state() -> None:
    hero = _actor(
        "hero",
        Faction.ALLY,
        triggers=(_trigger(EffectEventType.LONG_REST_COMPLETED, 4),),
    )

    resolution = resolve_actor_trigger_events(
        (hero,),
        (EffectEvent(EffectEventType.LONG_REST_COMPLETED, actor_id="hero"),),
    )

    assert resolution.actors[0].temp_hp == 4
    assert resolution.activations[0].owner_actor_id == "hero"
