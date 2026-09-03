from dataclasses import replace

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    Faction,
    FeatureGrant,
    FeatureSourceKind,
    ProficiencyProfile,
)
from dnd_board_game.application import (
    hidden_states_from_precombat_attempts,
    precombat_stealth_is_available,
    resolve_precombat_stealth,
)
from dnd_board_game.combat import ActiveCombatEffect, HiddenState
from dnd_board_game.exploration import (
    EncounterOpeningOutcome,
    EncounterOpeningResolution,
)
from dnd_board_game.world import Coordinate


def _actor(
    actor_id: str,
    faction: Faction,
    *,
    dexterity: int = 10,
    wisdom: int = 10,
    skills: tuple[str, ...] = (),
    mira_stealth: bool = False,
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=faction,
        ability_scores=AbilityScores(dexterity=dexterity, wisdom=wisdom),
        proficiency_bonus=2,
        proficiencies=ProficiencyProfile(skills=skills),
        features=(
            (
                FeatureGrant(
                    "mira_shadow_stealth",
                    "Mistrzyni ukrycia",
                    FeatureSourceKind.SCENARIO,
                    "test:mira",
                ),
            )
            if mira_stealth
            else ()
        ),
    )


def _opening(outcome: EncounterOpeningOutcome) -> EncounterOpeningResolution:
    return EncounterOpeningResolution("rule", outcome, "title", "narration", 0)


def test_precombat_stealth_is_available_only_for_authored_hide_openings() -> None:
    assert precombat_stealth_is_available(
        _opening(EncounterOpeningOutcome.PARTY_CAN_HIDE)
    )
    assert precombat_stealth_is_available(
        _opening(EncounterOpeningOutcome.PARTY_INITIATIVE_ADVANTAGE_AND_CAN_HIDE)
    )
    assert not precombat_stealth_is_available(
        _opening(EncounterOpeningOutcome.PARTY_INITIATIVE_ADVANTAGE)
    )
    assert not precombat_stealth_is_available(
        _opening(EncounterOpeningOutcome.NO_SURPRISE)
    )


def test_precombat_stealth_compares_one_roll_with_each_enemy_passive_perception() -> None:
    rogue = _actor("rogue", Faction.ALLY, dexterity=16, skills=("stealth",), mira_stealth=True)
    goblin = _actor("goblin", Faction.ENEMY, wisdom=10)
    scout = _actor("scout", Faction.ENEMY, wisdom=16, skills=("perception",))

    resolution = resolve_precombat_stealth(
        (rogue, goblin, scout),
        (),
        actor_id="rogue",
        natural_roll=9,
    )

    assert resolution.attempt.total == 14
    assert resolution.attempt.hidden_from_actor_ids == ("goblin",)
    assert resolution.attempt.detected_by_actor_ids == ("scout",)
    assert hidden_states_from_precombat_attempts(
        (resolution.attempt,),
        (rogue, goblin, scout),
    ) == (HiddenState("rogue", 14, ("goblin",)),)


def test_each_actor_gets_only_one_precombat_stealth_attempt() -> None:
    rogue = _actor("rogue", Faction.ALLY, mira_stealth=True)
    goblin = _actor("goblin", Faction.ENEMY)
    first = resolve_precombat_stealth(
        (rogue, goblin), (), actor_id="rogue", natural_roll=15
    )

    try:
        resolve_precombat_stealth(
            (rogue, goblin),
            (first.attempt,),
            actor_id="rogue",
            natural_roll=20,
        )
    except ValueError as exc:
        assert "wykorzystał już próbę" in str(exc)
    else:
        raise AssertionError("Second precombat Stealth attempt should be rejected.")


def test_precombat_hide_rejects_a_hero_without_miras_feature() -> None:
    hero = _actor("hero", Faction.ALLY)
    enemy = _actor("enemy", Faction.ENEMY)

    try:
        resolve_precombat_stealth(
            (hero, enemy), (), actor_id="hero", natural_roll=20
        )
    except ValueError as exc:
        assert "tylko Mira" in str(exc)
    else:
        raise AssertionError("A non-Mira hero should not receive a Hide attempt.")


def test_pass_without_trace_dynamically_adds_ten_within_thirty_feet() -> None:
    caster = _actor("druid", Faction.ALLY)
    near_ally = replace(
        _actor("rogue", Faction.ALLY),
        position=Coordinate(6, 0),
        features=_actor("mira", Faction.ALLY, mira_stealth=True).features,
    )
    far_ally = replace(
        _actor("ranger", Faction.ALLY),
        position=Coordinate(7, 0),
        features=_actor("mira", Faction.ALLY, mira_stealth=True).features,
    )
    enemy = replace(
        _actor("goblin", Faction.ENEMY),
        position=Coordinate(1, 0),
    )
    effect = ActiveCombatEffect(
        id="pass-without-trace",
        actor_id="druid",
        source_actor_id="druid",
        kind="stealth_bonus_aura",
        label="Przejście bez śladu",
        object_id="spell:pass_without_trace",
        value=10,
    )

    near = resolve_precombat_stealth(
        (caster, near_ally, far_ally, enemy),
        (),
        actor_id="rogue",
        natural_roll=10,
        active_effects=(effect,),
    )
    far = resolve_precombat_stealth(
        (caster, near_ally, far_ally, enemy),
        (),
        actor_id="ranger",
        natural_roll=10,
        active_effects=(effect,),
    )

    assert near.attempt.total == 20
    assert far.attempt.total == 10
