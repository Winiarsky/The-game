from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys
import unicodedata

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


def _ascii_lower(text: str) -> str:
    normalized = str(text or "").translate(str.maketrans({"ł": "l", "Ł": "L"}))
    return unicodedata.normalize("NFKD", normalized).encode("ascii", "ignore").decode("ascii").lower()


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
    desc = _ascii_lower(desc)
    assert "ulubiona bron:" in desc
    assert "divine skill:" in desc
    assert "dozwolony divine font:" in desc
    assert "domeny do wyboru:" in desc
    assert "czar domenowy:" in desc
    assert "advanced domain spell:" in desc


def test_cleric_deity_description_lists_domain_spells_for_cayden_cailean():
    actor = _DummyActor()
    desc = actor._choice_description("cayden_cailean")
    _assert_structured(desc)
    desc = _ascii_lower(desc)
    assert "wybor bostwa kleryka." not in desc
    assert "bog wolnosci" in desc
    assert "rapier" in desc
    assert "twarz w tlumie" in desc
    assert "nieskrepowany krok" in desc
    assert "przejedzenie" in desc
    assert "atletyczny zryw" in desc


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
        "staff_nexus",
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


def test_rogue_racket_descriptions_include_concrete_runtime_mechanics():
    actor = _DummyActor()

    ruffian = actor._choice_description("ruffian").lower()
    assert "intimidation" in ruffian
    assert "medium armor" in ruffian
    assert "todo" in ruffian

    scoundrel = actor._choice_description("scoundrel").lower()
    assert "deception" in scoundrel
    assert "diplomacy" in scoundrel
    assert "feint" in scoundrel
    assert "off-guard" in scoundrel

    thief = actor._choice_description("thief").lower()
    assert "thievery" in thief
    assert "finesse melee" in thief
    assert "dex zamiast str" in thief


def test_sorcerer_bloodline_descriptions_include_spell_and_focus_details():
    actor = _DummyActor()

    imperial = _ascii_lower(actor._choice_description("imperial"))
    assert "magiczny pocisk" in imperial
    assert "pamiec przodkow" in imperial
    assert "blood magic" in imperial


def test_wizard_study_and_thesis_descriptions_include_runtime_mechanics():
    actor = _DummyActor()

    universalist = _ascii_lower(actor._choice_description("universalist"))
    assert "dlon adepta" in universalist
    assert "dodatkowy class feat" in universalist

    abjuration = _ascii_lower(actor._choice_description("abjuration"))
    assert "ochronna aura" in abjuration
    assert "bonusowy czar" in abjuration

    staff_nexus = _ascii_lower(actor._choice_description("staff_nexus"))
    assert "bonded item" in staff_nexus
    assert "kostur" in staff_nexus


def test_twin_feint_description_mentions_two_actions_and_second_attack_off_guard():
    actor = _DummyActor()
    raw = actor._choice_description("twin_feint")
    _assert_structured(raw)
    desc = raw.lower()
    assert "koszt: 2 akcje" in desc
    assert "2 melee strikes" in desc or "2 melee strike" in desc
    assert "drugi atak" in desc
    assert "off-guard" in desc


def test_druid_order_descriptions_list_feat_and_spell_on_separate_lines():
    actor = _DummyActor()
    expected = {
        "animal": ("zwierzecy towarzysz", "ulecz zwierze", "command animal companion"),
        "leaf": ("leshy chowaniec", "dobra jagoda", "command familiar"),
        "storm": ("zrodzony z burzy", "poryw burzy", "clumsy 2"),
        "wild": ("dziki ksztalt", "dzika mutacja", "focus spell za 1"),
    }

    for choice_id, (feat_label, spell_label, rules_hint) in expected.items():
        desc = actor._choice_description(choice_id)
        _assert_structured(desc)
        low = _ascii_lower(desc)
        assert "trained skill=" not in low
        assert "\n  - feat startowy - " in low
        assert "\n  - order spell - " in low
        assert feat_label in low
        assert spell_label in low
        assert rules_hint in low


def test_animal_companion_type_description_uses_runtime_details_instead_of_generic_fallback():
    actor = _DummyActor()
    desc = actor._choice_description("cat")
    _assert_structured(desc)
    low = _ascii_lower(desc)
    assert "efekt zalezy od opcji" not in low
    assert "predkosc: 35 ft." in low
    assert "ataki:" in low
    assert "jaws 1d6" in low
    assert "claw 1d4" in low
    assert "support:" in low
    assert "flat-footed" in low or "off-guard" in low


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
