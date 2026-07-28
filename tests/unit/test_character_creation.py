from dataclasses import replace

import pytest

from dnd_board_game.actors import AbilityScores
from dnd_board_game.character_creation import (
    CharacterDraft,
    LevelUpChoices,
    build_character,
    character_record_payload,
    created_character_from_payload,
    load_character_catalog,
    load_character_resources,
    level_up_character,
    validate_character_draft,
)
from dnd_board_game.inventory import effective_armor_class
from dnd_board_game.combat import (
    CombatCondition,
    DamageType,
    actor_spell_cast_validation,
    consume_spell_resource,
)
from dnd_board_game.combat import breath_weapon_attack_source
from dnd_board_game.rules import complete_long_rest
from dnd_board_game.scenarios import (
    build_encounter_from_scenario,
    compile_actor_combat_content,
    encounter_with_custom_party,
    load_scenario,
)


CATALOG_PATH = "content/character_creation/catalog.json"


@pytest.fixture
def catalog():
    return load_character_catalog(CATALOG_PATH)


@pytest.fixture
def resources(catalog):
    return load_character_resources(catalog, "content")


def fighter_draft() -> CharacterDraft:
    return CharacterDraft(
        id="aldren",
        name="Aldren",
        species_id="human",
        class_id="fighter",
        background_id="soldier",
        base_ability_scores=AbilityScores(15, 14, 13, 12, 10, 8),
        selected_skill_ids=("perception", "survival"),
        selected_fighting_style_id="defense",
        equipment_package_id="fighter_sword_and_board",
        portrait="portraits/custom/aldren.webp",
        selected_species_language_ids=("elvish",),
        selected_background_tool_ids=("dice_set",),
    )


def tiefling_fighter_draft(*, level: int) -> CharacterDraft:
    return CharacterDraft(
        id=f"tiefling_fighter_{level}",
        name="Ash",
        species_id="tiefling",
        class_id="fighter",
        background_id="soldier",
        level=level,
        base_ability_scores=AbilityScores(15, 14, 13, 12, 10, 8),
        selected_skill_ids=("perception", "survival"),
        selected_fighting_style_id="defense",
        selected_subclass_id="champion" if level >= 3 else "",
        equipment_package_id="fighter_sword_and_board",
        selected_background_tool_ids=("dice_set",),
    )


def test_character_catalog_loads_character_content(catalog, resources):
    assert [item.id for item in catalog.species] == [
        "human", "elf", "dwarf", "halfling", "dragonborn",
        "gnome", "half_elf", "half_orc", "tiefling",
    ]
    assert [item.id for item in catalog.classes] == [
        "barbarian", "bard", "cleric", "druid", "fighter", "monk",
        "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard",
    ]
    assert [item.id for item in catalog.backgrounds] == [
        "acolyte", "charlatan", "criminal", "entertainer", "folk_hero",
        "guild_artisan", "hermit", "noble", "outlander", "sage", "sailor",
        "soldier", "urchin",
    ]
    assert all(item.description for item in catalog.species)
    assert all(item.description for item in catalog.classes)
    assert all(item.description for item in catalog.backgrounds)
    assert all(len(item.skill_proficiencies) == 2 for item in catalog.backgrounds)
    assert all(item.feature_ids for item in catalog.backgrounds)
    assert all(item.permission_ids for item in catalog.backgrounds)
    assert len(resources.inventory_items) >= 29
    assert len(resources.spells) >= 127


