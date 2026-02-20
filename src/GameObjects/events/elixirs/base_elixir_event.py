from __future__ import annotations

import logging
from typing import Iterable
from dataclasses import replace

from board import consts
from bonuses import BonusEffect, BonusType
from damage_types import DamageType
from statuses import Status
from statuses.check_effects import CheckEffect

from ..base import ActionCostEvent, EventContext, EventResult

logger = logging.getLogger(__name__)

TURNS_PER_MINUTE = 10


def _minutes(minutes: int) -> int:
    return max(0, int(minutes) * TURNS_PER_MINUTE)


def _hours(hours: int) -> int:
    return _minutes(int(hours) * 60)


def _parse_dice(dice: str) -> tuple[int, int, int]:
    raw = str(dice or "").lower().replace(" ", "")
    if "d" not in raw:
        return 0, 0, 0
    count_part, rest = raw.split("d", 1)
    count = int(count_part or 0)
    bonus = 0
    sides_part = rest
    if "+" in rest:
        sides_part, bonus_part = rest.split("+", 1)
        try:
            bonus = int(bonus_part)
        except Exception:
            bonus = 0
    try:
        sides = int(sides_part or 0)
    except Exception:
        sides = 0
    return count, sides, bonus


def _avg_dice(dice: str) -> int:
    count, sides, bonus = _parse_dice(dice)
    if count <= 0 or sides <= 0:
        return int(bonus)
    avg = count * (sides + 1) / 2.0 + bonus
    return int(avg)


def _is_undead(target) -> bool:
    if target is None:
        return False
    has_tag = getattr(target, "has_tag", None)
    if callable(has_tag):
        try:
            return bool(has_tag("undead"))
        except Exception:
            return False
    tags = getattr(target, "tags", None) or []
    return "undead" in tags


