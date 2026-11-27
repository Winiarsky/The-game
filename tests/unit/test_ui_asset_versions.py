"""A normal page refresh must load new panel code after an application update."""

import re
import shutil
from pathlib import Path

from dnd_board_game.ui.exploration_app import ExplorationUiSession
from dnd_board_game.ui.routes import create_app


def test_play_page_versions_assets_and_changes_only_edited_asset(
    tmp_path: Path,
) -> None:
    session = ExplorationUiSession(
        "content/scenarios/recruitment_arena.json",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
    )
    app = create_app(session, character_dir=tmp_path / "characters")
    static = tmp_path / "static"
    static.mkdir()
    for source in Path(app.static_folder).iterdir():
        if source.is_file():
            shutil.copyfile(source, static / source.name)
    app.static_folder = str(static)
    client = app.test_client()

    def asset_urls() -> dict[str, str]:
        response = client.get("/play")
        assert response.status_code == 200
        urls = re.findall(
            r'(?:src|href)="(/static/[^"?]+\?v=[a-f0-9]{12})"', response.text
        )
        return {url.split("?")[0].rsplit("/", 1)[1]: url for url in urls}

    original = asset_urls()
    assert {
        "exploration.js", "exploration.css", "board_panel.js", "shared_mana.js",
        "player_ui.js", "player_ui.css",
    } <= original.keys()
    assert asset_urls() == original
    for name in ("exploration.js", "player_ui.js", "player_ui.css"):
        path = static / name
        path.write_text(path.read_text() + "\n/* Simulate a new UI release. */\n")
        updated = asset_urls()
        assert updated[name] != original[name]
        assert {key: value for key, value in updated.items() if key != name} == {
            key: value for key, value in original.items() if key != name
        }
        assert "Simulate a new UI release" in client.get(updated[name]).text
        original = updated
