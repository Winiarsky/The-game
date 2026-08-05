from dataclasses import replace

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    Faction,
    FeatureGrant,
    FeatureSourceKind,
)
from dnd_board_game.combat import (
    ActionEconomyCost,
    ActiveCombatEffect,
    InitiativeEntry,
    InitiativeOrder,
    SceneAbilityCheck,
    SceneInteractionCondition,
    SceneInteractionEffect,
    SceneInteraction,
    SceneObject,
    AttackSource,
    AttackSourceType,
    apply_combat_interaction_effects,
    attack_source_with_combat_effects,
    attack_source_with_target_combat_effects,
    available_combat_interaction_options,
    available_scene_interactions,
    combat_interaction_hint_positions,
    consume_next_attack_effects,
    expire_combat_effects,
    expire_invalid_combat_effects,
    expire_turn_start_effects,
    replace_actor,
    resolve_scene_interaction,
    start_combat,
)
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    EffectDuration,
    EffectEvent,
    EffectEventType,
    RollMode,
    RollModifier,
    RollModifierType,
    resolve_d20_roll,
)
from dnd_board_game.world import Coordinate


def test_interaction_without_check_sets_success_flag():
    interaction = SceneInteraction(
        "open_crate",
        "Otwórz skrzynię",
        success_flag="crate_opened",
        success_message="Skrzynia została otwarta.",
    )

    result = resolve_scene_interaction(interaction)

    assert result.success is True
    assert result.flag_key == "crate_opened"
    assert result.message == "Skrzynia została otwarta."


def test_interaction_with_ability_check_succeeds_on_total_at_least_dc():
    interaction = SceneInteraction(
        "inspect_crate",
        "Zbadaj skrzynię",
        ability_check=SceneAbilityCheck(
            ability="wisdom",
            skill="perception",
            dc=12,
            modifiers=(RollModifier("Biegłość w Percepcji", 2, RollModifierType.PROFICIENCY, "proficiency"),),
        ),
        success_flag="crate_secured",
        failure_flag="crate_trap_missed",
        success_message="Zabezpieczasz skrzynię.",
        failure_message="Nie dostrzegasz mechanizmu.",
    )

    result = resolve_scene_interaction(interaction, natural_roll=10)

    assert result.success is True
    assert result.flag_key == "crate_secured"
    assert result.roll is not None
    assert result.roll.total == 12


def test_interaction_with_ability_check_failure_sets_failure_flag():
    interaction = SceneInteraction(
        "inspect_crate",
        "Zbadaj skrzynię",
        ability_check=SceneAbilityCheck("wisdom", 12),
        success_flag="crate_secured",
        failure_flag="crate_trap_missed",
        failure_message="Nie dostrzegasz niczego podejrzanego.",
    )

    result = resolve_scene_interaction(interaction, natural_roll=5)

    assert result.success is False
    assert result.flag_key == "crate_trap_missed"
    assert result.message == "Nie dostrzegasz niczego podejrzanego."


def test_scene_object_without_explicit_interactions_gets_default_interaction():
    scene_object = SceneObject("crate", "Skrzynia", (Coordinate(1, 0),), "Zbadaj")

    interactions = available_scene_interactions(scene_object)

    assert len(interactions) == 1
    assert interactions[0].id == "interact_crate"
    assert interactions[0].label == "Zbadaj"


def test_combat_interaction_conditions_return_available_option():
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(5, 5))
    state = _combat_state(hero, enemy)
    scene_object = SceneObject(
        "cart",
        "Wóz",
        (Coordinate(1, 0),),
        "Użyj wozu",
        interactions=(
            SceneInteraction(
                "take_cover",
                "Otrzymaj osłonę",
                conditions=(
                    SceneInteractionCondition("action_available"),
                    SceneInteractionCondition("actor_adjacent_to_object"),
                ),
                effects=(SceneInteractionEffect("grant_ac_bonus_until_move", (("value", 2),)),),
            ),
        ),
    )

    options = available_combat_interaction_options((scene_object,), state, hero, Coordinate(1, 0))

    assert len(options) == 1
    assert options[0].id == "take_cover"
    assert "akcja główna jest dostępna" in options[0].conditions


