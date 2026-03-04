from __future__ import annotations

from board import consts
from GameObjects.items.inventory import get_equipped_weapons

from .attack.attack_event import _weapon_event_name
from .attack.basic_melee_attack_event import BasicMeleeAttackEvent
from .base import ActionCostEvent, EventContext, EventResult
from .demoralize_utils import perform_demoralize
from .registry import dispatch_event, register_event


def _actor_id(actor) -> str:
    return str(getattr(actor, "object_id", None) or getattr(actor, "name", None) or id(actor))


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


def _weapon_hands(weapon: object) -> int:
    try:
        return 2 if int(getattr(weapon, "hands_required", 1) or 1) >= 2 else 1
    except Exception:
        return 1


def _equipped_melee_weapons_1h(actor) -> list[object]:
    equipped = list(get_equipped_weapons(actor) or [])
    out: list[object] = []
    for weapon in equipped:
        if bool(getattr(weapon, "ranged", False)):
            continue
        if _weapon_hands(weapon) != 1:
            continue
        out.append(weapon)
    return out


def _pick_adjacent_target(ctx: EventContext, actor):
    actor_pos = getattr(actor, "position", None)
    if actor_pos is None:
        return None, None
    candidates = BasicMeleeAttackEvent._adjacent_enemies(ctx.game, actor_pos)
    if not candidates:
        return None, None
    if len(candidates) == 1:
        return candidates[0]
    positions = [pos for _enemy, pos in candidates]
    try:
        try:
            ctx.game.conn.set_leds(positions, consts.INTERACT_FIELD_RGB)
        except Exception:
            pass
        selected = ctx.game.conn.scan_board(positions)
    finally:
        try:
            ctx.game.conn.leds_off()
        except Exception:
            pass
    for enemy, pos in candidates:
        if pos == selected:
            return enemy, pos
    return None, None


def try_trigger_youre_next(ctx: EventContext, actor, *, defeated_target=None) -> dict[str, object] | None:
    if actor is None or not _has_status(actor, "youre_next"):
        return None
    excluded = []
    if defeated_target is not None:
        excluded.append(_actor_id(defeated_target))
    payload = perform_demoralize(
        ctx,
        actor,
        extra_bonus=2,
        source_action="youre_next",
        forced_target=None,
        excluded_target_ids=excluded,
        enforce_combat_immunity=True,
    )
    if not bool(payload.get("success", False)):
        message = str(payload.get("message", "") or "").strip()
        if message:
            try:
                ctx.game.ui_log(f"You're Next: {message}")
            except Exception:
                pass
        return payload
    try:
        ctx.game.events.safe_emit_action(
            actor=actor,
            action_id="youre_next_trigger",
            action_tags=["rogue", "youre_next", "demoralize", "fear", "emotion", "mental"],
            target=payload.get("target"),
            target_pos=payload.get("target_pos"),
            outcome=payload.get("outcome"),
            frightened=payload.get("frightened", 0),
        )
    except Exception:
        pass
    return payload


@register_event
class TwinFeintEvent(ActionCostEvent):
    name = "twin_feint"
    default_tags = ["rogue", "attack_melee", "attack", "feint"]
    actions_cost = 1
    consumes_action = True
    available_in_combat = True
    available_in_exploration = False

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Twin Feint: brak aktora.")
        if not _has_status(actor, "twin_feint"):
            return EventResult.cancelled(message="Twin Feint: wymaga featu Twin Feint.")

        melee_weapons = _equipped_melee_weapons_1h(actor)
        if len(melee_weapons) < 2:
            return EventResult.cancelled(message="Twin Feint: wymagane 2 bronie melee 1H.")

        first_weapon = melee_weapons[0]
        second_weapon = melee_weapons[1]
        first_event = _weapon_event_name(first_weapon)
        second_event = _weapon_event_name(second_weapon)
        if not first_event or not second_event:
            return EventResult.cancelled(message="Twin Feint: brak eventu Strike dla aktywnej broni.")

        target, target_pos = _pick_adjacent_target(ctx, actor)
        if target is None:
            return EventResult.cancelled(message="Twin Feint: brak celu w zasięgu.")

        base_metadata = dict(ctx.metadata or {})
        first_result = dispatch_event(
            str(first_event),
            EventContext(
                game=ctx.game,
                actor=actor,
                tags=list(ctx.tags or []),
                metadata={
                    **base_metadata,
                    "forced_target": target,
                    "forced_target_pos": target_pos,
                },
            ),
        )

        second_result = None
        if getattr(target, "position", None) is not None:
            second_result = dispatch_event(
                str(second_event),
                EventContext(
                    game=ctx.game,
                    actor=actor,
                    tags=list(ctx.tags or []),
                    metadata={
                        **base_metadata,
                        "forced_target": target,
                        "forced_target_pos": target_pos,
                        "force_flat_footed": True,
                        "force_flat_footed_source": "twin_feint",
                    },
                ),
            )

        first_data = dict((first_result.data or {}) if isinstance(first_result, EventResult) else {})
        second_data = dict((second_result.data or {}) if isinstance(second_result, EventResult) else {})
        hit_count = int(bool(first_data.get("hit", False))) + int(bool(second_data.get("hit", False)))
        defeated = bool(first_data.get("defeated", False)) or bool(second_data.get("defeated", False))

        try:
            ctx.game.events.safe_emit_action(
                actor=actor,
                action_id=self.name,
                action_tags=self._effective_tags(ctx),
                target=target,
                target_pos=target_pos,
                first_hit=bool(first_data.get("hit", False)),
                second_hit=bool(second_data.get("hit", False)),
                defeated=defeated,
            )
        except Exception:
            pass

        msg = f"Twin Feint: trafienia {hit_count}/2."
        if defeated:
            msg += " Przeciwnik pokonany."
        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=1,
            message=msg,
            data={"first": first_data, "second": second_data, "defeated": defeated},
        )

