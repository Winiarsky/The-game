from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from board import consts
from hero import Hero
from skills import Skill

from .base import State
from .heroes_turns import HeroesTurn


logger = logging.getLogger(__name__)


class Start(State):
    
    def welcome_message(self):
        logger.info("Witamy w grze planszowej!")
        self.game.ui_log("Witamy w grze planszowej!")
        
    def set_heroes_starting_positions(self) -> State:
        heroes: list[Hero] = self.game.heroes
        starting_positions = [tuple(pos) for pos in self.game.scenario['starting_positions']]
        logger.info("Ustawianie pozycji startowych bohaterów.")
        self.game.ui_log("Ustawianie pozycji startowych bohaterów.")
        logger.info(starting_positions)
        while True:
            response = self.game.conn.read_card(
                "Skanuj karte ACCEPT by ustawic figurke na polu startowym, lub DECLINE by zakonczyc setup",
                ["ACCEPT", "DECLINE"],
            )
            if response.upper() == "DECLINE":
                logger.info("Setup graczy zakonczony.")
                self.game.ui_log("Setup bohaterów zakończony.")
                break
            if response.upper() == "ACCEPT":
                logger.info("Ustaw figurke swojego bohatera na wolnym polu startowym.")
            self.game.conn.set_leds(starting_positions, consts.MOVE_FIELD_RGB) # usunac pozycje zajete
            logger.info("Odczytuje polozenie figurki...")
            pos = self.game.conn.scan_board(starting_positions)
            self.game.conn.leds_off()
            hero = Hero()
            try:
                self.game.board.place(hero, pos)
            except ValueError as exc:
                logger.error("Nie można ustawić bohatera: %s", exc)
                continue
            heroes.append(hero)
            logger.info(
                f"Bohater ustawiony na pozycji {pos}."
            )
            self._maybe_prompt_chameleon_gnome(hero)
            self._maybe_prompt_familiar_owner(hero)
            self.game.ui_hero(hero, note=f"Ustawiony na polu startowym {pos}")
            self.game.ui_log(f"Bohater ustawiony na pozycji {pos}.")
        self.game.heroes = heroes
        return HeroesTurn(self.game)

    def _collect_terrain_choices(self) -> list[str]:
        board = self.game.board
        seen: set[str] = set()
        choices: list[str] = []
        excluded = {"basic", "dim_light", "darkness"}
        for row in getattr(board, "_grid", []):
            for cell in row:
                terrain = getattr(cell, "field", None)
                if terrain is None:
                    continue
                tags = list(getattr(terrain, "terrain_tags", ()) or ())
                if tags:
                    for tag in tags:
                        if not tag or tag in excluded or tag in seen:
                            continue
                        seen.add(tag)
                        choices.append(tag)
                    continue
                name = getattr(terrain, "name", None)
                if not name or name in excluded or name in seen:
                    continue
                seen.add(name)
                choices.append(name)
        choices.sort()
        return choices

    def _normalize_choice(self, answer: str | None, choices: list[str]) -> str | None:
        if not answer:
            return None
        raw = str(answer).strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        if raw in choices:
            return raw
        return None

    def _get_status(self, hero: Hero, status_id: str):
        getter = getattr(hero, "get_status", None)
        if callable(getter):
            return getter(status_id)
        for status in getattr(hero, "statuses", []) or []:
            if getattr(status, "id", None) == status_id:
                return status
        return None

    def _maybe_prompt_chameleon_gnome(self, hero: Hero) -> None:
        if not hero.has_status("chameleon_gnome"):
            return
        status = self._get_status(hero, "chameleon_gnome")
        if status is None:
            return
        data = getattr(status, "data", None) or {}
        data["chameleon_terrain"] = None
        choices = self._collect_terrain_choices()
        if not choices:
            self.game.ui_log("Chameleon Gnome: brak dostępnych terenów do wyboru.")
            return
        prompt = (
            "Chameleon Gnome: wybierz typ terenu. "
            "Na tym terenie otrzymujesz +2 circumstance do Stealth."
        )
        answer: str | None = None
        ui = getattr(self.game, "ui", None)
        if ui is not None and hasattr(ui, "prompt_choice"):
            answer = ui.prompt_choice(prompt, choices=choices, source="setup")
        else:
            try:
                answer = input(prompt + " ").strip() or None
            except Exception:
                answer = None
        choice = self._normalize_choice(answer, choices)
        if choice is None:
            self.game.ui_log("Chameleon Gnome: nie wybrano poprawnego terenu.")
            return
        data["chameleon_terrain"] = choice
        self.game.ui_log(f"Chameleon Gnome: wybrany teren: {choice}.")

    def _maybe_prompt_familiar_owner(self, hero: Hero) -> None:
        if not hero.has_status("FamiliarOwner"):
            return
        status = self._get_status(hero, "FamiliarOwner")
        if status is None:
            return
        data = getattr(status, "data", None) or {}
        data["familiar_mode"] = None
        data["familiar_guidance_skill"] = None
        choices = [
            "Scout (Perception)",
            "Guidance (Skill)",
            "Distract (Enemy)",
            "Deliver Touch Spell",
            "Scent/Seek",
        ]
        prompt = "Familiar: wybierz tryb działania (stały dla Command Familiar)."
        answer: str | None = None
        ui = getattr(self.game, "ui", None)
        if ui is not None and hasattr(ui, "prompt_choice"):
            answer = ui.prompt_choice(prompt, choices=choices, source="setup")
        else:
            try:
                answer = input(prompt + " ").strip() or None
            except Exception:
                answer = None
        choice = self._normalize_choice(answer, choices)
        if choice is None:
            self.game.ui_log("Familiar: nie wybrano poprawnego trybu.")
            return
        mode_map = {
            "Scout (Perception)": "scout",
            "Guidance (Skill)": "guidance",
            "Distract (Enemy)": "distract",
            "Deliver Touch Spell": "deliver_touch",
            "Scent/Seek": "scent_seek",
        }
        mode = mode_map.get(choice)
        if not mode:
            self.game.ui_log("Familiar: nie rozpoznano trybu.")
            return
        data["familiar_mode"] = mode
        if mode == "guidance":
            skill_choices = [s.value for s in Skill]
            skill_prompt = "Guidance: wybierz skill dla stałego bonusu +1."
            skill_answer: str | None = None
            if ui is not None and hasattr(ui, "prompt_choice"):
                skill_answer = ui.prompt_choice(skill_prompt, choices=skill_choices, source="setup")
            else:
                try:
                    skill_answer = input(skill_prompt + " ").strip() or None
                except Exception:
                    skill_answer = None
            skill_choice = self._normalize_choice(skill_answer, skill_choices)
            if skill_choice is None:
                self.game.ui_log("Guidance: nie wybrano poprawnego skilla.")
                return
            data["familiar_guidance_skill"] = skill_choice
        self.game.ui_log(f"Familiar: wybrany tryb: {mode}.")
