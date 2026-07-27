import json
from pathlib import Path

import pytest

from dnd_board_game.actors import CreatureSize, Faction
from dnd_board_game.combat import (
    ActionEconomyCost,
    AttackKind,
    CombatCondition,
    AttackSourceType,
    DamageType,
    EnvironmentSetupType,
    SceneObjectiveCondition,
    SetupVisibility,
    SpellCastingKind,
)
from dnd_board_game.exploration import NpcOutcomeTier, SceneMode
from dnd_board_game.inventory import HandSlot, effective_armor_class
from dnd_board_game.scenarios import (
    RULESET_DND_5E_2014,
    SCENARIO_SCHEMA,
    build_encounter_from_scenario,
    build_exploration_from_scenario,
    load_scenario,
)
from dnd_board_game.world import Coordinate, find_path


def _abandoned_watchtower_data_without_refs():
    base = Path("content/scenarios/abandoned_watchtower")
    data = json.loads((base / "scenario.json").read_text(encoding="utf-8"))
    data.pop("parts", None)
    data["actors"] = json.loads((base / "actors.json").read_text(encoding="utf-8"))["actors"]
    data["objectives"] = json.loads((base / "objectives.json").read_text(encoding="utf-8"))["objectives"]
    data["llm_context"] = json.loads((base / "llm_context.json").read_text(encoding="utf-8"))["llm_context"]
    data["exploration"] = {
        "party_start_zone": json.loads((base / "exploration/party_start_zone.json").read_text(encoding="utf-8"))["party_start_zone"],
        "zones": json.loads((base / "exploration/zones.json").read_text(encoding="utf-8"))["zones"],
        "points": json.loads((base / "exploration/points.json").read_text(encoding="utf-8"))["points"],
        "challenges": json.loads((base / "exploration/challenges.json").read_text(encoding="utf-8"))["challenges"],
        "encounter_triggers": json.loads((base / "exploration/encounter_triggers.json").read_text(encoding="utf-8"))["encounter_triggers"],
        "npc_transitions": json.loads((base / "exploration/npc_transitions.json").read_text(encoding="utf-8"))["npc_transitions"],
        "resources": json.loads((base / "exploration/resources.json").read_text(encoding="utf-8"))["resources"],
        "initial_resources": json.loads((base / "exploration/initial_resources.json").read_text(encoding="utf-8"))["initial_resources"],
    }
    attack = {
        "id": "test_attack",
        "name": "Test Attack",
        "source_type": "weapon",
        "range_feet": 5,
        "attack_modifier": 1,
        "damage": {"fixed": 1, "damage_type": "bludgeoning"},
    }
    for actor in data["actors"]:
        actor.pop("item_refs", None)
        actor.pop("spell_preparation", None)
        actor["attacks"] = [attack]
    return data


def _village_square_data_without_refs():
    path = Path("content/scenarios/village_square_mvp.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    attack = {
        "id": "test_attack",
        "name": "Test Attack",
        "source_type": "weapon",
        "range_feet": 5,
        "attack_modifier": 1,
        "damage": {"fixed": 1, "damage_type": "bludgeoning"},
    }
    for actor in data["actors"]:
        actor.pop("item_refs", None)
        actor["attacks"] = [attack]
    data["exploration"].pop("merchants", None)
    data["exploration"]["points"] = [
        point
        for point in data["exploration"]["points"]
        if point.get("merchant_id") is None
    ]
    return data


def test_load_scenario_builds_actors_and_attack_sources():
    loaded = load_scenario("content/scenarios/goblin_ambush.json")
    encounter = build_encounter_from_scenario(loaded)

    assert encounter.scenario_id == "goblin_ambush"
    assert encounter.scenario_name == "Zasadzka goblina"
    assert encounter.board.dimensions.cols == 20
    assert encounter.board.dimensions.rows == 30

    hero = next(actor for actor in encounter.actors if actor.id == "hero")
    goblin = next(actor for actor in encounter.actors if actor.id == "goblin")
    assert hero.name == "Bohater"
    assert hero.faction == Faction.ALLY
    assert hero.size == CreatureSize.MEDIUM
    assert hero.ac == 14
    assert hero.hp == 20
    assert hero.position == Coordinate(0, 0)
    assert hero.ability_scores.strength == 16
    assert goblin.name == "Goblin"
    assert goblin.faction == Faction.ENEMY
    assert goblin.size == CreatureSize.SMALL
    assert goblin.position == Coordinate(1, 0)
    assert goblin.damage_affinities.resistances == ()

    hero_source = encounter.attack_sources_by_actor[hero.id]
    assert hero_source.name == "Miecz"
    assert hero_source.source_type == AttackSourceType.WEAPON
    assert [(item.label, item.value) for item in hero_source.attack_roll_request.modifiers] == [
        ("Siła", 3),
        ("Biegłość", 2),
    ]
    assert hero_source.damage_die_sides == 8
    assert next(item for item in hero.inventory if item.id == "longsword").versatile_damage_dice == "1d10"
    assert hero_source.damage_type == DamageType.SLASHING.value

    goblin_source = encounter.attack_sources_by_actor[goblin.id]
    assert goblin_source.name == "Szabla"
    assert [(item.label, item.value) for item in goblin_source.attack_roll_request.modifiers] == [
        ("Zręczność", 2),
        ("Biegłość", 2),
    ]
    assert goblin_source.damage_die_sides == 6
    assert goblin_source.damage_modifier == 2


def test_load_scenario_normalizes_multicomponent_ndm_damage(tmp_path) -> None:
    data = _village_square_data_without_refs()
    data["actors"][0]["attacks"][0]["damage"] = {
        "components": [
            {
                "id": "blade",
                "label": "Ostrze",
                "dice": "2d6",
                "modifier": 3,
                "damage_type": "slashing",
            },
            {
                "id": "flame",
                "label": "Płomień",
                "dice": "1d4",
                "damage_type": "fire",
            },
        ]
    }
    scenario_path = tmp_path / "multi_damage.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    encounter = build_encounter_from_scenario(load_scenario(scenario_path))
    actor = encounter.actors[0]
    source = encounter.attack_sources_by_actor[actor.id]

    assert [component.id for component in source.damage_components] == [
        "blade",
        "flame",
    ]
    assert source.damage_components[0].dice is not None
    assert source.damage_components[0].dice.format() == "2d6"
    assert source.damage_hint == "Ostrze: 2d6 + 3 cięte + Płomień: 1d4 od ognia"


