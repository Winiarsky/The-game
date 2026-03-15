from __future__ import annotations

import logging

from board import consts
from skills import Skill
from actions.move_utils import adjusted_forced_movement_squares
from GameObjects.interactions_mixin import resolve_skill_check_with_sources, compute_skill_modifier_with_sources
from statuses import PRONE_STATUS, apply_prone_effects

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


@register_event
class ShoveEvent(ActionCostEvent):
    """Shove: Athletics vs Fortitude DC."""

    name = "shove"
    default_tags = ["attack", "athletics", "shove", "manipulate"]
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

    def _compute_push_destination(self, ctx: EventContext, target, *, steps: int) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
        board = ctx.game.board
        source_pos = getattr(ctx.actor, "position", None)
        target_pos = getattr(target, "position", None)
        if source_pos is None or target_pos is None:
            return None, None
        steps = adjusted_forced_movement_squares(target, steps)
        if steps <= 0:
            return target_pos, target_pos
        dx = target_pos[0] - source_pos[0]
        dy = target_pos[1] - source_pos[1]
        step_x = 0 if dx == 0 else (1 if dx > 0 else -1)
        step_y = 0 if dy == 0 else (1 if dy > 0 else -1)
        cur = target_pos
        for _ in range(max(0, steps)):
            nxt = (cur[0] + step_x, cur[1] + step_y)
            try:
                if board.is_blocked(cur, nxt):
                    break
            except Exception:
                pass
            try:
                if not board.can_enter(nxt, allow_occupied=False):
                    break
            except Exception:
                break
            cur = nxt
        return target_pos, cur

    def _confirm_forced_destination(self, ctx: EventContext, *, destination: tuple[int, int]) -> bool:
        conn = getattr(ctx.game, "conn", None)
        if conn is None:
            return True
        ui_log = getattr(ctx.game, "ui_log", None)
        while True:
            try:
                conn.set_leds([destination], consts.MOVE_TARGET_RGB)
                if callable(ui_log):
                    ui_log(
                        f"Shove: przestaw figurke celu na {destination} i kliknij podswietlone pole, aby potwierdzic."
                    )
                choice = conn.scan_board([destination])
            except Exception:
                logger.debug("Shove confirm failed, falling back to auto-confirm.", exc_info=True)
                return True
            finally:
                try:
                    conn.leds_off()
                except Exception:
                    pass
            if choice == destination:
                return True
            if callable(ui_log):
                ui_log("Shove: potwierdz podswietlone pole docelowe.")

    def _apply_push_with_confirmation(self, ctx: EventContext, target, *, steps: int) -> bool:
        board = ctx.game.board
        start_pos, destination = self._compute_push_destination(ctx, target, steps=steps)
        if start_pos is None or destination is None:
            return False
        if destination == start_pos:
            return False
        if not self._confirm_forced_destination(ctx, destination=destination):
            return False
        try:
            board.move(start_pos, destination)
        except Exception:
            return False
        try:
            target.position = destination
        except Exception:
            pass
        return True

    def execute(self, ctx: EventContext) -> EventResult:
        if not ctx.in_combat:
            return EventResult.cancelled(message="Shove dostępne tylko w walce.")

        hero = ctx.actor
        if hero is None:
            return EventResult.cancelled(message="Brak bohatera do akcji shove.")
        hero_pos = getattr(hero, "position", None)
        if hero_pos is None:
            return EventResult.cancelled(message="Bohater nie stoi na planszy.")

        reach_ft = best_reach_ft_for_trait(hero, "shove", default_ft=5)
        if reach_ft > 5:
            candidates = enemies_in_reach(ctx.game, hero_pos, reach_ft=reach_ft)
        else:
            candidates = BasicMeleeAttackEvent._adjacent_enemies(ctx.game, hero_pos)
        if not candidates:
            return EventResult.cancelled(message="Brak wrogów w zasięgu shove.")

        enemy, enemy_pos = self._pick_enemy(ctx, candidates)
        if enemy is None:
            return EventResult.cancelled(message="Nie wybrano celu.")

        tags = self._effective_tags(ctx)
        emitted = None
        try:
            emitted = ctx.game.events.safe_emit_action(
                return_event=True,
                actor=hero,
                action_id="shove",
                action_tags=tags,
                target=enemy,
                target_pos=enemy_pos,
            )
        except Exception:
            emitted = None
        if isinstance(emitted, dict) and bool(emitted.get("disrupted", False)):
            msg = "Shove przerwane przez Atak okazyjny."
            try:
                ctx.game.ui_log(msg)
            except Exception:
                pass
            return EventResult(success=False, consumed_action=True, actions_spent=self.actions_cost, message=msg)

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

        moved = False
        if outcome == "success":
            moved = self._apply_push_with_confirmation(ctx, enemy, steps=1)
        elif outcome == "critical_success":
            moved = self._apply_push_with_confirmation(ctx, enemy, steps=2)
        elif outcome == "critical_failure":
            try:
                hero.add_status(PRONE_STATUS)
            except Exception:
                pass
            apply_prone_effects(hero)

        movement_suffix = ""
        if outcome in {"success", "critical_success"}:
            movement_suffix = " Cel odepchniety." if moved else " Cel nie zostal przesuniety."
        msg = f"Shove: {outcome}.{movement_suffix}"
        try:
            ctx.game.ui_log(msg)
        except Exception:
            pass
        return EventResult(success=True, consumed_action=self.consumes_action, message=msg)
