"""Canonical printable links and restricted local PDF delivery."""
from pathlib import Path
from threading import RLock
from types import SimpleNamespace

import pytest
from flask import Flask
from flask.testing import FlaskClient

from dnd_board_game.physical_cards import handout_files
from dnd_board_game.ui import mission_zero, routes
from tests.unit.test_mission_zero import session


PUBLIC_FILES = (
    "characters.pdf", "map_a4.pdf", "map_full.pdf", "mission_0/tiles.pdf",
    "mission_0/items.pdf", "mission_0/order.pdf", "mission_0/receipts.pdf",
    "reference/rules.pdf", "reference/markers.pdf",
)


@pytest.fixture(scope="module")
def materials_app(tmp_path_factory: pytest.TempPathFactory) -> Flask:
    # The download/list routes only need launcher transport, not a game engine.
    stub = SimpleNamespace(
        combat_state=None, _board_state_lock=RLock(),
        _cancel_obsolete_board_input=lambda: None, _sync_board_leds=lambda: None,
    )
    app = routes.create_app(stub, character_dir=tmp_path_factory.mktemp("handout-characters"))
    app.config["TESTING"] = True
    return app


@pytest.fixture
def materials_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    folder = tmp_path / "handouts"
    folder.mkdir()
    monkeypatch.setattr(handout_files, "HANDOUTS_ROOT", folder)
    return folder


@pytest.fixture
def client(materials_app: Flask, materials_root: Path) -> FlaskClient:
    return materials_app.test_client()


def write_pdf(folder: Path, filename: str) -> bytes:
    path = folder / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    data = ("%PDF-1.4\n" + filename + "\n%%EOF\n").encode("ascii")
    path.write_bytes(data)
    return data


def test_registry_has_only_current_handouts(materials_root: Path) -> None:
    assert tuple(spec.filename for spec in handout_files.HANDOUT_FILES) == PUBLIC_FILES
    for filename in PUBLIC_FILES:
        assert handout_files.handout_path(filename, root=materials_root) == materials_root / filename
        assert handout_files.handout_url(filename) == "/session-materials/" + filename


def test_listing_distinguishes_maps_tiles_and_separate_documents(
    client: FlaskClient, materials_root: Path,
) -> None:
    for filename in PUBLIC_FILES:
        write_pdf(materials_root, filename)
    response = client.get("/session-materials")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert html.count('class="save-card"') == len(PUBLIC_FILES)
    for filename in PUBLIC_FILES:
        assert f'href="/session-materials/{filename}"' in html
    assert "A4" in html and "cały arkusz" in html and "kafle" in html
    for old_path in ("runy_v01", "runy_relacje_v03", "misja_0_komplet_A4", "karty_postaci_A4"):
        assert old_path not in html


def test_listing_disables_missing_materials(client: FlaskClient) -> None:
    html = client.get("/session-materials").get_data(as_text=True)
    assert html.count("Ten pakiet nie został jeszcze wygenerowany.") == len(PUBLIC_FILES)
    assert 'href="/session-materials/' not in html


@pytest.mark.parametrize("filename", PUBLIC_FILES)
def test_download_delivers_the_current_file(
    filename: str, client: FlaskClient, materials_root: Path,
) -> None:
    data = write_pdf(materials_root, filename)
    response = client.get("/session-materials/" + filename)
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.get_data() == data
    assert Path(filename).name in response.headers["Content-Disposition"]


@pytest.mark.parametrize("filename", ("characters.pdf", "mission_0/tiles.pdf", "reference/rules.pdf"))
def test_registered_missing_file_is_404(filename: str, client: FlaskClient) -> None:
    assert client.get("/session-materials/" + filename).status_code == 404


def test_registered_directory_is_not_delivered(client: FlaskClient, materials_root: Path) -> None:
    (materials_root / "characters.pdf").mkdir()
    assert client.get("/session-materials/characters.pdf").status_code == 404
    assert 'href="/session-materials/characters.pdf"' not in client.get("/session-materials").get_data(as_text=True)


@pytest.mark.parametrize("filename", (
    "private.pdf", "mission_0/private.pdf", "README.md", "characters.pdf.bak",
    "karty_postaci_A4.pdf", "misja_0_komplet_A4.pdf", "sciaga_graczy_A4.pdf",
    "znaczniki_A4.pdf", "../private.pdf", "mission_0/../../private.pdf",
    "%2e%2e%2fprivate.pdf", "mission_0/%2e%2e/%2e%2e/private.pdf",
    "mission_0%5ctiles.pdf", "reference/rules.pdf/..",
))
def test_unlisted_and_traversal_paths_never_reach_delivery(
    filename: str, client: FlaskClient, materials_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_pdf(materials_root, "private.pdf")
    write_pdf(materials_root, "mission_0/private.pdf")
    (materials_root.parent / "private.pdf").write_bytes(b"outside secret")
    def unexpected_delivery(*args: object, **kwargs: object) -> None:
        raise AssertionError("Rejected path reached PDF delivery")
    monkeypatch.setattr(routes, "send_from_directory", unexpected_delivery)
    assert client.get("/session-materials/" + filename).status_code == 404


def test_external_symlink_is_not_listed_or_delivered(
    client: FlaskClient, materials_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    outside = materials_root.parent / "private.pdf"
    outside.write_bytes(b"outside secret")
    (materials_root / "characters.pdf").symlink_to(outside)
    with pytest.raises(ValueError, match="poza"):
        handout_files.handout_path("characters.pdf", root=materials_root)
    def unexpected_delivery(*args: object, **kwargs: object) -> None:
        raise AssertionError("External symlink reached PDF delivery")
    monkeypatch.setattr(routes, "send_from_directory", unexpected_delivery)
    assert client.get("/session-materials/characters.pdf").status_code == 404
    assert 'href="/session-materials/characters.pdf"' not in client.get("/session-materials").get_data(as_text=True)


def test_mission_payload_uses_physical_material_urls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    game = session(tmp_path, legacy_combat=False)
    asset_url = mission_zero.asset_url
    def scenario_asset(root: Path, filename: str) -> str:
        assert not filename.endswith(".pdf"), "Print download used scenario asset routing"
        return asset_url(root, filename)
    monkeypatch.setattr(mission_zero, "asset_url", scenario_asset)
    data = mission_zero.payload(game)
    assert data is not None
    assert data["print_cutouts"] == "/session-materials/mission_0/tiles.pdf"
    assert data["print_characters"] == "/session-materials/characters.pdf"
    assert data["print_map"] == "/session-materials/map_a4.pdf"
