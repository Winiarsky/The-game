"""Regression coverage for the physical-mana export contract."""

import json
from pathlib import Path

import pytest

from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.character_creation.physical_mana_help import physical_mana_flaw
from dnd_board_game.physical_cards.mana_print import PROFILE, build_print_hero
from dnd_board_game.physical_cards.mana_print_html import FORMATS, render_hero_html
from dnd_board_game.rules.physical_mana import hero_abilities, turn_supply
from dnd_board_game.scenarios.pooled_mana_catalog import requirement_text, ability_description, hero_profile


@pytest.mark.parametrize("hero_id", PLAYABLE_HERO_IDS)
def test_all_abilities_costs_and_reaction_labels_reach_every_format(hero_id: str) -> None:
    hero = build_print_hero(hero_id)
    catalog = hero_abilities(hero_id)
    assert {a.id for a in hero.cards} == {a.id for a in catalog}
    slots = [a.panel_slot for a in hero.cards]
    assert None not in slots
    assert len(slots) == len(set(slots))
    for card, rule in zip(hero.cards, catalog, strict=True):
        assert (card.cost, card.timing, card.description) == (
            (),
            rule.timing,
            requirement_text(rule.id, hero_id) + " " + ability_description(hero_id, rule.id),
        )
        assert (card.key == "AUTO") == (rule.timing == "R")
    for format_id in FORMATS:
        html = render_hero_html(hero, format_id)
        for ability in catalog:
            assert html.count(f'data-card-id="{ability.id}"') == 1
        assert PROFILE in html
        assert hero.flaw[0] in html
        for color in ("C", "N", "Z", "B", "F"):
            assert f'data-mana="{color}"' in html
    assert (hero.keep, hero.capacity) == (1, None)
    assert dict(hero.mana_values) == hero_profile(hero_id)["values"]
    assert hero.flaw[1] == physical_mana_flaw(hero_id).body


def test_lorian_has_nine_shared_market_abilities() -> None:
    hero = build_print_hero("lorian")
    cards = {c.id: c for c in hero.cards}
    assert len(cards) == 9
    assert {"mana_inspiration", "mana_tuning", "mana_recovery", "mana_great_tuning", "victory_hymn"} <= cards.keys()
    assert "mana_transmutation" not in cards and "mana_refresh" not in cards
    assert "Osobista pula" in render_hero_html(hero, "minimal")


def test_garran_card_explains_contest_and_boost() -> None:
    hero = build_print_hero("garran")
    shield = next(c for c in hero.cards if c.id == "shield_bash")
    assert (shield.timing, shield.cost) == ("D", ())
    assert "12 pkt" in shield.description
    assert "k20 + modyfikator Siły" in shield.description
    assert "aplikacja rzuca za wroga" in shield.description
    assert "+1k6" in shield.description
    assert "poniżej połowy" in build_print_hero("dagna").flaw[1]


def test_mana_symbols_escape_text_and_match_combat_icon_shapes() -> None:
    from dnd_board_game.physical_cards.mana_symbols import PATHS, mana_text

    js = Path("src/dnd_board_game/ui/static/physical_mana.js").read_text()
    assert all(path in js for path in PATHS.values())
    rendered = mana_text("<script> (N) zamiast (B). Z rynku.")
    assert "<script>" not in rendered and "&lt;script&gt;" in rendered
    assert rendered.count("<svg") == 2 and "Z rynku." in rendered


def test_printed_weapon_damage_includes_runtime_ability_and_archery_bonuses() -> None:
    erynd = build_print_hero("erynd")
    assert erynd.initiative == 6
    assert any("Długi łuk: +6" in weapon and "1k8 + 4" in weapon for weapon in erynd.weapons)
    assert any("Nóż myśliwski: +1" in weapon and "1k4 + 1" in weapon for weapon in erynd.weapons)
    assert any(
        "Miecz: +4" in weapon and "1k8 + 4" in weapon
        for weapon in build_print_hero("garran").weapons
    )


def test_retired_passives_are_replaced_and_new_damage_limits_are_explicit() -> None:
    dagna = dict(build_print_hero("dagna").passives)
    assert "Uczeń Życia" not in dagna
    assert "Wiara" in dagna["Nasycenie maną"]
    assert "Łaska" in dagna["Nasycenie maną"]
    assert "Odzyskiwanie magiczne" not in dict(build_print_hero("nimra").passives)
    assert "+2k6" in dict(build_print_hero("mira").passives)["Atak z cienia"]
    assert "+3k6" not in dict(build_print_hero("mira").passives)["Atak z cienia"]
    assert "1k6" in dict(build_print_hero("erynd").passives)["Pierwsza krew"]


