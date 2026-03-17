from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.interactions_mixin.status_mixin import StatusMixin
from statuses.classes.champion.feats.ranged_reprisal import RANGED_REPRISAL_STATUS
from statuses.race.human.feats.adapted_cantrip import ADAPTED_CANTRIP_STATUS
from statuses.race.human.feats.elf_atavism import ELF_ATAVISM_STATUS
from statuses.race.human.feats.general_training import GENERAL_TRAINING_STATUS
from statuses.race.human.feats.natural_ambition import NATURAL_AMBITION_STATUS
from statuses.race.human.feats.natural_skill import NATURAL_SKILL_STATUS
from statuses.race.human.feats.unconventional_weaponry import UNCONVENTIONAL_WEAPONRY_STATUS
from statuses.race.human.heritages.skilled_heritage import SKILLED_HERITAGE_STATUS
from statuses.race.human.heritages.versatile_heritage import VERSATILE_HERITAGE_STATUS


class DummyUI:
    def __init__(self, answers: list[str]):
        self.answers = list(answers)
        self.enabled = True
        self.allow_cli_fallback = False

    def prompt_choice(self, _prompt: str, choices=None, **_kwargs):
        if self.answers:
            return self.answers.pop(0)
        if choices:
            return choices[0]
        return None


class CaptureUI(DummyUI):
    def __init__(self, answers: list[str]):
        super().__init__(answers)
        self.calls: list[dict] = []

    def prompt_choice(self, _prompt: str, choices=None, **kwargs):
        self.calls.append({"choices": list(choices or []), **kwargs})
        return super().prompt_choice(_prompt, choices=choices, **kwargs)


class DummyHero(StatusMixin):
    def __init__(self):
        super().__init__()
        self.messages: list[str] = []

    def ui_log(self, message: str) -> None:
        self.messages.append(str(message))


