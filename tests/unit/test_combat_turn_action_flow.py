from dataclasses import replace

import pytest

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    ActorResourcePool,
    Faction,
    FeatureGrant,
    FeatureSourceKind,
    ProficiencyProfile,
    RecoveryPeriod,
)
from dnd_board_game.application import CombatTurnActionFlowService
from dnd_board_game.combat import (
    AttackSource,
    AttackSourceType,
    CombatState,
    CombatCondition,
    ConditionState,
    HiddenState,
    InitiativeEntry,
    InitiativeOrder,
    start_combat,
    has_condition,
    finish_turn,
    movement_remaining,
    resolve_smoke_screen,
)
from dnd_board_game.inventory import ArmorCategory, InventoryItem
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import BLOCKING_TERRAIN, BoardState, Coordinate


def _actor(actor_id: str, faction: Faction, position: Coordinate) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(dexterity=14),
    )


def _state(*actors: Actor) -> CombatState:
    request = D20RollRequest()
    order = InitiativeOrder(
        tuple(
            InitiativeEntry(
                actor,
                resolve_d20_roll(D20RollInput(request, 20 - index)),
                2,
                index,
            )
            for index, actor in enumerate(actors)
        )
    )
    return start_combat(tuple(actors), order)


def _mira(actor: Actor) -> Actor:
    return replace(
        actor,
        id=ActorId("mira"),
        name="Mira",
        features=(
            *actor.features,
            FeatureGrant(
                "mira_shadow_stealth",
                "Mistrzyni ukrycia",
                FeatureSourceKind.SCENARIO,
                "boardgame_archetype:mira",
            ),
        ),
    )


def _source() -> AttackSource:
    return AttackSource("Miecz", AttackSourceType.WEAPON, 5, D20RollRequest())


def test_dash_consumes_action_and_extends_movement() -> None:
    service = CombatTurnActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))

    transition = service.use_dash(state=_state(hero, goblin), active_effects=())

    assert transition.state.turn_action.action_use.value == "action_used"
    assert transition.state.turn_action.extra_movement_feet == 30
    assert dict(transition.event_payload) == {
        "actor_id": "hero",
        "extra_movement_feet": 30,
    }


def test_dodge_and_disengage_create_explicit_turn_effects() -> None:
    service = CombatTurnActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))
    state = _state(hero, goblin)

    dodged = service.use_dodge(state=state, active_effects=())
    disengaged = service.use_disengage(state=state, active_effects=())

    assert dodged.active_effects[0].kind == "dodge_until_next_turn"
    assert dodged.state.turn_action.action_use.value == "action_used"
    assert disengaged.active_effects[0].kind == "disengage_until_turn_end"
    assert disengaged.state.turn_action.action_use.value == "action_used"


def test_prone_and_stand_transitions_do_not_consume_action() -> None:
    service = CombatTurnActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))
    state = _state(hero, goblin)

    prone = service.drop_prone(state=state, active_effects=())
    stood = service.stand_up(state=prone.state, active_effects=())

    assert has_condition(prone.state.condition_states, "hero", CombatCondition.PRONE)
    assert prone.state.turn_action.action_use.value == "action_available"
    assert not has_condition(stood.state.condition_states, "hero", CombatCondition.PRONE)
    assert stood.state.turn_action.movement_used_feet == 15
    assert stood.state.turn_action.action_use.value == "action_available"


def test_help_preparation_and_confirmation_create_advantage_effect() -> None:
    service = CombatTurnActionFlowService()
    helper = _actor("helper", Faction.ALLY, Coordinate(0, 0))
    ally = _actor("ally", Faction.ALLY, Coordinate(0, 1))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = _state(helper, ally, goblin)

    preparation = service.prepare_help(state=state)
    confirmed = service.confirm_help(
        state=state,
        active_effects=(),
        helper_id=preparation.helper_id,
        ally_ids=preparation.ally_ids,
        target_ids=preparation.target_ids,
        ally_id="ally",
        target_id="goblin",
    )

    assert preparation.ally_ids == ("ally",)
    assert preparation.target_ids == ("goblin",)
    effect = confirmed.active_effects[0]
    assert effect.kind == "help_attack_advantage"
    assert effect.actor_id == "ally"
    assert effect.target_actor_id == "goblin"


