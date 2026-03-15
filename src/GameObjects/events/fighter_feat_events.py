from __future__ import annotations

from collections import OrderedDict
from typing import Any

from combat import refresh_flanking_statuses
from combat.damage_utils import remove_defeated_enemy
from combat.hp_engine import apply_damage as hp_apply_damage
from damage_types import DamageType
from GameObjects.items.inventory import get_equipped_weapons
from statuses import Status
from statuses.classes.fighter.feats.snagging_strike import apply_snagging_flat_footed

from .attack.attack_event import _select_weapon_from_equipped, _weapon_event_name
from .base import ActionCostEvent, EventContext, EventResult
from .registry import dispatch_event, list_events, register_event


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


def _equipped_melee_weapons(actor) -> list[object]:
    equipped = list(get_equipped_weapons(actor) or [])
    out: list[object] = []
    for weapon in equipped:
        if bool(getattr(weapon, "ranged", False)):
            continue
        out.append(weapon)
    return out


def _equipped_ranged_weapons(actor) -> list[object]:
    equipped = list(get_equipped_weapons(actor) or [])
    return [weapon for weapon in equipped if bool(getattr(weapon, "ranged", False))]


def _weapon_traits(weapon: object) -> set[str]:
    raw = getattr(weapon, "traits", None) or ()
    return {str(item or "").strip().lower() for item in raw}


def _weapon_hands(weapon: object) -> int:
    try:
        return 2 if int(getattr(weapon, "hands_required", 1) or 1) >= 2 else 1
    except Exception:
        return 1


def _free_hands(actor) -> int:
    occupied = 0
    for weapon in get_equipped_weapons(actor):
        occupied += _weapon_hands(weapon)
    if getattr(actor, "equipped_shield", None) is not None:
        occupied += 1
    return max(0, 2 - occupied)


def _pick_event_name_for_weapons(ctx: EventContext, weapons: list[object], *, prompt: str) -> str | None:
    if not weapons:
        return None
    chosen = _select_weapon_from_equipped(ctx, weapons)
    if chosen is None:
        return None
    event_name = _weapon_event_name(chosen)
    if not event_name:
        return None
    return str(event_name).strip().lower()


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


def _event_weapon_key(event_name: str) -> str:
    cls = list_events().get(str(event_name).strip().lower())
    if cls is None:
        return str(event_name)
    return str(getattr(cls, "action_id_base", event_name) or event_name)


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
    weapon_key = _event_weapon_key(event_name)
    weapon_counts[weapon_key] = int(weapon_counts.get(weapon_key, 0) or 0) + amount


def _prompt_double_slice_precision_choice(ctx: EventContext) -> str:
    ui = getattr(ctx.game, "ui", None)
    if ui is not None and getattr(ui, "enabled", False):
        try:
            answer = ui.prompt_choice(
                "Double Slice: do którego Strike doliczyć precision damage?",
                choices=["Pierwszy Strike", "Drugi Strike", "Brak precision"],
                source="fighter_double_slice",
            )
            normalized = str(answer or "").strip().lower()
            if "drugi" in normalized or normalized in {"2", "second"}:
                return "second"
            if "brak" in normalized or normalized in {"0", "none", "no"}:
                return "none"
        except Exception:
            pass
    return "first"


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


def _resolve_combined_damage_type(
    damage_components: list[tuple[str, int]],
    *,
    preferred: str | None = None,
) -> str:
    if preferred:
        normalized = str(preferred or "").strip().lower()
        if normalized:
            return normalized
    for dmg_type, amount in damage_components:
        try:
            value = int(amount or 0)
        except Exception:
            value = 0
        if value > 0:
            normalized = str(dmg_type or "").strip().lower()
            if normalized:
                return normalized
    return DamageType.NORMAL.value


def _apply_merged_damage(
    target,
    damage_components: list[tuple[str, int]],
    *,
    preferred_damage_type: str | None = None,
) -> bool:
    total_damage = sum(max(0, int(amount or 0)) for _dmg_type, amount in damage_components)
    if total_damage <= 0:
        return False
    combined_damage_type = _resolve_combined_damage_type(damage_components, preferred=preferred_damage_type)

    applier = getattr(target, "apply_damage", None)
    if callable(applier):
        try:
            _, defeated = applier(total_damage, combined_damage_type)
            return bool(defeated)
        except Exception:
            pass
    info = hp_apply_damage(target, total_damage, combined_damage_type, source="fighter:double_slice")
    return bool((info or {}).get("defeated", False))


