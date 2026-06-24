from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.base import EventContext, EventResult
from GameObjects.events.magic.magic_event import MagicEvent, MagicEventResolver
from GameObjects.events.widen_spell_event import WidenSpellEvent
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from statuses.base import Status
from statuses.classes.druid.feats.widen_spell import WIDEN_SPELL_STATUS


@dataclass
class DummyHero(StatusMixin):
    pass


def _druid_status() -> Status:
    return Status(
        id="druid",
        data={"druid_setup": {"order": "animal"}},
    )


def test_widen_spell_event_requires_feat():
    actor = DummyHero()
    actor.add_status(_druid_status())
    ctx = EventContext(game=SimpleNamespace(state=object(), ui_log=lambda *_a, **_k: None), actor=actor)

    result = WidenSpellEvent().run(ctx)
    assert result.success is False
    assert "wymaga featu" in str(result.message or "").lower()


def test_widen_spell_sets_ready_and_is_consumed_by_next_spell():
    actor = DummyHero()
    actor.add_status(_druid_status())
    actor.add_status(WIDEN_SPELL_STATUS)
    game_logs: list[str] = []
    ctx = EventContext(game=SimpleNamespace(state=object(), ui_log=lambda msg: game_logs.append(str(msg))), actor=actor)

    widen_result = WidenSpellEvent().run(ctx)
    assert widen_result.success is True
    assert actor.has_status("widen_spell_ready")

    class DummySpell(MagicEvent):
        name = "dummy_spell_after_widen"
        actions_cost = 1
        spell_tags = ["primal"]

        def execute(self, _ctx: EventContext) -> EventResult:
            return EventResult(success=True, consumed_action=True, message="ok")

    result = MagicEventResolver.resolve(DummySpell(), ctx)

    assert result.success is True
    assert not actor.has_status("widen_spell_ready")
    assert any("widen spell" in msg.lower() for msg in game_logs)
