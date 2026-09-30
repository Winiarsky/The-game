"""Shared vector signs and stable positions for the 30-cell arena panel."""

from html import escape

# Deliberately drawn paths, independent of font support and readable in mono.
RUNES = [
    ("Rozwidlenie", "M12 21V4M4 5l8 7 8-7"),
    ("Wieża", "M5 21V4h14v17M5 10h14M12 4v17"),
    ("Klepsydra", "M4 3h16L4 21h16Z"),
    ("Trójząb", "M12 22V2M4 3v8h16V3"),
    ("Brama", "M3 21V8l9-6 9 6v13M8 21V11h8v10"),
    ("Romb", "M12 2 21 12 12 22 3 12ZM12 7v10"),
    ("Hak", "M5 3h14v9H9v9M5 17l4 4 4-4"),
    ("Błysk", "M15 2 5 13h8l-4 9 11-13h-8Z"),
    ("Oko", "M2 12 12 5l10 7-10 7ZM12 9v6"),
    ("Schody", "M3 21v-6h6V9h6V3h6M3 3h6"),
    ("Korona", "M3 7l5 5 4-9 4 9 5-5v13H3Z"),
    ("Węzeł", "M3 8h18v8H3ZM8 3v18h8V3Z"),
    ("Grot", "M4 21 12 3l8 18M8 14h8M12 14v7"),
    ("Kotwica", "M12 3v18M6 7h12M3 14l9 7 9-7M3 10v4M21 10v4"),
    ("Spirala", "M20 21H4V3h16v12H10V9h4"),
    ("Kielich", "M4 3h16v7l-8 6-8-6ZM12 16v5M7 21h10"),
    ("Most", "M3 21V3h5v10h8V3h5v18M3 18h18"),
    ("Fala", "M3 5l6 5 6-5 6 5M3 14l6 5 6-5 6 5"),
    ("Klucz", "M5 3h8v8H5ZM9 11v10h11v-5M15 21v-5"),
    ("Iskra", "M12 2l3 7 7 3-7 3-3 7-3-7-7-3 7-3ZM12 8v8M8 12h8"),
]
INFORMATION = ("Gwiazda", "M12 2v20M2 12h20M5 5l14 14M5 19 19 5M8 8h8v8H8Z")
BASIC = [
    ("Ruch", "M15 4a2 2 0 1 0-4 0 2 2 0 1 0 4 0M12 8l-2 6 5 3 2 5M10 14l-3 8M12 8l4 4h4M12 8H8l-4 5"),
    ("Atak", "M5 19 18 6l3-3v6L8 22M3 14l7 7M5 21l-2 2"),
    ("Zmiana broni", "M3 3l18 18M3 21 21 3M3 3h5v5M21 3h-5v5M3 17l4 4M17 21l4-4"),
    ("Przedmiot", "M8 2h8M9 2v7L4 18v4h16v-4l-5-9V2M6 16h12"),
    ("Puste pole", ""),
    ("Koniec tury", "M5 22V3h14l-4 5 4 5H5"),
]
CONTROLS = [
    ("Zmniejsz", "M4 12h16"),
    ("Zwiększ", "M4 12h16M12 4v16"),
    ("Zatwierdź", "M3 12l6 7L21 5"),
    ("Wróć", "M10 4 3 11l7 7M3 11h12a6 6 0 0 1 0 12"),
]
# BASIC/CONTROLS retain the source glyph library used by existing print builders.
# Only SYMBOLS defines physical positions, shared by the live game and new prints.
SYMBOLS = [
    BASIC[0], BASIC[1], BASIC[3], BASIC[5], ("Przerwa", ""),
    *RUNES, INFORMATION, CONTROLS[1], CONTROLS[0], CONTROLS[2], CONTROLS[3],
]


def rune_slot(name: str) -> int:
    """Find a rune in the printed panel without depending on catalog ordering."""
    return next(index for index, (label, _) in enumerate(SYMBOLS) if label == name)


def panel_icon(slot: int) -> str:
    name, path = SYMBOLS[slot]
    if not path:
        return ""
    return (
        f'<svg viewBox="0 0 24 24" class="panel-symbol glyph" data-panel-slot="{slot}" role="img" aria-label="{escape(name)}">'
        f'<path d="{path}"/></svg>'
    )


