from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dnd_board_game.combat.attack_flow import AttackKind, effective_attack_kind

from .base import ActionResource, CombatActionMechanic, MechanicScope, TargetingMode


@dataclass(frozen=True, slots=True)
class AttackMechanic(CombatActionMechanic):
    pass


@dataclass(frozen=True, slots=True)
class BasicAttack(AttackMechanic):
    pass


@dataclass(frozen=True, slots=True)
class MeleeAttack(BasicAttack):
    pass


@dataclass(frozen=True, slots=True)
class RangedAttack(BasicAttack):
    pass


@dataclass(frozen=True, slots=True)
class SpellAttack(AttackMechanic):
    pass


@dataclass(frozen=True, slots=True)
class SpellAttackRoll(SpellAttack):
    pass


@dataclass(frozen=True, slots=True)
class SpellSaveAttack(SpellAttack):
    pass


@dataclass(frozen=True, slots=True)
class AreaSpellAttack(SpellSaveAttack):
    pass


@dataclass(frozen=True, slots=True)
class OpportunityAttack(MeleeAttack):
    pass


@dataclass(frozen=True, slots=True)
class ReadyAttack(AttackMechanic):
    pass


def attack_mechanic_from_source(source: Any) -> AttackMechanic:
    source_type = getattr(getattr(source, "source_type", None), "value", str(getattr(source, "source_type", "")))
    source_id = str(getattr(source, "id", "") or getattr(source, "name", "attack")).strip() or "attack"
    name = str(getattr(source, "name", "Atak"))
    tags = _attack_tags(source)
    if getattr(source, "area", None) is not None:
        return AreaSpellAttack(
            id=f"attack.{source_id}",
            name=name,
            scope=MechanicScope.COMBAT,
            resource=ActionResource.ACTION,
            targeting=TargetingMode.AREA,
            summary="Czar obszarowy wskazuje środek albo kierunek na planszy, potem rozstrzyga cele w obszarze.",
            tags=tags,
        )
    if source_type == "spell" and getattr(source, "save_ability", None):
        return SpellSaveAttack(
            id=f"attack.{source_id}",
            name=name,
            scope=MechanicScope.COMBAT,
            resource=ActionResource.ACTION,
            targeting=TargetingMode.ENEMY,
            summary="Czar przeciw pojedynczemu celowi rozstrzygany rzutem obronnym celu.",
            tags=tags,
        )
    if source_type == "spell":
        return SpellAttackRoll(
            id=f"attack.{source_id}",
            name=name,
            scope=MechanicScope.COMBAT,
            resource=ActionResource.ACTION,
            targeting=TargetingMode.ENEMY,
            summary="Czar przeciw pojedynczemu celowi rozstrzygany rzutem ataku.",
            tags=tags,
        )
    if effective_attack_kind(source) == AttackKind.MELEE:
        return MeleeAttack(
            id=f"attack.{source_id}",
            name=name,
            scope=MechanicScope.COMBAT,
            resource=ActionResource.ACTION,
            targeting=TargetingMode.ENEMY,
            summary="Atak wręcz przeciw żywemu przeciwnikowi w zasięgu broni.",
            tags=tags,
        )
    return RangedAttack(
        id=f"attack.{source_id}",
        name=name,
        scope=MechanicScope.COMBAT,
        resource=ActionResource.ACTION,
        targeting=TargetingMode.ENEMY,
        summary="Atak dystansowy przeciw widocznemu przeciwnikowi w zasięgu i linii efektu.",
        tags=tags,
    )


def opportunity_attack_mechanic() -> OpportunityAttack:
    return OpportunityAttack(
        id="reaction.opportunity_attack",
        name="Atak okazyjny",
        scope=MechanicScope.COMBAT,
        resource=ActionResource.REACTION,
        targeting=TargetingMode.ENEMY,
        summary="Reakcja przeciw przeciwnikowi opuszczającemu zasięg wręcz/reach.",
        tags=("reaction", "melee", "movement_trigger"),
    )


def ready_attack_mechanic() -> ReadyAttack:
    return ReadyAttack(
        id="action.ready_attack",
        name="Ready: przygotowany atak",
        scope=MechanicScope.COMBAT,
        resource=ActionResource.ACTION,
        targeting=TargetingMode.ENEMY,
        summary="Akcja główna przygotowuje atak, który może zostać wykonany później reakcją.",
        tags=("ready", "reaction_trigger"),
    )


def _attack_tags(source: Any) -> tuple[str, ...]:
    tags = ["attack"]
    source_type = getattr(getattr(source, "source_type", None), "value", str(getattr(source, "source_type", "")))
    if source_type:
        tags.append(source_type)
    if getattr(source, "area", None) is not None:
        tags.append("area")
    if getattr(source, "save_ability", None):
        tags.append("saving_throw")
    if getattr(source, "spell_level", 0):
        tags.append("spell_slot")
    if effective_attack_kind(source) == AttackKind.MELEE:
        tags.append("melee")
    else:
        tags.append("ranged")
    return tuple(tags)
