from __future__ import annotations

from statuses.base import Status
from statuses.classes.bard.feats.reach_spell import REACH_SPELL_STATUS
from statuses.classes.bard.inspiration import INSPIRATION_STATUS

BARD_PROMPT = (
    "KLASA: BARD\n"
    "Key Ability: Charyzma (+2 na 1. poziomie).\n"
    "Punkty Zycia: 8 + modyfikator Kondycji.\n\n"
    "Bieglosci startowe:\n"
    "- Percepcja: Expert\n"
    "- Rzuty obronne: Fortitude Trained, Reflex Trained, Will Expert\n"
    "- Skille: Performance Trained + 4 dodatkowe skille (+ INT mod)\n\n"
    "Magia:\n"
    "- Tradycja: okultystyczna (occult)\n"
    "- Repertuar na 1. poziomie: 5 cantripow i 2 czary 1. rangi\n"
    "- 5 cantripow wybierasz z listy occult podczas tworzenia postaci\n"
    "- Composition cantrips z klasy (automatycznie, bez wyboru): Inspire Courage, Counter Performance\n"
    "- Sloty na 1. poziomie: 2 czary 1. rangi / dzien\n"
    "- Focus Pool: 1 Focus Point\n"
    "Podczas setupu wybierasz Muse i kompletujesz repertuar."
)


def BardStatus() -> Status:
    """Class: Bard (opis do UI prompta)."""
    return Status(
        id="bard",
        label="Bard",
        data={
            "ui_prompt": BARD_PROMPT,
            "class_hp": 8,
            "ui_choice_kind": "bard_setup",
            "bard_spell_tradition": "occult",
            "bard_known_cantrips_at_level1": 5,
            "bard_known_rank_1_spells_at_level1": 2,
            "bard_rank_1_slots_per_day": 2,
            "bard_bonus_cantrips": ["inspire_courage", "counter_performance"],
            "bard_bonus_focus_spells": ["counter_performance"],
            "set_actor_attrs": {"focus_point": 1, "class_name": "bard"},
            "grants_statuses": [INSPIRATION_STATUS, REACH_SPELL_STATUS],
        },
    )


BARD_STATUS = BardStatus()

__all__ = [
    "BARD_PROMPT",
    "BardStatus",
    "BARD_STATUS",
]