def test_exploration_cards_share_runtime_methods_and_passives() -> None:
    from dnd_board_game.rules.exploration_mana_catalog import HEROES, hero_methods
    from dnd_board_game.application.exploration_mana_flow import method_modifiers
    from dnd_board_game.ui.training_arena import training_hero
    for hero in HEROES:
        cards = build_print_hero(hero).exploration
        assert len(cards) == 2 and {c.kind for c in cards} == {'npc', 'object'}
        for card, method in zip(cards, hero_methods(hero)):
            assert card.id == method.id
            assert card.modifier == sum(m.value for m in method_modifiers(training_hero(hero), method))
    assert build_print_hero('brakka').exploration[0].ability == 'Kondycja'
    assert 'Praktyka terenowa' in dict(build_print_hero('erynd').passives)


def test_descriptions_are_standalone_and_finite_effects_are_named() -> None:
    nimra = {c.id: c for c in build_print_hero("nimra").cards}
    assert "2k6" in nimra["nimra_flame_fan"].description
    assert "15 ft" in nimra["nimra_flame_fan"].description
    assert "najbliższej" in nimra["nimra_lightning_path"].description
    assert "sojusznika" in nimra["nimra_lightning_path"].description
    for hero_id in PLAYABLE_HERO_IDS:
        for card in build_print_hero(hero_id).cards:
            assert "jak obecnie" not in card.description.casefold()
            assert "obecny stożek" not in card.description.casefold()


def test_html_export_uses_all_four_layouts_without_raster_dependency(tmp_path: Path) -> None:
    for format_id in FORMATS:
        html = render_hero_html(build_print_hero("nimra"), format_id)
        assert html.count("data-card-id=") == 12
        assert html.count("data-page=") == 8
        assert "<img" not in html
    with pytest.raises(ValueError):
        render_hero_html(build_print_hero("nimra"), "unknown")


