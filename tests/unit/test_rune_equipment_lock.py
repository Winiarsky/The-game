"""New rune combats lock equipment even when launched from an isolated checkpoint."""
from types import SimpleNamespace

import pytest

from dnd_board_game.character_creation.runes import apply_rune_profile
from dnd_board_game.ui.party_preparation import locked, require_unlocked
from dnd_board_game.ui.training_arena import training_hero


def test_rune_combat_locks_weapon_changes_without_mission_exit_flag():
    actor=apply_rune_profile(training_hero('garran'))
    s=SimpleNamespace(combat_state=SimpleNamespace(actors=(actor,)), exploration=SimpleNamespace(scenario_id='isolated'))
    assert locked(s)
    with pytest.raises(ValueError,match='Wyposażenie ustalono'):require_unlocked(s)


def test_legacy_combat_and_pre_mission_preparation_remain_available():
    s=SimpleNamespace(combat_state=SimpleNamespace(actors=(training_hero('garran'),)), exploration=SimpleNamespace(scenario_id='isolated'))
    assert not locked(s)
    s.combat_state=None
    require_unlocked(s)
