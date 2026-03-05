from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from bonuses import BonusEffect, BonusType, aggregate_best_by_type, build_modifiers_grid, compute_total_modifier, format_effects_log, select_best_effects
from statuses import Status
from statuses.check_effects import CheckEffect
from GameObjects.interactions_mixin.skill_checks import resolve_skill_check
from ui_client import get_ui_client
from statuses import DARKVISION_STATUS, DIM_LIGHT_VISION_STATUS, IN_DARK_STATUS, IN_DIM_LIGHT_STATUS, LOW_LIGHT_VISION_STATUS
from skills import Skill
from combat.degree_of_success import natural_mode_from_shift, natural_shift_from_mode, natural_shift_from_roll

logger = logging.getLogger(__name__)


OUTCOME_ORDER = ["critical_failure", "failure", "success", "critical_success"]


def _is_hero(obj) -> bool:
    try:
        from hero import Hero

        return isinstance(obj, Hero)
    except Exception:
        return False


def _parse_roll_details(answer, *, infer_natural_from_roll: bool = False) -> dict[str, object]:
    roll = 0
    shift = 0
    if isinstance(answer, dict):
        raw_roll = answer.get("roll", answer.get("value", answer.get("result", 0)))
        try:
            roll = int(raw_roll or 0)
        except Exception:
            roll = 0
        mode = answer.get("natural_mode", answer.get("natural", answer.get("nat", None)))
        shift = natural_shift_from_mode(mode)
        if shift == 0 and infer_natural_from_roll:
            shift = natural_shift_from_roll(roll)
    else:
        try:
            roll = int(answer or 0)
        except Exception:
            roll = 0
        if infer_natural_from_roll:
            shift = natural_shift_from_roll(roll)
    return {
        "roll": int(roll),
        "natural_shift": int(shift),
        "natural_mode": natural_mode_from_shift(shift),
    }


def prompt_for_roll(prompt: str, *, return_details: bool = False, infer_natural_from_roll: bool = False, **ui_kwargs):
    """Lokalny wrapper na prompt w testach (ułatwia monkeypatch get_ui_client)."""
    ui_client = get_ui_client()
    if ui_client is not None and hasattr(ui_client, "prompt_roll") and getattr(ui_client, "enabled", True):
        if "layout" not in ui_kwargs:
            ui_kwargs["layout"] = "test"
        ui_kwargs.setdefault("answer_placeholder", "Podaj wynik rzutu")
        ui_kwargs.setdefault("source", "game")
        ui_answer = ui_client.prompt_roll(prompt, return_meta=bool(return_details), **ui_kwargs)
        details = _parse_roll_details(ui_answer, infer_natural_from_roll=infer_natural_from_roll)
        if return_details:
            return details
        return int(details.get("roll", 0) or 0)
    if ui_client is not None and not getattr(ui_client, "allow_cli_fallback", False):
        raise RuntimeError("UI-only mode: prompt_for_roll wymaga aktywnego UI.")
    while True:
        raw = input(prompt).strip()
        if not raw:
            continue
        try:
            value = int(raw)
            if return_details:
                return _parse_roll_details(value, infer_natural_from_roll=infer_natural_from_roll)
            return value
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


def _has_status(obj, status) -> bool:
    if obj is None:
        return False
    has_status = getattr(obj, "has_status", None)
    if callable(has_status):
        return bool(has_status(status))
    for item in getattr(obj, "statuses", []) or []:
        item_id = getattr(item, "id", None)
        if item_id == status.id or item == status.id:
            return True
    return False


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


