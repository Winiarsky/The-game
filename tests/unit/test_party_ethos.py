"""Party stance changes the physical deck without letting drain undo choices."""
from collections import Counter
from dataclasses import replace

import pytest

from dnd_board_game.rules.party_ethos import PartyEthos, shift
from dnd_board_game.rules.pooled_mana import (
    COLORS, PooledMana, new_mana, confirm_shuffle, reveal, take, drain,
    attack_mana, report_removed, recover,
)
from dnd_board_game.application import party_ethos
from dnd_board_game.ui import mission_zero as mission, confrontation
from dnd_board_game.hardware.board_panel import panel_position
from tests.unit.test_mission_zero import session, stage, send, start_battle


@pytest.mark.parametrize('players', [3, 4, 5, 6])
@pytest.mark.parametrize('position', range(7))
def test_all_sizes_and_positions_conserve_active_and_excluded_cards(players, position):
    ethos = PartyEthos(position)
    pool = new_mana(tuple(f'h{i}' for i in range(players)), excluded=ethos.excluded)
    assert pool.total == players * 10 - 2 * abs(position - 3)
    assert pool.composition['Z'] == 2 * players
    assert sum(pool.composition.values()) == len(pool.deck)
    assert all(n >= 3 for n in pool.composition.values())
    known_deck = tuple(c for c, n in pool.composition.items() for _ in range(n))
    pool = confirm_shuffle(pool, known_deck)
    assert Counter((*pool.deck, *pool.excluded)) == Counter({c: 2 * players for c in COLORS})
    assert PooledMana.from_payload(pool.as_payload()) == pool


def test_choices_are_once_only_bounded_and_reverse_on_the_same_track():
    state = PartyEthos()
    for i in range(5):
        state = shift(state, f'force:{i}', 'ruthlessness')
    assert state.position == 6
    assert shift(state, 'force:0', 'solidarity') == state
    state = shift(state, 'peace:1', 'solidarity')
    assert state.position == 5  # Overflow never builds an invisible extra debt.
    for i in range(6):
        state = shift(state, f'peace:{i+2}', 'solidarity')
    assert state.position == 0
    assert state.excluded == ('C', 'C', 'C', 'F', 'F', 'F')
    with pytest.raises(ValueError): PartyEthos(True)
    with pytest.raises(ValueError): shift(state, 'bad', 'unknown')


def test_drain_returns_every_active_zone_but_never_excluded_cards():
    pool = new_mana(('garran',), 'garran', excluded=PartyEthos(4).excluded)
    # One personal card, one prison card, one burned card, one expired card.
    pool = confirm_shuffle(pool, ('C', 'B', 'N', 'Z', *('C',)*4, *('B',)*3, *('N',)*3, *('Z',)*4, *('F',)*5))
    pool = take(reveal(reveal(pool, 'C'), 'B'), 0)
    pool = attack_mana(pool, 'offer', captor='bandit')
    pool = report_removed(attack_mana(pool, 'deck'), 'N')
    pool = replace(pool, deck=pool.deck[1:], expired=('Z',))
    pool = confirm_shuffle(drain(pool, 'Presja'))
    assert len(pool.deck) == 23 and pool.excluded == ('B', 'N')
    assert not pool.pools and not pool.prisons and not pool.burned and not pool.expired
    ready = replace(pool, phase='ready')
    with pytest.raises(ValueError): recover(ready, ('B',))
    invalid = ('B',) * 5 + (None,) * 18
    with pytest.raises(ValueError): confirm_shuffle(drain(ready, 'Presja'), invalid)


def test_unknown_deck_rejects_an_excluded_copy_and_old_save_stays_neutral():
    pool = confirm_shuffle(new_mana(('garran',), 'garran', excluded=PartyEthos(6).excluded))
    pool = replace(pool, phase='burn', pending_count=3)
    pool = report_removed(report_removed(pool, 'B'), 'B')
    with pytest.raises(ValueError): report_removed(pool, 'B')
    old = new_mana(('garran',)).as_payload()
    old.pop('excluded')
    restored = PooledMana.from_payload(old)
    assert restored.total == 25 and not restored.excluded


