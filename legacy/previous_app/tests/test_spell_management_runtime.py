from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.base import EventContext, EventResult
from GameObjects.events.magic.magic_event import MagicEvent, MagicEventResolver
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from GameObjects.events.registry import list_events
from spell_management import (
    can_cast_managed_spell,
    initialize_actor_spell_management,
    swap_sorcerer_repertoire_spell,
)
from statuses.base import Status


@dataclass
class DummyActor(StatusMixin):
    name: str = "hero"
    object_id: str = "hero"
    class_name: str = "wizard"
    position: tuple[int, int] | None = (0, 0)
    statuses: list = field(default_factory=list)
    focus_point: int = 0


class _Rank1MagicMissile(MagicEvent):
    name = "magic_missile"
    spell_tags = ["rank1", "arcane", "evocation"]

    def execute(self, ctx: EventContext) -> EventResult:
        _ = ctx
        return EventResult(success=True, consumed_action=True, message="cast")


class _Rank1Fear(MagicEvent):
    name = "fear"
    spell_tags = ["rank1", "arcane", "emotion"]

    def execute(self, ctx: EventContext) -> EventResult:
        _ = ctx
        return EventResult(success=True, consumed_action=True, message="cast")


class _Rank1Soothe(MagicEvent):
    name = "soothe"
    spell_tags = ["rank1", "occult", "emotion", "healing"]

    def execute(self, ctx: EventContext) -> EventResult:
        _ = ctx
        return EventResult(success=True, consumed_action=True, message="cast")


class _CantripDetectMagic(MagicEvent):
    name = "detect_magic"
    spell_tags = ["cantrip", "arcane", "divination"]

    def execute(self, ctx: EventContext) -> EventResult:
        _ = ctx
        return EventResult(success=True, consumed_action=True, message="cast")


class _CantripShield(MagicEvent):
    name = "shield_cantrip"
    spell_tags = ["cantrip", "arcane", "abjuration"]

    def execute(self, ctx: EventContext) -> EventResult:
        _ = ctx
        return EventResult(success=True, consumed_action=True, message="cast")


class _Rank2AcidArrow(MagicEvent):
    name = "acid_arrow"
    spell_tags = ["rank2", "arcane", "evocation"]

    def execute(self, ctx: EventContext) -> EventResult:
        _ = ctx
        return EventResult(success=True, consumed_action=True, message="cast")


def _rank1_test_spell_event(spell_id: str, tradition: str = "divine") -> type[MagicEvent]:
    class _Rank1PreparedSpell(MagicEvent):
        name = str(spell_id)
        spell_tags = ["rank1", str(tradition), "evocation"]

        def execute(self, ctx: EventContext) -> EventResult:
            _ = ctx
            return EventResult(success=True, consumed_action=True, message="cast")

    return _Rank1PreparedSpell


def _game():
    return SimpleNamespace(
        state=object(),
        ui=SimpleNamespace(enabled=False, allow_cli_fallback=False),
        events=None,
        ui_log=lambda *_a, **_k: None,
    )


class _ChoiceUI:
    def __init__(self, answers: list[str] | None = None):
        self.enabled = True
        self.allow_cli_fallback = False
        self._answers = list(answers or [])

    def prompt_choice(self, _prompt, choices=None, **_kwargs):
        if self._answers:
            return self._answers.pop(0)
        if choices:
            return choices[0]
        return None


def _game_with_ui(ui):
    return SimpleNamespace(
        state=object(),
        ui=ui,
        events=None,
        ui_log=lambda *_a, **_k: None,
    )


def test_wizard_prepared_rank1_slots_are_consumed_by_game_state():
    actor = DummyActor()
    actor.wizard_school_spells = ["magic_missile"]
    actor.wizard_prepared_rank1_slots = 2

    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)
    assert state.get("enforce") is True
    assert state.get("slot_remaining", {}).get("rank_1") == 2
    assert list(state.get("prepared_today", {}).get("rank_1", [])) == ["magic_missile", "magic_missile"]

    ctx = EventContext(game=_game(), actor=actor)
    spell = _Rank1MagicMissile()

    first = MagicEventResolver.resolve(spell, ctx)
    second = MagicEventResolver.resolve(spell, ctx)
    third = MagicEventResolver.resolve(spell, ctx)

    assert first.success is True
    assert second.success is True
    assert third.success is False
    assert "brak" in str(third.message or "").lower()
    assert int(getattr(actor, "wizard_prepared_rank1_slots_remaining", 0) or 0) == 0