def _format_breakdown(effects: Iterable[BonusEffect], skill_id: str, target_id: str | None = None) -> list[str]:
    lines: list[str] = []
    aggregated = aggregate_best_by_type(effects, skill_id, target_id)
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
    apply_modifiers: bool = True,
    consume_statuses: bool = True,
) -> SkillCheckResolution:
    """Policz wynik testu umiejętności z bonusami i efektami statusów."""
    tags = list(tags)
    if "roll" not in tags:
        tags.append("roll")
    modifier, breakdown, notes, promote_src, demote_src, promote_tgt, demote_tgt, consume_src, consume_tgt, effects = _collect_modifier_data(
        skill_id=skill_id,
        tags=tags,
        actor=actor,
        target=target,
        base_modifier=base_modifier,
    )

    prompt_msg = f"Test {skill_id} (DC {dc})."
    summary_lines = []
    if breakdown:
        summary_lines.append(f"Premie/kary (najwyższe per typ): {', '.join(breakdown)}")
    if base_modifier:
        summary_lines.append(f"Modyfikator bazowy: {base_modifier:+d}")
    if skill_id == Skill.REFLEX.value and _is_hero(actor):
        try:
            from statuses.clumsy import clumsy_reflex_penalty

            penalty = int(clumsy_reflex_penalty(actor) or 0)
            if penalty > 0:
                summary_lines.append(f"Clumsy: -{penalty} status do Reflex (uwzględnij ręcznie).")
        except Exception:
            pass
    if notes:
        summary_lines.append(f"Uwagi: {' | '.join(notes)}")
    if apply_modifiers:
        summary_lines.append(f"Łączny modyfikator: {modifier:+d} (doliczany automatycznie).")
        prompt_long = "Podaj wynik rzutu d20 (bez premii). " + " ".join(summary_lines)
    else:
        summary_lines.append(f"Modyfikator do uwzględnienia: {modifier:+d}.")
        prompt_long = "Podaj końcowy wynik (uwzględnij premie/kary). " + " ".join(summary_lines)
    modifiers_grid = build_modifiers_grid(select_best_effects(effects, skill_id))
    roll_data = prompt_for_roll(
        prompt_msg,
        layout="test",
        prompt_long=prompt_long,
        answer_placeholder="Wynik rzutu",
        modifiers=modifiers_grid,
        return_details=True,
        infer_natural_from_roll=bool(apply_modifiers),
    )
    if isinstance(roll_data, dict):
        roll = int(roll_data.get("roll", 0) or 0)
        natural_shift = int(roll_data.get("natural_shift", 0) or 0)
    else:
        roll = int(roll_data or 0)
        natural_shift = natural_shift_from_roll(roll) if apply_modifiers else 0
    return resolve_skill_check_with_sources_from_roll(
        skill_id=skill_id,
        dc=dc,
        actor=actor,
        tags=tags,
        roll=roll,
        natural_shift=natural_shift,
        target=target,
        game=game,
        base_modifier=base_modifier,
        apply_modifiers=apply_modifiers,
        consume_statuses=consume_statuses,
        _precomputed=(modifier, breakdown, notes, promote_src, demote_src, promote_tgt, demote_tgt, consume_src, consume_tgt, effects),
    )