def test_app_print_page_exposes_current_pdfs_and_same_passive_text(tmp_path: Path) -> None:
    from dnd_board_game.ui.exploration_app import ExplorationUiSession
    from dnd_board_game.ui.routes import create_app

    session = ExplorationUiSession(
        "content/scenarios/ostatni_transport_00_gildia.json", save_dir=tmp_path / "saves"
    )
    response = (
        create_app(session, character_dir=tmp_path / "characters")
        .test_client()
        .get("/rules/physical-mana")
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    for format_id in FORMATS:
        assert f"physical_mana_v02/{format_id}/all_heroes.pdf" in html
    assert "1k6 obrażeń" in html
    assert "Ładowanie many" in html
    assert "spalone, wygasłe i uwięzione" in html
    assert "Pula zostaje po użyciu" in html
    assert "Czarna" in html
    assert "Fioletow" not in html and "fioletow" not in html


def test_black_mana_preserves_cost_codes_and_prints_in_every_format() -> None:
    from dnd_board_game.combat.physical_mana import WAVES
    from dnd_board_game.physical_cards.mana_symbols import mana_symbol
    from dnd_board_game.rules.physical_mana import COLORS, ABILITIES

    assert COLORS["F"] == "czarna"
    assert 'aria-label="1 mana czarna"' in mana_symbol("F")
    assert 'aria-label="1 mana dowolna"' in mana_symbol("*")
    assert WAVES[5][0] == "Czarne zakłócenie"
    assert "czarną manę" in WAVES[5][1]
    black_abilities = [ability for ability in ABILITIES if "F" in ability.cost]
    assert black_abilities
    for ability in black_abilities:
        assert "czarna" in ability.cost_label
        assert "fiolet" not in ability.cost_label.lower()
    for hero_id in PLAYABLE_HERO_IDS:
        for format_id in FORMATS:
            html = render_hero_html(build_print_hero(hero_id), format_id)
            assert 'aria-label="1 mana czarna"' in html
            assert "fiolet" not in html.lower()
            assert "#e9d6f3" not in html


@pytest.mark.parametrize("hero_id", PLAYABLE_HERO_IDS)
def test_panel_cards_share_stable_symbols_with_arena(hero_id: str) -> None:
    from dnd_board_game.ui.board_panel_symbols import (
        HERO_PANEL_ABILITIES, SYMBOLS, ability_panel_slot, panel_icon,
    )

    hero = build_print_hero(hero_id)
    active = list(hero.cards)
    assert set(HERO_PANEL_ABILITIES[hero_id]) - {""} == {c.id for c in active}
    assert len(active) <= 20
    assert len({c.panel_slot for c in active}) == len(active)
    for card in reversed(active):
        assert card.panel_slot == ability_panel_slot(hero_id, card.id)
        assert 6 <= card.panel_slot < 26
        assert SYMBOLS[card.panel_slot][0] in panel_icon(card.panel_slot)
    for format_id in FORMATS:
        html = render_hero_html(hero, format_id)
        for card in active:
            assert panel_icon(card.panel_slot) in html
        for key in ("SPACJA", "ENTER", "ESC", "Q", "W", "E", "R"):
            assert f'<span class="key">{key}</span>' not in html
        assert "wyłączony" in html
        for slot in (0, 1, 2, 3, 5, 26, 27, 28, 29):
            assert panel_icon(slot) in html


def test_removed_interaction_slot_is_blank_without_moving_other_symbols() -> None:
    from dnd_board_game.ui.board_panel_symbols import SYMBOLS, PANEL_CONTROLS, panel_icon

    assert len(SYMBOLS) == 30
    assert SYMBOLS[4] == ("Puste pole", "")
    assert panel_icon(4) == ""
    assert SYMBOLS[5][0] == "Koniec tury"
    assert SYMBOLS[6][0] == "Rozwidlenie"
    assert SYMBOLS[26][0] == "Zmniejsz"
    assert all(slot != 4 for slot, _, _ in PANEL_CONTROLS)
    for hero_id in PLAYABLE_HERO_IDS:
        for format_id in FORMATS:
            html = render_hero_html(build_print_hero(hero_id), format_id)
            assert 'data-panel-slot="4"' not in html
            assert '>Interakcja<' not in html


def test_party_confrontation_prints_expose_35_passives_and_influence_modifiers():
    from dnd_board_game.application.confrontation import build
    from dnd_board_game.scenarios.confrontation import passives,scene_by_id
    from dnd_board_game.ui.training_arena import training_hero
    for hero_id in PLAYABLE_HERO_IDS:
        hero=build_print_hero(hero_id)
        assert dict(hero.exploration_passives)=={c:p['label'] for c,p in passives(hero_id).items()}
        for method in hero.exploration:
            scene=scene_by_id('nessa_raise' if method.kind=='npc' else 'sealed_cache')
            profile=build((training_hero(hero_id),),scene).actor
            assert method.influence_modifier==profile.impact_modifier
            assert method.modifier==profile.test_modifier
        html=render_hero_html(hero,'minimal')
        assert 'Pasywy kolorów w eksploracji' in html
        assert 'Dokładnie 21: sukces' not in html and 'Przekroczenie: utrudnienie' not in html
        assert '1/1/2/3' in html


def test_card_fields_separate_charge_burning_and_only_real_boosts():
    from dnd_board_game.physical_cards.mana_ability_text import ability_sections
    for hero in PLAYABLE_HERO_IDS:
        for card in build_print_hero(hero).cards:
            fields=dict(card.sections)
            assert list(fields)[:4]==['Ładunek','Akcja','Spalanie','Efekt']
            assert card.sections==ability_sections(hero,card.id)
    cards={c.id:dict(c.sections) for c in build_print_hero('garran').cards}
    assert 'Podbicia' not in cards['second_wind']
    assert 'Podbicia' not in cards['iron_bastion']
    assert cards['defensive_stance']['Spalanie']=='0 kart.'
    assert '12 pkt' in cards['shield_bash']['Ładunek']
    assert 'Łącznie maks. 2' in cards['shield_bash']['Podbicia']
    assert 'nie wymaga' in cards['shield_bash']['Podbicia']
    assert 'Podbicie' not in requirement_text('second_wind','garran')
    lorian=dict(ability_sections('lorian','mana_recovery'))
    assert lorian['Spalanie']=='0 kart.' and '+2 spalone karty' in lorian['Podbicia']
