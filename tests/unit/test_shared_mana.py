from collections import Counter
from dataclasses import replace

import pytest

from dnd_board_game.rules.shared_mana import (
    ManaPhase, SharedMana, begin_mana_turn, pay_mana, finish_mana_action,
    request_mana_end_turn, confirm_mana_refill, confirm_mana_discard,
    request_mana_refresh, confirm_mana_refresh, validate_card_operation,
)
from dnd_board_game.rules.shared_mana_catalog import CATALOG, shared_ability


def test_catalog_has_exact_character_budgets_and_payments():
    assert len(CATALOG) == 66
    for hero in {a.hero_id for a in CATALOG}:
        assert Counter(a.category for a in CATALOG if a.hero_id == hero) == (
            {"basic": 5, "boost": 4, "ultimate": 3} if hero == "nimra" else
            {"basic": 4, "boost": 3, "ultimate": 2})
    for ability in CATALOG:
        assert 1 <= len(ability.payment({})) <= 5


def test_tuning_last_two_cards_is_atomic_and_does_not_refresh():
    state = begin_mana_turn(SharedMana(deck=2, market=5, discard=18), "lorian")
    validate_card_operation(state, "mana_tuning", 1)
    paid = pay_mana(state, revision=state.revision, actor_id="lorian", ability_id="mana_tuning", count=1)
    done = finish_mana_action(paid, revision=paid.revision)
    assert (done.deck, done.market, done.discard) == (1, 4, 20)
    assert not done.exhausted
    assert done.phase == ManaPhase.READY


def test_tuning_preflight_accounts_for_flaw_and_additional_discard():
    with pytest.raises(ValueError):
        validate_card_operation(SharedMana(deck=21, market=2, discard=2), "mana_tuning", 2)
    with pytest.raises(ValueError):
        validate_card_operation(SharedMana(deck=1, market=5, discard=19), "mana_tuning", 1)


def test_recovery_can_put_its_own_paid_cost_back_on_deck():
    state = begin_mana_turn(SharedMana(), "lorian")
    paid = pay_mana(state, revision=state.revision, actor_id="lorian", ability_id="mana_recovery", count=3, boosts=(("recover", 1),))
    done = finish_mana_action(paid, revision=paid.revision)
    assert (done.deck, done.market, done.discard) == (23, 2, 0)
    assert done.spent_this_turn == 3


def test_great_tuning_resolves_before_empty_market_refresh():
    state = begin_mana_turn(SharedMana(deck=0, market=4, discard=21, exhausted=True), "lorian")
    paid = pay_mana(state, revision=state.revision, actor_id="lorian", ability_id="mana_great_tuning", count=4)
    assert paid.phase == ManaPhase.RESOLVING
    with pytest.raises(ValueError):
        request_mana_refresh(paid, revision=paid.revision)
    done = finish_mana_action(paid, revision=paid.revision)
    assert (done.deck, done.market, done.discard) == (0, 3, 22)
    assert done.phase == ManaPhase.READY


def test_no_spend_turn_discards_last_card_and_refreshes_once():
    state = begin_mana_turn(SharedMana(deck=0, market=1, discard=24, exhausted=True), "garran")
    end = request_mana_end_turn(state, revision=state.revision)
    discard = confirm_mana_refill(end, revision=end.revision)
    assert discard.phase == ManaPhase.DISCARD
    refresh = confirm_mana_discard(discard, revision=discard.revision)
    assert refresh.phase == ManaPhase.REFRESH
    fresh = confirm_mana_refresh(refresh, revision=refresh.revision)
    assert (fresh.deck, fresh.market, fresh.discard, fresh.cycle) == (20, 5, 0, 2)
    assert fresh.end_turn_pending
    with pytest.raises(ValueError):
        confirm_mana_refresh(fresh, revision=refresh.revision)


def test_reaction_by_another_hero_does_not_pay_active_heros_turn():
    state = begin_mana_turn(SharedMana(deck=0, market=5, discard=20), "garran")
    paid = pay_mana(state, revision=state.revision, actor_id="nimra", ability_id="shield", count=1)
    done = finish_mana_action(paid, revision=paid.revision)
    assert done.spent_this_turn == 0
    end = request_mana_end_turn(done, revision=done.revision)
    assert confirm_mana_refill(end, revision=end.revision).phase == ManaPhase.DISCARD


def test_payment_cannot_be_replayed_or_refreshed_mid_resolution():
    state = begin_mana_turn(SharedMana(), "nimra")
    paid = pay_mana(state, revision=state.revision, actor_id="nimra", ability_id="nimra_frost_pulse", count=1, echo_spell=True)
    with pytest.raises(ValueError):
        pay_mana(paid, revision=state.revision, actor_id="nimra", ability_id="nimra_frost_pulse", count=1)
    assert SharedMana.from_payload(paid.as_payload()) == paid


def test_echo_and_boosts_share_five_card_limit():
    ability = shared_ability("nimra", "nimra_flame_fan")
    assert len(ability.payment({"damage": 2}, surcharge=1)) == 5
    for boosts, surcharge in [({"damage": 2}, 2), ({"damage": 3}, 0), ({"damage": True}, 0), ({"other": 1}, 0)]:
        with pytest.raises(ValueError):
            ability.payment(boosts, surcharge)
    state = begin_mana_turn(SharedMana(), "nimra")
    for i in range(3):
        # A refresh changes cards, but does not silently erase the spell streak.
        paid = pay_mana(state, revision=state.revision, actor_id="nimra", ability_id="nimra_frost_pulse", count=i+1, echo_spell=True)
        assert paid.echo_count == i+1
        done = finish_mana_action(paid, revision=paid.revision)
        refresh = request_mana_refresh(done, revision=done.revision)
        state = confirm_mana_refresh(refresh, revision=refresh.revision)


@pytest.mark.parametrize("fields", [{"deck": 19}, {"market": 6, "deck": 19}, {"market": True}, {"discard": -1}])
def test_invalid_counts_are_rejected(fields):
    with pytest.raises(ValueError):
        SharedMana(**fields)
