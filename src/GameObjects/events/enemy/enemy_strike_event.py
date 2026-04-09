from __future__ import annotations

import logging
import random
import re

from combat import effective_ac
from combat.degree_of_success import is_critical_success, is_hit, natural_shift_from_roll, resolve_outcome
from combat.hp_engine import apply_damage as hp_apply_damage
from damage_types import DamageType
from statuses import PoisonedStatus, SickenedStatus, SlowedStatus

from GameObjects.items.inventory import ensure_actor_inventory
from GameObjects.items.weapon import normalize_weapon_id
from GameObjects.events.attack.attack_base import check_concealed
from GameObjects.events.attack.base_attack_range_event import BaseRangeAttackEvent

from ..base import ActionCostEvent, EventContext, EventResult, mapping_setdefault_actor
from ..registry import register_event

logger = logging.getLogger(__name__)

_DAMAGE_RE = re.compile(r"(?P<count>\d+)[kd](?P<sides>\d+)", re.IGNORECASE)


class _EnemyRangeAnalyzer(BaseRangeAttackEvent):
    pass


def _weapon_traits(weapon) -> set[str]:
    return {str(item or "").strip().lower() for item in (getattr(weapon, "traits", ()) or ()) if str(item or "").strip()}


def _weapon_has_trait(weapon, trait: str) -> bool:
    needle = str(trait or "").strip().lower()
    if not needle:
        return False
    traits = _weapon_traits(weapon)
    return any(current == needle or current.startswith(f"{needle}:") for current in traits)


def _weapon_trait_value(weapon, trait: str, default: int = 0) -> int:
    needle = str(trait or "").strip().lower()
    if not needle:
        return int(default)
    for current in _weapon_traits(weapon):
        if not current.startswith(f"{needle}:"):
            continue
        raw = current.split(":", 1)[1]
        raw = raw.lower().replace("d", "")
        try:
            return int(raw)
        except Exception:
            continue
    return int(default)


def _weapon_reach_ft(actor, weapon) -> int:
    reach_ft = _weapon_trait_value(weapon, "reach", default=0)
    if reach_ft > 0:
        return max(5, reach_ft)
    try:
        return max(5, int(getattr(actor, "reach", 1) or 1) * 5)
    except Exception:
        return 5


def _iter_weapons(actor) -> list[object]:
    inventory = ensure_actor_inventory(actor)
    return [item for item in inventory if str(getattr(item, "category", "") or "").strip().lower() == "weapon"]


def _select_weapon(actor, *, weapon_id: object | None = None, prefer_ranged: bool | None = None):
    weapons = _iter_weapons(actor)
    if not weapons:
        return None

    wanted = normalize_weapon_id(weapon_id)
    if not wanted:
        wanted = normalize_weapon_id(getattr(actor, "active_weapon", None))
    if wanted:
        for weapon in weapons:
            if normalize_weapon_id(getattr(weapon, "item_id", None)) == wanted:
                return weapon

    if prefer_ranged is not None:
        for weapon in weapons:
            if bool(getattr(weapon, "ranged", False)) is prefer_ranged:
                return weapon

    for weapon in weapons:
        if normalize_weapon_id(getattr(weapon, "item_id", None)) != "unarmed":
            return weapon
    return weapons[0]


