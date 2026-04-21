from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from board import consts
from hero import Hero
from localization import localize_term_pl, localized_hint_pl
from skills import Skill
from spell_management import initialize_actor_spell_management
from character_creation import (
    CharacterRepository,
    create_character,
    hero_from_snapshot,
    list_character_menu_options,
)
from statuses.backgrounds.backgrounds import BACKGROUND_DEFINITIONS, get_background_status

from .base import State
from .heroes_turns import HeroesTurn


logger = logging.getLogger(__name__)


class Start(State):
    initial_action_name = "set_heroes_starting_positions"
    
    def welcome_message(self):
        logger.info("Witamy w grze planszowej!")
        self.game.ui_log("Witamy w grze planszowej!")
        
    def set_heroes_starting_positions(self) -> State:
        heroes: list[Hero] = self.game.heroes
        used_character_ids: set[str] = set()
        starting_positions = [tuple(pos) for pos in self.game.scenario['starting_positions']]
        preselected_count = int(getattr(self.game, "preselected_hero_count", 0) or 0)
        logger.info("Ustawianie pozycji startowych bohaterów.")
        self.game.ui_log("Ustawianie pozycji startowych bohaterów.")
        ui_idle_hint = getattr(self.game, "ui_idle_hint", None)
        logger.info(starting_positions)

        def _finish_setup() -> State:
            self.game.heroes = heroes
            if getattr(self.game, "is_generated_encounter", None) and self.game.is_generated_encounter():
                from .combat import Combat

                return Combat(self.game)
            return HeroesTurn(self.game)

        def _setup_single_hero(preselected_hero: Hero | None = None) -> bool:
            hero = preselected_hero or self._pick_or_create_hero(used_character_ids)
            if hero is None:
                self.game.ui_log("Nie wybrano bohatera. Spróbuj ponownie.")
                return False

            hero_name = str(getattr(hero, "name", "Bohater") or "Bohater")
            logger.info("Wybierz pole startowe dla bohatera %s.", hero_name)
            self.game.ui_log(
                f"Wybierz puste pole startowe dla bohatera {hero_name}, klikając jedno z podświetlonych pól."
            )
            if callable(ui_idle_hint):
                ui_idle_hint(
                    "Wskaż miejsce dla figurki",
                    f"Wybierz puste pole startowe dla bohatera {hero_name}, klikając jedno z podświetlonych pól.",
                )
            self.game.conn.set_leds(starting_positions, consts.MOVE_FIELD_RGB) # usunac pozycje zajete
            time.sleep(0.12)
            logger.info("Odczytuje wybrane pole startowe...")
            pos = self.game.conn.scan_board(starting_positions)
            self.game.conn.leds_off()
            if pos is None:
                self.game.ui_log("Nie odczytano pola. Spróbuj ponownie.")
                return False
            prompt = (
                f"Wybrane pole startowe dla bohatera {hero_name}: {pos}.\n"
                "Postaw teraz figurkę na tym polu i potwierdź Enterem."
            )
            ui = getattr(self.game, "ui", None)
            if ui is not None and getattr(ui, "enabled", False) and hasattr(ui, "prompt_info"):
                try:
                    ui.prompt_info("Ustaw figurkę bohatera", prompt_long=prompt, source="hero_setup_place")
                except Exception:
                    self.game.ui_log(prompt)
            else:
                self.game.ui_log(prompt)
            try:
                self.game.board.place(hero, pos)
            except ValueError as exc:
                logger.error("Nie można ustawić bohatera: %s", exc)
                return False
            heroes.append(hero)
            char_id = str(getattr(hero, "character_id", "") or "").strip().lower()
            if char_id:
                used_character_ids.add(char_id)
            logger.info(
                f"Bohater ustawiony na pozycji {pos}."
            )
            self._maybe_prompt_chameleon_gnome(hero)
            self._maybe_prompt_advanced_alchemy(hero)
            self._maybe_prepare_spells(hero)
            self.game.ui_hero(hero, note=f"Ustawiony na polu startowym {pos}")
            self.game.ui_log(f"Bohater ustawiony na pozycji {pos}.")
            return True

        while getattr(self.game, "preselected_character_ids", None):
            hero = self._consume_preselected_hero(used_character_ids)
            if hero is None:
                continue
            _setup_single_hero(hero)

        if preselected_count and any(getattr(hero, "position", None) is not None for hero in heroes):
            self.game.ui_log("Setup bohaterów zakończony automatycznie z wybranych postaci.")
            return _finish_setup()

        while True:
            has_hero_on_board = any(getattr(hero, "position", None) is not None for hero in heroes)
            if not has_hero_on_board:
                if not _setup_single_hero():
                    continue
                continue
            if has_hero_on_board:
                options = [
                    {
                        "id": "__start_game__",
                        "label": "Graj",
                        "desc": "Rozpocznij grę z aktualnie ustawionymi bohaterami.",
                        "key": "enter",
                    },
                    {
                        "id": "__add_hero__",
                        "label": "Dodaj kolejnego bohatera",
                        "desc": "Wybierz kolejnego bohatera i ustaw jego figurkę na planszy.",
                        "key": "*",
                    },
                ]
                answer = self._prompt_menu_choice(
                    title="Setup bohaterów",
                    subtitle="Enter: graj, *: dodaj bohatera",
                    source="hero_setup_next",
                    options=options,
                    layout="menu_numpad",
                )
                picked = self._decode_menu_choice(answer or "", options) if answer else None
                if picked == "__start_game__":
                    logger.info("Setup bohaterów zakończony przez opcję Graj.")
                    self.game.ui_log("Setup bohaterów zakończony. Start gry.")
                    break
                if picked == "__add_hero__":
                    _setup_single_hero()
                    continue
        return _finish_setup()

    def _character_repository(self) -> CharacterRepository:
        return CharacterRepository(PROJECT_ROOT / "data" / "heroes")

    def _pick_or_create_hero(self, used_character_ids: set[str]) -> Hero | None:
        repo = self._character_repository()
        base_options = list_character_menu_options(repo, exclude_ids=used_character_ids)
        options: list[dict[str, Any]] = []
        for option in base_options:
            enriched = dict(option)
            snapshot = repo.load_character(str(option.get("id") or ""))
            preview = self._build_hero_preview_payload(snapshot, fallback_label=str(option.get("label") or ""))
            if preview:
                enriched["hero_preview"] = preview
            options.append(enriched)
        create_option = {
            "id": "__create_new__",
            "label": "Stwórz nowego bohatera",
            "desc": "Uruchamia pełny pipeline tworzenia postaci.",
            "key": "*",
            "hero_preview": {
                "name": "Nowy bohater",
                "note": "Uruchamia kreator tworzenia postaci.",
                "image": "/static/placeholder.png",
            },
        }
        options_with_create = list(options) + [create_option]

        if not options:
            self.game.ui_log("Brak zapisanych bohaterów. Uruchamiam tworzenie nowej postaci.")
            created = create_character(self.game, repo)
            if created is None:
                return None
            return created.hero

        answer = self._prompt_menu_choice(
            title="Wybór Bohatera",
            subtitle="8 góra, 2 dół, Enter potwierdzenie, * nowy bohater",
            source="hero_select",
            options=options_with_create,
            layout="menu_numpad",
        )
        if not answer:
            return None
        picked = self._decode_menu_choice(answer, options_with_create)
        if not picked:
            return None
        if picked == "__create_new__":
            created = create_character(self.game, repo)
            if created is None:
                return None
            return created.hero

        snapshot = repo.load_character(picked)
        if snapshot is None:
            self.game.ui_log(f"Nie udało się wczytać bohatera '{picked}'.")
            return None
        hero = hero_from_snapshot(snapshot)
        self.game.ui_log(f"Wczytano bohatera: {getattr(hero, 'name', picked)}.")
        return hero

    def _consume_preselected_hero(self, used_character_ids: set[str]) -> Hero | None:
        queue = getattr(self.game, "preselected_character_ids", None)
        if queue is None:
            return None
        repo = self._character_repository()
        while queue:
            picked = str(queue.popleft() or "").strip().lower()
            if not picked or picked in used_character_ids:
                continue
            snapshot = repo.load_character(picked)
            if snapshot is None:
                self.game.ui_log(f"Nie udało się wczytać preselected bohatera '{picked}'.")
                continue
            hero = hero_from_snapshot(snapshot)
            self.game.ui_log(f"Wczytano bohatera: {getattr(hero, 'name', picked)}.")
            return hero
        return None

    def _prompt_menu_choice(
        self,
        *,
        title: str,
        subtitle: str,
        source: str,
        options: list[dict[str, Any]],
        layout: str = "dialog",
    ) -> str | None:
        if not options:
            return None
        ui = getattr(self.game, "ui", None)
        choice_meta = []
        for idx, option in enumerate(options, start=1):
            entry: dict[str, Any] = {
                "raw": option["id"],
                "label": option["label"],
                "desc": option.get("desc") or "",
                "key": option.get("key") or str(idx),
            }
            for key, value in option.items():
                if key in {"id", "label", "desc", "key"}:
                    continue
                entry[key] = value
            choice_meta.append(entry)
        if ui is not None and hasattr(ui, "prompt_choice"):
            try:
                answer = ui.prompt_choice(
                    title,
                    choices=[item["label"] for item in choice_meta],
                    source=source,
                    layout=layout,
                    title=title,
                    subtitle=subtitle,
                    choice_meta=choice_meta,
                )
                if answer:
                    return str(answer)
            except Exception:
                pass
        elif ui is None or getattr(ui, "allow_cli_fallback", False):
            try:
                return input(title + " ").strip() or None
            except Exception:
                return None
        return None

    @staticmethod
    def _decode_menu_choice(raw: str, options: list[dict[str, str]]) -> str | None:
        text = str(raw or "").strip()
        if not text:
            return None
        by_id = {str(item["id"]).strip().lower(): str(item["id"]).strip().lower() for item in options}
        by_label = {str(item["label"]).strip().lower(): str(item["id"]).strip().lower() for item in options}
        by_key = {
            str(item.get("key") or "").strip().lower(): str(item["id"]).strip().lower()
            for item in options
            if str(item.get("key") or "").strip()
        }
        low = text.lower()
        if low in by_id:
            return by_id[low]
        if low in by_label:
            return by_label[low]
        if low in by_key:
            return by_key[low]
        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(options):
                return str(options[idx]["id"]).strip().lower()
        return None

    @staticmethod
    def _build_hero_preview_payload(snapshot: dict[str, Any] | None, *, fallback_label: str = "") -> dict[str, Any] | None:
        if not isinstance(snapshot, dict):
            return None

        def _as_dict(value: Any) -> dict[str, Any]:
            return dict(value) if isinstance(value, dict) else {}

        def _as_list(value: Any) -> list[Any]:
            return list(value) if isinstance(value, list) else []

        ability_scores = _as_dict(snapshot.get("ability_scores"))
        ability_modifiers = _as_dict(snapshot.get("ability_modifiers"))
        skill_ranks = _as_dict(snapshot.get("skill_ranks"))
        save_ranks = _as_dict(snapshot.get("save_ranks"))

        status_ids = [
            str(item).strip()
            for item in _as_list(snapshot.get("status_ids"))
            if str(item).strip()
        ]
        for item in _as_list(snapshot.get("class_feat_ids")):
            feat_id = str(item).strip()
            if feat_id and feat_id not in status_ids:
                status_ids.append(feat_id)
        statuses = [localize_term_pl(item) for item in status_ids]

        return {
            "character_id": str(snapshot.get("character_id") or "").strip().lower(),
            "name": str(snapshot.get("name") or fallback_label or "Bohater"),
            "note": f"Poziom {int(snapshot.get('level') or 1)}",
            "level": int(snapshot.get("level") or 1),
            "class_id": str(snapshot.get("class_id") or ""),
            "ancestry_id": str(snapshot.get("ancestry_id") or ""),
            "heritage_id": str(snapshot.get("heritage_id") or ""),
            "background_label": str(snapshot.get("background_label") or ""),
            "background_feat_id": str(snapshot.get("background_feat_id") or ""),
            "image": str(snapshot.get("portrait_image") or snapshot.get("image") or "/static/placeholder.png"),
            "ac": snapshot.get("ac"),
            "max_hp": snapshot.get("max_hp"),
            "base_speed_feet": snapshot.get("base_speed_feet"),
            "speed_feet": snapshot.get("speed_feet", snapshot.get("base_speed_feet")),
            "ability_scores": ability_scores,
            "ability_modifiers": ability_modifiers,
            "skill_ranks": skill_ranks,
            "save_ranks": save_ranks,
            "trained_skills": _as_list(snapshot.get("trained_skills")),
            "lore_skills": _as_list(snapshot.get("lore_skills")),
            "statuses": statuses,
            "money_text": snapshot.get("money_text"),
            "bulk_summary": _as_dict(snapshot.get("bulk_summary")),
        }

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

    def _maybe_prompt_background(self, hero: Hero) -> None:
        statuses = list(getattr(hero, "statuses", []) or [])
        for status in statuses:
            data = getattr(status, "data", None) or {}
            if bool(data.get("is_background")):
                return

        definitions = list(BACKGROUND_DEFINITIONS)
        if not definitions:
            self.game.ui_log("Tlo: brak zdefiniowanych teł.")
            return

        label_to_key: dict[str, str] = {}
        choices: list[str] = []
        for definition in definitions:
            key = str(getattr(definition, "key", "") or "").strip().lower()
            fallback_label = str(getattr(definition, "label", "") or key).strip()
            label = str(localize_term_pl(f"background_{key}") or localize_term_pl(key) or fallback_label).strip()
            if not key or not label:
                continue
            label_to_key[label] = key
            if fallback_label:
                label_to_key[fallback_label] = key
            choices.append(label)
        if not choices:
            self.game.ui_log("Tlo: brak poprawnych opcji wyboru.")
            return

        prompt = "Tlo: wybierz tlo postaci"
        answer: str | None = None
        ui = getattr(self.game, "ui", None)
        if ui is not None and hasattr(ui, "prompt_choice"):
            answer = ui.prompt_choice(prompt, choices=choices, source="setup")
        elif ui is None or getattr(ui, "allow_cli_fallback", False):
            try:
                answer = input(prompt + " ").strip() or None
            except Exception:
                answer = None

        selected_key: str | None = None
        if answer:
            raw = str(answer).strip()
            if raw.isdigit():
                idx = int(raw) - 1
                if 0 <= idx < len(choices):
                    selected_key = label_to_key.get(choices[idx])
            if selected_key is None:
                selected_key = label_to_key.get(raw)
            if selected_key is None:
                norm = raw.lower().replace(" ", "_")
                direct = get_background_status(norm)
                if direct is not None:
                    selected_key = str((direct.data or {}).get("background_key") or "").strip().lower()

        if not selected_key:
            self.game.ui_log("Tlo: nie wybrano poprawnej opcji.")
            return

        background_status = get_background_status(selected_key)
        if background_status is None:
            self.game.ui_log(f"Tlo: nie znaleziono statusu '{selected_key}'.")
            return
        if not hero.add_status(background_status):
            self.game.ui_log("Tlo: nie udalo sie dodac wybranego tla.")
            return

        chosen_label = str((background_status.data or {}).get("background_label") or background_status.display_label)
        chosen_feat = str((background_status.data or {}).get("background_feat_id") or "").strip()
        if chosen_feat:
            self.game.ui_log(
                f"Tlo: wybrano {chosen_label}. Dodany feat: {chosen_feat}."
            )
        else:
            self.game.ui_log(f"Tlo: wybrano {chosen_label}.")

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
        elif ui is None or getattr(ui, "allow_cli_fallback", False):
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
        if not hero.has_status("FamiliarOwner") and not hero.has_status("alchemist_familiar_guidance"):
            return
        status = self._get_status(hero, "FamiliarOwner") or self._get_status(hero, "alchemist_familiar_guidance")
        if status is None:
            return
        data = getattr(status, "data", None) or {}
        data.setdefault("familiar_mode", None)
        data.setdefault("familiar_guidance_skill", None)
        choices = [
            "Scout (Perception)",
            "Guidance (Skill)",
            "Distract (Enemy)",
            "Deliver Touch Spell",
            "Scent/Seek",
        ]
        choice_meta = [
            {
                "raw": "Scout (Perception)",
                "label": "Scout (Perception)",
                "desc": "Fluff: Chowaniec wypatruje zagrozen.\nMechanika:\n- Kiedy: Po wyborze trybu i uzyciu akcji Komenderuj chowanca.\n- Efekt: Jednorazowy +2 circumstance do najblizszego testu Percepcji.",
                "key": "1",
            },
            {
                "raw": "Guidance (Skill)",
                "label": "Guidance (Skill)",
                "desc": "Fluff: Chowaniec wspiera cie przy wybranej umiejetnosci.\nMechanika:\n- Kiedy: Po wyborze trybu i uzyciu akcji Komenderuj chowanca.\n- Efekt: Jednorazowy +1 circumstance do wybranego skilla.",
                "key": "2",
            },
            {
                "raw": "Distract (Enemy)",
                "label": "Distract (Enemy)",
                "desc": "Fluff: Chowaniec rozprasza przeciwnika we wlasciwym momencie.\nMechanika:\n- Kiedy: Po wyborze celu i uzyciu akcji Komenderuj chowanca.\n- Efekt: Wybrany wrog dostaje -1 do najblizszego ataku wrecz; efekt znika po tym ataku.",
                "key": "3",
            },
            {
                "raw": "Deliver Touch Spell",
                "label": "Deliver Touch Spell",
                "desc": "Fluff: Chowaniec przenosi energie czaru dotykowego.\nMechanika:\n- Kiedy: Przy kolejnym czarze dotykowym po uzyciu akcji Komenderuj chowanca.\n- Efekt: Zasieg czaru dotykowego rosnie z 5 ft do 10 ft i efekt znika po uzyciu.",
                "key": "4",
            },
            {
                "raw": "Scent/Seek",
                "label": "Scent/Seek",
                "desc": "Fluff: Chowaniec szuka ukrytych obiektow po zapachu i ruchu.\nMechanika:\n- Kiedy: Natychmiast po uzyciu akcji Komenderuj chowanca.\n- Efekt: Gra informuje, czy w poblizu sa ukryte obiekty.",
                "key": "5",
            },
        ]
        prompt = "Chowaniec: wybierz tryb dzialania (staly dla akcji Komenderuj chowanca)."
        answer: str | None = None
        ui = getattr(self.game, "ui", None)
        if ui is not None and hasattr(ui, "prompt_choice"):
            answer = ui.prompt_choice(
                prompt,
                choices=choices,
                source="setup",
                layout="menu_numpad",
                choice_meta=choice_meta,
            )
        elif ui is None or getattr(ui, "allow_cli_fallback", False):
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
            elif ui is None or getattr(ui, "allow_cli_fallback", False):
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

    @staticmethod
    def _normalize_event_name(raw: str | None) -> str:
        return str(raw or "").strip().lower()

    def _advanced_alchemy_event_choices(self) -> list[str]:
        try:
            import GameObjects.events.all_events  # noqa: F401
            from GameObjects.events.bombs.base_alchemical_bomb_event import BaseAlchemicalBombEvent
            from GameObjects.events.elixirs.base_elixir_event import BaseElixirEvent
            from GameObjects.events.poisons.base_poison_event import BasePoisonEvent
            from GameObjects.events.registry import list_events
        except Exception:
            return []
        base_types = (BaseAlchemicalBombEvent, BaseElixirEvent, BasePoisonEvent)
        choices: list[str] = []
        for name, cls in list_events().items():
            try:
                if not issubclass(cls, base_types):
                    continue
            except Exception:
                continue
            choices.append(str(name).strip().lower())
        return sorted(set(choices))

    def _advanced_alchemy_choice_meta(self, event_choices: list[str]) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        for event_name in list(event_choices or []):
            raw = str(event_name or "").strip().lower()
            if not raw:
                continue
            label = localize_term_pl(raw)
            hint = localized_hint_pl(raw) or "Przedmiot alchemiczny gotowy do użycia po stworzeniu."
            desc = (
                f"Fluff: Przygotowujesz {label.lower()} w laboratorium polowym.\n"
                "Mechanika:\n"
                "- Kiedy: W fazie startowej, podczas Advanced Alchemy.\n"
                f"- Efekt: Zużywasz 1 reagent i tworzysz 2 sztuki; {hint}"
            )
            out.append(
                {
                    "raw": raw,
                    "label": label,
                    "desc": desc,
                    "key": "",
                }
            )
        out.append(
            {
                "raw": "end",
                "label": "Zakończ",
                "desc": (
                    "Fluff: Odkładasz fiolki i kończysz przygotowania.\n"
                    "Mechanika:\n"
                    "- Kiedy: W dowolnym momencie wyboru eventu.\n"
                    "- Efekt: Kończy Advanced Alchemy bez zużywania kolejnych reagentów."
                ),
                "key": "",
            }
        )
        return out

    @staticmethod
    def _advanced_alchemy_available_reagents(hero: Hero) -> int:
        level = int(getattr(hero, "level", 1) or 1)
        int_mod: int | None = None
        try:
            int_mod = int(getattr(hero, "intelligence_modifier"))
        except Exception:
            int_mod = None
        if int_mod is None:
            mods = getattr(hero, "ability_modifiers", None)
            if isinstance(mods, dict):
                try:
                    int_mod = int(mods.get("intelligence"))
                except Exception:
                    int_mod = None
        if int_mod is None:
            score = getattr(hero, "intelligence", None)
            try:
                score_int = int(score)
                int_mod = (score_int - 10) // 2
            except Exception:
                int_mod = 0
        return max(0, level + int(int_mod or 0))

    def _prompt_advanced_alchemy_reagent_budget(self, *, available_reagents: int | None = None) -> int | None:
        max_budget = max(0, int(available_reagents or 0))
        options = [
            {
                "id": str(value),
                "label": str(value),
                "desc": f"Zużyj {value} reagentów.",
                "key": str(value),
            }
            for value in range(0, max_budget + 1)
        ]
        options.append(
            {
                "id": "end",
                "label": "Zakończ",
                "desc": "Pomiń Advanced Alchemy.",
                "key": "end",
            }
        )
        while True:
            header = "Advanced Alchemy: podaj liczbę reagentów do zużycia"
            if available_reagents is not None:
                header += f" [dostępne: {available_reagents}]"
            header += " (lub end aby zakończyć)"
            raw = self._prompt_menu_choice(
                title="Advanced Alchemy",
                subtitle=header,
                source="advanced_alchemy_budget",
                options=options,
                layout="menu_numpad",
            )
            if raw is None:
                return None
            normalized = self._decode_menu_choice(str(raw or ""), options) or self._normalize_event_name(raw)
            if normalized == "end":
                return None
            try:
                budget = int(normalized)
            except Exception:
                self.game.ui_log("Advanced Alchemy: niepoprawna liczba reagentów.")
                continue
            if budget < 0:
                self.game.ui_log("Advanced Alchemy: liczba reagentów nie może być ujemna.")
                continue
            return budget

    def _maybe_prompt_advanced_alchemy(self, hero: Hero) -> None:
        if not hero.has_status("advanced_alchemy"):
            return
        try:
            from GameObjects.items.inventory import add_alchemical_item
        except Exception:
            self.game.ui_log("Advanced Alchemy: brak modułu itemów alchemicznych.")
            return

        allowed = self._advanced_alchemy_event_choices()
        if not allowed:
            self.game.ui_log("Advanced Alchemy: brak dostępnych eventów alchemicznych.")
            return

        try:
            preview = ", ".join(allowed[:10]) + (", ..." if len(allowed) > 10 else "")
            available_reagents = self._advanced_alchemy_available_reagents(hero)
            ui = getattr(self.game, "ui", None)
            if ui is not None and hasattr(ui, "prompt_info"):
                ui.prompt_info(
                    "Advanced Alchemy",
                    prompt_long=(
                        "Wybierz liczbę reagentów, a następnie event alchemiczny dla każdego reagenta.\n"
                        "Każdy reagent tworzy 2 sztuki przedmiotu (bez preparation counter).\n"
                        f"Dostępne reagenty: {available_reagents}\n"
                        "Wpisz 'end', aby zakończyć crafting.\n"
                        f"Dostępne eventy: {preview}"
                    ),
                    source="advanced_alchemy",
                )
        except Exception:
            pass

        budget = self._prompt_advanced_alchemy_reagent_budget(
            available_reagents=self._advanced_alchemy_available_reagents(hero)
        )
        if budget is None:
            self.game.ui_log("Advanced Alchemy: zakończono bez craftingu.")
            return
        if budget == 0:
            self.game.ui_log("Advanced Alchemy: 0 reagentów, pominięto crafting.")
            return

        created_total = 0
        crafting_choices = list(allowed) + ["end"]
        crafting_choice_meta = self._advanced_alchemy_choice_meta(allowed)
        crafting_options = [
            {
                "id": str(item.get("raw") or ""),
                "label": str(item.get("label") or ""),
                "desc": str(item.get("desc") or ""),
                "key": str(item.get("key") or ""),
            }
            for item in crafting_choice_meta
        ]
        for idx in range(1, budget + 1):
            while True:
                raw_choice = self._prompt_menu_choice(
                    title="Advanced Alchemy",
                    subtitle=f"Wybierz event alchemiczny [{idx}/{budget}] albo zakończ.",
                    source="advanced_alchemy_choice",
                    options=crafting_options,
                    layout="menu_numpad",
                )
                if raw_choice is None:
                    self.game.ui_log(
                        f"Advanced Alchemy: przerwano crafting po {created_total} stworzonych przedmiotach."
                    )
                    return
                choice = self._decode_menu_choice(str(raw_choice or ""), crafting_options) or self._normalize_event_name(raw_choice)
                if choice == "end":
                    self.game.ui_log(
                        f"Advanced Alchemy: przerwano crafting po {created_total} stworzonych przedmiotach."
                    )
                    return
                if choice not in allowed:
                    self.game.ui_log(f"Advanced Alchemy: '{choice}' nie jest poprawnym eventem alchemicznym.")
                    continue
                add_alchemical_item(
                    hero,
                    event_name=choice,
                    preparation_counter=0,
                    prepared_by_advanced_alchemy=True,
                )
                add_alchemical_item(
                    hero,
                    event_name=choice,
                    preparation_counter=0,
                    prepared_by_advanced_alchemy=True,
                )
                created_total += 2
                self.game.ui_log(
                    f"Advanced Alchemy: stworzono 2x {choice} ({idx}/{budget})."
                )
                break
        self.game.ui_log(f"Advanced Alchemy: zakończono crafting. Łącznie stworzono {created_total} przedmiotów.")

    def _maybe_prepare_spells(self, hero: Hero) -> None:
        try:
            state = initialize_actor_spell_management(
                self.game,
                hero,
                prompt=True,
                enforce=True,
            )
        except Exception:
            return
        if not bool(state.get("enabled", False)):
            return
        known = state.get("known", {}) or {}
        summary = ", ".join(
            [
                f"cantrip={len(list(known.get('cantrip', []) or []))}",
                f"rank1={len(list(known.get('rank_1', []) or []))}",
                f"focus={len(list(known.get('focus', []) or []))}",
            ]
        )
        self.game.ui_log(f"{getattr(hero, 'name', 'Bohater')}: spell management aktywny ({summary}).")