def test_fast_hands_changes_use_object_action_into_bonus_action():
    rogue = replace(
        _actor("rogue", Faction.ALLY, Coordinate(0, 0)),
        features=(
            FeatureGrant(
                "fast_hands",
                "Fast Hands",
                FeatureSourceKind.SUBCLASS,
                "thief",
            ),
        ),
    )
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(5, 5))
    state = _combat_state(rogue, enemy)
    scene_object = SceneObject(
        "lever",
        "Dźwignia",
        (Coordinate(1, 0),),
        "Przestaw",
        interactions=(
            SceneInteraction(
                "pull_lever",
                "Przestaw dźwignię",
                action_cost=ActionEconomyCost.ACTION,
            ),
        ),
    )

    options = available_combat_interaction_options(
        (scene_object,),
        state,
        rogue,
        Coordinate(1, 0),
    )

    assert options[0].action_cost == ActionEconomyCost.BONUS_ACTION


def test_combat_interaction_hints_include_reachable_object_before_conditions_are_met():
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(5, 5))
    state = _combat_state(hero, enemy)
    scene_object = SceneObject(
        "cart",
        "Wóz",
        (Coordinate(2, 0),),
        "Użyj wozu",
        interactions=(
            SceneInteraction(
                "take_cover",
                "Otrzymaj osłonę",
                conditions=(SceneInteractionCondition("actor_adjacent_to_object"),),
            ),
        ),
    )

    options = available_combat_interaction_options((scene_object,), state, hero, Coordinate(2, 0))
    hints = combat_interaction_hint_positions((scene_object,), state, hero, frozenset({Coordinate(2, 0)}))

    assert options == ()
    assert hints == (Coordinate(2, 0),)


def test_combat_interaction_applies_and_expires_ac_bonus():
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), ac=14)
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(5, 5))
    state = _combat_state(hero, enemy)
    scene_object = SceneObject("cart", "Wóz", (Coordinate(1, 0),), "Użyj wozu", cover_bonus=2)
    interaction = SceneInteraction(
        "take_cover",
        "Otrzymaj osłonę",
        effects=(SceneInteractionEffect("grant_ac_bonus_until_move", (("value", 2), ("label", "Osłona: wóz"))),),
    )

    applied = apply_combat_interaction_effects(
        state=state,
        actor=hero,
        scene_object=scene_object,
        interaction=interaction,
        target_position=Coordinate(1, 0),
        active_effects=(),
    )
    protected = next(actor for actor in applied.state.actors if actor.id == hero.id)

    assert protected.ac == 16
    assert applied.active_effects[0].kind == "grant_ac_bonus_until_move"

    moved_state = replace_actor(applied.state, replace(protected, position=Coordinate(0, 1)))
    expired_state, active_effects = expire_invalid_combat_effects(moved_state, (scene_object,), applied.active_effects)
    expired = next(actor for actor in expired_state.actors if actor.id == hero.id)

    assert expired.ac == 14
    assert active_effects == ()


def test_encounter_end_expires_scene_cover_and_restores_materialized_ac():
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0), ac=14)
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(5, 5))
    state = _combat_state(hero, enemy)
    scene_object = SceneObject("cart", "Wóz", (Coordinate(1, 0),), "Użyj wozu", cover_bonus=2)
    interaction = SceneInteraction(
        "take_cover",
        "Otrzymaj osłonę",
        effects=(SceneInteractionEffect("grant_ac_bonus_until_move", (("value", 2),)),),
    )
    applied = apply_combat_interaction_effects(
        state=state,
        actor=hero,
        scene_object=scene_object,
        interaction=interaction,
        target_position=Coordinate(1, 0),
        active_effects=(),
    )

    expired_state, active_effects, expired_effects = expire_combat_effects(
        applied.state,
        applied.active_effects,
        EffectEvent(EffectEventType.ENCOUNTER_ENDED),
    )

    assert next(actor for actor in expired_state.actors if actor.id == hero.id).ac == 14
    assert active_effects == ()
    assert expired_effects == applied.active_effects


