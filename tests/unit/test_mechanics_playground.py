import json
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.actors import (
    Faction,
    PreparableSpell,
)
from dnd_board_game.combat import (
    ActionUse,
    DamageComponentInput,
    DamageType,
    HiddenState,
    ReactionKind,
    ReactionOption,
    ReactionWindow,
    SpellSlotState,
    apply_damage_result,
    replace_actor,
    resolve_damage,
    resolve_actor_saving_throw,
)
from dnd_board_game.character_creation import (
    all_default_character_drafts,
    apply_boardgame_archetype,
    build_character,
    default_character_drafts,
    load_character_catalog,
    load_character_resources,
)
from dnd_board_game.character_creation.srd_manifest import SRD_SPELL_IDS_BY_LEVEL
from dnd_board_game.exploration import (
    CheckAggregation,
    CheckParticipants,
    ConsequenceTarget,
    ExplorationCheckPlan,
    ExplorationHazard,
    ExplorationHazardDamage,
    ExplorationHazardTrigger,
    PartyPosition,
)
from dnd_board_game.inventory import InventoryItem, SpellcastingFocusKind
from dnd_board_game.rules import (
    RollMode,
    SaveDamageOnSuccess,
    SavingThrowRequest,
    SpellAccessKind,
    SpellAccessProfile,
)
from dnd_board_game.scenarios import load_scenario
from dnd_board_game.scenarios.loader import _parse_spell_definition
from dnd_board_game.ui.exploration_app import (
    ExplorationUiSession,
    PendingInteraction,
    PendingKind,
    PendingStage,
    UiFlowStage,
)
from dnd_board_game.ui.routes import create_app
from dnd_board_game.ui.playground_cases import load_playground_audit_registry
from dnd_board_game.world import Coordinate


SCENARIO_PATH = "content/scenarios/mechanics_playground/scenario.json"


def _session(tmp_path) -> ExplorationUiSession:
    return ExplorationUiSession(
        SCENARIO_PATH,
        session_id="mechanics_playground_test",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
    )


def _start_configured_playground_encounter(session: ExplorationUiSession) -> None:
    session.start_encounter_setup()
    while (
        session.encounter_setup_flow is not None
        and not session.encounter_setup_flow.completed
    ):
        if session.encounter_setup_flow.is_player_start_step:
            position = session.encounter_setup_flow.remaining_player_start_positions()[0]
            session.assign_encounter_player_start_position(position)
        else:
            session.confirm_encounter_setup_step()
    session.start_encounter_initiative()
    prompt_count = len(session.encounter_initiative_flow.prompts)
    for index in range(prompt_count):
        session.submit_encounter_initiative_roll(20 - index)


def _start_board_weapon_attack(
    session: ExplorationUiSession,
    target_position: Coordinate,
) -> dict[str, object]:
    """Select an ordinary attack from the target field, without an action card."""

    payload = session.select_board_position(target_position)
    if payload["combat"]["pending_player_attack"] is not None:
        return payload
    menu = session.pending_combat_context_menu
    assert menu is not None
    option = next(
        candidate
        for candidate in menu.options
        if candidate.action.value == "attack"
    )
    return session.confirm_combat_context_menu(option.id)
    assert session.combat_state is not None


def test_mechanics_playground_loads_all_training_modules() -> None:
    loaded = load_scenario(SCENARIO_PATH)

    assert loaded.definition.id == "mechanics_playground"
    assert {zone.id for zone in loaded.definition.exploration_zones} == {
        "control_room",
        "combat_arena",
        "spell_lab",
        "exploration_course",
        "social_lab",
        "rest_station",
    }
    assert any(
        point.npc_interaction is not None
        for point in loaded.definition.exploration_points
    )
    assert loaded.definition.exploration_encounter_triggers[0].id == "playground_trial"


def test_playground_audit_cases_are_replayable_and_report_progress() -> None:
    registry = load_playground_audit_registry()
    payload = registry.as_payload()

    assert payload["inventory"]["total"] == 236
    assert payload["progress"] == {
        "tested": 177,
        "skipped": 59,
        "resolved": 236,
        "total": 236,
        "percent": 100.0,
    }
    assert {case["id"] for case in payload["cases"]} == {
        "spell_invisibility",
        "spell_gentle_repose",
        "spell_feather_fall",
        "spell_mirror_image",
        "spell_sanctuary",
        "spell_levitate",
        "spell_locate_animals_or_plants",
        "spell_locate_object",
        "spell_magic_mouth",
        "spell_magic_weapon",
        "spell_misty_step",
        "spell_moonbeam",
        "spell_pass_without_trace",
        "spell_prayer_of_healing",
        "spell_protection_from_poison",
        "spell_ray_of_enfeeblement",
        "spell_rope_trick",
        "spell_scorching_ray",
        "spell_see_invisibility",
        "spell_shatter",
        "spell_silence",
        "spell_spider_climb",
        "spell_spike_growth",
        "spell_spiritual_weapon",
        "spell_suggestion",
        "spell_warding_bond",
        "spell_web",
        "spell_zone_of_truth",
        "spell_acid_splash",
        "spell_chill_touch",
        "spell_dancing_lights",
        "spell_druidcraft",
        "spell_eldritch_blast",
        "spell_fire_bolt",
        "spell_guidance",
        "spell_light",
        "spell_mage_hand",
        "spell_mending",
        "spell_message",
        "spell_minor_illusion",
        "spell_poison_spray",
        "spell_prestidigitation",
        "spell_produce_flame",
        "spell_ray_of_frost",
        "spell_resistance",
        "spell_sacred_flame",
        "spell_shillelagh",
        "spell_shocking_grasp",
        "spell_spare_the_dying",
        "spell_thaumaturgy",
        "spell_true_strike",
        "spell_vicious_mockery",
        "species_human_versatility",
        "species_high_elf_darkvision",
        "species_high_elf_fey_ancestry",
        "species_high_elf_trance",
        "species_high_elf_weapon_training",
        "species_high_elf_cantrip",
        "species_hill_dwarf_darkvision",
        "species_dwarf_resilience",
        "species_dwarf_speed",
        "species_dwarf_stonecunning",
        "species_hill_dwarf_toughness",
        "species_halfling_lucky",
        "species_halfling_brave",
        "species_halfling_nimbleness",
        "species_lightfoot_naturally_stealthy",
        "species_dragonborn_breath_weapon",
        "species_dragonborn_ancestry",
        "species_rock_gnome_darkvision",
        "species_gnome_cunning",
        "species_rock_gnome_artificers_lore",
        "species_rock_gnome_tinker",
        "species_half_elf_elven_traits",
        "species_half_elf_skill_versatility",
        "species_half_orc_darkvision",
        "species_half_orc_relentless_endurance",
        "species_half_orc_savage_attacks",
        "species_tiefling_darkvision",
        "species_tiefling_hellish_resistance",
        "species_tiefling_infernal_legacy",
        "class_barbarian_rage",
        "class_barbarian_unarmored_defense",
        "class_barbarian_reckless_attack",
        "class_barbarian_danger_sense",
        "class_berserker_frenzy",
        "class_bard_spellcasting",
        "class_bard_bardic_inspiration",
        "class_bard_jack_of_all_trades",
        "class_bard_song_of_rest",
        "class_lore_bonus_proficiencies",
        "class_lore_cutting_words",
        "class_cleric_spellcasting_life_domain",
        "class_life_disciple_of_life",
        "class_cleric_turn_undead",
        "class_life_preserve_life",
        "class_druid_druidic",
        "class_druid_spellcasting",
        "class_druid_wild_shape",
        "class_land_bonus_cantrip",
        "class_land_natural_recovery",
        "class_land_terrain_spells",
        "class_fighter_fighting_style",
        "class_fighter_archery",
        "class_fighter_defense",
        "class_fighter_dueling",
        "class_fighter_two_weapon_fighting",
        "class_fighter_second_wind",
        "class_fighter_action_surge",
        "class_champion_improved_critical",
        "class_monk_unarmored_defense",
        "class_monk_martial_arts",
        "class_monk_ki_actions",
        "class_monk_unarmored_movement",
        "class_monk_deflect_missiles",
        "class_open_hand_technique",
        "class_paladin_divine_sense",
        "class_paladin_lay_on_hands",
        "class_paladin_style_spellcasting",
        "class_paladin_divine_smite",
        "class_paladin_divine_health",
        "class_devotion_sacred_weapon",
        "class_devotion_turn_unholy",
        "class_ranger_favored_enemy",
        "class_ranger_natural_explorer",
        "class_ranger_style_spellcasting",
        "class_ranger_primeval_awareness",
        "class_hunter_colossus_slayer",
        "class_hunter_giant_killer",
        "class_hunter_horde_breaker",
        "class_rogue_expertise",
        "class_rogue_sneak_attack",
        "class_rogue_thieves_cant",
        "class_rogue_cunning_action",
        "class_thief_fast_hands",
        "class_thief_second_story_work",
        "class_sorcerer_spellcasting_draconic_resilience",
        "class_sorcerer_font_of_magic",
        "class_metamagic_careful",
        "class_metamagic_distant",
        "class_metamagic_empowered",
        "class_metamagic_extended",
        "class_metamagic_heightened",
        "class_metamagic_quickened",
        "class_metamagic_subtle",
        "class_metamagic_twinned",
        "class_warlock_pact_magic",
        "class_fiend_dark_ones_blessing",
        "class_warlock_blast_invocations",
        "class_warlock_at_will_invocations",
        "class_warlock_beguiling_influence",
        "class_warlock_devils_sight",
        "class_warlock_pact_blade",
        "class_warlock_pact_chain",
        "class_warlock_pact_tome",
        "class_wizard_spellbook",
        "class_wizard_arcane_recovery",
        "class_evocation_savant",
        "class_evocation_sculpt_spells",
        "mechanic_flanking",
        "mechanic_spell_effect_consumers",
    } | {
        f"spell_{spell_id}"
        for spell_ids in SRD_SPELL_IDS_BY_LEVEL.values()
        for spell_id in spell_ids
    }
    assert all(case["manual_steps"] for case in payload["cases"])
    assert all(case["automatic_tests"] for case in payload["cases"])