# Explicit order is the printed contract; catalog sorting must never move a rune.
HERO_PANEL_ABILITIES: dict[str, tuple[str, ...]] = {
    "garran": (
        "second_wind",
        "action_surge",
        "shield_bash",
        "defensive_stance",
        "garran_command_halt",
        "garran_shield_wall",
        "garran_rally",
        "garran_guard_companion",
    ),
    "brakka": (
        "rage",
        "reckless_attack",
        "powerful_strike",
        "shoulder_check",
        "acceleration",
        "deafening_roar",
        "grapple",
    ),
    "mira": (
        "hide",
        "smoke_screen",
        "guard_vault",
        "combat_trap_detection",
        "hamstring_cut",
        "piercing_attack",
        "blade_mistress",
    ),
    "dagna": (
        "sacred_flame",
        "healing_word",
        "bless",
        "preserve_life",
        "divine_care_aura",
        "guiding_bolt",
        "healing_grace_aura",
        "lesser_restoration",
        "turn_undead",
        "spiritual_weapon",
    ),
    "lorian": (
        "mana_inspiration",
        "mana_tuning",
        "mana_transmutation",
        "mana_transfer",
        "mana_reservation",
        "mana_recovery",
        "mana_refresh",
        "optical_scope",
        "mocking_shot",
        "entangling_shot",
        "panic_whisper",
        "thunderwave",
    ),
    "nimra": (
        "nimra_frost_pulse",
        "nimra_acid_splash",
        "nimra_mind_spike",
        "nimra_flame_fan",
        "nimra_force_wave",
        "nimra_sticky_matrix",
        "misty_step",
        "nimra_sleep",
        "nimra_fog",
        "nimra_web",
        "nimra_lightning_path",
        "nimra_mind_break",
        "nimra_stasis",
        "shatter",
        "nimra_sculpt_field",
        "nimra_distant_spell",
        "nimra_overcharged_spell",
        "nimra_forced_weave",
        "nimra_energy_transmutation",
    ),
    "erynd": (
        "hunters_mark",
        "cunning_action",
        "aim",
        "anchoring_arrow",
        "exposing_arrow",
        "disrupting_arrow",
        "double_shot",
        "misty_step",
        "spike_growth",
    ),
}


# Preserve legacy ability ids for older scenarios. Current rune cards provide
# their own explicit slots below, independently of this compatibility ordering.
from dnd_board_game.rules.shared_mana_catalog import CATALOG
for _hero_id, _previous in tuple(HERO_PANEL_ABILITIES.items()):
    _ids = [a.id for a in CATALOG if a.hero_id == _hero_id]
    _slots = [key if key in _ids else "" for key in _previous]
    for _key in _ids:
        if _key not in _slots:
            if "" in _slots:
                _slots[_slots.index("")] = _key
            else:
                _slots.append(_key)
    HERO_PANEL_ABILITIES[_hero_id] = tuple(_slots)


def ability_panel_slot(hero_id: str, ability_id: str) -> int:
    from dnd_board_game.scenarios.rune_catalog import rune_card
    card = rune_card(hero_id, ability_id)
    if card is not None:
        return card.slot
    return 5 + HERO_PANEL_ABILITIES[hero_id].index(ability_id)


PANEL_CONTROLS: tuple[tuple[int, str, str], ...] = (
    (
        0,
        "Ruch",
        "Wybierz podświetlone pole figurki i zatwierdź ruch. Pozostały ruch możesz wykorzystać później w tej turze.",
    ),
    (
        1,
        "Atak",
        "Wskaż pole legalnego celu dla wyposażonej broni i zatwierdź. Zwykły atak nie kosztuje run.",
    ),
    (
        2,
        "Przedmiot",
        "Podejrzyj użycie przedmiotu i zatwierdź. Zastępuje zwykły atak w tej turze.",
    ),
    (
        3,
        "Koniec tury",
        "Zatwierdź zakończenie tury. Niewydane runy zostają; przydział odbywa się tylko na początku walki.",
    ),
    (25, "Informacja o bohaterze", "Niebieska Gwiazda pokazuje aktualne PW, stany, zasoby, cechy i wyposażenie. Powrót zachowuje wybraną akcję i cel."),
    (26, "Zwiększ", "Zwiększ wynik kości lub przewiń dalej."),
    (27, "Zmniejsz", "Zmniejsz wynik kości lub przewiń wstecz."),
    (28, "Zatwierdź", "Zatwierdź cel, wynik kości lub końcowe podsumowanie."),
    (
        29,
        "Wróć",
        "Z podglądu wróć do pełnego menu. Podczas wpisywania wróć do poprzedniego wyniku.",
    ),
)
