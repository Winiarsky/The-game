"""Deterministic push-your-luck transitions. Physical offers stay on the table."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any, Mapping

from .exploration_mana_conditions import ManaCondition
from .exploration_mana_catalog import COLORS, RULES_VERSION, method_by_id, obstacle_description


@dataclass(frozen=True, slots=True)
class ManaAttempt:
    id: str
    target_id: str
    method_id: str
    values: tuple[int, ...]
    obstacle: str = "none"
    phase: str = "offer"
    colors: tuple[str, ...] = ()
    amounts: tuple[int, ...] = ()
    busted: bool = False
    success: bool | None = None
    rolls: tuple[int, ...] = ()
    roll_total: int | None = None
    reroll_used: bool = False
    revision: int = 0
    end_reason: str = ""
    condition: ManaCondition = ManaCondition()
    proposal_status: str = 'unseen'
    sensitive_used: bool = False
    favor_status: str = 'available'

    @property
    def outcome_kind(self) -> str:
        if self.phase != 'result':
            return ''
        return 'compromise' if self.proposal_status == 'accepted' else 'success' if self.success else 'failure'

    @property
    def goal_met(self) -> bool:
        return self.condition.kind == 'color_goal' and self.colors.count(self.condition.color) >= self.condition.count

    def __post_init__(self) -> None:
        method_by_id(self.method_id)
        obstacle_description(self.obstacle)
        if len(self.values) != 5 or any(type(v) is not int or not 1 <= v <= 21 for v in self.values):
            raise ValueError("Profil wymaga pięciu dodatnich wartości do 21.")
        if self.phase not in {"offer", "decision", "bargain", "roll", "reroll_choice", "result"}:
            raise ValueError("Nieprawidłowy etap próby.")
        if len(self.colors) != len(self.amounts) or any(c not in COLORS for c in self.colors):
            raise ValueError("Nieprawidłowa historia kart.")
        if self.proposal_status not in {'unseen', 'offered', 'accepted', 'declined'} or self.favor_status not in {'available', 'armed', 'used'}:
            raise ValueError('Nieprawidłowy stan warunku.')
        if self.phase == 'bargain' and (self.condition.kind != 'compromise' or self.proposal_status != 'offered'):
            raise ValueError('Brak aktywnej propozycji porozumienia.')
        if self.revision < 0 or any(type(v) is not int or v < 1 for v in self.amounts):
            raise ValueError("Nieprawidłowy zapis próby.")

    @property
    def total(self) -> int:
        return sum(self.amounts)

    @property
    def bonus(self) -> int:
        return 0 if self.busted else card_bonus(self.total)

    def to_data(self) -> dict[str, Any]:
        return {"version": RULES_VERSION, **asdict(self)}

    @classmethod
    def from_data(cls, data: Mapping[str, Any]) -> ManaAttempt:
        raw = dict(data)
        version = raw.pop("version", None)
        if type(version) is not int or version not in (1, RULES_VERSION):
            raise ValueError("Nieobsługiwana wersja próby eksploracji.")
        raw['condition'] = ManaCondition(**raw.get('condition', {})) if version == RULES_VERSION else ManaCondition()
        for key in ("values", "colors", "amounts", "rolls"):
            raw[key] = tuple(raw[key])
        return cls(**raw)


def card_bonus(total: int) -> int:
    if total == 20:
        return 6
    if 18 <= total <= 19:
        return 4
    if 15 <= total <= 17:
        return 2
    if 11 <= total <= 14:
        return 1
    return 0


def next_value(attempt: ManaAttempt, color: str) -> int:
    if color not in COLORS:
        raise ValueError("Wybierz jeden z pięciu kolorów many.")
    if attempt.favor_status == 'armed':
        return 1
    previous = attempt.colors[-1] if attempt.colors else None
    extra = 2 if ((attempt.obstacle == "repeat" and previous == color)
                  or (attempt.obstacle == "after_red" and previous == "C")) else 0
    return attempt.values[COLORS.index(color)] + extra


def choose_color(attempt: ManaAttempt, color: str) -> ManaAttempt:
    if attempt.phase != "offer":
        raise ValueError("Najpierw zadeklaruj dobór, zanim odkryjesz karty.")
    value = next_value(attempt, color)
    # Even without the discarded offers we know a sixth selected copy is impossible.
    if attempt.colors.count(color) >= 5:
        raise ValueError("W talii jest tylko pięć kart tego koloru.")
    updated = replace(attempt, colors=(*attempt.colors, color), amounts=(*attempt.amounts, value),
                      revision=attempt.revision + 1, phase="decision",
                      sensitive_used=attempt.sensitive_used or (attempt.condition.kind == 'sensitive_topic' and color == attempt.condition.color),
                      favor_status='used' if attempt.favor_status == 'armed' else attempt.favor_status)
    if updated.total > 21:
        return replace(updated, phase="roll", busted=True, end_reason="bust")
    if updated.total == 21:
        return replace(updated, phase="result", success=True, end_reason="exact")
    if updated.obstacle == "four" and len(updated.colors) == 4:
        return replace(updated, phase="roll", end_reason="limit")
    if (updated.condition.kind == 'compromise' and updated.proposal_status == 'unseen'
            and updated.condition.minimum <= updated.total <= updated.condition.maximum):
        return replace(updated, phase='bargain', proposal_status='offered')
    return updated


def answer_bargain(attempt: ManaAttempt, *, accept: bool) -> ManaAttempt:
    if attempt.phase != 'bargain':
        raise ValueError('Nie ma propozycji oczekującej na odpowiedź.')
    return replace(attempt, phase='result' if accept else 'decision',
                   proposal_status='accepted' if accept else 'declined',
                   end_reason='compromise' if accept else '', revision=attempt.revision + 1)


def set_favor(attempt: ManaAttempt, *, armed: bool) -> ManaAttempt:
    if attempt.phase != 'offer' or attempt.condition.kind != 'favor' or attempt.favor_status == 'used':
        raise ValueError('Ustępstwo nie jest dostępne.')
    status = 'armed' if armed else 'available'
    if status == attempt.favor_status:
        raise ValueError('Ustępstwo już ma ten stan.')
    return replace(attempt, favor_status=status, revision=attempt.revision + 1)


def declare_draw(attempt: ManaAttempt) -> ManaAttempt:
    if attempt.phase != "decision":
        raise ValueError("Nie można teraz zadeklarować kolejnego doboru.")
    return replace(attempt, phase="offer", revision=attempt.revision + 1)


def stand(attempt: ManaAttempt, *, empty_deck: bool = False) -> ManaAttempt:
    if attempt.phase != ("offer" if empty_deck else "decision"):
        raise ValueError("Pas musi nastąpić przed odkryciem następnej oferty.")
    if not attempt.colors:
        raise ValueError("Przygotuj pełną talię i wykonaj pierwszy dobór.")
    return replace(attempt, phase="roll", revision=attempt.revision + 1,
                   end_reason="empty" if empty_deck else "stand")


def request_reroll(attempt: ManaAttempt) -> ManaAttempt:
    if attempt.phase != "reroll_choice" or attempt.reroll_used:
        raise ValueError("Przerzut nie jest dostępny.")
    return replace(attempt, phase="roll", reroll_used=True, revision=attempt.revision + 1)


def accept_failure(attempt: ManaAttempt) -> ManaAttempt:
    if attempt.phase != "reroll_choice":
        raise ValueError("Nie ma porażki oczekującej na decyzję.")
    return replace(attempt, phase="result", revision=attempt.revision + 1)
