from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.interactions_mixin.status_mixin import StatusMixin
from statuses.classes.alchemist.alchemist_research_field import ALCHEMIST_RESEARCH_FIELD_STATUS


class _Hero(StatusMixin):
    def __init__(self, forced_choice: str | None = None):
        self.statuses = []
        self._forced_choice = forced_choice
        self.logs: list[str] = []

    def _pick_choice_id(self, prompt: str, choices: list[str], *, source: str = "status") -> str | None:
        if self._forced_choice and self._forced_choice in choices:
            return self._forced_choice
        return super()._pick_choice_id(prompt, choices, source=source)

    def ui_log(self, message: str) -> None:
        self.logs.append(str(message))


def test_alchemist_research_field_choice_descriptions_are_not_placeholder():
    hero = _Hero()
    for field_id in ("bomber", "chirurgeon", "mutagenist"):
        text = hero._choice_description(field_id)
        low = text.lower()
        assert "brak dodatkowego opisu mechaniki" not in low
        assert "mechanika:" in low
        assert "fluff:" in low


def test_alchemist_research_field_bomber_sets_runtime_payload():
    hero = _Hero(forced_choice="bomber")
    hero.add_status(ALCHEMIST_RESEARCH_FIELD_STATUS)
    status = hero.get_status("alchemist_research_field")
    data = dict(getattr(status, "data", {}) or {})
    assert data.get("research_field") == "bomber"
    assert bool(data.get("bomb_splash_primary_only")) is True
    assert list(data.get("signature_items") or []) == ["acidflask", "alchemists_fire"]


def test_alchemist_research_field_chirurgeon_sets_runtime_payload():
    hero = _Hero(forced_choice="chirurgeon")
    hero.add_status(ALCHEMIST_RESEARCH_FIELD_STATUS)
    status = hero.get_status("alchemist_research_field")
    data = dict(getattr(status, "data", {}) or {})
    assert data.get("research_field") == "chirurgeon"
    assert bool(data.get("use_crafting_for_medicine")) is True
    assert list(data.get("signature_items") or []) == ["antidote", "antiplague"]


def test_alchemist_research_field_mutagenist_sets_runtime_payload():
    hero = _Hero(forced_choice="mutagenist")
    hero.add_status(ALCHEMIST_RESEARCH_FIELD_STATUS)
    status = hero.get_status("alchemist_research_field")
    data = dict(getattr(status, "data", {}) or {})
    assert data.get("research_field") == "mutagenist"
    assert list(data.get("signature_items") or []) == ["quicksilver_mutagen", "juggernaut_mutagen"]
    assert bool(data.get("mutagenic_flashback_used")) is False
