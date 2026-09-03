import pytest

from dnd_board_game.combat import CombatResolutionStage
from dnd_board_game.physical_cards import (
    CARD_ACTION_CATALOG,
    CHARACTER_DECKS,
    CardPhase,
    CardTriggerWindow,
    CombatCardRoute,
    DecisionCardActionKind,
    card_action_definition,
    validate_card_phase,
)


def test_catalog_covers_every_non_universal_character_card() -> None:
    cards = {
        (card.source_id, card.kind)
        for deck in CHARACTER_DECKS.values()
        for card in deck.action_cards
        if card.kind != DecisionCardActionKind.UNIVERSAL.value
    }

    assert len(cards) == 180
    assert "basic_attack" not in CARD_ACTION_CATALOG
    assert {source_id for source_id, _kind in cards} <= set(CARD_ACTION_CATALOG)
    for source_id, kind in cards:
        assert card_action_definition(
            source_id,
            qr_kind=DecisionCardActionKind(kind),
        ).source_id == source_id


def test_catalog_phase_totals_match_reviewed_table() -> None:
    assert sum(
        definition.phase is CardPhase.COMBAT
        for definition in CARD_ACTION_CATALOG.values()
    ) == 153
    assert sum(
        definition.phase is CardPhase.EXPLORATION
        for definition in CARD_ACTION_CATALOG.values()
    ) == 52
    assert sum(
        definition.phase is CardPhase.BOTH
        for definition in CARD_ACTION_CATALOG.values()
    ) == 1
    assert sum(
        definition.phase is CardPhase.REMOVED
        for definition in CARD_ACTION_CATALOG.values()
    ) == 9


def test_retired_basic_attack_card_is_not_scanner_playable() -> None:
    with pytest.raises(ValueError, match="zatwierdzonego katalogu"):
        card_action_definition(
            "basic_attack",
            qr_kind=DecisionCardActionKind.ATTACK,
        )


def test_prototype_cards_expose_precise_trigger_and_toggle_contracts() -> None:
    rage = card_action_definition("rage")
    cutting_words = card_action_definition("cutting_words")
    guidance = card_action_definition("guidance")
    alarm = card_action_definition("alarm")

    assert rage.toggle is True
    assert rage.effect_type == "toggle_status"
    assert cutting_words.trigger_windows == (
        CardTriggerWindow.ATTACK_ROLL_REVEALED,
        CardTriggerWindow.DAMAGE_ROLL_REVEALED,
    )
    assert guidance.trigger_windows == (
        CardTriggerWindow.BEFORE_EXPLORATION_CHECK,
    )
    assert alarm.trigger_windows == (CardTriggerWindow.SHORT_REST_PREVIEW,)
    assert CardTriggerWindow.ATTACK_ROLL_REVEALED.value == (
        CombatResolutionStage.ATTACK_ROLL_REVEALED.value
    )
    assert CardTriggerWindow.DAMAGE_ROLL_REVEALED.value == (
        CombatResolutionStage.DAMAGE_ROLL_REVEALED.value
    )


def test_second_class_feature_cards_have_executable_contracts() -> None:
    expected = {
        "turn_undead": "area_wisdom_save_turn_undead",
        "wild_shape": "choose_combat_beast_form",
        "cunning_action": "choose_bonus_action_mobility",
        "pact_of_the_blade": "summon_selected_pact_weapon",
        "metamagic_careful": "modify_prepared_spell_careful",
        "metamagic_distant": "modify_prepared_spell_range",
        "metamagic_extended": "modify_prepared_spell_duration",
        "metamagic_heightened": "modify_prepared_spell_save",
        "metamagic_quickened": "modify_prepared_spell_action_cost",
        "metamagic_twinned": "modify_prepared_single_target_spell",
    }

    assert {
        source_id: card_action_definition(source_id).effect_type
        for source_id in expected
    } == expected
    wild_shape = card_action_definition("wild_shape")
    assert wild_shape.toggle is True
    empowered = card_action_definition("metamagic_empowered")
    assert empowered.trigger_windows == (
        CardTriggerWindow.DAMAGE_ROLL_REVEALED,
    )


