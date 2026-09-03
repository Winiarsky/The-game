from dataclasses import replace

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    Faction,
    FeatureGrant,
    FeatureSourceKind,
    ProficiencyProfile,
    CreatureSize,
    passive_skill_score,
    skill_modifier,
)
from dnd_board_game.combat import (
    AttackSource,
    AttackSourceType,
    HiddenState,
    SceneObject,
    attack_source_with_hidden_advantage,
    hide_eligibility,
    is_hidden_from,
    legal_attack_targets,
    reveal_all_to_observer,
    refresh_hidden_after_movement,
    resolve_hide,
    resolve_search,
)
from dnd_board_game.combat.setup import SetupVisibility
from dnd_board_game.rules import D20RollRequest, RollMode
from dnd_board_game.world import BLOCKING_TERRAIN, BoardState, Coordinate


def _actor(
    actor_id: str,
    faction: Faction,
    position: Coordinate,
    *,
    dexterity: int = 10,
    wisdom: int = 10,
    skills: tuple[str, ...] = (),
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(dexterity=dexterity, wisdom=wisdom),
        proficiency_bonus=2,
        proficiencies=ProficiencyProfile(skills=skills),
    )


def _source() -> AttackSource:
    return AttackSource("Łuk", AttackSourceType.WEAPON, 80, D20RollRequest())


def _as_mira(actor: Actor) -> Actor:
    return replace(
        actor,
        id=ActorId("mira"),
        name="Mira",
        features=(
            *actor.features,
            FeatureGrant(
                feature_id="mira_shadow_stealth",
                label="Mistrzyni ukrycia",
                source_kind=FeatureSourceKind.SCENARIO,
                source_ref="boardgame_archetype:mira",
            ),
        ),
    )


def test_mira_can_hide_in_clear_sight_but_not_beside_a_conscious_enemy() -> None:
    mira = _as_mira(_actor("hero", Faction.ALLY, Coordinate(0, 0)))
    distant = _actor("distant", Faction.ENEMY, Coordinate(3, 0))
    adjacent = replace(distant, id=ActorId("adjacent"), position=Coordinate(1, 0))

    assert hide_eligibility(BoardState(), mira, (mira, distant)).allowed is True
    blocked = hide_eligibility(BoardState(), mira, (mira, adjacent))
    assert blocked.allowed is False
    assert blocked.blocking_observer_ids == ("adjacent",)


def test_mira_records_individual_perception_and_ends_stealth_when_seen_by_all() -> None:
    mira = _as_mira(_actor("hero", Faction.ALLY, Coordinate(0, 0)))
    first = _actor("first", Faction.ENEMY, Coordinate(3, 0))
    second = _actor("second", Faction.ENEMY, Coordinate(4, 0))

    result = resolve_hide(
        (),
        mira,
        (mira, first, second),
        stealth_total=12,
        observer_perception_totals={"first": 11, "second": 12},
    )

    assert result.hidden_state == HiddenState(
        "mira",
        12,
        ("first",),
        (("first", 11), ("second", 12)),
    )
    assert result.detected_by_actor_ids == ("second",)

    seen_by_all = resolve_hide(
        (),
        mira,
        (mira, first),
        stealth_total=5,
        observer_perception_totals={"first": 15},
    )
    assert seen_by_all.hidden_state is None
    assert seen_by_all.hidden_states == ()
    assert seen_by_all.detected_by_actor_ids == ("first",)


def test_mira_new_stealth_session_rebuilds_observer_results_after_last_detection() -> None:
    mira = _as_mira(_actor("hero", Faction.ALLY, Coordinate(0, 0)))
    first = _actor("first", Faction.ENEMY, Coordinate(3, 0))
    second = _actor("second", Faction.ENEMY, Coordinate(4, 0))
    previous_session = (HiddenState("mira", 18, ("first",)),)

    ended = resolve_search(previous_session, first, perception_total=18)
    restarted = resolve_hide(
        ended.hidden_states,
        mira,
        (mira, first, second),
        stealth_total=14,
        observer_perception_totals={"first": 15, "second": 10},
    )

    assert ended.hidden_states == ()
    assert restarted.hidden_state == HiddenState(
        "mira",
        14,
        ("second",),
        (("first", 15), ("second", 10)),
    )
    assert restarted.detected_by_actor_ids == ("first",)


def test_skill_profile_applies_proficiency_to_stealth_and_passive_perception() -> None:
    rogue = _actor("rogue", Faction.ALLY, Coordinate(0, 0), dexterity=16, skills=("stealth",))
    scout = _actor("scout", Faction.ENEMY, Coordinate(4, 0), wisdom=14, skills=("perception",))

    assert skill_modifier(rogue, "stealth") == 5
    assert passive_skill_score(scout, "perception") == 14


