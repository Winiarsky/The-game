"""Deterministic physical-card economy, shared by play and seeded evaluation.

Unknown cards are represented by None. The physical adapter reports revelations;
the simulation adapter may provide a completely known deck. No RNG or IO here.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, replace
from typing import Mapping

COLORS = ("C", "B", "Z", "F", "N")
MANA_LIMIT = 6
CHARGE_BONUS_TIERS = tuple((count, count) for count in range(MANA_LIMIT + 1))


def charge_roll_bonus(card_count: int) -> int:
    """Every physical card grants +1; trump never doubles a test bonus."""
    return max(0, min(MANA_LIMIT, card_count))


def ability_charge(hand: tuple[str, ...], values: Mapping[str, int]) -> int:
    return min(MANA_LIMIT, sum(values[c] for c in hand))

MANA_PRESSURE_FEATURES = frozenset({"mana_burn_offer", "mana_burn_deck", "mana_prison"})


def deck_copies(players: int) -> int:
    """Five colours; ten cards per hero, at least twenty-five in the encounter."""
    if not 1 <= players <= 7:
        raise ValueError("Talia wymaga 1–7 bohaterów.")
    return max(5, 2 * players)


@dataclass(frozen=True, slots=True)
class PooledMana:
    heroes: tuple[str, ...]
    copies: int
    deck: tuple[str | None, ...]
    offer: tuple[str, ...] = ()
    pools: tuple[tuple[str, tuple[str, ...]], ...] = ()
    burned: tuple[str, ...] = ()
    prisons: tuple[tuple[str, tuple[str, ...]], ...] = ()
    phase: str = "setup"
    actor: str = ""
    draw_due: bool = False
    cycle: int = 1
    revision: int = 0
    pending_count: int = 0
    captor: str = ""
    reason: str = "Nowa walka: zbierz komplet i przetasuj talię."
    last_paid: tuple[str, ...] = ()
    used: tuple[str, ...] = ()
    turns: int = 0
    catalog_version: int = 3
    values: tuple[tuple[str, tuple[int, ...]], ...] = ()
    expired: tuple[str, ...] = ()
    burn_due: int = 0
    resume_draw: bool = False
    excluded: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.catalog_version not in {1, 2, 3}:
            raise ValueError("Nieobsługiwana wersja katalogu zapisu many.")
        if not self.heroes or len(set(self.heroes)) != len(self.heroes) or type(self.copies) is not int or self.copies < 1:
            raise ValueError("Nieprawidłowy skład talii.")
        if self.phase not in {"setup", "reveal", "choose", "ready", "drain", "burn", "prison", "release", "expire"}:
            raise ValueError("Nieznana faza many.")
        if len(self.offer) > 2 or self.pending_count < 0 or self.burn_due < 0:
            raise ValueError("Nieprawidłowa oferta lub spalanie.")
        if len(dict(self.pools)) != len(self.pools) or any(h not in self.heroes for h, _ in self.pools):
            raise ValueError("Nieprawidłowy właściciel puli.")
        if len(dict(self.values)) != len(self.values) or any(h not in self.heroes or len(v) != 5 or any(type(n) is not int or n < 1 for n in v) for h, v in self.values):
            raise ValueError("Nieprawidłowa tabela punktów ładunku.")
        if len(dict(self.prisons)) != len(self.prisons):
            raise ValueError("Powtórzony właściciel więzienia many.")
        if any(c not in COLORS for c in (*self.offer, *self.burned, *self.expired, *self.excluded, *(c for _, hand in (*self.pools, *self.prisons) for c in hand))):
            raise ValueError("Ujawniona karta wymaga znanego koloru.")
        cards = (*self.deck, *self.offer, *self.burned, *self.expired, *self.excluded,
                 *(c for _, hand in self.pools for c in hand),
                 *(c for _, hand in self.prisons for c in hand))
        counts = Counter(c for c in cards if c is not None)
        if len(cards) != 5 * self.copies or any(c not in COLORS or n > self.copies for c, n in counts.items()):
            raise ValueError("Karty nie zgadzają się z kompletem talii.")

    @property
    def composition(self) -> dict[str, int]:
        return {c: self.copies - self.excluded.count(c) for c in COLORS}

    @property
    def total(self) -> int:
        return 5 * self.copies - len(self.excluded)

    def point_values(self, actor: str) -> dict[str, int]:
        return dict(zip(COLORS, dict(self.values).get(actor, (1, 1, 1, 1, 1))))

    def points(self, actor: str) -> int:
        values = self.point_values(actor)
        return ability_charge(self.hand(actor), values)

    def roll_bonus(self, actor: str) -> int:
        return charge_roll_bonus(len(self.hand(actor)))

    def full(self, actor: str) -> bool:
        return len(self.hand(actor)) >= MANA_LIMIT

    def hand(self, actor: str) -> tuple[str, ...]:
        return dict(self.pools).get(actor, ())

    def as_payload(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_payload(cls, data: Mapping[str, object]) -> PooledMana:
        values = dict(data)
        for key in ("heroes", "deck", "offer", "burned", "last_paid", "used", "expired", "excluded"):
            values[key] = tuple(values.get(key, ()))
        for key in ("pools", "prisons", "values"):
            values[key] = tuple((str(owner), tuple(cards)) for owner, cards in values.get(key, ()))
        if values.get('catalog_version', 1) < 3:
            # Preserve physical zones, including historical overfull hands. New
            # draws cannot exceed six; the next drain clears legacy overflow.
            values['values'] = tuple((hero, tuple(2 if i == max(range(5), key=lambda j: old[j]) else 1
                                                  for i in range(5))) for hero, old in values['values'])
            values['catalog_version'] = 3
            if values.get('actor') in values.get('heroes', ()):
                hand = dict(values['pools']).get(values['actor'], ())
                if len(hand) >= MANA_LIMIT:
                    values['draw_due'] = False
                    if values.get('phase') == 'choose': values['phase'] = 'ready'
        return cls(**values)


def new_mana(heroes: tuple[str, ...], actor: str = "", *, copies: int | None = None, values: Mapping[str, Mapping[str, int]] | None = None, excluded: tuple[str, ...] = ()) -> PooledMana:
    count = deck_copies(len(heroes)) if copies is None else copies
    return PooledMana(heroes, count, (None,) * (5 * count - len(excluded)), actor=actor, draw_due=actor in heroes, excluded=excluded,
                      values=tuple((h, tuple(v[c] for c in COLORS)) for h, v in (values or {}).items()))


def _change(state: PooledMana, **values: object) -> PooledMana:
    return replace(state, revision=state.revision + 1, **values)


def _fill_phase(state: PooledMana) -> str:
    if len(state.offer) < 2 and state.deck:
        return "reveal"
    return "choose" if state.draw_due and state.offer else "ready"


def confirm_shuffle(state: PooledMana, deck: tuple[str | None, ...] | None = None) -> PooledMana:
    if state.phase not in {"setup", "drain"}:
        raise ValueError("Nie ma tasowania do potwierdzenia.")
    fresh = new_mana(state.heroes, state.actor, copies=state.copies, excluded=state.excluded)
    fresh = replace(fresh, deck=deck if deck is not None else fresh.deck,
                    draw_due=state.draw_due, cycle=state.cycle + int(state.phase == "drain"),
                    revision=state.revision, turns=state.turns, used=state.used, values=state.values, phase="reveal",
                    reason="Odkryj karty i zgłoś ich kolory runami.")
    return _change(fresh)


def start_turn(state: PooledMana, actor: str, *, round_end: bool = False) -> PooledMana:
    if state.phase != "ready" or state.burn_due:
        raise ValueError("Dokończ operację many przed zmianą tury.")
    updated = _change(state, actor=actor, draw_due=actor in state.heroes and not state.full(actor),
                      used=tuple(k for k in state.used if not k.startswith(actor + ":")),
                      turns=state.turns + 1, last_paid=())
    if round_end:
        if not updated.deck:
            return drain(updated, "Brak karty do wygaśnięcia na koniec rundy.")
        return replace(updated, phase="expire", pending_count=1, resume_draw=True, captor="")
    if not updated.draw_due:
        return updated
    if not state.deck and not state.offer:
        return drain(updated, "Brak karty do obowiązkowego doboru.")
    return replace(updated, phase=_fill_phase(updated))


def reveal(state: PooledMana, color: str) -> PooledMana:
    if state.phase != "reveal" or not state.deck or color not in COLORS:
        raise ValueError("Nie można teraz odkryć tej karty.")
    if state.deck[0] is not None and state.deck[0] != color:
        raise ValueError("Kolor nie zgadza się ze znanym wierzchem talii.")
    updated = _change(state, deck=state.deck[1:], offer=(*state.offer, color))
    return replace(updated, phase=_fill_phase(updated))


def take(state: PooledMana, index: int) -> PooledMana:
    if state.phase != "choose" or not state.draw_due or type(index) is not int or not 0 <= index < len(state.offer):
        raise ValueError("Wybierz jedną z odkrytych kart.")
    if state.full(state.actor):
        raise ValueError("Masz już 6 kart many. Nie dobierasz kolejnej.")
    hands = dict(state.pools)
    hands[state.actor] = (*state.hand(state.actor), state.offer[index])
    return _change(state, pools=tuple(hands.items()), offer=state.offer[:index] + state.offer[index + 1:],
                   phase="ready", draw_due=False)


def pay_pool(state: PooledMana, actor: str, *, free: bool = False) -> PooledMana:
    if state.phase != "ready" or state.burn_due or actor not in state.heroes:
        raise ValueError("Najpierw dokończ dobór lub operację kart.")
    if not free and not state.hand(actor):
        raise ValueError("Zdolność wymaga naładowania maną.")
    return _change(state, last_paid=() if free else state.hand(actor), burn_due=0 if free else 1)


def finish_burn(state: PooledMana) -> PooledMana:
    """Resolve cost after the committed action, retaining charge through its effect."""
    count = state.burn_due
    state = replace(state, burn_due=0)
    return attack_mana(state, "deck", count) if count else state


def drain(state: PooledMana, reason: str) -> PooledMana:
    return _change(state, phase="drain", pending_count=0, captor="", reason=reason, burn_due=0, resume_draw=False)


def attack_mana(state: PooledMana, source: str, count: int = 1, *, captor: str = "") -> PooledMana:
    if state.phase != "ready" or type(count) is not int or count < 1 or source not in {"deck", "offer"}:
        raise ValueError("Nieprawidłowy atak na manę.")
    cards = state.deck if source == "deck" else state.offer
    if len(cards) < count:
        return drain(state, "Nie można wykonać pełnego uwięzienia/spalenia many.")
    if source == "deck":
        return _change(state, phase="prison" if captor else "burn", pending_count=count, captor=captor)
    removed = state.offer[:count]
    prisons = dict(state.prisons)
    if captor:
        prisons[captor] = (*prisons.get(captor, ()), *removed)
    return _change(state, offer=state.offer[count:], prisons=tuple(prisons.items()),
                   burned=state.burned if captor else (*state.burned, *removed))


def report_removed(state: PooledMana, color: str) -> PooledMana:
    if state.phase not in {"burn", "prison", "expire"} or color not in COLORS or not state.deck:
        raise ValueError("Nie ma karty do zgłoszenia.")
    if state.deck[0] is not None and state.deck[0] != color:
        raise ValueError("Kolor nie zgadza się ze znanym wierzchem talii.")
    prisons = dict(state.prisons)
    if state.captor:
        prisons[state.captor] = (*prisons.get(state.captor, ()), color)
    remaining = state.pending_count - 1
    updated = _change(state, deck=state.deck[1:], prisons=tuple(prisons.items()),
                   burned=state.burned if state.captor or state.phase == "expire" else (*state.burned, color),
                   expired=(*state.expired, color) if state.phase == "expire" else state.expired,
                   pending_count=remaining, phase=state.phase if remaining else "ready", captor=state.captor if remaining else "")
    if not remaining and state.resume_draw:
        if updated.draw_due and not updated.deck and not updated.offer:
            return drain(updated, "Brak karty do obowiązkowego doboru po wygaśnięciu.")
        return replace(updated, resume_draw=False, phase=_fill_phase(updated) if updated.draw_due else "ready")
    return updated


def recover(state: PooledMana, colors: tuple[str, ...], *, top: bool = False) -> PooledMana:
    if state.phase != "ready":
        raise ValueError("Najpierw dokończ operację many.")
    remaining = list(state.burned)
    for color in colors:
        if color not in remaining:
            raise ValueError("Brak tego koloru w spalonych kartach.")
        remaining.remove(color)
    return _change(state, burned=tuple(remaining), deck=(*colors, *state.deck) if top else (*state.deck, *colors))


def release(state: PooledMana, captor: str) -> PooledMana:
    prisons = dict(state.prisons)
    cards = prisons.pop(captor, ())
    return _change(state, prisons=tuple(prisons.items()), deck=(*state.deck, *cards),
                   phase="ready" if state.phase == "release" else state.phase)


def tune(state: PooledMana, colors: tuple[str, ...]) -> PooledMana:
    """Report a legal look at the top cards, in their chosen new order."""
    if state.phase != "ready" or len(colors) != min(2, len(state.deck)) or any(c not in COLORS for c in colors):
        raise ValueError("Zgłoś do dwóch podejrzanych kart w nowej kolejności.")
    known = Counter(c for c in state.deck[:len(colors)] if c is not None)
    if any(Counter(colors)[c] < n for c, n in known.items()):
        raise ValueError("Podgląd musi zachować znane kolory.")
    return _change(state, deck=(*colors, *state.deck[len(colors):]))


def bottom_to_top(state: PooledMana) -> PooledMana:
    # An unknown physical card stays unknown until its normal reveal/burn.
    if state.phase != 'ready' or not state.deck:
        raise ValueError('Przeniesienie wymaga niepustej talii i zakończenia poprzedniej operacji.')
    return _change(state, deck=(state.deck[-1], *state.deck[:-1]))
