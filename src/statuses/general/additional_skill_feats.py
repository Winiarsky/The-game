from __future__ import annotations

from statuses.base import Status


def _general_feat_status(
    feat_id: str,
    label: str,
    description: str,
    *,
    data: dict[str, object] | None = None,
    stacks: bool = False,
) -> Status:
    payload: dict[str, object] = {"ui_description": description}
    if isinstance(data, dict):
        payload.update(data)
    return Status(
        id=feat_id,
        label=label,
        stacks=bool(stacks),
        data=payload,
    )


ADDITIONAL_LORE_STATUS = _general_feat_status(
    "additional_lore",
    "Additional Lore",
    (
        "Wybierz dodatkowa specjalizacje Lore i stajesz sie w niej trained. "
        "Dalsze automatyczne podniesienia rangi (3/7/15) sa na razie notatka UI."
    ),
    data={
        "ui_choice_kind": "additional_lore",
        "additional_lore_choices": [
            "academia",
            "engineering",
            "heraldry",
            "legal",
            "mercantile",
            "military",
            "sailing",
            "underworld",
            "warfare",
        ],
        "additional_lore_choice": None,
        "trained_lore_skills": [],
    },
)

ALCHEMICAL_CRAFTING_STATUS = _general_feat_status(
    "alchemical_crafting",
    "Alchemical Crafting",
    (
        "Mozesz tworzyc przedmioty alchemiczne przez Craft. "
        "System zapisuje to na bohaterze i dodaje starterowe receptury (uproszczenie)."
    ),
    data={
        "can_craft_alchemical_items": True,
        "granted_formulas": [
            "acid_flask",
            "alchemists_fire",
            "bottled_lightning",
            "frost_vial",
        ],
    },
)

ARCANE_SENSE_STATUS = _general_feat_status(
    "arcane_sense",
    "Arcane Sense",
    (
        "Zyskujesz Detect Magic jako arcane innate cantrip at-will. "
        "Skalowanie poziomu czaru przy wysokiej biegosci Arcana jest na razie opisowe."
    ),
    data={
        "granted_cantrips": ["detect_magic"],
        "innate_magic_tradition": "arcane",
    },
)

COMBAT_CLIMBER_STATUS = _general_feat_status(
    "combat_climber",
    "Combat Climber",
    (
        "Nie jestes flat-footed podczas Climb i mozesz wspinac sie z jedna zajeta reka. "
        "Na razie notatka UI (brak pelnej mechaniki ruchu wspinaczki)."
    ),
)

EXPERIENCED_PROFESSIONAL_STATUS = _general_feat_status(
    "experienced_professional",
    "Experienced Professional",
    (
        "Ogranicza krytyczne porazki i poprawia Earn Income na Lore. "
        "Na razie notatka UI (brak pelnej mechaniki Earn Income)."
    ),
)

FAST_RECOVERY_STATUS = _general_feat_status(
    "fast_recovery",
    "Fast Recovery",
    (
        "Szybsza regeneracja po odpoczynku i mocniejsze obnizanie stage poison/disease. "
        "Mechanika poison jest czesciowo wsparta; odpoczynek i drained pozostaja opisowe."
    ),
    data={
        "poison_stage_reduction_on_success": 2,
        "poison_stage_reduction_on_success_virulent": 1,
        "poison_stage_reduction_on_critical_success": 3,
        "poison_stage_reduction_on_critical_success_virulent": 2,
        "overnight_healing_multiplier": 2,
        "drained_recovery_bonus": 1,
    },
)

FEATHER_STEP_STATUS = _general_feat_status(
    "feather_step",
    "Feather Step",
    (
        "Mozesz Step w difficult terrain. "
        "Na razie notatka UI (brak dedykowanej obslugi trudnego terenu dla Step)."
    ),
)

GROUP_COERCION_STATUS = _general_feat_status(
    "group_coercion",
    "Group Coercion",
    (
        "Coerce moze objac wielu celow jednoczesnie. "
        "Na razie notatka UI (brak pelnej mechaniki rozmow grupowych)."
    ),
)

LENGTHY_DIVERSION_STATUS = _general_feat_status(
    "lengthy_diversion",
    "Lengthy Diversion",
    (
        "Po krytycznym Create a Diversion pozostajesz ukryty dluzej. "
        "Na razie notatka UI (czas trwania zalezy od GM i sytuacji)."
    ),
)

QUICK_IDENTIFICATION_STATUS = _general_feat_status(
    "quick_identification",
    "Quick Identification",
    (
        "Skraca czas Identify Magic (1 min / 3 akcje / 1 akcja). "
        "Na razie notatka UI (brak czasow eksploracyjnych per minuta w silniku)."
    ),
)

