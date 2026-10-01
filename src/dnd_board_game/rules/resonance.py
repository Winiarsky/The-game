"""Serializable rules state for the accepted charge/continuous-resonance profile.

No UI, clock, random generator, filesystem or hardware belongs in this module.
The ordered entries, not a cached collection of bonuses, are authoritative.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


PROFILE = "rune_charges_v02"
MAX_CHARGES = 20
Task = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ChargeCard:
    id: str
    name: str
    rune: str
    base_cost: int
    enhanced_cost: int
    budget: str
    target: str
    requirements: str
    effect: str


@dataclass(frozen=True, slots=True)
class ChargeWeapon:
    id: str
    name: str
    ability: str
    kind: str
    range: int
    components: tuple[dict[str, Any], ...]
    attack_bonus: int = 0
    source_type: str = "weapon"
    ammunition_type: str = ""
    ammunition_cost: int = 0
    on_hit_condition: str = ""
    save_ability: str = ""
    save_dc: int = 0
    minimum_movement: int = 0
    requires_adjacent_ally: bool = False
    spell_save_ability: str = ""
    spell_save_dc: int = 0
    spell_save_half: bool = False
    proficiency_id: str = ""


@dataclass(frozen=True, slots=True)
class ResonanceEntry:
    rune: str
    contributor: str
    effective: str | None


@dataclass(slots=True)
class ResonanceChain:
    id: int
    entries: list[ResonanceEntry] = field(default_factory=list)
    members: list[str] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self.entries:
            if entry.effective:
                counts[entry.effective] = counts.get(entry.effective, 0) + 1
        return counts


@dataclass(slots=True)
class ChargeActorState:
    charges: int = MAX_CHARGES
    turn: int = 0
    ordinary: bool = True
    special: bool = True
    reaction: bool = True
    base_spent: int = 0
    temporary_movement: int = 0
    turn_base: int = 0
    move_locked: bool = False
    moved: bool = False
    offensive: bool = False
    continued: bool = False
    shot: bool = False
    sneak_used: bool = False
    start_adjacent: list[str] = field(default_factory=list)
    hidden: list[str] = field(default_factory=list)
    hide_total: int = 0
    statuses: list[Task] = field(default_factory=list)
    cup: int = 0
    shield: int = 0
    regeneration_round: int = 0
    regeneration_reason: str = ""
    last_power: str = ""
    power_streak: int = 0
    last_rune: str = ""
    mark: str = ""


@dataclass(slots=True)
class ChargeState:
    """Only profile-specific state; HP, equipment and coordinates remain on Actor."""

    version: int = 1
    revision: int = 0
    serial: int = 0
    order: list[str] = field(default_factory=list)
    index: int = 0
    round: int = 1
    fighters: dict[str, ChargeActorState] = field(default_factory=dict)
    chain: ResonanceChain | None = None
    phase: str = "idle"
    preview: Task | None = None
    action: Task | None = None
    queue: list[Task] = field(default_factory=list)
    task: Task | None = None
    history: list[str] = field(default_factory=list)
    die_value: int = 1
    inspected: str = ""
    info_page: int = 0
    notice: str = ""

    def as_payload(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_payload(cls, raw: Mapping[str, Any], actor_ids: set[str]) -> ChargeState:
        data = deepcopy(dict(raw))
        if data.get("version") != 1:
            raise ValueError("Nieznana wersja zapisu walki ładunków.")
        for key in ("revision", "serial", "info_page"):
            if type(data.get(key, 0)) is not int or (key != "info_page" and data.get(key, 0) < 0):
                raise ValueError("Nieprawidłowa wersja decyzji w zapisie.")
        order = data.get("order")
        if not isinstance(order, list) or not order or len(order) != len(set(order)) or set(order) - actor_ids:
            raise ValueError("Nieprawidłowa kolejność walki ładunków.")
        if type(data.get("index")) is not int or not 0 <= data["index"] < len(order):
            raise ValueError("Nieprawidłowy indeks tury.")
        if type(data.get("round")) is not int or data["round"] < 1:
            raise ValueError("Nieprawidłowy numer rundy.")
        fighters = data.get("fighters", {})
        if not isinstance(fighters, dict) or set(fighters) != actor_ids:
            raise ValueError("Zapis ładunków nie odpowiada uczestnikom walki.")
        data["fighters"] = {key: ChargeActorState(**value) for key, value in fighters.items()}
        for fighter in data["fighters"].values():
            if any(type(getattr(fighter, key)) is not int or getattr(fighter, key) < 0 for key in ("charges", "turn", "cup", "shield", "base_spent", "temporary_movement", "regeneration_round")) or not 0 <= fighter.charges <= MAX_CHARGES:
                raise ValueError("Nieprawidłowa pula zasobów w zapisie.")
            if set(fighter.hidden) - actor_ids or set(fighter.start_adjacent) - actor_ids or (fighter.mark and fighter.mark not in actor_ids):
                raise ValueError("Stan bohatera wskazuje nieznany cel.")
        if data.get("chain"):
            chain = data["chain"]
            if set(chain.get("members", ())) - actor_ids or len(chain["members"]) != len(set(chain["members"])):
                raise ValueError("Nieprawidłowi uczestnicy Rezonansu.")
            entries = [ResonanceEntry(**entry) for entry in chain["entries"]]
            previous = None
            for entry in entries:
                if entry.rune not in {"Wieża", "Grot", "Schody", "Błysk", "Hak", "Oko", "Kielich", "Węzeł", "Fala", "Klepsydra"} or entry.contributor not in actor_ids or entry.effective != (previous if entry.rune == "Fala" else entry.rune):
                    raise ValueError("Nieprawidłowa kolejność run Rezonansu.")
                previous = entry.effective
            data["chain"] = ResonanceChain(chain["id"], entries, chain["members"])
        if data.get("phase") not in {"idle", "preview", "task", "result", "end-preview", "finished"}:
            raise ValueError("Nieprawidłowy etap walki ładunków.")
        def validate_task(value: Any) -> None:
            if isinstance(value, list):
                for item in value:
                    validate_task(item)
            elif isinstance(value, dict):
                for key in ("actor", "target", "source"):
                    if value.get(key) and value[key] not in actor_ids:
                        raise ValueError("Kolejka walki wskazuje nieznaną postać.")
                if value.get("targets") and set(value["targets"]) - actor_ids:
                    raise ValueError("Kolejka walki zawiera nieznane cele.")
                if value.get("type") == "roll":
                    parts = value.get("parts", ())
                    if not parts or any(type(p.get("count")) is not int or p["count"] < 1 or p.get("sides") not in {4, 6, 8, 10, 12, 20, 100} for p in parts):
                        raise ValueError("Nieprawidłowe kości w zapisie.")
                    sides = [p["sides"] for p in parts for _ in range(p["count"])]
                    results = value.get("dice_results", [])
                    if len(results) > len(sides) or any(type(n) is not int or not 1 <= n <= sides[i] for i, n in enumerate(results)):
                        raise ValueError("Nieprawidłowy zaakceptowany wynik kości.")
                for child in value.values():
                    if isinstance(child, (list, dict)):
                        validate_task(child)
        for key in ("task", "queue", "action", "preview"):
            validate_task(data.get(key))
        return cls(**data)


def cards_for(catalog: Mapping[str, Any], actor_id: str) -> tuple[ChargeCard, ...]:
    cards = []
    for row in catalog["heroes"].get(actor_id, {}).get("cards", ()):
        effect = row["effect"]
        for source, ability in (("Siły", "Siła"), ("Mądrości", "Mądrość"), ("Charyzmy", "Charyzma"), ("Inteligencji", "Inteligencja")):
            effect = effect.replace(f"ST {source}", f"ST {catalog['rules']['save_dc_base']} + {ability}")
        cards.append(ChargeCard(**dict(row, effect=effect)))
    return tuple(cards)


def roll_result(task: Mapping[str, Any], values: list[int]) -> tuple[int | None, int, bool]:
    check = task["outcome"] in {"attack", "hide", "bash", "contest", "save", "death_save"}
    natural = None
    if check and task["parts"] and task["parts"][0]["sides"] == 20:
        natural = max(values) if task.get("mode") == "advantage" else min(values) if task.get("mode") == "disadvantage" else values[0]
    total = (natural if natural is not None else sum(values)) + task.get("modifier", 0)
    if task["outcome"] in {"damage", "enemy_spell"}:
        total = sum(part["value"] for part in damage_components(task, values))
    success = (natural == 20 or (natural != 1 and total >= task["dc"])) if task["outcome"] == "attack" else total >= task.get("dc", 0)
    return natural, total, success


def damage_components(task: Mapping[str, Any], values: list[int]) -> list[dict[str, Any]]:
    grouped: dict[str, int] = {}
    index = 0
    for part in task["components"]:
        value = part.get("value", 0)
        if part.get("count"):
            value = values[index] + part.get("modifier", 0)
            index += 1
        grouped[part["damage_type"]] = grouped.get(part["damage_type"], 0) + value
    return [{"damage_type": kind, "value": max(0, value // task.get("divisor", 1))} for kind, value in grouped.items()]


def bonus_summary(counts: Mapping[str, int]) -> list[dict[str, str | int]]:
    descriptions = {
        "Wieża": lambda n: f"+{n} KP",
        "Grot": lambda n: f"+{n}k4 obrażeń na cel",
        "Schody": lambda n: f"+{2*n} ruchu na początku tury",
        "Błysk": lambda n: f"{n}k4 leczenia na początku tury",
        "Hak": lambda n: f"Przeniesienie po obrażeniach do {n} pól",
        "Oko": lambda n: f"+{n} do k20 (nie do ST)",
        "Kielich": lambda n: f"Limit {2*n} tymczasowych PW",
        "Klepsydra": lambda n: f"Limit {2*n} osłony (bez psychicznych)",
        "Węzeł": lambda n: f"Wrogowie: −{n} ruchu",
    }
    return [{"rune": rune, "count": n, "text": descriptions[rune](n)} for rune, n in counts.items() if rune in descriptions]
