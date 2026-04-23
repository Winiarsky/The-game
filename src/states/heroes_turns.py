from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from .base import State
from .intent_menu import (
    build_intent_options,
    choose_event_from_bucket,
    choose_option,
    filter_alchemy_events_for_actor,
    filter_events_for_actor,
    filter_player_events,
    filter_magic_events_for_actor,
    group_events,
    render_actor_stats,
)
from spell_management import ensure_actor_spell_state
from narration import narrate_action_result

from GameObjects.events import EventContext
from GameObjects.events.registry import dispatch_event, list_events
import GameObjects.events.all_events  # noqa: F401  # rejestruj eventy
from board import consts

logger = logging.getLogger(__name__)


class HeroesTurn(State):
    def __init__(self, game):
        super().__init__(game)
        self.active_hero = None

    def on_enter(self):
        logger.info("Tura bohaterow!")
        self.game.ui_log("Tura bohaterów!")
        self.game.ui_event("initiative", {"round": None, "order": [], "active_id": None})
        ui_active_actor = getattr(self.game, "ui_active_actor", None)
        if callable(ui_active_actor):
            ui_active_actor(None)
        ui_idle_hint = getattr(self.game, "ui_idle_hint", None)
        if callable(ui_idle_hint):
            ui_idle_hint(
                "Tura bohaterów",
                "Kliknij figurkę bohatera na planszy, aby wybrać aktywnego bohatera, a potem akcję.",
            )

    def on_exit(self):
        logger.info("Koniec tury bohaterow.")
        self.game.ui_log("Koniec tury bohaterów.")

    def _choose_active_hero(self):
        available_heroes = [hero for hero in self.game.heroes if hero.position is not None]
        heroes_positions = [hero.position for hero in available_heroes]
        if not heroes_positions:
            logger.info("Brak bohaterów na planszy.")
            self.game.ui_log("Brak bohaterów na planszy.")
            return None
        ui_idle_hint = getattr(self.game, "ui_idle_hint", None)
        if callable(ui_idle_hint):
            ui_idle_hint(
                "Wybór bohatera",
                "Gra czeka teraz na klik figurki bohatera na planszy.",
            )
        self.game.conn.set_leds(heroes_positions, consts.HERO_HIGHLIGHT_RGB)
        try:
            try:
                pos = self.game.conn.scan_board(heroes_positions)
            except TimeoutError:
                self.game.ui_log("Kontynuuj wybór w UI. Plansza nie zwróciła kliknięcia bohatera.")
                return self._choose_active_hero_from_ui(available_heroes)
            hero = self.game.board.occupant_at(pos)
            if hero is not None:
                return hero
        finally:
            self.game.conn.leds_off()
        return self._choose_active_hero_from_ui(available_heroes)

    def _choose_active_hero_from_ui(self, available_heroes):
        if not available_heroes:
            return None
        if len(available_heroes) == 1:
            return available_heroes[0]
        options = []
        for hero in available_heroes:
            pos = getattr(hero, "position", None)
            pos_text = f"Pole {tuple(pos)}" if pos is not None else "Poza planszą"
            class_name = str(getattr(hero, "class_name", None) or getattr(hero, "class_id", "") or "").strip()
            class_text = class_name if class_name else "Bohater"
            options.append(
                {
                    "id": str(getattr(hero, "object_id", "") or getattr(hero, "character_id", "") or hero.name).strip().lower(),
                    "label": str(getattr(hero, "name", "Bohater")),
                    "desc": f"{class_text} · {pos_text}",
                    "category": "utility",
                    "icon": "◈",
                }
            )
        ui_idle_hint = getattr(self.game, "ui_idle_hint", None)
        if callable(ui_idle_hint):
            ui_idle_hint(
                "Wybór bohatera",
                "Plansza nie zwróciła kliknięcia. Wybierz aktywnego bohatera z listy w UI.",
            )
        answer = choose_option(
            self.game,
            title="Aktywny bohater",
            subtitle="Wybierz bohatera do wykonania akcji.",
            source="hero_select",
            options=options,
        )
        by_id = {str(option["id"]).strip().lower(): hero for option, hero in zip(options, available_heroes)}
        return by_id.get(str(answer or "").strip().lower())

    def _has_any_hero_on_board(self) -> bool:
        return any(getattr(hero, "position", None) is not None for hero in list(getattr(self.game, "heroes", []) or []))

    def _recover_no_heroes_on_board(self) -> State:
        answer = choose_option(
            self.game,
            title="Brak bohaterów",
            subtitle="Wybierz dalsze działanie.",
            source="heroes_missing",
            options=[
                {
                    "id": "recover",
                    "label": "Ustaw bohaterów",
                    "desc": "Wróć do ustawiania pozycji startowych bohaterów.",
                },
                {
                    "id": "stay",
                    "label": "Pozostań",
                    "desc": "Pozostań w tym stanie bez bohaterów na planszy.",
                },
            ],
        )

        if answer == "recover":
            from .start import Start

            return Start(self.game).set_heroes_starting_positions()

        self.game.ui_log("Pozostajesz bez bohaterów na planszy.")
        return self

    def _show_actor_stats(self, actor) -> None:
        text = render_actor_stats(actor, combat_state=None)
        ui = getattr(self.game, "ui", None)
        if ui is not None and hasattr(ui, "prompt_info") and getattr(ui, "enabled", False):
            try:
                ui.prompt_info(
                    "Statystyki",
                    prompt_long=text,
                    source="stats",
                )
                return
            except Exception:
                pass
        self.game.ui_log(text)

    def choose_action(self) -> State:
        all_events = list_events()
        available_events = {
            name: cls for name, cls in all_events.items() if getattr(cls, "available_in_exploration", True)
        }
        available_events = filter_player_events(available_events, actor_is_hero=True)
        # wybierz aktywnego bohatera tylko jeśli jeszcze nie ma
        if self.active_hero is None or getattr(self.active_hero, "position", None) is None:
            hero = self._choose_active_hero()
            if hero is None:
                if not self._has_any_hero_on_board():
                    return self._recover_no_heroes_on_board()
                return self
            self.active_hero = hero
        hero = self.active_hero
        available_events = filter_events_for_actor(
            available_events,
            actor=hero,
            in_combat=False,
            game=self.game,
        )
        try:
            ensure_actor_spell_state(hero, game=self.game)
        except Exception:
            pass
        available_events = filter_magic_events_for_actor(
            available_events,
            actor=hero,
            game=self.game,
        )
        available_events = filter_alchemy_events_for_actor(
            available_events,
            actor=hero,
        )
        if not available_events:
            logger.warning("Brak zarejestrowanych eventów dla eksploracji (po filtrze bohatera).")
            self.game.ui_log("Brak akcji do wykonania.")
            return self
        ui_active_actor = getattr(self.game, "ui_active_actor", None)
        if callable(ui_active_actor):
            ui_active_actor(hero)

        # podświetl aktywnego bohatera podczas wyboru akcji
        highlighted = False
        try:
            pos = getattr(hero, "position", None)
            if pos is not None:
                self.game.conn.set_leds([pos], consts.HERO_HIGHLIGHT_RGB)
                highlighted = True
        except Exception:
            pass

        grouped = group_events(available_events, actor=hero)
        intent_options = build_intent_options(grouped, in_combat=False, actor=hero, available_events=available_events)
        choice = choose_option(
            self.game,
            title="Akcje",
            subtitle="8/2 nawigacja, Enter potwierdzenie.",
            source="intent",
            options=intent_options,
        )

        if highlighted:
            try:
                self.game.conn.leds_off()
            except Exception:
                pass

        event_name: str | None = None
        if not choice:
            self.game.ui_log("Nie wybrano akcji.")
            return self

        if choice == "stats":
            self._show_actor_stats(hero)
            return self

        if event_name is None:
            if choice == "interact":
                event_name = "interaction"
            elif choice == "equipment":
                event_name = "equip"
            elif choice == "attack":
                if "attack" in available_events:
                    event_name = "attack"
                else:
                    event_name = choose_event_from_bucket(
                        self.game,
                        bucket_id=choice,
                        available_events=available_events,
                        event_names=list(grouped.get(choice, [])),
                        source=f"intent:{choice}",
                    )
                    if not event_name:
                        self.game.ui_log("Nie wybrano akcji ataku.")
                        return self
            elif choice in ("magic", "alchemy", "special"):
                event_name = choose_event_from_bucket(
                    self.game,
                    bucket_id=choice,
                    available_events=available_events,
                    event_names=list(grouped.get(choice, [])),
                    source=f"intent:{choice}",
                )
                if not event_name:
                    self.game.ui_log(f"Nie wybrano akcji z kategorii '{choice}'.")
                    return self
            else:
                event_name = str(choice).strip().lower()

        if event_name not in available_events:
            logger.error("Nieznana akcja '%s'", event_name)
            self.game.ui_log(f"Nieznana akcja '{event_name}'")
            return self

        ctx = EventContext(game=self.game, actor=hero)
        result = dispatch_event(event_name, ctx)
        if result.message:
            self.game.ui_log(result.message)
        else:
            status = "powiodła się" if result.success else "nie powiodła się"
            self.game.ui_log(f"Akcja '{event_name}' {status}.")
        try:
            self.game.ui_narration(
                narrate_action_result(actor=hero, action_id=event_name, result=result),
                summary="Jaki był efekt akcji",
                source=f"action_result:{event_name}",
                priority="result" if result.success else "warning",
                semantic_type="result",
            )
        except Exception:
            logger.debug("Nie udało się wysłać narracji wyniku akcji '%s'.", event_name, exc_info=True)
        if event_name == "end" and result.success:
            self.active_hero = None  # wymuś wybór kolejnego bohatera
        return self
    
