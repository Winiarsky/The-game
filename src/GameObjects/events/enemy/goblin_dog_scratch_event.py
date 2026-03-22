from __future__ import annotations

from ..base import ActionCostEvent, EventContext, EventResult
from ..registry import register_event
from .enemy_strike_event import apply_goblin_pox


@register_event
class GoblinDogScratchEvent(ActionCostEvent):
    name = "goblin_dog_scratch"
    default_tags = ["enemy", "manipulate", "disease"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True
    actions_cost = 2

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Scratch: gobliński pies nie stoi na planszy.")

        board = ctx.game.board
        affected = []
        for pos in board.get_neighbors(getattr(actor, "position", None), include_position=False, diagonal=True):
            target = board.occupant_at(pos)
            if target is None:
                continue
            if target not in (list(getattr(ctx.game, "heroes", []) or []) + list(getattr(ctx.game, "enemies", []) or [])):
                continue
            if apply_goblin_pox(target):
                affected.append(target)

        if not affected:
            return EventResult.cancelled(message="Scratch: brak sąsiadujących celów podatnych na goblin pox.")

        names = ", ".join(str(getattr(target, "name", "cel")) for target in affected)
        message = f"{getattr(actor, 'name', 'Goblin Dog')} używa Scratch. Zarażeni: {names}."
        try:
            ctx.game.ui_log(message)
        except Exception:
            pass
        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=2,
            message=message,
            data={"affected_targets": affected},
        )


__all__ = ["GoblinDogScratchEvent"]
