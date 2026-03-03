from __future__ import annotations

from statuses.base import Status
from statuses.general.shield_block import SHIELD_BLOCK_STATUS

DRUID_ORDER_CHOICES = ["animal", "leaf", "storm", "wild"]
DRUID_ORDER_SKILLS = {
    "animal": "athletics",
    "leaf": "diplomacy",
    "storm": "acrobatics",
    "wild": "intimidation",
}
DRUID_ORDER_START_FEATS = {
    "animal": "animal_companion",
    "leaf": "leshy_familiar",
    "storm": "storm_born",
    "wild": "wild_shape",
}
DRUID_ORDER_SPELLS = {
    "animal": "heal_animal",
    "leaf": "goodberry",
    "storm": "tempest_surge",
    "wild": "wild_morph",
}
DRUID_ORDER_FOCUS_BONUS = {
    "animal": 0,
    "leaf": 1,
    "storm": 1,
    "wild": 0,
}

DRUID_PROMPT = (
    "KEY ABILITY: WISDOM\n"
    "At 1st level, your class gives you an ability boost to Wisdom.\n"
    "HIT POINTS: 8 plus your Constitution Modifier\n\n"
    "INITIAL PROFICIENCIES:\n"
    "PERCEPTION\n"
    "Trained in Perception\n"
    "SAVING THROWS\n"
    "Trained in Fortitude\n"
    "Trained in Reflex\n"
    "Expert in Will\n"
    "SKILLS\n"
    "Trained in Nature\n"
    "Trained in a number of additional skills equal to 3 plus your Intelligence modifier\n"
    "ATTACKS\n"
    "Trained in simple weapons\n"
    "Trained in unarmed attacks\n"
    "DEFENSES\n"
    "Trained in light armor\n"
    "Trained in medium armor\n"
    "Trained in unarmored defense\n"
    "SPELLS\n"
    "Primal spellcasting\n"
    "Focus Pool: 1 Focus Point\n\n"
    "DRUIDIC ORDER:\n"
    "Podczas setupu wybierasz order (animal/leaf/storm/wild).\n"
    "Order nadaje dodatkowy skill, startowy feat i order spell."
)


def DruidStatus() -> Status:
    """Class: Druid (opis do UI prompta)."""
    return Status(
        id="druid",
        label="Druid",
        data={
            "ui_prompt": DRUID_PROMPT,
            "ui_choice_kind": "druid_setup",
            "druid_order_choices": list(DRUID_ORDER_CHOICES),
            "druid_order_skills": dict(DRUID_ORDER_SKILLS),
            "druid_order_start_feats": dict(DRUID_ORDER_START_FEATS),
            "druid_order_spells": dict(DRUID_ORDER_SPELLS),
            "druid_order_focus_bonus": dict(DRUID_ORDER_FOCUS_BONUS),
            "set_actor_attrs": {"class_name": "druid", "focus_point": 1},
            "grants_statuses": [SHIELD_BLOCK_STATUS],
        },
    )


DRUID_STATUS = DruidStatus()

__all__ = [
    "DRUID_ORDER_CHOICES",
    "DRUID_ORDER_SKILLS",
    "DRUID_ORDER_START_FEATS",
    "DRUID_ORDER_SPELLS",
    "DRUID_ORDER_FOCUS_BONUS",
    "DRUID_PROMPT",
    "DruidStatus",
    "DRUID_STATUS",
]
