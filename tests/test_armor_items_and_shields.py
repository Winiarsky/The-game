from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import dataclass, field
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.events.attack.attack_base import AttackEventBase
from GameObjects.events.base import EventContext
from GameObjects.events.raise_shield_event import RaiseShieldEvent
from GameObjects.interactions_mixin import BonusMixin
from GameObjects.interactions_mixin.skill_check_resolver import compute_skill_modifier_with_sources
from GameObjects.items.armor import (
    apply_critical_damage_reduction,
    create_armor,
    get_equipped_armor,
    normalize_armor_id,
)
from GameObjects.items.inventory import ensure_actor_inventory
from GameObjects.items.shield import BucklerShield, create_shield, normalize_shield_id
from combat.reactions.reactive_shield_reaction import ReactiveShieldReaction
from skills import Skill
from statuses import RAISE_SHIELD_ALLOW_STATUS, Status


@dataclass
class Actor(BonusMixin):
    statuses: list[object] = field(default_factory=list)
    bonuses: list[object] = field(default_factory=list)
    inventory: list[object] = field(default_factory=list)
    equipped_armor_item_id: str | None = None
    equipped_shield: object | None = None
    weapon_loadout: list[str] = field(default_factory=lambda: ["unarmed"])
    armor_loadout: list[str] = field(default_factory=list)
    shield_loadout: list[str] = field(default_factory=list)
    ac: int = 10
    dex_mod: int = 0
    object_id: str = "actor-1"

    def has_status(self, status_id: str) -> bool:
        return any(getattr(item, "id", item) == status_id for item in self.statuses)

    def add_status(self, status) -> bool:
        self.statuses.append(status)
        return True


class CombatCtx(EventContext):
    @property
    def in_combat(self):  # type: ignore[override]
        return True

    @property
    def in_exploration(self):  # type: ignore[override]
        return False


def _ac_bonus_value(actor) -> int:
    for bonus in actor.bonuses:
        if getattr(bonus, "tag", None) != "ac":
            continue
        if str(getattr(bonus, "source", "") or "").startswith("raise_shield:"):
            return int(getattr(bonus, "value", 0) or 0)
    return 0


def test_armor_profiles_and_aliases():
    full_plate = create_armor("full plate")
    studded = create_armor("studded_leather")
    chain_shirt = create_armor("chain shirt")
    half_plate = create_armor("half_plate")

    assert full_plate is not None and full_plate.ac_bonus == 6
    assert "bulwark" in full_plate.traits
    assert studded is not None and studded.dex_cap == 3
    assert chain_shirt is not None and chain_shirt.ac_bonus == 2
    assert half_plate is not None and half_plate.ac_bonus == 5
    assert normalize_armor_id("plytowa") == "full_plate"
    assert normalize_armor_id("chainshirt") == "chain_shirt"


def test_shield_profiles_and_aliases():
    buckler = create_shield("buckler")
    wooden = create_shield("wooden_shield")
    steel = create_shield("steel_shield")
    tower = create_shield("tower shield")

    assert buckler is not None and int(buckler.ac_bonus) == 1
    assert int(buckler.hardness) == 3
    assert wooden is not None and int(wooden.ac_bonus) == 2
    assert int(wooden.hardness) == 3
    assert int(wooden.max_hp) == 12
    assert steel is not None and int(steel.ac_bonus) == 2
    assert int(steel.hardness) == 5
    assert tower is not None and int(tower.ac_bonus) == 2
    assert int(getattr(tower, "take_cover_ac_bonus", 0)) == 4
    assert int(getattr(tower, "speed_penalty_feet", 0)) == 5
    assert "tower_shield" in (tower.traits or ())
    assert normalize_shield_id("tarcza") == "steel_shield"
    assert normalize_shield_id("drewniana_tarcza") == "wooden_shield"


