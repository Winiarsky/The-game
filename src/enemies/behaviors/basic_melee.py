from __future__ import annotations

import logging
import random

from board import consts

logger = logging.getLogger(__name__)


def _heroes_in_range(game, enemy_pos: tuple[int, int], include_diagonal: bool = True) -> list[tuple[int, int]]:
    board = game.board
    neighbors = board.get_neighbors(enemy_pos, include_position=False, diagonal=include_diagonal)
    positions: list[tuple[int, int]] = []
    for pos in neighbors:
        occ = board.occupant_at(pos)
        if occ in game.heroes:
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


def _attack_hero(enemy, game, targets: list[tuple[int, int]]) -> None:
    """Prosty atak wręcz na wskazanego bohatera."""
    conn = game.conn
    board = game.board
    conn.set_leds(targets, consts.ENEMY_MOVE_RGB)
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
    logger.info(
        "%s zadaje %s obrażeń (1d6 + %s). Rany bohatera: %s.",
        getattr(enemy, "name", "wróg"),
        damage,
        getattr(enemy, "strength", 0),
        getattr(hero, "wounds", '?'),
    )


def basic_melee(enemy, game, combat_state, actions_left: int = 1) -> int:
    """Bardzo prosty algorytm: ruch (1 akcja) + ewentualnie atak (2 akcje).

    Zwraca liczbę zużytych akcji w tej turze (dla wrógów)."""
    board = game.board
    if enemy.position is None:
        logger.info("%s nie jest na planszy – pomijam turę.", enemy.name)
        return 0

    actions_used = 0
    attack_cost = 1
    while actions_used < actions_left:
        remaining = actions_left - actions_used
        # próbuj zaatakować, jeśli w zasięgu i masz akcję
        adj = _heroes_in_range(game, enemy.position)
        if adj and remaining >= attack_cost:
            _attack_hero(enemy, game, adj)
            actions_used += attack_cost
            continue

        # spróbuj ruchu (1 akcja)
        if remaining <= 0:
            break
        move_budget = max(1, getattr(enemy, "move_points", 3))
        moved = False
        steps_left = move_budget
        while steps_left > 0:
            adj_now = _heroes_in_range(game, enemy.position)
            if adj_now:
                break
            nearest_pos, dist = _nearest_hero(game, enemy.position)
            if nearest_pos is None:
                logger.info("%s nie widzi celu, kończy turę.", enemy.name)
                steps_left = 0
                break

            neighbors = board.get_neighbors(enemy.position, include_position=False, diagonal=False)
            walkable: list[tuple[int, int]] = [
                pos for pos in neighbors if board.can_traverse(enemy.position, pos, allow_occupied=False)
            ]
            if not walkable:
                logger.info("%s nie ma gdzie się poruszyć, kończy turę.", enemy.name)
                steps_left = 0
                break

            # wybierz kierunek, który skraca dystans do najbliższego bohatera
            dist_now = abs(enemy.position[0] - nearest_pos[0]) + abs(enemy.position[1] - nearest_pos[1])
            better_steps = [
                pos for pos in walkable
                if (abs(pos[0] - nearest_pos[0]) + abs(pos[1] - nearest_pos[1])) < dist_now
            ]
            if better_steps:
                # deterministycznie wybierz jedno pole (najmniejszy dystans)
                target_candidates = sorted(
                    better_steps,
                    key=lambda p: abs(p[0] - nearest_pos[0]) + abs(p[1] - nearest_pos[1])
                )[:1]
            else:
                target_candidates = walkable[:1]

            game.conn.set_leds(target_candidates, consts.ENEMY_MOVE_RGB)
            logger.info(
                "%s (ruch w akcji: %s/%s) próbuje podejść do najbliższego bohatera (na %s, dystans %s). "
                "Przesuń figurkę i zeskanuj pole docelowe.",
                enemy.name,
                (move_budget - steps_left + 1),
                move_budget,
                nearest_pos,
                dist,
            )
            try:
                target = game.conn.scan_board(target_candidates)
            finally:
                game.conn.leds_off()

            if target not in walkable:
                logger.info("Wybrano nieprawidłowe pole – kończę akcję ruchu.")
                steps_left = 0
                break

            try:
                board.move(enemy.position, target)
                moved = True
                logger.info("%s przesuwa się na %s.", enemy.name, target)
            except Exception as exc:
                logger.error("Nie udało się przesunąć %s: %s", enemy.name, exc)
                steps_left = 0
                break

            steps_left -= 1

        if moved:
            actions_used += 1
            continue
        # jeśli nie ruszył się w ogóle, zakończ akcję bez dalszych prób
        actions_used += 1
        break

    # jeśli po wszystkich akcjach stoimy obok, informacyjny log
    if _heroes_in_range(game, enemy.position):
        logger.info("%s jest obok bohatera – w kolejnej akcji może zaatakować.", enemy.name)

    return actions_used
