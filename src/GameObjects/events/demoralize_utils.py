from __future__ import annotations

from typing import Iterable

from bonuses import BonusEffect, BonusType
from skills import Skill
from GameObjects.interactions_mixin import compute_skill_modifier_with_sources, resolve_skill_check_with_sources
from GameObjects.events.base import EventContext, mapping_setdefault_actor
from GameObjects.events.magic.magic_utils import grid_distance_feet


DEMORALIZE_RANGE_FEET = 30


def _actor_id(actor) -> str:
    return str(getattr(actor, "object_id", None) or getattr(actor, "name", None) or id(actor))


def _is_alive(target) -> bool:
    if target is None:
        return False
    if getattr(target, "position", None) is None:
        return False
    hp = getattr(target, "hp", None)
    try:
        if hp is not None and int(hp) <= 0:
            return False
    except Exception:
        pass
    dead_checker = getattr(target, "is_dead", None)
    if callable(dead_checker):
        try:
            return not bool(dead_checker())
        except Exception:
            return True
    return True


def _iter_demoralize_targets(ctx: EventContext, actor, *, excluded_ids: set[str] | None = None):
    excluded_ids = set(excluded_ids or set())
    actor_pos = getattr(actor, "position", None)
    if actor_pos is None:
        return []

    enemies = list(getattr(ctx.game, "enemies", []) or [])
    heroes = list(getattr(ctx.game, "heroes", []) or [])
    if actor in heroes:
        pool = enemies
    elif actor in enemies:
        pool = heroes
    else:
        pool = enemies

    valid: list[tuple[object, tuple[int, int]]] = []
    for target in pool:
        if not _is_alive(target):
            continue
        target_id = _actor_id(target)
        if target_id in excluded_ids:
            continue
        pos = getattr(target, "position", None)
        if pos is None:
            continue
        try:
            if grid_distance_feet(actor_pos, pos) > DEMORALIZE_RANGE_FEET:
                continue
        except Exception:
            continue
        valid.append((target, pos))
    return valid


def _pick_target(ctx: EventContext, candidates: list[tuple[object, tuple[int, int]]]):
    if not candidates:
        return None, None
    if len(candidates) == 1:
        return candidates[0]
    positions = [pos for _target, pos in candidates]
    try:
        try:
            ctx.game.conn.set_leds(positions, [[180, 60, 0] for _ in positions])
        except Exception:
            pass
        selected = ctx.game.conn.scan_board(positions)
    finally:
        try:
            ctx.game.conn.leds_off()
        except Exception:
            pass
    for target, pos in candidates:
        if pos == selected:
            return target, pos
    return None, None


def _immunity_store_for_actor(ctx: EventContext, actor):
    if not ctx.in_combat:
        return None
    state = getattr(ctx.game, "state", None)
    if state is None:
        return None
    store = getattr(state, "demoralize_immunity", None)
    if not isinstance(store, dict):
        store = {}
        try:
            setattr(state, "demoralize_immunity", store)
        except Exception:
            return None
    payload = mapping_setdefault_actor(store, actor, set)
    if isinstance(payload, set):
        return payload
    fixed = set(payload or [])
    try:
        key = actor
        store[key] = fixed
    except Exception:
        store[f"actor:{_actor_id(actor)}"] = fixed
    return fixed


def is_demoralize_immune_this_combat(ctx: EventContext, actor, target) -> bool:
    immunity = _immunity_store_for_actor(ctx, actor)
    if immunity is None:
        return False
    return _actor_id(target) in immunity


def mark_demoralize_immunity_this_combat(ctx: EventContext, actor, target) -> None:
    immunity = _immunity_store_for_actor(ctx, actor)
    if immunity is None:
        return
    try:
        immunity.add(_actor_id(target))
    except Exception:
        return


def _remove_bonuses_with_prefix(target, prefix: str) -> None:
    remover = getattr(target, "remove_bonuses_with_prefix", None)
    if callable(remover):
        try:
            remover(prefix)
            return
        except Exception:
            pass
    bonuses = getattr(target, "bonuses", None)
    if not isinstance(bonuses, list):
        return
    kept = [item for item in bonuses if not str(getattr(item, "source", "") or "").startswith(prefix)]
    try:
        target.bonuses = kept
    except Exception:
        pass


def _apply_frightened_penalties(target, *, frightened: int, source_key: str) -> None:
    if target is None or frightened <= 0:
        return
    _remove_bonuses_with_prefix(target, f"demoralize:fear:{source_key}")
    adder = getattr(target, "add_bonus", None)
    if not callable(adder):
        return
    duration = 2 if frightened >= 2 else 1
    tags: list[str] = ["ac", "attack_melee", "attack_ranged", "magic"]
    tags.extend([skill.value for skill in Skill])
    for tag in tags:
        try:
            adder(
                BonusEffect(
                    type=BonusType.STATUS,
                    value=int(frightened),
                    tag=tag,
                    source=f"demoralize:fear:{source_key}",
                    label=f"frightened {frightened}",
                    is_penalty=True,
                    duration_turns=duration,
                )
            )
        except Exception:
            continue


