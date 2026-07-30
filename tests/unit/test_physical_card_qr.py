from __future__ import annotations

import json
from pathlib import Path

import pytest

from dnd_board_game.physical_cards import (
    DecisionCardActionKind,
    build_decision_card_qr_payload,
    generate_decision_card_qr,
    parse_decision_card_qr_payload,
)


def test_decision_card_payload_round_trip() -> None:
    encoded = build_decision_card_qr_payload("spell", "eldritch_blast")

    assert encoded == "dndbg:v1:action:spell:eldritch_blast"
    assert parse_decision_card_qr_payload(encoded).action_kind is (
        DecisionCardActionKind.SPELL
    )
    assert parse_decision_card_qr_payload(encoded).source_id == "eldritch_blast"


@pytest.mark.parametrize(
    "payload",
    (
        "other:v1:action:spell:eldritch_blast",
        "dndbg:v2:action:spell:eldritch_blast",
        "dndbg:v1:other:spell:eldritch_blast",
        "dndbg:v1:action:unknown:eldritch_blast",
        "dndbg:v1:action:spell:Eldritch-Blast",
        "dndbg:v1:action:spell",
    ),
)
def test_decision_card_payload_rejects_unknown_or_malformed_values(
    payload: str,
) -> None:
    with pytest.raises(ValueError):
        parse_decision_card_qr_payload(payload)


def test_generate_decision_card_qr_writes_svg_and_metadata(tmp_path: Path) -> None:
    output = tmp_path / "eldritch_blast.svg"
    payload = build_decision_card_qr_payload("spell", "eldritch_blast")

    asset = generate_decision_card_qr(
        payload,
        output,
        label="EB-01",
    )

    assert output.read_text(encoding="utf-8").startswith("<?xml")
    metadata = json.loads(asset.metadata_path.read_text(encoding="utf-8"))
    assert metadata["payload"] == payload
    assert metadata["label"] == "EB-01"
    assert metadata["action_kind"] == "spell"
    assert metadata["source_id"] == "eldritch_blast"
    assert metadata["quiet_zone_modules"] == 4
    assert metadata["error_correction"] == "H"
    assert metadata["total_module_count"] == metadata["module_count"] + 8


def test_generate_decision_card_qr_does_not_overwrite_by_default(
    tmp_path: Path,
) -> None:
    output = tmp_path / "eldritch_blast.png"
    output.write_bytes(b"existing")
    payload = build_decision_card_qr_payload("spell", "eldritch_blast")

    with pytest.raises(FileExistsError):
        generate_decision_card_qr(payload, output, label="EB-01")


def test_generate_decision_card_qr_requires_printable_quiet_zone(
    tmp_path: Path,
) -> None:
    payload = build_decision_card_qr_payload("spell", "eldritch_blast")

    with pytest.raises(ValueError, match="at least 4"):
        generate_decision_card_qr(
            payload,
            tmp_path / "eldritch_blast.svg",
            label="EB-01",
            quiet_zone_modules=3,
        )


def test_generate_decision_card_qr_writes_deterministic_png(
    tmp_path: Path,
) -> None:
    payload = build_decision_card_qr_payload("spell", "eldritch_blast")
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"

    generate_decision_card_qr(payload, first, label="EB-01")
    generate_decision_card_qr(payload, second, label="EB-01")

    assert first.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert first.read_bytes() == second.read_bytes()
