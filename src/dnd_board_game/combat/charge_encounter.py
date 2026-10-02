"""Deterministic combat for directed rune relations and compatible legacy saves.

An encounter works on a private copy of profile state and immutable Actor
records. The application commits ``combat_state()`` only after a valid command.
Dice are supplied by the caller; reading projections never advances the queue.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace
from typing import Any, Callable, Mapping

from dnd_board_game.actors import Actor, ActorId, Faction, FeatureGrant, FeatureSourceKind, DeathSaveState, passive_skill_score
from dnd_board_game.core.player_labels_pl import ABILITY_LABELS_PL
from dnd_board_game.inventory.magic_items import effective_ability_modifier
from dnd_board_game.inventory.ammunition import consume_ammunition, has_ammunition
from dnd_board_game.inventory.armor import effective_armor_class, effective_speed_feet
from dnd_board_game.actors.exhaustion import effective_max_hit_points
from dnd_board_game.rules.resonance import (
    ChargeActorState, ChargeCard, ChargeState, ChargeWeapon, ResonanceChain,
    ResonanceEntry, Task, cards_for, damage_components, roll_result,
    MEMORY_LIMIT, STARTER_RUNES,
    legal_next_runes, relation_preview, relation_modifiers,
)
from dnd_board_game.world import BoardState, Coordinate, line_of_sight_clear
from dnd_board_game.world.charge_movement import ChargePath, charge_paths, distance, free, playable
from dnd_board_game.world.movement import neighbors
from .session import CombatState, CombatStatus, EnemyOutcome, record_ammunition_expenditure, finalize_ammunition_recovery
from .action_economy import ActionUse
from .attack_positioning import AttackPositioning, evaluate_cover_from_origin, with_defensive_spot_cover
from .scene import SceneObject


def point(value: list[int] | tuple[int, int] | Coordinate) -> Coordinate:
    if isinstance(value, Coordinate):
        return value
    if not isinstance(value, (list, tuple)) or len(value) != 2 or any(type(n) is not int for n in value):
        raise ValueError("Nieprawidłowe pole planszy.")
    return Coordinate(*value)


def hymn_source(actor: Actor) -> str:
    return next((f.source_ref for f in actor.features if f.feature_id == "resonance_hymn"), "")


def hymn_sides(actor: Actor) -> int:
    """The indefinite grant survives combat boundaries without profile state."""
    grant = next((f for f in actor.features if f.feature_id == "resonance_hymn"), None)
    return 8 if grant and "1k8" in grant.label else 6


class ChargeEncounter:
    def __init__(self, combat: CombatState, board: BoardState, catalog: Mapping[str, Any], weapons: Mapping[str, ChargeWeapon], *, cover_bonuses: Mapping[Coordinate, int] | None = None, items: tuple[Task, ...] = (), scene_objects: tuple[SceneObject, ...] = ()) -> None:
        if combat.resonance is None:
            raise ValueError("Walka nie korzysta z profilu ładunków.")
        combat.resonance.validate_catalog(catalog)
        self.original = combat
        self.s = deepcopy(combat.resonance)
        self.actors = {str(a.id): a for a in combat.actors}
        self.board = board
        self.catalog = catalog
        self.weapons = weapons
        self.cover_bonuses = cover_bonuses or {}
        self.scene_objects = scene_objects
        self.items = items or tuple(dict(id=i.id, owner=str(a.id), name=i.name, count=2, sides=4, modifier=2)
                                   for a in combat.actors for i in self.potions(a) if a.faction == Faction.ALLY)

    @property
    def is_relations(self) -> bool:
        return self.s.version == 2

    @property
    def active(self) -> Actor:
        return self.actor(self.s.order[self.s.index])

    def actor(self, actor_id: str) -> Actor:
        return self.actors[actor_id]

    def fighter(self, actor_id: str | None = None) -> ChargeActorState:
        return self.s.fighters[actor_id or str(self.active.id)]

    def update_actor(self, actor: Actor) -> None:
        self.actors[str(actor.id)] = actor

    def allies(self, actor: Actor | None = None) -> list[Actor]:
        a = actor or self.active
        return [b for b in self.actors.values() if b.faction == a.faction]

    def enemies(self, actor: Actor | None = None) -> list[Actor]:
        a = actor or self.active
        return [b for b in self.actors.values() if b.faction not in {a.faction, Faction.NEUTRAL} and b.hp > 0 and str(b.id) not in self.original.enemy_ai.escaped_actor_ids]

    def note(self, text: str) -> None:
        self.s.history.insert(0, text)
        if self.s.action is not None:
            self.s.action.setdefault("results", []).append(text)

    def member(self, actor_id: str) -> bool:
        return bool(self.s.chain and actor_id in self.s.chain.members)

    def counts(self) -> dict[str, int]:
        if self.is_relations:
            return {entry.rune: 1 for entry in self.s.chain.entries} if self.s.chain else {}
        return self.s.chain.counts() if self.s.chain else {}

    def bonus(self, actor_id: str, rune: str) -> int:
        return self.counts().get(rune, 0) if not self.is_relations and self.member(actor_id) else 0

    def next_runes(self, rune: str | None = None) -> list[str]:
        rune = rune or (self.s.chain.entries[-1].rune if self.s.chain and self.s.chain.entries else None)
        return legal_next_runes(rune, self.catalog["rules"].get("rune_relations", {}), self.catalog["rules"].get("starter_runes", STARTER_RUNES))

    def resonance_preview(self, card_or_id: ChargeCard | str | None = None, targets: list[str] | None = None) -> Task:
        card = self.card(card_or_id) if isinstance(card_or_id, str) else card_or_id
        entries = [asdict(entry) for entry in self.s.chain.entries] if self.s.chain else []
        return relation_preview(card if self.is_relations else None, entries, str(self.active.id),
                                self.catalog["rules"].get("rune_relations", {}), self.catalog["rules"]["starter_runes"])

    def effect_modifiers(self, card_or_id: ChargeCard | str | None = None) -> Task:
        card_or_id = card_or_id or (self.s.preview or {}).get("id")
        card = self.card(card_or_id) if isinstance(card_or_id, str) else card_or_id
        return relation_modifiers(card, self.resonance_preview(card)) if self.is_relations else {}

    def action_modifiers(self, actor_id: str, power: str) -> Task:
        action = self.s.action or {}
        return action.get("modifiers", {}) if action.get("actor") == actor_id and action.get("id") == power else {}

    def turn_duration(self, source: str) -> Task:
        return dict(source=source, until_start=source, turn=self.fighter(source).turn+1)

    def grant_pool(self, target: str, kind: str, value: int, source: str) -> None:
        field = "cup" if kind == "temporary" else "shield"
        f = self.fighter(target)
        if kind == "temporary" and self.actor(target).temp_hp >= value:
            return
        if value < getattr(f, field):
            return
        if kind == "temporary" and self.actor(target).temp_hp:
            self.update_actor(replace(self.actor(target), temp_hp=0))
        setattr(f, field, value)
        self.add_status(target, kind, value=value, **self.turn_duration(source))
        self.note(f"{self.actor(target).name}: {value} {'tymczasowych PW' if kind == 'temporary' else 'pkt osłony'} do następnej tury {self.actor(source).name}.")

    def grant_ac(self, target: str, value: int, source: str, power: str) -> None:
        self.add_status(target, f"ward:{power}", value=value, **self.turn_duration(source))

    def hymn_sides(self, actor_id: str) -> int:
        return (self.status(actor_id, "hymn") or {}).get("sides", hymn_sides(self.actor(actor_id)))

    def ability(self, actor_id: str, ability: str) -> int:
        return effective_ability_modifier(self.actor(actor_id), ability)

    def status(self, actor_id: str, kind: str) -> Task | None:
        return next((s for s in self.fighter(actor_id).statuses if s["type"] == kind), None)

    def add_status(self, actor_id: str, kind: str, **extra: Any) -> None:
        f = self.fighter(actor_id)
        f.statuses = [s for s in f.statuses if s["type"] != kind]
        f.statuses.append(dict(type=kind, **extra))

    def shielded(self, actor_id: str) -> bool:
        a, g = self.actor(actor_id), self.actors.get("garran")
        return bool(a.faction == Faction.ALLY and actor_id != "garran" and a.hp > 0 and g and g.hp > 0
                    and any(i.kind == "shield" and i.equipped for i in g.inventory) and distance(a.position, g.position) == 1)

    def cover(self, actor_id: str, origin: Coordinate | None = None) -> AttackPositioning:
        """Current protection on the tile, optionally including the attack line."""
        actor = self.actor(actor_id)
        cover = (evaluate_cover_from_origin(self.board, origin, actor, self.board_actors(), self.scene_objects)
                 if origin is not None else AttackPositioning())
        return with_defensive_spot_cover(cover, actor, self.scene_objects)

    def ac(self, actor_id: str, origin: Coordinate | None = None) -> int:
        return (effective_armor_class(self.actor(actor_id)) + self.bonus(actor_id, "Wieża") + int(self.shielded(actor_id))
                + (self.status(actor_id, "arcane") or {}).get("value", 2 if self.status(actor_id, "arcane") else 0)
                + sum(s.get("value", 0) for s in self.fighter(actor_id).statuses if s["type"].startswith("ward:"))
                + self.cover(actor_id, origin).cover_bonus
                - (2 if self.status(actor_id, "broken") else 0))

    def movement(self, actor_id: str | None = None) -> int:
        actor_id = actor_id or str(self.active.id)
        a, f = self.actor(actor_id), self.fighter(actor_id)
        if f.move_locked or self.status(actor_id, "root") or any(s["type"] == "round_root" and s["round"] == self.s.round for s in f.statuses):
            return 0
        limit = f.turn_base
        if self.status(actor_id, "slow"):
            limit //= 2
        limit = max(0, limit-(self.status(actor_id, "move_penalty") or {}).get("value", 0))
        if a.faction == Faction.ENEMY and not self.is_relations:
            limit = max(0, limit-self.counts().get("Węzeł", 0))
        return max(0, limit-f.base_spent) + max(0, f.temporary_movement)

    def flanking(self, actor_id: str, target_id: str) -> bool:
        a, target = self.actor(actor_id), self.actor(target_id)
        return distance(a.position, target.position) == 1 and any(
            b.id != a.id and b.hp > 0 and distance(b.position, target.position) == 1
            and (a.position.col-target.position.col)*(b.position.col-target.position.col)
            + (a.position.row-target.position.row)*(b.position.row-target.position.row) < 0
            for b in self.allies(a))

    def free(self, p: Coordinate, actor_id: str = "") -> bool:
        return free(self.board, self.board_actors(), p, actor_id)

    def board_actors(self) -> tuple[Actor, ...]:
        return tuple(a for a in self.actors.values() if str(a.id) not in self.original.enemy_ai.escaped_actor_ids)

    def paths(self, actor_id: str, budget: int, *, parkour: bool = False) -> dict[Coordinate, ChargePath]:
        return charge_paths(self.board, self.actor(actor_id), self.board_actors(), budget, parkour=parkour)

    def adjacent_path(self, actor_id: str, target_id: str, budget: int) -> dict[str, Any] | None:
        paths = self.paths(actor_id, budget)
        options = [(paths[p].cost, len(paths[p].cells), p.row, p.col, p, paths[p])
                   for p in neighbors(self.board, self.actor(target_id).position) if p in paths]
        if not options:
            return None
        *_, destination, path = min(options)
        return {"destination": list(destination), "path": path.as_payload()}

    def join(self, actor_id: str) -> None:
        if self.is_relations or not self.s.chain or self.actor(actor_id).faction != Faction.ALLY or self.member(actor_id):
            return
        self.s.chain.members.append(actor_id)
        f = self.fighter(actor_id)
        f.cup, f.shield = 2*self.bonus(actor_id, "Kielich"), 2*self.bonus(actor_id, "Klepsydra")

    def add_rune(self, actor_id: str, rune: str) -> None:
        if self.is_relations:
            if rune not in STARTER_RUNES or (rune == "Fala" and actor_id != "nimra"):
                raise ValueError("Nieprawidłowa runa mocy.")
            if self.s.chain is None:
                self.s.serial += 1
                self.s.chain = ResonanceChain(self.s.serial)
            self.s.chain.entries.append(ResonanceEntry(rune, actor_id, rune))
            self.s.chain.entries = self.s.chain.entries[-MEMORY_LIMIT:]
            self.s.chain.members = list(dict.fromkeys(entry.contributor for entry in self.s.chain.entries))
            self.note(f"{self.actor(actor_id).name}: {rune} do Rezonansu.")
            return
        if self.s.chain is None:
            self.s.serial += 1
            self.s.chain = ResonanceChain(self.s.serial)
        self.join(actor_id)
        entries = self.s.chain.entries
        effective = (entries[-1].effective if entries else None) if rune == "Fala" else rune
        entries.append(ResonanceEntry(rune, actor_id, effective))
        for member in self.s.chain.members:
            f = self.fighter(member)
            if effective == "Kielich":
                f.cup += 2
            if effective == "Klepsydra":
                f.shield += 2
        f = self.fighter(actor_id)
        if effective == "Schody" and not f.move_locked:
            f.temporary_movement += 2
        if effective == "Błysk":
            self.s.queue.append(self.dice_task("Błysk · nowa kopia", actor_id, 1, 4, "heal", target=actor_id))
        self.note(f"{self.actor(actor_id).name}: {rune} do Rezonansu.")

    def end_chain(self, reason: str) -> None:
        if not self.s.chain:
            return
        if not self.is_relations:
            for f in self.s.fighters.values():
                f.cup = f.shield = f.temporary_movement = 0
        self.s.chain = None
        self.note(f"Rezonans wygaszony: {reason}.")

    def expire_turn_start(self, actor_id: str) -> None:
        for f in self.s.fighters.values():
            expired = [status for status in f.statuses if status.get("until_start") == actor_id
                       and status.get("turn", 0) <= self.fighter(actor_id).turn]
            if self.is_relations:
                if any(status["type"] == "temporary" for status in expired):
                    f.cup = 0
                if any(status["type"] == "prevention" for status in expired):
                    f.shield = 0
            f.statuses = [status for status in f.statuses if status not in expired]

    def expire_turn_end(self, actor_id: str) -> None:
        for f in self.s.fighters.values():
            f.statuses = [status for status in f.statuses if not (status.get("until_end") == actor_id
                          and status.get("turn", 0) <= self.fighter(actor_id).turn)]

    def skip_turn(self, actor_id: str) -> None:
        """Skipped unconscious sources still advance their printed deadlines."""
        self.fighter(actor_id).turn += 1
        self.expire_turn_start(actor_id)
        self.expire_turn_end(actor_id)

    def begin_turn(self) -> None:
        a = self.active
        f = self.fighter()
        f.turn += 1
        f.ordinary = f.special = f.reaction = True
        f.base_spent = f.temporary_movement = 0
        f.moved = f.offensive = f.continued = f.shot = f.sneak_used = False
        f.move_locked = bool(self.status(str(a.id), "prone"))
        f.statuses = [s for s in f.statuses if s["type"] != "prone" and not (s["type"] == "round_root" and s["round"] < self.s.round)]
        self.expire_turn_start(str(a.id))
        f.turn_base = effective_speed_feet(a) // 5
        if str(a.id) == "garran" and any(distance(a.position, b.position) == 1 for b in self.enemies()):
            f.turn_base //= 2
        f.start_adjacent = [str(b.id) for b in self.enemies() if distance(a.position, b.position) == 1]
        self.join(str(a.id))
        if not f.move_locked:
            f.temporary_movement = 2*self.bonus(str(a.id), "Schody")
        flashes = self.bonus(str(a.id), "Błysk")
        if flashes:
            self.s.queue.append(self.dice_task("Błysk · początek tury", str(a.id), flashes, 4, "heal", target=str(a.id)))
        if a.hp == 0 and a.uses_death_saves and not a.death_saves.dead and not a.death_saves.stable and not flashes:
            self.s.queue.append(self.dice_task("Rzut przeciw śmierci", str(a.id), 1, 20, "death_save", dc=10, modifier=self.bonus(str(a.id), "Oko")))
        self.s.phase = "idle"
        self.advance()

    def end_turn(self) -> bool:
        if self.s.phase not in {"idle", "end-preview"} or self.s.task:
            return False
        a, f = self.active, self.fighter()
        if a.faction == Faction.ALLY and a.hp > 0 and not f.continued:
            self.end_chain("koniec tury bez mocy runicznej" if self.is_relations else "koniec tury bez mocy wzmocnionej")
        rage = self.status(str(a.id), "rage")
        if rage:
            rage["remaining"] -= 1
            if not f.offensive or rage["remaining"] <= 0:
                f.statuses.remove(rage)
        self.expire_turn_end(str(a.id))
        f.temporary_movement = 0
        # A skipped unconscious turn does not terminate another hero's chain.
        for _ in self.s.order:
            self.s.index = (self.s.index+1) % len(self.s.order)
            if self.s.index == 0:
                self.s.round += 1
            if str(self.active.id) not in self.original.enemy_ai.escaped_actor_ids and (self.active.hp > 0 or (self.active.uses_death_saves and not self.active.death_saves.dead and not self.active.death_saves.stable)):
                self.begin_turn()
                return True
            self.skip_turn(str(self.active.id))
        self.end_chain("koniec walki")
        self.s.phase = "finished"
        return True

    def cards(self) -> tuple[ChargeCard, ...]:
        return cards_for(self.catalog, str(self.active.id))

    def card(self, card_id: str) -> ChargeCard | None:
        return next((c for c in self.cards() if c.id == card_id), None)

    def surcharge(self, card: ChargeCard, targets: list[str]) -> int:
        a, f = self.active, self.fighter()
        if str(a.id) == "nimra" and f.last_power == card.id:
            return 4 if f.power_streak >= 2 else 2
        if str(a.id) == "lorian" and not any(b.id != a.id and b.hp > 0 and distance(a.position, b.position) <= 2 for b in self.allies()):
            return 2
        if str(a.id) == "dagna" and card.id == "sacred_flame" and any(b.id != a.id and 0 < b.hp < b.max_hp/2 and distance(a.position, b.position) == 1 for b in self.allies()):
            return 2
        if str(a.id) == "erynd" and card.id in {"double_shot", "skirmish_shot", "anchoring_arrow"} and any(
            any(b.id != a.id and b.hp > 0 and distance(self.actor(t).position, b.position) == 1 for b in self.allies()) for t in targets):
            return 2
        return 0

    def price(self, card: ChargeCard, mode: str = "auto", targets: list[str] | None = None) -> int:
        return (card.cost if self.is_relations else card.enhanced_cost if mode == "enhanced" else card.base_cost) + self.surcharge(card, targets or [])

    def unavailable(self, action_id: str, mode: str = "base") -> str:
        a, f, c = self.active, self.fighter(), self.card(action_id)
        if a.hp <= 0:
            return "Postać nieprzytomna"
        if action_id in {"attack", "breaking_strike", "powerful_strike", "shadow_attack", "hamstring_cut", "charge", "double_shot", "skirmish_shot", "anchoring_arrow"}:
            weapon = self.weapons[str(a.id)]
            if weapon.ammunition_cost and not has_ammunition(a, weapon.ammunition_type, weapon.ammunition_cost*(2 if action_id == "double_shot" else 1)):
                return "Brak wymaganej amunicji"
        if action_id == "move":
            return "" if self.movement() else "Brak ruchu"
        if action_id in {"attack", "item"}:
            if not f.ordinary:
                return "Atak / przedmiot wykorzystany"
            if action_id == "item" and not self.items:
                return "Brak mikstury leczenia"
            return ""
        if action_id == "focus":
            return "" if a.faction == Faction.ALLY and f.special else "Specjalna wykorzystana"
        if not c:
            return "Brak tej mocy"
        if not f.special:
            return "Specjalna wykorzystana"
        if "A" in c.budget and not f.ordinary:
            return "Wymaga ataku i specjalnej"
        if c.id == "bastion_charge" and (f.moved or f.move_locked or self.movement() <= 0):
            return "Wymaga pełnego, niewykorzystanego ruchu"
        if c.id == "rage" and self.status(str(a.id), "rage"):
            return "Szał już aktywny"
        if c.id == "shield_bash" and not any(i.kind == "shield" and i.equipped for i in a.inventory):
            return "Wymaga tarczy"
        if c.id in {"breaking_strike", "powerful_strike", "hamstring_cut", "shadow_attack", "charge", "double_shot", "skirmish_shot", "anchoring_arrow"} and self.weapons[str(a.id)].source_type != "weapon":
            return "Wymaga broni"
        if c.id in {"breaking_strike", "powerful_strike", "hamstring_cut", "charge"} and self.weapons[str(a.id)].kind != "melee":
            return "Wymaga broni wręcz"
        if c.id in {"double_shot", "skirmish_shot", "anchoring_arrow"} and self.weapons[str(a.id)].proficiency_id not in {"longbow", "shortbow"}:
            return "Wymaga łuku"
        if self.is_relations:
            blocked = self.resonance_preview(c)["blocked_reasons"]
            if blocked:
                return " · ".join(blocked)
        return "Za mało ładunków" if f.charges < self.price(c, mode, (self.s.preview or {}).get("targets", [])) else ""

    @staticmethod
    def potions(actor: Actor) -> list[Any]:
        return [i for i in actor.inventory if i.quantity > 0 and (i.id in {"potion_of_healing", "healing_potion", "mission_potion", "mission_weak_potion"} or i.source_ref in {"potion_of_healing", "healing_potion"})]

    def choose(self, action_id: str) -> bool:
        if self.s.phase != "idle" or self.unavailable(action_id):
            return False
        self.s.preview = dict(id=action_id, mode="auto" if self.is_relations else "base", targets=[], destination=None, path=None,
                              center=None, exclude=None, exclude_chosen=False)
        if action_id == "item":
            self.s.preview["item"] = deepcopy(self.items[0])
        self.s.phase = "preview"
        if action_id in {"rage", "second_wind", "hide", "focus", "item"}:
            self.s.preview["targets"] = [str(self.active.id)]
        if action_id in {"roar", "force_wave", "preserve_life"}:
            self.s.preview["center"] = list(self.active.position)
        return True

    def mode(self, mode: str) -> bool:
        if self.is_relations or self.s.phase != "preview" or mode not in {"base", "enhanced"} or not self.card(self.s.preview["id"]):
            return False
        self.s.preview["mode"] = mode
        if self.s.preview["id"] == "bastion_charge" and self.s.preview["targets"]:
            preview = self.adjacent_path(str(self.active.id), self.s.preview["targets"][0], self.movement()+(2 if mode == "enhanced" else 0))
            self.s.preview.update(preview or {"destination": None, "path": None, "targets": []})
        return True

    def area(self, preview: Task | None = None) -> list[str]:
        p = preview or self.s.preview
        if not p or p["center"] is None:
            return []
        radius = (1 if p["id"] == "flame_fan" else 2) + self.effect_modifiers(p["id"]).get("range_bonus", 0)
        return [str(a.id) for a in self.board_actors() if (a.hp > 0 or (p["id"] == "preserve_life" and not a.death_saves.dead)) and playable(self.board, a.position)
                and distance(a.position, point(p["center"])) <= radius
                and (p["id"] == "flame_fan" or ((a.faction == self.active.faction) if p["id"] == "preserve_life"
                     else (a.faction not in {self.active.faction, Faction.NEUTRAL} if self.is_relations else a.faction != self.active.faction)))]

    def legal_targets(self, preview: Task | None = None) -> list[str]:
        p = preview or self.s.preview
        if not p:
            return []
        a, action_id = self.active, p["id"]
        if action_id in {"rage", "second_wind", "hide", "focus"}:
            return [str(a.id)]
        if action_id in {"move", "misty_step", "flame_fan", "force_wave", "roar", "preserve_life"}:
            return []
        modifiers = self.effect_modifiers(action_id)
        range_bonus = modifiers.get("range_bonus", 0)
        if action_id == "item":
            return [str(b.id) for b in self.allies() if not b.death_saves.dead and distance(a.position, b.position) <= 1]
        if action_id in {"bless", "healing_word", "inspiration", "passage_song", "energy_recovery", "arcane_shield"}:
            return [str(b.id) for b in self.allies() if distance(a.position, b.position) <= 6+range_bonus
                    and not b.death_saves.dead and (b.hp > 0 or action_id == "healing_word")
                    and (action_id not in {"inspiration", "energy_recovery"} or b.id != a.id)
                    and not (action_id == "inspiration" and hymn_source(b))]
        targets = []
        for b in self.enemies():
            d, actor_id, target_id = distance(a.position, b.position), str(a.id), str(b.id)
            if action_id == "guard_vault":
                legal = d <= 4+range_bonus and any(self.free(q, actor_id) for q in neighbors(self.board, b.position))
            elif action_id in {"bastion_charge", "charge"}:
                legal = bool(self.adjacent_path(actor_id, target_id, self.path_budget(p)))
            elif action_id == "shield_bash":
                legal = d == 1 and line_of_sight_clear(self.board, a.position, b.position)
            elif action_id == "shadow_attack" and target_id not in self.fighter().hidden:
                legal = False
            elif action_id == "hunters_mark":
                legal = d <= 12+range_bonus and line_of_sight_clear(self.board, a.position, b.position)
            elif action_id in {"sacred_flame", "mockery", "force_darts"}:
                legal = d <= 6+range_bonus and (action_id == "mockery" or line_of_sight_clear(self.board, a.position, b.position))
            else:
                origin = point(p["destination"]) if action_id == "skirmish_shot" and p.get("destination") else a.position
                legal = distance(origin, b.position) <= self.weapons[actor_id].range+range_bonus and line_of_sight_clear(self.board, origin, b.position)
            if legal:
                targets.append(target_id)
        return targets

    def target_candidates(self, preview: Task | None = None) -> list[str]:
        """Visible creatures to inspect, including currently illegal targets."""
        p = preview or self.s.preview
        if not p or p["id"] in {"move", "misty_step", "rage", "second_wind", "hide", "focus",
                                "flame_fan", "force_wave", "roar", "preserve_life"}:
            return []
        if p["id"] == "skirmish_shot" and not p.get("destination"):
            return []
        if p["id"] == "guard_vault" and p.get("targets"):
            return []
        friendly = p["id"] in {"item", "bless", "healing_word", "inspiration", "passage_song", "energy_recovery", "arcane_shield"}
        actors = self.allies() if friendly else self.enemies()
        return [str(a.id) for a in actors if not a.death_saves.dead and playable(self.board, a.position)]

    def target_rejection(self, target_id: str, preview: Task | None = None) -> str:
        """Explain existing legality without mutating the action or its targets."""
        p = preview or self.s.preview
        if not p:
            return "Najpierw wybierz działanie."
        if target_id in self.legal_targets(p):
            return ""
        if target_id not in self.actors:
            return "Nie ma tu celu."
        a, b, action_id = self.active, self.actor(target_id), p["id"]
        if target_id in self.original.enemy_ai.escaped_actor_ids:
            return "Cel opuścił pole walki."
        if b.death_saves.dead or (b.hp <= 0 and action_id not in {"item", "healing_word"}):
            return "Cel jest nieprzytomny lub pokonany."
        friendly = action_id in {"item", "bless", "healing_word", "inspiration", "passage_song", "energy_recovery", "arcane_shield"}
        if friendly and b.faction != a.faction:
            return "To działanie wymaga sojusznika."
        if not friendly and b.faction in {a.faction, Faction.NEUTRAL}:
            return "To działanie wymaga przeciwnika."
        if action_id in {"inspiration", "energy_recovery"} and b.id == a.id:
            return "Wybierz innego bohatera."
        if action_id == "inspiration" and hymn_source(b):
            return "Cel ma już niewykorzystany Hymn odwagi."
        if action_id == "shadow_attack" and target_id not in self.fighter().hidden:
            return "Cel widzi atakującego; ta moc wymaga ukrycia przed celem."
        if action_id in {"bastion_charge", "charge"}:
            return "Brak wolnej drogi do pola przy celu w zasięgu tej mocy."
        range_bonus = self.effect_modifiers(action_id).get("range_bonus", 0)
        origin = point(p["destination"]) if action_id == "skirmish_shot" and p.get("destination") else a.position
        limit = (1 if action_id == "item" else 6+range_bonus) if friendly else {
            "guard_vault": 4+range_bonus, "shield_bash": 1,
            "hunters_mark": 12+range_bonus, "sacred_flame": 6+range_bonus,
            "mockery": 6+range_bonus, "force_darts": 6+range_bonus,
        }.get(action_id, self.weapons[str(a.id)].range+range_bonus)
        if distance(origin, b.position) > limit:
            return f"Cel jest poza zasięgiem ({distance(origin, b.position)} pól; zasięg: {limit})."
        if action_id == "guard_vault":
            return "Brak wolnego pola obok celu."
        if not friendly and action_id != "mockery" and not line_of_sight_clear(self.board, origin, b.position):
            return "Przeszkoda zasłania linię widzenia do celu."
        return "Ten cel nie spełnia warunków działania."

    def path_budget(self, preview: Task) -> int:
        action_id = preview["id"]
        bonus = self.effect_modifiers(action_id).get("move_bonus", 0)
        if action_id == "move":
            return self.movement()
        if action_id == "charge":
            return 3+bonus
        if action_id == "skirmish_shot":
            return 2+bonus
        if action_id == "bastion_charge":
            return self.movement()+bonus+(2 if not self.is_relations and preview.get("mode") == "enhanced" else 0)
        return self.board.dimensions.cols*self.board.dimensions.rows

    def available_fields(self) -> list[Coordinate]:
        if self.s.task and self.s.task["type"] == "bonus_target":
            return [self.actor(key).position for key in self.s.task["targets"] if self.actor(key).hp > 0
                    and distance(self.actor(key).position, self.actor(self.s.task["source"]).position) == 1]
        if self.s.task and self.s.task["type"] == "relocate":
            return self.relocation_fields(self.s.task)
        p, a = self.s.preview, self.active
        if self.s.phase != "preview" or p is None:
            return []
        if p["id"] in {"flame_fan", "force_wave"} and p["center"] is not None and not p["exclude_chosen"]:
            return [self.actor(key).position for key in self.area()]
        if p["id"] == "flame_fan":
            return [Coordinate(x, y) for y in range(self.board.dimensions.rows) for x in range(self.board.dimensions.cols)
                    if playable(self.board, Coordinate(x, y)) and distance(a.position, Coordinate(x, y)) <= 6+self.effect_modifiers(p["id"]).get("range_bonus", 0)]
        if p["id"] in {"move", "skirmish_shot"} and not (p["id"] == "skirmish_shot" and p["destination"]):
            return [q for q in self.paths(str(a.id), self.path_budget(p)) if q != a.position]
        if p["id"] == "misty_step":
            return [Coordinate(x, y) for y in range(self.board.dimensions.rows) for x in range(self.board.dimensions.cols)
                    if self.free(Coordinate(x, y), str(a.id)) and distance(a.position, Coordinate(x, y)) <= 6+self.effect_modifiers(p["id"]).get("range_bonus", 0)
                    and line_of_sight_clear(self.board, a.position, Coordinate(x, y)) and Coordinate(x, y) != a.position]
        if p["id"] == "guard_vault" and p["targets"]:
            paths = self.paths(str(a.id), self.board.dimensions.cols*self.board.dimensions.rows, parkour=True)
            return [q for q in neighbors(self.board, self.actor(p["targets"][0]).position) if q in paths and q != a.position]
        return [self.actor(key).position for key in self.legal_targets()]

    def select(self, pos: Coordinate) -> bool:
        if pos not in self.available_fields():
            return False
        if self.s.task and self.s.task["type"] == "bonus_target":
            self.s.task["target"] = next(key for key in self.s.task["targets"] if self.actor(key).position == pos)
            return True
        if self.s.task and self.s.task["type"] == "relocate":
            self.s.task["destination"] = list(pos)
            return True
        p, a = self.s.preview, self.active
        if p["id"] in {"flame_fan", "force_wave"} and p["center"] is not None and not p["exclude_chosen"]:
            p["exclude"] = next(key for key in self.area() if self.actor(key).position == pos)
            p["exclude_chosen"] = True
            return True
        if p["id"] == "flame_fan":
            p.update(center=list(pos), exclude=None, exclude_chosen=False)
            return True
        if p["id"] in {"move", "misty_step", "skirmish_shot"} and not (p["id"] == "skirmish_shot" and p["destination"]):
            path = ChargePath((pos,), (0,)) if p["id"] == "misty_step" else self.paths(str(a.id), self.path_budget(p))[pos]
            p.update(destination=list(pos), path=path.as_payload(), targets=[])
            return True
        if p["id"] == "guard_vault" and p["targets"]:
            path = self.paths(str(a.id), self.board.dimensions.cols*self.board.dimensions.rows, parkour=True)[pos]
            p.update(destination=list(pos), path=path.as_payload())
            return True
        target_id = next(key for key in self.legal_targets() if self.actor(key).position == pos)
        if p["id"] in {"bless", "passage_song"}:
            if target_id in p["targets"]:
                p["targets"].remove(target_id)
            elif len(p["targets"]) < 2:
                p["targets"].append(target_id)
        elif p["id"] in {"double_shot", "force_darts"}:
            maximum = 3 if p["id"] == "force_darts" else 2
            if len(p["targets"]) == maximum:
                p["targets"] = []
            p["targets"].append(target_id)
        else:
            p["targets"] = [target_id]
        if p["id"] in {"bastion_charge", "charge"}:
            p.update(self.adjacent_path(str(a.id), target_id, self.path_budget(p)))
        return True

    def exclude(self, actor_id: str | None) -> bool:
        p = self.s.preview
        if self.s.phase != "preview" or not p or p["id"] not in {"flame_fan", "force_wave"} or p["center"] is None:
            return False
        if actor_id is not None and actor_id not in self.area():
            return False
        p.update(exclude=actor_id, exclude_chosen=True)
        return True

    def ready(self) -> bool:
        p = self.s.preview
        if not p or self.s.phase != "preview" or self.unavailable(p["id"], p["mode"]):
            return False
        if p["id"] in {"rage", "second_wind", "hide", "focus"}:
            return p["targets"] == [str(self.active.id)]
        if p["id"] in {"force_wave", "flame_fan"}:
            return p["center"] is not None and p["exclude_chosen"]
        if p["id"] in {"roar", "preserve_life"}:
            return True
        if p["id"] in {"move", "misty_step"}:
            return p["destination"] is not None
        if p["id"] in {"guard_vault", "bastion_charge", "charge", "skirmish_shot"}:
            return p["destination"] is not None and len(p["targets"]) == 1
        if p["id"] in {"bless", "passage_song"}:
            return 1 <= len(p["targets"]) <= 2
        return len(p["targets"]) == (3 if p["id"] == "force_darts" else 2 if p["id"] == "double_shot" else 1)

    def cancel(self) -> bool:
        if self.s.inspected:
            self.s.inspected = ""
            return True
        if self.s.phase == "preview":
            p = self.s.preview
            if p["id"] == "guard_vault" and p["targets"]:
                p.update(targets=[], destination=None, path=None)
            elif p["id"] == "skirmish_shot" and p["destination"]:
                p.update(targets=[], destination=None, path=None)
            else:
                self.s.preview = None
                self.s.phase = "idle"
            return True
        if self.s.task and self.s.task["type"] == "relocate":
            self.s.task["destination"] = None
            return True
        if self.s.phase == "end-preview":
            self.s.phase = "idle"
            return True
        return False

    def revalidate(self, p: Task) -> bool:
        if p["id"] == "item" and p.get("item") not in self.items:
            return False
        if p["center"] is not None and (not playable(self.board, point(p["center"])) or (p["id"] == "flame_fan" and distance(self.active.position, point(p["center"])) > 6+self.effect_modifiers(p["id"]).get("range_bonus", 0))):
            return False
        if p["exclude"] is not None and p["exclude"] not in self.area(p):
            return False
        if p["destination"] is not None and not self.free(point(p["destination"]), str(self.active.id)):
            return False
        if p["id"] == "misty_step" and point(p["destination"]) not in self.available_fields():
            return False
        if p["id"] in {"rage", "second_wind", "hide", "focus"}:
            if p["targets"] != [str(self.active.id)]:
                return False
        elif p["id"] in {"move", "misty_step", "force_wave", "flame_fan", "roar", "preserve_life"}:
            if p["targets"]:
                return False
        elif any(key not in self.legal_targets(p) for key in p["targets"]):
            return False
        if p["id"] == "guard_vault" and distance(point(p["destination"]), self.actor(p["targets"][0]).position) != 1:
            return False
        if p["id"] in {"bastion_charge", "charge"}:
            updated = self.adjacent_path(str(self.active.id), p["targets"][0], self.path_budget(p))
            return bool(updated and updated["path"] == p["path"] and updated["destination"] == p["destination"])
        if p["path"] and p["id"] != "misty_step":
            budget = self.path_budget(p)
            path = self.paths(str(self.active.id), budget, parkour=p["id"] == "guard_vault").get(point(p["destination"]))
            return bool(path and path.as_payload() == p["path"])
        return True

    def commit(self) -> bool:
        if not self.ready() or not self.revalidate(self.s.preview):
            return False
        p, a, f = deepcopy(self.s.preview), self.active, self.fighter()
        c = self.card(p["id"])
        self.s.serial += 1
        self.s.action = dict(**p, serial=self.s.serial, actor=str(a.id), harmed=[], damage_groups={}, handled_hooks=[],
                             results=[], had_chain=bool(self.s.chain), card=bool(c), closed=False,
                             modifiers=self.effect_modifiers(c), resonance=self.resonance_preview(c), successful=False, resonance_applied=False)
        if c:
            cost = self.price(c, p["mode"], p["targets"])
            self.s.action["paid_cost"] = cost
            f.charges -= cost
            f.special = False
            if "A" in c.budget:
                f.ordinary = False
            if self.is_relations:
                if self.s.action["resonance"]["transition"] == "reset":
                    self.end_chain("niezgodna runa · nowy łańcuch")
                f.continued = True
            elif p["mode"] == "enhanced":
                self.add_rune(str(a.id), c.rune)
                f.continued = True
            if str(a.id) == "nimra" and f.last_rune and f.last_rune != c.rune:
                self.offer_regeneration(str(a.id), "Inna runa niż poprzednia moc")
            f.power_streak = f.power_streak+1 if f.last_power == c.id else 1
            f.last_power, f.last_rune = c.id, c.rune
            self.note(f"{a.name}: {c.name}, −{cost} ładunków.")
        elif p["id"] == "focus":
            f.special = False
            self.end_chain("Skupienie")
        elif p["id"] in {"attack", "item"}:
            f.ordinary = False
        self.s.preview = None
        self.s.phase = "task"
        self.plan(p)
        self.s.queue.append(dict(type="finish"))
        self.advance()
        return True

    @staticmethod
    def dice_task(label: str, actor: str, count: int, sides: int, outcome: str, **extra: Any) -> Task:
        return dict(type="roll", label=label, actor=actor, parts=[dict(count=count, sides=sides, label=label)], outcome=outcome, **extra)

    @staticmethod
    def save_task(target: str, ability: str, dc: int, effect: Task) -> Task:
        return dict(type="save", target=target, ability=ability, dc=dc, effect=effect)

    def plan(self, p: Task) -> None:
        q, actor_id, action_id = self.s.queue, str(self.active.id), p["id"]
        target = p["targets"][0] if p["targets"] else ""
        dc = int(self.catalog["rules"]["save_dc_base"])
        modifiers = self.s.action.get("modifiers", {})
        def healing_task(label: str, sides: int, targets: list[str], modifier: int = 0) -> Task:
            task = self.dice_task(label, actor_id, 1, sides, "heal_group", targets=targets,
                                  modifier=modifier+modifiers.get("heal_flat", 0), power=True)
            task["parts"].extend(dict(die, label="Rezonans · leczenie") for die in modifiers.get("heal_dice", []))
            return task
        if action_id == "focus":
            q.append(self.dice_task("Skupienie · odzysk ładunków", actor_id, 1, 20, "charges", target=actor_id))
        elif action_id == "item":
            potion = p["item"]
            if potion["owner"]:
                owner = self.actor(potion["owner"])
                self.update_actor(replace(owner, inventory=tuple(replace(i, quantity=i.quantity-1) if i.id == potion["id"] else i for i in owner.inventory if i.id != potion["id"] or i.quantity > 1)))
            self.s.action["consumed_item"] = potion
            q.append(self.dice_task(potion["name"], actor_id, potion["count"], potion["sides"], "heal", target=target, modifier=potion["modifier"]))
        elif action_id == "second_wind":
            q.append(healing_task("Żar odnowy", 10, p["targets"], self.active.level))
        elif action_id == "rage":
            q.append(dict(type="status", target=actor_id, status="rage", extra=dict(remaining=max(1, self.ability(actor_id, "strength")+self.ability(actor_id, "constitution")+modifiers.get("duration_bonus", 0)))))
        elif action_id == "hide":
            advantage = bool(modifiers.get("hide_advantage") or modifiers.get("check_advantage"))
            task = self.dice_task("Całun cienia · Zręczność", actor_id, 1, 20, "hide",
                modifier=self.ability(actor_id, "dexterity")+self.bonus(actor_id, "Oko")+self.cover_bonuses.get(self.active.position, 0),
                dc=min((passive_skill_score(b, "perception") for b in self.enemies()), default=10)-modifiers.get("perception_penalty", 0)+1,
                perception_penalty=modifiers.get("perception_penalty", 0), mode="advantage" if advantage else "normal")
            if advantage:
                task["parts"].append(dict(count=1, sides=20, label="Druga k20"))
            q.append(task)
        elif action_id == "shield_bash":
            self.fighter().offensive = True
            q.append(self.dice_task("Impuls egidy · obrona przeciwnika", target, 1, 20, "contest", source=actor_id,
                                   modifier=max(self.ability(target, "strength"), self.ability(target, "dexterity"))))
        elif action_id in {"move", "bastion_charge", "charge", "guard_vault", "skirmish_shot", "misty_step"}:
            previous = list(self.active.position)
            if action_id == "bastion_charge":
                self.fighter().move_locked = True
                self.fighter().temporary_movement = 0
                self.fighter().offensive = True
            for pos, cost in zip(p["path"]["cells"], p["path"]["costs"]):
                q.append(dict(type="move_step", actor=actor_id, origin=previous, position=pos, cost=cost if action_id == "move" else 0,
                              opportunities=action_id not in {"skirmish_shot", "misty_step"} and not modifiers.get("no_opportunity", False), parkour=action_id == "guard_vault"))
                previous = pos
            if action_id == "bastion_charge":
                q.append(self.save_task(target, "constitution", dc+self.ability(actor_id, "strength")+len(p["path"]["cells"]),
                                       dict(kind="prone", source=actor_id, destination=p["destination"], save_penalty=modifiers.get("enemy_save_penalty", 0))))
            if action_id in {"charge", "skirmish_shot"}:
                q.append(dict(type="attack", actor=actor_id, target=target, power=action_id))
        elif action_id in {"attack", "breaking_strike", "powerful_strike", "shadow_attack", "hamstring_cut", "double_shot", "anchoring_arrow"}:
            q.extend(dict(type="attack", actor=actor_id, target=t, power=action_id) for t in p["targets"])
        elif action_id == "hunters_mark":
            self.fighter().mark = target
            if modifiers.get("enemy_move_penalty"):
                self.add_status(target, "move_penalty", value=modifiers["enemy_move_penalty"],
                                until_end=target, turn=self.fighter(target).turn+1)
            self.note(f"Piętno łowcy: {self.actor(target).name}.")
        elif action_id == "inspiration":
            b = self.actor(target)
            sides = modifiers.get("hymn_sides", 6)
            self.update_actor(replace(b, features=(*b.features, FeatureGrant("resonance_hymn", f"Hymn odwagi · 1k{sides}", FeatureSourceKind.SCENARIO, actor_id, "Bezterminowa kość do wybranego k20, do wykorzystania."))))
            if self.is_relations:
                self.add_status(target, "hymn", sides=sides, source=actor_id)
            self.note(f"{b.name}: Hymn odwagi · 1k{sides} do wykorzystania.")
        elif action_id == "energy_recovery":
            q.append(self.dice_task("Akord odnowy", actor_id, 1, 6, "charges", target=target, modifier=modifiers.get("charge_bonus_flat", 0)))
        elif action_id == "healing_word":
            q.append(healing_task("Leczenie", 6, p["targets"], self.ability(actor_id, "wisdom")))
        elif action_id == "preserve_life":
            q.append(healing_task("Krąg odnowy · wspólna kość", 6, self.area(p)))
        elif action_id in {"bless", "arcane_shield"}:
            q.extend(dict(type="status", target=t, status="bless" if action_id == "bless" else "arcane",
                          extra=dict(value=(1+modifiers.get("bless_bonus", 0)) if action_id == "bless" else (2+modifiers.get("target_ac_next_turn", 0)),
                                     source=actor_id, until_start=actor_id, turn=self.fighter().turn+1)) for t in p["targets"])
        elif action_id == "passage_song":
            q.extend(dict(type="relocate", target=t, source=actor_id, radius=2+modifiers.get("move_bonus", 0), walk=True, opportunities=False, label="Pieśń przejścia", destination=None) for t in p["targets"])
        elif action_id == "force_darts":
            for index, t in enumerate(p["targets"]):
                components = [dict(count=1, sides=4, modifier=1, damage_type="force", label="Pocisk eteru")]
                if index == 0:
                    components.extend(dict(die, modifier=die.get("modifier", 0), label=die.get("label", "Rezonans · pierwszy pocisk"))
                                      for die in modifiers.get("first_damage_dice", []))
                q.append(dict(type="damage", actor=actor_id, target=t, power=action_id, components=components))
        elif action_id == "roar":
            targets = self.area(p)
            self.fighter().offensive = bool(targets)
            q.extend(self.save_task(t, "wisdom", dc+self.ability(actor_id, "strength"), dict(kind="fear", source=actor_id, save_penalty=modifiers.get("enemy_save_penalty", 0),
                        move_penalty=modifiers.get("enemy_move_penalty", 0))) for t in targets)
        elif action_id in {"sacred_flame", "mockery", "force_wave", "flame_fan"}:
            self.fighter().offensive = True
            save, ability, sides, damage_type, half = {
                "sacred_flame": ("dexterity", "wisdom", 6, "radiant", False),
                "mockery": ("wisdom", "charisma", 4, "psychic", False),
                "force_wave": ("strength", "intelligence", 6, "force", True),
                "flame_fan": ("dexterity", "intelligence", 6, "fire", True),
            }[action_id]
            targets = [t for t in self.area(p) if t != p["exclude"]] if action_id in {"force_wave", "flame_fan"} else p["targets"]
            task = self.dice_task("Obrażenia mocy · wspólny rzut", actor_id, 2, sides, "area_damage", targets=targets,
                                   save_ability=save, dc=dc+self.ability(actor_id, ability), damage_type=damage_type, half=half, fear=action_id == "mockery",
                                   origin=p["center"] if p.get("center") is not None else list(self.active.position),
                                   save_penalty=modifiers.get("enemy_save_penalty", 0), move_penalty=modifiers.get("enemy_move_penalty", 0))
            task["parts"].extend(dict(die, label=die.get("label", "Rezonans · obrażenia")) for die in modifiers.get("damage_dice_extra", []))
            q.append(task)

    def offer_regeneration(self, actor_id: str, reason: str) -> None:
        if actor_id in self.actors and self.actor(actor_id).faction == Faction.ALLY:
            f = self.fighter(actor_id)
            if f.regeneration_round != self.s.round:
                f.regeneration_reason = reason

    def heal(self, target_id: str, amount: int, source: str = "", power: bool = False) -> None:
        a = self.actor(target_id)
        if a.death_saves.dead:
            return
        bonus = 2 if power and source == "dagna" and target_id != source else 0
        hp = min(effective_max_hit_points(a), a.hp+max(1, amount+bonus))
        self.update_actor(replace(a, hp=hp, death_saves=DeathSaveState() if hp else a.death_saves))
        if power and source == "dagna" and target_id != source and a.hp < a.max_hp/2 and hp > a.hp:
            self.offer_regeneration(source, "Leczenie sojusznika poniżej połowy PW")
        self.note(f"{a.name}: +{hp-a.hp} PW ({hp}/{a.max_hp}).")

    def damage(self, target_id: str, components: list[Task], source: str, *, critical: bool = False) -> Task:
        a, f = self.actor(target_id), self.fighter(target_id)
        hp, temporary = a.hp, a.temp_hp
        if self.is_relations:
            # Printed temporary PW and item-granted temporary PW form one pool.
            if temporary > f.cup:
                f.cup = 0
                f.statuses = [status for status in f.statuses if status["type"] != "temporary"]
            else:
                temporary = 0
        loss = dict(hp=0, temporary=0, shield=0, received=0)
        for component in components:
            kind, value = component["damage_type"], max(0, component["value"])
            if kind in a.damage_affinities.immunities:
                value = 0
            if kind in a.damage_affinities.resistances or (self.status(target_id, "rage") and kind in {"bludgeoning", "piercing", "slashing"}):
                value //= 2
            if kind in a.damage_affinities.vulnerabilities:
                value *= 2
            shield = min(f.shield, value) if kind != "psychic" else 0
            f.shield -= shield
            value -= shield
            loss["shield"] += shield
            loss["received"] += value
            cup = min(f.cup, value)
            f.cup -= cup
            value -= cup
            temp = min(temporary, value)
            temporary -= temp
            value -= temp
            loss["temporary"] += cup+temp
            lost = min(hp, value)
            hp -= lost
            loss["hp"] += lost
        death = a.death_saves
        if hp == 0 and a.uses_death_saves and loss["received"] > 0:
            if a.hp == 0:
                failures = min(3, death.failures+(2 if critical else 1))
                death = DeathSaveState(failures=failures, successes=death.successes, dead=failures == 3)
            elif loss["received"]-loss["temporary"]-a.hp >= a.max_hp:
                death = DeathSaveState(failures=3, dead=True)
            else:
                death = DeathSaveState()
        self.update_actor(replace(a, hp=hp, temp_hp=temporary, death_saves=death))
        if loss["received"]:
            if self.s.action:
                if target_id not in self.s.action["harmed"]:
                    self.s.action["harmed"].append(target_id)
                group = self.s.action["damage_groups"].setdefault(source, [])
                if target_id not in group:
                    group.append(target_id)
            if target_id == "brakka" and self.status(target_id, "rage") and self.actor(source).faction == Faction.ENEMY:
                self.offer_regeneration(target_id, "Obrażenia podczas Szału")
        detail = f", −{loss['temporary']} tymczasowych PW" if loss["temporary"] else ""
        detail += f", osłona pochłonęła {loss['shield']}" if loss["shield"] else ""
        self.note(f"{a.name}: −{loss['hp']} PW{detail}.")
        return loss

    def attack_task(self, task: Task) -> None:
        actor_id, target_id = task["actor"], task["target"]
        a, b, f = self.actor(actor_id), self.actor(target_id), self.fighter(actor_id)
        weapon = ChargeWeapon(**task["weapon"]) if task.get("weapon") else self.weapons[actor_id]
        if a.hp <= 0 or b.hp <= 0 or distance(a.position, b.position) > weapon.range or not line_of_sight_clear(self.board, a.position, b.position):
            self.note("Atak nie jest już możliwy.")
            return
        if weapon.spell_save_ability:
            parts = [dict(count=p["count"], sides=p["sides"], label=p["label"]) for p in weapon.components if p.get("count")]
            roll = dict(type="roll", actor=actor_id, target=target_id, label=weapon.name, outcome="enemy_spell",
                        components=list(weapon.components), parts=parts, weapon=asdict(weapon))
            if parts:
                self.s.queue.insert(0, roll)
            else:
                self.resolve_roll(roll, [], None, 0, True)
            f.offensive = True
            return
        if weapon.ammunition_cost:
            if not has_ammunition(a, weapon.ammunition_type, weapon.ammunition_cost):
                self.note(f"{a.name}: brak amunicji.")
                return
            spent = consume_ammunition(a, weapon.ammunition_type, weapon.ammunition_cost)
            self.update_actor(spent.actor_after)
            self.original = record_ammunition_expenditure(self.original, a, spent)
        f.offensive = True
        melee, hidden = weapon.kind == "melee", target_id in f.hidden
        modifiers = self.action_modifiers(actor_id, task.get("power", "attack"))
        next_attack = self.status(actor_id, "next_attack") if weapon.source_type == "weapon" else None
        advantage = hidden or bool(melee and self.status(target_id, "prone")) or bool(modifiers.get("check_advantage") or modifiers.get("attack_advantage") or next_attack)
        if next_attack:
            f.statuses.remove(next_attack)
        disadvantage = bool(self.status(actor_id, "fear")) or (not melee and any(distance(a.position, e.position) == 1 for e in self.enemies(a)))
        f.statuses = [s for s in f.statuses if s["type"] != "fear"]
        mode = "normal" if advantage == disadvantage else "advantage" if advantage else "disadvantage"
        precision = int(actor_id == "erynd" and not f.shot and not f.moved and not melee)
        f.shot = True
        components = list(weapon.attack_modifiers)
        # Older/custom weapons can carry only the aggregate. Preserve that value.
        remainder = weapon.attack_bonus-sum(part["value"] for part in components)
        if remainder:
            components.append(dict(label="Broń i efekty", value=remainder))
        if a.faction == Faction.ALLY:
            components.insert(0, dict(label=ABILITY_LABELS_PL[weapon.ability], value=self.ability(actor_id, weapon.ability)))
        bonuses = (("Rezonans · Oko", self.bonus(actor_id, "Oko")),
                   ("Pieczęć łaski", (self.status(actor_id, "bless") or {}).get("value", int(bool(self.status(actor_id, "bless"))))),
                   ("Czysty strzał · pierwszy strzał bez ruchu", precision),
                   ("Powalony cel · atak dystansowy", -2 if not melee and self.status(target_id, "prone") else 0))
        components.extend(dict(label=label, value=value) for label, value in bonuses if value)
        modifier = sum(part["value"] for part in components)
        cover = self.cover(target_id, a.position)
        roll = self.dice_task(f"{a.name} → {b.name} · {weapon.name}", actor_id, 1, 20, "attack", target=target_id,
                             modifier=modifier, modifier_components=components, dc=self.ac(target_id, a.position),
                             cover_bonus=cover.cover_bonus, cover_sources=list(cover.cover_sources),
                             mode=mode, power=task.get("power", "attack"),
                             hidden=hidden, melee=melee, reaction_pending=task.get("reaction_pending", False), weapon=asdict(weapon))
        roll["life_drain"] = task.get("life_drain", False)
        if mode != "normal":
            roll["parts"].append(dict(count=1, sides=20, label="Druga k20"))
        self.s.queue.insert(0, roll)

    def damage_task(self, task: Task) -> None:
        if self.actor(task["target"]).hp <= 0:
            return
        components = deepcopy(task["components"])
        grot = self.bonus(task["actor"], "Grot")
        if grot:
            components.append(dict(count=grot*(2 if task.get("critical") else 1), sides=4, modifier=0,
                                   damage_type=components[0]["damage_type"], label="Rezonans · Grot"))
        roll = dict(task, type="roll", outcome="damage", label=f"Obrażenia → {self.actor(task['target']).name}", components=components,
                    parts=[dict(count=p["count"], sides=p["sides"], label=p["label"]) for p in components if p.get("count")])
        if roll["parts"]:
            self.s.queue.insert(0, roll)
        else:
            self.resolve_roll(roll, [], None, 0, True)

    def relocation_fields(self, task: Task) -> list[Coordinate]:
        a = self.actor(task["target"])
        if a.hp <= 0:
            return []
        paths = self.paths(str(a.id), task["radius"]) if task.get("walk") or task["label"] == "Impuls egidy" else None
        return [Coordinate(x, y) for y in range(self.board.dimensions.rows) for x in range(self.board.dimensions.cols)
                if distance(a.position, Coordinate(x, y)) <= task["radius"] and self.free(Coordinate(x, y), str(a.id))
                and (paths is None or Coordinate(x, y) in paths)
                and (task["label"] != "Impuls egidy" or Coordinate(x, y) != a.position)]

    def move_step(self, task: Task) -> None:
        actor_id = task["actor"]
        a, f, destination = self.actor(actor_id), self.fighter(actor_id), point(task["position"])
        # An interrupt can kill, root or relocate the mover. Never continue a stale path.
        rooted_step = self.status(actor_id, "root") and (not self.is_relations or task["cost"] > 0)
        stale_destination = self.is_relations and not task.get("parkour") and not self.free(destination, actor_id)
        overspent = self.is_relations and task["cost"] > self.movement(actor_id)
        if a.hp <= 0 or (task.get("origin") and point(task["origin"]) != a.position) or rooted_step or stale_destination or overspent:
            self.s.queue = [t for t in self.s.queue if t.get("actor") != actor_id or t["type"] != "move_step"]
            self.s.queue.insert(0, dict(type="correction", actor=actor_id, position=list(a.position), label="Ruch przerwany. Ustaw figurkę na podświetlonym polu."))
            return
        if task["opportunities"] and not task.get("checked"):
            responders = [str(b.id) for b in self.enemies(a) if self.fighter(str(b.id)).reaction and self.weapons[str(b.id)].kind == "melee"
                          and distance(b.position, a.position) <= self.weapons[str(b.id)].range < distance(b.position, destination)
                          and str(b.id) not in f.hidden and line_of_sight_clear(self.board, b.position, a.position)]
            if responders:
                self.s.queue[0:0] = [*(dict(type="opportunity", actor=b, target=actor_id) for b in responders), dict(task, checked=True)]
                return
        previous_flanks = {str(b.id) for b in self.enemies(a) if self.flanking(actor_id, str(b.id))}
        self.update_actor(replace(a, position=destination))
        f.moved = True
        temporary = min(f.temporary_movement, task["cost"])
        f.temporary_movement -= temporary
        f.base_spent += task["cost"]-temporary
        if actor_id == "mira" and any(str(b.id) not in previous_flanks and self.flanking(actor_id, str(b.id)) for b in self.enemies(a)):
            self.offer_regeneration(actor_id, "Wejście na flankę własnym ruchem")

    def advance(self) -> None:
        if self.s.task:
            return
        while self.s.queue:
            task = self.s.queue.pop(0)
            kind = task["type"]
            if kind == "attack":
                self.attack_task(task)
            elif kind == "damage":
                self.damage_task(task)
            elif kind == "status":
                self.add_status(task["target"], task["status"], **task["extra"])
            elif kind == "move_step":
                self.move_step(task)
            elif kind == "passage_end":
                a = self.actor(task["actor"])
                if a.hp > 0 and not any(distance(a.position, b.position) == 1 for b in self.enemies(a)):
                    self.offer_regeneration(task["source"], "Pieśń przejścia wyprowadziła sojusznika z zagrożenia")
            elif kind == "escape":
                a = self.actor(task["actor"])
                if a.hp > 0 and a.position == point(task["destination"]):
                    outcome = EnemyOutcome(str(a.id), a.name, "escaped", self.s.round)
                    self.original = replace(self.original, enemy_ai=replace(self.original.enemy_ai, outcomes=(*self.original.enemy_ai.outcomes, outcome)))
                    self.note(f"{a.name} uciekł z walki.")
            elif kind == "save":
                a, effect = self.actor(task["target"]), task["effect"]
                if a.hp <= 0 or self.actor(effect["source"]).hp <= 0:
                    continue
                if effect.get("destination") and self.actor(effect["source"]).position != point(effect["destination"]):
                    continue
                disadvantage = str(a.id) == "mira" and bool(self.fighter(str(a.id)).hidden)
                origin = point(effect["origin"]) if effect.get("origin") is not None else self.actor(effect["source"]).position
                cover = (evaluate_cover_from_origin(self.board, origin, a, self.board_actors(), self.scene_objects)
                         if task["ability"] == "dexterity" else AttackPositioning())
                roll = self.dice_task(f"{a.name} · obrona", str(a.id), 1, 20, "save", dc=task["dc"], effect=effect,
                    modifier=self.ability(str(a.id), task["ability"])+self.bonus(str(a.id), "Oko")+(self.status(str(a.id), "bless") or {}).get("value", int(bool(self.status(str(a.id), "bless"))))-effect.get("save_penalty", 0)+cover.cover_bonus,
                    cover_bonus=cover.cover_bonus, cover_sources=list(cover.cover_sources),
                    mode="disadvantage" if disadvantage else "normal")
                if disadvantage:
                    roll["parts"].append(dict(count=1, sides=20, label="Druga k20"))
                self.s.queue.insert(0, roll)
            elif kind == "finish":
                self.finish()
            elif kind == "close_action":
                self.close_action()
            elif kind == "opportunity":
                a, b = self.actor(task["actor"]), self.actor(task["target"])
                if a.hp <= 0 or b.hp <= 0 or not self.fighter(str(a.id)).reaction:
                    continue
                if a.faction == Faction.ENEMY:
                    self.s.queue.insert(0, dict(type="attack", actor=str(a.id), target=str(b.id), power="opportunity", reaction_pending=True))
                else:
                    self.s.task = task
            elif kind == "relocate":
                if self.relocation_fields(task):
                    self.s.task = task
            elif kind == "recover":
                f = self.fighter(task["actor"])
                if f.regeneration_round != self.s.round and f.regeneration_reason and f.charges < 20:
                    self.s.task = task
                else:
                    f.regeneration_reason = ""
            else:
                self.s.task = task
            if self.s.task:
                self.s.phase = "task"
                dice = self.roll_dice()
                self.s.die_value = max(1, dice[0]["sides"]//2) if dice else 1
                return
        self.s.phase = "result" if self.s.action else "idle"

    def finish(self) -> None:
        action = self.s.action
        if not action or action["closed"]:
            return
        if action["actor"] == "nimra" and action["card"] and sum(self.actor(t).faction == Faction.ENEMY for t in action["harmed"]) >= 2:
            self.offer_regeneration("nimra", "Moc zraniła co najmniej dwóch wrogów")
        action["closed"] = True
        source = action["actor"]
        if self.is_relations and action["card"] and self.actor(source).hp > 0:
            modifiers = action.get("modifiers", {})
            if modifiers.get("self_ac_next_turn"):
                self.grant_ac(source, modifiers["self_ac_next_turn"], source, action["id"])
            if modifiers.get("self_temp_hp"):
                self.grant_pool(source, "temporary", modifiers["self_temp_hp"], source)
            if modifiers.get("next_attack_advantage"):
                self.add_status(source, "next_attack", **self.turn_duration(source))
            targets = self.area(action) if action["id"] == "preserve_life" else action["targets"]
            for target in targets:
                if self.actor(target).faction != Faction.ALLY or self.actor(target).hp <= 0:
                    continue
                if modifiers.get("target_temp_hp"):
                    self.grant_pool(target, "temporary", modifiers["target_temp_hp"], source)
                if modifiers.get("shield_pool"):
                    self.grant_pool(target, "prevention", modifiers["shield_pool"], source)
                if modifiers.get("target_ac_next_turn") and action["id"] != "arcane_shield":
                    self.grant_ac(target, modifiers["target_ac_next_turn"], source, action["id"])
            if modifiers.get("bonus_move") and action.get("successful") and not self.fighter(source).move_locked:
                self.s.queue.append(dict(type="relocate", target=source, source=source, radius=modifiers["bonus_move"], walk=True,
                                         opportunities=not modifiers.get("no_opportunity", False), label="Ruch po mocy", destination=None))
            if modifiers.get("adjacent_ally_heal_dice"):
                targets = [str(ally.id) for ally in self.allies(self.actor(source)) if str(ally.id) != source
                           and ally.hp > 0 and distance(ally.position, self.actor(source).position) == 1]
                if targets:
                    self.s.queue.append(dict(type="bonus_target", source=source, targets=targets,
                                             dice=deepcopy(modifiers["adjacent_ally_heal_dice"]),
                                             label="Żar odnowy · wybierz sojusznika", target=None))
        elif not self.is_relations:
            for source, targets in action["damage_groups"].items():
                radius = self.bonus(source, "Hak")
                if radius:
                    self.s.queue.extend(dict(type="relocate", target=t, source=source, radius=radius, label="Rezonans runy Hak", destination=None)
                        for t in targets if self.actor(t).hp > 0 and self.actor(t).faction != self.actor(source).faction and f"{source}:{t}" not in action["handled_hooks"])
        self.s.queue.append(dict(type="close_action"))

    def close_action(self) -> None:
        action = self.s.action
        if not action:
            return
        if self.is_relations and action["card"]:
            if action.get("resonance_applied"):
                return
            action["resonance_applied"] = True
            card = self.card(action["id"])
            before = action["resonance"]["memory_before"]
            if action["actor"] == "lorian" and before and action["resonance"]["transition"] == "continue" and before[-1]["contributor"] != "lorian":
                self.fighter("lorian").charges = min(20, self.fighter("lorian").charges+1)
                self.note("Zgrana drużyna: Lorian +1 ładunek.")
            if card.ends_resonance:
                self.end_chain("wyładowanie rozpatrzone w całości")
            else:
                self.add_rune(action["actor"], card.rune)
        elif not self.is_relations and action["card"] and action["mode"] == "base":
            if action["actor"] == "lorian" and action["had_chain"]:
                self.fighter("lorian").charges = min(20, self.fighter("lorian").charges+1)
                self.note("Zgrana drużyna: Lorian +1 ładunek.")
            self.end_chain("moc podstawowa rozpatrzona w całości")
        self.s.queue.extend(dict(type="recover", actor=key) for key, f in self.s.fighters.items()
                            if f.regeneration_reason and f.regeneration_round != self.s.round)

    def roll_dice(self) -> list[Task]:
        task = self.s.task
        return [dict(part, part_index=i) for i, part in enumerate(task["parts"]) for _ in range(part["count"])] if task and task["type"] == "roll" else []

    def confirm_enemy_roll(self, roll_die: Callable[[int], int]) -> bool:
        if not self.is_relations:
            return self._confirm_enemy_roll(roll_die)
        checkpoint = deepcopy(self.s), dict(self.actors), self.original
        try:
            return self._confirm_enemy_roll(roll_die)
        except Exception as exc:
            self.s, self.actors, self.original = checkpoint
            if isinstance(exc, (TypeError, ValueError)):
                return False
            raise

    def _confirm_enemy_roll(self, roll_die: Callable[[int], int]) -> bool:
        task = self.s.task
        if not task or task["type"] != "roll" or self.actor(task["actor"]).faction != Faction.ENEMY:
            return False
        rolls: list[Task] = []

        def resolve(roll: Task) -> None:
            dice = [[roll_die(part["sides"]) for _ in range(part["count"])] for part in roll["parts"]]
            if any(type(value) is not int or not 1 <= value <= part["sides"] for part, values in zip(roll["parts"], dice) for value in values):
                raise ValueError("Nieprawidłowy wynik kości przeciwnika.")
            values = list(map(sum, dice))
            natural, total, success = roll_result(roll, values)
            before = len(self.s.action["results"]) if self.s.action else 0
            self.resolve_roll(roll, values, natural, total, success)
            rolls.append(dict(label=roll["label"], outcome=roll["outcome"], dice=dice, total=total, success=success,
                              modifier=roll.get("modifier", 0), dc=roll.get("dc"),
                              messages=self.s.action["results"][before:] if self.s.action else []))

        self.s.task = None
        if task.get("reaction_pending"):
            self.fighter(task["actor"]).reaction = False
        resolve(task)
        if task["outcome"] == "attack" and self.s.queue and self.s.queue[0]["type"] == "damage" and self.s.queue[0]["actor"] == task["actor"]:
            self.damage_task(self.s.queue.pop(0))
            if self.s.queue and self.s.queue[0]["type"] == "roll" and self.s.queue[0].get("outcome") == "damage":
                resolve(self.s.queue.pop(0))
        self.s.task = dict(type="enemy-result", actor=task["actor"], target=task.get("target"), power=task.get("power"), label=task["label"], rolls=rolls)
        self.s.phase = "task"
        return True

    def submit_die(self, value: int, index: int) -> bool:
        task, dice = self.s.task, self.roll_dice()
        if not task or task["type"] != "roll" or self.actor(task["actor"]).faction == Faction.ENEMY:
            return False
        confirmed = task.get("dice_results", [])
        if type(value) is not int or type(index) is not int or index != len(confirmed) or index >= len(dice) or not 1 <= value <= dice[index]["sides"]:
            return False
        task["dice_results"] = [*confirmed, value]
        if len(task["dice_results"]) < len(dice):
            self.s.die_value = max(1, dice[len(task["dice_results"])]["sides"]//2)
            return True
        totals = [0]*len(task["parts"])
        for die, result in zip(dice, task["dice_results"]):
            totals[die["part_index"]] += result
        self.s.task = None
        natural, total, success = roll_result(task, totals)
        if natural is not None and hymn_source(self.actor(task["actor"])):
            self.s.task = dict(type="hymn", actor=task["actor"], roll=task, values=totals, natural=natural, total=total, success=success)
        else:
            self.resolve_roll(task, totals, natural, total, success)
            self.advance()
        return True

    def decide_hymn(self, use: bool) -> bool:
        task = self.s.task
        if not task or task["type"] != "hymn":
            return False
        self.s.task = None
        if use:
            a = self.actor(task["actor"])
            task["source"] = hymn_source(a) if hymn_source(a) in self.actors else ""
            sides = self.hymn_sides(str(a.id))
            self.update_actor(replace(a, features=tuple(f for f in a.features if f.feature_id != "resonance_hymn")))
            self.fighter(str(a.id)).statuses = [status for status in self.fighter(str(a.id)).statuses if status["type"] != "hymn"]
            self.s.queue.insert(0, self.dice_task("Hymn odwagi", str(a.id), 1, sides, "hymn", pending=task))
        else:
            self.resolve_roll(task["roll"], task["values"], task["natural"], task["total"], task["success"])
        self.advance()
        return True

    def resolve_roll(self, task: Task, values: list[int], natural: int | None, total: int, success: bool) -> None:
        actor_id, outcome = task["actor"], task["outcome"]
        a, f, q = self.actor(actor_id), self.fighter(actor_id), self.s.queue
        target_id = task.get("target", "")
        if outcome == "hymn":
            p = task["pending"]
            result = p["total"]+values[0]
            ok = (p["natural"] == 20 or (p["natural"] != 1 and result >= p["roll"]["dc"])) if p["roll"]["outcome"] == "attack" else result >= p["roll"].get("dc", 0)
            if ok and p["roll"]["outcome"] == "attack":
                self.offer_regeneration(p["source"], "Sojusznik trafił, wykorzystując Hymn")
            self.resolve_roll(p["roll"], p["values"], p["natural"], result, ok)
            return
        result_text = f" / ST {task['dc']} · {'sukces' if success else 'porażka'}" if "dc" in task and natural is not None else ""
        self.note(f"{task['label']}: {total}{result_text}.")
        if outcome == "heal":
            self.heal(target_id, total)
        elif outcome == "heal_group":
            for target in task["targets"]:
                self.heal(target, total, actor_id, task.get("power", False))
        elif outcome in {"charges", "regenerate"}:
            recipient = self.fighter(target_id or actor_id)
            recipient.charges = min(20, recipient.charges+max(0, total))
            if outcome == "regenerate":
                recipient.regeneration_reason = ""
        elif outcome == "hide":
            previous = f.hidden
            f.hide_total = total
            f.hidden = [str(b.id) for b in self.enemies(a) if total > passive_skill_score(b, "perception")-task.get("perception_penalty", 0)]
            if f.hidden and self.s.action:
                self.s.action["successful"] = True
            if any(key not in previous for key in f.hidden):
                self.offer_regeneration(actor_id, "Ukrycie przed nowym wrogiem")
        elif outcome == "contest":
            source = task["source"]
            modifiers = self.action_modifiers(source, "shield_bash")
            roll = self.dice_task("Impuls egidy · test Siły", source, 1, 20, "bash", target=actor_id,
                                  modifier=self.ability(source, "strength")+self.bonus(source, "Oko"), dc=total+1,
                                  mode="advantage" if modifiers.get("check_advantage") else "normal")
            if modifiers.get("check_advantage"):
                roll["parts"].append(dict(count=1, sides=20, label="Druga k20"))
            q.insert(0, roll)
        elif outcome == "bash" and success:
            if self.s.action:
                self.s.action["successful"] = True
            q.insert(0, dict(type="damage", actor=actor_id, target=target_id, power="shield_bash", components=[dict(count=1, sides=6,
                             modifier=self.ability(actor_id, "strength"), damage_type="bludgeoning", label="Impuls egidy")]))
        elif outcome == "area_damage":
            q[0:0] = [self.save_task(t, task["save_ability"], task["dc"], dict(kind="damage", value=total, damage_type=task["damage_type"],
                       half=task["half"], fear=task["fear"], source=actor_id, save_penalty=task.get("save_penalty", 0),
                       origin=task.get("origin", list(a.position)),
                       move_penalty=task.get("move_penalty", 0))) for t in task["targets"]]
        elif outcome == "enemy_spell":
            weapon = ChargeWeapon(**task["weapon"])
            q.insert(0, self.save_task(target_id, weapon.spell_save_ability, weapon.spell_save_dc,
                dict(kind="spell_damage", source=actor_id, components=damage_components(task, values), half=weapon.spell_save_half)))
        elif outcome == "save":
            effect = task["effect"]
            if effect["kind"] == "spell_damage":
                if not success or effect["half"]:
                    components = [dict(p, value=p["value"]//(2 if success else 1)) for p in effect["components"]]
                    self.damage(actor_id, components, effect["source"])
            elif effect["kind"] == "damage":
                if not success or effect["half"]:
                    q.insert(0, dict(type="damage", actor=effect["source"], target=actor_id, divisor=2 if success else 1,
                        components=[dict(value=effect["value"], count=0, damage_type=effect["damage_type"], label="Moc")]))
                if not success and effect["fear"]:
                    self.add_status(actor_id, "fear", until_end=actor_id, turn=f.turn+1)
            elif not success and effect["kind"] not in a.condition_immunities:
                self.add_status(actor_id, effect["kind"], until_end=actor_id, turn=f.turn+1)
            if not success and effect.get("move_penalty"):
                self.add_status(actor_id, "move_penalty", value=effect["move_penalty"], until_end=actor_id, turn=f.turn+1)
        elif outcome == "attack":
            if success:
                weapon = ChargeWeapon(**task["weapon"])
                critical = natural == 20
                parts = deepcopy(list(weapon.components))
                for index, part in enumerate(parts):
                    if critical and part.get("count"):
                        part["count"] = part.get("count", 0)+2 if actor_id == "brakka" and index == 0 and weapon.source_type == "weapon" else part.get("count", 0)*2
                def extra(sides: int, label: str, damage_type: str = parts[0]["damage_type"]) -> None:
                    parts.append(dict(count=2 if critical else 1, sides=sides, modifier=0, damage_type=damage_type, label=label))
                if task["power"] == "breaking_strike":
                    extra(6, "Ostrze przełamania", "magic")
                modifiers = self.action_modifiers(actor_id, task["power"])
                for die in modifiers.get("attack_bonus_dice", []):
                    parts.append(dict(count=die["count"]*(2 if critical else 1), sides=die["sides"], modifier=die.get("modifier", 0),
                                      damage_type=parts[0]["damage_type"] if die["damage_type"] == "weapon" else die["damage_type"],
                                      label=die.get("label", "Rezonans · moc")))
                if self.status(actor_id, "rage") and task["melee"] and weapon.source_type == "weapon":
                    extra(6, "Runiczny szał")
                if f.mark == target_id and weapon.source_type == "weapon":
                    extra(4, "Piętno łowcy")
                if actor_id == "mira" and weapon.source_type == "weapon" and actor_id == str(self.active.id) and not f.sneak_used and (task["hidden"] or self.flanking(actor_id, target_id)):
                    extra(6, "Cios z zaskoczenia")
                    f.sneak_used = True
                if actor_id == "brakka" and weapon.source_type == "weapon" and task["melee"] and target_id not in f.start_adjacent:
                    self.offer_regeneration(actor_id, "Trafienie nowego sąsiada bronią wręcz")
                if actor_id == "erynd" and not task["melee"] and (f.mark == target_id or (not f.moved and distance(a.position, self.actor(target_id).position) >= 4)):
                    self.offer_regeneration(actor_id, "Cel oznaczony lub daleki strzał bez ruchu")
                q.insert(0, dict(type="damage", actor=actor_id, target=target_id, components=parts, critical=critical, power=task["power"], hit=True, hidden=task["hidden"], weapon=task["weapon"], life_drain=task.get("life_drain", False)))
            elif a.faction == Faction.ENEMY:
                if target_id == "garran" or self.shielded(target_id):
                    self.offer_regeneration("garran", "Wróg chybił Garrana / Żywą tarczę")
                blessing = self.status(target_id, "bless")
                if blessing:
                    self.offer_regeneration(blessing["source"], "Wróg chybił sojusznika z Pieczęcią łaski")
            f.hidden = []
        elif outcome == "damage":
            loss = self.damage(target_id, damage_components(task, values), actor_id, critical=task.get("critical", False))
            if task.get("life_drain") and loss["received"] >= 2 and self.actor(actor_id).hp > 0:
                self.heal(actor_id, loss["received"]//2)
            target = self.actor(target_id)
            if task.get("hit") and target.hp > 0:
                weapon = ChargeWeapon(**task["weapon"])
                eligible = f.base_spent >= weapon.minimum_movement and (not weapon.requires_adjacent_ally or any(
                    ally.id != a.id and ally.hp > 0 and distance(ally.position, target.position) == 1 for ally in self.allies(a)))
                if weapon.on_hit_condition and eligible:
                    if weapon.save_ability:
                        q.insert(0, self.save_task(target_id, weapon.save_ability, weapon.save_dc, dict(kind=weapon.on_hit_condition, source=actor_id)))
                    elif weapon.on_hit_condition not in target.condition_immunities:
                        self.add_status(target_id, weapon.on_hit_condition, until_end=target_id, turn=self.fighter(target_id).turn+1)
                if task["power"] == "powerful_strike":
                    self.add_status(target_id, "broken", until_start=actor_id, turn=f.turn+1)
                if task["power"] == "hamstring_cut":
                    self.add_status(target_id, "slow", until_end=target_id, turn=self.fighter(target_id).turn+1)
                    if task.get("hidden"):
                        self.add_status(target_id, "round_root", round=self.s.round+1)
                if task["power"] == "anchoring_arrow":
                    self.add_status(target_id, "root", until_end=target_id, turn=self.fighter(target_id).turn+1)
                modifiers = self.action_modifiers(actor_id, task["power"])
                if modifiers.get("enemy_move_penalty"):
                    self.add_status(target_id, "move_penalty", value=modifiers["enemy_move_penalty"],
                                    until_end=target_id, turn=self.fighter(target_id).turn+1)
            if task.get("power") == "shield_bash" and target.hp > 0:
                q.insert(0, dict(type="relocate", target=target_id, source=actor_id, radius=1, label="Impuls egidy", destination=None))
            if task.get("power") == "opportunity" and loss["received"] > 0 and target.hp > 0 and self.bonus(actor_id, "Hak"):
                if self.s.action:
                    self.s.action["handled_hooks"].append(f"{actor_id}:{target_id}")
                q.insert(0, dict(type="relocate", target=target_id, source=actor_id, radius=self.bonus(actor_id, "Hak"), label="Rezonans runy Hak", destination=None))
        elif outcome == "death_save":
            success = success and natural != 1
            if natural == 20:
                self.heal(actor_id, 1)
            else:
                successes = min(3, a.death_saves.successes+int(success))
                failures = min(3, a.death_saves.failures+(0 if success else 2 if natural == 1 else 1))
                self.update_actor(replace(a, death_saves=DeathSaveState(successes, failures, successes == 3, failures == 3)))

    def recover(self, use: bool) -> bool:
        task = self.s.task
        if not task or task["type"] != "recover":
            return False
        f = self.fighter(task["actor"])
        self.s.task = None
        if use and f.charges < 20 and f.regeneration_round != self.s.round:
            f.regeneration_round = self.s.round
            self.s.queue.insert(0, self.dice_task("Odzysk klasowy", task["actor"], 1, 4, "regenerate"))
        f.regeneration_reason = ""
        self.advance()
        return True

    def opportunity(self, use: bool) -> bool:
        task = self.s.task
        if not task or task["type"] != "opportunity":
            return False
        self.s.task = None
        if use and self.fighter(task["actor"]).reaction:
            self.fighter(task["actor"]).reaction = False
            self.s.queue.insert(0, dict(type="attack", actor=task["actor"], target=task["target"], power="opportunity"))
        self.advance()
        return True

    def confirm_relocation(self) -> bool:
        task = self.s.task
        if not task or task["type"] != "relocate" or task["destination"] is None or point(task["destination"]) not in self.relocation_fields(task):
            return False
        a = self.actor(task["target"])
        was_adjacent = any(distance(a.position, b.position) == 1 for b in self.enemies(a))
        if task.get("walk"):
            path = self.paths(str(a.id), task["radius"]).get(point(task["destination"]))
            if path is None:
                return False
            previous = list(a.position)
            steps = []
            for destination in path.cells:
                steps.append(dict(type="move_step", actor=str(a.id), origin=previous, position=list(destination), cost=0,
                                  opportunities=task.get("opportunities", False)))
                previous = list(destination)
            if task["label"] == "Pieśń przejścia" and was_adjacent:
                steps.append(dict(type="passage_end", actor=str(a.id), source=task["source"]))
            self.s.queue[0:0] = steps
        else:
            self.update_actor(replace(a, position=point(task["destination"])))
        self.note(f"{task['label']}: przestawiono {a.name}.")
        self.s.task = None
        self.advance()
        return True

    def confirm_bonus_target(self) -> bool:
        task = self.s.task
        if not task or task["type"] != "bonus_target" or not task.get("target") or task["target"] not in task["targets"]:
            return False
        source, target = task["source"], task["target"]
        if self.actor(target).faction != Faction.ALLY or self.actor(target).hp <= 0 or self.actor(source).hp <= 0 or distance(self.actor(source).position, self.actor(target).position) != 1:
            return False
        self.s.task = None
        self.s.queue.insert(0, dict(type="roll", label="Żar odnowy · leczenie sojusznika", actor=source,
                                  parts=[dict(die, label="Leczenie sojusznika") for die in task["dice"]],
                                  outcome="heal_group", targets=[target], power=True))
        self.advance()
        return True

    def skip_bonus_target(self) -> bool:
        if not self.s.task or self.s.task["type"] != "bonus_target":
            return False
        self.s.task = None
        self.advance()
        return True

    def acknowledge(self) -> bool:
        if self.s.task and self.s.task["type"] in {"enemy-result", "correction", "enemy-move"}:
            self.s.task = None
            self.advance()
            return True
        if self.s.phase != "result":
            return False
        self.s.action = None
        self.s.phase = "idle"
        if not any(a.hp > 0 and a.faction == Faction.ALLY for a in self.actors.values()) or not any(a.hp > 0 and a.faction == Faction.ENEMY and str(a.id) not in self.original.enemy_ai.escaped_actor_ids for a in self.actors.values()):
            self.end_chain("koniec walki")
            self.s.phase = "finished"
        return True

    def prepare_enemy_turn(self, *, target_id: str = "", destination: Coordinate | None = None, weapons: tuple[ChargeWeapon, ...] = (), intent: str = "", escape_target: Coordinate | None = None, heal_target: str | None = None, life_drain: bool = False) -> bool:
        """Adapt an authored AI intention to legal charge-profile movement."""
        if self.active.faction != Faction.ENEMY or self.s.phase != "idle":
            return False
        a, actor_id = self.active, str(self.active.id)
        visible = [b for b in self.enemies(a) if actor_id not in self.fighter(str(b.id)).hidden]
        target = next((b for b in visible if str(b.id) == target_id), None)
        if target is None and visible:
            target = min(visible, key=lambda b: (distance(a.position, b.position), b.hp, str(b.id)))
        paths = self.paths(actor_id, self.movement())
        weapon = weapons[0] if weapons else self.weapons[actor_id]
        reachable = [(p, path) for p, path in paths.items() if target and distance(p, target.position) <= weapon.range and line_of_sight_clear(self.board, p, target.position)]
        if destination not in paths:
            destination = None
        defensive = intent.startswith(("escape", "flee", "retreat", "regroup", "guard", "hold", "heal", "cornered"))
        if reachable and not defensive:
            destination, path = min(reachable, key=lambda pair: (pair[1].cost, len(pair[1].cells), pair[0]))
        elif defensive:
            destination = destination or a.position
            path = paths.get(destination, ChargePath((), ()))
        elif paths and target:
            destination = destination or min(paths, key=lambda p: (distance(p, target.position), paths[p].cost, p))
            path = paths[destination]
        else:
            destination, path = a.position, ChargePath((), ())
        self.s.serial += 1
        self.s.action = dict(id="enemy", actor=actor_id, serial=self.s.serial, card=False, mode="base", closed=False,
                             had_chain=bool(self.s.chain), harmed=[], damage_groups={}, handled_hooks=[], results=[])
        self.fighter().ordinary = False
        if path.cells:
            self.s.queue.append(dict(type="enemy-move", actor=actor_id, path=path.as_payload(), destination=list(destination), label=f"Przesuń {a.name} na wskazane pole i zatwierdź."))
            previous = list(a.position)
            for p, cost in zip(path.cells, path.costs):
                self.s.queue.append(dict(type="move_step", actor=actor_id, origin=previous, position=list(p), cost=cost, opportunities=True))
                previous = list(p)
        if escape_target is not None and destination == escape_target:
            self.s.queue.append(dict(type="escape", actor=actor_id, destination=list(destination)))
        elif target and not defensive:
            for source in weapons or (weapon,):
                self.s.queue.append(dict(type="attack", actor=actor_id, target=str(target.id), power="attack", weapon=asdict(source), life_drain=life_drain))
        elif not defensive:
            # An unseen opponent can be found, but searching consumes the attack.
            for b in self.enemies(a):
                if actor_id in self.fighter(str(b.id)).hidden and passive_skill_score(a, "perception") >= self.fighter(str(b.id)).hide_total:
                    self.fighter(str(b.id)).hidden.remove(actor_id)
            self.note(f"{a.name} szuka ukrytych przeciwników.")
        if heal_target in self.actors and 0 < self.actor(heal_target).hp < self.actor(heal_target).max_hp:
            self.s.queue.append(self.dice_task("Odnowa sojusznika", actor_id, 1, 6, "heal", target=heal_target, modifier=2))
        self.s.queue.append(dict(type="finish"))
        self.advance()
        return True

    def combat_state(self) -> CombatState:
        actors = tuple(self.actors[str(a.id)] for a in self.original.actors)
        order = replace(self.original.initiative_order,
                        entries=tuple(replace(e, actor=self.actor(str(e.actor.id))) for e in self.original.initiative_order.entries),
                        current_index=self.s.index, round_number=self.s.round)
        f = self.fighter()
        finished = self.s.phase == "finished"
        winner = None
        if finished:
            winner = Faction.ALLY if any(a.hp > 0 and a.faction == Faction.ALLY for a in actors) else Faction.ENEMY
        state = replace(self.original, actors=actors, initiative_order=order, resonance=deepcopy(self.s),
                       status=CombatStatus.FINISHED if finished else CombatStatus.ACTIVE, winner=winner,
                       spent_reaction_actor_ids=frozenset(ActorId(key) for key, value in self.s.fighters.items() if not value.reaction),
                       turn_action=replace(self.original.turn_action, action_use=ActionUse.ACTION_AVAILABLE if f.ordinary else ActionUse.ACTION_USED,
                           rune_special_used=not f.special, reaction_available=f.reaction, movement_used_feet=f.base_spent*5,
                           extra_movement_feet=f.temporary_movement*5, movement_action_used=f.move_locked))
        return finalize_ammunition_recovery(state, winner) if finished else state
