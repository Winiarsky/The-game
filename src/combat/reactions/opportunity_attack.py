from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any

from GameObjects.interactions_mixin import prompt_for_roll
from combat.damage_utils import burn_it_bonus, burn_it_prompt_note
from combat.degree_of_success import is_critical_success, is_hit, natural_shift_from_roll, resolve_outcome
from combat.flanking import effective_ac
from combat.hp_engine import apply_damage as hp_apply_damage
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
    priority: int = 10

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

    def _roll_attack(self, attacker, defender, game) -> tuple[int, int, bool, bool]:
        """Zwróć (roll_total, target_ac, critical, hit). MAP pomijamy."""
        attack_bonus = getattr(attacker, "attack_bonus", 0)
        d20 = random.randint(1, 20)
        total = d20 + attack_bonus
        target_ac = effective_ac(defender)
        natural_shift = natural_shift_from_roll(d20)
        outcome = resolve_outcome(total, target_ac, natural_shift=natural_shift)
        crit = is_critical_success(outcome)
        hit = is_hit(outcome)
        return total, target_ac, crit, hit

    def _do_player_attack(self, hero, target, game) -> tuple[bool, bool]:
        """Obsłuż OA bohatera z promptem jak w normalnym ataku.

        Zwraca `(executed, critical_hit)`.
        """
        from actions.attack import _choose_damage_type  # lokalnie, by uniknąć cykli importów
        total, target_ac, crit, hit = self._roll_attack(hero, target, game)
        msg = f"Atak okazyjny: r={total} vs AC {target_ac}"
        if game.ui:
            game.ui_log(msg)
        else:
            print(msg)
        if not hit:
            return True, False

        dmg_type = _choose_damage_type(game)
        if dmg_type is None:
            return False, False
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
        return True, bool(crit)

    def _do_enemy_attack(self, enemy, target, game, event) -> tuple[bool, bool]:
        """Uproszczony OA wroga: auto-rozstrzygnięcie jak w basic_melee.

        Zwraca `(executed, critical_hit)`.
        """
        total, target_ac, crit, hit = self._roll_attack(enemy, target, game)
        msg = f"{getattr(enemy, 'name', 'wróg')} wykonuje atak okazyjny: r={total} vs AC {target_ac}"
        logger.info(msg)
        game.ui_log(msg)
        if not hit:
            return True, False
        damage = random.randint(1, 6) + getattr(enemy, "strength", 0)
        defeated = False
        try:
            apply = getattr(target, "apply_damage", None)
            if callable(apply):
                _, defeated = apply(damage, "normal")
            else:
                info = hp_apply_damage(target, damage, "normal", source="reaction:opportunity_attack")
                defeated = bool(info.get("defeated", False))
        except Exception:
            pass
        game.ui_log(f"Atak okazyjny zadaje {damage} obrażeń.")
        if defeated:
            try:
                game.ui_log(f"{getattr(target, 'name', 'Cel')} pada od ataku okazyjnego.")
            except Exception:
                pass
        if crit and "manipulate" in (event.get("action_tags") or []):
            game.ui_log("Krytyk – akcja manipulate przerwana.")
        return True, bool(crit)

    def execute(self, actor, event: dict[str, Any], ctx) -> bool:
        game = ctx.game
        target = event.get("actor")
        if target is None:
            return False
        tags = set(event.get("action_tags") or [])
        if actor in getattr(game, "heroes", []):
            executed, crit = self._do_player_attack(actor, target, game)
            if executed and crit and "manipulate" in tags:
                event["disrupted"] = True
                event["disruption_reason"] = "opportunity_attack_critical_manipulate"
            return executed
        executed, crit = self._do_enemy_attack(actor, target, game, event)
        if executed and crit and "manipulate" in tags:
            event["disrupted"] = True
            event["disruption_reason"] = "opportunity_attack_critical_manipulate"
        return executed
