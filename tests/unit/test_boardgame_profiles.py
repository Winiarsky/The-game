from dataclasses import replace

from dnd_board_game.character_creation import (
    apply_boardgame_archetype,
    build_character,
    default_character_drafts,
    load_character_catalog,
    load_character_resources,
    reconcile_boardgame_feature_removals,
)
from dnd_board_game.inventory import effective_armor_class


def _actors():
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    return {
        draft.id: apply_boardgame_archetype(
            build_character(draft, catalog, resources).actor,
            spell_definitions=tuple(spell for _, spell in resources.spells),
        )
        for draft in default_character_drafts()
    }


def _actors_at_level(level: int):
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    return {
        draft.id: apply_boardgame_archetype(
            replace(build_character(draft, catalog, resources).actor, level=level),
            spell_definitions=tuple(spell for _, spell in resources.spells),
        )
        for draft in default_character_drafts()
    }


def test_curated_exploration_features_are_attached() -> None:
    actors = _actors()
    expected = {
        "garran": {
            "iron_line",
            "action_surge",
            "shield_bash",
            "defensive_stance",
            "garran_command_halt",
            "garran_shield_wall",
            "garran_rally",
            "garran_guard_companion",
        },
        "brakka": {
            "intimidation", "reckless_attack", "powerful_strike",
            "shoulder_check", "brakka_grapple", "hard_as_rock", "acceleration", "deafening_roar",
        },
        "mira": {
            "instinctive_dodge",
            "smoke_screen",
            "hamstring_cut",
            "piercing_attack",
            "guard_vault",
            "blade_mistress",
            "combat_trap_detection",
        },
        "dagna": set(),
        "lorian": {
            "crossbowman",
            "mocking_shot",
            "provoking_shot",
            "counterpoint",
            "distracting_shout",
            "social_grace_bargaining",
            "improvisation",
        },
        "erynd": {
            "first_blood",
            "scouts_vigilance",
            "cunning_action",
            "aim",
            "anchoring_arrow",
            "exposing_arrow",
            "disrupting_arrow",
            "double_shot",
        },
    }
    for actor_id, feature_ids in expected.items():
        assert {feature.feature_id for feature in actors[actor_id].features} >= feature_ids
    flaw_ids = {
        "garran": "flaw_remorse",
        "brakka": "flaw_chains",
        "mira": "flaw_exposed_panic",
        "dagna": "flaw_leave_no_one",
        "lorian": "flaw_needs_audience",
        "nimra": "flaw_arcane_echo",
        "erynd": "flaw_friendly_fire_trauma",
    }
    for actor_id, flaw_id in flaw_ids.items():
        assert flaw_id in {
            feature.feature_id for feature in actors[actor_id].features
        }
    dagna_feature_ids = {
        feature.feature_id for feature in actors["dagna"].features
    }
    assert "stonecunning" not in dagna_feature_ids
    assert "shelter_of_the_faithful" not in dagna_feature_ids
    assert "flaw_leave_no_one" in dagna_feature_ids


def test_dagna_retired_features_are_removed_without_touching_her_flaw() -> None:
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = next(draft for draft in default_character_drafts() if draft.id == "dagna")
    dagna = build_character(draft, catalog, resources).actor
    original_feature_ids = {feature.feature_id for feature in dagna.features}
    assert {"stonecunning", "shelter_of_the_faithful"} <= original_feature_ids

    retired = apply_boardgame_archetype(
        dagna,
        spell_definitions=tuple(spell for _, spell in resources.spells),
    )
    restored = reconcile_boardgame_feature_removals(retired)
    feature_ids = {feature.feature_id for feature in restored.features}

    assert "stonecunning" not in feature_ids
    assert "shelter_of_the_faithful" not in feature_ids
    assert "flaw_leave_no_one" in feature_ids


def test_garran_tactics_and_erynd_instinct_are_long_rest_resources() -> None:
    actors = _actors()
    tactics = next(pool for pool in actors["garran"].resource_pools if pool.id == "tactics_uses")
    instinct = next(pool for pool in actors["erynd"].resource_pools if pool.id == "instinct")
    assert (tactics.current, tactics.maximum, tactics.recovery.value) == (4, 4, "long_rest")
    assert (instinct.current, instinct.maximum, instinct.recovery.value) == (4, 4, "long_rest")
    assert "hunters_mark" in actors["erynd"].spell_ids
    assert any(
        mapping == ("hunters_mark", "instinct")
        for profile in actors["erynd"].spell_access
        for mapping in profile.resource_ids_by_spell
    )
    assert "fighting_style_archery" in {
        feature.feature_id for feature in actors["erynd"].features
    }
    assert set(actors["erynd"].proficiencies.expertise) >= {"stealth", "survival"}


