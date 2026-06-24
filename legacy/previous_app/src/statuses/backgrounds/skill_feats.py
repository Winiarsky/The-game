from __future__ import annotations

from bonuses import BonusEffect, BonusType
from skills import Skill
from statuses.base import Status
from statuses.check_effects import CheckEffect


def _skill_feat_status(
    feat_id: str,
    label: str,
    description: str,
    *,
    skill_ids: tuple[str, ...] = (),
    mechanics_line: str = "",
) -> Status:
    skill_list = [str(item).strip().lower() for item in skill_ids if str(item).strip()]
    check_effects: list[CheckEffect] = []
    if skill_list:
        check_effects.append(
            CheckEffect(
                applies_to="source",
                skills=skill_list,
                bonus_effects=[
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=2,
                        tag=skill_id,
                        source=f"status:{feat_id}",
                        label=f"{label} +2",
                    )
                    for skill_id in skill_list
                ],
                prompt_notes=[f"{label}: +2 status."],
            )
        )
    fluff = str(description or "").strip()
    mechanic = str(mechanics_line or "").strip()
    ui_description = "\n".join(
        line for line in (fluff, f"Mechanika: {mechanic}" if mechanic else "") if line
    )
    return Status(
        id=feat_id,
        label=label,
        data={
            "ui_description": ui_description,
            "skill_feat_placeholder": False,
            "skill_feat_fallback_mechanic": bool(skill_list),
        },
        check_effects=check_effects or None,
    )


STUDENT_OF_THE_CANON_STATUS = _skill_feat_status(
    "student_of_the_canon",
    "Student of the Canon",
    "Studiowałeś pisma swojej wiary i szybko przywołujesz właściwą doktrynę.",
    skill_ids=(Skill.RELIGION.value,),
    mechanics_line="+2 status do testów Religii.",
)

STEADY_BALANCE_STATUS = _skill_feat_status(
    "steady_balance",
    "Steady Balance",
    "Utrzymujesz równowagę w trudnym terenie i na wąskich powierzchniach.",
    skill_ids=(Skill.ACROBATICS.value,),
    mechanics_line="+2 status do testów Akrobatyki.",
)

TRAIN_ANIMAL_STATUS = _skill_feat_status(
    "train_animal",
    "Train Animal",
    "Skuteczniej szkolisz zwierzęta i potrzebujesz na to mniej czasu.",
    skill_ids=(Skill.NATURE.value,),
    mechanics_line="+2 status do testów Natury (w tym szkolenie zwierząt).",
)

SPECIALTY_CRAFTING_STATUS = _skill_feat_status(
    "specialty_crafting",
    "Specialty Crafting",
    "Masz wyspecjalizowane rzemiosło w wybranej dziedzinie.",
    skill_ids=(Skill.CRAFTING.value,),
    mechanics_line="+2 status do testów Rzemiosła.",
)

HOBNOBBER_STATUS = _skill_feat_status(
    "hobnobber",
    "Hobnobber",
    "Szybko zbierasz plotki i informacje społeczne w osadach.",
    skill_ids=(Skill.DIPLOMACY.value,),
    mechanics_line="+2 status do testów Dyplomacji.",
)

GROUP_IMPRESSION_STATUS = _skill_feat_status(
    "group_impression",
    "Group Impression",
    "Możesz jednocześnie wywrzeć dobre wrażenie na wielu celach.",
    skill_ids=(Skill.DIPLOMACY.value,),
    mechanics_line="+2 status do testów Dyplomacji.",
)

EXPERIENCED_TRACKER_STATUS = _skill_feat_status(
    "experienced_tracker",
    "Experienced Tracker",
    "Tropisz cele szybciej i bardziej niezawodnie.",
    skill_ids=(Skill.SURVIVAL.value,),
    mechanics_line="+2 status do testów Przetrwania.",
)

CHARMING_LIAR_STATUS = _skill_feat_status(
    "charming_liar",
    "Charming Liar",
    "Lepiej maskujesz społeczne kłamstwa i ich konsekwencje.",
    skill_ids=(Skill.DECEPTION.value,),
    mechanics_line="+2 status do testów Oszustwa.",
)

EXPERIENCED_SMUGGLER_STATUS = _skill_feat_status(
    "experienced_smuggler",
    "Experienced Smuggler",
    "Jesteś wprawiony w ukrywaniu kontrabandy i nielegalnych przedmiotów.",
    skill_ids=(Skill.STEALTH.value,),
    mechanics_line="+2 status do testów Skradania.",
)

STREETWISE_STATUS = _skill_feat_status(
    "streetwise",
    "Streetwise",
    "Pozyskujesz miejskie informacje przez kontakty i uliczne sieci.",
    skill_ids=(Skill.SOCIETY.value,),
    mechanics_line="+2 status do testów Społeczeństwa.",
)