QUICK_REPAIR_STATUS = _general_feat_status(
    "quick_repair",
    "Quick Repair",
    (
        "Skraca czas akcji Repair (1 min / 3 akcje / 1 akcja). "
        "Na razie notatka UI."
    ),
)

QUICK_SQUEEZE_STATUS = _general_feat_status(
    "quick_squeeze",
    "Quick Squeeze",
    (
        "Szybsze przeciskanie (Squeeze). "
        "Na razie notatka UI."
    ),
)

READ_LIPS_STATUS = _general_feat_status(
    "read_lips",
    "Read Lips",
    (
        "Mozesz czytac z ruchu warg w znanym jezyku. "
        "Na razie notatka UI (testy Society i warunki widocznosci rozstrzyga GM)."
    ),
)

RIDE_STATUS = _general_feat_status(
    "ride",
    "Ride",
    (
        "Command an Animal dla ruchu wierzchowca automatycznie sie udaje. "
        "Na razie notatka UI (pelna obsluga mount turn economy jest ograniczona)."
    ),
)

SIGN_LANGUAGE_STATUS = _general_feat_status(
    "sign_language",
    "Sign Language",
    (
        "Znasz jezyki migowe zwiazane ze znanymi jezykami. "
        "Na razie notatka UI."
    ),
)

SNARE_CRAFTING_STATUS = _general_feat_status(
    "snare_crafting",
    "Snare Crafting",
    (
        "Mozesz tworzyc sidla i dostajesz starterowe receptury sidel (uproszczenie)."
    ),
    data={
        "can_craft_snares": True,
        "granted_formulas": [
            "alarm_snare",
            "hampering_snare",
            "marking_snare",
            "trip_snare",
        ],
    },
)

SUBTLE_THEFT_STATUS = _general_feat_status(
    "subtle_theft",
    "Subtle Theft",
    (
        "Obserwatorzy maja kare do wykrycia twojej kradziezy, a Palm/Steal po Diversion "
        "moze nie zdradzic pozycji. Na razie notatka UI."
    ),
)

TERRAIN_STALKER_STATUS = _general_feat_status(
    "terrain_stalker",
    "Terrain Stalker",
    (
        "W wybranym typie trudnego terenu mozesz Sneak na krotki dystans bez rzutu. "
        "Na razie notatka UI."
    ),
    data={
        "ui_choice_kind": "terrain_stalker",
        "terrain_stalker_choices": ["rubble", "snow", "underbrush"],
        "terrain_stalker_choice": None,
    },
)

TITAN_WRESTLER_STATUS = _general_feat_status(
    "titan_wrestler",
    "Titan Wrestler",
    (
        "Mozesz Disarm/Grapple/Shove/Trip znacznie wieksze cele. "
        "Na razie notatka UI."
    ),
)

VIRTUOSIC_PERFORMER_STATUS = _general_feat_status(
    "virtuosic_performer",
    "Virtuosic Performer",
    (
        "Wybierasz specjalizacje Performance i dostajesz +1 circumstance "
        "(+2 na master). Na razie notatka UI."
    ),
    data={
        "ui_choice_kind": "virtuosic_performer",
        "virtuosic_performer_choices": [
            "acting",
            "comedy",
            "dance",
            "keyboards",
            "oratory",
            "percussion",
            "singing",
            "strings",
            "winds",
        ],
        "virtuosic_performer_choice": None,
        "virtuosic_performer_bonus": 1,
    },
)


__all__ = [
    "ADDITIONAL_LORE_STATUS",
    "ALCHEMICAL_CRAFTING_STATUS",
    "ARCANE_SENSE_STATUS",
    "COMBAT_CLIMBER_STATUS",
    "EXPERIENCED_PROFESSIONAL_STATUS",
    "FAST_RECOVERY_STATUS",
    "FEATHER_STEP_STATUS",
    "GROUP_COERCION_STATUS",
    "LENGTHY_DIVERSION_STATUS",
    "QUICK_IDENTIFICATION_STATUS",
    "QUICK_REPAIR_STATUS",
    "QUICK_SQUEEZE_STATUS",
    "READ_LIPS_STATUS",
    "RIDE_STATUS",
    "SIGN_LANGUAGE_STATUS",
    "SNARE_CRAFTING_STATUS",
    "SUBTLE_THEFT_STATUS",
    "TERRAIN_STALKER_STATUS",
    "TITAN_WRESTLER_STATUS",
    "VIRTUOSIC_PERFORMER_STATUS",
]
