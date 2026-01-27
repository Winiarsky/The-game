import logging
from pathlib import Path
import sys
from time import sleep
from typing import Tuple

from .actions_registy import register
from .base import ActionContext, BaseAction
from .move_utils import perform_movement, default_on_enter
from board import consts
from interactions.common import prompt_for_roll
from awareness import iter_watchers_in_rooms, summarize_watchers
from obstacle import Obstacle

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


logger = logging.getLogger(__name__)


@register
class StealthAction(BaseAction):
    name = "stealth"
    prompt_source = "Wybierz bohatera do skradania"

    def on_choose_info(self, ctx: ActionContext):
        logger.info("Akcja stealth: test ukrycia, a potem ruch jak w Move (kliknięcie bieżącego pola kończy).")

    def _choose_hero(self, ctx: ActionContext):
        heroes_positions = [hero.position for hero in ctx.game.heroes if hero.position is not None]
        if not heroes_positions:
            logger.warning("Brak bohaterów na planszy.")
            return None, None
        ctx.game.conn.set_leds(heroes_positions, consts.HERO_HIGHLIGHT_RGB)
        source = ctx.game.conn.scan_board(heroes_positions)
        ctx.game.conn.leds_off()
        board = ctx.game.board
        hero = board.occupant_at(source)
        return hero, source

    def _validate_neighbors(self, ctx: ActionContext, current: Tuple[int, int], neighbours: list[Tuple[int, int]]) -> list[Tuple[int, int]]:
        """Jak w MoveAction – pola, na które można wejść/przejść (plus bieżące pole jako opcja zakończenia)."""
        validated: list[Tuple[int, int]] = [current]
        board = ctx.game.board
        for neighbor in neighbours:
            if neighbor == current:
                continue
            if board.can_traverse(current, neighbor, allow_occupied=True):
                validated.append(neighbor)
        return validated

    def _wall_bonus(self, ctx: ActionContext, pos: Tuple[int, int]) -> int:
        board = ctx.game.board
        col, row = pos
        bonus = 0
        for dc, dr in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            neighbor = (col + dc, row + dr)
            if board.in_bounds(neighbor) and board.is_blocked(pos, neighbor):
                bonus += 1
        return bonus

    def _compute_modifier(self, ctx: ActionContext, pos: Tuple[int, int]) -> tuple[int, list[str]]:
        """Zwraca (suma, detale)."""
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
        for room_id in rooms_here:
            current = hero.stealth_fail_counts.get(room_id, 0) + 1
            hero.stealth_fail_counts[room_id] = current
            if critical or current >= consts.STEALTH_FAIL_MAX_ATTEMPTS:
                hero.blocked_stealth_rooms.add(room_id)
        hero.remove_status("stealth")
        hero.stealth_detection_dc = None
        hero.stealth_bonus = 0

    def _apply_success(self, hero, rooms_here: set[str], roll: int) -> int:
        hero.stealth_detection_dc = roll
        hero.remove_status("observable")
        hero.add_status("stealth")
        for room_id in rooms_here:
            hero.stealth_fail_counts[room_id] = 0
        bonus = 0
        if roll >= 20:
            bonus = 1 + (roll - 20) // 5
        hero.stealth_bonus = bonus
        return bonus

    def _trigger_critical_fail_effects(self, ctx: ActionContext, pos: Tuple[int, int]) -> None:
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

    def execute(self, ctx: ActionContext):
        hero, hero_pos = self._choose_hero(ctx)
        if hero is None or hero_pos is None:
            return

        board = ctx.game.board
        rooms_here = board.rooms_at(hero_pos)
        has_hide_status = hero.has_status("hide")
        watchers = iter_watchers_in_rooms(board, rooms_here, ignore_obj=hero) if not has_hide_status else []
        penalty, blockers = summarize_watchers(watchers) if watchers else (0, [])
        if hero.has_status("observable"):
            logger.info("Masz status observable – nie możesz wejść w ukrycie.")
            return
        if rooms_here and any(room in hero.blocked_stealth_rooms for room in rooms_here):
            logger.info("Ten bohater ma zablokowane próby stealth w tym pokoju.")
            return

        already_stealth = hero.has_status("stealth")
        if not already_stealth:
            if blockers:
                positions = [pos for _watcher, pos in blockers]
                logger.info("Nie możesz wejść w ukrycie – ktoś cię obserwuje.")
                if positions:
                    ctx.game.conn.set_leds(positions, consts.WATCH_ALERT_RGB)
                    sleep(consts.WATCH_ALERT_SECONDS)
                    ctx.game.conn.leds_off()
                return
            modifier, details = self._compute_modifier(ctx, hero_pos)
            if hero.has_status("hide"):
                bonus_hide = getattr(hero, "hide_stealth_bonus", 0)
                if bonus_hide:
                    modifier += bonus_hide
                    details.append(f"ukrycie +{bonus_hide}")
            if penalty:
                modifier -= penalty
                details.append(f"strażnicy czujności {-(penalty)}")
            details_txt = ", ".join(details) if details else "brak modyfikatorów"
            roll = prompt_for_roll(
                f"Podaj końcowy wynik testu Stealth (modyfikator {modifier:+d}: {details_txt}): "
            )
            result = roll
            if result < consts.STEALTH_CRITICAL_FAIL:
                self._apply_fail(hero, rooms_here, critical=True)
                self._trigger_critical_fail_effects(ctx, hero_pos)
                logger.info("Krytyczna porażka – pokój zablokowany dla stealth.")
                return
            if result < consts.STEALTH_FAIL:
                self._apply_fail(hero, rooms_here, critical=False)
                for room_id in rooms_here:
                    fails = hero.stealth_fail_counts.get(room_id, 0)
                    if fails >= consts.STEALTH_FAIL_MAX_ATTEMPTS:
                        hero.blocked_stealth_rooms.add(room_id)
                logger.info("Nie udaje się wejść w ukrycie.")
                return

            bonus = self._apply_success(hero, rooms_here, result)
            ctx.game.conn.set_leds([hero_pos], consts.STEALTH_SUCCESS_RGB)
            sleep(consts.RESPONSE_DELAY)
            ctx.game.conn.leds_off()
            if bonus > 0:
                logger.info("Wchodzisz w ukrycie (DC wykrycia %s, premia stealth +%s).", result, bonus)
            else:
                logger.info("Wchodzisz w ukrycie (DC wykrycia %s).", result)
        else:
            logger.info("Już jesteś w ukryciu – przejdź w trybie stealth.")
            if self._attempt_spot_here(ctx, hero, hero_pos):
                return

        self._stealth_move(ctx, hero, hero_pos)

    def _stealth_move(self, ctx: ActionContext, hero, start_pos: Tuple[int, int]) -> None:
        board = ctx.game.board
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

    def _attempt_spot_here(self, ctx: ActionContext, hero, position: Tuple[int, int]) -> bool:
        """Wywołaj próby wykrycia w obecnych pokojach; True jeśli ktoś zauważył."""
        spotted_any = False
        rooms = ctx.game.board.rooms_at(position)
        watchers_here = iter_watchers_in_rooms(ctx.game.board, rooms, ignore_obj=hero)
        for watcher, _pos in watchers_here:
            attempt = getattr(watcher, "attempt_spot", None)
            if not callable(attempt):
                continue
            spotted, msg = attempt(hero, ctx.game)
            if msg:
                logger.info(msg)
                ctx.game.ui_log(msg)
            spotted_any = spotted_any or spotted
        return spotted_any