def test_tiefling_infernal_legacy_is_level_gated_slotless_and_recovers(
    catalog,
    resources,
):
    level_one = build_character(
        tiefling_fighter_draft(level=1),
        catalog,
        resources,
    ).actor
    level_two = build_character(
        tiefling_fighter_draft(level=2),
        catalog,
        resources,
    ).actor
    level_three = build_character(
        tiefling_fighter_draft(level=3),
        catalog,
        resources,
    ).actor

    assert {spell.id for spell in level_one.spells} == {"thaumaturgy"}
    assert {spell.id for spell in level_two.spells} == {
        "thaumaturgy",
        "hellish_rebuke",
    }
    assert {spell.id for spell in level_three.spells} == {
        "thaumaturgy",
        "hellish_rebuke",
        "darkness",
    }
    assert not level_two.spell_slots
    assert {
        pool.id for pool in level_three.resource_pools
    } >= {
        "infernal_legacy_hellish_rebuke",
        "infernal_legacy_darkness",
    }
    rebuke = next(
        action
        for action in compile_actor_combat_content(level_two).combat_actions
        if action.id == "hellish_rebuke"
    )
    assert rebuke.action_type == "reaction_damage"
    assert rebuke.ongoing_damage_dice_count == 2
    assert rebuke.damage_die_sides == 10
    assert rebuke.upcast_value_per_level == 1

    hands_free = replace(
        level_two,
        inventory=tuple(
            replace(item, equipped=False, held_in=())
            for item in level_two.inventory
        ),
    )
    validation = actor_spell_cast_validation(hands_free, "hellish_rebuke")
    assert validation is not None and validation.valid
    use = consume_spell_resource(
        hands_free,
        spell_level=1,
        spell_id="hellish_rebuke",
    )
    spent_pool = next(
        pool
        for pool in use.actor_after.resource_pools
        if pool.id == "infernal_legacy_hellish_rebuke"
    )
    assert spent_pool.current == 0
    restored = complete_long_rest(use.actor_after).actor_after
    restored_pool = next(
        pool
        for pool in restored.resource_pools
        if pool.id == "infernal_legacy_hellish_rebuke"
    )
    assert restored_pool.current == 1


def test_character_validation_requires_supported_level_point_buy_and_legal_choices(catalog):
    draft = replace(
        fighter_draft(),
        level=4,
        base_ability_scores=AbilityScores(18, 14, 13, 12, 10, 8),
        selected_skill_ids=("athletics", "perception"),
        selected_subclass_id="champion",
    )

    validation = validate_character_draft(draft, catalog)

    assert validation.valid is False
    assert {issue.code for issue in validation.issues} == {
        "unsupported",
        "point_buy_range",
        "already_granted",
    }


def test_fighter_build_derives_actor_rules_and_equipment(catalog, resources):
    created = build_character(fighter_draft(), catalog, resources)
    actor = created.actor

    assert actor.name == "Aldren"
    assert actor.level == 1
    assert actor.ability_scores == AbilityScores(16, 15, 14, 13, 11, 9)
    assert actor.max_hp == actor.hp == 12
    assert actor.ac == 12
    assert effective_armor_class(actor) == 19
    assert actor.proficiency_bonus == 2
    assert actor.proficiencies.saving_throws == ("strength", "constitution")
    assert actor.proficiencies.tools == ("land_vehicles", "dice_set")
    assert actor.proficiencies.skills == (
        "athletics",
        "intimidation",
        "perception",
        "survival",
    )
    assert actor.uses_death_saves is True
    assert actor.hit_dice[0].die_sides == 10
    assert actor.hit_dice[0].remaining == 1
    assert actor.resource_pools[0].id == "second_wind_uses"
    assert actor.resource_pools[0].recovery.value == "short_rest"
    assert {feature.feature_id for feature in actor.features} >= {
        "second_wind",
        "fighting_style_defense",
    }
    assert {item.source_ref for item in actor.inventory} >= {
        "longsword",
        "shield",
        "chain_mail",
        "crossbow_bolt",
        "dice_set",
    }
    assert created.languages == ("common", "elvish")
    assert "second_wind" in created.trait_ids


def test_custom_character_compiles_equipment_into_runtime_attack_sources(
    catalog,
    resources,
):
    actor = build_character(fighter_draft(), catalog, resources).actor

    compiled = compile_actor_combat_content(actor)

    source_ids = {source.id for source in compiled.attack_sources}
    assert {"longsword_slash", "crossbow_shot"} <= source_ids
    longsword = next(
        source
        for source in compiled.attack_sources
        if source.id == "longsword_slash"
    )
    assert longsword.source_item_id == "longsword"
    assert sum(
        modifier.value
        for modifier in longsword.attack_roll_request.modifiers
    ) == 5


