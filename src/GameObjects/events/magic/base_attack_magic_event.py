from __future__ import annotations

import logging
from typing import Iterable

from ui_client import get_ui_client
from bonuses import compute_total_modifier
from combat import effective_ac

from ..base import EventContext, EventResult
from .magic_event import MagicEvent
from .magic_utils import pick_target_in_range

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
        target, target_pos = pick_target_in_range(
            ctx,
            source_pos,
            candidates,
            max_range_feet=self.range_feet,
            allowed_kinds=("enemy", "hero") if self.target_kind == "any" else (self.target_kind,),
        )
        if target is None or target_pos is None:
            return EventResult.cancelled(message="Brak celu w zasięgu.")

        target_ac, base_ac, modifier = self._target_ac_with_bonuses(target, attacker=actor)
        modifier_note = ""
        if modifier:
            sign = "+" if modifier > 0 else ""
            modifier_note = f" (bazowe {base_ac}, modyfikatory {sign}{modifier})"
        action_tag = (self._effective_tags(ctx) or ["spell_attack"])[0]
        bonus_info = self._format_bonus_info(actor, action_tag, target=target)

        roll = get_ui_client().prompt_roll(
            f"Atak zaklęciem przeciwko AC {target_ac}",
            source="game",
            layout="test",
            subtitle=f"bazowe {base_ac}{modifier_note}",
            prompt_long=bonus_info.strip(),
            answer_placeholder="Wynik d20 + spell attack",
        )
        critical = roll >= target_ac + 10
        hit = roll >= target_ac
        if not hit:
            return EventResult(success=True, consumed_action=self.consumes_action, message="Czar chybia.")

        return self._resolve_on_target(target, target_pos, ctx, critical=critical)

    # --- helpers ---
    def _target_ac_with_bonuses(self, target, *, attacker=None) -> tuple[int, int, int]:
        base_ac = getattr(target, "ac", effective_ac(target))
        bonuses = list(getattr(target, "bonuses", [])) if hasattr(target, "bonuses") else []
        modifier = compute_total_modifier(bonuses, "ac", getattr(attacker, "object_id", None)) if bonuses else 0
        target_ac = base_ac + modifier
        return target_ac, base_ac, modifier

    def _attacker_modifier(self, attacker, action_tag: str, target=None) -> int:
        compute = getattr(attacker, "compute_modifier", None)
        if callable(compute):
            try:
                return int(compute(action_tag, target=target))
            except Exception:
                logger.debug("Nie udało się policzyć compute_modifier dla %s", action_tag, exc_info=True)
        return 0

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