def _will_dc(ctx: EventContext, target, actor) -> int:
    base_will = int(getattr(target, "will_bonus", 0) or 0)
    modifier, breakdown, _notes = compute_skill_modifier_with_sources(
        skill_id=Skill.WILL.value,
        actor=target,
        target=actor,
        tags=["save", "will", "fear", "mental", "demoralize"],
        base_modifier=base_will,
    )
    if breakdown:
        try:
            ctx.game.ui_log(f"Demoralize: modyfikatory Will celu: {', '.join(breakdown)}.")
        except Exception:
            pass
    return 10 + int(modifier)


def perform_demoralize(
    ctx: EventContext,
    actor,
    *,
    extra_bonus: int = 0,
    source_action: str = "demoralize",
    forced_target=None,
    excluded_target_ids: Iterable[str] | None = None,
    enforce_combat_immunity: bool = True,
) -> dict[str, object]:
    if actor is None:
        return {"success": False, "cancelled": True, "message": "Demoralize: brak aktora."}
    if getattr(actor, "position", None) is None:
        return {"success": False, "cancelled": True, "message": "Demoralize: aktor nie jest na planszy."}

    excluded = {str(item).strip() for item in (excluded_target_ids or []) if str(item).strip()}
    candidates = _iter_demoralize_targets(ctx, actor, excluded_ids=excluded)
    if forced_target is not None:
        selected = None
        for target, pos in candidates:
            if target is forced_target:
                selected = (target, pos)
                break
        if selected is None:
            return {"success": False, "cancelled": True, "message": "Demoralize: wymuszony cel jest poza zasiegiem."}
        target, target_pos = selected
    else:
        target, target_pos = _pick_target(ctx, candidates)
    if target is None:
        return {"success": False, "cancelled": True, "message": "Demoralize: brak celu w zasiegu."}

    if enforce_combat_immunity and is_demoralize_immune_this_combat(ctx, actor, target):
        return {
            "success": False,
            "cancelled": True,
            "immunity_blocked": True,
            "target": target,
            "target_pos": target_pos,
            "message": "Demoralize: ten cel jest juz odporny na twoje zastraszanie do konca walki.",
        }

    dc = _will_dc(ctx, target, actor)
    try:
        base_intimidation = int(getattr(actor, "intimidation_bonus", 0) or 0)
    except Exception:
        base_intimidation = 0
    total_base = int(base_intimidation) + int(extra_bonus or 0)
    tags = ["concentrate", "emotion", "fear", "mental", "demoralize", Skill.INTIMIDATION.value]
    result = resolve_skill_check_with_sources(
        skill_id=Skill.INTIMIDATION.value,
        dc=dc,
        actor=actor,
        target=target,
        tags=tags,
        game=ctx.game,
        base_modifier=total_base,
        apply_modifiers=True,
    )

    if enforce_combat_immunity:
        mark_demoralize_immunity_this_combat(ctx, actor, target)

    outcome = str(getattr(result, "outcome", "failure") or "failure")
    frightened = 0
    if outcome == "critical_success":
        frightened = 2
    elif outcome == "success":
        frightened = 1

    if frightened > 0:
        source_key = f"{source_action}:{_actor_id(actor)}:{_actor_id(target)}"
        _apply_frightened_penalties(target, frightened=frightened, source_key=source_key)
        try:
            ctx.game.ui_log(
                f"Demoralize: {getattr(target, 'name', 'Cel')} otrzymuje Frightened {frightened}."
            )
        except Exception:
            pass
    else:
        try:
            ctx.game.ui_log(f"Demoralize: brak efektu ({outcome}).")
        except Exception:
            pass

    message = f"Demoralize: {outcome}."
    if frightened > 0:
        message = f"{message} Frightened {frightened}."
    elif outcome == "critical_failure":
        message = f"{message} Cel i tak otrzymuje odpornosc na twoje Demoralize do konca walki."
    return {
        "success": True,
        "cancelled": False,
        "target": target,
        "target_pos": target_pos,
        "outcome": outcome,
        "frightened": frightened,
        "dc": int(dc),
        "roll": int(getattr(result, "roll", 0) or 0),
        "modifier": int(getattr(result, "modifier", 0) or 0),
        "total": int(getattr(result, "total", 0) or 0),
        "message": message,
    }