def test_custom_party_replaces_scenario_fixtures_and_keeps_runtime_sources(
    catalog,
    resources,
):
    actor = build_character(fighter_draft(), catalog, resources).actor
    encounter = build_encounter_from_scenario(
        load_scenario("content/scenarios/gate_skirmish.json")
    )

    customized = encounter_with_custom_party(encounter, (actor,))

    allies = tuple(
        candidate
        for candidate in customized.actors
        if candidate.faction.value == "ally"
    )
    assert [str(candidate.id) for candidate in allies] == ["aldren"]
    assert {
        source.id
        for source in customized.attack_source_options_by_actor[actor.id]
    } >= {"longsword_slash", "crossbow_shot"}


def test_level_up_to_two_applies_progression_without_free_rest(catalog, resources):
    created = build_character(fighter_draft(), catalog, resources)
    actor = replace(
        created.actor,
        hp=7,
        experience_points=300,
        resource_pools=tuple(
            replace(pool, current=0)
            if pool.id == "second_wind_uses"
            else pool
            for pool in created.actor.resource_pools
        ),
    )

    result = level_up_character(
        replace(created, actor=actor),
        catalog,
        resources,
    )

    assert result.level_after == 2
    assert result.hit_points_gained == 8
    assert result.character_after.actor.hp == 15
    assert result.character_after.actor.max_hp == 20
    assert result.character_after.actor.hit_dice[0].remaining == 2
    pools = {
        pool.id: pool.current
        for pool in result.character_after.actor.resource_pools
    }
    assert pools == {"second_wind_uses": 0, "action_surge_uses": 1}


def test_level_up_rejects_character_without_required_xp(catalog, resources):
    created = build_character(fighter_draft(), catalog, resources)

    with pytest.raises(ValueError, match="Za mało XP"):
        level_up_character(created, catalog, resources)


def test_sorcerer_level_up_collects_new_spell_and_metamagic_choices(
    catalog,
    resources,
):
    draft = CharacterDraft(
        id="sylra",
        name="Sylra",
        species_id="human",
        class_id="sorcerer",
        background_id="soldier",
        base_ability_scores=AbilityScores(8, 14, 13, 12, 10, 15),
        selected_skill_ids=("arcana", "deception"),
        equipment_package_id="sorcerer_explorer",
        selected_cantrip_ids=(
            "acid_splash",
            "fire_bolt",
            "mage_hand",
            "minor_illusion",
        ),
        selected_spell_ids=("burning_hands", "shield"),
        selected_subclass_id="draconic_bloodline",
        selected_species_language_ids=("draconic",),
        selected_background_tool_ids=("dice_set",),
    )
    created = build_character(draft, catalog, resources)
    created = replace(
        created,
        actor=replace(created.actor, experience_points=900),
    )

    level_two = level_up_character(
        created,
        catalog,
        resources,
        choices=LevelUpChoices(
            selected_spell_ids=("burning_hands", "shield", "magic_missile"),
        ),
    ).character_after
    level_three = level_up_character(
        level_two,
        catalog,
        resources,
        choices=LevelUpChoices(
            selected_spell_ids=(
                "burning_hands",
                "shield",
                "magic_missile",
                "misty_step",
            ),
            selected_class_option_ids=("quickened_spell", "subtle_spell"),
        ),
    ).character_after

    assert level_two.actor.level == 2
    assert next(
        pool for pool in level_two.actor.resource_pools if pool.id == "sorcery_points"
    ).maximum == 2
    assert level_three.actor.level == 3
    assert {"metamagic_quickened", "metamagic_subtle"} <= {
        feature.feature_id for feature in level_three.actor.features
    }


def test_rogue_combines_species_background_and_class_proficiencies(catalog, resources):
    draft = CharacterDraft(
        id="mira",
        name="Mira",
        species_id="elf",
        class_id="rogue",
        background_id="criminal",
        base_ability_scores=AbilityScores(10, 15, 14, 13, 12, 8),
        selected_skill_ids=("acrobatics", "athletics", "insight", "performance"),
        selected_expertise_ids=("stealth", "perception"),
        equipment_package_id="rogue_burglar",
        selected_species_cantrip_ids=("mage_hand",),
        selected_species_language_ids=("dwarvish",),
        selected_background_tool_ids=("dice_set",),
    )

    created = build_character(draft, catalog, resources)
    actor = created.actor

    assert actor.speed_feet == 30
    assert actor.senses.darkvision_feet == 60
    assert actor.ability_scores.dexterity == 17
    assert actor.max_hp == 10
    assert set(actor.proficiencies.skills) == {
        "perception",
        "deception",
        "stealth",
        "acrobatics",
        "athletics",
        "insight",
        "performance",
    }
    assert actor.proficiencies.tools == ("thieves_tools", "dice_set")
    assert actor.proficiencies.expertise == ("stealth", "perception")
    assert "sneak_attack" in {feature.feature_id for feature in actor.features}
    assert effective_armor_class(actor) == 14


