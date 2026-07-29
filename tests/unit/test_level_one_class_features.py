from dataclasses import replace

import pytest

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    ActorResourcePool,
    Faction,
    FeatureGrant,
    FeatureSourceKind,
    RecoveryPeriod,
)
from dnd_board_game.application import CombatTurnActionFlowService
from dnd_board_game.character_creation import (
    CharacterDraft,
    build_character,
    load_character_catalog,
    load_character_resources,
)
from dnd_board_game.combat import (
    ActionUse,
    AttackKind,
    AttackSource,
    AttackSourceType,
    CombatCondition,
    ConditionState,
    DamageComponentInput,
    DamageType,
    InitiativeEntry,
    InitiativeOrder,
    HealingSource,
    HealingSourceType,
    apply_life_domain_to_healing_source,
    apply_fighting_style_to_attack_source,
    apply_damage_result,
    attack_source_with_combat_effects,
    attack_source_with_target_combat_effects,
    attack_source_for_actor,
    build_player_initiative_prompts,
    commit_sneak_attack_hit,
    plan_sneak_attack,
    resolve_action_surge,
    resolve_damage,
    resolve_rage,
    resolve_lay_on_hands,
    resolve_reckless_attack,
    resolve_second_wind,
    resolve_actor_saving_throw,
    healing_source_at_cast_level,
    start_combat,
    use_turn_action,
    unarmed_strike_source,
)
from dnd_board_game.inventory import (
    ArmorCategory,
    HandSlot,
    InventoryItem,
    effective_armor_class,
    effective_speed_feet,
)
from dnd_board_game.rules import (
    D20RollInput,
    D20RerollRequired,
    D20RollKind,
    D20RollRequest,
    RollMode,
    SavingThrowEffectTag,
    SavingThrowRequest,
    actor_is_immune_to_effect,
    apply_actor_d20_traits,
    apply_arcane_recovery,
    complete_short_rest,
    resolve_d20_roll,
)
from dnd_board_game.world import Coordinate


@pytest.fixture
def content():
    catalog = load_character_catalog("content/character_creation/catalog.json")
    return catalog, load_character_resources(catalog, "content")


def _fighter(content, *, style: str = "defense", level: int = 1):
    catalog, resources = content
    return build_character(
        CharacterDraft(
            id="aldren",
            name="Aldren",
            species_id="human",
            class_id="fighter",
            background_id="soldier",
            base_ability_scores=AbilityScores(15, 14, 13, 12, 10, 8),
            selected_skill_ids=("perception", "survival"),
            selected_fighting_style_id=style,
            equipment_package_id="fighter_sword_and_board",
            level=level,
            selected_subclass_id="champion" if level >= 3 else "",
            selected_species_language_ids=("elvish",),
            selected_background_tool_ids=("dice_set",),
        ),
        catalog,
        resources,
    ).actor


def _rogue(content, *, level: int = 1):
    catalog, resources = content
    return build_character(
        CharacterDraft(
            id="mira",
            name="Mira",
            species_id="elf",
            class_id="rogue",
            background_id="criminal",
            base_ability_scores=AbilityScores(10, 15, 14, 13, 12, 8),
            selected_skill_ids=("acrobatics", "athletics", "insight", "performance"),
            selected_expertise_ids=("stealth", "perception"),
            equipment_package_id="rogue_burglar",
            level=level,
            selected_subclass_id="thief" if level >= 3 else "",
            selected_species_cantrip_ids=("mage_hand",),
            selected_species_language_ids=("dwarvish",),
            selected_background_tool_ids=("dice_set",),
        ),
        catalog,
        resources,
    ).actor


def _cleric(content):
    catalog, resources = content
    return build_character(
        CharacterDraft(
            id="elowen",
            name="Elowen",
            species_id="dwarf",
            class_id="cleric",
            background_id="acolyte",
            base_ability_scores=AbilityScores(10, 12, 14, 8, 15, 13),
            selected_skill_ids=("medicine", "persuasion"),
            equipment_package_id="cleric_guardian",
            selected_cantrip_ids=("guidance", "light", "sacred_flame"),
            selected_prepared_spell_ids=(
                "healing_word",
                "inflict_wounds",
                "guiding_bolt",
                "shield_of_faith",
            ),
            selected_subclass_id="life_domain",
            selected_species_tool_ids=("smiths_tools",),
            selected_background_language_ids=("elvish", "gnomish"),
        ),
        catalog,
        resources,
    ).actor


