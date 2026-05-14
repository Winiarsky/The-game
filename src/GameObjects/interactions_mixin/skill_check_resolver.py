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
from combat.degree_of_success import (
    clamp_natural_shift,
    natural_mode_from_shift,
    natural_shift_from_mode,
    natural_shift_from_roll,
)

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
    raw_roll = 0
    shift = 0
    modifier_delta = 0
    computed_total = None
    if isinstance(answer, dict):
        raw_roll_data = answer.get("raw_roll", answer.get("roll", answer.get("value", answer.get("result", 0))))
        roll_value = answer.get("roll", answer.get("value", answer.get("result", 0)))
        try:
            raw_roll = int(raw_roll_data or 0)
        except Exception:
            raw_roll = 0
        try:
            roll = int(roll_value or 0)
        except Exception:
            roll = 0
        if raw_roll == 0 and roll != 0:
            raw_roll = roll
        mode = answer.get("natural_mode", answer.get("natural", answer.get("nat", None)))
        shift = natural_shift_from_mode(mode)
        if shift == 0:
            shift = clamp_natural_shift(answer.get("natural_shift"))
        if shift == 0 and infer_natural_from_roll:
            shift = natural_shift_from_roll(raw_roll)
        try:
            modifier_delta = int(answer.get("modifier_delta", 0) or 0)
        except Exception:
            modifier_delta = 0
        if "computed_total" in answer:
            try:
                computed_total = int(answer.get("computed_total", 0) or 0)
            except Exception:
                computed_total = None
    else:
        try:
            roll = int(answer or 0)
        except Exception:
            roll = 0
        raw_roll = roll
        if infer_natural_from_roll:
            shift = natural_shift_from_roll(raw_roll)
    out = {
        "roll": int(roll),
        "raw_roll": int(raw_roll),
        "natural_shift": int(shift),
        "natural_mode": natural_mode_from_shift(shift),
        "modifier_delta": int(modifier_delta),
    }
    if computed_total is not None:
        out["computed_total"] = int(computed_total)
    return out


def _int_or_default(value, default: int = 0) -> int:
    try:
        return int(value or 0)
    except Exception:
        return int(default)


RANK_STEP_BONUS = {
    "untrained": 0,
    "trained": 2,
    "expert": 4,
    "master": 6,
    "legendary": 8,
}

SKILL_TO_ABILITY = {
    "acrobatics": "dexterity",
    "arcana": "intelligence",
    "athletics": "strength",
    "crafting": "intelligence",
    "deception": "charisma",
    "diplomacy": "charisma",
    "intimidation": "charisma",
    "medicine": "wisdom",
    "nature": "wisdom",
    "occultism": "intelligence",
    "performance": "charisma",
    "religion": "wisdom",
    "society": "intelligence",
    "stealth": "dexterity",
    "survival": "wisdom",
    "thievery": "dexterity",
    "perception": "wisdom",
    "fortitude": "constitution",
    "reflex": "dexterity",
    "will": "wisdom",
}

