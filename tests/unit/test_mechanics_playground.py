import json
from dataclasses import replace
from pathlib import Path

from dnd_board_game.actors import Faction
from dnd_board_game.combat import DamageType, SpellSlotState
from dnd_board_game.character_creation.srd_manifest import SRD_SPELL_IDS_BY_LEVEL
from dnd_board_game.exploration import (
    ExplorationHazard,
    ExplorationHazardDamage,
    ExplorationHazardTrigger,
)
from dnd_board_game.inventory import InventoryItem, SpellcastingFocusKind
from dnd_board_game.rules import (
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
)
from dnd_board_game.ui.routes import create_app
from dnd_board_game.ui.playground_cases import load_playground_audit_registry


SCENARIO_PATH = "content/scenarios/mechanics_playground/scenario.json"


def _session(tmp_path) -> ExplorationUiSession:
    return ExplorationUiSession(
        SCENARIO_PATH,
        session_id="mechanics_playground_test",
        observation_dir=tmp_path / "observations",
        save_dir=tmp_path / "saves",
    )


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