def _wizard(content):
    catalog, resources = content
    return build_character(
        CharacterDraft(
            id="vael",
            name="Vael",
            species_id="human",
            class_id="wizard",
            background_id="sage",
            base_ability_scores=AbilityScores(8, 14, 13, 15, 12, 10),
            selected_skill_ids=("investigation", "medicine"),
            equipment_package_id="wizard_scholar",
            selected_cantrip_ids=("fire_bolt", "mage_hand", "minor_illusion"),
            selected_spell_ids=(
                "burning_hands",
                "comprehend_languages",
                "shield",
                "alarm",
                "magic_missile",
                "sleep",
            ),
            selected_prepared_spell_ids=(
                "burning_hands",
                "comprehend_languages",
                "shield",
                "magic_missile",
            ),
            selected_species_language_ids=("elvish",),
            selected_background_language_ids=("dwarvish", "gnomish"),
        ),
        catalog,
        resources,
    ).actor


def _species_fighter(content, species_id: str):
    catalog, resources = content
    return build_character(
        CharacterDraft(
            id=f"{species_id}_hero",
            name=f"Test {species_id}",
            species_id=species_id,
            class_id="fighter",
            background_id="soldier",
            base_ability_scores=AbilityScores(15, 14, 13, 12, 10, 8),
            selected_skill_ids=("animal_handling", "survival"),
            selected_fighting_style_id="defense",
            equipment_package_id="fighter_sword_and_board",
            selected_species_language_ids=(
                ("dwarvish",)
                if species_id in {"human", "elf"}
                else ()
            ),
            selected_species_cantrip_ids=(
                ("mage_hand",) if species_id == "elf" else ()
            ),
            selected_species_tool_ids=(
                ("smiths_tools",) if species_id == "dwarf" else ()
            ),
            selected_background_tool_ids=("dice_set",),
        ),
        catalog,
        resources,
    ).actor


def _barbarian(content, *, level: int = 1):
    catalog, resources = content
    return build_character(
        CharacterDraft(
            id="rurik",
            name="Rurik",
            species_id="human",
            class_id="barbarian",
            background_id="soldier",
            base_ability_scores=AbilityScores(15, 14, 13, 12, 10, 8),
            selected_skill_ids=("animal_handling", "survival"),
            equipment_package_id="barbarian_greataxe",
            level=level,
            selected_subclass_id=(
                "path_of_the_berserker" if level >= 3 else ""
            ),
            selected_species_language_ids=("elvish",),
            selected_background_tool_ids=("dice_set",),
        ),
        catalog,
        resources,
    ).actor


def _monk(content, *, level: int = 1):
    catalog, resources = content
    return build_character(
        CharacterDraft(
            id="shen",
            name="Shen",
            species_id="human",
            class_id="monk",
            background_id="acolyte",
            base_ability_scores=AbilityScores(10, 15, 13, 8, 14, 12),
            selected_skill_ids=("acrobatics", "stealth"),
            equipment_package_id="monk_staff",
            level=level,
            selected_subclass_id=(
                "way_of_the_open_hand" if level >= 3 else ""
            ),
            selected_species_language_ids=("elvish",),
            selected_background_language_ids=("dwarvish", "gnomish"),
        ),
        catalog,
        resources,
    ).actor


def _enemy(position: Coordinate) -> Actor:
    return Actor(
        id=ActorId("enemy"),
        name="Goblin",
        ac=13,
        hp=8,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=Faction.ENEMY,
    )


def _ally(position: Coordinate) -> Actor:
    return Actor(
        id=ActorId("ally"),
        name="Sojusznik",
        ac=13,
        hp=8,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=Faction.ALLY,
    )


def _state(*actors: Actor):
    request = D20RollRequest()
    entries = tuple(
        InitiativeEntry(
            actor,
            resolve_d20_roll(D20RollInput(request, 20 - index)),
            0,
            index,
        )
        for index, actor in enumerate(actors)
    )
    return start_combat(tuple(actors), InitiativeOrder(entries))


def _weapon_source(
    item_id: str,
    *,
    kind: AttackKind = AttackKind.MELEE,
) -> AttackSource:
    return AttackSource(
        id=f"{item_id}_attack",
        name=item_id,
        source_type=AttackSourceType.WEAPON,
        range_feet=5 if kind == AttackKind.MELEE else 80,
        attack_kind=kind,
        attack_roll_request=D20RollRequest(),
        damage_hint="1d8 + 3 piercing",
        damage_die_sides=8,
        damage_modifier=3,
        damage_type="piercing",
        source_item_id=item_id,
        ability="dexterity",
    )