def test_gate_skirmish_loads_rest_and_recharge_limited_attack_sources() -> None:
    encounter = build_encounter_from_scenario(
        load_scenario("content/scenarios/gate_skirmish.json")
    )
    hero = next(actor for actor in encounter.actors if str(actor.id) == "hero")
    goblin = next(actor for actor in encounter.actors if str(actor.id) == "goblin_b")
    heroic_strike = next(
        source
        for source in encounter.attack_source_options_by_actor[hero.id]
        if source.id == "heroic_strike"
    )
    frenzied_lunge = next(
        source
        for source in encounter.attack_source_options_by_actor[goblin.id]
        if source.id == "goblin_frenzied_lunge"
    )

    assert heroic_strike.resource_pool_id == "heroic_strike_uses"
    assert hero.portrait == "portraits/abandoned_watchtower/hero.webp"
    assert goblin.portrait == "portraits/abandoned_watchtower/goblin-rubble.webp"
    assert hero.features[0].feature_id == "heroic_strike"
    assert hero.features[0].action_ids == ("heroic_strike",)
    assert hero.resource_pools[0].recovery.value == "short_rest"
    assert frenzied_lunge.resource_pool_id == "frenzied_lunge_charge"
    assert goblin.resource_pools[0].recharge is not None
    assert goblin.resource_pools[0].recharge.minimum_roll == 5
    assert goblin.features[0].feature_id == "goblin_frenzied_lunge"
    assert goblin.features[0].source_ref == "goblin"


def test_actor_rejects_duplicate_feature_references(tmp_path) -> None:
    data = json.loads(Path("content/scenarios/gate_skirmish.json").read_text(encoding="utf-8"))
    data["actors"][0]["feature_refs"] = ["heroic_strike", "heroic_strike"]
    scenario_path = tmp_path / "duplicate_feature.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate features"):
        load_scenario(scenario_path)


def test_feature_grant_rejects_component_id_collision_with_actor(tmp_path) -> None:
    data = json.loads(Path("content/scenarios/gate_skirmish.json").read_text(encoding="utf-8"))
    data["actors"][0]["resource_pools"] = [
        {
            "id": "heroic_strike_uses",
            "label": "Kolizja",
            "maximum": 1,
            "recovery": "never",
        }
    ]
    scenario_path = tmp_path / "feature_collision.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="resource_pools ids must be unique"):
        load_scenario(scenario_path)


def test_load_scenario_parses_actor_damage_affinities(tmp_path):
    data = json.loads(Path("content/scenarios/goblin_ambush.json").read_text(encoding="utf-8"))
    actor = data["actors"][1]
    actor["damage_resistances"] = ["fire", "cold"]
    actor["damage_immunities"] = ["poison"]
    actor["damage_vulnerabilities"] = ["radiant"]
    scenario_path = tmp_path / "damage_affinities.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    encounter = build_encounter_from_scenario(load_scenario(scenario_path))
    loaded_actor = next(item for item in encounter.actors if str(item.id) == actor["id"])

    assert loaded_actor.damage_affinities.resistances == (DamageType.FIRE, DamageType.COLD)
    assert loaded_actor.damage_affinities.immunities == (DamageType.POISON,)
    assert loaded_actor.damage_affinities.vulnerabilities == (DamageType.RADIANT,)


def test_reference_monster_exposes_damage_affinity_fixture(tmp_path):
    data = json.loads(Path("content/scenarios/goblin_ambush.json").read_text(encoding="utf-8"))
    monster = data["actors"][1]
    monster["id"] = "stone_guardian"
    monster["source_ref"] = "stone_guardian"
    scenario_path = tmp_path / "stone_guardian_encounter.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    encounter = build_encounter_from_scenario(load_scenario(scenario_path))
    guardian = next(actor for actor in encounter.actors if str(actor.id) == "stone_guardian")

    assert guardian.damage_affinities.resistances == (DamageType.SLASHING, DamageType.PIERCING)
    assert guardian.damage_affinities.immunities == (DamageType.POISON,)
    assert guardian.damage_affinities.vulnerabilities == (DamageType.THUNDER,)
    assert guardian.condition_immunities == ("poisoned",)
    source = encounter.attack_sources_by_actor[guardian.id]
    assert source.save_ability == "dexterity"
    assert source.save_dc == 12
    assert source.save_damage_on_success == "half"
    assert [item.id for item in encounter.multiattack_sources_by_actor[guardian.id]] == [
        "stone_slam",
        "stone_slam",
    ]


def test_load_scenario_rejects_unknown_damage_affinity(tmp_path):
    data = json.loads(Path("content/scenarios/goblin_ambush.json").read_text(encoding="utf-8"))
    data["actors"][1]["damage_resistances"] = ["sunlight"]
    scenario_path = tmp_path / "bad_damage_affinity.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="damage_resistances"):
        load_scenario(scenario_path)


def test_poison_vial_exposes_data_driven_poisoned_condition(tmp_path):
    data = json.loads(Path("content/scenarios/gate_skirmish.json").read_text(encoding="utf-8"))
    data["actors"][0]["item_refs"].append("poison_vial")
    scenario_path = tmp_path / "poison_condition.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    encounter = build_encounter_from_scenario(load_scenario(scenario_path))
    hero = next(actor for actor in encounter.actors if str(actor.id) == data["actors"][0]["id"])
    action = next(
        item
        for item in encounter.combat_actions_by_actor[hero.id]
        if item.id == "splash_poison_vial"
    )

    assert action.condition == CombatCondition.POISONED
    assert action.save_ability == "constitution"
    assert action.save_dc == 12
    assert action.save_timing == "turn_end"


def test_load_scenario_rejects_unknown_save_policy(tmp_path):
    data = _abandoned_watchtower_data_without_refs()
    data["actors"][1]["attacks"][0]["save_ability"] = "dexterity"
    data["actors"][1]["attacks"][0]["save_damage_on_success"] = "quarter"
    scenario_path = tmp_path / "bad_save_policy.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="save_damage_on_success"):
        load_scenario(scenario_path)


def test_load_multi_actor_scenario_builds_separate_actors_and_sources():
    encounter = build_encounter_from_scenario(load_scenario("content/scenarios/multi_actor_skirmish.json"))

    assert encounter.scenario_id == "multi_actor_skirmish"
    assert len(encounter.actors) == 5
    ids = {str(actor.id) for actor in encounter.actors}
    assert ids == {"hero", "rogue", "goblin_a", "goblin_b", "goblin_c"}
    assert set(str(actor_id) for actor_id in encounter.attack_sources_by_actor) == ids

    goblin_a = next(actor for actor in encounter.actors if actor.id == "goblin_a")
    goblin_b = next(actor for actor in encounter.actors if actor.id == "goblin_b")
    rogue = next(actor for actor in encounter.actors if actor.id == "rogue")
    assert goblin_a.name == "Goblin A"
    assert goblin_b.name == "Goblin B"
    assert goblin_a.position == Coordinate(1, 0)
    assert goblin_b.position == Coordinate(1, 1)
    assert encounter.attack_sources_by_actor[rogue.id].name == "Kusza"
    assert encounter.attack_sources_by_actor[rogue.id].source_item_id == "crossbow"


