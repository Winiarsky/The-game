from __future__ import annotations

from typing import Any, Iterable

CORE_SKILL_IDS = (
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


def status_labels(actor: Any) -> list[str]:
    if actor is None:
        return []
    labels_getter = getattr(actor, "status_labels", None)
    if callable(labels_getter):
        try:
            labels = list(labels_getter() or [])
            return [str(item) for item in labels if str(item).strip()]
        except Exception:
            pass
    out: list[str] = []
    for status in list(getattr(actor, "statuses", []) or []):
        label = (
            getattr(status, "display_label", None)
            or getattr(status, "label", None)
            or getattr(status, "id", None)
            or status
        )
        text = str(label or "").strip()
        if text:
            out.append(text)
    return out


def background_preview(actor: Any) -> tuple[str | None, str | None, str | None, str | None]:
    background_label = None
    background_feat_id = None
    background_ability_boosts_ui = None
    background_skill_training_ui = None
    for status in list(getattr(actor, "statuses", []) or []):
        data = getattr(status, "data", None) or {}
        if not bool(data.get("is_background")):
            continue
        background_label = (
            data.get("background_label")
            or getattr(status, "label", None)
            or getattr(status, "id", None)
        )
        background_feat_id = data.get("background_feat_id")
        background_ability_boosts_ui = data.get("background_ability_boosts_ui")
        background_skill_training_ui = data.get("background_skill_training_ui")
        break

    if not background_label:
        raw_background_id = str(getattr(actor, "background_id", "") or "").strip().lower()
        if raw_background_id:
            try:
                from localization import localize_term_pl

                background_label = (
                    localize_term_pl(raw_background_id)
                    or localize_term_pl(f"background_{raw_background_id}")
                    or raw_background_id.replace("_", " ").strip().title()
                )
            except Exception:
                background_label = raw_background_id.replace("_", " ").strip().title()

    return (
        str(background_label) if background_label else None,
        str(background_feat_id) if background_feat_id else None,
        str(background_ability_boosts_ui) if background_ability_boosts_ui else None,
        str(background_skill_training_ui) if background_skill_training_ui else None,
    )


def _inventory_snapshot(actor: Any) -> tuple[dict[str, Any] | None, dict[str, int] | None, str | None, dict[str, Any] | None, list[str]]:
    hand_slots: dict[str, Any] | None = None
    coin_pouch: dict[str, int] | None = None
    money_text: str | None = None
    bulk_summary: dict[str, Any] | None = None
    inventory_items: list[str] = []

    try:
        from GameObjects.items.inventory import hand_slots_snapshot

        hand_slots = hand_slots_snapshot(actor)
    except Exception:
        hand_slots = None

    try:
        from economy import actor_bulk_summary, ensure_actor_coin_pouch, format_actor_money

        coin_pouch = ensure_actor_coin_pouch(actor, default_gp=int(getattr(actor, "starting_gold_gp", 0) or 0))
        money_text = format_actor_money(actor)
        bulk_summary = actor_bulk_summary(actor)
    except Exception:
        coin_pouch = None
        money_text = None
        bulk_summary = None

    try:
        for item in list(getattr(actor, "inventory", []) or []):
            label = str(getattr(item, "name", "") or getattr(item, "item_id", "") or "").strip()
            if label:
                inventory_items.append(label)
    except Exception:
        inventory_items = []

    return hand_slots, coin_pouch, money_text, bulk_summary, inventory_items


def _normalize_skill_training(actor: Any) -> tuple[dict[str, str], list[str]]:
    def _normalize_skill_id(value: object) -> str:
        return str(value or "").strip().lower()

    raw_skill_ranks = getattr(actor, "skill_ranks", {}) or {}
    normalized_skill_ranks: dict[str, str] = {}
    if isinstance(raw_skill_ranks, dict):
        for key, rank in raw_skill_ranks.items():
            skill_id = _normalize_skill_id(key)
            if skill_id in CORE_SKILL_IDS:
                normalized_skill_ranks[skill_id] = str(rank or "untrained").strip().lower()

    trained_skills = {
        _normalize_skill_id(item)
        for item in list(getattr(actor, "trained_skills", []) or [])
        if _normalize_skill_id(item) in CORE_SKILL_IDS
    }

    if not normalized_skill_ranks and not trained_skills:
        for skill_id in CORE_SKILL_IDS:
            if bool(getattr(actor, f"{skill_id}_trained", False)):
                trained_skills.add(skill_id)

    if not normalized_skill_ranks and trained_skills:
        normalized_skill_ranks = {skill_id: "trained" for skill_id in trained_skills}
    if not trained_skills and normalized_skill_ranks:
        trained_skills = {
            skill_id
            for skill_id, rank in normalized_skill_ranks.items()
            if str(rank or "untrained").strip().lower() != "untrained"
        }

    return normalized_skill_ranks, sorted(trained_skills)


def _speed_snapshot_values(actor: Any, *, default_feet: int = 25) -> tuple[int | None, int | None]:
    raw_base_speed = getattr(actor, "base_speed_feet", None)
    try:
        raw_base_speed = int(raw_base_speed)
    except Exception:
        raw_base_speed = None
    if raw_base_speed is not None and raw_base_speed <= 0:
        raw_base_speed = None

    speed_bonus = 0
    for status in list(getattr(actor, "statuses", []) or []):
        data = getattr(status, "data", None) or {}
        if raw_base_speed is None and "base_speed_feet" in data:
            try:
                candidate = int(data.get("base_speed_feet") or 0)
            except Exception:
                candidate = 0
            if candidate > 0:
                raw_base_speed = candidate
        try:
            speed_bonus += int(data.get("base_speed_bonus_feet", 0) or 0)
        except Exception:
            continue

    if raw_base_speed is None:
        raw_base_speed = max(0, int(default_feet or 25))
    display_speed = max(0, int(raw_base_speed) + max(0, int(speed_bonus)))
    return int(raw_base_speed), int(display_speed)


def _spellcasting_snapshot(actor: Any) -> dict[str, Any] | None:
    state: dict[str, Any] = {}
    try:
        from spell_management import ensure_actor_spell_state

        ensured = ensure_actor_spell_state(actor, enforce=False)
        if isinstance(ensured, dict):
            state = dict(ensured)
    except Exception:
        state = dict(getattr(actor, "spell_state", {}) or {})

    try:
        from focus_pool import get_focus_points, get_focus_pool_max

        focus_points = int(get_focus_points(actor))
        focus_pool_max = int(get_focus_pool_max(actor))
    except Exception:
        try:
            focus_points = max(0, int(getattr(actor, "focus_point", 0) or 0))
        except Exception:
            focus_points = 0
        try:
            focus_pool_max = max(focus_points, int(getattr(actor, "focus_pool_max", 0) or 0))
        except Exception:
            focus_pool_max = focus_points

    known = dict(state.get("known", {}) or {})
    slot_total = {
        str(key): int(value or 0)
        for key, value in dict(state.get("slot_total", {}) or {}).items()
        if str(key).strip()
    }
    slot_remaining = {
        str(key): int(value or 0)
        for key, value in dict(state.get("slot_remaining", {}) or {}).items()
        if str(key).strip()
    }
    known_spells = {
        str(tier): [str(item) for item in list(items or []) if str(item).strip()]
        for tier, items in known.items()
        if isinstance(items, list) and list(items or [])
    }
    if not bool(state.get("enabled")) and focus_points <= 0 and focus_pool_max <= 0 and not slot_total and not known_spells:
        return None

    known_counts = {tier: len(items) for tier, items in known_spells.items()}

    # Build prepared spell usage info for prepared casters (wizard/cleric/druid)
    prepared_today = dict(state.get("prepared_today", {}) or {})
    prepared_counts_raw = dict(state.get("prepared_counts", {}) or {})
    consumed_counts_raw = dict(state.get("consumed_counts", {}) or {})
    prepared_spell_usage: dict[str, list[dict]] = {}
    for tier, spell_list in prepared_today.items():
        if not spell_list:
            continue
        tier_counts = dict(prepared_counts_raw.get(tier, {}) or {})
        tier_consumed = dict(consumed_counts_raw.get(tier, {}) or {})
        seen: set[str] = set()
        entries: list[dict] = []
        for sid in spell_list:
            if not sid or sid in seen:
                continue
            seen.add(sid)
            total = int(tier_counts.get(sid, 1) or 1)
            used = int(tier_consumed.get(sid, 0) or 0)
            entries.append({"id": sid, "prepared": total, "used": used, "remaining": max(0, total - used)})
        if entries:
            prepared_spell_usage[tier] = entries

    return {
        "enabled": bool(state.get("enabled")) or bool(slot_total) or focus_pool_max > 0,
        "class_name": str(state.get("class_name") or getattr(actor, "class_name", "") or ""),
        "focus_points": int(focus_points),
        "focus_pool_max": int(focus_pool_max),
        "slot_total": dict(slot_total),
        "slot_remaining": dict(slot_remaining),
        "known_counts": dict(known_counts),
        "known_spells": dict(known_spells),
        "prepared_spell_usage": prepared_spell_usage,
    }


def build_hero_snapshot(hero: Any, *, note: str | None = None) -> dict[str, Any]:
    hero_id = getattr(hero, "object_id", None) or getattr(hero, "name", None) or "hero"
    hand_slots, coin_pouch, money_text, bulk_summary, inventory_items = _inventory_snapshot(hero)
    (
        background_label,
        background_feat_id,
        background_ability_boosts_ui,
        background_skill_training_ui,
    ) = background_preview(hero)
    normalized_skill_ranks, trained_skills = _normalize_skill_training(hero)
    ac_value = getattr(hero, "ac", None)
    ac_base = getattr(hero, "ac", None)
    ac_modifier = 0
    try:
        from combat import ac_with_bonuses

        ac_value, ac_base, ac_modifier = ac_with_bonuses(hero)
    except Exception:
        pass
    raw_base_speed_feet, display_speed_feet = _speed_snapshot_values(hero)
    spellcasting = _spellcasting_snapshot(hero)

    spell_dc: int | None = None
    class_dc: int | None = None
    perception_modifier: int | None = None
    try:
        spell_dc = int(getattr(hero, "spell_dc", None) or 0) or None
    except Exception:
        pass
    try:
        class_dc = int(getattr(hero, "class_dc", None) or 0) or None
    except Exception:
        pass
    try:
        perception_modifier = int(getattr(hero, "perception_modifier", None) or 0)
    except Exception:
        pass

    return {
        "id": str(hero_id),
        "character_id": getattr(hero, "character_id", None),
        "name": getattr(hero, "name", None) or str(hero_id),
        "image": getattr(hero, "image", None),
        "statuses": status_labels(hero),
        "note": note,
        "level": getattr(hero, "level", None),
        "pos": getattr(hero, "position", None),
        "wounds": getattr(hero, "wounds", None),
        "initiative": getattr(hero, "initiative", None),
        "class_id": getattr(hero, "class_id", None) or getattr(hero, "class_name", None),
        "ancestry_id": getattr(hero, "ancestry_id", None),
        "heritage_id": getattr(hero, "heritage_id", None),
        "ac": ac_value,
        "ac_base": ac_base,
        "ac_modifier": ac_modifier,
        "max_hp": getattr(hero, "max_hp", None),
        "base_speed_feet": raw_base_speed_feet,
        "speed_feet": display_speed_feet,
        "ability_scores": dict(getattr(hero, "ability_scores", {}) or {}),
        "ability_modifiers": dict(getattr(hero, "ability_modifiers", {}) or {}),
        "skill_ranks": normalized_skill_ranks,
        "save_ranks": dict(getattr(hero, "save_ranks", {}) or {}),
        "perception_rank": getattr(hero, "perception_rank", None),
        "perception_modifier": perception_modifier,
        "spell_dc": spell_dc,
        "class_dc": class_dc,
        "trained_skills": trained_skills,
        "lore_skills": list(getattr(hero, "lore_skills", []) or []),
        "background_label": background_label,
        "background_feat_id": background_feat_id,
        "background_ability_boosts_ui": background_ability_boosts_ui,
        "background_skill_training_ui": background_skill_training_ui,
        "preview_barbarian_instinct_id": getattr(hero, "preview_barbarian_instinct_id", None),
        "creation_in_progress": bool(getattr(hero, "character_creation_in_progress", False)),
        "hand_slots": hand_slots,
        "coin_pouch": coin_pouch,
        "money_text": money_text,
        "bulk_summary": bulk_summary,
        "inventory_items": list(inventory_items),
        "spellcasting": spellcasting,
    }


def build_companion_snapshot(companion: Any, *, note: str | None = None) -> dict[str, Any]:
    companion_id = getattr(companion, "object_id", None) or getattr(companion, "name", None) or "companion"
    try:
        max_hp = int(getattr(companion, "max_hp", 0) or 0)
    except Exception:
        max_hp = 0
    try:
        hp = int(getattr(companion, "hp", 0) or 0)
    except Exception:
        hp = 0
    try:
        speed_feet = max(0, int(getattr(companion, "land_speed_feet", 25) or 25))
    except Exception:
        speed_feet = 25

    raw_mods = dict(getattr(companion, "ability_mods", {}) or {})
    ability_modifiers = {
        "strength": int(raw_mods.get("str", 0) or 0),
        "dexterity": int(raw_mods.get("dex", 0) or 0),
        "constitution": int(raw_mods.get("con", 0) or 0),
        "intelligence": int(raw_mods.get("int", 0) or 0),
        "wisdom": int(raw_mods.get("wis", 0) or 0),
        "charisma": int(raw_mods.get("cha", 0) or 0),
    }
    owner_name = str(getattr(companion, "owner_name", "") or "").strip()

    return {
        "id": str(companion_id),
        "character_id": None,
        "name": getattr(companion, "name", None) or str(companion_id),
        "image": getattr(companion, "image", None),
        "statuses": status_labels(companion),
        "note": note,
        "level": getattr(companion, "level", None),
        "pos": getattr(companion, "position", None),
        "wounds": max(0, max_hp - hp) if max_hp > 0 else None,
        "initiative": None,
        "class_id": "animal_companion",
        "ancestry_id": None,
        "heritage_id": None,
        "ac": getattr(companion, "ac", None),
        "ac_base": getattr(companion, "ac", None),
        "ac_modifier": 0,
        "max_hp": max_hp or None,
        "base_speed_feet": speed_feet,
        "speed_feet": speed_feet,
        "ability_scores": {},
        "ability_modifiers": ability_modifiers,
        "skill_ranks": {},
        "save_ranks": {},
        "perception_rank": None,
        "perception_modifier": None,
        "spell_dc": None,
        "class_dc": None,
        "trained_skills": [],
        "lore_skills": [],
        "background_label": None,
        "background_feat_id": None,
        "background_ability_boosts_ui": None,
        "background_skill_training_ui": None,
        "preview_barbarian_instinct_id": None,
        "creation_in_progress": False,
        "hand_slots": None,
        "coin_pouch": None,
        "money_text": None,
        "bulk_summary": None,
        "inventory_items": [],
        "spellcasting": None,
        "is_companion": True,
        "owner_id": getattr(companion, "owner_id", None),
        "owner_name": owner_name or None,
        "companion_type": getattr(companion, "companion_type", None),
    }


def build_active_actor_payload(
    actor: Any | None,
    *,
    heroes: Iterable[Any] | None = None,
    enemies: Iterable[Any] | None = None,
    default_kind: str | None = None,
) -> dict[str, Any]:
    if actor is None:
        return {"id": None, "name": None, "kind": None}

    kind = default_kind
    if kind is None:
        hero_pool = tuple(heroes or ())
        enemy_pool = tuple(enemies or ())
        if actor in hero_pool or bool(getattr(actor, "character_creation_in_progress", False)):
            kind = "hero"
        elif actor in enemy_pool:
            kind = "enemy"

    actor_id = getattr(actor, "object_id", None) or getattr(actor, "name", None) or str(id(actor))
    return {
        "id": str(actor_id),
        "name": getattr(actor, "name", None) or str(actor_id),
        "kind": kind,
        "image": getattr(actor, "image", None) or getattr(actor, "portrait_image", None),
        "asset_id": str(actor_id),
    }


__all__ = [
    "CORE_SKILL_IDS",
    "_speed_snapshot_values",
    "background_preview",
    "build_active_actor_payload",
    "build_companion_snapshot",
    "build_hero_snapshot",
    "status_labels",
]
