from __future__ import annotations

from typing import Any, Iterable, Optional, Sequence, Tuple

from statuses import Status
from ui_client import get_ui_client
from damage_types import DamageType


def _status_list(target: Any) -> Iterable[Status]:
    statuses = getattr(target, "statuses", None)
    if not isinstance(statuses, list):
        return []
    result: list[Status] = []
    for status in statuses:
        if isinstance(status, Status):
            result.append(status)
    return result


def _compute_resistance_value(target: Any, raw_val: object) -> Optional[int]:
    if isinstance(raw_val, (int, float)):
        return int(raw_val)
    if isinstance(raw_val, dict):
        if "value" in raw_val:
            try:
                return int(raw_val.get("value"))
            except Exception:
                return None
        if "per_2_levels" in raw_val:
            try:
                per_2 = int(raw_val.get("per_2_levels", 0))
            except Exception:
                per_2 = 0
            level = getattr(target, "level", 1) or 1
            try:
                level = int(level)
            except Exception:
                level = 1
            reduction = max(1, (level + 1) // 2) * per_2 if per_2 else 0
            try:
                minimum = int(raw_val.get("minimum", 0))
            except Exception:
                minimum = 0
            return max(minimum, reduction)
    return None


def damage_resistance_info(target: Any, damage_type: str) -> Tuple[int, Optional[str]]:
    """Zwraca (redukcja, źródło) dla obrażeń danego typu."""
    best = 0
    best_label: Optional[str] = None
    for status in _status_list(target):
        res_map = status.data.get("damage_resistance")
        if not isinstance(res_map, dict):
            continue
        val = _compute_resistance_value(target, res_map.get(damage_type))
        if isinstance(val, int) and val > best:
            best = val
            best_label = status.display_label
    return best, best_label


def damage_resistance(target: Any, damage_type: str) -> int:
    """Maksymalna redukcja obrażeń danego typu wynikająca ze statusów."""
    best, _ = damage_resistance_info(target, damage_type)
    return best


def apply_damage_resistance(target: Any, amount: int, damage_type: str) -> tuple[int, int]:
    """Zwraca (obrażenia_po_redukcji, zredukowano_o)."""
    reduction = damage_resistance(target, damage_type)
    effective = max(0, int(amount) - reduction)
    return effective, reduction


def format_damage_prompt(target: Any, components: Sequence[tuple[str, int]]) -> str:
    """Zbuduj opis obrażeń po redukcjach dla promptu/UI."""
    parts: list[str] = []
    notes: list[str] = []
    for idx, (dmg_type, amount) in enumerate(components):
        reduction, source = damage_resistance_info(target, dmg_type)
        effective = max(0, int(amount) - reduction)
        if idx == 0:
            parts.append(f"obrazenia {dmg_type} {effective}")
        else:
            parts.append(f"i od {dmg_type} {effective}")
        if reduction:
            src_label = source or "status"
            notes.append(f"-{reduction} za odpornosc z {src_label}")
    notes_text = f" ({'; '.join(notes)})" if notes else ""
    return " ".join(parts) + notes_text


def prompt_damage_summary(target: Any, components: Sequence[tuple[str, int]]) -> str:
    """Wyślij prompt informacyjny z obrażeniami po redukcjach."""
    summary = format_damage_prompt(target, components)
    try:
        get_ui_client().prompt_info(
            "Obrazenia",
            prompt_long=summary,
            source="damage",
        )
    except Exception:
        pass
    return summary


def _has_status(obj, status_id: str) -> bool:
    if obj is None:
        return False
    has_status = getattr(obj, "has_status", None)
    if callable(has_status):
        try:
            return bool(has_status(status_id))
        except Exception:
            return False
    statuses = getattr(obj, "statuses", None)
    if isinstance(statuses, list):
        return any(getattr(s, "id", s) == status_id for s in statuses)
    return False


def burn_it_bonus(actor: Any, damage_type: str, *, persistent: bool = False) -> int:
    """Zwróć bonus z Burn It! dla obrażeń ognia."""
    if damage_type != DamageType.FIRE.value:
        return 0
    if not _has_status(actor, "burn_it"):
        return 0
    if persistent:
        return 1
    level = getattr(actor, "level", 1) or 1
    try:
        level = int(level)
    except Exception:
        level = 1
    return max(1, level // 2)


def burn_it_prompt_note(actor: Any, damage_type: str, *, persistent: bool = False) -> str | None:
    bonus = burn_it_bonus(actor, damage_type, persistent=persistent)
    if not bonus:
        return None
    if persistent:
        return "Burn It!: wpisz wartość -1 (bonus +1 doda się automatycznie)."
    return f"Burn It!: +{bonus} status do obrażeń ognia (dodane automatycznie)."


def _neighbors_from_game(game: Any, center_pos: tuple[int, int], *, diagonal: bool = True) -> list[tuple[int, int]]:
    board = getattr(game, "board", None)
    if board is not None and hasattr(board, "get_neighbors"):
        try:
            return list(board.get_neighbors(center_pos, include_position=False, diagonal=diagonal))
        except Exception:
            return []
    x, y = center_pos
    return [
        (x + dx, y + dy)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if not (dx == 0 and dy == 0)
    ]


def _remove_enemy_from_game(game: Any, enemy: Any) -> None:
    pos = getattr(enemy, "position", None)
    try:
        if pos is not None:
            game.board.remove(pos)
    except Exception:
        pass
    try:
        game.enemies.remove(enemy)
    except Exception:
        pass
    try:
        enemy.position = None
    except Exception:
        pass


def apply_splash_damage(
    game: Any,
    center_pos: tuple[int, int] | None,
    amount: int,
    damage_type: str,
    *,
    exclude: Any | Iterable[Any] | tuple[int, int] | None = None,
    include_heroes: bool = True,
    include_enemies: bool = True,
    hero_info: bool = True,
    info_title: str | None = None,
    source: str = "splash",
    diagonal: bool = True,
    remove_defeated: bool = True,
) -> dict[str, list[Any]]:
    """Zadaj splash damage sąsiadom (hero -> info, enemy -> auto HP)."""
    result = {"heroes": [], "enemies": [], "defeated": []}
    if game is None or center_pos is None:
        return result
    if int(amount) <= 0:
        return result
    neighbors = _neighbors_from_game(game, center_pos, diagonal=diagonal)
    if not neighbors:
        return result

    def _is_excluded(obj: Any) -> bool:
        if exclude is None:
            return False
        if obj is exclude:
            return True
        if isinstance(exclude, (list, tuple, set)):
            if obj in exclude:
                return True
            pos = getattr(obj, "position", None)
            if pos is not None and pos in exclude:
                return True
        if isinstance(exclude, tuple) and len(exclude) == 2:
            return getattr(obj, "position", None) == exclude
        return False

    if include_heroes:
        for hero in getattr(game, "heroes", []):
            if _is_excluded(hero):
                continue
            if getattr(hero, "position", None) in neighbors:
                result["heroes"].append(hero)
                if hero_info:
                    try:
                        name = getattr(hero, "name", None) or getattr(hero, "object_id", "Hero")
                        get_ui_client().prompt_info(
                            info_title or "Splash Damage",
                            prompt_long=(
                                f"{name} otrzymuje {int(amount)} obrażeń splash "
                                f"({damage_type}). Zapisz ręcznie."
                            ),
                            source=source,
                        )
                    except Exception:
                        pass

    if include_enemies:
        for enemy in list(getattr(game, "enemies", [])):
            if _is_excluded(enemy):
                continue
            if getattr(enemy, "position", None) in neighbors:
                result["enemies"].append(enemy)
                apply = getattr(enemy, "apply_damage", None)
                defeated = False
                if callable(apply):
                    try:
                        _hp, defeated = apply(max(0, int(amount)), damage_type)
                    except Exception:
                        defeated = False
                if defeated:
                    result["defeated"].append(enemy)
                    if remove_defeated:
                        _remove_enemy_from_game(game, enemy)

    return result