def test_load_gate_skirmish_uses_shared_map_setup_and_ranged_rogue():
    encounter = build_encounter_from_scenario(load_scenario("content/scenarios/gate_skirmish.json"))

    enemies = [actor for actor in encounter.actors if actor.faction == Faction.ENEMY]
    rogue = next(actor for actor in encounter.actors if actor.id == "rogue")
    cleric = next(actor for actor in encounter.actors if actor.id == "cleric")
    rubble_guard = next(actor for actor in encounter.actors if actor.id == "goblin_b")

    assert len(enemies) == 2
    assert encounter.player_start_zones == ((Coordinate(7, 6), Coordinate(8, 6), Coordinate(9, 6)),)
    assert encounter.attack_sources_by_actor[rogue.id].name == "Kusza"
    assert encounter.attack_sources_by_actor[rogue.id].range_feet == 80
    assert encounter.attack_sources_by_actor[rogue.id].attack_kind == AttackKind.RANGED
    assert rogue.proficiency_bonus == 2
    assert rogue.skill_proficiencies == ("stealth", "sleight_of_hand", "perception")
    assert rogue.skill_expertise == ("stealth",)
    assert rogue.proficiencies.saving_throws == ("dexterity", "intelligence")
    assert rogue.proficiencies.weapons == ("crossbow", "dagger")
    assert rubble_guard.triggers[0].id == "rubble_guard_resolve"
    assert rubble_guard.triggers[0].event_type.value == "turn_start"
    assert rubble_guard.triggers[0].effect_kind.value == "grant_temp_hp"
    hero = next(actor for actor in encounter.actors if actor.id == "hero")
    assert {item.id for item in hero.inventory} >= {
        "longsword",
        "crossbow",
        "strength_potion",
        "sticky_flask",
    }
    longsword = next(item for item in hero.inventory if item.id == "longsword")
    dagger = next(item for item in hero.inventory if item.id == "dagger")
    crossbow = next(item for item in hero.inventory if item.id == "crossbow")
    assert longsword.equipped is True
    longsword_source = next(
        source
        for source in encounter.attack_source_options_by_actor[hero.id]
        if source.id == "longsword_slash"
    )
    assert longsword_source.attack_kind == AttackKind.MELEE
    assert longsword_source.reach_feet == 5
    assert longsword.held_in == (HandSlot.MAIN_HAND,)
    assert dagger.equipped is True
    assert dagger.held_in == (HandSlot.OFF_HAND,)
    assert crossbow.equipped is False
    assert crossbow.hands_required == 2
    assert {source.id for source in encounter.weapon_attack_sources_by_item_id["crossbow"]} == {"crossbow_shot"}
    assert "crossbow_shot" in {
        source.id for source in encounter.attack_source_options_by_actor[hero.id]
    }
    strength_potion = next(item for item in hero.inventory if item.id == "strength_potion")
    assert strength_potion.name == "Magiczny napój siły"
    strength_action = next(action for action in encounter.combat_actions_by_actor[hero.id] if action.id == "drink_strength_potion")
    assert strength_action.action_type == "strength_potion"
    assert strength_action.source_item_id == "strength_potion"
    assert strength_action.action_cost == ActionEconomyCost.ACTION
    sticky_action = next(
        action
        for action in encounter.combat_actions_by_actor[hero.id]
        if action.id == "splash_sticky_flask"
    )
    assert sticky_action.action_type == "targeted_item_effect"
    assert sticky_action.source_item_id == "sticky_flask"
    assert sticky_action.target_faction == "enemy"
    assert sticky_action.range_feet == 5
    assert sticky_action.effect_kind == "apply_condition"
    assert sticky_action.condition == CombatCondition.RESTRAINED
    assert sticky_action.save_ability == "dexterity"
    assert sticky_action.save_dc == 12
    assert sticky_action.save_timing == "turn_end"
    assert sticky_action.duration == "permanent"
    assert sticky_action.action_cost == ActionEconomyCost.ACTION
    assert cleric.auras[0].id == "protective_reliquary"
    assert cleric.auras[0].radius_feet == 10
    assert cleric.auras[0].effect_kind.value == "saving_throw_bonus"
    cleric_sources = {source.id: source for source in encounter.attack_source_options_by_actor[cleric.id]}
    assert cleric_sources["sacred_flame"].casting_kind == SpellCastingKind.CANTRIP
    assert cleric_sources["sacred_flame"].spell_level == 0
    assert cleric_sources["sacred_flame"].attack_kind == AttackKind.RANGED
    assert cleric_sources["sacred_flame"].reach_feet is None
    assert cleric_sources["radiant_line"].casting_kind == SpellCastingKind.LEVELED
    assert cleric_sources["radiant_line"].spell_level == 1
    assert cleric_sources["radiant_line"].area is not None
    assert cleric_sources["radiant_line"].area.target_mode.value == "all_creatures"
    healing_word = encounter.healing_sources_by_actor[cleric.id][0]
    assert healing_word.casting_kind == SpellCastingKind.LEVELED
    assert healing_word.action_cost == ActionEconomyCost.BONUS_ACTION
    assert {spell.id for spell in cleric.spells} == {
        "sacred_flame",
        "radiant_line",
        "healing_word",
        "bless_attack_bonus",
        "comprehend_languages",
        "shield",
        "counterspell",
        "warding_rite",
        "call_guardian_spirit",
        "veil_step",
        "repelling_pulse",
        "grasping_current",
        "weakening_miasma",
        "binding_frost",
        "unravel_magic",
    }
    assert cleric.spell_access[0].kind.value == "prepared"
    assert cleric.spell_access[0].allowed_focus_kinds == (
        "holy_symbol",
        "component_pouch",
    )
    assert next(spell for spell in cleric.spells if spell.id == "radiant_line").components.materials[0].item_id == "incense"
    ritual = next(
        spell for spell in cleric.spells if spell.id == "comprehend_languages"
    )
    assert ritual.ritual is True
    assert ritual.exploration_effect is not None
    assert ritual.exploration_effect.flag_key == "comprehend_languages_active"
    bless = next(action for action in encounter.combat_actions_by_actor[cleric.id] if action.id == "bless_attack_bonus")
    assert bless.action_type == "concentration_attack_bonus"
    assert bless.casting_kind == SpellCastingKind.LEVELED
    assert bless.spell_level == 1
    assert bless.concentration is True
    assert bless.target_faction == "ally"
    assert bless.target_count == 3
    assert bless.upcast_targets_per_level == 1
    assert bless.value == 1
    summon = next(
        action
        for action in encounter.combat_actions_by_actor[cleric.id]
        if action.id == "call_guardian_spirit"
    )
    assert summon.action_type == "summon"
    assert summon.concentration is True
    assert summon.range_feet == 30
    assert summon.summon is not None
    assert summon.summon.name == "Duch strażnik"
    assert summon.summon.attack_damage_type == DamageType.RADIANT
    teleport = next(
        action
        for action in encounter.combat_actions_by_actor[cleric.id]
        if action.id == "veil_step"
    )
    assert teleport.action_type == "spell_movement"
    assert teleport.action_cost == ActionEconomyCost.BONUS_ACTION
    assert teleport.movement is not None
    assert teleport.movement.kind.value == "teleport"
    push = next(
        action
        for action in encounter.combat_actions_by_actor[cleric.id]
        if action.id == "repelling_pulse"
    )
    assert push.movement is not None
    assert push.movement.kind.value == "push"
    assert push.movement.distance_feet == 10
    assert push.save_ability == "strength"
    debuff = next(
        action
        for action in encounter.combat_actions_by_actor[cleric.id]
        if action.id == "weakening_miasma"
    )
    assert debuff.action_type == "spell_debuff"
    assert debuff.effect_kind == "apply_condition"
    assert debuff.condition == CombatCondition.POISONED
    assert debuff.save_ability == "constitution"
    assert debuff.save_timing == "turn_end"
    dispel = next(
        action
        for action in encounter.combat_actions_by_actor[cleric.id]
        if action.id == "unravel_magic"
    )
    assert dispel.action_type == "spell_dispel"
    assert dispel.effect_kind == "dispel_magic"
    assert dispel.range_feet == 60
    assert dispel.target_faction == "any"
    shield = next(
        action
        for action in encounter.combat_actions_by_actor[cleric.id]
        if action.id == "shield"
    )
    assert shield.action_type == "reaction_ac_bonus"
    assert shield.action_cost == ActionEconomyCost.REACTION
    assert shield.casting_kind == SpellCastingKind.LEVELED
    assert shield.spell_level == 1
    assert shield.value == 5
    assert encounter.board.terrain_at(Coordinate(8, 5)).blocks_movement is True
    assert encounter.board.terrain_at(Coordinate(10, 7)).is_difficult is True


