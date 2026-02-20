from __future__ import annotations

import logging

from board import consts
from skills import Skill
from statuses import PoisonedStatus
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources

from ..base import ActionCostEvent, EventContext, EventResult

logger = logging.getLogger(__name__)


class BasePoisonEvent(ActionCostEvent):
    """Wspólna logika dla trucizn (nałożenie statusu Poisoned)."""

    actions_cost = 1
    default_tags = ["poison", "alchemical", "manipulate"]
    available_in_combat = True
    available_in_exploration = True
    consumes_action = True

    dc: int = 0
    onset_turns: int | None = None
    duration_turns: int = 1
    stages: list[dict[str, object]] = []

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do użycia trucizny.")
        actor_pos = getattr(actor, "position", None)
        if actor_pos is None:
            return EventResult.cancelled(message="Bohater nie stoi na planszy.")

        target, _target_pos = self._pick_target(ctx, actor_pos)
        if target is None:
            return EventResult.cancelled(message="Brak celu w zasięgu.")

        if not self.stages or self.dc <= 0:
            return EventResult.cancelled(message="Brak danych trucizny.")

        result = resolve_skill_check_with_sources(
            skill_id=Skill.FORTITUDE.value,
            dc=int(self.dc),
            actor=target,
            target=None,
            tags=["poison", Skill.FORTITUDE.value],
            game=ctx.game,
            apply_modifiers=True,
        )

        stage = 0
        if result.outcome == "failure":
            stage = 1
        elif result.outcome == "critical_failure":
            stage = 2

        if stage <= 0:
            try:
                ctx.game.ui_log(f"{self._event_label()}: sukces obrony, brak efektu.")
            except Exception:
                pass
            return EventResult(success=True, consumed_action=self.consumes_action, message="Trucizna odparta.")

        stage = min(stage, len(self.stages))
        poison = PoisonedStatus(
            duration=int(self.duration_turns),
            damage=int(self.stages[0].get("damage", 0) or 0),
            dc=int(self.dc),
            source=self.name,
            stages=self.stages,
            stage=stage,
            onset=self.onset_turns,
        )
        adder = getattr(target, "add_status", None)
        if callable(adder):
            adder(poison)
        try:
            ctx.game.ui_log(f"{self._event_label()}: {result.outcome}, stage {stage}.")
        except Exception:
            pass
        return EventResult(success=True, consumed_action=self.consumes_action, message="Trucizna nałożona.")

    def _event_label(self) -> str:
        return getattr(self, "name", "poison").replace("_", " ").title()

    def _pick_target(self, ctx: EventContext, actor_pos: tuple[int, int]):
        board = ctx.game.board
        candidates: list[tuple[object, tuple[int, int]]] = []
        for pos in board.get_neighbors(actor_pos, include_position=True, diagonal=True):
            occ = board.occupant_at(pos)
            if occ is None:
                continue
            if occ in getattr(ctx.game, "heroes", []) or occ in getattr(ctx.game, "enemies", []):
                candidates.append((occ, pos))

        if not candidates:
            return None, None
        if len(candidates) == 1:
            return candidates[0]

        positions = [pos for _obj, pos in candidates]
        try:
            ctx.game.conn.set_leds(positions, consts.INTERACT_FIELD_RGB)
            choice = ctx.game.conn.scan_board(positions)
        finally:
            try:
                ctx.game.conn.leds_off()
            except Exception:
                pass
        for obj, pos in candidates:
            if pos == choice:
                return obj, pos
        return None, None


__all__ = ["BasePoisonEvent"]