def test_cleric_builds_spell_slots_access_and_preparation(catalog, resources):
    draft = CharacterDraft(
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
    )

    created = build_character(draft, catalog, resources)
    actor = created.actor

    assert actor.spell_save_dc == 13
    assert actor.spell_slots[0].level == 1
    assert actor.spell_slots[0].remaining == actor.spell_slots[0].maximum == 2
    assert {
        "guidance", "light", "sacred_flame", "bless", "cure_wounds",
        "healing_word", "inflict_wounds", "guiding_bolt", "shield_of_faith",
    } <= set(actor.spell_ids)
    assert actor.spell_preparation is not None
    assert actor.spell_preparation.confirmed is True
    assert actor.spell_preparation.preparation_limit == 4
    assert actor.spell_preparation.prepared_spell_ids == (
        "healing_word",
        "inflict_wounds",
        "guiding_bolt",
        "shield_of_faith",
    )
    assert actor.spell_preparation.always_prepared_spell_ids == (
        "bless",
        "cure_wounds",
    )
    assert "heavy" in actor.proficiencies.armor
    assert "disciple_of_life" in {feature.feature_id for feature in actor.features}
    assert effective_armor_class(actor) == 17
    assert actor.damage_affinities.is_resistant_to(DamageType.POISON)
    assert "dwarven_speed" in {feature.feature_id for feature in actor.features}
    assert created.languages == ("common", "dwarvish", "elvish", "gnomish")


def test_level_one_prepared_caster_does_not_receive_level_two_spells(
    catalog,
    resources,
):
    draft = CharacterDraft(
        id="elowen_l1",
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
    )

    actor = build_character(draft, catalog, resources).actor

    assert "spiritual_weapon" not in actor.spell_ids
    assert all(spell.level <= 1 for spell in actor.spells)


def test_life_domain_level_three_gates_and_grants_domain_spells(
    catalog,
    resources,
):
    draft = CharacterDraft(
        id="elowen_l3",
        name="Elowen III",
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
            "aid",
            "hold_person",
        ),
        selected_subclass_id="life_domain",
        selected_species_tool_ids=("smiths_tools",),
        selected_background_language_ids=("elvish", "gnomish"),
        level=3,
    )

    actor = build_character(draft, catalog, resources).actor

    assert set(actor.spell_preparation.always_prepared_spell_ids) == {
        "bless",
        "cure_wounds",
        "lesser_restoration",
        "spiritual_weapon",
    }
    assert "channel_divinity_preserve_life" in {
        feature.feature_id for feature in actor.features
    }


def test_fiend_expanded_spells_are_choices_not_automatically_known(
    catalog,
    resources,
):
    base = CharacterDraft(
        id="vex",
        name="Vex",
        species_id="human",
        class_id="warlock",
        background_id="soldier",
        base_ability_scores=AbilityScores(8, 14, 13, 12, 10, 15),
        selected_skill_ids=("arcana", "deception"),
        equipment_package_id="warlock_scholar",
        selected_cantrip_ids=("eldritch_blast", "mage_hand"),
        selected_spell_ids=("burning_hands", "hex"),
        selected_subclass_id="the_fiend",
        selected_species_language_ids=("infernal",),
        selected_background_tool_ids=("dice_set",),
    )
    # Hex is not part of SRD 5.1 and therefore remains unavailable.
    with pytest.raises(ValueError, match="niedostępne"):
        build_character(base, catalog, resources)

    actor = build_character(
        replace(base, selected_spell_ids=("burning_hands", "command")),
        catalog,
        resources,
    ).actor
    assert {"burning_hands", "command"} <= set(actor.spell_ids)
    assert actor.spell_preparation is None
    compiled = compile_actor_combat_content(actor)
    command = next(
        action
        for action in compiled.combat_actions
        if action.id == "command"
    )
    assert command.action_type == "targeted_status"
    assert command.condition == CombatCondition.INCAPACITATED
    assert command.save_ability == "wisdom"
    assert command.instructions


