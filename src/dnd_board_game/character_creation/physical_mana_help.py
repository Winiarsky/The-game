"""Shared, profile-specific passive notes for the UI and physical prints."""

from .boardgame_help import HERO_PASSIVES, RuleNote
from dnd_board_game.actors import Actor, FeatureGrant
from dnd_board_game.rules.charge_rolls import uses_charge
from dnd_board_game.rules.physical_mana import FLAWS, MANA_PASSIVES


HIDDEN_SKILL_FEATURES = frozenset({"expertise", "erynd_expertise", "jack_of_all_trades", "skill_versatility"})


def visible_character_features(actor: Actor) -> tuple[FeatureGrant, ...]:
    """Presentation only: retain retired skill data in the actor and save files."""
    return tuple(f for f in actor.features
                 if not uses_charge(actor) or f.feature_id not in HIDDEN_SKILL_FEATURES)


def physical_mana_passives(hero_id: str) -> tuple[RuleNote, ...]:
    removed = {"Uczeń Życia", "Kusznik", "Odzyskiwanie magiczne", "Ekspertyza", "Ekspertyza zwiadowcy"}
    replacements = {
        "Styl walki: Obrona": "Gdy nosisz pancerz, masz +1 KP. Aplikacja i karta postaci uwzględniają tę premię.",
        "Ulepszony krytyk": "Atak bronią trafia krytycznie, gdy na k20 wypadnie naturalne 19 lub 20. Nie dotyczy testu Siły przy Uderzeniu tarczą.",
        "Żelazna linia": "Gdy Garran i sojusznik flankują wspólnego przeciwnika, ten sojusznik ma +1 KP przeciw atakom tego przeciwnika. Premia nie chroni Garrana ani nie działa przeciw innym wrogom.",
        "Obrona bez pancerza": "Bez pancerza twoja KP wynosi 10 + modyfikator Zręczności + modyfikator Kondycji. Możesz korzystać z tarczy.",
        "Mistrzyni ukrycia": "Ukryj się zużywa akcję dodatkową. Wykonujesz jeden test Zręczności z naładowaniem i innymi premiami; aplikacja wykonuje osobny test wykrycia dla każdego wroga. Remis oznacza wykrycie. Nie potrzebujesz osłony, ale sąsiadujący wróg lub blokujący stan uniemożliwia zwykłe ukrycie.",
        "Skradanie": "Podczas ukrycia możesz przebyć do 20 ft w turze. Dobrowolne ujawnienie się zwiększa ten limit do 25 ft; odejmij od niego ruch już wykonany.",
        "Atak z cienia": "Rapier lub nóż: +1k6 za ukrycie przed celem albo własną flankę; +2k6 za oba. Raz we własnej turze, przy jednym wybranym trafieniu przed obrażeniami. Atak kończy ukrycie. Ukrycie przed celem daje też przewagę ataku.",
        "Pierwsza krew": "Raz we własnej turze trafienie długim łukiem w cel z pełnymi PW dodaje 1k6 obrażeń. Wybierz trafienie przed rzutem obrażeń.",
    }
    notes = tuple(
        RuleNote(
            "Feyowskie pochodzenie" if note.name == "Fey Ancestry" else note.name,
            replacements.get(note.name, note.body),
        )
        for note in HERO_PASSIVES[hero_id]
        if note.name not in removed
    )
    from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile
    profile = hero_profile(hero_id)
    name, body = profile["passive_name"], profile["passive"]
    if hero_id == "erynd":
        notes = (*notes, RuleNote("Praktyka terenowa", "+2 do własnych testów przy obiekcie w eksploracji (uwzględnione na karcie). Nie dodaje punktów many ani premii do pułapek w walce."))
    return (*notes, RuleNote(name, body))


def physical_mana_flaw(hero_id: str) -> RuleNote:
    from dnd_board_game.scenarios.pooled_mana_catalog import hero_profile
    profile = hero_profile(hero_id)
    name, body = profile["flaw_name"], profile["flaw"]
    return RuleNote(name, body)
