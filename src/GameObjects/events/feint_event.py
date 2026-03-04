from __future__ import annotations

from board import consts
from skills import Skill
from statuses import Status

from GameObjects.interactions_mixin import compute_skill_modifier_with_sources, resolve_skill_check_with_sources

from .base import ActionCostEvent, EventContext, EventResult, mapping_setdefault_actor
from .registry import register_event


def _actor_id(actor) -> str:
    return str(getattr(actor, "object_id", None) or getattr(actor, "name", None) or id(actor))


def _has_status(actor, status_id: str) -> bool:
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


def _rogue_racket(actor) -> str | None:
    if actor is None:
        return None
    getter = getattr(actor, "get_status_data", None)
    if callable(getter):
        try:
            value = getter("rogue", "rogue_racket", None)
            raw = str(value or "").strip().lower()
            if raw:
                return raw
            setup = getter("rogue", "rogue_setup", {})
            if isinstance(setup, dict):
                raw = str(setup.get("racket", "") or "").strip().lower()
                if raw:
                    return raw
        except Exception:
            pass
    raw = str(getattr(actor, "rogue_racket", "") or "").strip().lower()
    return raw or None


def _iter_adjacent_targets(ctx: EventContext, actor):
    board = getattr(ctx.game, "board", None)
    actor_pos = getattr(actor, "position", None)
    if board is None or actor_pos is None:
        return []
    heroes = list(getattr(ctx.game, "heroes", []) or [])
    enemies = list(getattr(ctx.game, "enemies", []) or [])
    pool = enemies if actor in heroes else heroes
    neighbors = set(board.get_neighbors(actor_pos, include_position=False, diagonal=True))
    out: list[tuple[object, tuple[int, int]]] = []
    for target in pool:
        pos = getattr(target, "position", None)
        if pos is None or pos not in neighbors:
            continue
        out.append((target, pos))
    return out


def _pick_target(ctx: EventContext, candidates: list[tuple[object, tuple[int, int]]]):
    if not candidates:
        return None, None
    if len(candidates) == 1:
        return candidates[0]
    positions = [pos for _target, pos in candidates]
    try:
        try:
            ctx.game.conn.set_leds(positions, consts.INTERACT_FIELD_RGB)
        except Exception:
            pass
        choice = ctx.game.conn.scan_board(positions)
    finally:
        try:
            ctx.game.conn.leds_off()
        except Exception:
            pass
    for target, pos in candidates:
        if pos == choice:
            return target, pos
    return None, None


def _can_be_feinted(target) -> tuple[bool, str]:
    if target is None:
        return False, "Brak celu."
    if bool(getattr(target, "cannot_be_feinted", False)):
        return False, "Ten cel ignoruje próby Feint."
    if _has_status(target, "mindless"):
        return False, "Feint: cel bez umysłu nie daje się zwieść."
    if _has_status(target, "unconscious"):
        return False, "Feint: cel jest nieprzytomny."
    if _has_status(target, "blind") and _has_status(target, "deafened"):
        return False, "Feint: cel nie widzi i nie słyszy twoich zwodów."
    return True, ""


def _upsert_feint_flat_footed(
    target,
    *,
    source_id: str,
    source_turns_left: int,
    attacker_id: str | None,
    melee_only: bool,
) -> None:
    statuses = getattr(target, "statuses", None)
    if not isinstance(statuses, list):
        return
    filtered = []
    for status in statuses:
        sid = getattr(status, "id", status)
        data = getattr(status, "data", None) or {}
        if sid != "feint_flat_footed":
            filtered.append(status)
            continue
        if str(data.get("source_id", "") or "") != str(source_id):
            filtered.append(status)
            continue
        if str(data.get("attacker_id", "") or "") != str(attacker_id or ""):
            filtered.append(status)
            continue
        if bool(data.get("melee_only", False)) != bool(melee_only):
            filtered.append(status)
            continue
    filtered.append(
        Status(
            id="feint_flat_footed",
            label="Flat-Footed (Feint)",
            data={
                "source_id": str(source_id),
                "source_turns_left": int(source_turns_left),
                "attacker_id": str(attacker_id) if attacker_id else None,
                "melee_only": bool(melee_only),
                "ac_penalty": 2,
                "flat_footed_source": "feint",
            },
        )
    )
    try:
        target.statuses = filtered
    except Exception:
        pass