def test_gate_skirmish_blocks_fallen_gate_but_allows_cart_tile():
    encounter = build_encounter_from_scenario(load_scenario("content/scenarios/gate_skirmish.json"))
    hero = next(actor for actor in encounter.actors if actor.id == "hero")

    gate_path = find_path(encounter.board, hero, encounter.actors, Coordinate(8, 5))
    cart_path = find_path(encounter.board, hero, encounter.actors, Coordinate(8, 8))

    assert gate_path.valid is False
    assert cart_path.valid is True


def test_load_scenario_builds_environment_entries():
    encounter = build_encounter_from_scenario(load_scenario("content/scenarios/goblin_ambush.json"))

    assert len(encounter.environment) == 1
    entry = encounter.environment[0]
    assert entry.id == "broken_crate"
    assert entry.setup_type == EnvironmentSetupType.CONTAINER
    assert entry.visibility == SetupVisibility.VISIBLE
    assert entry.positions == (Coordinate(3, 1),)


def test_load_first_playable_scene_builds_setup_objective_and_scene_object():
    encounter = build_encounter_from_scenario(load_scenario("content/scenarios/first_playable_scene.json"))

    assert encounter.scenario_id == "first_playable_scene"
    assert len(encounter.actors) == 5
    assert encounter.player_start_zones == (
        (Coordinate(0, 0), Coordinate(1, 0), Coordinate(0, 1), Coordinate(1, 1)),
    )
    assert len(encounter.objectives) == 1
    assert encounter.objectives[0].id == "secure_crate"
    assert encounter.objectives[0].condition == SceneObjectiveCondition.FLAG_EQUALS
    assert encounter.objectives[0].flag_key == "crate_secured"
    assert encounter.objectives[0].flag_value is True
    assert len(encounter.scene_objects) == 1
    scene_object = encounter.scene_objects[0]
    assert scene_object.id == "ancient_crate"
    assert scene_object.interaction_label == "Zbadaj skrzynię"
    assert scene_object.blocks_movement is False
    assert scene_object.allow_interaction_when_occupied_by_enemy is True
    assert scene_object.cover_bonus == 2
    assert scene_object.interactions[0].id == "inspect_crate"
    assert scene_object.interactions[0].ability_check is not None
    assert scene_object.interactions[0].ability_check.dc == 12
    assert scene_object.interactions[0].success_flag == "crate_secured"
    assert encounter.board.terrain_at(Coordinate(3, 1)).blocks_movement is True
    assert encounter.board.terrain_at(Coordinate(2, 2)).is_difficult is True


def test_load_gate_skirmish_parses_combat_interaction_conditions_and_effects():
    encounter = build_encounter_from_scenario(load_scenario("content/scenarios/gate_skirmish.json"))
    cart = next(scene_object for scene_object in encounter.scene_objects if scene_object.id == "broken_cart")
    rubble = next(scene_object for scene_object in encounter.scene_objects if scene_object.id == "rubble_patch")

    take_cover = next(interaction for interaction in cart.interactions if interaction.id == "take_cover_cart")
    climb = next(interaction for interaction in cart.interactions if interaction.id == "climb_cart")
    throw_rubble = next(interaction for interaction in rubble.interactions if interaction.id == "throw_rubble")

    assert [condition.condition_type for condition in take_cover.conditions] == [
        "action_available",
        "actor_adjacent_to_object",
    ]
    assert take_cover.effects[0].effect_type == "grant_ac_bonus_until_move"
    assert ("value", 2) in take_cover.effects[0].parameters
    assert cart.projectile_cover_bonus == 2
    assert [effect.effect_type for effect in climb.effects] == [
        "move_actor_to_tile",
        "grant_attack_bonus_while_on_object",
    ]
    assert rubble.blocks_movement is False
    assert [condition.condition_type for condition in throw_rubble.conditions] == [
        "action_available",
        "actor_on_object",
        "adjacent_enemy_exists",
    ]
    assert throw_rubble.effects[0].effect_type == "grant_next_attack_penalty"
    assert ("value", -2) in throw_rubble.effects[0].parameters
    assert ("saving_throw_ability", "dexterity") in throw_rubble.effects[0].parameters
    assert ("saving_throw_dc", 12) in throw_rubble.effects[0].parameters


