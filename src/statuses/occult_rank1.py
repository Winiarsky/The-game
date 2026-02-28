from __future__ import annotations

from .base import Status


def CharmedStatus(*, duration: int | None = 3, source: str | None = None) -> Status:
    return Status(
        id="charmed",
        label="Charmed",
        duration=duration,
        source=source,
        data={"effect_tags": ["charmed", "mental"]},
    )


def FloatingDiskStatus(*, duration: int | None = 10, source: str | None = None) -> Status:
    return Status(
        id="floating_disk",
        label="Floating Disk",
        duration=duration,
        source=source,
        data={"ui_description": "Dysk unosi ekwipunek i odciaza bohatera (uproszczenie)."},
    )


def IllusoryDisguiseStatus(
    *,
    persona: str = "masked",
    duration: int | None = 10,
    source: str | None = None,
) -> Status:
    style = str(persona or "masked")
    return Status(
        id="illusory_disguise",
        label=f"Illusory Disguise ({style})",
        duration=duration,
        source=source,
        data={"persona": style, "effect_tags": ["illusion"]},
    )


def MageArmorStatus(*, duration: int | None = 10, source: str | None = None) -> Status:
    return Status(
        id="mage_armor",
        label="Mage Armor",
        duration=duration,
        source=source,
        data={"effect_tags": ["abjuration", "defense"]},
    )


def MindlinkStatus(
    *,
    source_id: str | None,
    source_turns_left: int | None = 3,
    duration: int | None = 3,
    source: str | None = None,
) -> Status:
    return Status(
        id="mindlink",
        label="Mindlink",
        duration=duration,
        source=source,
        data={
            "source_id": source_id,
            "source_turns_left": source_turns_left,
            "effect_tags": ["divination", "mental"],
        },
    )


def SleepStatus(
    *,
    source_id: str | None,
    source_turns_left: int | None = 2,
    duration: int | None = 1,
    source: str | None = None,
) -> Status:
    return Status(
        id="sleep",
        label="Asleep",
        duration=duration,
        source=source,
        data={
            "source_id": source_id,
            "source_turns_left": source_turns_left,
            "effect_tags": ["sleep", "mental"],
        },
    )


def SpiritLinkCasterStatus(
    *,
    target_id: str | None,
    duration: int | None = 1,
    source: str | None = None,
) -> Status:
    return Status(
        id="spirit_link_caster",
        label="Spirit Link (caster)",
        duration=duration,
        source=source,
        data={"target_id": target_id, "effect_tags": ["spirit_link"]},
    )


def SpiritLinkTargetStatus(
    *,
    source_id: str | None,
    duration: int | None = 1,
    source: str | None = None,
) -> Status:
    return Status(
        id="spirit_link_target",
        label="Spirit Link",
        duration=duration,
        source=source,
        data={"source_id": source_id, "effect_tags": ["spirit_link"]},
    )


def SummonedFeyStatus(*, duration: int | None = 1, source: str | None = None) -> Status:
    return Status(
        id="summoned_fey",
        label="Summoned Fey",
        duration=duration,
        source=source,
        data={"effect_tags": ["summon", "fey"]},
    )


def TrueStrikeStatus(*, duration: int | None = 1, source: str | None = None) -> Status:
    return Status(
        id="true_strike",
        label="True Strike",
        duration=duration,
        source=source,
        data={"effect_tags": ["fortune", "divination"]},
    )


def UnseenServantStatus(*, duration: int | None = 3, source: str | None = None) -> Status:
    return Status(
        id="unseen_servant",
        label="Unseen Servant",
        duration=duration,
        source=source,
        data={"ui_description": "Niewidzialny pomocnik wspiera drobne czynnosci (opisowo)."},
    )


def VentriloquismStatus(*, duration: int | None = 1, source: str | None = None) -> Status:
    return Status(
        id="ventriloquism",
        label="Ventriloquism",
        duration=duration,
        source=source,
        data={"effect_tags": ["illusion", "auditory"]},
    )


__all__ = [
    "CharmedStatus",
    "FloatingDiskStatus",
    "IllusoryDisguiseStatus",
    "MageArmorStatus",
    "MindlinkStatus",
    "SleepStatus",
    "SpiritLinkCasterStatus",
    "SpiritLinkTargetStatus",
    "SummonedFeyStatus",
    "TrueStrikeStatus",
    "UnseenServantStatus",
    "VentriloquismStatus",
]