def test_rubble_interaction_requires_actor_on_object_and_adjacent_enemy():
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1))
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(2, 1))
    state = _combat_state(hero, enemy)
    scene_object = SceneObject(
        "rubble",
        "Rumowisko",
        (Coordinate(1, 1),),
        "Użyj rumowiska",
        interactions=(
            SceneInteraction(
                "throw_rubble",
                "Sypnij gruzem",
                conditions=(
                    SceneInteractionCondition("action_available"),
                    SceneInteractionCondition("actor_on_object"),
                    SceneInteractionCondition("adjacent_enemy_exists"),
                ),
            ),
        ),
    )

    options = available_combat_interaction_options((scene_object,), state, hero, Coordinate(1, 1))

    assert len(options) == 1
    assert options[0].id == "throw_rubble"

    moved_hero = replace(hero, position=Coordinate(0, 0))
    moved_state = _combat_state(moved_hero, enemy)

    assert available_combat_interaction_options((scene_object,), moved_state, moved_hero, Coordinate(1, 1)) == ()


def test_rubble_interaction_adds_next_attack_penalty_and_consumes_it():
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1))
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(2, 1))
    state = _combat_state(hero, enemy)
    scene_object = SceneObject("rubble", "Rumowisko", (Coordinate(1, 1),), "Użyj rumowiska")
    interaction = SceneInteraction(
        "throw_rubble",
        "Sypnij gruzem",
        effects=(SceneInteractionEffect("grant_next_attack_penalty", (("value", -2), ("label", "Gruz w oczach"))),),
    )
    source = AttackSource(
        "Szabla",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(modifiers=(RollModifier("Siła", 2, RollModifierType.ABILITY, "strength"),)),
    )

    applied = apply_combat_interaction_effects(
        state=state,
        actor=hero,
        scene_object=scene_object,
        interaction=interaction,
        target_position=Coordinate(1, 1),
        active_effects=(),
    )
    modified_source = attack_source_with_combat_effects(enemy, source, applied.active_effects)

    assert applied.active_effects[0].actor_id == str(enemy.id)
    assert applied.active_effects[0].kind == "grant_next_attack_penalty"
    assert applied.active_effects[0].value == -2
    assert "Goblin" in applied.message
    assert any(modifier.label == "Gruz w oczach" and modifier.value == -2 for modifier in modified_source.attack_roll_request.modifiers)
    assert consume_next_attack_effects(applied.active_effects, str(enemy.id)) == ()


def test_magic_weapon_bonus_applies_only_to_enchanted_weapon_source() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1))
    longsword = AttackSource(
        "Długi miecz",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
        source_item_id="longsword",
        damage_modifier=3,
    )
    longbow = replace(
        longsword,
        name="Długi łuk",
        source_item_id="longbow",
    )
    effect = ActiveCombatEffect(
        id="magic-weapon",
        actor_id="hero",
        kind="magic_weapon",
        label="Magiczna broń",
        object_id="weapon:longsword",
        value=1,
    )

    enchanted = attack_source_with_combat_effects(hero, longsword, (effect,))
    untouched = attack_source_with_combat_effects(hero, longbow, (effect,))

    assert any(
        modifier.label == "Magiczna broń" and modifier.value == 1
        for modifier in enchanted.attack_roll_request.modifiers
    )
    assert enchanted.damage_modifier == 4
    assert untouched == longbow


def test_vicious_mockery_disadvantages_only_next_weapon_attack() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1))
    effect = ActiveCombatEffect(
        id="vicious-mockery:hero",
        actor_id="hero",
        kind="vicious_mockery_disadvantage",
        label="Zjadliwa kpina",
        object_id="spell:vicious_mockery",
        value=0,
        duration=EffectDuration.UNTIL_NEXT_ATTACK,
    )
    weapon = AttackSource(
        "Długi miecz",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
    )
    spell = AttackSource(
        "Ognisty pocisk",
        AttackSourceType.SPELL,
        120,
        D20RollRequest(),
    )

    mocked_weapon = attack_source_with_combat_effects(hero, weapon, (effect,))
    mocked_spell = attack_source_with_combat_effects(hero, spell, (effect,))

    assert mocked_weapon.attack_roll_request.mode == RollMode.DISADVANTAGE
    assert mocked_spell.attack_roll_request.mode == RollMode.NORMAL
    assert consume_next_attack_effects((effect,), "hero") == ()


