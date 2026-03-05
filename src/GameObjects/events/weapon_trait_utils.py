from __future__ import annotations

from typing import Iterable


def _normalized_tags(raw_tags: Iterable[object] | None) -> list[str]:
    out: list[str] = []
    for item in raw_tags or ():
        tag = str(item or "").strip().lower().replace("-", "_").replace(" ", "_")
        if not tag:
            continue
        out.append(tag)
    return list(dict.fromkeys(out))


def _has_trait(tags: Iterable[str], trait: str) -> bool:
    for tag in tags or ():
        if tag == trait or tag.startswith(f"{trait}:") or tag.startswith(f"{trait}_"):
            return True
    return False


def _trait_value(tags: Iterable[str], trait: str) -> str | None:
    for tag in tags or ():
        if tag == trait:
            return None
        if tag.startswith(f"{trait}:"):
            value = tag.split(":", 1)[1].strip()
            return value or None
        if tag.startswith(f"{trait}_"):
            value = tag.split("_", 1)[1].strip()
            return value or None
    return None


def _reach_ft_from_tags(tags: Iterable[str]) -> int:
    if not _has_trait(tags, "reach"):
        return 5
    raw = _trait_value(tags, "reach")
    if raw is None:
        return 10
    try:
        return max(10, int(raw))
    except Exception:
        return 10


def equipped_weapon_traits(actor) -> list[tuple[object, list[str]]]:
    try:
        from GameObjects.items.inventory import get_equipped_weapons

        equipped = list(get_equipped_weapons(actor) or [])
    except Exception:
        equipped = []
    out: list[tuple[object, list[str]]] = []
    for weapon in equipped:
        tags = _normalized_tags(getattr(weapon, "traits", None))
        item_id = str(getattr(weapon, "item_id", "") or "").strip().lower().replace("-", "_").replace(" ", "_")
        if item_id and item_id not in tags:
            tags.append(item_id)
        out.append((weapon, tags))
    return out


def actor_has_equipped_weapon_trait(actor, trait: str) -> bool:
    wanted = str(trait or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not wanted:
        return False
    for _weapon, tags in equipped_weapon_traits(actor):
        if _has_trait(tags, wanted):
            return True
    return False


def best_reach_ft_for_trait(actor, trait: str, *, default_ft: int = 5) -> int:
    wanted = str(trait or "").strip().lower().replace("-", "_").replace(" ", "_")
    best = max(5, int(default_ft or 5))
    for _weapon, tags in equipped_weapon_traits(actor):
        if not _has_trait(tags, wanted):
            continue
        best = max(best, _reach_ft_from_tags(tags))
    return best


def enemies_in_reach(game, source_pos: tuple[int, int], *, reach_ft: int) -> list[tuple[object, tuple[int, int]]]:
    if source_pos is None:
        return []
    try:
        cells = max(1, int(reach_ft // 5))
    except Exception:
        cells = 1
    out: list[tuple[object, tuple[int, int]]] = []
    board = getattr(game, "board", None)
    enemies = list(getattr(game, "enemies", []) or [])
    for enemy in enemies:
        pos = getattr(enemy, "position", None)
        if not (isinstance(pos, tuple) and len(pos) == 2):
            continue
        try:
            if board is not None and hasattr(board, "in_bounds") and not board.in_bounds(pos):
                continue
        except Exception:
            continue
        if max(abs(int(pos[0]) - int(source_pos[0])), abs(int(pos[1]) - int(source_pos[1]))) <= cells:
            out.append((enemy, pos))
    return out


__all__ = [
    "actor_has_equipped_weapon_trait",
    "best_reach_ft_for_trait",
    "enemies_in_reach",
    "equipped_weapon_traits",
]