def resolve_skill_check_with_sources_from_roll(
    *,
    skill_id: str,
    dc: int,
    actor,
    tags: Sequence[str],
    roll: int,
    natural_shift: int = 0,
    target=None,
    game=None,
    base_modifier: int = 0,
    apply_modifiers: bool = True,
    consume_statuses: bool = True,
    _precomputed=None,
) -> SkillCheckResolution:
    """Wersja resolvera z podanym wynikiem rzutu (bez promptu)."""
    tags = list(tags)
    if "roll" not in tags:
        tags.append("roll")
    if _precomputed is None:
        modifier, breakdown, notes, promote_src, demote_src, promote_tgt, demote_tgt, consume_src, consume_tgt, _effects = _collect_modifier_data(
            skill_id=skill_id,
            tags=tags,
            actor=actor,
            target=target,
            base_modifier=base_modifier,
        )
    else:
        modifier, breakdown, notes, promote_src, demote_src, promote_tgt, demote_tgt, consume_src, consume_tgt, _effects = _precomputed

    try:
        from statuses.pf2_conditions import forced_skill_outcome
    except Exception:
        forced_skill_outcome = None
    if callable(forced_skill_outcome):
        forced_outcome, forced_note = forced_skill_outcome(actor, tags=tags)
    else:
        forced_outcome, forced_note = (None, None)
    if forced_note:
        notes.append(str(forced_note))

    def _apply_outcome(current_roll: int, *, shift: int) -> tuple[int, int, str]:
        total_val = current_roll + modifier if apply_modifiers else current_roll
        outcome_val = resolve_skill_check(dc, total_val, natural_shift=shift)
        for value, cond in list(promote_src) + list(promote_tgt):
            if cond is None or outcome_val in cond:
                outcome_val = _apply_shift(outcome_val, value)
        for value, cond in list(demote_src) + list(demote_tgt):
            if cond is None or outcome_val in cond:
                outcome_val = _apply_shift(outcome_val, -value)
        return current_roll, total_val, outcome_val

    roll, total, outcome = _apply_outcome(roll, shift=natural_shift)
    if forced_outcome:
        outcome = str(forced_outcome)

    def _has_status(actor_obj, status_id: str) -> bool:
        if actor_obj is None:
            return False
        has_status = getattr(actor_obj, "has_status", None)
        if callable(has_status):
            try:
                return bool(has_status(status_id))
            except Exception:
                return False
        statuses = getattr(actor_obj, "statuses", None)
        if isinstance(statuses, list):
            return any(getattr(s, "id", s) == status_id for s in statuses)
        return False

    def _consume_status(actor_obj, status_id: str) -> None:
        if actor_obj is None:
            return
        remover = getattr(actor_obj, "remove_status", None)
        if callable(remover):
            try:
                remover(status_id)
                return
            except Exception:
                pass
        statuses = getattr(actor_obj, "statuses", None)
        if isinstance(statuses, list):
            for idx in range(len(statuses) - 1, -1, -1):
                if getattr(statuses[idx], "id", statuses[idx]) == status_id:
                    del statuses[idx]
                    break

    def _prompt_halfling_luck() -> bool:
        ui_client = get_ui_client()
        if ui_client is not None and getattr(ui_client, "enabled", True):
            try:
                choice = ui_client.prompt_choice(
                    "Użyć Halfling Luck? (przerzut, wynik obowiązkowy)",
                    choices=["tak", "nie"],
                    source="halfling_luck",
                )
                return str(choice or "").strip().lower().startswith("t")
            except Exception:
                pass
        if ui_client is not None and not getattr(ui_client, "allow_cli_fallback", False):
            return False
        try:
            resp = input("Użyć Halfling Luck? [t/N]: ")
            return resp.strip().lower().startswith("t")
        except Exception:
            return False

    if outcome in ("failure", "critical_failure") and _has_status(actor, "halfling_luck"):
        if _prompt_halfling_luck():
            reroll_data = prompt_for_roll(
                "Halfling Luck: przerzut (użyj nowego wyniku).",
                layout="test",
                answer_placeholder="Wynik k20",
                return_details=True,
                infer_natural_from_roll=bool(apply_modifiers),
            )
            if isinstance(reroll_data, dict):
                reroll = int(reroll_data.get("roll", 0) or 0)
                reroll_shift = int(reroll_data.get("natural_shift", 0) or 0)
            else:
                reroll = int(reroll_data or 0)
                reroll_shift = natural_shift_from_roll(reroll) if apply_modifiers else 0
            roll, total, outcome = _apply_outcome(reroll, shift=reroll_shift)
            _consume_status(actor, "halfling_luck")

    def _counter_performance_total(actor_obj) -> int | None:
        statuses = getattr(actor_obj, "statuses", None)
        if not isinstance(statuses, list) or not statuses:
            return None
        best: int | None = None
        for status in statuses:
            if getattr(status, "id", None) != "counter_performance":
                continue
            data = getattr(status, "data", None) or {}
            try:
                value = int(data.get("performance_total", 0) or 0)
            except Exception:
                value = 0
            if value <= 0:
                continue
            if best is None or value > best:
                best = value
        return best

    if skill_id in (Skill.FORTITUDE.value, Skill.REFLEX.value, Skill.WILL.value):
        perf_total = _counter_performance_total(actor)
        if perf_total is not None and total < perf_total:
            original_total = total
            total = perf_total
            outcome = resolve_skill_check(dc, total)
            notes.append(
                f"Counter Performance: wynik save {original_total} zastapiony przez {perf_total}."
            )

    resolution = SkillCheckResolution(
        outcome=outcome,
        roll=roll,
        modifier=modifier,
        total=total,
        dc=dc,
        notes=notes,
        breakdown=breakdown,
    )

    if consume_statuses:
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
            all_lines = format_effects_log(_effects, skill_id)
            if all_lines:
                game.ui_log(f"{skill_id}: premie/kary: {', '.join(all_lines)}.")
            if base_modifier:
                game.ui_log(f"{skill_id}: modyfikator bazowy: {base_modifier:+d}.")
    except Exception:
        pass

    return resolution


