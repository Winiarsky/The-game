from __future__ import annotations

from statuses.base import Status

ALCHEMIST_FAMILIAR_GUIDANCE_PROMPT = (
    "Masz familiara i mozesz uzywac akcji Command Familiar."
)


def AlchemistFamiliarGuidanceStatus() -> Status:
    """Feat: Alchemist Familiar (Guidance) (opis do UI prompta)."""
    return Status(
        id="alchemist_familiar_guidance",
        label="Alchemist Familiar (Guidance)",
        data={"ui_prompt": ALCHEMIST_FAMILIAR_GUIDANCE_PROMPT},
    )


ALCHEMIST_FAMILIAR_GUIDANCE_STATUS = AlchemistFamiliarGuidanceStatus()

__all__ = [
    "ALCHEMIST_FAMILIAR_GUIDANCE_PROMPT",
    "AlchemistFamiliarGuidanceStatus",
    "ALCHEMIST_FAMILIAR_GUIDANCE_STATUS",
]
