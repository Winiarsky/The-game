from __future__ import annotations

import logging
from typing import Iterable

from board import consts
from combat.stealth_runtime import clear_combat_stealth, has_combat_stealth_state
from GameObjects.interactions_mixin import prompt_for_roll
from GameObjects.interactions_mixin.skill_check_resolver import compute_skill_modifier_with_sources
from GameObjects.companions.support_runtime import apply_spell_attack_animal_companion_support
from bonuses import BonusType, build_modifiers_grid
from combat import ac_with_bonuses
from combat.degree_of_success import is_critical_success, is_hit, natural_shift_from_roll, resolve_outcome
from character_creation.catalog import CLASS_KEY_ABILITY_DEFAULT
from character_creation.mechanics import RANK_BONUS, proficiency_bonus
from led_fx import animate_projectile_line
from skills import Skill

from ..base import EventContext, EventResult
from ..attack.attack_base import check_concealed
from .magic_event import MagicEvent
from .magic_utils import pick_target_in_range
from statuses.familiar import FAMILIAR_TOUCH_DELIVERY_STATUS

logger = logging.getLogger(__name__)

_SPELLCASTING_PROGRESSION_BY_CLASS: dict[str, tuple[tuple[int, str], ...]] = {
    "bard": ((1, "trained"), (7, "expert"), (15, "master"), (19, "legendary")),
    "cleric": ((1, "trained"), (7, "expert"), (15, "master"), (19, "legendary")),
    "druid": ((1, "trained"), (7, "expert"), (15, "master"), (19, "legendary")),
    "sorcerer": ((1, "trained"), (7, "expert"), (15, "master"), (19, "legendary")),
    "wizard": ((1, "trained"), (7, "expert"), (15, "master"), (19, "legendary")),
}


