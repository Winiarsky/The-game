from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, List, Optional
from GameObjects.interactions_mixin import prompt_for_roll

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import actions  # noqa: F401  # rejestracja akcji przy starcie stanu walki
from board import consts
from GameObjects.Enemies.behaviors import get_behavior
from .base import State
from .heroes_turns import HeroesTurn
from GameObjects.events import EventContext
from GameObjects.events.registry import dispatch_event, list_events
import GameObjects.events.all_events  # noqa: F401

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
        self.base_initiative: dict[Any, int] = {}
        self.temp_initiative: dict[Any, int] = {}
        self.base_order: list[Any] = []      # stała kolejność bazowa
        self.round_queue: list[Any] = []     # kolejka na bieżącą rundę (konsumowana)
        self.round_index: int = 1

    def on_enter(self):
        logger.info("Walka rozpoczęta.")
        self.game.ui_log("Walka rozpoczęta.")
        self.game.ui_log("Press Enter aby kontynuować walkę.")
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
            self.game.conn.leds_off()
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
                val = enemy.roll_initiative()
                self.base_initiative[enemy] = val
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
            self.base_initiative.setdefault(hero, getattr(hero, "initiative", -1))
            participants.append(hero)
        for enemy in self.game.enemies:
            if getattr(enemy, "position", None) is None:
                continue
            self.base_initiative.setdefault(enemy, getattr(enemy, "initiative", -1))
            participants.append(enemy)
        participants.sort(key=self._effective_initiative_sort_key, reverse=True)
        self.base_order = participants
        self.round_queue = list(self.base_order)
        self.initiative_order = list(self.base_order)
        self.actions_used.clear()
        self.delayed.clear()
        self._initiatives_ready = True
        logger.info("Kolejność inicjatywy: %s", self.base_order)
        order = [getattr(obj, "name", None) or getattr(obj, "object_id", str(obj)) for obj in self.base_order]
        self.game.ui_log(f"Kolejność inicjatywy: {order}")
        self._send_initiative_event()

    def _clear_initiatives(self) -> None:
        for hero in self.game.heroes:
            try:
                hero.initiative = None  # type: ignore[attr-defined]
            except Exception:
                pass
        for enemy in self.game.enemies:
            enemy.initiative = None
        self._initiatives_ready = False
        self.base_initiative.clear()
        self.temp_initiative.clear()
        self.delayed.clear()
        self.base_order.clear()
        self.round_queue.clear()

    # --- Turn helpers ---
    def _cleanup_removed(self) -> None:
        def _alive(objs: list[Any]) -> list[Any]:
            alive: list[Any] = []
            for obj in objs:
                if obj in self.game.heroes:
                    if getattr(obj, "position", None) is None:
                        continue
                elif obj in self.game.enemies:
                    if getattr(obj, "position", None) is None or getattr(obj, "hp", 1) <= 0:
                        continue
                alive.append(obj)
            return alive

        self.base_order = _alive(self.base_order)
        self.round_queue = _alive(self.round_queue)
        self.initiative_order = list(self.base_order)
        # usuń martwe z map inicjatywy
        for mapping in (self.base_initiative, self.temp_initiative):
            for dead in [k for k in list(mapping.keys()) if k not in self.base_order]:
                mapping.pop(dead, None)

    def _clear_start_of_turn_effects(self, actor) -> None:
        """Usuń efekty jednorundowe (np. raise_shield) na początku inicjatywy bohatera."""
        if actor in getattr(self.game, "heroes", []):
            tick = getattr(actor, "tick_bonuses_turn", None)
            if callable(tick):
                try:
                    tick()
                except Exception:
                    logger.debug("Nie udało się odliczyć bonusów dla %s", actor)
            remover = getattr(actor, "remove_bonuses_with_prefix", None)
            if callable(remover):
                try:
                    remover("raise_shield:")
                except Exception:
                    logger.debug("Nie udało się wyczyścić efektów raise_shield dla %s", actor)

    def _current_actor(self):
        self._cleanup_removed()
        if not self.round_queue:
            return None
        actor = self.round_queue[0]
        if actor not in self.actions_used:
            self._clear_start_of_turn_effects(actor)
            self.actions_used[actor] = 0
            reset_react = getattr(actor, "reset_reactions", None)
            if callable(reset_react):
                try:
                    reset_react()
                except Exception as exc:
                    logger.error("Nie udało się zresetować reakcji dla %s: %s", actor, exc)
        return actor

    def _advance_turn(self):
        if not self.round_queue:
            return
        try:
            self.round_queue.pop(0)
        except IndexError:
            return
        if not self.round_queue:
            # nowa runda: reset opóźnień do bazowych inicjatyw
            self.round_index += 1
            self.temp_initiative.clear()
            self.delayed.clear()
            self.round_queue = list(self.base_order)
        self.initiative_order = list(self.round_queue)
        actor = self._current_actor()
        if actor is not None:
            self._clear_start_of_turn_effects(actor)
            self.actions_used[actor] = 0
            logger.debug("Nowa tura dla %s – reset licznika akcji.", actor)
            reset_react = getattr(actor, "reset_reactions", None)
            if callable(reset_react):
                try:
                    reset_react()
                except Exception as exc:
                    logger.error("Nie udało się zresetować reakcji dla %s: %s", actor, exc)
        self._send_initiative_event()

    # --- Combat flow ---
    def _end_combat_if_no_enemies(self) -> Optional[State]:
        enemies_alive = [e for e in self.game.enemies if getattr(e, "hp", 0) > 0 and getattr(e, "position", None) is not None]
        if enemies_alive:
            return None
        logger.info("Brak wrogów na planszy – koniec walki.")
        return HeroesTurn(self.game)

    def _actor_id(self, actor: Any) -> str:
        return getattr(actor, "object_id", None) or getattr(actor, "name", None) or str(id(actor))

    def _effective_initiative(self, actor: Any) -> int:
        if actor in self.temp_initiative:
            return self.temp_initiative[actor]
        if actor in self.base_initiative:
            return self.base_initiative[actor]
        return getattr(actor, "initiative", -1)

    def _effective_initiative_sort_key(self, actor: Any) -> int:
        return self._effective_initiative(actor)

    def _send_initiative_event(self) -> None:
        """Wyślij kolejkę inicjatywy do UI."""
        if not getattr(self.game, "ui", None):
            return
        order_payload: list[dict[str, Any]] = []
        done_set = set(self.base_order) - set(self.round_queue)
        # kolejność: najpierw obecna kolejka rundy, potem już-ograne (w bazowej kolejności)
        ordered_objs = list(self.round_queue) + [obj for obj in self.base_order if obj not in self.round_queue]
        for obj in ordered_objs:
            base = self.base_initiative.get(obj, getattr(obj, "initiative", -1))
            eff = self._effective_initiative(obj)
            delta = eff - base
            order_payload.append(
                {
                    "id": self._actor_id(obj),
                    "name": getattr(obj, "name", None) or getattr(obj, "object_id", "actor"),
                    "kind": "hero" if obj in self.game.heroes else "enemy",
                    "base": base,
                    "current": eff,
                    "delta": delta,
                    "done": obj in done_set,
                }
            )
        active = self._current_actor()
        self.game.ui_event(
            "initiative",
            {
                "round": self.round_index,
                "order": order_payload,
                "active_id": self._actor_id(active) if active else None,
            },
        )

    def _confirm_actor_position(self, actor) -> bool:
        return True

    def _handle_hero_decline(self, hero, *, auto_delay: bool = False) -> State:
        if not self._confirm_actor_position(hero):
            logger.info("Nie potwierdzono pozycji bohatera – przerwano wybór END/DELAY.")
            return self
        decision = "delay" if auto_delay else None
        if decision is None:
            used = self.actions_used.get(hero, 0)
            remaining = self.ACTION_LIMIT - used
            prompt = (
                "Limit akcji wyczerpany. END – koniec tury (8), DELAY – opóźnij (7, obniża inicjatywę)"
                if remaining <= 0
                else f"Masz {remaining} niewykorzystanych akcji. END – koniec tury (8), DELAY – opóźnij (7, obniża inicjatywę)"
            )
            decision = self.game.conn.read_card(prompt, ["end", "delay"]).strip().lower()

        if decision in ("delay", "7", "7 delay", "7 end", "7delay", "7end"):
            if hero in self.delayed:
                logger.info("Już opóźniałeś turę w tej rundzie.")
                self.game.ui_log("Już opóźniałeś turę w tej rundzie.")
                return self

            delta = prompt_for_roll("O ile obniżasz inicjatywę w tej rundzie? (liczba) ")
            try:
                delta = max(0, int(delta))
            except Exception:
                delta = 0
            base_init = self.base_initiative.get(hero, getattr(hero, "initiative", 0))
            new_init = max(0, base_init - delta)
            self.temp_initiative[hero] = new_init
            self.delayed.add(hero)

            # w bieżącej kolejce usuń aktora z przodu (jeśli tam był) i wstaw wg nowej inicjatywy malejąco
            if self.round_queue and self.round_queue[0] is hero:
                self.round_queue.pop(0)
            inserted = False
            for idx, obj in enumerate(self.round_queue):
                if self._effective_initiative(obj) < new_init:
                    self.round_queue.insert(idx, hero)
                    inserted = True
                    break
            if not inserted:
                self.round_queue.append(hero)

            logger.info("Bohater opóźnia turę – inicjatywa %s -> %s.", base_init, new_init)
            self.game.ui_log(f"Bohater opóźnia turę – inicjatywa {base_init} -> {new_init}.")
            self.actions_used[hero] = 0
            self._send_initiative_event()
            return self

        logger.info("Bohater kończy turę.")
        self.game.ui_log("Bohater kończy turę.")
        self._advance_turn()
        return self

    def _process_enemy_turn(self, enemy) -> State:
        logger.info("Tura przeciwnika: %s", getattr(enemy, "name", "Enemy"))
        used = self.actions_used.get(enemy, 0)
        limit = self.ACTION_LIMIT
        behavior_fn = get_behavior(getattr(enemy, "behavior_id", None))
        while used < limit:
            try:
                spent = behavior_fn(enemy, self.game, self, actions_left=limit - used)
            except Exception as exc:
                logger.error("AI przeciwnika (%s) nie powiodło się: %s", behavior_fn.__name__, exc)
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
        # Wyczyść jednorundowe bonusy osłon (np. raise_shield) na początku tury bohatera
        remover = getattr(actor, "remove_bonuses_with_prefix", None)
        if callable(remover):
            try:
                remover("raise_shield:")
            except Exception:
                logger.debug("Nie udało się wyczyścić efektów raise_shield dla %s", actor)

        used = self.actions_used.get(actor, 0)
        self.actions_used[actor] = used
        logger.info("Tura bohatera (%s). Akcje: %s/%s", actor, used, self.ACTION_LIMIT)
        self.game.ui_hero(actor, note=f"Akcje: {used}/{self.ACTION_LIMIT}")

        all_events = list_events()
        available_events = {
            name: cls for name, cls in all_events.items() if getattr(cls, "available_in_combat", True)
        }
        if not all_events:
            logger.warning("Brak zarejestrowanych eventów dla walki.")
            self.game.ui_log("Brak akcji do wykonania.")
            self._advance_turn()
            return self

        # podświetl aktywnego bohatera, żeby było jasne kto działa
        highlighted = False
        try:
            pos = getattr(actor, "position", None)
            if pos is not None:
                self.game.conn.set_leds([pos], consts.HERO_HIGHLIGHT_RGB)
                highlighted = True
        except Exception:
            pass

        ordered_choices = sorted(available_events.keys())
        logger.info("Dostępne akcje: %s", ", ".join(ordered_choices))
        self.game.ui_log(
            f"Aktywny: {getattr(actor, 'name', actor)}. Dostępne akcje: {', '.join(ordered_choices)}."
        )
        raw_choice = self.game.conn.read_card(
            "Podaj nazwę akcji",
        ).strip().lower()
        if highlighted:
            try:
                self.game.conn.leds_off()
            except Exception:
                pass

        if raw_choice not in all_events:
            logger.error("Nieznana akcja '%s'", raw_choice)
            self.game.ui_log(f"Nieznana akcja '{raw_choice}'")
            return self

        ctx = EventContext(game=self.game, actor=actor)
        result = dispatch_event(raw_choice, ctx)

        # delay/end mogą nie zużywać akcji
        if result.consumed_action:
            self.actions_used[actor] = self.actions_used.get(actor, 0) + 1
            if self.actions_used[actor] >= self.ACTION_LIMIT:
                logger.info(
                    "Wykorzystano limit %s akcji. Użyj end lub delay aby zakończyć turę.",
                    self.ACTION_LIMIT,
                )
        if result.message:
            self.game.ui_log(result.message)
        else:
            status = "powiodła się" if result.success else "nie powiodła się"
            self.game.ui_log(f"Akcja '{raw_choice}' {status}.")
        # end i delay same wywołują zmianę kolejki; jeśli aktywny uległ zmianie, nie ruszaj tutaj
        if raw_choice in ("end",):
            return self
        return self
