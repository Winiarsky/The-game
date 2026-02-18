from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any

from GameObjects.interactions_mixin import prompt_for_roll
from combat.damage_utils import burn_it_bonus, burn_it_prompt_note
from combat.flanking import effective_ac
from .base import Reaction

logger = logging.getLogger(__name__)


def _has_status(actor, status_id: str) -> bool:
    """Sprawdź status zarówno przez has_status, jak i listę statuses."""
    if hasattr(actor, "has_status"):
        try:
            return bool(actor.has_status(status_id))
        except Exception:
            return False
    statuses = getattr(actor, "statuses", None)
    if isinstance(statuses, list):
        return any(getattr(s, "id", s) == status_id for s in statuses)
    return False


def _is_leaving_reach(event: dict[str, Any]) -> bool:
    if event.get("leaving_reach"):
        return True
    return False


def _has_trigger_tag(event: dict[str, Any]) -> tuple[bool, str | None]:
    tags = set(event.get("action_tags") or [])
    for tag in ("manipulate", "move", "ranged_attack"):
        if tag in tags:
            return True, tag
    return False, None


@dataclass
class OpportunityAttack(Reaction):
    """Reakcja PF2: OA bez MAP, na move/manipulate/ranged, lub opuszczenie pola w reach."""

    id: str = "opportunity_attack"
    label: str = "Atak okazyjny"

    def triggers(self, actor, event: dict[str, Any]) -> bool:
        if not _has_status(actor, "opportunity_attack"):
            return False
        target = event.get("actor")
        if target is None or target is actor:
            return False
        tagged, _tag = _has_trigger_tag(event)
        if tagged or _is_leaving_reach(event):
            # reach sprawdzi dispatcher; tu tylko logika tagów
            return True
        return False

    def reason(self, actor, event: dict[str, Any]) -> str:
        tagged, tag = _has_trigger_tag(event)
        if tagged and tag:
            return f"cel używa akcji {tag}"
        if _is_leaving_reach(event):
            return "cel opuszcza twój zasięg"
        return "okazja do ataku"

    def _roll_attack(self, attacker, defender, game) -> tuple[int, int, bool]:
        """Zwróć (roll_total, d20, critical). MAP pomijamy."""
        attack_bonus = getattr(attacker, "attack_bonus", 0)
        d20 = random.randint(1, 20)
        total = d20 + attack_bonus
        target_ac = effective_ac(defender)
        crit = d20 == 20 or total >= target_ac + 10
        return total, target_ac, crit

    def _do_player_attack(self, hero, target, game) -> bool:
        """Obsłuż OA bohatera z promptem jak w normalnym ataku."""
        from actions.attack import _choose_damage_type  # lokalnie, by uniknąć cykli importów
        total, target_ac, crit = self._roll_attack(hero, target, game)
        msg = f"Atak okazyjny: r={total} vs AC {target_ac}"
        if game.ui:
            game.ui_log(msg)
        else:
            print(msg)
        if total < target_ac:
            return False

        dmg_type = _choose_damage_type(game)
        if dmg_type is None:
            return False
        note = burn_it_prompt_note(hero, dmg_type)
        amount = prompt_for_roll(
            f"Ile obrażeń {dmg_type} zadajesz (atak okazyjny)? ",
            layout="damage",
            answer_placeholder=f"Obrażenia {dmg_type}",
            prompt_long=note,
        )
        bonus = burn_it_bonus(hero, dmg_type)
        _, defeated = target.apply_damage(int(amount) + int(bonus), dmg_type)
        if defeated:
            try:
                pos = getattr(target, "position", None)
                if pos:
                    game.board.remove(pos)
                game.enemies.remove(target)
            except Exception:
                pass
            target.position = None
        return True

    def _do_enemy_attack(self, enemy, target, game, event) -> bool:
        """Uproszczony OA wroga: auto-rozstrzygnięcie jak w basic_melee."""
        total, target_ac, crit = self._roll_attack(enemy, target, game)
        msg = f"{getattr(enemy, 'name', 'wróg')} wykonuje atak okazyjny: r={total} vs AC {target_ac}"
        logger.info(msg)
        game.ui_log(msg)
        if total < target_ac:
            return False
        damage = random.randint(1, 6) + getattr(enemy, "strength", 0)
        try:
            target.wounds += damage  # type: ignore[attr-defined]
        except Exception:
            pass
        game.ui_log(f"Atak okazyjny zadaje {damage} obrażeń. Rany bohatera: {getattr(target, 'wounds', '?')}.")
        if crit and "manipulate" in (event.get("action_tags") or []):
            game.ui_log("Krytyk – akcja manipulate przerwana.")
        return True

    def execute(self, actor, event: dict[str, Any], ctx) -> bool:
        game = ctx.game
        target = event.get("actor")
        if target is None:
            return False
        if actor in getattr(game, "heroes", []):
            return self._do_player_attack(actor, target, game)
        return self._do_enemy_attack(actor, target, game, event)