def test_load_abandoned_watchtower_builds_exploration_scene():
    loaded = load_scenario("content/scenarios/abandoned_watchtower.json")
    exploration = build_exploration_from_scenario(loaded)

    assert loaded.definition.content_header.schema == SCENARIO_SCHEMA
    assert loaded.definition.content_header.schema_version == 1
    assert loaded.definition.content_header.ruleset_id == RULESET_DND_5E_2014
    assert loaded.definition.content_header.source_pack_ids == ("project_original",)
    assert exploration.content_header == loaded.definition.content_header
    assert loaded.definition.scene_mode == SceneMode.EXPLORATION
    assert exploration.scenario_id == "abandoned_watchtower"
    assert exploration.party_position.zone_id == "gate"
    assert len(exploration.actors) == 3
    assert {actor.id for actor in exploration.actors} == {"hero", "rogue", "cleric"}
    assert len(exploration.environment) == 2
    assert exploration.board.terrain_at(Coordinate(8, 5)).blocks_movement is False
    assert len(exploration.zones) == 4
    assert len(exploration.challenges) == 2
    assert len(exploration.observations) == 6
    gate_observation = next(
        item for item in exploration.observations if item.id == "look_through_gate_gap"
    )
    assert gate_observation.id == "look_through_gate_gap"
    assert gate_observation.dc == 10
    assert [fact.minimum_total for fact in gate_observation.facts] == [10, 15, 20]
    assert gate_observation.facts[1].reveal_flag == "gate_goblins_spotted"
    initiative_edge = gate_observation.facts[2].encounter_edge
    assert initiative_edge is not None
    assert initiative_edge.encounter_trigger_id == "gate_open_skirmish"
    challenge = next(item for item in exploration.challenges if item.id == "closed_gate")
    assert challenge.completed_flag == "gate_passed"
    assert challenge.reveals_on_complete == ()
    vault = next(option for option in challenge.options if option.id == "vault_gate")
    assert len(vault.hazards) == 1
    assert vault.hazards[0].id == "fall_from_gate"
    assert vault.hazards[0].saving_throw.ability == "dexterity"
    assert vault.hazards[0].saving_throw.dc == 12
    assert vault.hazards[0].damage.damage_type == "bludgeoning"
    assert vault.hazards[0].failure_effects == (
        {"type": "apply_condition", "parameters": {"condition": "prone"}},
    )
    assert exploration.traps[0].id == "gate_alarm_wire"
    assert exploration.traps[0].detection_observation_id == "search_gate_traps"
    assert exploration.traps[0].activation_forbidden_flags == (
        "gate_critical_breach",
    )
    assert exploration.traps[0].hazard.failure_effects[0]["type"] == "add_noise"
    gate_trigger = next(item for item in exploration.encounter_triggers if item.id == "gate_open_skirmish")
    assert gate_trigger.outcome_on_victory is not None
    assert any(
        effect["type"] == "reveal_point" and effect["parameters"]["point_id"] == "wounded_scout"
        for effect in gate_trigger.outcome_on_victory.effects
    )
    assert gate_trigger.outcome_on_retreat is not None
    assert gate_trigger.outcome_on_retreat.effects[0]["parameters"]["key"] == (
        "party_retreated_at_gate"
    )
    assert gate_trigger.outcome_on_surrender is not None
    assert gate_trigger.outcome_on_surrender.effects[0]["parameters"]["key"] == (
        "party_surrendered_at_gate"
    )
    assert challenge.llm_policy.allowed_local_skills == ("crafting", "lockpicking")
    assert "heavy_force" in challenge.llm_policy.allowed_approach_tags
    assert "bribe" not in challenge.llm_policy.allowed_approach_tags
    assert challenge.llm_policy.dc_min == 8
    assert challenge.llm_policy.dc_max == 18
    assert challenge.llm_policy.max_resources_per_attempt == 1
    assert "Opuszczona" in exploration.llm_context.summary
    assert "brak działającego mechanizmu lotu" in exploration.llm_context.forbidden_assumptions
    gate = next(zone for zone in exploration.zones if zone.id == "gate")
    assert gate.image == "assets/gate_preview.png"
    assert "lina nie pozwala latać" in gate.llm_context.forbidden_assumptions
    assert {item.id for item in gate.item_instances} == {"gate_rotten_planks", "gate_loose_stones"}
    rotten_planks = next(item for item in gate.item_instances if item.id == "gate_rotten_planks")
    assert rotten_planks.definition_id == "wooden_plank"
    assert rotten_planks.quantity == 4
    assert rotten_planks.properties >= {"long", "wooden", "fragile"}
    assert {fixture.id for fixture in gate.fixtures} == {
        "watchtower_gate",
        "gate_corroded_hinges",
        "gate_thorny_brush",
    }
    hinges = next(fixture for fixture in gate.fixtures if fixture.id == "gate_corroded_hinges")
    assert hinges.detachable is True
    assert hinges.yield_items[0].definition_id == "scrap_metal"
    assert hinges.yield_items[0].available is False
    guidance = {fact.id: fact for fact in challenge.llm_context.guidance_facts}
    assert guidance["gate.force_possible"].minimum_hint_level == 1
    assert guidance["gate.force_is_loud"].minimum_hint_level == 1
    assert guidance["gate.noise_affects_scout"].visibility.value == "hidden"
    assert guidance["gate.no_rope_flight"].kind.value == "constraint"
    assert {resource.id for resource in exploration.resources} == {
        "rope",
        "wedge",
        "saw",
        "scout_reports",
    }
    assert next(resource for resource in exploration.resources if resource.id == "wedge").consume_on_use is True
    assert next(resource for resource in exploration.resources if resource.id == "rope").consume_on_use is False
    assert set(next(resource for resource in exploration.resources if resource.id == "rope").properties) >= {
        "long",
        "binding",
        "load_bearing",
    }
    assert exploration.initial_resource_ids == ("rope", "wedge")
    assert {purpose.id for purpose in exploration.crafting_policy.purposes} == {
        "heavy_force",
        "climbing_aid",
        "leverage",
        "precision_tool",
    }
    courtyard = next(zone for zone in exploration.zones if zone.id == "courtyard")
    assert courtyard.search_dc == 12
    assert courtyard.search_reveals == ("hidden_cache",)
    courtyard_challenge = next(item for item in exploration.challenges if item.id == "courtyard_search")
    assert courtyard_challenge.zone_id == "courtyard"
    assert courtyard_challenge.completed_flag == "courtyard_searched"
    assert courtyard_challenge.reveals_on_complete == ()
    assert "listening" in courtyard_challenge.llm_policy.allowed_approach_tags
    assert "heavy_force" not in courtyard_challenge.llm_policy.allowed_approach_tags
    wounded_scout = next(point for point in exploration.points if point.id == "wounded_scout")
    assert wounded_scout.zone_id == "courtyard"
    assert wounded_scout.visibility == SetupVisibility.HIDDEN
    assert wounded_scout.npc_interaction is not None
    assert wounded_scout.npc_interaction.name == "Ranny zwiadowca"
    assert wounded_scout.npc_interaction.id == "wounded_scout"
    transition = next(item for item in exploration.npc_transitions if item.id == "scout_knife_escalation")
    assert transition.npc_id == "wounded_scout"
    assert [variant.id for variant in transition.variants] == [
        "gate_secured",
        "courtyard_secured",
        "danger_nearby",
    ]
    theft = next(
        permission
        for permission in wounded_scout.npc_interaction.policy.intent_permissions
        if permission.intent == "theft"
    )
    reports = theft.target("scout_reports")
    assert reports is not None
    assert reports.branch(NpcOutcomeTier.CRITICAL_FAILURE).transition_id == "scout_knife_escalation"
    assert wounded_scout.npc_interaction.initial_attitude.value == "indifferent"
    assert "przygnieciony" in wounded_scout.npc_interaction.initial_physical_state
    assert "scout_stabilized" in wounded_scout.npc_interaction.policy.allowed_flags
    policy = wounded_scout.npc_interaction.policy
    assert policy.intent_permission("medical") is not None
    assert policy.intent_permission("medical").state_on_success is not None
    assert "ustabilizowany" in policy.intent_permission("medical").state_on_success.physical_state
    assert policy.intent_permission("information") is not None
    assert policy.intent_permission("information").status == "locked"
    assert policy.intent_permission("social").uses_social_reaction is True
    assert policy.intent_permission("social").attempt_policy is not None
    assert policy.intent_permission("social").attempt_policy.max_attempts == 2
    assert policy.intent_permission("social").attempt_policy.retry_requires_any_flags == (
        "scout_treated",
        "scout_stabilized",
    )
    assert policy.intent_permission("intimidation").attempt_policy.max_attempts == 1
    theft_target = policy.intent_permission("theft").target("scout_reports")
    assert theft_target is not None
    assert theft_target.ability == "dexterity"
    assert theft_target.skill == "sleight_of_hand"
    assert theft_target.dc == 14
    assert len(theft_target.outcome_branches) == 4
    assert policy.intent_permission("intimidation").target("scout_information") is not None
    assert policy.intent_permission("trade").status == "blocked"
    assert "sleight_of_hand" in policy.allowed_skills
    assert {info.id for info in wounded_scout.npc_interaction.locked_information} == {
        "tower_hint",
        "beast_hint",
        "commander_curse_hint",
        "hidden_cache_hint",
    }
    tower_hint = next(info for info in wounded_scout.npc_interaction.locked_information if info.id == "tower_hint")
    assert tower_hint.effects_on_reveal == (
        {"type": "set_flag", "parameters": {"key": "tower_hint_learned", "value": True}},
    )


