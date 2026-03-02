from __future__ import annotations

from bonuses import BonusEffect, BonusType

from .base import ActionCostEvent, EventContext, EventResult
from .registry import register_event
from .magic.magic_utils import grid_distance_feet


def _is_champion(actor) -> bool:
    if actor is None:
        return False
    has_status = getattr(actor, "has_status", None)
    if callable(has_status):
        try:
            if bool(has_status("champion")):
                return True
        except Exception:
            pass
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) == "champion":
            return True
    class_name = str(getattr(actor, "class_name", "") or "").strip().lower()
    return class_name == "champion"


def _focus_points(actor) -> int:
    raw = getattr(actor, "focus_point", None)
    if raw is None and _is_champion(actor):
        try:
            setattr(actor, "focus_point", 1)
        except Exception:
            return 0
        raw = 1
    try:
        return max(0, int(raw or 0))
    except Exception:
        return 0


def _set_focus_points(actor, value: int) -> None:
    points = max(0, int(value))
    try:
        setattr(actor, "focus_point", points)
    except Exception:
        return


def _source_id(actor) -> str | None:
    if actor is None:
        return None
    return getattr(actor, "object_id", None) or getattr(actor, "name", None) or str(actor)


def _apply_heal(target, amount: int) -> None:
    healer = getattr(target, "heal", None)
    if callable(healer):
        try:
            healer(max(0, int(amount)))
            return
        except Exception:
            pass
    try:
        wounds = int(getattr(target, "wounds", 0) or 0)
        setattr(target, "wounds", max(0, wounds - max(0, int(amount))))
    except Exception:
        pass


@register_event
class LayOnHandsEvent(ActionCostEvent):
    name = "lay_on_hands"
    actions_cost = 1
    consumes_action = True
    default_tags = ["magic", "spell", "focus", "champion", "healing", "manipulate"]
    available_in_combat = True
    available_in_exploration = True
    range_feet = 5

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Lay on Hands: brak aktora.")
        if not _is_champion(actor):
            return EventResult.cancelled(message="Lay on Hands: tylko Champion może użyć tej akcji.")

        current_focus = _focus_points(actor)
        if current_focus <= 0:
            return EventResult.cancelled(message="Lay on Hands: brak Focus Point.")

        target = self._pick_target(ctx, actor)
        if target is None:
            return EventResult.cancelled(message="Lay on Hands: brak celu.")

        level = getattr(actor, "level", 1) or 1
        try:
            level = int(level)
        except Exception:
            level = 1
        spell_rank = max(1, (level + 1) // 2)
        heal_amount = 6 * spell_rank

        _set_focus_points(actor, current_focus - 1)
        _apply_heal(target, heal_amount)
        self._apply_ac_bonus(target, source_id=_source_id(actor))

        target_name = getattr(target, "name", None) or getattr(target, "object_id", "cel")
        return EventResult(
            success=True,
            consumed_action=ctx.in_combat,
            actions_spent=1 if ctx.in_combat else None,
            message=(
                f"Lay on Hands: {target_name} leczy {heal_amount} HP i otrzymuje +2 status AC "
                f"na 1 turę. Focus Point: {_focus_points(actor)}."
            ),
        )

    def _pick_target(self, ctx: EventContext, actor):
        source_pos = getattr(actor, "position", None)
        candidates = []
        for hero in getattr(ctx.game, "heroes", []) or []:
            pos = getattr(hero, "position", None)
            if pos is None or source_pos is None:
                continue
            if grid_distance_feet(source_pos, pos) > self.range_feet:
                continue
            candidates.append(hero)
        if actor not in candidates:
            candidates.insert(0, actor)
        if not candidates:
            return actor
        if len(candidates) == 1:
            return candidates[0]

        names = [getattr(hero, "name", None) or getattr(hero, "object_id", f"Hero {idx + 1}") for idx, hero in enumerate(candidates)]
        ui = getattr(ctx.game, "ui", None)
        if ui is not None and hasattr(ui, "prompt_choice"):
            try:
                answer = ui.prompt_choice(
                    "Lay on Hands: wybierz cel leczenia.",
                    choices=names,
                    source=self.name,
                )
                if answer is not None:
                    raw = str(answer).strip()
                    if raw in names:
                        return candidates[names.index(raw)]
            except Exception:
                pass

        positions = [getattr(hero, "position", None) for hero in candidates if getattr(hero, "position", None) is not None]
        if not positions:
            return candidates[0]
        try:
            ctx.game.conn.set_leds(positions, [[60, 150, 255] for _ in positions])
            chosen = ctx.game.conn.scan_board(positions)
        finally:
            try:
                ctx.game.conn.leds_off()
            except Exception:
                pass
        for hero in candidates:
            if getattr(hero, "position", None) == chosen:
                return hero
        return candidates[0]

    @staticmethod
    def _apply_ac_bonus(target, *, source_id: str | None) -> None:
        remover = getattr(target, "remove_bonuses_with_prefix", None)
        if callable(remover):
            try:
                remover("lay_on_hands:")
            except Exception:
                pass
        adder = getattr(target, "add_bonus", None)
        if not callable(adder):
            return
        source = f"lay_on_hands:{source_id}" if source_id else "lay_on_hands"
        adder(
            BonusEffect(
                type=BonusType.STATUS,
                value=2,
                tag="ac",
                source=source,
                label="lay on hands",
                duration_turns=1,
            )
        )
