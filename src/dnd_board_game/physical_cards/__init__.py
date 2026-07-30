"""Physical player-interface contracts and printable asset generation."""

from .qr_generation import GeneratedQrAsset, generate_decision_card_qr
from .qr_payload import (
    DECISION_CARD_QR_VERSION,
    DecisionCardActionKind,
    DecisionCardQrPayload,
    build_decision_card_qr_payload,
    parse_decision_card_qr_payload,
)

__all__ = [
    "DECISION_CARD_QR_VERSION",
    "DecisionCardActionKind",
    "DecisionCardQrPayload",
    "GeneratedQrAsset",
    "build_decision_card_qr_payload",
    "generate_decision_card_qr",
    "parse_decision_card_qr_payload",
]
