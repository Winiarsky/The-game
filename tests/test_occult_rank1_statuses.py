from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from statuses import (
    CharmedStatus,
    FloatingDiskStatus,
    IllusoryDisguiseStatus,
    MageArmorStatus,
    MindlinkStatus,
    SleepStatus,
    SpiritLinkCasterStatus,
    SpiritLinkTargetStatus,
    SummonedFeyStatus,
    TrueStrikeStatus,
    UnseenServantStatus,
    VentriloquismStatus,
)


def test_basic_occult_rank1_status_ids():
    assert CharmedStatus().id == "charmed"
    assert FloatingDiskStatus().id == "floating_disk"
    assert MageArmorStatus().id == "mage_armor"
    assert SummonedFeyStatus().id == "summoned_fey"
    assert TrueStrikeStatus().id == "true_strike"
    assert UnseenServantStatus().id == "unseen_servant"
    assert VentriloquismStatus().id == "ventriloquism"


def test_illusory_disguise_keeps_persona_in_data():
    status = IllusoryDisguiseStatus(persona="guard", source="spell:test")
    assert status.id == "illusory_disguise"
    assert status.data.get("persona") == "guard"
    assert status.source == "spell:test"


def test_mindlink_and_sleep_store_source_fields():
    mindlink = MindlinkStatus(source_id="caster-1", source_turns_left=3)
    sleep = SleepStatus(source_id="caster-1", source_turns_left=2)

    assert mindlink.data.get("source_id") == "caster-1"
    assert mindlink.data.get("source_turns_left") == 3
    assert sleep.data.get("source_id") == "caster-1"
    assert sleep.data.get("source_turns_left") == 2


def test_spirit_link_statuses_store_counterparty_id():
    caster = SpiritLinkCasterStatus(target_id="ally-2")
    target = SpiritLinkTargetStatus(source_id="caster-1")

    assert caster.id == "spirit_link_caster"
    assert caster.data.get("target_id") == "ally-2"
    assert target.id == "spirit_link_target"
    assert target.data.get("source_id") == "caster-1"
