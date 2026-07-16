from __future__ import annotations

from dataclasses import dataclass

from .base import ActionResource, CombatActionMechanic, MechanicScope, TargetingMode


@dataclass(frozen=True, slots=True)
class DefensiveAction(CombatActionMechanic):
    pass


@dataclass(frozen=True, slots=True)
class DodgeAction(DefensiveAction):
    pass


@dataclass(frozen=True, slots=True)
class DisengageAction(DefensiveAction):
    pass


@dataclass(frozen=True, slots=True)
class SupportAction(CombatActionMechanic):
    pass


@dataclass(frozen=True, slots=True)
class ConcentrationAction(SupportAction):
    pass


@dataclass(frozen=True, slots=True)
class HelpAction(SupportAction):
    pass


@dataclass(frozen=True, slots=True)
class ReadyAction(SupportAction):
    pass


@dataclass(frozen=True, slots=True)
class ItemAction(CombatActionMechanic):
    pass


@dataclass(frozen=True, slots=True)
class StrengthPotionAction(ItemAction):
    pass


@dataclass(frozen=True, slots=True)
class TargetedItemEffectAction(ItemAction):
    pass


def dodge_mechanic() -> DodgeAction:
    return DodgeAction(
        id="action.dodge",
        name="Unik",
        scope=MechanicScope.COMBAT,
        resource=ActionResource.ACTION,
        targeting=TargetingMode.SELF,
        summary="Unik zużywa akcję i nakłada tymczasowy efekt obronny do początku następnej tury aktora.",
        tags=("defense", "action_economy"),
    )


def disengage_mechanic() -> DisengageAction:
    return DisengageAction(
        id="action.disengage",
        name="Odwrót",
        scope=MechanicScope.COMBAT,
        resource=ActionResource.ACTION,
        targeting=TargetingMode.SELF,
        summary="Odwrót zużywa akcję i blokuje ataki okazyjne do końca bieżącej tury.",
        tags=("defense", "movement", "opportunity_attack"),
    )


def help_mechanic() -> HelpAction:
    return HelpAction(
        id="action.help",
        name="Help",
        scope=MechanicScope.COMBAT,
        resource=ActionResource.ACTION,
        targeting=TargetingMode.ACTOR,
        summary="Help wybiera sojusznika i przeciwnika; sojusznik dostaje przewagę na następny atak przeciw temu celowi.",
        tags=("support", "advantage"),
    )


def concentration_attack_bonus_mechanic(
    action_id: str = "concentration_attack_bonus",
    label: str = "Czar koncentracyjny",
) -> ConcentrationAction:
    return ConcentrationAction(
        id=f"spell.{action_id}",
        name=label,
        scope=MechanicScope.COMBAT,
        resource=ActionResource.ACTION,
        targeting=TargetingMode.ALLY,
        summary="Czar koncentracyjny wybiera sojusznika i utrzymuje premię do ataku, dopóki koncentracja trwa.",
        tags=("spell", "concentration", "buff", "attack_bonus"),
    )


def ready_mechanic() -> ReadyAction:
    return ReadyAction(
        id="action.ready",
        name="Ready",
        scope=MechanicScope.COMBAT,
        resource=ActionResource.ACTION,
        targeting=TargetingMode.NONE,
        summary="Ready zużywa akcję teraz i zapisuje warunek późniejszej reakcji.",
        tags=("support", "reaction_trigger"),
    )


def strength_potion_mechanic(action_id: str = "drink_strength_potion", label: str = "Napój siły") -> StrengthPotionAction:
    return StrengthPotionAction(
        id=f"item.{action_id}",
        name=label,
        scope=MechanicScope.COMBAT,
        resource=ActionResource.ACTION,
        targeting=TargetingMode.SELF,
        summary="Przedmiot zużywa akcję i nakłada premię do ataku oraz obrażeń z Siły.",
        tags=("item", "buff", "strength"),
    )


def targeted_item_effect_mechanic(
    action_id: str,
    label: str,
    *,
    targeting: TargetingMode = TargetingMode.ENEMY,
) -> TargetedItemEffectAction:
    return TargetedItemEffectAction(
        id=f"item.{action_id}",
        name=label,
        scope=MechanicScope.COMBAT,
        resource=ActionResource.ACTION,
        targeting=targeting,
        summary="Przedmiot zużywa akcję i jedną sztukę, a następnie nakłada jawny efekt na legalny cel.",
        tags=("item", "targeted", "effect"),
    )
