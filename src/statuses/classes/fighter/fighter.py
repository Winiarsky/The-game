from __future__ import annotations

from statuses.base import Status
from statuses.general.shield_block import SHIELD_BLOCK_STATUS
from statuses.opportunity_attack import OPPORTUNITY_ATTACK_STATUS

FIGHTER_KEY_ABILITY_CHOICES = ["strength", "dexterity"]

FIGHTER_PROMPT = (
    "KEY ABILITY: STRENGTH or DEXTERITY\n"
    "At 1st level, your class gives you an ability boost to Strength or Dexterity.\n"
    "HIT POINTS: 10 plus your Constitution Modifier\n\n"
    "INITIAL PROFICIENCIES (summary):\n"
    "Perception: Expert\n"
    "Saving Throws: Expert Fortitude, Expert Reflex, Trained Will\n"
    "Attacks: Trained simple/martial + unarmed\n"
    "Defenses: Trained all armor + unarmored\n\n"
    "Atak okazyjny (Attack of Opportunity): otrzymujesz automatycznie.\n"
    "Shield Block: otrzymujesz automatycznie.\n"
    "Skille prowadzisz ręcznie poza grą (UI reminder)."
)


def FighterStatus() -> Status:
    return Status(
        id="fighter",
        label="Fighter",
        data={
            "ui_prompt": FIGHTER_PROMPT,
            "ui_choice_kind": "fighter_setup",
            "fighter_key_ability_choices": list(FIGHTER_KEY_ABILITY_CHOICES),
            "set_actor_attrs": {"class_name": "fighter"},
            "grants_statuses": [OPPORTUNITY_ATTACK_STATUS, SHIELD_BLOCK_STATUS],
        },
    )


FIGHTER_STATUS = FighterStatus()

__all__ = [
    "FIGHTER_KEY_ABILITY_CHOICES",
    "FIGHTER_PROMPT",
    "FighterStatus",
    "FIGHTER_STATUS",
]
