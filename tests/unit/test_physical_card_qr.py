from __future__ import annotations

import json
from pathlib import Path

import pytest

from dnd_board_game.physical_cards import (
    DecisionCardActionKind,
    build_decision_card_qr_payload,
    build_actor_card_qr_payload,
    generate_decision_card_qr,
    normalize_decision_card_scanner_text,
    parse_decision_card_qr_payload,
    parse_actor_card_qr_payload,
    resolve_universal_card_scan,
)


def test_decision_card_payload_round_trip() -> None:
    encoded = build_decision_card_qr_payload("spell", "eldritch_blast")

    assert encoded == "dndbg:v1:action:spell:eldritch_blast"
    assert parse_decision_card_qr_payload(encoded).action_kind is (
        DecisionCardActionKind.SPELL
    )
    assert parse_decision_card_qr_payload(encoded).source_id == "eldritch_blast"


def test_owned_decision_card_payload_round_trip_uses_v2() -> None:
    encoded = build_decision_card_qr_payload(
        "spell",
        "mage_hand",
        actor_id="nimra",
    )

    assert encoded == "dndbg:v2:action:spell:mage_hand:nimra"
    parsed = parse_decision_card_qr_payload(encoded)
    assert parsed.version == 2
    assert parsed.actor_id == "nimra"


def test_owned_v2_payload_requires_owner() -> None:
    with pytest.raises(ValueError, match="must contain an actor owner"):
        build_decision_card_qr_payload("spell", "mage_hand", version=2)


def test_actor_card_payload_round_trip() -> None:
    encoded = build_actor_card_qr_payload("kael")

    assert encoded == "dndbg:v1:actor:kael"
    assert parse_actor_card_qr_payload(encoded).actor_id == "kael"


def test_actor_card_payload_normalizes_keyboard_wedge_separator() -> None:
    assert normalize_decision_card_scanner_text("dndbg>v1>actor>kael") == (
        "dndbg:v1:actor:kael"
    )


def test_keyboard_wedge_scanner_separator_is_normalized() -> None:
    scanned = "dndbg>v1>action>universal>accept"

    assert normalize_decision_card_scanner_text(scanned) == (
        "dndbg:v1:action:universal:accept"
    )


@pytest.mark.parametrize(
    "canonical",
    (
        "dndbg:v2:action:feature:bardic_inspiration:lorian",
        "dndbg:v2:action:spell:healing_word:guild_bard",
        "dndbg:v1:actor:guild_scout",
    ),
)
def test_keyboard_wedge_scanner_normalizes_underscores_for_every_card_payload(
    canonical: str,
) -> None:
    scanned = canonical.replace(":", ">").replace("_", "?")

    normalized = normalize_decision_card_scanner_text(scanned)

    assert normalized == canonical


def test_reported_bardic_inspiration_scan_round_trips() -> None:
    normalized = normalize_decision_card_scanner_text(
        "dndbg>v2>action>feature>bardic?inspiration>lorian"
    )

    parsed = parse_decision_card_qr_payload(normalized)

    assert parsed.action_kind is DecisionCardActionKind.FEATURE
    assert parsed.source_id == "bardic_inspiration"
    assert parsed.actor_id == "lorian"


def test_reported_hunters_mark_scan_round_trips() -> None:
    normalized = normalize_decision_card_scanner_text(
        "dndbg>v2>action>spell>hunters?mark>erynd"
    )

    parsed = parse_decision_card_qr_payload(normalized)

    assert parsed.action_kind is DecisionCardActionKind.SPELL
    assert parsed.source_id == "hunters_mark"
    assert parsed.actor_id == "erynd"


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


@pytest.mark.parametrize("action", ("accept", "decline", "maneuvers", "equipment"))
def test_resolve_universal_control_card(action: str) -> None:
    payload = build_decision_card_qr_payload("universal", action)

    card = resolve_universal_card_scan(payload)

    assert card.action.value == action
    expected_label = {
        "accept": "AKCEPTUJ",
        "decline": "ODRZUĆ",
        "maneuvers": "MANEWRY",
        "equipment": "EKWIPUNEK",
    }[action]
    assert card.player_label == expected_label


def test_resolve_universal_control_card_rejects_other_card_kinds() -> None:
    payload = build_decision_card_qr_payload("spell", "eldritch_blast")

    with pytest.raises(ValueError, match="uniwersalną"):
        resolve_universal_card_scan(payload)