def test_second_wind_spends_bonus_action_and_short_rest_resource(content):
    fighter = replace(_fighter(content), hp=5, position=Coordinate(0, 0))
    state = _state(fighter, _enemy(Coordinate(1, 0)))

    result = resolve_second_wind(state, 6)

    assert result.actor_after.hp == 12
    assert result.healing.amount == 7
    assert result.actor_after.resource_pools[0].current == 0
    assert result.state.turn_action.bonus_action_use == ActionUse.ACTION_USED
    with pytest.raises(ValueError, match="już wykorzystane"):
        resolve_second_wind(result.state, 4)


def test_lay_on_hands_spends_selected_points_and_an_action() -> None:
    paladin = replace(
        _ally(Coordinate(0, 0)),
        id=ActorId("paladin"),
        features=(
            FeatureGrant(
                "lay_on_hands",
                "Lay on Hands",
                FeatureSourceKind.CLASS,
                "paladin",
                resource_ids=("lay_on_hands_points",),
            ),
        ),
        resource_pools=(
            ActorResourcePool(
                "lay_on_hands_points",
                "Lay on Hands",
                5,
                5,
                RecoveryPeriod.LONG_REST,
            ),
        ),
    )
    wounded = replace(_ally(Coordinate(1, 0)), hp=2)
    enemy = _enemy(Coordinate(2, 0))
    state = _state(paladin, wounded, enemy)

    result = resolve_lay_on_hands(state, str(wounded.id), 4)

    assert result.target_after.hp == 6
    assert result.healer_after.resource_pools[0].current == 1
    assert result.state.turn_action.action_use == ActionUse.ACTION_USED
    with pytest.raises(ValueError, match="wystarczającej"):
        resolve_lay_on_hands(
            _state(result.healer_after, wounded, enemy),
            str(wounded.id),
            2,
        )


def test_level_two_fighter_action_surge_restores_one_spent_action(content):
    fighter = replace(_fighter(content, level=2), position=Coordinate(0, 0))
    state = _state(fighter, _enemy(Coordinate(1, 0)))
    after_action = use_turn_action(state).state

    result = resolve_action_surge(after_action)

    assert result.state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
    assert next(
        pool for pool in result.actor_after.resource_pools
        if pool.id == "action_surge_uses"
    ).current == 0
    with pytest.raises(ValueError, match="wykorzystane"):
        resolve_action_surge(use_turn_action(result.state).state)


def test_barbarian_rage_spends_bonus_action_and_adds_melee_strength_damage(content):
    barbarian = replace(_barbarian(content), position=Coordinate(0, 0))
    state = _state(barbarian, _enemy(Coordinate(1, 0)))

    rage = resolve_rage(state, ())
    source = attack_source_with_combat_effects(
        rage.actor_after,
        replace(_weapon_source("greataxe"), ability="strength"),
        rage.active_effects,
    )

    assert rage.state.turn_action.bonus_action_use == ActionUse.ACTION_USED
    assert source.damage_modifier == 5
    assert next(
        pool for pool in rage.actor_after.resource_pools
        if pool.id == "rage_uses"
    ).current == 1
    strength_check = apply_actor_d20_traits(
        rage.actor_after,
        D20RollRequest(ability="strength"),
        D20RollKind.ABILITY_CHECK,
        active_effects=rage.active_effects,
    )
    strength_save = apply_actor_d20_traits(
        rage.actor_after,
        D20RollRequest(ability="strength"),
        D20RollKind.SAVING_THROW,
        active_effects=rage.active_effects,
    )
    damage = apply_damage_result(
        rage.actor_after,
        resolve_damage(
            (
                DamageComponentInput(9, DamageType.SLASHING, "miecz"),
                DamageComponentInput(9, DamageType.FIRE, "ogień"),
            )
        ),
        active_effects=rage.active_effects,
    )

    assert strength_check.mode == RollMode.ADVANTAGE
    assert strength_save.mode == RollMode.ADVANTAGE
    assert damage.damage.total_applied == 13

    heavy_armor = InventoryItem(
        "plate",
        "Zbroja płytowa",
        "armor",
        armor_category=ArmorCategory.HEAVY,
        armor_base_ac=18,
    )
    armored = replace(rage.actor_after, inventory=(*rage.actor_after.inventory, heavy_armor))
    armored_damage = apply_damage_result(
        armored,
        resolve_damage((DamageComponentInput(9, DamageType.SLASHING, "miecz"),)),
        active_effects=rage.active_effects,
    )
    armored_check = apply_actor_d20_traits(
        armored,
        D20RollRequest(ability="strength"),
        D20RollKind.ABILITY_CHECK,
        active_effects=rage.active_effects,
    )

    assert armored_damage.damage.total_applied == 9
    assert armored_check.mode == RollMode.NORMAL


