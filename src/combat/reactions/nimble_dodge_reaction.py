from __future__ import annotations

from dataclasses import dataclass

from bonuses import BonusEffect, BonusType

from .base import Reaction


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


@dataclass
class NimbleDodgeReaction(Reaction):
    id: str = "nimble_dodge"
    label: str = "Nimble Dodge"
    priority: int = 60
    action_cost: int = 1
    requires_reach: bool = False
    blocks_range_attacker: bool = False

    def triggers(self, actor, event: dict[str, object]) -> bool:
        if actor is None:
            return False
        if not _has_status(actor, "nimble_dodge"):
            return False
        if event.get("target") is not actor:
            return False
        action_id = str(event.get("action_id", "") or "")
        if not action_id.endswith("_pre"):
            return False
        tags = {str(tag or "").strip().lower() for tag in (event.get("action_tags") or [])}
        if not tags:
            return False
        if "attack" in tags:
            return True
        return any(tag.startswith("attack_") for tag in tags)

    def reason(self, actor, event: dict[str, object]) -> str:
        attacker = event.get("actor")
        attacker_name = getattr(attacker, "name", "atakującemu")
        return f"Nimble Dodge przeciw atakowi ({attacker_name})"

    def execute(self, actor, event: dict[str, object], ctx) -> bool:
        adder = getattr(actor, "add_bonus", None)
        if not callable(adder):
            return False
        attacker = event.get("actor")
        attacker_id = getattr(attacker, "object_id", None)
        event_uid = str(event.get("event_uid", "") or "nimble_dodge")
        try:
            adder(
                BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=2,
                    tag="ac",
                    source=f"nimble_dodge:{event_uid}",
                    target_id=str(attacker_id) if attacker_id else None,
                    label="nimble dodge",
                    duration_turns=1,
                )
            )
        except Exception:
            return False

        try:
            ctx.game.ui_log("Nimble Dodge: +2 circumstance AC przeciw wyzwalającemu atakowi.")
        except Exception:
            pass
        return True