def test_erynd_uses_the_mobile_hunter_equipment_without_stealth_armor_penalty() -> None:
    erynd = _actors()["erynd"]
    items = {item.source_ref or item.id: item for item in erynd.inventory}

    assert items["longbow"].equipped is True
    assert items["hunting_knife"].equipped is False
    assert "finesse" not in items["hunting_knife"].properties
    assert items["studded_leather_armor"].equipped is True
    assert {"shortsword", "shortsword_2"}.isdisjoint(items)
    assert items["studded_leather_armor"].stealth_disadvantage is False
    assert effective_armor_class(erynd) == 16


def test_mira_uses_rapier_and_throwing_knives_without_a_shortbow() -> None:
    mira = _actors()["mira"]
    items = tuple(mira.inventory)
    source_refs = {item.source_ref or item.id for item in items}
    knives = tuple(item for item in items if item.name == "Nóż do rzucania")
    feature_ids = {feature.feature_id for feature in mira.features}

    assert "rapier" in source_refs
    assert "shortbow" not in source_refs
    assert len(knives) == 4
    assert {
        "mira_shadow_stealth",
        "mira_shadow_killer",
        "mira_ranged_evasion",
        "instinctive_dodge",
        "smoke_screen",
        "hamstring_cut",
        "piercing_attack",
        "guard_vault",
        "blade_mistress",
        "combat_trap_detection",
        "lucky",
        "flaw_exposed_panic",
    } <= feature_ids
    assert {
        "brave",
        "halfling_nimbleness",
        "naturally_stealthy",
        "flaw_interrogation",
        "break_in",
        "exploit_weakness",
    }.isdisjoint(feature_ids)


def test_mira_legacy_flaw_is_migrated_without_resetting_actor_state() -> None:
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = next(draft for draft in default_character_drafts() if draft.id == "mira")
    legacy = build_character(draft, catalog, resources).actor
    legacy = replace(legacy, hp=7)

    migrated = reconcile_boardgame_feature_removals(legacy)
    feature_ids = {feature.feature_id for feature in migrated.features}

    assert migrated.hp == 7
    assert "flaw_exposed_panic" in feature_ids
    assert "flaw_interrogation" not in feature_ids


def test_martial_archetypes_receive_starting_combat_choices_and_rest_resources() -> None:
    actors = _actors()
    garran = actors["garran"]
    mira = actors["mira"]
    erynd = actors["erynd"]

    garran_pools = {pool.id: pool for pool in garran.resource_pools}
    assert garran_pools["action_surge_uses"].recovery.value == "short_rest"
    assert garran_pools["tactics_uses"].maximum == 4
    assert {
        "guard_duty_uses", "defensive_stance_uses", "lay_on_hands_points"
    }.isdisjoint(garran_pools)

    mira_pools = {pool.id: pool for pool in mira.resource_pools}
    assert "instinctive_dodge_uses" not in mira_pools
    assert (mira_pools["trick_uses"].current, mira_pools["trick_uses"].maximum) == (4, 4)
    assert {"invisibility", "find_traps", "vicious_mockery", "mirror_image"}.isdisjoint(mira.spell_ids)
    assert set(erynd.spell_ids) == {"hunters_mark", "misty_step", "spike_growth"}

    resource_by_spell = {
        spell_id: resource_id
        for actor in (mira, erynd)
        for profile in actor.spell_access
        for spell_id, resource_id in profile.resource_ids_by_spell
    }
    assert resource_by_spell["misty_step"] == "instinct"
    assert resource_by_spell["spike_growth"] == "instinct"


