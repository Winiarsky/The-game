from __future__ import annotations

from statuses.base import Status
from statuses.classes.monk.feats.flurry_of_blows import FLURRY_OF_BLOWS_STATUS
from statuses.classes.monk.feats.powerful_fist import POWERFUL_FIST_STATUS

MONK_KEY_ABILITY_CHOICES = ["strength", "dexterity"]
MONK_FEAT_CHOICES = [
    "crane_stance",
    "dragon_stance",
    "ki_rush",
    "ki_strike",
    "monastic_weaponry",
    "mountain_stance",
    "tiger_stance",
    "wolf_stance",
]

MONK_PROMPT = (
    "KEY ABILITY: STRENGTH OR DEXTERITY\n"
    "At 1st level, your class gives you an ability boost to your choice of Strength or Dexterity.\n"
    "HIT POINTS: 10 plus your Constitution Modifier\n\n"
    "INITIAL PROFICIENCIES (summary):\n"
    "Perception: Expert\n"
    "Saving Throws: Expert Fortitude, Expert Reflex, Expert Will\n"
    "Attacks: Trained simple weapons + unarmed\n"
    "Defenses: Trained unarmored defense\n\n"
    "CLASS FEATURES:\n"
    "Flurry of Blows: 2 unarmed Strikes (Flourish).\n"
    "Powerful Fist: bazowy fist 1k6 zamiast 1k4.\n"
    "Podczas setupu wybierasz key ability i 1 class feat poziomu 1."
)


def MonkStatus() -> Status:
    return Status(
        id="monk",
        label="Monk",
        data={
            "ui_prompt": MONK_PROMPT,
            "ui_choice_kind": "monk_setup",
            "monk_key_ability_choices": list(MONK_KEY_ABILITY_CHOICES),
            "monk_feat_choices": list(MONK_FEAT_CHOICES),
            "set_actor_attrs": {"class_name": "monk"},
            "grants_statuses": [FLURRY_OF_BLOWS_STATUS, POWERFUL_FIST_STATUS],
        },
    )


MONK_STATUS = MonkStatus()

__all__ = [
    "MONK_KEY_ABILITY_CHOICES",
    "MONK_FEAT_CHOICES",
    "MONK_PROMPT",
    "MonkStatus",
    "MONK_STATUS",
]
