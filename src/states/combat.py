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
        self.attack_state: dict[Any, dict[str, object]] = {}
        self.status_initiative_penalty: dict[Any, int] = {}

    def on_enter(self):
        logger.info("Walka rozpoczęta.")
        self.game.ui_log("Walka rozpoczęta.")
        # Wyświetl informacyjny prompt na starcie walki.
        self.game.ui_event(
            "info",
            {
                "text": "O bogowie, walka!",
                "source": "combat",
            },
        )
        ui_idle_hint = getattr(self.game, "ui_idle_hint", None)
        if callable(ui_idle_hint):
            ui_idle_hint("Walka", "Śledź inicjatywę i wybierz akcję aktywnego aktora.")
        self._reset_heroes_initiative()
        self._ensure_initiative_order()

    def on_exit(self):
        logger.info("Zakończenie walki.")
        self.game.ui_log("Zakończenie walki.")
        self._clear_combat_statuses()
        self._clear_initiatives()

    def _clear_combat_statuses(self) -> None:
        """Wyczyść statusy i bonusy, które mają kończyć się po walce."""
        try:
            from GameObjects.events.magic.lighting_effects import clear_magic_lighting

            clear_magic_lighting(self.game)
        except Exception:
            pass
        for actor in list(getattr(self.game, "heroes", []) or []) + list(getattr(self.game, "enemies", []) or []):
            remover_status = getattr(actor, "remove_status", None)
            if callable(remover_status):
                try:
                    remover_status("rage")
                except Exception:
                    pass
                try:
                    remover_status("animal_instinct_active")
                except Exception:
                    pass
                try:
                    remover_status("dragon_instinct_active")
                except Exception:
                    pass
                try:
                    remover_status("giant_instinct_active")
                except Exception:
                    pass
                try:
                    remover_status("spirit_instinct_active")
                except Exception:
                    pass
                statuses = getattr(actor, "statuses", None)
                if isinstance(statuses, list):
                    for status in list(statuses):
                        if getattr(status, "id", None) != "clumsy":
                            continue
                        source = getattr(status, "source", None)
                        if source == "giant_instinct":
                            try:
                                statuses.remove(status)
                            except ValueError:
                                pass
            remover_bonus = getattr(actor, "remove_bonuses_by_source", None)
            if callable(remover_bonus):
                try:
                    remover_bonus("rage")
                except Exception:
                    pass
            statuses = getattr(actor, "statuses", None)
            if isinstance(statuses, list):
                for status in list(statuses):
                    if getattr(status, "id", None) != "darkvision":
                        continue
                    data = getattr(status, "data", None) or {}
                    if data.get("source_tag") != "rage":
                        continue
                    try:
                        statuses.remove(status)
                    except ValueError:
                        pass

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
            penalty = self._status_initiative_penalty_value(hero)
            if penalty:
                self.base_initiative[hero] = int(self.base_initiative[hero]) - penalty
                self.status_initiative_penalty[hero] = penalty
            participants.append(hero)
        for enemy in self.game.enemies:
            if getattr(enemy, "position", None) is None:
                continue
            self.base_initiative.setdefault(enemy, getattr(enemy, "initiative", -1))
            penalty = self._status_initiative_penalty_value(enemy)
            if penalty:
                self.base_initiative[enemy] = int(self.base_initiative[enemy]) - penalty
                self.status_initiative_penalty[enemy] = penalty
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
        self.attack_state.clear()
        self.status_initiative_penalty.clear()
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
        for dead in [k for k in list(self.status_initiative_penalty.keys()) if k not in self.base_order]:
            self.status_initiative_penalty.pop(dead, None)

    def _status_initiative_penalty_value(self, actor) -> int:
        statuses = getattr(actor, "statuses", None)
        if not isinstance(statuses, list):
            return 0
        best = 0
        for status in statuses:
            data = getattr(status, "data", None) or {}
            val = data.get("initiative_penalty", 0)
            try:
                val = int(val)
            except Exception:
                val = 0
            if val > best:
                best = val
        return int(best)

    def _resort_base_order(self) -> None:
        self._cleanup_removed()
        self.base_order.sort(
            key=lambda obj: self.base_initiative.get(obj, getattr(obj, "initiative", -1)),
            reverse=True,
        )

    def _rebuild_round_queue(self) -> None:
        remaining = [obj for obj in self.base_order if obj in self.round_queue]
        remaining.sort(key=self._effective_initiative_sort_key, reverse=True)
        self.round_queue = remaining
        self.initiative_order = list(self.round_queue)
        self._send_initiative_event()

    def sync_status_initiative_penalty(self, actor, *, reorder_round_queue: bool = False) -> None:
        current = self._status_initiative_penalty_value(actor)
        prev = self.status_initiative_penalty.get(actor, 0)
        if current == prev:
            return
        base = self.base_initiative.get(actor, getattr(actor, "initiative", -1))
        self.base_initiative[actor] = int(base) - int(current - prev)
        if current:
            self.status_initiative_penalty[actor] = current
        else:
            self.status_initiative_penalty.pop(actor, None)
        self._resort_base_order()
        if reorder_round_queue:
            self._rebuild_round_queue()

    def _clear_start_of_turn_effects(self, actor) -> None:
        """Usuń efekty jednorundowe (np. raise_shield) na początku inicjatywy bohatera."""
        try:
            self.attack_state.pop(actor, None)
        except Exception:
            pass
        try:
            if hasattr(actor, "_attack_trait_state"):
                delattr(actor, "_attack_trait_state")
        except Exception:
            pass
        if actor in getattr(self.game, "heroes", []):
            remover = getattr(actor, "remove_bonuses_with_prefix", None)
            if callable(remover):
                try:
                    remover("raise_shield:")
                except Exception:
                    logger.debug("Nie udało się wyczyścić efektów raise_shield dla %s", actor)

        tick = getattr(actor, "tick_bonuses_turn", None)
        if callable(tick):
            try:
                tick()
            except Exception:
                logger.debug("Nie udało się odliczyć bonusów dla %s", actor)

        # obrażenia ciągłe na początku inicjatywy
        try:
            from statuses import process_persistent_damage

            process_persistent_damage(actor, self.game)
        except Exception as exc:
            logger.debug("Nie udało się przetworzyć persistent damage dla %s: %s", actor, exc)

        try:
            from statuses import process_poisoned

            process_poisoned(actor, self.game)
        except Exception as exc:
            logger.debug("Nie udało się przetworzyć poisoned dla %s: %s", actor, exc)

        # wygaszanie statusów utrzymywanych przez aktora (np. grabbed/restrained)
        try:
            self._expire_held_statuses(actor)
        except Exception as exc:
            logger.debug("Nie udało się wygasić utrzymywanych statusów: %s", exc)

        # wygaszanie statusów liczonych od tury źródła
        try:
            self._expire_sourced_statuses(actor)
        except Exception as exc:
            logger.debug("Nie udało się wygasić statusów źródłowych: %s", exc)

        tick_statuses = getattr(actor, "tick_statuses_turn", None)
        if callable(tick_statuses):
            try:
                tick_statuses()
            except Exception:
                logger.debug("Nie udało się odliczyć statusów dla %s", actor)
        try:
            self.sync_status_initiative_penalty(actor, reorder_round_queue=False)
        except Exception:
            logger.debug("Nie udało się zsynchronizować kary do inicjatywy dla %s", actor)

    def _iter_held_statuses(self, source_actor):
        source_id = self._actor_id(source_actor)
        if not source_id:
            return []
        held = []
        actors = list(getattr(self.game, "heroes", [])) + list(getattr(self.game, "enemies", []))
        for target in actors:
            statuses = getattr(target, "statuses", None) or []
            for status in statuses:
                if getattr(status, "id", None) not in ("grabbed", "restrained"):
                    continue
                data = getattr(status, "data", None) or {}
                if data.get("source_id") != source_id:
                    continue
                held.append((target, status))
        return held

    def _clear_hold_status(self, target, status) -> None:
        status_id = getattr(status, "id", None)
        remover = getattr(target, "remove_status", None)
        if callable(remover):
            try:
                remover(status)
            except Exception:
                pass
        if status_id == "grabbed":
            try:
                from statuses import clear_grabbed_effects

                clear_grabbed_effects(target)
            except Exception:
                pass
        elif status_id == "restrained":
            try:
                from statuses import clear_restrained_effects

                clear_restrained_effects(target)
            except Exception:
                pass

    def _expire_held_statuses(self, source_actor) -> None:
        for target, status in self._iter_held_statuses(source_actor):
            data = getattr(status, "data", None) or {}
            if "maintain_turns_left" not in data:
                continue
            try:
                turns_left = int(data.get("maintain_turns_left", 0))
            except Exception:
                turns_left = 0
            turns_left -= 1
            data["maintain_turns_left"] = turns_left
            if turns_left < 0:
                self._clear_hold_status(target, status)

    def _expire_sourced_statuses(self, source_actor) -> None:
        source_id = self._actor_id(source_actor)
        if not source_id:
            return
        actors = list(getattr(self.game, "heroes", [])) + list(getattr(self.game, "enemies", []))
        for target in actors:
            statuses = getattr(target, "statuses", None)
            if not isinstance(statuses, list) or not statuses:
                continue
            remaining = []
            removed = 0
            for status in statuses:
                data = getattr(status, "data", None) or {}
                if data.get("source_id") != source_id or "source_turns_left" not in data:
                    remaining.append(status)
                    continue
                try:
                    turns_left = int(data.get("source_turns_left", 0))
                except Exception:
                    turns_left = 0
                turns_left -= 1
                data["source_turns_left"] = turns_left
                if turns_left <= 0:
                    removed += 1
                    continue
                remaining.append(status)
            if removed:
                try:
                    target.statuses = remaining
                except Exception:
                    pass

    def _confirm_break_hold(self, source_actor, held_statuses) -> bool:
        ui = None
        try:
            from ui_client import get_ui_client
        except Exception:
            get_ui_client = None
        prompt = "Inna akcja przerwie chwyt (grabbed/restrained). Kontynuować?"
        try:
            if get_ui_client is not None:
                ui = get_ui_client()
                if ui is not None and getattr(ui, "enabled", True):
                    choice = ui.prompt_choice(prompt, choices=["tak", "nie"], source="grapple_break")
                    return str(choice or "").strip().lower().startswith("t")
        except Exception:
            pass
        if ui is not None and not getattr(ui, "allow_cli_fallback", False):
            return False
        try:
            resp = input(f"{prompt} [t/N]: ")
            return resp.strip().lower().startswith("t")
        except Exception:
            return False

    def _current_actor(self):
        self._cleanup_removed()
        if not self.round_queue:
            return None
        actor = self.round_queue[0]
        if actor not in self.actions_used:
            self._clear_start_of_turn_effects(actor)
            self.actions_used[actor] = self._start_turn_actions_used(actor)
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
            logger.debug("Nowa tura dla %s – reset licznika akcji.", actor)
        self._send_initiative_event()

    def _start_turn_actions_used(self, actor) -> int:
        used = 0
        try:
            from statuses import consume_stunned_actions

            used = min(self.ACTION_LIMIT, max(0, int(consume_stunned_actions(actor) or 0)))
        except Exception:
            used = 0
        if used > 0:
            try:
                self.game.ui_log(f"{getattr(actor, 'name', 'Aktor')} jest stunned: traci {used} akcji.")
            except Exception:
                pass
        return used

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
            base = self.temp_initiative[actor]
        elif actor in self.base_initiative:
            base = self.base_initiative[actor]
        else:
            base = getattr(actor, "initiative", -1)
        try:
            from statuses import deafened_initiative_penalty

            penalty = deafened_initiative_penalty(actor, only_unapplied=True)
        except Exception:
            penalty = 0
        return int(base) - int(penalty or 0)

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
        ui_active_actor = getattr(self.game, "ui_active_actor", None)
        if callable(ui_active_actor):
            ui_active_actor(active)

    def apply_initiative_penalty(self, actor, penalty: int) -> None:
        """Obniż inicjatywę aktora i przestaw w kolejce (używane np. przez deafened)."""
        try:
            penalty = int(penalty)
        except Exception:
            penalty = 0
        if penalty <= 0:
            return

        try:
            from statuses import deafened_initiative_penalty

            unapplied = deafened_initiative_penalty(actor, only_unapplied=True)
        except Exception:
            unapplied = 0
        base_init = self._effective_initiative(actor)
        new_init = base_init if unapplied else base_init - penalty
        try:
            from statuses import mark_deafened_initiative_applied

            mark_deafened_initiative_applied(actor)
        except Exception:
            pass
        self.temp_initiative[actor] = new_init

        if actor in self.round_queue:
            if self.round_queue and self.round_queue[0] is actor:
                self.round_queue.pop(0)
            else:
                try:
                    self.round_queue.remove(actor)
                except ValueError:
                    pass
            inserted = False
            for idx, obj in enumerate(self.round_queue):
                if self._effective_initiative(obj) < new_init:
                    self.round_queue.insert(idx, actor)
                    inserted = True
                    break
            if not inserted:
                self.round_queue.append(actor)
            self.initiative_order = list(self.round_queue)
        self._send_initiative_event()

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

            delta = prompt_for_roll(
                "O ile obniżasz inicjatywę w tej rundzie? (liczba) ",
                layout="test",
                answer_placeholder="Modyfikator inicjatywy",
            )
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
        ui_active_actor = getattr(self.game, "ui_active_actor", None)
        if callable(ui_active_actor):
            ui_active_actor(actor)

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
        if not available_events:
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

        if raw_choice not in available_events:
            logger.error("Nieznana akcja '%s'", raw_choice)
            self.game.ui_log(f"Nieznana akcja '{raw_choice}'")
            return self

        # podtrzymanie chwytu (grabbed/restrained) – blokada innych akcji jeśli wymagane
        held_statuses = self._iter_held_statuses(actor)
        if held_statuses and raw_choice not in ("end", "delay"):
            maintain_ids = set()
            needs_block = False
            for _target, status in held_statuses:
                data = getattr(status, "data", None) or {}
                if not data.get("allow_other_actions_in_meantime", True):
                    needs_block = True
                mid = data.get("maintain_action_id")
                if mid:
                    maintain_ids.add(str(mid))
            if needs_block and raw_choice not in maintain_ids:
                if self._confirm_break_hold(actor, held_statuses):
                    for target, status in held_statuses:
                        self._clear_hold_status(target, status)
                else:
                    return self

        ctx = EventContext(game=self.game, actor=actor)
        result = dispatch_event(raw_choice, ctx)

        # delay/end mogą nie zużywać akcji
        if result.consumed_action:
            spent = getattr(result, "actions_spent", None)
            if spent is None:
                spent = result.data.get("actions_spent", None) if isinstance(getattr(result, "data", None), dict) else None
            try:
                spent = int(spent) if spent is not None else 1
            except Exception:
                spent = 1
            self.actions_used[actor] = self.actions_used.get(actor, 0) + spent
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