def test_level_three_barbarian_has_three_rage_uses(content):
    barbarian = _barbarian(content, level=3)

    rage_pool = next(
        pool for pool in barbarian.resource_pools if pool.id == "rage_uses"
    )

    assert rage_pool.maximum == 3


def test_barbarian_unarmored_defense_uses_dexterity_constitution_and_allows_shield(
    content,
):
    barbarian = _barbarian(content)
    shield = InventoryItem(
        "shield",
        "Tarcza",
        "shield",
        armor_class_bonus=2,
        held_in=(HandSlot.OFF_HAND,),
    )

    assert barbarian.ac == 14
    assert effective_armor_class(barbarian) == 14
    assert effective_armor_class(
        replace(barbarian, inventory=(*barbarian.inventory, shield))
    ) == 16

    medium_armor = InventoryItem(
        "hide",
        "Skórzany pancerz",
        "armor",
        armor_category=ArmorCategory.MEDIUM,
        armor_base_ac=12,
        armor_dexterity_cap=2,
    )
    assert effective_armor_class(
        replace(barbarian, inventory=(medium_armor,))
    ) == 14


def test_level_two_barbarian_has_advantage_on_visible_danger_dexterity_save(content):
    barbarian = _barbarian(content, level=2)

    visible_danger = apply_actor_d20_traits(
        barbarian,
        D20RollRequest(ability="dexterity"),
        D20RollKind.SAVING_THROW,
        effect_tags=(SavingThrowEffectTag.VISIBLE_DANGER.value,),
    )
    hidden_danger = apply_actor_d20_traits(
        barbarian,
        D20RollRequest(ability="dexterity"),
        D20RollKind.SAVING_THROW,
    )
    blocked_modes = {
        condition: apply_actor_d20_traits(
            barbarian,
            D20RollRequest(ability="dexterity"),
            D20RollKind.SAVING_THROW,
            effect_tags=(SavingThrowEffectTag.VISIBLE_DANGER.value,),
            condition_states=(
                ConditionState(str(barbarian.id), condition),
            ),
        ).mode
        for condition in (
            CombatCondition.BLINDED,
            CombatCondition.DEAFENED,
            CombatCondition.INCAPACITATED,
        )
    }

    assert visible_danger.mode == RollMode.ADVANTAGE
    assert hidden_danger.mode == RollMode.NORMAL
    assert set(blocked_modes.values()) == {RollMode.NORMAL}


def test_reckless_attack_grants_melee_strength_advantage_to_both_sides(content):
    barbarian = replace(
        _barbarian(content, level=2),
        position=Coordinate(0, 0),
    )
    enemy = _enemy(Coordinate(1, 0))
    state = _state(barbarian, enemy)

    reckless = resolve_reckless_attack(state, ())
    barbarian_source = attack_source_with_combat_effects(
        barbarian,
        replace(_weapon_source("greataxe"), ability="strength"),
        reckless.active_effects,
    )
    enemy_source = attack_source_with_target_combat_effects(
        enemy,
        barbarian,
        _weapon_source("scimitar"),
        reckless.active_effects,
    )

    assert barbarian_source.attack_roll_request.mode == RollMode.ADVANTAGE
    assert enemy_source.attack_roll_request.mode == RollMode.ADVANTAGE


