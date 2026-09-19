"""UI and printed mats use the same editorial source for all mana colours."""
import importlib
from pathlib import Path

from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.scenarios.confrontation import passives
from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile


def test_all_passives_have_trigger_effect_and_explicit_stacking():
    for hero in PLAYABLE_HERO_IDS:
        for profile in (passives(hero), hero_profile(hero)['color_passives']):
            assert len(profile)==5
            for item in profile.values():
                text=item['display']
                assert all(text[key].strip() for key in ('name','when','effect','stacking','short'))
                assert item['label'].startswith(text['name']+':')
                if item['kind']=='recover':
                    assert text['diagram']=='recovery'
                    assert 'najwcześniej' in text['effect']
                    assert 'Potwierdź ✓' in text['instruction']
                if item['kind'].startswith('heal'):
                    assert 'dobierzesz' in text['when']


def test_print_uses_live_descriptions_and_preserves_recovery_diagram(monkeypatch):
    root=Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(root/'scripts'))
    mats=importlib.import_module('build_hero_mats')
    for hero_id in PLAYABLE_HERO_IDS:
        hero=mats.build_print_hero(hero_id)
        # No duplicate print copy required: mana descriptions come from runtime data.
        html=mats.mana_page(hero,{})
        assert html.count('class="mana-slot"')==5
        assert html.count('class="passive-block ')==10
        assert 'mana_recovery.svg' in html
        assert '63 × 88 mm' in html
        assert 'Potwierdź' in html
        assert 'postępu / postępu' not in html
