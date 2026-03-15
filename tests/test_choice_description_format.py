from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.interactions_mixin.status_mixin import StatusMixin
from character_creation.catalog import (
    ANCESTRY_FEAT_IDS_BY_ANCESTRY,
    CLASS_FEAT_CHOICES_MANUAL,
    HERITAGE_IDS_BY_ANCESTRY,
)


@dataclass
class _DummyActor(StatusMixin):
    statuses: list = field(default_factory=list)


def _assert_structured(desc: str) -> None:
    text = str(desc or "").strip()
    assert text, "Opis jest pusty."
    assert "Fluff:" in text
    assert "Mechanika:" in text
    assert "Kiedy:" in text
    assert "Efekt:" in text
    assert " | " not in text


def _spell_ids_from_registry() -> set[str]:
    try:
        import GameObjects.events.all_events  # noqa: F401
        from GameObjects.events.registry import list_events
    except Exception:
        return set()

    spell_ids: set[str] = set()
    for event_id, event_cls in (list_events() or {}).items():
        tags = [str(tag or "").strip().lower() for tag in list(getattr(event_cls, "spell_tags", []) or [])]
        tags += [str(tag or "").strip().lower() for tag in list(getattr(event_cls, "default_tags", []) or [])]
        if "cantrip" in tags or "focus" in tags or any(tag.startswith("rank") for tag in tags):
            spell_ids.add(str(event_id).strip().lower())
    return spell_ids


def test_all_key_choice_descriptions_are_structured():
    actor = _DummyActor()
    ids: set[str] = set()

    for values in HERITAGE_IDS_BY_ANCESTRY.values():
        ids.update(str(item or "").strip().lower() for item in list(values or []) if str(item or "").strip())
    for values in ANCESTRY_FEAT_IDS_BY_ANCESTRY.values():
        ids.update(str(item or "").strip().lower() for item in list(values or []) if str(item or "").strip())
    for values in CLASS_FEAT_CHOICES_MANUAL.values():
        ids.update(str(item or "").strip().lower() for item in list(values or []) if str(item or "").strip())

    ids.update(StatusMixin._general_feat_registry().keys())
    for class_map in StatusMixin._class_feat_registry().values():
        ids.update(str(item or "").strip().lower() for item in class_map.keys())

    ids.update(_spell_ids_from_registry())

    assert ids, "Brak identyfikatorow do audytu opisow."
    for choice_id in sorted(ids):
        desc = actor._choice_description(choice_id)
        _assert_structured(desc)


def test_cantrip_choice_descriptions_have_mechanics_text():
    actor = _DummyActor()
    for choice_id in (
        "acid_splash",
        "chill_touch",
        "dancing_lights",
        "detect_magic",
        "electric_arc",
        "guidance",
        "ray_of_frost",
        "produce_flame",
        "light",
        "tanglefoot",
        "shield",
        "ghost_sound",
        "stabilize",
        "daze",
        "disrupt_undead",
        "divine_lance",
        "forbidding_ward",
        "know_direction",
        "message",
        "prestidigitation",
        "read_aura",
        "sigil",
        "telekinetic_projectile",
    ):
        desc = actor._choice_description(choice_id)
        _assert_structured(desc)
        assert "Brak dodatkowego opisu mechaniki." not in desc


def test_daze_description_contains_save_and_status_outcomes():
    actor = _DummyActor()
    desc = actor._choice_description("daze")
    _assert_structured(desc)
    desc = desc.lower()
    assert "will save" in desc
    assert "stunned" in desc


def test_champion_cause_descriptions_have_mechanics_text():
    actor = _DummyActor()
    for choice_id in ("paladin", "redeemer", "liberator"):
        desc = actor._choice_description(choice_id)
        _assert_structured(desc)
        assert "Brak dodatkowego opisu mechaniki." not in desc


def test_champion_deity_descriptions_have_mechanics_text():
    actor = _DummyActor()
    for choice_id in ("iomedae", "sarenrae", "torag", "shelyn", "desna", "abadar", "custom"):
        desc = actor._choice_description(choice_id)
        _assert_structured(desc)
        assert "Brak dodatkowego opisu mechaniki." not in desc


def test_deity_description_contains_weapon_domains_font_and_divine_skill():
    actor = _DummyActor()
    desc = actor._choice_description("abadar")
    _assert_structured(desc)
    desc = desc.lower()
    assert "ulubiona bron:" in desc
    assert "divine skill:" in desc
    assert "dozwolony divine font:" in desc
    assert "domeny:" in desc


def test_class_setup_choice_descriptions_have_mechanics_text():
    actor = _DummyActor()
    ids = (
        # cleric
        "cloistered_cleric",
        "warpriest",
        "heal",
        "harm",
        "asmodeus",
        "calistria",
        "cayden_cailean",
        "desna",
        "iomedae",
        "sarenrae",
        "torag",
        "custom",
        "cities",
        "earth",
        "travel",
        "wealth",
        # druid
        "animal",
        "leaf",
        "storm",
        "wild",
        # ranger
        "flurry",
        "precision",
        "outwit",
        # rogue
        "ruffian",
        "scoundrel",
        "thief",
        # sorcerer
        "aberrant",
        "angelic",
        "draconic",
        "elemental",
        "imperial",
        "undead",
        "black",
        "red",
        "air",
        "water",
        # wizard
        "abjuration",
        "illusion",
        "universalist",
        "improved_familiar_attunement",
        "metamagical_experimentation",
        "spell_blending",
        "spell_substitution",
        "wand",
        "ring",
        "staff",
        "weapon",
        "other_item",
    )
    for choice_id in ids:
        desc = actor._choice_description(choice_id)
        _assert_structured(desc)
        assert "Brak dodatkowego opisu mechaniki." not in desc


def test_descriptions_use_multiline_format_without_pipe_separator():
    actor = _DummyActor()
    for choice_id in ("abadar", "might", "guidance"):
        desc = actor._choice_description(choice_id)
        _assert_structured(desc)
        assert " | " not in desc
        assert "\n- Kiedy:" in desc
        assert "\n- Efekt" in desc


def test_prompt_choice_uses_character_creation_source_when_creation_in_progress(monkeypatch):
    captured: dict[str, str] = {}

    class _UiStub:
        enabled = True
        allow_cli_fallback = False

        @staticmethod
        def prompt_choice(_prompt, *, choices=None, source=None, **_kwargs):
            captured["source"] = str(source or "")
            if choices:
                return choices[0]
            return None

    actor = _DummyActor()
    actor.character_creation_in_progress = True
    monkeypatch.setattr("ui_client.get_ui_client", lambda: _UiStub())

    result = actor._prompt_choice("Test", ["A", "B"], source="status")
    assert result == "A"
    assert captured.get("source") == "character_creation"
