from __future__ import annotations

from typing import Any

from prompt_text_catalog import render_prompt_text


_HP_MAX_FLAT_KEYS = (
    "hp_max_flat",
    "max_hp_flat",
    "hp_flat_bonus",
    "max_hp_bonus",
    "hp_bonus",
)
_HP_MAX_PER_LEVEL_KEYS = (
    "hp_max_per_level",
    "max_hp_per_level",
    "hp_per_level_bonus",
)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _iter_status_data(actor: Any):
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return
    for status in statuses:
        data = getattr(status, "data", None)
        if isinstance(data, dict):
            yield data


def uses_wounds_model(actor: Any) -> bool:
    return hasattr(actor, "wounds")


def _status_hp_contributors(actor: Any) -> tuple[int, int]:
    flat = 0
    per_level = 0
    for data in _iter_status_data(actor):
        for key in _HP_MAX_FLAT_KEYS:
            if key in data:
                flat += _safe_int(data.get(key), 0)
                break
        for key in _HP_MAX_PER_LEVEL_KEYS:
            if key in data:
                per_level += _safe_int(data.get(key), 0)
                break
    return int(flat), int(per_level)


def _status_first_int(actor: Any, keys: tuple[str, ...]) -> int | None:
    for data in _iter_status_data(actor):
        for key in keys:
            if key not in data:
                continue
            try:
                return int(data.get(key))
            except Exception:
                continue
    return None


def _drained_reduction(actor: Any, level: int) -> int:
    try:
        from statuses import drained_value

        drained = max(0, int(drained_value(actor) or 0))
        return drained * max(1, int(level))
    except Exception:
        return 0


def computed_max_hp(actor: Any) -> int | None:
    if actor is None:
        return None
    level = max(1, _safe_int(getattr(actor, "level", 1), 1))
    flat_bonus, per_level = _status_hp_contributors(actor)

    ancestry_hp = getattr(actor, "ancestry_hp", None)
    if ancestry_hp is None:
        ancestry_hp = _status_first_int(actor, ("ancestry_hp", "hp_ancestry"))
    class_hp = getattr(actor, "class_hp", None)
    if class_hp is None:
        class_hp = _status_first_int(actor, ("class_hp", "hp_class"))
    has_component_hp = ancestry_hp is not None or class_hp is not None

    base_raw = getattr(actor, "max_hp", None)
    if has_component_hp:
        ancestry_val = max(0, _safe_int(ancestry_hp, 0))
        class_val = max(0, _safe_int(class_hp, 0))
        base = ancestry_val + class_val
        if base <= 0:
            if base_raw is not None:
                base = _safe_int(base_raw, 0)
            else:
                base_hp = getattr(actor, "base_max_hp", None)
                if base_hp is None:
                    return None
                base = _safe_int(base_hp, 0)
        total = base + flat_bonus + per_level * level
        total -= _drained_reduction(actor, level)
        return max(1, total)

    if base_raw is None:
        base_hp = getattr(actor, "base_max_hp", None)
        if base_hp is None:
            return None
        base = _safe_int(base_hp, 0)
        total = base + flat_bonus + per_level * level
        total -= _drained_reduction(actor, level)
        return max(1, total)

    base = _safe_int(base_raw, 0)
    total = base + flat_bonus + per_level * level
    total -= _drained_reduction(actor, level)
    return max(1, total)


def current_hp(actor: Any) -> int | None:
    if actor is None:
        return None
    if uses_wounds_model(actor):
        max_hp = computed_max_hp(actor)
        if max_hp is None:
            return None
        wounds = max(0, _safe_int(getattr(actor, "wounds", 0), 0))
        return max(0, int(max_hp) - wounds)
    if hasattr(actor, "hp"):
        return _safe_int(getattr(actor, "hp", 0), 0)
    return None


def get_temp_hp(actor: Any) -> int:
    if actor is None:
        return 0
    return max(0, _safe_int(getattr(actor, "temp_hp", 0), 0))


