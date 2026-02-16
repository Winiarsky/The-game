from __future__ import annotations

import logging
from time import sleep
from typing import Tuple

from board import consts
from combat import refresh_flanking_statuses
from GameObjects.Interactables.utils.awareness import iter_watchers_in_rooms, summarize_watchers
from GameObjects.Obstacles.basic_obstacle import Obstacle
from actions.move_utils import perform_movement, default_on_enter
from skills import Skill
from statuses import IN_DIM_LIGHT_STATUS, IN_DARK_STATUS, OBSERVABLE_STATUS, STEALTH_STATUS, StealthStatus, Status

from .base import EventContext, EventResult, GameEvent
from .registry import register_event, dispatch_event

logger = logging.getLogger(__name__)


def _get_stealth_memory(hero) -> tuple[set[str], dict[str, int]]:
    """Zwróć (blocked_rooms, fail_counts) przechowywane w statusie stealth_memory."""
    statuses = getattr(hero, "statuses", None) or []
    for status in statuses:
        if isinstance(status, Status) and status.id == "stealth_memory":
            data = getattr(status, "data", {}) or {}
            blocked = data.setdefault("blocked_rooms", set())
            fails = data.setdefault("fail_counts", {})
            return blocked, fails

    # jeśli brak – utwórz
    data = {"blocked_rooms": set(), "fail_counts": {}}
    mem_status = Status(id="stealth_memory", label="Stealth Memory", data=data)
    adder = getattr(hero, "add_status", None)
    if callable(adder):
        try:
            adder(mem_status)
        except Exception:
            pass
    else:
        if isinstance(statuses, list):
            statuses.append(mem_status)
    return data["blocked_rooms"], data["fail_counts"]  # type: ignore[index]


