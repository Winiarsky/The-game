from __future__ import annotations

import logging

from board import consts
from GameObjects.Interactables.loot_pile import LootPile
from GameObjects.items.inventory import (
    all_inventory_sections,
    ensure_actor_inventory,
    inventory_index_of,
    is_item_active,
    item_category,
    item_description,
    item_label,
    remove_item,
    toggle_item_activation,
    transfer_item,
)
from GameObjects.items.weapon import normalize_weapon_id

from .base import ActionCostEvent, EventContext, EventResult
from .registry import register_event

logger = logging.getLogger(__name__)


_LEGEND = (
    "Nawigacja: 8=Góra, 2=Dół, 5=Aktywuj/Dezaktywuj, "
    "6=Przekaż, 4=Upuść, 0=Wyjdź"
)

_PROMPT_IMAGE = "/static/equip_nav_hint.svg"

_UP_COMMANDS = {"8", "end", "up", "arrowup"}
_DOWN_COMMANDS = {"2", "interact", "down", "arrowdown"}
_TOGGLE_COMMANDS = {"5", "test_attack", "toggle", "activate"}
_TRANSFER_COMMANDS = {"6", "special", "transfer", "pass"}
_DROP_COMMANDS = {"4", "stealth", "drop"}
_EXIT_COMMANDS = {"0", "cancel", "exit", "back"}

_CATEGORY_LABEL = {
    "weapon": "Bronie",
    "shield": "Tarcze",
    "armor": "Zbroje",
    "potion": "Mikstury",
}


def _command_from_raw(raw: object) -> str:
    text = str(raw or "").strip().lower()
    if not text:
        return "noop"
    if text in _UP_COMMANDS:
        return "up"
    if text in _DOWN_COMMANDS:
        return "down"
    if text in _TOGGLE_COMMANDS:
        return "toggle"
    if text in _TRANSFER_COMMANDS:
        return "transfer"
    if text in _DROP_COMMANDS:
        return "drop"
    if text in _EXIT_COMMANDS:
        return "exit"
    return text


def _target_heroes_for_transfer(ctx: EventContext, actor) -> list[object]:
    heroes = [hero for hero in getattr(ctx.game, "heroes", []) if hero is not actor and getattr(hero, "position", None) is not None]
    if not ctx.in_combat:
        return heroes
    board = getattr(ctx.game, "board", None)
    actor_pos = getattr(actor, "position", None)
    if board is None or actor_pos is None:
        return []
    neighbors = set(board.get_neighbors(actor_pos, include_position=False, diagonal=True))
    return [hero for hero in heroes if getattr(hero, "position", None) in neighbors]


def _pick_transfer_target(ctx: EventContext, actor) -> object | None:
    targets = _target_heroes_for_transfer(ctx, actor)
    if not targets:
        return None
    positions = [hero.position for hero in targets if getattr(hero, "position", None) is not None]
    if not positions:
        return None
    try:
        ui_log = getattr(ctx.game, "ui_log", None)
        if callable(ui_log):
            ui_log("Wskaż bohatera na planszy, któremu chcesz przekazać przedmiot.")
    except Exception:
        pass
    try:
        ctx.game.conn.set_leds(positions, consts.HERO_HIGHLIGHT_RGB)
    except Exception:
        pass
    try:
        selected_pos = ctx.game.conn.scan_board(positions)
    finally:
        try:
            ctx.game.conn.leds_off()
        except Exception:
            pass
    for hero in targets:
        if getattr(hero, "position", None) == selected_pos:
            return hero
    return None


def _section_title(category: str) -> str:
    return _CATEGORY_LABEL.get(category, category.replace("_", " ").title())


def _selection_entries(actor) -> list[tuple[str, object]]:
    entries: list[tuple[str, object]] = []
    for category, items in all_inventory_sections(actor):
        for item in items:
            entries.append((category, item))
    return entries


def _render_inventory_prompt(actor, entries: list[tuple[str, object]], selected_idx: int) -> str:
    lines: list[str] = []
    lines.append("Ekwipunek:")
    if not entries:
        lines.append("- brak przedmiotów")
        lines.append("")
        lines.append(_LEGEND)
        return "\n".join(lines)

    grouped = all_inventory_sections(actor)
    cursor_item = entries[selected_idx][1] if 0 <= selected_idx < len(entries) else None
    lines.append("")
    for category, items in grouped:
        lines.append(f"[{_section_title(category)}]")
        for item in items:
            selected = item is cursor_item
            marker = ">" if selected else " "
            active = " [AKTYWNY]" if is_item_active(actor, item) else ""
            lines.append(f"{marker} {item_label(item)}{active}")
        lines.append("")
    lines.append(_LEGEND)
    return "\n".join(lines).strip()


def _render_selected_subtitle(item) -> str:
    return f"Wybrano: {item_label(item)} ({item_category(item)})"