def test_playground_configures_only_requested_dummies(tmp_path) -> None:
    session = _session(tmp_path)

    payload = session.configure_playground_trial(
        dummy_count=2,
        armor_class=18,
        hit_points=50,
        speed_feet=0,
        ability_score=14,
        creature_type="undead",
        affinity="vulnerability",
        damage_type="radiant",
        condition_immunity="poisoned",
    )
    assert payload["current_zone"]["id"] == "combat_arena"
    assert payload["pending_encounter"]["trigger_id"] == "playground_trial"

    session.start_encounter_setup()
    encounter = session.encounter_setup_flow.encounter
    enemies = tuple(actor for actor in encounter.actors if actor.faction == Faction.ENEMY)

    assert len(enemies) == 2
    assert all(actor.ac == 18 and actor.max_hp == 50 for actor in enemies)
    assert all(actor.speed_feet == 0 and actor.creature_type == "undead" for actor in enemies)
    assert all(actor.ability_scores.wisdom == 14 for actor in enemies)
    assert all(
        actor.damage_affinities.vulnerabilities == (DamageType.RADIANT,)
        for actor in enemies
    )
    assert all(actor.condition_immunities == ("poisoned",) for actor in enemies)


def test_playground_arena_scans_a_real_starting_card_for_all_seven_archetypes(
    tmp_path,
) -> None:
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    cases = {
        "barbarian": ("feature", "rage", "resolved"),
        "bard": ("feature", "bardic_inspiration", "select_board_target"),
        "cleric": ("spell", "sacred_flame", "select_board_target"),
        "fighter": ("feature", "second_wind", "enter_feature_value"),
        "ranger": ("spell", "hunters_mark", "select_board_target"),
        "rogue": ("board", "", "confirm_attack"),
        "wizard": ("spell", "ray_of_frost", "select_board_target"),
    }
    results: dict[str, str] = {}

    for class_id, (kind, source_id, expected_next_step) in cases.items():
        session = ExplorationUiSession(
            SCENARIO_PATH,
            session_id=f"arena_class_card_{class_id}",
            observation_dir=tmp_path / class_id / "observations",
            save_dir=tmp_path / class_id / "saves",
        )
        draft = next(
            candidate
            for candidate in default_character_drafts()
            if candidate.class_id == class_id
        )
        actor = apply_boardgame_archetype(
            build_character(draft, catalog, resources).actor,
            spell_definitions=tuple(spell for _, spell in resources.spells),
        )
        if kind == "spell":
            actor = replace(
                actor,
                inventory=tuple(
                    replace(item, equipped=False, held_in=())
                    if item.kind == "weapon"
                    else item
                    for item in actor.inventory
                ),
            )
        party = (actor,)
        if class_id == "bard":
            ally_draft = next(
                candidate
                for candidate in default_character_drafts()
                if candidate.class_id == "fighter"
            )
            party = (actor, build_character(ally_draft, catalog, resources).actor)
        session.configure_custom_party(party)
        session.configure_playground_trial(
            dummy_count=1,
            armor_class=12,
            hit_points=20,
            speed_feet=0,
            ability_score=10,
            creature_type="construct",
            affinity="none",
            damage_type="slashing",
        )
        _start_configured_playground_encounter(session)
        if class_id in {"fighter", "paladin"}:
            current = session.combat_state.initiative_order.current_actor
            session.combat_state = replace_actor(
                session.combat_state,
                replace(current, hp=max(1, current.max_hp - 2)),
            )
        client = create_app(
            session,
            character_dir=tmp_path / class_id / "characters",
        ).test_client()

        if kind == "board":
            current = session.combat_state.initiative_order.current_actor
            dummy = next(
                candidate
                for candidate in session.combat_state.actors
                if candidate.faction == Faction.ENEMY
            )
            dummy = replace(
                dummy,
                position=Coordinate(current.position.col + 1, current.position.row),
            )
            session.combat_state = replace_actor(session.combat_state, dummy)
            payload = _start_board_weapon_attack(session, dummy.position)
            assert payload["combat"]["pending_player_attack"]["stage"] == expected_next_step
            results[class_id] = expected_next_step
            continue

        response = client.post(
            "/api/physical-cards/scan",
            json={
                "payload": f"dndbg:v2:action:{kind}:{source_id}:{actor.id}",
            },
        )

        assert response.status_code == 200, (class_id, response.get_json())
        payload = response.get_json()
        assert payload["feedback"]["next_step"] == expected_next_step, (
            class_id,
            payload,
        )
        assert "resources" in payload["feedback"]
        results[class_id] = payload["feedback"]["next_step"]

    assert set(results) == set(cases)


def test_playground_arena_scans_new_martial_archetype_cards(tmp_path) -> None:
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    cases = (
        ("fighter", "garran", "defensive_stance", "resolved"),
        ("barbarian", "brakka", "reckless_attack", "resolved"),
        ("rogue", "mira", "instinctive_dodge", "resolved"),
        ("ranger", "erynd", "cunning_action", "enter_feature_value"),
        ("rogue", "mira", "exploit_weakness", "resolved"),
        ("ranger", "erynd", "patient_shot", "resolved"),
    )

    for class_id, actor_id, source_id, expected_next_step in cases:
        session = ExplorationUiSession(
            SCENARIO_PATH,
            session_id=f"arena_new_martial_card_{actor_id}_{source_id}",
            observation_dir=tmp_path / actor_id / source_id / "observations",
            save_dir=tmp_path / actor_id / source_id / "saves",
        )
        draft = next(
            candidate
            for candidate in default_character_drafts()
            if candidate.class_id == class_id
        )
        actor = apply_boardgame_archetype(
            build_character(draft, catalog, resources).actor,
            spell_definitions=tuple(spell for _, spell in resources.spells),
        )
        session.configure_custom_party((actor,))
        session.configure_playground_trial(
            dummy_count=1,
            armor_class=12,
            hit_points=20,
            speed_feet=0,
            ability_score=10,
            creature_type="construct",
            affinity="none",
            damage_type="slashing",
        )
        _start_configured_playground_encounter(session)
        client = create_app(
            session,
            character_dir=tmp_path / actor_id / "characters",
        ).test_client()

        response = client.post(
            "/api/physical-cards/scan",
            json={
                "payload": f"dndbg:v2:action:feature:{source_id}:{actor_id}",
            },
        )

        assert response.status_code == 200, (actor_id, response.get_json())
        payload = response.get_json()
        assert payload["feedback"]["next_step"] == expected_next_step
        current = payload["state"]["combat"]["current_actor"]
        if source_id in {"defensive_stance", "instinctive_dodge"}:
            resource_id = f"{source_id}_uses"
            pool = next(
                item for item in current["resource_pools"] if item["id"] == resource_id
            )
            assert pool["current"] == 0
        if source_id in {"exploit_weakness", "patient_shot"}:
            resource_id = (
                "trick_uses" if source_id == "exploit_weakness" else "instinct"
            )
            pool = next(
                item for item in current["resource_pools"] if item["id"] == resource_id
            )
            assert pool["current"] == 2
            assert any(
                effect["kind"] == "next_attack_advantage"
                for effect in payload["state"]["combat"]["active_effects"]
            )


def test_playground_arena_scans_new_mira_and_erynd_resource_cards(tmp_path) -> None:
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    cases = {
        "rogue": ("mira", "invisibility", "select_board_target", "trick_uses"),
        "ranger": ("erynd", "goodberry", "confirm_action", "instinct"),
    }

    for class_id, (actor_id, source_id, expected_next_step, resource_id) in cases.items():
        session = ExplorationUiSession(
            SCENARIO_PATH,
            session_id=f"arena_resource_card_{actor_id}",
            observation_dir=tmp_path / actor_id / "observations",
            save_dir=tmp_path / actor_id / "saves",
        )
        draft = next(
            candidate
            for candidate in default_character_drafts()
            if candidate.class_id == class_id
        )
        actor = apply_boardgame_archetype(
            build_character(draft, catalog, resources).actor,
            spell_definitions=tuple(spell for _, spell in resources.spells),
        )
        actor = replace(
            actor,
            inventory=tuple(
                replace(item, equipped=False, held_in=())
                if item.kind == "weapon"
                else item
                for item in actor.inventory
            ),
        )
        session.configure_custom_party((actor,))
        session.configure_playground_trial(
            dummy_count=1,
            armor_class=12,
            hit_points=20,
            speed_feet=0,
            ability_score=10,
            creature_type="construct",
            affinity="none",
            damage_type="slashing",
        )
        _start_configured_playground_encounter(session)
        client = create_app(
            session,
            character_dir=tmp_path / actor_id / "characters",
        ).test_client()

        response = client.post(
            "/api/physical-cards/scan",
            json={
                "payload": f"dndbg:v2:action:spell:{source_id}:{actor_id}",
            },
        )

        assert response.status_code == 200, (actor_id, response.get_json())
        payload = response.get_json()
        assert payload["feedback"]["next_step"] == expected_next_step
        confirmation = client.post(
            "/api/combat/concentration/confirm",
            json=({"target_id": actor_id} if source_id == "invisibility" else {}),
        )
        assert confirmation.status_code == 200, (actor_id, confirmation.get_json())
        confirmed = confirmation.get_json()
        pool = next(
            item
            for item in confirmed["combat"]["current_actor"]["resource_pools"]
            if item["id"] == resource_id
        )
        assert pool["maximum"] == 3
        assert pool["current"] == pool["maximum"] - 1


