from __future__ import annotations

from collections import OrderedDict

from bonuses import BonusEffect, BonusType
from combat.damage_utils import remove_defeated_enemy
from statuses import Status

from .attack.basic_melee_attack_event import BasicMeleeAttackEvent
from .base import ActionCostEvent, EventContext, EventResult
from .registry import dispatch_event, register_event


MONK_STANCE_ACTIVE_STATUS_ID = "monk_stance_active"
MONK_STANCE_AC_CIRC_SOURCE = "monk_stance:ac:circumstance"
MONK_STANCE_AC_ITEM_SOURCE = "monk_stance:ac:item"


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


def _focus_points(actor) -> int:
    raw = getattr(actor, "focus_point", None)
    try:
        return max(0, int(raw or 0))
    except Exception:
        return 0


def _current_attacks_this_turn(ctx: EventContext, actor) -> int:
    state = getattr(ctx.game, "state", None)
    if not ctx.in_combat or state is None:
        return 0
    attack_state = getattr(state, "attack_state", None)
    if not isinstance(attack_state, dict):
        return 0
    payload = attack_state.get(actor, {}) or {}
    try:
        return max(0, int(payload.get("attacks_this_turn", 0) or 0))
    except Exception:
        return 0


def _bump_attack_state(ctx: EventContext, actor, *, event_name: str, count: int = 1) -> None:
    if not ctx.in_combat:
        return
    state = getattr(ctx.game, "state", None)
    if state is None:
        return
    attack_state = getattr(state, "attack_state", None)
    if not isinstance(attack_state, dict):
        return
    try:
        amount = max(0, int(count))
    except Exception:
        amount = 0
    if amount <= 0:
        return
    payload = attack_state.setdefault(actor, {})
    payload["attacks_this_turn"] = int(payload.get("attacks_this_turn", 0) or 0) + amount
    weapon_counts = payload.setdefault("weapon_counts", {})
    weapon_key = "attack_unarmed"
    weapon_counts[weapon_key] = int(weapon_counts.get(weapon_key, 0) or 0) + amount


def _merge_damage_components(*groups: list[tuple[str, int]]) -> list[tuple[str, int]]:
    merged: "OrderedDict[str, int]" = OrderedDict()
    for group in groups:
        for dmg_type, amount in group:
            dtype = str(dmg_type or "").strip().lower()
            if not dtype:
                continue
            try:
                value = max(0, int(amount or 0))
            except Exception:
                value = 0
            if value <= 0:
                continue
            merged[dtype] = int(merged.get(dtype, 0) or 0) + value
    return [(dtype, amount) for dtype, amount in merged.items() if amount > 0]


def _apply_merged_damage(target, damage_components: list[tuple[str, int]]) -> bool:
    defeated = False
    applier = getattr(target, "apply_damage", None)
    for dmg_type, amount in damage_components:
        if defeated:
            break
        value = max(0, int(amount or 0))
        if value <= 0:
            continue
        if callable(applier):
            try:
                _hp, defeated = applier(value, str(dmg_type))
                continue
            except Exception:
                pass
    return bool(defeated)


def _apply_pending_persistent(target, payloads: list[dict], *, ctx: EventContext, source: str) -> None:
    helper = BasicMeleeAttackEvent()
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        helper._apply_on_hit_persistent(target, payload, ctx=ctx, source=source)


def _remove_defeated_target(game, target, target_pos) -> None:
    pos = target_pos if isinstance(target_pos, tuple) else getattr(target, "position", None)
    if target in getattr(game, "enemies", []):
        try:
            remove_defeated_enemy(game, target, position=pos, source="monk_feat")
            return
        except Exception:
            pass
    if isinstance(pos, tuple):
        try:
            game.board.remove(pos)
        except Exception:
            pass
    try:
        if target in getattr(game, "heroes", []):
            game.heroes.remove(target)
    except Exception:
        pass
    try:
        target.position = None
    except Exception:
        pass


