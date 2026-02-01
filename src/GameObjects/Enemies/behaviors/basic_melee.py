from __future__ import annotations

import logging
import random
import time
from board import consts
from actions.move_utils import find_path, path_cost_feet, trim_path_to_feet
from combat import refresh_flanking_statuses, flat_footed_penalty
from combat.reactions import dispatch_reactions

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
    roll = random.randint(1, 20) + attack_bonus
    penalty = flat_footed_penalty(hero)
    penalty_note = f" (cel flankowany: -{penalty} do AC)" if penalty else ""

    prompt = (
        f"{getattr(enemy, 'name', 'wróg')} atakuje bohatera na {target_pos}: "
        f"r={roll} (1d20 + {attack_bonus}){penalty_note}. "
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

    game.events.safe_emit_action(
        actor=enemy,
        action_id="enemy_attack_melee",
        action_tags=["attack_melee"],
        target=hero,
        target_pos=target_pos,
        damage=damage,
    )


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
        try:
            refresh_flanking_statuses(game)
        except Exception as exc:
            logger.error("Nie udało się odświeżyć flankowania: %s", exc)
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
        move_budget_feet = max(1, getattr(enemy, "move_points", 3)) * 5
        move_used = False
        path_id = None
        try:
            nearest_pos, _dist = _nearest_hero(game, enemy.position)
            if nearest_pos is None:
                logger.info("%s nie widzi celu, kończy turę.", enemy.name)
                actions_used = actions_left
                break

            # szukaj najbliższego pola wokół bohatera, na które można wejść
            logger.info(
                "[AI] Wróg %s szuka ruchu w stronę bohatera na %s (budżet ruchu %s stóp).",
                enemy.name,
                nearest_pos,
                move_budget_feet,
            )
            neighbor_targets = [
                cand
                for cand in board.get_neighbors(nearest_pos, include_position=False, diagonal=True)
                if _adjacent_reachable(board, cand, nearest_pos)
            ]
            reachable_paths: list[tuple[list[tuple[int, int]], tuple[int, int], int]] = []
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
                    reachable_paths.append((path, cand, path_cost_feet(path)))

            if not reachable_paths:
                logger.info("[AI] %s nie ma ścieżki do żadnego sąsiedniego pola celu – kończy turę.", enemy.name)
                actions_used = actions_left
                break

            # Podświetl wroga (czerwony) i cel (zielony); bez potwierdzenia kliknięciem celu.
            try:
                game.conn.set_leds([enemy.position], consts.ENEMY_START_RGB)
                game.conn.set_leds([nearest_pos], consts.MOVE_FIELD_RGB)
            except Exception:
                pass

            # wybierz najkrótszą ścieżkę
            reachable_paths.sort(key=lambda p: p[2])
            full_path, goal, full_feet = reachable_paths[0]
            # ogranicz do budżetu ruchu
            truncated, used_feet = trim_path_to_feet(full_path, move_budget_feet)
            if len(truncated) < 2:
                logger.info("[AI] %s nie może wykonać nawet jednego kroku w budżecie %s stóp.", enemy.name, move_budget_feet)
                actions_used = actions_left
                break
            dest = truncated[-1]
            logger.info(
                "[AI] Najkrótsza ścieżka do %s: %s pól / %s stóp (przycięta do %s pól / %s stóp). Cel skanu: %s",
                goal,
                len(full_path) - 1,
                full_feet,
                len(truncated) - 1,
                used_feet,
                dest,
            )
            path_id = f"enemy-path-{time.time_ns()}"
            game.ui_event("path_preview", {"id": path_id, "steps": len(truncated) - 1, "feet": used_feet, "target": dest})

            start_and_path = [enemy.position] + truncated[1:]
            colors = [consts.ENEMY_START_RGB] + [consts.ENEMY_MOVE_RGB] * (len(truncated) - 1)
            game.conn.set_leds(start_and_path, colors)
            logger.info(
                "%s (budżet ruchu %s stóp) – ścieżka do %s (%s pól / %s stóp). Przenieś figurkę na cel i zeskanuj.",
                enemy.name,
                move_budget_feet,
                dest,
                len(truncated) - 1,
                used_feet,
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

    # jeśli po wszystkich akcjach stoimy obok, informacyjny log
    if _heroes_in_range(game, enemy.position):
        logger.info("%s jest obok bohatera – w kolejnej akcji może zaatakować.", enemy.name)

    return actions_used
