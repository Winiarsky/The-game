from dataclasses import replace

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    Faction,
    ability_check_roll_modifiers,
    attack_roll_modifiers,
    passive_skill_score,
    saving_throw_roll_modifiers,
)
from dnd_board_game.inventory import (
    InventoryItem,
    ItemAttunementAction,
    MagicItemEffect,
    MagicItemEffectKind,
    active_magic_item_effects,
    apply_item_attunement,
    effective_armor_class,
    effective_speed_feet,
    inventory_item_payload,
)
from dnd_board_game.scenarios import load_scenario
from dnd_board_game.world import Coordinate


def _effect(kind: MagicItemEffectKind, value: int = 1) -> MagicItemEffect:
    return MagicItemEffect(kind.value, kind, value)


def _item(
    *effects: MagicItemEffect,
    attuned: bool = True,
    equipped: bool = True,
    broken: bool = False,
) -> InventoryItem:
    return InventoryItem(
        "amulet",
        "Amulet strażnika",
        "magic_item",
        equipped=equipped,
        broken=broken,
        requires_attunement=True,
        attuned=attuned,
        magic_effects=effects,
    )


def _actor(item: InventoryItem) -> Actor:
    return Actor(
        ActorId("hero"),
        "Bohater",
        14,
        20,
        0,
        30,
        Coordinate(0, 0),
        Faction.ALLY,
        ability_scores=AbilityScores(dexterity=14, wisdom=12),
        inventory=(item,),
    )


def test_active_magic_effects_feed_existing_rule_resolvers() -> None:
    actor = _actor(
        _item(
            _effect(MagicItemEffectKind.ARMOR_CLASS_BONUS),
            _effect(MagicItemEffectKind.SAVING_THROW_BONUS),
            _effect(MagicItemEffectKind.ABILITY_CHECK_BONUS, 2),
            _effect(MagicItemEffectKind.ATTACK_ROLL_BONUS),
            _effect(MagicItemEffectKind.SPEED_BONUS_FEET, 10),
        )
    )

    assert effective_armor_class(actor) == 15
    assert effective_speed_feet(actor) == 40
    assert saving_throw_roll_modifiers(actor, "wisdom")[-1].value == 1
    assert ability_check_roll_modifiers(actor, "wisdom")[-1].value == 2
    assert passive_skill_score(actor, "perception") == 13
    assert attack_roll_modifiers(actor, "dexterity", proficient=False)[-1].value == 1


def test_attunement_equipment_and_item_availability_gate_effects() -> None:
    effect = _effect(MagicItemEffectKind.ARMOR_CLASS_BONUS)
    base = _item(effect)

    assert len(active_magic_item_effects(_actor(base), effect.kind)) == 1
    assert effective_armor_class(_actor(replace(base, attuned=False))) == 14
    assert effective_armor_class(_actor(replace(base, equipped=False))) == 14
    assert effective_armor_class(_actor(replace(base, broken=True))) == 14


def test_effect_can_explicitly_work_while_carried_and_payload_preserves_contract() -> None:
    effect = MagicItemEffect(
        "carried_speed",
        MagicItemEffectKind.SPEED_BONUS_FEET,
        5,
        requires_equipped=False,
    )
    item = _item(effect, equipped=False)

    assert effective_speed_feet(_actor(item)) == 35
    assert inventory_item_payload(item)["magic_effects"] == [
        {
            "id": "carried_speed",
            "kind": "speed_bonus_feet",
            "value": 5,
            "requires_equipped": False,
        }
    ]


def test_reference_amulet_is_data_driven_and_unlocks_after_attunement() -> None:
    scenario = load_scenario("content/scenarios/abandoned_watchtower.json")
    cleric = next(
        actor
        for actor in scenario.definition.actors
        if str(actor.id) == "cleric"
    )
    amulet = next(item for item in cleric.inventory if item.id == "guardian_amulet")

    assert amulet.attuned is False
    assert [effect.kind for effect in amulet.magic_effects] == [
        MagicItemEffectKind.ARMOR_CLASS_BONUS,
        MagicItemEffectKind.SAVING_THROW_BONUS,
    ]
    before = effective_armor_class(cleric)
    attuned = apply_item_attunement(
        cleric,
        item_id=amulet.id,
        action=ItemAttunementAction.ATTUNE,
    )

    assert effective_armor_class(attuned.actor) == before + 1
    assert saving_throw_roll_modifiers(attuned.actor, "wisdom")[-1].label == amulet.name
