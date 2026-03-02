from __future__ import annotations

from statuses.base import Status
from statuses.classes.champion.feats.raise_shield_allow import CHAMPION_RAISE_SHIELD_ALLOW_FEAT
from statuses.general.shield_block import SHIELD_BLOCK_STATUS

CHAMPION_KEY_ABILITY_CHOICES = ["strength", "dexterity"]
CHAMPION_CAUSE_CHOICES = ["paladin", "redeemer", "liberator"]
CHAMPION_DEITY_CHOICES = ["iomedae", "sarenrae", "torag", "shelyn", "desna", "abadar", "custom"]
CHAMPION_DEITY_SKILL_CHOICES = {
    "iomedae": ["religion", "diplomacy"],
    "sarenrae": ["religion", "medicine"],
    "torag": ["religion", "crafting"],
    "shelyn": ["religion", "performance"],
    "desna": ["religion", "survival"],
    "abadar": ["religion", "society"],
    "custom": ["religion", "diplomacy", "intimidation", "medicine", "society", "athletics", "crafting"],
}

CHAMPION_PROMPT = (
    "KEY ABILITY: STRENGTH OR DEXTERITY\n"
    "At 1st level, your class gives you an ability boost to your choice of Strength or Dexterity.\n"
    "HIT POINTS: 10 plus your Constitution Modifier\n"
    "You increase your maximum number of HP by this number at 1st level and every level thereafter.\n\n"
    "INITIAL PROFICIENCIES:\n"
    "PERCEPTION\n"
    "Trained in Perception\n"
    "SAVING THROWS\n"
    "Expert in Fortitude\n"
    "Trained in Reflex\n"
    "Expert in Will\n"
    "SKILLS\n"
    "Trained in Religion\n"
    "Trained in one skill determined by your choice of deity\n"
    "Trained in a number of additional skills equal to 2 plus your Intelligence modifier\n"
    "ATTACKS\n"
    "Trained in simple weapons\n"
    "Trained in martial weapons\n"
    "Trained in unarmed attacks\n"
    "DEFENSES\n"
    "Trained in all armor\n"
    "Trained in unarmored defense"
)


def ChampionStatus() -> Status:
    """Class: Champion (opis do UI prompta)."""
    return Status(
        id="champion",
        label="Champion",
        data={
            "ui_prompt": CHAMPION_PROMPT,
            "ui_choice_kind": "champion_setup",
            "champion_key_ability_choices": list(CHAMPION_KEY_ABILITY_CHOICES),
            "champion_cause_choices": list(CHAMPION_CAUSE_CHOICES),
            "champion_deity_choices": list(CHAMPION_DEITY_CHOICES),
            "champion_deity_skill_choices": dict(CHAMPION_DEITY_SKILL_CHOICES),
            "set_actor_attrs": {"focus_point": 1, "class_name": "champion"},
            "grants_statuses": [CHAMPION_RAISE_SHIELD_ALLOW_FEAT, SHIELD_BLOCK_STATUS],
        },
    )


CHAMPION_STATUS = ChampionStatus()

__all__ = [
    "CHAMPION_KEY_ABILITY_CHOICES",
    "CHAMPION_CAUSE_CHOICES",
    "CHAMPION_DEITY_CHOICES",
    "CHAMPION_DEITY_SKILL_CHOICES",
    "CHAMPION_PROMPT",
    "ChampionStatus",
    "CHAMPION_STATUS",
]
