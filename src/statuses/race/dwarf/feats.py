from __future__ import annotations

from typing import Iterable, Sequence

from bonuses import BonusEffect, BonusType
from GameObjects.Enemies.enemy_types import EnemyType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect

_DWARF_FEAT_DATA = {"ancestry": "dwarf", "feat": True, "traits": ["dwarf", "feat"]}


def _tags_variants(base_tags: Iterable[str]) -> list[list[str]]:
    """Ułatwia tworzenie reguł dla wielu pojedynczych tagów."""
    return [[tag] for tag in base_tags]


def DwarvenLoreStatus() -> Status:
    """Informacja: trening w Crafting, Religion oraz wybranym Lore."""
    return Status(
        id="feat_dwarven_lore",
        label="Dwarven Lore",
        data={
            **_DWARF_FEAT_DATA,
            "prompt_notes": [
                "Otrzymujesz poziom trained w Crafting, Religion oraz wybranym Lore (wg MG)."
            ],
        },
    )


DWARVEN_LORE_STATUS = DwarvenLoreStatus()


def DwarvenWeaponFamiliarityStatus() -> Status:
    """Informacja: biegłość w uncommon dwarf weapons."""
    return Status(
        id="feat_dwarven_weapon_familiarity",
        label="Dwarven Weapon Familiarity",
        data={
            **_DWARF_FEAT_DATA,
            "prompt_notes": ["Jesteś biegły w uncommon dwarf weapons."],
        },
    )


DWARVEN_WEAPON_FAMILIARITY_STATUS = DwarvenWeaponFamiliarityStatus()


def RockRunnerStatus() -> Status:
    """Akrobatyka na kamiennym podłożu – sukces podbijany do krytyka; info o terenie."""
    promote_effects: list[CheckEffect] = [
        CheckEffect(
            applies_to="source",
            skills=[Skill.ACROBATICS.value],
            tags_required=tags,
            promote=1,
            promote_on=["success"],
            prompt_notes=[
                "Rock Runner: sukces w Akrobatyce na kamiennym terenie staje się krytykiem; ignorujesz trudny teren z tagiem rock/earth/stone."
            ],
        )
        for tags in _tags_variants(["rock", "stone", "earth"])
    ]
    return Status(
        id="feat_rock_runner",
        label="Rock Runner",
        data={**_DWARF_FEAT_DATA},
        check_effects=promote_effects,
    )


ROCK_RUNNER_STATUS = RockRunnerStatus()


def StoneCunningStatus() -> Status:
    """Premia okoliczności +2 do Perception vs stone/rock/earth."""
    bonus = BonusEffect(
        type=BonusType.CIRCUMSTANCE,
        value=2,
        tag=Skill.PERCEPTION.value,
        source="feat:stone_cunning",
        label="+2 Perception vs stone/rock/earth",
    )
    check_effects: list[CheckEffect] = [
        CheckEffect(
            applies_to="source",
            skills=[Skill.PERCEPTION.value],
            tags_required=tags,
            bonus_effects=[bonus],
            prompt_notes=["Stone Cunning: +2 circumstance do Perception vs stone/rock/earth."],
        )
        for tags in _tags_variants(["rock", "stone", "earth"])
    ]
    return Status(
        id="feat_stone_cunning",
        label="Stone Cunning",
        data={**_DWARF_FEAT_DATA},
        check_effects=check_effects,
    )


STONE_CUNNING_STATUS = StoneCunningStatus()


def UnburdenedIronStatus() -> Status:
    """Informacja: redukcje prędkości mniejsze o 1 pole."""
    return Status(
        id="feat_unburdened_iron",
        label="Unburdened Iron",
        data={
            **_DWARF_FEAT_DATA,
            "speed_reduction_mitigate": 1,
            "prompt_notes": ["Redukcje prędkości zmniejszone o 1 pole (min 0)."],
        },
    )


UNBURDENED_IRON_STATUS = UnburdenedIronStatus()


def VengefulHatredStatus(target: EnemyType | str = EnemyType.HUMAN) -> Status:
    """Wybrany typ wroga otrzymuje +1 do zadawanych obrażeń (informacja do promptu)."""
    target_value = target.value if isinstance(target, EnemyType) else str(target)
    return Status(
        id="feat_vengeful_hatred",
        label=f"Vengeful Hatred ({target_value})",
        data={
            **_DWARF_FEAT_DATA,
            "vengeful_hatred_target": target_value,
            "damage_bonus_vs_target": 1,
            "prompt_notes": [
                f"Przeciw {target_value}: zadawane obrażenia +1 (dodaj w promptcie obrażeń)."
            ],
        },
    )


VENGEFUL_HATRED_STATUS = VengefulHatredStatus()


__all__: Sequence[str] = [
    "DwarvenLoreStatus",
    "DWARVEN_LORE_STATUS",
    "DwarvenWeaponFamiliarityStatus",
    "DWARVEN_WEAPON_FAMILIARITY_STATUS",
    "RockRunnerStatus",
    "ROCK_RUNNER_STATUS",
    "StoneCunningStatus",
    "STONE_CUNNING_STATUS",
    "UnburdenedIronStatus",
    "UNBURDENED_IRON_STATUS",
    "VengefulHatredStatus",
    "VENGEFUL_HATRED_STATUS",
    "EnemyType",
]