def test_warlock_invocations_grant_at_will_spells_skills_and_devils_sight(
    catalog,
    resources,
):
    actor = build_character(
        CharacterDraft(
            id="vex_invocations",
            name="Vex",
            species_id="human",
            class_id="warlock",
            background_id="soldier",
            base_ability_scores=AbilityScores(8, 14, 13, 12, 10, 15),
            selected_skill_ids=("arcana", "investigation"),
            equipment_package_id="warlock_scholar",
            selected_cantrip_ids=("eldritch_blast", "mage_hand"),
            selected_spell_ids=("command", "charm_person", "hellish_rebuke"),
            selected_subclass_id="the_fiend",
            selected_class_option_ids=("armor_of_shadows", "beguiling_influence"),
            selected_species_language_ids=("infernal",),
            selected_background_tool_ids=("dice_set",),
            level=2,
        ),
        catalog,
        resources,
    ).actor

    assert {"deception", "persuasion"} <= set(actor.proficiencies.skills)
    assert "mage_armor" in actor.spell_ids
    assert any(
        profile.kind.value == "at_will"
        and "mage_armor" in profile.spell_ids
        for profile in actor.spell_access
    )
    slotless = replace(
        actor,
        spell_slots=tuple(
            replace(slot, remaining=0)
            for slot in actor.spell_slots
        ),
        inventory=tuple(
            replace(
                item,
                equipped=item.spellcasting_focus_kind is not None,
                held_in=(),
            )
            for item in actor.inventory
        ),
    )
    validation = actor_spell_cast_validation(slotless, "mage_armor")
    assert validation is not None and validation.valid
    assert consume_spell_resource(
        slotless,
        spell_level=1,
        spell_id="mage_armor",
    ).consumed is False

    devil_sighted = build_character(
        CharacterDraft(
            id="vex_devils_sight",
            name="Vex",
            species_id="human",
            class_id="warlock",
            background_id="soldier",
            base_ability_scores=AbilityScores(8, 14, 13, 12, 10, 15),
            selected_skill_ids=("arcana", "investigation"),
            equipment_package_id="warlock_scholar",
            selected_cantrip_ids=("eldritch_blast", "mage_hand"),
            selected_spell_ids=("command", "charm_person", "hellish_rebuke"),
            selected_subclass_id="the_fiend",
            selected_class_option_ids=("devils_sight", "beguiling_influence"),
            selected_species_language_ids=("infernal",),
            selected_background_tool_ids=("dice_set",),
            level=2,
        ),
        catalog,
        resources,
    ).actor
    assert devil_sighted.senses.darkvision_feet == 120
    assert devil_sighted.senses.magical_darkness_vision_feet == 120


@pytest.mark.parametrize(
    ("pact_option", "selected_cantrips", "expected_spell"),
    (
        (
            "pact_of_the_chain",
            ("eldritch_blast", "mage_hand"),
            "find_familiar",
        ),
        (
            "pact_of_the_tome",
            (
                "eldritch_blast",
                "mage_hand",
                "guidance",
                "light",
                "druidcraft",
            ),
            "guidance",
        ),
    ),
)
def test_warlock_pact_boons_grant_chain_ritual_or_tome_cantrips(
    catalog,
    resources,
    pact_option,
    selected_cantrips,
    expected_spell,
):
    actor = build_character(
        CharacterDraft(
            id=f"vex_{pact_option}",
            name="Vex",
            species_id="human",
            class_id="warlock",
            background_id="soldier",
            base_ability_scores=AbilityScores(8, 14, 13, 12, 10, 15),
            selected_skill_ids=("arcana", "investigation"),
            equipment_package_id="warlock_scholar",
            selected_cantrip_ids=selected_cantrips,
            selected_spell_ids=(
                "command",
                "charm_person",
                "hellish_rebuke",
                "misty_step",
            ),
            selected_subclass_id="the_fiend",
            selected_class_option_ids=(
                "agonizing_blast",
                "armor_of_shadows",
                pact_option,
            ),
            selected_species_language_ids=("infernal",),
            selected_background_tool_ids=("dice_set",),
            level=3,
        ),
        catalog,
        resources,
    ).actor

    assert expected_spell in actor.spell_ids
    if pact_option == "pact_of_the_chain":
        familiar = next(
            profile
            for profile in actor.spell_access
            if expected_spell in profile.spell_ids
        )
        assert familiar.kind.value == "spellbook"
        validation = actor_spell_cast_validation(
            actor,
            "find_familiar",
            ritual=True,
        )
        assert validation is not None
        # The ritual still correctly requires its consumed 10 gp material.
        assert validation.valid is False
        assert any("komponentu materialnego" in error for error in validation.errors)
    else:
        assert {
            "guidance",
            "light",
            "druidcraft",
        } <= set(actor.spell_ids)