def test_playground_arena_spends_new_level_three_tactical_resources(tmp_path) -> None:
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    cases = {
        "fighter": ("garran", "shield_of_faith", "select_board_target", "tactics_uses", 2),
        "barbarian": ("brakka", "false_life", "confirm_action", "ferocity_uses", 1),
    }

    for class_id, (actor_id, source_id, next_step, pool_id, remaining) in cases.items():
        session = ExplorationUiSession(
            SCENARIO_PATH,
            session_id=f"arena_level_three_resource_{actor_id}",
            observation_dir=tmp_path / actor_id / "observations",
            save_dir=tmp_path / actor_id / "saves",
        )
        draft = next(
            candidate
            for candidate in default_character_drafts()
            if candidate.class_id == class_id
        )
        actor = apply_boardgame_archetype(
            replace(build_character(draft, catalog, resources).actor, level=3),
            spell_definitions=tuple(spell for _, spell in resources.spells),
        )
        actor = replace(
            actor,
            inventory=tuple(
                replace(item, equipped=False, held_in=())
                if item.kind == "weapon"
                else item
                for item in actor.inventory
            ),
        )
        session.configure_custom_party((actor,))
        session.configure_playground_trial(
            dummy_count=1,
            armor_class=12,
            hit_points=20,
            speed_feet=0,
            ability_score=10,
            creature_type="construct",
            affinity="none",
            damage_type="slashing",
        )
        _start_configured_playground_encounter(session)
        client = create_app(
            session,
            character_dir=tmp_path / actor_id / "characters",
        ).test_client()

        scanned = client.post(
            "/api/physical-cards/scan",
            json={"payload": f"dndbg:v2:action:spell:{source_id}:{actor_id}"},
        )
        assert scanned.status_code == 200, (actor_id, scanned.get_json())
        assert scanned.get_json()["feedback"]["next_step"] == next_step

        confirmed = client.post(
            "/api/combat/concentration/confirm",
            json=(
                {"target_id": actor_id}
                if next_step == "select_board_target"
                else {"roll_total": 1}
            ),
        )
        assert confirmed.status_code == 200, (actor_id, confirmed.get_json())
        pool = next(
            item
            for item in confirmed.get_json()["combat"]["current_actor"]["resource_pools"]
            if item["id"] == pool_id
        )
        assert pool["current"] == remaining


def test_playground_arena_accepts_nimras_actor_bound_grease_card(tmp_path) -> None:
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = next(
        candidate for candidate in default_character_drafts() if candidate.id == "nimra"
    )
    actor = apply_boardgame_archetype(
        build_character(draft, catalog, resources).actor,
        spell_definitions=tuple(spell for _, spell in resources.spells),
    )
    session = ExplorationUiSession(
        SCENARIO_PATH,
        session_id="arena_nimra_grease_owner",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
    )
    session.configure_custom_party((actor,))
    session.configure_playground_trial(
        dummy_count=1,
        armor_class=12,
        hit_points=20,
        speed_feet=0,
        ability_score=10,
        creature_type="construct",
        affinity="none",
        damage_type="slashing",
    )
    _start_configured_playground_encounter(session)
    client = create_app(session, character_dir=tmp_path / "characters").test_client()

    response = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v2:action:spell:grease:nimra"},
    )

    assert response.status_code == 200, response.get_json()
    assert response.get_json()["feedback"]["next_step"] == "select_board_target"


def test_playground_reaction_reminder_accepts_non_active_owners_card(tmp_path) -> None:
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = next(
        candidate for candidate in default_character_drafts() if candidate.id == "lorian"
    )
    lorian = apply_boardgame_archetype(
        build_character(draft, catalog, resources).actor,
        spell_definitions=tuple(spell for _, spell in resources.spells),
    )
    session = _session(tmp_path)
    session.configure_custom_party((lorian,))
    session.configure_playground_trial(
        dummy_count=1,
        armor_class=12,
        hit_points=20,
        speed_feet=0,
        ability_score=10,
        creature_type="construct",
        affinity="none",
        damage_type="slashing",
    )
    _start_configured_playground_encounter(session)
    enemy = next(
        actor for actor in session.combat_state.actors if actor.faction == Faction.ENEMY
    )
    enemy_index = next(
        index
        for index, entry in enumerate(session.combat_state.initiative_order.entries)
        if entry.actor.id == enemy.id
    )
    session.combat_state = replace(
        session.combat_state,
        initiative_order=replace(
            session.combat_state.initiative_order,
            current_index=enemy_index,
        ),
    )
    session.pending_reaction_window = ReactionWindow(
        interrupted_actor_id=str(enemy.id),
        trigger_event="attack_roll_revealed",
        options=(
            ReactionOption(
                id=f"cutting-words:{lorian.id}:{enemy.id}",
                kind=ReactionKind.CUTTING_WORDS,
                reactor_actor_id=str(lorian.id),
                target_actor_id=str(enemy.id),
                trigger_event="attack_roll_revealed",
                effect_id="cutting_words",
                label="Cięta riposta",
                value=6,
            ),
        ),
    )
    client = create_app(session, character_dir=tmp_path / "characters").test_client()

    reminder = session.state_payload()["combat"]["card_reminders"]
    response = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v2:action:feature:cutting_words:lorian"},
    )

    assert len(reminder) == 1
    assert {
        "source_id": "cutting_words",
        "label": "Cięta riposta",
        "owner_actor_id": "lorian",
        "owner_actor_name": lorian.name,
        "trigger_window": "attack_roll_revealed",
    }.items() <= reminder[0].items()
    assert "Inspir" in str(reminder[0].get("resource_note"))
    assert response.status_code == 200, response.get_json()
    assert "Wpisz wynik kości Inspiracji" in response.get_json()["feedback"]["message"]


def test_playground_reset_restores_trial_and_keeps_configuration(tmp_path) -> None:
    session = _session(tmp_path)
    session.configure_playground_trial(
        dummy_count=4,
        armor_class=15,
        hit_points=30,
        speed_feet=10,
        ability_score=10,
        creature_type="construct",
        affinity="resistance",
        damage_type="fire",
    )
    session.start_encounter_setup()

    payload = session.reset_playground_trial()

    assert payload["pending_encounter"] is None
    assert payload["encounter_setup"] is None
    assert payload["combat"] is None
    assert payload["current_zone"]["id"] == "combat_arena"
    assert payload["playground"]["config"]["dummy_count"] == 4


def test_playground_arena_routes_rage_and_frenzy_physical_cards(tmp_path) -> None:
    session = _session(tmp_path)
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = next(
        draft
        for draft in default_character_drafts()
        if draft.class_id == "barbarian"
    )
    barbarian = apply_boardgame_archetype(
        build_character(draft, catalog, resources).actor,
        spell_definitions=tuple(spell for _, spell in resources.spells),
    )
    session.configure_custom_party((barbarian,))
    session.configure_playground_trial(
        dummy_count=1,
        armor_class=12,
        hit_points=20,
        speed_feet=0,
        ability_score=10,
        creature_type="construct",
        affinity="none",
        damage_type="slashing",
    )
    session.start_encounter_setup()
    while (
        session.encounter_setup_flow is not None
        and not session.encounter_setup_flow.completed
    ):
        if session.encounter_setup_flow.is_player_start_step:
            position = session.encounter_setup_flow.remaining_player_start_positions()[0]
            session.assign_encounter_player_start_position(position)
        else:
            session.confirm_encounter_setup_step()
    session.start_encounter_initiative()
    session.submit_encounter_initiative_roll(20)
    client = create_app(
        session,
        character_dir=tmp_path / "characters",
    ).test_client()

    frenzy_without_rage = client.post(
        "/api/physical-cards/scan",
        json={"payload": f"dndbg:v2:action:feature:frenzy:{barbarian.id}"},
    )
    rage = client.post(
        "/api/physical-cards/scan",
        json={"payload": f"dndbg:v2:action:feature:rage:{barbarian.id}"},
    )
    reckless = client.post(
        "/api/physical-cards/scan",
        json={"payload": f"dndbg:v2:action:feature:reckless_attack:{barbarian.id}"},
    )
    frenzy = client.post(
        "/api/physical-cards/scan",
        json={"payload": f"dndbg:v2:action:feature:frenzy:{barbarian.id}"},
    )

    assert frenzy_without_rage.status_code == 400
    assert "tylko podczas Rage" in frenzy_without_rage.get_json()["error"]
    assert rage.status_code == 200
    assert frenzy.status_code == 200
    assert reckless.status_code == 200, reckless.get_json()
    assert {
        effect.kind
        for effect in session.active_combat_effects
        if effect.actor_id == str(barbarian.id)
    } >= {"rage", "frenzy", "reckless_attack"}

    current = session.combat_state.initiative_order.current_actor
    dummy = next(
        actor for actor in session.combat_state.actors if actor.faction == Faction.ENEMY
    )
    dummy = replace(
        dummy,
        position=Coordinate(current.position.col + 1, current.position.row),
    )
    session.combat_state = replace_actor(session.combat_state, dummy)

    selected = _start_board_weapon_attack(session, dummy.position)
    assert selected["combat"]["pending_player_attack"]["target"]["id"] == str(dummy.id)
    assert selected["combat"]["pending_player_attack"]["stage"] == "confirm_attack"

    session.confirm_player_attack_target()
    rolled = session.submit_player_attack_roll(natural_roll=20, natural_roll_2=19)
    assert rolled["combat"]["pending_player_attack"]["stage"] == "damage_roll"
    resolved_attack = session.submit_player_damage_roll(damage=6)
    assert resolved_attack["combat"]["pending_player_attack"] is None
    damaged_dummy = next(
        actor
        for actor in resolved_attack["combat"]["actors"]
        if actor["id"] == str(dummy.id)
    )
    assert damaged_dummy["hp"] < damaged_dummy["max_hp"]