def test_shocking_grasp_source_has_advantage_against_metal_armor():
    caster = _ally(Coordinate(0, 0))
    target = replace(
        _enemy(Coordinate(1, 0)),
        inventory=(
            InventoryItem(
                "worn_chain_mail",
                "Chain mail",
                "armor",
                equipped=True,
                source_ref="chain_mail",
            ),
        ),
    )
    source = AttackSource(
        id="shocking_grasp",
        name="Shocking Grasp",
        source_type=AttackSourceType.SPELL,
        range_feet=5,
        attack_roll_request=D20RollRequest(),
        attack_kind=AttackKind.MELEE,
        advantage_against_metal_armor=True,
    )

    effective = attack_source_with_target_combat_effects(
        caster,
        target,
        source,
        (),
    )

    assert effective.attack_roll_request.mode == RollMode.ADVANTAGE


def test_monk_martial_arts_uses_dexterity_and_d4_for_unarmed_strike(content):
    monk = _monk(content)

    source = unarmed_strike_source(monk)

    assert monk.ac == 15
    assert source.ability == "dexterity"
    assert source.damage_components[0].dice.format() == "1d4"
    assert source.damage_modifier == 3

    armor = InventoryItem(
        "scale_mail",
        "Zbroja łuskowa",
        "armor",
        armor_category=ArmorCategory.MEDIUM,
        armor_base_ac=14,
        armor_dexterity_cap=2,
    )
    armored = replace(monk, inventory=(*monk.inventory, armor))
    armored_source = unarmed_strike_source(armored)
    assert armored_source.ability == "strength"
    assert armored_source.damage_components[0].fixed == 1


def test_monk_unarmored_defense_and_movement_stop_with_armor_or_shield(content):
    monk = _monk(content, level=2)
    shield = InventoryItem(
        "shield",
        "Tarcza",
        "shield",
        armor_class_bonus=2,
        held_in=(HandSlot.OFF_HAND,),
    )
    armor = InventoryItem(
        "hide",
        "Skórzany pancerz",
        "armor",
        armor_category=ArmorCategory.MEDIUM,
        armor_base_ac=12,
        armor_dexterity_cap=2,
    )

    assert monk.ac == 15
    assert effective_speed_feet(monk) == 40
    assert effective_armor_class(replace(monk, inventory=(shield,))) == 15
    assert effective_speed_feet(replace(monk, inventory=(shield,))) == 30
    assert effective_armor_class(replace(monk, inventory=(armor,))) == 14
    assert effective_speed_feet(replace(monk, inventory=(armor,))) == 30


def test_half_orc_savage_attacks_adds_one_weapon_die_only_on_critical(content):
    half_orc = _species_fighter(content, "half_orc")
    source = attack_source_for_actor(
        replace(
            _weapon_source("longsword"),
            damage_components=(),
            damage_die_sides=8,
            ability="strength",
        ),
        half_orc,
    )

    assert source.damage_components[0].formula() == "1d8 + 3"
    assert source.damage_components[0].formula(critical=True) == "3d8 + 3"


def test_archery_fighting_style_adds_two_only_to_ranged_weapon_attacks(content):
    fighter = _fighter(content, style="archery")
    ranged = apply_fighting_style_to_attack_source(
        fighter,
        _weapon_source("crossbow", kind=AttackKind.RANGED),
    )
    melee = apply_fighting_style_to_attack_source(
        fighter,
        _weapon_source("longsword"),
    )

    assert ranged.attack_roll_request.modifiers[-1].value == 2
    assert ranged.attack_roll_request.modifiers[-1].label.endswith("Archery")
    assert melee.attack_roll_request.modifiers == ()


def test_dueling_fighting_style_adds_two_damage_with_a_shield(content):
    fighter = _fighter(content, style="dueling")

    source = apply_fighting_style_to_attack_source(
        fighter,
        _weapon_source("longsword"),
    )

    assert source.damage_modifier == 5
    assert source.damage_components[0].modifier == 5
    assert "Dueling" in source.damage_hint


def test_sneak_attack_adds_one_d6_and_is_marked_only_after_hit(content):
    rogue = replace(_rogue(content), position=Coordinate(0, 0))
    target = _enemy(Coordinate(1, 0))
    ally = _ally(Coordinate(1, 1))
    state = _state(rogue, target, ally)
    source = _weapon_source("rapier")

    plan = plan_sneak_attack(
        state=state,
        active_effects=(),
        attacker=rogue,
        target=target,
        source=source,
        roll_mode=RollMode.NORMAL,
    )

    assert plan.eligible is True
    assert plan.source.damage_components[-1].id == "sneak_attack"
    assert plan.source.damage_components[-1].dice.format() == "1d6"
    effects = commit_sneak_attack_hit((), str(rogue.id))
    repeated = plan_sneak_attack(
        state=state,
        active_effects=effects,
        attacker=rogue,
        target=target,
        source=source,
        roll_mode=RollMode.ADVANTAGE,
    )
    assert repeated.eligible is False
    assert "już" in repeated.reason


