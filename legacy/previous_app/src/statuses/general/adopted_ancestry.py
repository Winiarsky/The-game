from __future__ import annotations

from statuses.base import Status

ADOPTED_ANCESTRY_DESCRIPTION = (
    "Wybierz jedna powszechna ancestry. Mozesz wybierac feats tej ancestry. "
    "Wymagania weryfikuj recznie. UI podpowie wybor."
)

ADOPTED_ANCESTRY_RACES = [
    "dwarf",
    "elf",
    "gnome",
    "goblin",
    "halfling",
    "human",
]

ADOPTED_ANCESTRY_FEATS = {
    "dwarf": [
        "stonecunning",
        "unburdened_iron",
        "dwarven_lore",
        "rock_runner",
        "vengeful_hatred",
        "dwarven_weapon_familiarity",
    ],
    "elf": [
        "ancestral_longevity",
        "elven_lore",
        "elven_weapon_familiarity",
        "forlorn",
        "nimble_elf",
        "otherworldly_magic",
        "unwavering_mien",
    ],
    "gnome": [
        "gnome_weapon_familiarity",
        "gnome_obsession",
        "animal_accomplice",
        "burrow_elocutionist",
        "fey_fellowship",
        "illusion_sense",
        "first_world_magic",
    ],
    "goblin": [
        "goblin_scuttle",
        "city_scavenger",
        "burn_it",
        "goblin_weapon_familiarity",
        "goblin_song",
        "goblin_lore",
        "junk_tinker",
        "rough_rider",
        "very_sneaky",
    ],
    "halfling": [
        "distracting_shadows",
        "sure_feet",
        "titan_slinger",
        "unfettered_halfling",
        "halfling_luck",
        "halfling_lore",
        "halfling_weapon_familiarity",
        "watchful_halfling",
    ],
    "human": [
        "adapted_cantrip",
        "natural_ambition",
        "general_training",
        "natural_skill",
        "unconventional_weaponry",
        "cooperative_nature",
        "haughty_obstinacy",
    ],
}


def AdoptedAncestryStatus() -> Status:
    """Feat: Adopted Ancestry (opis do UI)."""
    return Status(
        id="adopted_ancestry",
        label="Adopted Ancestry",
        data={
            "ui_description": ADOPTED_ANCESTRY_DESCRIPTION,
            "ui_choice_kind": "adopted_ancestry",
            "adopted_ancestry_races": ADOPTED_ANCESTRY_RACES,
            "adopted_ancestry_feats": ADOPTED_ANCESTRY_FEATS,
        },
    )


ADOPTED_ANCESTRY_STATUS = AdoptedAncestryStatus()

__all__ = [
    "AdoptedAncestryStatus",
    "ADOPTED_ANCESTRY_STATUS",
    "ADOPTED_ANCESTRY_DESCRIPTION",
]