MULTILINGUAL_STATUS = _skill_feat_status(
    "multilingual",
    "Multilingual",
    "Znasz dodatkowe języki ponad standardowy limit.",
    skill_ids=(Skill.SOCIETY.value,),
    mechanics_line="+2 status do testów Społeczeństwa.",
)

FASCINATING_PERFORMANCE_STATUS = _skill_feat_status(
    "fascinating_performance",
    "Fascinating Performance",
    "Podczas występu skupiasz uwagę i fascynujesz obserwatorów.",
    skill_ids=(Skill.PERFORMANCE.value,),
    mechanics_line="+2 status do testów Występów.",
)

BATTLE_MEDICINE_STATUS = _skill_feat_status(
    "battle_medicine",
    "Battle Medicine",
    "Potrafisz szybko opatrzyć sojusznika nawet w środku walki.",
    skill_ids=(Skill.MEDICINE.value,),
    mechanics_line="+2 status do testów Medycyny.",
)

ODDITY_IDENTIFICATION_STATUS = _skill_feat_status(
    "oddity_identification",
    "Oddity Identification",
    "Skuteczniej rozpoznajesz niezwykłe obiekty i osobliwości okultystyczne.",
    skill_ids=(Skill.OCCULTISM.value,),
    mechanics_line="+2 status do testów Okultyzmu.",
)

LIE_TO_ME_STATUS = _skill_feat_status(
    "lie_to_me",
    "Lie to Me",
    "Łatwiej wychwytujesz kłamstwa podczas rozmów.",
    skill_ids=(Skill.SOCIETY.value,),
    mechanics_line="+2 status do testów Społeczeństwa.",
)

IMPRESSIVE_PERFORMANCE_STATUS = _skill_feat_status(
    "impressive_performance",
    "Impressive Performance",
    "Występem wpływasz na nastawienie i wrażenie innych.",
    skill_ids=(Skill.PERFORMANCE.value,),
    mechanics_line="+2 status do testów Występów.",
)

QUICK_COERCION_STATUS = _skill_feat_status(
    "quick_coercion",
    "Quick Coercion",
    "Przymuszasz cele szybciej niż zwykle.",
    skill_ids=(Skill.INTIMIDATION.value,),
    mechanics_line="+2 status do testów Zastraszania.",
)

NATURAL_MEDICINE_STATUS = _skill_feat_status(
    "natural_medicine",
    "Natural Medicine",
    "W wybranych sytuacjach możesz używać Nature zamiast Medicine.",
    skill_ids=(Skill.NATURE.value,),
    mechanics_line="+2 status do testów Natury.",
)

SURVEY_WILDLIFE_STATUS = _skill_feat_status(
    "survey_wildlife",
    "Survey Wildlife",
    "Szybko rozpoznajesz ślady stworzeń i lokalną faunę.",
    skill_ids=(Skill.SURVIVAL.value,),
    mechanics_line="+2 status do testów Przetrwania.",
)

HEFTY_HAULER_STATUS = _skill_feat_status(
    "hefty_hauler",
    "Hefty Hauler",
    "Możesz nieść większy ciężar, zanim staniesz się przeciążony.",
    skill_ids=(Skill.ATHLETICS.value,),
    mechanics_line="+2 status do testów Atletyki.",
)

QUICK_JUMP_STATUS = _skill_feat_status(
    "quick_jump",
    "Quick Jump",
    "Skaczesz sprawniej i z mniejszym przygotowaniem.",
    skill_ids=(Skill.ATHLETICS.value,),
    mechanics_line="+2 status do testów Atletyki.",
)

CAT_FALL_STATUS = _skill_feat_status(
    "cat_fall",
    "Cat Fall",
    "Zmniejszasz obrażenia od upadku dzięki wyćwiczonym lądowaniom.",
    skill_ids=(Skill.ACROBATICS.value,),
    mechanics_line="+2 status do testów Akrobatyki.",
)

BARGAIN_HUNTER_STATUS = _skill_feat_status(
    "bargain_hunter",
    "Bargain Hunter",
    "Skuteczniej wynegocjujesz korzystne ceny podczas zakupów.",
    skill_ids=(Skill.DIPLOMACY.value,),
    mechanics_line="+2 status do testów Dyplomacji.",
)

TERRAIN_EXPERTISE_STATUS = _skill_feat_status(
    "terrain_expertise",
    "Terrain Expertise",
    "Zyskujesz wyszkolenie powiązane z wybranym typem terenu.",
    skill_ids=(Skill.SURVIVAL.value,),
    mechanics_line="+2 status do testów Przetrwania.",
)

COURTLY_GRACES_STATUS = _skill_feat_status(
    "courtly_graces",
    "Courtly Graces",
    "Sprawnie poruszasz się po etykiecie i protokole dworskim.",
    skill_ids=(Skill.SOCIETY.value,),
    mechanics_line="+2 status do testów Społeczeństwa.",
)

