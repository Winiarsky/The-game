from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.base import EventContext, EventResult
from GameObjects.events.rogue_feat_events import TwinFeintEvent
from statuses.base import Status


@dataclass
class DummyActor:
    object_id: str = "hero-1"
    name: str = "Hero"
    position: tuple[int, int] | None = (0, 0)
    statuses: list[Status] = field(default_factory=lambda: [Status(id="twin_feint")])

    def has_status(self, status_id: str) -> bool:
        return any(getattr(item, "id", item) == status_id for item in self.statuses)


def test_twin_feint_marks_second_strike_as_forced_off_guard(monkeypatch):
    actor = DummyActor()
    target = SimpleNamespace(object_id="enemy-1", name="Enemy", position=(1, 0))
    game = SimpleNamespace(
        enemies=[target],
        heroes=[actor],
        events=SimpleNamespace(safe_emit_action=lambda **_kwargs: None),
        ui_log=lambda *_a, **_k: None,
    )

    weapon_a = object()
    weapon_b = object()

    calls: list[tuple[str, dict]] = []

    def _fake_dispatch(name, event_ctx):
        metadata = dict(event_ctx.metadata or {})
        calls.append((str(name), metadata))
        return EventResult(
            success=True,
            consumed_action=True,
            data={"hit": True, "defeated": False, "target": target, "target_pos": target.position},
        )

    monkeypatch.setattr("GameObjects.events.rogue_feat_events._equipped_melee_weapons_1h", lambda _actor: [weapon_a, weapon_b])
    monkeypatch.setattr(
        "GameObjects.events.rogue_feat_events._weapon_event_name",
        lambda weapon: "first_strike" if weapon is weapon_a else "second_strike",
    )
    monkeypatch.setattr("GameObjects.events.rogue_feat_events._pick_adjacent_target", lambda _ctx, _actor: (target, target.position))
    monkeypatch.setattr("GameObjects.events.rogue_feat_events.dispatch_event", _fake_dispatch)

    result = TwinFeintEvent().run(EventContext(game=game, actor=actor))

    assert result.success is True
    assert len(calls) == 2
    assert calls[0][0] == "first_strike"
    assert calls[1][0] == "second_strike"
    assert calls[1][1].get("force_flat_footed") is True
    assert calls[1][1].get("force_flat_footed_source") == "twin_feint"

