"""Session UI wording is editable without mutating or restarting a game."""
import json
from pathlib import Path

import pytest

from dnd_board_game.ui.session_copy import load_ui_copy, render_ui_text, ui_text


def test_copy_is_read_fresh_and_interpolation_preserves_unprovided_tokens(tmp_path: Path) -> None:
    folder = tmp_path / "text/ui"
    folder.mkdir(parents=True)
    source = folder / "combat.json"
    source.write_text(json.dumps({"turn": "Tura {name} · {round}"}))
    assert ui_text("combat.turn", root=tmp_path, name="Mira") == "Tura Mira · {round}"
    source.write_text(json.dumps({"turn": "Teraz {name}"}))
    assert ui_text("combat.turn", root=tmp_path, name="Nimra") == "Teraz Nimra"


def test_missing_or_non_text_key_reports_its_location() -> None:
    with pytest.raises(ValueError, match="combat.missing"):
        render_ui_text({"combat": {}}, "combat.missing")
    with pytest.raises(ValueError, match="combat.portraits"):
        render_ui_text({"combat": {"portraits": {}}}, "combat.portraits")


def test_malformed_copy_identifies_editable_file(tmp_path: Path) -> None:
    folder = tmp_path / "text/ui"
    folder.mkdir(parents=True)
    source = folder / "navigation.json"
    source.write_text("{bad")
    with pytest.raises(ValueError, match="navigation.json"):
        load_ui_copy(tmp_path)
