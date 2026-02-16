from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from bonuses import BonusEffect, aggregate_best_by_type, compute_total_modifier
from statuses import Status
from statuses.check_effects import CheckEffect
from GameObjects.interactions_mixin import resolve_skill_check
from ui_client import get_ui_client
from bonuses import BonusType

logger = logging.getLogger(__name__)


OUTCOME_ORDER = ["critical_failure", "failure", "success", "critical_success"]


def prompt_for_roll(prompt: str, **ui_kwargs) -> int:
    """Lokalny wrapper na prompt w testach (ułatwia monkeypatch get_ui_client)."""
    ui_client = get_ui_client()
    if ui_client is not None and hasattr(ui_client, "prompt_roll") and getattr(ui_client, "enabled", True):
        if "layout" not in ui_kwargs:
            ui_kwargs["layout"] = "test"
        ui_kwargs.setdefault("answer_placeholder", "Podaj wynik rzutu")
        ui_kwargs.setdefault("source", "game")
        ui_answer = ui_client.prompt_roll(prompt, **ui_kwargs)
        if isinstance(ui_answer, int):
            return ui_answer
    while True:
        raw = input(prompt).strip()
        if not raw:
            continue
        try:
            return int(raw)
        except ValueError:
            continue


@dataclass
class SkillCheckResolution:
    outcome: str
    roll: int
    modifier: int
    total: int
    dc: int
    notes: list[str]
    breakdown: list[str]


def _status_list(obj) -> list[Status]:
    statuses = getattr(obj, "statuses", None)
    if not statuses:
        return []
    result: list[Status] = []
    for s in statuses:
        if isinstance(s, Status):
            result.append(s)
        else:
            # string -> goła definicja bez efektów
            result.append(Status(id=str(s)))
    return result


def _collect_from_statuses(statuses: Iterable[Status], skill_id: str, tags: Sequence[str], applies_to: str):
    bonus_effects: list[BonusEffect] = []
    promote_rules: list[tuple[int, Optional[set[str]]]] = []
    demote_rules: list[tuple[int, Optional[set[str]]]] = []
    notes: list[str] = []
    consume_statuses: list[Status] = []
    for status in statuses:
        effects: Optional[Sequence[CheckEffect]] = getattr(status, "check_effects", None)
        if not effects:
            continue
        for effect in effects:
            if effect.applies_to != applies_to:
                continue
            if not effect.matches(skill_id, tags):
                continue
            if getattr(status, "data", None) and status.data.get("consume_on_use"):
                consume_statuses.append(status)
            bonus_effects.extend(effect.bonus_effects)
            if effect.promote:
                promote_rules.append((int(effect.promote), set(effect.promote_on) if effect.promote_on else None))
            if effect.demote:
                demote_rules.append((int(effect.demote), set(effect.demote_on) if effect.demote_on else None))
            notes.extend(effect.prompt_notes)
    return bonus_effects, promote_rules, demote_rules, notes, consume_statuses


def _format_breakdown(effects: Iterable[BonusEffect], skill_id: str) -> list[str]:
    lines: list[str] = []
    aggregated = aggregate_best_by_type(effects, skill_id)
    for btype, data in aggregated.items():
        bonus_val = data["bonus"]
        penalty_val = data["penalty"]
        bonuses: Iterable[BonusEffect] = data["bonuses"]  # type: ignore[assignment]
        penalties: Iterable[BonusEffect] = data["penalties"]  # type: ignore[assignment]

        if bonus_val:
            src = next((eff.label or eff.source for eff in bonuses if eff.value == bonus_val), btype.value)
            lines.append(f"+{bonus_val} {btype.value} ({src})")
        if penalty_val:
            src = next((eff.label or eff.source for eff in penalties if abs(eff.value) == penalty_val), btype.value)
            lines.append(f"-{penalty_val} {btype.value} ({src})")
    return lines


def _apply_shift(outcome: str, shift: int) -> str:
    idx = OUTCOME_ORDER.index(outcome)
    new_idx = max(0, min(len(OUTCOME_ORDER) - 1, idx + shift))
    return OUTCOME_ORDER[new_idx]


