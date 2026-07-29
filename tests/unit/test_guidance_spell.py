from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import ActiveCombatEffect
from dnd_board_game.exploration.models import (
    CheckAggregation,
    CheckParticipants,
    ConsequenceTarget,
    ExplorationCheckPlan,
)
from dnd_board_game.ui.exploration_app import _check_inputs_from_payload
from dnd_board_game.world import Coordinate


def test_guidance_optional_physical_d4_is_added_to_one_ability_check() -> None:
    actor = Actor(
        id=ActorId("cleric"),
        name="Kleryk",
        ac=12,
        hp=10,
        max_hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        ability_scores=AbilityScores(wisdom=14),
    )
    plan = ExplorationCheckPlan(
        participants=CheckParticipants.SINGLE_ACTOR,
        aggregation=CheckAggregation.LEAD_RESULT,
        consequence_targets=(ConsequenceTarget.LEAD_ACTOR,),
        ability="wisdom",
        skill="perception",
        dc=15,
        lead_actor_id="cleric",
    )
    guidance = ActiveCombatEffect(
        id="guidance:cleric",
        actor_id="cleric",
        kind="guidance_roll_bonus",
        label="Wskazówki",
        object_id="spell:guidance",
        value=4,
    )

    inputs = _check_inputs_from_payload(
        (actor,),
        plan,
        {"cleric": {"natural_roll": 10, "guidance_roll": 3}},
        (guidance,),
    )

    assert len(inputs) == 1
    modifiers = inputs[0].request.modifiers
    assert any(
        modifier.label == "Wskazówki" and modifier.value == 3
        for modifier in modifiers
    )
