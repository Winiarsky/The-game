"""Regression coverage for the physical-mana export contract."""

import json
from pathlib import Path

import pytest

from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.character_creation.physical_mana_help import physical_mana_flaw
from dnd_board_game.physical_cards.mana_print import PROFILE, build_print_hero
from dnd_board_game.physical_cards.mana_print_html import FORMATS, render_hero_html
from dnd_board_game.rules.physical_mana import hero_abilities, turn_supply


@pytest.mark.parametrize("hero_id", PLAYABLE_HERO_IDS)
def test_all_abilities_costs_and_reaction_labels_reach_every_format(hero_id: str) -> None:
    hero = build_print_hero(hero_id)
    catalog = hero_abilities(hero_id)
    assert {a.id for a in hero.cards} == {a.id for a in catalog}
    keys = [a.key for a in hero.cards if a.timing != "R"]
    assert "MENU" not in keys
    assert len(keys) == len(set(keys))
    for card, rule in zip(hero.cards, catalog, strict=True):
        assert (card.cost, card.timing, card.description) == (
            rule.cost,
            rule.timing,
            rule.description,
        )
        assert (card.key == "AUTO") == (rule.timing == "R")
    for format_id in FORMATS:
        html = render_hero_html(hero, format_id)
        for ability in catalog:
            assert html.count(f'data-card-id="{ability.id}"') == 1
        assert PROFILE in html
        assert hero.flaw[0] in html
        for color in ("C", "N", "Z", "B", "F", "*"):
            assert f'data-mana="{color}"' in html
    assert (hero.keep, hero.capacity) == (
        turn_supply(hero_id)["keep"],
        turn_supply(hero_id)["capacity"],
    )
    assert hero.flaw[1] == physical_mana_flaw(hero_id).body


def test_lorian_has_current_mana_keyboard_and_larger_reserve() -> None:
    hero = build_print_hero("lorian")
    cards = {c.id: c for c in hero.cards}
    assert len(cards) == 14
    assert {
        i: cards[i].key
        for i in (
            "mana_inspiration",
            "mana_tuning",
            "mana_transmutation",
            "mana_recovery",
            "mana_refresh",
        )
    } == {
        "mana_inspiration": "Q",
        "mana_tuning": "R",
        "mana_transmutation": "F",
        "mana_recovery": "C",
        "mana_refresh": "V",
    }
    assert "bardic_inspiration" not in cards and "faerie_fire" not in cards
    assert (hero.keep, hero.capacity) == (3, 6)
    assert not any(name == "Kusznik" for name, _ in hero.passives)


def test_garran_card_explains_bonus_shield_and_mana_exchange() -> None:
    hero = build_print_hero("garran")
    shield = next(c for c in hero.cards if c.id == "shield_bash")
    assert (shield.key, shield.timing, shield.cost) == ("E", "D", ("C", "N"))
    assert "1k6 + modyfikator Siły" in shield.description
    assert "aplikacja rzuci za cel" in shield.description
    html = render_hero_html(hero, "minimal")
    assert "dwiema niebieskimi kartami" in html
    assert "jedynego sąsiadującego wroga" in html


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
    assert any("Długi łuk: +8" in weapon and "1k8 + 4" in weapon for weapon in erynd.weapons)
    assert any("Nóż myśliwski: +3" in weapon and "1k4 + 1" in weapon for weapon in erynd.weapons)
    assert any(
        "Miecz: +6" in weapon and "1k8 + 4" in weapon
        for weapon in build_print_hero("garran").weapons
    )


def test_retired_passives_are_replaced_and_new_damage_limits_are_explicit() -> None:
    dagna = dict(build_print_hero("dagna").passives)
    assert "komórk" not in dagna["Uczeń Życia"]
    assert "Z" in dagna["Uczeń Życia"]
    assert "Odzyskiwanie magiczne" not in dict(build_print_hero("nimra").passives)
    assert "+2k6" in dict(build_print_hero("mira").passives)["Atak z cienia"]
    assert "+3k6" not in dict(build_print_hero("mira").passives)["Atak z cienia"]
    assert "1k6" in dict(build_print_hero("erynd").passives)["Pierwsza krew"]


def test_descriptions_are_standalone_and_finite_effects_are_named() -> None:
    nimra = {c.id: c for c in build_print_hero("nimra").cards}
    assert "2k6" in nimra["nimra_flame_fan"].description
    assert "15 ft" in nimra["nimra_flame_fan"].description
    assert "najbliższą" in nimra["nimra_lightning_path"].description
    assert "sojusznika" in nimra["nimra_lightning_path"].description
    for hero_id in PLAYABLE_HERO_IDS:
        for card in build_print_hero(hero_id).cards:
            assert "jak obecnie" not in card.description.casefold()
            assert "obecny stożek" not in card.description.casefold()


def test_html_export_uses_all_four_layouts_without_raster_dependency(tmp_path: Path) -> None:
    for format_id in FORMATS:
        html = render_hero_html(build_print_hero("nimra"), format_id)
        assert html.count("data-card-id=") == 20
        assert html.count("data-page=") == (7 if format_id in ("cards", "bw_test") else 5)
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
        assert f"{PROFILE}/{format_id}/all_heroes.pdf" in html
    assert "1k6 obrażeń" in html
    assert "Pojemność 6" in html
    assert "Swamp — czarna" in html
    assert "Cyfra 1 w kółku" in html
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
