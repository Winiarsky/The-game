from __future__ import annotations

from typing import Any

from GameObjects.interactions_mixin import prompt_for_roll
from damage_types import DamageType
from statuses import Status, SpeedPenaltyStatus, make_persistent_damage


def _actor_id(actor) -> str:
    if actor is None:
        return ""
    return str(getattr(actor, "object_id", None) or getattr(actor, "name", None) or id(actor))


def _get_status(actor, status_id: str):
    if actor is None:
        return None
    getter = getattr(actor, "get_status", None)
    if callable(getter):
        try:
            return getter(status_id)
        except Exception:
            return None
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) == status_id:
            return status
    return None


def _active_support_bundle(owner, game) -> tuple[Status, dict[str, Any], Any, str] | None:
    if owner is None or game is None:
        return None
    status = _get_status(owner, "animal_companion_support")
    if status is None:
        return None
    combat_state = getattr(game, "state", None)
    getter = getattr(combat_state, "get_animal_companion", None)
    if not callable(getter):
        return None
    companion = getter(owner)
    if companion is None or getattr(companion, "position", None) is None:
        return None
    data = getattr(status, "data", None) or {}
    companion_type = str(data.get("companion_type") or getattr(companion, "companion_type", "") or "").strip().lower()
    if not companion_type:
        companion_type = str(getattr(companion, "companion_type", "wolf") or "wolf").strip().lower()
    return status, data, companion, companion_type


def _position(obj) -> tuple[int, int] | None:
    if isinstance(obj, tuple) and len(obj) == 2:
        try:
            return (int(obj[0]), int(obj[1]))
        except Exception:
            return None
    raw = getattr(obj, "position", None)
    if isinstance(raw, tuple) and len(raw) == 2:
        try:
            return (int(raw[0]), int(raw[1]))
        except Exception:
            return None
    return None


def _in_companion_reach(companion, target) -> bool:
    source = _position(companion)
    target_pos = _position(target)
    if source is None or target_pos is None:
        return False
    try:
        reach = max(1, int(getattr(companion, "reach_cells", 1) or 1))
    except Exception:
        reach = 1
    return max(abs(source[0] - target_pos[0]), abs(source[1] - target_pos[1])) <= reach


def _event_distance_feet(event: dict[str, Any]) -> int:
    src = _position(event.get("from_pos"))
    dst = _position(event.get("to_pos"))
    if src is None or dst is None:
        return 0
    cells = max(abs(src[0] - dst[0]), abs(src[1] - dst[1]))
    return max(0, int(cells) * 5)


def _replace_matching_statuses(target, matcher, replacement: Status | None) -> None:
    statuses = list(getattr(target, "statuses", []) or [])
    kept = [status for status in statuses if not matcher(status)]
    if replacement is not None:
        kept.append(replacement)
    try:
        target.statuses = kept
    except Exception:
        pass


def _status_data(status) -> dict[str, Any]:
    data = getattr(status, "data", None) or {}
    if isinstance(data, dict):
        return data
    return {}


def _apply_badger_step_lock(target, *, source_actor, locked_position: tuple[int, int] | None) -> None:
    source_id = _actor_id(source_actor)

    def _matcher(status) -> bool:
        if getattr(status, "id", None) != "animal_companion_badger_step_locked":
            return False
        data = _status_data(status)
        return str(data.get("source_id", "") or "") == source_id

    _replace_matching_statuses(
        target,
        _matcher,
        Status(
            id="animal_companion_badger_step_locked",
            label="Badger Support: no Step",
            stacks=True,
            source="animal_companion_support:badger",
            data={
                "source_id": source_id,
                "source_turns_left": 1,
                "locked_position": locked_position,
            },
        ),
    )


def _apply_cat_off_guard(target, *, source_actor) -> None:
    source_id = _actor_id(source_actor)

    def _matcher(status) -> bool:
        if getattr(status, "id", None) != "off_guard":
            return False
        data = _status_data(status)
        return str(data.get("source_id", "") or "") == source_id and str(getattr(status, "source", "") or "") == "animal_companion_support:cat"

    _replace_matching_statuses(
        target,
        _matcher,
        Status(
            id="off_guard",
            label="Off-Guard (Cat Support)",
            stacks=True,
            source="animal_companion_support:cat",
            data={
                "ac_penalty": 2,
                "source_id": source_id,
                "source_turns_left": 2,
                "effect_tags": ["off_guard", "flat_footed"],
            },
        ),
    )


