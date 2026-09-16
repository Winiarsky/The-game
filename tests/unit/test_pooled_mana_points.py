from dataclasses import replace

import pytest

from tests.unit.test_hero_rules_consistency import heroes
from tests.unit.test_physical_mana import session_for
from tests.unit.test_pooled_mana_runtime import prepare
from dnd_board_game.combat import current_actor
from dnd_board_game.combat.pooled_mana import point_modifiers, quote_pool
from dnd_board_game.rules import ActiveEffect
from dnd_board_game.rules.shared_mana import sync_pool
from dnd_board_game.rules.shared_mana_catalog import shared_ability
from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile, pool_ability
from dnd_board_game.world import Coordinate


@pytest.mark.parametrize('hero,ability', [('garran', 'second_wind'), ('brakka', 'powerful_strike'),
    ('dagna', 'healing_word'), ('lorian', 'mana_recovery'), ('nimra', 'nimra_mind_spike'),
    ('erynd', 'double_shot'), ('mira', 'hamstring_cut')])
def test_context_no_longer_adds_hidden_charge_points(heroes, tmp_path, hero, ability):
    s = session_for(heroes[hero], tmp_path, pooled=True)
    prepare(s)
    actor = current_actor(s.combat_state)
    ally = replace(actor, id='ally', position=Coordinate(actor.position.col, actor.position.row + 1))
    state = replace(s.combat_state, actors=(actor, ally))
    effects = (ActiveEffect('rage', hero, 'rage', 'Szał', 'rage', 1),) if hero == 'brakka' else ()
    if hero == 'mira':
        from dnd_board_game.combat import HiddenState
        state = replace(state, hidden_states=(HiddenState(hero, 20, ('enemy',)),))
    pool = state.shared_mana.pooled
    if hero == 'nimra':
        pool = replace(pool, deck=pool.deck[2:], pools=((hero, ('C', 'Z', 'N')),))
        state = replace(state, shared_mana=sync_pool(state.shared_mana, pool))
    bonus, surcharge, notes = point_modifiers(state, actor, shared_ability(hero, ability), (ally,), effects)
    assert bonus == 0
    assert surcharge == 0
    assert not notes
    assert state.shared_mana.pooled == pool


def test_dagna_and_lorian_flaws_add_burn_instead_of_threshold(heroes, tmp_path):
    for hero, ability in [('dagna', 'sacred_flame'), ('lorian', 'mocking_shot')]:
        s = session_for(heroes[hero], tmp_path / hero, pooled=True)
        prepare(s)
        actor = current_actor(s.combat_state)
        ally = replace(actor, id='ally', hp=9, max_hp=20,
                       position=Coordinate(actor.position.col + (1 if hero == 'dagna' else 4), actor.position.row))
        pool = replace(s.combat_state.shared_mana.pooled, heroes=(hero, 'ally'))
        state = replace(s.combat_state, actors=(actor, ally), shared_mana=sync_pool(s.combat_state.shared_mana, pool))
        assert point_modifiers(state, actor, shared_ability(hero, ability), (), ())[1] == 1


def test_nimra_echo_increases_burn_and_other_spell_resets_streak(heroes, tmp_path):
    from dnd_board_game.rules.shared_mana import pay_mana, finish_mana_action
    s = session_for(heroes['nimra'], tmp_path, pooled=True)
    prepare(s, 'N', 'C')
    mana = replace(s.combat_state.shared_mana, echo_spell='nimra_mind_spike', echo_count=5)
    state = replace(s.combat_state, shared_mana=mana)
    actor = current_actor(state)
    assert point_modifiers(state, actor, shared_ability('nimra', 'nimra_mind_spike'), (), ())[1] == 2
    paid = pay_mana(mana, revision=mana.revision, actor_id='nimra', ability_id='nimra_frost_pulse', count=1, echo_spell=True)
    assert (paid.echo_spell, paid.echo_count) == ('nimra_frost_pulse', 1)
