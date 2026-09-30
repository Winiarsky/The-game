"""Personal, rechargeable rune tokens. No files, UI or hardware dependencies."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, replace
from typing import Mapping, Sequence

CATEGORIES = ("offense", "defense", "mobility", "aura")
SYMBOLS = (
    ("Grot", "Hak", "Trójząb", "Błysk"),
    ("Wieża", "Kotwica", "Brama", "Węzeł"),
    ("Oko", "Schody", "Rozwidlenie", "Klepsydra"),
    ("Korona", "Kielich", "Klucz", "Romb"),
)
NAMES = dict(zip(CATEGORIES, ("Ofensywa", "Obrona", "Mobilność", "Aura")))


def category_of(rune: str) -> str:
    for category, symbols in zip(CATEGORIES, SYMBOLS):
        if rune in symbols:
            return category
    raise ValueError("Nieznany żeton runy.")


@dataclass(frozen=True, slots=True)
class RuneBaskets:
    heroes: tuple[str, ...]
    capacities: tuple[tuple[str, tuple[int, ...]], ...]
    hands: tuple[tuple[str, tuple[str, ...]], ...]
    phase: str = "allocation"
    actor_index: int = 0
    category_index: int = 0
    picks: tuple[str, ...] = ()
    used_once: tuple[tuple[str, str], ...] = ()
    recharge_actor: str = ""
    recharge_remaining: int = 0
    recharge_category: str = ""
    recharge_roll: int = 2
    recharge_fixed_category: str = ""
    regeneration_used: tuple[tuple[str, str, int], ...] = ()
    model: str = "baskets_v02"

    def __post_init__(self) -> None:
        if not self.heroes or len(set(self.heroes)) != len(self.heroes):
            raise ValueError("Wskaż różnych właścicieli koszyków.")
        if tuple(h for h, _ in self.hands) != self.heroes or tuple(h for h, _ in self.capacities) != self.heroes:
            raise ValueError("Koszyki nie odpowiadają bohaterom.")
        if not 0 <= self.actor_index < len(self.heroes) or not 0 <= self.category_index < 4:
            raise ValueError("Nieprawidłowy etap przygotowania koszyków.")
        if self.phase not in {"allocation", "ready", "recharge_category", "recharge_roll", "recharge_review", "focus_confirm", "regeneration"}:
            raise ValueError("Nieznany etap koszyków.")
        for hero, limits in self.capacities:
            if len(limits) != 4 or any(type(n) is not int or not 0 <= n <= 8 for n in limits):
                raise ValueError("Nieprawidłowa pojemność koszyka.")
            counts = Counter(category_of(r) for r in self.hand(hero))
            if any(counts[c] > n for c, n in zip(CATEGORIES, limits)):
                raise ValueError("Przekroczono pojemność koszyka.")
        if Counter(self.picks) - Counter(self.hand(self.actor)):
            raise ValueError("Nieprawidłowa historia deklarowanych żetonów.")
        if self.phase.startswith("recharge") and (self.recharge_actor not in self.heroes or self.recharge_remaining < 1):
            raise ValueError("Brak właściciela ładowania.")
        if self.phase in {"recharge_roll", "recharge_review"} and self.recharge_category not in CATEGORIES:
            raise ValueError("Wybierz kategorię ładowania.")
        if type(self.recharge_roll) is not int or not 1 <= self.recharge_roll <= 4:
            raise ValueError("Wynik k4 musi wynosić od 1 do 4.")

    @property
    def actor(self) -> str:
        return self.recharge_actor or self.heroes[self.actor_index]

    @property
    def category(self) -> str:
        return CATEGORIES[self.category_index]

    @property
    def deck(self) -> tuple[str, ...]:
        return ()

    @property
    def offer(self) -> tuple[str, ...]:
        return ()

    @property
    def discard(self) -> tuple[str, ...]:
        return ()

    def hand(self, hero: str) -> tuple[str, ...]:
        return dict(self.hands).get(hero, ())

    def capacity(self, hero: str, category: str) -> int:
        if hero not in self.heroes or category not in CATEGORIES:
            raise ValueError("Nieznany koszyk bohatera.")
        return dict(self.capacities)[hero][CATEGORIES.index(category)]

    def charged(self, hero: str, category: str) -> tuple[str, ...]:
        return tuple(r for r in self.hand(hero) if category_of(r) == category)

    def missing(self, hero: str, category: str) -> int:
        return self.capacity(hero, category) - len(self.charged(hero, category))

    def as_payload(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_payload(cls, raw: Mapping[str, object]) -> RuneBaskets:
        data = dict(raw)
        for key in ("heroes", "picks"):
            data[key] = tuple(data.get(key, ()))
        for key in ("capacities", "hands"):
            data[key] = tuple((h, tuple(values)) for h, values in data[key])
        for key in ("used_once", "regeneration_used"):
            data[key] = tuple(tuple(row) for row in data.get(key, ()))
        return cls(**data)


def new_baskets(capacities: Mapping[str, Mapping[str, int]]) -> RuneBaskets:
    heroes = tuple(capacities)
    return RuneBaskets(heroes, tuple((h, tuple(capacities[h][c] for c in CATEGORIES)) for h in heroes),
                       tuple((h, ()) for h in heroes))


def _hands(pool: RuneBaskets, hero: str, cards: Sequence[str]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if hero not in pool.heroes:
        raise ValueError("Nieznany właściciel run.")
    return tuple((h, tuple(cards) if h == hero else hand) for h, hand in pool.hands)


def declare_token(pool: RuneBaskets, rune: str) -> RuneBaskets:
    if pool.phase != "allocation" or category_of(rune) != pool.category or not pool.missing(pool.actor, pool.category):
        raise ValueError("Wybierz żeton bieżącej kategorii w granicach jej pojemności.")
    return replace(pool, hands=_hands(pool, pool.actor, (*pool.hand(pool.actor), rune)), picks=(*pool.picks, rune))


def undo_token(pool: RuneBaskets) -> RuneBaskets:
    if pool.phase != "allocation" or not pool.picks:
        raise ValueError("Brak żetonu do cofnięcia.")
    cards = list(pool.hand(pool.actor))
    cards.remove(pool.picks[-1])
    return replace(pool, hands=_hands(pool, pool.actor, cards), picks=pool.picks[:-1])


def confirm_category(pool: RuneBaskets) -> RuneBaskets:
    if pool.phase != "allocation" or pool.missing(pool.actor, pool.category):
        raise ValueError("Najpierw zadeklaruj wszystkie żetony tej kategorii.")
    if pool.category_index < 3:
        return replace(pool, category_index=pool.category_index + 1, picks=())
    if pool.actor_index + 1 < len(pool.heroes):
        return replace(pool, actor_index=pool.actor_index + 1, category_index=0, picks=())
    return replace(pool, phase="ready", picks=())


def spend_tokens(pool: RuneBaskets, payments: Mapping[str, Sequence[str]], *, once: tuple[str, str] | None = None) -> RuneBaskets:
    if pool.phase != "ready":
        raise ValueError("Najpierw zakończ przygotowanie lub ładowanie run.")
    if once and once in pool.used_once:
        raise ValueError("Ta moc została już wykorzystana w tej walce.")
    for hero, symbols in payments.items():
        if hero not in pool.heroes or Counter(symbols) - Counter(pool.hand(hero)):
            raise ValueError("Brakuje zadeklarowanych żetonów. Wybierz koszt ponownie.")
    hands = pool.hands
    for hero, symbols in payments.items():
        cards = list(dict(hands)[hero])
        for rune in symbols:
            cards.remove(rune)
        hands = tuple((h, tuple(cards) if h == hero else hand) for h, hand in hands)
    return replace(pool, hands=hands, used_once=(*pool.used_once, once) if once else pool.used_once)


def start_recharge(pool: RuneBaskets, hero: str, count: int, category: str = "") -> RuneBaskets:
    if pool.phase != "ready" or hero not in pool.heroes or count < 1:
        raise ValueError("Nie można teraz ładować run.")
    missing = pool.missing(hero, category) if category else sum(pool.missing(hero, c) for c in CATEGORIES)
    if not missing:
        raise ValueError("Wskazane koszyki są pełne.")
    return replace(pool, phase="recharge_roll" if category else "recharge_category", recharge_actor=hero,
                   recharge_remaining=min(count, missing), recharge_category=category, recharge_fixed_category=category, recharge_roll=2)


def confirm_recharge(pool: RuneBaskets) -> RuneBaskets:
    if pool.phase != "recharge_review" or not pool.missing(pool.actor, pool.recharge_category):
        raise ValueError("Brak wyniku ładowania do zatwierdzenia.")
    rune = SYMBOLS[CATEGORIES.index(pool.recharge_category)][pool.recharge_roll - 1]
    remaining = pool.recharge_remaining - 1
    return replace(pool, hands=_hands(pool, pool.actor, (*pool.hand(pool.actor), rune)),
                   phase=("recharge_roll" if pool.recharge_fixed_category else "recharge_category") if remaining else "ready", recharge_remaining=remaining,
                   recharge_category=pool.recharge_fixed_category if remaining else "", recharge_fixed_category=pool.recharge_fixed_category if remaining else "",
                   recharge_actor=pool.actor if remaining else "", recharge_roll=2)
