from __future__ import annotations

import logging

from combat import refresh_flanking_statuses
from GameObjects.events import EventContext
from GameObjects.events.registry import dispatch_event
from GameObjects.Enemies.behaviors.basic_melee import _heroes_in_range

logger = logging.getLogger(__name__)


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
        adj = _heroes_in_range(game, enemy.position)
        if adj and remaining >= attack_cost:
            logger.info("[AI][flanking] Wróg %s ma cel w zasięgu (%s) – próba ataku przez event.", enemy.name, adj)
            res = dispatch_event("enemy_attack_melee", EventContext(game=game, actor=enemy))
            actions_used += 1 if res.consumed_action else 0
            continue

        if remaining <= 0:
            break

        res = dispatch_event("enemy_move", EventContext(game=game, actor=enemy))
        if res.success:
            actions_used += 1 if res.consumed_action else 0
            continue
        actions_used += 1
        break

    if _heroes_in_range(game, enemy.position):
        logger.info("%s jest obok bohatera – w kolejnej akcji może zaatakować.", enemy.name)

    return actions_used
