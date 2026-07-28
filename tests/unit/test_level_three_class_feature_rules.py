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
from dnd_board_game.combat import (
    ActionUse,
    AttackKind,
    AttackSource,
    AttackSourceType,
    DamageComponentInput,
    DamageComponentSpec,
    DamageType,
    CombatCondition,
    PreserveLifeAllocation,
    apply_metamagic_to_source,
    apply_agonizing_blast,
    apply_damage_result,
    available_wild_shape_forms,
    convert_spell_slot_to_sorcery_points,
    create_spell_slot_from_sorcery_points,
    climbing_movement_cost,
    dark_ones_blessing_temporary_hit_points,
    deflect_missiles,
    divine_smite_damage,
    metamagic_sorcery_point_cost,
    metamagic_options_for_source,
    jump_distances,
    natural_recovery_capacity,
    preserve_life_capacity,
    resolve_bardic_inspiration,
    resolve_channel_turn,
    resolve_divine_sense,
    resolve_flurry_of_blows,
    resolve_frenzy,
    resolve_martial_arts_bonus_attack,
    resolve_open_hand_technique,
    resolve_patient_defense,
    resolve_pact_weapon,
    resolve_preserve_life,
    resolve_primeval_awareness,
    resolve_rage,
    resolve_sacred_weapon,
    resolve_wild_shape,
    resolve_damage,
    resolve_step_of_the_wind,
    sculpt_spells_protected_creature_count,
    validate_preserve_life_allocations,
    wild_shape_limits,
    wild_shape_attack_source,
    InitiativeEntry,
    InitiativeOrder,
    start_combat,
    has_condition,
    replace_actor,
    expire_condition_states,
    SpellSlotState,
)
from dnd_board_game.inventory import HandSlot, InventoryItem
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    DiceExpression,
    EffectEvent,
    EffectEventType,
    SpellComponents,
    SpellDefinition,
    SpellDuration,
    SpellDurationKind,
    SpellRange,
    SpellRangeKind,
    SpellSchool,
    SpellCastingTime,
    resolve_d20_roll,
)
from dnd_board_game.world import Coordinate


