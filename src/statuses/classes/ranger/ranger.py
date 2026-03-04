from __future__ import annotations

from statuses.base import Status
from statuses.classes.ranger.hunt_prey import HUNT_PREY_STATUS

RANGER_KEY_ABILITY_CHOICES = ["strength", "dexterity"]
RANGER_HUNTERS_EDGE_CHOICES = ["flurry", "precision", "outwit"]
RANGER_FEAT_CHOICES = [
    "animal_companion",
    "crossbow_ace",
    "hunted_shot",
    "monster_hunter",
    "twin_takedown",
]

RANGER_PROMPT = (
    "KEY ABILITY: STRENGTH OR DEXTERITY\n"
    "At 1st level, your class gives you an ability boost to your choice of Strength or Dexterity.\n"
    "HIT POINTS: 10 plus your Constitution Modifier\n\n"
    "INITIAL PROFICIENCIES (summary):\n"
    "Perception: Expert\n"
    "Saving Throws: Expert Fortitude, Expert Reflex, Trained Will\n"
    "Attacks: Trained simple/martial + unarmed\n"
    "Defenses: Trained light/medium armor + unarmored\n"
    "Skills: Trained in Nature + Survival\n\n"
    "CLASS FEATURES:\n"
    "Hunt Prey: oznaczasz jednego przeciwnika jako cel.\n"
    "Hunter's Edge: Flurry / Precision / Outwit.\n"
    "Podczas setupu wybierasz key ability, hunter's edge i 1 class feat poziomu 1."
)


def RangerStatus() -> Status:
    return Status(
        id="ranger",
        label="Ranger",
        data={
            "ui_prompt": RANGER_PROMPT,
            "ui_choice_kind": "ranger_setup",
            "ranger_key_ability_choices": list(RANGER_KEY_ABILITY_CHOICES),
            "ranger_hunters_edge_choices": list(RANGER_HUNTERS_EDGE_CHOICES),
            "ranger_feat_choices": list(RANGER_FEAT_CHOICES),
            "set_actor_attrs": {"class_name": "ranger"},
            "grants_statuses": [HUNT_PREY_STATUS],
        },
    )


RANGER_STATUS = RangerStatus()

__all__ = [
    "RANGER_KEY_ABILITY_CHOICES",
    "RANGER_HUNTERS_EDGE_CHOICES",
    "RANGER_FEAT_CHOICES",
    "RANGER_PROMPT",
    "RangerStatus",
    "RANGER_STATUS",
]