def test_load_abandoned_watchtower_folder_manifest_matches_alias_file():
    from_alias = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower.json"))
    from_folder = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower"))

    assert from_alias.scenario_id == from_folder.scenario_id == "abandoned_watchtower"
    assert [zone.id for zone in from_alias.zones] == [zone.id for zone in from_folder.zones]
    assert [challenge.id for challenge in from_alias.challenges] == [challenge.id for challenge in from_folder.challenges]
    assert [point.id for point in from_alias.points] == [point.id for point in from_folder.points]
    assert from_folder.initial_resource_ids == ("rope", "wedge")


def test_load_abandoned_watchtower_folder_keeps_monster_and_item_refs_working():
    loaded = load_scenario("content/scenarios/abandoned_watchtower")
    exploration = build_exploration_from_scenario(loaded)
    encounter = build_encounter_from_scenario(loaded)

    hero = next(actor for actor in exploration.actors if actor.id == "hero")
    assert hero.name == "Bohater"
    assert {item.id for item in hero.inventory} >= {"longsword", "strength_potion"}
    assert loaded.path == Path("content/scenarios/abandoned_watchtower/scenario.json")
    rogue = next(actor for actor in exploration.actors if actor.id == "rogue")
    cleric = next(actor for actor in exploration.actors if actor.id == "cleric")
    assert {item.id for item in rogue.inventory} >= {"crossbow", "thieves_tools"}
    assert set(next(item for item in rogue.inventory if item.id == "thieves_tools").properties) >= {
        "metallic",
        "prying",
    }
    assert "sacred_flame" in cleric.spell_ids
    shield = next(item for item in cleric.inventory if item.id == "shield")
    assert shield.equipped is True
    assert shield.armor_class_bonus == 2
    assert shield.armor_proficiency == "shield"
    assert effective_armor_class(cleric) == cleric.ac + 2
    healers_kit = next(item for item in cleric.inventory if item.id == "healers_kit")
    assert healers_kit.quantity == 1
    assert healers_kit.charges_current == 10
    wand = next(item for item in cleric.inventory if item.id == "binding_wand")
    assert wand.charges_current == 7
    assert wand.charges_maximum == 7
    assert wand.charges_recovery.value == "long_rest"
    assert wand.charges_recovery_dice == "1d6"
    assert wand.requires_attunement is True
    assert wand.attuned is False
    wand_action = next(
        action
        for action in encounter.combat_actions_by_actor[cleric.id]
        if action.id == "binding_wand_restraint"
    )
    assert wand_action.charge_cost == 1
    assert cleric.spell_preparation is not None
    assert cleric.spell_preparation.source_label == "lista czarów kapłana"
    assert cleric.spell_preparation.preparation_limit == 2
    assert cleric.spell_preparation.prepared_spell_ids == ("healing_word", "bless_attack_bonus")
    assert cleric.hit_dice[0].die_sides == 8
    assert cleric.hit_dice[0].remaining == 2
    assert {spell.id for spell in cleric.spell_preparation.available_spells} == {
        "radiant_line",
        "healing_word",
        "bless_attack_bonus",
    }
    gate = next(zone for zone in exploration.zones if zone.id == "gate")
    assert gate.short_rest_policy is not None
    assert gate.short_rest_policy.safety.value == "contested"
    assert gate.short_rest_policy.duration_minutes == 60
    assert gate.short_rest_policy.completion_effects[0]["type"] == "add_noise"
    gate = next(challenge for challenge in exploration.challenges if challenge.id == "closed_gate")
    lockpick = next(option for option in gate.options if option.id == "lockpick_gate")
    flame = next(option for option in gate.options if option.id == "reveal_bolt_with_flame")
    assert lockpick.requires_item_ids == ("thieves_tools",)
    assert lockpick.ability_check.skill is None
    assert lockpick.ability_check.tool == "thieves_tools"
    assert lockpick.bonuses[0].source_id == "thieves_tools"
    assert lockpick.bonuses[0].modifier == 0
    assert lockpick.bonuses[0].breakage_risk is not None
    assert lockpick.bonuses[0].breakage_risk.chance_percent == 25
    assert flame.requires_spell_ids == ("sacred_flame",)
    assert flame.bonuses[0].source_id == "sacred_flame"
    assert flame.bonuses[0].spell_level == 0
    assert flame.bonuses[0].modifier == 1


