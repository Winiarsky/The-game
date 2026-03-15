from __future__ import annotations

import logging
from typing import Iterable

from GameObjects.interactions_mixin import prompt_for_roll
from bonuses import build_modifiers_grid, compute_total_modifier, format_effects_log, select_best_effects
from combat import ac_with_bonuses
from combat.degree_of_success import is_critical_success, is_hit, natural_shift_from_roll, resolve_outcome

from ..base import EventContext, EventResult
from ..attack.attack_base import check_concealed
from .magic_event import MagicEvent
from .magic_utils import pick_target_in_range
from statuses.familiar import FAMILIAR_TOUCH_DELIVERY_STATUS

logger = logging.getLogger(__name__)


class BaseMagicAttackEvent(MagicEvent):
    """Bazowa klasa dla ataków magicznych wymagających wyboru celu."""

    target_kind: str = "enemy"  # enemy | hero | any
    range_feet: int | None = 30
    default_tags = ["magic", "spell"]

    def _resolve_on_target(self, target, pos, ctx: EventContext, *, critical: bool = False) -> EventResult:
        """Zaimplementuj w klasach pochodnych faktyczny efekt czaru."""
        raise NotImplementedError

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
        target, target_pos = pick_target_in_range(
            ctx,
            source_pos,
            candidates,
            max_range_feet=max_range,
            allowed_kinds=("enemy", "hero") if self.target_kind == "any" else (self.target_kind,),
            tags=self._effective_tags(ctx),
        )
        if target is None or target_pos is None:
            return EventResult.cancelled(message="Brak celu w zasięgu.")
        if consume_touch_delivery:
            try:
                actor.remove_status(FAMILIAR_TOUCH_DELIVERY_STATUS)
            except Exception:
                pass

        if not check_concealed(ctx, target):
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
        action_tag = (self._effective_tags(ctx) or ["spell_attack"])[0]
        extra_effects = []
        try:
            from statuses import enfeebled_attack_penalty_effects

            extra_effects.extend(enfeebled_attack_penalty_effects(actor, action_tag))
        except Exception:
            pass
        modifier, best_effects, log_lines = self._attack_modifier_details(actor, action_tag, target=target)
        if extra_effects:
            modifier, best_effects, log_lines = self._attack_modifier_details(
                actor,
                action_tag,
                target=target,
                extra_effects=extra_effects,
            )
        if log_lines:
            try:
                ctx.game.ui_log(f"Modyfikatory ({action_tag}): {', '.join(log_lines)}.")
            except Exception:
                pass
        prompt_long = f"Modyfikator łączny: {modifier:+d} (doliczany automatycznie)."

        roll_data = prompt_for_roll(
            f"Atak zaklęciem przeciwko AC {target_ac}",
            layout="test",
            subtitle=f"bazowe {base_ac}{modifier_note}",
            prompt_long=prompt_long,
            modifiers=build_modifiers_grid(best_effects),
            roll_stack={
                "components": [
                    {
                        "id": "spell_attack",
                        "label": "Atak czarem",
                        "value": int(modifier or 0),
                        "description": "Łączny modyfikator ataku magicznego.",
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
        total_roll = roll + modifier + modifier_delta
        outcome = resolve_outcome(total_roll, target_ac, natural_shift=natural_shift)
        critical = is_critical_success(outcome)
        hit = is_hit(outcome)
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
        payload = dict(getattr(result, "data", None) or {})
        payload.setdefault("target", target)
        payload.setdefault("spell_attack_hit", True)
        payload.setdefault("spell_attack_outcome", str(outcome))
        result.data = payload
        return result

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
        effects = list(getattr(attacker, "bonuses", [])) if hasattr(attacker, "bonuses") else []
        if extra_effects:
            effects.extend(list(extra_effects))
        target_id = getattr(target, "object_id", None)
        modifier = compute_total_modifier(effects, action_tag, target_id) if effects else 0
        best_effects = select_best_effects(effects, action_tag, target_id)
        log_lines = format_effects_log(effects, action_tag, target_id)
        return modifier, best_effects, log_lines

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
