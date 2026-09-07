"""Regressions from the physical playtest: observers, duration and stale loadout."""

from dataclasses import replace
from pathlib import Path

from dnd_board_game.actors import Actor
from dnd_board_game.character_creation import (
    default_character_drafts,
    load_character_catalog,
    load_character_resources,
    build_character,
    apply_boardgame_archetype,
)
from dnd_board_game.character_creation.physical_mana import apply_physical_mana_profile
from dnd_board_game.character_creation.loadout_repair import repair_mira_loadout
from dnd_board_game.combat import current_actor
from dnd_board_game.combat.stealth import HiddenState
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.rules import EffectEvent, EffectEventType, expire_active_effects
from dnd_board_game.rules.physical_mana import mana_ability
from dnd_board_game.world import Coordinate
from tests.unit.test_hero_rules_consistency import heroes
from tests.unit.test_garran_mana_movement import positioned_session


def test_rage_lasts_strength_plus_constitution_rounds_and_survives_save(
    heroes: dict[str, Actor],
    tmp_path: Path,
) -> None:
    s = positioned_session(heroes["brakka"], tmp_path, Coordinate(3, 4))
    actor = current_actor(s.combat_state)
    rounds = max(
        1, (actor.ability_scores.constitution - 10) // 2 + (actor.ability_scores.strength - 10) // 2
    )
    s.use_combat_class_feature("rage")
    assert "KON + modyfikator SIŁ rund" in mana_ability("brakka", "rage").description
    assert next(e for e in s.active_combat_effects if e.kind == "rage").remaining_rounds == rounds
    s._expire_turn_start_effects()
    assert any(e.kind == "rage" for e in s.active_combat_effects)
    for _ in range(rounds - 1):
        s.active_combat_effects = expire_active_effects(
            s.active_combat_effects, EffectEvent(EffectEventType.ROUND_ENDED)
        ).active_effects
        assert any(e.kind == "rage" for e in s.active_combat_effects)
    s._expire_turn_end_effects(current_actor(s.combat_state))
    assert any(e.kind == "rage" for e in s.active_combat_effects)
    s.save_snapshot()
    s.load_snapshot()
    rage = next(e for e in s.active_combat_effects if e.kind == "rage")
    assert rage.remaining_rounds == 1
    assert any(
        "Szał · 1" in c["label"]
        for c in s.state_payload()["combat"]["current_actor"]["status_chips"]
    )
    effects = expire_active_effects(
        s.active_combat_effects, EffectEvent(EffectEventType.ROUND_ENDED)
    ).active_effects
    assert not any(e.kind in {"rage", "rage_duration"} for e in effects)


def test_shoulder_check_preview_is_offensive_and_has_structured_mana(
    heroes: dict[str, Actor],
    tmp_path: Path,
) -> None:
    s = positioned_session(heroes["brakka"], tmp_path, Coordinate(3, 4))
    s.use_combat_class_feature("rage")
    payload = s.start_combat_class_feature_targeting("shoulder_check")["combat"][
        "class_feature_targeting"
    ]
    assert payload["mana_cost"] == list(mana_ability("brakka", "shoulder_check").cost)
    assert "leczenia" not in payload["instructions"]
    assert "leczenia" not in payload["cost"]
    assert payload["instructions"] == mana_ability("brakka", "shoulder_check").description


