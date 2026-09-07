"""Garran pays a positional movement cost, with no physical card validation."""

from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.character_creation.physical_mana import apply_physical_mana_profile
from dnd_board_game.combat import current_actor
from dnd_board_game.combat.archetype_flaws import (
    flaw_ability_check_modifiers,
    flaw_attack_roll_modifiers,
    flaw_saving_throw_modifiers,
    synchronize_dynamic_flaw_effects,
)
from dnd_board_game.combat.magic_movement import move_actor_magically
from dnd_board_game.combat.physical_mana_movement import (
    declare_ordinary_movement,
    movement_mana_notice,
)
from dnd_board_game.rules import ActiveEffect, EffectEvent, EffectEventType, expire_active_effects
from dnd_board_game.rules.physical_mana import FLAWS
from dnd_board_game.ui.exploration_app import ExplorationUiSession, _feature_grant_payload
from dnd_board_game.ui.routes import _character_sheet_feature_entries
from dnd_board_game.world import Coordinate
from tests.unit.test_hero_rules_consistency import heroes
from tests.unit.test_physical_mana import session_for


def positioned_session(
    hero: Actor, tmp_path: Path, enemy_position: Coordinate
) -> ExplorationUiSession:
    session = session_for(hero, tmp_path)
    state = session.combat_state
    actor = current_actor(state)
    enemies = [a for a in state.actors if a.faction == Faction.ENEMY]
    positions = {actor.id: Coordinate(3, 3), enemies[0].id: enemy_position}
    positions.update({a.id: Coordinate(10 + i, 10) for i, a in enumerate(enemies[1:])})
    session.combat_state = replace(
        state,
        actors=tuple(replace(a, position=positions.get(a.id, a.position)) for a in state.actors),
    )
    return session


@pytest.mark.parametrize(
    "position,cost", [(Coordinate(3, 4), 2), (Coordinate(4, 4), 2), (Coordinate(3, 5), 1)]
)
def test_cost_uses_adjacent_enemy_including_diagonal_in_solo(
    heroes: dict[str, Actor], tmp_path: Path, position: Coordinate, cost: int
) -> None:
    session = positioned_session(heroes["garran"], tmp_path, position)
    notice = movement_mana_notice(session.combat_state, ())
    assert notice.cost == cost and not notice.started
    payload = session.state_payload()["combat"]["physical_mana"]
    assert payload["movement"]["cost"] == cost
    assert payload["selected_cost"] == "1 dowolna za każdy atak"
    move = next(o for o in session._combat_turn_action_options() if o.action.value == "move")
    assert move.label == notice.label and notice.description in move.description


@pytest.mark.parametrize(
    "faction,hp", [(Faction.ALLY, 10), (Faction.NEUTRAL, 10), (Faction.ENEMY, 0)]
)
def test_allies_neutrals_and_defeated_enemies_do_not_trigger(
    heroes: dict[str, Actor], tmp_path: Path, faction: Faction, hp: int
) -> None:
    session = positioned_session(heroes["garran"], tmp_path, Coordinate(3, 4))
    session.combat_state = replace(
        session.combat_state,
        actors=tuple(
            replace(a, faction=faction, hp=hp) if a.position == Coordinate(3, 4) else a
            for a in session.combat_state.actors
        ),
    )
    assert movement_mana_notice(session.combat_state, ()).cost == 1


def test_other_hero_and_legacy_profile_keep_their_rules(
    heroes: dict[str, Actor], tmp_path: Path
) -> None:
    session = positioned_session(heroes["brakka"], tmp_path, Coordinate(3, 4))
    assert movement_mana_notice(session.combat_state, ()).cost == 1
    legacy = replace(heroes["garran"], position=Coordinate(3, 3))
    session.combat_state = replace(
        session.combat_state,
        actors=tuple(
            replace(legacy, id=a.id) if a.id == current_actor(session.combat_state).id else a
            for a in session.combat_state.actors
        ),
    )
    assert movement_mana_notice(session.combat_state, ()) is None
    assert declare_ordinary_movement(session.combat_state, ()) == ()


