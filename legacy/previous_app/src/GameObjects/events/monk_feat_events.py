from __future__ import annotations

from collections import OrderedDict

from bonuses import BonusEffect, BonusType
from combat.damage_utils import remove_defeated_enemy
from statuses import SpeedPenaltyStatus, Status
from statuses.check_effects import CheckEffect

from .attack.basic_melee_attack_event import BasicMeleeAttackEvent
from .base import ActionCostEvent, EventContext, EventResult
from .registry import dispatch_event, register_event


MONK_STANCE_ACTIVE_STATUS_ID = "monk_stance_active"
MONK_STANCE_LOCK_STATUS_ID = "monk_stance_lock"
MONK_STANCE_AC_CIRC_SOURCE = "monk_stance:ac:circumstance"
MONK_STANCE_AC_ITEM_SOURCE = "monk_stance:ac:item"
MONK_STANCE_AC_DEX_SOURCE = "monk_stance:ac:dex_cap"
MONK_STANCE_SPEED_SOURCE = "monk_stance:speed"
MONK_STANCE_DEFENSE_SOURCE = "monk_stance:defense"


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


def _actor_source_id(actor) -> str | None:
    if actor is None:
        return None
    raw = str(getattr(actor, "object_id", None) or getattr(actor, "name", None) or "").strip()
    return raw or None


def _status_value(actor, status_id: str, key: str, default=None):
    getter = getattr(actor, "get_status_data", None)
    if callable(getter):
        try:
            return getter(status_id, key, default)
        except Exception:
            return default
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) != status_id:
            continue
        data = getattr(status, "data", None) or {}
        return data.get(key, default)
    return default


def _dex_modifier(actor) -> int:
    if actor is None:
        return 0
    mods = getattr(actor, "ability_modifiers", None)
    if isinstance(mods, dict):
        try:
            return int(mods.get("dexterity", 0) or 0)
        except Exception:
            return 0
    for attr in ("dex_mod", "dexterity_mod"):
        raw = getattr(actor, attr, None)
        if raw is None:
            continue
        try:
            return int(raw or 0)
        except Exception:
            return 0
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
    weapon_key = str(event_name or "unarmed").strip().lower().replace("-", "_").replace(" ", "_") or "unarmed"
    if not weapon_key.startswith("attack_"):
        weapon_key = f"attack_{weapon_key}"
    weapon_counts[weapon_key] = int(weapon_counts.get(weapon_key, 0) or 0) + amount


def _normalized_trait_tags(item) -> set[str]:
    return {
        str(tag or "").strip().lower().replace("-", "_").replace(" ", "_")
        for tag in (getattr(item, "traits", None) or ())
        if str(tag or "").strip()
    }


def _resolve_monastic_weapon(actor, metadata: dict | None = None):
    if actor is None or not _has_status(actor, "monastic_weaponry") or _has_status(actor, MONK_STANCE_ACTIVE_STATUS_ID):
        return None
    try:
        from GameObjects.items.inventory import get_equipped_weapons
    except Exception:
        return None

    equipped = [
        item
        for item in list(get_equipped_weapons(actor) or [])
        if "monk" in _normalized_trait_tags(item) and not bool(getattr(item, "ranged", False))
    ]
    if not equipped:
        return None

    payload = dict(metadata or {})
    selected = payload.get("selected_weapon")
    if selected in equipped:
        return selected

    selected_iid = str(payload.get("selected_weapon_instance_id", "") or "").strip()
    if selected_iid:
        for item in equipped:
            if str(getattr(item, "instance_id", "") or "").strip() == selected_iid:
                return item

    return equipped[0]


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


def _remove_statuses_by_source_prefix(actor, prefix: str) -> None:
    if actor is None:
        return
    statuses = getattr(actor, "statuses", None)
    if not isinstance(statuses, list):
        return
    actor.statuses = [
        status
        for status in statuses
        if not str(getattr(status, "source", "") or "").startswith(prefix)
    ]


def _clear_monk_stance_effects(actor) -> None:
    _remove_statuses(actor, MONK_STANCE_ACTIVE_STATUS_ID)
    _remove_statuses_by_source_prefix(actor, "monk_stance:")
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
        try:
            remover(MONK_STANCE_AC_DEX_SOURCE)
        except Exception:
            pass
    try:
        from actions.move_utils import reset_turn_movement_runtime

        reset_turn_movement_runtime(actor)
    except Exception:
        pass


