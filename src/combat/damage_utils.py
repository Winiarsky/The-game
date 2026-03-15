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


def _normalize_burn_it_source_kind(value: object) -> str:
    raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if raw in {"spell", "alchemical"}:
        return raw
    return ""


def _to_non_negative_int(value: object, *, default: int = 0) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = int(default)
    return max(0, parsed)


def _burn_it_persistent_bonus(actor: Any) -> int:
    default_bonus = 1
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return default_bonus
    for status in statuses:
        if getattr(status, "id", None) != "burn_it":
            continue
        data = getattr(status, "data", None)
        if isinstance(data, dict):
            return _to_non_negative_int(data.get("burn_it_persistent_bonus", 1), default=1)
        return default_bonus
    return default_bonus


def burn_it_bonus(
    actor: Any,
    damage_type: str,
    *,
    persistent: bool = False,
    source_kind: str | None = None,
    spell_rank: int | None = None,
    item_level: int | None = None,
) -> int:
    """Zwróć bonus z Burn It! dla obrażeń ognia.

    By the book:
    - spell: połowa rangi czaru (min. 1),
    - alchemical: 1/4 poziomu przedmiotu (min. 1),
    - persistent fire: +1 status.
    """
    if damage_type != DamageType.FIRE.value:
        return 0
    if not _has_status(actor, "burn_it"):
        return 0
    source = _normalize_burn_it_source_kind(source_kind)
    if source not in {"spell", "alchemical"}:
        return 0
    if persistent:
        return _burn_it_persistent_bonus(actor)
    if source == "spell":
        rank = _to_non_negative_int(spell_rank, default=1)
        return max(1, rank // 2)
    lvl = _to_non_negative_int(item_level, default=1)
    return max(1, lvl // 4)


def burn_it_prompt_note(
    actor: Any,
    damage_type: str,
    *,
    persistent: bool = False,
    source_kind: str | None = None,
    spell_rank: int | None = None,
    item_level: int | None = None,
) -> str | None:
    bonus = burn_it_bonus(
        actor,
        damage_type,
        persistent=persistent,
        source_kind=source_kind,
        spell_rank=spell_rank,
        item_level=item_level,
    )
    if not bonus:
        return None
    if persistent:
        return f"Burn It!: +{bonus} status do persistent fire (dodane automatycznie)."
    source = _normalize_burn_it_source_kind(source_kind)
    if source == "spell":
        rank = _to_non_negative_int(spell_rank, default=1)
        return (
            f"Burn It!: +{bonus} status do obrażeń ognia "
            f"(czar rangi {rank}, połowa rangi; dodane automatycznie)."
        )
    if source == "alchemical":
        lvl = _to_non_negative_int(item_level, default=1)
        return (
            f"Burn It!: +{bonus} status do obrażeń ognia "
            f"(przedmiot poziomu {lvl}, 1/4 poziomu; dodane automatycznie)."
        )
    return None


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
    remove_defeated_enemy(game, enemy, source="splash")


def _extract_enemy_loot(enemy: Any) -> list[object]:
    loot: list[object] = []
    explicit_loot = getattr(enemy, "loot_items", None)
    if isinstance(explicit_loot, list):
        loot.extend([item for item in list(explicit_loot) if item is not None])
    inventory = getattr(enemy, "inventory", None)
    if isinstance(inventory, list):
        loot.extend([item for item in list(inventory) if item is not None])

    cp_total = 0
    try:
        cp_total += max(0, int(getattr(enemy, "loot_cp", 0) or 0))
    except Exception:
        pass
    try:
        from economy import coin_pouch_total_cp

        cp_total += max(0, int(coin_pouch_total_cp(getattr(enemy, "coin_pouch", None)) or 0))
    except Exception:
        pass
    if cp_total > 0:
        loot.append({"kind": "currency_cp", "amount_cp": int(cp_total)})
    return loot


def _drop_loot_pile(game: Any, pos: tuple[int, int], loot: list[object]) -> int:
    if game is None or not loot:
        return 0
    board = getattr(game, "board", None)
    if board is None:
        return 0
    try:
        from GameObjects.Interactables.loot_pile import LootPile
    except Exception:
        return 0

    pile = None
    try:
        for obj in list(board.interactables_at(pos)):
            if isinstance(obj, LootPile):
                pile = obj
                break
    except Exception:
        pile = None

    if pile is None:
        try:
            pile = LootPile()
            board.add_interactable(pile, pos)
        except Exception:
            return 0

    added = 0
    for item in loot:
        if item is None:
            continue
        try:
            pile.loot_items.append(item)
            added += 1
        except Exception:
            continue
    return int(added)


def remove_defeated_enemy(
    game: Any,
    enemy: Any,
    *,
    position: tuple[int, int] | None = None,
    drop_loot: bool = True,
    source: str = "damage",
) -> dict[str, Any]:
    """Usuń pokonanego przeciwnika z planszy/listy i opcjonalnie zostaw loot."""
    pos = position if isinstance(position, tuple) else getattr(enemy, "position", None)
    loot = _extract_enemy_loot(enemy) if drop_loot else []
    removed_from_board = False

    board = getattr(game, "board", None)
    if board is not None and isinstance(pos, tuple):
        should_remove = True
        try:
            occ_getter = getattr(board, "occupant_at", None)
            if callable(occ_getter):
                occ = occ_getter(pos)
                if occ is not enemy and occ is not None:
                    should_remove = False
        except Exception:
            should_remove = True
        if should_remove:
            try:
                board.remove(pos)
                removed_from_board = True
            except Exception:
                removed_from_board = False

    removed_from_list = False
    try:
        enemies = getattr(game, "enemies", None)
        if isinstance(enemies, list) and enemy in enemies:
            enemies.remove(enemy)
            removed_from_list = True
    except Exception:
        removed_from_list = False

    try:
        enemy.position = None
    except Exception:
        pass

    dropped = 0
    if isinstance(pos, tuple) and loot:
        dropped = _drop_loot_pile(game, pos, loot)
    try:
        setattr(enemy, "loot_items", [])
    except Exception:
        pass
    try:
        setattr(enemy, "inventory", [])
    except Exception:
        pass
    try:
        setattr(enemy, "loot_cp", 0)
    except Exception:
        pass
    try:
        setattr(enemy, "coin_pouch", {"cp": 0, "sp": 0, "gp": 0, "pp": 0})
    except Exception:
        pass

    return {
        "removed_from_board": bool(removed_from_board),
        "removed_from_list": bool(removed_from_list),
        "loot_dropped": int(dropped),
        "source": str(source),
    }


def cleanup_defeated_enemies(game: Any, *, drop_loot: bool = True, source: str = "cleanup") -> int:
    """Awaryjne sprzątanie martwych przeciwników pozostających na planszy/liście."""
    if game is None:
        return 0
    enemies = list(getattr(game, "enemies", []) or [])
    removed = 0
    for enemy in enemies:
        if enemy is None:
            continue
        is_defeated = False
        try:
            hp_value = getattr(enemy, "hp", 1)
            is_defeated = int(hp_value) <= 0
        except Exception:
            is_defeated = False
        if not is_defeated:
            is_defeated = _has_status(enemy, "dead")
        if not is_defeated:
            continue
        remove_defeated_enemy(game, enemy, drop_loot=drop_loot, source=source)
        removed += 1
    return int(removed)


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
                applied_automatically = False
                apply = getattr(hero, "apply_damage", None)
                if callable(apply):
                    try:
                        apply(max(0, int(amount)), damage_type)
                        applied_automatically = True
                    except Exception:
                        applied_automatically = False
                if hero_info:
                    try:
                        name = getattr(hero, "name", None) or getattr(hero, "object_id", "Hero")
                        if applied_automatically:
                            details = f"{name} otrzymuje {int(amount)} obrażeń splash ({damage_type})."
                        else:
                            details = (
                                f"{name} otrzymuje {int(amount)} obrażeń splash "
                                f"({damage_type}). Zapisz ręcznie."
                            )
                        get_ui_client().prompt_info(
                            info_title or "Splash Damage",
                            prompt_long=details,
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