def test_wizard_unknown_rank1_spell_is_blocked_without_prepared_copy():
    actor = DummyActor()
    actor.wizard_school_spells = ["magic_missile"]
    actor.wizard_prepared_rank1_slots = 2
    initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)

    result = MagicEventResolver.resolve(_Rank1Fear(), EventContext(game=_game(), actor=actor))

    assert result.success is False
    assert "nie jest znany" in str(result.message or "").lower()


def test_wizard_empty_prepared_lists_block_casting():
    actor = DummyActor()
    initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)

    result = MagicEventResolver.resolve(_Rank1MagicMissile(), EventContext(game=_game(), actor=actor))

    assert result.success is False
    assert "brak przygotowanych" in str(result.message or "").lower()


def test_wizard_level3_uses_table_slots_for_rank2_and_consumes_them():
    actor = DummyActor()
    actor.level = 3
    actor.wizard_spellbook = {
        "cantrip": ["detect_magic", "light", "mage_hand", "message", "read_aura"],
        "rank_1": ["magic_missile", "fear", "grease"],
        "rank_2": ["acid_arrow"],
    }
    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)

    assert int((state.get("slot_total", {}) or {}).get("rank_1", 0) or 0) == 3
    assert int((state.get("slot_total", {}) or {}).get("rank_2", 0) or 0) == 2
    assert list((state.get("prepared_today", {}) or {}).get("rank_2", [])) == ["acid_arrow", "acid_arrow"]

    ctx = EventContext(game=_game(), actor=actor)
    first = MagicEventResolver.resolve(_Rank2AcidArrow(), ctx)
    second = MagicEventResolver.resolve(_Rank2AcidArrow(), ctx)
    third = MagicEventResolver.resolve(_Rank2AcidArrow(), ctx)

    assert first.success is True
    assert second.success is True
    assert third.success is False
    assert "brak przygotowanej kopii" in str(third.message or "").lower()


def test_wizard_spell_blending_adjusts_slots_and_cantrip_budget_during_preparation():
    actor = DummyActor()
    actor.level = 3
    actor.statuses = [
        Status(
            id="wizard",
            data={
                "wizard_setup": {
                    "thesis": "spell_blending",
                    "arcane_study": "evocation",
                }
            },
        )
    ]
    actor.wizard_spellbook = {
        "cantrip": ["detect_magic", "light", "mage_hand", "message", "read_aura"],
        "rank_1": ["magic_missile", "fear", "grease"],
        "rank_2": ["acid_arrow"],
    }
    ui = _ChoiceUI(
        [
            "2x ranga 1 -> +1 slot ranga 2 (Spell Blending)",
            "1x ranga 1 -> +2 cantripy",
            "Done",
        ]
    )

    state = initialize_actor_spell_management(_game_with_ui(ui), actor, prompt=True, enforce=True)

    assert int((state.get("slot_total", {}) or {}).get("rank_1", 0) or 0) == 0
    assert int((state.get("slot_total", {}) or {}).get("rank_2", 0) or 0) == 3
    assert int((state.get("slot_total", {}) or {}).get("cantrip", 0) or 0) == 7
    payload = dict(state.get("wizard_spell_blending", {}) or {})
    assert payload.get("enabled") is True
    assert list(payload.get("blends") or []) == [{"source_rank": 1, "target_rank": 2}]
    assert list(payload.get("cantrip_trades") or []) == [1]
    assert int(payload.get("extra_cantrips", 0) or 0) == 2


def test_staff_nexus_daily_preparation_builds_charges_and_reduces_available_slots():
    actor = DummyActor()
    actor.statuses = [
        Status(
            id="wizard",
            data={
                "wizard_setup": {
                    "thesis": "staff_nexus",
                    "arcane_study": "evocation",
                    "school": "evocation",
                    "staff_nexus_cantrip": "detect_magic",
                    "staff_nexus_rank_1_spell": "magic_missile",
                }
            },
        )
    ]
    actor.wizard_spellbook = {
        "cantrip": ["detect_magic", "light", "mage_hand", "message", "read_aura"],
        "rank_1": ["magic_missile", "fear", "grease"],
    }
    ui = _ChoiceUI(["Ranga 1 -> +1 ladunkow Staff Nexus"])

    state = initialize_actor_spell_management(_game_with_ui(ui), actor, prompt=True, enforce=True)

    staff = dict(state.get("wizard_staff_nexus", {}) or {})
    assert staff.get("enabled") is True
    assert staff.get("cantrip_spell") == "detect_magic"
    assert staff.get("rank_1_spell") == "magic_missile"
    assert int(staff.get("base_charges", 0) or 0) == 1
    assert int(staff.get("charges_total", 0) or 0) == 2
    assert list(staff.get("extra_charge_ranks") or []) == [1]
    assert int((state.get("slot_total", {}) or {}).get("rank_1", 0) or 0) == 2


