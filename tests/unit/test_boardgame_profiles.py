from dataclasses import replace

from dnd_board_game.character_creation import (
    apply_boardgame_archetype,
    build_character,
    default_character_drafts,
    load_character_catalog,
    load_character_resources,
)


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
            "guard_duty",
            "iron_line",
            "action_surge",
            "lay_on_hands",
            "defensive_stance",
        },
        "brakka": {"intimidation", "reckless_attack", "frenzy"},
        "mira": {
            "break_in",
            "cunning_action",
            "instinctive_dodge",
            "exploit_weakness",
        },
        "dagna": {"diagnosis"},
        "erynd": {"tracking", "cunning_action", "patient_shot"},
    }
    for actor_id, feature_ids in expected.items():
        assert {feature.feature_id for feature in actors[actor_id].features} >= feature_ids
    flaw_ids = {
        "garran": "flaw_command_guilt",
        "brakka": "flaw_chains",
        "mira": "flaw_interrogation",
        "dagna": "flaw_leave_no_one",
        "lorian": "flaw_approval",
        "nimra": "flaw_arcane_echo",
        "erynd": "flaw_ambush_survivor",
    }
    for actor_id, flaw_id in flaw_ids.items():
        assert flaw_id in {
            feature.feature_id for feature in actors[actor_id].features
        }


def test_guard_duty_and_instinct_are_long_rest_resources() -> None:
    actors = _actors()
    guard = next(pool for pool in actors["garran"].resource_pools if pool.id == "guard_duty_uses")
    instinct = next(pool for pool in actors["erynd"].resource_pools if pool.id == "instinct")
    assert (guard.current, guard.maximum, guard.recovery.value) == (3, 3, "long_rest")
    assert (instinct.current, instinct.maximum, instinct.recovery.value) == (3, 3, "long_rest")
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


def test_martial_archetypes_receive_starting_combat_choices_and_rest_resources() -> None:
    actors = _actors()
    garran = actors["garran"]
    mira = actors["mira"]
    erynd = actors["erynd"]

    garran_pools = {pool.id: pool for pool in garran.resource_pools}
    assert garran_pools["action_surge_uses"].recovery.value == "short_rest"
    assert garran_pools["defensive_stance_uses"].recovery.value == "short_rest"
    assert garran_pools["lay_on_hands_points"].maximum == 15

    mira_pools = {pool.id: pool for pool in mira.resource_pools}
    assert mira_pools["instinctive_dodge_uses"].recovery.value == "short_rest"
    assert (mira_pools["trick_uses"].current, mira_pools["trick_uses"].maximum) == (3, 3)
    assert {"invisibility", "find_traps"} <= set(mira.spell_ids)
    assert {"hunters_mark", "goodberry", "find_traps"} <= set(erynd.spell_ids)

    resource_by_spell = {
        spell_id: resource_id
        for actor in (mira, erynd)
        for profile in actor.spell_access
        for spell_id, resource_id in profile.resource_ids_by_spell
    }
    assert resource_by_spell["invisibility"] == "trick_uses"
    assert resource_by_spell["find_traps"] in {"trick_uses", "instinct"}
    assert resource_by_spell["goodberry"] == "instinct"


def test_level_three_cards_receive_matching_features_spells_and_pools() -> None:
    level_three = _actors_at_level(3)

    assert {"action_surge", "cunning_action"} <= {
        feature.feature_id for feature in level_three["brakka"].features
    }
    assert {pool.id for pool in level_three["garran"].resource_pools} >= {
        "tactics_uses"
    }
    assert {pool.id for pool in level_three["brakka"].resource_pools} >= {
        "ferocity_uses"
    }

    expected_spells = {
        "garran": {"command", "shield_of_faith", "heroism", "warding_bond"},
        "brakka": {"false_life", "thunderwave"},
        "mira": {"invisibility", "find_traps", "vicious_mockery", "mirror_image"},
        "dagna": {"sacred_flame", "healing_word", "bless", "sanctuary", "guiding_bolt", "aid", "lesser_restoration", "warding_bond"},
        "lorian": {"vicious_mockery", "thunderwave", "healing_word", "faerie_fire", "heroism", "hideous_laughter"},
        "nimra": {"ray_of_frost", "grease", "shield", "sleep", "fog_cloud", "web", "hold_person", "misty_step", "shatter"},
        "erynd": {"hunters_mark", "goodberry", "find_traps", "misty_step", "spike_growth", "see_invisibility"},
    }
    for actor_id, spell_ids in expected_spells.items():
        assert spell_ids <= set(level_three[actor_id].spell_ids)

    custom_resources = {
        "garran": ("tactics_uses", 3),
        "brakka": ("ferocity_uses", 2),
        "mira": ("trick_uses", 3),
        "erynd": ("instinct", 3),
    }
    for actor_id, (pool_id, maximum) in custom_resources.items():
        pool = next(
            pool for pool in level_three[actor_id].resource_pools if pool.id == pool_id
        )
        assert (pool.current, pool.maximum, pool.recovery.value) == (
            maximum,
            maximum,
            "long_rest",
        )


def test_level_three_starters_get_primary_boost_and_only_their_card_deck_access() -> None:
    actors = _actors()
    expected_scores = {
        "garran": ("strength", 18),
        "brakka": ("strength", 19),
        "mira": ("dexterity", 19),
        "dagna": ("wisdom", 18),
        "lorian": ("charisma", 19),
        "nimra": ("intelligence", 19),
        "erynd": ("dexterity", 19),
    }
    expected_access = {
        "garran": {"command", "shield_of_faith", "heroism", "warding_bond"},
        "brakka": {"false_life", "thunderwave"},
        "mira": {"invisibility", "find_traps", "vicious_mockery", "mirror_image"},
        "dagna": {"sacred_flame", "healing_word", "bless", "sanctuary", "guiding_bolt", "aid", "lesser_restoration", "warding_bond"},
        "lorian": {"vicious_mockery", "thunderwave", "healing_word", "faerie_fire", "heroism", "hideous_laughter"},
        "nimra": {"ray_of_frost", "grease", "shield", "sleep", "fog_cloud", "web", "hold_person", "misty_step", "shatter"},
        "erynd": {"hunters_mark", "goodberry", "find_traps", "misty_step", "spike_growth", "see_invisibility"},
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


def test_boardgame_primary_boost_is_idempotent() -> None:
    actor = _actors()["mira"]
    reapplied = apply_boardgame_archetype(actor)

    assert reapplied.ability_scores.dexterity == 19
    assert sum(
        feature.feature_id == "boardgame_level_3_ability_boost"
        for feature in reapplied.features
    ) == 1
