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
        "base_speed_feet": getattr(hero, "base_speed_feet", None),
        "ability_scores": dict(getattr(hero, "ability_scores", {}) or {}),
        "ability_modifiers": dict(getattr(hero, "ability_modifiers", {}) or {}),
        "skill_ranks": normalized_skill_ranks,
        "save_ranks": dict(getattr(hero, "save_ranks", {}) or {}),
        "perception_rank": getattr(hero, "perception_rank", None),
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
    }


__all__ = [
    "CORE_SKILL_IDS",
    "background_preview",
    "build_active_actor_payload",
    "build_hero_snapshot",
    "status_labels",
]