def test_ready_preparation_and_confirmation_create_trigger_effect() -> None:
    service = CombatTurnActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))
    state = _state(hero, goblin)

    preparation = service.prepare_ready(
        state=state,
        attack_sources_by_actor={hero.id: _source()},
    )
    confirmed = service.confirm_ready(
        state=state,
        active_effects=(),
        actor_id=preparation.actor_id,
        triggers=preparation.triggers,
        trigger="enemy_moves",
    )

    assert preparation.triggers == ("enemy_moves", "enemy_attacks")
    assert confirmed.active_effects[0].kind == "ready_attack"
    assert confirmed.active_effects[0].object_id == "combat_action:ready:enemy_moves"
    assert confirmed.state.turn_action.action_use.value == "action_used"


def test_hide_uses_action_and_preserves_per_observer_hidden_state() -> None:
    service = CombatTurnActionFlowService()
    hero = _mira(replace(
        _actor("hero", Faction.ALLY, Coordinate(0, 0)),
        speed_feet=25,
        proficiencies=ProficiencyProfile(skills=("stealth",)),
    ))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))
    board = BoardState()
    board.set_terrain(Coordinate(2, 0), BLOCKING_TERRAIN)
    state = _state(hero, goblin)

    pending = service.prepare_hide(state=state, board=board)
    hidden = service.resolve_hide(
        state=state,
        board=board,
        pending=pending,
        natural_roll=12,
        active_effects=(),
    )

    assert pending.modifier == 4
    assert hidden.state.turn_action.action_use.value == "action_used"
    assert hidden.state.hidden_states[0].hidden_from_actor_ids == ("goblin",)
    assert hidden.state.hidden_states[0].stealth_total == 16
    assert movement_remaining(hidden.state, hero) == 20

    after_twenty_feet = replace(
        hidden.state,
        turn_action=replace(hidden.state.turn_action, movement_used_feet=20),
    )
    assert movement_remaining(after_twenty_feet, hero) == 0

    ended = service.end_hide(state=after_twenty_feet, active_effects=())
    assert ended.state.hidden_states == ()
    assert movement_remaining(ended.state, hero) == 5
    assert ended.state.turn_action.action_use.value == "action_used"

    adjacent_state = replace(
        hidden.state,
        actors=tuple(
            replace(candidate, position=Coordinate(3, 0))
            if candidate.id == hero.id
            else candidate
            for candidate in hidden.state.actors
        ),
    )
    after_turn = finish_turn(adjacent_state)
    assert after_turn.hidden_states == ()


def test_smoke_screen_allows_fresh_hide_beside_enemy_after_action_was_spent() -> None:
    service = CombatTurnActionFlowService()
    base_mira = _mira(_actor("hero", Faction.ALLY, Coordinate(0, 0)))
    mira = replace(
        base_mira,
        features=(
            *base_mira.features,
            FeatureGrant(
                "smoke_screen",
                "Zasłona dymna",
                FeatureSourceKind.SCENARIO,
                "boardgame_archetype:mira",
            ),
        ),
        resource_pools=(
            ActorResourcePool(
                "trick_uses",
                "Fortele",
                2,
                2,
                RecoveryPeriod.LONG_REST,
            ),
        ),
    )
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(1, 0))
    state = _state(mira, goblin)
    smoke = resolve_smoke_screen(state, ())

    pending = service.prepare_hide(
        state=smoke.state,
        board=BoardState(),
        active_effects=smoke.active_effects,
    )
    hidden = service.resolve_hide(
        state=smoke.state,
        board=BoardState(),
        pending=pending,
        natural_roll=20,
        opposing_natural_rolls={"goblin": 20},
        active_effects=smoke.active_effects,
    )

    assert hidden.state.turn_action.action_use.value == "action_used"
    assert hidden.state.hidden_states[0].hidden_from_actor_ids == ("goblin",)
    assert all(
        effect.kind not in {"smoke_screen_hide_pending", "movement_speed_cap"}
        for effect in hidden.active_effects
    )