def test_first_combat_spell_batch_uses_shared_runtime_routes() -> None:
    expected_routes = {
        "magic_missile": CombatCardRoute.COMBAT_ACTION,
        "fire_bolt": CombatCardRoute.ATTACK_SOURCE,
        "eldritch_blast": CombatCardRoute.ATTACK_SOURCE,
        "sacred_flame": CombatCardRoute.ATTACK_SOURCE,
        "guiding_bolt": CombatCardRoute.ATTACK_SOURCE,
        "cure_wounds": CombatCardRoute.HEALING_SOURCE,
        "healing_word": CombatCardRoute.HEALING_SOURCE,
        "bless": CombatCardRoute.COMBAT_ACTION,
        "shield_of_faith": CombatCardRoute.COMBAT_ACTION,
        "shield": CombatCardRoute.REACTION,
        "misty_step": CombatCardRoute.COMBAT_ACTION,
        "sleep": CombatCardRoute.COMBAT_ACTION,
        "hold_person": CombatCardRoute.COMBAT_ACTION,
        "thunderwave": CombatCardRoute.ATTACK_SOURCE,
        "spiritual_weapon": CombatCardRoute.COMBAT_ACTION,
    }

    assert {
        source_id: card_action_definition(source_id).combat_route
        for source_id in expected_routes
    } == expected_routes
    assert card_action_definition("shield").trigger_windows == (
        CardTriggerWindow.ATTACK_ROLL_REVEALED,
    )
    assert all(
        card_action_definition(source_id).effect_type != "legacy_action"
        for source_id in expected_routes
    )


def test_second_combat_spell_batch_uses_shared_runtime_routes() -> None:
    attack_sources = {
        "acid_arrow",
        "acid_splash",
        "burning_hands",
        "chill_touch",
        "inflict_wounds",
        "poison_spray",
        "ray_of_frost",
        "shatter",
        "shocking_grasp",
    }
    combat_actions = {
        "scorching_ray",
        "entangle",
        "grease",
        "web",
        "faerie_fire",
        "fog_cloud",
    }

    assert all(
        card_action_definition(source_id).combat_route
        is CombatCardRoute.ATTACK_SOURCE
        for source_id in attack_sources
    )
    assert all(
        card_action_definition(source_id).combat_route
        is CombatCardRoute.COMBAT_ACTION
        for source_id in combat_actions
    )
    assert all(
        card_action_definition(source_id).effect_type != "legacy_action"
        for source_id in attack_sources | combat_actions
    )


def test_third_combat_spell_batch_uses_support_and_reaction_routes() -> None:
    combat_actions = {
        "aid",
        "barkskin",
        "blur",
        "darkness",
        "darkvision",
        "false_life",
        "heroism",
        "lesser_restoration",
        "mage_armor",
        "mirror_image",
        "protection_from_evil_and_good",
        "protection_from_poison",
        "sanctuary",
        "see_invisibility",
        "divine_care_aura",
        "healing_grace_aura",
    }

    assert all(
        card_action_definition(source_id).combat_route
        is CombatCardRoute.COMBAT_ACTION
        for source_id in combat_actions
    )
    rebuke = card_action_definition("hellish_rebuke")
    assert rebuke.combat_route is CombatCardRoute.REACTION
    assert rebuke.trigger_windows == (CardTriggerWindow.AFTER_DAMAGE_APPLIED,)
    assert all(
        card_action_definition(source_id).effect_type != "legacy_action"
        for source_id in combat_actions | {"hellish_rebuke"}
    )


def test_fourth_combat_spell_batch_uses_debuff_and_persistent_routes() -> None:
    attack_sources = {"ray_of_enfeeblement", "vicious_mockery"}
    combat_actions = {
        "bane",
        "blindness_deafness",
        "command",
        "color_spray",
        "hideous_laughter",
        "heat_metal",
        "moonbeam",
        "flaming_sphere",
        "spike_growth",
        "silence",
        "gust_of_wind",
        "flame_blade",
        "hunters_mark",
    }

    assert all(
        card_action_definition(source_id).combat_route
        is CombatCardRoute.ATTACK_SOURCE
        for source_id in attack_sources
    )
    assert all(
        card_action_definition(source_id).combat_route
        is CombatCardRoute.COMBAT_ACTION
        for source_id in combat_actions
    )
    assert card_action_definition("moonbeam").targeting.endswith("on_rescan")
    assert card_action_definition("flaming_sphere").targeting.endswith(
        "on_rescan"
    )


