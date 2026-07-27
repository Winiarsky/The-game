from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import NpcAttitude


SOCIAL_CHECK_SKILLS = ("persuasion", "deception", "intimidation")


class SocialRequestRisk(str, Enum):
    """Risk an NPC accepts when fulfilling a player's request."""

    NO_RISK = "no_risk"
    MINOR_RISK = "minor_risk"
    SIGNIFICANT_RISK = "significant_risk"


@dataclass(frozen=True, slots=True)
class SocialInteractionPlan:
    attitude: NpcAttitude
    request_risk: SocialRequestRisk
    possible: bool
    requires_roll: bool
    dc: int | None

    def __post_init__(self) -> None:
        if self.possible and self.requires_roll and self.dc is None:
            raise ValueError("A social interaction roll requires a DC.")
        if (not self.possible or not self.requires_roll) and self.dc is not None:
            raise ValueError("A social interaction without a roll cannot define a DC.")

    def as_payload(self) -> dict[str, object]:
        return {
            "attitude": self.attitude.value,
            "request_risk": self.request_risk.value,
            "possible": self.possible,
            "requires_roll": self.requires_roll,
            "dc": self.dc,
        }


_REACTION_THRESHOLDS: dict[
    NpcAttitude, dict[SocialRequestRisk, int | None]
] = {
    NpcAttitude.FRIENDLY: {
        SocialRequestRisk.NO_RISK: 0,
        SocialRequestRisk.MINOR_RISK: 10,
        SocialRequestRisk.SIGNIFICANT_RISK: 20,
    },
    NpcAttitude.INDIFFERENT: {
        SocialRequestRisk.NO_RISK: 10,
        SocialRequestRisk.MINOR_RISK: 20,
        SocialRequestRisk.SIGNIFICANT_RISK: None,
    },
    NpcAttitude.HOSTILE: {
        SocialRequestRisk.NO_RISK: 20,
        SocialRequestRisk.MINOR_RISK: None,
        SocialRequestRisk.SIGNIFICANT_RISK: None,
    },
}


def plan_social_interaction(
    attitude: NpcAttitude,
    request_risk: SocialRequestRisk,
) -> SocialInteractionPlan:
    """Map the D&D 5e (2014) conversation reaction table to a request plan."""

    threshold = _REACTION_THRESHOLDS[attitude][request_risk]
    if threshold is None:
        return SocialInteractionPlan(attitude, request_risk, False, False, None)
    if threshold == 0:
        return SocialInteractionPlan(attitude, request_risk, True, False, None)
    return SocialInteractionPlan(attitude, request_risk, True, True, threshold)
