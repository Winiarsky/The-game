from __future__ import annotations

import logging
import time

from board import consts
from actions.move_utils import find_path, path_cost_feet, trim_path_to_feet
from combat import refresh_flanking_statuses
from combat.reactions import dispatch_reactions
from statuses import speed_penalty_value, speed_bonus_value

from ..base import EventContext, EventResult, GameEvent
from ..registry import register_event

logger = logging.getLogger(__name__)


def _adjacent_reachable(board, a: tuple[int, int], b: tuple[int, int]) -> bool:
    if not (board.in_bounds(a) and board.in_bounds(b)):
        return False
    if board.is_blocked(a, b):
        return False
    for edge_obj in board.edge_interactables_between(a, b):
        blocks_passage = getattr(edge_obj, "blocks_passage", None)
        if callable(blocks_passage) and blocks_passage(a, b):
            return False
    return True


def _nearest_hero(game, enemy_pos: tuple[int, int]) -> tuple[tuple[int, int] | None, int]:
    best_pos = None
    best_dist = 999
    for hero in game.heroes:
        if getattr(hero, "position", None) is None:
            continue
        hx, hy = hero.position
        ex, ey = enemy_pos
        dist = abs(hx - ex) + abs(hy - ey)
        if dist < best_dist:
            best_dist = dist
            best_pos = hero.position
    return best_pos, best_dist


def _dispatch_move_reactions(game, mover, src: tuple[int, int], dst: tuple[int, int]) -> None:
    state = getattr(game, "state", None)
    if getattr(getattr(state, "__class__", None), "__name__", "") != "Combat":
        return
    leaving = False
    for reactor in list(getattr(game, "heroes", [])) + list(getattr(game, "enemies", [])):
        if reactor is mover:
            continue
        rpos = getattr(reactor, "position", None)
        if rpos is None:
            continue
        reach = getattr(reactor, "reach", 1) or 1
        dx = abs(rpos[0] - src[0])
        dy = abs(rpos[1] - src[1])
        if max(dx, dy) <= reach:
            dx2 = abs(rpos[0] - dst[0])
            dy2 = abs(rpos[1] - dst[1])
            if max(dx2, dy2) > reach:
                leaving = True
                break

    event = {
        "actor": mover,
        "action_tags": {"move"},
        "from_pos": src,
        "to_pos": dst,
        "leaving_reach": leaving,
    }

    game.events.safe_emit_action(
        actor=mover,
        action_id="enemy_move",
        action_tags=["move"],
        from_pos=src,
        to_pos=dst,
        leaving_reach=leaving,
    )

    dispatch_reactions(game, event)


@register_event
class EnemyMoveEvent(GameEvent):
    name = "enemy_move"
    default_tags = ["move", "enemy"]
    consumes_action = True
    available_in_exploration = False

    def execute(self, ctx: EventContext) -> EventResult:
        enemy = ctx.actor
        if enemy is None or getattr(enemy, "position", None) is None:
            return EventResult(success=False, consumed_action=False, message="Wróg nie jest na planszy.")
        if getattr(enemy, "has_status", lambda _s: False)("grabbed") or getattr(enemy, "has_status", lambda _s: False)("restrained"):
            return EventResult(success=False, consumed_action=False, message="Wróg jest grabbed/restrained – nie może się ruszyć.")

        game = ctx.game
        board = game.board

        base_distance = getattr(enemy, "distance", None)
        if base_distance is None:
            base_distance = max(1, getattr(enemy, "move_points", 3)) * 5
        penalty = speed_penalty_value(enemy)
        bonus = speed_bonus_value(enemy)
        move_budget_feet = max(0, int(base_distance) - int(penalty) + int(bonus))
        if move_budget_feet <= 0:
            return EventResult(success=False, consumed_action=True, message="Wróg jest spowolniony i nie może się ruszyć.")
        nearest_pos, _dist = _nearest_hero(game, enemy.position)
        if nearest_pos is None:
            return EventResult(success=False, consumed_action=False, message="Wróg nie widzi celu.")

        neighbor_targets = [
            cand
            for cand in board.get_neighbors(nearest_pos, include_position=False, diagonal=True)
            if _adjacent_reachable(board, cand, nearest_pos)
        ]
        reachable_paths: list[tuple[list[tuple[int, int]], tuple[int, int], int]] = []
        for cand in neighbor_targets:
            if not board.can_enter(cand, allow_occupied=False):
                continue
            path = find_path(board, enemy.position, cand, allow_diagonal=True, allow_occupied=False, mover=enemy)
            if path:
                reachable_paths.append((path, cand, path_cost_feet(path, board, mover=enemy)))

        if not reachable_paths:
            return EventResult(success=False, consumed_action=False, message="Brak ścieżki dla ruchu wroga.")

        reachable_paths.sort(key=lambda p: p[2])
        full_path, goal, full_feet = reachable_paths[0]
        truncated = trim_path_to_feet(full_path, move_budget_feet, board, mover=enemy)
        used_feet = path_cost_feet(truncated, board, mover=enemy)
        if len(truncated) < 2:
            return EventResult(success=False, consumed_action=True, message="Nie można wykonać kroku w budżecie ruchu.")
        dest = truncated[-1]

        path_id = f"enemy-path-{time.time_ns()}"
        game.ui_event("path_preview", {"id": path_id, "steps": len(truncated) - 1, "feet": used_feet, "target": dest})
        try:
            start_and_path = [enemy.position] + truncated[1:]
            colors = [consts.ENEMY_START_RGB] + [consts.ENEMY_MOVE_RGB] * (len(truncated) - 1)
            game.conn.set_leds(start_and_path, colors)
            confirm = game.conn.scan_board([dest])
            if confirm != dest:
                return EventResult(success=False, consumed_action=False, message="Ruch wroga anulowany (zły skan).")

            _dispatch_move_reactions(game, enemy, enemy.position, dest)
            game.board.move(enemy.position, dest)
            try:
                from GameObjects.events.magic.runtime_effects import process_alarm_wards_for_move

                process_alarm_wards_for_move(game, enemy, dest)
            except Exception:
                pass
            try:
                refresh_flanking_statuses(game)
            except Exception as exc:
                logger.error("Nie udało się odświeżyć flankowania po ruchu wroga: %s", exc)
            return EventResult(success=True, consumed_action=True, message=f"Wróg przemieszcza się na {dest}.")
        except Exception as exc:
            logger.error("Ruch wroga nie powiódł się: %s", exc)
            return EventResult(success=False, consumed_action=False, message=str(exc))
        finally:
            try:
                game.ui_event("path_clear", {"id": path_id})
            except Exception:
                pass
            try:
                game.conn.leds_off()
            except Exception:
                pass
