"""One editable source feeds runtime, tutorial, and print without changing rules."""
from __future__ import annotations

from copy import deepcopy
import importlib
import json
from pathlib import Path

import pytest

from dnd_board_game.scenarios import character_text as text
from dnd_board_game.scenarios.confrontation import catalog, passives, lesson_by_id
from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile, pool_ability
from dnd_board_game.physical_cards.mana_print import build_print_hero
from dnd_board_game.physical_cards.mana_ability_text import ability_sections

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def editable_source(tmp_path, monkeypatch):
    data = deepcopy(text.load_text())
    path = tmp_path / 'karty_postaci.json'
    path.write_text(json.dumps(data, ensure_ascii=False))
    monkeypatch.setattr(text, 'SOURCE_PATH', path)
    return path, data


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def test_complete_source_covers_every_current_action_passive_and_lesson():
    from dnd_board_game.application.training_walkthrough import steps
    from dnd_board_game.scenarios.pooled_mana_catalog import load_catalog
    source = text.load_text()
    for hid, hero in source['heroes'].items():
        assert set(hero['tutorial']) == {s.ability.id for s in steps(hid)}
        assert {a.id for a in build_print_hero(hid).cards} <= set(hero['actions'])
        for mode in ('combat', 'exploration'):
            assert set(hero['passives'][mode]) == set('CBZFN')
    for aid, ability in load_catalog()['abilities'].items():
        assert aid in source['heroes'][ability['hero']]['actions']
    assert set(source['tutorial']['exploration_lessons']) == {l['id'] for l in catalog()['lessons']}
    raw = json.loads((ROOT/'content/balance/pooled_mana/catalog.json').read_text())
    assert all('display' not in p and 'label' not in p for h in raw['heroes'].values() for p in h['color_passives'].values())
    assert all('description' not in a for a in raw['abilities'].values())


def test_saved_edit_reaches_runtime_and_print_without_restart(editable_source, monkeypatch):
    from dnd_board_game.ui.shared_mana import declared_ability
    path, data = editable_source
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    mats = importlib.import_module('build_hero_mats')
    before = build_print_hero('garran')  # warm all caches before editing
    mechanical_cost = pool_ability('second_wind')
    passives('garran')
    hero = data['heroes']['garran']
    hero['history'] = 'Nowa historia do karty.'
    hero['flaw']['description'] = 'Nowy opis skazy.'
    hero['actions']['second_wind']['name'] = 'Nowa nazwa oddechu'
    hero['actions']['second_wind']['description'] = 'Nowy opis leczenia.'
    for mode in ('combat', 'exploration'):
        hero['passives'][mode]['B'].update(name='Zmieniony pasyw '+mode, effect='Pełny nowy opis.', short='Krótki nowy opis.')
    save(path, data)
    after = build_print_hero('garran')
    assert after.hp == before.hp and after.abilities == before.abilities
    assert pool_ability('second_wind') == mechanical_cost
    assert dict(after.story)['Historia'] == hero['history']
    assert after.flaw[1] == hero['flaw']['description']
    from dnd_board_game.ui.routes import _character_sheet_feature_entries
    from dnd_board_game.ui.exploration_app import _feature_grant_payload
    from dnd_board_game.ui.training_arena import training_hero
    from dnd_board_game.ui.hero_selection import physical_mana_guides
    actor = training_hero('garran')
    flaw = next(f for f in actor.features if f.feature_id == 'flaw_remorse')
    assert _character_sheet_feature_entries((flaw,), actor_id='garran')[0]['rule_text'] == 'Nowy opis skazy.'
    assert _feature_grant_payload(flaw, 'garran')['mechanics'] == 'Nowy opis skazy.'
    assert physical_mana_guides()['garran'].flaw == 'Nowy opis skazy.'

    assert dict(ability_sections('garran', 'second_wind'))['Efekt'] == 'Nowy opis leczenia.'
    assert declared_ability('garran', 'second_wind').name == 'Nowa nazwa oddechu'
    assert hero_profile('garran')['color_passives']['B']['display']['effect'] == 'Pełny nowy opis.'
    assert passives('garran')['B']['display']['effect'] == 'Pełny nowy opis.'
    assert 'Nowy opis leczenia.' in mats.actions_page(after, text.print_copy()['heroes']['garran'])
    html = mats.mana_page(after, {})
    assert 'Zmieniony pasyw combat' in html and 'Zmieniony pasyw exploration' in html
    assert html.count('Krótki nowy opis.') == 2
    assert 'Pełny nowy opis.' not in html


def test_saved_tutorial_edit_is_visible_in_actual_payload(editable_source, tmp_path):
    from tests.unit.test_training_walkthrough import prepared
    from dnd_board_game.ui import training_walkthrough as ui
    path, data = editable_source
    session = prepared(tmp_path)
    ui.payload(session)  # existing session, no relaunch required
    data['heroes']['garran']['tutorial']['pool_draw'] = 'Narracja po poprawce autora.'
    data['tutorial']['foundations']['pool_draw'].update(name='Lekcja autora', instruction='Instrukcja autora.')
    data['tutorial']['intro'] = 'Wprowadzenie autora.'
    save(path, data)
    payload = ui.payload(session)
    assert payload['intro'] == 'Wprowadzenie autora.'
    assert payload['current']['name'] == 'Lekcja autora'
    assert payload['current']['instruction'] == 'Instrukcja autora.'
    assert 'Narracja po poprawce autora.' in payload['current']['narration']


def test_action_lesson_keeps_authored_narration(editable_source, tmp_path):
    from tests.unit.test_training_walkthrough import prepared
    from dnd_board_game.ui import training_walkthrough as ui
    path, data = editable_source
    index = next(i for i,s in enumerate(text.tutorial_steps('garran')) if s.id == 'second_wind')
    session = prepared(tmp_path, index=index)
    data['heroes']['garran']['tutorial']['second_wind'] = 'Własna lekcja leczenia.'
    save(path, data)
    assert 'Własna lekcja leczenia.' in ui.payload(session)['current']['narration']


def test_exploration_lessons_and_shared_aid_follow_source(editable_source, monkeypatch):
    path, data = editable_source
    lid = next(iter(data['tutorial']['exploration_lessons']))
    lesson_by_id('dagna', lid)
    data['tutorial']['exploration_lessons'][lid]['instruction'] = 'Instrukcja obiektu autora.'
    data['player_aid'][0]['lead'] = 'Wspólne zasady autora.'
    save(path, data)
    assert lesson_by_id('dagna', lid).instruction == 'Instrukcja obiektu autora.'
    monkeypatch.syspath_prepend(str(ROOT/'scripts'))
    mats = importlib.import_module('build_hero_mats')
    assert 'Wspólne zasady autora.' in mats.player_aid_page(text.load_text()['player_aid'][0])


def test_incomplete_copy_fails_instead_of_using_obsolete_description(editable_source):
    path, data = editable_source
    del data['heroes']['garran']['passives']['combat']['B']['effect']
    save(path, data)
    with pytest.raises(ValueError, match='garran.combat.B.effect'):
        hero_profile('garran')