def _collect_modifier_data(
    *,
    skill_id: str,
    tags: Sequence[str],
    actor,
    target=None,
    base_modifier: int = 0,
):
    tags = list(tags)
    all_effects: list[BonusEffect] = []
    bonuses = getattr(actor, "bonuses", None)
    if isinstance(bonuses, list):
        all_effects.extend(bonuses)

    src_effects, promote_src, demote_src, notes_src, consume_src = _collect_from_statuses(
        _status_list(actor), skill_id, tags, "source"
    )
    all_effects.extend(src_effects)
    tgt_effects, promote_tgt, demote_tgt, notes_tgt, consume_tgt = _collect_from_statuses(
        _status_list(target), skill_id, tags, "target"
    ) if target else ([], [], [], [], [])
    all_effects.extend(tgt_effects)

    if skill_id == Skill.PERCEPTION.value and target is not None:
        if _has_status(actor, DARKVISION_STATUS) and _has_status(target, IN_DARK_STATUS):
            all_effects.append(
                BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=10,
                    tag=skill_id,
                    source="status:darkvision",
                    label="darkvision +10",
                )
            )
        if (_has_status(actor, DIM_LIGHT_VISION_STATUS) or _has_status(actor, LOW_LIGHT_VISION_STATUS)) and _has_status(
            target, IN_DIM_LIGHT_STATUS
        ):
            all_effects.append(
                BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=2,
                    tag=skill_id,
                    source="status:low_light_vision",
                    label="low light vision +2",
                )
            )
    if skill_id == Skill.PERCEPTION.value and any(tag in {"trap", "traps"} for tag in tags):
        if _has_status(actor, Status(id="trap_finder")):
            all_effects.append(
                BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=1,
                    tag=Skill.PERCEPTION.value,
                    source="rogue:trap_finder",
                    label="Trap Finder +1",
                )
            )

    notes = list(notes_src) + list(notes_tgt)

    if skill_id == Skill.REFLEX.value:
        try:
            from statuses.clumsy import clumsy_reflex_penalty
        except Exception:
            clumsy_reflex_penalty = None
        if clumsy_reflex_penalty:
            penalty = int(clumsy_reflex_penalty(actor) or 0)
            if penalty > 0:
                if _is_hero(actor):
                    notes.append(f"Clumsy: -{penalty} status do Reflex (uwzględnij ręcznie).")
                else:
                    all_effects.append(
                        BonusEffect(
                            type=BonusType.STATUS,
                            value=penalty,
                            tag=skill_id,
                            source="status:clumsy",
                            label="clumsy",
                            is_penalty=True,
                        )
                    )

    if skill_id in (Skill.FORTITUDE.value, Skill.REFLEX.value, Skill.WILL.value) and "fear" in tags:
        has_status = getattr(actor, "has_status", None)
        has_ic = False
        if callable(has_status):
            try:
                has_ic = bool(has_status("inspire_courage"))
            except Exception:
                has_ic = False
        if not has_ic:
            statuses = getattr(actor, "statuses", None)
            if isinstance(statuses, list):
                has_ic = any(getattr(s, "id", None) == "inspire_courage" for s in statuses)
        if has_ic:
            all_effects.append(
                BonusEffect(
                    type=BonusType.STATUS,
                    value=1,
                    tag=skill_id,
                    source="status:inspire_courage_fear",
                    label="inspire courage",
                )
            )

    if skill_id == Skill.STEALTH.value:
        try:
            game = getattr(actor, "game", None)
            if game is not None:
                from GameObjects.events.magic.lighting_effects import is_position_in_light_aura

                if is_position_in_light_aura(game, getattr(actor, "position", None)):
                    all_effects.append(
                        BonusEffect(
                            type=BonusType.CIRCUMSTANCE,
                            value=10,
                            tag=Skill.STEALTH.value,
                            source="light_aura",
                            label="light aura",
                            is_penalty=True,
                        )
                    )
        except Exception:
            pass

    try:
        from statuses.pf2_conditions import skill_penalty_value

        extra_penalty = int(skill_penalty_value(actor, skill_id=skill_id, tags=tags) or 0)
    except Exception:
        extra_penalty = 0
    if extra_penalty > 0:
        all_effects.append(
            BonusEffect(
                type=BonusType.STATUS,
                value=extra_penalty,
                tag=skill_id,
                source="status:pf2_condition_penalty",
                label="conditions",
                is_penalty=True,
            )
        )

    is_recall_knowledge = "knowledge" in tags or "recall_knowledge" in tags or "recall-knowledge" in tags
    try:
        from statuses.classes.ranger.ranger_utils import hunter_edge as ranger_hunter_edge
        from statuses.classes.ranger.ranger_utils import is_hunted_prey as ranger_is_hunted_prey

        if target is not None and ranger_is_hunted_prey(actor, target):
            if skill_id in {Skill.DECEPTION.value, Skill.INTIMIDATION.value, Skill.STEALTH.value}:
                if ranger_hunter_edge(actor) == "outwit":
                    all_effects.append(
                        BonusEffect(
                            type=BonusType.CIRCUMSTANCE,
                            value=2,
                            tag=skill_id,
                            source="ranger:outwit",
                            label="outwit +2",
                        )
                    )
            if is_recall_knowledge and ranger_hunter_edge(actor) == "outwit":
                all_effects.append(
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=skill_id,
                        source="ranger:outwit",
                        label="outwit +2",
                    )
                )
            if skill_id == Skill.PERCEPTION.value and "seek" in tags:
                all_effects.append(
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.PERCEPTION.value,
                        source="ranger:hunt_prey_seek",
                        label="hunt prey +2",
                    )
                )
            if skill_id == Skill.SURVIVAL.value and "track" in tags:
                all_effects.append(
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=Skill.SURVIVAL.value,
                        source="ranger:hunt_prey_track",
                        label="hunt prey +2",
                    )
                )
    except Exception:
        pass
    if is_recall_knowledge and _has_status(actor, Status(id="bardic_lore")):
        notes.append(
            "Bardic Lore: Recall Knowledge z advantage (rzuc 2x k20 i wybierz lepszy wynik) - opisowo."
        )

    if _has_status(actor, Status(id="versatile_performance")):
        if skill_id == Skill.DIPLOMACY.value:
            notes.append(
                "Versatile Performance: zamiast Diplomacy mozesz wykonac test Performance (opisowo)."
            )
        elif skill_id == Skill.INTIMIDATION.value:
            notes.append(
                "Versatile Performance: zamiast Intimidation mozesz wykonac test Performance (opisowo)."
            )
        elif skill_id == Skill.DECEPTION.value:
            notes.append(
                "Versatile Performance: zamiast Deception mozesz wykonac test Performance (opisowo)."
            )

    target_id = getattr(target, "object_id", None) if target is not None else None
    modifier = base_modifier + (compute_total_modifier(all_effects, skill_id, target_id) if all_effects else 0)
    breakdown = _format_breakdown(all_effects, skill_id, target_id)
    return modifier, breakdown, notes, promote_src, demote_src, promote_tgt, demote_tgt, consume_src, consume_tgt, all_effects


def compute_skill_modifier_with_sources(
    *,
    skill_id: str,
    actor,
    target=None,
    tags: Sequence[str] | None = None,
    base_modifier: int = 0,
) -> tuple[int, list[str], list[str]]:
    """Zwróć (modifier, breakdown, notes) bez wykonywania rzutu."""
    tags = list(tags or [])
    modifier, breakdown, notes, _ps, _ds, _pt, _dt, _cs, _ct, _effects = _collect_modifier_data(
        skill_id=skill_id,
        tags=tags,
        actor=actor,
        target=target,
        base_modifier=base_modifier,
    )
    return modifier, breakdown, notes
