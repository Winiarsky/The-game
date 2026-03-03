from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from GameObjects.events.magic.magic_utils import grid_distance_feet
from GameObjects.interactions_mixin import prompt_for_roll
from combat import effective_ac
from combat.hp_engine import apply_damage as hp_apply_damage
from combat.hp_engine import current_hp as hp_current_hp
from combat.hp_engine import heal as hp_heal
from damage_types import DamageType
from statuses import clear_grabbed_effects, clear_restrained_effects
from statuses.enfeebled import EnfeebledStatus

from .base import Reaction


def _is_champion(actor) -> bool:
    if actor is None:
        return False
    has_status = getattr(actor, "has_status", None)
    if callable(has_status):
        try:
            if bool(has_status("champion")):
                return True
        except Exception:
            pass
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) == "champion":
            return True
    class_name = str(getattr(actor, "class_name", "") or "").strip().lower()
    return class_name == "champion"


def _source_id(actor) -> str | None:
    if actor is None:
        return None
    return getattr(actor, "object_id", None) or getattr(actor, "name", None) or str(actor)


def _champion_setup(actor) -> dict[str, Any]:
    if actor is None:
        return {}
    getter = getattr(actor, "get_status_data", None)
    if callable(getter):
        setup = getter("champion", "champion_setup", {})
        if isinstance(setup, dict):
            return dict(setup)
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) != "champion":
            continue
        data = getattr(status, "data", None) or {}
        setup = data.get("champion_setup")
        if isinstance(setup, dict):
            return dict(setup)
    return {}


def _event_damage(event: dict[str, Any]) -> int:
    raw_damage = event.get("damage")
    try:
        dmg = int(raw_damage)
    except Exception:
        dmg = 0
    if dmg > 0:
        return dmg
    components = event.get("damage_components") or []
    total = 0
    if isinstance(components, list):
        for item in components:
            try:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    total += max(0, int(item[1]))
            except Exception:
                continue
    return max(0, int(total))


def _heal_prevented_damage(target, amount: int) -> None:
    if target is None or amount <= 0:
        return
    healer = getattr(target, "heal", None)
    if callable(healer):
        try:
            healer(amount)
            return
        except Exception:
            pass
    try:
        hp_heal(target, amount, source="champion_reaction:prevented")
    except Exception:
        pass


def _distance_feet(a: tuple[int, int] | None, b: tuple[int, int] | None) -> int:
    if a is None or b is None:
        return 10**9
    try:
        return int(grid_distance_feet(a, b))
    except Exception:
        return 10**9


def _is_alive(actor) -> bool:
    if actor is None:
        return False
    if getattr(actor, "position", None) is None:
        return False
    try:
        if bool(getattr(actor, "has_status", lambda *_a, **_k: False)("dead")):
            return False
    except Exception:
        pass
    hp = hp_current_hp(actor)
    if hp is None:
        return True
    return int(hp) > 0


def _same_side(game, first, second) -> bool | None:
    if game is None:
        return None
    heroes = list(getattr(game, "heroes", []))
    enemies = list(getattr(game, "enemies", []))
    if first in heroes and second in heroes:
        return True
    if first in enemies and second in enemies:
        return True
    if first in heroes and second in enemies:
        return False
    if first in enemies and second in heroes:
        return False
    return None


def _is_hero(game, actor) -> bool:
    return actor in list(getattr(game, "heroes", []))


def _bresenham_cells(a: tuple[int, int], b: tuple[int, int]) -> list[tuple[int, int]]:
    x0, y0 = a
    x1, y1 = b
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    out = [(x0, y0)]
    while (x0, y0) != (x1, y1):
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
        out.append((x0, y0))
    return out


def _line_of_effect_clear(game, source_pos: tuple[int, int] | None, target_pos: tuple[int, int] | None) -> bool:
    if source_pos is None or target_pos is None:
        return False
    board = getattr(game, "board", None) if game is not None else None
    if board is None or not hasattr(board, "is_blocked"):
        return True
    if source_pos == target_pos:
        return True
    try:
        points = _bresenham_cells(source_pos, target_pos)
    except Exception:
        return True
    for idx in range(len(points) - 1):
        cur = points[idx]
        nxt = points[idx + 1]
        try:
            if bool(board.is_blocked(cur, nxt)):
                return False
        except Exception:
            pass
        edge_between = getattr(board, "edge_interactables_between", None)
        if callable(edge_between):
            try:
                for edge_obj in edge_between(cur, nxt):
                    blocks_passage = getattr(edge_obj, "blocks_passage", None)
                    if callable(blocks_passage) and blocks_passage(cur, nxt):
                        return False
            except Exception:
                continue
    return True


