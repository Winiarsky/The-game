from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from states.intent_menu import build_intent_options


class _Actor:
    def __init__(self, statuses: list[str] | None = None):
        self.statuses = [type("_Status", (), {"id": sid})() for sid in list(statuses or [])]

    def has_status(self, status_id: str) -> bool:
        wanted = str(status_id or "").strip().lower()
        return any(str(getattr(item, "id", item)).strip().lower() == wanted for item in self.statuses)


def _grouped_with_stealth() -> dict:
    return {
        "direct": {"move": object(), "stealth": object()},
        "attack": [],
        "magic": [],
        "alchemy": [],
        "special": [],
    }


def test_intent_uses_stealth_entry_when_actor_not_hidden():
    options = build_intent_options(_grouped_with_stealth(), in_combat=True, actor=_Actor([]))
    stealth = next(item for item in options if item.get("id") == "stealth")
    assert stealth["label"] == "Skradanie"


def test_intent_uses_sneak_move_entry_when_actor_already_stealth():
    options = build_intent_options(_grouped_with_stealth(), in_combat=True, actor=_Actor(["stealth"]))
    stealth = next(item for item in options if item.get("id") == "stealth")
    assert stealth["label"] == "Poruszaj sie skrycie"
