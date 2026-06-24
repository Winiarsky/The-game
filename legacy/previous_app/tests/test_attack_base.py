import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from bonuses import BonusEffect, BonusType  # noqa: E402
from GameObjects.events.attack.attack_base import AttackEventBase  # noqa: E402


class DummyAttack(AttackEventBase):
    name = "dummy_attack"


class DummyAttacker:
    def __init__(self, object_id="hero-1", modifier=0, formatted=""):
        self.object_id = object_id
        self._modifier = modifier
        self._formatted = formatted

    def compute_modifier(self, tag, target=None):
        return self._modifier

    def format_prompt(self, tag, target=None):
        return self._formatted


class DummyTarget:
    def __init__(self, ac=15, bonuses=None):
        self.ac = ac
        self.bonuses = bonuses or []


class DummyDamageActor:
    def __init__(self, *, str_mod=0, dex_mod=0):
        self.str_mod = str_mod
        self.dex_mod = dex_mod
        self.ability_modifiers = {
            "strength": str_mod,
            "dexterity": dex_mod,
        }


def test_ac_with_bonuses_applies_extra_and_target_filters_target_id():
    attacker = DummyAttacker(object_id="hero-1")
    matching = BonusEffect(
        type=BonusType.STATUS,
        value=1,
        tag="ac",
        source="buff",
        target_id="hero-1",
    )
    mismatching = BonusEffect(
        type=BonusType.STATUS,
        value=2,
        tag="ac",
        source="other",
        target_id="enemy-xyz",
    )
    extra_cover = BonusEffect(
        type=BonusType.CIRCUMSTANCE,
        value=2,
        tag="ac",
        source="cover:greater",
        target_id="hero-1",
    )
    target = DummyTarget(ac=15, bonuses=[matching, mismatching])

    attack = DummyAttack()
    target_ac, base_ac, modifier = attack._ac_with_bonuses(target, attacker=attacker, extra_bonuses=[extra_cover])

    assert base_ac == 15
    # only matching STATUS + extra_cover (circumstance) should count: 1 + 2 = 3
    assert modifier == 3
    assert target_ac == 18


def test_attacker_modifier_uses_compute_modifier():
    attacker = DummyAttacker(modifier=-2)
    attack = DummyAttack()

    mod = attack._attacker_modifier(attacker, "attack_melee")
    assert mod == -2


def test_format_bonus_info_is_empty_without_bonuses():
    attacker = DummyAttacker(formatted="+1 flank")
    attack = DummyAttack()

    info = attack._format_bonus_info(attacker, "attack_melee")
    assert info == ""


def test_attack_roll_stack_payload_contains_pf2_components():
    attack = DummyAttack()
    payload = attack._attack_roll_stack_payload(
        weapon_attack_bonus={
            "proficiency_bonus": 7,
            "ability_bonus": 4,
            "item_bonus": 1,
            "rank": "trained",
            "level": 5,
            "rank_step": 2,
            "ability_key": "strength",
        },
        modifier=2,
    )
    components = list(payload.get("components", []) or [])
    ids = [str(item.get("id")) for item in components]
    assert ids == ["proficiency", "ability", "item", "situational"]
    values = {str(item.get("id")): int(item.get("value", 0) or 0) for item in components}
    assert values["proficiency"] == 7
    assert values["ability"] == 4
    assert values["item"] == 1
    assert values["situational"] == 2
    assert int(payload.get("auto_total_modifier", 0) or 0) == 14


def test_damage_roll_stack_payload_contains_pf2_components():
    attack = DummyAttack()
    actor = DummyDamageActor(str_mod=4)
    payload = attack._damage_roll_stack_payload(
        actor=actor,
        damage_prompt="1k8 + STR",
        extra_flat_bonus=3,
    )
    components = list(payload.get("components", []) or [])
    ids = [str(item.get("id")) for item in components]
    assert ids == ["ability", "item", "status", "circumstance", "other"]
    values = {str(item.get("id")): int(item.get("value", 0) or 0) for item in components}
    assert values["ability"] == 4
    assert values["item"] == 0
    assert values["status"] == 0
    assert values["circumstance"] == 0
    assert values["other"] == 3
    assert int(payload.get("auto_total_modifier", 0) or 0) == 7


def test_prompt_damage_roll_total_prefers_computed_total(monkeypatch):
    attack = DummyAttack()
    actor = DummyDamageActor(str_mod=4)

    def _prompt(*_args, **_kwargs):
        return {
            "roll": 6,
            "raw_roll": 6,
            "modifier_delta": 2,
            "computed_total": 15,
        }

    monkeypatch.setattr("GameObjects.events.attack.attack_base.prompt_for_roll", _prompt)

    total = attack._prompt_damage_roll_total(
        prompt="Obrażenia 1k8 + STR:",
        actor=actor,
        damage_prompt="1k8 + STR",
        extra_flat_bonus=3,
    )
    assert total == 15
