from __future__ import annotations

import logging

from board import consts
from bonuses import BonusEffect, BonusType
from skills import Skill
from GameObjects.interactions_mixin import resolve_skill_check_with_sources, compute_skill_modifier_with_sources

from .base import EventContext, EventResult, ActionCostEvent
from .registry import register_event
from .attack.basic_melee_attack_event import BasicMeleeAttackEvent
from .weapon_trait_utils import best_reach_ft_for_trait, enemies_in_reach

logger = logging.getLogger(__name__)


def _save_dc(target, skill_id: str, tags: list[str], ctx: EventContext) -> int:
    modifier, breakdown, _notes = compute_skill_modifier_with_sources(
        skill_id=skill_id,
        actor=target,
        target=target,
        tags=tags,
        base_modifier=0,
    )
    if breakdown:
        try:
            ctx.game.ui_log(f"{skill_id} DC modyfikatory: {', '.join(breakdown)}.")
        except Exception:
            pass
    return 10 + modifier


def _actor_id(actor) -> str:
    return str(getattr(actor, "object_id", None) or getattr(actor, "name", None) or "actor")


def _apply_disarm_penalty(target, *, source: str, turns: int) -> None:
    if target is None:
        return
    remover = getattr(target, "remove_bonuses_with_prefix", None)
    if callable(remover):
        try:
            remover("disarm:")
        except Exception:
            pass
    effects = [
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=2,
            tag="attack_melee",
            source=source,
            label="disarmed",
            is_penalty=True,
            duration_turns=max(1, int(turns)),
        ),
        BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=2,
            tag="attack_ranged",
            source=source,
            label="disarmed",
            is_penalty=True,
            duration_turns=max(1, int(turns)),
        ),
    ]
    adder = getattr(target, "add_bonus", None)
    if callable(adder):
        for effect in effects:
            try:
                adder(effect)
            except Exception:
                continue
        return
    bonuses = getattr(target, "bonuses", None)
    if isinstance(bonuses, list):
        bonuses.extend(effects)


@register_event
class DisarmEvent(ActionCostEvent):
    """Disarm: Athletics vs Reflex DC."""

    name = "disarm"
    default_tags = ["attack", "athletics", "disarm", "manipulate"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True
    actions_cost = 1

    def _pick_enemy(self, ctx: EventContext, candidates):
        if not candidates:
            return None, None
        if len(candidates) == 1:
            return candidates[0]
        positions = [pos for _, pos in candidates]
        while True:
            try:
                ctx.game.conn.set_leds(positions, consts.INTERACT_FIELD_RGB)
                choice = ctx.game.conn.scan_board(positions)
            finally:
                try:
                    ctx.game.conn.leds_off()
                except Exception:
                    pass
            for enemy, pos in candidates:
                if pos == choice:
                    return enemy, pos
            logger.info("Nie wybrano poprawnego celu – spróbuj ponownie.")
            ctx.game.ui_log("Nie wybrano poprawnego celu – spróbuj ponownie.")

    def execute(self, ctx: EventContext) -> EventResult:
        if not ctx.in_combat:
            return EventResult.cancelled(message="Disarm dostępne tylko w walce.")

        hero = ctx.actor
        if hero is None:
            return EventResult.cancelled(message="Brak bohatera do akcji disarm.")
        hero_pos = getattr(hero, "position", None)
        if hero_pos is None:
            return EventResult.cancelled(message="Bohater nie stoi na planszy.")

        reach_ft = best_reach_ft_for_trait(hero, "disarm", default_ft=5)
        if reach_ft > 5:
            candidates = enemies_in_reach(ctx.game, hero_pos, reach_ft=reach_ft)
        else:
            candidates = BasicMeleeAttackEvent._adjacent_enemies(ctx.game, hero_pos)
        if not candidates:
            return EventResult.cancelled(message="Brak wrogów w zasięgu disarm.")

        enemy, enemy_pos = self._pick_enemy(ctx, candidates)
        if enemy is None:
            return EventResult.cancelled(message="Nie wybrano celu.")

        tags = self._effective_tags(ctx)
        emitted = None
        try:
            emitted = ctx.game.events.safe_emit_action(
                return_event=True,
                actor=hero,
                action_id="disarm",
                action_tags=tags,
                target=enemy,
                target_pos=enemy_pos,
            )
        except Exception:
            emitted = None
        if isinstance(emitted, dict) and bool(emitted.get("disrupted", False)):
            msg = "Disarm przerwane przez Atak okazyjny."
            try:
                ctx.game.ui_log(msg)
            except Exception:
                pass
            return EventResult(success=False, consumed_action=True, actions_spent=self.actions_cost, message=msg)

        dc = _save_dc(enemy, Skill.REFLEX.value, tags, ctx)
        result = resolve_skill_check_with_sources(
            skill_id=Skill.ATHLETICS.value,
            dc=dc,
            actor=hero,
            target=enemy,
            tags=tags,
            game=ctx.game,
            apply_modifiers=True,
        )
        outcome = result.outcome

        if outcome == "success":
            _apply_disarm_penalty(enemy, source=f"disarm:{_actor_id(hero)}", turns=1)
        elif outcome == "critical_success":
            _apply_disarm_penalty(enemy, source=f"disarm:{_actor_id(hero)}", turns=2)
        elif outcome == "critical_failure":
            _apply_disarm_penalty(hero, source=f"disarm:self:{_actor_id(enemy)}", turns=1)

        msg = f"Disarm: {outcome}."
        try:
            ctx.game.ui_log(msg)
        except Exception:
            pass
        return EventResult(success=True, consumed_action=self.consumes_action, message=msg)
