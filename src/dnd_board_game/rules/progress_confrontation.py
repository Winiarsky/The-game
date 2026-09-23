"""One-round confrontations: one approach, one check, optional social reputation."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any, Mapping

from .reputation import BOOSTS


@dataclass(frozen=True, slots=True)
class Approach:
    id: str
    name: str
    description: str
    ability: str
    modifier: int
    dc: int = 14
    repeatable: bool = True

    def __post_init__(self) -> None:
        if not self.id or type(self.dc) is not int or self.dc < 1 or type(self.modifier) is not int:
            raise ValueError("Nieprawidłowe podejście konfrontacji.")


@dataclass(frozen=True, slots=True)
class Participant:
    id: str
    name: str
    options: tuple[Approach, ...]


@dataclass(frozen=True, slots=True)
class Confrontation:
    participants: tuple[Participant, ...]
    social: bool
    stage: str = "introduction"
    turn: int = 0
    progress: int = 0
    selected: str = ""
    choices: tuple[tuple[str, str], ...] = ()
    first_test_bonus: int = 0
    first_test_label: str = ""
    check_modifier: int = 0
    original_roll: int | None = None
    extra_roll: int | None = None
    boost: str = ""
    paid: int = 0
    last: str = ""
    last_roll: int | None = None
    last_total: int | None = None
    last_impact: int = 0
    last_critical: str = ""
    natural_one_seen: bool = False
    outcome: str = ""
    tier: str = ""

    def __post_init__(self) -> None:
        if (not self.participants or len({p.id for p in self.participants}) != len(self.participants)
                or not 0 <= self.turn < len(self.participants)
                or not -1 <= self.progress <= self.maximum):
            raise ValueError("Nieprawidłowy stan toru konfrontacji.")
        if self.stage not in {"introduction", "approach", "check", "summary", "extra_check", "after_action", "result"}:
            raise ValueError("Nieznany etap konfrontacji.")
        if self.boost not in {"", *(key for key, _, _ in BOOSTS)} or self.paid not in (0, 5):
            raise ValueError("Nieprawidłowe wsparcie reputacją.")
        for value in (self.original_roll, self.extra_roll, self.last_roll):
            if value is not None and (type(value) is not int or not 1 <= value <= 20):
                raise ValueError("Wynik k20 musi być naturalną liczbą od 1 do 20.")
        if self.paid and (self.boost != "extra_die" or self.original_roll is None):
            raise ValueError("Opłacona druga kość wymaga pierwszego rzutu.")

    @property
    def actor(self) -> Participant:
        return self.participants[self.turn]

    @property
    def maximum(self) -> int:
        return len(self.participants)

    @property
    def approach(self) -> Approach | None:
        return next((option for option in self.actor.options if option.id == self.selected), None)

    def to_data(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_data(cls, data: Mapping[str, Any]) -> Confrontation:
        values = dict(data)
        values["participants"] = tuple(Participant(p["id"], p["name"], tuple(Approach(**a) for a in p["options"])) for p in values["participants"])
        values["choices"] = tuple(tuple(entry) for entry in values.get("choices", ()))
        return cls(**values)


def begin(state: Confrontation) -> Confrontation:
    if state.stage != "introduction":
        raise ValueError("Konfrontacja już się rozpoczęła.")
    return replace(state, stage="approach")


def available_approaches(state: Confrontation) -> tuple[Approach, ...]:
    used = {approach for _, approach in state.choices}
    return tuple(a for a in state.actor.options if a.repeatable or a.id not in used)


def choose(state: Confrontation, approach_id: str) -> Confrontation:
    if state.stage != "approach":
        raise ValueError("Najpierw zakończ poprzednie działanie.")
    option = next((a for a in available_approaches(state) if a.id == approach_id), None)
    if option is None:
        raise ValueError("To podejście nie jest dostępne.")
    return replace(state, selected=option.id, stage="check", check_modifier=option.modifier + state.first_test_bonus,
                   original_roll=None, extra_roll=None, boost="", paid=0, last="", last_critical="")


def roll(state: Confrontation, natural: int) -> Confrontation:
    if type(natural) is not int or not 1 <= natural <= 20:
        raise ValueError("Podaj naturalny wynik k20 od 1 do 20.")
    if state.stage == "check":
        return replace(state, original_roll=natural, stage="summary")
    if state.stage == "extra_check" and state.paid == 5:
        return replace(state, extra_roll=natural, stage="summary")
    raise ValueError("Nie oczekujemy teraz rzutu.")


def available_boosts(state: Confrontation, reputation: int) -> tuple[str, ...]:
    if state.stage != "summary" or not state.social or state.paid or state.original_roll == 20:
        return ()
    return tuple(key for key, cost, _ in BOOSTS if reputation >= cost and (state.original_roll != 1 or key == "extra_die"))


def select_boost(state: Confrontation, key: str, reputation: int) -> Confrontation:
    if key not in available_boosts(state, reputation):
        raise ValueError("Ta opcja reputacji nie jest dostępna.")
    return replace(state, boost="" if state.boost == key else key)


def cancel(state: Confrontation) -> Confrontation:
    if state.stage == "check":
        return replace(state, stage="approach", selected="", check_modifier=0)
    if state.stage == "summary" and not state.paid:
        return replace(state, boost="")
    raise ValueError("Nie można cofnąć opłaconej lub rozstrzygniętej próby.")


def preview(state: Confrontation) -> dict[str, Any]:
    if state.original_roll is None or state.approach is None:
        return {}
    natural = max(state.original_roll, state.extra_roll or state.original_roll)
    bonus = next((bonus for key, _, bonus in BOOSTS if key == state.boost), 0)
    total = natural + state.check_modifier + bonus
    critical = "failure" if natural == 1 else "success" if natural == 20 else ""
    delta = -1 if natural == 1 else 2 if natural == 20 else int(total >= state.approach.dc)
    return dict(natural=natural, total=total, bonus=bonus, delta=delta, critical=critical,
                progress=max(-1, min(state.maximum, state.progress + delta)))


def tier(progress: int, party_size: int) -> str:
    if progress < 0: return "worsened"
    if progress == 0: return "unchanged"
    if progress >= party_size: return "full"
    if party_size > 3 and progress >= party_size - 1: return "bonus"
    if progress >= (party_size + 1) // 2: return "success"
    return "complication"


def _complete_action(state: Confrontation, delta: int) -> Confrontation:
    raw = state.progress + delta
    progress = max(-1, min(state.maximum, raw))
    finished = raw < -1 or raw >= state.maximum or state.turn == state.maximum - 1
    result_tier = tier(progress, state.maximum) if finished else ""
    outcome = ("success" if result_tier in {"success", "bonus", "full"} else "compromise" if result_tier == "complication" else "failure") if finished else ""
    return replace(state, progress=progress, stage="result" if finished else "after_action",
                   tier=result_tier, outcome=outcome, choices=(*state.choices, (state.actor.id, state.selected)))


def confirm(state: Confrontation, reputation: int) -> tuple[Confrontation, int]:
    """Return a new state and exact payment; the adapter persists both atomically."""
    if state.stage != "summary" or state.original_roll is None:
        raise ValueError("Najpierw wykonaj rzut.")
    if state.boost and not state.paid and state.boost not in available_boosts(state, reputation):
        raise ValueError("Brak reputacji na wybrane wsparcie.")
    cost = 0 if state.paid else next((cost for key, cost, _ in BOOSTS if key == state.boost), 0)
    if state.boost == "extra_die" and not state.paid:
        return replace(state, stage="extra_check", paid=cost), cost
    if state.paid and state.extra_roll is None:
        raise ValueError("Najpierw podaj wynik opłaconej drugiej kości.")
    result = preview(state)
    label = "Krytyczna porażka" if result["critical"] == "failure" else "Krytyczny sukces" if result["critical"] == "success" else "Sukces" if result["delta"] else "Porażka"
    resolved = replace(state, first_test_bonus=0, last_roll=result["natural"], last_total=result["total"],
                       last_impact=result["delta"], last_critical=result["critical"],
                       natural_one_seen=state.natural_one_seen or result["natural"] == 1,
                       last=f'{state.actor.name}: {label.lower()} ({result["total"]}, ST {state.approach.dc}). Tor {state.progress} → {result["progress"]}.')
    return _complete_action(resolved, result["delta"]), cost


def pass_turn(state: Confrontation) -> Confrontation:
    if state.stage != "approach":
        raise ValueError("Nie można pasować podczas rozpoczętej próby.")
    return _complete_action(replace(state, selected="", last=f"{state.actor.name} pasuje."), 0)


def advance(state: Confrontation) -> Confrontation:
    if state.stage != "after_action":
        raise ValueError("Najpierw rozstrzygnij działanie.")
    return replace(state, turn=state.turn + 1, stage="approach", selected="", boost="", paid=0,
                   original_roll=None, extra_roll=None, check_modifier=0, last="", last_roll=None,
                   last_total=None, last_impact=0, last_critical="")