@pytest.mark.parametrize(
    "enemy_position,first_destination,cost",
    [
        (Coordinate(3, 4), Coordinate(4, 3), 2),
        (Coordinate(3, 5), Coordinate(3, 4), 1),
    ],
)
def test_split_movement_remembers_start_price_after_save_and_resets_next_turn(
    heroes: dict[str, Actor],
    tmp_path: Path,
    enemy_position: Coordinate,
    first_destination: Coordinate,
    cost: int,
) -> None:
    session = positioned_session(heroes["garran"], tmp_path, enemy_position)
    session.preview_combat_movement(col=first_destination.col, row=first_destination.row)
    assert not movement_mana_notice(session.combat_state, session.active_combat_effects).started
    assert "raz na turę" in session.board_message
    session.submit_combat_movement(col=first_destination.col, row=first_destination.row)
    assert session.pending_opportunity_movement is None
    notice = movement_mana_notice(session.combat_state, session.active_combat_effects)
    assert notice.started and notice.cost == cost
    assert "bez kolejnej dopłaty" in notice.label
    assert (
        declare_ordinary_movement(session.combat_state, session.active_combat_effects)
        == session.active_combat_effects
    )
    session.save_snapshot()
    session.load_snapshot()
    assert movement_mana_notice(session.combat_state, session.active_combat_effects) == notice
    # The marker only records a declared action; no card hand/balance is required.
    actor = current_actor(session.combat_state)
    remaining = expire_active_effects(
        session.active_combat_effects,
        EffectEvent(EffectEventType.TURN_END, actor_id=str(actor.id)),
    ).active_effects
    assert not movement_mana_notice(session.combat_state, remaining).started


def test_opportunity_cancel_is_free_and_confirmation_locks_origin_cost(
    heroes: dict[str, Actor],
    tmp_path: Path,
) -> None:
    session = positioned_session(heroes["garran"], tmp_path, Coordinate(3, 4))
    session.submit_combat_movement(col=3, row=2)
    assert session.pending_opportunity_movement is not None
    assert not movement_mana_notice(session.combat_state, session.active_combat_effects).started
    session.cancel_opportunity_movement()
    assert not movement_mana_notice(session.combat_state, session.active_combat_effects).started
    session.submit_combat_movement(col=3, row=2)
    session.confirm_opportunity_movement()
    notice = movement_mana_notice(session.combat_state, session.active_combat_effects)
    assert notice.started and notice.cost == 2


def test_forced_or_ability_movement_does_not_start_ordinary_movement(
    heroes: dict[str, Actor],
    tmp_path: Path,
) -> None:
    session = positioned_session(heroes["garran"], tmp_path, Coordinate(3, 4))
    state = move_actor_magically(
        session.combat_state, current_actor(session.combat_state), Coordinate(3, 1)
    )
    notice = movement_mana_notice(state, session.active_combat_effects)
    assert notice.cost == 1 and not notice.started
    effects = declare_ordinary_movement(state, ())
    state = move_actor_magically(state, current_actor(state), Coordinate(3, 3))
    assert movement_mana_notice(state, effects).cost == 1


def test_stale_remorse_penalties_and_saved_text_are_replaced(heroes: dict[str, Actor]) -> None:
    actor = apply_physical_mana_profile(heroes["garran"])
    legacy_effect = ActiveEffect(
        id="old",
        actor_id="garran",
        kind="flaw_remorse_active",
        label="Wyrzuty sumienia",
        object_id="old",
        value=-2,
    )
    for modifiers in (
        flaw_attack_roll_modifiers,
        flaw_saving_throw_modifiers,
        flaw_ability_check_modifiers,
    ):
        assert modifiers(actor, (legacy_effect,)) == ()
    assert synchronize_dynamic_flaw_effects((actor,), (), (legacy_effect,)) == ()
    feature = next(f for f in actor.features if f.feature_id == FLAWS["garran"][0])
    stale = replace(feature, label="Wyrzuty sumienia", description="Stara dopłata za atak")
    payload = _feature_grant_payload(stale, "garran")
    assert payload["label"] == "Nieustępliwość" and payload["mechanics"] == FLAWS["garran"][2]
    entry = _character_sheet_feature_entries((stale,), actor_id="garran")[0]
    assert entry["name"] == "Nieustępliwość" and entry["rule_text"] == FLAWS["garran"][2]


@pytest.mark.parametrize("prone", [False, True])
def test_same_tile_is_free_unless_ordinary_movement_stands_up(
    heroes: dict[str, Actor],
    tmp_path: Path,
    prone: bool,
) -> None:
    from dnd_board_game.combat.conditions import CombatCondition, ConditionState

    session = positioned_session(heroes["garran"], tmp_path, Coordinate(3, 4))
    if prone:
        session.combat_state = replace(
            session.combat_state,
            condition_states=(ConditionState("garran", CombatCondition.PRONE),),
        )
    session.submit_combat_movement(col=3, row=3)
    notice = movement_mana_notice(session.combat_state, session.active_combat_effects)
    assert notice.started == prone
    assert notice.cost == 2