def _normalize_token(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _status_payload(actor, status_id: str) -> dict:
    normalized_status = _normalize_token(status_id)
    getter = getattr(actor, "get_status_data", None)
    if callable(getter):
        try:
            raw = getter(normalized_status, f"{normalized_status}_setup", {})
            if isinstance(raw, dict):
                return dict(raw)
        except Exception:
            pass
    for status in list(getattr(actor, "statuses", []) or []):
        if _normalize_token(getattr(status, "id", "")) != normalized_status:
            continue
        data = getattr(status, "data", None) or {}
        if isinstance(data, dict):
            setup = data.get(f"{normalized_status}_setup")
            if isinstance(setup, dict):
                return dict(setup)
    return {}


def _actor_spellcasting_class(actor) -> str:
    direct = _normalize_token(getattr(actor, "class_name", None))
    if direct in _SPELLCASTING_PROGRESSION_BY_CLASS:
        return direct
    for class_id in _SPELLCASTING_PROGRESSION_BY_CLASS:
        if _status_payload(actor, class_id):
            return class_id
        if any(_normalize_token(getattr(status, "id", "")) == class_id for status in list(getattr(actor, "statuses", []) or [])):
            return class_id
    return direct


def _actor_spellcasting_key_ability(actor) -> str:
    class_id = _actor_spellcasting_class(actor)
    if not class_id:
        return ""
    setup = _status_payload(actor, class_id)
    candidates = (
        setup.get("key_ability"),
        getattr(actor, f"{class_id}_key_ability", None),
        CLASS_KEY_ABILITY_DEFAULT.get(class_id),
    )
    for raw in candidates:
        normalized = _normalize_token(raw)
        if normalized:
            return normalized
    return ""


def _actor_ability_modifier(actor, ability_id: str) -> int:
    ability_key = _normalize_token(ability_id)
    if not ability_key:
        return 0
    ability_modifiers = getattr(actor, "ability_modifiers", None)
    if isinstance(ability_modifiers, dict):
        try:
            return int(ability_modifiers.get(ability_key, 0) or 0)
        except Exception:
            return 0
    aliases = {
        "strength": ("str_mod", "strength_mod"),
        "dexterity": ("dex_mod", "dexterity_mod"),
        "constitution": ("con_mod", "constitution_mod"),
        "intelligence": ("int_mod", "intelligence_mod"),
        "wisdom": ("wis_mod", "wisdom_mod"),
        "charisma": ("cha_mod", "charisma_mod"),
    }
    for attr in aliases.get(ability_key, ()):
        try:
            return int(getattr(actor, attr, 0) or 0)
        except Exception:
            continue
    return 0


def _actor_level(actor) -> int:
    try:
        return max(1, int(getattr(actor, "level", 1) or 1))
    except Exception:
        return 1


def _spellcasting_rank_for_actor(actor) -> str:
    class_id = _actor_spellcasting_class(actor)
    progression = _SPELLCASTING_PROGRESSION_BY_CLASS.get(class_id)
    if not progression:
        return "untrained"
    level = _actor_level(actor)
    rank = "untrained"
    for threshold, candidate in progression:
        if level >= int(threshold):
            rank = str(candidate)
    return str(rank)


def _effect_signed_value(effect) -> int:
    try:
        value = int(getattr(effect, "value", 0) or 0)
    except Exception:
        value = 0
    is_penalty = bool(getattr(effect, "is_penalty", False) or value < 0)
    return -abs(value) if is_penalty else abs(value)


def _effect_label(effect) -> str:
    return str(getattr(effect, "label", None) or getattr(effect, "source", None) or getattr(effect, "tag", "mod") or "mod")


def _default_spell_attack_modifier_tags(action_tag: str, *, include_attack_ranged: bool = False) -> list[str]:
    tags = []
    normalized = _normalize_token(action_tag)
    for tag in (normalized, "spell_attack", "magic"):
        if tag and tag not in tags:
            tags.append(tag)
    if include_attack_ranged and "attack_ranged" not in tags:
        tags.append("attack_ranged")
    return tags


def _default_spell_dc_modifier_tags(action_tag: str) -> list[str]:
    tags = []
    normalized = _normalize_token(action_tag)
    for tag in (normalized, "spell_dc", "magic"):
        if tag and tag not in tags:
            tags.append(tag)
    return tags


def _effect_spellcasting_scope(effect) -> str:
    source = _normalize_token(getattr(effect, "source", None))
    label = _normalize_token(getattr(effect, "label", None))
    combined = f"{source} {label}".strip()
    has_attack = "spell_attack" in combined
    has_dc = "spell_dc" in combined
    if has_attack and not has_dc:
        return "spell_attack"
    if has_dc and not has_attack:
        return "spell_dc"
    return "generic"


def _matched_effects_for_tags(effects, tags: list[str], target_id: str | None, *, expected_scope: str | None = None):
    matched = []
    seen = set()
    for effect in list(effects or []):
        scope = _effect_spellcasting_scope(effect)
        if expected_scope and scope not in {expected_scope, "generic"}:
            continue
        if not any(bool(getattr(effect, "matches", lambda *_a, **_k: False)(tag, target_id)) for tag in tags):
            continue
        marker = id(effect)
        if marker in seen:
            continue
        seen.add(marker)
        matched.append(effect)
    return matched


def _select_best_effects_for_tags(effects, tags: list[str], target_id: str | None, *, expected_scope: str | None = None):
    matched = _matched_effects_for_tags(effects, tags, target_id, expected_scope=expected_scope)
    if not matched:
        return []
    grouped: dict[BonusType, list] = {}
    for effect in matched:
        grouped.setdefault(getattr(effect, "type", BonusType.CIRCUMSTANCE), []).append(effect)
    selected = []
    for bonus_type, items in grouped.items():
        bonuses = [item for item in items if _effect_signed_value(item) >= 0]
        penalties = [item for item in items if _effect_signed_value(item) < 0]
        if bonuses:
            selected.append(max(bonuses, key=lambda item: abs(_effect_signed_value(item))))
        if penalties:
            selected.append(max(penalties, key=lambda item: abs(_effect_signed_value(item))))
    order = {BonusType.CIRCUMSTANCE: 0, BonusType.STATUS: 1, BonusType.ITEM: 2}
    return sorted(
        selected,
        key=lambda item: (
            order.get(getattr(item, "type", BonusType.CIRCUMSTANCE), 99),
            1 if _effect_signed_value(item) < 0 else 0,
            _effect_label(item),
        ),
    )


def _selected_effect_log_lines(selected_effects) -> list[str]:
    lines = []
    for effect in list(selected_effects or []):
        signed = _effect_signed_value(effect)
        if signed == 0:
            continue
        sign = "+" if signed >= 0 else ""
        bonus_type = getattr(effect, "type", BonusType.CIRCUMSTANCE)
        lines.append(f"{sign}{signed} {bonus_type.value} ({_effect_label(effect)})")
    return lines


def _selected_effect_components(selected_effects) -> list[dict]:
    components = []
    label_prefix = {
        BonusType.CIRCUMSTANCE: "Okoliczności",
        BonusType.STATUS: "Status",
        BonusType.ITEM: "Przedmiot",
    }
    for idx, effect in enumerate(list(selected_effects or []), start=1):
        signed = _effect_signed_value(effect)
        if signed == 0:
            continue
        bonus_type = getattr(effect, "type", BonusType.CIRCUMSTANCE)
        source_label = _effect_label(effect)
        components.append(
            {
                "id": f"{bonus_type.value}_{idx}",
                "label": f"{label_prefix.get(bonus_type, 'Modyfikator')}: {source_label}",
                "value": int(signed),
                "description": f"Automatycznie wykryty {bonus_type.value} modifier.",
                "editable": True,
            }
        )
    return components


def _spellcasting_base_components(actor) -> tuple[int, list[dict]]:
    class_id = _actor_spellcasting_class(actor)
    rank = _spellcasting_rank_for_actor(actor)
    level = _actor_level(actor)
    key_ability = _actor_spellcasting_key_ability(actor)
    rank_bonus = int(RANK_BONUS.get(str(rank), 0) or 0)
    proficiency = proficiency_bonus(level, rank)
    key_modifier = _actor_ability_modifier(actor, key_ability)
    components = []
    if class_id:
        components.append(
            {
                "id": "spellcasting_proficiency",
                "label": "Biegłość spellcastingu",
                "value": int(proficiency),
                "description": f"Poziom {level} + {str(rank).title()} ({rank_bonus:+d}).",
                "editable": False,
            }
        )
    if key_ability:
        components.append(
            {
                "id": "spellcasting_key_ability",
                "label": f"Key Ability: {key_ability[:3].upper()}",
                "value": int(key_modifier),
                "description": "Modyfikator cechy kluczowej dla tej klasy czarującej.",
                "editable": False,
            }
        )
    return int(proficiency + key_modifier), components


def _spell_attack_breakdown(actor, *, action_tag: str = "magic", target=None, extra_effects=None, modifier_tags=None):
    effects = list(getattr(actor, "bonuses", [])) if hasattr(actor, "bonuses") else []
    if extra_effects:
        effects.extend(list(extra_effects))
    target_id = getattr(target, "object_id", None)
    tags = [tag for tag in list(modifier_tags or []) if _normalize_token(tag)]
    if not tags:
        tags = _default_spell_attack_modifier_tags(action_tag)
    base_modifier, base_components = _spellcasting_base_components(actor)
    expected_scope = "spell_dc" if "spell_dc" in tags else "spell_attack"
    best_effects = _select_best_effects_for_tags(effects, tags, target_id, expected_scope=expected_scope)
    situational_modifier = sum(_effect_signed_value(effect) for effect in best_effects)
    return {
        "modifier": int(base_modifier + situational_modifier),
        "base_modifier": int(base_modifier),
        "components": list(base_components) + _selected_effect_components(best_effects),
        "best_effects": best_effects,
        "log_lines": _selected_effect_log_lines(best_effects),
    }


def spell_attack_modifier_details(actor, *, action_tag: str = "magic", target=None, extra_effects=None, modifier_tags=None):
    breakdown = _spell_attack_breakdown(
        actor,
        action_tag=action_tag,
        target=target,
        extra_effects=extra_effects,
        modifier_tags=modifier_tags,
    )
    return int(breakdown["modifier"]), list(breakdown["best_effects"]), list(breakdown["log_lines"])


def spell_dc_details(actor, *, action_tag: str = "magic", target=None, extra_effects=None) -> tuple[int, int, list, list[str]]:
    breakdown = _spell_attack_breakdown(
        actor,
        action_tag=action_tag,
        target=target,
        extra_effects=extra_effects,
        modifier_tags=_default_spell_dc_modifier_tags(action_tag),
    )
    modifier = int(breakdown["modifier"])
    best_effects = list(breakdown["best_effects"])
    log_lines = list(breakdown["log_lines"])
    return 10 + int(modifier), int(modifier), best_effects, log_lines


def prompt_spell_attack_roll(
    *,
    actor,
    target,
    target_ac: int,
    action_tag: str = "magic",
    prompt_text: str | None = None,
    subtitle: str | None = None,
    extra_effects=None,
    game=None,
    modifier_tags=None,
):
    breakdown = _spell_attack_breakdown(
        actor,
        action_tag=action_tag,
        target=target,
        extra_effects=extra_effects,
        modifier_tags=modifier_tags,
    )
    modifier = int(breakdown["modifier"])
    best_effects = list(breakdown["best_effects"])
    log_lines = list(breakdown["log_lines"])
    components = list(breakdown["components"])
    if log_lines and game is not None:
        try:
            game.ui_log(f"Modyfikatory ({action_tag}): {', '.join(log_lines)}.")
        except Exception:
            pass
    roll_data = prompt_for_roll(
        prompt_text or f"Atak zaklęciem przeciwko AC {target_ac}",
        layout="test",
        subtitle=subtitle,
        prompt_long="Gra dolicza automatycznie biegłość spellcastingu, key ability i zapisane premie/kary.",
        modifiers=build_modifiers_grid(best_effects),
        roll_stack={
            "components": list(components),
            "auto_total_modifier": int(modifier or 0),
        },
        auto_total_modifier=int(modifier or 0),
        answer_placeholder="Wynik k20",
        return_details=True,
        infer_natural_from_roll=True,
    )
    if isinstance(roll_data, dict):
        roll = int(roll_data.get("roll", 0) or 0)
        natural_shift = int(roll_data.get("natural_shift", 0) or 0)
        if natural_shift == 0:
            raw_roll = int(roll_data.get("raw_roll", roll) or roll)
            natural_shift = natural_shift_from_roll(raw_roll)
        modifier_delta = int(roll_data.get("modifier_delta", 0) or 0)
    else:
        roll = int(roll_data or 0)
        natural_shift = natural_shift_from_roll(roll)
        modifier_delta = 0
    total_roll = int(roll) + int(modifier) + int(modifier_delta)
    outcome = resolve_outcome(total_roll, int(target_ac), natural_shift=natural_shift)
    return {
        "roll": int(roll),
        "modifier": int(modifier),
        "modifier_delta": int(modifier_delta),
        "total": int(total_roll),
        "outcome": str(outcome),
        "critical": bool(is_critical_success(outcome)),
        "hit": bool(is_hit(outcome)),
    }


def _save_prompt_label(skill_id: str) -> str:
    normalized = str(skill_id or "").strip().lower()
    if normalized == Skill.FORTITUDE.value:
        return "Fortitude"
    if normalized == Skill.REFLEX.value:
        return "Reflex"
    if normalized == Skill.WILL.value:
        return "Will"
    return normalized.replace("_", " ").strip().title() or "Save"


def prompt_spell_save_roll(
    *,
    target,
    skill_id: str,
    dc: int,
    attacker=None,
    tags: list[str] | None = None,
    prompt_text: str | None = None,
):
    tags = list(tags or [])
    base_bonus = 0
    if skill_id == Skill.WILL.value:
        base_bonus = int(getattr(target, "will_bonus", 0) or 0)
    elif skill_id == Skill.FORTITUDE.value:
        base_bonus = int(getattr(target, "fortitude_bonus", 0) or 0)
    elif skill_id == Skill.REFLEX.value:
        base_bonus = int(getattr(target, "reflex_bonus", 0) or 0)

    modifier, breakdown, notes = compute_skill_modifier_with_sources(
        skill_id=skill_id,
        actor=target,
        target=attacker,
        tags=tags,
        base_modifier=base_bonus,
    )
    save_label = _save_prompt_label(skill_id)
    subtitle = f"{getattr(target, 'name', 'Cel')} · {save_label} save vs DC {int(dc)}"
    summary_parts = []
    if breakdown:
        summary_parts.append("Modyfikatory: " + ", ".join(str(item) for item in breakdown if str(item)))
    if notes:
        summary_parts.append("Uwagi: " + ", ".join(str(item) for item in notes if str(item)))
    roll_data = prompt_for_roll(
        prompt_text or f"{save_label} save przeciw DC {int(dc)}",
        layout="test",
        subtitle=subtitle,
        prompt_long="\n".join(summary_parts) if summary_parts else None,
        roll_stack={
            "components": [
                {
                    "id": skill_id,
                    "label": f"{save_label} save",
                    "value": int(modifier or 0),
                    "description": f"Łączny modyfikator obronny {save_label}.",
                    "editable": True,
                }
            ],
            "auto_total_modifier": int(modifier or 0),
        },
        auto_total_modifier=int(modifier or 0),
        answer_placeholder="Wynik k20",
        return_details=True,
        infer_natural_from_roll=True,
    )
    if isinstance(roll_data, dict):
        roll = int(roll_data.get("roll", 0) or 0)
        natural_shift = int(roll_data.get("natural_shift", 0) or 0)
        if natural_shift == 0:
            raw_roll = int(roll_data.get("raw_roll", roll) or roll)
            natural_shift = natural_shift_from_roll(raw_roll)
        modifier_delta = int(roll_data.get("modifier_delta", 0) or 0)
    else:
        roll = int(roll_data or 0)
        natural_shift = natural_shift_from_roll(roll)
        modifier_delta = 0
    total = int(roll) + int(modifier) + int(modifier_delta)
    outcome = resolve_outcome(total, int(dc), natural_shift=natural_shift)
    return str(outcome), int(roll), int(total)


class BaseMagicAttackEvent(MagicEvent):
    """Bazowa klasa dla ataków magicznych wymagających wyboru celu."""

    target_kind: str = "enemy"  # enemy | hero | any
    range_feet: int | None = 30
    default_tags = ["magic", "spell"]
    projectile_trail_rgb = [40, 100, 160]
    projectile_head_rgb = [120, 220, 255]
    projectile_impact_rgb = [210, 245, 255]
    projectile_palette = consts.MAGIC_PROJECTILE_PALETTE

    def _resolve_on_target(self, target, pos, ctx: EventContext, *, critical: bool = False) -> EventResult:
        """Zaimplementuj w klasach pochodnych faktyczny efekt czaru."""
        raise NotImplementedError

    def _play_projectile_animation(self, game, start: tuple[int, int] | None, end: tuple[int, int] | None) -> None:
        try:
            animate_projectile_line(
                getattr(game, "conn", None),
                start,
                end,
                trail_color=self.projectile_trail_rgb,
                head_color=self.projectile_head_rgb,
                impact_color=self.projectile_impact_rgb,
                palette=self.projectile_palette,
            )
        except Exception:
            logger.debug("Nie udało się odtworzyć animacji zaklęcia.", exc_info=True)

    def _iter_candidates(self, game) -> Iterable[tuple[object, tuple[int, int] | None, str]]:
        if self.target_kind == "hero":
            for hero in getattr(game, "heroes", []):
                yield hero, getattr(hero, "position", None), "hero"
        elif self.target_kind == "any":
            for hero in getattr(game, "heroes", []):
                yield hero, getattr(hero, "position", None), "hero"
            for enemy in getattr(game, "enemies", []):
                yield enemy, getattr(enemy, "position", None), "enemy"
        else:  # default enemy
            for enemy in getattr(game, "enemies", []):
                yield enemy, getattr(enemy, "position", None), "enemy"

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak aktywnego bohatera do rzucenia czaru.")
        source_pos = getattr(actor, "position", None)
        if source_pos is None:
            return EventResult.cancelled(message="Bohater nie stoi na planszy.")

        candidates = list(self._iter_candidates(ctx.game))
        max_range = self.range_feet
        consume_touch_delivery = False
        if max_range == 5 and self._has_status(actor, FAMILIAR_TOUCH_DELIVERY_STATUS):
            max_range = 10
            consume_touch_delivery = True
        selection = pick_target_in_range(
            ctx,
            source_pos,
            candidates,
            max_range_feet=max_range,
            allowed_kinds=("enemy", "hero") if self.target_kind == "any" else (self.target_kind,),
            tags=self._effective_tags(ctx),
            allow_guess_undetected=True,
            return_selection_details=True,
        )
        if isinstance(selection, tuple) and len(selection) == 2:
            target, target_pos = selection
            if target is None or target_pos is None:
                selection = {"kind": "cancel"}
            else:
                selection = {"kind": "target", "target": target, "pos": target_pos, "guessed": False}
        if str(selection.get("kind", "")) == "cancel":
            return EventResult.cancelled(message="Brak celu w zasięgu.")

        target = selection.get("target")
        target_pos = selection.get("pos")
        if consume_touch_delivery:
            try:
                actor.remove_status(FAMILIAR_TOUCH_DELIVERY_STATUS)
            except Exception:
                pass
        if str(selection.get("kind", "")) == "miss":
            guessed_pos = selection.get("pos")
            self._play_projectile_animation(ctx.game, source_pos, guessed_pos)
            return EventResult(
                success=True,
                consumed_action=self.consumes_action,
                message="Czar chybia: błędnie wskazane pole dla undetected celu.",
                data={
                    "target": None,
                    "target_pos": guessed_pos,
                    "spell_attack_hit": False,
                    "spell_attack_outcome": "wrong_square",
                    "guessed_target_square": guessed_pos,
                },
            )
        if target is None or target_pos is None:
            return EventResult.cancelled(message="Brak celu w zasięgu.")

        if not check_concealed(ctx, target):
            self._play_projectile_animation(ctx.game, source_pos, target_pos)
            return EventResult(
                success=True,
                consumed_action=self.consumes_action,
                message="Czar chybia (concealed).",
                data={
                    "target": target,
                    "spell_attack_hit": False,
                    "spell_attack_outcome": "failure",
                },
            )

        target_ac, base_ac, modifier = self._target_ac_with_bonuses(target, attacker=actor)
        modifier_note = ""
        if modifier:
            sign = "+" if modifier > 0 else ""
            modifier_note = f" (bazowe {base_ac}, modyfikatory {sign}{modifier})"
        effective_tags = list(self._effective_tags(ctx) or [])
        action_tag = "magic"
        extra_effects = []
        try:
            from statuses import attack_penalty_effects, clumsy_attack_penalty_effects

            extra_effects.extend(attack_penalty_effects(actor, action_tag="magic"))
            if "attack_ranged" in effective_tags:
                extra_effects.extend(
                    clumsy_attack_penalty_effects(
                        actor,
                        action_tag="attack_ranged",
                        is_ranged=True,
                        is_finesse=False,
                    )
                )
        except Exception:
            pass
        attack_result = prompt_spell_attack_roll(
            actor=actor,
            target=target,
            target_ac=target_ac,
            action_tag=action_tag,
            prompt_text=f"Atak zaklęciem przeciwko AC {target_ac}",
            subtitle=f"bazowe {base_ac}{modifier_note}",
            extra_effects=extra_effects,
            game=getattr(ctx, "game", None),
            modifier_tags=_default_spell_attack_modifier_tags(
                action_tag,
                include_attack_ranged=("attack_ranged" in effective_tags),
            ),
        )
        outcome = str(attack_result.get("outcome", "failure"))
        critical = bool(attack_result.get("critical"))
        hit = bool(attack_result.get("hit"))
        self._play_projectile_animation(ctx.game, source_pos, target_pos)
        if not hit:
            return EventResult(
                success=True,
                consumed_action=self.consumes_action,
                message="Czar chybia.",
                data={
                    "target": target,
                    "spell_attack_hit": False,
                    "spell_attack_outcome": str(outcome),
                },
            )

        self._maybe_prompt_vengeful_hatred(actor, target)
        result = self._resolve_on_target(target, target_pos, ctx, critical=critical)
        support_result = apply_spell_attack_animal_companion_support(
            ctx,
            actor,
            target,
            tags=self._effective_tags(ctx),
        )
        payload = dict(getattr(result, "data", None) or {})
        payload.setdefault("target", target)
        payload.setdefault("spell_attack_hit", True)
        payload.setdefault("spell_attack_outcome", str(outcome))
        if support_result.get("applied"):
            payload["animal_companion_support_applied"] = True
            payload["animal_companion_support_notes"] = list(support_result.get("notes") or [])
            if support_result.get("defeated"):
                payload["defeated"] = True
        result.data = payload
        if support_result.get("applied"):
            notes = [str(note) for note in list(support_result.get("notes") or []) if str(note)]
            if notes:
                base_message = str(getattr(result, "message", "") or "").strip()
                suffix = " ".join(notes)
                result.message = f"{base_message} {suffix}".strip()
        return result

    def post(self, ctx: EventContext, result: EventResult) -> None:
        if not bool(getattr(result, "success", False)):
            return
        actor = getattr(ctx, "actor", None)
        game = getattr(ctx, "game", None)
        if actor is None or game is None:
            return
        has_status = getattr(actor, "has_status", None)
        has_stealth = False
        if callable(has_status):
            try:
                has_stealth = bool(has_status("stealth"))
            except Exception:
                has_stealth = False
        if not has_combat_stealth_state(actor) and not has_stealth:
            return
        clear_combat_stealth(actor, clear_stealth=True, add_observable=True)
        try:
            ui_log = getattr(game, "ui_log", None)
            if callable(ui_log):
                ui_log("Atak z ukrycia ujawnia twoją pozycję.")
            ui_hero = getattr(game, "ui_hero", None)
            if callable(ui_hero):
                ui_hero(actor, note="Atak ujawnia twoją pozycję")
            ui_active = getattr(game, "ui_active_actor", None)
            if callable(ui_active):
                ui_active(actor)
        except Exception:
            logger.debug("Nie udało się odświeżyć UI po ataku zaklęciem z ukrycia.", exc_info=True)

    @staticmethod
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

    # --- helpers ---
    def _target_ac_with_bonuses(self, target, *, attacker=None) -> tuple[int, int, int]:
        return ac_with_bonuses(target, attacker=attacker, include_magic=True)

    def _attacker_modifier(self, attacker, action_tag: str, target=None) -> int:
        compute = getattr(attacker, "compute_modifier", None)
        if callable(compute):
            try:
                return int(compute(action_tag, target=target))
            except Exception:
                logger.debug("Nie udało się policzyć compute_modifier dla %s", action_tag, exc_info=True)
        return 0

    def _attack_modifier_details(self, attacker, action_tag: str, target=None, extra_effects=None):
        return spell_attack_modifier_details(
            attacker,
            action_tag=action_tag,
            target=target,
            extra_effects=extra_effects,
        )

    def _format_bonus_info(self, attacker, action_tag: str, target=None) -> str:
        formatter = getattr(attacker, "format_prompt", None)
        if not callable(formatter):
            return ""
        try:
            formatted = formatter(action_tag, target=target)
            return f"\nModyfikatory ({action_tag}):\n{formatted}\n" if formatted else ""
        except Exception:
            logger.debug("format_prompt nie powiódł się dla %s", action_tag, exc_info=True)
            return ""

    def _maybe_prompt_vengeful_hatred(self, attacker, target) -> None:
        """Pokaż informację o +1 do obrażeń vs wybrany typ przeciwnika (bez naliczania)."""
        getter = getattr(attacker, "get_status_data", None)
        if callable(getter):
            enemy_type = getter("vengeful_hatred", "enemy_type", None)
            bonus = getter("vengeful_hatred", "damage_bonus", 1)
        else:
            enemy_type = None
            bonus = 1
            for status in getattr(attacker, "statuses", []) or []:
                if getattr(status, "id", None) != "vengeful_hatred":
                    continue
                data = getattr(status, "data", {}) or {}
                enemy_type = data.get("enemy_type")
                bonus = data.get("damage_bonus", 1)
                break
        if not enemy_type:
            return
        target_type = getattr(target, "enemy_type", None)
        if target_type is None:
            return
        enemy_type_norm = getattr(enemy_type, "value", enemy_type)
        target_type_norm = getattr(target_type, "value", target_type)
        if enemy_type_norm != target_type_norm:
            return
        try:
            from ui_client import get_ui_client

            get_ui_client().prompt_info(
                "Vengeful Hatred",
                prompt_long=(
                    f"Bonus do obrazen +{int(bonus)} vs {enemy_type_norm}. "
                    "Dodaj recznie do wyniku."
                ),
                source="vengeful_hatred",
            )
        except Exception:
            return