def test_staff_nexus_rank1_spell_can_be_cast_without_prepared_copy_and_spends_charge_instead_of_slot():
    actor = DummyActor()
    actor.statuses = [
        Status(
            id="wizard",
            data={
                "wizard_setup": {
                    "thesis": "staff_nexus",
                    "arcane_study": "evocation",
                    "school": "evocation",
                    "staff_nexus_cantrip": "detect_magic",
                    "staff_nexus_rank_1_spell": "magic_missile",
                }
            },
        )
    ]
    actor.wizard_spellbook = {
        "cantrip": ["detect_magic", "light", "mage_hand", "message", "read_aura"],
        "rank_1": ["magic_missile", "fear", "grease"],
    }
    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)
    state["prepared_today"]["rank_1"] = []
    state["prepared_counts"]["rank_1"] = {}
    state["consumed_counts"]["rank_1"] = {}
    state["slot_remaining"]["rank_1"] = 0
    actor.spell_state = state

    result = MagicEventResolver.resolve(_Rank1MagicMissile(), EventContext(game=_game(), actor=actor))

    assert result.success is True
    staff = dict((getattr(actor, "spell_state", {}) or {}).get("wizard_staff_nexus", {}) or {})
    assert int(staff.get("charges_remaining", 0) or 0) == 0
    assert int(((getattr(actor, "spell_state", {}) or {}).get("slot_remaining", {}) or {}).get("rank_1", 0) or 0) == 0

    second = MagicEventResolver.resolve(_Rank1MagicMissile(), EventContext(game=_game(), actor=actor))
    assert second.success is False


def test_staff_nexus_cantrip_can_be_cast_without_preparing_it():
    actor = DummyActor()
    actor.statuses = [
        Status(
            id="wizard",
            data={
                "wizard_setup": {
                    "thesis": "staff_nexus",
                    "arcane_study": "evocation",
                    "school": "evocation",
                    "staff_nexus_cantrip": "detect_magic",
                    "staff_nexus_rank_1_spell": "magic_missile",
                }
            },
        )
    ]
    actor.wizard_spellbook = {
        "cantrip": ["detect_magic", "light", "mage_hand", "message", "read_aura"],
        "rank_1": ["magic_missile", "fear", "grease"],
    }
    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)
    state["prepared_today"]["cantrip"] = []
    state["prepared_counts"]["cantrip"] = {}
    actor.spell_state = state

    first = MagicEventResolver.resolve(_CantripDetectMagic(), EventContext(game=_game(), actor=actor))
    second = MagicEventResolver.resolve(_CantripDetectMagic(), EventContext(game=_game(), actor=actor))

    assert first.success is True
    assert second.success is True
    staff = dict((getattr(actor, "spell_state", {}) or {}).get("wizard_staff_nexus", {}) or {})
    assert int(staff.get("charges_remaining", 0) or 0) == 1


def test_staff_nexus_prompt_can_prefer_staff_over_prepared_copy():
    actor = DummyActor()
    actor.statuses = [
        Status(
            id="wizard",
            data={
                "wizard_setup": {
                    "thesis": "staff_nexus",
                    "arcane_study": "evocation",
                    "school": "evocation",
                    "staff_nexus_cantrip": "detect_magic",
                    "staff_nexus_rank_1_spell": "magic_missile",
                }
            },
        )
    ]
    actor.wizard_spellbook = {
        "cantrip": ["detect_magic", "light", "mage_hand", "message", "read_aura"],
        "rank_1": ["magic_missile", "fear", "grease"],
    }
    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)
    actor.spell_state = state

    result = MagicEventResolver.resolve(
        _Rank1MagicMissile(),
        EventContext(game=_game_with_ui(_ChoiceUI(["Staff Nexus"])), actor=actor),
    )

    assert result.success is True
    staff = dict((getattr(actor, "spell_state", {}) or {}).get("wizard_staff_nexus", {}) or {})
    assert int(staff.get("charges_remaining", 0) or 0) == 0
    assert int(((getattr(actor, "spell_state", {}) or {}).get("slot_remaining", {}) or {}).get("rank_1", 0) or 0) == 3


