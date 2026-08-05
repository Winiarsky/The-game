from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dnd_board_game.scenarios.content_contract import validate_stable_id


DECISION_CARD_QR_PREFIX = "dndbg"
DECISION_CARD_QR_VERSION = 1
OWNED_DECISION_CARD_QR_VERSION = 2
_ACTION_SEGMENT = "action"
_ACTOR_SEGMENT = "actor"
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
    actor_id: str | None = None

    def __post_init__(self) -> None:
        if self.version not in {
            DECISION_CARD_QR_VERSION,
            OWNED_DECISION_CARD_QR_VERSION,
        }:
            raise ValueError(
                f"Unsupported decision-card QR version: {self.version}."
            )
        validate_stable_id(self.source_id, "decision-card QR source_id")
        if self.actor_id is not None:
            validate_stable_id(self.actor_id, "decision-card QR actor_id")
        if self.version == DECISION_CARD_QR_VERSION and self.actor_id is not None:
            raise ValueError("Decision-card QR v1 cannot contain an actor owner.")
        if self.version == OWNED_DECISION_CARD_QR_VERSION and self.actor_id is None:
            raise ValueError("Decision-card QR v2 must contain an actor owner.")

    def encode(self) -> str:
        payload = (
            f"{DECISION_CARD_QR_PREFIX}:v{self.version}:{_ACTION_SEGMENT}:"
            f"{self.action_kind.value}:{self.source_id}"
        )
        return f"{payload}:{self.actor_id}" if self.actor_id is not None else payload


@dataclass(frozen=True, slots=True)
class ActorCardQrPayload:
    actor_id: str
    version: int = DECISION_CARD_QR_VERSION

    def __post_init__(self) -> None:
        if self.version != DECISION_CARD_QR_VERSION:
            raise ValueError(f"Unsupported actor-card QR version: {self.version}.")
        validate_stable_id(self.actor_id, "actor-card QR actor_id")

    def encode(self) -> str:
        return (
            f"{DECISION_CARD_QR_PREFIX}:v{self.version}:"
            f"{_ACTOR_SEGMENT}:{self.actor_id}"
        )


def build_actor_card_qr_payload(
    actor_id: str,
    *,
    version: int = DECISION_CARD_QR_VERSION,
) -> str:
    return ActorCardQrPayload(actor_id=actor_id, version=version).encode()


def build_decision_card_qr_payload(
    action_kind: DecisionCardActionKind | str,
    source_id: str,
    *,
    version: int | None = None,
    actor_id: str | None = None,
) -> str:
    resolved_version = (
        OWNED_DECISION_CARD_QR_VERSION
        if actor_id is not None and version is None
        else DECISION_CARD_QR_VERSION
        if version is None
        else version
    )
    return DecisionCardQrPayload(
        action_kind=DecisionCardActionKind(action_kind),
        source_id=source_id,
        version=resolved_version,
        actor_id=actor_id,
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
    if len(parts) not in {5, 6}:
        raise ValueError("Decision-card QR payload must contain 5 or 6 segments.")
    prefix, raw_version, action_segment, raw_kind, source_id, *owner = parts
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
        actor_id=owner[0] if owner else None,
    )


def parse_actor_card_qr_payload(value: str) -> ActorCardQrPayload:
    if not isinstance(value, str):
        raise TypeError("Actor-card QR payload must be a string.")
    parts = value.split(":")
    if len(parts) != 4:
        raise ValueError("Actor-card QR payload must contain exactly 4 segments.")
    prefix, raw_version, actor_segment, actor_id = parts
    if prefix != DECISION_CARD_QR_PREFIX:
        raise ValueError("Unknown actor-card QR prefix.")
    if actor_segment != _ACTOR_SEGMENT:
        raise ValueError("Actor-card QR payload does not declare an actor.")
    if not raw_version.startswith("v") or not raw_version[1:].isdigit():
        raise ValueError("Actor-card QR version must use the v<number> format.")
    return ActorCardQrPayload(
        actor_id=actor_id,
        version=int(raw_version[1:]),
    )
