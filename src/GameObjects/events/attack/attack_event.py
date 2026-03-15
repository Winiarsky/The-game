from __future__ import annotations

from GameObjects.items.inventory import ensure_actor_inventory, get_equipped_weapons, item_description, item_label
from GameObjects.items.weapon import normalize_weapon_id
from ..base import EventContext, EventResult, GameEvent
from ..registry import dispatch_event, get_event_cls, register_event


def _weapon_event_name(weapon) -> str | None:
    from_id = normalize_weapon_id(getattr(weapon, "item_id", None))
    explicit = str(getattr(weapon, "event_name", "") or "").strip().lower()
    if explicit:
        return explicit
    if from_id:
        return from_id
    return None


def _select_weapon_from_equipped(ctx: EventContext, equipped: list[object]) -> object | None:
    if not equipped:
        return None
    if len(equipped) == 1:
        return equipped[0]

    labels = []
    for idx, weapon in enumerate(equipped, start=1):
        labels.append(
            {
                "raw": str(getattr(weapon, "instance_id", idx)),
                "label": item_label(weapon),
                "desc": item_description(weapon),
                "key": str(idx),
            }
        )

    ui = getattr(ctx.game, "ui", None)
    if ui and getattr(ui, "enabled", False):
        answer = ui.prompt_choice(
            "Wybierz broń do ataku",
            choices=[entry["label"] for entry in labels],
            source="attack",
            layout="dialog",
            choice_meta=labels,
            title="Wybór broni",
            subtitle="Masz aktywne dwie bronie 1H.",
            prompt_long="Wybierz numer broni do tego ataku.",
        )
        if answer:
            normalized = str(answer).strip().lower()
            if normalized.isdigit():
                idx = int(normalized) - 1
                if 0 <= idx < len(equipped):
                    return equipped[idx]
            for entry, weapon in zip(labels, equipped):
                if normalized in (entry["raw"].lower(), entry["label"].lower()):
                    return weapon

    acceptable = [normalize_weapon_id(getattr(item, "item_id", None)) or item_label(item).lower() for item in equipped]
    answer = ctx.game.conn.read_card("Wybierz broń do ataku", acceptable).strip().lower()
    for weapon in equipped:
        weapon_id = normalize_weapon_id(getattr(weapon, "item_id", None))
        if answer == (weapon_id or "").lower():
            return weapon
        if answer == item_label(weapon).strip().lower():
            return weapon
    return None


def _has_status(actor, status_id: str) -> bool:
    if actor is None:
        return False
    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            return bool(checker(status_id))
        except Exception:
            return False
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", status) == status_id:
            return True
    return False


def _generic_weapon_attack(ctx: EventContext, weapon) -> EventResult:
    from .base_attack_range_event import BaseRangeAttackEvent
    from .basic_melee_attack_event import BasicMeleeAttackEvent

    weapon_id = normalize_weapon_id(getattr(weapon, "item_id", None)) or "weapon"
    weapon_name = item_label(weapon)
    ranged = bool(getattr(weapon, "ranged", False))

    if ranged:
        event = BaseRangeAttackEvent()
        event.default_tags = ["attack_ranged", "ranged_attack", weapon_id]
        try:
            event.range_increment_ft = max(5, int(getattr(weapon, "range_increment_ft", 60) or 60))
        except Exception:
            event.range_increment_ft = 60
    else:
        event = BasicMeleeAttackEvent()
        event.default_tags = ["attack_melee", weapon_id]

    event.name = f"generic_{weapon_id}"
    event.weapon_label = weapon_name
    event.action_id_base = f"attack_{weapon_id}"
    event.damage_prompt = str(getattr(weapon, "damage_prompt", "1k4 + STR") or "1k4 + STR")
    event.damage_type = str(getattr(weapon, "damage_type", "bludgeoning") or "bludgeoning")

    runtime_ctx = EventContext(
        game=ctx.game,
        actor=ctx.actor,
        tags=list(ctx.tags or []),
        metadata={
            **dict(ctx.metadata or {}),
            "selected_weapon": weapon,
            "selected_weapon_instance_id": str(getattr(weapon, "instance_id", "") or ""),
        },
    )
    return event.run(runtime_ctx)


@register_event
class AttackEvent(GameEvent):
    name = "attack"
    default_tags = ["attack"]
    consumes_action = True

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak aktora do ataku.")
        if _has_status(actor, "monk_stance_active"):
            return dispatch_event(
                "unarmed",
                EventContext(
                    game=ctx.game,
                    actor=actor,
                    tags=list(ctx.tags or []),
                    metadata=dict(ctx.metadata or {}),
                ),
            )

        ensure_actor_inventory(actor)
        equipped = get_equipped_weapons(actor)

        explicit_weapon = normalize_weapon_id((ctx.metadata or {}).get("weapon_id") or (ctx.metadata or {}).get("weapon"))
        selected = None
        if explicit_weapon:
            for weapon in equipped:
                if normalize_weapon_id(getattr(weapon, "item_id", None)) == explicit_weapon:
                    selected = weapon
                    break
            if selected is None:
                return EventResult.cancelled(message=f"Wybrana broń nie jest aktywna: {explicit_weapon}.")
        else:
            # Bazowy "attack" zawsze używa aktualnie aktywnej broni (pierwsza z equipped).
            selected = equipped[0] if equipped else None

        # Attack event fallbackuje do unarmed, ale unarmed pozostaje osobnym eventem.
        if selected is None:
            return dispatch_event(
                "unarmed",
                EventContext(
                    game=ctx.game,
                    actor=actor,
                    tags=list(ctx.tags or []),
                    metadata=dict(ctx.metadata or {}),
                ),
            )

        event_name = _weapon_event_name(selected)
        if not event_name:
            return EventResult.cancelled(message=f"Brak eventu ataku dla broni: {item_label(selected)}.")

        has_specific_event = True
        try:
            get_event_cls(event_name)
        except Exception:
            has_specific_event = False

        if not has_specific_event:
            return _generic_weapon_attack(ctx, selected)

        result = dispatch_event(
            event_name,
            EventContext(
                game=ctx.game,
                actor=actor,
                tags=list(ctx.tags or []),
                metadata={
                    **dict(ctx.metadata or {}),
                    "selected_weapon": selected,
                    "selected_weapon_instance_id": str(getattr(selected, "instance_id", "") or ""),
                },
            ),
        )
        return result