def test_heavy_armor_applies_speed_penalty_and_requires_two_stealth_rolls() -> None:
    service = CombatTurnActionFlowService()
    armor = InventoryItem(
        "chain_mail",
        "Kolczuga",
        "armor",
        equipped=True,
        armor_category=ArmorCategory.HEAVY,
        armor_base_ac=16,
        armor_dexterity_cap=0,
        armor_strength_requirement=13,
        stealth_disadvantage=True,
        armor_proficiency="heavy",
    )
    hero = _mira(replace(
        _actor("hero", Faction.ALLY, Coordinate(0, 0)),
        inventory=(armor,),
        ability_scores=AbilityScores(strength=12, dexterity=14),
        proficiencies=ProficiencyProfile(armor=("heavy",)),
    ))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))
    board = BoardState()
    board.set_terrain(Coordinate(2, 0), BLOCKING_TERRAIN)
    state = _state(hero, goblin)

    dashed = service.use_dash(state=state, active_effects=())
    pending = service.prepare_hide(state=state, board=board)

    assert dashed.state.turn_action.extra_movement_feet == 20
    assert pending.roll_mode == "disadvantage"
    with pytest.raises(ValueError, match="dwóch wyników"):
        service.resolve_hide(
            state=state,
            board=board,
            pending=pending,
            natural_roll=18,
            active_effects=(),
        )
    hidden = service.resolve_hide(
        state=state,
        board=board,
        pending=pending,
        natural_roll=18,
        natural_roll_2=7,
        active_effects=(),
    )
    assert hidden.state.hidden_states == ()
    assert "automatycznie się kończy" in hidden.message_body


def test_search_uses_action_and_reveals_hidden_enemy_to_searcher() -> None:
    service = CombatTurnActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))
    state = replace(
        _state(hero, goblin),
        hidden_states=(HiddenState("goblin", 14, ("hero",)),),
    )

    pending = service.prepare_search(state=state)
    searched = service.resolve_search(
        state=state,
        pending=pending,
        natural_roll=20,
        active_effects=(),
    )

    assert searched.state.turn_action.action_use.value == "action_used"
    assert searched.state.hidden_states == ()
    assert dict(searched.event_payload)["found_actor_ids"] == ["goblin"]


def test_mira_combat_trap_detection_scans_45_feet_and_consumes_action() -> None:
    service = CombatTurnActionFlowService()
    base_mira = _mira(_actor("hero", Faction.ALLY, Coordinate(0, 0)))
    mira = replace(
        base_mira,
        features=(
            *base_mira.features,
            FeatureGrant(
                "combat_trap_detection",
                "Wykrycie pułapek",
                FeatureSourceKind.SCENARIO,
                "boardgame_archetype:mira",
            ),
        ),
    )
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))
    state = _state(mira, goblin)

    pending = service.prepare_trap_detection(state=state)
    resolved = service.resolve_trap_detection(
        state=state,
        pending=pending,
        natural_roll=14,
        natural_roll_2=None,
        active_effects=(),
    )

    assert pending.action == "detect_traps"
    assert resolved.state.turn_action.action_use.value == "action_used"
    assert dict(resolved.event_payload)["radius_feet"] == 45
    assert "obszar 45 stóp" in resolved.message_body


def test_trap_detection_rejects_other_heroes_and_an_already_spent_action() -> None:
    service = CombatTurnActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))
    with pytest.raises(ValueError, match="nie posiada"):
        service.prepare_trap_detection(state=_state(hero, goblin))

    base_mira = _mira(hero)
    mira = replace(
        base_mira,
        features=(
            *base_mira.features,
            FeatureGrant(
                "combat_trap_detection",
                "Wykrycie pułapek",
                FeatureSourceKind.SCENARIO,
                "boardgame_archetype:mira",
            ),
        ),
    )
    spent = service.use_dodge(state=_state(mira, goblin), active_effects=()).state
    with pytest.raises(ValueError, match="już zużyta"):
        service.prepare_trap_detection(state=spent)


def test_net_escape_uses_plain_strength_check_and_consumes_action() -> None:
    service = CombatTurnActionFlowService()
    hero = replace(
        _actor("hero", Faction.ALLY, Coordinate(0, 0)),
        ability_scores=AbilityScores(strength=14),
    )
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))
    state = replace(
        _state(hero, goblin),
        condition_states=(
            ConditionState(
                "hero",
                CombatCondition.RESTRAINED,
                source_label="Sieć: Sieć",
            ),
        ),
    )

    pending = service.prepare_net_escape(state=state)
    escaped = service.resolve_net_escape(
        state=state,
        pending=pending,
        natural_roll=8,
        active_effects=(),
    )

    assert pending.modifier == 2
    assert not has_condition(
        escaped.state.condition_states,
        "hero",
        CombatCondition.RESTRAINED,
    )
    assert escaped.state.turn_action.action_use.value == "action_used"


def test_actions_reject_enemy_turn_and_missing_help_targets() -> None:
    service = CombatTurnActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(4, 0))

    with pytest.raises(ValueError, match="To nie jest tura bohatera"):
        service.use_dash(state=_state(goblin, hero), active_effects=())

    with pytest.raises(ValueError, match="Brak żywego sojusznika"):
        service.prepare_help(state=_state(hero, goblin))
