from __future__ import annotations

from board import consts
from skills import Skill
from GameObjects.interactions_mixin import resolve_skill_check_with_sources

from .base import ActionCostEvent, EventContext, EventResult
from .registry import register_event


def _is_trap_like(obj) -> bool:
    if obj is None:
        return False
    return bool(
        hasattr(obj, "trap_armed")
        and callable(getattr(obj, "detect_trap", None))
        and callable(getattr(obj, "disable_trap", None))
    )


def _iter_traps(ctx: EventContext, *, detected_only: bool, armed_only: bool) -> list[tuple[object, tuple[int, int]]]:
    board = getattr(ctx.game, "board", None)
    if board is None:
        return []
    rows = int(getattr(board, "rows", 0) or 0)
    cols = int(getattr(board, "cols", 0) or 0)
    out: list[tuple[object, tuple[int, int]]] = []
    seen: set[int] = set()
    for row in range(rows):
        for col in range(cols):
            pos = (col, row)
            try:
                interactables = list(board.interactables_at(pos))
            except Exception:
                continue
            for obj in interactables:
                if id(obj) in seen:
                    continue
                seen.add(id(obj))
                if not _is_trap_like(obj):
                    continue
                if armed_only and not bool(getattr(obj, "trap_armed", False)):
                    continue
                if detected_only and not bool(getattr(obj, "trap_detected", False)):
                    continue
                out.append((obj, pos))
    return out


def _pick_trap(ctx: EventContext, candidates: list[tuple[object, tuple[int, int]]]):
    if not candidates:
        return None, None
    if len(candidates) == 1:
        return candidates[0]
    positions = [pos for _trap, pos in candidates]
    while True:
        try:
            try:
                ctx.game.conn.set_leds(positions, consts.INTERACT_FIELD_RGB)
            except Exception:
                pass
            selected = ctx.game.conn.scan_board(positions)
        finally:
            try:
                ctx.game.conn.leds_off()
            except Exception:
                pass
        if selected is None:
            return None, None
        for trap, pos in candidates:
            if pos == selected:
                return trap, pos
        try:
            ctx.game.ui_log("Wybierz jedno z podświetlonych pól pułapek.")
        except Exception:
            pass


def _trap_name(trap) -> str:
    name = str(getattr(trap, "trap_name", "") or "").strip()
    if name:
        return name
    return "Pułapka"


def _trap_identify_dc(trap) -> int:
    getter = getattr(trap, "_effective_identify_dc", None)
    if callable(getter):
        try:
            return int(getter())
        except Exception:
            pass
    return int(getattr(trap, "trap_identify_dc", None) or getattr(trap, "trap_disable_dc", 18) or 18)


def _trap_disable_dc(trap) -> int:
    try:
        return int(getattr(trap, "trap_disable_dc", 18) or 18)
    except Exception:
        return 18


def _resolve_trap_by_metadata(ctx: EventContext, candidates, metadata):
    forced_target = metadata.get("forced_target")
    if forced_target is not None:
        for trap, pos in candidates:
            if trap is forced_target:
                return trap, pos
    forced_pos = metadata.get("forced_target_pos")
    if isinstance(forced_pos, tuple) and len(forced_pos) == 2:
        for trap, pos in candidates:
            if tuple(pos) == tuple(forced_pos):
                return trap, pos
    return None, None


@register_event
class IdentifyTrapEvent(ActionCostEvent):
    name = "identify_trap"
    default_tags = ["trap", "identify", "skill", "thievery", "manipulate"]
    actions_cost = 1
    consumes_action = True
    available_in_combat = True
    available_in_exploration = True

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Identify Trap: brak aktora.")
        candidates = _iter_traps(ctx, detected_only=True, armed_only=True)
        if not candidates:
            return EventResult.cancelled(message="Identify Trap: brak wykrytych aktywnych pułapek.")
        metadata = dict(ctx.metadata or {})
        trap, target_pos = _resolve_trap_by_metadata(ctx, candidates, metadata)
        if trap is None:
            trap, target_pos = _pick_trap(ctx, candidates)
        if trap is None:
            return EventResult.cancelled(message="Identify Trap: anulowano wybór pułapki.")

        dc = _trap_identify_dc(trap)
        result = resolve_skill_check_with_sources(
            skill_id=Skill.THIEVERY.value,
            dc=dc,
            actor=actor,
            target=trap,
            tags=["trap", "identify", Skill.THIEVERY.value],
            game=ctx.game,
            apply_modifiers=True,
        )
        outcome, details = trap.identify_trap(int(getattr(result, "total", 0) or 0))
        try:
            ctx.game.ui_event("info", {"text": details, "source": "identify_trap"})
        except Exception:
            pass
        try:
            ctx.game.events.safe_emit_action(
                actor=actor,
                action_id=self.name,
                action_tags=self._effective_tags(ctx),
                target=trap,
                target_pos=target_pos,
                outcome=outcome,
                dc=dc,
                roll=int(getattr(result, "roll", 0) or 0),
                total=int(getattr(result, "total", 0) or 0),
            )
        except Exception:
            pass
        return EventResult(
            success=True,
            consumed_action=self.consumes_action,
            actions_spent=1,
            message=f"Identify Trap ({_trap_name(trap)}): {outcome}.",
            data={
                "trap": trap,
                "target_pos": target_pos,
                "outcome": outcome,
                "details": details,
                "dc": dc,
                "roll": int(getattr(result, "roll", 0) or 0),
                "total": int(getattr(result, "total", 0) or 0),
            },
        )


@register_event
class DisableDeviceEvent(ActionCostEvent):
    name = "disable_device"
    default_tags = ["trap", "disable", "skill", "thievery", "manipulate"]
    actions_cost = 2
    consumes_action = True
    available_in_combat = True
    available_in_exploration = True

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Disable Device: brak aktora.")
        candidates = _iter_traps(ctx, detected_only=True, armed_only=True)
        if not candidates:
            return EventResult.cancelled(message="Disable Device: brak wykrytych aktywnych pułapek.")
        metadata = dict(ctx.metadata or {})
        trap, target_pos = _resolve_trap_by_metadata(ctx, candidates, metadata)
        if trap is None:
            trap, target_pos = _pick_trap(ctx, candidates)
        if trap is None:
            return EventResult.cancelled(message="Disable Device: anulowano wybór pułapki.")

        dc = _trap_disable_dc(trap)
        result = resolve_skill_check_with_sources(
            skill_id=Skill.THIEVERY.value,
            dc=dc,
            actor=actor,
            target=trap,
            tags=["trap", "disable", Skill.THIEVERY.value],
            game=ctx.game,
            apply_modifiers=True,
        )
        outcome, details = trap.disable_trap(int(getattr(result, "total", 0) or 0), actor=actor, game=ctx.game)
        try:
            ctx.game.events.safe_emit_action(
                actor=actor,
                action_id=self.name,
                action_tags=self._effective_tags(ctx),
                target=trap,
                target_pos=target_pos,
                outcome=outcome,
                dc=dc,
                roll=int(getattr(result, "roll", 0) or 0),
                total=int(getattr(result, "total", 0) or 0),
            )
        except Exception:
            pass
        return EventResult(
            success=True,
            consumed_action=self.consumes_action,
            actions_spent=2,
            message=f"Disable Device ({_trap_name(trap)}): {details}",
            data={
                "trap": trap,
                "target_pos": target_pos,
                "outcome": outcome,
                "details": details,
                "dc": dc,
                "roll": int(getattr(result, "roll", 0) or 0),
                "total": int(getattr(result, "total", 0) or 0),
            },
        )