def _remove_statuses(actor, status_id: str) -> None:
    if actor is None:
        return
    remover = getattr(actor, "remove_status", None)
    if callable(remover):
        for _ in range(6):
            if not _has_status(actor, status_id):
                break
            try:
                remover(status_id)
            except Exception:
                break
        return
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return
    actor.statuses = [status for status in statuses if getattr(status, "id", status) != status_id]


def _clear_monk_stance_effects(actor) -> None:
    _remove_statuses(actor, MONK_STANCE_ACTIVE_STATUS_ID)
    remover = getattr(actor, "remove_bonuses_by_source", None)
    if callable(remover):
        try:
            remover(MONK_STANCE_AC_CIRC_SOURCE)
        except Exception:
            pass
        try:
            remover(MONK_STANCE_AC_ITEM_SOURCE)
        except Exception:
            pass


def _add_ac_bonus(actor, *, source: str, bonus_type: BonusType, value: int, label: str) -> None:
    if actor is None:
        return
    try:
        amount = int(value)
    except Exception:
        amount = 0
    if amount <= 0:
        return

    effect = BonusEffect(
        type=bonus_type,
        value=amount,
        tag="ac",
        source=source,
        label=label,
    )

    adder = getattr(actor, "add_bonus", None)
    if callable(adder):
        try:
            adder(effect)
            return
        except Exception:
            pass

    bonuses = getattr(actor, "bonuses", None)
    if isinstance(bonuses, list):
        bonuses.append(effect)


def _activate_stance(
    actor,
    *,
    stance_id: str,
    stance_label: str,
    profile: dict,
    ui_notes: list[str] | None = None,
    ac_circumstance_bonus: int = 0,
    ac_item_bonus: int = 0,
) -> None:
    _clear_monk_stance_effects(actor)
    adder = getattr(actor, "add_status", None)
    if callable(adder):
        adder(
            Status(
                id=MONK_STANCE_ACTIVE_STATUS_ID,
                label=f"{stance_label} (Active)",
                data={
                    "effect_tags": ["stance", "monk"],
                    "stance_id": stance_id,
                    "stance_label": stance_label,
                    "unarmed_profile": dict(profile),
                    "ui_notes": list(ui_notes or []),
                },
            )
        )

    _add_ac_bonus(
        actor,
        source=MONK_STANCE_AC_CIRC_SOURCE,
        bonus_type=BonusType.CIRCUMSTANCE,
        value=ac_circumstance_bonus,
        label=f"{stance_label}: AC",
    )
    _add_ac_bonus(
        actor,
        source=MONK_STANCE_AC_ITEM_SOURCE,
        bonus_type=BonusType.ITEM,
        value=ac_item_bonus,
        label=f"{stance_label}: AC",
    )


def _stance_profile_crane() -> dict:
    return {
        "label": "crane wing",
        "damage_prompt": "1k6 + STR",
        "damage_type": "bludgeoning",
        "extra_tags": ["unarmed", "agile", "finesse", "nonlethal"],
    }


def _stance_profile_dragon() -> dict:
    return {
        "label": "dragon tail",
        "damage_prompt": "1k10 + STR",
        "damage_type": "bludgeoning",
        "extra_tags": ["unarmed", "backswing", "nonlethal"],
    }


def _stance_profile_mountain() -> dict:
    return {
        "label": "falling stone",
        "damage_prompt": "1k8 + STR",
        "damage_type": "bludgeoning",
        "extra_tags": ["unarmed", "forceful", "nonlethal"],
    }


def _stance_profile_tiger() -> dict:
    return {
        "label": "tiger claw",
        "damage_prompt": "1k8 + STR",
        "damage_type": "slashing",
        "extra_tags": ["unarmed", "agile", "finesse", "nonlethal"],
        "on_hit_persistent_damage": {
            "formula": "1k4",
            "damage_type": "bleed",
            "on_critical_only": True,
        },
    }


