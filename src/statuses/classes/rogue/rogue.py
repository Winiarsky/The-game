from __future__ import annotations

from statuses.base import Status
from statuses.classes.rogue.sneak_attack import SNEAK_ATTACK_STATUS
from statuses.classes.rogue.surprise_attack import SURPRISE_ATTACK_STATUS

ROGUE_RACKET_CHOICES = ["ruffian", "scoundrel", "thief"]
ROGUE_FEAT_CHOICES = ["nimble_dodge", "trap_finder", "twin_feint", "youre_next"]

ROGUE_PROMPT = (
    "KEY ABILITY: DEXTERITY (Scoundrel: CHA allowed, Ruffian: STR allowed)\n"
    "At 1st level, your class gives you an ability boost based on racket.\n"
    "HIT POINTS: 8 plus your Constitution Modifier\n\n"
    "INITIAL PROFICIENCIES (summary):\n"
    "Perception: Expert\n"
    "Saving Throws: Expert Reflex, Trained Fortitude, Trained Will\n"
    "Attacks: Trained simple weapons + martial weapons + unarmed\n"
    "Defenses: Trained light armor + unarmored (Ruffian: medium armor)\n\n"
    "CLASS FEATURES:\n"
    "Sneak Attack: +1k6 precision na odpowiednich atakach vs flat-footed.\n"
    "Surprise Attack: runda 1, cele przed swoją turą są flat-footed przeciw twoim atakom.\n"
    "Podczas setupu wybierasz racket, key ability i 1 class feat poziomu 1."
)


def RogueStatus() -> Status:
    return Status(
        id="rogue",
        label="Rogue",
        data={
            "ui_prompt": ROGUE_PROMPT,
            "class_hp": 8,
            "ui_choice_kind": "rogue_setup",
            "rogue_racket_choices": list(ROGUE_RACKET_CHOICES),
            "rogue_feat_choices": list(ROGUE_FEAT_CHOICES),
            "set_actor_attrs": {"class_name": "rogue"},
            "grants_statuses": [SNEAK_ATTACK_STATUS, SURPRISE_ATTACK_STATUS],
        },
    )


ROGUE_STATUS = RogueStatus()

__all__ = [
    "ROGUE_RACKET_CHOICES",
    "ROGUE_FEAT_CHOICES",
    "ROGUE_PROMPT",
    "RogueStatus",
    "ROGUE_STATUS",
]