def _pick_target(ctx: EventContext, actor, weapon):
    game = ctx.game
    board = game.board
    forced_target = (ctx.metadata or {}).get("forced_target")
    if forced_target is not None:
        return forced_target

    actor_pos = getattr(actor, "position", None)
    if actor_pos is None:
        return None

    candidates = []
    if bool(getattr(weapon, "ranged", False)):
        for hero in getattr(game, "heroes", []) or []:
            if getattr(hero, "position", None) is None:
                continue
            candidates.append(hero)
    else:
        reach_squares = max(1, _weapon_reach_ft(actor, weapon) // 5)
        for hero in getattr(game, "heroes", []) or []:
            pos = getattr(hero, "position", None)
            if pos is None:
                continue
            if max(abs(actor_pos[0] - pos[0]), abs(actor_pos[1] - pos[1])) <= reach_squares:
                candidates.append(hero)

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    positions = [getattr(target, "position", None) for target in candidates if getattr(target, "position", None) is not None]
    if not positions:
        return None
    try:
        ctx.game.conn.set_leds(positions, [[180, 50, 50] for _ in positions])
        choice = ctx.game.conn.scan_board(positions)
    finally:
        try:
            ctx.game.conn.leds_off()
        except Exception:
            pass
    for target in candidates:
        if getattr(target, "position", None) == choice:
            return target
    return None


def _parse_damage_prompt(prompt: object) -> tuple[int, int, str | None]:
    text = str(prompt or "").strip().lower()
    match = _DAMAGE_RE.search(text.replace(" ", ""))
    if not match:
        return 0, 0, None
    count = int(match.group("count") or 0)
    sides = int(match.group("sides") or 0)
    ability = None
    if "str" in text:
        ability = "strength"
    elif "dex" in text:
        ability = "dexterity"
    return count, sides, ability


def _roll_damage(actor, weapon) -> tuple[int, str]:
    prompt = getattr(weapon, "damage_prompt", "1k6")
    count, sides, ability = _parse_damage_prompt(prompt)
    total = 0
    for _ in range(max(1, count)):
        total += random.randint(1, max(1, sides))

    weapon_id = normalize_weapon_id(getattr(weapon, "item_id", None))
    bonuses = dict(getattr(actor, "weapon_damage_bonuses", {}) or {})
    if weapon_id in bonuses:
        total += int(bonuses.get(weapon_id) or 0)
    elif ability == "strength":
        total += int(getattr(actor, "strength", 0) or 0)
    elif ability == "dexterity":
        total += int(getattr(actor, "dex_mod", 0) or 0)

    damage_type = str(getattr(weapon, "damage_type", DamageType.NORMAL.value) or DamageType.NORMAL.value)
    return max(0, int(total)), damage_type


def _deadly_bonus(weapon) -> int:
    sides = _weapon_trait_value(weapon, "deadly", default=0)
    if sides <= 0:
        return 0
    return random.randint(1, sides)


def _target_is_off_guard(target) -> bool:
    checker = getattr(target, "has_status", None)
    if callable(checker):
        try:
            return bool(checker("off_guard") or checker("flat_footed"))
        except Exception:
            return False
    for status in getattr(target, "statuses", []) or []:
        sid = str(getattr(status, "id", status) or "").strip().lower()
        if sid in {"off_guard", "flat_footed"}:
            return True
    return False


def _is_goblin_pox_immune(target) -> bool:
    if target is None:
        return False
    enemy_type = str(getattr(target, "enemy_type", "") or "").strip().lower()
    if enemy_type == "goblin":
        return True
    trait_checker = getattr(target, "has_trait", None)
    if callable(trait_checker):
        try:
            if trait_checker("goblin") or trait_checker("goblin_dog"):
                return True
        except Exception:
            pass
    traits = {str(item or "").strip().lower() for item in (getattr(target, "traits", ()) or ()) if str(item or "").strip()}
    if {"goblin", "goblin_dog"} & traits:
        return True
    name = str(getattr(target, "name", "") or "").strip().lower()
    return "goblin" in name


def apply_goblin_pox(target) -> bool:
    if target is None or _is_goblin_pox_immune(target):
        return False
    adder = getattr(target, "add_status", None)
    if not callable(adder):
        return False
    try:
        adder(
            PoisonedStatus(
                duration=1440,
                damage=0,
                dc=17,
                source="goblin_pox",
                stages=[
                    {"conditions": [SickenedStatus(value=1, duration=1, source="goblin_pox")]},
                    {
                        "conditions": [
                            SickenedStatus(value=1, duration=1, source="goblin_pox"),
                            SlowedStatus(value=1, duration=1, source="goblin_pox"),
                        ]
                    },
                    {"conditions": [SickenedStatus(value=2, duration=1440, source="goblin_pox")]},
                ],
                stage=1,
            )
        )
        return True
    except Exception:
        return False


def _apply_damage(target, amount: int, damage_type: str) -> int:
    before_hp = None
    current_hp = getattr(target, "current_hp", None)
    if callable(current_hp):
        try:
            before_hp = int(current_hp())
        except Exception:
            before_hp = None
    apply = getattr(target, "apply_damage", None)
    if callable(apply):
        try:
            apply(amount, damage_type)
            if before_hp is not None and callable(current_hp):
                return max(0, before_hp - int(current_hp()))
            return max(0, int(amount))
        except Exception:
            pass
    try:
        info = hp_apply_damage(target, amount, damage_type, source="enemy_strike")
        return max(0, int((info or {}).get("hp_damage", 0) or 0))
    except Exception:
        return 0


def _attack_state(ctx: EventContext, actor) -> dict[str, object]:
    if not ctx.in_combat:
        return {}
    combat_state = getattr(ctx.game, "state", None)
    payload = mapping_setdefault_actor(getattr(combat_state, "attack_state", {}), actor, dict)
    return payload if isinstance(payload, dict) else {}


def _attacks_this_turn(ctx: EventContext, actor) -> int:
    if actor is None:
        return 0
    payload = _attack_state(ctx, actor)
    metadata = dict(ctx.metadata or {})
    fixed = metadata.get("fixed_attacks_this_turn")
    if fixed is not None:
        try:
            return max(0, int(fixed))
        except Exception:
            return 0
    try:
        return max(0, int(payload.get("attacks_this_turn", 0) or 0))
    except Exception:
        return 0


def _map_penalty(ctx: EventContext, actor, weapon) -> int:
    attacks = _attacks_this_turn(ctx, actor)
    if attacks <= 0:
        return 0
    agile = _weapon_has_trait(weapon, "agile")
    if attacks == 1:
        return 4 if agile else 5
    return 8 if agile else 10


def _bump_attack_state(ctx: EventContext, actor, *, weapon, count: int = 1) -> None:
    if not ctx.in_combat or actor is None:
        return
    payload = _attack_state(ctx, actor)
    payload["attacks_this_turn"] = int(payload.get("attacks_this_turn", 0) or 0) + max(0, int(count or 0))
    weapon_counts = payload.get("weapon_counts")
    if not isinstance(weapon_counts, dict):
        weapon_counts = {}
    weapon_key = normalize_weapon_id(getattr(weapon, "item_id", None)) or "weapon"
    weapon_counts[weapon_key] = int(weapon_counts.get(weapon_key, 0) or 0) + max(0, int(count or 0))
    payload["weapon_counts"] = weapon_counts


@register_event
class EnemyStrikeEvent(ActionCostEvent):
    name = "enemy_strike"
    default_tags = ["attack", "enemy"]
    consumes_action = True
    available_in_exploration = False
    actions_cost = 1

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Strike: wróg nie stoi na planszy.")

        metadata = dict(ctx.metadata or {})
        prefer_ranged = metadata.get("prefer_ranged")
        if prefer_ranged is not None:
            prefer_ranged = bool(prefer_ranged)
        weapon = _select_weapon(actor, weapon_id=metadata.get("weapon_id"), prefer_ranged=prefer_ranged)
        if weapon is None:
            return EventResult.cancelled(message="Strike: wróg nie ma broni.")

        try:
            actor.active_weapon = normalize_weapon_id(getattr(weapon, "item_id", None))
        except Exception:
            pass

        target = _pick_target(ctx, actor, weapon)
        if target is None or getattr(target, "position", None) is None:
            return EventResult.cancelled(message="Strike: brak celu.")

        actor_pos = getattr(actor, "position", None)
        target_pos = getattr(target, "position", None)
        if actor_pos is None or target_pos is None:
            return EventResult.cancelled(message="Strike: brak pozycji.")

        ranged = bool(getattr(weapon, "ranged", False))
        cover_type = "none"
        range_penalty = 0
        if ranged:
            analyzer = _EnemyRangeAnalyzer()
            analyzer.range_increment_ft = int(getattr(weapon, "range_increment_ft", 60) or 60)
            analysis = analyzer._analyze_shot(ctx.game, actor_pos, target_pos, target=target)
            cover_type = str(analysis.get("cover_type", "none") or "none")
            range_penalty = int(analysis.get("range_penalty", 0) or 0)
            if bool(analysis.get("blocked", False)):
                return EventResult.cancelled(message="Strike: linia strzału jest zablokowana.")
        else:
            reach_squares = max(1, _weapon_reach_ft(actor, weapon) // 5)
            if max(abs(actor_pos[0] - target_pos[0]), abs(actor_pos[1] - target_pos[1])) > reach_squares:
                return EventResult.cancelled(message="Strike: cel jest poza zasięgiem broni.")

        if not check_concealed(ctx, target):
            _bump_attack_state(ctx, actor, weapon=weapon)
            return EventResult(
                success=True,
                consumed_action=True,
                actions_spent=1,
                message="Strike chybia przez concealed.",
                data={"outcome": "concealed_miss", "target": target},
            )

        weapon_id = normalize_weapon_id(getattr(weapon, "item_id", None)) or "weapon"
        attack_bonus = int(dict(getattr(actor, "weapon_attack_bonuses", {}) or {}).get(weapon_id, getattr(actor, "attack_bonus", 0)) or 0)
        extra_mod = 0
        compute_modifier = getattr(actor, "compute_modifier", None)
        if callable(compute_modifier):
            try:
                extra_mod = int(compute_modifier("attack_ranged" if ranged else "attack_melee", target=target) or 0)
            except Exception:
                extra_mod = 0

        map_penalty = _map_penalty(ctx, actor, weapon)
        natural_roll = random.randint(1, 20)
        total_attack = natural_roll + attack_bonus + extra_mod - map_penalty - range_penalty
        cover_bonus = _EnemyRangeAnalyzer.COVER_AC.get(cover_type, 0) if ranged else 0
        target_ac = int(effective_ac(target) or 10) + int(cover_bonus or 0)
        outcome = resolve_outcome(total_attack, target_ac, natural_shift=natural_shift_from_roll(natural_roll))

        damage = 0
        hp_dealt = 0
        damage_type = str(getattr(weapon, "damage_type", DamageType.NORMAL.value) or DamageType.NORMAL.value)
        pox_applied = False
        if is_hit(outcome):
            damage, damage_type = _roll_damage(actor, weapon)
            if _weapon_has_trait(weapon, "backstabber") and _target_is_off_guard(target):
                damage += 1
            if is_critical_success(outcome):
                damage = max(0, int(damage) * 2)
                damage += _deadly_bonus(weapon)
            hp_dealt = _apply_damage(target, damage, damage_type)
            if _weapon_has_trait(weapon, "jaws") and getattr(actor, "behavior_id", None) == "goblin_dog_hunter":
                pox_applied = apply_goblin_pox(target)

        _bump_attack_state(ctx, actor, weapon=weapon)

        try:
            ctx.game.events.safe_emit_action(
                actor=actor,
                action_id=self.name,
                action_tags=self._effective_tags(ctx),
                target=target,
                target_pos=target_pos,
                weapon_id=weapon_id,
                outcome=outcome,
                damage=damage,
                damage_type=damage_type,
                map_penalty=map_penalty,
                cover=cover_type,
                ranged=ranged,
            )
            if hp_dealt > 0:
                ctx.game.events.safe_emit_action(
                    actor=actor,
                    action_id="damage_applied",
                    action_tags=["damage", "attack", "enemy"],
                    target=target,
                    target_pos=target_pos,
                    source_action=self.name,
                    damage=int(hp_dealt),
                    damage_type=damage_type,
                )
        except Exception:
            pass

        summary = (
            f"{getattr(actor, 'name', 'Wróg')} wykonuje Strike {getattr(weapon, 'name', 'bronią')}"
            f" przeciw {getattr(target, 'name', 'celowi')}: {outcome}."
        )
        if is_hit(outcome):
            summary = f"{summary} Obrażenia {damage} ({damage_type})."
            if pox_applied:
                summary = f"{summary} Cel łapie goblin pox."
        elif ranged and cover_bonus:
            summary = f"{summary} Osłona celu: +{cover_bonus} AC."
        try:
            ctx.game.ui_log(summary)
        except Exception:
            pass

        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=1,
            message=summary,
            data={
                "outcome": outcome,
                "target": target,
                "weapon": weapon,
                "damage": damage,
                "hp_dealt": hp_dealt,
                "cover_type": cover_type,
                "map_penalty": map_penalty,
                "pox_applied": pox_applied,
            },
        )


__all__ = ["EnemyStrikeEvent", "apply_goblin_pox"]