ROLL_AUDIO_BY_SKILL = {
    "acrobatics": "audio/voiceover/runtime_prompts/roll_acrobatics_prompt_001.mp3",
    "arcana": "audio/voiceover/runtime_prompts/roll_arcana_prompt_001.mp3",
    "athletics": "audio/voiceover/runtime_prompts/roll_athletics_prompt_001.mp3",
    "crafting": "audio/voiceover/runtime_prompts/roll_crafting_prompt_001.mp3",
    "deception": "audio/voiceover/runtime_prompts/roll_deception_prompt_001.mp3",
    "diplomacy": "audio/voiceover/runtime_prompts/roll_diplomacy_prompt_001.mp3",
    "intimidation": "audio/voiceover/runtime_prompts/roll_intimidation_prompt_001.mp3",
    "lore": "audio/voiceover/runtime_prompts/roll_lore_prompt_001.mp3",
    "medicine": "audio/voiceover/runtime_prompts/roll_medicine_prompt_001.mp3",
    "nature": "audio/voiceover/runtime_prompts/roll_nature_prompt_001.mp3",
    "occultism": "audio/voiceover/runtime_prompts/roll_occultism_prompt_001.mp3",
    "performance": "audio/voiceover/runtime_prompts/roll_performance_prompt_001.mp3",
    "religion": "audio/voiceover/runtime_prompts/roll_religion_prompt_001.mp3",
    "society": "audio/voiceover/runtime_prompts/roll_society_prompt_001.mp3",
    "stealth": "audio/voiceover/runtime_prompts/roll_stealth_prompt_001.mp3",
    "survival": "audio/voiceover/runtime_prompts/roll_survival_prompt_001.mp3",
    "thievery": "audio/voiceover/runtime_prompts/roll_thievery_prompt_001.mp3",
    "perception": "audio/voiceover/runtime_prompts/roll_perception_prompt_001.mp3",
    "fortitude": "audio/voiceover/runtime_prompts/roll_fortitude_prompt_001.mp3",
    "reflex": "audio/voiceover/runtime_prompts/roll_reflex_prompt_001.mp3",
    "will": "audio/voiceover/runtime_prompts/roll_will_prompt_001.mp3",
}


def _roll_prompt_audio(prompt: object) -> str | None:
    raw = str(prompt or "").strip().lower()
    if not raw.startswith("test "):
        return None
    skill = raw.split(" ", 2)[1].strip(" .():")
    return ROLL_AUDIO_BY_SKILL.get(skill)


def _actor_has_status_id(actor, status_id: str) -> bool:
    if actor is None:
        return False
    has_status = getattr(actor, "has_status", None)
    if callable(has_status):
        try:
            return bool(has_status(status_id))
        except Exception:
            return False
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return False
    needle = str(status_id or "").strip().lower()
    return any(str(getattr(status, "id", status) or "").strip().lower() == needle for status in statuses)


def _ability_label_pl(ability_key: str) -> str:
    mapping = {
        "strength": "Siła",
        "dexterity": "Zręczność",
        "constitution": "Kondycja",
        "intelligence": "Inteligencja",
        "wisdom": "Mądrość",
        "charisma": "Charyzma",
    }
    return mapping.get(str(ability_key or "").strip().lower(), str(ability_key or "Atrybut"))


def _skill_rank_for_actor(actor, skill_id: str) -> str:
    raw_skill = str(skill_id or "").strip().lower()
    if actor is None:
        return "untrained"
    if raw_skill == Skill.PERCEPTION.value:
        return str(getattr(actor, "perception_rank", "untrained") or "untrained").strip().lower()
    if raw_skill in (Skill.FORTITUDE.value, Skill.REFLEX.value, Skill.WILL.value):
        save_ranks = getattr(actor, "save_ranks", None)
        if isinstance(save_ranks, dict):
            return str(save_ranks.get(raw_skill, "untrained") or "untrained").strip().lower()
    skill_ranks = getattr(actor, "skill_ranks", None)
    if isinstance(skill_ranks, dict):
        return str(skill_ranks.get(raw_skill, "untrained") or "untrained").strip().lower()
    return "untrained"


def _ability_mod_for_actor(actor, ability_key: str) -> int:
    if actor is None:
        return 0
    raw_key = str(ability_key or "").strip().lower()
    mods = getattr(actor, "ability_modifiers", None)
    if isinstance(mods, dict):
        return _int_or_default(mods.get(raw_key, 0), 0)
    short = {"strength": "str", "dexterity": "dex", "constitution": "con", "intelligence": "int", "wisdom": "wis", "charisma": "cha"}
    short_key = short.get(raw_key)
    if short_key:
        return _int_or_default(getattr(actor, f"{short_key}_mod", 0), 0)
    return 0


