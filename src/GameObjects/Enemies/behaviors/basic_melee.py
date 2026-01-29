from __future__ import annotations

import logging
import random
import time
from board import consts
from actions.move_utils import find_path

logger = logging.getLogger(__name__)


def _heroes_in_range(game, enemy_pos: tuple[int, int], include_diagonal: bool = True) -> list[tuple[int, int]]:
    board = game.board
    neighbors = board.get_neighbors(enemy_pos, include_position=False, diagonal=include_diagonal)
    positions: list[tuple[int, int]] = []
    for pos in neighbors:
        occ = board.occupant_at(pos)
        if occ in game.heroes and _adjacent_reachable(board, enemy_pos, pos):
            positions.append(pos)
    return positions


def _nearest_hero(game, enemy_pos: tuple[int, int]) -> tuple[tuple[int, int] | None, int]:
    """Zwraca (pozycja, dystans) najbliższego bohatera (manhattan)."""
    best_pos = None
    best_dist = 999
    for hero in game.heroes:
        if hero.position is None:
            continue
        hx, hy = hero.position
        ex, ey = enemy_pos
        dist = abs(hx - ex) + abs(hy - ey)
        if dist < best_dist:
            best_dist = dist
            best_pos = hero.position
    return best_pos, best_dist


def _adjacent_reachable(board, a: tuple[int, int], b: tuple[int, int]) -> bool:
    """Sprawdza, czy między sąsiadami nie ma ściany/blokera na krawędzi (ignoruje zajętość pól)."""
    if not (board.in_bounds(a) and board.in_bounds(b)):
        return False
    if board.is_blocked(a, b):
        return False
    for edge_obj in board.edge_interactables_between(a, b):
        blocks_passage = getattr(edge_obj, "blocks_passage", None)
        if callable(blocks_passage) and blocks_passage(a, b):
            return False
    return True


def _attack_hero(enemy, game, targets: list[tuple[int, int]]) -> None:
    """Prosty atak wręcz na wskazanego bohatera."""
    board = game.board
    conn = game.conn

    conn.set_leds(targets, consts.MOVE_FIELD_RGB)  # zielone: cel ataku
    try:
        target_pos = conn.scan_board(targets)
    finally:
        conn.leds_off()

    hero = board.occupant_at(target_pos)
    if hero not in game.heroes:
        logger.info("Wybrano cel, który nie jest bohaterem – atak anulowany.")
        return

    attack_bonus = getattr(enemy, "attack_bonus", 0)
    target_bonus = getattr(hero, "enemy_attack_bonus", 0)
    roll = random.randint(1, 20) + attack_bonus + target_bonus

    prompt = (
        f"{getattr(enemy, 'name', 'wróg')} atakuje bohatera na {target_pos}: "
        f"r={roll} (1d20 + {attack_bonus} + bonus celu {target_bonus}). "
        "Potwierdź trafienie: ACCEPT/DECLINE"
    )
    response = conn.read_card(prompt, ["ACCEPT", "DECLINE"])
    if response.upper() != "ACCEPT":
        logger.info("Atak nie trafia (odrzucono trafienie).")
        return

    damage = random.randint(1, 6) + getattr(enemy, "strength", 0)
    try:
        hero.wounds += damage  # type: ignore[attr-defined]
    except Exception:
        pass
    dmg_msg = (
        f"{getattr(enemy, 'name', 'wróg')} zadaje {damage} obrażeń (1d6 + {getattr(enemy, 'strength', 0)}). "
        f"Rany bohatera: {getattr(hero, 'wounds', '?')}."
    )
    logger.info(dmg_msg)
    game.ui_log(dmg_msg)