def _paladin_retributive_strike(champion, attacker, game) -> None:
    source_pos = getattr(champion, "position", None)
    target_pos = getattr(attacker, "position", None)
    reach = max(1, int(getattr(champion, "reach", 1) or 1))
    if _distance_feet(source_pos, target_pos) > reach * 5:
        try:
            game.ui_log("Retributive Strike: agresor poza zasiegiem kontrataku.")
        except Exception:
            pass
        return
    attack_bonus = int(getattr(champion, "attack_bonus", 0) or 0)
    roll = prompt_for_roll(
        "Retributive Strike: rzut ataku (k20).",
        layout="test",
        answer_placeholder="Wynik k20",
    )
    total = int(roll) + attack_bonus
    target_ac = int(effective_ac(attacker))
    if total < target_ac:
        try:
            game.ui_log(f"Retributive Strike: pudlo ({total} vs AC {target_ac}).")
        except Exception:
            pass
        return
    damage = prompt_for_roll(
        "Retributive Strike: obrazenia.",
        layout="damage",
        answer_placeholder="Suma obrazen",
    )
    defeated = False
    try:
        apply = getattr(attacker, "apply_damage", None)
        if callable(apply):
            _, defeated = apply(max(0, int(damage)), DamageType.NORMAL.value)
        else:
            info = hp_apply_damage(
                attacker,
                max(0, int(damage)),
                DamageType.NORMAL.value,
                source="champion_reaction",
            )
            defeated = bool(info.get("defeated", False))
    except Exception:
        defeated = False
    try:
        game.ui_log(f"Retributive Strike trafia za {int(damage)} obrazen.")
    except Exception:
        pass
    if defeated:
        try:
            pos = getattr(attacker, "position", None)
            if pos is not None:
                game.board.remove(pos)
        except Exception:
            pass
        try:
            game.enemies.remove(attacker)
        except Exception:
            pass
        try:
            attacker.position = None
        except Exception:
            pass


def _redeemer_effect(champion, attacker, game, *, enfeebled_value: int) -> None:
    adder = getattr(attacker, "add_status", None)
    if not callable(adder):
        return
    try:
        adder(
            EnfeebledStatus(
                value=max(1, int(enfeebled_value)),
                source="champion_reaction",
                # Wygasa po następnej turze agresora:
                # 1) start jego kolejnej tury: 2 -> 1 (efekt trwa),
                # 2) start kolejnej po niej: 1 -> 0 (efekt znika).
                source_id=_source_id(attacker),
                source_turns_left=2,
            )
        )
        game.ui_log(
            f"Glimpse of Redemption: agresor otrzymuje Enfeebled {max(1, int(enfeebled_value))} na 1 ture."
        )
    except Exception:
        pass


def _choose_liberator_step(game, target) -> bool:
    if game is None:
        return True
    if not _is_hero(game, target):
        return True
    ui = getattr(game, "ui", None)
    if ui is not None and getattr(ui, "enabled", False):
        try:
            choice = ui.prompt_choice(
                f"Liberating Step: czy {getattr(target, 'name', 'cel')} ma wykonac Step?",
                choices=["tak", "nie"],
                source="champion_liberator_step",
            )
            return str(choice or "").strip().lower().startswith("t")
        except Exception:
            return True
    return True


def _choose_redeemer_outcome(game, attacker) -> str:
    if game is None:
        return "strike"
    if not _is_hero(game, attacker):
        return "strike"

    ui = getattr(game, "ui", None)
    if ui is not None and getattr(ui, "enabled", False):
        try:
            choice = ui.prompt_choice(
                "Glimpse of Redemption: wybierz wynik ataku.",
                choices=["powstrzymaj atak", "zadaj obrazenia i otrzymaj enfeebled 2"],
                source="champion_redeemer_choice",
            )
            raw = str(choice or "").strip().lower()
            if raw.startswith("powstrzymaj") or raw.startswith("wstrzymaj"):
                return "forgo"
            return "strike"
        except Exception:
            pass
    return "strike"


