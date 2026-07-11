from dnd_board_game.actions import (
    AreaSpellAttack,
    ConcentrationAction,
    MeleeAttack,
    RangedAttack,
    SpellHealing,
    attack_mechanic_from_source,
    builtin_combat_mechanics,
    combat_action_mechanic_from_definition,
    healing_mechanic_from_source,
)
from dnd_board_game.combat import AttackSource, AttackSourceType, HealingSource, HealingSourceType, SpellArea, SpellAreaShape
from dnd_board_game.rules import D20RollRequest
from dnd_board_game.scenarios.loader import ScenarioCombatActionDefinition


def test_weapon_attack_sources_map_to_melee_or_ranged_mechanics():
    melee = AttackSource("Miecz", AttackSourceType.WEAPON, 5, D20RollRequest(), id="longsword")
    ranged = AttackSource("Kusza", AttackSourceType.WEAPON, 80, D20RollRequest(), id="crossbow")

    melee_mechanic = attack_mechanic_from_source(melee)
    ranged_mechanic = attack_mechanic_from_source(ranged)

    assert isinstance(melee_mechanic, MeleeAttack)
    assert melee_mechanic.inheritance_path() == (
        "ActionMechanic",
        "CombatActionMechanic",
        "AttackMechanic",
        "BasicAttack",
        "MeleeAttack",
    )
    assert isinstance(ranged_mechanic, RangedAttack)
    assert ranged_mechanic.targeting.value == "enemy"


def test_area_spell_source_maps_to_area_spell_attack_hierarchy():
    source = AttackSource(
        "Smuga światła",
        AttackSourceType.SPELL,
        30,
        D20RollRequest(),
        id="radiant_line",
        spell_level=1,
        area=SpellArea(SpellAreaShape.LINE, length_feet=30),
        save_ability="dexterity",
        save_damage_on_success="half",
    )

    mechanic = attack_mechanic_from_source(source)

    assert isinstance(mechanic, AreaSpellAttack)
    assert mechanic.inheritance_path() == (
        "ActionMechanic",
        "CombatActionMechanic",
        "AttackMechanic",
        "SpellAttack",
        "SpellSaveAttack",
        "AreaSpellAttack",
    )
    assert "saving_throw" in mechanic.tags
    assert "area" in mechanic.tags


def test_healing_source_maps_to_spell_healing_mechanic():
    source = HealingSource("healing_word", "Słowo leczenia", HealingSourceType.SPELL, 60, spell_level=1)

    mechanic = healing_mechanic_from_source(source)

    assert isinstance(mechanic, SpellHealing)
    assert mechanic.resource.value == "action"
    assert mechanic.targeting.value == "ally"


def test_combat_action_definition_maps_to_item_action():
    action = ScenarioCombatActionDefinition(
        id="drink_strength_potion",
        name="Napój siły",
        action_type="strength_potion",
        label="Wypij napój siły",
        value=2,
        ability="strength",
    )

    mechanic = combat_action_mechanic_from_definition(action)

    assert mechanic.inheritance_path() == (
        "ActionMechanic",
        "CombatActionMechanic",
        "ItemAction",
        "StrengthPotionAction",
    )
    assert "strength" in mechanic.tags


def test_combat_action_definition_maps_to_concentration_action():
    action = ScenarioCombatActionDefinition(
        id="bless_attack_bonus",
        name="Błogosławieństwo",
        action_type="concentration_attack_bonus",
        label="Błogosławieństwo",
        value=1,
        target_faction="ally",
        spell_level=1,
    )

    mechanic = combat_action_mechanic_from_definition(action)

    assert isinstance(mechanic, ConcentrationAction)
    assert mechanic.inheritance_path() == (
        "ActionMechanic",
        "CombatActionMechanic",
        "SupportAction",
        "ConcentrationAction",
    )
    assert "concentration" in mechanic.tags


def test_builtin_combat_mechanics_cover_current_turn_actions():
    ids = {mechanic.id for mechanic in builtin_combat_mechanics()}

    assert {
        "movement.basic_move",
        "action.dash",
        "action.dodge",
        "action.disengage",
        "action.help",
        "spell.concentration_attack_bonus",
        "action.ready",
        "reaction.opportunity_attack",
        "action.ready_attack",
    } <= ids