class BaseElixirEvent(ActionCostEvent):
    """Wspólna logika dla eliksirów (wypicie/napojenie)."""

    actions_cost = 1
    default_tags = ["elixir", "alchemical", "manipulate"]
    available_in_combat = True
    available_in_exploration = True
    consumes_action = True

    prompt_description: str | None = None
    tier_choices: tuple[str, ...] = ("lesser", "moderate", "greater", "major")
    tiers: dict[str, dict[str, object]] = {}

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do użycia eliksiru.")
        actor_pos = getattr(actor, "position", None)
        if actor_pos is None:
            return EventResult.cancelled(message="Bohater nie stoi na planszy.")

        tier = self._prompt_level()
        if not tier:
            return EventResult.cancelled(message="Nie wybrano poziomu eliksiru.")
        tier_data = self.tiers.get(tier)
        if not tier_data:
            return EventResult.cancelled(message="Niepoprawny poziom eliksiru.")

        target, target_pos = self._pick_target(ctx, actor_pos)
        if target is None or target_pos is None:
            return EventResult.cancelled(message="Brak celu w zasięgu.")

        self._apply_elixir(ctx, target, tier, tier_data)
        self._record_mutagen_consumption(target, tier)
        return EventResult(success=True, consumed_action=self.consumes_action, message=f"Użyto eliksiru ({tier}).")

    def _prompt_level(self) -> str | None:
        from ui_client import get_ui_client

        ui = get_ui_client()
        if self.prompt_description:
            try:
                ui.prompt_info(self._event_label(), prompt_long=self.prompt_description, source=self.name)
            except Exception:
                pass
        choice = ui.prompt_choice(
            f"Wybierz poziom {self._event_label()}:",
            choices=list(self.tier_choices),
            source=self.name,
        )
        if choice is None:
            return None
        raw = str(choice).strip().lower()
        if raw in self.tiers:
            return raw
        for option in self.tier_choices:
            if raw.startswith(option[0]):
                return option
        return None

    def _event_label(self) -> str:
        return getattr(self, "name", "elixir").replace("_", " ").title()

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

    def _prompt_value(self, title: str, *, dice: str, source: str) -> int:
        from ui_client import get_ui_client

        ui = get_ui_client()
        val = ui.prompt_roll(
            f"{title} – podaj wartość ({dice}):",
            source=source,
            layout="damage",
            answer_placeholder="Wartość",
        )
        try:
            return int(val or 0)
        except Exception:
            return 0

    def _heal_amount(self, ctx: EventContext, target, dice: str) -> int:
        if target in getattr(ctx.game, "enemies", []):
            return _avg_dice(dice)
        if target in getattr(ctx.game, "heroes", []):
            return self._prompt_value(self._event_label(), dice=dice, source=self.name)
        return self._prompt_value(self._event_label(), dice=dice, source=self.name)

    def _apply_heal_or_harm(self, target, amount: int) -> None:
        if amount <= 0:
            return
        if _is_undead(target):
            apply = getattr(target, "apply_damage", None)
            if callable(apply):
                apply(amount, DamageType.POSITIVE.value)
            return
        healer = getattr(target, "heal", None)
        if callable(healer):
            healer(amount)

    def _add_bonus(self, target, effect: BonusEffect) -> None:
        adder = getattr(target, "add_bonus", None)
        if callable(adder):
            try:
                adder(effect)
            except Exception:
                pass

    def _apply_elixir(self, ctx: EventContext, target, tier: str, tier_data: dict[str, object]) -> None:
        raise NotImplementedError

    def _is_mutagen(self) -> bool:
        tags = self.default_tags or []
        return "mutagen" in tags

    def _get_status(self, target, status_id: str):
        getter = getattr(target, "get_status", None)
        if callable(getter):
            try:
                return getter(status_id)
            except Exception:
                return None
        for status in getattr(target, "statuses", []) or []:
            if getattr(status, "id", None) == status_id:
                return status
        return None

    def _replace_status_data(self, target, status_id: str, new_data: dict) -> bool:
        statuses = getattr(target, "statuses", None)
        if not isinstance(statuses, list):
            return False
        for idx, status in enumerate(statuses):
            if getattr(status, "id", None) == status_id:
                try:
                    statuses[idx] = replace(status, data=new_data)
                    return True
                except Exception:
                    return False
        return False

    def _record_mutagen_consumption(self, target, tier: str) -> None:
        if not self._is_mutagen():
            return
        status = self._get_status(target, "alchemist_research_field")
        if status is None:
            return
        data = getattr(status, "data", None) or {}
        if data.get("research_field") != "mutagenist":
            return
        consumed = list(data.get("mutagen_consumed", []) or [])
        entry = {"name": self.name, "tier": str(tier)}
        if entry not in consumed:
            consumed.append(entry)
        new_data = dict(data)
        new_data["mutagen_consumed"] = consumed
        self._replace_status_data(target, "alchemist_research_field", new_data)


def make_bonus_status(
    *,
    status_id: str,
    label: str,
    duration: int | None,
    effects: Iterable[CheckEffect],
    data: dict[str, object] | None = None,
) -> Status:
    return Status(
        id=status_id,
        label=label,
        duration=duration,
        data=data or {},
        check_effects=list(effects),
    )


def skill_bonus_effect(
    *,
    skill_id: str,
    bonus: int,
    bonus_type: BonusType,
    source: str,
    label: str,
    is_penalty: bool = False,
) -> BonusEffect:
    return BonusEffect(
        type=bonus_type,
        value=abs(int(bonus)),
        tag=skill_id,
        source=source,
        label=label,
        is_penalty=is_penalty,
    )


def skill_check_effect(
    *,
    applies_to: str,
    skills: Iterable[str],
    tags_required: Iterable[str] | None,
    bonus_effects: Iterable[BonusEffect],
    promote: int = 0,
    promote_on: Iterable[str] | None = None,
    demote: int = 0,
    demote_on: Iterable[str] | None = None,
    prompt_notes: Iterable[str] | None = None,
) -> CheckEffect:
    return CheckEffect(
        applies_to=applies_to,
        skills=list(skills),
        tags_required=list(tags_required) if tags_required else None,
        bonus_effects=list(bonus_effects),
        promote=promote,
        promote_on=list(promote_on) if promote_on else None,
        demote=demote,
        demote_on=list(demote_on) if demote_on else None,
        prompt_notes=list(prompt_notes or []),
    )


__all__ = [
    "BaseElixirEvent",
    "TURNS_PER_MINUTE",
    "_minutes",
    "_hours",
    "_avg_dice",
    "_is_undead",
    "make_bonus_status",
    "skill_bonus_effect",
    "skill_check_effect",
]
