"""Executable combat sources granted by SRD species traits."""

from __future__ import annotations

from dnd_board_game.actors import Actor, actor_has_feature
from dnd_board_game.rules import D20RollRequest, DiceExpression

from .attack_flow import AttackKind, AttackSource, AttackSourceType
from .damage import DamageComponentSpec, DamageType
from .spells import SpellArea, SpellAreaShape, SpellAreaTargetMode


def breath_weapon_attack_source(actor: Actor) -> AttackSource | None:
    """Return the selected dragonborn ancestry breath as an area save source."""
    if not actor_has_feature(actor, "breath_weapon"):
        return None
    profile = _breath_profile(actor)
    if profile is None:
        return None
    damage_type, shape, save_ability = profile
    area = SpellArea(
        shape=shape,
        length_feet=30 if shape == SpellAreaShape.LINE else 15,
        width_feet=5,
        target_mode=SpellAreaTargetMode.ALL_CREATURES,
    )
    component = DamageComponentSpec(
        id="base",
        damage_type=damage_type,
        dice=DiceExpression(2, 6),
        label="Broń oddechowa",
    )
    return AttackSource(
        id="breath_weapon",
        name="Broń oddechowa",
        source_type=AttackSourceType.CUSTOM,
        range_feet=area.length_feet,
        attack_kind=AttackKind.RANGED,
        attack_roll_request=D20RollRequest(),
        damage_type=damage_type.value,
        damage_die_sides=6,
        damage_components=(component,),
        area=area,
        save_ability=save_ability,
        save_dc=(
            8
            + actor.proficiency_bonus
            + (actor.ability_scores.constitution - 10) // 2
        ),
        save_damage_on_success="half",
        resource_pool_id="breath_weapon_uses",
    )


def _breath_profile(
    actor: Actor,
) -> tuple[DamageType, SpellAreaShape, str] | None:
    for feature in actor.features:
        feature_id = feature.feature_id
        if not feature_id.startswith("breath_weapon_") or feature_id == "breath_weapon":
            continue
        parts = feature_id.split("_")
        if len(parts) != 5:
            continue
        _, _, damage_id, shape_id, save_id = parts
        return (
            DamageType(damage_id),
            SpellAreaShape(shape_id),
            {"dex": "dexterity", "con": "constitution"}[save_id],
        )
    return None