def test_fifth_combat_spell_batch_uses_buff_and_utility_routes() -> None:
    combat_actions = {
        "divine_favor",
        "enlarge_reduce",
        "expeditious_retreat",
        "levitate",
        "magic_weapon",
        "shillelagh",
        "true_strike",
        "resistance",
        "warding_bond",
        "find_familiar",
        "find_traps",
        "goodberry",
        "prayer_of_healing",
        "spare_the_dying",
    }

    assert all(
        card_action_definition(source_id).combat_route
        is CombatCardRoute.COMBAT_ACTION
        for source_id in combat_actions
    )
    assert (
        card_action_definition("produce_flame").combat_route
        is CombatCardRoute.ATTACK_SOURCE
    )
    assert all(
        card_action_definition(source_id).effect_type != "legacy_action"
        for source_id in combat_actions | {"produce_flame"}
    )


def test_first_martial_class_feature_batch_has_precise_card_contracts() -> None:
    source_ids = {
        "action_surge",
        "second_wind",
        "rage",
        "reckless_attack",
        "powerful_strike",
        "shoulder_check",
        "hard_as_rock",
        "acceleration",
        "deafening_roar",
        "martial_arts_strike",
        "flurry_of_blows",
        "patient_defense",
        "step_of_the_wind",
        "deflect_missiles",
        "lay_on_hands",
        "divine_smite",
        "channel_divinity_sacred_weapon",
        "channel_divinity_turn_the_unholy",
    }

    assert all(
        card_action_definition(source_id).effect_type != "legacy_action"
        for source_id in source_ids
    )
    assert card_action_definition("martial_arts_strike").action_id == (
        "martial_arts_bonus_attack"
    )
    assert card_action_definition("channel_divinity_sacred_weapon").action_id == (
        "sacred_weapon"
    )
    assert card_action_definition("divine_smite").trigger_windows == (
        CardTriggerWindow.ATTACK_ROLL_REVEALED,
    )
    assert card_action_definition("deflect_missiles").trigger_windows == (
        CardTriggerWindow.AFTER_DAMAGE_APPLIED,
    )


def test_mira_redesign_cards_have_explicit_runtime_contracts() -> None:
    expected_effects = {
        "instinctive_dodge": "stealth_reaction_spend_trick_single_attack_disadvantage",
        "smoke_screen": "spend_trick_move_then_forced_hide",
        "hamstring_cut": "flanking_melee_attack_persistent_half_speed",
        "piercing_attack": "flanking_melee_attack_then_collinear_attack",
        "guard_vault": "melee_attack_then_move_behind_target",
        "blade_mistress": "hidden_throwing_knife_bleeding_rider",
        "combat_trap_detection": "physical_perception_reveal_traps_in_radius",
    }

    assert {
        source_id: card_action_definition(source_id).effect_type
        for source_id in expected_effects
    } == expected_effects
    dodge = card_action_definition("instinctive_dodge")
    assert dodge.combat_route is CombatCardRoute.REACTION
    assert dodge.trigger_windows == (CardTriggerWindow.ATTACK_ROLL_REVEALED,)
    assert card_action_definition("combat_trap_detection").targeting == (
        "self_radius_45"
    )
    assert card_action_definition("break_in").phase is CardPhase.REMOVED


def test_removed_and_wrong_phase_cards_are_rejected() -> None:
    with pytest.raises(ValueError, match="wycofana"):
        validate_card_phase(
            card_action_definition("animal_messenger"),
            CardPhase.EXPLORATION,
        )
    with pytest.raises(ValueError, match="wyłącznie podczas walki"):
        validate_card_phase(
            card_action_definition("invisibility"),
            CardPhase.EXPLORATION,
        )
    with pytest.raises(ValueError, match="Rodzaj kodu QR"):
        card_action_definition(
            "rage",
            qr_kind=DecisionCardActionKind.SPELL,
        )
