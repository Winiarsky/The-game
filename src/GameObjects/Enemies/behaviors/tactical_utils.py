from __future__ import annotations

from actions.move_utils import find_path, movement_budget_feet, path_cost_feet
from combat import flanking_positions
from combat.hero_side_targets import current_hp_value, hero_side_targets, is_targetable_actor
from GameObjects.events.enemy.enemy_strike_event import _EnemyRangeAnalyzer, _select_weapon, _weapon_reach_ft


def is_alive(actor) -> bool:
    return is_targetable_actor(actor)


def living_heroes(game) -> list[object]:
    return [hero for hero in hero_side_targets(game, only_living=True) if is_alive(hero)]


def living_enemy_allies(game, actor) -> list[object]:
    return [enemy for enemy in getattr(game, "enemies", []) or [] if enemy is not actor and is_alive(enemy)]


def chebyshev_distance(a: tuple[int, int] | None, b: tuple[int, int] | None) -> int:
    if a is None or b is None:
        return 999
    return max(abs(int(a[0]) - int(b[0])), abs(int(a[1]) - int(b[1])))


def distance_ft(a: tuple[int, int] | None, b: tuple[int, int] | None) -> int:
    return chebyshev_distance(a, b) * 5


def hp_ratio(actor) -> float:
    if actor is None:
        return 0.0
    try:
        max_hp = max(1, int(getattr(actor, "max_hp", current_hp_value(actor) or 1) or 1))
        current = max(0, int(current_hp_value(actor) or 0))
        return max(0.0, min(1.0, float(current) / float(max_hp)))
    except Exception:
        return 0.0


def adjacent_positions(board, pos: tuple[int, int] | None) -> list[tuple[int, int]]:
    if pos is None:
        return []
    try:
        return list(board.get_neighbors(pos, include_position=False, diagonal=True))
    except Exception:
        return []


def adjacent_to_target(board, pos: tuple[int, int], target_pos: tuple[int, int] | None) -> bool:
    return chebyshev_distance(pos, target_pos) <= 1


def count_adjacent_allies(game, pos: tuple[int, int], *, actor=None, target=None) -> int:
    count = 0
    for ally in living_enemy_allies(game, actor):
        ally_pos = getattr(ally, "position", None)
        if ally is target:
            continue
        if chebyshev_distance(pos, ally_pos) <= 1:
            count += 1
    return count


def count_adjacent_heroes(game, pos: tuple[int, int]) -> int:
    count = 0
    for hero in living_heroes(game):
        if chebyshev_distance(pos, getattr(hero, "position", None)) <= 1:
            count += 1
    return count


def count_adjacent_enemies_to_target(game, target) -> int:
    target_pos = getattr(target, "position", None)
    if target_pos is None:
        return 0
    count = 0
    for enemy in getattr(game, "enemies", []) or []:
        if not is_alive(enemy):
            continue
        if chebyshev_distance(getattr(enemy, "position", None), target_pos) <= 1:
            count += 1
    return count


def target_is_lone(game, target) -> bool:
    target_pos = getattr(target, "position", None)
    if target_pos is None:
        return False
    support = 0
    for hero in living_heroes(game):
        if hero is target:
            continue
        if chebyshev_distance(getattr(hero, "position", None), target_pos) <= 1:
            support += 1
    return support <= 0


def _iter_board_positions(board, actor=None, target=None):
    rows = getattr(board, "rows", None)
    cols = getattr(board, "cols", None)
    if isinstance(rows, int) and isinstance(cols, int) and rows > 0 and cols > 0:
        for row in range(rows):
            for col in range(cols):
                yield (col, row)
        return

    seen: set[tuple[int, int]] = set()
    seeds = []
    actor_pos = getattr(actor, "position", None)
    target_pos = getattr(target, "position", None)
    if actor_pos is not None:
        seeds.append(actor_pos)
        seeds.extend(adjacent_positions(board, actor_pos))
    if target_pos is not None:
        seeds.append(target_pos)
        seeds.extend(adjacent_positions(board, target_pos))
    for pos in seeds:
        if pos is None or pos in seen:
            continue
        seen.add(pos)
        yield pos


def reachable_positions(game, actor, *, max_feet: int | None = None, include_current: bool = True) -> list[dict[str, object]]:
    board = game.board
    actor_pos = getattr(actor, "position", None)
    if actor_pos is None:
        return []
    budget = int(max_feet if max_feet is not None else movement_budget_feet(actor, default_feet=getattr(actor, "distance", 25) or 25))
    result: list[dict[str, object]] = []
    for pos in _iter_board_positions(board, actor=actor):
        if pos != actor_pos:
            try:
                if not board.can_enter(pos, allow_occupied=False):
                    continue
            except Exception:
                pass
        if pos == actor_pos and not include_current:
            continue
        path = find_path(board, actor_pos, pos, allow_diagonal=True, allow_occupied=False, mover=actor)
        if not path:
            continue
        cost = path_cost_feet(path, board, mover=actor)
        if pos == actor_pos:
            cost = 0
        if cost > budget:
            continue
        result.append({"position": pos, "path": path, "cost": cost})
    return result


def ranged_cover_rank(game, *, attacker, defender_pos: tuple[int, int] | None) -> int:
    attacker_pos = getattr(attacker, "position", None)
    if attacker_pos is None or defender_pos is None:
        return 0
    analyzer = _EnemyRangeAnalyzer()
    analysis = analyzer._analyze_shot(game, attacker_pos, defender_pos, target=attacker)
    if bool(analysis.get("blocked", False)):
        return 4
    mapping = {"none": 0, "minor": 1, "standard": 2, "greater": 3, "block": 4}
    return int(mapping.get(str(analysis.get("cover_type", "none") or "none"), 0))


def flank_positions_for_target(game, actor, target) -> list[tuple[int, int]]:
    board = game.board
    target_pos = getattr(target, "position", None)
    if target_pos is None:
        return []
    ally_positions = [
        getattr(ally, "position", None)
        for ally in living_enemy_allies(game, actor)
        if getattr(ally, "position", None) is not None
    ]
    return flanking_positions(board, target_pos, [pos for pos in ally_positions if pos is not None])


def positions_in_weapon_reach(game, actor, target, weapon) -> set[tuple[int, int]]:
    board = game.board
    target_pos = getattr(target, "position", None)
    if target_pos is None:
        return set()
    reach_squares = max(1, _weapon_reach_ft(actor, weapon) // 5)
    result: set[tuple[int, int]] = set()
    for pos in _iter_board_positions(board, actor=actor, target=target):
        if chebyshev_distance(pos, target_pos) > reach_squares:
            continue
        if pos != getattr(actor, "position", None):
            try:
                if not board.can_enter(pos, allow_occupied=False):
                    continue
            except Exception:
                pass
        result.add(pos)
    return result


def can_attack_from_position(game, actor, target, weapon, pos: tuple[int, int]) -> bool:
    target_pos = getattr(target, "position", None)
    if target_pos is None:
        return False
    if bool(getattr(weapon, "ranged", False)):
        attacker_proxy = type("AttackerProxy", (), {"position": pos})()
        analyzer = _EnemyRangeAnalyzer()
        analyzer.range_increment_ft = int(getattr(weapon, "range_increment_ft", 60) or 60)
        analysis = analyzer._analyze_shot(game, pos, target_pos, target=target)
        return not bool(analysis.get("blocked", False))
    return pos in positions_in_weapon_reach(game, actor, target, weapon)


def best_weapon(actor, *, ranged: bool | None = None, weapon_id: object | None = None):
    return _select_weapon(actor, weapon_id=weapon_id, prefer_ranged=ranged)
