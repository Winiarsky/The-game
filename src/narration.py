from __future__ import annotations

from typing import Any


def _humanize(action_id: str) -> str:
    return str(action_id or "akcja").replace("_", " ").strip()


def _name(obj: Any, fallback: str) -> str:
    if obj is None:
        return fallback
    if isinstance(obj, dict):
        return str(obj.get("name") or obj.get("id") or fallback)
    return str(getattr(obj, "name", None) or getattr(obj, "object_id", None) or fallback)


def narrate_action_event(event: dict[str, Any]) -> str:
    actor_name = _name(event.get("actor"), "Aktor")
    action_id = str(event.get("action_id") or "action")
    target = event.get("target")
    target_name = _name(target, "cel") if target is not None else None
    to_pos = event.get("to_pos")

    if action_id == "move_start":
        return f"{actor_name} przygotowuje się do ruchu."
    if action_id == "move":
        if to_pos is not None:
            return f"{actor_name} przemieszcza się na pole {to_pos}."
        return f"{actor_name} się porusza."
    if action_id == "interaction":
        if target_name:
            return f"{actor_name} wchodzi w interakcję z {target_name}."
        return f"{actor_name} rozpoczyna interakcję."
    if action_id == "interaction_end":
        return f"{actor_name} kończy interakcję."
    if "attack" in action_id:
        if target_name:
            return f"{actor_name} atakuje {target_name}."
        return f"{actor_name} wykonuje atak."
    if action_id == "seek":
        return f"{actor_name} rozgląda się za ukrytymi elementami."
    if action_id == "stealth":
        return f"{actor_name} próbuje się ukryć."

    return f"{actor_name} wykonuje akcję: {_humanize(action_id)}."
