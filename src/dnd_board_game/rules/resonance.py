"""Serializable rules state for directed rune relations and legacy charge saves.

No UI, clock, random generator, filesystem or hardware belongs in this module.
The ordered entries, not a cached collection of bonuses, are authoritative.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from dnd_board_game.rules.rune_modifiers import validate_modifiers


PROFILE = "rune_relations_v03"
LEGACY_PROFILE = "rune_charges_v02"
MEMORY_LIMIT = 3
STARTER_RUNES = ("Wieża", "Grot", "Schody", "Błysk", "Hak", "Oko", "Kielich", "Węzeł", "Klepsydra", "Fala")
MAX_CHARGES = 20
Task = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ChargeCard:
    id: str
    name: str
    rune: str
    base_cost: int = 0
    enhanced_cost: int = 0
    budget: str = "S"
    target: str = ""
    requirements: str = ""
    effect: str = ""
    cost: int = 0
    resonance_bonuses: tuple[Task, ...] = ()
    requires_resonance: tuple[str, ...] = ()
    ends_resonance: bool = False
    base_modifiers: Task = field(default_factory=dict)


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
    attack_modifiers: tuple[Task, ...] = ()


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

    version: int = 2
    profile: str = PROFILE
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

    def validate_catalog(self, catalog: Mapping[str, Any]) -> None:
        """Check persisted paid decisions against their authoritative catalog."""
        expected_profile = PROFILE if self.version == 2 else LEGACY_PROFILE
        if catalog.get("profile") != expected_profile or self.profile != expected_profile:
            raise ValueError("Katalog mocy nie odpowiada wersji zapisanej walki.")
        if self.version == 1:
            return
        actor_ids = set(self.fighters)
        if self.chain:
            validate_memory([asdict(entry) for entry in self.chain.entries], actor_ids, catalog["rules"]["rune_relations"])
        preview = self.preview
        if preview:
            action_id = preview.get("id")
            cards = cards_for(catalog, self.order[self.index])
            if preview.get("mode") != "auto" or action_id not in {"attack", "move", "focus", "item", *(card.id for card in cards)}:
                raise ValueError("Nieprawidłowy podgląd mocy runicznej.")
        action = self.action
        if not action:
            return
        if action.get("actor") != self.order[self.index]:
            raise ValueError("Akcja nie należy do aktywnej tury.")
        card = next((card for card in cards_for(catalog, action["actor"]) if card.id == action.get("id")), None)
        if type(action.get("card")) is not bool or action["card"] != (card is not None):
            raise ValueError("Oznaczenie opłaconej mocy nie odpowiada jej karcie.")
        if not action["card"] and action.get("modifiers", {}) != {}:
            raise ValueError("Akcja poza kartami nie może otrzymać premii mocy.")
        if action["card"]:
            if action.get("mode") != "auto":
                raise ValueError("Nieprawidłowa opłacona moc.")
            remembered = action.get("resonance", {}).get("memory_before")
            if not isinstance(remembered, list):
                raise ValueError("Brak pamięci sprzed opłaconej mocy.")
            validate_memory(remembered, actor_ids, catalog["rules"]["rune_relations"])
            expected = relation_preview(card, remembered, action["actor"], catalog["rules"]["rune_relations"], catalog["rules"]["starter_runes"])
            if action.get("resonance") != expected or expected["blocked_reasons"]:
                raise ValueError("Nieprawidłowe warunki opłaconej mocy.")
            validate_modifiers(action.get("modifiers"))
            if action.get("modifiers") != relation_modifiers(card, expected):
                raise ValueError("Premie opłaconej mocy różnią się od jej karty.")
            if type(action.get("paid_cost")) is not int or action["paid_cost"]-card.cost not in {0, 2, 4}:
                raise ValueError("Nieprawidłowy koszt opłaconej mocy.")
            live = [asdict(entry) for entry in self.chain.entries] if self.chain else []
            expected_live = expected["memory_after"] if action.get("resonance_applied") else expected["eligible_memory"]
            if live != expected_live:
                raise ValueError("Pamięć Rezonansu nie odpowiada etapowi rozstrzygania mocy.")

    def as_payload(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_payload(cls, raw: Mapping[str, Any], actor_ids: set[str]) -> ChargeState:
        data = deepcopy(dict(raw))
        version = data.get("version")
        if type(version) is not int or version not in {1, 2}:
            raise ValueError("Nieznana wersja zapisu walki ładunków.")
        expected_profile = LEGACY_PROFILE if version == 1 else PROFILE
        if data.get("profile", expected_profile if version == 1 else None) != expected_profile:
            raise ValueError("Profil zapisu nie odpowiada wersji mechaniki run.")
        data["profile"] = expected_profile
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
            if version == 2 and any(type(getattr(fighter, key)) is not bool for key in
                    ("ordinary", "special", "reaction", "move_locked", "moved", "offensive", "continued", "shot", "sneak_used")):
                raise ValueError("Nieprawidłowy stan budżetów tury.")
            if any(type(getattr(fighter, key)) is not int or getattr(fighter, key) < 0 for key in ("charges", "turn", "cup", "shield", "base_spent", "temporary_movement", "regeneration_round", "turn_base", "power_streak")) or not 0 <= fighter.charges <= MAX_CHARGES:
                raise ValueError("Nieprawidłowa pula zasobów w zapisie.")
            if set(fighter.hidden) - actor_ids or set(fighter.start_adjacent) - actor_ids or (fighter.mark and fighter.mark not in actor_ids):
                raise ValueError("Stan bohatera wskazuje nieznany cel.")
        if data.get("chain"):
            chain = data["chain"]
            if set(chain.get("members", ())) - actor_ids or len(chain["members"]) != len(set(chain["members"])):
                raise ValueError("Nieprawidłowi uczestnicy Rezonansu.")
            entries = [ResonanceEntry(**entry) for entry in chain["entries"]]
            if not entries or type(chain.get("id")) is not int or chain["id"] < 1:
                raise ValueError("Nieprawidłowa pamięć Rezonansu.")
            if version == 2 and len(entries) > MEMORY_LIMIT:
                raise ValueError("Pamięć Rezonansu obejmuje najwyżej trzy wpisy.")
            previous = None
            for entry in entries:
                if entry.rune not in STARTER_RUNES or entry.contributor not in actor_ids:
                    raise ValueError("Nieprawidłowy wpis Rezonansu.")
                expected = (previous if entry.rune == "Fala" else entry.rune) if version == 1 else entry.rune
                if entry.effective != expected:
                    raise ValueError("Nieprawidłowy symbol Rezonansu.")
                if version == 2:
                    if entry.rune == "Fala" and entry.contributor != "nimra":
                        raise ValueError("Fala należy wyłącznie do Nimry.")
                previous = entry.effective
            data["chain"] = ResonanceChain(chain["id"], entries, chain["members"])
        if data.get("phase") not in {"idle", "preview", "task", "result", "end-preview", "finished"}:
            raise ValueError("Nieprawidłowy etap walki ładunków.")
        if version == 2:
            if data["phase"] == "preview" and (not isinstance(data.get("preview"), dict) or data.get("action") or data.get("task")):
                raise ValueError("Podgląd nie odpowiada etapowi zapisu.")
            if data["phase"] == "task" and not isinstance(data.get("task"), dict):
                raise ValueError("Brak oczekującej decyzji graczy.")
            if data["phase"] in {"idle", "end-preview", "finished"} and (data.get("task") or data.get("queue") or data.get("action")):
                raise ValueError("Etap walki zawiera nieoczekujące rozstrzygnięcie.")
            if data["phase"] == "result" and (not data.get("action") or data.get("task") or data.get("queue")):
                raise ValueError("Wynik nie odpowiada zakończonej akcji.")
            known_queue = {"roll", "attack", "damage", "status", "move_step", "escape", "save", "finish", "close_action",
                           "passage_end", "opportunity", "relocate", "recover", "bonus_target", "correction", "enemy-move"}
            known_pending = {"roll", "hymn", "opportunity", "relocate", "recover", "bonus_target", "correction", "enemy-move", "enemy-result"}
            if any(not isinstance(task, dict) or task.get("type") not in known_queue for task in data.get("queue", [])):
                raise ValueError("Nieznany etap kolejki mocy.")
            if data.get("task") and data["task"].get("type") not in known_pending:
                raise ValueError("Nieznana decyzja graczy.")
        def validate_coordinate(value: Any) -> None:
            if not isinstance(value, (list, tuple)) or len(value) != 2 or any(type(component) is not int for component in value):
                raise ValueError("Nieprawidłowa para współrzędnych w zapisie walki.")

        def validate_task(value: Any) -> None:
            if isinstance(value, list):
                for item in value:
                    validate_task(item)
            elif isinstance(value, dict):
                if version == 2:
                    for key in ("destination", "position", "origin", "center"):
                        if value.get(key) is not None:
                            validate_coordinate(value[key])
                    if value.get("path") is not None:
                        path = value["path"]
                        if (not isinstance(path, dict) or not isinstance(path.get("cells"), list)
                                or not isinstance(path.get("costs"), list) or len(path["cells"]) != len(path["costs"])
                                or any(type(cost) is not int or cost < 0 for cost in path["costs"])):
                            raise ValueError("Nieprawidłowy zapis drogi ruchu.")
                        for cell in path["cells"]:
                            validate_coordinate(cell)
                for key in ("actor", "target", "source", "until_start", "until_end"):
                    if value.get(key) and value[key] not in actor_ids:
                        raise ValueError("Kolejka walki wskazuje nieznaną postać.")
                if value.get("targets") and set(value["targets"]) - actor_ids:
                    raise ValueError("Kolejka walki zawiera nieznane cele.")
                if value.get("type") == "roll":
                    if value.get("outcome") not in {"attack", "hide", "bash", "contest", "save", "death_save", "damage", "area_damage",
                            "enemy_spell", "heal", "heal_group", "charges", "regenerate", "hymn"}:
                        raise ValueError("Nieznany wynik rzutu w zapisie.")
                    parts = value.get("parts", ())
                    if not parts or len(parts) > 100 or any(type(p.get("count")) is not int or not 1 <= p["count"] <= 100
                            or type(p.get("sides")) is not int or p.get("sides") not in {4, 6, 8, 10, 12, 20, 100} for p in parts):
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
        if version == 2:
            for fighter in data["fighters"].values():
                validate_task(fighter.statuses)
        return cls(**data)


def cards_for(catalog: Mapping[str, Any], actor_id: str) -> tuple[ChargeCard, ...]:
    cards = []
    for row in catalog["heroes"].get(actor_id, {}).get("cards", ()):
        effect = row["effect"]
        for source, ability in (("Siły", "Siła"), ("Mądrości", "Mądrość"), ("Charyzmy", "Charyzma"), ("Inteligencji", "Inteligencja")):
            effect = effect.replace(f"ST {source}", f"ST {catalog['rules']['save_dc_base']} + {ability}")
        card_data = dict(row, effect=effect)
        for key in ("resonance_bonuses", "requires_resonance"):
            if key in card_data:
                card_data[key] = tuple(card_data[key])
        cards.append(ChargeCard(**card_data))
    return tuple(cards)


def legal_next_runes(rune: str | None, relations: Mapping[str, Any],
                     starter_runes: tuple[str, ...] | list[str] = STARTER_RUNES) -> list[str]:
    if not rune or rune == "Fala":
        return list(starter_runes)
    return list(relations.get(rune, ()))


def validate_memory(entries: list[Task], actor_ids: set[str], relations: Mapping[str, Any] | None = None) -> None:
    if len(entries) > MEMORY_LIMIT:
        raise ValueError("Pamięć Rezonansu obejmuje najwyżej trzy wpisy.")
    previous = None
    for entry in entries:
        rune = entry.get("rune")
        if rune not in STARTER_RUNES or entry.get("contributor") not in actor_ids or entry.get("effective") != rune:
            raise ValueError("Nieprawidłowy wpis pamięci Rezonansu.")
        if rune == "Fala" and entry["contributor"] != "nimra":
            raise ValueError("Fala należy wyłącznie do Nimry.")
        if relations is not None and previous and rune not in legal_next_runes(previous, relations):
            raise ValueError("Niezgodne połączenie w pamięci Rezonansu.")
        previous = rune


def relation_preview(card: ChargeCard | None, entries: list[Task], contributor: str, relations: Mapping[str, Any],
                     starter_runes: tuple[str, ...] | list[str] = STARTER_RUNES) -> Task:
    before = deepcopy(entries)
    last = before[-1]["rune"] if before else None
    result = dict(transition="start", memory_before=before, eligible_memory=[], memory_after=before,
                  allowed_next=legal_next_runes(last, relations, starter_runes), active_bonuses=[], missing_bonuses=[],
                  missing_required_runes=[], continuity_allowed=True, blocked_reasons=[])
    if card is None:
        return result
    legal = not last or card.rune in legal_next_runes(last, relations, starter_runes)
    eligible = before if legal else []
    symbols = {entry["rune"] for entry in eligible}
    active, missing = [], []
    for bonus in card.resonance_bonuses:
        absent = [rune for rune in bonus["requires"] if rune not in symbols]
        (missing if absent else active).append(dict(deepcopy(bonus), **({"missing": absent} if absent else {})))
    absent_required = [rune for rune in card.requires_resonance if rune not in {entry["rune"] for entry in before}]
    blocked = []
    if absent_required:
        blocked.append("Wymaga Rezonansu: " + " + ".join(absent_required))
    if (card.requires_resonance or card.ends_resonance) and (not last or not legal):
        blocked.append("Wymaga legalnej kontynuacji Rezonansu")
    result.update(transition="finisher" if card.ends_resonance else "start" if not last else "continue" if legal else "reset",
                  eligible_memory=eligible, memory_after=[] if card.ends_resonance else
                  [*eligible, dict(rune=card.rune, effective=card.rune, contributor=contributor)][-MEMORY_LIMIT:],
                  active_bonuses=active, missing_bonuses=missing, missing_required_runes=absent_required,
                  continuity_allowed=legal, blocked_reasons=blocked)
    return result


def relation_modifiers(card: ChargeCard | None, preview: Task) -> Task:
    modifiers = deepcopy(card.base_modifiers) if card else {}
    for bonus in preview["active_bonuses"]:
        for name, value in bonus.get("modifiers", {}).items():
            if isinstance(value, list):
                modifiers[name] = [*modifiers.get(name, []), *deepcopy(value)]
            elif isinstance(value, bool):
                modifiers[name] = bool(modifiers.get(name, False) or value)
            elif name == "hymn_sides":
                modifiers[name] = max(modifiers.get(name, 0), value)
            else:
                modifiers[name] = modifiers.get(name, 0) + value
    return modifiers


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