def _step_candidates(game, source_pos: tuple[int, int]) -> list[tuple[int, int]]:
    board = getattr(game, "board", None)
    if board is None:
        return []
    getter = getattr(board, "get_neighbors", None)
    if callable(getter):
        try:
            neighbors = list(getter(source_pos, include_position=False, diagonal=True) or [])
        except Exception:
            neighbors = []
    else:
        x, y = source_pos
        neighbors = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                neighbors.append((x + dx, y + dy))
    out: list[tuple[int, int]] = []
    for candidate in neighbors:
        if candidate == source_pos:
            continue
        in_bounds = getattr(board, "in_bounds", None)
        if callable(in_bounds):
            try:
                if not bool(in_bounds(candidate)):
                    continue
            except Exception:
                continue
        is_blocked = getattr(board, "is_blocked", None)
        if callable(is_blocked):
            try:
                if bool(is_blocked(source_pos, candidate)):
                    continue
            except Exception:
                pass
        edge_between = getattr(board, "edge_interactables_between", None)
        if callable(edge_between):
            try:
                blocked_by_edge = False
                for edge_obj in edge_between(source_pos, candidate):
                    blocks_passage = getattr(edge_obj, "blocks_passage", None)
                    if callable(blocks_passage) and blocks_passage(source_pos, candidate):
                        blocked_by_edge = True
                        break
                if blocked_by_edge:
                    continue
            except Exception:
                pass
        can_enter = getattr(board, "can_enter", None)
        if callable(can_enter):
            try:
                if not bool(can_enter(candidate, allow_occupied=False)):
                    continue
            except Exception:
                continue
        out.append(candidate)
    return out


def _attempt_liberating_step(target, attacker, game) -> bool:
    if not _choose_liberator_step(game, target):
        try:
            game.ui_log(f"Liberating Step: {getattr(target, 'name', 'Cel')} rezygnuje ze Step.")
        except Exception:
            pass
        return False
    source_pos = getattr(target, "position", None)
    attacker_pos = getattr(attacker, "position", None)
    if source_pos is None:
        return False
    candidates = _step_candidates(game, source_pos)
    if not candidates:
        return False
    if attacker_pos is not None:
        candidates.sort(
            key=lambda pos: (_distance_feet(pos, attacker_pos), -pos[0], -pos[1]),
            reverse=True,
        )
    else:
        candidates.sort()
    destination = candidates[0]
    board = getattr(game, "board", None)
    moved = False
    mover = getattr(board, "move", None) if board is not None else None
    if callable(mover):
        try:
            mover(source_pos, destination)
            moved = True
        except Exception:
            moved = False
    if not moved:
        try:
            setattr(target, "position", destination)
            moved = True
        except Exception:
            moved = False
    else:
        # fallback dla prostych stubów planszy, które nie aktualizują obiektu aktora
        if getattr(target, "position", None) == source_pos:
            try:
                setattr(target, "position", destination)
            except Exception:
                pass
    if moved:
        try:
            game.ui_log(
                f"Liberating Step: {getattr(target, 'name', 'Cel')} wykonuje Step na {destination}."
            )
        except Exception:
            pass
    return moved


def _liberator_effect(target, attacker, game) -> None:
    removed_any = False
    remover = getattr(target, "remove_status", None)
    if callable(remover):
        try:
            removed_any = bool(remover("grabbed")) or removed_any
        except Exception:
            pass
        try:
            removed_any = bool(remover("restrained")) or removed_any
        except Exception:
            pass
        try:
            removed_any = bool(remover("immobilized")) or removed_any
        except Exception:
            pass
    try:
        clear_grabbed_effects(target)
    except Exception:
        pass
    try:
        clear_restrained_effects(target)
    except Exception:
        pass
    if removed_any:
        try:
            game.ui_log("Liberating Step: usunieto Grabbed/Restrained/Immobilized z chronionego celu.")
        except Exception:
            pass
    _attempt_liberating_step(target, attacker, game)


class ChampionCauseStrategy(Protocol):
    cause_id: str

    def reason(self) -> str: ...

    def resolve_prevention(self, champion, attacker, target, game, *, damage: int, base_prevented: int) -> tuple[int, dict[str, Any]]: ...

    def apply_secondary(self, champion, attacker, target, game, *, details: dict[str, Any]) -> None: ...


@dataclass(frozen=True)
class _PaladinStrategy:
    cause_id: str = "paladin"

    def reason(self) -> str:
        return "Retributive Strike"

    def resolve_prevention(self, champion, attacker, target, game, *, damage: int, base_prevented: int) -> tuple[int, dict[str, Any]]:
        _ = champion
        _ = attacker
        _ = target
        _ = game
        _ = damage
        return base_prevented, {}

    def apply_secondary(self, champion, attacker, target, game, *, details: dict[str, Any]) -> None:
        _ = details
        _ = target
        _paladin_retributive_strike(champion, attacker, game)