def _add_ac_bonus(actor, *, source: str, bonus_type: BonusType, value: int, label: str, is_penalty: bool = False) -> None:
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
        is_penalty=bool(is_penalty),
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
    status_data: dict | None = None,
    extra_statuses: list[Status] | None = None,
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
                    "expire_on_combat_end": True,
                    **dict(status_data or {}),
                },
            )
        )
        for status in list(extra_statuses or []):
            try:
                adder(status)
            except Exception:
                pass

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
    try:
        from actions.move_utils import reset_turn_movement_runtime

        reset_turn_movement_runtime(actor)
    except Exception:
        pass


def _add_mountain_runtime_effects(actor) -> list[Status]:
    dex_penalty = max(0, _dex_modifier(actor))
    if dex_penalty > 0:
        _add_ac_bonus(
            actor,
            source=MONK_STANCE_AC_DEX_SOURCE,
            bonus_type=BonusType.CIRCUMSTANCE,
            value=dex_penalty,
            label="Mountain Stance: Dex cap +0",
            is_penalty=True,
        )

    return [
        SpeedPenaltyStatus(
            penalty_feet=5,
            source=MONK_STANCE_SPEED_SOURCE,
            label="Mountain Stance: Speed -5 ft",
        ),
        Status(
            id="monk_mountain_defense",
            label="Mountain Stance: Anti-Trip/Shove",
            source=MONK_STANCE_DEFENSE_SOURCE,
            data={"effect_tags": ["stance", "monk"]},
            check_effects=(
                CheckEffect(
                    applies_to="target",
                    skills=("reflex",),
                    tags_required=("trip",),
                    bonus_effects=(
                        BonusEffect(
                            type=BonusType.CIRCUMSTANCE,
                            value=2,
                            tag="reflex",
                            source=MONK_STANCE_DEFENSE_SOURCE,
                            label="Mountain Stance",
                        ),
                    ),
                ),
                CheckEffect(
                    applies_to="target",
                    skills=("fortitude",),
                    tags_required=("shove",),
                    bonus_effects=(
                        BonusEffect(
                            type=BonusType.CIRCUMSTANCE,
                            value=2,
                            tag="fortitude",
                            source=MONK_STANCE_DEFENSE_SOURCE,
                            label="Mountain Stance",
                        ),
                    ),
                ),
            ),
        ),
    ]


def _add_stance_lock(actor, stance_label: str) -> None:
    adder = getattr(actor, "add_status", None)
    if not callable(adder):
        return
    adder(
        Status(
            id=MONK_STANCE_LOCK_STATUS_ID,
            label="Stance Lock",
            source="monk_stance:lock",
            data={
                "effect_tags": ["stance", "monk"],
                "source_id": _actor_source_id(actor),
                "source_turns_left": 1,
                "expire_on_combat_end": True,
                "stance_label": stance_label,
            },
        )
    )


