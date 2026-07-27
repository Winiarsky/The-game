from dataclasses import replace
from random import Random

from dnd_board_game.actors import AbilityScores, Actor, ActorId, DamageAffinityProfile, Faction
from dnd_board_game.application import (
    apply_exploration_hazard_outcome,
    resolve_exploration_hazard,
)
from dnd_board_game.combat import DamageType
from dnd_board_game.exploration import (
    ExplorationHazard,
    ExplorationHazardDamage,
    ExplorationHazardTrigger,
    ExplorationState,
    PartyPosition,
)
from dnd_board_game.rules import (
    EffectDuration,
    SaveDamageOnSuccess,
    SavingThrowRequest,
)
from dnd_board_game.world import Coordinate


def test_exploration_hazard_applies_save_before_damage_resistance() -> None:
    actor = Actor(
        id=ActorId("hero"),
        name="Bohater",
        ac=14,
        hp=20,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        ability_scores=AbilityScores(dexterity=14),
        damage_affinities=DamageAffinityProfile(resistances=(DamageType.BLUDGEONING,)),
    )
    hazard = ExplorationHazard(
        id="fall",
        label="Upadek",
        trigger=ExplorationHazardTrigger.CRITICAL_FAILURE,
        saving_throw=SavingThrowRequest(
            "dexterity",
            12,
            "Upadek",
            SaveDamageOnSuccess.HALF,
        ),
        damage=ExplorationHazardDamage("bludgeoning", fixed=8),
        success_message="Kontrolowany upadek.",
        failure_message="Twarde lądowanie.",
    )

    result = resolve_exploration_hazard(actor, hazard, natural_roll=10, rng=Random(1))

    assert result.saving_throw.success is True
    assert result.base_damage == 8
    assert result.applied_damage.damage.total_before_reduction == 4
    assert result.applied_damage.damage.total_applied == 2
    assert result.actor_after.hp == 18


def test_exploration_hazard_applies_failure_condition_to_exploration_state() -> None:
    state = ExplorationState((), (), PartyPosition("gate"))
    effects = (
        {"type": "apply_condition", "parameters": {"condition": "prone"}},
    )

    updated, results = apply_exploration_hazard_outcome(
        state,
        effects,
        actor_id="hero",
        challenge_id="closed_gate",
    )

    assert len(updated.condition_states) == 1
    assert updated.condition_states[0].actor_id == "hero"
    assert updated.condition_states[0].condition.value == "prone"
    assert results[0].changed is True


def test_exploration_hazard_preserves_condition_source_and_rest_duration() -> None:
    state = ExplorationState((), (), PartyPosition("gate"))
    effects = (
        {
            "type": "apply_condition",
            "parameters": {
                "condition": "poisoned",
                "duration": "until_short_rest",
                "source_label": "Zatrute kolce",
            },
        },
    )

    updated, _results = apply_exploration_hazard_outcome(
        state,
        effects,
        actor_id="hero",
        challenge_id="closed_gate",
    )

    condition = updated.condition_states[0]
    assert condition.condition.value == "poisoned"
    assert condition.duration == EffectDuration.UNTIL_SHORT_REST
    assert condition.source_label == "Zatrute kolce"