@register_event
class StealthEvent(GameEvent):
    name = "stealth"
    default_tags = [Skill.STEALTH.value, "move"]
    consumes_action = True

    @staticmethod
    def _stealth_stats(hero) -> tuple[int | None, int]:
        """
        Odczytaj (detection_dc, stealth_bonus) z aktywnego StealthStatus.
        Preferuje helper get_status_data z StatusMixin; w razie braku skanuje listę statuses.
        """
        getter = getattr(hero, "get_status_data", None)
        if callable(getter):
            dc = getter("stealth", "stealth_detection_dc", None)
            bonus = getter("stealth", "stealth_bonus", 0)
            return dc, bonus
        statuses = getattr(hero, "statuses", None) or []
        for status in statuses:
            if getattr(status, "id", None) == "stealth":
                data = getattr(status, "data", {}) or {}
                return data.get("stealth_detection_dc"), data.get("stealth_bonus", 0)
        return None, 0

    def execute(self, ctx: EventContext) -> EventResult:
        game = ctx.game
        hero = ctx.actor
        if hero not in getattr(game, "heroes", []) or getattr(hero, "position", None) is None:
            heroes_positions = [h.position for h in getattr(game, "heroes", []) if h.position is not None]
            if not heroes_positions:
                logger.warning("Brak bohaterów na planszy.")
                return EventResult.cancelled(message="Brak bohaterów.")
            game.conn.set_leds(heroes_positions, consts.HERO_HIGHLIGHT_RGB)
            source = game.conn.scan_board(heroes_positions)
            game.conn.leds_off()
            hero = game.board.occupant_at(source)

        if hero is None or getattr(hero, "position", None) is None:
            return EventResult.cancelled(message="Nie wybrano bohatera do stealth.")

        board = game.board
        hero_pos = hero.position
        rooms_here = board.rooms_at(hero_pos)
        blocked_rooms, fail_counts = _get_stealth_memory(hero)
        has_hide_status = hero.has_status("hide")
        in_dim_light = hero.has_status(IN_DIM_LIGHT_STATUS)
        in_dark = hero.has_status(IN_DARK_STATUS)
        watchers = iter_watchers_in_rooms(board, rooms_here, ignore_obj=hero) if not has_hide_status and not in_dim_light and not in_dark else []
        penalty, blockers = summarize_watchers(watchers) if watchers else (0, [])
        if hero.has_status(OBSERVABLE_STATUS) and not in_dim_light and not in_dark:
            logger.info("Masz status observable – nie możesz wejść w ukrycie.")
            return EventResult.noop(message="Status observable blokuje stealth.")
        if rooms_here and any(room in blocked_rooms for room in rooms_here):
            logger.info("Ten bohater ma zablokowane próby stealth w tym pokoju.")
            return EventResult.noop(message="Pokój zablokowany dla stealth.")

        already_stealth = hero.has_status(STEALTH_STATUS)
        covered = hero.has_status("covered")

        if not already_stealth:
            if blockers and not covered and not in_dim_light and not in_dark:
                positions = [pos for _watcher, pos in blockers]
                logger.info("Nie możesz wejść w ukrycie – ktoś cię obserwuje.")
                if positions:
                    game.conn.set_leds(positions, consts.WATCH_ALERT_RGB)
                    sleep(consts.WATCH_ALERT_SECONDS)
                    game.conn.leds_off()
                return EventResult.noop(message="Obserwatorzy blokują stealth.")
            game.events.safe_emit_action(
                actor=hero,
                action_id="stealth_start",
                action_tags=self._effective_tags(ctx),
                pos=hero_pos,
            )
            base_modifier, details = self._compute_modifier(ctx, hero_pos)
            if covered:
                base_modifier += 2
                details.append("osłona +2")
            if penalty:
                base_modifier -= penalty
                details.append(f"strażnicy czujności {-(penalty)}")
            tags = self._effective_tags(ctx) + ["try_stealth"]
            details_txt = ", ".join(details) if details else "brak modyfikatorów"
            result = dispatch_event(
                "skill_check",
                EventContext(
                    game=game,
                    actor=hero,
                    tags=tags,
                    metadata={
                        "dc": consts.STEALTH_FAIL,
                        "skill_id": Skill.STEALTH.value,
                        "skill_label": "Stealth",
                        "base_modifier": base_modifier,
                        "details": details_txt,
                        "apply_modifiers": False,  # gracz podaje ostateczny wynik
                    },
                ),
            )
            outcome = result.data.get("outcome") if result.data else None
            total = result.data.get("total") if result.data else 0

            if outcome == "critical_failure" or total < consts.STEALTH_CRITICAL_FAIL:
                self._apply_fail(hero, rooms_here, critical=True)
                self._trigger_critical_fail_effects(ctx, hero_pos)
                logger.info("Krytyczna porażka – pokój zablokowany dla stealth.")
                return EventResult.noop(message="Krytyczna porażka stealth.")
            if outcome in ("failure", None) or total < consts.STEALTH_FAIL:
                self._apply_fail(hero, rooms_here, critical=False)
                logger.info("Nie udaje się wejść w ukrycie.")
                return EventResult.noop(message="Nie weszto w stealth.")

            bonus = self._apply_success(hero, rooms_here, total)
            game.conn.set_leds([hero_pos], consts.STEALTH_SUCCESS_RGB)
            sleep(consts.RESPONSE_DELAY)
            game.conn.leds_off()
            if bonus > 0:
                logger.info("Wchodzisz w ukrycie (DC wykrycia %s, premia stealth +%s).", total, bonus)
            else:
                logger.info("Wchodzisz w ukrycie (DC wykrycia %s).", total)
        else:
            dc, bonus = self._stealth_stats(hero)
            logger.info("Już jesteś w ukryciu – przejdź w trybie stealth. (DC=%s, bonus=%s)", dc, bonus)
            if self._attempt_spot_here(ctx, hero, hero_pos):
                return EventResult.noop(message="Zostałeś dostrzeżony.")

        self._stealth_move(ctx, hero, hero_pos)
        return EventResult(success=True, consumed_action=self.consumes_action, message="Stealth wykonany.")

    # --- helpery przeniesione z akcji ---
    def _validate_neighbors(self, ctx: EventContext, current: Tuple[int, int], neighbours: list[Tuple[int, int]]) -> list[Tuple[int, int]]:
        validated: list[Tuple[int, int]] = [current]
        board = ctx.game.board
        for neighbor in neighbours:
            if neighbor == current:
                continue
            if board.can_traverse(current, neighbor, allow_occupied=True):
                validated.append(neighbor)
        return validated

    def _wall_bonus(self, ctx: EventContext, pos: Tuple[int, int]) -> int:
        board = ctx.game.board
        col, row = pos
        bonus = 0
        for dc, dr in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            neighbor = (col + dc, row + dr)
            if board.in_bounds(neighbor) and board.is_blocked(pos, neighbor):
                bonus += 1
        return bonus

    def _compute_modifier(self, ctx: EventContext, pos: Tuple[int, int]) -> tuple[int, list[str]]:
        board = ctx.game.board
        total = 0
        details: list[str] = []

        cell = board.cell_at(pos)
        terrain_mod = getattr(cell.field, "stealth_impact", 0)
        if terrain_mod:
            total += terrain_mod
            details.append(f"teren {terrain_mod:+d}")

        seen_interactables: set[int] = set()
        seen_obstacles: set[int] = set()
        neighbors = board.get_neighbors(pos, include_position=True, diagonal=True)
        for candidate in neighbors:
            for obj in board.interactables_at(candidate):
                obj_id = id(obj)
                if obj_id in seen_interactables:
                    continue
                seen_interactables.add(obj_id)
                impact = getattr(obj, "stealth_impact", 0)
                if impact:
                    total += impact
                    details.append(f"{obj.__class__.__name__} {impact:+d}")
            occupant = board.occupant_at(candidate)
            if isinstance(occupant, Obstacle):
                obj_id = id(occupant)
                if obj_id in seen_obstacles:
                    continue
                seen_obstacles.add(obj_id)
                impact = getattr(occupant, "stealth_impact", 0)
                if impact:
                    total += impact
                    details.append(f"przeszkoda {impact:+d}")

        wall_bonus = self._wall_bonus(ctx, pos)
        if wall_bonus:
            total += wall_bonus
            details.append(f"ściany {wall_bonus:+d}")

        return total, details

    def _apply_fail(self, hero, rooms_here: set[str], *, critical: bool) -> None:
        blocked_rooms, fail_counts = _get_stealth_memory(hero)
        for room_id in rooms_here:
            current = fail_counts.get(room_id, 0) + 1
            fail_counts[room_id] = current
            if critical or current >= consts.STEALTH_FAIL_MAX_ATTEMPTS:
                blocked_rooms.add(room_id)
        hero.remove_status(STEALTH_STATUS)

    def _apply_success(self, hero, rooms_here: set[str], roll: int) -> int:
        blocked_rooms, fail_counts = _get_stealth_memory(hero)
        hero.remove_status(OBSERVABLE_STATUS)
        hero.remove_status(STEALTH_STATUS)  # odśwież dane statusu
        bonus = 0
        if roll >= 20:
            bonus = 1 + (roll - 20) // 5
        for room_id in rooms_here:
            fail_counts[room_id] = 0
            if room_id in blocked_rooms:
                blocked_rooms.discard(room_id)
        hero.add_status(StealthStatus(detection_dc=roll, stealth_bonus=bonus))
        return bonus

    def _trigger_critical_fail_effects(self, ctx: EventContext, pos: Tuple[int, int]) -> None:
        board = ctx.game.board
        cell = board.cell_at(pos)
        for candidate in [cell.field]:
            handler = getattr(candidate, "on_critical_stealth_fail", None)
            if callable(handler):
                msg = handler()
                if msg:
                    logger.info(msg)

        neighbors = board.get_neighbors(pos, include_position=True, diagonal=True)
        seen: set[int] = set()
        for candidate in neighbors:
            for obj in board.interactables_at(candidate):
                if id(obj) in seen:
                    continue
                seen.add(id(obj))
                handler = getattr(obj, "on_critical_stealth_fail", None)
                if callable(handler):
                    msg = handler()
                    if msg:
                        logger.info(msg)

    def _stealth_move(self, ctx: EventContext, hero, start_pos: Tuple[int, int]) -> None:
        board = ctx.game.board
        try:
            perform_movement(
                ctx,
                hero,
                start_pos,
                lambda current: self._validate_neighbors(ctx, current, board.get_neighbors(current)),
                led_color=consts.STEALTH_MOVE_RGB,
                end_message="Kończysz ruch w ukryciu.",
                allow_occupied=True,
                on_enter=default_on_enter,
            )
            events = getattr(ctx.game, "events", None)
            if events and hasattr(events, "safe_emit_action"):
                events.safe_emit_action(
                    actor=hero,
                    action_id="stealth_move",
                    action_tags=self._effective_tags(ctx),
                    from_pos=start_pos,
                    to_pos=getattr(hero, "position", None),
                )
        finally:
            try:
                refresh_flanking_statuses(ctx.game)
            except Exception as exc:
                logger.error("Nie udało się odświeżyć flankowania po ruchu w stealth: %s", exc)

    def _attempt_spot_here(self, ctx: EventContext, hero, position: Tuple[int, int]) -> bool:
        spotted_any = False
        rooms = ctx.game.board.rooms_at(position)
        watchers_here = iter_watchers_in_rooms(ctx.game.board, rooms, ignore_obj=hero)
        for watcher, _pos in watchers_here:
            attempt = getattr(watcher, "attempt_spot", None)
            if not callable(attempt):
                continue
            spotted, msg = attempt(hero, ctx.game)
            if msg and not hasattr(watcher, "_log_watch_event"):
                logger.info(msg)
                ctx.game.ui_log(msg)
            spotted_any = spotted_any or spotted
        return spotted_any