def _intrinsic_skill_bonus(actor, skill_id: str) -> int | None:
    if actor is None:
        return None
    raw_skill = str(skill_id or "").strip().lower()
    attr_name = {
        Skill.PERCEPTION.value: "perception_bonus",
        Skill.FORTITUDE.value: "fortitude_bonus",
        Skill.REFLEX.value: "reflex_bonus",
        Skill.WILL.value: "will_bonus",
    }.get(raw_skill, f"{raw_skill}_bonus")
    if not hasattr(actor, attr_name):
        return None
    return _int_or_default(getattr(actor, attr_name, 0), 0)


def _resolve_base_modifier_components(actor, skill_id: str, requested_base_modifier: int) -> tuple[int, list[dict[str, object]]]:
    raw_skill = str(skill_id or "").strip().lower()
    rank = _skill_rank_for_actor(actor, raw_skill)
    rank_step = int(RANK_STEP_BONUS.get(rank, 0))
    level = _int_or_default(getattr(actor, "level", 0), 0)
    level_component = level if rank != "untrained" else 0
    ability_key = str(SKILL_TO_ABILITY.get(raw_skill, "intelligence"))
    ability_mod = _ability_mod_for_actor(actor, ability_key)

    derived_total = int(level_component + rank_step + ability_mod)
    explicit_bonus = _intrinsic_skill_bonus(actor, raw_skill)
    resolved = _int_or_default(requested_base_modifier, 0)
    if resolved == 0:
        if explicit_bonus is not None:
            resolved = int(explicit_bonus)
        else:
            resolved = int(derived_total)

    components: list[dict[str, object]] = [
        {
            "id": "level",
            "label": "Poziom",
            "value": int(level_component),
            "description": "Poziom postaci (tylko jeśli co najmniej Trained).",
            "editable": True,
        },
        {
            "id": "proficiency_step",
            "label": "Biegłość",
            "value": int(rank_step),
            "description": f"Stopień biegłości ({rank}).",
            "editable": True,
        },
        {
            "id": "ability",
            "label": _ability_label_pl(ability_key),
            "value": int(ability_mod),
            "description": f"Modyfikator cechy ({_ability_label_pl(ability_key)}).",
            "editable": True,
        },
    ]

    remainder = int(resolved - derived_total)
    if remainder != 0:
        components.append(
            {
                "id": "other_base",
                "label": "Pozostałe bazowe",
                "value": int(remainder),
                "description": "Różnica między wyliczeniem a bazowym bonusem postaci.",
                "editable": True,
            }
        )
    return int(resolved), components


def _is_recall_knowledge(tags: Sequence[str]) -> bool:
    normalized = {str(tag or "").strip().lower().replace("-", "_") for tag in list(tags or [])}
    return bool({"knowledge", "recall_knowledge"}.intersection(normalized))


def _bardic_lore_modifier(actor) -> int:
    level = _int_or_default(getattr(actor, "level", 0), 0)
    ability_mod = _ability_mod_for_actor(actor, "intelligence")
    return int(level + RANK_STEP_BONUS["trained"] + ability_mod)


def _versatile_performance_substitute(skill_id: str, tags: Sequence[str], actor) -> tuple[str, str] | None:
    if not _actor_has_status_id(actor, "versatile_performance"):
        return None
    normalized_skill = str(skill_id or "").strip().lower()
    normalized_tags = {str(tag or "").strip().lower().replace("-", "_") for tag in list(tags or [])}
    if normalized_skill == Skill.DIPLOMACY.value and "make_impression" in normalized_tags:
        return Skill.PERFORMANCE.value, "Versatile Performance: Make an Impression rozliczone przez Performance."
    if normalized_skill == Skill.INTIMIDATION.value and "demoralize" in normalized_tags:
        return Skill.PERFORMANCE.value, "Versatile Performance: Demoralize rozliczone przez Performance."
    if normalized_skill == Skill.DECEPTION.value and "impersonate" in normalized_tags:
        return Skill.PERFORMANCE.value, "Versatile Performance: Impersonate rozliczone przez Performance."
    return None


