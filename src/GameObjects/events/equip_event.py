from __future__ import annotations

import ast
import logging
import random

from board import consts
from GameObjects.Interactables.loot_pile import LootPile
from GameObjects.items.goodberry_item import is_goodberry_item
from GameObjects.items.inventory import (
    all_inventory_sections,
    assign_item_to_hand,
    hand_slots_snapshot,
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
    "Nawigacja: 8=Góra, 2=Dół, 4=Poprzednia sekcja, 6=Następna sekcja, "
    "7=Przypnij lewa ręka, 9=Przypnij prawa ręka, "
    "Enter=Użyj/Aktywuj, /=Upuść, *=Przekaż, 0=Wyjdź"
)

_PROMPT_IMAGE = "/static/equip_nav_hint.svg"

_UP_COMMANDS = {"8", "end", "up", "arrowup"}
_DOWN_COMMANDS = {"2", "interact", "down", "arrowdown"}
_TOGGLE_COMMANDS = {"5", "enter", "use", "test_attack", "toggle", "activate"}
_SECTION_PREV_COMMANDS = {"4", "left", "section_prev", "prev_section"}
_SECTION_NEXT_COMMANDS = {"6", "right", "section_next", "next_section"}
_HAND_LEFT_COMMANDS = {"7", "hand_left", "left_hand", "main_hand", "lewa"}
_HAND_RIGHT_COMMANDS = {"9", "hand_right", "right_hand", "off_hand", "prawa"}
_TRANSFER_COMMANDS = {"*", "special", "transfer", "pass"}
_DROP_COMMANDS = {"/", "drop"}
_EXIT_COMMANDS = {"0", "cancel", "exit", "back"}

