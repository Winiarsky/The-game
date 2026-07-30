from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dnd_board_game.scenarios.content_contract import validate_stable_id


DECISION_CARD_QR_PREFIX = "dndbg"
DECISION_CARD_QR_VERSION = 1
_ACTION_SEGMENT = "action"
_KEYBOARD_WEDGE_SEPARATOR = ">"


class DecisionCardActionKind(StrEnum):
    ATTACK = "attack"
    SPELL = "spell"
    FEATURE = "feature"
    ITEM = "item"
    UNIVERSAL = "universal"


@dataclass(frozen=True, slots=True)
class DecisionCardQrPayload:
    action_kind: DecisionCardActionKind
    source_id: str
    version: int = DECISION_CARD_QR_VERSION

    def __post_init__(self) -> None:
        if self.version != DECISION_CARD_QR_VERSION:
            raise ValueError(
                f"Unsupported decision-card QR version: {self.version}."
            )
        validate_stable_id(self.source_id, "decision-card QR source_id")

    def encode(self) -> str:
        return (
            f"{DECISION_CARD_QR_PREFIX}:v{self.version}:{_ACTION_SEGMENT}:"
            f"{self.action_kind.value}:{self.source_id}"
        )


def build_decision_card_qr_payload(
    action_kind: DecisionCardActionKind | str,
    source_id: str,
    *,
    version: int = DECISION_CARD_QR_VERSION,
) -> str:
    return DecisionCardQrPayload(
        action_kind=DecisionCardActionKind(action_kind),
        source_id=source_id,
        version=version,
    ).encode()


def normalize_decision_card_scanner_text(value: str) -> str:
    """Normalize text emitted by a keyboard-wedge scanner to canonical QR text."""
    if not isinstance(value, str):
        raise TypeError("Decision-card scanner text must be a string.")
    normalized = value.strip().lower()
    if normalized.startswith(f"{DECISION_CARD_QR_PREFIX}{_KEYBOARD_WEDGE_SEPARATOR}"):
        normalized = normalized.replace(_KEYBOARD_WEDGE_SEPARATOR, ":")
    return normalized


def parse_decision_card_qr_payload(value: str) -> DecisionCardQrPayload:
    if not isinstance(value, str):
        raise TypeError("Decision-card QR payload must be a string.")
    parts = value.split(":")
    if len(parts) != 5:
        raise ValueError("Decision-card QR payload must contain exactly 5 segments.")
    prefix, raw_version, action_segment, raw_kind, source_id = parts
    if prefix != DECISION_CARD_QR_PREFIX:
        raise ValueError("Unknown decision-card QR prefix.")
    if action_segment != _ACTION_SEGMENT:
        raise ValueError("Decision-card QR payload does not declare an action.")
    if not raw_version.startswith("v") or not raw_version[1:].isdigit():
        raise ValueError("Decision-card QR version must use the v<number> format.")
    return DecisionCardQrPayload(
        action_kind=DecisionCardActionKind(raw_kind),
        source_id=source_id,
        version=int(raw_version[1:]),
    )
