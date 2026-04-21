from __future__ import annotations

from enemy_prompting import enemy_prompt_step

from combat.hero_side_targets import hero_side_targets

from ..base import ActionCostEvent, EventContext, EventResult
from ..registry import register_event
from .enemy_strike_event import apply_goblin_pox, goblin_pox_description


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
        hero_targets = list(hero_side_targets(ctx.game, only_living=True))
        enemy_targets = [
            enemy
            for enemy in list(getattr(ctx.game, "enemies", []) or [])
            if getattr(enemy, "position", None) is not None and int(getattr(enemy, "hp", 1) or 0) > 0
        ]
        valid_targets = list(hero_targets) + list(enemy_targets)
        affected = []
        for pos in board.get_neighbors(getattr(actor, "position", None), include_position=False, diagonal=True):
            target = board.occupant_at(pos)
            if target is None:
                continue
            if target not in valid_targets:
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
        try:
            enemy_prompt_step(
                ctx.game,
                f"Efekt choroby: {getattr(actor, 'name', 'Goblin Dog')}",
                prompt_long=(
                    f"Scratch rozprzestrzenia goblin pox.\n"
                    f"Zarażeni: {names}\n\n"
                    f"{goblin_pox_description()}\n\n"
                    "Nałóż efekt na planszy i potwierdź Enterem."
                ),
                source="goblin_dog_scratch_result",
                log_message=message,
            )
        except Exception:
            pass
        ui_actor_snapshot = getattr(ctx.game, "ui_actor_snapshot", None)
        if callable(ui_actor_snapshot):
            for target in affected:
                try:
                    ui_actor_snapshot(target, note="Goblin pox")
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
