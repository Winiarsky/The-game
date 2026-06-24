from __future__ import annotations


_POOL_ATTR_CANDIDATES = ("focus_pool_max", "wizard_focus_pool_max", "focus_pool_size")


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def get_focus_points(actor) -> int:
    if actor is None:
        return 0
    return max(0, _safe_int(getattr(actor, "focus_point", 0), 0))


def get_focus_pool_max(actor) -> int:
    if actor is None:
        return 0
    candidates: list[int] = []
    for attr_name in _POOL_ATTR_CANDIDATES:
        candidates.append(max(0, _safe_int(getattr(actor, attr_name, 0), 0)))
    current = get_focus_points(actor)
    if current > 0:
        candidates.append(current)
    return max(candidates or [0])


def set_focus_points(actor, value: int, *, clamp_to_pool: bool = True) -> int:
    if actor is None:
        return 0
    points = max(0, _safe_int(value, 0))
    pool_max = get_focus_pool_max(actor)
    if clamp_to_pool and pool_max > 0:
        points = min(points, pool_max)
    if points > pool_max:
        pool_max = points
    try:
        setattr(actor, "focus_point", int(points))
    except Exception:
        return points
    if pool_max > 0:
        try:
            setattr(actor, "focus_pool_max", int(pool_max))
        except Exception:
            pass
    return int(points)


def ensure_focus_pool(actor, *, minimum_pool: int = 0) -> tuple[int, int]:
    if actor is None:
        return 0, 0
    current = get_focus_points(actor)
    pool_max = max(get_focus_pool_max(actor), max(0, _safe_int(minimum_pool, 0)))
    if current > pool_max:
        pool_max = current
    try:
        setattr(actor, "focus_point", int(current))
    except Exception:
        pass
    if pool_max > 0:
        try:
            setattr(actor, "focus_pool_max", int(pool_max))
        except Exception:
            pass
    return int(current), int(pool_max)

