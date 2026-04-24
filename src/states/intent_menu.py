from __future__ import annotations

import re
from typing import Any, Iterable

from localization import localize_term_pl, localized_hint_pl
from prompt_copy import merge_menu_prompt, render_prompt_copy

_SPELL_ID_ALIASES = {
    "shield": "shield_cantrip",
    "detectmagic": "detect_magic",
    "acidsplash": "acid_splash",
}

_CLASS_TAGS = {
    "alchemist",
    "barbarian",
    "bard",
    "champion",
    "cleric",
    "druid",
    "fighter",
    "monk",
    "ranger",
    "rogue",
    "sorcerer",
    "wizard",
}

_ANCESTRY_TAGS = {
    "dwarf",
    "elf",
    "gnome",
    "goblin",
    "halfling",
    "human",
    "orc",
}

_STATUS_GATED_ACTIONS = {
    "double_slice",
    "exacting_strike",
    "flurry_of_blows",
    "goblin_scuttle",
    "goblin_song",
    "hunted_shot",
    "hunt_prey",
    "point_blank_shot",
    "power_attack",
    "snagging_strike",
    "sudden_charge",
    "twin_feint",
    "twin_takedown",
}

_CLASS_GATED_ACTIONS: dict[str, str] = {
    "drain_bonded_item": "wizard",
    "drain_familiar": "wizard",
    "wizard_spell_substitution": "wizard",
    "rage": "barbarian",
}

_SPECIAL_SOURCE_CLASS_OVERRIDES = {
    "command_animal_companion",
    "commandfamilair",
    "hunt_prey",
    "hunted_shot",
}

_SPECIAL_SOURCE_HERITAGE_OVERRIDES = {
    "ancientblood",
    "goblin_scuttle",
    "goblin_song",
}

_HINT_ALIASES: dict[str, str] = {
    "cover": "take_cover",
}