def basic_melee(enemy, game, combat_state, actions_left: int = 1) -> int:
    """Bardzo prosty algorytm: ruch (1 akcja) + ewentualnie atak (2 akcje).

    Zwraca liczbę zużytych akcji w tej turze (dla wrógów)."""
    board = game.board
    logger.info("[AI] Start tury wroga %s, pozycja %s, akcje_do_wykorzystania=%s", enemy.name, enemy.position, actions_left)
    if enemy.position is None:
        logger.info("%s nie jest na planszy – pomijam turę.", enemy.name)
        return 0

    actions_used = 0
    attack_cost = 1
    while actions_used < actions_left:
        remaining = actions_left - actions_used
        logger.debug("[AI] Pętla akcji wroga: użyte=%s, pozostalo=%s", actions_used, remaining)
        # próbuj zaatakować, jeśli w zasięgu i masz akcję
        adj = _heroes_in_range(game, enemy.position)
        if adj and remaining >= attack_cost:
            logger.info("[AI] Wróg %s ma cel w zasięgu (%s) – próba ataku.", enemy.name, adj)
            _attack_hero(enemy, game, adj)
            actions_used += attack_cost
            continue

        # spróbuj ruchu (1 akcja)
        if remaining <= 0:
            break
        move_budget = max(1, getattr(enemy, "move_points", 3))
        move_used = False
        path_id = None
        try:
            nearest_pos, _dist = _nearest_hero(game, enemy.position)
            if nearest_pos is None:
                logger.info("%s nie widzi celu, kończy turę.", enemy.name)
                actions_used = actions_left
                break

            # szukaj najbliższego pola wokół bohatera, na które można wejść
            logger.info("[AI] Wróg %s szuka ruchu w stronę bohatera na %s (budżet ruchu %s).", enemy.name, nearest_pos, move_budget)
            neighbor_targets = [
                cand
                for cand in board.get_neighbors(nearest_pos, include_position=False, diagonal=True)
                if _adjacent_reachable(board, cand, nearest_pos)
            ]
            reachable_paths: list[tuple[list[tuple[int, int]], tuple[int, int]]] = []
            for cand in neighbor_targets:
                if not board.can_enter(cand, allow_occupied=False):
                    continue
                path = find_path(
                    board,
                    enemy.position,
                    cand,
                    allow_diagonal=True,
                    allow_occupied=False,
                )
                if path:
                    reachable_paths.append((path, cand))

            if not reachable_paths:
                logger.info("[AI] %s nie ma ścieżki do żadnego sąsiedniego pola celu – kończy turę.", enemy.name)
                actions_used = actions_left
                break

            # Podświetl wroga (czerwony) i cel (zielony); bez potwierdzenia kliknięciem celu.
            try:
                game.conn.set_leds([enemy.position], consts.ENEMY_MOVE_RGB)
                game.conn.set_leds([nearest_pos], consts.MOVE_FIELD_RGB)
            except Exception:
                pass

            # wybierz najkrótszą ścieżkę
            reachable_paths.sort(key=lambda p: len(p[0]))
            full_path, goal = reachable_paths[0]
            # ogranicz do budżetu ruchu
            truncated = full_path[: move_budget + 1]
            dest = truncated[-1]
            logger.info("[AI] Najkrótsza ścieżka do %s: %s kroków (przycięta do %s). Cel skanu: %s", goal, len(full_path) - 1, len(truncated) - 1, dest)
            path_id = f"enemy-path-{time.time_ns()}"
            game.ui_event("path_preview", {"id": path_id, "steps": len(truncated) - 1, "target": dest})

            game.conn.set_leds(truncated[1:], consts.ENEMY_MOVE_RGB)
            logger.info(
                "%s (budżet ruchu %s) – ścieżka do %s (%s pól). Przenieś figurkę na cel i zeskanuj.",
                enemy.name,
                move_budget,
                dest,
                len(truncated) - 1,
            )
            try:
                confirm = game.conn.scan_board([dest])
            finally:
                # zostaw widoczny cel (zielony) jeśli to inne pole
                if nearest_pos != dest:
                    try:
                        game.conn.set_leds([nearest_pos], consts.MOVE_FIELD_RGB)
                    except Exception:
                        pass
                else:
                    game.conn.leds_off()
            if confirm != dest:
                logger.info("[AI] Zeskanowano inne pole (%s) zamiast %s – akcja ruchu anulowana.", confirm, dest)
                actions_used += 1
                continue

            try:
                board.move(enemy.position, dest)
                move_used = True
            except ValueError as exc:
                logger.error("Nie można przesunąć przeciwnika na %s: %s", dest, exc)
        finally:
            if path_id:
                game.ui_event("path_clear", {"id": path_id})
            game.conn.leds_off()

        if move_used:
            actions_used += 1
            continue
        actions_used += 1
        break

    # jeśli po wszystkich akcjach stoimy obok, informacyjny log
    if _heroes_in_range(game, enemy.position):
        logger.info("%s jest obok bohatera – w kolejnej akcji może zaatakować.", enemy.name)

    return actions_used