UNDERWATER_MARAUDER_STATUS = _skill_feat_status(
    "underwater_marauder",
    "Underwater Marauder",
    "Walczysz i poruszasz się skuteczniej pod wodą.",
    skill_ids=(Skill.ATHLETICS.value,),
    mechanics_line="+2 status do testów Atletyki.",
)

FORAGER_STATUS = _skill_feat_status(
    "forager",
    "Forager",
    "W trakcie podróży potrafisz zdobywać żywność i zapasy.",
    skill_ids=(Skill.SURVIVAL.value,),
    mechanics_line="+2 status do testów Przetrwania.",
)

PICKPOCKET_STATUS = _skill_feat_status(
    "pickpocket",
    "Pickpocket",
    "Potrafisz kraść drobne przedmioty bez zwracania uwagi.",
    skill_ids=(Skill.THIEVERY.value,),
    mechanics_line="+2 status do testów Złodziejstwa.",
)

INTIMIDATING_GLARE_STATUS = _skill_feat_status(
    "intimidating_glare",
    "Intimidating Glare",
    "Możesz Demoralize nawet bez wspólnego języka.",
    skill_ids=(Skill.INTIMIDATION.value,),
    mechanics_line="+2 status do testów Zastraszania.",
)


SKILL_FEAT_STATUS_BY_ID: dict[str, Status] = {
    "student_of_the_canon": STUDENT_OF_THE_CANON_STATUS,
    "steady_balance": STEADY_BALANCE_STATUS,
    "train_animal": TRAIN_ANIMAL_STATUS,
    "specialty_crafting": SPECIALTY_CRAFTING_STATUS,
    "hobnobber": HOBNOBBER_STATUS,
    "group_impression": GROUP_IMPRESSION_STATUS,
    "experienced_tracker": EXPERIENCED_TRACKER_STATUS,
    "charming_liar": CHARMING_LIAR_STATUS,
    "experienced_smuggler": EXPERIENCED_SMUGGLER_STATUS,
    "streetwise": STREETWISE_STATUS,
    "multilingual": MULTILINGUAL_STATUS,
    "fascinating_performance": FASCINATING_PERFORMANCE_STATUS,
    "battle_medicine": BATTLE_MEDICINE_STATUS,
    "oddity_identification": ODDITY_IDENTIFICATION_STATUS,
    "lie_to_me": LIE_TO_ME_STATUS,
    "impressive_performance": IMPRESSIVE_PERFORMANCE_STATUS,
    "quick_coercion": QUICK_COERCION_STATUS,
    "natural_medicine": NATURAL_MEDICINE_STATUS,
    "survey_wildlife": SURVEY_WILDLIFE_STATUS,
    "hefty_hauler": HEFTY_HAULER_STATUS,
    "quick_jump": QUICK_JUMP_STATUS,
    "cat_fall": CAT_FALL_STATUS,
    "bargain_hunter": BARGAIN_HUNTER_STATUS,
    "terrain_expertise": TERRAIN_EXPERTISE_STATUS,
    "courtly_graces": COURTLY_GRACES_STATUS,
    "underwater_marauder": UNDERWATER_MARAUDER_STATUS,
    "forager": FORAGER_STATUS,
    "pickpocket": PICKPOCKET_STATUS,
    "intimidating_glare": INTIMIDATING_GLARE_STATUS,
}


__all__ = [
    "STUDENT_OF_THE_CANON_STATUS",
    "STEADY_BALANCE_STATUS",
    "TRAIN_ANIMAL_STATUS",
    "SPECIALTY_CRAFTING_STATUS",
    "HOBNOBBER_STATUS",
    "GROUP_IMPRESSION_STATUS",
    "EXPERIENCED_TRACKER_STATUS",
    "CHARMING_LIAR_STATUS",
    "EXPERIENCED_SMUGGLER_STATUS",
    "STREETWISE_STATUS",
    "MULTILINGUAL_STATUS",
    "FASCINATING_PERFORMANCE_STATUS",
    "BATTLE_MEDICINE_STATUS",
    "ODDITY_IDENTIFICATION_STATUS",
    "LIE_TO_ME_STATUS",
    "IMPRESSIVE_PERFORMANCE_STATUS",
    "QUICK_COERCION_STATUS",
    "NATURAL_MEDICINE_STATUS",
    "SURVEY_WILDLIFE_STATUS",
    "HEFTY_HAULER_STATUS",
    "QUICK_JUMP_STATUS",
    "CAT_FALL_STATUS",
    "BARGAIN_HUNTER_STATUS",
    "TERRAIN_EXPERTISE_STATUS",
    "COURTLY_GRACES_STATUS",
    "UNDERWATER_MARAUDER_STATUS",
    "FORAGER_STATUS",
    "PICKPOCKET_STATUS",
    "INTIMIDATING_GLARE_STATUS",
    "SKILL_FEAT_STATUS_BY_ID",
]