def test_playground_arena_routes_fighter_physical_feature_cards(tmp_path) -> None:
    session = _session(tmp_path)
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = next(
        draft
        for draft in default_character_drafts()
        if draft.class_id == "fighter"
    )
    fighter = build_character(
        replace(draft, level=3, selected_subclass_id="champion"),
        catalog,
        resources,
    ).actor
    session.configure_custom_party((fighter,))
    session.configure_playground_trial(
        dummy_count=1,
        armor_class=12,
        hit_points=20,
        speed_feet=0,
        ability_score=10,
        creature_type="construct",
        affinity="none",
        damage_type="slashing",
    )
    _start_configured_playground_encounter(session)
    current = session.combat_state.initiative_order.current_actor
    session.combat_state = replace_actor(
        session.combat_state,
        replace(current, hp=current.max_hp - 8),
    )
    client = create_app(
        session,
        character_dir=tmp_path / "characters",
    ).test_client()

    second_wind = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:feature:second_wind"},
    )

    assert second_wind.status_code == 200
    assert second_wind.get_json()["feedback"]["next_step"] == (
        "enter_feature_value"
    )
    assert second_wind.get_json()["state"]["combat"][
        "physical_feature_prompt"
    ]["die_sides"] == 10
    resolved = client.post(
        "/api/combat/class-feature",
        json={"action_id": "second_wind", "natural_roll": 6},
    )
    assert resolved.status_code == 200
    assert resolved.get_json()["combat"]["physical_feature_prompt"] is None

    session.combat_state = replace(
        session.combat_state,
        turn_action=replace(
            session.combat_state.turn_action,
            action_use=ActionUse.ACTION_USED,
        ),
    )
    surged = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:feature:action_surge"},
    )

    assert surged.status_code == 200
    assert surged.get_json()["state"]["combat"]["turn_action"][
        "action_use"
    ] == "action_available"


def test_playground_arena_routes_monk_ki_and_strike_cards(tmp_path) -> None:
    session = _session(tmp_path)
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = next(
        draft
        for draft in all_default_character_drafts()
        if draft.class_id == "monk"
    )
    monk = build_character(
        replace(
            draft,
            level=3,
            selected_subclass_id="way_of_the_open_hand",
        ),
        catalog,
        resources,
    ).actor
    session.configure_custom_party((monk,))
    session.configure_playground_trial(
        dummy_count=1,
        armor_class=12,
        hit_points=20,
        speed_feet=0,
        ability_score=10,
        creature_type="construct",
        affinity="none",
        damage_type="slashing",
    )
    _start_configured_playground_encounter(session)
    client = create_app(
        session,
        character_dir=tmp_path / "characters",
    ).test_client()

    patient = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:feature:patient_defense"},
    )
    assert patient.status_code == 200
    assert any(
        effect.kind == "dodge_until_next_turn"
        for effect in session.active_combat_effects
    )

    session.combat_state = replace(
        session.combat_state,
        turn_action=replace(
            session.combat_state.turn_action,
            bonus_action_use=ActionUse.ACTION_AVAILABLE,
            attack_action_active=True,
            attacks_used=1,
            attacks_maximum=1,
        ),
    )
    martial = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:feature:martial_arts_strike"},
    )
    assert martial.status_code == 200
    assert martial.get_json()["state"]["combat"]["turn_action"][
        "bonus_attacks_remaining"
    ] == 1

    session.combat_state = replace(
        session.combat_state,
        turn_action=replace(
            session.combat_state.turn_action,
            bonus_action_use=ActionUse.ACTION_AVAILABLE,
            bonus_attacks_remaining=0,
            bonus_attack_source_id="",
            attack_action_active=True,
            attacks_used=1,
            attacks_maximum=1,
        ),
    )
    flurry = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:feature:flurry_of_blows"},
    )
    assert flurry.status_code == 200
    assert flurry.get_json()["state"]["combat"]["turn_action"][
        "bonus_attacks_remaining"
    ] == 2

    outside_window = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:feature:deflect_missiles"},
    )
    assert outside_window.status_code == 400
    assert "wyłącznie po ujawnieniu" in outside_window.get_json()["error"]

    enemy = next(
        actor
        for actor in session.combat_state.actors
        if actor.faction == Faction.ENEMY
    )
    session.pending_reaction_window = ReactionWindow(
        interrupted_actor_id=str(enemy.id),
        trigger_event="hit_by_ranged_weapon_attack",
        options=(
            ReactionOption(
                id="arena-deflect",
                kind=ReactionKind.DEFLECT_MISSILES,
                reactor_actor_id=str(monk.id),
                target_actor_id=str(enemy.id),
                trigger_event="hit_by_ranged_weapon_attack",
                effect_id="deflect_missiles",
                label="Deflect Missiles",
                value=9,
            ),
        ),
    )
    deflect = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:feature:deflect_missiles"},
    )
    assert deflect.status_code == 200
    assert deflect.get_json()["feedback"]["next_step"] == (
        "enter_feature_value"
    )
    assert deflect.get_json()["state"]["combat"]["physical_feature_prompt"][
        "incoming_damage"
    ] == 9


def test_playground_arena_routes_paladin_feature_cards_and_smite_window(
    tmp_path,
) -> None:
    session = _session(tmp_path)
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = next(
        draft
        for draft in all_default_character_drafts()
        if draft.class_id == "paladin"
    )
    paladin = build_character(
        replace(
            draft,
            level=3,
            selected_subclass_id="oath_of_devotion",
            selected_fighting_style_id="defense",
            selected_prepared_spell_ids=(
                "bless",
                "cure_wounds",
                "shield_of_faith",
            ),
        ),
        catalog,
        resources,
    ).actor
    session.configure_custom_party((paladin,))
    session.configure_playground_trial(
        dummy_count=1,
        armor_class=12,
        hit_points=20,
        speed_feet=0,
        ability_score=10,
        creature_type="undead",
        affinity="none",
        damage_type="slashing",
    )
    _start_configured_playground_encounter(session)
    current = session.combat_state.initiative_order.current_actor
    enemy = next(
        actor
        for actor in session.combat_state.actors
        if actor.faction == Faction.ENEMY
    )
    session.combat_state = replace_actor(
        session.combat_state,
        replace(current, hp=current.max_hp - 5),
    )
    session.combat_state = replace_actor(
        session.combat_state,
        replace(
            enemy,
            position=Coordinate(current.position.col + 1, current.position.row),
        ),
    )
    enemy = next(
        actor
        for actor in session.combat_state.actors
        if actor.faction == Faction.ENEMY
    )
    client = create_app(
        session,
        character_dir=tmp_path / "characters",
    ).test_client()

    lay_on_hands = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:feature:lay_on_hands"},
    )
    assert lay_on_hands.status_code == 200
    assert lay_on_hands.get_json()["feedback"]["next_step"] == (
        "select_board_target"
    )

    sacred = client.post(
        "/api/physical-cards/scan",
        json={
            "payload": (
                "dndbg:v1:action:feature:channel_divinity_sacred_weapon"
            )
        },
    )
    assert sacred.status_code == 200
    sacred_prompt = sacred.get_json()["state"]["combat"][
        "physical_feature_prompt"
    ]
    assert sacred_prompt["input_kind"] == "weapon"
    assert sacred_prompt["weapons"]

    turn_unholy = client.post(
        "/api/physical-cards/scan",
        json={
            "payload": (
                "dndbg:v1:action:feature:channel_divinity_turn_the_unholy"
            )
        },
    )
    assert turn_unholy.status_code == 200
    turn_prompt = turn_unholy.get_json()["state"]["combat"][
        "physical_feature_prompt"
    ]
    assert turn_prompt["input_kind"] == "saving_rolls"
    assert [target["id"] for target in turn_prompt["targets"]] == [str(enemy.id)]

    early_smite = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:feature:divine_smite"},
    )
    assert early_smite.status_code == 400
    assert "dopiero po potwierdzonym trafieniu" in early_smite.get_json()["error"]

    _start_board_weapon_attack(session, enemy.position)
    session.confirm_player_attack_target()
    session.submit_player_attack_roll(natural_roll=20)
    smite = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:feature:divine_smite"},
    )

    assert smite.status_code == 200
    assert smite.get_json()["feedback"]["next_step"] == "enter_feature_value"
    smite_prompt = smite.get_json()["state"]["combat"][
        "physical_feature_prompt"
    ]
    assert smite_prompt["input_kind"] == "slot"
    assert smite_prompt["available_slot_levels"] == [1]
    selected_smite = client.post(
        "/api/combat/divine-smite",
        json={"slot_level": 1},
    )
    assert selected_smite.status_code == 200, selected_smite.get_json()
    assert selected_smite.get_json()["combat"]["physical_feature_prompt"] is None
    assert selected_smite.get_json()["combat"]["pending_player_attack"][
        "divine_smite_slot_level"
    ] == 1