def test_mira_observers_stay_lit_until_action_preview_and_return_on_cancel(
    heroes: dict[str, Actor],
    tmp_path: Path,
) -> None:
    s = positioned_session(heroes["mira"], tmp_path, Coordinate(3, 4))
    actor = current_actor(s.combat_state)
    enemies = [a for a in s.combat_state.actors if a.faction != actor.faction]
    s.combat_state = replace(
        s.combat_state, hidden_states=(HiddenState("mira", 20, (str(enemies[0].id),)),)
    )
    target = s._current_board_scan_target()
    assert not target.positions  # Passive feedback, no forced scanner input.
    colors = {frame.color for frame in target.feedback.frames}
    assert LedColor.STEALTH_OBSERVER_UNAWARE in colors
    assert LedColor.STEALTH_OBSERVER_SEES in colors
    payload = s.state_payload()["combat"]
    assert not payload["current_actor"]["hidden"]["visible_observer_attack_advantage"]
    assert all(
        not o["has_attack_advantage_against_actor"]
        for o in payload["current_actor"]["hidden"]["observers"]
    )
    assert "basic:hide" not in {o.id for o in s._combat_turn_action_options()}
    option = next(
        o for o in s._combat_turn_action_options() if o.source_id and "rapier" in o.source_id
    )
    s.confirm_combat_turn_action(option.id)
    colors = {frame.color for frame in s._current_board_scan_target().feedback.frames}
    assert LedColor.STEALTH_OBSERVER_UNAWARE not in colors
    assert LedColor.STEALTH_OBSERVER_SEES not in colors
    s.cancel_combat_turn_action_preview()
    assert LedColor.STEALTH_OBSERVER_UNAWARE in {
        f.color for f in s._current_board_scan_target().feedback.frames
    }
    move = next(o for o in s._combat_turn_action_options() if o.action.value == "move")
    s.confirm_combat_turn_action(move.id)
    assert not {LedColor.STEALTH_OBSERVER_UNAWARE, LedColor.STEALTH_OBSERVER_SEES} & {
        f.color for f in s._current_board_scan_target().feedback.frames
    }


def test_retired_mira_starter_loadout_is_repaired_once_without_losing_loot() -> None:
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = replace(
        next(d for d in default_character_drafts() if d.id == "mira"),
        equipment_package_id="rogue_burglar",
    )
    old = apply_boardgame_archetype(build_character(draft, catalog, resources).actor)
    loot = replace(next(i for i in old.inventory if i.id == "shortbow"), id="loot:shortbow")
    old = replace(old, hp=7, inventory=(*old.inventory, loot))
    actor = apply_physical_mana_profile(old)
    assert actor.hp == 7 and loot in actor.inventory
    assert not {"shortbow", "arrow", "dagger", "dagger_2"} & {i.id for i in actor.inventory}
    assert sum(i.quantity for i in actor.inventory if i.source_ref == "throwing_knife") == 4
    assert repair_mira_loadout(actor) == actor
    assert actor.currency == old.currency


def test_hide_summary_lists_both_groups_without_retired_panic_penalty(
    heroes: dict[str, Actor], tmp_path: Path
) -> None:
    from dnd_board_game.application.combat_turn_action_flow import CombatTurnActionFlowService
    from dnd_board_game.combat.mira_features import resolve_smoke_screen
    from dnd_board_game.world import BoardState

    s = positioned_session(heroes["mira"], tmp_path, Coordinate(3, 4))
    smoke = resolve_smoke_screen(s.combat_state, ())
    enemies = [a for a in smoke.state.actors if a.faction != current_actor(smoke.state).faction]
    service = CombatTurnActionFlowService()
    pending = service.prepare_hide(
        state=smoke.state, board=BoardState(), active_effects=smoke.active_effects
    )
    result = service.resolve_hide(
        state=smoke.state,
        board=BoardState(),
        pending=pending,
        natural_roll=7,
        opposing_natural_rolls={str(enemies[0].id): 20, str(enemies[1].id): 1},
        active_effects=smoke.active_effects,
    )
    assert enemies[0].name in result.message_body and enemies[1].name in result.message_body
    assert "Nadal widzą Mirę:" in result.message_body
    assert "+2 do ataków" not in result.message_body
    assert not any(e.kind == "smoke_screen_hide_pending" for e in result.active_effects)


