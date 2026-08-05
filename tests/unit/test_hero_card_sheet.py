from pathlib import Path

from dnd_board_game.physical_cards import (
    HERO_CARD_SPECS,
    generate_hero_card_sheet,
)


def test_hero_card_specs_cover_twelve_unique_archetypes() -> None:
    assert len(HERO_CARD_SPECS) == 12
    assert len({spec.actor_id for spec in HERO_CARD_SPECS}) == 12
    assert all(spec.payload == f"dndbg:v1:actor:{spec.actor_id}" for spec in HERO_CARD_SPECS)


def test_generate_hero_card_sheet_writes_duplex_pdf_and_manifest(
    tmp_path: Path,
) -> None:
    result = generate_hero_card_sheet(
        tmp_path / "heroes.pdf",
        preview_dir=tmp_path / "preview",
    )

    assert result.pdf_path.read_bytes().startswith(b"%PDF")
    assert result.card_count == 12
    assert result.page_count == 6
    assert result.manifest_path.is_file()
    assert len(tuple((tmp_path / "preview").glob("*.png"))) == 6
