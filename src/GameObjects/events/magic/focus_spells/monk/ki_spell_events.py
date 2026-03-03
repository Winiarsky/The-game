from __future__ import annotations

from statuses import Status

from ....base import EventContext, EventResult
from ....move_event import MoveEvent
from ....registry import dispatch_event, register_event
from ....step_event import StepEvent
from ...focus_utils import focus_spell_rank
from ...magic_event import MagicEvent
from ...spell_types import SpellTradition


def _is_monk(actor) -> bool:
    if actor is None:
        return False
    has_status = getattr(actor, "has_status", None)
    if callable(has_status):
        try:
            if bool(has_status("monk")):
                return True
        except Exception:
            pass
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) == "monk":
            return True
    class_name = str(getattr(actor, "class_name", "") or "").strip().lower()
    return class_name == "monk"


def _has_status(actor, status_id: str) -> bool:
    if actor is None:
        return False
    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            return bool(checker(status_id))
        except Exception:
            return False
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", status) == status_id:
            return True
    return False


def _focus_points(actor) -> int:
    raw = getattr(actor, "focus_point", None)
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


def _prompt_choice(ctx: EventContext, prompt: str, choices: list[str], *, source: str) -> str | None:
    ui = getattr(ctx.game, "ui", None)
    answer = None
    if ui is not None and hasattr(ui, "prompt_choice"):
        try:
            answer = ui.prompt_choice(prompt, choices=choices, source=source)
        except Exception:
            answer = None
    if answer is None:
        if ui is not None and not getattr(ui, "allow_cli_fallback", False):
            return None
        try:
            answer = input(f"{prompt} {choices}: ").strip() or None
        except Exception:
            answer = None
    if answer is None:
        return None
    raw = str(answer).strip()
    if not raw:
        return None
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(choices):
            return choices[idx]
    for item in choices:
        if raw.lower() == item.lower():
            return item
    return None


class MonkFocusSpellEvent(MagicEvent):
    actions_cost = 1
    default_tags = ["magic", "spell", "focus", "monk"]
    spell_tags = ["focus", "occult", "monk"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["focus"]

    required_feat_status: str = ""

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message=f"{self.name}: missing actor.")
        if not _is_monk(actor):
            return EventResult.cancelled(message=f"{self.name}: only Monk can cast this focus spell.")
        if self.required_feat_status and not _has_status(actor, self.required_feat_status):
            return EventResult.cancelled(message=f"{self.name}: wymaga featu {self.required_feat_status}.")

        points = _focus_points(actor)
        if points <= 0:
            return EventResult.cancelled(message=f"{self.name}: no Focus Point.")

        result = self._execute_effect(ctx)
        if not result.success:
            return result

        _set_focus_points(actor, points - 1)
        base_msg = str(result.message or f"{self.name}: effect applied.")
        result.message = f"{base_msg} Focus Point: {_focus_points(actor)}."
        return result

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        raise NotImplementedError


@register_event
class KiRushEvent(MonkFocusSpellEvent):
    name = "ki_rush"
    required_feat_status = "ki_rush"
    default_tags = MonkFocusSpellEvent.default_tags + ["transmutation", "move", "concentrate"]
    spell_tags = MonkFocusSpellEvent.spell_tags + ["transmutation"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        sequence_labels = ["Stride + Stride", "Step + Step", "Stride + Step", "Step + Stride"]
        selected = _prompt_choice(
            ctx,
            "Ki Rush: wybierz sekwencje ruchu",
            sequence_labels,
            source=self.name,
        ) or sequence_labels[0]

        move_map = {
            "Stride + Stride": ("stride", "stride"),
            "Step + Step": ("step", "step"),
            "Stride + Step": ("stride", "step"),
            "Step + Stride": ("step", "stride"),
        }
        sequence = move_map.get(selected, ("stride", "stride"))

        runner_stride = MoveEvent()
        runner_step = StepEvent()
        for idx, kind in enumerate(sequence, start=1):
            if kind == "step":
                result = runner_step.execute(EventContext(game=ctx.game, actor=actor, metadata=dict(ctx.metadata or {})))
            else:
                result = runner_stride.execute(EventContext(game=ctx.game, actor=actor, metadata=dict(ctx.metadata or {})))
            if not result.success:
                return EventResult.cancelled(message=f"Ki Rush: ruch #{idx} nieudany ({result.message or kind}).")

        adder = getattr(actor, "add_status", None)
        if callable(adder):
            adder(
                Status(
                    id="concealed",
                    label="Concealed",
                    duration=1,
                    source=self.name,
                    data={"effect_tags": ["concealment"]},
                )
            )

        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=1,
            message="Ki Rush: wykonano 2 ruchy, otrzymujesz concealed do początku następnej tury.",
        )


@register_event
class KiStrikeEvent(MonkFocusSpellEvent):
    name = "ki_strike"
    required_feat_status = "ki_strike"
    default_tags = MonkFocusSpellEvent.default_tags + ["transmutation", "attack"]
    spell_tags = MonkFocusSpellEvent.spell_tags + ["transmutation"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        getter = getattr(actor, "get_status_data", None)
        if callable(getter):
            damage_types = list(getter("ki_strike", "ki_strike_damage_type_choices", []))
        else:
            damage_types = []
        if not damage_types:
            damage_types = ["force", "lawful", "negative", "positive"]

        chosen_damage_type = _prompt_choice(
            ctx,
            "Ki Strike: wybierz typ dodatkowych obrażeń",
            [str(choice) for choice in damage_types],
            source=self.name,
        ) or str(damage_types[0])

        strike_mode = _prompt_choice(
            ctx,
            "Ki Strike: wybierz tryb ataku",
            ["Unarmed Strike", "Flurry of Blows"],
            source=self.name,
        ) or "Unarmed Strike"

        rank = max(1, int(focus_spell_rank(actor, minimum=1) or 1))
        extra_dice = 1 + max(0, (rank - 1) // 4)
        extra_formula = f"{extra_dice}k6"

        metadata = dict(ctx.metadata or {})
        metadata.update(
            {
                "ki_strike_attack_bonus": 1,
                "ki_strike_extra_formula": extra_formula,
                "ki_strike_extra_damage_type": str(chosen_damage_type),
            }
        )

        event_name = "flurry_of_blows" if "flurry" in strike_mode.lower() else "unarmed"
        strike_result = dispatch_event(
            event_name,
            EventContext(
                game=ctx.game,
                actor=actor,
                tags=list(ctx.tags or []),
                metadata=metadata,
            ),
        )
        if not strike_result.success:
            return EventResult.cancelled(message=strike_result.message or "Ki Strike: atak nieudany.")

        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=1,
            message=(
                f"Ki Strike: {event_name} z +1 status do ataku i dodatkowym {extra_formula} "
                f"{chosen_damage_type}."
            ),
            data=dict(strike_result.data or {}),
        )
