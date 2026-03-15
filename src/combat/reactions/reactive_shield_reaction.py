from __future__ import annotations

from dataclasses import dataclass

from bonuses import BonusEffect, BonusType
from GameObjects.items.shield import get_equipped_shield
from statuses import SpeedPenaltyStatus

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


def _clear_raise_shield_speed_penalties(actor) -> None:
    statuses = list(getattr(actor, "statuses", []) or [])
    if not statuses:
        return
    kept = []
    for status in statuses:
        status_id = str(getattr(status, "id", "") or "").strip().lower()
        source = str(getattr(status, "source", "") or "")
        if status_id == "speed_penalty" and source.startswith("raise_shield:"):
            continue
        kept.append(status)
    try:
        setattr(actor, "statuses", kept)
    except Exception:
        pass


def _apply_tower_shield_speed_penalty(actor, *, source_tag: str, shield) -> None:
    penalty = max(0, int(getattr(shield, "speed_penalty_feet", 0) or 0))
    if penalty <= 0:
        return
    adder = getattr(actor, "add_status", None)
    if not callable(adder):
        return
    actor_id = str(getattr(actor, "object_id", "") or "").strip() or None
    try:
        adder(
            SpeedPenaltyStatus(
                penalty_feet=penalty,
                source=source_tag,
                source_id=actor_id,
                source_turns_left=1,
                duration=1,
                label=f"reactive shield: -{penalty} ft",
            )
        )
    except Exception:
        return


@dataclass
class ReactiveShieldReaction(Reaction):
    id: str = "reactive_shield"
    label: str = "Reactive Shield"
    priority: int = 45
    action_cost: int = 1
    requires_reach: bool = False
    blocks_range_attacker: bool = False

    def triggers(self, actor, event: dict[str, object]) -> bool:
        if actor is None:
            return False
        if not _has_status(actor, "reactive_shield"):
            return False
        if event.get("target") is not actor:
            return False
        action_id = str(event.get("action_id", "") or "")
        if not action_id.endswith("_pre"):
            return False
        tags = set(event.get("action_tags") or [])
        if "attack_melee" not in tags:
            return False
        shield = get_equipped_shield(actor, create_default=False)
        if shield is None:
            return False
        if bool(getattr(shield, "is_destroyed", False)):
            return False
        return True

    def reason(self, actor, event: dict[str, object]) -> str:
        _ = event
        return f"Reactive Shield: ochrona {getattr(actor, 'name', 'celu')}"

    def execute(self, actor, event: dict[str, object], ctx) -> bool:
        shield = get_equipped_shield(actor, create_default=False)
        if shield is None:
            return False

        remover = getattr(actor, "remove_bonuses_with_prefix", None)
        if callable(remover):
            try:
                remover("raise_shield:")
            except Exception:
                pass
        _clear_raise_shield_speed_penalties(actor)

        round_idx = getattr(getattr(ctx.game, "state", None), "round_index", None)
        source_tag = f"raise_shield:round{round_idx}" if round_idx is not None else "raise_shield"
        try:
            shield_ac_bonus = max(0, int(getattr(shield, "ac_bonus", 2) or 2))
        except Exception:
            shield_ac_bonus = 2

        adder = getattr(actor, "add_bonus", None)
        if not callable(adder):
            return False
        try:
            adder(
                BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=shield_ac_bonus,
                    tag="ac",
                    source=source_tag,
                    label="tarcza w górze",
                    duration_turns=1,
                )
            )
        except Exception:
            return False
        _apply_tower_shield_speed_penalty(actor, source_tag=source_tag, shield=shield)

        try:
            ctx.game.ui_log(f"Reactive Shield: podnosisz tarczę (+{shield_ac_bonus} AC) na ten atak.")
        except Exception:
            pass
        return True