def test_armor_penalties_and_requirements_match_crb_table():
    leather = create_armor("leather_armor")
    chain_shirt = create_armor("chain_shirt")
    chain_mail = create_armor("chain_mail")
    splint = create_armor("splint_mail")
    half_plate = create_armor("half_plate")
    assert leather is not None and chain_shirt is not None
    assert chain_mail is not None and splint is not None and half_plate is not None

    assert int(getattr(leather, "check_penalty", 0)) == 1
    assert int(getattr(leather, "speed_penalty_feet", 0)) == 0
    assert int(getattr(chain_shirt, "check_penalty", 0)) == 1
    assert int(getattr(chain_shirt, "strength_requirement", 0)) == 12
    assert int(getattr(chain_mail, "check_penalty", 0)) == 2
    assert int(getattr(chain_mail, "speed_penalty_feet", 0)) == 5
    assert str(getattr(chain_mail, "armor_category", "")) == "medium"
    assert int(getattr(splint, "dex_cap", 0)) == 1
    assert int(getattr(splint, "strength_requirement", 0)) == 16
    assert int(getattr(half_plate, "price_cp", 0)) == 1800
    assert int(getattr(half_plate, "speed_penalty_feet", 0)) == 10


def test_armor_trait_profiles_are_assigned():
    expected_traits = {
        "padded_armor": {"comfort"},
        "leather_armor": set(),
        "studded_leather": set(),
        "chain_shirt": {"flexible", "noisy"},
        "hide_armor": set(),
        "scale_mail": set(),
        "breastplate": set(),
        "chain_mail": {"flexible", "noisy"},
        "splint_mail": set(),
        "half_plate": set(),
        "full_plate": {"bulwark"},
    }
    for armor_id, expected in expected_traits.items():
        armor = create_armor(armor_id)
        assert armor is not None
        traits = {str(item or "").strip().lower() for item in tuple(getattr(armor, "traits", ()) or ())}
        assert traits == expected


def test_inventory_can_seed_armor_and_shield_loadout():
    actor = Actor(armor_loadout=["full_plate"], shield_loadout=["buckler"])
    inventory = ensure_actor_inventory(actor)
    item_ids = {str(getattr(item, "item_id", "")) for item in inventory}

    assert "full_plate" in item_ids
    assert "buckler" in item_ids


def test_get_equipped_armor_from_equipped_item_id():
    actor = Actor()
    armor = create_armor("scale_mail")
    assert armor is not None
    actor.inventory = [armor]
    actor.equipped_armor_item_id = str(getattr(armor, "instance_id", ""))

    equipped = get_equipped_armor(actor)
    assert equipped is armor


def test_equipped_armor_adds_item_bonus_to_ac_resolution():
    actor = Actor(ac=10)
    armor = create_armor("studded_leather")
    assert armor is not None
    actor.inventory = [armor]
    actor.equipped_armor_item_id = str(getattr(armor, "instance_id", ""))

    event = AttackEventBase()
    target_ac, _base, _mod = event._ac_with_bonuses(actor)

    assert target_ac == 12


def test_noisy_armor_penalizes_stealth_modifier():
    actor = Actor()
    armor = create_armor("chain_mail")
    assert armor is not None
    actor.inventory = [armor]
    actor.equipped_armor_item_id = str(getattr(armor, "instance_id", ""))

    modifier, _breakdown, _notes = compute_skill_modifier_with_sources(
        skill_id=Skill.STEALTH.value,
        actor=actor,
        tags=["stealth", "roll"],
        base_modifier=0,
    )
    assert modifier == -2


def test_flexible_armor_ignores_check_penalty_for_acrobatics_and_athletics():
    actor = Actor()
    flexible = create_armor("chain_shirt")
    assert flexible is not None
    actor.inventory = [flexible]
    actor.equipped_armor_item_id = str(getattr(flexible, "instance_id", ""))

    acro_mod, _acro_breakdown, _acro_notes = compute_skill_modifier_with_sources(
        skill_id=Skill.ACROBATICS.value,
        actor=actor,
        tags=["acrobatics", "roll"],
        base_modifier=0,
    )
    ath_mod, _ath_breakdown, _ath_notes = compute_skill_modifier_with_sources(
        skill_id=Skill.ATHLETICS.value,
        actor=actor,
        tags=["athletics", "roll"],
        base_modifier=0,
    )
    assert acro_mod == 0
    assert ath_mod == 0

    non_flexible = create_armor("scale_mail")
    assert non_flexible is not None
    actor.inventory = [non_flexible]
    actor.equipped_armor_item_id = str(getattr(non_flexible, "instance_id", ""))

    ath_mod_nf, _ath_breakdown_nf, _ath_notes_nf = compute_skill_modifier_with_sources(
        skill_id=Skill.ATHLETICS.value,
        actor=actor,
        tags=["athletics", "roll"],
        base_modifier=0,
    )
    assert ath_mod_nf == -2