@register_event
class EquipEvent(ActionCostEvent):
    name = "equip"
    default_tags = ["equip", "manipulate", "inventory"]
    available_in_combat = True
    available_in_exploration = True
    consumes_action = True
    actions_cost = 1

    def _read_command(self, ctx: EventContext, *, prompt_long: str, subtitle: str) -> str:
        ui = getattr(ctx.game, "ui", None)
        if ui and getattr(ui, "enabled", False):
            choice_meta = [
                {"raw": "up", "label": "Góra", "desc": "Przesuń zaznaczenie do góry.", "key": "8"},
                {"raw": "down", "label": "Dół", "desc": "Przesuń zaznaczenie w dół.", "key": "2"},
                {"raw": "toggle", "label": "Aktywuj/Dezaktywuj", "desc": "Przełącz stan itemu.", "key": "5"},
                {"raw": "transfer", "label": "Przekaż", "desc": "Przekaż item innemu bohaterowi.", "key": "6"},
                {"raw": "drop", "label": "Upuść", "desc": "Upuść item na pole jako loot.", "key": "4"},
                {"raw": "exit", "label": "Wyjdź", "desc": "Zamknij bez zmian.", "key": "0"},
            ]
            ans = ui.prompt_choice(
                "Ekwipunek",
                choices=[entry["label"] for entry in choice_meta],
                source="equip",
                layout="equip_nav",
                choice_meta=choice_meta,
                title="Ekwipunek",
                subtitle=subtitle,
                prompt_long=prompt_long,
                image=_PROMPT_IMAGE,
            )
            return _command_from_raw(ans)
        try:
            raw = ctx.game.conn.read_card("Ekwipunek: 8/2/5/6/4/0", [])
        except Exception:
            raw = ""
        return _command_from_raw(raw)

    def _drop_item(self, ctx: EventContext, actor, item) -> tuple[bool, str]:
        actor_pos = getattr(actor, "position", None)
        board = getattr(ctx.game, "board", None)
        if actor_pos is None or board is None:
            return False, "Nie możesz upuścić przedmiotu poza planszą."
        if not remove_item(actor, item):
            return False, "Nie udało się usunąć przedmiotu z ekwipunku."
        pile = None
        for obj in list(board.interactables_at(actor_pos)):
            if isinstance(obj, LootPile):
                pile = obj
                break
        if pile is None:
            pile = LootPile()
            try:
                board.add_interactable(pile, actor_pos)
            except Exception:
                return False, "Nie udało się utworzyć znacznika loot."
        pile.loot_items.append(item)
        return True, f"Upuszczono {item_label(item)} na pole {actor_pos}."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do otwarcia ekwipunku.")

        entries = _selection_entries(actor)
        if not entries:
            return EventResult.cancelled(message="Ekwipunek jest pusty.")

        cursor = int(getattr(actor, "inventory_cursor", 0) or 0)
        cursor = max(0, min(cursor, len(entries) - 1))

        while True:
            entries = _selection_entries(actor)
            if not entries:
                return EventResult.cancelled(message="Ekwipunek jest pusty.")
            cursor = max(0, min(cursor, len(entries) - 1))
            category, selected_item = entries[cursor]

            subtitle = _render_selected_subtitle(selected_item)
            details = item_description(selected_item)
            prompt_long = f"{_render_inventory_prompt(actor, entries, cursor)}\n\nSzczegóły:\n{details}"
            command = self._read_command(ctx, prompt_long=prompt_long, subtitle=subtitle)

            if command == "up":
                cursor = (cursor - 1 + len(entries)) % len(entries)
                continue
            if command == "down":
                cursor = (cursor + 1) % len(entries)
                continue
            if command == "exit":
                try:
                    setattr(actor, "inventory_cursor", cursor)
                except Exception:
                    pass
                return EventResult.cancelled(message="Zamknięto ekwipunek.")

            if command == "toggle":
                success, message = toggle_item_activation(actor, selected_item)
                try:
                    setattr(actor, "inventory_cursor", inventory_index_of(actor, selected_item))
                except Exception:
                    pass
                return EventResult(success=success, consumed_action=bool(success), message=message)

            if command == "transfer":
                target = _pick_transfer_target(ctx, actor)
                if target is None:
                    if ctx.in_combat:
                        msg = "Brak sąsiedniego bohatera do przekazania."
                    else:
                        msg = "Brak bohatera do przekazania."
                    return EventResult.cancelled(message=msg)
                success, message = transfer_item(actor, target, selected_item)
                return EventResult(success=success, consumed_action=bool(success), message=message)

            if command == "drop":
                success, message = self._drop_item(ctx, actor, selected_item)
                return EventResult(success=success, consumed_action=bool(success), message=message)

            # Dopuszczamy też szybkie przełączanie przez nazwę broni.
            maybe_weapon = normalize_weapon_id(command)
            if maybe_weapon:
                for _, item in entries:
                    if normalize_weapon_id(getattr(item, "item_id", None)) == maybe_weapon:
                        success, message = toggle_item_activation(actor, item)
                        return EventResult(success=success, consumed_action=bool(success), message=message)
                return EventResult.cancelled(message=f"Brak broni '{maybe_weapon}' w ekwipunku.")

            logger.info("Nieznana komenda ekwipunku: %s", command)
            return EventResult.cancelled(message=f"Nieznana komenda ekwipunku: {command}.")