def _resolve_skill_runtime_context(
    *,
    actor,
    skill_id: str,
    tags: Sequence[str],
    requested_base_modifier: int,
) -> tuple[str, int, list[str]]:
    normalized_skill = str(skill_id or "").strip().lower()
    requested = _int_or_default(requested_base_modifier, 0)
    notes: list[str] = []

    effective_skill = normalized_skill
    effective_requested = requested

    original_default, _ = _resolve_base_modifier_components(actor, normalized_skill, 0)
    original_resolved, _ = _resolve_base_modifier_components(actor, normalized_skill, requested)
    extra_delta = int(original_resolved - original_default)

    versatile = _versatile_performance_substitute(normalized_skill, tags, actor)
    if versatile is not None:
        effective_skill, note = versatile
        substitute_default, _ = _resolve_base_modifier_components(actor, effective_skill, 0)
        effective_requested = int(substitute_default + extra_delta)
        notes.append(note)

    effective_default, _ = _resolve_base_modifier_components(actor, effective_skill, 0)
    effective_resolved, _ = _resolve_base_modifier_components(actor, effective_skill, effective_requested)
    effective_extra_delta = int(effective_resolved - effective_default)

    if _is_recall_knowledge(tags) and _actor_has_status_id(actor, "bardic_lore"):
        bardic_total = int(_bardic_lore_modifier(actor) + effective_extra_delta)
        if bardic_total > effective_resolved:
            effective_requested = bardic_total
            notes.append(
                f"Bardic Lore: Recall Knowledge uzywa lepszego modyfikatora {bardic_total:+d}."
            )
        else:
            notes.append(
                f"Bardic Lore: dostepne do Recall Knowledge (aktualny modyfikator {effective_resolved:+d} jest rowny lub lepszy)."
            )

    return effective_skill, int(effective_requested), notes


def _skill_roll_stack_payload(
    *,
    base_components: list[dict[str, object]],
    modifiers_grid: dict,
    total_modifier: int,
) -> dict[str, object]:
    components = list(base_components) + _modifier_components_from_grid(modifiers_grid, include_empty=True)
    return {
        "components": components,
        "auto_total_modifier": int(total_modifier),
    }


def _modifier_components_from_grid(modifiers: dict, *, include_empty: bool = False) -> list[dict[str, object]]:
    components: list[dict[str, object]] = []
    buckets = (
        ("bonItem", "item", "Przedmiot", 1),
        ("penItem", "item", "Przedmiot", -1),
        ("bonStat", "status", "Status", 1),
        ("penStat", "status", "Status", -1),
        ("bonCirc", "circumstance", "Okoliczności", 1),
        ("penCirc", "circumstance", "Okoliczności", -1),
    )
    counts: dict[str, int] = {}
    for key, modifier_type, fallback_label, sign in buckets:
        for idx, row in enumerate(list(modifiers.get(key, []) or [])):
            if not isinstance(row, dict):
                continue
            raw_value = _int_or_default(row.get("value", 0), 0)
            if raw_value == 0:
                continue
            label = str(row.get("label") or fallback_label).strip() or fallback_label
            value = abs(raw_value) * int(sign)
            counts[modifier_type] = counts.get(modifier_type, 0) + 1
            component_id = modifier_type if counts[modifier_type] == 1 else f"{modifier_type}_{counts[modifier_type]}"
            components.append(
                {
                    "id": component_id,
                    "label": label,
                    "value": int(value),
                    "description": f"{modifier_type} {'bonus' if sign > 0 else 'penalty'}",
                    "type": modifier_type,
                    "editable": True,
                }
            )
    if include_empty:
        labels = {"item": "Przedmiot", "status": "Status", "circumstance": "Okoliczności"}
        descriptions = {
            "item": "Premie/kary z przedmiotów i run.",
            "status": "Premie/kary status.",
            "circumstance": "Premie/kary okolicznościowe.",
        }
        existing = {str(item.get("id")) for item in components}
        for modifier_type in ("item", "status", "circumstance"):
            if modifier_type in existing:
                continue
            components.append(
                {
                    "id": modifier_type,
                    "label": labels[modifier_type],
                    "value": 0,
                    "description": descriptions[modifier_type],
                    "type": modifier_type,
                    "editable": True,
                }
            )
    return components


