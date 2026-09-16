"""Hide the retired skill layer while retaining actions and saved character data."""
from dnd_board_game.character_creation.physical_mana_help import visible_character_features
from dnd_board_game.physical_cards.mana_print import build_print_hero
from dnd_board_game.physical_cards.mana_print_html import render_hero_html
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.ui.exploration_app import create_app, _combat_actor_payload
from tests.unit.test_launcher_ui import _session


def test_retired_expertise_hidden_without_removing_data_or_active_passives() -> None:
    for hero, retired in [('mira','expertise'),('erynd','erynd_expertise')]:
        actor=training_hero(hero)
        before=actor.proficiencies
        if hero=='mira':
            assert retired in {f.feature_id for f in actor.features}
        assert retired not in {f.feature_id for f in visible_character_features(actor)}
        assert retired not in {f['id'] for f in _combat_actor_payload(actor)['features']}
        assert actor.proficiencies==before and before.skills and before.expertise
        hero_print=build_print_hero(hero)
        assert hero_print.skills  # Available for future rules; not printed.
        html=render_hero_html(hero_print,'minimal')
        assert 'Umiejętności — baza' not in html and 'Ekspertyza' not in html
        assert 'Nasycenie maną' in html
        if hero=='mira':
            assert 'Mistrzyni ukrycia' in html and 'test Zręczności' in html


def test_roster_hides_skill_list_and_uses_current_test_formula(tmp_path) -> None:
    client=create_app(_session(tmp_path)).test_client()
    for hero in ('garran','brakka','mira','dagna','lorian','nimra','erynd'):
        response=client.get('/characters/'+hero)
        assert response.status_code==200
        html=response.get_data(as_text=True)
        assert '<h2>Biegłości</h2>' not in html
        assert 'Ekspertyza' not in html and 'Premia z biegłości' not in html
        assert 'k20 + cecha + naładowanie + inne premie' in html
        assert 'Naładowanie bez puli' in html
        if hero=='mira':
            assert 'test Zręczności' in html and 'Test Skradania' not in html
