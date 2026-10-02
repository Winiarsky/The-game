"""Self powers cannot accidentally acquire a nearby enemy as their target."""
from copy import deepcopy

import pytest

from dnd_board_game.ui.resonance import presentation
from tests.unit.test_resonance_combat import game as legacy_game
from tests.unit.test_rune_relations_combat import game, restore


@pytest.mark.parametrize("legacy", (False, True))
@pytest.mark.parametrize("hero,action", (
    ("garran", "second_wind"), ("brakka", "rage"),
    ("mira", "hide"), ("garran", "focus"),
))
def test_self_action_only_offers_its_owner(hero: str, action: str, legacy: bool) -> None:
    e = (legacy_game if legacy else game)(hero)
    assert e.choose(action)
    before = deepcopy(e.s.as_payload())
    assert e.legal_targets() == [hero]
    assert e.available_fields() == [e.active.position]
    assert e.target_candidates() == []
    assert not e.select(e.actor("enemy0").position)
    assert e.s.as_payload() == before
    assert e.ready() and e.commit()


@pytest.mark.parametrize("hero,action", (("brakka", "roar"), ("dagna", "preserve_life")))
def test_automatic_area_power_does_not_offer_individual_enemy_selection(hero: str, action: str) -> None:
    e = game(hero)
    assert e.choose(action)
    assert e.available_fields() == []
    assert not e.select(e.actor("enemy0").position)
    assert e.s.preview["targets"] == []
    assert e.ready() and e.commit()


def test_saved_bad_self_preview_can_be_corrected_without_spending_resources() -> None:
    e = game()
    assert e.choose("second_wind")
    e.s.preview["targets"] = ["enemy0"]  # Preview created by the previous runtime.
    e = restore(e)
    before = deepcopy(e.s.as_payload())
    assert not e.ready() and not e.commit()
    assert e.s.as_payload() == before
    view, board = presentation(e)
    assert 28 not in {control["slot"] for control in view["controls"]}
    assert board.legal == (e.active.position,)
    assert e.select(e.active.position)
    assert e.ready() and e.commit()
    assert e.s.task["outcome"] == "heal_group"
    assert e.s.task["targets"] == ["garran"]