def _sum_modifier_bucket(modifiers: dict, key: str, *, is_penalty: bool = False) -> int:
    total = 0
    for row in list(modifiers.get(key, []) or []):
        value = _int_or_default(row.get("value", 0), 0) if isinstance(row, dict) else 0
        total += -abs(value) if is_penalty else abs(value)
    return int(total)


def _prepare_roll_stack_payload(
    *,
    roll_stack: dict | None,
    modifiers: dict | None,
    auto_total_modifier: int | None,
) -> dict | None:
    base_payload: dict = dict(roll_stack or {})
    raw_components = list(base_payload.get("components") or [])
    components: list[dict[str, object]] = []

    if raw_components:
        for idx, row in enumerate(raw_components):
            if not isinstance(row, dict):
                continue
            components.append(
                {
                    "id": str(row.get("id") or f"component_{idx + 1}"),
                    "label": str(row.get("label") or f"Składnik {idx + 1}"),
                    "value": _int_or_default(row.get("value", 0), 0),
                    "description": str(row.get("description") or row.get("desc") or ""),
                    "editable": bool(row.get("editable", True)),
                }
            )
    elif isinstance(modifiers, dict):
        components.extend(_modifier_components_from_grid(modifiers))

    components_total = sum(_int_or_default(item.get("value", 0), 0) for item in components)
    auto_total = auto_total_modifier
    if auto_total is None and "auto_total_modifier" in base_payload:
        auto_total = _int_or_default(base_payload.get("auto_total_modifier", 0), 0)
    if auto_total is None:
        auto_total = int(components_total)

    if int(auto_total) != int(components_total):
        diff = int(auto_total) - int(components_total)
        components.append(
            {
                "id": "other_auto",
                "label": "Pozostałe",
                "value": int(diff),
                "description": "Pozostały automatyczny modyfikator.",
                "editable": True,
            }
        )

    if not components and int(auto_total) == 0:
        return None

    base_payload["components"] = components
    base_payload["auto_total_modifier"] = int(auto_total)
    return base_payload