def test_playground_arena_exposes_only_legal_card_reminders(tmp_path) -> None:
    session = _session(tmp_path)
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = next(
        candidate
        for candidate in default_character_drafts()
        if candidate.class_id == "fighter"
    )
    garran = apply_boardgame_archetype(
        build_character(draft, catalog, resources).actor,
        spell_definitions=tuple(spell for _, spell in resources.spells),
    )
    session.configure_custom_party((garran,))
    session.configure_playground_trial(
        dummy_count=1,
        armor_class=12,
        hit_points=20,
        speed_feet=0,
        ability_score=10,
        creature_type="construct",
        affinity="none",
        damage_type="slashing",
    )
    _start_configured_playground_encounter(session)

    combat_before = session.combat_state
    reminders = session.state_payload()["combat"]["card_reminders"]

    assert session.combat_state == combat_before
    assert reminders
    assert all(item["owner_actor_id"] == "garran" for item in reminders)
    assert all(item["trigger_window"] == "action_selection" for item in reminders)
    assert {item["source_id"] for item in reminders} >= {
        "second_wind",
        "action_surge",
        "defensive_stance",
    }


@pytest.mark.parametrize("menu_id", ("maneuvers", "equipment"))
def test_playground_arena_opens_physical_menu_cards(tmp_path, menu_id: str) -> None:
    session = _session(tmp_path)
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = next(item for item in default_character_drafts() if item.id == "garran")
    actor = apply_boardgame_archetype(
        build_character(draft, catalog, resources).actor,
        spell_definitions=tuple(spell for _, spell in resources.spells),
    )
    session.configure_custom_party((actor,))
    session.configure_playground_trial(
        dummy_count=1,
        armor_class=12,
        hit_points=20,
        speed_feet=0,
        ability_score=10,
        creature_type="construct",
        affinity="none",
        damage_type="slashing",
    )
    _start_configured_playground_encounter(session)
    client = create_app(session, character_dir=tmp_path / "characters").test_client()

    response = client.post(
        "/api/physical-cards/scan",
        json={"payload": f"dndbg:v1:action:universal:{menu_id}"},
    )

    assert response.status_code == 200, response.get_json()
    assert response.get_json()["effect"] == f"open_{menu_id}_menu"
    assert response.get_json()["feedback"]["next_step"] == "select_menu_option"


def test_playground_enemy_field_falls_back_to_unarmed_attack(tmp_path) -> None:
    session = _session(tmp_path)
    session.configure_playground_trial(
        dummy_count=1,
        armor_class=12,
        hit_points=20,
        speed_feet=0,
        ability_score=10,
        creature_type="construct",
        affinity="none",
        damage_type="slashing",
    )
    _start_configured_playground_encounter(session)
    current = session.combat_state.initiative_order.current_actor
    current = replace(
        current,
        inventory=tuple(
            replace(item, equipped=False, held_in=())
            if item.kind == "weapon"
            else item
            for item in current.inventory
        ),
    )
    session.combat_state = replace_actor(session.combat_state, current)
    dummy = next(
        actor
        for actor in session.combat_state.actors
        if actor.faction == Faction.ENEMY
    )
    dummy = replace(
        dummy,
        position=Coordinate(current.position.col + 1, current.position.row),
    )
    session.combat_state = replace_actor(session.combat_state, dummy)
    client = create_app(
        session,
        character_dir=tmp_path / "characters",
    ).test_client()

    retired_card = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:attack:basic_attack"},
    )
    assert retired_card.status_code == 400
    assert "zatwierdzonego katalogu" in retired_card.get_json()["error"]

    payload = _start_board_weapon_attack(session, dummy.position)

    assert payload["combat"]["pending_player_attack"]["source"]["id"] == "unarmed_strike"
    assert payload["combat"]["pending_player_attack"]["stage"] == "confirm_attack"


def test_playground_exploration_rejects_guidance_card_in_favor_of_tiles(tmp_path) -> None:
    session = _session(tmp_path)
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = next(
        draft
        for draft in default_character_drafts()
        if draft.class_id == "cleric"
    )
    cleric = build_character(draft, catalog, resources).actor
    cleric = replace(
        cleric,
        inventory=tuple(
            replace(item, equipped=False, held_in=())
            for item in cleric.inventory
        ),
    )
    session.configure_custom_party((cleric,))
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.pending = PendingInteraction(
        kind=PendingKind.CHALLENGE,
        stage=PendingStage.ROLL,
        check_plan=ExplorationCheckPlan(
            participants=CheckParticipants.SINGLE_ACTOR,
            aggregation=CheckAggregation.LEAD_RESULT,
            consequence_targets=(ConsequenceTarget.LEAD_ACTOR,),
            ability="wisdom",
            skill="perception",
            dc=12,
            lead_actor_id=str(cleric.id),
        ),
    )
    client = create_app(
        session,
        character_dir=tmp_path / "characters",
    ).test_client()

    response = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:spell:guidance"},
    )

    assert response.status_code == 400
    assert "Karty eksploracji są obecnie wyłączone" in response.get_json()["error"]
    assert not any(
        effect.kind == "guidance_roll_bonus"
        for effect in session.active_combat_effects
    )


def test_playground_short_rest_rejects_alarm_exploration_card(tmp_path) -> None:
    session = _session(tmp_path)
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = next(
        draft
        for draft in all_default_character_drafts()
        if draft.class_id == "wizard"
    )
    wizard = build_character(draft, catalog, resources).actor
    spell_data = json.loads(
        Path("content/spells/alarm.json").read_text(encoding="utf-8")
    )
    alarm = _parse_spell_definition(spell_data, "alarm")
    wizard = replace(
        wizard,
        spells=(*wizard.spells, alarm),
        spell_access=(
            *wizard.spell_access,
            SpellAccessProfile(
                SpellAccessKind.KNOWN,
                (alarm.id,),
                casting_ability="intelligence",
                allowed_focus_kinds=("component_pouch", "arcane"),
            ),
        ),
        spell_preparation=replace(
            wizard.spell_preparation,
            available_spells=(
                *wizard.spell_preparation.available_spells,
                PreparableSpell(alarm.id, alarm.name, alarm.level),
            ),
            prepared_spell_ids=(
                *wizard.spell_preparation.prepared_spell_ids[:-1],
                alarm.id,
            ),
        ),
        inventory=tuple(
            replace(item, equipped=False, held_in=())
            if item.kind == "weapon"
            else item
            for item in wizard.inventory
        ),
    )
    session.configure_custom_party((wizard,))
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.state = replace(
        session.state,
        party_position=PartyPosition("rest_station"),
    )
    session.start_short_rest()
    client = create_app(
        session,
        character_dir=tmp_path / "characters",
    ).test_client()
    slots_before = wizard.spell_slots[0].remaining

    response = client.post(
        "/api/physical-cards/scan",
        json={
            "payload": f"dndbg:v2:action:spell:alarm:{wizard.id}",
        },
    )

    assert response.status_code == 400
    assert "Karty eksploracji są obecnie wyłączone" in response.get_json()["error"]
    updated = session.exploration.actors[0]
    assert updated.spell_slots[0].remaining == slots_before
    assert dict(session.state.flags.values).get("short_rest_alarm_active") is not True

    session.cancel_short_rest()

    assert dict(session.state.flags.values).get("short_rest_alarm_active") is not True