def test_cart_choice_uses_rune_skips_test_and_survives_save(tmp_path):
    s = session(tmp_path)
    stage(s, 'road')
    assert party_ethos.read(s.state.flags) == PartyEthos()
    assert panel_position(7) in mission.scan_target(s).positions
    before = mission.read(s)['revision']
    result = mission.select_position(s, panel_position(7))
    assert result['party_ethos']['label'] == 'Bezwzględność'
    assert result['party_ethos']['total'] == 28
    assert mission.read(s)['stage'] == 'cart_coerced'
    assert mission.read(s)['fatigue'] == 0
    assert not confrontation.active(s)
    with pytest.raises(ValueError): mission.command(s, dict(action='cart_coerce', revision=before))
    s.save_snapshot(); s.load_snapshot()
    assert party_ethos.read(s.state.flags).position == 4
    send(s, 'next')
    assert mission.read(s)['stage'] == 'arrival'
    # Both battle and subsequent object scenes take the same adjusted composition.
    start_battle(s)
    assert s.combat_state.shared_mana.pooled.total == 28
    assert s.combat_state.shared_mana.pooled.excluded == ('B', 'N')


def test_starting_cart_confrontation_locks_coercion_even_after_leaving(tmp_path):
    s = session(tmp_path); stage(s, 'road'); send(s, 'cart')
    confrontation.command(s, dict(action='leave', revision=confrontation.read_store(s)['revision']))
    assert 'cart_coerce' not in {c['action'] for c in mission.payload(s)['choices']}
    with pytest.raises(ValueError): send(s, 'cart_coerce')
    assert party_ethos.read(s.state.flags).position == 3


@pytest.mark.parametrize('coerced', [False, True])
def test_actual_truce_updates_next_confrontation_and_checkpoint(coerced, tmp_path):
    from tests.unit.test_pooled_mana_runtime import prepare
    s = session(tmp_path)
    stage(s, 'road'); mission.checkpoint(s, mission.read(s))
    if coerced: send(s, 'cart_coerce')
    start_battle(s); prepare(s, 'C', 'B')
    enemies = [a for a in s.combat_state.actors if a.faction.value == 'enemy']
    s.combat_state = replace(s.combat_state, actors=tuple(replace(a, hp=0) if a.id == enemies[0].id else a for a in s.combat_state.actors))
    s.state_payload()
    assert mission.read(s)['stage'] == 'surrender'
    send(s, 'accept')
    assert s.combat_state is None
    assert party_ethos.read(s.state.flags).position == (3 if coerced else 2)
    with pytest.raises(ValueError): send(s, 'accept')
    mission.launch_confrontation(s, 'armory')
    view = confrontation.payload(s)
    assert view['mana']['total'] == (30 if coerced else 28)
    assert view['mana']['composition']['C'] == (6 if coerced else 5)
    assert 'czerwone:' in view['mana']['preparation']
    s.save_snapshot(); s.load_snapshot()
    assert party_ethos.read(s.state.flags).position == (3 if coerced else 2)
    confrontation.command(s, dict(action='leave', revision=confrontation.read_store(s)['revision']))
    send(s, 'checkpoint', id='road')
    assert party_ethos.read(s.state.flags) == PartyEthos()


def test_refusing_truce_changes_only_future_decks_and_does_not_repeat(tmp_path):
    from tests.unit.test_pooled_mana_runtime import prepare
    s = start_battle(session(tmp_path)); prepare(s, 'C', 'B')
    enemies = [a for a in s.combat_state.actors if a.faction.value == 'enemy']
    s.combat_state = replace(s.combat_state, actors=tuple(replace(a, hp=0) if a.id == enemies[0].id else a for a in s.combat_state.actors))
    s.state_payload()
    assert mission.read(s)['stage'] == 'surrender'
    pool = s.combat_state.shared_mana.pooled
    send(s, 'refuse')
    assert party_ethos.read(s.state.flags).position == 4
    assert mission.read(s)['outcome'] == 'refused'
    assert s.combat_state.shared_mana.pooled == pool
    assert confirm_shuffle(drain(pool, 'Presja')).total == 30
    s.state_payload()
    assert mission.read(s)['stage'] == 'battle'
    with pytest.raises(ValueError): send(s, 'refuse')
    assert s.state_payload()['party_ethos']['total'] == 28