def test_true_strike_advantage_applies_only_against_declared_target() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1))
    marked = _actor("marked", Faction.ENEMY, Coordinate(2, 1))
    other = _actor("other", Faction.ENEMY, Coordinate(1, 2))
    effect = ActiveCombatEffect(
        id="true-strike:hero:marked",
        actor_id="hero",
        kind="next_attack_advantage",
        label="Prawdziwe uderzenie",
        object_id="spell:true_strike",
        value=0,
        target_actor_id="marked",
        duration=EffectDuration.CONCENTRATION,
    )
    source = AttackSource(
        "Krótki miecz",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
    )

    against_marked = attack_source_with_target_combat_effects(
        hero,
        marked,
        source,
        (effect,),
    )
    against_other = attack_source_with_target_combat_effects(
        hero,
        other,
        source,
        (effect,),
    )

    assert against_marked.attack_roll_request.mode == RollMode.ADVANTAGE
    assert against_other.attack_roll_request.mode == RollMode.NORMAL


def test_protection_from_evil_and_good_hinders_listed_creature_attacks() -> None:
    attacker = replace(
        _actor("undead", Faction.ENEMY, Coordinate(1, 1)),
        creature_type="undead",
    )
    protected = _actor("protected", Faction.ALLY, Coordinate(2, 1))
    effect = ActiveCombatEffect(
        id="protection:protected",
        actor_id="protected",
        kind="protection_from_evil_and_good",
        label="Ochrona przed dobrem i złem",
        object_id="spell:protection_from_evil_and_good",
        value=0,
    )
    source = AttackSource(
        "Szpony",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
    )

    modified = attack_source_with_target_combat_effects(
        attacker,
        protected,
        source,
        (effect,),
    )

    assert modified.attack_roll_request.mode == RollMode.DISADVANTAGE


def test_hunters_mark_adds_one_d6_only_to_casters_weapon_hits() -> None:
    from dnd_board_game.combat import DamageComponentSpec, DamageType
    from dnd_board_game.rules import DiceExpression

    ranger = _actor("ranger", Faction.ALLY, Coordinate(0, 0))
    ally = _actor("ally", Faction.ALLY, Coordinate(0, 1))
    marked = _actor("marked", Faction.ENEMY, Coordinate(1, 0))
    other = _actor("other", Faction.ENEMY, Coordinate(1, 1))
    source = AttackSource(
        "Łuk",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
        damage_components=(
            DamageComponentSpec(
                "bow",
                DamageType.PIERCING,
                DiceExpression(1, 8),
                label="Łuk",
            ),
        ),
    )
    mark = ActiveCombatEffect(
        id="hunters-mark:ranger:marked",
        actor_id=str(marked.id),
        kind="hunters_mark",
        label="Znak łowcy",
        object_id="spell:hunters_mark",
        value=6,
        source_actor_id=str(ranger.id),
        target_actor_id=str(marked.id),
    )

    marked_source = attack_source_with_target_combat_effects(
        ranger, marked, source, (mark,)
    )
    marked_source_again = attack_source_with_target_combat_effects(
        ranger, marked, marked_source, (mark,)
    )
    wrong_attacker = attack_source_with_target_combat_effects(
        ally, marked, source, (mark,)
    )
    wrong_target = attack_source_with_target_combat_effects(
        ranger, other, source, (mark,)
    )

    assert marked_source.damage_components[-1].dice == DiceExpression(1, 6)
    assert marked_source.damage_components[-1].label == "Znak łowcy"
    assert len(marked_source_again.damage_components) == 2
    assert len(wrong_attacker.damage_components) == 1
    assert len(wrong_target.damage_components) == 1


