"""Explicit physical setups for lessons; never used by ordinary encounters."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from itertools import product
from typing import Mapping

from dnd_board_game.rules.pooled_mana import COLORS, PooledMana
from dnd_board_game.rules.pooled_mana_catalog import PoolAbility

FOUNDATIONS = (
    ("pool_draw", "Dobór i wspólna karta", "Przetasuj komplet, odkryj dwie karty i zgłoś ich kolory. Wybierz jedną runą. Drugą zostaw dla następnego bohatera. Każda karta daje +1 do testów. Atut daje 2 ładunku zdolności; reszta 1. Trzy atuty odblokowują ultę, ale dobór trwa do 6 kart."),
    ("pool_charge", "Pełne naładowanie i pasywy", "Przygotuj wskazane 5 kart. Dobierz szóstą: osiągniesz limit osobistej puli. Sprawdź statusy kolorów i premię naładowania +6 do ataków, testów cech i obron zamiast biegłości; ✓ rozpocznie próbną kolejną turę już bez doboru."),
    ("pool_expire", "Upływ rundy", "Dobierz kartę. ✓ przechodzi do końca próbnej rundy. Zgłoś kolor jednej karty z wierzchu odłożonej do wygasłych; Lorian nie może jej odzyskać przed drainem."),
    ("pool_hold", "Zwykły atak i oszczędzanie", "Dobierz kartę, a potem wykonaj zwykły atak bronią w kukłę. Rzut: k20 + cecha broni + naładowanie + inne premie. Każda fizyczna karta daje +1 do testu, maks. +6. Atut nie podwaja tej premii. Nie dodajesz tej premii do obrażeń. Twoja pula pozostaje; zwykły atak nie spala kart."),
    ("pool_burn", "Spalenie odkrytej karty", "Dobierz kartę. Potem uruchom zapowiedziane spalenie przez ✓. Odłóż pozostawioną kartę do spalonych, nie na spód talii."),
    ("pool_prison", "Uwięzienie i uwolnienie", "Dobierz kartę. ✓ symuluje uwięzienie odkrytej karty przez kukłę. Następne ✓ symuluje jej pokonanie: oddaj uwięzioną kartę na spód."),
    ("pool_drain", "Mana drain zbiera cały komplet", "Przygotujemy końcówkę talii: po tasowaniu pozostaw trzy karty wskazane w instrukcji, resztę połóż jako spalone. Dobierz kartę. ✓ uruchomi spalenie dwóch kart przy zbyt małej talii. Zbierz i przetasuj WSZYSTKIE karty."),
)


def lesson_hand(definition: PoolAbility, values: Mapping[str, int], copies: int,
                boost_color: str = "") -> tuple[str, ...]:
    if definition.free:
        return ()
    candidates = []
    for counts in product(range(copies + 1), repeat=5):
        if sum(counts) > 6:
            continue
        hand = tuple(c for c, n in zip(COLORS, counts) for _ in range(n))
        try:
            definition.validate(hand, values)
        except ValueError:
            continue
        candidates.append(hand)
    if not candidates:
        raise ValueError("Nieosiągalny układ lekcji w tej talii.")
    return min(candidates, key=lambda hand: (len(hand), sum(values[c] for c in hand), hand))


def prepare_lesson(pool: PooledMana, ability_id: str, hand: tuple[str, ...]) -> PooledMana:
    """Called after an explicitly confirmed fresh shuffle; UI explains removed cards."""
    if ability_id == "pool_drain":
        all_cards = list(COLORS) * pool.copies
        for c in ("C", "B", "Z"):
            all_cards.remove(c)
        return replace(pool, deck=("C", "B", "Z"), burned=tuple(all_cards), offer=(), pools=(),
                       phase="reveal", draw_due=True)
    if ability_id == "pool_charge":
        return replace(pool, deck=(None,) * (pool.copies * 5 - len(hand)), pools=((pool.actor, hand),),
                       offer=(), draw_due=True, phase="reveal")
    if ability_id.startswith("pool_"):
        return pool
    burned = ()
    if ability_id in {"mana_recovery", "mana_great_tuning"}:
        counts = Counter(hand)
        available = tuple(c for c in COLORS for _ in range(pool.copies - counts[c]))
        burned = available[:min(5, len(available))]
    return replace(pool, deck=(None,) * (pool.copies * 5 - len(hand) - len(burned)),
                   pools=((pool.actor, hand),), burned=burned, offer=(), draw_due=False, phase="reveal")