def test_reveal_all_to_observer_preserves_other_observers() -> None:
    states = (
        HiddenState("goblin", 18, ("wizard", "cleric")),
        HiddenState("rogue", 21, ("wizard",)),
    )

    revealed = reveal_all_to_observer(states, "wizard")

    assert revealed == (HiddenState("goblin", 18, ("cleric",)),)


def test_hide_requires_breaking_clear_sight_but_three_quarters_cover_is_enough() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))
    board = BoardState()

    visible = hide_eligibility(board, hero, (hero, goblin))
    covered = hide_eligibility(
        board,
        hero,
        (hero, goblin),
        (
            SceneObject(
                "wall",
                "Blanki",
                (Coordinate(2, 0),),
                "",
                visibility=SetupVisibility.VISIBLE,
                projectile_cover_bonus=5,
            ),
        ),
    )

    assert visible.allowed is False
    assert visible.blocking_observer_ids == ("goblin",)
    assert covered.allowed is True


def test_lightfoot_halfling_can_hide_behind_larger_creature() -> None:
    halfling = replace(
        _actor("halfling", Faction.ALLY, Coordinate(0, 0)),
        size=CreatureSize.SMALL,
        features=(
            FeatureGrant(
                feature_id="naturally_stealthy",
                label="Naturally Stealthy",
                source_kind=FeatureSourceKind.SPECIES,
                source_ref="halfling",
            ),
        ),
    )
    ally = _actor("fighter", Faction.ALLY, Coordinate(2, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))

    result = hide_eligibility(BoardState(), halfling, (halfling, ally, goblin))

    assert result.allowed is True
    assert result.blocking_observer_ids == ()


def test_hide_is_resolved_individually_against_passive_perception() -> None:
    rogue = _actor("rogue", Faction.ALLY, Coordinate(0, 0), dexterity=16, skills=("stealth",))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0), wisdom=10)
    scout = _actor("scout", Faction.ENEMY, Coordinate(4, 1), wisdom=16, skills=("perception",))

    result = resolve_hide((), rogue, (rogue, goblin, scout), stealth_total=15)

    assert result.hidden_state == HiddenState("rogue", 15, ("goblin",))
    assert result.detected_by_actor_ids == ("scout",)


def test_hide_accepts_light_based_passive_perception_adjustments() -> None:
    rogue = _actor("rogue", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0), wisdom=16)
    scout = _actor("scout", Faction.ENEMY, Coordinate(4, 1), wisdom=20)

    result = resolve_hide(
        (),
        rogue,
        (rogue, goblin, scout),
        stealth_total=12,
        passive_perception_adjustments={"goblin": -5},
        automatically_hidden_from_actor_ids=("scout",),
    )

    assert result.hidden_state == HiddenState(
        "rogue",
        12,
        ("goblin", "scout"),
    )
    assert result.detected_by_actor_ids == ()


def test_search_reveals_only_to_the_searching_actor() -> None:
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))
    scout = _actor("scout", Faction.ENEMY, Coordinate(4, 1))
    hidden = (HiddenState("rogue", 15, ("goblin", "scout")),)

    result = resolve_search(hidden, goblin, perception_total=15)

    assert result.found_actor_ids == ("rogue",)
    assert result.hidden_states == (HiddenState("rogue", 15, ("scout",)),)


def test_moving_back_into_clear_sight_ends_hidden_relationship() -> None:
    board = BoardState()
    board.set_terrain(Coordinate(2, 0), BLOCKING_TERRAIN)
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))
    moved = replace(hero, position=Coordinate(3, 0))

    result = refresh_hidden_after_movement(
        board,
        moved,
        (moved, goblin),
        (HiddenState("hero", 18, ("goblin",)),),
    )

    assert result.revealed_to_actor_ids == ("goblin",)
    assert result.hidden_states == ()


def test_hidden_target_is_not_legal_and_hidden_attacker_gets_advantage() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))
    hidden = (HiddenState("hero", 18, ("goblin",)),)

    targets = legal_attack_targets(BoardState(), goblin, (hero, goblin), _source(), hidden)
    advantaged = attack_source_with_hidden_advantage(
        _source(),
        is_hidden_from(hidden, "hero", "goblin"),
    )

    assert targets == ()
    assert advantaged.attack_roll_request.mode == RollMode.ADVANTAGE
    assert advantaged.attack_roll_request.modifiers[-1].label == "Atak z ukrycia"