def test_branding_smite_accepts_ranged_weapon_attack() -> None:
    from dnd_board_game.combat import AttackKind, DamageComponentSpec, DamageType
    from dnd_board_game.rules import DiceExpression

    paladin = _actor("paladin", Faction.ALLY, Coordinate(0, 0))
    bow = AttackSource(
        "Łuk",
        AttackSourceType.WEAPON,
        150,
        D20RollRequest(),
        damage_components=(
            DamageComponentSpec(
                "bow",
                DamageType.PIERCING,
                DiceExpression(1, 8),
                label="Łuk",
            ),
        ),
        attack_kind=AttackKind.RANGED,
    )
    effect = ActiveCombatEffect(
        id="branding-smite:paladin",
        actor_id="paladin",
        kind="branding_smite",
        label="Piętnujące porażenie",
        object_id="spell:branding_smite",
        value=2,
    )

    branded = attack_source_with_combat_effects(paladin, bow, (effect,))

    assert branded.damage_components[-1].dice == DiceExpression(2, 6)
    assert branded.damage_components[-1].damage_type == DamageType.RADIANT


def test_flame_blade_replaces_weapon_proxy_with_melee_spell_attack() -> None:
    from dnd_board_game.combat import DamageComponentSpec, DamageType
    from dnd_board_game.rules import DiceExpression

    druid = _actor("druid", Faction.ALLY, Coordinate(0, 0))
    scimitar = AttackSource(
        "Bułat",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
        damage_components=(
            DamageComponentSpec(
                "scimitar",
                DamageType.SLASHING,
                DiceExpression(1, 6),
                label="Bułat",
            ),
        ),
        ability="dexterity",
    )
    effect = ActiveCombatEffect(
        id="flame-blade:druid",
        actor_id="druid",
        kind="flame_blade",
        label="Ostrze płomieni",
        object_id="spell:flame_blade",
        value=3,
    )

    blade = attack_source_with_combat_effects(druid, scimitar, (effect,))

    assert blade.id == "flame_blade"
    assert blade.name == "Ostrze płomieni"
    assert blade.source_type == AttackSourceType.SPELL
    assert blade.ability == "wisdom"
    assert blade.damage_components == (
        DamageComponentSpec(
            "flame_blade",
            DamageType.FIRE,
            DiceExpression(3, 6),
            label="Ostrze płomieni",
        ),
    )


def test_heat_metal_penalty_disadvantages_wearers_attacks() -> None:
    wearer = _actor("wearer", Faction.ENEMY, Coordinate(0, 0))
    source = AttackSource(
        "Miecz",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
    )
    effect = ActiveCombatEffect(
        id="heat-metal:wearer",
        actor_id="wearer",
        kind="heat_metal_disadvantage",
        label="Rozgrzany metal",
        object_id="spell:heat_metal",
        value=0,
    )

    heated = attack_source_with_combat_effects(wearer, source, (effect,))

    assert heated.attack_roll_request.mode == RollMode.DISADVANTAGE


def test_blindsight_or_truesight_ignores_blur_within_sense_range() -> None:
    from dnd_board_game.actors.senses import ActorSenseProfile

    ordinary = _actor("ordinary", Faction.ENEMY, Coordinate(0, 0))
    seer = replace(
        _actor("seer", Faction.ENEMY, Coordinate(0, 0)),
        senses=ActorSenseProfile(blindsight_feet=30),
    )
    blurred = _actor("blurred", Faction.ALLY, Coordinate(3, 0))
    source = AttackSource(
        "Miecz",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
    )
    effect = ActiveCombatEffect(
        id="blur:blurred",
        actor_id="blurred",
        kind="attacks_against_disadvantage",
        label="Rozmycie",
        object_id="spell:blur",
        value=0,
    )

    ordinary_attack = attack_source_with_target_combat_effects(
        ordinary, blurred, source, (effect,)
    )
    sighted_attack = attack_source_with_target_combat_effects(
        seer, blurred, source, (effect,)
    )

    assert ordinary_attack.attack_roll_request.mode == RollMode.DISADVANTAGE
    assert sighted_attack.attack_roll_request.mode == RollMode.NORMAL


