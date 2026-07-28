"""Authoritative migration plan for SRD spells still using assisted casts.

The family is not an implementation claim.  It tells the implementation audit
which deterministic resolver boundary a spell should move to.  Every entry also
has a stable scene flag, so a deliberately narrative remainder can still be
grounded by authored content and the GM classifier.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from pathlib import Path

from .srd_manifest import SRD_SPELL_IDS_BY_LEVEL


class AssistedSpellFamily(StrEnum):
    DAMAGE = "damage"
    CONDITION = "condition"
    BUFF = "buff"
    SUMMON = "summon"
    EXPLORATION = "exploration"
    NARRATIVE = "narrative"


@dataclass(frozen=True, slots=True)
class AssistedSpellPlan:
    spell_id: str
    family: AssistedSpellFamily
    resolver_id: str

    @property
    def cast_flag(self) -> str:
        return f"cast_{self.spell_id}"


_SPELL_IDS_BY_FAMILY: dict[AssistedSpellFamily, tuple[str, ...]] = {
    AssistedSpellFamily.DAMAGE: (
        "acid_arrow",
        "branding_smite",
        "flame_blade",
        "flaming_sphere",
        "guiding_bolt",
        "heat_metal",
        "hellish_rebuke",
        "magic_missile",
        "moonbeam",
        "scorching_ray",
        "spiritual_weapon",
        "thunderwave",
    ),
    AssistedSpellFamily.CONDITION: (
        "animal_friendship",
        "bane",
        "blindness_deafness",
        "calm_emotions",
        "charm_person",
        "color_spray",
        "command",
        "entangle",
        "enthrall",
        "faerie_fire",
        "grease",
        "hideous_laughter",
        "hold_person",
        "ray_of_enfeeblement",
        "sleep",
        "web",
        "zone_of_truth",
    ),
    AssistedSpellFamily.BUFF: (
        "aid",
        "barkskin",
        "bless",
        "blur",
        "darkness",
        "darkvision",
        "divine_favor",
        "enhance_ability",
        "enlarge_reduce",
        "expeditious_retreat",
        "false_life",
        "feather_fall",
        "fog_cloud",
        "guidance",
        "gust_of_wind",
        "heroism",
        "hunters_mark",
        "invisibility",
        "jump",
        "lesser_restoration",
        "levitate",
        "longstrider",
        "mage_armor",
        "magic_weapon",
        "mirror_image",
        "pass_without_trace",
        "protection_from_evil_and_good",
        "protection_from_poison",
        "resistance",
        "sanctuary",
        "shield_of_faith",
        "shillelagh",
        "silence",
        "spider_climb",
        "spike_growth",
        "true_strike",
        "warding_bond",
    ),
    AssistedSpellFamily.SUMMON: (
        "find_familiar",
        "find_steed",
        "floating_disk",
        "unseen_servant",
    ),
    AssistedSpellFamily.EXPLORATION: (
        "alarm",
        "arcane_lock",
        "continual_flame",
        "create_or_destroy_water",
        "detect_evil_and_good",
        "detect_magic",
        "detect_poison_and_disease",
        "find_traps",
        "gentle_repose",
        "goodberry",
        "identify",
        "knock",
        "locate_animals_or_plants",
        "locate_object",
        "prayer_of_healing",
        "purify_food_and_drink",
        "rope_trick",
        "see_invisibility",
        "speak_with_animals",
    ),
    AssistedSpellFamily.NARRATIVE: (
        "alter_self",
        "animal_messenger",
        "arcanists_magic_aura",
        "augury",
        "detect_thoughts",
        "disguise_self",
        "illusory_script",
        "magic_mouth",
        "silent_image",
        "suggestion",
    ),
}

_RESOLVER_GROUPS: dict[str, tuple[str, ...]] = {
    "attack_damage": ("acid_arrow", "guiding_bolt", "scorching_ray"),
    "weapon_rider": ("branding_smite", "divine_favor", "hunters_mark"),
    "persistent_damage": (
        "flame_blade",
        "flaming_sphere",
        "heat_metal",
        "moonbeam",
        "spiritual_weapon",
    ),
    "reaction_damage": ("hellish_rebuke",),
    "area_save_damage": ("thunderwave", "spike_growth"),
    "multi_target_damage": ("magic_missile",),
    "save_condition": (
        "bane",
        "blindness_deafness",
        "calm_emotions",
        "charm_person",
        "color_spray",
        "command",
        "entangle",
        "enthrall",
        "faerie_fire",
        "grease",
        "hideous_laughter",
        "hold_person",
        "ray_of_enfeeblement",
        "sleep",
        "web",
        "zone_of_truth",
    ),
    "targeted_exploration_save": ("animal_friendship", "suggestion"),
    "hit_point_buff": ("aid", "false_life", "heroism"),
    "armor_class_buff": (
        "barkskin",
        "blur",
        "mage_armor",
        "magic_weapon",
        "mirror_image",
        "shield_of_faith",
        "warding_bond",
    ),
    "roll_die_buff": ("bless", "guidance", "resistance", "true_strike"),
    "vision_or_obscurement": (
        "darkness",
        "darkvision",
        "fog_cloud",
        "invisibility",
        "see_invisibility",
        "silence",
    ),
    "movement_buff": (
        "expeditious_retreat",
        "feather_fall",
        "gust_of_wind",
        "jump",
        "levitate",
        "longstrider",
        "spider_climb",
    ),
    "ability_or_form_buff": (
        "alter_self",
        "enhance_ability",
        "enlarge_reduce",
        "pass_without_trace",
        "protection_from_evil_and_good",
        "protection_from_poison",
        "sanctuary",
        "shillelagh",
    ),
    "condition_removal": ("lesser_restoration",),
    "creature_summon": ("find_familiar", "find_steed"),
    "utility_summon": ("floating_disk", "unseen_servant"),
    "authored_scene_flag": (
        "alarm",
        "animal_messenger",
        "arcane_lock",
        "arcanists_magic_aura",
        "augury",
        "continual_flame",
        "create_or_destroy_water",
        "detect_evil_and_good",
        "detect_magic",
        "detect_poison_and_disease",
        "detect_thoughts",
        "disguise_self",
        "find_traps",
        "gentle_repose",
        "goodberry",
        "identify",
        "illusory_script",
        "knock",
        "locate_animals_or_plants",
        "locate_object",
        "magic_mouth",
        "prayer_of_healing",
        "purify_food_and_drink",
        "rope_trick",
        "silent_image",
        "speak_with_animals",
    ),
}

_RESOLVER_BY_SPELL = {
    spell_id: resolver_id
    for resolver_id, spell_ids in _RESOLVER_GROUPS.items()
    for spell_id in spell_ids
}

ASSISTED_SPELL_PLANS = tuple(
    AssistedSpellPlan(
        spell_id,
        family,
        _RESOLVER_BY_SPELL[spell_id],
    )
    for family, spell_ids in _SPELL_IDS_BY_FAMILY.items()
    for spell_id in spell_ids
)


@dataclass(frozen=True, slots=True)
class AssistedSpellAudit:
    assisted_spell_ids: tuple[str, ...]
    missing_plan_ids: tuple[str, ...]
    stale_plan_ids: tuple[str, ...]
    duplicate_plan_ids: tuple[str, ...]
    missing_resolver_ids: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not (
            self.missing_plan_ids
            or self.stale_plan_ids
            or self.duplicate_plan_ids
            or self.missing_resolver_ids
        )


def audit_assisted_spell_plans(spells_root: str | Path) -> AssistedSpellAudit:
    canonical_ids = {
        spell_id
        for spell_ids in SRD_SPELL_IDS_BY_LEVEL.values()
        for spell_id in spell_ids
    }
    assisted_ids: set[str] = set()
    for path in Path(spells_root).glob("*.json"):
        raw = json.loads(path.read_text(encoding="utf-8"))
        spell_id = raw.get("id")
        effect = raw.get("effect")
        if (
            spell_id in canonical_ids
            and isinstance(effect, dict)
            and effect.get("kind") == "assisted"
        ):
            assisted_ids.add(str(spell_id))
    plan_ids = tuple(plan.spell_id for plan in ASSISTED_SPELL_PLANS)
    duplicates = tuple(
        sorted(
            spell_id
            for spell_id in set(plan_ids)
            if plan_ids.count(spell_id) > 1
        )
    )
    return AssistedSpellAudit(
        assisted_spell_ids=tuple(sorted(assisted_ids)),
        missing_plan_ids=tuple(sorted(assisted_ids - set(plan_ids))),
        stale_plan_ids=tuple(sorted(set(plan_ids) - canonical_ids)),
        duplicate_plan_ids=duplicates,
        missing_resolver_ids=tuple(
            sorted(
                plan.spell_id
                for plan in ASSISTED_SPELL_PLANS
                if not plan.resolver_id.strip()
            )
        ),
    )


def assisted_spell_plan(spell_id: str) -> AssistedSpellPlan | None:
    return next(
        (plan for plan in ASSISTED_SPELL_PLANS if plan.spell_id == spell_id),
        None,
    )


__all__ = [
    "ASSISTED_SPELL_PLANS",
    "AssistedSpellAudit",
    "AssistedSpellFamily",
    "AssistedSpellPlan",
    "assisted_spell_plan",
    "audit_assisted_spell_plans",
]