def _actor(*feature_ids: str, level: int = 3, hp: int = 20, max_hp: int = 20):
    return Actor(
        id=ActorId("hero"),
        name="Hero",
        ac=14,
        hp=hp,
        max_hp=max_hp,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(1, 1),
        faction=Faction.ALLY,
        level=level,
        ability_scores=AbilityScores(14, 16, 12, 14, 16, 16),
        features=tuple(
            FeatureGrant(
                feature_id=feature_id,
                label=feature_id,
                source_kind=FeatureSourceKind.CLASS,
                source_ref="test",
            )
            for feature_id in feature_ids
        ),
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


def test_level_three_druid_limits_and_natural_recovery():
    actor = _actor("wild_shape", "natural_recovery")

    limits = wild_shape_limits(actor)

    assert limits.maximum_challenge_rating == 0.25
    assert limits.swimming_allowed is False
    assert limits.flying_allowed is False
    assert limits.duration_hours == 1
    assert natural_recovery_capacity(actor) == 2


def test_wild_shape_uses_beast_hp_natural_attack_and_overflow_damage():
    druid = replace(
        _actor("wild_shape", hp=17, max_hp=20),
        resource_pools=(
            ActorResourcePool(
                "wild_shape_uses",
                "Wild Shape",
                2,
                2,
                RecoveryPeriod.SHORT_REST,
            ),
        ),
    )
    enemy = replace(_actor(), id=ActorId("enemy"), faction=Faction.ENEMY)
    state = _state(druid, enemy)

    transformed = resolve_wild_shape(state, form_id="wolf")
    wolf = transformed.actor_after
    source = wild_shape_attack_source(wolf)

    assert wolf.wild_shape is not None
    assert wolf.wild_shape.original_hp == 17
    assert wolf.hp == 11
    assert wolf.max_hp == 11
    assert wolf.creature_type == "beast"
    assert transformed.state.turn_action.action_use == ActionUse.ACTION_USED
    assert wolf.resource_pools[0].current == 1
    assert source is not None
    assert source.name == "Ugryzienie"
    assert source.damage_hint == "2d4+1"

    damage = resolve_damage((DamageComponentInput(15, DamageType.SLASHING),))
    applied = apply_damage_result(wolf, damage)

    assert applied.actor_after.wild_shape is None
    assert applied.actor_after.creature_type == "humanoid"
    assert applied.actor_after.hp == 13
    assert applied.actor_after.max_hp == 20
    assert applied.defeated is False


def test_wild_shape_manual_revert_uses_bonus_action():
    druid = replace(
        _actor("wild_shape"),
        resource_pools=(
            ActorResourcePool(
                "wild_shape_uses",
                "Wild Shape",
                2,
                2,
                RecoveryPeriod.SHORT_REST,
            ),
        ),
    )
    enemy = replace(_actor(), id=ActorId("enemy"), faction=Faction.ENEMY)
    transformed = resolve_wild_shape(_state(druid, enemy), form_id="panther")
    next_turn = _state(transformed.actor_after, enemy)

    reverted = resolve_wild_shape(next_turn)

    assert reverted.reverted is True
    assert reverted.actor_after.wild_shape is None
    assert reverted.state.turn_action.bonus_action_use == ActionUse.ACTION_USED
    assert reverted.actor_after.resource_pools[0].current == 1


def test_level_three_wild_shape_catalog_contains_only_legal_land_forms():
    druid = _actor("wild_shape")

    forms = available_wild_shape_forms(druid)

    assert {form.id for form in forms} >= {"wolf", "panther", "riding_horse"}
    assert all(form.challenge_rating <= 0.25 for form in forms)
    assert not any(form.has_swimming_speed or form.has_flying_speed for form in forms)


def test_turn_undead_spends_channel_divinity_and_applies_turned_condition():
    cleric = replace(
        _actor("turn_undead"),
        spell_save_dc=14,
        resource_pools=(
            ActorResourcePool(
                "channel_divinity_uses",
                "Channel Divinity",
                1,
                1,
                RecoveryPeriod.SHORT_REST,
            ),
        ),
    )
    zombie = replace(
        _actor(),
        id=ActorId("zombie"),
        faction=Faction.ENEMY,
        creature_type="undead",
        position=Coordinate(2, 1),
    )
    skeleton = replace(
        zombie,
        id=ActorId("skeleton"),
        position=Coordinate(3, 1),
    )

    result = resolve_channel_turn(
        _state(cleric, zombie, skeleton),
        action_id="turn_undead",
        saving_rolls={"zombie": 2, "skeleton": 20},
    )

    assert result.turned_target_ids == ("zombie",)
    assert result.successful_save_target_ids == ("skeleton",)
    assert has_condition(
        result.state.condition_states,
        "zombie",
        CombatCondition.TURNED,
    )
    assert result.actor_after.resource_pools[0].current == 0
    assert result.state.turn_action.action_use == ActionUse.ACTION_USED

    damaged = apply_damage_result(
        zombie,
        resolve_damage((DamageComponentInput(1, DamageType.RADIANT),)),
    )
    after_damage = replace_actor(result.state, damaged.actor_after)
    assert not has_condition(
        after_damage.condition_states,
        "zombie",
        CombatCondition.TURNED,
    )


def test_primeval_awareness_spends_selected_slot_and_reveals_only_types():
    ranger = replace(
        _actor("primeval_awareness"),
        spell_slots=(SpellSlotState(1, 1, 1), SpellSlotState(2, 1, 1)),
    )
    fiend = replace(
        _actor(),
        id=ActorId("fiend"),
        faction=Faction.ENEMY,
        creature_type="fiend",
    )
    goblin = replace(
        fiend,
        id=ActorId("goblin"),
        creature_type="humanoid",
    )

    result = resolve_primeval_awareness(
        _state(ranger, fiend, goblin),
        slot_level=2,
    )

    assert result.detected_creature_types == ("fiend",)
    assert result.duration_minutes == 2
    assert result.actor_after.spell_slots[0].remaining == 1
    assert result.actor_after.spell_slots[1].remaining == 0
    assert result.state.turn_action.action_use == ActionUse.ACTION_USED


def test_frenzy_activates_during_rage_and_grants_later_bonus_weapon_attack():
    barbarian = replace(
        _actor("rage", "frenzy"),
        inventory=(
            InventoryItem(
                "greataxe",
                "Greataxe",
                "weapon",
                equipped=True,
                source_ref="greataxe",
                hands_required=2,
                held_in=(HandSlot.MAIN_HAND, HandSlot.OFF_HAND),
            ),
        ),
        resource_pools=(
            ActorResourcePool(
                "rage_uses",
                "Rage",
                3,
                3,
                RecoveryPeriod.LONG_REST,
            ),
        ),
    )
    enemy = replace(_actor(), id=ActorId("enemy"), faction=Faction.ENEMY)
    rage = resolve_rage(_state(barbarian, enemy), ())

    activated = resolve_frenzy(rage.state, rage.active_effects)

    assert activated.activated is True
    assert any(effect.kind == "frenzy" for effect in activated.active_effects)

    next_turn = _state(activated.actor, enemy)
    bonus = resolve_frenzy(next_turn, activated.active_effects)

    assert bonus.activated is False
    assert bonus.bonus_attack_source_id == "greataxe"
    assert bonus.state.turn_action.bonus_action_use == ActionUse.ACTION_USED
    assert bonus.state.turn_action.bonus_attacks_remaining == 1


def test_pact_of_the_blade_creates_one_equipped_replaceable_weapon():
    warlock = _actor("pact_of_the_blade")
    enemy = replace(_actor(), id=ActorId("enemy"), faction=Faction.ENEMY)
    longsword = InventoryItem(
        "longsword",
        "Longsword",
        "weapon",
        equipped=False,
        source_ref="longsword",
        hands_required=1,
    )

    first = resolve_pact_weapon(_state(warlock, enemy), longsword)

    pact = next(item for item in first.actor_after.inventory if item.id == "pact_weapon")
    assert pact.source_ref == "longsword"
    assert pact.equipped is True
    assert first.state.turn_action.action_use == ActionUse.ACTION_USED

    greataxe = InventoryItem(
        "greataxe",
        "Greataxe",
        "weapon",
        equipped=False,
        source_ref="greataxe",
        hands_required=2,
    )
    second = resolve_pact_weapon(_state(first.actor_after, enemy), greataxe)
    pact_weapons = tuple(
        item for item in second.actor_after.inventory if item.id == "pact_weapon"
    )
    assert len(pact_weapons) == 1
    assert pact_weapons[0].source_ref == "greataxe"


def test_divine_smite_scales_and_gets_fiend_or_undead_die():
    actor = _actor("divine_smite")

    ordinary = divine_smite_damage(
        actor,
        slot_level=1,
        target_creature_type="humanoid",
    )
    fiend = divine_smite_damage(
        actor,
        slot_level=2,
        target_creature_type="fiend",
    )

    assert ordinary.dice == DiceExpression(2, 8)
    assert fiend.dice == DiceExpression(4, 8)


def test_preserve_life_enforces_pool_and_half_hit_point_cap():
    cleric = _actor("channel_divinity_preserve_life")
    wounded = replace(
        _actor(level=3, hp=2, max_hp=20),
        id=ActorId("wounded"),
    )

    assert preserve_life_capacity(cleric) == 15
    validate_preserve_life_allocations(
        cleric,
        (wounded,),
        (PreserveLifeAllocation("wounded", 8),),
    )
    with pytest.raises(ValueError, match="połowy"):
        validate_preserve_life_allocations(
            cleric,
            (wounded,),
            (PreserveLifeAllocation("wounded", 9),),
        )


def test_deflect_missiles_reduces_and_catches_projectile():
    monk = _actor("deflect_missiles")

    result = deflect_missiles(
        monk,
        natural_d10=6,
        incoming_damage=10,
        has_free_hand=True,
    )

    assert result.reduction == 12
    assert result.damage_after_reduction == 0
    assert result.caught is True
    assert result.can_return_projectile is True


def test_open_hand_technique_applies_all_three_hit_options_and_long_reaction_lock():
    monk = replace(
        _actor("open_hand_technique", level=3),
        id=ActorId("monk"),
        position=Coordinate(1, 1),
    )
    target = replace(
        _actor(level=3),
        id=ActorId("target"),
        faction=Faction.ENEMY,
        position=Coordinate(2, 1),
    )
    state = _state(monk, target)

    denied = resolve_open_hand_technique(
        state,
        attacker_id="monk",
        target_id="target",
        mode="no_reactions",
    )
    assert has_condition(
        denied.state.condition_states,
        "target",
        CombatCondition.NO_REACTIONS,
    )
    after_current_end, expired = expire_condition_states(
        denied.state.condition_states,
        EffectEvent(EffectEventType.TURN_END, actor_id="monk"),
    )
    assert not expired
    after_next_end, expired = expire_condition_states(
        after_current_end,
        EffectEvent(EffectEventType.TURN_END, actor_id="monk"),
    )
    assert expired
    assert not after_next_end

    prone = resolve_open_hand_technique(
        state,
        attacker_id="monk",
        target_id="target",
        mode="prone",
        natural_roll=1,
    )
    assert prone.succeeded
    assert has_condition(
        prone.state.condition_states,
        "target",
        CombatCondition.PRONE,
    )

    pushed = resolve_open_hand_technique(
        state,
        attacker_id="monk",
        target_id="target",
        mode="push",
        natural_roll=1,
        push_destination=Coordinate(5, 1),
    )
    assert pushed.succeeded
    assert pushed.target_after.position == Coordinate(5, 1)


def test_metamagic_costs_match_2014_table():
    assert metamagic_sorcery_point_cost("metamagic_subtle") == 1
    assert metamagic_sorcery_point_cost("metamagic_quickened") == 2
    assert metamagic_sorcery_point_cost("metamagic_heightened") == 3
    assert metamagic_sorcery_point_cost(
        "metamagic_twinned",
        spell_level=2,
    ) == 2


def test_metamagic_transforms_spell_source_and_charges_one_combined_resource():
    spell = SpellDefinition(
        id="test_ray",
        name="Test Ray",
        level=1,
        school=SpellSchool.EVOCATION,
        casting_time=SpellCastingTime.ACTION,
        range=SpellRange(SpellRangeKind.DISTANCE, 60),
        components=SpellComponents(verbal=True, somatic=True),
        duration=SpellDuration(SpellDurationKind.MINUTE),
        effect_kind="attack",
    )
    sorcerer = replace(
        _actor(
            "metamagic_distant",
            "metamagic_quickened",
            "metamagic_subtle",
            "metamagic_extended",
            "metamagic_twinned",
            "metamagic_empowered",
        ),
        spells=(spell,),
        resource_pools=(
            ActorResourcePool(
                "sorcery_points",
                "Sorcery Points",
                3,
                3,
                RecoveryPeriod.LONG_REST,
            ),
        ),
    )
    source = AttackSource(
        id=spell.id,
        name=spell.name,
        source_type=AttackSourceType.SPELL,
        range_feet=60,
        attack_kind=AttackKind.RANGED,
        attack_roll_request=D20RollRequest(),
        damage_type="fire",
        damage_die_sides=6,
        damage_components=(
            DamageComponentSpec(
                "base",
                DamageType.FIRE,
                dice=DiceExpression(2, 6),
            ),
        ),
        spell_level=1,
    )

    option_ids = {option.id for option in metamagic_options_for_source(sorcerer, source)}
    distant = apply_metamagic_to_source(
        sorcerer,
        source,
        ("metamagic_distant",),
    )
    quickened = apply_metamagic_to_source(
        sorcerer,
        source,
        ("metamagic_quickened",),
    )
    combined = apply_metamagic_to_source(
        sorcerer,
        source,
        ("metamagic_quickened", "metamagic_empowered"),
    )

    assert {
        "metamagic_distant",
        "metamagic_quickened",
        "metamagic_subtle",
        "metamagic_extended",
        "metamagic_twinned",
        "metamagic_empowered",
    } <= option_ids
    assert distant.range_feet == 120
    assert quickened.action_cost.value == "bonus_action"
    assert combined.resource_pool_id == "sorcery_points"
    assert combined.resource_cost == 3
    with pytest.raises(ValueError, match="tylko jednej"):
        apply_metamagic_to_source(
            sorcerer,
            source,
            ("metamagic_distant", "metamagic_quickened"),
        )


def test_second_story_work_removes_climbing_surcharge_and_extends_jumps():
    thief = _actor("second_story_work")
    ordinary = _actor()

    thief_jumps = jump_distances(thief)
    ordinary_jumps = jump_distances(ordinary)

    assert climbing_movement_cost(thief, 10) == 10
    assert climbing_movement_cost(ordinary, 10) == 20
    assert (
        thief_jumps.running_long_jump_feet
        == ordinary_jumps.running_long_jump_feet + 3
    )
    assert (
        thief_jumps.running_high_jump_feet
        == ordinary_jumps.running_high_jump_feet + 3
    )


def test_font_of_magic_converts_slots_and_creates_temporary_slots():
    sorcerer = replace(
        _actor("font_of_magic"),
        spell_slots=(SpellSlotState(1, 0, 4), SpellSlotState(2, 1, 2)),
        resource_pools=(
            ActorResourcePool(
                "sorcery_points",
                "Sorcery Points",
                0,
                3,
                RecoveryPeriod.LONG_REST,
            ),
        ),
    )

    gained = convert_spell_slot_to_sorcery_points(sorcerer, slot_level=2)
    created = create_spell_slot_from_sorcery_points(
        gained.actor_after,
        slot_level=1,
    )

    assert gained.actor_after.spell_slots[1].remaining == 0
    assert gained.actor_after.resource_pools[0].current == 2
    assert created.actor_after.resource_pools[0].current == 0
    assert created.actor_after.spell_slots[-1].temporary is True
    assert created.actor_after.spell_slots[-1].remaining == 1


def test_fiend_evoker_and_agonizing_blast_formulas():
    warlock = _actor("dark_ones_blessing", "agonizing_blast")
    evoker = _actor("sculpt_spells")
    source = AttackSource(
        id="eldritch_blast",
        name="Eldritch Blast",
        source_type=AttackSourceType.SPELL,
        range_feet=120,
        attack_kind=AttackKind.RANGED,
        attack_roll_request=D20RollRequest(),
        damage_type="force",
        damage_die_sides=10,
        damage_components=(
            DamageComponentSpec(
                id="base",
                damage_type=DamageType.FORCE,
                dice=DiceExpression(1, 10),
            ),
        ),
    )

    modified = apply_agonizing_blast(warlock, source)

    assert dark_ones_blessing_temporary_hit_points(warlock) == 6
    assert sculpt_spells_protected_creature_count(evoker) == 4
    assert modified.damage_modifier == 3
    assert modified.damage_components[0].modifier == 3


def test_bardic_inspiration_spends_bonus_action_and_grants_die():
    bard = replace(
        _actor("bardic_inspiration"),
        resource_pools=(
            ActorResourcePool(
                "bardic_inspiration_uses",
                "Bardic Inspiration",
                3,
                3,
                RecoveryPeriod.LONG_REST,
            ),
        ),
    )
    ally = replace(
        _actor(),
        id=ActorId("ally"),
        position=Coordinate(3, 1),
    )
    enemy = replace(
        _actor(),
        id=ActorId("enemy"),
        faction=Faction.ENEMY,
        position=Coordinate(8, 8),
    )

    result = resolve_bardic_inspiration(
        _state(bard, ally, enemy),
        (),
        target_id="ally",
    )

    assert result.die_sides == 6
    assert result.state.turn_action.bonus_action_use == ActionUse.ACTION_USED
    assert result.bard_after.resource_pools[0].current == 2
    assert result.active_effects[0].actor_id == "ally"


def test_patient_defense_and_step_of_wind_spend_ki():
    monk = replace(
        _actor("ki"),
        resource_pools=(
            ActorResourcePool(
                "ki_points",
                "Ki",
                3,
                3,
                RecoveryPeriod.SHORT_REST,
            ),
        ),
    )
    enemy = replace(_actor(), id=ActorId("enemy"), faction=Faction.ENEMY)

    patient = resolve_patient_defense(_state(monk, enemy), ())
    step = resolve_step_of_the_wind(_state(monk, enemy), ())

    assert patient.actor_after.resource_pools[0].current == 2
    assert patient.active_effects[0].kind == "dodge_until_next_turn"
    assert step.actor_after.resource_pools[0].current == 2
    assert step.state.turn_action.extra_movement_feet == monk.speed_feet
    assert step.active_effects[0].kind == "disengage_until_turn_end"


def test_martial_arts_and_flurry_queue_the_correct_unarmed_strikes():
    monk = replace(
        _actor("martial_arts", "ki"),
        resource_pools=(
            ActorResourcePool(
                "ki_points",
                "Ki",
                3,
                3,
                RecoveryPeriod.SHORT_REST,
            ),
        ),
    )
    enemy = replace(_actor(), id=ActorId("enemy"), faction=Faction.ENEMY)
    attacked = replace(
        _state(monk, enemy),
        turn_action=replace(
            _state(monk, enemy).turn_action,
            action_use=ActionUse.ACTION_USED,
            attack_action_active=True,
            attacks_used=1,
            attacks_maximum=1,
        ),
    )

    martial = resolve_martial_arts_bonus_attack(attacked)
    flurry = resolve_flurry_of_blows(attacked)

    assert martial.state.turn_action.bonus_attacks_remaining == 1
    assert martial.state.turn_action.bonus_attack_source_id == "unarmed_strike"
    assert martial.state.turn_action.bonus_action_use == ActionUse.ACTION_USED
    assert flurry.state.turn_action.bonus_attacks_remaining == 2
    assert flurry.actor_after.resource_pools[0].current == 2


def test_preserve_life_spends_channel_and_heals_only_to_half():
    cleric = replace(
        _actor("channel_divinity_preserve_life"),
        resource_pools=(
            ActorResourcePool(
                "channel_divinity_uses",
                "Channel Divinity",
                1,
                1,
                RecoveryPeriod.SHORT_REST,
            ),
        ),
    )
    ally = replace(
        _actor(hp=2, max_hp=20),
        id=ActorId("ally"),
        position=Coordinate(2, 1),
    )
    enemy = replace(
        _actor(),
        id=ActorId("enemy"),
        faction=Faction.ENEMY,
        position=Coordinate(8, 8),
    )

    result = resolve_preserve_life(
        _state(cleric, ally, enemy),
        (PreserveLifeAllocation("ally", 8),),
    )

    healed = next(actor for actor in result.state.actors if actor.id == ally.id)
    assert healed.hp == 10
    assert result.healing_spent == 8
    assert result.cleric_after.resource_pools[0].current == 0


def test_divine_sense_spends_action_and_reports_types_without_locations():
    paladin = replace(
        _actor("divine_sense"),
        resource_pools=(
            ActorResourcePool(
                "divine_sense_uses",
                "Divine Sense",
                2,
                2,
                RecoveryPeriod.LONG_REST,
            ),
        ),
    )
    fiend = replace(
        _actor(),
        id=ActorId("fiend"),
        faction=Faction.ENEMY,
        creature_type="fiend",
        position=Coordinate(3, 1),
    )

    result = resolve_divine_sense(_state(paladin, fiend))

    assert result.detected_creature_types == ("fiend",)
    assert result.state.turn_action.action_use == ActionUse.ACTION_USED
    assert result.actor_after.resource_pools[0].current == 1


def test_sacred_weapon_tracks_selected_weapon_and_modifies_only_its_attacks():
    sword = InventoryItem(
        id="sword",
        name="Sword",
        kind="weapon",
        equipped=True,
        source_ref="longsword",
        hands_required=1,
        held_in=(HandSlot.MAIN_HAND,),
    )
    paladin = replace(
        _actor("channel_divinity_sacred_weapon"),
        inventory=(sword,),
        resource_pools=(
            ActorResourcePool(
                "channel_divinity_uses",
                "Channel Divinity",
                1,
                1,
                RecoveryPeriod.SHORT_REST,
            ),
        ),
    )
    enemy = replace(_actor(), id=ActorId("enemy"), faction=Faction.ENEMY)

    result = resolve_sacred_weapon(_state(paladin, enemy), ())

    assert result.weapon_item_id == "sword"
    assert result.attack_bonus == 3
    assert result.active_effects[0].object_id == "weapon:sword"
    assert result.actor_after.resource_pools[0].current == 0