def test_level_three_rogue_sneak_attack_uses_two_d6(content):
    rogue = replace(_rogue(content, level=3), position=Coordinate(0, 0))
    target = _enemy(Coordinate(1, 0))
    state = _state(rogue, target, _ally(Coordinate(1, 1)))

    plan = plan_sneak_attack(
        state=state,
        active_effects=(),
        attacker=rogue,
        target=target,
        source=_weapon_source("rapier"),
        roll_mode=RollMode.NORMAL,
    )

    assert plan.eligible is True
    assert plan.source.damage_components[-1].dice.format() == "2d6"


def test_level_two_rogue_uses_disengage_as_cunning_bonus_action(content):
    rogue = replace(_rogue(content, level=2), position=Coordinate(0, 0))
    state = _state(rogue, _enemy(Coordinate(1, 0)))
    after_action = use_turn_action(state).state

    result = CombatTurnActionFlowService().use_disengage(
        state=after_action,
        active_effects=(),
    )

    assert result.state.turn_action.action_use == ActionUse.ACTION_USED
    assert result.state.turn_action.bonus_action_use == ActionUse.ACTION_USED


def test_sneak_attack_rejects_disadvantage_even_with_adjacent_ally(content):
    rogue = replace(_rogue(content), position=Coordinate(0, 0))
    target = _enemy(Coordinate(1, 0))
    state = _state(rogue, target, _ally(Coordinate(1, 1)))

    plan = plan_sneak_attack(
        state=state,
        active_effects=(),
        attacker=rogue,
        target=target,
        source=_weapon_source("rapier"),
        roll_mode=RollMode.DISADVANTAGE,
    )

    assert plan.eligible is False
    assert "disadvantage" in plan.reason


def test_dwarven_speed_ignores_heavy_armor_strength_penalty(content):
    catalog, resources = content
    dwarf = build_character(
        CharacterDraft(
            id="brokk",
            name="Brokk",
            species_id="dwarf",
            class_id="fighter",
            background_id="soldier",
            base_ability_scores=AbilityScores(8, 14, 15, 12, 13, 10),
            selected_skill_ids=("perception", "survival"),
            selected_fighting_style_id="defense",
            equipment_package_id="fighter_sword_and_board",
            selected_species_tool_ids=("smiths_tools",),
            selected_background_tool_ids=("dice_set",),
        ),
        catalog,
        resources,
    ).actor
    heavy_armor = InventoryItem(
        id="test_plate",
        name="Testowa zbroja płytowa",
        kind="armor",
        equipped=True,
        armor_category=ArmorCategory.HEAVY,
        armor_base_ac=18,
        armor_strength_requirement=15,
    )

    armored = replace(dwarf, inventory=(heavy_armor,))

    assert armored.ability_scores.strength == 8
    assert effective_speed_feet(armored) == 25


def test_life_domain_scales_healing_bonus_with_cast_level(content):
    cleric = _cleric(content)
    source = HealingSource(
        id="cure_wounds",
        name="Leczenie ran",
        source_type=HealingSourceType.SPELL,
        range_feet=5,
        healing_hint="1d8 + 3",
        healing_die_sides=8,
        healing_modifier=3,
        spell_level=1,
    )

    domain_source = apply_life_domain_to_healing_source(cleric, source)
    upcast = healing_source_at_cast_level(domain_source, 2)

    assert domain_source.healing_modifier == 6
    assert upcast.healing_modifier == 7
    assert "Disciple of Life" in domain_source.healing_hint


def test_arcane_recovery_restores_slot_once_between_long_rests(content):
    wizard = _wizard(content)
    depleted = replace(
        wizard,
        spell_slots=(replace(wizard.spell_slots[0], remaining=0),),
    )

    recovered = apply_arcane_recovery(
        complete_short_rest(depleted),
        slot_level=1,
    )

    assert recovered.actor_after.spell_slots[0].remaining == 1
    assert recovered.actor_after.resource_pools[0].current == 0
    with pytest.raises(ValueError, match="już wykorzystane"):
        apply_arcane_recovery(
            complete_short_rest(recovered.actor_after),
            slot_level=1,
        )