def test_sorcerer_unknown_rank1_spell_is_blocked_when_management_is_enforced():
    actor = DummyActor(class_name="sorcerer")
    actor.sorcerer_known_rank_1_spells = ["magic_missile"]
    initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)

    result = MagicEventResolver.resolve(_Rank1Fear(), EventContext(game=_game(), actor=actor))

    assert result.success is False
    assert "nie jest znany" in str(result.message or "").lower()


def test_sorcerer_rank1_slots_are_consumed_by_spell_management():
    actor = DummyActor(class_name="sorcerer")
    actor.sorcerer_known_cantrips = ["detect_magic", "light", "mage_hand", "message", "read_aura"]
    actor.sorcerer_known_rank_1_spells = ["magic_missile"]
    actor.sorcerer_rank_1_slots_per_day = 2

    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)
    assert int((state.get("slot_remaining", {}) or {}).get("rank_1", 0) or 0) == 2

    ctx = EventContext(game=_game(), actor=actor)
    first = MagicEventResolver.resolve(_Rank1MagicMissile(), ctx)
    second = MagicEventResolver.resolve(_Rank1MagicMissile(), ctx)
    third = MagicEventResolver.resolve(_Rank1MagicMissile(), ctx)

    assert first.success is True
    assert second.success is True
    assert third.success is False
    assert "brak slot" in str(third.message or "").lower()
    assert int(getattr(actor, "sorcerer_rank_1_slots_remaining", 0) or 0) == 0


def test_sorcerer_level3_uses_rank2_slots_and_consumes_them():
    actor = DummyActor(class_name="sorcerer")
    actor.level = 3
    actor.sorcerer_known_cantrips = ["detect_magic", "light", "mage_hand", "message", "read_aura"]
    actor.sorcerer_known_rank_1_spells = ["magic_missile", "fear"]
    actor.sorcerer_known_rank_2_spells = ["acid_arrow"]

    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)
    assert int((state.get("slot_total", {}) or {}).get("rank_1", 0) or 0) == 4
    assert int((state.get("slot_total", {}) or {}).get("rank_2", 0) or 0) == 3

    ctx = EventContext(game=_game(), actor=actor)
    first = MagicEventResolver.resolve(_Rank2AcidArrow(), ctx)
    second = MagicEventResolver.resolve(_Rank2AcidArrow(), ctx)
    third = MagicEventResolver.resolve(_Rank2AcidArrow(), ctx)
    fourth = MagicEventResolver.resolve(_Rank2AcidArrow(), ctx)

    assert first.success is True
    assert second.success is True
    assert third.success is True
    assert fourth.success is False
    assert "brak slot" in str(fourth.message or "").lower()
    assert int(getattr(actor, "sorcerer_rank_2_slots_remaining", 0) or 0) == 0


def test_sorcerer_setup_known_spells_are_merged_into_spell_state():
    actor = DummyActor(class_name="sorcerer")
    actor.focus_point = 1
    actor.statuses = [
        Status(
            id="sorcerer",
            data={
                "sorcerer_setup": {
                    "spell_tradition": "primal",
                    "known_cantrips": ["produce_flame", "electric_arc"],
                    "known_rank_1_spells": ["burning_hands", "gust_of_wind", "hydraulic_push"],
                    "bloodline_initial_focus_spell": "elemental_toss",
                    "bloodline_granted_spells": {"rank_1": "burning_hands"},
                    "rank_1_slots_per_day": 3,
                }
            },
        )
    ]

    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)
    rank_1_known = list((state.get("known", {}) or {}).get("rank_1", []) or [])

    assert "burning_hands" in rank_1_known
    assert "gust_of_wind" in rank_1_known
    assert "hydraulic_push" in rank_1_known


