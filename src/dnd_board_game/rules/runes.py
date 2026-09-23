"""Finite encounter rune resources; all transitions are deterministic and immutable."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, replace
from typing import Mapping, Sequence

RESOURCE_RUNES = ("Rozwidlenie", "Wieża", "Klepsydra", "Trójząb", "Brama", "Romb", "Hak",
                  "Błysk", "Oko", "Schody", "Korona", "Węzeł", "Grot", "Kotwica", "Kielich", "Klucz")
_LEGACY_RESOURCE_RUNES = ("Wieża", "Klepsydra", "Brama", "Błysk", "Oko", "Korona", "Węzeł", "Kotwica", "Kielich", "Klucz")
HAND_LIMIT = 7


@dataclass(frozen=True, slots=True)
class RunePool:
    heroes: tuple[str, ...]
    deck: tuple[str, ...]
    offer: tuple[str, ...]
    hands: tuple[tuple[str, tuple[str, ...]], ...]
    discard: tuple[str, ...] = ()
    actor_index: int = 0
    picks: tuple[str, ...] = ()
    phase: str = "allocation"
    used_once: tuple[tuple[str, str], ...] = ()
    deck_version: int = 2

    def __post_init__(self) -> None:
        if not self.heroes or len(set(self.heroes)) != len(self.heroes):
            raise ValueError("Wskaż różnych bohaterów przydziału.")
        if not 0 <= self.actor_index < len(self.heroes) or self.phase not in {"allocation", "ready"}:
            raise ValueError("Nieprawidłowy etap przydziału run.")
        if tuple(h for h, _ in self.hands) != self.heroes or any(len(c) > HAND_LIMIT for _, c in self.hands):
            raise ValueError("Nieprawidłowe ręce bohaterów lub limit siedmiu run.")
        cards = (*self.deck, *self.offer, *self.discard, *(c for _, cards in self.hands for c in cards))
        if type(self.deck_version) is not int or self.deck_version not in {1, 2}:
            raise ValueError("Nieznana wersja talii run.")
        composition = _LEGACY_RESOURCE_RUNES if self.deck_version == 1 else RESOURCE_RUNES
        if Counter(cards) != Counter({r: len(self.heroes) for r in composition}):
            raise ValueError("Nie zgadza się skład skończonej talii run.")
        if Counter(self.picks) - Counter(self.hand(self.actor)):
            raise ValueError("Historia wyborów nie odpowiada ręce bohatera.")

    @property
    def actor(self) -> str:
        return self.heroes[self.actor_index]

    def hand(self, hero: str) -> tuple[str, ...]:
        return dict(self.hands).get(hero, ())

    def as_payload(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_payload(cls, raw: Mapping[str, object]) -> RunePool:
        return cls(heroes=tuple(raw["heroes"]), deck=tuple(raw["deck"]), offer=tuple(raw["offer"]),
                   hands=tuple((h, tuple(cards)) for h, cards in raw["hands"]),
                   discard=tuple(raw.get("discard", ())), actor_index=int(raw.get("actor_index", 0)),
                   picks=tuple(raw.get("picks", ())), phase=str(raw.get("phase", "allocation")),
                   used_once=tuple(tuple(v) for v in raw.get("used_once", ())),
                   deck_version=raw.get("deck_version", 1))


def new_runes(heroes: Sequence[str], shuffled_deck: Sequence[str]) -> RunePool:
    heroes, deck = tuple(heroes), tuple(shuffled_deck)
    count = len(heroes) + 2
    return RunePool(heroes, deck[count:], deck[:count], tuple((h, ()) for h in heroes))


def _hands(pool: RunePool, hero: str, cards: Sequence[str]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if hero not in pool.heroes:
        raise ValueError("Nieznany właściciel run.")
    return tuple((h, tuple(cards) if h == hero else hand) for h, hand in pool.hands)


def take_rune(pool: RunePool, rune: str) -> RunePool:
    if pool.phase != "allocation" or rune not in pool.offer:
        raise ValueError("Ta runa nie jest dostępna w puli przydziału.")
    if len(pool.hand(pool.actor)) >= HAND_LIMIT:
        raise ValueError("Bohater ma już siedem run.")
    offer = list(pool.offer)
    offer.remove(rune)
    return replace(pool, offer=tuple(offer), hands=_hands(pool, pool.actor, (*pool.hand(pool.actor), rune)), picks=(*pool.picks, rune))


def undo_rune(pool: RunePool) -> RunePool:
    if pool.phase != "allocation" or not pool.picks:
        raise ValueError("Nie ma wyboru tej postaci do cofnięcia.")
    rune = pool.picks[-1]
    hand = list(pool.hand(pool.actor))
    hand.reverse()
    hand.remove(rune)
    hand.reverse()
    return replace(pool, offer=(*pool.offer, rune), hands=_hands(pool, pool.actor, hand), picks=pool.picks[:-1])


def confirm_allocation(pool: RunePool) -> RunePool:
    if pool.phase != "allocation":
        raise ValueError("Przydział został już zakończony.")
    if pool.actor_index + 1 < len(pool.heroes):
        return replace(pool, actor_index=pool.actor_index + 1, picks=())
    if not pool.offer:
        return replace(pool, picks=(), phase="ready")
    if not any(len(pool.hand(hero)) < HAND_LIMIT for hero in pool.heroes):
        return replace(pool, offer=(), discard=(*pool.discard, *pool.offer), picks=(), phase="ready")
    return replace(pool, actor_index=0, picks=())


def plan_payment(hand: Sequence[str], costs: Sequence[str]) -> tuple[str, ...]:
    """Reserve specific runes before wildcard payments, preserving scarce choices."""
    remaining = list(hand)
    paid: list[str] = []
    for rune in (*[c for c in costs if c != "*"], *[c for c in costs if c == "*"]):
        selected = remaining[0] if rune == "*" and remaining else rune
        if selected not in remaining:
            raise ValueError(f"Brakuje runy: {rune if rune != '*' else 'dowolna'}.")
        remaining.remove(selected)
        paid.append(selected)
    return tuple(paid)


def spend_runes(pool: RunePool, hero: str, costs: Sequence[str], *, once: str = "") -> RunePool:
    if pool.phase != "ready":
        raise ValueError("Najpierw zakończ przydział run.")
    if once and (hero, once) in pool.used_once:
        raise ValueError("Ta moc została już użyta w tej walce.")
    payment = plan_payment(pool.hand(hero), costs)
    hand = list(pool.hand(hero))
    for rune in payment:
        hand.remove(rune)
    return replace(pool, hands=_hands(pool, hero, hand), discard=(*pool.discard, *payment),
                   used_once=(*pool.used_once, (hero, once)) if once else pool.used_once)


def exchange_rune(pool: RunePool, hero: str, rune: str) -> RunePool:
    if not pool.deck or rune not in pool.hand(hero):
        raise ValueError("Wymiana wymaga runy na ręce i runy w talii.")
    hand = list(pool.hand(hero))
    hand.remove(rune)
    hand.append(pool.deck[0])
    return replace(pool, deck=pool.deck[1:], discard=(*pool.discard, rune), hands=_hands(pool, hero, hand))


def recover_rune(pool: RunePool, hero: str, rune: str) -> RunePool:
    if rune not in pool.discard or len(pool.hand(hero)) >= HAND_LIMIT:
        raise ValueError("Nie można odzyskać tej runy do ręki.")
    discard = list(pool.discard)
    discard.remove(rune)
    return replace(pool, discard=tuple(discard), hands=_hands(pool, hero, (*pool.hand(hero), rune)))


def card_payment_requirements(hand: Sequence[str], required: Sequence[str]) -> tuple[str, ...]:
    """Reserve named runes before exposing wildcard choices to the player."""
    if not required:
        return ()
    remaining = list(hand)
    # Reserve a named booster so fallback payment cannot accidentally consume it.
    named_boosts = tuple(r for r in required[1:] if r != "*")
    paid_boosts = plan_payment(remaining, named_boosts)
    for rune in paid_boosts:
        remaining.remove(rune)
    base = required[0]
    base_cost = (base,) if base in remaining or base == "*" else ("*", "*")
    expanded = (*base_cost, *named_boosts, *(r for r in required[1:] if r == "*"))
    plan_payment(hand, expanded)
    return expanded


def available_payment_runes(hand: Sequence[str], required: Sequence[str]) -> tuple[str, ...]:
    """Runes left after reserving every mandatory named component."""
    remaining = list(hand)
    for rune in card_payment_requirements(hand, required):
        if rune != "*":
            remaining.remove(rune)
    return tuple(remaining)


def plan_card_payment(hand: Sequence[str], required: Sequence[str],
                      selected_wildcards: Sequence[str] | None = None) -> tuple[str, ...]:
    """Quote automatically, or validate the player's exact wildcard choices."""
    expanded = card_payment_requirements(hand, required)
    remaining = available_payment_runes(hand, required)
    count = expanded.count("*")
    selected = tuple(remaining[:count] if selected_wildcards is None else selected_wildcards)
    if len(selected) != count or Counter(selected) - Counter(remaining):
        raise ValueError("Wybierz dokładnie dostępne runy na dowolne składniki kosztu.")
    choices = iter(selected)
    return tuple(next(choices) if rune == "*" else rune for rune in expanded)


def validate_card_payment(hand: Sequence[str], required: Sequence[str],
                          payment: Sequence[str] | None) -> tuple[str, ...]:
    """A commit may never silently decide which wildcard runes to discard."""
    expanded = card_payment_requirements(hand, required)
    if payment is None:
        if "*" in expanded:
            raise ValueError("Najpierw wybierz runy, którymi zapłacisz dowolny koszt.")
        return expanded
    paid = tuple(payment)
    named = Counter(r for r in expanded if r != "*")
    if (len(paid) != len(expanded) or named - Counter(paid)
            or Counter(paid) - Counter(hand) or any(r not in RESOURCE_RUNES for r in paid)):
        raise ValueError("Wybrane runy nie pokrywają pełnego kosztu karty.")
    return paid
