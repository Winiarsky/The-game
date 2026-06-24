from __future__ import annotations

from typing import Any

from economy import coin_pouch_from_cp, coin_pouch_total_cp, format_cp_value, normalize_coin_pouch
from GameObjects.items.inventory import item_label


def ensure_party_stash(game: Any) -> list[object]:
    raw = getattr(game, "party_stash", None)
    if not isinstance(raw, list):
        raw = []
        try:
            setattr(game, "party_stash", raw)
        except Exception:
            pass
    return raw


def ensure_party_coin_pouch(game: Any) -> dict[str, int]:
    raw = getattr(game, "party_coin_pouch", None)
    pouch = normalize_coin_pouch(raw)
    if isinstance(raw, dict):
        raw.clear()
        raw.update(pouch)
        return raw
    else:
        try:
            setattr(game, "party_coin_pouch", dict(pouch))
        except Exception:
            pass
    return pouch


def add_party_cp(game: Any, amount_cp: int) -> int:
    amount = max(0, int(amount_cp or 0))
    if amount <= 0:
        return 0
    pouch = ensure_party_coin_pouch(game)
    current = coin_pouch_total_cp(pouch)
    updated = coin_pouch_from_cp(current + amount)
    pouch.clear()
    pouch.update(updated)
    try:
        setattr(game, "party_coin_pouch", pouch)
    except Exception:
        pass
    return amount


def add_party_stash_items(game: Any, items: list[object]) -> int:
    stash = ensure_party_stash(game)
    count = 0
    for item in list(items or []):
        if item is None:
            continue
        stash.append(item)
        count += 1
    return count


def take_party_stash_item(game: Any, index: int) -> object | None:
    stash = ensure_party_stash(game)
    try:
        idx = int(index)
    except Exception:
        return None
    if idx < 0 or idx >= len(stash):
        return None
    return stash.pop(idx)


def party_stash_items(game: Any) -> list[object]:
    return list(ensure_party_stash(game))


def format_party_money(game: Any) -> str:
    return format_cp_value(coin_pouch_total_cp(ensure_party_coin_pouch(game)))


def currency_cp(item: object) -> int | None:
    if not isinstance(item, dict) or str(item.get("kind", "")).strip().lower() != "currency_cp":
        return None
    try:
        return max(0, int(item.get("amount_cp", 0) or 0))
    except Exception:
        return 0


def split_currency(items: list[object]) -> tuple[list[object], int]:
    item_loot: list[object] = []
    coin_cp = 0
    for item in list(items or []):
        amount_cp = currency_cp(item)
        if amount_cp is not None:
            coin_cp += amount_cp
            continue
        item_loot.append(item)
    return item_loot, coin_cp


def item_summary(items: list[object], coin_cp: int = 0, *, max_items: int = 4) -> str:
    labels = [item_label(item) for item in list(items or [])]
    parts: list[str] = []
    shown = labels[:max_items]
    if shown:
        parts.append(", ".join(shown))
    if len(labels) > max_items:
        parts.append(f"+{len(labels) - max_items} więcej")
    if coin_cp > 0:
        parts.append(f"monety: {format_cp_value(coin_cp)}")
    return ", ".join(part for part in parts if str(part).strip()) or "nic użytecznego"


def item_details_markdown(items: list[object], coin_cp: int = 0) -> str:
    rows = [f"- {item_label(item)}" for item in list(items or [])]
    if coin_cp > 0:
        rows.append(f"- monety: {format_cp_value(coin_cp)}")
    return "\n".join(rows) if rows else "- nic użytecznego"


def find_loot_piles(game: Any) -> list[object]:
    board = getattr(game, "board", None)
    if board is None:
        return []
    try:
        from GameObjects.Interactables.loot_pile import LootPile
    except Exception:
        LootPile = None  # type: ignore[assignment]
    piles: list[object] = []
    rows = int(getattr(board, "rows", 0) or 0)
    cols = int(getattr(board, "cols", 0) or 0)
    for row in range(rows):
        for col in range(cols):
            try:
                objects = list(board.interactables_at((col, row)))
            except Exception:
                continue
            for obj in objects:
                if LootPile is not None and not isinstance(obj, LootPile):
                    continue
                if not list(getattr(obj, "loot_items", []) or []):
                    continue
                piles.append(obj)
    return piles


__all__ = [
    "add_party_cp",
    "add_party_stash_items",
    "currency_cp",
    "ensure_party_coin_pouch",
    "ensure_party_stash",
    "find_loot_piles",
    "format_party_money",
    "item_details_markdown",
    "item_summary",
    "party_stash_items",
    "split_currency",
    "take_party_stash_item",
]