def prompt_for_roll(prompt: str, *, return_details: bool = False, infer_natural_from_roll: bool = False, **ui_kwargs):
    """Lokalny wrapper na prompt w testach (ułatwia monkeypatch get_ui_client)."""
    ui_client = get_ui_client()
    layout = str(ui_kwargs.get("layout", "test") or "test")
    roll_stack_arg = ui_kwargs.pop("roll_stack", None)
    auto_total_modifier = ui_kwargs.pop("auto_total_modifier", None)
    roll_stack_payload = _prepare_roll_stack_payload(
        roll_stack=roll_stack_arg if isinstance(roll_stack_arg, dict) else None,
        modifiers=ui_kwargs.get("modifiers") if isinstance(ui_kwargs.get("modifiers"), dict) else None,
        auto_total_modifier=_int_or_default(auto_total_modifier, 0) if auto_total_modifier is not None else None,
    )
    if roll_stack_payload is not None and layout.strip().lower() == "test":
        ui_kwargs["roll_stack"] = roll_stack_payload
    if ui_client is not None and hasattr(ui_client, "prompt_roll") and getattr(ui_client, "enabled", True):
        if "layout" not in ui_kwargs:
            ui_kwargs["layout"] = "test"
        ui_kwargs.setdefault("answer_placeholder", "Podaj wynik rzutu")
        ui_kwargs.setdefault("audio", _roll_prompt_audio(prompt))
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
    effective_skill_id, effective_requested_base, runtime_notes = _resolve_skill_runtime_context(
        actor=actor,
        skill_id=skill_id,
        tags=tags,
        requested_base_modifier=int(base_modifier or 0),
    )
    resolved_base_modifier, base_components = _resolve_base_modifier_components(
        actor,
        effective_skill_id,
        int(effective_requested_base or 0),
    )
    modifier, breakdown, notes, promote_src, demote_src, promote_tgt, demote_tgt, consume_src, consume_tgt, effects = _collect_modifier_data(
        skill_id=effective_skill_id,
        tags=tags,
        actor=actor,
        target=target,
        base_modifier=resolved_base_modifier,
    )
    notes = list(runtime_notes) + list(notes)

    prompt_msg = f"Test {skill_id} (DC {dc})."
    summary_lines = []
    if breakdown:
        summary_lines.append(f"Premie/kary (najwyższe per typ): {', '.join(breakdown)}")
    if resolved_base_modifier:
        summary_lines.append(f"Modyfikator bazowy: {resolved_base_modifier:+d}")
    if skill_id == Skill.REFLEX.value and _is_hero(actor):
        try:
            from statuses.clumsy import clumsy_reflex_penalty

            penalty = int(clumsy_reflex_penalty(actor) or 0)
            if penalty > 0:
                summary_lines.append(f"Clumsy: -{penalty} status do Reflex (uwzględnij ręcznie).")
        except Exception:
            pass
    if notes:
        summary_lines.append("Uwagi: " + "; ".join(notes))
    if apply_modifiers:
        summary_lines.append(f"Łączny modyfikator: {modifier:+d} (doliczany automatycznie).")
        prompt_long = "Podaj wynik rzutu d20 (bez premii). " + " ".join(summary_lines)
    else:
        summary_lines.append(f"Modyfikator do uwzględnienia: {modifier:+d}.")
        prompt_long = "Podaj końcowy wynik (uwzględnij premie/kary). " + " ".join(summary_lines)
    modifiers_grid = build_modifiers_grid(select_best_effects(effects, skill_id))
    roll_stack_payload = _skill_roll_stack_payload(
        base_components=base_components,
        modifiers_grid=modifiers_grid,
        total_modifier=int(modifier or 0),
    )
    use_loremaster_etude = _is_recall_knowledge(tags) and _actor_has_status_id(actor, "loremaster_etude_ready")
    if use_loremaster_etude:
        first_roll = prompt_for_roll(
            f"{prompt_msg} (Loremaster's Etude 1/2)",
            layout="test",
            prompt_long=prompt_long,
            answer_placeholder="Wynik rzutu",
            modifiers=modifiers_grid,
            roll_stack=roll_stack_payload,
            auto_total_modifier=int(modifier or 0),
            return_details=True,
            infer_natural_from_roll=bool(apply_modifiers),
        )
        second_roll = prompt_for_roll(
            f"{prompt_msg} (Loremaster's Etude 2/2)",
            layout="test",
            prompt_long=prompt_long,
            answer_placeholder="Wynik rzutu",
            modifiers=modifiers_grid,
            roll_stack=roll_stack_payload,
            auto_total_modifier=int(modifier or 0),
            return_details=True,
            infer_natural_from_roll=bool(apply_modifiers),
        )

        def _roll_value(payload) -> int:
            if isinstance(payload, dict):
                return int(payload.get("roll", 0) or 0)
            return int(payload or 0)

        roll_data = first_roll if _roll_value(first_roll) >= _roll_value(second_roll) else second_roll
        remover = getattr(actor, "remove_status", None)
        if callable(remover):
            try:
                remover("loremaster_etude_ready")
            except Exception:
                pass
        runtime_notes.append("Loremaster's Etude: użyto lepszego z 2 rzutow do Recall Knowledge.")
        notes = list(runtime_notes) + [note for note in notes if note not in runtime_notes]
    else:
        roll_data = prompt_for_roll(
            prompt_msg,
            layout="test",
            prompt_long=prompt_long,
            answer_placeholder="Wynik rzutu",
            modifiers=modifiers_grid,
            roll_stack=roll_stack_payload,
            auto_total_modifier=int(modifier or 0),
            return_details=True,
            infer_natural_from_roll=bool(apply_modifiers),
        )
    if isinstance(roll_data, dict):
        roll = int(roll_data.get("roll", 0) or 0)
        natural_shift = int(roll_data.get("natural_shift", 0) or 0)
        if natural_shift == 0 and apply_modifiers:
            raw_roll = int(roll_data.get("raw_roll", roll) or roll)
            natural_shift = natural_shift_from_roll(raw_roll)
        modifier_delta = int(roll_data.get("modifier_delta", 0) or 0)
    else:
        roll = int(roll_data or 0)
        natural_shift = natural_shift_from_roll(roll) if apply_modifiers else 0
        modifier_delta = 0
    return resolve_skill_check_with_sources_from_roll(
        skill_id=skill_id,
        dc=dc,
        actor=actor,
        tags=tags,
        roll=roll,
        natural_shift=natural_shift,
        modifier_delta=modifier_delta,
        target=target,
        game=game,
        base_modifier=resolved_base_modifier,
        apply_modifiers=apply_modifiers,
        consume_statuses=consume_statuses,
        _precomputed=(
            effective_skill_id,
            modifier,
            breakdown,
            notes,
            promote_src,
            demote_src,
            promote_tgt,
            demote_tgt,
            consume_src,
            consume_tgt,
            effects,
        ),
    )


