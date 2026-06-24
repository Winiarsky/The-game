from __future__ import annotations

import random

from skills import Skill
from statuses import PRONE_STATUS, apply_prone_effects
from GameObjects.interactions_mixin import compute_skill_modifier_with_sources, resolve_skill_check_with_sources_from_roll

from ..base import ActionCostEvent, EventContext, EventResult
from ..registry import register_event
from .enemy_strike_event import _bump_attack_state, _map_penalty, _select_weapon, _weapon_has_trait, _weapon_reach_ft


def _save_dc(target, skill_id: str, tags: list[str]) -> int:
    modifier, _breakdown, _notes = compute_skill_modifier_with_sources(
        skill_id=skill_id,
        actor=target,
        target=target,
        tags=tags,
        base_modifier=0,
    )
    return 10 + int(modifier or 0)


@register_event
class EnemyTripEvent(ActionCostEvent):
    name = "enemy_trip"
    default_tags = ["attack", "athletics", "trip", "enemy"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True
    actions_cost = 1

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Trip: wróg nie stoi na planszy.")

        metadata = dict(ctx.metadata or {})
        weapon = _select_weapon(actor, weapon_id=metadata.get("weapon_id"), prefer_ranged=False)
        if weapon is None or not _weapon_has_trait(weapon, "trip"):
            return EventResult.cancelled(message="Trip: wróg nie ma odpowiedniej broni.")

        target = metadata.get("forced_target")
        if target is None or getattr(target, "position", None) is None:
            return EventResult.cancelled(message="Trip: brak celu.")

        actor_pos = getattr(actor, "position", None)
        target_pos = getattr(target, "position", None)
        if actor_pos is None or target_pos is None:
            return EventResult.cancelled(message="Trip: brak pozycji.")

        reach_squares = max(1, _weapon_reach_ft(actor, weapon) // 5)
        if max(abs(actor_pos[0] - target_pos[0]), abs(actor_pos[1] - target_pos[1])) > reach_squares:
            return EventResult.cancelled(message="Trip: cel jest poza zasięgiem.")

        tags = self._effective_tags(ctx)
        natural_roll = random.randint(1, 20)
        map_penalty = _map_penalty(ctx, actor, weapon)
        dc = _save_dc(target, Skill.REFLEX.value, list(tags))
        result = resolve_skill_check_with_sources_from_roll(
            skill_id=Skill.ATHLETICS.value,
            dc=dc,
            actor=actor,
            target=target,
            tags=tags,
            roll=natural_roll,
            natural_shift=1 if natural_roll == 20 else -1 if natural_roll == 1 else 0,
            game=ctx.game,
            modifier_delta=-map_penalty,
        )
        outcome = str(result.outcome or "failure")

        if outcome in {"success", "critical_success"}:
            try:
                target.add_status(PRONE_STATUS)
            except Exception:
                pass
            apply_prone_effects(target)
        elif outcome == "critical_failure":
            try:
                actor.add_status(PRONE_STATUS)
            except Exception:
                pass
            apply_prone_effects(actor)

        _bump_attack_state(ctx, actor, weapon=weapon)

        try:
            ctx.game.events.safe_emit_action(
                actor=actor,
                action_id=self.name,
                action_tags=tags,
                target=target,
                target_pos=target_pos,
                outcome=outcome,
                map_penalty=map_penalty,
            )
        except Exception:
            pass

        message = f"{getattr(actor, 'name', 'Wróg')} próbuje Trip na {getattr(target, 'name', 'celu')}: {outcome}."
        try:
            ctx.game.ui_log(message)
        except Exception:
            pass
        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=1,
            message=message,
            data={"outcome": outcome, "target": target, "map_penalty": map_penalty},
        )


__all__ = ["EnemyTripEvent"]
