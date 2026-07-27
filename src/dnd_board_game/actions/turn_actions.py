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
class DefensiveSpellReaction(DefensiveAction):
    pass


@dataclass(frozen=True, slots=True)
class SpellCounterReaction(DefensiveAction):
    pass


@dataclass(frozen=True, slots=True)
class LongCastAction(SupportAction):
    pass


@dataclass(frozen=True, slots=True)
class SummonAction(SupportAction):
    pass


@dataclass(frozen=True, slots=True)
class SpellMovementAction(SupportAction):
    pass


@dataclass(frozen=True, slots=True)
class SpellDebuffAction(SupportAction):
    pass


@dataclass(frozen=True, slots=True)
class SpellDispelAction(SupportAction):
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


def defensive_spell_reaction_mechanic(
    action_id: str = "shield",
    label: str = "Czar obronny",
) -> DefensiveSpellReaction:
    return DefensiveSpellReaction(
        id=f"spell.{action_id}",
        name=label,
        scope=MechanicScope.COMBAT,
        resource=ActionResource.REACTION,
        targeting=TargetingMode.SELF,
        summary="Czar jest oferowany po trafieniu, zużywa reakcję i slot oraz podnosi AC do początku następnej tury.",
        tags=("spell", "reaction", "defense", "armor_class"),
    )


def spell_counter_reaction_mechanic(
    action_id: str = "counterspell",
    label: str = "Kontrczar",
) -> SpellCounterReaction:
    return SpellCounterReaction(
        id=f"spell.{action_id}",
        name=label,
        scope=MechanicScope.COMBAT,
        resource=ActionResource.REACTION,
        targeting=TargetingMode.ENEMY,
        summary="Kontrczar przerywa widziany czar w zasięgu, zużywając reakcję i wybrany slot czaru.",
        tags=("spell", "reaction", "counter", "interrupt"),
    )


def long_cast_mechanic(
    action_id: str = "long_cast",
    label: str = "Długie rzucanie",
) -> LongCastAction:
    return LongCastAction(
        id=f"spell.{action_id}",
        name=label,
        scope=MechanicScope.COMBAT,
        resource=ActionResource.ACTION,
        targeting=TargetingMode.SELF,
        summary="Czar wymaga akcji w każdej kolejnej turze i koncentracji aż do ukończenia.",
        tags=("spell", "concentration", "long_cast", "interruptible"),
    )


def summon_mechanic(
    action_id: str = "summon",
    label: str = "Przywołanie",
) -> SummonAction:
    return SummonAction(
        id=f"spell.{action_id}",
        name=label,
        scope=MechanicScope.COMBAT,
        resource=ActionResource.ACTION,
        targeting=TargetingMode.TILE,
        summary=(
            "Czar wybiera wolne pole w zasięgu, tworzy sojusznika w inicjatywie "
            "i utrzymuje go przez koncentrację."
        ),
        tags=("spell", "concentration", "summon", "position"),
    )


def spell_movement_mechanic(
    action_id: str = "spell_movement",
    label: str = "Magiczny ruch",
) -> SpellMovementAction:
    return SpellMovementAction(
        id=f"spell.{action_id}",
        name=label,
        scope=MechanicScope.COMBAT,
        resource=ActionResource.ACTION,
        targeting=TargetingMode.TILE,
        summary=(
            "Czar teleportuje rzucającego albo przemieszcza wybrany cel bez "
            "zużywania jego ruchu i bez ataków okazyjnych."
        ),
        tags=("spell", "movement", "teleport", "forced_movement"),
    )


def spell_debuff_mechanic(
    action_id: str = "spell_debuff",
    label: str = "Osłabienie",
) -> SpellDebuffAction:
    return SpellDebuffAction(
        id=f"spell.{action_id}",
        name=label,
        scope=MechanicScope.COMBAT,
        resource=ActionResource.ACTION,
        targeting=TargetingMode.ENEMY,
        summary=(
            "Czar wybiera widocznego przeciwnika, rozstrzyga save i po porażce "
            "nakłada warunek obsługiwany przez wspólny lifecycle tur."
        ),
        tags=("spell", "debuff", "condition", "saving_throw"),
    )


def spell_dispel_mechanic(
    action_id: str = "spell_dispel",
    label: str = "Rozproszenie magii",
) -> SpellDispelAction:
    return SpellDispelAction(
        id=f"spell.{action_id}",
        name=label,
        scope=MechanicScope.COMBAT,
        resource=ActionResource.ACTION,
        targeting=TargetingMode.ACTOR,
        summary=(
            "Czar kończy efekty czarów na widocznym celu; silniejsze efekty "
            "wymagają testu cechy rzucania czarów."
        ),
        tags=("spell", "dispel", "magic", "ability_check"),
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