def test_druid_land_and_paladin_oath_level_three_choices_are_executable_grants(
    catalog,
    resources,
):
    druid = build_character(
        CharacterDraft(
            id="rowan",
            name="Rowan",
            species_id="human",
            class_id="druid",
            background_id="sage",
            base_ability_scores=AbilityScores(10, 14, 13, 12, 15, 8),
            selected_skill_ids=("nature", "survival"),
            equipment_package_id="druid_explorer",
            selected_cantrip_ids=("druidcraft", "guidance", "shillelagh"),
            selected_prepared_spell_ids=(
                "animal_friendship",
                "cure_wounds",
                "entangle",
                "faerie_fire",
                "healing_word",
                "moonbeam",
            ),
            selected_subclass_id="circle_of_the_land",
            selected_class_option_ids=("circle_land_coast",),
            selected_species_language_ids=("dwarvish",),
            selected_background_language_ids=("elvish", "sylvan"),
            level=3,
        ),
        catalog,
        resources,
    ).actor
    assert set(druid.spell_preparation.always_prepared_spell_ids) == {
        "mirror_image",
        "misty_step",
    }

    paladin = build_character(
        CharacterDraft(
            id="ser_ada",
            name="Ser Ada",
            species_id="human",
            class_id="paladin",
            background_id="soldier",
            base_ability_scores=AbilityScores(15, 10, 14, 8, 12, 13),
            selected_skill_ids=("medicine", "persuasion"),
            selected_fighting_style_id="defense",
            equipment_package_id="paladin_guardian",
            selected_prepared_spell_ids=(
                "bless",
                "cure_wounds",
                "shield_of_faith",
            ),
            selected_subclass_id="oath_of_devotion",
            selected_species_language_ids=("celestial",),
            selected_background_tool_ids=("dice_set",),
            level=3,
        ),
        catalog,
        resources,
    ).actor
    channel = next(
        pool
        for pool in paladin.resource_pools
        if pool.id == "channel_divinity_uses"
    )
    assert channel.maximum == 1
    assert {
        "channel_divinity_sacred_weapon",
        "channel_divinity_turn_the_unholy",
    } <= {feature.feature_id for feature in paladin.features}


def test_lore_bard_level_three_combines_bonus_skills_and_expertise(
    catalog,
    resources,
):
    actor = build_character(
        CharacterDraft(
            id="lyra",
            name="Lyra",
            species_id="human",
            class_id="bard",
            background_id="soldier",
            base_ability_scores=AbilityScores(8, 14, 13, 12, 10, 15),
            selected_skill_ids=("arcana", "deception", "performance"),
            selected_expertise_ids=("arcana", "medicine"),
            equipment_package_id="bard_diplomat",
            selected_cantrip_ids=("vicious_mockery", "mage_hand"),
            selected_spell_ids=(
                "bane",
                "charm_person",
                "healing_word",
                "heroism",
                "hold_person",
                "invisibility",
            ),
            selected_subclass_id="college_of_lore",
            selected_class_option_ids=(
                "bard_instrument_flute",
                "bard_instrument_lute",
                "bard_instrument_viol",
                "lore_skill_medicine",
                "lore_skill_nature",
                "lore_skill_stealth",
            ),
            selected_species_language_ids=("elvish",),
            selected_background_tool_ids=("dice_set",),
            level=3,
        ),
        catalog,
        resources,
    ).actor

    assert {"medicine", "nature", "stealth"} <= set(
        actor.proficiencies.skills
    )
    assert actor.proficiencies.expertise == ("arcana", "medicine")
    assert {"flute", "lute", "viol"} <= set(actor.proficiencies.tools)
    assert "cutting_words" in {
        feature.feature_id for feature in actor.features
    }


