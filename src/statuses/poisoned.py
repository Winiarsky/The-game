from __future__ import annotations

from typing import Optional, Sequence
import random

from damage_types import DamageType
from skills import Skill
from statuses.base import Status
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources


def PoisonedStatus(
    *,
    duration: int,
    damage: int,
    dc: int,
    source: str | None = None,
    stages: Sequence[dict[str, object]] | None = None,
    stage: int | None = None,
    onset: int | None = None,
) -> Status:
    """Status: Poisoned (czasowy, z testem Fortitude co turę, opcjonalne stage'e)."""
    return Status(
        id="poisoned",
        label="Poisoned",
        duration=int(duration),
        source=source,
        data={
            "dc": int(dc),
            "damage": int(damage),
            "damage_type": DamageType.POISON.value,
            "stages": list(stages) if stages else None,
            "stage": int(stage) if stage is not None else None,
            "onset": int(onset) if onset is not None else None,
        },
    )


def _poison_damage_for_outcome(base_damage: int, outcome: str) -> int:
    if outcome == "critical_success":
        return 0
    if outcome == "success":
        return max(0, int(base_damage) // 2)
    if outcome == "critical_failure":
        return max(0, int(base_damage) * 2)
    return max(0, int(base_damage))


def _shift_stage(current: int, delta: int, max_stage: int) -> int:
    return max(0, min(max_stage, current + delta))


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


def _roll_dice(dice: str) -> int:
    count, sides, bonus = _parse_dice(dice)
    if count <= 0 or sides <= 0:
        return int(bonus)
    total = 0
    for _ in range(count):
        total += random.randint(1, sides)
    total += int(bonus)
    return int(total)


def _stage_effects(stage_data: dict[str, object], actor=None, game=None) -> tuple[int, list[str], str | None]:
    damage = 0
    tags: list[str] = []
    note = None
    if not stage_data:
        return damage, tags, note
    try:
        dice = stage_data.get("dice")
        if dice:
            from ui_client import get_ui_client

            ui = get_ui_client()
            if game is not None and actor in getattr(game, "heroes", []):
                if ui is not None and getattr(ui, "enabled", False):
                    dmg = ui.prompt_roll(
                        f"Poisoned – podaj obrażenia ({dice}):",
                        source="poisoned",
                        layout="damage",
                        answer_placeholder="Obrażenia",
                    )
                    damage = int(dmg or 0)
                else:
                    damage = _avg_dice(str(dice))
            else:
                damage = _roll_dice(str(dice))
        else:
            damage = int(stage_data.get("damage", 0) or 0)
    except Exception:
        damage = 0
    try:
        extra_tags = stage_data.get("tags") or []
        tags.extend([str(t) for t in extra_tags if t])
    except Exception:
        pass
    try:
        note = stage_data.get("note")
        if note:
            note = str(note)
    except Exception:
        note = None
    return damage, tags, note


def _apply_stage_condition(actor, stage_data: dict[str, object]) -> None:
    condition = stage_data.get("condition")
    if not condition:
        return
    adder = getattr(actor, "add_status", None)
    if not callable(adder):
        return
    try:
        if isinstance(condition, Status):
            adder(condition)
        elif isinstance(condition, str):
            adder(Status(id=condition))
    except Exception:
        pass


def process_poisoned(actor, game) -> None:
    """Obsłuż start tury: rzut obronny vs poison, stage i obrażenia."""
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list) or not statuses:
        return
    for status in list(statuses):
        if getattr(status, "id", None) != "poisoned":
            continue
        data = getattr(status, "data", None) or {}
        try:
            dc = int(data.get("dc"))
        except Exception:
            continue
        damage_type = data.get("damage_type", DamageType.POISON.value)

        stages = data.get("stages") or None
        stage = data.get("stage")
        if stage is None:
            stage = 1 if stages else 0
        try:
            stage = int(stage)
        except Exception:
            stage = 1 if stages else 0

        onset = data.get("onset")
        if onset is not None:
            try:
                onset = int(onset)
            except Exception:
                onset = None

        result = resolve_skill_check_with_sources(
            skill_id=Skill.FORTITUDE.value,
            dc=dc,
            actor=actor,
            target=None,
            tags=["poison", Skill.FORTITUDE.value],
            game=game,
            apply_modifiers=True,
        )

        if onset and onset > 0:
            new_onset = max(0, onset - 1)
            try:
                idx = statuses.index(status)
                data_update = dict(data)
                data_update["onset"] = new_onset
                statuses[idx] = Status(
                    id=status.id,
                    label=status.label,
                    duration=status.duration,
                    source=status.source,
                    stacks=status.stacks,
                    data=data_update,
                    check_effects=status.check_effects,
                )
            except Exception:
                pass
            continue

        if stages:
            max_stage = len(stages)
            delta_map = {
                "critical_success": -2,
                "success": -1,
                "failure": 1,
                "critical_failure": 2,
            }
            stage = _shift_stage(stage, delta_map.get(result.outcome, 0), max_stage)
            if stage <= 0:
                try:
                    remover = getattr(actor, "remove_status", None)
                    if callable(remover):
                        remover("poisoned")
                except Exception:
                    pass
                continue
            stage_data = stages[stage - 1] if 0 < stage <= len(stages) else {}
            damage, extra_tags, note = _stage_effects(stage_data, actor=actor, game=game)
            _apply_stage_condition(actor, stage_data)
        else:
            damage = int(data.get("damage", 0) or 0)
            extra_tags = []
            note = None

        dealt = _poison_damage_for_outcome(damage, result.outcome)
        if dealt:
            apply = getattr(actor, "apply_damage", None)
            if callable(apply):
                apply(dealt, damage_type)
        try:
            if hasattr(game, "ui_log"):
                msg = f"Poisoned: {result.outcome} – obrażenia {dealt} ({damage_type})."
                if note:
                    msg = f"{msg} {note}"
                game.ui_log(msg)
            if hasattr(game, "ui_event"):
                game.ui_event(
                    "info",
                    {"text": f"Poisoned: otrzymujesz {dealt} obrażeń ({damage_type})."},
                )
        except Exception:
            pass

        if stages:
            try:
                idx = statuses.index(status)
                data_update = dict(data)
                data_update["stage"] = stage
                statuses[idx] = Status(
                    id=status.id,
                    label=status.label,
                    duration=status.duration,
                    source=status.source,
                    stacks=status.stacks,
                    data=data_update,
                    check_effects=status.check_effects,
                )
            except Exception:
                pass


__all__ = ["PoisonedStatus", "process_poisoned"]
