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
DRUID_ORDER_UI_DETAILS = {
    "animal": {
        "fluff": "Krąg zwierząt buduje więź druida z bestiami i wspólną walką na planszy.",
        "feat_summary": (
            "wybierasz young animal companion. W walce wydajesz 1 akcję na Command Animal Companion, "
            "aby dać mu 2 własne akcje na Stride, Strike albo Support."
        ),
        "spell_summary": (
            "focus spell leczący living animal. Wariant touch działa w 5 ft za 1 akcję, a wariant "
            "ranged kosztuje 2 akcje i ma zasięg 30 ft."
        ),
    },
    "leaf": {
        "fluff": "Krąg liścia stawia na opiekę, naturę i wsparcie przez leshy familiara.",
        "feat_summary": (
            "zyskujesz leshy familiar i status FamiliarOwner. Familiar korzysta z obecnej mechaniki "
            "Command Familiar, np. Scout, Guidance, Distract albo Touch Delivery."
        ),
        "spell_summary": (
            "focus spell za 2 akcje. Tworzysz Goodberry w ekwipunku; liczba jagód skaluje się z rangą "
            "focus spell, a każda po użyciu leczy 1d6+4."
        ),
    },
    "storm": {
        "fluff": "Krąg burzy skupia się na panowaniu nad pogodą i agresywnych czarach elektrycznych.",
        "feat_summary": (
            "ignorujesz pogodowe kary do ranged spell attack i Perception. Targeted spells ignorują też "
            "concealment wynikający z pogody."
        ),
        "spell_summary": (
            "focus spell za 2 akcje na 30 ft. Cel wykonuje basic Reflex save przeciw obrażeniom electricity; "
            "przy failure lub critical failure dostaje też Clumsy 2 i persistent electricity damage."
        ),
    },
    "wild": {
        "fluff": "Krąg dzikości stawia na przemiany i walkę w zmienionej formie.",
        "feat_summary": (
            "dostajesz dodatkowy focus spell Dziki ksztalt. Za 2 akcje zmieniasz formę; na starcie masz "
            "pest formy, a od wyższych rang także formy zwierzęce i +2 status do ataków w formie."
        ),
        "spell_summary": (
            "focus spell za 1 akcję. Wybierasz efekt morph spośród odblokowanych featami, np. pazury, "
            "szczęki albo skrzydła; na wyższych rangach możesz łączyć kilka efektów naraz."
        ),
    },
}

DRUID_SPELLS_PER_DAY = {
    1: {"cantrip": 5, "rank_1": 2},
    2: {"cantrip": 5, "rank_1": 3},
    3: {"cantrip": 5, "rank_1": 3, "rank_2": 2},
    4: {"cantrip": 5, "rank_1": 3, "rank_2": 3},
    5: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 2},
    6: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3},
    7: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 2},
    8: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 3},
    9: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 3, "rank_5": 2},
    10: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 3, "rank_5": 3},
    11: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 3, "rank_5": 3, "rank_6": 2},
    12: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 3, "rank_5": 3, "rank_6": 3},
    13: {
        "cantrip": 5,
        "rank_1": 3,
        "rank_2": 3,
        "rank_3": 3,
        "rank_4": 3,
        "rank_5": 3,
        "rank_6": 3,
        "rank_7": 2,
    },
    14: {
        "cantrip": 5,
        "rank_1": 3,
        "rank_2": 3,
        "rank_3": 3,
        "rank_4": 3,
        "rank_5": 3,
        "rank_6": 3,
        "rank_7": 3,
    },
    15: {
        "cantrip": 5,
        "rank_1": 3,
        "rank_2": 3,
        "rank_3": 3,
        "rank_4": 3,
        "rank_5": 3,
        "rank_6": 3,
        "rank_7": 3,
        "rank_8": 2,
    },
    16: {
        "cantrip": 5,
        "rank_1": 3,
        "rank_2": 3,
        "rank_3": 3,
        "rank_4": 3,
        "rank_5": 3,
        "rank_6": 3,
        "rank_7": 3,
        "rank_8": 3,
    },
    17: {
        "cantrip": 5,
        "rank_1": 3,
        "rank_2": 3,
        "rank_3": 3,
        "rank_4": 3,
        "rank_5": 3,
        "rank_6": 3,
        "rank_7": 3,
        "rank_8": 3,
        "rank_9": 2,
    },
    18: {
        "cantrip": 5,
        "rank_1": 3,
        "rank_2": 3,
        "rank_3": 3,
        "rank_4": 3,
        "rank_5": 3,
        "rank_6": 3,
        "rank_7": 3,
        "rank_8": 3,
        "rank_9": 3,
    },
    19: {
        "cantrip": 5,
        "rank_1": 3,
        "rank_2": 3,
        "rank_3": 3,
        "rank_4": 3,
        "rank_5": 3,
        "rank_6": 3,
        "rank_7": 3,
        "rank_8": 3,
        "rank_9": 3,
        "rank_10": 1,
    },
    20: {
        "cantrip": 5,
        "rank_1": 3,
        "rank_2": 3,
        "rank_3": 3,
        "rank_4": 3,
        "rank_5": 3,
        "rank_6": 3,
        "rank_7": 3,
        "rank_8": 3,
        "rank_9": 3,
        "rank_10": 1,
    },
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
    "Na poczatku scenariusza przygotowujesz czary zgodnie z tabela Druid Spells per Day.\n"
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
            "class_hp": 8,
            "ui_choice_kind": "druid_setup",
            "druid_order_choices": list(DRUID_ORDER_CHOICES),
            "druid_order_skills": dict(DRUID_ORDER_SKILLS),
            "druid_order_start_feats": dict(DRUID_ORDER_START_FEATS),
            "druid_order_spells": dict(DRUID_ORDER_SPELLS),
            "druid_order_focus_bonus": dict(DRUID_ORDER_FOCUS_BONUS),
            "druid_spells_per_day": {level: dict(slots) for level, slots in DRUID_SPELLS_PER_DAY.items()},
            "druid_spell_tradition": "primal",
            "druid_prepared_cantrips_at_level1": 5,
            "druid_prepared_rank_1_slots_at_level1": 2,
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
    "DRUID_ORDER_UI_DETAILS",
    "DRUID_SPELLS_PER_DAY",
    "DRUID_PROMPT",
    "DruidStatus",
    "DRUID_STATUS",
]