def test_duplicate_starting_weapons_are_distinct_runtime_instances(
    catalog,
    resources,
):
    ranger = build_character(
        CharacterDraft(
            id="talan",
            name="Talan",
            species_id="human",
            class_id="ranger",
            selected_class_option_ids=(
                "favored_enemy_beast",
                "natural_explorer_forest",
            ),
            background_id="soldier",
            base_ability_scores=AbilityScores(12, 15, 14, 10, 13, 8),
            selected_skill_ids=("nature", "perception", "stealth"),
            equipment_package_id="ranger_archer",
            selected_species_language_ids=("elvish",),
            selected_background_tool_ids=("dice_set",),
        ),
        catalog,
        resources,
    ).actor

    shortswords = tuple(
        item
        for item in ranger.inventory
        if item.source_ref == "shortsword"
    )
    assert [item.id for item in shortswords] == [
        "shortsword",
        "shortsword_2",
    ]
    assert all(item.quantity == 1 for item in shortswords)
    arrows = next(item for item in ranger.inventory if item.source_ref == "arrow")
    assert arrows.quantity == 20


def test_ranger_humanoid_favored_enemy_requires_exactly_two_races(
    catalog,
    resources,
):
    base = CharacterDraft(
        id="talan_humanoid",
        name="Talan",
        species_id="human",
        class_id="ranger",
        selected_class_option_ids=(
            "favored_enemy_humanoid",
            "natural_explorer_forest",
        ),
        background_id="soldier",
        base_ability_scores=AbilityScores(12, 15, 14, 10, 13, 8),
        selected_skill_ids=("nature", "perception", "stealth"),
        equipment_package_id="ranger_archer",
        selected_species_language_ids=("elvish",),
        selected_background_tool_ids=("dice_set",),
    )

    validation = validate_character_draft(base, catalog)
    assert any(
        issue.field == "selected_class_option_ids"
        and "dwie rasy humanoidów" in issue.message
        for issue in validation.issues
    )

    character = build_character(
        replace(
            base,
            selected_class_option_ids=(
                *base.selected_class_option_ids,
                "favored_enemy_humanoid_race_gnoll",
                "favored_enemy_humanoid_race_orc",
            ),
        ),
        catalog,
        resources,
    )

    assert {
        "favored_enemy_humanoid",
        "favored_enemy_humanoid_race_gnoll",
        "favored_enemy_humanoid_race_orc",
    } <= set(character.trait_ids)


def test_wizard_builds_spellbook_character(catalog, resources):
    draft = CharacterDraft(
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
    )

    actor = build_character(draft, catalog, resources).actor

    assert actor.max_hp == 8
    assert actor.spell_save_dc == 13
    assert actor.spell_access[0].kind.value == "spellbook"
    assert actor.spell_preparation is not None
    assert actor.spell_preparation.preparation_limit == 4
    assert actor.spell_preparation.prepared_spell_ids == (
        "burning_hands",
        "comprehend_languages",
        "shield",
        "magic_missile",
    )
    assert actor.resource_pools[0].id == "arcane_recovery_uses"
    assert actor.proficiencies.skills == (
        "arcana",
        "history",
        "investigation",
        "medicine",
    )
    fire_bolt = next(
        source
        for source in compile_actor_combat_content(actor).attack_sources
        if source.id == "fire_bolt"
    )
    assert fire_bolt.tabletop_riders == (
        "Trafiony nieprzymocowany łatwopalny obiekt, którego nikt nie nosi, zapala się.",
    )