def resolve_skill_check_with_sources(
    *,
    skill_id: str,
    dc: int,
    actor,
    tags: Sequence[str],
    target=None,
    game=None,
    base_modifier: int = 0,
    apply_modifiers: bool = False,
) -> SkillCheckResolution:
    """Policz wynik testu umiejętności z bonusami i efektami statusów."""

    tags = list(tags)

    # bonusy z aktora
    all_effects: list[BonusEffect] = []
    bonuses = getattr(actor, "bonuses", None)
    if isinstance(bonuses, list):
        all_effects.extend(bonuses)

    # statusy source / target
    src_effects, promote_src, demote_src, notes_src, consume_src = _collect_from_statuses(_status_list(actor), skill_id, tags, "source")
    all_effects.extend(src_effects)
    tgt_effects, promote_tgt, demote_tgt, notes_tgt, consume_tgt = _collect_from_statuses(_status_list(target), skill_id, tags, "target") if target else ([], [], [], [], [])
    all_effects.extend(tgt_effects)

    modifier = base_modifier + (compute_total_modifier(all_effects, skill_id) if all_effects else 0)
    breakdown = _format_breakdown(all_effects, skill_id)
    notes = list(notes_src) + list(notes_tgt)

    prompt_msg = f"Test {skill_id} (DC {dc})."
    prompt_long = (
        (
            "Podaj wynik rzutu (bez premii sytuacyjnych). "
            if apply_modifiers
            else "Podaj końcowy wynik (uwzględnij swoje premie/kary). "
        )
        + f"Premie/kary: {', '.join(breakdown) if breakdown else 'brak'} (suma {modifier:+d}, "
        + ("doliczana automatycznie)." if apply_modifiers else "nie jest doliczana automatycznie).")
    )
    modifiers_grid = _build_modifiers_grid(all_effects)
    roll = prompt_for_roll(
        prompt_msg,
        layout="test",
        prompt_long=prompt_long,
        answer_placeholder="Wynik rzutu",
        modifiers=modifiers_grid,
    )
    total = roll + modifier if apply_modifiers else roll
    outcome = resolve_skill_check(dc, total)

    # przesunięcia sukcesu
    # zastosuj przesunięcia warunkowe w kolejności: src-promote, tgt-promote, src-demote, tgt-demote
    for value, cond in list(promote_src) + list(promote_tgt):
        if cond is None or outcome in cond:
            outcome = _apply_shift(outcome, value)
    for value, cond in list(demote_src) + list(demote_tgt):
        if cond is None or outcome in cond:
            outcome = _apply_shift(outcome, -value)

    resolution = SkillCheckResolution(
        outcome=outcome,
        roll=roll,
        modifier=modifier,
        total=total,
        dc=dc,
        notes=notes,
        breakdown=breakdown,
    )

    # zużyj statusy jednorazowe, jeśli zostały użyte w tym teście
    try:
        if consume_src:
            remover = getattr(actor, "remove_status", None)
            if callable(remover):
                for s in consume_src:
                    remover(s)
        if consume_tgt and target is not None:
            remover = getattr(target, "remove_status", None)
            if callable(remover):
                for s in consume_tgt:
                    remover(s)
    except Exception:
        pass

    try:
        if game and hasattr(game, "ui_log"):
            game.ui_log(
                f"{skill_id}: {outcome} (r={roll}, mod={modifier:+d}, suma={total} vs DC {dc}). "
                f"{' | '.join(notes) if notes else ''}"
            )
    except Exception:
        pass

    return resolution


def _build_modifiers_grid(effects: list) -> dict:
    """Przygotuj dane do sekcji premii/kar w UI."""
    buckets = {
        "penCirc": [],
        "bonCirc": [],
        "penStat": [],
        "bonStat": [],
    }
    for eff in effects:
        value = getattr(eff, "value", 0) or 0
        label = getattr(eff, "label", None) or getattr(eff, "tag", None) or getattr(eff, "source", "") or "mod"
        btype = getattr(eff, "type", None)
        is_penalty = value < 0
        if btype == BonusType.CIRCUMSTANCE:
            key = "penCirc" if is_penalty else "bonCirc"
        elif btype == BonusType.STATUS:
            key = "penStat" if is_penalty else "bonStat"
        else:
            key = "penCirc" if is_penalty else "bonCirc"
        buckets[key].append({"label": label, "value": value})
    for key, arr in buckets.items():
        arr.sort(key=lambda x: abs(x.get("value", 0)), reverse=True)
    return buckets
