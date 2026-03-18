from __future__ import annotations

from damage_types import DamageType

from ..registry import register_event
from .base_attack_range_event import BaseRangeAttackEvent
from .basic_melee_attack_event import BasicMeleeAttackEvent


@register_event
class LongswordAttackEvent(BasicMeleeAttackEvent):
    name = "longsword"
    weapon_label = "longswordem"
    damage_prompt = "1k8 + STR"
    action_id_base = "attack_longsword"
    default_tags = ["attack_melee", "longsword", "versatile:p"]
    damage_type = DamageType.SLASHING.value


@register_event
class ClubAttackEvent(BasicMeleeAttackEvent):
    name = "club"
    weapon_label = "maczugą"
    damage_prompt = "1k6 + STR"
    action_id_base = "attack_club"
    default_tags = ["attack_melee", "club"]
    damage_type = DamageType.BLUDGEONING.value


@register_event
class SpearAttackEvent(BasicMeleeAttackEvent):
    name = "spear"
    weapon_label = "włócznią"
    damage_prompt = "1k6 + STR"
    action_id_base = "attack_spear"
    default_tags = ["attack_melee", "spear", "thrown:20"]
    damage_type = DamageType.PIERCING.value


@register_event
class ShortswordAttackEvent(BasicMeleeAttackEvent):
    name = "shortsword"
    weapon_label = "krótkim mieczem"
    damage_prompt = "1k6 + STR"
    action_id_base = "attack_shortsword"
    default_tags = ["attack_melee", "shortsword", "agile", "finesse", "versatile:s"]
    damage_type = DamageType.PIERCING.value


@register_event
class RapierAttackEvent(BasicMeleeAttackEvent):
    name = "rapier"
    weapon_label = "rapierem"
    damage_prompt = "1k6 + STR"
    action_id_base = "attack_rapier"
    default_tags = ["attack_melee", "rapier", "deadly:d8", "disarm", "finesse"]
    damage_type = DamageType.PIERCING.value


@register_event
class GreataxeAttackEvent(BasicMeleeAttackEvent):
    name = "greataxe"
    weapon_label = "wielkim toporem"
    damage_prompt = "1k12 + STR"
    action_id_base = "attack_greataxe"
    default_tags = ["attack_melee", "greataxe", "sweep"]
    damage_type = DamageType.SLASHING.value


@register_event
class WarhammerAttackEvent(BasicMeleeAttackEvent):
    name = "warhammer"
    weapon_label = "młotem wojennym"
    damage_prompt = "1k8 + STR"
    action_id_base = "attack_warhammer"
    default_tags = ["attack_melee", "warhammer", "shove"]
    damage_type = DamageType.BLUDGEONING.value


@register_event
class HalberdAttackEvent(BasicMeleeAttackEvent):
    name = "halberd"
    weapon_label = "halabardą"
    damage_prompt = "1k10 + STR"
    action_id_base = "attack_halberd"
    default_tags = ["attack_melee", "halberd", "reach:10", "trip", "versatile:p"]
    damage_type = DamageType.SLASHING.value


@register_event
class GlaiveAttackEvent(BasicMeleeAttackEvent):
    name = "glaive"
    weapon_label = "glewią"
    damage_prompt = "1k8 + STR"
    action_id_base = "attack_glaive"
    default_tags = ["attack_melee", "glaive", "reach:10", "deadly:d8"]
    damage_type = DamageType.SLASHING.value


@register_event
class MaceAttackEvent(BasicMeleeAttackEvent):
    name = "mace"
    weapon_label = "buzdyganem"
    damage_prompt = "1k6 + STR"
    action_id_base = "attack_mace"
    default_tags = ["attack_melee", "mace", "shove"]
    damage_type = DamageType.BLUDGEONING.value


@register_event
class JavelinAttackEvent(BaseRangeAttackEvent):
    name = "javelin"
    weapon_label = "oszczepem"
    damage_prompt = "1k6 + STR"
    action_id_base = "attack_javelin"
    damage_type = DamageType.PIERCING.value
    range_increment_ft = 30
    default_tags = ["attack_ranged", "ranged_attack", "javelin", "spear", "thrown:30"]


@register_event
class ShortbowAttackEvent(BaseRangeAttackEvent):
    name = "shortbow"
    weapon_label = "krótkim łukiem"
    damage_prompt = "1k6"
    action_id_base = "attack_shortbow"
    damage_type = DamageType.PIERCING.value
    range_increment_ft = 60
    default_tags = ["attack_ranged", "ranged_attack", "bow", "shortbow", "deadly:d10"]


@register_event
class LightCrossbowAttackEvent(BaseRangeAttackEvent):
    name = "light_crossbow"
    weapon_label = "lekką kuszą"
    damage_prompt = "1k8"
    action_id_base = "attack_light_crossbow"
    damage_type = DamageType.PIERCING.value
    range_increment_ft = 120
    default_tags = ["attack_ranged", "ranged_attack", "crossbow", "simple_crossbow", "light_crossbow", "reload:1"]
