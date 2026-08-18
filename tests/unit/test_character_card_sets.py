from __future__ import annotations

import json

import pytest
from PIL import Image, ImageChops, ImageDraw

from dnd_board_game.physical_cards.character_card_sets import (
    ADDITIONAL_ART,
    CHARACTER_DECKS,
    DAGNA_ART,
    DAGNA_DECK,
    GARRAN_ART,
    GARRAN_DECK,
    CARD_SIZE_PX,
    SAFE_MARGIN_MM,
    _art_panel_for,
    _access_badge,
    _card_resource_lines,
    _fit_timing_font,
    _font,
    _mm,
    _phase_label,
    _stat_lines,
    _wrapped_lines,
    generate_character_sheet_bw_pdf,
    generate_character_card_set_bw_test,
    generate_character_card_set,
    printable_action_cards,
    render_character_sheet_bw,
    render_character_dossier_bw,
    render_character_action_card_bw_test,
)
from dnd_board_game.character_creation import PLAYABLE_HERO_IDS
from dnd_board_game.physical_cards.action_catalog import (
    CURATED_CARD_OWNERS,
    CardPhase,
    CardTriggerWindow,
    CombatCardRoute,
    card_action_definition,
)
from dnd_board_game.physical_cards.qr_payload import (
    parse_actor_card_qr_payload,
    parse_decision_card_qr_payload,
)


def test_character_decks_have_expected_unique_active_cards() -> None:
    assert len(CHARACTER_DECKS["garran"].action_cards) == 12
    assert len(CHARACTER_DECKS["dagna"].action_cards) == 13
    assert "improved_critical" not in {card.source_id for card in CHARACTER_DECKS["garran"].action_cards}
    assert "disciple_of_life" not in {card.source_id for card in CHARACTER_DECKS["dagna"].action_cards}

    for actor_id in PLAYABLE_HERO_IDS:
        deck = CHARACTER_DECKS[actor_id]
        assert "basic_attack" not in {card.source_id for card in deck.action_cards}
        payloads = [card.payload_for(deck.actor_id) for card in deck.action_cards]
        assert len(payloads) == len(set(payloads))
        for card in deck.action_cards:
            parsed = parse_decision_card_qr_payload(card.payload_for(deck.actor_id))
            assert parsed.source_id == card.source_id
            if card.source_id not in {"accept", "decline", "maneuvers", "equipment"}:
                assert parsed.actor_id == deck.actor_id
            assert card.required_level in {1, 2, 3}
            if card.source_id not in {"accept", "decline"}:
                assert card.mechanic
                assert card.flavor


def test_seven_archetypes_have_balanced_combat_only_decks() -> None:
    expected = {
        "garran": {
            "second_wind",
            "action_surge",
            "lay_on_hands",
            "defensive_stance",
        },
        "brakka": {"rage", "reckless_attack", "frenzy"},
        "mira": {
            "cunning_action",
            "instinctive_dodge",
            "exploit_weakness",
            "invisibility",
            "find_traps",
        },
        "erynd": {
            "hunters_mark",
            "goodberry",
            "cunning_action",
            "patient_shot",
            "find_traps",
        },
        "dagna": {"sacred_flame", "healing_word", "bless", "sanctuary"},
        "lorian": {"bardic_inspiration", "vicious_mockery", "thunderwave", "healing_word"},
        "nimra": {"ray_of_frost", "grease", "shield", "sleep"},
    }

    for actor_id, source_ids in expected.items():
        cards = {
            card.source_id: card
            for card in printable_action_cards(CHARACTER_DECKS[actor_id])
        }
        assert source_ids <= set(cards)
        assert all(cards[source_id].required_level <= 3 for source_id in source_ids)
        combat_cards = tuple(
            card for card in cards.values() if card.kind != "universal"
        )
        assert 7 <= len(combat_cards) <= 9
        assert all(
            card_action_definition(card.source_id).phase
            is CardPhase.COMBAT
            for card in combat_cards
        )

    mira = {
        card.source_id: card
        for card in printable_action_cards(CHARACTER_DECKS["mira"])
    }
    erynd = {
        card.source_id: card
        for card in printable_action_cards(CHARACTER_DECKS["erynd"])
    }
    assert "3/3" in mira["invisibility"].mechanic
    assert "1 Instynkt" in erynd["goodberry"].mechanic
    assert "true_strike" not in mira
    assert "true_strike" not in erynd


def test_every_playable_hero_card_lists_passives_and_mechanical_flaw() -> None:
    canvas = Image.new("RGB", CARD_SIZE_PX, "white")
    draw = ImageDraw.Draw(canvas)
    passive_font = _font(_mm(2.05))
    passive_width = CARD_SIZE_PX[0] - 2 * _mm(SAFE_MARGIN_MM) - _mm(4)
    for actor_id in PLAYABLE_HERO_IDS:
        passives = CHARACTER_DECKS[actor_id].passives
        assert len(passives) >= 3
        flaws = tuple(entry for entry in passives if entry.startswith("Skaza:"))
        assert len(flaws) == 1
        assert "—" in flaws[0]
        assert any(token in flaws[0] for token in ("−1", "utrudnienie", "nie może", "Przerażony", "blokuje"))
        assert all(
            len(_wrapped_lines(draw, entry, passive_font, passive_width)) <= 4
            for entry in passives
        )
    canvas.close()