def _labelize(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if _normalize(raw) == "shield":
        label = localize_term_pl("raise_shield")
        if label:
            return label
    return localize_term_pl(raw)


def _normalize(value: str | None) -> str:
    return str(value or "").strip().lower()


def _normalize_spell_id(value: str | None) -> str:
    raw = _normalize(value).replace("-", "_").replace(" ", "_")
    if not raw:
        return ""
    return _SPELL_ID_ALIASES.get(raw, raw)


def _with_numpad_hint(subtitle: str) -> str:
    hint = "8/2 nawigacja, Enter potwierdzenie."
    base = str(subtitle or "").strip()
    if not base:
        return hint
    if "8/2" in base and "Enter" in base:
        return base
    return f"{base} {hint}"


def _actions_cost_text_pl(value: object) -> str:
    try:
        cost = int(value or 1)
    except Exception:
        cost = 1
    cost = max(1, min(3, cost))
    if cost == 1:
        return "Koszt: 1 akcja"
    return f"Koszt: {cost} akcje"


def _first_nonempty_line(raw: object) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    for line in text.splitlines():
        line = str(line).strip()
        if line:
            return line
    return ""


def _normalize_hint_text(raw: object) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    parts = [part.strip() for part in re.split(r"\s*\|\s*", text) if part.strip()]
    if len(parts) <= 1:
        return text
    return "\n".join([parts[0]] + [f"- {part}" for part in parts[1:]])


def _hint_for_event(event_name: str) -> str:
    raw = _normalize(event_name)
    if not raw:
        return ""
    hint = localized_hint_pl(raw)
    if hint:
        return _normalize_hint_text(hint)
    alias = _normalize(_HINT_ALIASES.get(raw))
    if alias:
        return _normalize_hint_text(localized_hint_pl(alias))
    return ""


def _focus_pool_state(actor: Any) -> tuple[int, int]:
    if actor is None:
        return 0, 0
    try:
        from focus_pool import ensure_focus_pool

        return ensure_focus_pool(actor)
    except Exception:
        try:
            current = max(0, int(getattr(actor, "focus_point", 0) or 0))
        except Exception:
            current = 0
        max_pool = 0
        for attr_name in ("focus_pool_max", "wizard_focus_pool_max", "focus_pool_size"):
            try:
                max_pool = max(max_pool, max(0, int(getattr(actor, attr_name, 0) or 0)))
            except Exception:
                continue
        if current > 0:
            max_pool = max(max_pool, current)
        return current, max_pool


def _event_doc_hint(event_cls: type | None) -> str:
    if event_cls is None:
        return ""
    return _normalize_hint_text(_first_nonempty_line(getattr(event_cls, "__doc__", "")))


def _magic_event_desc(event_name: str, event_cls: type | None) -> str:
    hint = _hint_for_event(event_name) or _event_doc_hint(event_cls)
    if event_cls is None:
        return hint

    spell_tags = [str(tag).strip().lower().replace("-", "_").replace(" ", "_") for tag in list(getattr(event_cls, "spell_tags", []) or [])]
    default_tags = [
        str(tag).strip().lower().replace("-", "_").replace(" ", "_")
        for tag in list(getattr(event_cls, "default_tags", []) or [])
    ]
    tags = set(spell_tags + default_tags)

    tier_label = ""
    if "cantrip" in tags:
        tier_label = "Cantrip"
    elif "focus" in tags:
        tier_label = "Focus"
    else:
        for raw in sorted(tags):
            match = re.fullmatch(r"rank_?([0-9]+)", raw)
            if not match:
                continue
            try:
                rank = max(1, int(match.group(1)))
            except Exception:
                continue
            tier_label = f"Ranga {rank}"
            break

    spell_label = localize_term_pl(event_name) or event_name.replace("_", " ").title()
    fluff_suffix = f" ({tier_label})" if tier_label else ""
    fluff_line = f"Fluff: {spell_label}{fluff_suffix}"

    # Build "Kiedy:" line — cost + range
    try:
        cost = int(getattr(event_cls, "actions_cost", 1) or 1)
    except Exception:
        cost = 1
    cost = max(1, min(3, cost))
    cost_text = "1 akcja" if cost == 1 else f"{cost} akcje"

    raw_range = getattr(event_cls, "range_feet", None)
    if isinstance(raw_range, int):
        range_text = f"zasięg {max(0, raw_range)} ft"
    elif "touch" in tags:
        range_text = "zasięg: dotyk"
    else:
        range_text = ""
    kiedy_parts = [cost_text]
    if range_text:
        kiedy_parts.append(range_text)
    kiedy_line = "- Kiedy: " + ", ".join(kiedy_parts)

    # Build "Efekt:" content — hint as primary, mechanics as sub-bullets
    mech_parts: list[str] = []

    traditions = [tag for tag in ("arcane", "divine", "occult", "primal") if tag in tags]
    if traditions:
        mech_parts.append("Tradycja: " + ", ".join(localize_term_pl(tag) for tag in traditions))

    schools = [
        tag
        for tag in ("abjuration", "conjuration", "divination", "enchantment", "evocation", "illusion", "necromancy", "transmutation")
        if tag in tags
    ]
    if schools:
        mech_parts.append("Szkoła: " + ", ".join(localize_term_pl(tag) for tag in schools))

    save_type = str(getattr(event_cls, "save_type", "") or "").strip().lower()
    _SAVE_LABELS = {"fortitude": "Wytrzymałość", "reflex": "Refleks", "will": "Wola"}
    if save_type in _SAVE_LABELS:
        is_basic = bool(getattr(event_cls, "basic_save", False))
        save_label = _SAVE_LABELS[save_type]
        mech_parts.append(f"Rzut obronny: {save_label}{' (basic)' if is_basic else ''}")

    area_feet = getattr(event_cls, "area_feet", None)
    area_type = str(getattr(event_cls, "area_type", "") or "").strip().lower()
    if isinstance(area_feet, int) and area_feet > 0:
        area_suffix = f" {area_type}" if area_type else ""
        mech_parts.append(f"Obszar: {area_feet} ft{area_suffix}")

    duration = str(getattr(event_cls, "duration", "") or "").strip()
    if duration:
        mech_parts.append(f"Czas trwania: {duration}")

    efekt_text = " ".join(hint.splitlines()).strip() if hint else "brak opisu"
    efekt_line = f"- Efekt: {efekt_text}"
    if mech_parts:
        efekt_line += "\n" + "\n".join(f"  - {p}" for p in mech_parts)

    return f"{fluff_line}\nMechanika:\n{kiedy_line}\n{efekt_line}"


def _attack_event_desc(event_name: str, event_cls: type | None) -> str:
    hint = _hint_for_event(event_name) or _event_doc_hint(event_cls)
    if event_cls is None:
        return hint
    parts: list[str] = []
    parts.append(_actions_cost_text_pl(getattr(event_cls, "actions_cost", 1)))

    damage_prompt = str(getattr(event_cls, "damage_prompt", "") or "").strip()
    if damage_prompt:
        parts.append(f"Obrazenia: {damage_prompt}")

    range_feet = getattr(event_cls, "range_feet", None)
    if isinstance(range_feet, int) and range_feet > 0:
        parts.append(f"Zasieg: {range_feet} ft")
    elif bool(getattr(event_cls, "range_increment_ft", 0)):
        try:
            incr = int(getattr(event_cls, "range_increment_ft", 0) or 0)
        except Exception:
            incr = 0
        if incr > 0:
            parts.append(f"Przyrost zasiegu: {incr} ft")

    text = "\n".join(f"- {part}" for part in parts if part)
    if hint:
        return f"{hint}\n{text}".strip() if text else hint
    return text


def _alchemy_tier_preview(tiers: object) -> str:
    if not isinstance(tiers, dict) or not tiers:
        return ""
    ordered_names = ("lesser", "moderate", "greater", "major")
    chosen_name = ""
    chosen_data: dict[str, Any] = {}
    for name in ordered_names:
        entry = tiers.get(name)
        if isinstance(entry, dict):
            chosen_name = str(name)
            chosen_data = dict(entry)
            break
    if not chosen_data:
        for raw_name, raw_data in tiers.items():
            if not isinstance(raw_data, dict):
                continue
            chosen_name = str(raw_name)
            chosen_data = dict(raw_data)
            break
    if not chosen_data:
        return ""

    fragments: list[str] = []

    def _append_stat(field: str, label: str, signed: bool = False, negate: bool = False) -> None:
        raw = chosen_data.get(field, None)
        if raw is None:
            return
        try:
            value = int(raw)
        except Exception:
            return
        if negate:
            value = -value
        if signed:
            fragments.append(f"{label} {value:+d}")
        else:
            fragments.append(f"{label} {value}")

    _append_stat("item_bonus", "premia item", signed=True)
    _append_stat("bonus", "premia", signed=True)
    _append_stat("base_bonus", "premia bazowa", signed=True)
    _append_stat("secret_bonus", "premia sekretna", signed=True)
    _append_stat("save_bonus", "premia do obrony", signed=True)
    _append_stat("speed_bonus", "predkosc", signed=True)
    _append_stat("speed_penalty", "predkosc", signed=True, negate=True)
    _append_stat("dc", "ST")
    _append_stat("escape_dc", "ST Ucieczki")
    _append_stat("splash", "splash")
    _append_stat("temp_hp", "tymczasowe HP")
    _append_stat("duration", "czas")

    for key, label in (
        ("damage_dice", "obrażenia"),
        ("persistent", "trwałe"),
        ("heal_dice", "leczenie"),
        ("fort_crit", "Wytrz. kryt."),
        ("will_crit", "Wola kryt."),
        ("extra_save", "dodatkowy rzut"),
        ("trained_skill", "test umiejętności"),
    ):
        raw = chosen_data.get(key, None)
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            fragments.append(f"{label}: {text}")

    if not fragments:
        return ""
    tier_label = localize_term_pl(chosen_name) or chosen_name
    return f"Poziom {tier_label}: " + ", ".join(fragments[:6])


def _alchemy_event_desc(event_name: str, event_cls: type | None) -> str:
    hint = _hint_for_event(event_name) or _event_doc_hint(event_cls)
    if event_cls is None:
        return hint
    parts: list[str] = []
    parts.append(_actions_cost_text_pl(getattr(event_cls, "actions_cost", 1)))

    tiers = getattr(event_cls, "tiers", None)
    if isinstance(tiers, dict) and tiers:
        tier_preview = _alchemy_tier_preview(tiers)
        if tier_preview:
            parts.append(tier_preview)
        tier_names = [str(key).strip().lower() for key in list(tiers.keys())[:4] if str(key).strip()]
        if tier_names:
            pretty = ", ".join(localize_term_pl(item) for item in tier_names)
            parts.append(f"Poziomy: {pretty}")

    range_feet = getattr(event_cls, "range_feet", None)
    if isinstance(range_feet, int) and range_feet > 0:
        parts.append(f"Zasieg: {range_feet} ft")

    text = "\n".join(f"- {part}" for part in parts if part)
    if hint:
        return f"{hint}\n{text}".strip() if text else hint
    return text


def _generic_event_desc(event_name: str, event_cls: type | None) -> str:
    hint = _hint_for_event(event_name)
    doc_hint = _event_doc_hint(event_cls)
    base_hint = hint or doc_hint
    if event_cls is None:
        return base_hint
    parts: list[str] = []
    parts.append(_actions_cost_text_pl(getattr(event_cls, "actions_cost", 1)))

    range_feet = getattr(event_cls, "range_feet", None)
    if isinstance(range_feet, int) and range_feet > 0:
        parts.append(f"Zasieg: {range_feet} ft")

    damage_prompt = str(getattr(event_cls, "damage_prompt", "") or "").strip()
    if damage_prompt:
        parts.append(f"Obrazenia: {damage_prompt}")

    tags = _event_tags(event_cls)
    if "stance" in tags:
        parts.append("Typ: postawa (stance).")
    elif "attack_melee" in tags or "attack_ranged" in tags or "attack" in tags:
        parts.append("Typ: akcja ofensywna.")
    elif "defense" in tags or "parry" in tags:
        parts.append("Typ: akcja obronna.")
    elif "concentrate" in tags:
        parts.append("Typ: koncentracja.")

    text = "\n".join(f"- {part}" for part in parts if part)
    if base_hint:
        return f"{base_hint}\n{text}".strip() if text else base_hint
    return text


def _event_desc(event_name: str, event_cls: type | None) -> str:
    if event_cls is None:
        return _hint_for_event(event_name)
    module_name = _normalize(getattr(event_cls, "__module__", ""))
    default_tags = {
        str(tag).strip().lower().replace("-", "_").replace(" ", "_")
        for tag in list(getattr(event_cls, "default_tags", []) or [])
    }
    if ".magic." in module_name or bool({"magic", "spell", "cantrip", "focus"} & default_tags):
        return _magic_event_desc(event_name, event_cls)
    if ".bombs." in module_name or ".elixirs." in module_name or ".poisons." in module_name or "alchemical" in default_tags:
        return _alchemy_event_desc(event_name, event_cls)
    if ".attack." in module_name or "attack_melee" in default_tags or "attack_ranged" in default_tags:
        return _attack_event_desc(event_name, event_cls)
    return _generic_event_desc(event_name, event_cls)


def _companion_command_desc(actor: Any, event_cls: type | None) -> str:
    base = _event_desc("command_animal_companion", event_cls)
    companion_type = "towarzysz"
    support_note = ""
    strike_lines: list[str] = []
    if actor is not None:
        getter = getattr(actor, "get_status_data", None)
        if callable(getter):
            try:
                companion_type = str(getter("animal_companion", "animal_companion_type", "") or "").strip().lower() or companion_type
            except Exception:
                pass
        try:
            from GameObjects.companions import companion_type_data

            data = dict(companion_type_data(companion_type) or {})
            support_note = str(data.get("support_benefit", "") or "").strip()
            for attack in list(data.get("attacks", []) or []):
                label = str(attack.get("label", attack.get("id", "Atak")) or "Atak")
                damage = str(attack.get("damage", "1d6") or "1d6")
                damage_type = str(attack.get("damage_type", "normal") or "normal")
                strike_lines.append(f"{label}: {damage} ({damage_type}).")
        except Exception:
            pass
    extras = []
    if strike_lines:
        extras.append("Ataki towarzysza: " + " ".join(strike_lines))
    if support_note:
        extras.append(f"Support: {support_note}")
    if extras:
        return f"{base}\n- Towarzysz: {companion_type.title()}.\n- " + "\n- ".join(extras)
    return base


def _hunt_prey_desc(event_cls: type | None) -> str:
    base = _event_desc("hunt_prey", event_cls)
    extra = (
        "Oznaczenie nie odnawia się co turę. Trwa, dopóki nie wyznaczysz nowej ofiary "
        "albo bieżący cel nie przestanie być ważny."
    )
    return f"{base}\n- {extra}".strip()


def _hunted_shot_desc(event_cls: type | None) -> str:
    base = _event_desc("hunted_shot", event_cls)
    extra = "Wymaga wcześniej oznaczonej ofiary. Jeśli poprzedni cel zginął, najpierw użyj Wyznacz ofiarę."
    return f"{base}\n- {extra}".strip()


def _contextual_event_desc(event_name: str, event_cls: type | None, actor: Any | None) -> str:
    key = _normalize(event_name)
    if key == "command_animal_companion":
        return _companion_command_desc(actor, event_cls)
    if key == "hunt_prey":
        return _hunt_prey_desc(event_cls)
    if key == "hunted_shot":
        return _hunted_shot_desc(event_cls)
    return _event_desc(event_name, event_cls)


def _actor_has_status(actor: Any, status_id: str) -> bool:
    if actor is None:
        return False
    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            return bool(checker(status_id))
        except Exception:
            pass
    needle = _normalize(status_id)
    for status in list(getattr(actor, "statuses", []) or []):
        sid = _normalize(getattr(status, "id", status))
        if sid == needle:
            return True
    return False


def _actor_identity_tags(actor: Any) -> set[str]:
    tags: set[str] = set()
    if actor is None:
        return tags

    class_name = _normalize(getattr(actor, "class_name", ""))
    if class_name:
        tags.add(class_name)
    ancestry = _normalize(getattr(actor, "ancestry", ""))
    if ancestry:
        tags.add(ancestry)
    ancestry_id = _normalize(getattr(actor, "ancestry_id", ""))
    if ancestry_id:
        tags.add(ancestry_id)
    race = _normalize(getattr(actor, "race", ""))
    if race:
        tags.add(race)

    for status in list(getattr(actor, "statuses", []) or []):
        sid = _normalize(getattr(status, "id", status))
        if sid:
            tags.add(sid)
    return tags


def _actor_status_data(actor: Any, status_id: str) -> dict[str, Any]:
    if actor is None:
        return {}
    getter = getattr(actor, "get_status_data", None)
    if callable(getter):
        try:
            data = getter(status_id, None, None)
        except TypeError:
            try:
                data = getter(status_id)
            except Exception:
                data = None
        except Exception:
            data = None
        if isinstance(data, dict):
            return dict(data)
    needle = _normalize(status_id)
    for status in list(getattr(actor, "statuses", []) or []):
        sid = _normalize(getattr(status, "id", status))
        if sid != needle:
            continue
        payload = getattr(status, "data", None)
        if isinstance(payload, dict):
            return dict(payload)
    return {}


def _event_tags(event_cls: type | None) -> set[str]:
    if event_cls is None:
        return set()
    tags: set[str] = set()
    for tag in list(getattr(event_cls, "default_tags", []) or []):
        normalized = _normalize(str(tag or "")).replace("-", "_").replace(" ", "_")
        if normalized:
            tags.add(normalized)
    return tags


def _iter_equipped_weapons(actor: Any) -> list[Any]:
    if actor is None:
        return []
    try:
        from GameObjects.items.inventory import get_equipped_weapons

        return list(get_equipped_weapons(actor) or [])
    except Exception:
        return []


def _board_has_detected_armed_trap(game: Any | None) -> bool:
    if game is None:
        return False
    board = getattr(game, "board", None)
    if board is None:
        return False
    try:
        rows = int(getattr(board, "rows", 0) or 0)
        cols = int(getattr(board, "cols", 0) or 0)
    except Exception:
        return False
    if rows <= 0 or cols <= 0:
        return False
    for row in range(rows):
        for col in range(cols):
            pos = (col, row)
            try:
                interactables = list(board.interactables_at(pos))
            except Exception:
                continue
            for obj in interactables:
                if not (
                    hasattr(obj, "trap_armed")
                    and callable(getattr(obj, "detect_trap", None))
                    and callable(getattr(obj, "disable_trap", None))
                ):
                    continue
                if not bool(getattr(obj, "trap_armed", False)):
                    continue
                if not bool(getattr(obj, "trap_detected", False)):
                    continue
                return True
    return False


def _weapon_traits(weapon: Any) -> set[str]:
    traits: set[str] = set()
    for raw in list(getattr(weapon, "traits", ()) or ()):
        text = str(raw or "").strip().lower().replace("-", "_")
        if not text:
            continue
        core = text.split(":", 1)[0]
        if core:
            traits.add(core)
    return traits


def _weapon_hands(weapon: Any) -> int:
    try:
        return max(0, int(getattr(weapon, "hands_required", 1) or 1))
    except Exception:
        return 1


def _weapon_is_ranged(weapon: Any) -> bool:
    return bool(getattr(weapon, "ranged", False))


def _weapon_reload(weapon: Any) -> int:
    try:
        return max(0, int(getattr(weapon, "reload", 0) or 0))
    except Exception:
        return 0


def _equipped_ranged_weapons(actor: Any, *, reload_zero_only: bool = False) -> list[Any]:
    items = [weapon for weapon in _iter_equipped_weapons(actor) if _weapon_is_ranged(weapon)]
    if reload_zero_only:
        return [weapon for weapon in items if _weapon_reload(weapon) <= 0]
    return items


def _equipped_melee_weapons(actor: Any) -> list[Any]:
    return [weapon for weapon in _iter_equipped_weapons(actor) if not _weapon_is_ranged(weapon)]


def _equipped_melee_one_h_weapons(actor: Any) -> list[Any]:
    return [weapon for weapon in _equipped_melee_weapons(actor) if _weapon_hands(weapon) == 1]


def _actor_free_hands(actor: Any) -> int:
    hands_used = 0
    for weapon in _iter_equipped_weapons(actor):
        hands_used += min(2, _weapon_hands(weapon))
    try:
        from GameObjects.items.shield import get_equipped_shield

        if get_equipped_shield(actor, create_default=False) is not None:
            hands_used += 1
    except Exception:
        pass
    return max(0, 2 - hands_used)


def _actor_has_hunted_prey(actor: Any) -> bool:
    if actor is None:
        return False
    for attr in ("ranger_hunted_prey_target_id", "hunted_prey_target_id"):
        raw = str(getattr(actor, attr, "") or "").strip()
        if raw:
            return True
    ranger_data = _actor_status_data(actor, "ranger")
    setup = ranger_data.get("ranger_setup")
    if isinstance(setup, dict):
        raw = str(setup.get("hunted_prey_target_id", "") or "").strip()
        if raw:
            return True
    return False


def _actor_attacks_this_turn(actor: Any, *, game: Any | None, in_combat: bool) -> int:
    if actor is None or not in_combat or game is None:
        return 0
    state = getattr(game, "state", None)
    attack_state = getattr(state, "attack_state", None)
    if not isinstance(attack_state, dict):
        return 0
    entry = attack_state.get(actor)
    if not isinstance(entry, dict):
        actor_id = str(getattr(actor, "object_id", "") or "")
        for key, payload in attack_state.items():
            if not isinstance(payload, dict):
                continue
            if key is actor:
                entry = payload
                break
            if actor_id and str(getattr(key, "object_id", "") or "") == actor_id:
                entry = payload
                break
    if not isinstance(entry, dict):
        return 0
    try:
        return max(0, int(entry.get("attacks_this_turn", 0) or 0))
    except Exception:
        return 0


def _actor_scenario_key(actor: Any) -> str:
    raw_id = str(getattr(actor, "object_id", "") or "").strip()
    if raw_id:
        return f"actor:{raw_id}"
    raw_name = str(getattr(actor, "name", "") or "").strip()
    if raw_name:
        return f"name:{raw_name.lower()}"
    return f"pyid:{id(actor)}"


def _wizard_spell_substitution_used(game: Any | None, actor: Any) -> bool:
    if game is None or actor is None:
        return False
    usage = getattr(game, "_wizard_spell_substitution_used", None)
    if not isinstance(usage, set):
        return False
    return _actor_scenario_key(actor) in usage


def _event_runtime_available(
    event_name: str,
    event_cls: type | None,
    *,
    actor: Any,
    game: Any | None,
    in_combat: bool,
) -> bool:
    key = _normalize(event_name)
    if not key:
        return True

    # Statyczne wymagania po statusie (featy/class features).
    if key in _STATUS_GATED_ACTIONS and not _actor_has_status(actor, key):
        return False

    required_class = _normalize(_CLASS_GATED_ACTIONS.get(key))
    if required_class and not _actor_has_status(actor, required_class):
        actor_class = _normalize(getattr(actor, "class_name", ""))
        if actor_class != required_class:
            return False

    required_feat = _normalize(getattr(event_cls, "required_feat_status", ""))
    if required_feat and not _actor_has_status(actor, required_feat):
        return False

    required_inventory_event = _normalize(getattr(event_cls, "required_inventory_event_name", ""))
    if required_inventory_event:
        try:
            from GameObjects.items.inventory import has_ready_event_item

            if not bool(has_ready_event_item(actor, required_inventory_event)):
                return False
        except Exception:
            return False

    if key in {"shield", "raise_shield"}:
        try:
            from GameObjects.items.shield import get_equipped_shield

            if get_equipped_shield(actor, create_default=False) is None:
                return False
        except Exception:
            return False

    if key == "parry":
        melee = _equipped_melee_weapons(actor)
        if not any("parry" in _weapon_traits(weapon) for weapon in melee):
            return False
    if key == "refocus":
        current_focus, max_focus = _focus_pool_state(actor)
        if max_focus <= 0:
            return False
        if current_focus >= max_focus:
            return False

    if key in {"point_blank_shot"} and not _equipped_ranged_weapons(actor):
        return False
    if key in {"power_attack", "sudden_charge"} and not _equipped_melee_weapons(actor):
        return False
    if key == "snagging_strike":
        if not _equipped_melee_weapons(actor):
            return False
        if _actor_free_hands(actor) < 1:
            return False
    if key in {"double_slice", "twin_feint", "twin_takedown"} and len(_equipped_melee_one_h_weapons(actor)) < 2:
        return False

    if key in {"hunted_shot", "twin_takedown"}:
        if not _actor_has_hunted_prey(actor):
            return False
    if key == "hunted_shot" and not _equipped_ranged_weapons(actor, reload_zero_only=True):
        return False

    if key == "moment_of_clarity":
        if not _actor_has_status(actor, "rage"):
            return False
        if not _actor_has_status(actor, "moment_of_clarity"):
            return False

    if key in {"drain_bonded_item", "drain_familiar"}:
        wizard_setup = _actor_status_data(actor, "wizard").get("wizard_setup")
        if isinstance(wizard_setup, dict):
            configured = _normalize(wizard_setup.get("drain_action"))
            if configured and configured != key:
                return False
    if key == "wizard_spell_substitution":
        wizard_setup = _actor_status_data(actor, "wizard").get("wizard_setup")
        thesis = ""
        if isinstance(wizard_setup, dict):
            thesis = _normalize(wizard_setup.get("thesis"))
        if not thesis:
            thesis = _normalize(getattr(actor, "wizard_thesis", ""))
        if thesis != "spell_substitution":
            return False
        if _wizard_spell_substitution_used(game, actor):
            return False
    if key == "retrain_sorcerer_spell":
        try:
            from GameObjects.events.sorcerer_runtime_events import has_retrainable_sorcerer_spell

            if not has_retrainable_sorcerer_spell(actor, game=game):
                return False
        except Exception:
            return False

    if key in {"identify_trap", "disable_device"}:
        if not _board_has_detected_armed_trap(game):
            return False

    if key == "exacting_strike" and _actor_attacks_this_turn(actor, game=game, in_combat=in_combat) < 1:
        return False

    required_focus = _normalize(getattr(event_cls, "required_focus_spell_id", ""))
    if required_focus:
        spell_state = dict(getattr(actor, "spell_state", {}) or {})
        known_focus = {
            _normalize_spell_id(item)
            for item in list((spell_state.get("known", {}) or {}).get("focus", []) or [])
            if _normalize_spell_id(item)
        }
        if known_focus and required_focus not in known_focus:
            return False

    return True


def _is_internal_attack_event(name: str, event_cls: type | None) -> bool:
    if event_cls is None:
        return False
    key = _normalize(name)
    if key in {"attack"}:
        return False
    module = _normalize(getattr(event_cls, "__module__", ""))
    return ".events.attack." in module


def _is_alchemy_item_event(event_cls: type | None) -> bool:
    if event_cls is None:
        return False
    try:
        from GameObjects.events.bombs.base_alchemical_bomb_event import BaseAlchemicalBombEvent
        from GameObjects.events.elixirs.base_elixir_event import BaseElixirEvent
        from GameObjects.events.poisons.base_poison_event import BasePoisonEvent

        return bool(issubclass(event_cls, (BaseAlchemicalBombEvent, BaseElixirEvent, BasePoisonEvent)))
    except Exception:
        return False


def _collect_magic_tags(event_cls: type | None) -> set[str]:
    if event_cls is None:
        return set()
    tags: set[str] = set()
    for tag in list(getattr(event_cls, "default_tags", []) or []):
        normalized = _normalize(str(tag or "")).replace("-", "_").replace(" ", "_")
        if normalized:
            tags.add(normalized)
    for tag in list(getattr(event_cls, "spell_tags", []) or []):
        normalized = _normalize(str(tag or "")).replace("-", "_").replace(" ", "_")
        if normalized:
            tags.add(normalized)
    return tags


def _is_spell_known_for_tier(
    *,
    spell_id: str,
    tier: str | None,
    known_by_tier: dict[str, set[str]],
    known_innate: set[str],
    actor_class: str | None = None,
    sorcerer_signature_spells: set[str] | None = None,
) -> bool:
    if spell_id in known_innate:
        return True
    if not tier:
        return True
    tier_known = set(known_by_tier.get(tier, set()) or set())
    if spell_id in tier_known:
        return True

    class_name = _normalize(actor_class)
    signature_set = {
        _normalize_spell_id(item)
        for item in set(sorcerer_signature_spells or set())
        if _normalize_spell_id(item)
    }
    if class_name == "sorcerer" and tier.startswith("rank_") and spell_id in signature_set:
        for rank_tier in ("rank_1", "rank_2", "rank_3", "rank_4", "rank_5", "rank_6", "rank_7", "rank_8", "rank_9", "rank_10"):
            if spell_id in set(known_by_tier.get(rank_tier, set()) or set()):
                return True
    return False


def filter_magic_events_for_actor(
    available_events: dict[str, type],
    *,
    actor: Any,
    game: Any | None = None,
) -> dict[str, type]:
    if not isinstance(available_events, dict) or not available_events:
        return {}
    if actor is None:
        return dict(available_events)

    try:
        from spell_management import (
            can_cast_managed_spell,
            classify_spell_tier,
            ensure_actor_spell_state,
            _wizard_staff_nexus_options,
        )
    except Exception:
        return dict(available_events)

    try:
        state = ensure_actor_spell_state(actor, game=game, enforce=True)
    except Exception:
        state = dict(getattr(actor, "spell_state", {}) or {})

    known = dict(state.get("known", {}) or {})
    actor_class = _normalize(state.get("class_name") or getattr(actor, "class_name", ""))
    known_innate = {_normalize_spell_id(item) for item in list(known.get("innate", []) or []) if _normalize_spell_id(item)}
    sorcerer_signature_spells = {
        _normalize_spell_id(item)
        for item in list(state.get("sorcerer_signature_spells", []) or [])
        if _normalize_spell_id(item)
    }
    known_by_tier: dict[str, set[str]] = {}
    for tier in ("cantrip", "focus", "rank_1", "rank_2", "rank_3", "rank_4", "rank_5", "rank_6", "rank_7", "rank_8", "rank_9", "rank_10"):
        known_by_tier[tier] = {_normalize_spell_id(item) for item in list(known.get(tier, []) or []) if _normalize_spell_id(item)}

    filtered: dict[str, type] = {}
    for event_name, event_cls in available_events.items():
        if classify_event_bucket(event_name, event_cls) != "magic":
            filtered[event_name] = event_cls
            continue

        normalized_event_id = _normalize_spell_id(event_name)
        tags = _collect_magic_tags(event_cls)
        tier = classify_spell_tier(list(tags))

        # Dla faktycznych czarów pokazuj tylko znane + aktualnie możliwe do rzucenia.
        if tier is not None:
            if not _is_spell_known_for_tier(
                spell_id=normalized_event_id,
                tier=tier,
                known_by_tier=known_by_tier,
                known_innate=known_innate,
                actor_class=actor_class,
                sorcerer_signature_spells=sorcerer_signature_spells,
            ):
                continue
            can_cast, _reason = can_cast_managed_spell(actor, spell_id=event_name, tier=tier)
            staff_available = bool(_wizard_staff_nexus_options(actor, spell_id=event_name, tier=tier).get("available"))
            if not can_cast and not staff_available:
                continue
            filtered[event_name] = event_cls
            continue

        # Metamagia i akcje pomocnicze w bucket "magic".
        if normalized_event_id in {"reach_spell", "widen_spell", "lingering_composition"} and not _actor_has_status(actor, normalized_event_id):
            continue
        if normalized_event_id == "domain_focus_spell":
            if not known_by_tier.get("focus"):
                continue
            try:
                if int(getattr(actor, "focus_point", 0) or 0) <= 0:
                    continue
            except Exception:
                pass

        filtered[event_name] = event_cls

    return filtered


def filter_alchemy_events_for_actor(
    available_events: dict[str, type],
    *,
    actor: Any,
) -> dict[str, type]:
    if not isinstance(available_events, dict) or not available_events:
        return {}
    if actor is None:
        return dict(available_events)

    try:
        from GameObjects.items.inventory import has_ready_alchemical_item
    except Exception:
        has_ready_alchemical_item = None

    filtered: dict[str, type] = {}
    for event_name, event_cls in available_events.items():
        if classify_event_bucket(event_name, event_cls) != "alchemy":
            filtered[event_name] = event_cls
            continue

        key = _normalize(event_name)

        if key == "quick_alchemy":
            if not _actor_has_status(actor, "quick_alchemy_allow"):
                continue
            filtered[event_name] = event_cls
            continue

        if key == "mutagenic_flashback":
            field_data = _actor_status_data(actor, "alchemist_research_field")
            if str(field_data.get("research_field", "") or "").strip().lower() != "mutagenist":
                continue
            if bool(field_data.get("mutagenic_flashback_used", False)):
                continue
            consumed = list(field_data.get("mutagen_consumed", []) or [])
            if not consumed:
                continue
            filtered[event_name] = event_cls
            continue

        if _is_alchemy_item_event(event_cls) and callable(has_ready_alchemical_item):
            try:
                if not bool(has_ready_alchemical_item(actor, key)):
                    continue
            except Exception:
                pass

        filtered[event_name] = event_cls

    return filtered


def filter_player_events(available_events: dict[str, type], *, actor_is_hero: bool = True) -> dict[str, type]:
    filtered: dict[str, type] = {}
    for name, cls in available_events.items():
        key = _normalize(name)
        module = _normalize(getattr(cls, "__module__", ""))
        tags = _event_tags(cls)
        if key in {"cancel", "skill_check"}:
            continue
        if actor_is_hero and (key.startswith("enemy_") or key.startswith("phase_")):
            continue
        if actor_is_hero and ("enemy" in tags or ".events.enemy" in module):
            continue
        if actor_is_hero and _is_internal_attack_event(key, cls):
            # Eventy szczegółowe ataku bronią są wywoływane przez główną akcję "attack".
            continue
        filtered[key] = cls
    return filtered


def filter_events_for_actor(
    available_events: dict[str, type],
    *,
    actor: Any,
    in_combat: bool,
    game: Any | None = None,
) -> dict[str, type]:
    if not isinstance(available_events, dict) or not available_events:
        return {}
    if actor is None:
        return dict(available_events)

    identity = _actor_identity_tags(actor)
    filtered: dict[str, type] = {}
    for name, cls in available_events.items():
        key = _normalize(name)
        tags = _event_tags(cls)

        # Akcje silnie zależne od stanu bohatera.
        if key == "command_animal_companion" and not _actor_has_status(actor, "animal_companion"):
            continue
        if key == "commandfamilair" and not (
            _actor_has_status(actor, "familiarowner") or _actor_has_status(actor, "alchemist_familiar_guidance")
        ):
            continue
        if key == "rage" and _actor_has_status(actor, "rage"):
            continue
        if key == "lay_on_hands":
            try:
                if int(getattr(actor, "focus_point", 0) or 0) <= 0:
                    continue
            except Exception:
                pass

        # Klasowe akcje pokazujemy wyłącznie właściwej klasie/postaci.
        class_tags = tags & _CLASS_TAGS
        if class_tags and not bool(class_tags & identity):
            continue

        # Rasowe akcje pokazujemy tylko właściwej ancestrii.
        ancestry_tags = tags & _ANCESTRY_TAGS
        if ancestry_tags and not bool(ancestry_tags & identity):
            continue

        stance_required = _normalize(getattr(cls, "stance_required_status", ""))
        if stance_required and not _actor_has_status(actor, stance_required):
            continue

        if in_combat and not bool(getattr(cls, "available_in_combat", True)):
            continue
        if (not in_combat) and not bool(getattr(cls, "available_in_exploration", True)):
            continue
        if not _event_runtime_available(
            key,
            cls,
            actor=actor,
            game=game,
            in_combat=in_combat,
        ):
            continue

        filtered[key] = cls
    return filtered


def classify_event_bucket(name: str, event_cls: type) -> str:
    key = _normalize(name)
    module = _normalize(getattr(event_cls, "__module__", ""))
    tags = [str(tag).strip().lower() for tag in list(getattr(event_cls, "default_tags", []) or [])]

    if key in {"move", "interaction", "seek", "stealth", "equip", "delay", "end"}:
        return "direct"
    if key == "attack":
        return "attack"
    if (
        key in {"quick_alchemy", "mutagenic_flashback"}
        or ".bombs." in module
        or ".elixirs." in module
        or ".poisons." in module
        or "alchemical" in tags
    ):
        return "alchemy"
    if ".magic." in module or "magic" in tags or "spell" in tags:
        return "magic"
    if ".attack." in module:
        return "attack"
    if "attack" in tags or "ranged_attack" in tags:
        # Manewry i featy ataku traktujemy jako akcje specjalne,
        # a bazowy strike pozostaje pod "Atak".
        return "special"
    return "special"


def _classify_special_action_source(
    name: str,
    event_cls: type | None,
    *,
    actor: Any | None = None,
) -> str:
    key = _normalize(name)
    if not key:
        return "generic"
    if key in _SPECIAL_SOURCE_HERITAGE_OVERRIDES:
        return "heritage"
    if key in _SPECIAL_SOURCE_CLASS_OVERRIDES:
        return "class"

    tags = _event_tags(event_cls)
    if "ancestry" in tags or "heritage" in tags or bool(tags & _ANCESTRY_TAGS):
        return "heritage"
    if bool(tags & _CLASS_TAGS):
        return "class"

    if key in _STATUS_GATED_ACTIONS or key in _CLASS_GATED_ACTIONS:
        if key not in _SPECIAL_SOURCE_HERITAGE_OVERRIDES:
            return "class"

    if actor is not None and key in {"command_animal_companion", "commandfamilair"}:
        if bool(_actor_identity_tags(actor) & _CLASS_TAGS):
            return "class"

    return "generic"


def group_events(available_events: dict[str, type], *, actor: Any | None = None) -> dict[str, Any]:
    grouped: dict[str, Any] = {
        "direct": {},
        "attack": [],
        "magic": [],
        "alchemy": [],
        "special": [],
        "special_by_source": {
            "generic": [],
            "heritage": [],
            "class": [],
        },
    }
    for name, cls in available_events.items():
        bucket = classify_event_bucket(name, cls)
        if bucket == "direct":
            grouped["direct"][name] = cls
        else:
            grouped[bucket].append(name)
            if bucket == "special":
                source = _classify_special_action_source(name, cls, actor=actor)
                grouped["special_by_source"].setdefault(source, []).append(name)

    for bucket in ("attack", "magic", "alchemy", "special"):
        grouped[bucket] = sorted(set(grouped[bucket]))
    for bucket in ("generic", "heritage", "class"):
        grouped["special_by_source"][bucket] = sorted(set(grouped["special_by_source"].get(bucket, [])))
    return grouped


def build_intent_options(
    grouped: dict[str, Any],
    *,
    in_combat: bool,
    actor: Any | None = None,
    available_events: dict[str, type] | None = None,
) -> list[dict[str, str]]:
    direct = grouped.get("direct", {}) or {}
    event_lookup = dict(available_events or {})
    special_by_source = dict(grouped.get("special_by_source", {}) or {})
    options: list[dict[str, str]] = []
    intent_copy = render_prompt_copy("turns.intent_options")

    def _push(intent_id: str, label: str, desc: str, *, category: str = "general", icon: str = "") -> None:
        override = {}
        if isinstance(intent_copy.get("options"), dict):
            override = intent_copy.get("options", {}).get(intent_id) or intent_copy.get("options", {}).get(str(intent_id).lower()) or {}
        options.append({"id": intent_id, "label": label, "desc": desc, "category": category, "icon": icon})
        if isinstance(override, dict):
            current = options[-1]
            for field in ("label", "desc", "category", "icon"):
                value = override.get(field)
                if value not in (None, ""):
                    current[field] = value

    if "move" in direct:
        _push("move", "Ruch", "Ruch po planszy.", category="movement", icon="→")
    if "interaction" in direct:
        _push("interact", "Interakcja", "Interakcja z obiektem na planszy.", category="movement", icon="⊕")
    if "seek" in direct:
        _push(
            "seek",
            "Szukaj",
            "Przeszukaj obszar do 30 ft gridowo; UI podswietla pola objete akcja i nie przechodzi przez sciany.",
            category="movement",
            icon="◎",
        )
    if "stealth" in direct:
        if _actor_has_status(actor, "stealth"):
            _push(
                "stealth",
                "Poruszaj sie skrycie",
                "Ruch skradaniem (Sneak): do polowy Speed; Very Sneaky moze dodac +5 ft.",
                category="movement",
                icon="◈",
            )
        else:
            _push(
                "stealth",
                "Skradanie",
                "Wejdz w ukrycie i poruszaj sie skrycie.",
                category="movement",
                icon="◈",
            )
    if grouped.get("attack"):
        _push("attack", "Atak", "Wybierz akcję ataku.", category="combat", icon="⚔")
    if grouped.get("magic"):
        _push("magic", "Magia", "Wybierz czar lub akcję magiczną.", category="combat", icon="✦")
    if grouped.get("alchemy"):
        _push("alchemy", "Alchemia", "Wybierz akcję alchemiczną.", category="combat", icon="⚗")
    for source, category, icon in (
        ("generic", "generic", "◇"),
        ("heritage", "heritage", "⬟"),
        ("class", "class", "★"),
    ):
        for event_name in list(special_by_source.get(source, []) or []):
            cls = event_lookup.get(event_name)
            _push(
                event_name,
                _labelize(event_name),
                _contextual_event_desc(event_name, cls, actor),
                category=category,
                icon=icon,
            )
    if "equip" in direct:
        _push("equipment", "Ekwipunek", "Ekwipunek i interakcje z przedmiotami.", category="utility", icon="◆")
    _push("stats", "Statystyki", "Pełne statystyki aktywnego bohatera.", category="utility", icon="◈")
    if in_combat and "delay" in direct:
        _push("delay", "Opóźnij", "Opóźnij turę.", category="turn", icon="◧")
    if "end" in direct:
        _push("end", "Koniec", "Zakończ turę.", category="turn", icon="■")

    return options


def _prompt_with_ui(
    game,
    *,
    title: str,
    subtitle: str,
    source: str,
    options: list[dict[str, str]],
    prompt_id: str | None = None,
) -> str | None:
    title, subtitle, options = merge_menu_prompt(
        prompt_id,
        title=title,
        subtitle=subtitle,
        options=options,
        source=source,
    )
    ui = getattr(game, "ui", None)
    choice_meta = []
    for idx, option in enumerate(options, start=1):
        choice_meta.append(
            {
                "raw": option["id"],
                "label": option["label"],
                "desc": option["desc"],
                "key": str(idx),
                "category": option.get("category", "general"),
                "icon": option.get("icon", ""),
            }
        )
    player_prompt = getattr(game, "player_prompt", None)
    if player_prompt is not None:
        try:
            answer = player_prompt.choice(
                title,
                choices=[entry["raw"] for entry in choice_meta],
                source=source,
                subtitle=_with_numpad_hint(subtitle),
                choice_meta=choice_meta,
                scope_key="hero_turn:intent",
                dedupe_key=f"intent_menu:{source}",
                layout="dialog",
                prompt_id=prompt_id,
            )
            raw = str(answer or "").strip()
            if raw:
                return raw
        except Exception:
            pass
    if not (ui and hasattr(ui, "prompt_choice")):
        return None
    answer = ui.prompt_choice(
        title,
        choices=[entry["label"] for entry in choice_meta],
        source=source,
        layout="dialog",
        choice_meta=choice_meta,
        title=title,
        subtitle=_with_numpad_hint(subtitle),
        prompt_id=prompt_id,
    )
    raw = str(answer or "").strip()
    if not raw:
        return None
    return raw


def choose_option(
    game,
    *,
    title: str,
    subtitle: str,
    source: str,
    options: list[dict[str, str]],
    prompt_id: str | None = None,
) -> str | None:
    if not options:
        return None

    title, subtitle, options = merge_menu_prompt(
        prompt_id,
        title=title,
        subtitle=subtitle,
        options=options,
        source=source,
    )

    by_id = {str(option["id"]).strip().lower(): str(option["id"]).strip().lower() for option in options}
    by_label = {str(option["label"]).strip().lower(): str(option["id"]).strip().lower() for option in options}

    def _decode(raw: str | None) -> str | None:
        text = str(raw or "").strip()
        if not text:
            return None
        low = text.lower()
        if low in by_id:
            return by_id[low]
        if low in by_label:
            return by_label[low]
        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(options):
                return str(options[idx]["id"]).strip().lower()
        return None

    ui_raw = _prompt_with_ui(
        game,
        title=title,
        subtitle=subtitle,
        source=source,
        options=options,
        prompt_id=prompt_id,
    )
    picked = _decode(ui_raw)
    if picked:
        return picked
    return None


def choose_event_from_bucket(
    game,
    *,
    bucket_id: str,
    available_events: dict[str, type],
    event_names: list[str],
    source: str,
) -> str | None:
    if not event_names:
        return None

    prompt_id = ""
    if bucket_id == "attack":
        title = "Atak"
        subtitle = "Wybierz rodzaj ataku."
        prompt_id = "turns.bucket.attack"
    elif bucket_id == "magic":
        title = "Magia"
        subtitle = "Wybierz czar lub akcję magiczną."
        prompt_id = "turns.bucket.magic"
    elif bucket_id == "alchemy":
        title = "Alchemia"
        subtitle = "Wybierz akcję alchemiczną."
        prompt_id = "turns.bucket.alchemy"
    else:
        title = "Specjalne"
        subtitle = "Wybierz akcję specjalną."
        prompt_id = "turns.bucket.special"

    options: list[dict[str, str]] = []
    for event_name in event_names:
        cls = available_events.get(event_name)
        options.append(
            {
                "id": event_name,
                "label": _labelize(event_name),
                "desc": _event_desc(event_name, cls),
            }
        )

    return choose_option(
        game,
        title=title,
        subtitle=subtitle,
        source=source,
        options=options,
        prompt_id=prompt_id,
    )


def render_actor_stats(actor: Any, *, combat_state: Any | None = None) -> str:
    def _safe_int(value: object, default: int = 0) -> int:
        try:
            return int(value)
        except Exception:
            return int(default)

    def _rank_step(rank: object) -> int:
        raw = str(rank or "").strip().lower()
        return {
            "untrained": 0,
            "trained": 2,
            "expert": 4,
            "master": 6,
            "legendary": 8,
        }.get(raw, 0)

    lines: list[str] = []
    actor_id = getattr(actor, "object_id", None) or getattr(actor, "name", "actor")
    level = _safe_int(getattr(actor, "level", 1), 1)
    lines.append(f"ID: {actor_id}")
    lines.append(f"Nazwa: {getattr(actor, 'name', actor_id)}")
    lines.append(f"Klasa: {localize_term_pl(getattr(actor, 'class_name', '-'))}")
    lines.append(f"Poziom: {level}")
    lines.append(f"Pozycja: {getattr(actor, 'position', '-')}")
    lines.append(f"Inicjatywa: {getattr(actor, 'initiative', '-')}")
    lines.append(f"HP maks.: {getattr(actor, 'max_hp', '-')}")
    lines.append(f"Rany: {getattr(actor, 'wounds', '-')}")
    lines.append(f"Tymczasowe HP: {getattr(actor, 'temp_hp', '-')}")
    current_focus, max_focus = _focus_pool_state(actor)
    if max_focus > 0:
        lines.append(f"Punkty Focus: {current_focus}/{max_focus}")
    else:
        lines.append("Punkty Focus: -")
    try:
        from economy import actor_bulk_summary, ensure_actor_coin_pouch, format_actor_money

        ensure_actor_coin_pouch(actor, default_gp=int(getattr(actor, "starting_gold_gp", 0) or 0))
        bulk = actor_bulk_summary(actor)
        lines.append(f"Sakiewka: {format_actor_money(actor)}")
        lines.append(
            "Bulk: "
            f"{bulk['total_display']} / {bulk['encumbered_limit_display']} (encumbered), "
            f"max {bulk['max_limit_display']}"
        )
    except Exception:
        pass
    if combat_state is not None:
        try:
            used = int(getattr(combat_state, "actions_used", {}).get(actor, 0))
        except Exception:
            used = 0
        try:
            limit = int(getattr(combat_state, "_action_limit")(actor))
        except Exception:
            limit = 3
        lines.append(f"Akcje (tura): {used}/{limit}")

    ability_mods = dict(getattr(actor, "ability_modifiers", {}) or {})
    skill_mods = dict(getattr(actor, "skill_modifiers", {}) or {})
    if ability_mods:
        lines.append("")
        lines.append("Atrybuty (mod.):")
        for key in ("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"):
            if key not in ability_mods:
                continue
            short = {
                "strength": "STR",
                "dexterity": "DEX",
                "constitution": "CON",
                "intelligence": "INT",
                "wisdom": "WIS",
                "charisma": "CHA",
            }.get(key, key.upper())
            mod = _safe_int(ability_mods.get(key), 0)
            lines.append(f"- {short}: {mod:+d}")

    try:
        from character_creation.mechanics import SKILL_TO_ABILITY
    except Exception:
        SKILL_TO_ABILITY = {
            "acrobatics": "dexterity",
            "arcana": "intelligence",
            "athletics": "strength",
            "crafting": "intelligence",
            "deception": "charisma",
            "diplomacy": "charisma",
            "intimidation": "charisma",
            "medicine": "wisdom",
            "nature": "wisdom",
            "occultism": "intelligence",
            "performance": "charisma",
            "religion": "wisdom",
            "society": "intelligence",
            "stealth": "dexterity",
            "survival": "wisdom",
            "thievery": "dexterity",
        }
    skill_order = (
        "acrobatics",
        "arcana",
        "athletics",
        "crafting",
        "deception",
        "diplomacy",
        "intimidation",
        "medicine",
        "nature",
        "occultism",
        "performance",
        "religion",
        "society",
        "stealth",
        "survival",
        "thievery",
    )
    skill_ranks = dict(getattr(actor, "skill_ranks", {}) or {})
    trained_skills = {
        str(item or "").strip().lower()
        for item in list(getattr(actor, "trained_skills", []) or [])
        if str(item or "").strip()
    }
    if not trained_skills and not skill_ranks:
        for skill_id in skill_order:
            if bool(getattr(actor, f"{skill_id}_trained", False)):
                trained_skills.add(skill_id)
    explicit_skills = {
        str(item or "").strip().lower()
        for item in skill_ranks.keys()
        if str(item or "").strip()
    }
    if not explicit_skills and skill_mods:
        explicit_skills = {
            str(item or "").strip().lower()
            for item in skill_mods.keys()
            if str(item or "").strip().lower() in skill_order
        }
    skill_ids = [item for item in skill_order if item in (explicit_skills | trained_skills)]
    lines.append("")
    lines.append("Biegłości skilli:")
    listed_skills = 0
    for skill_id in skill_ids:
        rank = str(skill_ranks.get(skill_id, "trained" if skill_id in trained_skills else "untrained") or "untrained").strip().lower()
        if rank == "untrained":
            continue
        prof = level + _rank_step(rank)
        ability_key = str(SKILL_TO_ABILITY.get(skill_id, "intelligence") or "intelligence").strip().lower()
        ability_mod = _safe_int(ability_mods.get(ability_key, 0), 0)
        total = _safe_int(skill_mods.get(skill_id), prof + ability_mod)
        listed_skills += 1
        lines.append(
            f"- {localize_term_pl(skill_id)}: {total:+d} "
            f"(biegłość {localize_term_pl(rank)} {prof:+d}, {localize_term_pl(ability_key)} {ability_mod:+d})"
        )
    if listed_skills == 0:
        lines.append("- Brak wytrenowanych skilli (wszystko untrained).")

    save_ranks = dict(getattr(actor, "save_ranks", {}) or {})
    if save_ranks:
        lines.append("")
        lines.append("Rzuty obronne:")
        save_rows = [
            ("fortitude", "Fortitude", "constitution", "con_mod", "fortitude_bonus"),
            ("reflex", "Reflex", "dexterity", "dex_mod", "reflex_bonus"),
            ("will", "Will", "wisdom", "wis_mod", "will_bonus"),
        ]
        for save_id, label, ability_key, ability_attr, total_attr in save_rows:
            rank = str(save_ranks.get(save_id, "untrained") or "untrained").strip().lower()
            prof = 0 if rank == "untrained" else level + _rank_step(rank)
            ability_mod = _safe_int(getattr(actor, ability_attr, ability_mods.get(ability_key, 0)), 0)
            total = _safe_int(getattr(actor, total_attr, prof + ability_mod), prof + ability_mod)
            lines.append(
                f"- {label}: {total:+d} "
                f"(biegłość {localize_term_pl(rank)} {prof:+d}, {localize_term_pl(ability_key)} {ability_mod:+d})"
            )

    statuses = list(getattr(actor, "statuses", []) or [])
    if statuses:
        lines.append("")
        lines.append("Statusy:")
        for status in statuses:
            sid = getattr(status, "id", status)
            duration = getattr(status, "duration", None)
            if duration is None:
                lines.append(f"- {localize_term_pl(sid)}")
            else:
                lines.append(f"- {localize_term_pl(sid)} (czas={duration})")
    else:
        lines.append("")
        lines.append("Statusy: brak")

    try:
        from GameObjects.items.inventory import all_inventory_sections, hand_slots_snapshot, item_label

        lines.append("")
        lines.append("Ekwipunek:")
        sections = list(all_inventory_sections(actor))
        if not sections:
            lines.append("- brak")
        else:
            for category, items in sections:
                labels = ", ".join(item_label(item) for item in items) or "-"
                lines.append(f"- {localize_term_pl(category)}: {labels}")
        slots = hand_slots_snapshot(actor)
        left = slots.get("left", {}) if isinstance(slots, dict) else {}
        right = slots.get("right", {}) if isinstance(slots, dict) else {}
        lines.append(
            "- Ręce: "
            f"Lewa={left.get('label', 'Pusta ręka')} · "
            f"Prawa={right.get('label', 'Pusta ręka')} · "
            f"Tryb={slots.get('mode_label', '-')}"
        )
    except Exception:
        pass

    known_prefixes = (
        "wizard_",
        "sorcerer_",
        "cleric_",
        "druid_",
        "alchemist_",
        "ranger_",
        "rogue_",
        "fighter_",
        "monk_",
        "champion_",
        "barbarian_",
    )
    runtime_rows: list[tuple[str, str]] = []
    for key in sorted(getattr(actor, "__dict__", {}).keys()):
        if key.startswith("_"):
            continue
        if not key.startswith(known_prefixes):
            continue
        value = getattr(actor, key, None)
        if callable(value):
            continue
        text = str(value)
        if len(text) > 180:
            text = text[:177] + "..."
        runtime_rows.append((key, text))

    if runtime_rows:
        lines.append("")
        lines.append("Runtime klasy:")
        for key, text in runtime_rows:
            lines.append(f"- {key}: {text}")

    spell_state = getattr(actor, "spell_state", None)
    if isinstance(spell_state, dict) and bool(spell_state.get("enabled", False)):
        known = spell_state.get("known", {}) or {}
        prepared = spell_state.get("prepared_today", {}) or {}
        remaining = spell_state.get("slot_remaining", {}) or {}
        lines.append("")
        lines.append("Stan magii:")
        lines.append(
            "- znane: "
            f"cantrip={len(list(known.get('cantrip', []) or []))}, "
            f"rank1={len(list(known.get('rank_1', []) or []))}, "
            f"focus={len(list(known.get('focus', []) or []))}, "
            f"innate={len(list(known.get('innate', []) or []))}"
        )
        if list(prepared.get("cantrip", []) or []):
            lines.append(f"- przygotowane cantripy: {', '.join(list(prepared.get('cantrip', []) or []))}")
        if list(prepared.get("rank_1", []) or []):
            lines.append(f"- przygotowane rank 1: {', '.join(list(prepared.get('rank_1', []) or []))}")
        if "rank_1" in remaining:
            lines.append(f"- pozostale sloty rank 1: {remaining.get('rank_1')}")
        lines.append(f"- enforce: {bool(spell_state.get('enforce', False))}")

    return "\n".join(lines).strip()
