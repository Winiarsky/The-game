from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.interactions_mixin.status_mixin import StatusMixin
from statuses.classes.bard.bard import BARD_STATUS
from statuses.classes.bard.inspiration import INSPIRATION_STATUS


@dataclass
class DummyHero(StatusMixin):
    messages: list[str] = field(default_factory=list)

    def ui_log(self, message: str) -> None:
        self.messages.append(message)


class DummyUI:
    def __init__(self, answer: str):
        self.answer = answer
        self.enabled = True
        self.last_prompt = None
        self.last_choices = None
        self.last_choice_meta = None
        self.info_calls: list[tuple[str, str]] = []

    def prompt_choice(self, prompt: str, choices=None, **kwargs):
        self.last_prompt = prompt
        self.last_choices = list(choices or [])
        self.last_choice_meta = list(kwargs.get("choice_meta") or [])
        return self.answer

    def prompt_info(self, *_args, **_kwargs):
        title = str(_args[0]) if _args else ""
        prompt_long = str(_kwargs.get("prompt_long") or "")
        self.info_calls.append((title, prompt_long))
        return None


def test_inspiration_choice_adds_maestro_feat_and_spell_note(monkeypatch):
    ui = DummyUI("Maestro")
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.focus_point = 1
    hero.add_status(INSPIRATION_STATUS)

    assert ui.last_prompt is not None and "Bard Muse" in ui.last_prompt
    assert hero.get_status_data("inspiration", "bard_muse") == "maestro"
    assert hero.has_status("lingering_composition")
    assert getattr(hero, "focus_point", None) == 2
    assert any("soothe" in msg.lower() for msg in hero.messages)
    assert any("lingering composition" in title.lower() for title, _ in ui.info_calls)


def test_bard_status_grants_inspiration_and_enigma_feat(monkeypatch):
    ui = DummyUI("Enigma")
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(BARD_STATUS)

    assert hero.has_status("bard")
    assert hero.has_status("inspiration")
    assert hero.get_status_data("inspiration", "bard_muse") == "enigma"
    assert hero.has_status("bardic_lore")
    assert any("true strike" in msg.lower() for msg in hero.messages)
    enigma_meta = next(
        (item for item in list(ui.last_choice_meta or []) if str(item.get("raw") or "").strip().lower() == "enigma"),
        None,
    )
    assert enigma_meta is not None
    desc = str(enigma_meta.get("desc") or "")
    assert "Bardyczna wiedza" in desc
    assert "Prawdziwy cios" in desc
    assert "Brak dodatkowego opisu mechaniki." not in desc