def test_sorcerer_signature_spell_allows_casting_on_higher_rank_tier():
    actor = DummyActor(class_name="sorcerer")
    actor.level = 3
    actor.sorcerer_known_cantrips = ["detect_magic", "light", "mage_hand", "message", "read_aura"]
    actor.sorcerer_known_rank_1_spells = ["magic_missile", "fear"]
    actor.sorcerer_signature_spells = ["magic_missile"]

    initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)
    can_cast_signature, _ = can_cast_managed_spell(actor, spell_id="magic_missile", tier="rank_2")
    can_cast_non_signature, _ = can_cast_managed_spell(actor, spell_id="fear", tier="rank_2")

    assert can_cast_signature is True
    assert can_cast_non_signature is False


def test_sorcerer_repertoire_swap_replaces_spell_within_same_tier():
    actor = DummyActor(class_name="sorcerer")
    actor.sorcerer_spell_tradition = "arcane"
    actor.sorcerer_known_cantrips = ["detect_magic", "light", "mage_hand", "message", "read_aura"]
    actor.sorcerer_known_rank_1_spells = ["magic_missile", "fear"]
    actor.statuses = [
        Status(
            id="sorcerer",
            data={
                "sorcerer_setup": {
                    "spell_tradition": "arcane",
                    "bloodline_granted_spells": {"rank_1": "magic_missile"},
                }
            },
        )
    ]

    initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)
    ok, _msg = swap_sorcerer_repertoire_spell(
        actor,
        from_spell="fear",
        to_spell="grease",
        tier="rank_1",
        game=_game(),
    )
    assert ok is True
    rank1 = list(getattr(actor, "sorcerer_known_rank_1_spells", []) or [])
    assert "grease" in rank1
    assert "fear" not in rank1


def test_sorcerer_repertoire_swap_blocks_bloodline_granted_spell():
    actor = DummyActor(class_name="sorcerer")
    actor.sorcerer_spell_tradition = "arcane"
    actor.sorcerer_known_cantrips = ["detect_magic", "light", "mage_hand", "message", "read_aura"]
    actor.sorcerer_known_rank_1_spells = ["magic_missile", "fear"]
    actor.statuses = [
        Status(
            id="sorcerer",
            data={
                "sorcerer_setup": {
                    "spell_tradition": "arcane",
                    "bloodline_granted_spells": {"rank_1": "magic_missile"},
                }
            },
        )
    ]

    initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)
    ok, message = swap_sorcerer_repertoire_spell(
        actor,
        from_spell="magic_missile",
        to_spell="grease",
        tier="rank_1",
        game=_game(),
    )
    assert ok is False
    assert "bloodline" in str(message or "").lower()


def test_cleric_prepares_rank1_slots_with_divine_font_bonus():
    actor = DummyActor(class_name="cleric")
    actor.cleric_font = "heal"
    actor.ability_modifiers = {"charisma": 2}

    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)

    assert int(state.get("cleric_font_slots", 0) or 0) == 3
    assert int((state.get("slot_total", {}) or {}).get("rank_1", 0) or 0) == 5
    assert "heal" in set(state.get("known", {}).get("rank_1", []) or [])


def test_cleric_level2_uses_table_slot_budget_with_font_on_rank1():
    actor = DummyActor(class_name="cleric")
    actor.level = 2
    actor.cleric_font = "heal"
    actor.ability_modifiers = {"charisma": 2}

    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)

    assert state.get("cleric_font_tier") == "rank_1"
    assert int(state.get("cleric_font_slots", 0) or 0) == 3
    assert int((state.get("slot_total", {}) or {}).get("rank_1", 0) or 0) == 6


def test_cleric_level3_moves_font_to_highest_rank():
    actor = DummyActor(class_name="cleric")
    actor.level = 3
    actor.cleric_font = "heal"
    actor.ability_modifiers = {"charisma": 2}

    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)

    assert state.get("cleric_font_tier") == "rank_2"
    assert int(state.get("cleric_font_slots", 0) or 0) == 3
    assert int((state.get("slot_total", {}) or {}).get("rank_1", 0) or 0) == 3
    assert int((state.get("slot_total", {}) or {}).get("rank_2", 0) or 0) == 5