def test_exploration_challenge_reveal_rejects_unknown_point(tmp_path):
    data = _abandoned_watchtower_data_without_refs()
    data["exploration"]["challenges"][0]["reveals_on_complete"] = ["missing_point"]
    scenario_path = tmp_path / "bad_reveal_point.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="reveals_on_complete"):
        load_scenario(scenario_path)


def test_exploration_challenge_reveal_rejects_point_from_other_zone(tmp_path):
    data = _abandoned_watchtower_data_without_refs()
    data["exploration"]["zones"].append(
        {
            "id": "remote_cellar",
            "name": "Odległa piwnica",
            "positions": [[19, 20]],
            "available_if_flag": "cellar_found",
        }
    )
    data["exploration"]["points"].append(
        {
            "id": "remote_secret",
            "name": "Odległy sekret",
            "zone_id": "remote_cellar",
            "positions": [[19, 20]],
            "visibility": "hidden",
        }
    )
    data["exploration"]["challenges"][0]["reveals_on_complete"] = ["remote_secret"]
    scenario_path = tmp_path / "bad_reveal_zone.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="outside challenge zone"):
        load_scenario(scenario_path)


def test_exploration_challenge_llm_policy_rejects_bad_range(tmp_path):
    data = _abandoned_watchtower_data_without_refs()
    data["exploration"]["challenges"][0]["llm_policy"]["dc_range"] = [18, 8]
    scenario_path = tmp_path / "bad_policy_range.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="dc_range"):
        load_scenario(scenario_path)


def test_exploration_challenge_llm_policy_rejects_unknown_consequence_type(tmp_path):
    data = _abandoned_watchtower_data_without_refs()
    data["exploration"]["challenges"][0]["llm_policy"]["allowed_consequence_types"] = ["add_noise", "summon_dragon"]
    scenario_path = tmp_path / "bad_policy_consequence.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="allowed_consequence_types"):
        load_scenario(scenario_path)


def test_exploration_zone_rejects_unknown_structured_item_property(tmp_path):
    data = _abandoned_watchtower_data_without_refs()
    gate = next(zone for zone in data["exploration"]["zones"] if zone["id"] == "gate")
    gate["available_items"][0]["added_properties"] = ["fragile", "magical_unobtainium"]
    scenario_path = tmp_path / "bad_scene_item_property.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown item properties: magical_unobtainium"):
        load_scenario(scenario_path)


def test_load_abandoned_watchtower_builds_exploration_encounter_triggers():
    exploration = build_exploration_from_scenario(load_scenario("content/scenarios/abandoned_watchtower.json"))

    triggers = {trigger.id: trigger for trigger in exploration.encounter_triggers}

    gate = triggers["gate_open_skirmish"]
    assert gate.condition.value == "flag_equals"
    assert gate.opening_policy is not None
    assert gate.opening_policy.challenge_id == "closed_gate"
    assert [rule.id for rule in gate.opening_policy.rules] == [
        "ambush_prepared_by_failure",
        "ambush_prepared_by_alert",
        "hidden_wall_entry",
        "critical_breach",
        "critical_lock_and_bolt_entry",
    ]
    assert gate.opening_policy.rules[1].min_noise == 3
    assert gate.opening_policy.rules[1].outcome.value == "enemies_surprise_party"
    assert "gate_noise_alarm" not in triggers
    assert triggers["scout_panic_alarm"].condition.value == "flag_equals"
    assert triggers["scout_panic_alarm"].flag_key == "scout_panicked"


def test_load_village_square_mvp_builds_exploration_locations_setup_points_and_objective():
    loaded = load_scenario("content/scenarios/village_square_mvp.json")
    exploration = build_exploration_from_scenario(loaded)

    assert loaded.definition.scene_mode == SceneMode.EXPLORATION
    assert exploration.scenario_id == "village_square_mvp"
    assert exploration.party_position.zone_id == "market"
    assert {zone.id for zone in exploration.zones} == {"market", "tavern", "elder_house", "forest_road"}
    assert len(exploration.objectives) == 1
    assert exploration.objectives[0].condition == SceneObjectiveCondition.FLAG_EQUALS
    assert exploration.objectives[0].flag_key == "quest_hook_found"

    market = next(zone for zone in exploration.zones if zone.id == "market")
    assert market.marker_position == Coordinate(8, 4)
    assert {option.id for option in market.options} >= {"talk_to_elder", "read_notice_board", "ask_for_rumors"}
    assert next(option for option in market.options if option.id == "talk_to_elder").success_flag == "quest_hook_found"

    visible_setup_points = {point.id for point in exploration.points if point.visibility == SetupVisibility.VISIBLE and point.requires_setup}
    assert visible_setup_points == {
        "merchant_stall",
        "elder_npc",
        "notice_board",
        "tavern_keeper",
    }
    hidden_point = next(point for point in exploration.points if point.id == "lost_pouch")
    assert hidden_point.visibility == SetupVisibility.HIDDEN
    assert hidden_point.requires_setup is False
    elder = next(point for point in exploration.points if point.id == "elder_npc")
    assert elder.npc_interaction is not None
    assert elder.npc_interaction.id == "elder_bren"
    merchant_point = next(
        point for point in exploration.points if point.id == "merchant_stall"
    )
    assert merchant_point.merchant_id == "mira_market_stall"
    merchant = exploration.merchants[0]
    assert merchant.name == "Mira, kupczyni z rynku"
    assert merchant.currency.gp == 100
    assert {
        item.id: item.quantity for item in merchant.inventory
    } == {
        "crossbow_bolt": 40,
        "healers_kit": 1,
        "strength_potion": 1,
        "dagger": 2,
        "leather_armor": 2,
        "chain_shirt": 1,
        "chain_mail": 1,
        "backpack": 2,
        "candle": 20,
        "torch": 20,
        "oil_flask": 10,
        "hempen_rope": 3,
        "rations": 20,
        "ink": 2,
        "ink_pen": 4,
        "paper": 20,
        "explorers_pack": 1,
    }
    chain_mail = next(item for item in merchant.inventory if item.id == "chain_mail")
    assert chain_mail.armor_category.value == "heavy"
    assert chain_mail.armor_base_ac == 16
    assert chain_mail.armor_dexterity_cap == 0
    assert chain_mail.armor_strength_requirement == 13
    assert chain_mail.stealth_disadvantage is True
    demand = elder.npc_interaction.policy.intent_permission("social").target(
        "demand_advance_payment"
    )
    assert demand is not None
    assert demand.branch(NpcOutcomeTier.CRITICAL_FAILURE).transition_id == "elder_negotiation_breakdown"
    transition = next(item for item in exploration.npc_transitions if item.id == "elder_negotiation_breakdown")
    assert [variant.id for variant in transition.variants] == ["notice_read", "default"]
    assert all(
        reaction.encounter_trigger_id is None
        for variant in transition.variants
        for reaction in variant.reactions
    )


