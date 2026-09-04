import json
from pathlib import Path

from PIL import Image


ASSET_ROOT = Path("assets/physical_cards/character_sets/keyboard_v1")


def test_keyboard_character_manifest_contains_controls_and_dossiers() -> None:
    manifest = json.loads(
        (ASSET_ROOT / "keyboard_character_cards_v1.json").read_text(encoding="utf-8")
    )

    assert manifest["version"] == 2
    assert manifest["page_contract"] == {
        "page_1": "Skróty, statystyki i opisy aktywnych zdolności.",
        "page_2": "Historia, motywacja, cel, pasywki, skaza i plan tury.",
    }
    assert {hero["hero_id"] for hero in manifest["heroes"]} == {
        "garran",
        "brakka",
        "mira",
        "dagna",
        "lorian",
        "nimra",
        "erynd",
    }
    for hero in manifest["heroes"]:
        assert hero["shortcuts"]
        assert hero["narrative"]["history"]
        assert hero["narrative"]["personal_goal"]
        assert hero["narrative"]["turn_plan"]
        assert hero["passives"]
        assert hero["flaw"]["body"]


def test_every_hero_has_keyboard_and_dossier_png() -> None:
    manifest = json.loads(
        (ASSET_ROOT / "keyboard_character_cards_v1.json").read_text(encoding="utf-8")
    )
    for hero in manifest["heroes"]:
        hero_id = hero["hero_id"]
        for suffix in ("keyboard", "dossier"):
            path = ASSET_ROOT / "png" / f"{hero_id}_{suffix}_sheet_v1.png"
            with Image.open(path) as image:
                assert image.size == (2048, 3072)
                assert image.info["dpi"][0] >= 299


def test_every_hero_has_grayscale_minimal_a4_pages() -> None:
    manifest = json.loads(
        (ASSET_ROOT / "keyboard_character_cards_v1.json").read_text(encoding="utf-8")
    )
    minimal_root = ASSET_ROOT / "minimal_bw"
    for hero in manifest["heroes"]:
        hero_id = hero["hero_id"]
        for page_kind in ("keyboard", "dossier"):
            path = minimal_root / "png" / f"{hero_id}_{page_kind}_minimal_bw_v1.png"
            with Image.open(path) as image:
                assert image.size == (2480, 3508)
                assert image.mode == "L"
                assert image.info["dpi"][0] >= 299
        assert (minimal_root / "pdf" / f"{hero_id}_minimal_bw_v1.pdf").stat().st_size > 10_000

    assert (minimal_root / "pdf" / "minimal_bw_character_sheets_v1.pdf").stat().st_size > 50_000
