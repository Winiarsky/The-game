"""Transport-neutral phase and execution contract for physical action cards."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .qr_payload import DecisionCardActionKind


class CardPhase(StrEnum):
    COMBAT = "combat"
    EXPLORATION = "exploration"
    BOTH = "both"
    REMOVED = "removed"


class CardTriggerWindow(StrEnum):
    ACTION_SELECTION = "action_selection"
    ATTACK_ROLL_REVEALED = "attack_roll_revealed"
    DAMAGE_ROLL_REVEALED = "damage_roll_revealed"
    BEFORE_EXPLORATION_CHECK = "before_exploration_check"
    SHORT_REST_PREVIEW = "short_rest_preview"
    AFTER_DAMAGE_APPLIED = "after_damage_applied"


class CombatCardRoute(StrEnum):
    """Existing combat runtime entry point used by a scanned card."""

    ATTACK_SOURCE = "attack_source"
    HEALING_SOURCE = "healing_source"
    COMBAT_ACTION = "combat_action"
    REACTION = "reaction"


@dataclass(frozen=True, slots=True)
class CardActionDefinition:
    source_id: str
    qr_kind: DecisionCardActionKind
    phase: CardPhase
    effect_type: str
    action_id: str
    targeting: str = "none"
    trigger_windows: tuple[CardTriggerWindow, ...] = (
        CardTriggerWindow.ACTION_SELECTION,
    )
    duration: str = "instant"
    toggle: bool = False
    combat_route: CombatCardRoute | None = None

    @property
    def playable(self) -> bool:
        return self.phase is not CardPhase.REMOVED


_COMBAT_IDS = frozenset(
    """
    action_surge second_wind shield_bash defensive_stance
    garran_command_halt garran_shield_wall garran_rally garran_guard_companion
    instinctive_dodge smoke_screen hamstring_cut piercing_attack guard_vault
    blade_mistress combat_trap_detection
    aim anchoring_arrow exposing_arrow disrupting_arrow double_shot
    rage reckless_attack powerful_strike shoulder_check hard_as_rock
    acceleration deafening_roar
    bardic_inspiration cutting_words optical_scope mocking_shot provoking_shot entangling_shot counterpoint
    distracting_shout preserve_life turn_undead wild_shape
    martial_arts_strike flurry_of_blows patient_defense step_of_the_wind
    deflect_missiles lay_on_hands divine_smite channel_divinity_sacred_weapon
    channel_divinity_turn_the_unholy cunning_action metamagic_careful
    metamagic_distant metamagic_empowered metamagic_extended
    metamagic_heightened metamagic_quickened metamagic_twinned
    pact_of_the_blade acid_arrow acid_splash aid bane barkskin bless
    divine_care_aura healing_grace_aura
    blindness_deafness blur burning_hands chill_touch color_spray command
    cure_wounds darkness darkvision divine_favor eldritch_blast enlarge_reduce
    entangle expeditious_retreat faerie_fire false_life find_familiar find_traps
    fire_bolt flame_blade flaming_sphere fog_cloud goodberry grease guiding_bolt
    gust_of_wind healing_word heat_metal hellish_rebuke heroism
    hideous_laughter hold_person hunters_mark inflict_wounds invisibility
    lesser_restoration levitate mage_armor magic_missile magic_weapon
    mirror_image misty_step moonbeam poison_spray prayer_of_healing
    produce_flame protection_from_evil_and_good protection_from_poison
    ray_of_enfeeblement ray_of_frost resistance sacred_flame sanctuary
    scorching_ray see_invisibility shatter shield shield_of_faith shillelagh
    shocking_grasp silence sleep spare_the_dying spike_growth spiritual_weapon
    thunderwave true_strike vicious_mockery warding_bond web panic_whisper
    stage_command accelerated_refrain
    nimra_frost_pulse nimra_acid_splash nimra_mind_spike nimra_flame_fan
    nimra_force_wave nimra_sticky_matrix nimra_sleep nimra_fog nimra_web
    nimra_lightning_path nimra_mind_break nimra_stasis
    nimra_sculpt_field nimra_distant_spell nimra_overcharged_spell
    nimra_forced_weave nimra_energy_transmutation
    """.split()
)

_EXPLORATION_IDS = frozenset(
    """
    natural_recovery divine_sense primeval_awareness font_of_magic
    metamagic_subtle arcane_recovery alarm alter_self animal_friendship
    arcanists_magic_aura augury calm_emotions charm_person comprehend_languages
    continual_flame create_or_destroy_water dancing_lights detect_evil_and_good
    detect_magic detect_poison_and_disease detect_thoughts disguise_self
    druidcraft enhance_ability enthrall feather_fall guidance identify knock
    light locate_animals_or_plants locate_object longstrider mage_hand mending
    minor_illusion pass_without_trace prestidigitation purify_food_and_drink
    rope_trick silent_image speak_with_animals spider_climb suggestion
    unseen_servant zone_of_truth guard_duty tactical_assessment intimidation
    brutal_effort tracking improvisation
    """.split()
)

_BOTH_IDS = frozenset(
    {
        "prayer_of_healing",
    }
)

_REMOVED_IDS = frozenset(
    {
        "animal_messenger",
        "arcane_lock",
        "floating_disk",
        "gentle_repose",
        "illusory_script",
        "jump",
        "magic_mouth",
        "message",
        "break_in",
    }
)

_FEATURE_IDS = frozenset(
    """
    action_surge second_wind shield_bash defensive_stance
    garran_command_halt garran_shield_wall garran_rally garran_guard_companion
    instinctive_dodge smoke_screen hamstring_cut piercing_attack guard_vault
    blade_mistress combat_trap_detection
    aim anchoring_arrow exposing_arrow disrupting_arrow double_shot
    rage reckless_attack powerful_strike shoulder_check hard_as_rock
    acceleration deafening_roar bardic_inspiration optical_scope mocking_shot provoking_shot entangling_shot
    counterpoint distracting_shout cutting_words preserve_life turn_undead
    wild_shape natural_recovery
    martial_arts_strike flurry_of_blows patient_defense step_of_the_wind
    deflect_missiles divine_sense lay_on_hands divine_smite
    channel_divinity_sacred_weapon channel_divinity_turn_the_unholy
    primeval_awareness cunning_action font_of_magic metamagic_careful
    metamagic_distant metamagic_empowered metamagic_extended
    metamagic_heightened metamagic_quickened metamagic_subtle
    metamagic_twinned pact_of_the_blade arcane_recovery guard_duty
    tactical_assessment intimidation brutal_effort tracking improvisation
    nimra_sculpt_field nimra_distant_spell nimra_overcharged_spell
    nimra_forced_weave nimra_energy_transmutation
    """.split()
)

_ACTION_ALIASES = {
    "channel_divinity_sacred_weapon": "sacred_weapon",
    "channel_divinity_turn_the_unholy": "turn_the_unholy",
    "martial_arts_strike": "martial_arts_bonus_attack",
    "pact_of_the_blade": "pact_weapon",
}

_PROTOTYPE_OVERRIDES: dict[str, dict[str, object]] = {
    "rage": {
        "effect_type": "toggle_status",
        "targeting": "self",
        "duration": "up_to_10_rounds",
        "toggle": True,
    },
    "action_surge": {
        "effect_type": "restore_spent_action",
        "targeting": "self",
    },
    "shield_bash": {
        "effect_type": "bonus_action_opposed_strength_damage_push",
        "targeting": "board_enemy",
    },
    "second_wind": {
        "effect_type": "physical_die_self_healing",
        "targeting": "self_then_d10",
    },
    "defensive_stance": {
        "effect_type": "movement_action_ac_bonus_until_move",
        "targeting": "self",
        "duration": "until_next_turn",
    },
    "garran_command_halt": {
        "effect_type": "spend_tactic_wisdom_save_movement_debuff",
        "targeting": "board_enemy",
        "duration": "until_target_turn_end",
    },
    "garran_shield_wall": {
        "effect_type": "spend_tactic_dynamic_adjacent_ally_ac_aura",
        "targeting": "self",
        "duration": "until_next_turn",
    },
    "garran_rally": {
        "effect_type": "spend_tactic_remove_fear_next_roll_advantage",
        "targeting": "allies_in_radius",
        "duration": "until_recipient_next_turn_end",
    },
    "garran_guard_companion": {
        "effect_type": "spend_tactic_redirect_single_hostile_target",
        "targeting": "board_ally",
        "duration": "until_trigger_or_adjacency_breaks",
    },
    "instinctive_dodge": {
        "effect_type": "stealth_reaction_spend_trick_single_attack_disadvantage",
        "targeting": "self_when_targeted",
        "trigger_windows": (CardTriggerWindow.ATTACK_ROLL_REVEALED,),
        "duration": "single_attack",
        "combat_route": CombatCardRoute.REACTION,
    },
    "smoke_screen": {
        "effect_type": "spend_trick_move_then_forced_hide",
        "targeting": "self_then_board_destination",
    },
    "hamstring_cut": {
        "effect_type": "flanking_melee_attack_persistent_half_speed",
        "targeting": "board_enemy",
    },
    "piercing_attack": {
        "effect_type": "flanking_melee_attack_then_collinear_attack",
        "targeting": "board_enemy",
    },
    "guard_vault": {
        "effect_type": "melee_attack_then_move_behind_target",
        "targeting": "board_enemy_with_free_rear_tile",
    },
    "blade_mistress": {
        "effect_type": "hidden_throwing_knife_bleeding_rider",
        "targeting": "prepared_attack",
    },
    "combat_trap_detection": {
        "effect_type": "physical_perception_reveal_traps_in_radius",
        "targeting": "self_radius_45",
    },
    "aim": {
        "effect_type": "spend_movement_for_next_longbow_advantage",
        "targeting": "self",
        "duration": "until_next_attack_or_turn_end",
    },
    "anchoring_arrow": {
        "effect_type": "instinct_longbow_attack_movement_lock",
        "targeting": "board_enemy",
        "duration": "d4_rounds",
    },
    "exposing_arrow": {
        "effect_type": "instinct_longbow_attack_reduce_ac",
        "targeting": "board_enemy",
        "duration": "until_next_erynd_turn",
    },
    "disrupting_arrow": {
        "effect_type": "instinct_longbow_attack_disrupt",
        "targeting": "board_enemy",
        "duration": "until_target_turn_end",
    },
    "double_shot": {
        "effect_type": "instinct_double_ammunition_single_roll",
        "targeting": "board_enemy",
    },
    "reckless_attack": {
        "effect_type": "melee_weapon_attack_with_advantage_and_exposure",
        "targeting": "board_enemy",
        "duration": "until_next_turn",
    },
    "powerful_strike": {
        "effect_type": "rage_ferocity_melee_attack_bonus",
        "targeting": "board_enemy",
    },
    "shoulder_check": {
        "effect_type": "opposed_strength_forced_movement",
        "targeting": "board_enemy_then_destination",
    },
    "hard_as_rock": {
        "effect_type": "reaction_reduce_post_resistance_damage",
        "targeting": "self",
        "trigger_windows": (CardTriggerWindow.DAMAGE_ROLL_REVEALED,),
        "combat_route": CombatCardRoute.REACTION,
    },
    "acceleration": {
        "effect_type": "rage_ferocity_double_turn_movement",
        "targeting": "self",
        "duration": "until_turn_end",
    },
    "deafening_roar": {
        "effect_type": "rage_ferocity_cone_save_damage_debuff",
        "targeting": "board_cone",
    },
    "martial_arts_strike": {
        "effect_type": "queue_bonus_unarmed_attack",
        "targeting": "self",
    },
    "flurry_of_blows": {
        "effect_type": "spend_ki_queue_two_unarmed_attacks",
        "targeting": "self",
    },
    "patient_defense": {
        "effect_type": "spend_ki_dodge",
        "targeting": "self",
        "duration": "until_next_turn",
    },
    "step_of_the_wind": {
        "effect_type": "spend_ki_dash_and_disengage",
        "targeting": "self",
        "duration": "current_turn",
    },
    "deflect_missiles": {
        "effect_type": "reaction_reduce_projectile_damage",
        "targeting": "incoming_projectile",
        "trigger_windows": (CardTriggerWindow.AFTER_DAMAGE_APPLIED,),
    },
    "lay_on_hands": {
        "effect_type": "allocate_healing_resource",
        "targeting": "board_ally_then_points",
    },
    "divine_smite": {
        "effect_type": "spend_slot_add_melee_weapon_damage",
        "targeting": "confirmed_melee_weapon_hit_then_slot",
        "trigger_windows": (CardTriggerWindow.ATTACK_ROLL_REVEALED,),
    },
    "channel_divinity_sacred_weapon": {
        "effect_type": "bind_attack_bonus_to_selected_weapon",
        "targeting": "equipped_weapon",
        "duration": "up_to_1_minute",
    },
    "channel_divinity_turn_the_unholy": {
        "effect_type": "area_wisdom_save_turn_fiends_and_undead",
        "targeting": "nearby_fiends_and_undead_then_saves",
        "duration": "up_to_1_minute",
    },
    "bardic_inspiration": {
        "effect_type": "grant_optional_roll_die",
        "targeting": "board_ally",
        "duration": "10_minutes_or_consumed",
    },
    "mocking_shot": {
        "effect_type": "single_crossbow_attack_mocking_debuff",
        "targeting": "board_enemy",
        "duration": "until_next_lorian_turn",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "optical_scope": {
        "effect_type": "double_crossbow_attack_single_scoped_target",
        "targeting": "board_enemy",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "provoking_shot": {
        "effect_type": "single_crossbow_attack_provocation",
        "targeting": "board_enemy",
        "duration": "until_next_lorian_turn",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "entangling_shot": {
        "effect_type": "area_crossbow_movement_control",
        "targeting": "board_area_all_creatures",
        "duration": "until_next_lorian_turn",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "counterpoint": {
        "effect_type": "reaction_crossbow_attack_inspired_ally_target",
        "targeting": "damaged_enemy",
        "trigger_windows": (CardTriggerWindow.AFTER_DAMAGE_APPLIED,),
        "combat_route": CombatCardRoute.REACTION,
    },
    "distracting_shout": {
        "effect_type": "reaction_reduce_damage_to_inspired_ally",
        "targeting": "inspired_ally_hit_by_attack",
        "trigger_windows": (CardTriggerWindow.DAMAGE_ROLL_REVEALED,),
        "combat_route": CombatCardRoute.REACTION,
    },
    "improvisation": {
        "effect_type": "reroll_failed_noncombat_charisma_check",
        "targeting": "self_failed_check",
        "trigger_windows": (CardTriggerWindow.BEFORE_EXPLORATION_CHECK,),
    },
    "panic_whisper": {
        "effect_type": "saving_throw_damage_and_forced_retreat",
        "targeting": "board_enemy",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "stage_command": {
        "effect_type": "saving_throw_selected_bounded_command",
        "targeting": "board_enemy_then_command",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "accelerated_refrain": {
        "effect_type": "concentration_crossbow_extra_attack_sequence",
        "targeting": "self",
        "duration": "three_rounds",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "cutting_words": {
        "effect_type": "reduce_revealed_roll",
        "targeting": "reacting_enemy",
        "trigger_windows": (
            CardTriggerWindow.ATTACK_ROLL_REVEALED,
            CardTriggerWindow.DAMAGE_ROLL_REVEALED,
        ),
    },
    "preserve_life": {
        "effect_type": "allocate_healing_pool",
        "targeting": "board_allies_then_values",
    },
    "turn_undead": {
        "effect_type": "area_wisdom_save_turn_undead",
        "targeting": "nearby_undead_then_saves",
        "duration": "up_to_1_minute",
    },
    "wild_shape": {
        "effect_type": "choose_combat_beast_form",
        "targeting": "self_then_form",
        "duration": "manual_toggle_or_beast_hp_depleted",
        "toggle": True,
    },
    "cunning_action": {
        "effect_type": "choose_bonus_action_mobility",
        "targeting": "self_then_dash_or_disengage",
        "duration": "current_turn",
    },
    "pact_of_the_blade": {
        "effect_type": "summon_selected_pact_weapon",
        "targeting": "self_then_weapon_form",
        "duration": "until_replaced_or_dismissed",
    },
    "metamagic_careful": {
        "effect_type": "modify_prepared_spell_careful",
        "targeting": "prepared_spell_then_protected_targets",
    },
    "metamagic_distant": {
        "effect_type": "modify_prepared_spell_range",
        "targeting": "prepared_spell",
    },
    "metamagic_empowered": {
        "effect_type": "reroll_revealed_spell_damage_dice",
        "targeting": "prepared_spell_after_damage_roll",
        "trigger_windows": (CardTriggerWindow.DAMAGE_ROLL_REVEALED,),
    },
    "metamagic_extended": {
        "effect_type": "modify_prepared_spell_duration",
        "targeting": "prepared_spell",
    },
    "metamagic_heightened": {
        "effect_type": "modify_prepared_spell_save",
        "targeting": "prepared_spell_then_one_target",
    },
    "metamagic_quickened": {
        "effect_type": "modify_prepared_spell_action_cost",
        "targeting": "prepared_spell",
    },
    "metamagic_twinned": {
        "effect_type": "modify_prepared_single_target_spell",
        "targeting": "prepared_spell_then_second_target",
    },
    "guidance": {
        "effect_type": "grant_next_check_die",
        "targeting": "pending_check_actor",
        "trigger_windows": (CardTriggerWindow.BEFORE_EXPLORATION_CHECK,),
        "duration": "current_check",
    },
    "alarm": {
        "effect_type": "prevent_rest_ambush_surprise",
        "targeting": "party",
        "trigger_windows": (CardTriggerWindow.SHORT_REST_PREVIEW,),
        "duration": "current_short_rest",
    },
    "invisibility": {
        "effect_type": "apply_status",
        "targeting": "board_ally",
        "duration": "concentration_up_to_1_hour",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "magic_missile": {
        "effect_type": "automatic_multi_target_damage",
        "targeting": "board_enemies_per_projectile",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "fire_bolt": {
        "effect_type": "spell_attack_damage",
        "targeting": "board_enemy",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "eldritch_blast": {
        "effect_type": "spell_attack_damage",
        "targeting": "board_enemy",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "sacred_flame": {
        "effect_type": "saving_throw_damage",
        "targeting": "board_enemy",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "guiding_bolt": {
        "effect_type": "spell_attack_damage_then_mark",
        "targeting": "board_enemy",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "cure_wounds": {
        "effect_type": "healing",
        "targeting": "board_ally_touch",
        "combat_route": CombatCardRoute.HEALING_SOURCE,
    },
    "healing_word": {
        "effect_type": "healing",
        "targeting": "board_ally",
        "combat_route": CombatCardRoute.HEALING_SOURCE,
    },
    "bless": {
        "effect_type": "grant_roll_bonus",
        "targeting": "board_allies",
        "duration": "concentration_up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "divine_care_aura": {
        "effect_type": "self_centered_enemy_attack_penalty_aura",
        "targeting": "self_aura",
        "duration": "concentration_5_rounds",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "healing_grace_aura": {
        "effect_type": "self_centered_limited_healing_bonus_aura",
        "targeting": "self_aura",
        "duration": "concentration_3_rounds",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "shield_of_faith": {
        "effect_type": "grant_ac_bonus",
        "targeting": "board_ally",
        "duration": "concentration_up_to_10_minutes",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "shield": {
        "effect_type": "reaction_ac_bonus",
        "targeting": "self",
        "trigger_windows": (CardTriggerWindow.ATTACK_ROLL_REVEALED,),
        "duration": "until_next_turn",
        "combat_route": CombatCardRoute.REACTION,
    },
    "misty_step": {
        "effect_type": "teleport",
        "targeting": "board_destination",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "sleep": {
        "effect_type": "hit_point_pool_status_area",
        "targeting": "board_area",
        "duration": "up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "hold_person": {
        "effect_type": "saving_throw_status",
        "targeting": "board_enemy",
        "duration": "concentration_up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "thunderwave": {
        "effect_type": "area_saving_throw_damage_and_push",
        "targeting": "board_area",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "spiritual_weapon": {
        "effect_type": "summon_combat_actor",
        "targeting": "board_summon_position",
        "duration": "up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "acid_arrow": {
        "effect_type": "spell_attack_damage_then_ongoing_damage",
        "targeting": "board_enemy",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "acid_splash": {
        "effect_type": "saving_throw_damage",
        "targeting": "board_enemy",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "burning_hands": {
        "effect_type": "area_saving_throw_damage",
        "targeting": "board_directional_area",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "chill_touch": {
        "effect_type": "spell_attack_damage_then_status",
        "targeting": "board_enemy",
        "duration": "until_next_turn",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "inflict_wounds": {
        "effect_type": "spell_attack_damage",
        "targeting": "board_enemy_touch",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "poison_spray": {
        "effect_type": "saving_throw_damage",
        "targeting": "board_enemy",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "ray_of_frost": {
        "effect_type": "spell_attack_damage_then_slow",
        "targeting": "board_enemy",
        "duration": "until_next_turn",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "scorching_ray": {
        "effect_type": "multi_target_spell_attacks",
        "targeting": "board_enemies_per_projectile",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "shatter": {
        "effect_type": "area_saving_throw_damage",
        "targeting": "board_area",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "shocking_grasp": {
        "effect_type": "spell_attack_damage_then_status",
        "targeting": "board_enemy_touch",
        "duration": "until_next_turn",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "entangle": {
        "effect_type": "persistent_difficult_terrain_and_status_zone",
        "targeting": "board_area",
        "duration": "concentration_up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "grease": {
        "effect_type": "persistent_difficult_terrain_and_status_zone",
        "targeting": "board_area",
        "duration": "up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "web": {
        "effect_type": "persistent_obscuring_difficult_terrain_and_status_zone",
        "targeting": "board_area",
        "duration": "concentration_up_to_1_hour",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "faerie_fire": {
        "effect_type": "area_saving_throw_attack_advantage_status",
        "targeting": "board_area",
        "duration": "concentration_up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "fog_cloud": {
        "effect_type": "persistent_obscuring_zone",
        "targeting": "board_area",
        "duration": "concentration_up_to_1_hour",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "aid": {
        "effect_type": "grant_maximum_and_current_hit_points",
        "targeting": "board_allies",
        "duration": "until_long_rest",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "barkskin": {
        "effect_type": "grant_minimum_armor_class",
        "targeting": "board_ally",
        "duration": "concentration_up_to_1_hour",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "blur": {
        "effect_type": "attacks_against_disadvantage",
        "targeting": "self",
        "duration": "concentration_up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "darkness": {
        "effect_type": "persistent_magical_obscuring_zone",
        "targeting": "board_area",
        "duration": "concentration_up_to_10_minutes",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "darkvision": {
        "effect_type": "grant_darkvision",
        "targeting": "board_ally_touch",
        "duration": "up_to_8_hours",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "false_life": {
        "effect_type": "grant_rolled_temporary_hit_points",
        "targeting": "self",
        "duration": "up_to_1_hour",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "hellish_rebuke": {
        "effect_type": "reaction_saving_throw_damage",
        "targeting": "damage_source",
        "trigger_windows": (CardTriggerWindow.AFTER_DAMAGE_APPLIED,),
        "combat_route": CombatCardRoute.REACTION,
    },
    "heroism": {
        "effect_type": "grant_fear_immunity_and_turn_temporary_hit_points",
        "targeting": "board_ally",
        "duration": "concentration_up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "lesser_restoration": {
        "effect_type": "remove_selected_condition",
        "targeting": "board_ally_then_status",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "mage_armor": {
        "effect_type": "grant_armor_class_base",
        "targeting": "board_unarmored_ally_touch",
        "duration": "up_to_8_hours",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "mirror_image": {
        "effect_type": "grant_attack_redirecting_duplicates",
        "targeting": "self",
        "duration": "up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "protection_from_evil_and_good": {
        "effect_type": "grant_creature_type_protection",
        "targeting": "board_ally_touch",
        "duration": "concentration_up_to_10_minutes",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "protection_from_poison": {
        "effect_type": "neutralize_poison_and_grant_protection",
        "targeting": "board_ally_touch",
        "duration": "up_to_1_hour",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "sanctuary": {
        "effect_type": "require_attacker_saving_throw",
        "targeting": "board_ally",
        "duration": "up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "see_invisibility": {
        "effect_type": "reveal_invisible_and_hidden_creatures",
        "targeting": "self",
        "duration": "up_to_1_hour",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "bane": {
        "effect_type": "saving_throw_roll_penalty",
        "targeting": "board_enemies",
        "duration": "concentration_up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "blindness_deafness": {
        "effect_type": "saving_throw_selected_status",
        "targeting": "board_enemy_then_status",
        "duration": "repeated_save",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "command": {
        "effect_type": "saving_throw_forced_halt",
        "targeting": "board_enemies",
        "duration": "until_next_turn",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "color_spray": {
        "effect_type": "hit_point_pool_status_area",
        "targeting": "board_directional_area",
        "duration": "until_next_turn",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "hideous_laughter": {
        "effect_type": "saving_throw_multi_status",
        "targeting": "board_enemy",
        "duration": "concentration_with_repeated_save",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "ray_of_enfeeblement": {
        "effect_type": "spell_attack_weapon_damage_penalty",
        "targeting": "board_enemy",
        "duration": "concentration_with_repeated_save",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "vicious_mockery": {
        "effect_type": "saving_throw_damage_then_attack_disadvantage",
        "targeting": "board_enemy",
        "duration": "until_next_attack",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "heat_metal": {
        "effect_type": "ongoing_damage_and_attack_disadvantage",
        "targeting": "board_enemy_with_metal",
        "duration": "concentration_up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "moonbeam": {
        "effect_type": "movable_ongoing_damage_zone",
        "targeting": "board_area_or_new_anchor_on_rescan",
        "duration": "concentration_up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "flaming_sphere": {
        "effect_type": "movable_ongoing_damage_zone",
        "targeting": "board_area_or_new_anchor_on_rescan",
        "duration": "concentration_up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "spike_growth": {
        "effect_type": "movement_damage_difficult_terrain_zone",
        "targeting": "board_area",
        "duration": "concentration_up_to_10_minutes",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "silence": {
        "effect_type": "verbal_component_blocking_zone",
        "targeting": "board_area",
        "duration": "concentration_up_to_10_minutes",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "gust_of_wind": {
        "effect_type": "saving_throw_forced_movement",
        "targeting": "board_enemy_then_destination",
        "duration": "concentration_up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "flame_blade": {
        "effect_type": "grant_temporary_spell_weapon",
        "targeting": "self",
        "duration": "concentration_up_to_10_minutes",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "hunters_mark": {
        "effect_type": "mark_target_for_weapon_damage",
        "targeting": "board_enemy",
        "duration": "concentration_up_to_1_hour",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "divine_favor": {
        "effect_type": "grant_weapon_damage_bonus",
        "targeting": "self",
        "duration": "concentration_up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "enlarge_reduce": {
        "effect_type": "selected_size_and_weapon_damage_modifier",
        "targeting": "board_ally_then_variant",
        "duration": "concentration_up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "expeditious_retreat": {
        "effect_type": "grant_bonus_action_dash",
        "targeting": "self",
        "duration": "concentration_up_to_10_minutes",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "levitate": {
        "effect_type": "ignore_difficult_terrain_movement_penalties",
        "targeting": "board_creature",
        "duration": "concentration_up_to_10_minutes",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "magic_weapon": {
        "effect_type": "bind_magic_attack_and_damage_bonus_to_weapon",
        "targeting": "board_ally_then_nonmagical_weapon",
        "duration": "concentration_up_to_1_hour",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "shillelagh": {
        "effect_type": "bind_spellcasting_attack_profile_to_weapon",
        "targeting": "self",
        "duration": "up_to_1_minute",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "true_strike": {
        "effect_type": "grant_next_attack_advantage_against_target",
        "targeting": "board_enemy",
        "duration": "concentration_until_next_attack",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "resistance": {
        "effect_type": "grant_next_saving_throw_die",
        "targeting": "board_ally",
        "duration": "concentration_up_to_1_minute_or_consumed",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "warding_bond": {
        "effect_type": "grant_defense_resistance_and_share_damage",
        "targeting": "board_ally_touch",
        "duration": "up_to_1_hour",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "find_familiar": {
        "effect_type": "select_familiar_combat_status",
        "targeting": "self_then_familiar_form",
        "duration": "until_encounter_end",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "find_traps": {
        "effect_type": "reveal_hidden_traps_in_area",
        "targeting": "board_area",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "goodberry": {
        "effect_type": "create_or_spend_goodberry_pool",
        "targeting": "party_pool_or_board_ally",
        "duration": "up_to_24_hours",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "prayer_of_healing": {
        "effect_type": "long_cast_multi_target_healing",
        "targeting": "board_allies",
        "duration": "instant_after_10_minutes",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "spare_the_dying": {
        "effect_type": "stabilize_dying_ally",
        "targeting": "board_dying_ally_touch",
        "combat_route": CombatCardRoute.COMBAT_ACTION,
    },
    "produce_flame": {
        "effect_type": "spell_attack_damage",
        "targeting": "board_enemy",
        "combat_route": CombatCardRoute.ATTACK_SOURCE,
    },
    "nimra_frost_pulse": {"effect_type": "saving_throw_damage_then_slow", "targeting": "board_enemy", "combat_route": CombatCardRoute.ATTACK_SOURCE},
    "nimra_acid_splash": {"effect_type": "area_saving_throw_damage", "targeting": "board_area", "combat_route": CombatCardRoute.ATTACK_SOURCE},
    "nimra_mind_spike": {"effect_type": "saving_throw_damage_then_status", "targeting": "board_enemy", "combat_route": CombatCardRoute.ATTACK_SOURCE},
    "nimra_flame_fan": {"effect_type": "area_saving_throw_damage", "targeting": "board_directional_area", "combat_route": CombatCardRoute.ATTACK_SOURCE},
    "nimra_force_wave": {"effect_type": "area_saving_throw_damage_and_push", "targeting": "board_directional_area", "combat_route": CombatCardRoute.ATTACK_SOURCE},
    "nimra_lightning_path": {"effect_type": "chain_saving_throw_damage", "targeting": "board_enemy", "combat_route": CombatCardRoute.ATTACK_SOURCE},
    "nimra_mind_break": {"effect_type": "area_saving_throw_damage_then_status", "targeting": "board_area", "combat_route": CombatCardRoute.ATTACK_SOURCE},
    "nimra_sticky_matrix": {"effect_type": "persistent_difficult_terrain_and_status_zone", "targeting": "board_area", "combat_route": CombatCardRoute.COMBAT_ACTION},
    "nimra_sleep": {"effect_type": "sleep_hit_point_pool", "targeting": "board_area", "combat_route": CombatCardRoute.COMBAT_ACTION},
    "nimra_fog": {"effect_type": "persistent_obscuring_zone", "targeting": "board_area", "combat_route": CombatCardRoute.COMBAT_ACTION},
    "nimra_web": {"effect_type": "persistent_obscuring_difficult_terrain_and_status_zone", "targeting": "board_area", "combat_route": CombatCardRoute.COMBAT_ACTION},
    "nimra_stasis": {"effect_type": "saving_throw_status", "targeting": "board_enemy", "combat_route": CombatCardRoute.COMBAT_ACTION},
}


def _phase_for(source_id: str) -> CardPhase:
    if source_id in _BOTH_IDS:
        return CardPhase.BOTH
    if source_id in _COMBAT_IDS:
        return CardPhase.COMBAT
    if source_id in _EXPLORATION_IDS:
        return CardPhase.EXPLORATION
    if source_id in _REMOVED_IDS:
        return CardPhase.REMOVED
    raise KeyError(source_id)


def _qr_kind_for(source_id: str) -> DecisionCardActionKind:
    if source_id in _FEATURE_IDS:
        return DecisionCardActionKind.FEATURE
    return DecisionCardActionKind.SPELL


def _definition(source_id: str) -> CardActionDefinition:
    phase = _phase_for(source_id)
    values: dict[str, object] = {
        "source_id": source_id,
        "qr_kind": _qr_kind_for(source_id),
        "phase": phase,
        "effect_type": "removed" if phase is CardPhase.REMOVED else "legacy_action",
        "action_id": _ACTION_ALIASES.get(source_id, source_id),
    }
    values.update(_PROTOTYPE_OVERRIDES.get(source_id, {}))
    return CardActionDefinition(**values)  # type: ignore[arg-type]


CARD_ACTION_CATALOG = {
    source_id: _definition(source_id)
    for source_id in sorted(_COMBAT_IDS | _EXPLORATION_IDS | _BOTH_IDS | _REMOVED_IDS)
}


# Personal decks use this allow-list for owner-aware QR v2 cards.  It is kept
# separate from D&D class ownership because the seven board-game archetypes
# deliberately remix existing mechanics.
CURATED_CARD_OWNERS: dict[str, tuple[str, ...]] = {
    "second_wind": ("garran",),
    "defensive_stance": ("garran",),
    "action_surge": ("garran",),
    "shield_bash": ("garran",),
    "garran_command_halt": ("garran",),
    "garran_shield_wall": ("garran",),
    "garran_rally": ("garran",),
    "garran_guard_companion": ("garran",),
    "rage": ("brakka",),
    "intimidation": ("brakka",),
    "reckless_attack": ("brakka",),
    "brutal_effort": ("brakka",),
    "powerful_strike": ("brakka",),
    "shoulder_check": ("brakka",),
    "hard_as_rock": ("brakka",),
    "acceleration": ("brakka",),
    "deafening_roar": ("brakka",),
    "thunderwave": ("lorian",),
    "mocking_shot": ("lorian",),
    "provoking_shot": ("lorian",),
    "counterpoint": ("lorian",),
    "distracting_shout": ("lorian",),
    "panic_whisper": ("lorian",),
    "stage_command": ("lorian",),
    "accelerated_refrain": ("lorian",),
    "instinctive_dodge": ("mira",),
    "smoke_screen": ("mira",),
    "hamstring_cut": ("mira",),
    "piercing_attack": ("mira",),
    "guard_vault": ("mira",),
    "blade_mistress": ("mira",),
    "combat_trap_detection": ("mira",),
    "cunning_action": ("erynd",),
    "disguise_self": ("mira", "lorian"),
    "sacred_flame": ("dagna",),
    "healing_word": ("dagna",),
    "bless": ("dagna",),
    "divine_care_aura": ("dagna",),
    "healing_grace_aura": ("dagna",),
    "guidance": ("dagna",),
    "preserve_life": ("dagna",),
    "sanctuary": ("dagna",),
    "guiding_bolt": ("dagna",),
    "aid": ("dagna",),
    "lesser_restoration": ("dagna",),
    "spiritual_weapon": ("dagna",),
    "prayer_of_healing": ("dagna",),
    "bardic_inspiration": ("lorian",),
    "optical_scope": ("lorian",),
    "entangling_shot": ("lorian",),
    "true_strike": ("erynd",),
    "mage_hand": ("lorian", "nimra"),
    "faerie_fire": ("lorian",),
    "hideous_laughter": ("lorian",),
    "cutting_words": ("lorian",),
    "calm_emotions": ("lorian",),
    "suggestion": ("lorian",),
    "enhance_ability": ("lorian",),
    "ray_of_frost": ("nimra",),
    "grease": ("nimra",),
    "entangle": ("nimra",),
    "shield": ("nimra",),
    "detect_magic": ("nimra",),
    "sleep": ("nimra",),
    "fog_cloud": ("nimra",),
    "identify": ("nimra",),
    "alarm": ("nimra",),
    "web": ("nimra",),
    "hold_person": ("nimra",),
    "misty_step": ("nimra", "erynd"),
    "shatter": ("nimra",),
    "nimra_frost_pulse": ("nimra",),
    "nimra_acid_splash": ("nimra",),
    "nimra_mind_spike": ("nimra",),
    "nimra_flame_fan": ("nimra",),
    "nimra_force_wave": ("nimra",),
    "nimra_sticky_matrix": ("nimra",),
    "nimra_sleep": ("nimra",),
    "nimra_fog": ("nimra",),
    "nimra_web": ("nimra",),
    "nimra_lightning_path": ("nimra",),
    "nimra_mind_break": ("nimra",),
    "nimra_stasis": ("nimra",),
    "nimra_sculpt_field": ("nimra",),
    "nimra_distant_spell": ("nimra",),
    "nimra_overcharged_spell": ("nimra",),
    "nimra_forced_weave": ("nimra",),
    "nimra_energy_transmutation": ("nimra",),
    "hunters_mark": ("erynd",),
    "aim": ("erynd",),
    "anchoring_arrow": ("erynd",),
    "exposing_arrow": ("erynd",),
    "disrupting_arrow": ("erynd",),
    "double_shot": ("erynd",),
    "spike_growth": ("erynd",),
}


def card_action_definition(
    source_id: str,
    *,
    qr_kind: DecisionCardActionKind | None = None,
) -> CardActionDefinition:
    try:
        definition = CARD_ACTION_CATALOG[source_id]
    except KeyError as exc:
        raise ValueError("Ta karta nie należy do zatwierdzonego katalogu akcji.") from exc
    if qr_kind is not None and definition.qr_kind is not qr_kind:
        raise ValueError("Rodzaj kodu QR nie pasuje do definicji karty.")
    return definition


def validate_card_phase(definition: CardActionDefinition, phase: CardPhase) -> None:
    if not definition.playable:
        raise ValueError("Ta karta została wycofana z gry i nie można jej użyć.")
    if definition.phase not in {phase, CardPhase.BOTH}:
        expected = "walki" if definition.phase is CardPhase.COMBAT else "eksploracji"
        raise ValueError(f"Tej karty można użyć wyłącznie podczas {expected}.")


__all__ = [
    "CARD_ACTION_CATALOG",
    "CURATED_CARD_OWNERS",
    "CardActionDefinition",
    "CardPhase",
    "CardTriggerWindow",
    "CombatCardRoute",
    "card_action_definition",
    "validate_card_phase",
]
