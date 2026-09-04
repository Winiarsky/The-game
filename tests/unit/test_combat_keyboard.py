from dataclasses import dataclass

from dnd_board_game.ui.combat_keyboard import (
    HERO_SHORTCUTS,
    shortcut_for_option,
)


@dataclass(frozen=True)
class Option:
    id: str
    source_id: str | None = None
    action_id: str | None = None
    action: str = "class_feature"
    category: str = "support"


def test_every_curated_hero_has_unique_character_shortcuts() -> None:
    assert set(HERO_SHORTCUTS) == {
        "garran",
        "brakka",
        "mira",
        "dagna",
        "lorian",
        "nimra",
        "erynd",
    }
    for bindings in HERO_SHORTCUTS.values():
        keys = [binding.key for binding in bindings]
        assert len(keys) == len(set(keys))


def test_shortcut_matches_stable_action_or_source_id() -> None:
    assert shortcut_for_option(
        "garran",
        Option("class-feature:garran_rally", action_id="garran_rally"),
    ) == "D"
    assert shortcut_for_option(
        "nimra",
        Option("attack-source:shatter", source_id="shatter"),
    ) == "K"


def test_nimra_uses_only_single_letter_shortcuts() -> None:
    keys = [binding.key for binding in HERO_SHORTCUTS["nimra"]]

    assert all(len(key) == 1 and key.isalpha() for key in keys)
    assert keys[:5] == ["T", "Y", "U", "G", "H"]


def test_common_shortcuts_and_selected_attack_are_resolved_without_list_positions() -> None:
    assert shortcut_for_option("mira", Option("turn:move")) == "M"
    assert shortcut_for_option("mira", Option("menu:weapons")) == "B"
    assert shortcut_for_option("mira", Option("menu:items")) == "I"
    assert shortcut_for_option("mira", Option("turn:end")) == "0"
    assert shortcut_for_option(
        "mira",
        Option(
            "attack-source:rapier_attack",
            source_id="rapier_attack",
            action="select_attack_source",
            category="attack",
        ),
        selected_attack_source_id="rapier_attack",
    ) == "SPACE"