def test_level_three_cards_receive_matching_features_spells_and_pools() -> None:
    level_three = _actors_at_level(3)

    assert {
        "action_surge",
        "cunning_action",
        "danger_sense",
        "frenzy",
    }.isdisjoint({feature.feature_id for feature in level_three["brakka"].features})
    assert {pool.id for pool in level_three["garran"].resource_pools} >= {
        "tactics_uses"
    }
    assert {pool.id for pool in level_three["brakka"].resource_pools} >= {
        "ferocity_uses"
    }

    expected_spells = {
        "garran": set(),
        "brakka": set(),
        "mira": set(),
        "dagna": {"sacred_flame", "healing_word", "bless", "divine_care_aura", "guiding_bolt", "healing_grace_aura", "lesser_restoration", "spiritual_weapon"},
        "lorian": {"thunderwave", "faerie_fire", "panic_whisper", "hideous_laughter", "stage_command", "accelerated_refrain"},
        "nimra": {"nimra_frost_pulse", "nimra_acid_splash", "nimra_mind_spike", "nimra_flame_fan", "nimra_force_wave", "nimra_sticky_matrix", "shield", "nimra_sleep", "nimra_fog", "nimra_web", "nimra_lightning_path", "nimra_mind_break", "nimra_stasis", "misty_step", "shatter"},
        "erynd": {"hunters_mark", "misty_step", "spike_growth"},
    }
    for actor_id, spell_ids in expected_spells.items():
        assert spell_ids <= set(level_three[actor_id].spell_ids)

    custom_resources = {
        "garran": ("tactics_uses", 4),
        "brakka": ("ferocity_uses", 3),
        "mira": ("trick_uses", 4),
        "erynd": ("instinct", 4),
    }
    for actor_id, (pool_id, maximum) in custom_resources.items():
        pool = next(
            pool for pool in level_three[actor_id].resource_pools if pool.id == pool_id
        )
        expected_current = 0 if actor_id == "brakka" else maximum
        expected_recovery = "never" if actor_id == "brakka" else "long_rest"
        assert (pool.current, pool.maximum, pool.recovery.value) == (
            expected_current, maximum, expected_recovery,
        )


def test_level_three_starters_get_primary_boost_and_only_their_card_deck_access() -> None:
    actors = _actors()
    assert (
        actors["brakka"].ability_scores.constitution,
        actors["brakka"].ac,
        actors["brakka"].hp,
    ) == (16, 14, 35)
    expected_scores = {
        "garran": ("strength", 18),
        "brakka": ("strength", 18),
        "mira": ("dexterity", 19),
        "dagna": ("wisdom", 18),
        "lorian": ("charisma", 19),
        "nimra": ("intelligence", 19),
        "erynd": ("dexterity", 19),
    }
    expected_access = {
        "garran": set(),
        "brakka": set(),
        "mira": set(),
        "dagna": {"sacred_flame", "healing_word", "bless", "divine_care_aura", "guiding_bolt", "healing_grace_aura", "lesser_restoration", "spiritual_weapon"},
        "lorian": {"thunderwave", "faerie_fire", "panic_whisper", "hideous_laughter", "stage_command", "accelerated_refrain"},
        "nimra": {"nimra_frost_pulse", "nimra_acid_splash", "nimra_mind_spike", "nimra_flame_fan", "nimra_force_wave", "nimra_sticky_matrix", "shield", "nimra_sleep", "nimra_fog", "nimra_web", "nimra_lightning_path", "nimra_mind_break", "nimra_stasis", "misty_step", "shatter"},
        "erynd": {"hunters_mark", "misty_step", "spike_growth"},
    }
    for actor_id, (ability_id, score) in expected_scores.items():
        actor = actors[actor_id]
        assert actor.level == 3
        assert getattr(actor.ability_scores, ability_id) == score
        assert {
            spell_id
            for profile in actor.spell_access
            for spell_id in profile.spell_ids
        } == expected_access[actor_id]
        assert actor.spell_preparation is None
    assert actors["erynd"].spell_slots == ()
    inspiration = next(
        pool
        for pool in actors["lorian"].resource_pools
        if pool.id == "bardic_inspiration_uses"
    )
    assert (inspiration.current, inspiration.maximum) == (4, 4)
    assert inspiration.recovery.value == "short_rest"
    metamagic = next(
        pool for pool in actors["nimra"].resource_pools if pool.id == "metamagic_points"
    )
    assert (metamagic.current, metamagic.maximum, metamagic.recovery.value) == (
        4,
        4,
        "long_rest",
    )
    lorian = actors["lorian"]
    assert {item.source_ref or item.id for item in lorian.inventory} == {
        "hand_crossbow",
        "rapier",
        "leather_armor",
        "lute",
    }
    assert {"persuasion", "stealth"}.isdisjoint(lorian.skill_expertise)


def test_boardgame_primary_boost_is_idempotent() -> None:
    actor = _actors()["mira"]
    reapplied = apply_boardgame_archetype(actor)

    assert reapplied.ability_scores.dexterity == 19
    assert sum(
        feature.feature_id == "boardgame_level_3_ability_boost"
        for feature in reapplied.features
    ) == 1