def test_darkvision_negates_nonmagical_ambient_darkness_within_range() -> None:
    from dnd_board_game.actors.senses import ActorSenseProfile

    brakka = replace(
        _actor("brakka", Faction.ALLY, Coordinate(0, 0)),
        senses=ActorSenseProfile(darkvision_feet=60),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(6, 0))
    source = AttackSource("Topór", AttackSourceType.WEAPON, 5, D20RollRequest())
    darkness = ActiveCombatEffect(
        id="ambient_darkness:crypt",
        actor_id="environment",
        kind="ambient_darkness",
        label="Niemagiczna ciemność",
        object_id="zone:crypt",
        value=0,
    )

    effective = attack_source_with_target_combat_effects(
        brakka,
        enemy,
        source,
        (darkness,),
    )

    assert effective.attack_roll_request.mode == RollMode.ADVANTAGE


def test_darkvision_does_not_reach_beyond_sixty_feet_in_ambient_darkness() -> None:
    from dnd_board_game.actors.senses import ActorSenseProfile

    brakka = replace(
        _actor("brakka", Faction.ALLY, Coordinate(0, 0)),
        senses=ActorSenseProfile(darkvision_feet=60),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(13, 0))
    source = AttackSource("Topór", AttackSourceType.WEAPON, 5, D20RollRequest())
    darkness = ActiveCombatEffect(
        id="ambient_darkness:crypt",
        actor_id="environment",
        kind="ambient_darkness",
        label="Niemagiczna ciemność",
        object_id="zone:crypt",
        value=0,
    )

    effective = attack_source_with_target_combat_effects(
        brakka,
        enemy,
        source,
        (darkness,),
    )

    assert effective.attack_roll_request.mode == RollMode.NORMAL


def test_shillelagh_uses_spellcasting_modifier_and_d8_for_club() -> None:
    hero = replace(
        _actor("hero", Faction.ALLY, Coordinate(1, 1)),
        spell_save_dc=14,
    )
    effect = ActiveCombatEffect(
        id="shillelagh:hero",
        actor_id="hero",
        kind="shillelagh",
        label="Kostur",
        object_id="spell:shillelagh",
        value=0,
    )
    club = AttackSource(
        id="club",
        name="Pałka",
        source_type=AttackSourceType.WEAPON,
        range_feet=5,
        attack_roll_request=D20RollRequest(),
        damage_hint="1d4",
        damage_components=(),
        proficiency_id="club",
        ability="strength",
    )
    from dnd_board_game.combat import DamageComponentSpec, DamageType
    from dnd_board_game.rules import DiceExpression

    club = replace(
        club,
        damage_components=(
            DamageComponentSpec(
                id="club",
                damage_type=DamageType.BLUDGEONING,
                dice=DiceExpression(1, 4),
            ),
        ),
    )

    enchanted = attack_source_with_combat_effects(hero, club, (effect,))

    assert enchanted.ability == "wisdom"
    assert enchanted.damage_components[0].dice == DiceExpression(1, 8)
    assert any(
        modifier.label == "Shillelagh"
        for modifier in enchanted.attack_roll_request.modifiers
    )


def test_ray_of_enfeeblement_halves_only_strength_weapon_damage() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1))
    effect = ActiveCombatEffect(
        id="ray:hero",
        actor_id="hero",
        kind="ray_of_enfeeblement",
        label="Promień osłabienia",
        object_id="spell:ray_of_enfeeblement",
        value=0,
        source_actor_id="wizard",
        duration=EffectDuration.CONCENTRATION,
    )
    strength_weapon = AttackSource(
        "Młot",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
        ability="strength",
    )
    dexterity_weapon = replace(
        strength_weapon,
        name="Rapier",
        ability="dexterity",
    )
    strength_spell = replace(
        strength_weapon,
        name="Czar Siły",
        source_type=AttackSourceType.SPELL,
    )

    assert (
        attack_source_with_combat_effects(hero, strength_weapon, (effect,)).damage_divisor
        == 2
    )
    assert (
        attack_source_with_combat_effects(hero, dexterity_weapon, (effect,)).damage_divisor
        == 1
    )
    assert (
        attack_source_with_combat_effects(hero, strength_spell, (effect,)).damage_divisor
        == 1
    )


