from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .qr_payload import DecisionCardActionKind, parse_decision_card_qr_payload


class UniversalCardAction(StrEnum):
    ACCEPT = "accept"
    DECLINE = "decline"


@dataclass(frozen=True, slots=True)
class ScannedUniversalCard:
    action: UniversalCardAction
    payload: str

    @property
    def player_label(self) -> str:
        return self.action.value.upper()


def resolve_universal_card_scan(payload: str) -> ScannedUniversalCard:
    parsed = parse_decision_card_qr_payload(payload)
    if parsed.action_kind is not DecisionCardActionKind.UNIVERSAL:
        raise ValueError("Zeskanowana karta nie jest uniwersalną kartą sterującą.")
    try:
        action = UniversalCardAction(parsed.source_id)
    except ValueError as exc:
        raise ValueError("Nieznana uniwersalna karta sterująca.") from exc
    return ScannedUniversalCard(action=action, payload=payload)