def test_saved_character_round_trip_rebuilds_derived_actor(catalog, resources):
    created = build_character(fighter_draft(), catalog, resources)

    payload = character_record_payload(created)
    restored = created_character_from_payload(payload, catalog, resources)

    assert payload["schema"] == "dnd_board_game.character"
    assert payload["schema_version"] == 7
    assert restored == created


def test_build_rejects_missing_content_resource(catalog, resources):
    broken = replace(
        resources,
        inventory_items=tuple(
            entry for entry in resources.inventory_items if entry[0] != "longsword"
        ),
    )

    with pytest.raises(ValueError, match="Brakuje definicji przedmiotu: longsword"):
        build_character(fighter_draft(), catalog, broken)


def test_saved_character_rejects_unknown_schema_version(catalog, resources):
    payload = character_record_payload(build_character(fighter_draft(), catalog, resources))
    payload["schema_version"] = 99

    with pytest.raises(ValueError, match="Nieobsługiwana wersja"):
        created_character_from_payload(payload, catalog, resources)


def test_saved_character_v2_migrates_with_zero_experience(catalog, resources):
    payload = character_record_payload(build_character(fighter_draft(), catalog, resources))
    payload["schema_version"] = 2
    payload.pop("experience_points")

    restored = created_character_from_payload(payload, catalog, resources)

    assert restored.actor.experience_points == 0


def test_half_elf_applies_two_distinct_flexible_ability_bonuses(catalog, resources):
    draft = replace(
        fighter_draft(),
        species_id="half_elf",
        selected_species_bonus_ability_ids=("strength", "constitution"),
        selected_species_skill_ids=("arcana", "nature"),
        selected_species_language_ids=("dwarvish",),
        selected_background_tool_ids=("dice_set",),
    )

    actor = build_character(draft, catalog, resources).actor

    assert actor.ability_scores == AbilityScores(16, 14, 14, 12, 10, 10)


def test_half_elf_rejects_charisma_as_flexible_bonus(catalog):
    validation = validate_character_draft(
        replace(
            fighter_draft(),
            species_id="half_elf",
            selected_species_bonus_ability_ids=("strength", "charisma"),
            selected_species_skill_ids=("arcana", "nature"),
            selected_species_language_ids=("dwarvish",),
        ),
        catalog,
    )
    assert validation.valid is False
    assert any(
        issue.field == "selected_species_bonus_ability_ids"
        and issue.code == "unknown"
        for issue in validation.issues
    )


def test_dragonborn_ancestry_drives_resistance_and_breath_source(catalog, resources):
    draft = replace(
        fighter_draft(),
        species_id="dragonborn",
        selected_species_language_ids=(),
        selected_species_variant_id="blue_dragon_ancestry",
    )

    actor = build_character(draft, catalog, resources).actor
    breath = breath_weapon_attack_source(actor)

    assert actor.damage_affinities.is_resistant_to(DamageType.LIGHTNING)
    assert breath is not None
    assert breath.area is not None
    assert breath.area.shape.value == "line"
    assert breath.save_ability == "dexterity"
    assert breath.damage_components[0].dice.format() == "2d6"
    assert breath.resource_pool_id == "breath_weapon_uses"


def test_fighter_requires_authored_fighting_style_choice(catalog):
    validation = validate_character_draft(
        replace(fighter_draft(), selected_fighting_style_id="great_weapon_fighting"),
        catalog,
    )

    assert validation.valid is False
    assert any(
        issue.field == "selected_fighting_style_id" and issue.code == "unknown"
        for issue in validation.issues
    )


def test_rogue_expertise_requires_an_owned_skill_proficiency(catalog):
    draft = CharacterDraft(
        id="mira",
        name="Mira",
        species_id="elf",
        class_id="rogue",
        background_id="criminal",
        base_ability_scores=AbilityScores(10, 15, 14, 13, 12, 8),
        selected_skill_ids=("acrobatics", "athletics", "insight", "performance"),
        selected_expertise_ids=("stealth", "arcana"),
        equipment_package_id="rogue_burglar",
        selected_species_cantrip_ids=("mage_hand",),
        selected_species_language_ids=("dwarvish",),
    )

    validation = validate_character_draft(draft, catalog)

    assert validation.valid is False
    assert any(issue.code == "not_proficient" for issue in validation.issues)