def _stance_profile_wolf() -> dict:
    return {
        "label": "wolf jaw",
        "damage_prompt": "1k8 + STR",
        "damage_type": "piercing",
        "extra_tags": ["unarmed", "agile", "finesse", "backstabber", "nonlethal"],
    }


@register_event
class FlurryOfBlowsEvent(ActionCostEvent):
    name = "flurry_of_blows"
    default_tags = ["monk", "attack_melee", "attack", "flourish", "unarmed"]
    actions_cost = 1
    consumes_action = True
    available_in_combat = True
    available_in_exploration = False

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Flurry of Blows: brak aktora.")
        if not _has_status(actor, "flurry_of_blows"):
            return EventResult.cancelled(message="Flurry of Blows: wymaga feature Flurry of Blows.")

        initial_attacks = _current_attacks_this_turn(ctx, actor)
        base_metadata = dict(ctx.metadata or {})

        first_result = dispatch_event(
            "unarmed",
            EventContext(
                game=ctx.game,
                actor=actor,
                tags=list(ctx.tags or []),
                metadata={
                    **base_metadata,
                    "fixed_attacks_this_turn": initial_attacks,
                    "suppress_attack_record": True,
                    "roll_only": True,
                },
            ),
        )
        if not first_result.success:
            return EventResult.cancelled(message=first_result.message or "Flurry of Blows: pierwszy Strike nieudany.")

        second_result = dispatch_event(
            "unarmed",
            EventContext(
                game=ctx.game,
                actor=actor,
                tags=list(ctx.tags or []),
                metadata={
                    **base_metadata,
                    "fixed_attacks_this_turn": initial_attacks + 1,
                    "suppress_attack_record": True,
                    "roll_only": True,
                },
            ),
        )

        _bump_attack_state(ctx, actor, event_name="unarmed", count=2)

        first_data = dict(first_result.data or {})
        second_data = dict(second_result.data or {})

        first_hit = bool(first_data.get("hit", False))
        second_hit = bool(second_data.get("hit", False))
        first_target = first_data.get("target")
        second_target = second_data.get("target")

        defeated = False
        messages: list[str] = []

        if first_hit and second_hit and first_target is not None and first_target is second_target:
            merged = _merge_damage_components(
                list(first_data.get("damage_components") or []),
                list(second_data.get("damage_components") or []),
            )
            if merged:
                defeated = _apply_merged_damage(first_target, merged)
                if defeated:
                    _remove_defeated_target(ctx.game, first_target, first_data.get("target_pos"))
            persistent_payloads = []
            if first_data.get("pending_persistent_payload"):
                persistent_payloads.append(dict(first_data.get("pending_persistent_payload") or {}))
            if second_data.get("pending_persistent_payload"):
                persistent_payloads.append(dict(second_data.get("pending_persistent_payload") or {}))
            _apply_pending_persistent(first_target, persistent_payloads, ctx=ctx, source=self.name)

            ctx.game.events.safe_emit_action(
                actor=actor,
                action_id=self.name,
                action_tags=self._effective_tags(ctx),
                target=first_target,
                target_pos=first_data.get("target_pos"),
                damage=sum(max(0, int(amount or 0)) for _dtype, amount in merged),
                damage_components=merged,
                defeated=defeated,
            )
            messages.append("Flurry of Blows: oba trafienia scalone dla resist/weakness.")
        else:
            for data in (first_data, second_data):
                if not bool(data.get("hit", False)):
                    continue
                target = data.get("target")
                if target is None:
                    continue
                components = list(data.get("damage_components") or [])
                this_defeated = _apply_merged_damage(target, components)
                if this_defeated:
                    _remove_defeated_target(ctx.game, target, data.get("target_pos"))
                payload = data.get("pending_persistent_payload")
                if payload:
                    _apply_pending_persistent(target, [dict(payload)], ctx=ctx, source=self.name)
                defeated = defeated or this_defeated
                ctx.game.events.safe_emit_action(
                    actor=actor,
                    action_id=self.name,
                    action_tags=self._effective_tags(ctx),
                    target=target,
                    target_pos=data.get("target_pos"),
                    damage=sum(max(0, int(amount or 0)) for _dtype, amount in components),
                    damage_components=components,
                    defeated=this_defeated,
                )

        if not second_result.success:
            messages.append(second_result.message or "Flurry of Blows: drugi Strike nieudany.")

        if not messages:
            hit_count = int(first_hit) + int(second_hit)
            messages.append(f"Flurry of Blows: trafienia {hit_count}/2.")
        if defeated:
            messages.append("Przeciwnik pokonany.")

        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=1,
            message=" ".join(messages).strip(),
            data={
                "first": first_data,
                "second": second_data,
                "defeated": defeated,
            },
        )