def test_loading_old_combat_repairs_mira_inventory(
    heroes: dict[str, Actor], tmp_path: Path
) -> None:
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = replace(
        next(d for d in default_character_drafts() if d.id == "mira"),
        equipment_package_id="rogue_burglar",
    )
    old = build_character(draft, catalog, resources).actor
    s = positioned_session(heroes["mira"], tmp_path, Coordinate(3, 4))
    s.combat_state = replace(
        s.combat_state,
        actors=tuple(
            replace(a, inventory=old.inventory, hp=7) if str(a.id) == "mira" else a
            for a in s.combat_state.actors
        ),
    )
    s.save_snapshot()
    s.load_snapshot()
    mira = current_actor(s.combat_state)
    assert mira.hp == 7
    assert sum(i.quantity for i in mira.inventory if i.source_ref == "throwing_knife") == 4
    assert not {"shortbow", "arrow"} & {i.id for i in mira.inventory}


def test_old_one_turn_rage_is_upgraded_on_load(heroes: dict[str, Actor], tmp_path: Path) -> None:
    from dnd_board_game.rules import EffectDuration

    s = positioned_session(heroes["brakka"], tmp_path, Coordinate(3, 4))
    s.use_combat_class_feature("rage")
    expected = next(e.remaining_rounds for e in s.active_combat_effects if e.kind == "rage")
    s.active_combat_effects = tuple(
        replace(e, duration=EffectDuration.UNTIL_TURN_START, remaining_rounds=None)
        if e.kind in {"rage", "rage_duration"} else e for e in s.active_combat_effects
    )
    s.save_snapshot()
    s.load_snapshot()
    rage = next(e for e in s.active_combat_effects if e.kind == "rage")
    assert rage.remaining_rounds == expected
    s._expire_turn_start_effects()
    assert any(e.kind == "rage" for e in s.active_combat_effects)


def test_active_physical_rage_cannot_be_toggled_in_later_turns(
    heroes: dict[str, Actor], tmp_path: Path,
) -> None:
    import pytest
    from dnd_board_game.combat import ActionUse
    from dnd_board_game.combat.class_features import resolve_rage
    from dnd_board_game.combat.session import TurnActionState

    s = positioned_session(heroes["brakka"], tmp_path, Coordinate(3, 4))
    assert any(o.action_id == "rage" for o in s._combat_turn_action_options())
    s.use_combat_class_feature("rage")
    # Reproduce the reported second turn: main action spent, bonus action ready.
    s.active_combat_effects = expire_active_effects(
        s.active_combat_effects, EffectEvent(EffectEventType.ROUND_ENDED)
    ).active_effects
    s.combat_state = replace(
        s.combat_state,
        initiative_order=replace(s.combat_state.initiative_order, round_number=2),
        turn_action=TurnActionState(action_use=ActionUse.ACTION_USED),
    )
    s.save_snapshot()
    s.load_snapshot()
    for action_use in (ActionUse.ACTION_AVAILABLE, ActionUse.ACTION_USED):
        s.combat_state = replace(
            s.combat_state, turn_action=replace(s.combat_state.turn_action, action_use=action_use)
        )
        options = s._combat_turn_action_menu_payload()["options"]
        assert not any(o["action_id"] == "rage" or o["shortcut"] == "Q" for o in options)
        assert any(o["action_id"] == "acceleration" for o in options)
    before_state, before_effects = s.combat_state, s.active_combat_effects
    with pytest.raises(ValueError, match="Szał już trwa"):
        resolve_rage(s.combat_state, s.active_combat_effects)
    with pytest.raises(ValueError, match="Szał już trwa"):
        s.use_combat_class_feature("rage")
    assert s.combat_state == before_state
    assert s.active_combat_effects == before_effects
    assert s.combat_state.turn_action.bonus_action_use == ActionUse.ACTION_AVAILABLE
    # Once the duration expires, the same activation becomes available again.
    for _ in range(20):
        s.active_combat_effects = expire_active_effects(
            s.active_combat_effects, EffectEvent(EffectEventType.ROUND_ENDED)
        ).active_effects
    assert any(o.action_id == "rage" for o in s._combat_turn_action_options())
    s.use_combat_class_feature("rage")
    assert any(e.kind == "rage" for e in s.active_combat_effects)