def _apply_wolf_speed_penalty(target, *, source_actor) -> None:
    source_id = _actor_id(source_actor)

    def _matcher(status) -> bool:
        if getattr(status, "id", None) != "speed_penalty":
            return False
        data = _status_data(status)
        return str(data.get("source_id", "") or "") == source_id and str(getattr(status, "source", "") or "") == "animal_companion_support:wolf"

    _replace_matching_statuses(
        target,
        _matcher,
        SpeedPenaltyStatus(
            penalty_feet=5,
            source="animal_companion_support:wolf",
            source_id=source_id,
            combat_rounds_left=10,
            expire_on_combat_end=True,
            label="Wolf Support -5ft",
        ),
    )


def _apply_bird_bleed(target, *, source_actor, amount: int) -> None:
    source_id = _actor_id(source_actor)
    source = f"animal_companion_support:bird:{source_id}"

    def _matcher(status) -> bool:
        return getattr(status, "id", None) == "persistent_damage" and str(getattr(status, "source", "") or "") == source

    replacement = None
    if int(amount or 0) > 0:
        replacement = make_persistent_damage(int(amount), DamageType.BLEED.value, source=source)
    _replace_matching_statuses(target, _matcher, replacement)


def animal_companion_support_action_listener(game, event: dict[str, Any]) -> None:
    owner = event.get("actor")
    bundle = _active_support_bundle(owner, game)
    if bundle is None:
        return
    _status, data, companion, companion_type = bundle
    action_id = str(event.get("action_id", "") or "").strip().lower()
    tags = {str(tag or "").strip().lower() for tag in (event.get("action_tags") or [])}

    if companion_type == "horse" and "move" in tags:
        moved = _event_distance_feet(event)
        if moved > 0:
            try:
                current = max(0, int(data.get("owner_move_feet_this_turn", 0) or 0))
            except Exception:
                current = 0
            data["owner_move_feet_this_turn"] = current + moved

    if companion_type != "snake":
        return

    blocked = set(str(item) for item in list(event.get("blocked_reactor_ids") or []) if str(item))
    for enemy in list(getattr(game, "enemies", []) or []):
        if getattr(enemy, "position", None) is None:
            continue
        if not _in_companion_reach(companion, enemy):
            continue
        blocked.add(_actor_id(enemy))
    if blocked:
        event["blocked_reactor_ids"] = sorted(blocked)


def animal_companion_support_forces_off_guard(game, attacker, target, *, is_melee: bool) -> bool:
    if not is_melee:
        return False
    bundle = _active_support_bundle(attacker, game)
    if bundle is None:
        return False
    _status, _data, companion, companion_type = bundle
    if companion_type != "dromaeosaur":
        return False
    board = getattr(game, "board", None)
    attacker_pos = _position(attacker)
    target_pos = _position(target)
    companion_pos = _position(companion)
    if board is None or attacker_pos is None or target_pos is None or companion_pos is None:
        return False
    try:
        from combat.flanking import _adjacent_reachable, _are_opposite
    except Exception:
        return False
    neighbors = board.get_neighbors(target_pos, include_position=False, diagonal=True)
    if attacker_pos not in neighbors or companion_pos not in neighbors:
        return False
    if not _adjacent_reachable(board, target_pos, attacker_pos):
        return False
    if not _adjacent_reachable(board, target_pos, companion_pos):
        return False
    return bool(_are_opposite(target_pos, attacker_pos, companion_pos))


