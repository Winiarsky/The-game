"""Executable consumer registry for data-driven SRD combat spell effects."""

from __future__ import annotations

from typing import Mapping


SPECIALIZED_ACTION_CONSUMERS: Mapping[str, str] = {
    "multi_target_damage": "player_multi_target_spell_flow",
    "reaction_ac_bonus": "combat_reaction_flow",
    "reaction_damage": "combat_reaction_flow",
    "spell_debuff": "spell_debuff_flow",
    "spell_movement": "magic_movement_flow",
    "stabilize": "combat_stabilization_flow",
    "summon": "summoning_flow",
}

EFFECT_KIND_CONSUMERS: Mapping[str, str] = {
    "ability_check_advantage": "exploration_check_plans",
    "apply_condition": "conditions",
    "attacks_against_advantage": "scene_interactions",
    "attacks_against_disadvantage": "scene_interactions",
    "bane_roll_penalty": "physical_roll_inputs",
    "bless_roll_bonus": "physical_roll_inputs",
    "bless_aura_source": "spell_auras",
    "bonus_action_dash": "combat_session",
    "branding_smite": "scene_interactions",
    "darkvision": "exploration_visibility",
    "divine_favor_damage": "scene_interactions",
    "divine_care_aura_source": "spell_auras",
    "enlarge_reduce": "scene_interactions",
    "feather_fall": "exploration_hazard_flow",
    "familiar": "player_combat_resource_flow",
    "flame_blade": "scene_interactions",
    "guidance_roll_bonus": "physical_roll_inputs",
    "goodberry_pool": "player_combat_resource_flow",
    "heroism_temp_hp": "player_combat_resource_flow",
    "healing_grace_aura_source": "spell_auras",
    "hunters_mark": "scene_interactions",
    "invisibility": "scene_interactions",
    "jump_multiplier": "class_feature_rules",
    "levitate": "conditions",
    "mage_armor_base": "armor_class",
    "magic_weapon": "scene_interactions",
    "max_hit_points_bonus": "player_combat_resource_flow",
    "minimum_armor_class": "armor_class",
    "mirror_image": "scene_interactions",
    "next_attack_advantage": "scene_interactions",
    "obscuring_zone": "scene_interactions",
    "ongoing_damage": "turn_effects",
    "ongoing_damage_zone": "spell_zones",
    "protection_from_evil_and_good": "scene_interactions",
    "protection_from_poison": "poison_protection",
    "prayer_healing": "player_combat_resource_flow",
    "remove_condition": "conditions",
    "resistance_roll_bonus": "physical_roll_inputs",
    "reveal_hidden_traps": "player_combat_resource_flow",
    "sanctuary": "player_combat_action_flow",
    "see_invisibility": "scene_interactions",
    "shillelagh": "scene_interactions",
    "silence_zone": "silence",
    "speed_bonus": "conditions",
    "spell_ac_bonus": "armor_class",
    "spider_climb": "class_feature_rules",
    "spike_growth_zone": "combat_movement_flow",
    "stealth_bonus_aura": "precombat_stealth_flow",
    "temporary_hit_points": "player_combat_resource_flow",
    "warding_bond": "damage_sharing",
    "web_zone": "web_zone",
    "zone_of_truth_zone": "zone_of_truth",
}


def consumer_for_combat_effect(effect: Mapping[str, object]) -> str | None:
    """Return the stable resolver boundary for one authored combat effect."""

    action_type = str(effect.get("action_type", ""))
    specialized = SPECIALIZED_ACTION_CONSUMERS.get(action_type)
    if specialized is not None:
        return specialized
    effect_kind = str(effect.get("effect_kind", ""))
    return EFFECT_KIND_CONSUMERS.get(effect_kind)


__all__ = [
    "EFFECT_KIND_CONSUMERS",
    "SPECIALIZED_ACTION_CONSUMERS",
    "consumer_for_combat_effect",
]