def test_playground_arena_routes_invisibility_from_scan_to_board_target(tmp_path) -> None:
    session = _session(tmp_path)
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = next(
        draft
        for draft in default_character_drafts()
        if draft.class_id == "wizard"
    )
    wizard = build_character(draft, catalog, resources).actor
    spell_data = json.loads(
        Path("content/spells/invisibility.json").read_text(encoding="utf-8")
    )
    invisibility = _parse_spell_definition(spell_data, "invisibility")
    wizard = replace(
        wizard,
        level=3,
        spells=(*wizard.spells, invisibility),
        spell_access=(
            *wizard.spell_access,
            SpellAccessProfile(
                SpellAccessKind.KNOWN,
                (invisibility.id,),
                casting_ability="intelligence",
                allowed_focus_kinds=("component_pouch", "arcane"),
            ),
        ),
        spell_preparation=replace(
            wizard.spell_preparation,
            available_spells=(
                *wizard.spell_preparation.available_spells,
                PreparableSpell(
                    invisibility.id,
                    invisibility.name,
                    invisibility.level,
                ),
            ),
            prepared_spell_ids=(
                *wizard.spell_preparation.prepared_spell_ids[:-1],
                invisibility.id,
            ),
        ),
        spell_slots=(*wizard.spell_slots, SpellSlotState(2, 1, 1)),
        inventory=tuple(
            replace(item, equipped=False, held_in=())
            if item.kind == "weapon"
            else item
            for item in wizard.inventory
        ),
    )
    session.configure_custom_party((wizard,))
    session.configure_playground_trial(
        dummy_count=1,
        armor_class=12,
        hit_points=20,
        speed_feet=0,
        ability_score=10,
        creature_type="construct",
        affinity="none",
        damage_type="slashing",
    )
    _start_configured_playground_encounter(session)
    client = create_app(
        session,
        character_dir=tmp_path / "characters",
    ).test_client()

    scanned = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:spell:invisibility"},
    )

    assert scanned.status_code == 200, scanned.get_json()
    payload = scanned.get_json()
    assert payload["feedback"]["next_step"] == "select_board_target"
    pending = payload["state"]["combat"]["pending_concentration_action"]
    assert pending["action"]["id"] == "invisibility"
    selected = session.select_board_position(
        session.combat_state.initiative_order.current_actor.position
    )
    selected_ids = selected["combat"]["pending_concentration_action"][
        "selected_target_ids"
    ]
    assert selected_ids == [str(wizard.id)]

    confirmed = session.confirm_combat_concentration_action(
        target_ids=tuple(selected_ids),
    )

    assert confirmed["combat"]["pending_concentration_action"] is None
    wizard_payload = next(
        actor for actor in confirmed["combat"]["actors"] if actor["id"] == str(wizard.id)
    )
    assert any(effect["kind"] == "invisibility" for effect in wizard_payload["effects"])


def test_playground_arena_routes_first_common_combat_spell_card_batch(tmp_path) -> None:
    session = _session(tmp_path)
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = next(
        draft
        for draft in default_character_drafts()
        if draft.class_id == "wizard"
    )
    caster = build_character(draft, catalog, resources).actor
    spell_ids = (
        "magic_missile",
        "fire_bolt",
        "eldritch_blast",
        "sacred_flame",
        "guiding_bolt",
        "cure_wounds",
        "healing_word",
        "bless",
        "shield_of_faith",
        "misty_step",
        "sleep",
        "hold_person",
        "thunderwave",
        "spiritual_weapon",
    )
    spells = tuple(
        _parse_spell_definition(
            json.loads(
                Path(f"content/spells/{spell_id}.json").read_text(
                    encoding="utf-8"
                )
            ),
            spell_id,
        )
        for spell_id in spell_ids
    )
    caster = replace(
        caster,
        level=3,
        spells=spells,
        spell_preparation=None,
        spell_access=(
            SpellAccessProfile(
                SpellAccessKind.KNOWN,
                spell_ids,
                casting_ability="intelligence",
                allowed_focus_kinds=(
                    "component_pouch",
                    "arcane",
                    "holy",
                    "druidic",
                ),
            ),
        ),
        spell_slots=(SpellSlotState(1, 4, 4), SpellSlotState(2, 3, 3)),
    )
    session.configure_custom_party((caster,))
    session.configure_playground_trial(
        dummy_count=1,
        armor_class=12,
        hit_points=20,
        speed_feet=0,
        ability_score=10,
        creature_type="humanoid",
        affinity="none",
        damage_type="slashing",
    )
    _start_configured_playground_encounter(session)
    client = create_app(
        session,
        character_dir=tmp_path / "characters",
    ).test_client()

    for spell_id in spell_ids:
        response = client.post(
            "/api/physical-cards/scan",
            json={"payload": f"dndbg:v1:action:spell:{spell_id}"},
        )

        assert response.status_code == 200, (spell_id, response.get_json())
        assert response.get_json()["applied"] is True
        assert response.get_json()["feedback"]["next_step"] == (
            "select_board_target"
        )
        session._clear_player_pending_choices()

    routed_events = [
        event
        for event in client.get("/api/session-log").get_json()["events"]
        if event["event_type"] == "ui_physical_action_card_resolved"
        and event["payload"].get("action_kind") == "spell"
    ]
    assert {event["payload"]["source_id"] for event in routed_events} >= set(
        spell_ids
    )
    current = session.combat_state.initiative_order.current_actor
    session.combat_state = replace_actor(
        session.combat_state,
        replace(current, hp=current.max_hp - 3),
    )
    healing_scan = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:spell:cure_wounds"},
    ).get_json()
    assert healing_scan["state"]["combat"]["targeting"]["kind"] == "healing"
    selected = session.select_board_position(current.position)
    assert selected["combat"]["pending_player_healing"]["target"]["id"] == str(
        current.id
    )


def test_playground_arena_routes_damage_and_control_spell_card_batch(tmp_path) -> None:
    session = _session(tmp_path)
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = next(
        draft
        for draft in default_character_drafts()
        if draft.class_id == "wizard"
    )
    caster = build_character(draft, catalog, resources).actor
    spell_ids = (
        "acid_arrow",
        "acid_splash",
        "burning_hands",
        "chill_touch",
        "inflict_wounds",
        "poison_spray",
        "ray_of_frost",
        "scorching_ray",
        "shatter",
        "shocking_grasp",
        "entangle",
        "grease",
        "web",
        "faerie_fire",
        "fog_cloud",
    )
    spells = tuple(
        _parse_spell_definition(
            json.loads(
                Path(f"content/spells/{spell_id}.json").read_text(
                    encoding="utf-8"
                )
            ),
            spell_id,
        )
        for spell_id in spell_ids
    )
    caster = replace(
        caster,
        level=3,
        spells=spells,
        spell_preparation=None,
        spell_access=(
            SpellAccessProfile(
                SpellAccessKind.KNOWN,
                spell_ids,
                casting_ability="intelligence",
                allowed_focus_kinds=(
                    "component_pouch",
                    "arcane",
                    "holy",
                    "druidic",
                ),
            ),
        ),
        spell_slots=(SpellSlotState(1, 4, 4), SpellSlotState(2, 3, 3)),
    )
    session.configure_custom_party((caster,))
    session.configure_playground_trial(
        dummy_count=2,
        armor_class=12,
        hit_points=20,
        speed_feet=10,
        ability_score=10,
        creature_type="humanoid",
        affinity="none",
        damage_type="slashing",
    )
    _start_configured_playground_encounter(session)
    client = create_app(
        session,
        character_dir=tmp_path / "characters",
    ).test_client()

    for spell_id in spell_ids:
        response = client.post(
            "/api/physical-cards/scan",
            json={"payload": f"dndbg:v1:action:spell:{spell_id}"},
        )

        assert response.status_code == 200, (spell_id, response.get_json())
        assert response.get_json()["feedback"]["next_step"] == (
            "select_board_target"
        )
        session._clear_player_pending_choices()

    scanned = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:spell:fog_cloud"},
    ).get_json()
    pending_zone = scanned["state"]["combat"]["pending_concentration_action"]
    selected_position = Coordinate(**pending_zone["legal_positions"][0])
    assert selected_position in session._current_board_scan_target().positions
    selected = session.select_board_position(selected_position)
    assert selected["combat"]["pending_concentration_action"]["anchor"] == {
        "col": selected_position.col,
        "row": selected_position.row,
    }

    confirmed = session.confirm_combat_concentration_action()
    zone = next(
        effect
        for effect in session.active_combat_effects
        if effect.kind == "obscuring_zone"
    )
    assert confirmed["combat"]["pending_concentration_action"] is None
    assert zone.anchor_position == selected_position
    assert zone.value == 20


def test_playground_arena_routes_defense_support_and_reaction_spell_batch(
    tmp_path,
) -> None:
    session = _session(tmp_path)
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = next(
        draft
        for draft in default_character_drafts()
        if draft.class_id == "wizard"
    )
    caster = build_character(draft, catalog, resources).actor
    spell_ids = (
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
    )
    spells = tuple(
        _parse_spell_definition(
            json.loads(
                Path(f"content/spells/{spell_id}.json").read_text(
                    encoding="utf-8"
                )
            ),
            spell_id,
        )
        for spell_id in spell_ids
    )
    caster = replace(
        caster,
        level=3,
        spells=spells,
        spell_preparation=None,
        spell_access=(
            SpellAccessProfile(
                SpellAccessKind.KNOWN,
                spell_ids,
                casting_ability="intelligence",
                allowed_focus_kinds=(
                    "component_pouch",
                    "arcane",
                    "holy",
                    "druidic",
                ),
            ),
        ),
        spell_slots=(SpellSlotState(1, 4, 4), SpellSlotState(2, 3, 3)),
        inventory=(
            *caster.inventory,
            InventoryItem(
                id="spell_component_protection_from_evil_and_good",
                name="Woda święcona lub srebro i żelazo",
                kind="spell_component",
                equipped=False,
            ),
        ),
    )
    session.configure_custom_party((caster,))
    session.configure_playground_trial(
        dummy_count=1,
        armor_class=12,
        hit_points=20,
        speed_feet=10,
        ability_score=10,
        creature_type="humanoid",
        affinity="none",
        damage_type="slashing",
    )
    _start_configured_playground_encounter(session)
    client = create_app(
        session,
        character_dir=tmp_path / "characters",
    ).test_client()
    self_spells = {"blur", "false_life", "mirror_image", "see_invisibility"}

    for spell_id in spell_ids:
        response = client.post(
            "/api/physical-cards/scan",
            json={"payload": f"dndbg:v1:action:spell:{spell_id}"},
        )

        assert response.status_code == 200, (spell_id, response.get_json())
        assert response.get_json()["feedback"]["next_step"] == (
            "confirm_action"
            if spell_id in self_spells
            else "select_board_target"
        )
        session._clear_player_pending_choices()

    enemy = next(
        actor
        for actor in session.combat_state.actors
        if actor.faction == Faction.ENEMY
    )
    session.combat_state = replace(
        session.combat_state,
        hidden_states=(
            HiddenState(str(enemy.id), 30, (str(caster.id),)),
        ),
    )
    scanned = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:spell:see_invisibility"},
    ).get_json()
    assert scanned["feedback"]["next_step"] == "confirm_action"
    confirmed = session.confirm_combat_concentration_action()
    assert confirmed["combat"]["pending_concentration_action"] is None
    assert any(
        effect.kind == "see_invisibility"
        and effect.actor_id == str(caster.id)
        for effect in session.active_combat_effects
    )
    assert session.combat_state.hidden_states == ()