def test_help_effect_grants_advantage_against_specific_target_and_is_consumed():
    helper = _actor("helper", Faction.ALLY, Coordinate(0, 0))
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0))
    target = _actor("goblin", Faction.ENEMY, Coordinate(0, 1))
    other = _actor("orc", Faction.ENEMY, Coordinate(2, 0))
    source = AttackSource("Miecz", AttackSourceType.WEAPON, 5, D20RollRequest())
    effect = ActiveCombatEffect(
        id="help:helper:ally:goblin",
        actor_id=str(ally.id),
        kind="help_attack_advantage",
        label="Pomoc",
        object_id="combat_action:help",
        value=0,
        source_actor_id=str(helper.id),
        target_actor_id=str(target.id),
    )

    helped = attack_source_with_target_combat_effects(ally, target, source, (effect,))
    other_target = attack_source_with_target_combat_effects(ally, other, source, (effect,))

    assert helped.attack_roll_request.mode == RollMode.ADVANTAGE
    assert other_target.attack_roll_request.mode == RollMode.NORMAL
    assert consume_next_attack_effects((effect,), str(ally.id), str(other.id)) == (effect,)
    assert consume_next_attack_effects((effect,), str(ally.id), str(target.id)) == ()


def test_invisibility_grants_attack_advantage_and_ends_after_attack() -> None:
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0))
    target = _actor("goblin", Faction.ENEMY, Coordinate(0, 1))
    source = AttackSource("Miecz", AttackSourceType.WEAPON, 5, D20RollRequest())
    effect = ActiveCombatEffect(
        id="invisibility:wizard:ally",
        actor_id=str(ally.id),
        kind="invisibility",
        label="Niewidzialność",
        object_id="spell:invisibility",
        value=0,
        source_actor_id="wizard",
        target_actor_id=str(ally.id),
        duration=EffectDuration.CONCENTRATION,
    )

    modified = attack_source_with_target_combat_effects(
        ally,
        target,
        source,
        (effect,),
    )

    assert modified.attack_roll_request.mode == RollMode.ADVANTAGE
    assert consume_next_attack_effects((effect,), str(ally.id), str(target.id)) == ()


def test_see_invisibility_cancels_only_invisibility_attack_modifiers() -> None:
    seer = _actor("seer", Faction.ALLY, Coordinate(1, 0))
    invisible_enemy = _actor("enemy", Faction.ENEMY, Coordinate(0, 1))
    source = AttackSource("Miecz", AttackSourceType.WEAPON, 5, D20RollRequest())
    invisibility = ActiveCombatEffect(
        id="invisibility:enemy",
        actor_id="enemy",
        kind="invisibility",
        label="Niewidzialność",
        object_id="spell:invisibility",
        value=0,
        source_actor_id="enemy",
        duration=EffectDuration.CONCENTRATION,
    )
    sight = ActiveCombatEffect(
        id="see-invisibility:seer",
        actor_id="seer",
        kind="see_invisibility",
        label="Widzenie niewidzialnego",
        object_id="spell:see_invisibility",
        value=0,
        source_actor_id="seer",
        duration=EffectDuration.UNTIL_ENCOUNTER_END,
    )

    without_sight = attack_source_with_target_combat_effects(
        seer,
        invisible_enemy,
        source,
        (invisibility,),
    )
    with_sight = attack_source_with_target_combat_effects(
        seer,
        invisible_enemy,
        source,
        (invisibility, sight),
    )
    enemy_attacks_seer = attack_source_with_target_combat_effects(
        invisible_enemy,
        seer,
        source,
        (invisibility, sight),
    )

    assert without_sight.attack_roll_request.mode == RollMode.DISADVANTAGE
    assert with_sight.attack_roll_request.mode == RollMode.NORMAL
    assert enemy_attacks_seer.attack_roll_request.mode == RollMode.NORMAL


def test_sanctuary_ends_when_protected_actor_makes_attack() -> None:
    sanctuary = ActiveCombatEffect(
        id="sanctuary:ally",
        actor_id="ally",
        kind="sanctuary",
        label="Sanktuarium",
        object_id="spell:sanctuary",
        value=0,
        source_actor_id="cleric",
        target_actor_id="ally",
        duration=EffectDuration.UNTIL_ENCOUNTER_END,
    )

    assert consume_next_attack_effects((sanctuary,), "ally", "goblin") == ()


