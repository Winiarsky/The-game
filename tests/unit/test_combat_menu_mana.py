"""Action tiles show canonical prices and one entry per executable feature."""

from pathlib import Path

import pytest

from dnd_board_game.application.recruitment_arena import HERO_ORDER
from dnd_board_game.combat.context_menu import (
    CombatMenuAction,
    CombatMenuCategory,
    CombatMenuOption,
)
from dnd_board_game.combat.physical_mana_movement import declare_ordinary_movement
from dnd_board_game.rules.physical_mana import mana_ability
from dnd_board_game.ui.combat_menu_mana import menu_mana_payload
from tests.unit.test_recruitment_arena import arena, begin


@pytest.mark.parametrize("hero", HERO_ORDER)
def test_all_hero_tiles_have_prices_and_unique_shortcuts(
    hero: str, tmp_path: Path
) -> None:
    session = arena(tmp_path)
    begin(session, hero)
    if hero == "brakka":
        session.use_combat_class_feature("rage")
    options = session._combat_turn_action_menu_payload()["options"]
    shortcuts = [o["shortcut"] for o in options if o["shortcut"]]
    assert len(shortcuts) == len(set(shortcuts))
    for option in options:
        assert isinstance(option["mana_cost"], list)
        ability = mana_ability(hero, option["action_id"] or option["source_id"] or "")
        if ability:
            assert option["mana_cost"] == list(ability.cost)
    assert next(o for o in options if o["id"] == "turn:end")["mana_cost"] == []
    assert next(o for o in options if o["shortcut"] == "SPACE")["mana_cost"] == ["*"]


def test_roar_has_one_tile_and_opens_area_preview(tmp_path: Path) -> None:
    session = arena(tmp_path)
    begin(session, "brakka")
    before = session._combat_turn_action_menu_payload()["options"]
    assert next(o for o in before if o["shortcut"] == "Q")["mana_cost"] == ["C"]
    session.use_combat_class_feature("rage")
    options = session._combat_turn_action_menu_payload()["options"]
    roar = [o for o in options if o["shortcut"] == "S"]
    assert len(roar) == 1
    assert roar[0]["action"] == "select_attack_source"
    assert roar[0]["mana_cost"] == ["C", "N", "*"]
    session.confirm_combat_turn_action(roar[0]["id"])
    assert session.combat_targeting_attack_source_id == "deafening_roar"
    assert session.combat_turn_preview_option_id == roar[0]["id"]


def test_movement_tile_removes_price_after_first_movement(tmp_path: Path) -> None:
    session = arena(tmp_path)
    begin(session, "brakka")
    options = session._combat_turn_action_menu_payload()["options"]
    assert next(o for o in options if o["id"] == "turn:move")["mana_cost"] == ["*"]
    session.active_combat_effects = declare_ordinary_movement(session.combat_state, ())
    moved = session._combat_turn_action_menu_payload()["options"]
    assert next(o for o in moved if o["id"] == "turn:move")["mana_cost"] == []


def test_metamagic_tile_includes_surcharge(tmp_path: Path) -> None:
    session = arena(tmp_path)
    begin(session, "nimra")
    option = CombatMenuOption(
        "test-meta",
        "Czar",
        "",
        CombatMenuCategory.MAGIC,
        CombatMenuAction.SELECT_ATTACK_SOURCE,
        source_id="nimra_frost_pulse",
        provider="nimra_metamagic:nimra_distant_spell",
    )
    payload = menu_mana_payload(option, session.combat_state, ())
    assert payload["mana_cost"] == list(
        mana_ability("nimra", "nimra_frost_pulse").cost
        + mana_ability("nimra", "nimra_distant_spell").cost
    )
