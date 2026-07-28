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