def test_playground_arena_routes_debuff_and_persistent_spell_batch(tmp_path) -> None:
    session = _session(tmp_path)
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = next(
        draft
        for draft in default_character_drafts()
        if draft.class_id == "wizard"
    )
    caster = build_character(draft, catalog, resources).actor
    spell_ids = (
        "bane",
        "blindness_deafness",
        "command",
        "color_spray",
        "hideous_laughter",
        "ray_of_enfeeblement",
        "vicious_mockery",
        "heat_metal",
        "moonbeam",
        "flaming_sphere",
        "spike_growth",
        "silence",
        "gust_of_wind",
        "flame_blade",
        "hunters_mark",
    )
    spells = tuple(
        _parse_spell_definition(
            json.loads(
                Path(f"content/spells/{spell_id}.json").read_text(
                    encoding="utf-8"
                )
            ),
            spell_id,
        )
        for spell_id in spell_ids
    )
    caster = replace(
        caster,
        level=3,
        spells=spells,
        spell_preparation=None,
        spell_access=(
            SpellAccessProfile(
                SpellAccessKind.KNOWN,
                spell_ids,
                casting_ability="intelligence",
                allowed_focus_kinds=(
                    "component_pouch",
                    "arcane",
                    "holy",
                    "druidic",
                ),
            ),
        ),
        spell_slots=(SpellSlotState(1, 4, 4), SpellSlotState(2, 4, 4)),
    )
    session.configure_custom_party((caster,))
    session.configure_playground_trial(
        dummy_count=2,
        armor_class=12,
        hit_points=30,
        speed_feet=10,
        ability_score=10,
        creature_type="humanoid",
        affinity="none",
        damage_type="slashing",
    )
    _start_configured_playground_encounter(session)
    enemy = next(
        actor
        for actor in session.combat_state.actors
        if actor.faction == Faction.ENEMY
    )
    session.combat_state = replace_actor(
        session.combat_state,
        replace(
            enemy,
            inventory=(
                *enemy.inventory,
                InventoryItem(
                    id="arena_metal_weapon",
                    name="Metalowy miecz treningowy",
                    kind="weapon",
                    properties=("metallic",),
                ),
            ),
        ),
    )
    client = create_app(
        session,
        character_dir=tmp_path / "characters",
    ).test_client()

    for spell_id in spell_ids:
        response = client.post(
            "/api/physical-cards/scan",
            json={"payload": f"dndbg:v1:action:spell:{spell_id}"},
        )

        assert response.status_code == 200, (spell_id, response.get_json())
        assert response.get_json()["feedback"]["next_step"] == (
            "confirm_action" if spell_id == "flame_blade" else "select_board_target"
        )
        session._clear_player_pending_choices()

    scanned = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:spell:moonbeam"},
    ).get_json()
    pending_zone = scanned["state"]["combat"]["pending_concentration_action"]
    anchor = Coordinate(**pending_zone["legal_positions"][0])
    session.select_board_position(anchor)
    session.confirm_combat_concentration_action()
    zone = next(
        effect
        for effect in session.active_combat_effects
        if effect.object_id == "combat_action:moonbeam"
        and effect.kind.startswith("ongoing_damage_zone:")
    )
    assert zone.anchor_position == anchor

    rescanned = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:spell:moonbeam"},
    ).get_json()
    assert rescanned["feedback"]["next_step"] == "select_board_target", rescanned
    assert session.pending_spell_zone_move_effect_id == zone.id
    assert session._current_board_scan_target().positions