def test_general_training_choice_grants_selected_general_feat(monkeypatch):
    ui = DummyUI(["Toughness"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(GENERAL_TRAINING_STATUS)

    assert hero.has_status("general_training")
    assert hero.get_status_data("general_training", "general_feat", None) == "toughness"
    assert hero.has_status("toughness")


def test_versatile_heritage_choice_grants_selected_general_feat(monkeypatch):
    ui = DummyUI(["Fleet"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(VERSATILE_HERITAGE_STATUS)

    assert hero.has_status("versatile_heritage")
    assert hero.get_status_data("versatile_heritage", "general_feat", None) == "fleet"
    assert hero.has_status("fleet")


def test_versatile_heritage_can_select_arcane_sense(monkeypatch):
    ui = DummyUI(["Arcane Sense"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(VERSATILE_HERITAGE_STATUS)

    assert hero.get_status_data("versatile_heritage", "general_feat", None) == "arcane_sense"
    assert hero.has_status("arcane_sense")
    assert hero.get_status_data("arcane_sense", "granted_cantrips", []) == ["detect_magic"]


def test_versatile_heritage_prompt_uses_polish_labels_and_choice_descriptions(monkeypatch):
    ui = CaptureUI(["fleet"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(VERSATILE_HERITAGE_STATUS)

    assert ui.calls
    first = ui.calls[0]
    choice_meta = list(first.get("choice_meta") or [])
    assert choice_meta
    fleet_entry = next((item for item in choice_meta if str(item.get("raw")) == "fleet"), None)
    assert fleet_entry is not None
    assert str(fleet_entry.get("label") or "").strip() == "Szybki krok"
    assert str(fleet_entry.get("desc") or "").strip()


def test_natural_ambition_uses_actor_class_and_grants_selected_class_feat(monkeypatch):
    ui = DummyUI(["Reach Spell"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.class_name = "bard"
    hero.add_status(NATURAL_AMBITION_STATUS)

    assert hero.has_status("natural_ambition")
    assert hero.get_status_data("natural_ambition", "class_name", None) == "bard"
    assert hero.get_status_data("natural_ambition", "class_feat", None) == "reach_spell"
    assert hero.has_status("reach_spell")


def test_natural_ambition_without_supported_class_stops_cleanly(monkeypatch):
    ui = DummyUI(["Reach Spell"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.class_name = "inventor"
    hero.add_status(NATURAL_AMBITION_STATUS)

    assert hero.get_status_data("natural_ambition", "class_feat", None) is None
    assert not hero.has_status("reach_spell")
    assert any("brak wspieranej klasy" in message.lower() for message in hero.messages)


def test_natural_ambition_for_cleric_grants_holy_castigation(monkeypatch):
    ui = DummyUI(["Holy Castigation"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.class_name = "cleric"
    hero.add_status(NATURAL_AMBITION_STATUS)

    assert hero.get_status_data("natural_ambition", "class_name", None) == "cleric"
    assert hero.get_status_data("natural_ambition", "class_feat", None) == "holy_castigation"
    assert hero.has_status("holy_castigation")


def test_natural_ambition_for_champion_grants_real_class_feat(monkeypatch):
    ui = DummyUI(["Ranged Reprisal"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.class_name = "champion"
    hero.champion_cause = "paladin"
    hero.add_status(NATURAL_AMBITION_STATUS)

    assert hero.get_status_data("natural_ambition", "class_name", None) == "champion"
    assert hero.get_status_data("natural_ambition", "class_feat", None) == "ranged_reprisal"
    assert hero.has_status("ranged_reprisal")
    assert not hero.has_status("raise_shield_allow")
    assert not hero.has_status("deific_weapon")


def test_natural_ambition_for_champion_without_cause_offers_deitys_domain(monkeypatch):
    ui = CaptureUI(["Domena bostwa"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.class_name = "champion"
    hero.add_status(NATURAL_AMBITION_STATUS)

    assert hero.get_status_data("natural_ambition", "class_feat", None) == "deitys_domain"
    first = ui.calls[0]
    choice_meta = list(first.get("choice_meta") or [])
    choice_ids = {str(item.get("raw") or "").strip().lower() for item in choice_meta}
    assert choice_ids == {"deitys_domain"}


def test_natural_ambition_for_champion_filters_choices_by_cause(monkeypatch):
    ui = CaptureUI(["Weight Of Guilt"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.class_name = "champion"
    hero.champion_cause = "redeemer"
    hero.add_status(NATURAL_AMBITION_STATUS)

    assert hero.get_status_data("natural_ambition", "class_feat", None) == "weight_of_guilt"
    assert hero.has_status("weight_of_guilt")
    assert ui.calls
    first = ui.calls[0]
    choice_meta = list(first.get("choice_meta") or [])
    choice_ids = {str(item.get("raw") or "").strip().lower() for item in choice_meta}
    assert choice_ids == {"deitys_domain", "weight_of_guilt"}


def test_natural_ambition_reprompts_when_feat_would_duplicate(monkeypatch):
    ui = DummyUI(["Ranged Reprisal", "deitys_domain"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.class_name = "champion"
    hero.champion_cause = "paladin"
    hero.add_status(RANGED_REPRISAL_STATUS)

    hero.add_status(NATURAL_AMBITION_STATUS)

    assert hero.get_status_data("natural_ambition", "class_feat", None) == "deitys_domain"
    assert hero.has_status("deitys_domain")


def test_natural_ambition_for_druid_grants_widen_spell(monkeypatch):
    ui = DummyUI(["Widen Spell"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.class_name = "druid"
    hero.add_status(NATURAL_AMBITION_STATUS)

    assert hero.get_status_data("natural_ambition", "class_name", None) == "druid"
    assert hero.get_status_data("natural_ambition", "class_feat", None) == "widen_spell"
    assert hero.has_status("widen_spell")


def test_natural_ambition_for_sorcerer_grants_familiar(monkeypatch):
    ui = DummyUI(["Familiar"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.class_name = "sorcerer"
    hero.add_status(NATURAL_AMBITION_STATUS)

    assert hero.get_status_data("natural_ambition", "class_name", None) == "sorcerer"
    assert hero.get_status_data("natural_ambition", "class_feat", None) == "familiar"
    assert hero.has_status("familiar")
    assert hero.has_status("FamiliarOwner")


def test_natural_ambition_for_wizard_grants_eschew_materials(monkeypatch):
    ui = DummyUI(["Eschew Materials"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.class_name = "wizard"
    hero.add_status(NATURAL_AMBITION_STATUS)

    assert hero.get_status_data("natural_ambition", "class_name", None) == "wizard"
    assert hero.get_status_data("natural_ambition", "class_feat", None) == "eschew_materials"
    assert hero.has_status("eschew_materials")


def test_natural_ambition_for_wizard_does_not_offer_hand_of_the_apprentice():
    choices = list(
        ((NATURAL_AMBITION_STATUS.data or {}).get("natural_ambition_class_feat_choices") or {}).get("wizard") or []
    )

    assert "hand_of_the_apprentice" not in choices


def test_adapted_cantrip_records_selected_choices(monkeypatch):
    ui = DummyUI(["Divine", "Guidance", "Detect Magic"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.class_name = "wizard"
    hero.wizard_spellbook = {"cantrip": ["detect_magic", "ray_of_frost", "mage_hand"], "rank_1": []}
    hero.add_status(ADAPTED_CANTRIP_STATUS)

    assert hero.has_status("adapted_cantrip")
    assert hero.get_status_data("adapted_cantrip", "adapted_tradition", None) == "divine"
    assert hero.get_status_data("adapted_cantrip", "adapted_cantrip", None) == "guidance"
    assert hero.get_status_data("adapted_cantrip", "replaced_cantrip", None) == "detect_magic"
    assert hero.get_status_data("adapted_cantrip", "removed_cantrips", []) == ["detect_magic"]
    assert hero.get_status_data("adapted_cantrip", "granted_cantrips", []) == ["guidance"]
    assert hero.get_status_data("adapted_cantrip", "innate_magic_tradition", None) == "divine"
    assert list((hero.wizard_spellbook or {}).get("cantrip") or []) == ["guidance", "ray_of_frost", "mage_hand"]


def test_adapted_cantrip_uses_dynamic_tradition_and_cantrip_pools(monkeypatch):
    ui = CaptureUI(["Divine", "Guidance", "Detect Magic"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.class_name = "wizard"
    hero.wizard_spellbook = {"cantrip": ["detect_magic", "ray_of_frost", "mage_hand"], "rank_1": []}
    hero.add_status(ADAPTED_CANTRIP_STATUS)

    assert len(ui.calls) >= 3
    first_meta = list(ui.calls[0].get("choice_meta") or [])
    second_meta = list(ui.calls[1].get("choice_meta") or [])
    third_meta = list(ui.calls[2].get("choice_meta") or [])

    assert "arcane" not in {str(item.get("raw") or "") for item in first_meta}
    assert {str(item.get("raw") or "") for item in first_meta} == {"divine", "occult", "primal"}
    assert "stabilize" in {str(item.get("raw") or "") for item in second_meta}
    assert "divine_lance" in {str(item.get("raw") or "") for item in second_meta}
    assert {str(item.get("raw") or "") for item in third_meta} == {"detect_magic", "ray_of_frost", "mage_hand"}


def test_adapted_cantrip_requires_spellcasting_class_feature(monkeypatch):
    ui = DummyUI(["Arcane", "Shield", "Detect Magic"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    added = hero.add_status(ADAPTED_CANTRIP_STATUS)

    assert added is False
    assert hero.has_status("adapted_cantrip") is False


def test_skilled_heritage_records_selected_skill(monkeypatch):
    ui = DummyUI(["Stealth"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(SKILLED_HERITAGE_STATUS)

    assert hero.has_status("skilled_heritage")
    assert hero.get_status_data("skilled_heritage", "skilled_heritage_skill", None) == "stealth"
    assert hero.get_status_data("skilled_heritage", "trained_skills", []) == ["stealth"]


def test_natural_skill_records_two_selected_skills(monkeypatch):
    ui = DummyUI(["Arcana", "Society"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(NATURAL_SKILL_STATUS)

    trained = hero.get_status_data("natural_skill", "trained_skills", [])
    assert trained == ["arcana", "society"]
    selected = hero.get_status_data("natural_skill", "natural_skill_selected_skills", [])
    assert selected == ["arcana", "society"]


def test_unconventional_weaponry_records_selected_weapon(monkeypatch):
    ui = DummyUI(["Falchion"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(UNCONVENTIONAL_WEAPONRY_STATUS)

    assert hero.has_status("unconventional_weaponry")
    assert hero.get_status_data("unconventional_weaponry", "weapon_name", None) == "falchion"
    assert hero.get_status_data("unconventional_weaponry", "counts_as", None) == "simple"
    overrides = hero.get_status_data("unconventional_weaponry", "weapon_proficiency_overrides", {})
    assert overrides.get("falchion") == "trained"


def test_elf_atavism_grants_selected_elf_heritage(monkeypatch):
    ui = DummyUI(["Seer Elf"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.add_status(ELF_ATAVISM_STATUS)

    assert hero.has_status("elf_atavism")
    assert hero.get_status_data("elf_atavism", "elf_atavism_choice", None) == "seer_elf"
    assert hero.has_status("seer_elf")


def test_elf_atavism_requires_first_level(monkeypatch):
    ui = DummyUI(["Seer Elf"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    hero.level = 2
    added = hero.add_status(ELF_ATAVISM_STATUS)

    assert added is False
    assert hero.has_status("elf_atavism") is False