def test_every_printed_combat_card_has_runtime_route_and_correct_reaction_window() -> None:
    for actor_id in PLAYABLE_HERO_IDS:
        for card in printable_action_cards(CHARACTER_DECKS[actor_id]):
            if card.kind == "universal":
                continue
            definition = card_action_definition(card.source_id)
            assert definition.phase is CardPhase.COMBAT
            assert actor_id in CURATED_CARD_OWNERS.get(card.source_id, ())
            if card.kind == "spell":
                assert definition.combat_route is not None
            if "REAKCJA" in card.timing:
                assert definition.combat_route is CombatCardRoute.REACTION or (
                    CardTriggerWindow.ATTACK_ROLL_REVEALED in definition.trigger_windows
                    or CardTriggerWindow.DAMAGE_ROLL_REVEALED in definition.trigger_windows
                )


def test_every_class_action_has_its_own_comic_panel() -> None:
    for deck in CHARACTER_DECKS.values():
        source_ids = {
            card.source_id
            for card in deck.action_cards
            if card.source_id not in {"accept", "decline"}
        }
        assigned_panels = {
            (_art_panel_for(deck, source_id).asset, _art_panel_for(deck, source_id).panel_index)
            for source_id in source_ids
        }
        assert len(assigned_panels) == len(source_ids)


def test_printable_cards_follow_current_phase_and_spell_content() -> None:
    dagna_cards = {
        card.source_id: card
        for card in printable_action_cards(DAGNA_DECK)
    }

    assert "gentle_repose" not in dagna_cards
    assert "guidance" not in dagna_cards
    assert "prayer_of_healing" not in dagna_cards
    assert dagna_cards["accept"].mechanic == ""
    all_mechanics = " ".join(
        card.mechanic
        for deck in CHARACTER_DECKS.values()
        for card in printable_action_cards(deck)
    )
    assert "wyższy komórkę" not in all_mechanics
    assert " slot" not in all_mechanics.lower()
    for actor_id in PLAYABLE_HERO_IDS:
        deck = CHARACTER_DECKS[actor_id]
        assert all(
            card.kind == "universal"
            or card_action_definition(card.source_id).phase is not CardPhase.REMOVED
            for card in printable_action_cards(deck)
        )

    lorian_cards = {
        card.source_id: card
        for card in printable_action_cards(CHARACTER_DECKS["lorian"])
    }
    nimra_cards = {
        card.source_id: card
        for card in printable_action_cards(CHARACTER_DECKS["nimra"])
    }
    assert "utrudnienie" in lorian_cards["vicious_mockery"].mechanic
    assert "10 stóp" in nimra_cards["shatter"].mechanic
    assert "konstrukty" in nimra_cards["shatter"].mechanic


def test_dossiers_list_exact_card_resources_instead_of_level_progression() -> None:
    expected = {
        "garran": ("Taktyka 3/3", "Ratunek polowy 15/15"),
        "brakka": ("Szał 3/3", "Dzikość 2/2"),
        "mira": ("Fortele 3/3", "Unik instynktowny 1/1"),
        "dagna": ("Komórki czarów: 4× 1. poziomu, 2× 2. poziomu", "Boska Moc 1/1"),
        "lorian": ("Komórki czarów: 4× 1. poziomu, 2× 2. poziomu", "Inspiracja bardowska 4/4"),
        "nimra": ("Komórki czarów: 4× 1. poziomu, 2× 2. poziomu", "Odzyskiwanie magiczne 1/1"),
        "erynd": ("Instynkt 3/3", "Karty niewymienione"),
    }
    for actor_id, required_fragments in expected.items():
        text = "\n".join(_card_resource_lines(CHARACTER_DECKS[actor_id]))
        assert all(fragment in text for fragment in required_fragments)
        assert "rozwój" not in text.lower()


def test_character_sheet_lists_only_spells_available_from_physical_deck() -> None:
    lorian = _stat_lines(CHARACTER_DECKS["lorian"])["spells"]
    nimra = _stat_lines(CHARACTER_DECKS["nimra"])["spells"]

    assert "Zauroczenie osoby" not in lorian
    assert "Wykrycie magii" not in nimra
    assert "Identyfikacja" not in nimra
    assert "Obezwładniający Żart" in lorian
    assert "Pajęczyna" in nimra


def test_black_and_white_character_sheet_is_toner_friendly(tmp_path) -> None:
    sheet = render_character_sheet_bw(GARRAN_DECK)
    red, green, blue = sheet.split()

    assert ImageChops.difference(red, green).getbbox() is None
    assert ImageChops.difference(red, blue).getbbox() is None
    histogram = red.histogram()
    dark_coverage = sum(histogram[:128]) / (sheet.width * sheet.height)
    assert dark_coverage < 0.12
    sheet.close()
    red.close()
    green.close()
    blue.close()

    output = tmp_path / "character_sheet_garran_bw.pdf"
    generate_character_sheet_bw_pdf("garran", output)
    assert output.read_bytes().startswith(b"%PDF")

    dossier = render_character_dossier_bw(GARRAN_DECK)
    red, green, blue = dossier.split()
    assert ImageChops.difference(red, green).getbbox() is None
    assert ImageChops.difference(red, blue).getbbox() is None
    assert sum(red.histogram()[:128]) / (dossier.width * dossier.height) < 0.12
    dossier.close()
    red.close()
    green.close()
    blue.close()