def test_halfling_lucky_requires_and_uses_physical_reroll(content):
    halfling = _species_fighter(content, "halfling")
    request = apply_actor_d20_traits(
        halfling,
        D20RollRequest(),
        D20RollKind.ABILITY_CHECK,
    )

    with pytest.raises(D20RerollRequired) as reroll:
        resolve_d20_roll(D20RollInput(request, 1))
    result = resolve_d20_roll(
        D20RollInput(request, 1, natural_rerolls=(14,))
    )

    assert reroll.value.count == 1
    assert result.original_natural_rolls == (1,)
    assert result.natural_rerolls == (14,)
    assert result.natural_roll == 14
    assert result.is_natural_1 is False


def test_halfling_lucky_rerolls_each_one_before_disadvantage_selection(content):
    halfling = _species_fighter(content, "halfling")
    request = apply_actor_d20_traits(
        halfling,
        D20RollRequest(mode=RollMode.DISADVANTAGE),
        D20RollKind.ATTACK,
    )

    result = resolve_d20_roll(
        D20RollInput(request, 1, 17, natural_rerolls=(12,))
    )

    assert result.natural_rolls == (12, 17)
    assert result.natural_roll == 12


@pytest.mark.parametrize(
    ("species_id", "effect_tag", "feature_label"),
    (
        ("halfling", SavingThrowEffectTag.FEAR, "Brave"),
        ("elf", SavingThrowEffectTag.CHARM, "Fey Ancestry"),
        ("dwarf", SavingThrowEffectTag.POISON, "Dwarven Resilience"),
    ),
)
def test_species_save_traits_grant_tagged_advantage(
    content,
    species_id,
    effect_tag,
    feature_label,
):
    actor = _species_fighter(content, species_id)
    request = apply_actor_d20_traits(
        actor,
        D20RollRequest(),
        D20RollKind.SAVING_THROW,
        effect_tags=(effect_tag.value,),
    )

    result = resolve_d20_roll(D20RollInput(request, 4, 17))

    assert request.mode == RollMode.ADVANTAGE
    assert result.natural_roll == 17
    assert any(
        feature_label in modifier.label
        for modifier in result.breakdown.active_modifiers
    )


def test_fey_ancestry_blocks_magical_sleep_but_not_ordinary_unconsciousness(content):
    elf = _species_fighter(content, "elf")

    assert actor_is_immune_to_effect(
        elf,
        SavingThrowEffectTag.MAGICAL_SLEEP.value,
    )
    assert not actor_is_immune_to_effect(elf, "unconscious")


@pytest.mark.parametrize("ability", ("intelligence", "wisdom", "charisma"))
def test_gnome_cunning_grants_advantage_only_to_mental_saves_against_magic(
    content,
    ability,
):
    gnome = _species_fighter(content, "gnome")

    magical = apply_actor_d20_traits(
        gnome,
        D20RollRequest(ability=ability),
        D20RollKind.SAVING_THROW,
        effect_tags=(SavingThrowEffectTag.MAGIC.value,),
    )
    nonmagical = apply_actor_d20_traits(
        gnome,
        D20RollRequest(ability=ability),
        D20RollKind.SAVING_THROW,
    )
    physical = apply_actor_d20_traits(
        gnome,
        D20RollRequest(ability="dexterity"),
        D20RollKind.SAVING_THROW,
        effect_tags=(SavingThrowEffectTag.MAGIC.value,),
    )

    assert magical.mode == RollMode.ADVANTAGE
    assert nonmagical.mode == RollMode.NORMAL
    assert physical.mode == RollMode.NORMAL


def test_shared_attack_initiative_and_save_paths_apply_species_traits(content):
    halfling = _species_fighter(content, "halfling")
    dwarf = _species_fighter(content, "dwarf")

    attack = attack_source_for_actor(_weapon_source("longsword"), halfling)
    initiative = build_player_initiative_prompts((halfling,))[0]
    poison_save = resolve_actor_saving_throw(
        dwarf,
        SavingThrowRequest(
            ability="constitution",
            dc=12,
            source_label="Trucizna",
            effect_tags=(SavingThrowEffectTag.POISON.value,),
        ),
        natural_roll=3,
        natural_roll_2=16,
    )

    assert attack.attack_roll_request.reroll_natural_ones is True
    assert initiative.request.reroll_natural_ones is True
    assert poison_save.natural_roll == 16
    assert poison_save.success is True
