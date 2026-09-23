from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Sequence

from dnd_board_game.actors import Actor
from dnd_board_game.inventory import effective_armor_class
from dnd_board_game.rules import ActiveEffect, ability_modifier
from dnd_board_game.world import Coordinate


class CombatTargetType(StrEnum):
    ACTOR = "actor"
    OBJECT = "object"
    TERRAIN = "terrain"
    INTERACTABLE = "interactable"


class CombatTargetVisibility(StrEnum):
    VISIBLE = "visible"
    HIDDEN = "hidden"
    CONDITIONAL = "conditional"


@dataclass(frozen=True, slots=True)
class CombatTarget:
    id: str
    name: str
    position: Coordinate
    ac: int
    hp: int
    target_type: CombatTargetType
    visibility: CombatTargetVisibility = CombatTargetVisibility.VISIBLE
    attackable: bool = True
    max_hp: int = 0
    temp_hp: int = 0
    defeated: bool = False
    unconscious: bool = False

    def __post_init__(self) -> None:
        if self.max_hp <= 0:
            object.__setattr__(self, "max_hp", max(0, self.hp))


def combat_effect_armor_class_bonus(
    actor: Actor,
    active_effects: tuple[ActiveEffect, ...] = (),
) -> int:
    from .runes import uses_runes
    if uses_runes(actor):
        kinds = {"spell_ac_bonus", "charge_ac", "iron_bastion_member", "garran_defensive_stance_ac", "garran_shield_wall_member"}
        bonus = max((e.value for e in active_effects if e.actor_id == str(actor.id) and e.kind in kinds), default=0)
        penalty = sum(e.value for e in active_effects if e.actor_id == str(actor.id) and e.kind == "erynd_exposed_ac")
        return bonus - penalty
    return (
        sum(
            effect.value
            for effect in active_effects
            if effect.actor_id == str(actor.id)
            and effect.kind in {
                "spell_ac_bonus",
                "charge_ac",
                "iron_bastion_member",
                "garran_defensive_stance_ac",
                "garran_shield_wall_member",
            }
        )
        - sum(
            effect.value
            for effect in active_effects
            if effect.actor_id == str(actor.id)
            and effect.kind == "erynd_exposed_ac"
        )
    )


def combat_armor_class(
    actor: Actor,
    active_effects: tuple[ActiveEffect, ...] = (),
) -> int:
    armor_class = int(any(e.kind == "mana_wave_4" for e in active_effects)) + effective_armor_class(actor) + combat_effect_armor_class_bonus(
        actor,
        active_effects,
    )
    barkskin_minimum = max(
        (
            effect.value
            for effect in active_effects
            if effect.actor_id == str(actor.id)
            and effect.kind == "minimum_armor_class"
        ),
        default=0,
    )
    mage_armor_base = max(
        (
            effect.value
            for effect in active_effects
            if effect.actor_id == str(actor.id)
            and effect.kind == "mage_armor_base"
        ),
        default=0,
    )
    wears_armor = any(
        item.available
        and item.equipped
        and item.kind == "armor"
        for item in actor.inventory
    )
    mage_armor_class = (
        mage_armor_base + ability_modifier(actor.ability_scores.dexterity)
        if mage_armor_base and not wears_armor
        else 0
    )
    warding_bond_bonus = sum(
        effect.value
        for effect in active_effects
        if effect.actor_id == str(actor.id)
        and effect.kind == "warding_bond"
    )
    return max(armor_class, barkskin_minimum, mage_armor_class) + warding_bond_bonus


def actor_as_combat_target(
    actor: Actor,
    active_effects: tuple[ActiveEffect, ...] = (),
    *,
    attacker: Actor | None = None,
    actors: Sequence[Actor] = (),
    opportunity_attack: bool = False,
) -> CombatTarget:
    contextual_ac = 0
    if opportunity_attack:
        if any(
            feature.feature_id == "halfling_nimbleness"
            for feature in actor.features
        ):
            contextual_ac += 1
        if attacker is not None:
            contextual_ac += sum(
                effect.value
                for effect in active_effects
                if effect.actor_id == str(actor.id)
                and effect.target_actor_id == str(attacker.id)
                and effect.kind == "guard_vault_opportunity_ac"
            )
    if attacker is not None:
        contextual_ac += iron_line_armor_class_bonus(attacker, actor, actors)
    return CombatTarget(
        id=str(actor.id),
        name=actor.name,
        position=actor.position,
        ac=combat_armor_class(actor, active_effects) + contextual_ac,
        hp=actor.hp,
        target_type=CombatTargetType.ACTOR,
        visibility=CombatTargetVisibility.VISIBLE,
        attackable=not actor.is_dead(),
        max_hp=actor.max_hp,
        temp_hp=actor.temp_hp,
        defeated=actor.is_defeated(),
        unconscious=actor.is_unconscious(),
    )


def mira_ranged_armor_class_bonus(actor: Actor, source: object) -> int:
    """Return Mira's contextual AC bonus against ranged attack rolls only."""

    if not any(
        feature.feature_id == "mira_ranged_evasion" for feature in actor.features
    ):
        return 0
    attack_kind = getattr(getattr(source, "attack_kind", None), "value", "")
    save_ability = getattr(source, "save_ability", None)
    return 2 if attack_kind == "ranged" and save_ability is None else 0


def iron_line_armor_class_bonus(
    attacker: Actor,
    target: Actor,
    actors: Sequence[Actor],
) -> int:
    """Grant the ally +1 AC while the ally and Garran flank this attacker."""
    if attacker.faction == target.faction or target.is_defeated():
        return 0
    target_delta = (
        target.position.col - attacker.position.col,
        target.position.row - attacker.position.row,
    )
    if max(abs(target_delta[0]), abs(target_delta[1])) != 1:
        return 0
    for protector in actors:
        if protector.id == target.id or protector.faction != target.faction:
            continue
        if protector.is_defeated() or not any(
            feature.feature_id == "iron_line" for feature in protector.features
        ):
            continue
        protector_delta = (
            protector.position.col - attacker.position.col,
            protector.position.row - attacker.position.row,
        )
        if protector_delta == (-target_delta[0], -target_delta[1]):
            return 1
    return 0


def target_is_defeated(target: CombatTarget) -> bool:
    return target.hp <= 0


def is_public_attack_target(target: CombatTarget) -> bool:
    return target.attackable and target.visibility == CombatTargetVisibility.VISIBLE