def _set_feint_next_attack(ctx: EventContext, actor, target) -> None:
    state = {}
    if getattr(ctx, "in_combat", False):
        attack_state = getattr(getattr(ctx.game, "state", None), "attack_state", None)
        if isinstance(attack_state, dict):
            state = mapping_setdefault_actor(attack_state, actor, dict)
    if not isinstance(state, dict):
        state = {}
    state["feint_next_attack_target_id"] = _actor_id(target)
    state["feint_next_attack_melee_only"] = True
    state["feint_next_attack_source"] = "feint"
    state["feint_next_attack_source_id"] = _actor_id(actor)
    if not getattr(ctx, "in_combat", False):
        try:
            setattr(actor, "_attack_trait_state", state)
        except Exception:
            pass


def _perception_dc(ctx: EventContext, actor, target) -> int:
    try:
        base_perception = int(getattr(target, "perception_bonus", 0) or 0)
    except Exception:
        base_perception = 0
    modifier, breakdown, _notes = compute_skill_modifier_with_sources(
        skill_id=Skill.PERCEPTION.value,
        actor=target,
        target=actor,
        tags=["feint", "perception", "mental", "manipulate"],
        base_modifier=base_perception,
    )
    if breakdown:
        try:
            ctx.game.ui_log(f"Feint: modyfikatory Perception DC celu: {', '.join(breakdown)}.")
        except Exception:
            pass
    return 10 + int(modifier)


@register_event
class FeintEvent(ActionCostEvent):
    name = "feint"
    default_tags = ["feint", "mental", "manipulate", "skill", "deception"]
    actions_cost = 1
    consumes_action = True
    available_in_combat = True
    available_in_exploration = False

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Feint: brak aktora na planszy.")

        candidates = _iter_adjacent_targets(ctx, actor)
        target, target_pos = _pick_target(ctx, candidates)
        if target is None:
            return EventResult.cancelled(message="Feint: brak celu w zasięgu.")

        can_feint, reason = _can_be_feinted(target)
        if not can_feint:
            return EventResult.cancelled(message=reason or "Feint nie działa na ten cel.")

        dc = _perception_dc(ctx, actor, target)
        try:
            base_deception = int(getattr(actor, "deception_bonus", 0) or 0)
        except Exception:
            base_deception = 0
        result = resolve_skill_check_with_sources(
            skill_id=Skill.DECEPTION.value,
            dc=dc,
            actor=actor,
            target=target,
            tags=["feint", "mental", "manipulate", Skill.DECEPTION.value],
            game=ctx.game,
            base_modifier=base_deception,
            apply_modifiers=True,
        )
        outcome = str(getattr(result, "outcome", "failure") or "failure")
        actor_uid = _actor_id(actor)
        target_uid = _actor_id(target)
        scoundrel = _rogue_racket(actor) == "scoundrel"

        message = f"Feint: {outcome}."
        if outcome == "critical_success":
            if scoundrel:
                _upsert_feint_flat_footed(
                    target,
                    source_id=actor_uid,
                    source_turns_left=2,
                    attacker_id=None,
                    melee_only=True,
                )
                message = "Feint: critical_success. Scoundrel: cel flat-footed vs wszystkie melee ataki do końca twojej następnej tury."
            else:
                _upsert_feint_flat_footed(
                    target,
                    source_id=actor_uid,
                    source_turns_left=2,
                    attacker_id=actor_uid,
                    melee_only=True,
                )
                message = "Feint: critical_success. Cel flat-footed vs twoje melee ataki do końca twojej następnej tury."
        elif outcome == "success":
            if scoundrel:
                _upsert_feint_flat_footed(
                    target,
                    source_id=actor_uid,
                    source_turns_left=2,
                    attacker_id=actor_uid,
                    melee_only=True,
                )
                message = "Feint: success. Scoundrel: cel flat-footed vs twoje melee ataki do końca twojej następnej tury."
            else:
                _set_feint_next_attack(ctx, actor, target)
                message = "Feint: success. Cel flat-footed przeciw twojemu następnemu melee atakowi w tej turze."
        elif outcome == "critical_failure":
            _upsert_feint_flat_footed(
                actor,
                source_id=actor_uid,
                source_turns_left=2,
                attacker_id=target_uid,
                melee_only=False,
            )
            message = "Feint: critical_failure. Jesteś flat-footed przeciw atakom celu do końca twojej następnej tury."

        try:
            ctx.game.events.safe_emit_action(
                actor=actor,
                action_id=self.name,
                action_tags=self._effective_tags(ctx),
                target=target,
                target_pos=target_pos,
                outcome=outcome,
                dc=dc,
                roll=int(getattr(result, "roll", 0) or 0),
                total=int(getattr(result, "total", 0) or 0),
            )
        except Exception:
            pass

        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=1,
            message=message,
            data={
                "outcome": outcome,
                "target": target,
                "target_pos": target_pos,
                "dc": dc,
                "roll": int(getattr(result, "roll", 0) or 0),
                "total": int(getattr(result, "total", 0) or 0),
                "scoundrel": scoundrel,
            },
        )

