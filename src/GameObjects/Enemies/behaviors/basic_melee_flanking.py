from __future__ import annotations

import logging
import time
from typing import Iterable

from actions.move_utils import find_path, path_cost_feet, trim_path_to_feet
from board import consts
from combat import flanking_positions, refresh_flanking_statuses
from combat.reactions import dispatch_reactions
from GameObjects.Enemies.behaviors.basic_melee import _adjacent_reachable, _attack_hero, _heroes_in_range

logger = logging.getLogger(__name__)


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
    event = {"actor": mover, "action_tags": {"move"}, "from_pos": src, "to_pos": dst, "leaving_reach": leaving}

    game.events.safe_emit_action(
        actor=mover,
        action_id="enemy_move",
        action_tags=["move"],
        from_pos=src,
        to_pos=dst,
        leaving_reach=leaving,
    )

    dispatch_reactions(game, event)


def _ally_positions(enemy, others: Iterable[object]) -> list[tuple[int, int]]:
    positions: list[tuple[int, int]] = []
    for ally in others:
        if ally is enemy:
            continue
        pos = getattr(ally, "position", None)
        if pos is not None:
            positions.append(pos)
    return positions


def _candidate_paths(board, enemy_pos, hero_pos, move_budget_feet: int, ally_positions: list[tuple[int, int]]):
    """Zwróć możliwe ścieżki do pól przy bohaterze, oznacz flanki."""
    neighbor_targets = [
        cand for cand in board.get_neighbors(hero_pos, include_position=False, diagonal=True) if _adjacent_reachable(board, cand, hero_pos)
    ]
    flanking_targets = set(flanking_positions(board, hero_pos, ally_positions))
    candidates = []
    for cand in neighbor_targets:
        if not board.can_enter(cand, allow_occupied=False):
            continue
        path = find_path(
            board,
            enemy_pos,
            cand,
            allow_diagonal=True,
            allow_occupied=False,
        )
        if not path:
            continue
        truncated, used_feet = trim_path_to_feet(path, move_budget_feet)
        if len(truncated) < 2:
            continue
        reaches_goal = truncated[-1] == cand
        is_flanking = cand in flanking_targets and reaches_goal
        candidates.append((is_flanking, used_feet, path_cost_feet(path), truncated, cand, hero_pos))
    candidates.sort(key=lambda item: (not item[0], item[1], item[2]))
    return candidates


def basic_melee_flanking(enemy, game, combat_state, actions_left: int = 1) -> int:
    """AI: ruch+atak z preferencją ruchów ustawiających flankę."""
    board = game.board
    logger.info(
        "[AI][flanking] Start tury wroga %s, pozycja %s, akcje_do_wykorzystania=%s", enemy.name, enemy.position, actions_left
    )
    if enemy.position is None:
        logger.info("%s nie jest na planszy – pomijam turę.", enemy.name)
        return 0

    actions_used = 0
    attack_cost = 1
    while actions_used < actions_left:
        remaining = actions_left - actions_used
        logger.debug("[AI][flanking] Pętla akcji wroga: użyte=%s, pozostalo=%s", actions_used, remaining)
        try:
            refresh_flanking_statuses(game)
        except Exception as exc:
            logger.error("Nie udało się odświeżyć flankowania: %s", exc)
        # próbuj zaatakować, jeśli w zasięgu i masz akcję
        adj = _heroes_in_range(game, enemy.position)
        if adj and remaining >= attack_cost:
            logger.info("[AI][flanking] Wróg %s ma cel w zasięgu (%s) – próba ataku.", enemy.name, adj)
            _attack_hero(enemy, game, adj)
            actions_used += attack_cost
            continue

        # spróbuj ruchu (1 akcja) z preferencją do flankowania
        if remaining <= 0:
            break
        move_budget_feet = max(1, getattr(enemy, "move_points", 3)) * 5
        move_used = False
        path_id = None
        try:
            ally_positions = _ally_positions(enemy, game.enemies)
            reachable_paths = []
            for hero in game.heroes:
                hero_pos = getattr(hero, "position", None)
                if hero_pos is None:
                    continue
                reachable_paths.extend(_candidate_paths(board, enemy.position, hero_pos, move_budget_feet, ally_positions))
            if reachable_paths:
                reachable_paths.sort(key=lambda item: (not item[0], item[1], item[2]))
            if not reachable_paths:
                logger.info("%s nie widzi celu, kończy turę.", enemy.name)
                actions_used = actions_left
                break

            target_hero_pos = reachable_paths[0][5]
            if not reachable_paths:
                logger.info("[AI][flanking] %s nie ma ścieżki do sąsiadów celu – kończy turę.", enemy.name)
                actions_used = actions_left
                break

            # Podświetl wroga (czerwony) i cel (zielony); bez potwierdzenia kliknięciem celu.
            try:
                game.conn.set_leds([enemy.position], consts.ENEMY_START_RGB)
                game.conn.set_leds([target_hero_pos], consts.MOVE_FIELD_RGB)
            except Exception:
                pass

            # wybierz ścieżkę: preferuj flankę, potem najkrótszą
            full_path = reachable_paths[0][3]
            used_feet = reachable_paths[0][1]
            flanking_selected = reachable_paths[0][0]
            dest = full_path[-1]
            path_id = f"enemy-path-{time.time_ns()}"
            game.ui_event(
                "path_preview",
                {"id": path_id, "steps": len(full_path) - 1, "feet": used_feet, "target": dest, "flanking": flanking_selected},
            )

            start_and_path = [enemy.position] + full_path[1:]
            colors = [consts.ENEMY_START_RGB] + [consts.ENEMY_MOVE_RGB] * (len(full_path) - 1)
            game.conn.set_leds(start_and_path, colors)
            flank_msg = " (flanka)" if flanking_selected else ""
            logger.info(
                "[AI][flanking] %s (budżet ruchu %s stóp) – ścieżka do %s%s (%s pól / %s stóp). Przenieś figurkę na cel i zeskanuj.",
                enemy.name,
                move_budget_feet,
                dest,
                flank_msg,
                len(full_path) - 1,
                used_feet,
            )
            try:
                confirm = game.conn.scan_board([dest])
            finally:
                if target_hero_pos != dest:
                    try:
                        game.conn.set_leds([target_hero_pos], consts.MOVE_FIELD_RGB)
                    except Exception:
                        pass
                else:
                    game.conn.leds_off()
            if confirm != dest:
                logger.info("[AI][flanking] Zeskanowano inne pole (%s) zamiast %s – akcja ruchu anulowana.", confirm, dest)
                actions_used += 1
                continue

            try:
                _dispatch_move_reactions(game, enemy, enemy.position, dest)
                board.move(enemy.position, dest)
                move_used = True
            except ValueError as exc:
                logger.error("Nie można przesunąć przeciwnika na %s: %s", dest, exc)
        finally:
            if path_id:
                game.ui_event("path_clear", {"id": path_id})
            game.conn.leds_off()

        if move_used:
            try:
                refresh_flanking_statuses(game)
            except Exception as exc:
                logger.error("Nie udało się odświeżyć flankowania po ruchu wroga: %s", exc)
            actions_used += 1
            continue
        actions_used += 1
        break

    if _heroes_in_range(game, enemy.position):
        logger.info("%s jest obok bohatera – w kolejnej akcji może zaatakować.", enemy.name)

    return actions_used