def test_every_timing_label_fits_before_the_level_badge() -> None:
    canvas = Image.new("RGB", CARD_SIZE_PX, "white")
    draw = ImageDraw.Draw(canvas)
    safe = _mm(SAFE_MARGIN_MM)
    level_font = _font(_mm(1.95), bold=True)
    level_width = draw.textbbox((0, 0), "OD STARTU", font=level_font)[2]
    timing_room = CARD_SIZE_PX[0] - 2 * safe - level_width - _mm(8)

    for actor_id in PLAYABLE_HERO_IDS:
        deck = CHARACTER_DECKS[actor_id]
        for card in printable_action_cards(deck):
            if card.source_id in {"accept", "decline"}:
                continue
            timing_text = " · ".join(filter(None, (_phase_label(card), card.timing)))
            font = _fit_timing_font(draw, timing_text, timing_room)
            assert draw.textbbox((0, 0), timing_text, font=font)[2] <= timing_room, (
                deck.actor_id,
                card.source_id,
                timing_text,
            )
            assert _access_badge(deck, card) == "OD STARTU"
    canvas.close()


def test_black_and_white_test_card_is_monochrome_and_low_coverage() -> None:
    card = render_character_action_card_bw_test(
        DAGNA_DECK,
        next(
            spec
            for spec in printable_action_cards(DAGNA_DECK)
            if spec.source_id == "healing_word"
        ),
    )
    red, green, blue = card.split()

    assert ImageChops.difference(red, green).getbbox() is None
    assert ImageChops.difference(red, blue).getbbox() is None
    dark_coverage = sum(red.histogram()[:128]) / (card.width * card.height)
    assert dark_coverage < 0.18

    card.close()
    red.close()
    green.close()
    blue.close()


def test_generate_front_only_black_and_white_test_deck(tmp_path) -> None:
    output = tmp_path / "card_set_garran_bw_test.pdf"
    result = generate_character_card_set_bw_test(
        "garran",
        output,
        preview_dir=tmp_path / "previews",
    )

    assert result.card_count == 13
    assert result.page_count == 6
    assert output.read_bytes().startswith(b"%PDF")
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["print_mode"] == "black_and_white_toner_fronts_only_with_dossier_and_statistics"
    assert manifest["backs_included"] is False
    assert manifest["page"]["pages"] == 6
    assert manifest["dossier_pages"] == 1
    assert manifest["statistics_pages"] == 1
    assert len(manifest["cards"]) == 13
    assert all(card.get("phase") != "removed" for card in manifest["cards"])
    assert len(tuple((tmp_path / "previews").glob("*_fronts_bw.png"))) == 4
    assert (tmp_path / "previews" / "dossier_bw.png").is_file()
    assert (tmp_path / "previews" / "statistics_bw.png").is_file()


@pytest.mark.parametrize(
    ("actor_id", "expected_cards", "expected_pages"),
    (
        ("garran", 13, 10),
        ("dagna", 14, 10),
        ("brakka", 12, 8),
        ("mira", 12, 8),
        ("lorian", 13, 10),
        ("nimra", 14, 10),
        ("erynd", 13, 10),
    ),
)
def test_generate_character_card_set(
    tmp_path,
    actor_id: str,
    expected_cards: int,
    expected_pages: int,
) -> None:
    output = tmp_path / f"card_set_{actor_id}.pdf"
    result = generate_character_card_set(
        actor_id,
        output,
        preview_dir=tmp_path / "previews" / actor_id,
    )

    assert result.card_count == expected_cards
    assert result.page_count == expected_pages
    assert output.read_bytes().startswith(b"%PDF")
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["cards"]) == expected_cards
    assert manifest["dossier_pages"] == 1
    assert manifest["statistics_pages"] == 1
    assert manifest["statistics_style"] == "black_and_white_toner"
    assert parse_actor_card_qr_payload(manifest["cards"][0]["payload"]).actor_id == actor_id
    assert manifest["cards"][1]["payload"] == "dndbg:v1:action:universal:accept"
    assert manifest["cards"][2]["payload"] == "dndbg:v1:action:universal:decline"
    assert parse_decision_card_qr_payload(manifest["cards"][5]["payload"]).actor_id == actor_id
    assert all("art_panel" in card for card in manifest["cards"][1:])
    assert all(card.get("phase") != "removed" for card in manifest["cards"])
    assert (tmp_path / "previews" / actor_id / "dossier.png").is_file()
    assert (tmp_path / "previews" / actor_id / "statistics.png").is_file()
    assert (tmp_path / "previews" / actor_id / "character_sheet_bw.png").is_file()
