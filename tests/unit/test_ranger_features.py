from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    Faction,
    FeatureGrant,
    FeatureSourceKind,
    apply_favored_enemy_advantage,
    favored_enemy_creature_type,
    favored_enemy_humanoid_races,
    natural_explorer_benefits,
    natural_explorer_terrain,
)
from dnd_board_game.rules import D20RollRequest, RollMode
from dnd_board_game.exploration import (
    CheckAggregation,
    CheckParticipants,
    ConsequenceTarget,
    ExplorationCheckPlan,
)
from dnd_board_game.ui.exploration_app import _actor_check_request
from dnd_board_game.world import Coordinate


def _ranger() -> Actor:
    return Actor(
        ActorId("ranger"),
        "Ranger",
        14,
        20,
        0,
        30,
        Coordinate(0, 0),
        Faction.ALLY,
        ability_scores=AbilityScores(),
        features=(
            FeatureGrant(
                "favored_enemy_undead",
                "Favored Enemy: Undead",
                FeatureSourceKind.CLASS,
                "ranger",
            ),
            FeatureGrant(
                "natural_explorer_forest",
                "Natural Explorer: Forest",
                FeatureSourceKind.CLASS,
                "ranger",
            ),
        ),
    )


def test_favored_enemy_applies_advantage_only_to_its_two_rule_contexts() -> None:
    ranger = _ranger()

    tracking = apply_favored_enemy_advantage(
        ranger,
        D20RollRequest(),
        creature_type="undead",
        context="survival_tracking",
    )
    unrelated = apply_favored_enemy_advantage(
        ranger,
        D20RollRequest(),
        creature_type="fiend",
        context="survival_tracking",
    )

    assert favored_enemy_creature_type(ranger) == "undead"
    assert tracking.mode == RollMode.ADVANTAGE
    assert unrelated.mode == RollMode.NORMAL


def test_humanoid_favored_enemy_requires_one_of_the_two_selected_races() -> None:
    ranger = Actor(
        ActorId("humanoid_hunter"),
        "Humanoid Hunter",
        14,
        20,
        0,
        30,
        Coordinate(0, 0),
        Faction.ALLY,
        features=tuple(
            FeatureGrant(feature_id, feature_id, FeatureSourceKind.CLASS, "ranger")
            for feature_id in (
                "favored_enemy_humanoid",
                "favored_enemy_humanoid_race_gnoll",
                "favored_enemy_humanoid_race_orc",
            )
        ),
    )

    orc = apply_favored_enemy_advantage(
        ranger,
        D20RollRequest(),
        creature_type="humanoid",
        humanoid_race="orc",
        context="survival_tracking",
    )
    human = apply_favored_enemy_advantage(
        ranger,
        D20RollRequest(),
        creature_type="humanoid",
        humanoid_race="human",
        context="survival_tracking",
    )

    assert favored_enemy_creature_type(ranger) == "humanoid"
    assert favored_enemy_humanoid_races(ranger) == ("gnoll", "orc")
    assert orc.mode == RollMode.ADVANTAGE
    assert human.mode == RollMode.NORMAL


def test_natural_explorer_exposes_all_2014_overland_benefits_in_chosen_terrain() -> None:
    ranger = _ranger()

    benefits = natural_explorer_benefits(ranger, terrain="forest")

    assert natural_explorer_terrain(ranger) == "forest"
    assert benefits is not None
    assert benefits.difficult_terrain_slows_travel is False
    assert benefits.can_become_lost_magically_only is True
    assert benefits.remains_alert_during_other_activity is True
    assert benefits.forage_yield_multiplier == 2
    assert benefits.learns_tracking_details is True
    assert natural_explorer_benefits(ranger, terrain="desert") is None


def test_authored_tracking_check_uses_favored_enemy_in_runtime_request() -> None:
    plan = ExplorationCheckPlan(
        participants=CheckParticipants.SINGLE_ACTOR,
        aggregation=CheckAggregation.LEAD_RESULT,
        consequence_targets=(ConsequenceTarget.LEAD_ACTOR,),
        ability="wisdom",
        skill="survival",
        dc=12,
        lead_actor_id="ranger",
        context_tags=("tracking", "creature_type:undead"),
    )

    request = _actor_check_request(_ranger(), plan)

    assert request.mode == RollMode.ADVANTAGE


def test_authored_humanoid_tracking_check_uses_race_tag() -> None:
    ranger = Actor(
        ActorId("ranger"),
        "Ranger",
        14,
        20,
        0,
        30,
        Coordinate(0, 0),
        Faction.ALLY,
        features=tuple(
            FeatureGrant(feature_id, feature_id, FeatureSourceKind.CLASS, "ranger")
            for feature_id in (
                "favored_enemy_humanoid",
                "favored_enemy_humanoid_race_gnoll",
                "favored_enemy_humanoid_race_orc",
            )
        ),
    )
    plan = ExplorationCheckPlan(
        participants=CheckParticipants.SINGLE_ACTOR,
        aggregation=CheckAggregation.LEAD_RESULT,
        consequence_targets=(ConsequenceTarget.LEAD_ACTOR,),
        ability="wisdom",
        skill="survival",
        dc=12,
        lead_actor_id="ranger",
        context_tags=(
            "tracking",
            "creature_type:humanoid",
            "humanoid_race:orc",
        ),
    )

    assert _actor_check_request(ranger, plan).mode == RollMode.ADVANTAGE
