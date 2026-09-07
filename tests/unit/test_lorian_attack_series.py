"""Only Lorian declares an ordinary multiattack; techniques keep fixed counts."""

from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.actors import Actor
from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.combat import ActionUse, current_actor
from dnd_board_game.combat.physical_mana import (
    attack_maximum,
    declare_series,
    effect,
    is_basic_weapon,
    reconcile_attack_series,
    validate_series_source,
)
from dnd_board_game.ui.routes import create_app
from tests.unit.test_hero_rules_consistency import heroes
from tests.unit.test_garran_mana_movement import positioned_session
from dnd_board_game.world import Coordinate


@pytest.mark.parametrize("hero_id", [i for i in PLAYABLE_HERO_IDS if i != "lorian"])
def test_other_heroes_go_straight_to_one_attack_and_cannot_declare_series(
    heroes: dict[str, Actor],
    tmp_path: Path,
    hero_id: str,
) -> None:
    session = positioned_session(heroes[hero_id], tmp_path, Coordinate(3, 4))
    actor = current_actor(session.combat_state)
    source = next(s for s in session._attack_sources_for_actor(actor) if is_basic_weapon(actor, s))
    session.select_combat_attack_source(source.id)
    session.combat_targeting_attack_source_id = source.id
    assert not session.state_payload()["combat"]["physical_mana"]["needs_attack_count"]
    with pytest.raises(ValueError, match="tylko Lorian"):
        declare_series(session.combat_state, (), 3)
    response = (
        create_app(session).test_client().post("/api/combat/attack-series", json={"count": 3})
    )
    assert response.status_code == 400
    session.select_player_attack_target_at_position(Coordinate(3, 4))
    session.confirm_player_attack_target()
    session.submit_player_attack_roll(natural_roll=2, natural_roll_2=2)
    turn = session.combat_state.turn_action
    assert turn.attacks_used == turn.attacks_maximum == 1
    assert turn.action_use == ActionUse.ACTION_USED
    with pytest.raises(ValueError):
        session.select_player_attack_target_at_position(Coordinate(3, 4))
        session.confirm_player_attack_target()
        session.submit_player_attack_roll(natural_roll=2, natural_roll_2=2)


@pytest.mark.parametrize("used", [0, 1, 3])
def test_old_ordinary_series_is_restricted_after_save_load(
    heroes: dict[str, Actor],
    tmp_path: Path,
    used: int,
) -> None:
    session = positioned_session(heroes["erynd"], tmp_path, Coordinate(3, 4))
    actor = current_actor(session.combat_state)
    source = next(s for s in session._attack_sources_for_actor(actor) if is_basic_weapon(actor, s))
    old_effects = (
        effect("erynd", "mana_attack_series", "Stara seria", 5),
        replace(effect("erynd", "mana_series_source", "Stary rodzaj serii"), object_id="basic"),
    )
    session.active_combat_effects = old_effects
    session.combat_state = replace(
        session.combat_state,
        turn_action=replace(
            session.combat_state.turn_action,
            attacks_used=used,
            attacks_maximum=5,
            attack_action_active=bool(used),
            action_use=ActionUse.ACTION_USED if used else ActionUse.ACTION_AVAILABLE,
        ),
    )
    # The resolver protects direct calls even before the UI reconciles a stale save.
    assert attack_maximum(actor, source, old_effects, 5) == 1
    if used:
        with pytest.raises(ValueError, match="jedno uderzenie"):
            validate_series_source(session.combat_state, source, old_effects)
    session.save_snapshot()
    session.load_snapshot()
    payload = session.state_payload()["combat"]["physical_mana"]
    assert payload["series"]["declared"] is None
    assert not payload["needs_attack_count"]
    if used:
        assert session.combat_state.turn_action.attacks_maximum == 1
        assert session.combat_state.turn_action.attacks_used == used
        assert payload["series"]["remaining"] == 0


@pytest.mark.parametrize(
    "hero_id,source_id", [("erynd", "double_shot"), ("lorian", "optical_scope")]
)
def test_two_attack_techniques_keep_their_fixed_count(
    heroes: dict[str, Actor],
    tmp_path: Path,
    hero_id: str,
    source_id: str,
) -> None:
    from types import SimpleNamespace

    session = positioned_session(heroes[hero_id], tmp_path, Coordinate(3, 4))
    actor = current_actor(session.combat_state)
    source = SimpleNamespace(id=source_id)
    assert attack_maximum(actor, source, (), 1) == 2
    session.combat_state = replace(
        session.combat_state,
        turn_action=replace(
            session.combat_state.turn_action,
            attack_action_active=True,
            action_use=ActionUse.ACTION_USED,
            attacks_used=1,
            attacks_maximum=2,
        ),
    )
    effects = (replace(effect(hero_id, "mana_series_source", "Technika"), object_id=source_id),)
    state, retained = reconcile_attack_series(session.combat_state, effects)
    assert state == session.combat_state and retained == effects


@pytest.mark.parametrize(
    "hero_id,ability_id,effect_kind",
    [
        ("garran", "action_surge", "mana_surge"),
        ("brakka", "reckless_attack", "mana_reckless"),
    ],
)
def test_attack_modifiers_prepare_only_one_ordinary_hit(
    heroes: dict[str, Actor],
    tmp_path: Path,
    hero_id: str,
    ability_id: str,
    effect_kind: str,
) -> None:
    from dnd_board_game.rules.physical_mana import mana_ability

    session = positioned_session(heroes[hero_id], tmp_path, Coordinate(3, 4))
    session.use_combat_class_feature(ability_id)
    modifier = next(e for e in session.active_combat_effects if e.kind == effect_kind)
    assert modifier.value == 1
    assert session.combat_state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
    assert "Następny zwykły atak" in mana_ability(hero_id, ability_id).description