def _remove_defeated_target(game, target, target_pos) -> None:
    pos = target_pos if isinstance(target_pos, tuple) else getattr(target, "position", None)
    if target in getattr(game, "enemies", []):
        try:
            remove_defeated_enemy(game, target, position=pos, source="fighter_feat")
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


def _is_flat_footed_target(target) -> bool:
    if target is None:
        return False
    has_status = getattr(target, "has_status", None)
    if callable(has_status):
        try:
            return bool(has_status("flat_footed"))
        except Exception:
            return False
    for status in getattr(target, "statuses", []) or []:
        if getattr(status, "id", None) == "flat_footed" or status == "flat_footed":
            return True
    return False


def _add_precision_bonus(components: list[tuple[str, int]], bonus: int) -> list[tuple[str, int]]:
    if bonus <= 0:
        return list(components)
    out: list[tuple[str, int]] = []
    applied = False
    for dmg_type, amount in components:
        try:
            value = int(amount or 0)
        except Exception:
            value = 0
        if not applied:
            out.append((str(dmg_type), value + int(bonus)))
            applied = True
        else:
            out.append((str(dmg_type), value))
    if not out:
        out.append(("precision", int(bonus)))
    return out


@register_event
class PointBlankShotEvent(ActionCostEvent):
    name = "point_blank_shot"
    default_tags = ["fighter", "stance", "open"]
    actions_cost = 1
    consumes_action = True
    available_in_combat = True
    available_in_exploration = False

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Point-Blank Shot: brak aktora.")
        if not _has_status(actor, "point_blank_shot"):
            return EventResult.cancelled(message="Point-Blank Shot: wymaga featu Point-Blank Shot.")
        if not _equipped_ranged_weapons(actor):
            return EventResult.cancelled(message="Point-Blank Shot: wymaga aktywnej broni dystansowej.")

        remover = getattr(actor, "remove_status", None)
        if callable(remover):
            try:
                remover("point_blank_shot_stance")
            except Exception:
                pass
        adder = getattr(actor, "add_status", None)
        if callable(adder):
            adder(
                Status(
                    id="point_blank_shot_stance",
                    label="Point-Blank Shot (Stance)",
                    data={"effect_tags": ["stance", "fighter"]},
                )
            )
        return EventResult(success=True, consumed_action=True, actions_spent=1, message="Point-Blank Shot: stance aktywna.")


@register_event
class PowerAttackEvent(ActionCostEvent):
    name = "power_attack"
    default_tags = ["fighter", "attack_melee", "flourish"]
    actions_cost = 2
    consumes_action = True
    available_in_combat = True
    available_in_exploration = False

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Power Attack: brak aktora.")
        if not _has_status(actor, "power_attack"):
            return EventResult.cancelled(message="Power Attack: wymaga featu Power Attack.")

        melee_weapons = [weapon for weapon in _equipped_melee_weapons(actor) if _weapon_hands(weapon) >= 1]
        if not melee_weapons:
            return EventResult.cancelled(message="Power Attack: wymaga aktywnej broni melee.")

        event_name = _pick_event_name_for_weapons(ctx, melee_weapons, prompt="Power Attack: wybierz broń melee")
        if not event_name:
            return EventResult.cancelled(message="Power Attack: nie wybrano ataku melee.")

        level = int(getattr(actor, "level", 1) or 1)
        if level >= 18:
            extra_dice = 3
        elif level >= 10:
            extra_dice = 2
        else:
            extra_dice = 1

        metadata = dict(ctx.metadata or {})
        metadata.update(
            {
                "power_attack_extra_dice": extra_dice,
                "map_attack_count": 2,
            }
        )
        strike_result = dispatch_event(
            event_name,
            EventContext(game=ctx.game, actor=actor, tags=list(ctx.tags or []), metadata=metadata),
        )
        if not strike_result.success:
            return EventResult.cancelled(message=strike_result.message or "Power Attack: atak nieudany.")
        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=2,
            message=strike_result.message or "Power Attack wykonany.",
            data=dict(strike_result.data or {}),
        )