def resolve_skill_check_with_sources_from_roll(
    *,
    skill_id: str,
    dc: int,
    actor,
    tags: Sequence[str],
    roll: int,
    natural_shift: int = 0,
    modifier_delta: int = 0,
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
        effective_skill_id, effective_requested_base, runtime_notes = _resolve_skill_runtime_context(
            actor=actor,
            skill_id=skill_id,
            tags=tags,
            requested_base_modifier=int(base_modifier or 0),
        )
        resolved_base_modifier, _base_components = _resolve_base_modifier_components(
            actor,
            effective_skill_id,
            int(effective_requested_base or 0),
        )
        modifier, breakdown, notes, promote_src, demote_src, promote_tgt, demote_tgt, consume_src, consume_tgt, _effects = _collect_modifier_data(
            skill_id=effective_skill_id,
            tags=tags,
            actor=actor,
            target=target,
            base_modifier=resolved_base_modifier,
        )
    else:
        runtime_notes = []
        resolved_base_modifier = _int_or_default(base_modifier, 0)
        (
            precomputed_skill_id,
            modifier,
            breakdown,
            notes,
            promote_src,
            demote_src,
            promote_tgt,
            demote_tgt,
            consume_src,
            consume_tgt,
            _effects,
        ) = _precomputed
        effective_skill_id = str(precomputed_skill_id or skill_id)
    notes = list(runtime_notes) + list(notes)

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

    def _apply_outcome(current_roll: int, *, shift: int, extra_modifier: int = 0) -> tuple[int, int, str]:
        total_val = current_roll + modifier + int(extra_modifier or 0) if apply_modifiers else current_roll
        outcome_val = resolve_skill_check(dc, total_val, natural_shift=shift)
        for value, cond in list(promote_src) + list(promote_tgt):
            if cond is None or outcome_val in cond:
                outcome_val = _apply_shift(outcome_val, value)
        for value, cond in list(demote_src) + list(demote_tgt):
            if cond is None or outcome_val in cond:
                outcome_val = _apply_shift(outcome_val, -value)
        return current_roll, total_val, outcome_val

    roll, total, outcome = _apply_outcome(
        roll,
        shift=natural_shift,
        extra_modifier=int(modifier_delta or 0) if apply_modifiers else 0,
    )
    if forced_outcome:
        outcome = str(forced_outcome)
    if apply_modifiers and int(modifier_delta or 0):
        notes.append(f"Korekta ręczna modyfikatora: {int(modifier_delta):+d}.")

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
                if reroll_shift == 0 and apply_modifiers:
                    reroll_raw = int(reroll_data.get("raw_roll", reroll) or reroll)
                    reroll_shift = natural_shift_from_roll(reroll_raw)
                reroll_modifier_delta = int(reroll_data.get("modifier_delta", 0) or 0)
            else:
                reroll = int(reroll_data or 0)
                reroll_shift = natural_shift_from_roll(reroll) if apply_modifiers else 0
                reroll_modifier_delta = 0
            roll, total, outcome = _apply_outcome(
                reroll,
                shift=reroll_shift,
                extra_modifier=int(reroll_modifier_delta or 0) if apply_modifiers else 0,
            )
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

    if effective_skill_id in (Skill.FORTITUDE.value, Skill.REFLEX.value, Skill.WILL.value):
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
                f"{'; '.join(notes) if notes else ''}"
            )
            all_lines = format_effects_log(_effects, skill_id)
            if all_lines:
                game.ui_log(f"{skill_id}: premie/kary: {', '.join(all_lines)}.")
            if resolved_base_modifier:
                game.ui_log(f"{skill_id}: modyfikator bazowy: {resolved_base_modifier:+d}.")
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
            from GameObjects.items.armor import bulwark_reflex_bonus

            bulwark_bonus = int(bulwark_reflex_bonus(actor, tags=tags) or 0)
        except Exception:
            bulwark_bonus = 0
        if bulwark_bonus > 0:
            all_effects.append(
                BonusEffect(
                    type=BonusType.ITEM,
                    value=bulwark_bonus,
                    tag=Skill.REFLEX.value,
                    source="armor:bulwark",
                    label="bulwark",
                )
            )
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

    if skill_id in (Skill.STEALTH.value, Skill.ACROBATICS.value, Skill.ATHLETICS.value):
        try:
            from GameObjects.items.armor import armor_skill_check_penalty

            armor_penalty = int(armor_skill_check_penalty(actor, skill_id=skill_id) or 0)
        except Exception:
            armor_penalty = 0
        if armor_penalty > 0:
            all_effects.append(
                BonusEffect(
                    type=BonusType.ITEM,
                    value=armor_penalty,
                    tag=skill_id,
                    source="armor:check_penalty",
                    label="armor check penalty",
                    is_penalty=True,
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
        from statuses.pf2_conditions import skill_penalty_value, skill_penalty_breakdown_label

        extra_penalty = int(skill_penalty_value(actor, skill_id=skill_id, tags=tags) or 0)
        extra_penalty_label = str(skill_penalty_breakdown_label(actor, skill_id=skill_id, tags=tags) or "conditions")
    except Exception:
        extra_penalty = 0
        extra_penalty_label = "conditions"
    if extra_penalty > 0:
        all_effects.append(
            BonusEffect(
                type=BonusType.STATUS,
                value=extra_penalty,
                tag=skill_id,
                source="status:pf2_condition_penalty",
                label=extra_penalty_label,
                is_penalty=True,
            )
        )

    is_recall_knowledge = _is_recall_knowledge(tags)
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
    resolved_base_modifier, _base_components = _resolve_base_modifier_components(actor, skill_id, int(base_modifier or 0))
    modifier, breakdown, notes, _ps, _ds, _pt, _dt, _cs, _ct, _effects = _collect_modifier_data(
        skill_id=skill_id,
        tags=tags,
        actor=actor,
        target=target,
        base_modifier=resolved_base_modifier,
    )
    return modifier, breakdown, notes