def test_loader_rejects_npc_branch_effect_with_precise_content_path(tmp_path):
    data = _village_square_data_without_refs()
    elder = next(point for point in data["exploration"]["points"] if point["id"] == "elder_npc")
    elder["npc_interaction"]["policy"]["intent_permissions"]["social"]["targets"][0]["outcomes"]["success"]["effects"] = [
        {"type": "grant_resource", "parameters": {"resource_id": "missing_reports"}}
    ]
    scenario_path = tmp_path / "bad_npc_branch_effect.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"NPC elder_bren\.intent_permissions\.social\.targets\.demand_advance_payment\.outcomes\.success\.effects\[0\].*missing_reports",
    ):
        load_scenario(scenario_path)


def test_loader_rejects_npc_transition_effect_outside_local_flag_policy(tmp_path):
    data = _village_square_data_without_refs()
    reaction = data["exploration"]["npc_transitions"][0]["variants"][-1]["reactions"][0]
    reaction["effects"] = [
        {"type": "set_flag", "parameters": {"key": "undeclared_transition_flag", "value": True}}
    ]
    scenario_path = tmp_path / "bad_npc_transition_effect.json"
    scenario_path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"NPC transition elder_negotiation_breakdown\.variants\.default\.reactions\.apologize\.effects\[0\].*undeclared_transition_flag",
    ):
        load_scenario(scenario_path)


def test_exploration_point_requires_setup_can_be_disabled(tmp_path):
    scenario_path = tmp_path / "exploration_points.json"
    scenario_path.write_text(
        json.dumps(
            {
                "id": "exploration_points",
                "name": "Exploration Points",
                "scene_mode": "exploration",
                "board": {"cols": 20, "rows": 30},
                "actors": [
                    {
                        "id": "hero",
                        "name": "Hero",
                        "kind": "player_character",
                        "faction": "ally",
                        "ac": 10,
                        "hp": 10,
                        "speed_feet": 30,
                        "position": [0, 0],
                        "ability_scores": {},
                        "attacks": [
                            {
                                "id": "hit",
                                "name": "Hit",
                                "source_type": "weapon",
                                "range_feet": 5,
                                "attack_modifier": 1,
                                "damage": {"dice": "1d4", "damage_type": "slashing"},
                            }
                        ],
                    }
                ],
                "exploration": {
                    "party_start_zone": "square",
                    "zones": [
                        {
                            "id": "square",
                            "name": "Square",
                            "positions": [[0, 0], [1, 0]],
                            "anchor_position": [0, 0],
                        }
                    ],
                    "points": [
                        {
                            "id": "notice",
                            "name": "Notice Board",
                            "zone_id": "square",
                            "positions": [[1, 0]],
                            "requires_setup": False,
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    exploration = build_exploration_from_scenario(load_scenario(scenario_path))

    assert exploration.points[0].requires_setup is False


def test_missing_required_field_reports_field_name(tmp_path):
    scenario_path = tmp_path / "broken.json"
    scenario_path.write_text(json.dumps({"id": "broken", "board": {"cols": 20, "rows": 30}}), encoding="utf-8")

    with pytest.raises(ValueError, match="scenario.actors"):
        load_scenario(scenario_path)


def test_unknown_enum_value_reports_field_name(tmp_path):
    root = tmp_path
    (root / "scenarios").mkdir()
    scenario_path = root / "scenarios" / "bad.json"
    scenario_path.write_text(
        json.dumps(
            {
                "id": "bad",
                "name": "Bad",
                "board": {"cols": 20, "rows": 30},
                "actors": [
                    {
                        "id": "hero",
                        "name": "Hero",
                        "kind": "player_character",
                        "faction": "unknown",
                        "ac": 10,
                        "hp": 10,
                        "speed_feet": 30,
                        "position": [0, 0],
                        "ability_scores": {},
                        "attacks": [
                            {
                                "id": "hit",
                                "name": "Hit",
                                "source_type": "weapon",
                                "range_feet": 5,
                                "attack_modifier": 1,
                                "damage": {"dice": "1d4", "damage_type": "slashing"},
                            }
                        ],
                    },
                    {
                        "id": "enemy",
                        "name": "Enemy",
                        "kind": "monster",
                        "faction": "enemy",
                        "ac": 10,
                        "hp": 10,
                        "speed_feet": 30,
                        "position": [1, 0],
                        "ability_scores": {},
                        "attacks": [
                            {
                                "id": "hit",
                                "name": "Hit",
                                "source_type": "weapon",
                                "range_feet": 5,
                                "attack_modifier": 1,
                                "damage": {"dice": "1d4", "damage_type": "slashing"},
                            }
                        ],
                    },
                ],
                "environment": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="actor hero.faction"):
        load_scenario(scenario_path)


def test_scenario_requires_ally_and_enemy(tmp_path):
    scenario_path = tmp_path / "only_ally.json"
    scenario_path.write_text(
        json.dumps(
            {
                "id": "only_ally",
                "name": "Only Ally",
                "board": {"cols": 20, "rows": 30},
                "actors": [
                    {
                        "id": "hero",
                        "name": "Hero",
                        "kind": "player_character",
                        "faction": "ally",
                        "ac": 10,
                        "hp": 10,
                        "speed_feet": 30,
                        "position": [0, 0],
                        "ability_scores": {},
                        "attacks": [
                            {
                                "id": "hit",
                                "name": "Hit",
                                "source_type": "weapon",
                                "range_feet": 5,
                                "attack_modifier": 1,
                                "damage": {"dice": "1d4", "damage_type": "slashing"},
                            }
                        ],
                    }
                ],
                "environment": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="at least one enemy"):
        load_scenario(scenario_path)