def _set_temp_hp(actor: Any, value: int, *, source: str | None = None) -> int:
    if actor is None:
        return 0
    final_value = max(0, _safe_int(value, 0))
    try:
        setattr(actor, "temp_hp", final_value)
    except Exception:
        return 0
    if final_value <= 0:
        try:
            setattr(actor, "temp_hp_source", None)
        except Exception:
            pass
    elif source is not None:
        try:
            setattr(actor, "temp_hp_source", str(source))
        except Exception:
            pass
    return final_value


def grant_temp_hp(actor: Any, amount: int, *, source: str | None = None) -> dict[str, Any]:
    granted = max(0, _safe_int(amount, 0))
    current = get_temp_hp(actor)
    if granted <= current:
        return {
            "changed": False,
            "temp_hp": current,
            "source": getattr(actor, "temp_hp_source", None),
            "granted": granted,
        }
    updated = _set_temp_hp(actor, granted, source=source)
    return {
        "changed": True,
        "temp_hp": updated,
        "source": getattr(actor, "temp_hp_source", None),
        "granted": granted,
    }


def clear_temp_hp(actor: Any, *, source: str | None = None) -> bool:
    if actor is None:
        return False
    if source is not None:
        current_source = str(getattr(actor, "temp_hp_source", "") or "")
        if current_source != str(source):
            return False
    before = get_temp_hp(actor)
    _set_temp_hp(actor, 0, source=None)
    return before > 0


def _consume_temp_hp(actor: Any, amount: int) -> tuple[int, int]:
    incoming = max(0, _safe_int(amount, 0))
    if incoming <= 0:
        return 0, 0
    current = get_temp_hp(actor)
    if current <= 0:
        return 0, incoming
    absorbed = min(current, incoming)
    _set_temp_hp(actor, current - absorbed, source=None)
    return absorbed, incoming - absorbed


def _is_player_wound_target(actor: Any) -> bool:
    if actor is None:
        return False
    if bool(getattr(actor, "character_id", None)):
        return True
    try:
        from hero import Hero

        return isinstance(actor, Hero)
    except Exception:
        return False


def _prompt_player_wounds(actor: Any, hp_damage: int, damage_type: str, *, source: str | None = None) -> None:
    if hp_damage <= 0 or not _is_player_wound_target(actor):
        return
    try:
        from ui_client import get_ui_client

        ui = get_ui_client()
    except Exception:
        return
    if ui is None or not getattr(ui, "enabled", False):
        return

    name = str(getattr(actor, "name", None) or "Bohater")
    total_wounds = max(0, _safe_int(getattr(actor, "wounds", 0), 0))
    max_hp = computed_max_hp(actor)
    total_line = f"Łącznie ran: {total_wounds}/{max_hp}." if max_hp else f"Łącznie ran: {total_wounds}."
    damage_type_label = str(damage_type or "").strip().lower()
    damage_line = f"Typ obrażeń: {damage_type_label}." if damage_type_label else None
    prompt_text = render_prompt_text(
        "combat.player_wounds",
        actor_name=name,
        hp_damage=hp_damage,
        total_wounds_line=total_line,
        damage_type_line=damage_line or "",
    )
    title = str(prompt_text.get("title") or f"Rany: {name}")
    prompt_long = str(
        prompt_text.get("body_markdown")
        or (
            f"{name} otrzymuje {hp_damage} ran.\n"
            f"Zapisz {hp_damage} ran na karcie postaci i potwierdź."
        )
    )
    details_markdown = str(prompt_text.get("details_markdown") or "").strip() or None
    summary = str(prompt_text.get("summary") or f"{name} otrzymuje {hp_damage} ran.")
    try:
        ui.prompt_info(
            title,
            prompt_long=prompt_long,
            source=source or "player_wounds",
            scope_key=f"wounds:{getattr(actor, 'object_id', name)}",
            dedupe_key=f"wounds:{getattr(actor, 'object_id', name)}:{total_wounds}:{hp_damage}:{damage_type_label}",
            summary=summary,
            details_markdown=details_markdown,
        )
    except Exception:
        return