def animal_companion_support_damage_bonus(game, owner, target, *, tags: list[str] | tuple[str, ...] | set[str]) -> tuple[int, list[str]]:
    bundle = _active_support_bundle(owner, game)
    if bundle is None:
        return 0, []
    _status, data, companion, companion_type = bundle
    if companion_type != "horse":
        return 0, []
    normalized_tags = {str(tag or "").strip().lower() for tag in (tags or [])}
    if "attack_melee" not in normalized_tags:
        return 0, []
    if not _in_companion_reach(companion, target):
        return 0, []
    try:
        moved_feet = max(0, int(data.get("owner_move_feet_this_turn", 0) or 0))
    except Exception:
        moved_feet = 0
    if moved_feet < 10:
        return 0, []
    return 2, ["Horse Support: po ruchu >=10 ft w tej turze +2 circumstance do obrażeń (doliczone)."]


def apply_on_hit_animal_companion_support(ctx, owner, target, *, tags: list[str] | tuple[str, ...] | set[str]) -> dict[str, Any]:
    bundle = _active_support_bundle(owner, getattr(ctx, "game", None))
    if bundle is None or target is None:
        return {"applied": False, "damage_components": [], "notes": [], "defeated": False}
    _status, _data, companion, companion_type = bundle
    if not _in_companion_reach(companion, target):
        return {"applied": False, "damage_components": [], "notes": [], "defeated": False}
    try:
        if int(getattr(target, "hp", 1) or 1) <= 0:
            return {"applied": False, "damage_components": [], "notes": [], "defeated": False}
    except Exception:
        pass

    notes: list[str] = []
    damage_components: list[tuple[str, int]] = []
    defeated = False
    applied = False
    target_pos = _position(target)
    apply_damage = getattr(target, "apply_damage", None)

    if companion_type == "badger":
        _apply_badger_step_lock(target, source_actor=owner, locked_position=target_pos)
        notes.append("Badger Support: cel nie może użyć Step, dopóki nie zmieni pozycji.")
        applied = True
    elif companion_type == "bear":
        amount = int(
            prompt_for_roll(
                "Bear Support: dodatkowe obrażenia 1k8 slashing - podaj wynik:",
                layout="damage",
                answer_placeholder="Bear support damage",
            )
            or 0
        )
        if amount > 0 and callable(apply_damage):
            try:
                _hp, defeated = apply_damage(amount, DamageType.SLASHING.value)
            except Exception:
                defeated = False
            damage_components.append((DamageType.SLASHING.value, amount))
            notes.append(f"Bear Support: +{amount} slashing.")
            applied = True
    elif companion_type == "bird":
        amount = int(
            prompt_for_roll(
                "Bird Support: persistent bleed 1k4 - podaj wynik:",
                layout="damage",
                answer_placeholder="Bird bleed",
            )
            or 0
        )
        if amount > 0:
            _apply_bird_bleed(target, source_actor=owner, amount=amount)
            notes.append(f"Bird Support: persistent bleed {amount}.")
            applied = True
    elif companion_type == "cat":
        _apply_cat_off_guard(target, source_actor=owner)
        notes.append("Cat Support: cel jest off-guard do końca twojej następnej tury.")
        applied = True
    elif companion_type == "wolf":
        _apply_wolf_speed_penalty(target, source_actor=owner)
        notes.append("Wolf Support: cel otrzymuje -5 ft status do Speed na 1 minutę.")
        applied = True

    return {
        "applied": bool(applied),
        "damage_components": list(damage_components),
        "notes": list(notes),
        "defeated": bool(defeated),
    }


def apply_spell_attack_animal_companion_support(ctx, owner, target, *, tags: list[str] | tuple[str, ...] | set[str]) -> dict[str, Any]:
    result = apply_on_hit_animal_companion_support(ctx, owner, target, tags=tags)
    for note_line in list(result.get("notes") or []):
        try:
            ctx.game.ui_log(note_line)
        except Exception:
            pass
    if result.get("defeated"):
        try:
            from combat.damage_utils import remove_defeated_enemy

            remove_defeated_enemy(
                ctx.game,
                target,
                position=getattr(target, "position", None),
                source="animal_companion_support:spell_attack",
            )
        except Exception:
            pass
    return result


__all__ = [
    "animal_companion_support_action_listener",
    "animal_companion_support_damage_bonus",
    "animal_companion_support_forces_off_guard",
    "apply_on_hit_animal_companion_support",
    "apply_spell_attack_animal_companion_support",
]
