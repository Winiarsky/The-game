from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from states.intent_menu import filter_magic_events_for_actor


class _MoveEvent:
    __module__ = "GameObjects.events.move_event"
    default_tags = ["move"]


class _MagicMissileEvent:
    __module__ = "GameObjects.events.magic.level_1st.events"
    default_tags = ["magic", "spell"]
    spell_tags = ["rank1", "arcane", "evocation"]


class _BurningHandsEvent:
    __module__ = "GameObjects.events.magic.level_1st.events"
    default_tags = ["magic", "spell"]
    spell_tags = ["rank1", "arcane", "evocation"]


class _MagicMissileRank2Event:
    __module__ = "GameObjects.events.magic.level_1st.events"
    default_tags = ["magic", "spell"]
    spell_tags = ["rank2", "arcane", "evocation"]


class _ReachSpellEvent:
    __module__ = "GameObjects.events.reach_spell_event"
    default_tags = ["manipulate", "metamagic", "spell", "magic"]
    spell_tags: list[str] = []


class _LingeringCompositionEvent:
    __module__ = "GameObjects.events.lingering_composition_event"
    default_tags = ["magic", "spell", "metamagic", "composition"]
    spell_tags: list[str] = []


@dataclass
class _Actor:
    class_name: str = "wizard"
    spell_state: dict = field(default_factory=dict)
    statuses: list = field(default_factory=list)

    def has_status(self, status_id: str) -> bool:
        needle = str(status_id or "").strip().lower()
        for status in list(self.statuses or []):
            if str(getattr(status, "id", status) or "").strip().lower() == needle:
                return True
        return False


def test_magic_bucket_keeps_only_known_castable_spells_for_actor():
    actor = _Actor(
        spell_state={
            "enabled": True,
            "enforce": True,
            "class_name": "wizard",
            "known": {
                "cantrip": [],
                "focus": [],
                "rank_1": ["magic_missile"],
                "innate": [],
            },
            "prepared_today": {"cantrip": [], "rank_1": ["magic_missile"]},
            "prepared_counts": {"rank_1": {"magic_missile": 1}},
            "consumed_counts": {"rank_1": {}},
            "slot_remaining": {"rank_1": 1},
        }
    )
    events = {
        "move": _MoveEvent,
        "magic_missile": _MagicMissileEvent,
        "burning_hands": _BurningHandsEvent,
    }

    filtered = filter_magic_events_for_actor(events, actor=actor, game=SimpleNamespace(ui=None))

    assert "move" in filtered
    assert "magic_missile" in filtered
    assert "burning_hands" not in filtered


def test_magic_bucket_hides_spell_when_no_resources_left():
    actor = _Actor(
        spell_state={
            "enabled": True,
            "enforce": True,
            "class_name": "wizard",
            "known": {
                "cantrip": [],
                "focus": [],
                "rank_1": ["magic_missile"],
                "innate": [],
            },
            "prepared_today": {"cantrip": [], "rank_1": ["magic_missile"]},
            "prepared_counts": {"rank_1": {"magic_missile": 1}},
            "consumed_counts": {"rank_1": {"magic_missile": 1}},
            "slot_remaining": {"rank_1": 0},
        }
    )
    events = {
        "move": _MoveEvent,
        "magic_missile": _MagicMissileEvent,
    }

    filtered = filter_magic_events_for_actor(events, actor=actor, game=SimpleNamespace(ui=None))

    assert "move" in filtered
    assert "magic_missile" not in filtered


def test_magic_bucket_hides_metamagic_action_without_feat_status():
    actor = _Actor(
        class_name="fighter",
        spell_state={
            "enabled": False,
            "enforce": False,
            "class_name": "fighter",
            "known": {"cantrip": [], "focus": [], "rank_1": [], "innate": []},
        },
    )
    events = {
        "move": _MoveEvent,
        "reach_spell": _ReachSpellEvent,
    }

    filtered_without = filter_magic_events_for_actor(events, actor=actor, game=SimpleNamespace(ui=None))
    assert "reach_spell" not in filtered_without

    actor.statuses.append(SimpleNamespace(id="reach_spell"))
    filtered_with = filter_magic_events_for_actor(events, actor=actor, game=SimpleNamespace(ui=None))
    assert "reach_spell" in filtered_with


def test_magic_bucket_hides_lingering_composition_without_feat_status():
    actor = _Actor(
        class_name="fighter",
        spell_state={
            "enabled": False,
            "enforce": False,
            "class_name": "fighter",
            "known": {"cantrip": [], "focus": [], "rank_1": [], "innate": []},
        },
    )
    events = {
        "lingering_composition": _LingeringCompositionEvent,
    }

    filtered_without = filter_magic_events_for_actor(events, actor=actor, game=SimpleNamespace(ui=None))
    assert "lingering_composition" not in filtered_without

    actor.statuses.append(SimpleNamespace(id="lingering_composition"))
    filtered_with = filter_magic_events_for_actor(events, actor=actor, game=SimpleNamespace(ui=None))
    assert "lingering_composition" in filtered_with


def test_magic_bucket_keeps_signature_spell_for_sorcerer_on_higher_rank():
    actor = _Actor(
        class_name="sorcerer",
        spell_state={
            "enabled": True,
            "enforce": True,
            "class_name": "sorcerer",
            "known": {
                "cantrip": [],
                "focus": [],
                "rank_1": ["magic_missile"],
                "rank_2": [],
                "innate": [],
            },
            "sorcerer_signature_spells": ["magic_missile"],
            "prepared_today": {"cantrip": [], "rank_1": ["magic_missile"], "rank_2": []},
            "slot_remaining": {"rank_1": 1, "rank_2": 1},
        },
    )
    events = {
        "magic_missile": _MagicMissileRank2Event,
    }

    filtered = filter_magic_events_for_actor(events, actor=actor, game=SimpleNamespace(ui=None))

    assert "magic_missile" in filtered


def test_magic_bucket_keeps_staff_nexus_spells_when_prepared_copy_is_missing():
    actor = _Actor(
        spell_state={
            "enabled": True,
            "enforce": True,
            "class_name": "wizard",
            "known": {
                "cantrip": ["detect_magic"],
                "focus": [],
                "rank_1": ["magic_missile"],
                "innate": [],
            },
            "prepared_today": {"cantrip": [], "rank_1": []},
            "prepared_counts": {"cantrip": {}, "rank_1": {}},
            "consumed_counts": {"rank_1": {}},
            "slot_remaining": {"rank_1": 0},
            "wizard_staff_nexus": {
                "enabled": True,
                "cantrip_spell": "detect_magic",
                "rank_1_spell": "magic_missile",
                "charges_total": 1,
                "charges_remaining": 1,
            },
        },
        statuses=[
            SimpleNamespace(
                id="wizard",
                data={"wizard_setup": {"thesis": "staff_nexus", "arcane_study": "evocation"}}
            )
        ],
    )
    events = {
        "magic_missile": _MagicMissileEvent,
        "detect_magic": type(
            "_DetectMagicEvent",
            (),
            {
                "__module__": "GameObjects.events.magic.cantrips.events",
                "default_tags": ["magic", "spell"],
                "spell_tags": ["cantrip", "arcane", "divination"],
            },
        ),
    }

    filtered = filter_magic_events_for_actor(events, actor=actor, game=SimpleNamespace(ui=None))

    assert "magic_missile" in filtered
    assert "detect_magic" in filtered
