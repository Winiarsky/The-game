from __future__ import annotations

import logging

from board import consts
from skills import Skill
from GameObjects.interactions_mixin import resolve_skill_check_with_sources, compute_skill_modifier_with_sources
from statuses import GrabbedStatus, RestrainedStatus, apply_grabbed_effects, apply_restrained_effects, clear_grabbed_effects, clear_restrained_effects

from .base import EventContext, EventResult, ActionCostEvent
from .registry import register_event
from .attack.basic_melee_attack_event import BasicMeleeAttackEvent

logger = logging.getLogger(__name__)


def _actor_id(actor) -> str | None:
    if actor is None:
        return None
    return getattr(actor, "object_id", None) or getattr(actor, "name", None) or str(actor)


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


def _remove_hold_statuses(target) -> None:
    remover = getattr(target, "remove_status", None)
    for sid in ("grabbed", "restrained"):
        if callable(remover):
            try:
                remover(sid)
            except Exception:
                pass
    clear_grabbed_effects(target)
    clear_restrained_effects(target)


@register_event
class GrappleEvent(ActionCostEvent):
    """Grapple: Athletics vs Fortitude DC."""

    name = "grapple"
    default_tags = ["attack", "athletics", "grapple", "manipulate"]
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
            return EventResult.cancelled(message="Grapple dostępne tylko w walce.")

        hero = ctx.actor
        if hero is None:
            return EventResult.cancelled(message="Brak bohatera do akcji grapple.")
        hero_pos = getattr(hero, "position", None)
        if hero_pos is None:
            return EventResult.cancelled(message="Bohater nie stoi na planszy.")

        candidates = BasicMeleeAttackEvent._adjacent_enemies(ctx.game, hero_pos)
        if not candidates:
            return EventResult.cancelled(message="Brak wrogów w zasięgu grapple.")

        enemy, enemy_pos = self._pick_enemy(ctx, candidates)
        if enemy is None:
            return EventResult.cancelled(message="Nie wybrano celu.")

        tags = self._effective_tags(ctx)
        dc = _save_dc(enemy, Skill.FORTITUDE.value, tags, ctx)

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
        source_id = _actor_id(hero)
        if outcome == "success":
            _remove_hold_statuses(enemy)
            try:
                enemy.add_status(GrabbedStatus(source_id=source_id, maintain_turns_left=0))
            except Exception:
                pass
            apply_grabbed_effects(enemy, source_id=source_id)
        elif outcome == "critical_success":
            _remove_hold_statuses(enemy)
            try:
                enemy.add_status(RestrainedStatus(source_id=source_id, maintain_turns_left=0))
            except Exception:
                pass
            apply_restrained_effects(enemy, source_id=source_id)
        elif outcome == "critical_failure":
            _remove_hold_statuses(hero)
            try:
                hero.add_status(GrabbedStatus(source_id=_actor_id(enemy), maintain_turns_left=0))
            except Exception:
                pass
            apply_grabbed_effects(hero, source_id=_actor_id(enemy))

        ctx.game.events.safe_emit_action(
            actor=hero,
            action_id="grapple",
            action_tags=tags,
            target=enemy,
            target_pos=enemy_pos,
            outcome=outcome,
        )

        msg = f"Grapple: {outcome}."
        try:
            ctx.game.ui_log(msg)
        except Exception:
            pass
        return EventResult(success=True, consumed_action=self.consumes_action, message=msg)