def test_cleric_rank1_casting_consumes_prepared_copy():
    actor = DummyActor(class_name="cleric")
    actor.cleric_font = "heal"
    actor.ability_modifiers = {"charisma": 1}

    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)
    prepared_counts = dict((state.get("prepared_counts", {}) or {}).get("rank_1", {}) or {})
    assert prepared_counts
    spell_id = max(prepared_counts.keys(), key=lambda sid: int(prepared_counts.get(sid, 0) or 0))
    spell_copies = int(prepared_counts.get(spell_id, 0) or 0)
    assert spell_copies > 0

    spell_cls = _rank1_test_spell_event(spell_id, tradition="divine")
    ctx = EventContext(game=_game(), actor=actor)
    for _ in range(spell_copies):
        result = MagicEventResolver.resolve(spell_cls(), ctx)
        assert result.success is True

    blocked = MagicEventResolver.resolve(spell_cls(), ctx)
    assert blocked.success is False
    assert "brak przygotowanej kopii" in str(blocked.message or "").lower()


def test_druid_rank1_casting_consumes_prepared_copy():
    actor = DummyActor(class_name="druid")

    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)
    prepared_counts = dict((state.get("prepared_counts", {}) or {}).get("rank_1", {}) or {})
    assert prepared_counts
    spell_id = max(prepared_counts.keys(), key=lambda sid: int(prepared_counts.get(sid, 0) or 0))
    spell_copies = int(prepared_counts.get(spell_id, 0) or 0)
    assert spell_copies > 0

    spell_cls = _rank1_test_spell_event(spell_id, tradition="primal")
    ctx = EventContext(game=_game(), actor=actor)
    for _ in range(spell_copies):
        result = MagicEventResolver.resolve(spell_cls(), ctx)
        assert result.success is True

    blocked = MagicEventResolver.resolve(spell_cls(), ctx)
    assert blocked.success is False
    assert "brak przygotowanej kopii" in str(blocked.message or "").lower()


def test_druid_level2_uses_table_slot_budget():
    actor = DummyActor(class_name="druid")
    actor.level = 2

    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)

    assert int((state.get("slot_total", {}) or {}).get("rank_1", 0) or 0) == 3
    assert int((state.get("slot_total", {}) or {}).get("rank_2", 0) or 0) == 0


def test_druid_level3_gets_rank2_slots_from_table():
    actor = DummyActor(class_name="druid")
    actor.level = 3

    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)

    assert int((state.get("slot_total", {}) or {}).get("rank_1", 0) or 0) == 3
    assert int((state.get("slot_total", {}) or {}).get("rank_2", 0) or 0) == 2


def test_racial_innate_cantrip_is_collected_as_known_spell():
    actor = DummyActor(class_name="fighter")
    actor.statuses = [
        Status(
            id="otherworldly_magic",
            data={
                "granted_cantrips": ["detect_magic"],
                "innate_magic_tradition": "arcane",
            },
        )
    ]
    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)

    assert "detect_magic" in list(state.get("known", {}).get("cantrip", []) or [])
    assert "detect_magic" in list(state.get("known", {}).get("innate", []) or [])

    result = MagicEventResolver.resolve(_CantripDetectMagic(), EventContext(game=_game(), actor=actor))
    assert result.success is True


def test_innate_shield_alias_is_castable_as_shield_cantrip_event():
    actor = DummyActor(class_name="fighter")
    actor.statuses = [
        Status(
            id="adapted_cantrip",
            data={
                "granted_cantrips": ["shield"],
                "innate_magic_tradition": "arcane",
            },
        )
    ]
    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)

    assert "shield_cantrip" in list(state.get("known", {}).get("cantrip", []) or [])
    assert "shield_cantrip" in list(state.get("known", {}).get("innate", []) or [])

    result = MagicEventResolver.resolve(_CantripShield(), EventContext(game=_game(), actor=actor))
    assert result.success is True


def test_adapted_cantrip_removes_replaced_cantrip_from_prepared_caster_pool():
    actor = DummyActor(class_name="cleric")
    actor.statuses = [
        Status(
            id="adapted_cantrip",
            data={
                "granted_cantrips": ["ray_of_frost"],
                "innate_magic_tradition": "arcane",
                "removed_cantrips": ["detect_magic"],
            },
        )
    ]
    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)

    known = dict(state.get("known", {}) or {})
    assert "detect_magic" not in list(known.get("cantrip", []) or [])
    assert "ray_of_frost" in list(known.get("cantrip", []) or [])
    assert "ray_of_frost" in list(known.get("innate", []) or [])


