"""D&D 5e 2014 level-1 Fighting Style attack transformations."""

from __future__ import annotations

from dataclasses import replace

from dnd_board_game.actors import Actor, actor_has_feature
from dnd_board_game.inventory import hands_required, normalize_hand_equipment
from dnd_board_game.rules import RollModifier, RollModifierType

from .attack_flow import AttackKind, AttackSource, AttackSourceType


def apply_fighting_style_to_attack_source(
    actor: Actor,
    source: AttackSource,
) -> AttackSource:
    if source.source_type != AttackSourceType.WEAPON:
        return source
    if (
        actor_has_feature(actor, "fighting_style_archery")
        and source.attack_kind == AttackKind.RANGED
    ):
        modifier = RollModifier(
            "Fighting Style: Archery",
            2,
            RollModifierType.FEATURE,
            stacking_key="fighting_style_archery",
        )
        return replace(
            source,
            attack_roll_request=replace(
                source.attack_roll_request,
                modifiers=(*source.attack_roll_request.modifiers, modifier),
            ),
        )
    if actor_has_feature(actor, "fighting_style_dueling") and _dueling_is_active(
        actor,
        source,
    ):
        components = tuple(
            replace(component, modifier=component.modifier + 2)
            if component.id == "base"
            else component
            for component in source.damage_components
        )
        return replace(
            source,
            damage_modifier=source.damage_modifier + 2,
            damage_components=components,
            damage_hint=f"{source.damage_hint} + 2 (Fighting Style: Dueling)",
        )
    return source


def _dueling_is_active(actor: Actor, source: AttackSource) -> bool:
    if source.attack_kind != AttackKind.MELEE or source.source_item_id is None:
        return False
    held = tuple(
        item
        for item in normalize_hand_equipment(actor.inventory)
        if item.available and item.equipped and item.held_in
    )
    weapon = next(
        (
            item
            for item in held
            if item.id == source.source_item_id or item.source_ref == source.source_item_id
        ),
        None,
    )
    if weapon is None or weapon.kind != "weapon" or hands_required(weapon) != 1:
        return False
    return not any(item.kind == "weapon" and item.id != weapon.id for item in held)
