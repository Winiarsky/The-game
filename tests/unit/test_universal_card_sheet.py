from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from dnd_board_game.physical_cards.universal_card_sheet import (
    CARD_ART_SIZE_PX,
    UNIVERSAL_CARD_ART_ROOT,
    UNIVERSAL_CARD_BACK_ASSET,
    UNIVERSAL_CARD_SPECS,
    generate_universal_card_sheet,
    render_universal_card_back,
    render_universal_card_front,
)


def test_universal_card_specs_have_stable_control_payloads() -> None:
    assert [spec.payload for spec in UNIVERSAL_CARD_SPECS] == [
        "dndbg:v1:action:universal:accept",
        "dndbg:v1:action:universal:decline",
    ]
    assert [spec.human_code for spec in UNIVERSAL_CARD_SPECS] == ["AC-01", "DC-01"]


def test_universal_card_art_uses_poker_size_plus_bleed() -> None:
    front = render_universal_card_front(UNIVERSAL_CARD_SPECS[0])
    back = render_universal_card_back()
    try:
        assert front.size == CARD_ART_SIZE_PX
        assert back.size == CARD_ART_SIZE_PX
    finally:
        front.close()
        back.close()


def test_universal_card_art_assets_exist() -> None:
    asset_names = [
        *(spec.background_asset for spec in UNIVERSAL_CARD_SPECS),
        UNIVERSAL_CARD_BACK_ASSET,
    ]

    assert all((UNIVERSAL_CARD_ART_ROOT / name).is_file() for name in asset_names)


def test_generate_universal_card_sheet_writes_two_page_pdf_and_manifest(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "accept_decline.pdf"

    result = generate_universal_card_sheet(pdf_path)

    pdf_data = pdf_path.read_bytes()
    assert pdf_data.startswith(b"%PDF")
    assert len(re.findall(rb"/Type /Page(?!s)", pdf_data)) == 2
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert result.card_count == 2
    assert result.page_count == 2
    assert manifest["page"]["format"] == "A4"
    assert manifest["card"] == {
        "trim_width_mm": 63,
        "trim_height_mm": 88,
        "bleed_mm": 3,
        "safe_margin_mm": 4,
        "qr_target_mm": 20,
    }
    assert manifest["duplex"] == {"pages": 2, "flip": "long_edge"}
    assert manifest["back_background_asset"] == UNIVERSAL_CARD_BACK_ASSET
    assert [card["source_id"] for card in manifest["cards"]] == [
        "accept",
        "decline",
    ]
    assert [card["background_asset"] for card in manifest["cards"]] == [
        spec.background_asset for spec in UNIVERSAL_CARD_SPECS
    ]


def test_generate_universal_card_sheet_refuses_to_overwrite(tmp_path: Path) -> None:
    pdf_path = tmp_path / "accept_decline.pdf"
    pdf_path.write_bytes(b"existing")

    with pytest.raises(FileExistsError):
        generate_universal_card_sheet(pdf_path)