@register_event
class ExactingStrikeEvent(ActionCostEvent):
    name = "exacting_strike"
    default_tags = ["fighter", "attack", "press"]
    actions_cost = 1
    consumes_action = True
    available_in_combat = True
    available_in_exploration = False

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Exacting Strike: brak aktora.")
        if not _has_status(actor, "exacting_strike"):
            return EventResult.cancelled(message="Exacting Strike: wymaga featu Exacting Strike.")
        if _current_attacks_this_turn(ctx, actor) < 1:
            return EventResult.cancelled(message="Exacting Strike (Press): wymaga co najmniej jednego ataku w tej turze.")

        metadata = dict(ctx.metadata or {})
        metadata.update({"exacting_strike_press": True})
        strike_result = dispatch_event(
            "attack",
            EventContext(game=ctx.game, actor=actor, tags=list(ctx.tags or []), metadata=metadata),
        )
        if not strike_result.success:
            return EventResult.cancelled(message=strike_result.message or "Exacting Strike: atak nieudany.")
        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=1,
            message=strike_result.message or "Exacting Strike wykonany.",
            data=dict(strike_result.data or {}),
        )


@register_event
class SnaggingStrikeEvent(ActionCostEvent):
    name = "snagging_strike"
    default_tags = ["fighter", "attack_melee"]
    actions_cost = 1
    consumes_action = True
    available_in_combat = True
    available_in_exploration = False

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Snagging Strike: brak aktora.")
        if not _has_status(actor, "snagging_strike"):
            return EventResult.cancelled(message="Snagging Strike: wymaga featu Snagging Strike.")
        if _free_hands(actor) < 1:
            return EventResult.cancelled(message="Snagging Strike: wymaga jednej wolnej ręki.")

        melee_weapons = _equipped_melee_weapons(actor)
        if not melee_weapons:
            return EventResult.cancelled(message="Snagging Strike: wymaga aktywnego ataku melee.")
        event_name = _pick_event_name_for_weapons(ctx, melee_weapons, prompt="Snagging Strike: wybierz broń")
        if not event_name:
            return EventResult.cancelled(message="Snagging Strike: nie wybrano ataku melee.")

        strike_result = dispatch_event(
            event_name,
            EventContext(game=ctx.game, actor=actor, tags=list(ctx.tags or []), metadata=dict(ctx.metadata or {})),
        )
        if not strike_result.success:
            return EventResult.cancelled(message=strike_result.message or "Snagging Strike: atak nieudany.")

        hit = bool((strike_result.data or {}).get("hit", False))
        target = (strike_result.data or {}).get("target")
        if hit and target is not None:
            try:
                apply_snagging_flat_footed(
                    target,
                    source_actor=actor,
                    source_turns_left=1,
                    reach=1,
                )
            except Exception:
                pass
        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=1,
            message=strike_result.message or "Snagging Strike wykonany.",
            data=dict(strike_result.data or {}),
        )


