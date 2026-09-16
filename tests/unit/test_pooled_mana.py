from collections import Counter
from dataclasses import replace
from random import Random

import pytest

from dnd_board_game.rules.pooled_mana import (
    COLORS, PooledMana, attack_mana, confirm_shuffle, drain, new_mana, pay_pool,
    recover, release, report_removed, reveal, start_turn, take, tune, finish_burn,
)
from dnd_board_game.rules.shared_mana import SharedMana, sync_pool
from dnd_board_game.evaluation.pooled_mana import run_trial
from dnd_board_game.scenarios.pooled_mana_catalog import load_catalog, pool_ability


def ready():
    s = confirm_shuffle(new_mana(("brakka", "dagna"), "brakka", copies=5), COLORS * 5)
    return take(reveal(reveal(s, "C"), "B"), 0)


def test_offer_and_charge_persist_after_payment_and_burn():
    s = ready()
    assert s.hand("brakka") == ("C",) and s.offer == ("B",)
    s = pay_pool(s, "brakka")
    assert s.offer == ("B",) and s.hand("brakka") == ("C",)
    s = report_removed(finish_burn(s), "Z")
    s = start_turn(s, "dagna")
    s = take(reveal(s, "F"), 0)
    assert s.hand("dagna") == ("B",) and s.offer == ("F",)
    with pytest.raises(ValueError):
        take(s, 0)


def test_full_drain_returns_burned_prison_and_personal_pools():
    s = attack_mana(ready(), "offer", captor="enemy")
    s = report_removed(attack_mana(s, "deck"), "Z")
    assert s.burned == ("Z",) and dict(s.prisons)["enemy"] == ("B",)
    s = attack_mana(s, "offer")
    assert s.phase == "drain"
    restored = confirm_shuffle(s)
    assert len(restored.deck) == 25 and not restored.pools and not restored.burned and not restored.prisons
    assert not restored.draw_due


def test_partial_spending_cannot_bypass_threshold_and_colors():
    ult = pool_ability("reaper")
    with pytest.raises(ValueError):
        ult.validate(("C", "N", "N"), load_catalog()["heroes"]["brakka"]["values"])
    ult.validate(("C", "C", "C"), load_catalog()["heroes"]["brakka"]["values"])


def test_exact_deck_burn_does_not_drain_until_next_unavailable_operation():
    s = ready()
    s = attack_mana(s, "deck", len(s.deck))
    while s.phase == "burn":
        s = report_removed(s, s.deck[0])
    assert s.phase == "ready" and not s.deck
    s = take(start_turn(s, "dagna"), 0)
    assert s.phase == "ready"
    assert start_turn(s, "brakka").phase == "drain"


def test_recover_and_release_preserve_order_and_supply():
    s = attack_mana(ready(), "offer", captor="enemy")
    s = report_removed(attack_mana(s, "deck"), "Z")
    s = recover(s, ("Z",), top=True)
    assert s.deck[0] == "Z"
    s = release(s, "enemy")
    assert s.deck[-1] == "B"
    s = tune(s, (s.deck[1], s.deck[0]))
    assert s.deck[1] == "Z"


def test_unknown_physical_deck_rejects_sixth_known_copy():
    s = new_mana(("brakka",), copies=1)
    s = reveal(confirm_shuffle(s), "C")
    with pytest.raises(ValueError):
        reveal(s, "C")


def test_save_roundtrip_preserves_pending_burn_and_pool_envelope():
    s = attack_mana(ready(), "deck", 2, captor="enemy")
    bridge = sync_pool(SharedMana(), s)
    assert SharedMana.from_payload(bridge.as_payload()) == bridge


@pytest.mark.parametrize("policy", ["basic_only", "spend_early", "save_ultimate", "adaptive", "cooperative"])
@pytest.mark.parametrize("pressure", ["none", "deck", "offer", "prison"])
def test_seeded_economy_is_reproducible_and_bounded(policy, pressure):
    args = (load_catalog(), ("brakka", "dagna", "lorian"), policy, 4, 12, pressure, 52)
    first = run_trial(*args)
    assert first == run_trial(*args)
    assert first["metrics"]["hero_turns"] == 36


def test_identical_public_cards_remain_two_physical_choices():
    s = confirm_shuffle(new_mana(('brakka',), 'brakka'))
    s = reveal(reveal(s, 'C'), 'C')
    assert s.offer == ('C', 'C')
    s = take(s, 1)
    assert s.offer == ('C',) and s.hand('brakka') == ('C',)


def test_drain_keeps_turn_usage_and_resumes_only_the_due_draw():
    s = replace(ready(), used=('brakka:once',), turns=3, draw_due=True)
    s = confirm_shuffle(drain(s, 'Brak many'))
    assert s.used == ('brakka:once',) and s.turns == 3 and s.draw_due
    s = take(reveal(reveal(s, 'C'), 'B'), 0)
    with pytest.raises(ValueError):
        take(s, 0)


@pytest.mark.parametrize('players,cards', [(1, 25), (4, 40), (5, 50), (7, 70)])
def test_fresh_encounters_scale_complete_deck_without_inherited_zones(players, cards):
    s = new_mana(tuple(str(i) for i in range(players)), '0')
    assert len(s.deck) == cards
    assert not s.pools and not s.burned and not s.prisons and not s.offer
