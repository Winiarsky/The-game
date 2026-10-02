"""Failed print exports preserve the previously published handouts."""
from pathlib import Path

import pytest

from dnd_board_game.physical_cards.handout_files import publish_pdf
from dnd_board_game.physical_cards.handout_maps import PRINT_SCALE
from scripts import build_handout_maps, build_handouts


def test_invalid_pdf_cannot_replace_a_published_document(tmp_path: Path) -> None:
    source, destination = tmp_path / "source.pdf", tmp_path / "published.pdf"
    source.write_bytes(b"unfinished export")
    destination.write_bytes(b"previous document")
    with pytest.raises(ValueError, match="Nieprawidłowy PDF"):
        publish_pdf(source, destination)
    assert destination.read_bytes() == b"previous document"
    assert not list(tmp_path.glob(".publish-*"))


def test_failed_copy_preserves_published_document_and_removes_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, destination = tmp_path / "source.pdf", tmp_path / "published.pdf"
    source.write_bytes(b"%PDF-new")
    destination.write_bytes(b"previous document")

    def failed_copy(source: Path, destination: Path) -> None:
        destination.write_bytes(b"partial copy")
        raise OSError("disk full")

    monkeypatch.setattr("dnd_board_game.physical_cards.handout_files.shutil.copyfile", failed_copy)
    with pytest.raises(OSError, match="disk full"):
        publish_pdf(source, destination)
    assert destination.read_bytes() == b"previous document"
    assert not list(tmp_path.glob(".publish-*"))


def test_bad_full_map_export_keeps_both_published_maps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "handouts"
    output.mkdir()
    for name in ("map_a4", "map_full"):
        (output / f"{name}.pdf").write_bytes(b"previous map")
    monkeypatch.setattr(build_handout_maps, "render_pdf", lambda source, pdf: pdf.write_bytes(b"%PDF-new"))
    monkeypatch.setattr(build_handout_maps, "pdf_pages", lambda pdf: 12 if pdf.stem == "map_a4" else 2)
    with pytest.raises(RuntimeError, match="map_full"):
        build_handout_maps.build_maps(output, tmp_path / "cache")
    assert all(path.read_bytes() == b"previous map" for path in output.glob("*.pdf"))


def test_bad_mission_export_keeps_every_published_mission_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "handouts"
    mission = output / "mission_0"
    mission.mkdir(parents=True)
    for name in ("tiles", "items", "order", "receipts"):
        (mission / f"{name}.pdf").write_bytes(b"previous handout")
    documents = dict(tiles="tiles", items="items", order="order", receipts="receipts")
    monkeypatch.setattr(build_handouts, "mission_documents", lambda pack, work: (documents, {}))
    monkeypatch.setattr(build_handouts, "render_pdf", lambda source, pdf: pdf.write_bytes(b"%PDF-new"))
    monkeypatch.setattr(build_handouts, "compact_pdf", lambda pdf: None)
    monkeypatch.setattr(build_handouts, "pdf_pages", lambda pdf: 7 if pdf.stem == "tiles" else 2)
    with pytest.raises(RuntimeError, match="items"):
        build_handouts.build_mission(output=output, work=tmp_path / "cache")
    assert all(path.read_bytes() == b"previous handout" for path in mission.glob("*.pdf"))


def test_mission_sources_share_board_scale_and_preserve_cutouts_and_item_reveal(tmp_path: Path) -> None:
    documents, metadata = build_handouts.mission_documents(build_handouts.MISSION, tmp_path)
    assert metadata["print_scale"] == PRINT_SCALE
    assert metadata["pdf_cell_mm"] == pytest.approx(25 * PRINT_SCALE)
    assert len(metadata["cutout_ids"]) == 18
    assert documents["tiles"].count('data-cutout=') == 18
    assert documents["tiles"].count('<section>') == 7
    assert metadata["item_cards"] == 7
    assert "Po identyfikacji — zastępuje kartę pierścienia" in documents["items"]
    assert "filter:grayscale(1)" in documents["items"]
    assert "filter:grayscale(1)" in documents["tiles"]