def _refresh_actor_ui(ctx: EventContext, actor) -> None:
    ui_hero = getattr(ctx.game, "ui_hero", None)
    if callable(ui_hero) and actor in getattr(ctx.game, "heroes", []):
        try:
            ui_hero(actor, note="Monk stance aktywna")
        except Exception:
            pass
    ui_active_actor = getattr(ctx.game, "ui_active_actor", None)
    if callable(ui_active_actor):
        try:
            ui_active_actor(actor)
        except Exception:
            pass


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
        monastic_weapon = _resolve_monastic_weapon(actor, base_metadata)
        attack_event_name = "unarmed"
        attack_state_key = "unarmed"
        if monastic_weapon is not None:
            try:
                from GameObjects.items.weapon import normalize_weapon_id
            except Exception:
                normalize_weapon_id = lambda value: str(value or "").strip().lower().replace("-", "_").replace(" ", "_")  # type: ignore[assignment]
            attack_event_name = "attack"
            attack_state_key = str(
                normalize_weapon_id(getattr(monastic_weapon, "item_id", None))
                or getattr(monastic_weapon, "item_id", "")
                or "unarmed"
            ).strip().lower().replace("-", "_").replace(" ", "_") or "unarmed"

        first_metadata = {
            **base_metadata,
            "fixed_attacks_this_turn": initial_attacks,
            "suppress_attack_record": True,
            "roll_only": True,
        }
        second_metadata = {
            **base_metadata,
            "fixed_attacks_this_turn": initial_attacks + 1,
            "suppress_attack_record": True,
            "roll_only": True,
        }
        if monastic_weapon is not None:
            selected_iid = str(getattr(monastic_weapon, "instance_id", "") or "")
            selected_item_id = str(getattr(monastic_weapon, "item_id", "") or "")
            for payload in (first_metadata, second_metadata):
                payload["selected_weapon"] = monastic_weapon
                payload["selected_weapon_instance_id"] = selected_iid
                payload["weapon_id"] = selected_item_id

        first_result = dispatch_event(
            attack_event_name,
            EventContext(
                game=ctx.game,
                actor=actor,
                tags=list(ctx.tags or []),
                metadata=first_metadata,
            ),
        )
        if not first_result.success:
            return EventResult.cancelled(message=first_result.message or "Flurry of Blows: pierwszy Strike nieudany.")

        second_result = dispatch_event(
            attack_event_name,
            EventContext(
                game=ctx.game,
                actor=actor,
                tags=list(ctx.tags or []),
                metadata=second_metadata,
            ),
        )

        _bump_attack_state(ctx, actor, event_name=attack_state_key, count=2)

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
    stance_status_data: dict[str, object] = {}
    extra_status_factories: tuple = ()
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
        if _has_status(actor, MONK_STANCE_LOCK_STATUS_ID):
            return EventResult.cancelled(message=f"{self.stance_label}: po wejściu w stance nie możesz użyć kolejnej stance action do początku następnej tury.")

        _activate_stance(
            actor,
            stance_id=self.stance_id,
            stance_label=self.stance_label,
            profile=self.stance_profile_builder(),
            ui_notes=list(self.ui_notes or []),
            ac_circumstance_bonus=self.ac_circumstance_bonus,
            ac_item_bonus=self.ac_item_bonus,
            status_data=dict(self.stance_status_data or {}),
            extra_statuses=[],
        )
        adder = getattr(actor, "add_status", None)
        for factory in tuple(self.extra_status_factories or ()):
            if not callable(factory):
                continue
            try:
                built = factory(actor)
            except Exception:
                continue
            if isinstance(built, Status):
                if callable(adder):
                    try:
                        adder(built)
                    except Exception:
                        pass
                continue
            if isinstance(built, list) and callable(adder):
                for item in built:
                    if not isinstance(item, Status):
                        continue
                    try:
                        adder(item)
                    except Exception:
                        continue
        _add_stance_lock(actor, self.stance_label)
        _refresh_actor_ui(ctx, actor)
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
    stance_status_data = {"leap_extra_squares": 1}
    ac_circumstance_bonus = 1
    ui_notes = [
        "Leap ma zwiększony zasięg o 1 pole, a stance daje +1 circumstance AC.",
    ]


@register_event
class DragonStanceEvent(_MonkStanceEvent):
    name = "dragon_stance"
    stance_required_status = "dragon_stance"
    stance_id = "dragon_stance"
    stance_label = "Dragon Stance"
    stance_profile_builder = staticmethod(_stance_profile_dragon)
    stance_status_data = {"ignore_difficult_terrain_squares_each_turn": 1}
    ui_notes = [
        "Pierwsze pole trudnego terenu w każdej twojej turze nie zwiększa kosztu ruchu.",
    ]


@register_event
class MountainStanceEvent(_MonkStanceEvent):
    name = "mountain_stance"
    stance_required_status = "mountain_stance"
    stance_id = "mountain_stance"
    stance_label = "Mountain Stance"
    stance_profile_builder = staticmethod(_stance_profile_mountain)
    extra_status_factories = (_add_mountain_runtime_effects,)
    ac_item_bonus = 4
    ui_notes = [
        "Dex cap +0, Speed -5 ft oraz +2 circumstance vs Trip/Shove działają automatycznie.",
    ]


@register_event
class TigerStanceEvent(_MonkStanceEvent):
    name = "tiger_stance"
    stance_required_status = "tiger_stance"
    stance_id = "tiger_stance"
    stance_label = "Tiger Stance"
    stance_profile_builder = staticmethod(_stance_profile_tiger)
    stance_status_data = {"step_extra_feet": 5, "step_min_speed_feet": 20}
    ui_notes = [
        "Jeśli twoja Speed wynosi co najmniej 20 ft, możesz wykonać Step na 10 ft.",
    ]


@register_event
class WolfStanceEvent(_MonkStanceEvent):
    name = "wolf_stance"
    stance_required_status = "wolf_stance"
    stance_id = "wolf_stance"
    stance_label = "Wolf Stance"
    stance_profile_builder = staticmethod(_stance_profile_wolf)
    ui_notes = [
        "Atakujesz profilem Wolf Jaw; trait Trip przy flankowaniu pozostaje ograniczony do obecnego runtime Trip.",
    ]