def test_bard_rank1_slots_are_consumed_by_spell_management():
    actor = DummyActor(class_name="bard")
    actor.bard_known_cantrips = ["daze", "light", "mage_hand", "message", "read_aura"]
    actor.bard_known_rank_1_spells = ["soothe", "fear"]
    actor.bard_rank_1_slots_per_day = 2

    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)
    assert state.get("slot_remaining", {}).get("rank_1") == 2

    ctx = EventContext(game=_game(), actor=actor)
    first = MagicEventResolver.resolve(_Rank1Soothe(), ctx)
    second = MagicEventResolver.resolve(_Rank1Soothe(), ctx)
    third = MagicEventResolver.resolve(_Rank1Soothe(), ctx)

    assert first.success is True
    assert second.success is True
    assert third.success is False
    assert "brak slot" in str(third.message or "").lower()
    assert int(getattr(actor, "bard_rank_1_slots_remaining", 0) or 0) == 0


def test_bard_level1_crb_baseline_repertoire_counts():
    actor = DummyActor(class_name="bard")
    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)

    known = dict(state.get("known", {}) or {})
    cantrips = list(known.get("cantrip", []) or [])
    rank1 = list(known.get("rank_1", []) or [])
    focus = list(known.get("focus", []) or [])

    # CRB lvl 1 bard: 5 cantrips + 2 composition cantrips.
    assert len(cantrips) == 7
    assert "inspire_courage" in cantrips
    assert "counter_performance" in cantrips
    assert len(rank1) >= 2
    assert "counter_performance" in focus
    assert int(state.get("slot_remaining", {}).get("rank_1", 0) or 0) == 2


def test_bard_spontaneous_casting_allows_repeating_same_known_rank1_spell():
    actor = DummyActor(class_name="bard")
    actor.bard_known_cantrips = ["daze", "light", "mage_hand", "message", "read_aura"]
    actor.bard_known_rank_1_spells = ["soothe", "fear"]
    actor.bard_rank_1_slots_per_day = 2
    initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)

    ctx = EventContext(game=_game(), actor=actor)
    # spontaneous casting: Fear + Fear is legal if spell is known.
    first = MagicEventResolver.resolve(_Rank1Fear(), ctx)
    second = MagicEventResolver.resolve(_Rank1Fear(), ctx)
    third = MagicEventResolver.resolve(_Rank1Fear(), ctx)

    assert first.success is True
    assert second.success is True
    assert third.success is False
    assert "brak slot" in str(third.message or "").lower()


def test_bard_cantrip_casts_do_not_consume_rank1_slots():
    actor = DummyActor(class_name="bard")
    actor.bard_known_cantrips = ["detect_magic", "daze", "light", "mage_hand", "message"]
    actor.bard_known_rank_1_spells = ["soothe", "fear"]
    actor.bard_rank_1_slots_per_day = 2
    initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)

    ctx = EventContext(game=_game(), actor=actor)
    r1 = MagicEventResolver.resolve(_CantripDetectMagic(), ctx)
    r2 = MagicEventResolver.resolve(_CantripDetectMagic(), ctx)
    r3 = MagicEventResolver.resolve(_CantripDetectMagic(), ctx)
    assert r1.success is True
    assert r2.success is True
    assert r3.success is True

    state = dict(getattr(actor, "spell_state", {}) or {})
    assert int((state.get("slot_remaining", {}) or {}).get("rank_1", 0) or 0) == 2


def test_bard_level1_baseline_spells_are_occult():
    actor = DummyActor(class_name="bard")
    state = initialize_actor_spell_management(_game(), actor, prompt=False, enforce=True)
    known = dict(state.get("known", {}) or {})
    spells_to_check = list(known.get("cantrip", []) or []) + list(known.get("rank_1", []) or [])

    registry = dict(list_events() or {})

    def _has_occult_tag(spell_id: str) -> bool:
        event_cls = registry.get(str(spell_id or "").strip().lower())
        if event_cls is None:
            return False
        tags = set()
        for tag in list(getattr(event_cls, "spell_tags", []) or []):
            tags.add(str(tag or "").strip().lower().replace("-", "_").replace(" ", "_"))
        for tag in list(getattr(event_cls, "default_tags", []) or []):
            tags.add(str(tag or "").strip().lower().replace("-", "_").replace(" ", "_"))
        return "occult" in tags

    for spell_id in spells_to_check:
        assert _has_occult_tag(spell_id), f"{spell_id} should be occult for lvl1 bard baseline."