def apply_damage(
    actor: Any,
    amount: int,
    damage_type: str,
    *,
    source: str | None = None,
    critical: bool = False,
    nonlethal: bool = False,
) -> dict[str, Any]:
    incoming = max(0, _safe_int(amount, 0))
    temp_absorbed, hp_damage = _consume_temp_hp(actor, incoming)
    defeated = False

    if hp_damage > 0:
        if uses_wounds_model(actor):
            try:
                current_wounds = max(0, _safe_int(getattr(actor, "wounds", 0), 0))
                setattr(actor, "wounds", current_wounds + hp_damage)
            except Exception:
                pass
            hp_now = current_hp(actor)
            if hp_now is not None and hp_now <= 0:
                try:
                    from statuses import on_reduced_to_zero

                    info = on_reduced_to_zero(
                        actor,
                        source=source or f"damage:{damage_type}",
                        critical=bool(critical),
                        nonlethal=bool(nonlethal),
                    )
                    defeated = bool((info or {}).get("dead", False))
                except Exception:
                    defeated = False
        elif hasattr(actor, "hp"):
            hp_now = _safe_int(getattr(actor, "hp", 0), 0) - hp_damage
            try:
                setattr(actor, "hp", hp_now)
            except Exception:
                pass
            defeated = hp_now <= 0

    _prompt_player_wounds(actor, hp_damage, damage_type, source=source)

    return {
        "incoming": incoming,
        "temp_absorbed": temp_absorbed,
        "hp_damage": hp_damage,
        "defeated": defeated,
        "current_hp": current_hp(actor),
        "temp_hp": get_temp_hp(actor),
    }


def heal(actor: Any, amount: int, *, source: str | None = None) -> dict[str, Any]:
    incoming = max(0, _safe_int(amount, 0))
    if incoming <= 0:
        return {
            "healed": 0,
            "current_hp": current_hp(actor),
            "temp_hp": get_temp_hp(actor),
        }

    blocked_reason = None
    blocked_amount = 0
    try:
        from GameObjects.events.elixirs.runtime_helpers import healing_block_amount, healing_block_reason

        blocked_amount = max(0, int(healing_block_amount(actor) or 0))
        blocked_reason = healing_block_reason(actor)
    except Exception:
        blocked_amount = 0
        blocked_reason = None

    healed = 0
    if uses_wounds_model(actor):
        old_wounds = max(0, _safe_int(getattr(actor, "wounds", 0), 0))
        min_wounds = max(0, int(blocked_amount or 0))
        new_wounds = max(min_wounds, old_wounds - incoming)
        healed = old_wounds - new_wounds
        try:
            setattr(actor, "wounds", new_wounds)
        except Exception:
            pass
        try:
            from statuses import on_heal

            on_heal(actor, source=source or "heal")
        except Exception:
            pass
    elif hasattr(actor, "hp"):
        hp_now = _safe_int(getattr(actor, "hp", 0), 0)
        max_hp = computed_max_hp(actor)
        if max_hp is None:
            new_hp = hp_now + incoming
        else:
            heal_cap = max(0, int(max_hp) - max(0, int(blocked_amount or 0)))
            new_hp = min(int(heal_cap), hp_now + incoming)
        healed = max(0, new_hp - hp_now)
        try:
            setattr(actor, "hp", new_hp)
        except Exception:
            pass
        try:
            from statuses import on_heal

            on_heal(actor, source=source or "heal")
        except Exception:
            pass

    return {
        "healed": healed,
        "current_hp": current_hp(actor),
        "temp_hp": get_temp_hp(actor),
        "blocked_healing_amount": max(0, int(blocked_amount or 0)),
        "blocked_healing_reason": blocked_reason,
    }


__all__ = [
    "uses_wounds_model",
    "computed_max_hp",
    "current_hp",
    "get_temp_hp",
    "grant_temp_hp",
    "clear_temp_hp",
    "apply_damage",
    "heal",
]