def test_bulwark_adds_reflex_bonus_in_area_context():
    actor = Actor(dex_mod=0)
    armor = create_armor("full_plate")
    assert armor is not None
    actor.inventory = [armor]
    actor.equipped_armor_item_id = str(getattr(armor, "instance_id", ""))

    modifier, _breakdown, _notes = compute_skill_modifier_with_sources(
        skill_id=Skill.REFLEX.value,
        actor=actor,
        tags=["save", "reflex", "area"],
        base_modifier=0,
    )
    assert modifier == 3


def test_armor_specialization_uses_group_effects():
    actor = Actor()
    armor = create_armor("chain_mail")
    assert armor is not None
    actor.inventory = [armor]
    actor.equipped_armor_item_id = str(getattr(armor, "instance_id", ""))
    actor.statuses = [Status(id="armor_specialization")]

    reduced, notes = apply_critical_damage_reduction(
        actor,
        [("slashing", 10)],
        critical=True,
    )
    assert reduced[0][1] == 6
    assert any("chain" in note.lower() for note in notes)

    plate = create_armor("full_plate")
    assert plate is not None
    actor.inventory = [plate]
    actor.equipped_armor_item_id = str(getattr(plate, "instance_id", ""))
    reduced_spec, notes_spec = apply_critical_damage_reduction(
        actor,
        [("slashing", 10)],
        critical=False,
    )
    assert reduced_spec[0][1] == 8
    assert any("plate" in note.lower() for note in notes_spec)

    leather = create_armor("hide_armor")
    assert leather is not None
    actor.inventory = [leather]
    actor.equipped_armor_item_id = str(getattr(leather, "instance_id", ""))
    reduced_leather, _notes_leather = apply_critical_damage_reduction(
        actor,
        [("bludgeoning", 10)],
        critical=False,
    )
    assert reduced_leather[0][1] == 9

    composite = create_armor("scale_mail")
    assert composite is not None
    actor.inventory = [composite]
    actor.equipped_armor_item_id = str(getattr(composite, "instance_id", ""))
    reduced_composite, _notes_composite = apply_critical_damage_reduction(
        actor,
        [("piercing", 10)],
        critical=False,
    )
    assert reduced_composite[0][1] == 9


def test_raise_shield_uses_equipped_shield_ac_bonus():
    hero = Actor()
    hero.equipped_shield = BucklerShield()
    hero.add_status(RAISE_SHIELD_ALLOW_STATUS)
    game = SimpleNamespace(state=SimpleNamespace(round_index=2), ui_log=lambda *_a, **_k: None)
    ctx = CombatCtx(game=game, actor=hero)

    result = RaiseShieldEvent().execute(ctx)

    assert result.success is True
    assert _ac_bonus_value(hero) == 1


def test_reactive_shield_uses_equipped_shield_ac_bonus():
    hero = Actor(statuses=[Status(id="reactive_shield")], equipped_shield=BucklerShield())
    game = SimpleNamespace(state=SimpleNamespace(round_index=5), ui_log=lambda *_a, **_k: None)
    ctx = SimpleNamespace(game=game)

    executed = ReactiveShieldReaction().execute(
        hero,
        {"target": hero, "action_id": "attack_sword_pre", "action_tags": ["attack_melee"]},
        ctx,
    )

    assert executed is True
    assert _ac_bonus_value(hero) == 1
