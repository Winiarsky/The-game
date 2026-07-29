"""Persistent Magic Mouth specifications stored in exploration magic effects."""

from __future__ import annotations

from dataclasses import dataclass
import json


@dataclass(frozen=True, slots=True)
class MagicMouthSpecification:
    object_id: str
    message: str
    trigger_description: str
    trigger_event: str = "interaction"

    def __post_init__(self) -> None:
        if not self.object_id.strip():
            raise ValueError("Wybierz przedmiot, który ma otrzymać Magiczne usta.")
        if not self.message.strip():
            raise ValueError("Wiadomość Magicznych ust nie może być pusta.")
        if len(self.message.split()) > 25:
            raise ValueError("Wiadomość Magicznych ust może mieć najwyżej 25 słów.")
        if not self.trigger_description.strip():
            raise ValueError("Opisz słyszalny albo widzialny warunek wyzwalający.")
        if self.trigger_event not in {"interaction", "authored_event"}:
            raise ValueError("Nieobsługiwany rodzaj wyzwalacza Magicznych ust.")


def encode_magic_mouth(specification: MagicMouthSpecification) -> str:
    return json.dumps(
        {
            "object_id": specification.object_id,
            "message": specification.message,
            "trigger_description": specification.trigger_description,
            "trigger_event": specification.trigger_event,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def decode_magic_mouth(value: str) -> MagicMouthSpecification:
    try:
        data = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Uszkodzony zapis Magicznych ust.") from exc
    if not isinstance(data, dict):
        raise ValueError("Uszkodzony zapis Magicznych ust.")
    return MagicMouthSpecification(
        object_id=str(data.get("object_id", "")),
        message=str(data.get("message", "")),
        trigger_description=str(data.get("trigger_description", "")),
        trigger_event=str(data.get("trigger_event", "interaction")),
    )


def magic_mouth_message_for_event(
    specification: MagicMouthSpecification,
    *,
    object_id: str,
    event: str,
) -> str | None:
    if specification.object_id != object_id:
        return None
    if specification.trigger_event != event:
        return None
    return specification.message


__all__ = [
    "MagicMouthSpecification",
    "decode_magic_mouth",
    "encode_magic_mouth",
    "magic_mouth_message_for_event",
]