_CATEGORY_LABEL = {
    "weapon": "Bronie",
    "shield": "Tarcze",
    "armor": "Zbroje",
    "potion": "Mikstury",
    "ammo": "Amunicja",
    "gear": "Sprzet",
    "consumable": "Zuzywalne",
    "misc": "Inne",
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
    if text in _SECTION_PREV_COMMANDS:
        return "section_prev"
    if text in _SECTION_NEXT_COMMANDS:
        return "section_next"
    if text in _HAND_LEFT_COMMANDS:
        return "hand_left"
    if text in _HAND_RIGHT_COMMANDS:
        return "hand_right"
    if text in _TRANSFER_COMMANDS:
        return "transfer"
    if text in _DROP_COMMANDS:
        return "drop"
    if text in _EXIT_COMMANDS:
        return "exit"
    return text


def _decode_ui_command(answer: object, choice_meta: list[dict[str, str]]) -> str:
    if isinstance(answer, str):
        raw_text = str(answer).strip()
        if raw_text.startswith("{") and raw_text.endswith("}"):
            try:
                parsed = ast.literal_eval(raw_text)
            except Exception:
                parsed = None
            if isinstance(parsed, dict):
                answer = parsed

    if isinstance(answer, dict):
        raw_cmd = str(answer.get("cmd", "") or "").strip().lower()
        raw_selected = str(answer.get("selected", "") or "").strip().lower()
        cmd = _command_from_raw(raw_cmd)
        if cmd in {"section_prev", "section_next"}:
            return cmd
        if cmd in {"hand_left", "hand_right", "transfer", "drop", "toggle"} and raw_selected:
            return f"{cmd}:{raw_selected}"
        if raw_selected:
            return raw_selected
        return cmd or "noop"

    raw = str(answer or "").strip()
    if not raw:
        return "noop"
    low = raw.lower()

    for entry in choice_meta:
        raw_id = str(entry.get("raw", "")).strip().lower()
        label = str(entry.get("label", "")).strip().lower()
        if low == raw_id or (label and low == label):
            return raw_id or "noop"

    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(choice_meta):
            mapped = str(choice_meta[idx].get("raw", "")).strip().lower()
            if mapped:
                return mapped

    return _command_from_raw(raw)


def _decode_item_index(command: str, entries: list[tuple[str, object]]) -> tuple[int, object] | tuple[None, None]:
    raw = str(command or "").strip().lower()
    if raw.startswith("item:"):
        try:
            idx = int(raw.split(":", 1)[1])
        except Exception:
            return None, None
        if 0 <= idx < len(entries):
            return idx, entries[idx][1]
        return None, None
    return None, None


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


def _ordered_categories(entries: list[tuple[str, object]]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for category, _item in entries:
        if category in seen:
            continue
        seen.add(category)
        ordered.append(category)
    return ordered


def _section_index_for_cursor(entries: list[tuple[str, object]], cursor: int) -> int:
    if not entries:
        return 0
    cursor = max(0, min(int(cursor), len(entries) - 1))
    category = str(entries[cursor][0] or "")
    categories = _ordered_categories(entries)
    if category in categories:
        return categories.index(category)
    return 0


def _cursor_for_section(entries: list[tuple[str, object]], section_index: int) -> int:
    if not entries:
        return 0
    categories = _ordered_categories(entries)
    if not categories:
        return 0
    normalized = int(section_index) % len(categories)
    target_category = categories[normalized]
    for idx, (category, _item) in enumerate(entries):
        if category == target_category:
            return idx
    return 0


def _move_cursor_section(entries: list[tuple[str, object]], cursor: int, delta: int) -> int:
    if not entries:
        return 0
    current_section = _section_index_for_cursor(entries, cursor)
    return _cursor_for_section(entries, current_section + int(delta))


def _item_mechanics_description(item) -> str:
    category = item_category(item)
    lines: list[str] = ["Mechanika:"]
    if category == "weapon":
        damage = str(getattr(item, "damage_prompt", "") or "")
        damage_type = str(getattr(item, "damage_type", "") or "").strip()
        hands = int(getattr(item, "hands_required", 1) or 1)
        ranged = bool(getattr(item, "ranged", False))
        prof = str(getattr(item, "proficiency_category", "") or "").strip()
        group = str(getattr(item, "weapon_group", "") or "").strip()
        if damage:
            dmg_line = f"- Atak: {damage}"
            if damage_type:
                dmg_line += f" ({damage_type})"
            lines.append(dmg_line)
        lines.append(f"- Typ: {'dystansowa' if ranged else 'wręcz'}")
        lines.append(f"- Ręce: {hands}H")
        if ranged:
            range_inc = int(getattr(item, "range_increment_ft", 0) or 0)
            reload = int(getattr(item, "reload", 0) or 0)
            lines.append(f"- Zasięg przyrostowy: {range_inc} ft")
            lines.append(f"- Przeładowanie: {reload}")
        if prof or group:
            lines.append(f"- Biegłość: {prof or '-'}")
            lines.append(f"- Grupa: {group or '-'}")
    elif category == "armor":
        try:
            from GameObjects.items.armor.specialization import (
                armor_group_label_pl,
                armor_specialization_description_pl,
            )
        except Exception:
            armor_group_label_pl = lambda value: str(value or "cloth")  # type: ignore[assignment]
            armor_specialization_description_pl = lambda **_kwargs: "-"  # type: ignore[assignment]
        ac_bonus = int(getattr(item, "ac_bonus", 0) or 0)
        dex_cap = int(getattr(item, "dex_cap", 0) or 0)
        str_req = int(getattr(item, "strength_requirement", 0) or 0)
        check_penalty = int(getattr(item, "check_penalty", 0) or 0)
        speed_penalty = int(getattr(item, "speed_penalty_feet", 0) or 0)
        armor_cat = str(getattr(item, "armor_category", "") or "").strip()
        armor_group = str(getattr(item, "armor_group", "cloth") or "cloth").strip().lower()
        traits = [str(tag or "").strip().lower() for tag in tuple(getattr(item, "traits", ()) or ()) if str(tag or "").strip()]
        trait_hints = {
            "comfort": "wygodny pancerz (bez dodatkowych efektow mechanicznych na tym etapie).",
            "flexible": "kara pancerza nie dotyczy Acrobatics i Athletics.",
            "noisy": "kara pancerza do Stealth zawsze obowiazuje.",
            "bulwark": "w Reflex vs efekty obszarowe liczysz min. +3 z DEX.",
        }
        specialization = armor_specialization_description_pl(
            armor_group=armor_group,
            armor_category=armor_cat or "light",
        )
        lines.append(f"- Pancerz: {armor_cat}")
        lines.append(f"- Grupa pancerza: {armor_group_label_pl(armor_group)}")
        lines.append(f"- AC: +{ac_bonus}")
        lines.append(f"- Limit DEX: +{dex_cap}")
        lines.append(f"- Wymagana STR: {str_req}")
        lines.append(f"- Kara testowa: -{check_penalty}")
        if speed_penalty > 0:
            lines.append(f"- Kara prędkości: -{speed_penalty} ft")
        lines.append(f"- Specjalizacja pancerza: {specialization}")
        bulwark_floor = getattr(item, "bulwark_reflex_floor", None)
        if bulwark_floor is not None:
            lines.append(f"- Bulwark Reflex floor: +{int(bulwark_floor)}")
        if traits:
            lines.append(f"- Cechy: {', '.join(traits)}")
            for tag in traits:
                hint = trait_hints.get(tag)
                if hint:
                    lines.append(f"- Trait {tag}: {hint}")
                else:
                    lines.append(f"- Trait {tag}: cecha specjalna pancerza.")
    elif category == "shield":
        ac_bonus = int(getattr(item, "ac_bonus", 0) or 0)
        take_cover_ac = int(getattr(item, "take_cover_ac_bonus", ac_bonus) or ac_bonus)
        hardness = int(getattr(item, "hardness", 0) or 0)
        hp = int(getattr(item, "current_hp", getattr(item, "max_hp", 0)) or 0)
        hp_max = int(getattr(item, "max_hp", hp) or hp)
        bt = int(getattr(item, "broken_threshold", 0) or 0)
        speed_penalty = int(getattr(item, "speed_penalty_feet", 0) or 0)
        traits = {str(tag or "").strip().lower() for tag in tuple(getattr(item, "traits", ()) or ())}
        ac_line = f"- AC z Raise Shield: +{ac_bonus}"
        if take_cover_ac > ac_bonus:
            lines.append(ac_line)
            lines.append(f"- AC z Take Cover: +{take_cover_ac}")
        else:
            lines.append(ac_line)
        lines.append(f"- Hardness: {hardness}")
        lines.append(f"- HP: {hp}/{hp_max}")
        lines.append(f"- BT: {bt}")
        if speed_penalty > 0:
            lines.append(f"- Kara prędkości po Raise Shield: -{speed_penalty} ft")
        if "tower_shield" in traits:
            lines.append("- Tower Shield: podniesiona tarcza daje osłonę na linii strzału; z Take Cover daje greater cover (+4 AC).")
    else:
        lines.append(f"- Typ przedmiotu: {category}")

    traits = tuple(getattr(item, "traits", ()) or ())
    if traits and category != "armor":
        lines.append(f"- Cechy: {', '.join(str(tag) for tag in traits)}")

    try:
        price_label = item._price_label(int(getattr(item, "price_cp", 0) or 0))  # type: ignore[attr-defined]
        bulk_label = item._bulk_label(getattr(item, "bulk", "-"))  # type: ignore[attr-defined]
    except Exception:
        price_label = f"{int(getattr(item, 'price_cp', 0) or 0)} cp"
        bulk_label = str(getattr(item, "bulk", "-") or "-")
    lines.append(f"- Cena: {price_label}")
    lines.append(f"- Bulk: {bulk_label}")

    use = ""
    try:
        use = str(item_description(item) or "")
    except Exception:
        use = ""
    if use:
        lines.append("")
        lines.append(use)
    return "\n".join(lines).strip()


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


def _render_hand_slots_line(actor) -> str:
    try:
        slots = hand_slots_snapshot(actor)
    except Exception:
        return "Ręce: -"
    left = (slots.get("left", {}) or {}).get("label", "Pusta ręka")
    right = (slots.get("right", {}) or {}).get("label", "Pusta ręka")
    mode = slots.get("mode_label", "")
    suffix = f" · {mode}" if mode else ""
    return f"Ręce: L={left} · P={right}{suffix}"


def _build_ui_item_choice_meta(actor, entries: list[tuple[str, object]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    hands_line = _render_hand_slots_line(actor)
    for idx, (category, item) in enumerate(entries):
        active = " [AKTYWNY]" if is_item_active(actor, item) else ""
        section = _section_title(category).upper()
        label = f"[{section}] {item_label(item)}{active}"
        desc = (
            f"Kategoria: {item_category(item)} ({_section_title(category)})\n"
            f"{hands_line}\n"
            f"{_item_mechanics_description(item)}"
        )
        out.append(
            {
                "raw": f"item:{idx}",
                "label": label,
                "desc": desc,
                "key": "",
            }
        )
    out.append(
        {
            "raw": "exit",
            "label": "Zamknij ekwipunek",
            "desc": "Powrót bez zmian.",
            "key": "0",
        }
    )
    return out


@register_event
class EquipEvent(ActionCostEvent):
    name = "equip"
    default_tags = ["equip", "manipulate", "inventory"]
    available_in_combat = True
    available_in_exploration = True
    consumes_action = True
    actions_cost = 1

    def _read_ui_selection(self, ctx: EventContext, actor, entries: list[tuple[str, object]], selected_idx: int) -> str:
        ui = getattr(ctx.game, "ui", None)
        if not (ui and getattr(ui, "enabled", False)):
            return "noop"
        choice_meta = _build_ui_item_choice_meta(actor, entries)
        section_idx = _section_index_for_cursor(entries, selected_idx) + 1 if entries else 0
        section_count = len(_ordered_categories(entries))
        ans = ui.prompt_choice(
            "Ekwipunek",
            choices=[entry["label"] for entry in choice_meta],
            source="equip",
            layout="menu_numpad",
            choice_meta=choice_meta,
            title="Ekwipunek",
            subtitle=f"Sekcja {section_idx}/{section_count} · 8/2 item · 4/6 sekcja · 7/9 ręce · Enter użyj",
            prompt_long="",
            image=_PROMPT_IMAGE,
            preselected_index=max(0, int(selected_idx)),
        )
        return _decode_ui_command(ans, choice_meta)

    def _consume_goodberry(self, ctx: EventContext, actor, item) -> tuple[bool, str]:
        if not remove_item(actor, item):
            return False, "Nie udało się zużyć Goodberry."

        heal_roll = random.randint(1, 6)
        heal_amount = int(heal_roll) + 4
        healer = getattr(actor, "heal", None)
        if callable(healer):
            try:
                healer(heal_amount)
            except Exception:
                pass

        prompt_long = (
            "Zjedzono Goodberry.\n"
            f"Leczenie: {heal_roll} + 4 = {heal_amount} HP."
        )
        prompted = False
        ui = getattr(ctx.game, "ui", None)
        if ui is not None and hasattr(ui, "prompt_info"):
            try:
                ui.prompt_info("Goodberry", prompt_long=prompt_long, source="goodberry_item")
                prompted = True
            except Exception:
                pass
        if not prompted:
            try:
                from ui_client import get_ui_client

                get_ui_client().prompt_info("Goodberry", prompt_long=prompt_long, source="goodberry_item")
            except Exception:
                pass
        return True, f"Zużyto Goodberry: uleczono {heal_amount} HP."

    def _read_command(self, ctx: EventContext, *, prompt_long: str, subtitle: str) -> str:
        ui = getattr(ctx.game, "ui", None)
        if ui and getattr(ui, "enabled", False):
            choice_meta: list[dict[str, str]] = [
                {"raw": "up", "label": "Góra", "desc": "Przesuń zaznaczenie do góry.", "key": "8"},
                {"raw": "down", "label": "Dół", "desc": "Przesuń zaznaczenie w dół.", "key": "2"},
                {"raw": "toggle", "label": "Aktywuj/Dezaktywuj", "desc": "Przełącz stan itemu.", "key": "Enter"},
                {"raw": "section_prev", "label": "Poprzednia sekcja", "desc": "Przejdź do poprzedniej sekcji ekwipunku.", "key": "4"},
                {"raw": "section_next", "label": "Następna sekcja", "desc": "Przejdź do następnej sekcji ekwipunku.", "key": "6"},
                {"raw": "hand_left", "label": "Lewa ręka", "desc": "Przypnij/aktywuj item w lewej ręce.", "key": "7"},
                {"raw": "hand_right", "label": "Prawa ręka", "desc": "Przypnij/aktywuj item w prawej ręce.", "key": "9"},
                {"raw": "drop", "label": "Upuść", "desc": "Upuść item na pole jako loot.", "key": "/"},
                {"raw": "transfer", "label": "Przekaż", "desc": "Przekaż item innemu bohaterowi.", "key": "*"},
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
            return _decode_ui_command(ans, choice_meta)
        try:
            raw = ctx.game.conn.read_card("Ekwipunek: 8/2/4/6/7/9/*//Enter/0", [])
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

        spent_actions = 0
        last_message: str | None = None
        remaining_actions: int | None = None
        if ctx.in_combat:
            try:
                remaining_actions = int(self._actions_remaining(ctx, actor) or 0)
            except Exception:
                remaining_actions = None

        def _finish_or_continue(success: bool, message: str) -> EventResult | None:
            nonlocal spent_actions, last_message
            last_message = message
            try:
                ctx.game.ui_log(message)
            except Exception:
                pass
            if not success:
                return None
            spent_actions += 1
            if remaining_actions is not None and spent_actions >= max(0, remaining_actions):
                return EventResult(
                    success=True,
                    consumed_action=spent_actions > 0,
                    actions_spent=spent_actions,
                    message=last_message or "Wykorzystano wszystkie akcje na ekwipunek.",
                )
            return None

        ui = getattr(ctx.game, "ui", None)
        if ui and getattr(ui, "enabled", False):
            cursor = int(getattr(actor, "inventory_cursor", 0) or 0)
            while True:
                entries = _selection_entries(actor)
                if not entries:
                    if spent_actions > 0:
                        return EventResult(
                            success=True,
                            consumed_action=True,
                            actions_spent=spent_actions,
                            message=last_message or "Ekwipunek jest pusty.",
                        )
                    return EventResult.cancelled(message="Ekwipunek jest pusty.")

                cursor = max(0, min(cursor, len(entries) - 1))
                command = self._read_ui_selection(ctx, actor, entries, cursor)
                if command == "up":
                    cursor = (cursor - 1 + len(entries)) % len(entries)
                    continue
                if command == "down":
                    cursor = (cursor + 1) % len(entries)
                    continue
                if command == "section_prev":
                    cursor = _move_cursor_section(entries, cursor, -1)
                    continue
                if command == "section_next":
                    cursor = _move_cursor_section(entries, cursor, 1)
                    continue
                if command == "exit":
                    try:
                        setattr(actor, "inventory_cursor", cursor)
                    except Exception:
                        pass
                    if spent_actions > 0:
                        return EventResult(
                            success=True,
                            consumed_action=True,
                            actions_spent=spent_actions,
                            message=last_message or "Zamknięto ekwipunek.",
                        )
                    if last_message:
                        return EventResult.cancelled(message=last_message)
                    return EventResult.cancelled(message="Zamknięto ekwipunek.")

                handled = False
                for prefix in ("hand_left:", "hand_right:", "drop:", "transfer:", "toggle:"):
                    if not command.startswith(prefix):
                        continue
                    local_cmd, raw_item = command.split(":", 1)
                    idx, selected_item = _decode_item_index(raw_item, entries)
                    if idx is None or selected_item is None:
                        last_message = "Nieprawidłowy wybór przedmiotu."
                        handled = True
                        break
                    cursor = idx
                    if local_cmd == "hand_left":
                        success, message = assign_item_to_hand(actor, selected_item, "left")
                    elif local_cmd == "hand_right":
                        success, message = assign_item_to_hand(actor, selected_item, "right")
                    elif local_cmd == "drop":
                        success, message = self._drop_item(ctx, actor, selected_item)
                    elif local_cmd == "transfer":
                        target = _pick_transfer_target(ctx, actor)
                        if target is None:
                            success = False
                            message = "Brak sąsiedniego bohatera do przekazania." if ctx.in_combat else "Brak bohatera do przekazania."
                        else:
                            success, message = transfer_item(actor, target, selected_item)
                    else:  # toggle
                        if is_goodberry_item(selected_item):
                            success, message = self._consume_goodberry(ctx, actor, selected_item)
                        else:
                            success, message = toggle_item_activation(actor, selected_item)
                    maybe_finish = _finish_or_continue(success, message)
                    if maybe_finish is not None:
                        return maybe_finish
                    handled = True
                    break
                if handled:
                    continue

                if command in {"hand_left", "hand_right"} and entries:
                    selected_item = entries[cursor][1]
                    side = "left" if command == "hand_left" else "right"
                    success, message = assign_item_to_hand(actor, selected_item, side)
                    maybe_finish = _finish_or_continue(success, message)
                    if maybe_finish is not None:
                        return maybe_finish
                    continue

                idx, selected_item = _decode_item_index(command, entries)
                if idx is not None and selected_item is not None:
                    cursor = idx
                    if is_goodberry_item(selected_item):
                        success, message = self._consume_goodberry(ctx, actor, selected_item)
                    else:
                        success, message = toggle_item_activation(actor, selected_item)
                    maybe_finish = _finish_or_continue(success, message)
                    if maybe_finish is not None:
                        return maybe_finish
                    continue
                last_message = f"Nieznana komenda ekwipunku: {command}."
                try:
                    ctx.game.ui_log(last_message)
                except Exception:
                    pass
                continue

        cursor = int(getattr(actor, "inventory_cursor", 0) or 0)

        while True:
            entries = _selection_entries(actor)
            if not entries:
                if spent_actions > 0:
                    return EventResult(
                        success=True,
                        consumed_action=True,
                        actions_spent=spent_actions,
                        message=last_message or "Ekwipunek jest pusty.",
                    )
                return EventResult.cancelled(message="Ekwipunek jest pusty.")
            cursor = max(0, min(cursor, len(entries) - 1))
            _category, selected_item = entries[cursor]

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
            if command == "section_prev":
                cursor = _move_cursor_section(entries, cursor, -1)
                continue
            if command == "section_next":
                cursor = _move_cursor_section(entries, cursor, 1)
                continue
            if command == "exit":
                try:
                    setattr(actor, "inventory_cursor", cursor)
                except Exception:
                    pass
                if spent_actions > 0:
                    return EventResult(
                        success=True,
                        consumed_action=True,
                        actions_spent=spent_actions,
                        message=last_message or "Zamknięto ekwipunek.",
                    )
                if last_message:
                    return EventResult.cancelled(message=last_message)
                return EventResult.cancelled(message="Zamknięto ekwipunek.")

            if command == "toggle":
                if is_goodberry_item(selected_item):
                    success, message = self._consume_goodberry(ctx, actor, selected_item)
                else:
                    success, message = toggle_item_activation(actor, selected_item)
                try:
                    setattr(actor, "inventory_cursor", inventory_index_of(actor, selected_item))
                except Exception:
                    pass
                maybe_finish = _finish_or_continue(success, message)
                if maybe_finish is not None:
                    return maybe_finish
                continue

            if command == "hand_left":
                success, message = assign_item_to_hand(actor, selected_item, "left")
                maybe_finish = _finish_or_continue(success, message)
                if maybe_finish is not None:
                    return maybe_finish
                continue

            if command == "hand_right":
                success, message = assign_item_to_hand(actor, selected_item, "right")
                maybe_finish = _finish_or_continue(success, message)
                if maybe_finish is not None:
                    return maybe_finish
                continue

            if command == "transfer":
                target = _pick_transfer_target(ctx, actor)
                if target is None:
                    if ctx.in_combat:
                        msg = "Brak sąsiedniego bohatera do przekazania."
                    else:
                        msg = "Brak bohatera do przekazania."
                    _finish_or_continue(False, msg)
                    continue
                success, message = transfer_item(actor, target, selected_item)
                maybe_finish = _finish_or_continue(success, message)
                if maybe_finish is not None:
                    return maybe_finish
                continue

            if command == "drop":
                success, message = self._drop_item(ctx, actor, selected_item)
                maybe_finish = _finish_or_continue(success, message)
                if maybe_finish is not None:
                    return maybe_finish
                continue

            # Dopuszczamy też szybkie przełączanie przez nazwę broni.
            maybe_weapon = normalize_weapon_id(command)
            if maybe_weapon:
                for _, item in entries:
                    if normalize_weapon_id(getattr(item, "item_id", None)) == maybe_weapon:
                        success, message = toggle_item_activation(actor, item)
                        maybe_finish = _finish_or_continue(success, message)
                        if maybe_finish is not None:
                            return maybe_finish
                        break
                else:
                    _finish_or_continue(False, f"Brak broni '{maybe_weapon}' w ekwipunku.")
                continue

            logger.info("Nieznana komenda ekwipunku: %s", command)
            _finish_or_continue(False, f"Nieznana komenda ekwipunku: {command}.")
            continue
