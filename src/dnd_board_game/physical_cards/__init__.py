"""Physical player-interface contracts and printable asset generation."""

from .qr_generation import GeneratedQrAsset, generate_decision_card_qr
from .qr_payload import (
    DECISION_CARD_QR_VERSION,
    DecisionCardActionKind,
    DecisionCardQrPayload,
    build_decision_card_qr_payload,
    normalize_decision_card_scanner_text,
    parse_decision_card_qr_payload,
)
from .universal_actions import (
    ScannedUniversalCard,
    UniversalCardAction,
    resolve_universal_card_scan,
)

__all__ = [
    "DECISION_CARD_QR_VERSION",
    "DecisionCardActionKind",
    "DecisionCardQrPayload",
    "GeneratedQrAsset",
    "ScannedUniversalCard",
    "UniversalCardAction",
    "build_decision_card_qr_payload",
    "generate_decision_card_qr",
    "normalize_decision_card_scanner_text",
    "parse_decision_card_qr_payload",
    "resolve_universal_card_scan",
]
