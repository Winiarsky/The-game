from __future__ import annotations

from typing import Any

from communication import make_communication
from localization.pl import localize_term_pl


NARRATOR_TITLE = "Mistrz gry"

_ACTION_SUFFIXES = (
    "_concealed_miss",
    "_wrong_square",
    "_critical_failure",
    "_critical_success",
    "_failure",
    "_success",
    "_miss",
    "_pre",
)


def _humanize(action_id: str) -> str:
    raw = str(action_id or "akcja").strip()
    if not raw:
        return "akcja"
    normalized = raw.lower().replace("-", "_").replace(" ", "_")
    for suffix in _ACTION_SUFFIXES:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    normalized = normalized.strip("_")
    localized = localize_term_pl(normalized)
    if localized:
        return localized
    return str(normalized or raw or "akcja").replace("_", " ").strip()


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


def build_narration_communication(
    *,
    summary: str,
    body_markdown: str,
    dedupe_key: str | None = None,
    priority: str = "info",
    semantic_type: str = "status_update",
    channel: str = "timeline",
    blocking: bool = False,
    next_hint: str | None = None,
) -> dict[str, Any]:
    context = {"next": str(next_hint)} if str(next_hint or "").strip() else None
    return make_communication(
        channel=channel,
        priority=priority,
        semantic_type=semantic_type,
        title=NARRATOR_TITLE,
        summary=summary,
        body_markdown=body_markdown,
        context=context,
        dedupe_key=dedupe_key,
        blocking=blocking,
    )


def _extract_damage_total(data: dict[str, Any]) -> int | None:
    for key in ("hp_dealt", "damage_total", "damage"):
        try:
            value = int(data.get(key, 0) or 0)
        except Exception:
            value = 0
        if value > 0:
            return value
    components = data.get("damage_components")
    if isinstance(components, (list, tuple)):
        total = 0
        for item in components:
            try:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    total += max(0, int(item[1] or 0))
            except Exception:
                continue
        if total > 0:
            return total
    return None


def _message_has_any(message: str, *tokens: str) -> bool:
    lowered = str(message or "").strip().lower()
    return any(token in lowered for token in tokens)


def narrate_action_result(*, actor: Any, action_id: str, result: Any) -> str:
    actor_name = _name(actor, "Aktor")
    result_message = str(getattr(result, "message", "") or "").strip()
    data = getattr(result, "data", None) or {}
    if not isinstance(data, dict):
        data = {}
    target = data.get("target")
    target_name = _name(target, "cel") if target is not None else None
    action_label = _humanize(action_id)

    if not bool(getattr(result, "success", False)):
        if target_name and (data.get("hit") is False or _message_has_any(result_message, "pudł", "chybi")):
            return f"{actor_name} próbuje dosięgnąć {target_name}, ale akcja nie przynosi efektu."
        if result_message:
            return f"{actor_name} nie doprowadza akcji do skutku. {result_message}"
        return f"{actor_name} nie zdołał wykonać akcji: {action_label}."

    if data.get("hit") is False or _message_has_any(result_message, "pudł", "chybi"):
        if _message_has_any(result_message, "concealed"):
            return (
                f"{actor_name} atakuje {target_name or 'cel'}, ale przeciwnik gubi się w zasłonie "
                "i cios nie dochodzi."
            )
        if data.get("guessed_target_square") is not None or _message_has_any(result_message, "błędnie wskazane pole"):
            return f"{actor_name} uderza w puste miejsce. To był błędny wybór pola."
        return f"{actor_name} atakuje {target_name or 'cel'}, ale pudłuje."

    if data.get("hit") is True:
        critical = bool(data.get("critical"))
        defeated = bool(data.get("defeated"))
        damage_total = _extract_damage_total(data)
        sentence = f"{actor_name} {'trafia krytycznie' if critical else 'trafia'} {target_name or 'cel'}"
        if damage_total is not None:
            sentence = f"{sentence} i zadaje {damage_total} obrażeń"
        sentence = f"{sentence}."
        if defeated:
            sentence = f"{sentence} {target_name or 'Cel'} pada."
        return sentence

    if action_id == "move":
        to_pos = data.get("to_pos")
        if to_pos is not None:
            return f"{actor_name} kończy ruch na polu {to_pos}."
        return f"{actor_name} kończy ruch."
    if action_id == "step":
        return f"{actor_name} wykonuje ostrożny krok i zmienia pozycję."
    if action_id == "interaction":
        return f"{actor_name} kończy interakcję z otoczeniem."
    if action_id == "seek":
        return f"{actor_name} rozgląda się uważnie za ukrytymi zagrożeniami lub śladami."
    if action_id == "raise_shield":
        return f"{actor_name} unosi tarczę i przygotowuje się na nadchodzący cios."
    if action_id == "end":
        return f"{actor_name} kończy swoją turę."

    if result_message:
        return f"{actor_name} wykonuje akcję {action_label}. {result_message}"
    return f"{actor_name} kończy akcję: {action_label}."