@dataclass(frozen=True)
class _RedeemerStrategy:
    cause_id: str = "redeemer"

    def reason(self) -> str:
        return "Glimpse of Redemption"

    def resolve_prevention(self, champion, attacker, target, game, *, damage: int, base_prevented: int) -> tuple[int, dict[str, Any]]:
        _ = champion
        _ = target
        outcome = _choose_redeemer_outcome(game, attacker)
        if outcome == "forgo":
            return damage, {"enfeebled_value": 0, "outcome": "forgo"}
        return base_prevented, {"enfeebled_value": 2, "outcome": "strike"}

    def apply_secondary(self, champion, attacker, target, game, *, details: dict[str, Any]) -> None:
        _ = target
        enfeebled_value = int(details.get("enfeebled_value", 0) or 0)
        if enfeebled_value > 0:
            _redeemer_effect(champion, attacker, game, enfeebled_value=enfeebled_value)


@dataclass(frozen=True)
class _LiberatorStrategy:
    cause_id: str = "liberator"

    def reason(self) -> str:
        return "Liberating Step"

    def resolve_prevention(self, champion, attacker, target, game, *, damage: int, base_prevented: int) -> tuple[int, dict[str, Any]]:
        _ = champion
        _ = attacker
        _ = target
        _ = game
        _ = damage
        return base_prevented, {}

    def apply_secondary(self, champion, attacker, target, game, *, details: dict[str, Any]) -> None:
        _ = champion
        _ = details
        _liberator_effect(target, attacker, game)


CAUSE_STRATEGIES: dict[str, ChampionCauseStrategy] = {
    "paladin": _PaladinStrategy(),
    "redeemer": _RedeemerStrategy(),
    "liberator": _LiberatorStrategy(),
}


@dataclass
class ChampionReaction(Reaction):
    id: str = "champion_reaction"
    label: str = "Champion's Reaction"
    priority: int = 30
    action_cost: int = 1
    requires_reach: bool = False
    blocks_range_attacker: bool = False
    protect_range_feet: int = 15

    def _strategy(self, actor) -> ChampionCauseStrategy:
        setup = _champion_setup(actor)
        cause = str(setup.get("cause", "paladin") or "paladin").strip().lower()
        return CAUSE_STRATEGIES.get(cause, CAUSE_STRATEGIES["paladin"])

    def triggers(self, actor, event: dict[str, Any]) -> bool:
        if not _is_champion(actor):
            return False
        attacker = event.get("actor")
        target = event.get("target")
        if attacker is None or target is None:
            return False
        if attacker is actor or target is actor:
            return False
        if not _is_alive(attacker) or not _is_alive(target):
            return False
        game = event.get("game")
        if game is not None:
            side_actor_target = _same_side(game, actor, target)
            side_actor_attacker = _same_side(game, actor, attacker)
            if side_actor_target is False:
                return False
            if side_actor_attacker is not False:
                return False
        if _event_damage(event) <= 0:
            return False
        actor_pos = getattr(actor, "position", None)
        target_pos = getattr(target, "position", None)
        if _distance_feet(actor_pos, target_pos) > self.protect_range_feet:
            return False
        if game is not None and not _line_of_effect_clear(game, actor_pos, target_pos):
            return False
        return True

    def reason(self, actor, event: dict[str, Any]) -> str:
        strategy = self._strategy(actor)
        target = event.get("target")
        target_name = getattr(target, "name", None) or getattr(target, "object_id", "sojusznik")
        return f"{strategy.reason()}: ochrona celu {target_name}"

    def execute(self, actor, event: dict[str, Any], ctx) -> bool:
        game = ctx.game
        attacker = event.get("actor")
        target = event.get("target")
        if attacker is None or target is None:
            return False
        if not _is_alive(attacker) or not _is_alive(target):
            return False
        damage = _event_damage(event)
        if damage <= 0:
            return False

        level = getattr(actor, "level", 1) or 1
        try:
            level = int(level)
        except Exception:
            level = 1
        base_prevented = min(damage, max(2, 2 + level))
        strategy = self._strategy(actor)
        prevented, details = strategy.resolve_prevention(
            actor,
            attacker,
            target,
            game,
            damage=damage,
            base_prevented=base_prevented,
        )
        prevented = max(0, min(damage, int(prevented)))
        _heal_prevented_damage(target, prevented)
        try:
            game.ui_log(
                f"{strategy.reason()}: redukujesz obrazenia o {prevented} "
                f"dla {getattr(target, 'name', 'celu')}."
            )
        except Exception:
            pass
        if details.get("outcome") == "forgo":
            try:
                game.ui_log("Glimpse of Redemption: agresor powstrzymuje atak.")
            except Exception:
                pass

        strategy.apply_secondary(actor, attacker, target, game, details=details)
        return True