def test_playground_arena_routes_buff_rescue_and_utility_spell_card_batch(
    tmp_path,
) -> None:
    session = _session(tmp_path)
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    draft = next(
        draft
        for draft in default_character_drafts()
        if draft.class_id == "wizard"
    )
    caster = build_character(draft, catalog, resources).actor
    spell_ids = (
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
        "produce_flame",
    )
    spells = tuple(
        _parse_spell_definition(
            json.loads(
                Path(f"content/spells/{spell_id}.json").read_text(
                    encoding="utf-8"
                )
            ),
            spell_id,
        )
        for spell_id in spell_ids
    )
    caster = replace(
        caster,
        level=3,
        spells=spells,
        spell_preparation=None,
        spell_access=(
            SpellAccessProfile(
                SpellAccessKind.KNOWN,
                spell_ids,
                casting_ability="intelligence",
                allowed_focus_kinds=(
                    "component_pouch",
                    "arcane",
                    "holy",
                    "druidic",
                ),
            ),
        ),
        spell_slots=(SpellSlotState(1, 8, 8), SpellSlotState(2, 8, 8)),
        inventory=(
            *caster.inventory,
            InventoryItem(
                id="spell_component_find_familiar",
                name="Węgiel, kadzidło i zioła",
                kind="spell_component",
                quantity=3,
                value_cp=1000,
            ),
            InventoryItem(
                id="spell_component_goodberry",
                name="Gałązka jemioły",
                kind="spell_component",
            ),
            InventoryItem(
                id="spell_component_warding_bond",
                name="Platynowe obrączki",
                kind="spell_component",
                quantity=2,
                value_cp=5000,
            ),
        ),
    )
    dying_ally = replace(
        caster,
        id="arena_dying_ally",
        name="Ranny sojusznik",
        hp=1,
        spells=(),
        spell_access=(),
        spell_slots=(),
    )
    session.configure_custom_party((caster, dying_ally))
    session.configure_playground_trial(
        dummy_count=1,
        armor_class=12,
        hit_points=20,
        speed_feet=10,
        ability_score=10,
        creature_type="humanoid",
        affinity="none",
        damage_type="slashing",
    )
    _start_configured_playground_encounter(session)
    client = create_app(
        session,
        character_dir=tmp_path / "characters",
    ).test_client()
    confirm_spells = {
        "divine_favor",
        "expeditious_retreat",
        "shillelagh",
        "find_familiar",
        "find_traps",
        "goodberry",
    }

    for spell_id in spell_ids:
        if spell_id == "spare_the_dying":
            arena_ally = next(
                actor
                for actor in session.combat_state.actors
                if str(actor.id) == "arena_dying_ally"
            )
            session.combat_state = replace_actor(
                session.combat_state,
                replace(arena_ally, hp=0),
            )
        response = client.post(
            "/api/physical-cards/scan",
            json={"payload": f"dndbg:v1:action:spell:{spell_id}"},
        )

        assert response.status_code == 200, (spell_id, response.get_json())
        assert response.get_json()["feedback"]["next_step"] == (
            "confirm_action"
            if spell_id in confirm_spells
            else "select_board_target"
        )
        session._clear_player_pending_choices()

    client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:spell:find_familiar"},
    )
    session.confirm_combat_concentration_action(effect_option="raven")
    produce_flame = next(
        source
        for source in session._attack_sources_for_actor(
            session.combat_state.initiative_order.current_actor
        )
        if source.id == "produce_flame"
    )
    assert produce_flame.attack_roll_request.mode is RollMode.ADVANTAGE

    session.combat_state = replace(
        session.combat_state,
        turn_action=replace(
            session.combat_state.turn_action,
            action_use=ActionUse.ACTION_AVAILABLE,
            leveled_action_spell_cast=False,
        ),
    )
    client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:spell:find_familiar"},
    )
    session.confirm_combat_concentration_action(effect_option="snake")
    assert any(
        source.id == "familiar_snake_bite"
        and source.action_cost.value == "bonus_action"
        for source in session._attack_sources_for_actor(
            session.combat_state.initiative_order.current_actor
        )
    )

    session.combat_state = replace(
        session.combat_state,
        turn_action=replace(
            session.combat_state.turn_action,
            action_use=ActionUse.ACTION_AVAILABLE,
            leveled_action_spell_cast=False,
        ),
    )
    client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:spell:find_familiar"},
    )
    session.confirm_combat_concentration_action(effect_option="cat")
    cat_actor = session.combat_state.initiative_order.current_actor
    dexterity_save = SavingThrowRequest(
        "dexterity",
        30,
        "Test chowańca",
        SaveDamageOnSuccess.NONE,
    )
    without_cat = resolve_actor_saving_throw(
        cat_actor,
        dexterity_save,
        natural_roll=10,
    )
    with_cat = resolve_actor_saving_throw(
        cat_actor,
        dexterity_save,
        natural_roll=10,
        active_effects=session.active_combat_effects,
    )
    assert with_cat.total == without_cat.total + 2

    session.combat_state = replace(
        session.combat_state,
        turn_action=replace(
            session.combat_state.turn_action,
            action_use=ActionUse.ACTION_AVAILABLE,
            leveled_action_spell_cast=False,
        ),
    )
    current_caster = session.combat_state.initiative_order.current_actor
    session.combat_state = replace_actor(
        session.combat_state,
        replace(current_caster, hp=current_caster.max_hp - 5),
    )
    client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:spell:prayer_of_healing"},
    )
    prayer_minutes_before = session.state.elapsed_minutes
    slot_before_prayer = next(
        slot.remaining
        for slot in session.combat_state.initiative_order.current_actor.spell_slots
        if slot.level == 2
    )
    prepared_prayer = session.confirm_combat_concentration_action(
        target_ids=(str(caster.id),),
        roll_total=8,
    )
    assert prepared_prayer["combat"]["pending_concentration_action"]["casting_ready"] is True
    assert any(
        effect.kind == "concentration_timed_cast"
        for effect in session.active_combat_effects
    )
    assert session.state.elapsed_minutes == prayer_minutes_before
    assert next(
        slot.remaining
        for slot in session.combat_state.initiative_order.current_actor.spell_slots
        if slot.level == 2
    ) == slot_before_prayer
    completed_prayer = client.post("/api/combat/timed-cast/complete", json={})
    assert completed_prayer.status_code == 200, completed_prayer.get_json()
    caster_after_prayer = next(
        actor
        for actor in session.combat_state.actors
        if str(actor.id) == str(caster.id)
    )
    assert caster_after_prayer.hp == caster_after_prayer.max_hp
    assert session.state.elapsed_minutes == prayer_minutes_before + 10
    assert next(
        slot.remaining
        for slot in caster_after_prayer.spell_slots
        if slot.level == 2
    ) == slot_before_prayer - 1
    assert not any(
        effect.kind == "concentration_timed_cast"
        for effect in session.active_combat_effects
    )

    session.combat_state = replace(
        session.combat_state,
        turn_action=replace(
            session.combat_state.turn_action,
            action_use=ActionUse.ACTION_AVAILABLE,
            leveled_action_spell_cast=False,
        ),
    )
    client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:spell:prayer_of_healing"},
    )
    session.confirm_combat_concentration_action(
        target_ids=(str(caster.id),),
        roll_total=8,
    )
    praying_caster = session.combat_state.initiative_order.current_actor
    incoming = apply_damage_result(
        praying_caster,
        resolve_damage((DamageComponentInput(2, DamageType.SLASHING),)),
    )
    session.combat_state = replace_actor(
        session.combat_state,
        incoming.actor_after,
    )
    session._maybe_prompt_concentration_check(incoming)
    interrupted = session.submit_concentration_check(natural_roll=1)
    caster_after_cancel = session.combat_state.initiative_order.current_actor
    assert interrupted["combat"]["pending_concentration_action"] is None
    assert "nie zużywa slotu" in session.board_message
    assert session.state.elapsed_minutes == prayer_minutes_before + 10
    assert next(
        slot.remaining
        for slot in caster_after_cancel.spell_slots
        if slot.level == 2
    ) == slot_before_prayer - 1
    assert not any(
        effect.kind == "concentration_timed_cast"
        for effect in session.active_combat_effects
    )

    session.combat_state = replace(
        session.combat_state,
        turn_action=replace(
            session.combat_state.turn_action,
            action_use=ActionUse.ACTION_AVAILABLE,
            leveled_action_spell_cast=False,
        ),
    )

    scanned = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:spell:goodberry"},
    ).get_json()
    assert scanned["feedback"]["next_step"] == "confirm_action"
    session.confirm_combat_concentration_action()
    caster_after_cast = next(
        actor
        for actor in session.combat_state.actors
        if str(actor.id) == str(caster.id)
    )
    assert next(
        pool
        for pool in caster_after_cast.resource_pools
        if pool.id == "goodberry_charges"
    ).current == 10
    assert str(session.combat_state.initiative_order.current_actor.id) == str(caster.id)

    rescanned = client.post(
        "/api/physical-cards/scan",
        json={"payload": "dndbg:v1:action:spell:goodberry"},
    ).get_json()
    assert session.combat_targeting_healing_source_id == "goodberry_use", session.board_message
    assert rescanned["state"]["combat"]["targeting"]["kind"] == "healing"
    assert rescanned["feedback"]["next_step"] == "select_board_target"
    goodberry_counter = next(
        item
        for item in rescanned["feedback"]["resources"]
        if item["id"] == "goodberry_charges"
    )
    assert goodberry_counter == {
        "id": "goodberry_charges",
        "label": "Dobre jagody",
        "current": 10,
        "maximum": 10,
    }
    session.combat_state = replace(
        session.combat_state,
        turn_action=replace(
            session.combat_state.turn_action,
            action_use=ActionUse.ACTION_AVAILABLE,
            leveled_action_spell_cast=False,
        ),
    )
    ally_after_cast = next(
        actor
        for actor in session.combat_state.actors
        if str(actor.id) == "arena_dying_ally"
    )
    session.select_player_healing_target_at_position(ally_after_cast.position)
    healed = session.submit_player_healing_roll(healing=1)
    healed_ally = next(
        actor
        for actor in session.combat_state.actors
        if str(actor.id) == "arena_dying_ally"
    )
    caster_after_berry = next(
        actor
        for actor in session.combat_state.actors
        if str(actor.id) == str(caster.id)
    )
    assert healed["combat"]["pending_player_healing"] is None
    assert healed_ally.hp == 1
    assert next(
        pool
        for pool in caster_after_berry.resource_pools
        if pool.id == "goodberry_charges"
    ).current == 9


def test_playground_feather_fall_reaction_prevents_fall_hazard(tmp_path) -> None:
    session = _session(tmp_path)
    actor = session.exploration.actors[0]
    spell_data = json.loads(
        Path("content/spells/feather_fall.json").read_text(encoding="utf-8")
    )
    spell = _parse_spell_definition(spell_data, "feather_fall")
    caster = replace(
        actor,
        spells=(spell,),
        spell_access=(
            SpellAccessProfile(
                SpellAccessKind.KNOWN,
                (spell.id,),
                casting_ability="intelligence",
                allowed_focus_kinds=("arcane",),
            ),
        ),
        inventory=(
            *actor.inventory,
            InventoryItem(
                id="arcane_focus",
                name="Ognisko mistyczne",
                kind="focus",
                spellcasting_focus_kind=SpellcastingFocusKind.ARCANE,
            ),
        ),
        spell_slots=(SpellSlotState(1, 1, 1),),
    )
    session.exploration = replace(session.exploration, actors=(caster,))
    hazard = ExplorationHazard(
        id="training_fall",
        label="Upadek treningowy",
        trigger=ExplorationHazardTrigger.FAILURE,
        saving_throw=SavingThrowRequest(
            "dexterity",
            12,
            "Upadek",
            SaveDamageOnSuccess.HALF,
        ),
        damage=ExplorationHazardDamage("bludgeoning", fixed=10),
        failure_message="Twarde lądowanie.",
    )
    session.pending = PendingInteraction(
        kind=PendingKind.CHALLENGE,
        stage=PendingStage.HAZARD_SAVE,
        hazard=hazard,
        hazard_actor_id=str(caster.id),
    )

    before_hp = caster.hp
    pending_payload = session.state_payload()["pending"]
    payload = session.cast_feather_fall_for_pending_hazard(str(caster.id))

    assert pending_payload["feather_fall_options"][0]["actor_id"] == str(caster.id)
    assert session.pending is None
    updated = session.exploration.actors[0]
    assert updated.hp == before_hp
    assert updated.spell_slots[0].remaining == 0
    assert any(
        message["title"] == "Powolne opadanie"
        and "nie otrzymuje obrażeń" in message["body"]
        for message in payload["messages"]
    )


def test_playground_http_controls_are_exposed_only_by_the_runtime(tmp_path) -> None:
    session = _session(tmp_path)
    client = create_app(
        session,
        character_dir=tmp_path / "characters",
    ).test_client()

    page = client.get("/play")
    javascript = client.get("/static/exploration.js").get_data(as_text=True)
    response = client.post(
        "/api/playground/configure",
        json={
            "dummy_count": 6,
            "armor_class": 13,
            "hit_points": 25,
            "speed_feet": 0,
            "creature_type": "construct",
            "affinity": "immunity",
            "damage_type": "poison",
            "condition_immunity": "poisoned",
        },
    )

    assert page.status_code == 200
    assert 'id="playground-panel"' in page.get_data(as_text=True)
    assert "function playgroundChatControlsHtml" in javascript
    assert "Ustaw manekiny i rozpocznij setup" in javascript
    assert "['control_room', 'combat_arena'].includes" in javascript
    assert response.status_code == 200
    assert response.get_json()["playground"]["config"]["dummy_count"] == 6


def test_playground_social_lab_fits_four_goals_and_system_exit(tmp_path) -> None:
    session = _session(tmp_path)
    session.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    session.state = replace(
        session.state,
        party_position=PartyPosition("social_lab"),
    )
    session.active_point_id = "master_zero"

    pads = session._board_interaction_pads()

    assert [pad.target_id for pad in pads[:-1]] == [
        "ask_rules",
        "persuasion_test",
        "deception_test",
        "intimidation_test",
    ]
    assert pads[-1].action_kind == "exit"
    assert pads[-1].position == Coordinate(12, 18)

    returned = session.select_board_position(pads[-1].position)
    assert returned["active_point"] is None
