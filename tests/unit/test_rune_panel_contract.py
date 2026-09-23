"""The live controls, replaceable cards and printed strip use one physical map."""
from types import SimpleNamespace

import pytest

from dnd_board_game.hardware.board_panel import (
    PANEL_GAPS, PANEL_INFO, PANEL_KEY, PANEL_MINUS, PANEL_PLUS,
    panel_delta, panel_feedback, panel_position,
)
from dnd_board_game.hardware.led_feedback import LedFeedback, LedFrame, LedRole
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.scenarios.rune_catalog import rune_cards
from dnd_board_game.rules.runes import RESOURCE_RUNES, validate_card_payment
from dnd_board_game.ui.board_panel import option_panel_payload
from dnd_board_game.ui.board_panel_symbols import SYMBOLS, ability_panel_slot, rune_slot
from dnd_board_game.world import Coordinate


def test_printed_controls_and_gaps_have_unambiguous_positions() -> None:
    assert [name for name, _ in SYMBOLS[:4]] == ['Ruch', 'Atak', 'Przedmiot', 'Koniec tury']
    assert tuple(i for i, (_, path) in enumerate(SYMBOLS) if not path) == PANEL_GAPS
    assert [name for name, _ in SYMBOLS[26:]] == ['Zwiększ', 'Zmniejsz', 'Zatwierdź', 'Wróć']
    assert rune_slot('Klucz') == PANEL_KEY == 23
    assert rune_slot('Gwiazda') == PANEL_INFO == 24
    assert len({panel_position(slot) for slot in range(30)}) == 30


def test_plus_minus_and_information_lights_preserve_map_targets() -> None:
    target = Coordinate(8, 11)
    base = LedFeedback((LedFrame((target, panel_position(25)), LedColor.LEGAL_ATTACK_TARGET, LedRole.ENEMY),))
    feedback = panel_feedback((18, PANEL_INFO), control_slots=(PANEL_PLUS, PANEL_MINUS), base=base)
    lights = {p: frame.color for frame in feedback.frames for p in frame.positions}
    assert lights[target] == LedColor.LEGAL_ATTACK_TARGET
    assert panel_position(25) not in lights
    assert lights[panel_position(18)] == tuple(round(c * .65) for c in LedColor.PANEL_RUNE)
    assert lights[panel_position(PANEL_INFO)] == tuple(round(c * .65) for c in LedColor.PANEL_INFO)
    assert lights[panel_position(PANEL_PLUS)] == LedColor.PANEL_PLUS
    assert lights[panel_position(PANEL_MINUS)] == LedColor.PANEL_MINUS
    assert panel_delta(PANEL_PLUS) == 1 and panel_delta(PANEL_MINUS) == -1
    with pytest.raises(ValueError):
        panel_delta(28)


@pytest.mark.parametrize('hero', ['garran', 'brakka', 'mira', 'dagna', 'lorian', 'nimra', 'erynd'])
def test_hero_actions_use_replaceable_card_bindings_and_reserve_information(hero: str) -> None:
    cards = rune_cards(hero)
    assert cards
    assert len({card.slot for card in cards}) == len(cards)
    for card in cards:
        assert 5 <= card.slot < PANEL_INFO
        assert ability_panel_slot(hero, card.id) == card.slot
        assert card.rune == SYMBOLS[card.slot][0]
        assert validate_card_payment((card.rune,), card.payment({}), None) == (card.rune,)
        option = SimpleNamespace(id='class-feature:' + card.id, action_id=card.id, source_id=None)
        assert option_panel_payload(hero, option)['panel_slot'] == card.slot


def test_resource_deck_and_allocation_slots_cover_exactly_the_card_symbols() -> None:
    from dnd_board_game.ui.runes import RUNE_SLOTS
    from dnd_board_game.scenarios.rune_catalog import rune_card
    cards = tuple(c for hero in ('garran', 'brakka', 'mira', 'dagna', 'lorian', 'nimra', 'erynd')
                  for c in rune_cards(hero))
    assert set(RESOURCE_RUNES) == {c.rune for c in cards}
    assert RUNE_SLOTS == {c.rune: c.slot for c in cards}
    activation = rune_card('dagna', 'spiritual_weapon_activation')
    assert activation.rune == SYMBOLS[activation.slot][0] == 'Schody'
    assert activation.payment({}) == ('Schody',)


def test_basics_remove_weapon_switch_and_use_item_and_end_turn_slots() -> None:
    for option_id, slot in [('turn:move', 0), ('menu:items', 2), ('turn:end', 3), ('menu:weapons', None)]:
        option = SimpleNamespace(id=option_id, action_id=None, source_id=None)
        assert option_panel_payload('garran', option)['panel_slot'] == slot
    attack = SimpleNamespace(id='attack-source:longsword', action_id=None, source_id='longsword')
    assert option_panel_payload('garran', attack, basic_attack=True)['panel_slot'] == 1