class _MonkStanceEvent(ActionCostEvent):
    stance_required_status: str = ""
    stance_id: str = ""
    stance_label: str = "Monk Stance"
    stance_profile_builder = staticmethod(lambda: {})
    ui_notes: list[str] = []
    ac_circumstance_bonus: int = 0
    ac_item_bonus: int = 0

    default_tags = ["monk", "stance"]
    actions_cost = 1
    consumes_action = True
    available_in_combat = True
    available_in_exploration = False

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message=f"{self.stance_label}: brak aktora.")
        if not _has_status(actor, self.stance_required_status):
            return EventResult.cancelled(message=f"{self.stance_label}: wymaga featu {self.stance_label}.")

        _activate_stance(
            actor,
            stance_id=self.stance_id,
            stance_label=self.stance_label,
            profile=self.stance_profile_builder(),
            ui_notes=list(self.ui_notes or []),
            ac_circumstance_bonus=self.ac_circumstance_bonus,
            ac_item_bonus=self.ac_item_bonus,
        )
        notes = " ".join(self.ui_notes or [])
        msg = f"{self.stance_label}: stance aktywna."
        if notes:
            msg = f"{msg} {notes}"
        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=1,
            message=msg,
        )


@register_event
class CraneStanceEvent(_MonkStanceEvent):
    name = "crane_stance"
    stance_required_status = "crane_stance"
    stance_id = "crane_stance"
    stance_label = "Crane Stance"
    stance_profile_builder = staticmethod(_stance_profile_crane)
    ac_circumstance_bonus = 1
    ui_notes = [
        "Jump/Leap bonusy pozostają reminderem UI (manual).",
    ]


@register_event
class DragonStanceEvent(_MonkStanceEvent):
    name = "dragon_stance"
    stance_required_status = "dragon_stance"
    stance_id = "dragon_stance"
    stance_label = "Dragon Stance"
    stance_profile_builder = staticmethod(_stance_profile_dragon)
    ui_notes = [
        "Ignore first difficult terrain square pozostaje reminderem UI (manual).",
    ]


@register_event
class MountainStanceEvent(_MonkStanceEvent):
    name = "mountain_stance"
    stance_required_status = "mountain_stance"
    stance_id = "mountain_stance"
    stance_label = "Mountain Stance"
    stance_profile_builder = staticmethod(_stance_profile_mountain)
    ac_item_bonus = 4
    ui_notes = [
        "Dex cap +0, speed -5 oraz shove/trip defense pozostają reminderem UI (manual).",
    ]


@register_event
class TigerStanceEvent(_MonkStanceEvent):
    name = "tiger_stance"
    stance_required_status = "tiger_stance"
    stance_id = "tiger_stance"
    stance_label = "Tiger Stance"
    stance_profile_builder = staticmethod(_stance_profile_tiger)
    ui_notes = [
        "Step 10 feet pozostaje reminderem UI (manual).",
    ]


@register_event
class WolfStanceEvent(_MonkStanceEvent):
    name = "wolf_stance"
    stance_required_status = "wolf_stance"
    stance_id = "wolf_stance"
    stance_label = "Wolf Stance"
    stance_profile_builder = staticmethod(_stance_profile_wolf)
    ui_notes = [
        "Trip trait przy flankowaniu pozostaje reminderem UI (manual).",
    ]