def test_help_effect_cancels_disadvantage_and_expires_on_helper_turn_start():
    helper = _actor("helper", Faction.ALLY, Coordinate(0, 0))
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0))
    target = _actor("goblin", Faction.ENEMY, Coordinate(0, 1))
    source = AttackSource("Miecz", AttackSourceType.WEAPON, 5, D20RollRequest(mode=RollMode.DISADVANTAGE))
    effect = ActiveCombatEffect(
        id="help:helper:ally:goblin",
        actor_id=str(ally.id),
        kind="help_attack_advantage",
        label="Pomoc",
        object_id="combat_action:help",
        value=0,
        source_actor_id=str(helper.id),
        target_actor_id=str(target.id),
    )

    helped = attack_source_with_target_combat_effects(ally, target, source, (effect,))

    assert helped.attack_roll_request.mode == RollMode.NORMAL
    assert expire_turn_start_effects((effect,), str(ally.id)) == (effect,)
    assert expire_turn_start_effects((effect,), str(helper.id)) == ()


def test_unconscious_target_grants_attack_advantage():
    attacker = _actor("attacker", Faction.ALLY, Coordinate(0, 0))
    target = replace(
        _actor("target", Faction.ENEMY, Coordinate(1, 0)),
        hp=0,
        uses_death_saves=True,
    )
    source = AttackSource("Miecz", AttackSourceType.WEAPON, 5, D20RollRequest())

    effective = attack_source_with_target_combat_effects(attacker, target, source, ())

    assert effective.attack_roll_request.mode == RollMode.ADVANTAGE


def test_rubble_interaction_resolves_enemy_dexterity_save_before_penalty():
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 1))
    enemy = _actor("goblin", Faction.ENEMY, Coordinate(2, 1), dexterity=14)
    state = _combat_state(hero, enemy)
    scene_object = SceneObject("rubble", "Rumowisko", (Coordinate(1, 1),), "Użyj rumowiska")
    interaction = SceneInteraction(
        "throw_rubble",
        "Sypnij gruzem",
        effects=(
            SceneInteractionEffect(
                "grant_next_attack_penalty",
                (("value", -2), ("label", "Gruz w oczach"), ("saving_throw_ability", "dexterity"), ("saving_throw_dc", 12)),
            ),
        ),
    )

    failed = apply_combat_interaction_effects(
        state=state,
        actor=hero,
        scene_object=scene_object,
        interaction=interaction,
        target_position=Coordinate(1, 1),
        active_effects=(),
        saving_throw_rolls={str(enemy.id): 5},
    )
    succeeded = apply_combat_interaction_effects(
        state=state,
        actor=hero,
        scene_object=scene_object,
        interaction=interaction,
        target_position=Coordinate(1, 1),
        active_effects=(),
        saving_throw_rolls={str(enemy.id): 15},
    )

    assert failed.saving_throw is not None
    assert failed.saving_throw.natural_roll == 5
    assert failed.saving_throw.modifier == 2
    assert failed.saving_throw.total == 7
    assert failed.saving_throw.dc == 12
    assert failed.saving_throw.success is False
    assert failed.active_effects[0].kind == "grant_next_attack_penalty"
    assert "rzut obronny na Zręczność" in failed.message
    assert "Porażka" in failed.message

    assert succeeded.saving_throw is not None
    assert succeeded.saving_throw.total == 17
    assert succeeded.saving_throw.success is True
    assert succeeded.active_effects == ()
    assert "Sukces" in succeeded.message


def _actor(actor_id: str, faction: Faction, position: Coordinate, *, ac: int = 12, dexterity: int = 10) -> Actor:
    return Actor(
        ActorId(actor_id),
        actor_id.title(),
        ac,
        10,
        0,
        30,
        position,
        faction,
        ability_scores=AbilityScores(dexterity=dexterity),
    )


def _combat_state(*actors: Actor):
    entries = []
    for index, actor in enumerate(actors):
        roll = resolve_d20_roll(D20RollInput(D20RollRequest(), 10 + index))
        entries.append(InitiativeEntry(actor, roll, 0, index))
    return start_combat(tuple(actors), InitiativeOrder(tuple(entries)))