@register_event
class DoubleSliceEvent(ActionCostEvent):
    name = "double_slice"
    default_tags = ["fighter", "attack_melee"]
    actions_cost = 2
    consumes_action = True
    available_in_combat = True
    available_in_exploration = False

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Double Slice: brak aktora.")
        if not _has_status(actor, "double_slice"):
            return EventResult.cancelled(message="Double Slice: wymaga featu Double Slice.")

        equipped = _equipped_melee_weapons(actor)
        one_h_melee = [weapon for weapon in equipped if _weapon_hands(weapon) == 1]
        if len(one_h_melee) < 2:
            return EventResult.cancelled(message="Double Slice: wymagane dwie bronie melee 1H.")

        first_weapon = one_h_melee[0]
        second_weapon = one_h_melee[1]
        first_event = _weapon_event_name(first_weapon)
        second_event = _weapon_event_name(second_weapon)
        if not first_event or not second_event:
            return EventResult.cancelled(message="Double Slice: brak eventu ataku dla aktywnych broni.")

        initial_attacks = _current_attacks_this_turn(ctx, actor)
        first_traits = _weapon_traits(first_weapon)
        second_traits = _weapon_traits(second_weapon)

        precision_choice = "first"
        if ("backstabber" in first_traits) or ("backstabber" in second_traits):
            precision_choice = _prompt_double_slice_precision_choice(ctx)

        first_result = dispatch_event(
            str(first_event),
            EventContext(
                game=ctx.game,
                actor=actor,
                tags=list(ctx.tags or []),
                metadata={
                    **dict(ctx.metadata or {}),
                    "fixed_attacks_this_turn": initial_attacks,
                    "roll_only": True,
                    "allow_auto_precision_bonus": False,
                },
            ),
        )
        if not first_result.success:
            return EventResult.cancelled(message=first_result.message or "Double Slice: pierwszy Strike nieudany.")

        first_target = (first_result.data or {}).get("target")
        first_target_pos = (first_result.data or {}).get("target_pos")

        if first_target is None:
            return EventResult(
                success=True,
                consumed_action=True,
                actions_spent=2,
                message=first_result.message or "Double Slice: pierwszy Strike wykonany.",
                data={"first": dict(first_result.data or {}), "second": {}},
            )

        second_penalty = 2 if "agile" not in _weapon_traits(second_weapon) else 0
        second_result = dispatch_event(
            str(second_event),
            EventContext(
                game=ctx.game,
                actor=actor,
                tags=list(ctx.tags or []),
                metadata={
                    **dict(ctx.metadata or {}),
                    "fixed_attacks_this_turn": initial_attacks,
                    "suppress_attack_record": True,
                    "forced_target": first_target,
                    "forced_target_pos": first_target_pos,
                    "attack_roll_penalty": second_penalty,
                    "attack_roll_penalty_type": "status",
                    "roll_only": True,
                    "allow_auto_precision_bonus": False,
                },
            ),
        )
        if second_result.success:
            _bump_attack_state(ctx, actor, event_name=str(second_event), count=1)

        first_hit = bool((first_result.data or {}).get("hit", False))
        second_hit = bool((second_result.data or {}).get("hit", False))
        hit_count = int(first_hit) + int(second_hit)

        target = (first_result.data or {}).get("target") or (second_result.data or {}).get("target")
        target_pos = (first_result.data or {}).get("target_pos") or (second_result.data or {}).get("target_pos")
        first_components = list((first_result.data or {}).get("damage_components") or []) if first_hit else []
        second_components = list((second_result.data or {}).get("damage_components") or []) if second_hit else []
        first_damage_type = str((first_components[0][0] if first_components else "") or "").strip().lower()
        second_damage_type = str((second_components[0][0] if second_components else "") or "").strip().lower()
        preferred_damage_type = first_damage_type or second_damage_type or DamageType.NORMAL.value
        # Precision damage w Double Slice liczymy maksymalnie raz (wybór przez UI).
        if _is_flat_footed_target(target):
            if precision_choice == "first" and first_hit and ("backstabber" in first_traits):
                first_components = _add_precision_bonus(first_components, 1)
            elif precision_choice == "second" and second_hit and ("backstabber" in second_traits):
                second_components = _add_precision_bonus(second_components, 1)
        merged_components = _merge_damage_components(first_components, second_components)

        defeated = False
        if target is not None and merged_components:
            defeated = _apply_merged_damage(
                target,
                merged_components,
                preferred_damage_type=preferred_damage_type,
            )
            if defeated:
                _remove_defeated_target(ctx.game, target, target_pos)

            try:
                refresh_flanking_statuses(ctx.game)
            except Exception:
                pass

            ctx.game.events.safe_emit_action(
                actor=actor,
                action_id=self.name,
                action_tags=self._effective_tags(ctx),
                target=target,
                target_pos=target_pos,
                damage=sum(max(0, int(amount or 0)) for _dtype, amount in merged_components),
                damage_components=merged_components,
                defeated=defeated,
            )

        summary = f"Double Slice: trafienia {hit_count}/2."
        if defeated:
            summary = f"{summary} Przeciwnik pokonany."

        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=2,
            message=summary,
            data={
                "first": dict(first_result.data or {}),
                "second": dict(second_result.data or {}),
                "damage_components": merged_components,
                "defeated": defeated,
                "target": target,
                "target_pos": target_pos,
                "precision_choice": precision_choice,
            },
        )
