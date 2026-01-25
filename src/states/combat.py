from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from actions.actions_registy import get_action, list_actions
from actions.base import ActionContext
from board import consts
from enemies import basic_melee
from .base import State
from .heroes_turns import HeroesTurn

logger = logging.getLogger(__name__)


class Combat(State):
    ACTION_LIMIT = 3

    def __init__(self, game):
        super().__init__(game)
        self.initiative_order: list[Any] = []
        self.turn_index: int = 0
        self.actions_used: dict[Any, int] = {}
        self.delayed: set[Any] = set()
        self._initiatives_ready = False

    def on_enter(self):
        logger.info("Walka rozpoczęta.")
        self.game.ui_log("Walka rozpoczęta.")
        self._reset_heroes_initiative()
        self._ensure_initiative_order()

    def on_exit(self):
        logger.info("Zakończenie walki.")
        self.game.ui_log("Zakończenie walki.")
        self._clear_initiatives()

    # --- Initiative helpers ---
    def _reset_heroes_initiative(self) -> None:
        for hero in self.game.heroes:
            try:
                hero.initiative = None  # type: ignore[attr-defined]
            except Exception:
                pass

    def _prompt_hero_initiatives(self) -> None:
        heroes = [h for h in self.game.heroes if getattr(h, "position", None) is not None]
        pending = [h for h in heroes if getattr(h, "initiative", None) is None]
        while pending:
            positions = [h.position for h in pending if h.position is not None]
            if not positions:
                break
            self.game.conn.set_leds(positions, consts.HERO_HIGHLIGHT_RGB)
            pos = self.game.conn.scan_board(positions)
            self.game.conn.leds_off()
            hero = self.game.board.occupant_at(pos)
            if hero not in pending:
                logger.info("Ten bohater ma już ustawioną inicjatywę.")
                continue
            try:
                hero.roll_for_initiative()  # type: ignore[attr-defined]
            except Exception as exc:
                logger.error("Nie udało się ustawić inicjatywy: %s", exc)
            else:
                self.game.ui_hero(hero, note="Ustawiono inicjatywę")
            pending = [h for h in heroes if getattr(h, "initiative", None) is None]

    def _roll_enemy_initiatives(self) -> None:
        for enemy in self.game.enemies:
            try:
                enemy.roll_initiative()
            except Exception as exc:
                logger.error("Rzut inicjatywy wroga nie powiódł się: %s", exc)

    def _ensure_initiative_order(self) -> None:
        if self._initiatives_ready:
            return
        self._prompt_hero_initiatives()
        self._roll_enemy_initiatives()
        participants: list[Any] = []
        for hero in self.game.heroes:
            if getattr(hero, "position", None) is None:
                continue
            participants.append(hero)
        for enemy in self.game.enemies:
            if getattr(enemy, "position", None) is None:
                continue
            participants.append(enemy)
        participants.sort(key=lambda obj: getattr(obj, "initiative", -1), reverse=True)
        self.initiative_order = participants
        self.turn_index = 0
        self.actions_used.clear()
        self.delayed.clear()
        self._initiatives_ready = True
        logger.info("Kolejność inicjatywy: %s", self.initiative_order)
        order = [getattr(obj, "name", None) or getattr(obj, "object_id", str(obj)) for obj in self.initiative_order]
        self.game.ui_log(f"Kolejność inicjatywy: {order}")

    def _clear_initiatives(self) -> None:
        for hero in self.game.heroes:
            try:
                hero.initiative = None  # type: ignore[attr-defined]
            except Exception:
                pass
        for enemy in self.game.enemies:
            enemy.initiative = None
        self._initiatives_ready = False

    # --- Turn helpers ---
    def _cleanup_removed(self) -> None:
        alive_participants: list[Any] = []
        for obj in self.initiative_order:
            if obj in self.game.heroes:
                if getattr(obj, "position", None) is None:
                    continue
            elif obj in self.game.enemies:
                if getattr(obj, "position", None) is None or getattr(obj, "hp", 1) <= 0:
                    continue
            alive_participants.append(obj)
        self.initiative_order = alive_participants
        if self.turn_index >= len(self.initiative_order):
            self.turn_index = 0

    def _current_actor(self):
        self._cleanup_removed()
        if not self.initiative_order:
            return None
        if self.turn_index >= len(self.initiative_order):
            self.turn_index = 0
        return self.initiative_order[self.turn_index]

    def _advance_turn(self):
        self.turn_index = (self.turn_index + 1) % max(1, len(self.initiative_order))
        actor = self._current_actor()
        if actor is not None:
            self.actions_used[actor] = 0
            logger.debug("Nowa tura dla %s – reset licznika akcji.", actor)

    # --- Combat flow ---
    def _end_combat_if_no_enemies(self) -> Optional[State]:
        enemies_alive = [e for e in self.game.enemies if getattr(e, "hp", 0) > 0 and getattr(e, "position", None) is not None]
        if enemies_alive:
            return None
        logger.info("Brak wrogów na planszy – koniec walki.")
        return HeroesTurn(self.game)

    def _handle_hero_decline(self, hero) -> State:
        used = self.actions_used.get(hero, 0)
        remaining = self.ACTION_LIMIT - used
        if remaining <= 0:
            prompt = "Limit akcji wyczerpany. END – koniec tury, DELAY – koniec kolejki"
        else:
            prompt = f"Masz {remaining} niewykorzystanych akcji. END – koniec tury, DELAY – koniec kolejki"
        decision = self.game.conn.read_card(prompt, ["1", "2", "END", "DELAY"]).strip().upper()
        if decision in ("2", "DELAY"):
            if hero in self.delayed:
                logger.info("Już opóźniałeś turę w tej rundzie.")
                self.game.ui_log("Już opóźniałeś turę w tej rundzie.")
            else:
                current = self.initiative_order.pop(self.turn_index)
                self.initiative_order.append(current)
                self.delayed.add(hero)
                logger.info("Bohater opóźnia ruch – trafia na koniec kolejki.")
                self.game.ui_log("Bohater opóźnia ruch – trafia na koniec kolejki.")
            self.actions_used[hero] = 0
            return self

        logger.info("Bohater kończy turę.")
        self._advance_turn()
        return self

    def _process_enemy_turn(self, enemy) -> State:
        logger.info("Tura przeciwnika: %s", getattr(enemy, "name", "Enemy"))
        used = self.actions_used.get(enemy, 0)
        limit = self.ACTION_LIMIT
        while used < limit:
            try:
                spent = basic_melee(enemy, self.game, self, actions_left=limit - used)
            except Exception as exc:
                logger.error("AI przeciwnika nie powiodło się: %s", exc)
                self.game.ui_log(f"AI przeciwnika nie powiodło się: {exc}")
                break
            spent = int(spent or 0)
            used += spent
            self.actions_used[enemy] = used
            if spent <= 0:
                break
            if used >= limit:
                break
        self._advance_turn()
        return self

    def choose_action(self) -> State:
        maybe_end = self._end_combat_if_no_enemies()
        if maybe_end:
            return maybe_end

        self._ensure_initiative_order()
        actor = self._current_actor()
        if actor is None:
            logger.info("Brak uczestników – powrót do tury bohaterów.")
            return HeroesTurn(self.game)

        if actor in self.game.enemies:
            remaining = self.ACTION_LIMIT - self.actions_used.get(actor, 0)
            logger.info("Tura przeciwnika: %s (akcje pozostałe: %s/%s)", getattr(actor, "name", "Enemy"), remaining, self.ACTION_LIMIT)
            self.game.ui_log(f"Tura przeciwnika: {getattr(actor, 'name', 'Enemy')} (akcje {remaining}/{self.ACTION_LIMIT})")
            return self._process_enemy_turn(actor)

        # Hero turn
        used = self.actions_used.get(actor, 0)
        self.actions_used[actor] = used
        logger.info("Tura bohatera (%s). Akcje: %s/%s", actor, used, self.ACTION_LIMIT)
        self.game.ui_hero(actor, note=f"Akcje: {used}/{self.ACTION_LIMIT}")

        available = list_actions()
        if not available:
            logger.warning("Brak zarejestrowanych akcji.")
            self.game.ui_log("Brak zarejestrowanych akcji dla bohatera.")
            self._advance_turn()
            return self

        logger.info("Dostępne akcje: %s (DECLINE aby zakończyć turę).", ", ".join(sorted(available)))
        self.game.ui_log(f"Dostępne akcje: {', '.join(sorted(available))} (DECLINE aby zakończyć turę).")
        choice = self.game.conn.read_card(
            "Wpisz nazwę akcji lub DECLINE by zakończyć turę: ",
            list(available.keys()) + ["DECLINE"],
        ).strip()
        if choice.upper() == "DECLINE":
            return self._handle_hero_decline(actor)

        try:
            action = get_action(choice)
        except KeyError as exc:
            logger.error("%s", exc)
            return self

        ctx = ActionContext(game=self.game, heroes_turn=self)
        action.execute(ctx)
        self.actions_used[actor] = self.actions_used.get(actor, 0) + 1
        if self.actions_used[actor] >= self.ACTION_LIMIT:
            logger.info("Wykorzystano limit %s akcji. Użyj DECLINE aby zakończyć turę lub kontynuuj innymi efektami.", self.ACTION_LIMIT)
        return self
