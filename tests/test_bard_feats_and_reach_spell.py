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
from GameObjects.events.reach_spell_event import ReachSpellEvent
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll
from statuses.classes.bard.feats.bardic_lore import BARDIC_LORE_STATUS
from statuses.classes.bard.feats.reach_spell import REACH_SPELL_STATUS
from statuses.classes.bard.feats.versatile_performance import VERSATILE_PERFORMANCE_STATUS


@dataclass
class DummyHero(StatusMixin):
    pass


def test_bardic_lore_adds_recall_knowledge_note():
    actor = DummyHero()
    actor.add_status(BARDIC_LORE_STATUS)

    res = resolve_skill_check_with_sources_from_roll(
        skill_id="arcana",
        dc=15,
        actor=actor,
        tags=["knowledge"],
        roll=10,
        apply_modifiers=True,
    )

    assert any("bardic lore" in note.lower() and "2x k20" in note.lower() for note in res.notes)


def test_versatile_performance_adds_diplomacy_note():
    actor = DummyHero()
    actor.add_status(VERSATILE_PERFORMANCE_STATUS)

    res = resolve_skill_check_with_sources_from_roll(
        skill_id="diplomacy",
        dc=15,
        actor=actor,
        tags=["diplomacy"],
        roll=10,
        apply_modifiers=True,
    )

    assert any("zamiast diplomacy" in note.lower() and "performance" in note.lower() for note in res.notes)


def test_reach_spell_extends_touch_to_30_and_consumes_ready_status():
    actor = DummyHero()
    actor.add_status(REACH_SPELL_STATUS)
    game_logs: list[str] = []
    game = SimpleNamespace(state=object(), ui_log=lambda msg: game_logs.append(str(msg)))
    ctx = EventContext(game=game, actor=actor)

    reach_result = ReachSpellEvent().run(ctx)
    assert reach_result.success is True
    assert actor.has_status("reach_spell_ready")

    class DummyTouchSpell(MagicEvent):
        name = "dummy_touch_spell"
        actions_cost = 1
        range_feet = 5
        spell_tags = ["touch", "arcane"]

        def execute(self, _ctx: EventContext) -> EventResult:
            return EventResult(success=True, consumed_action=True, message="ok")

    spell = DummyTouchSpell()
    result = MagicEventResolver.resolve(spell, ctx)

    assert result.success is True
    assert spell.range_feet == 30
    assert not actor.has_status("reach_spell_ready")
    assert any("reach spell" in msg.lower() and "30 ft" in msg.lower() for msg in game_logs)

