from __future__ import annotations

import logging
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, List, Optional
from GameObjects.interactions_mixin import prompt_for_roll

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import actions  # noqa: F401  # rejestracja akcji przy starcie stanu walki
from board import consts
from GameObjects.companions import build_animal_companion
from GameObjects.Enemies.behaviors import get_behavior
from .base import State
from .encounter_finished import EncounterFinished
from .heroes_turns import HeroesTurn
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
from GameObjects.events import EventContext
from GameObjects.events.registry import dispatch_event, list_events
import GameObjects.events.all_events  # noqa: F401
from enemy_prompting import clear_enemy_highlight, enemy_highlight, enemy_prompt_step
from narration import narrate_action_result
from prompt_copy import prompt_value
from prompt_text_catalog import render_prompt_text

logger = logging.getLogger(__name__)


def _format_hp_summary(actor: Any) -> str:
    try:
        from combat.hp_engine import computed_max_hp, current_hp

        hp = current_hp(actor)
        max_hp = computed_max_hp(actor)
        if hp is None or max_hp is None:
            return "nieznane"
        return f"{int(hp)}/{int(max_hp)}"
    except Exception:
        return "nieznane"


def _build_incapacitated_prompt_content(actor: Any, *, recovery_message: str | None = None) -> dict[str, str]:
    try:
        from statuses import death_threshold, dying_value, is_stable, is_unconscious, wounded_value

        dying = max(0, int(dying_value(actor) or 0))
        wounded = max(0, int(wounded_value(actor) or 0))
        stable = bool(is_stable(actor))
        unconscious = bool(is_unconscious(actor))
        threshold = max(1, int(death_threshold(actor) or 4))
    except Exception:
        dying = 0
        wounded = 0
        stable = False
        unconscious = False
        threshold = 4

    hp_summary = _format_hp_summary(actor)
    recovery_message_block = f"{str(recovery_message).strip()}\n\n" if str(recovery_message or "").strip() else ""
    state_summary = (
        str(recovery_message).strip()
        if str(recovery_message or "").strip()
        else f"{getattr(actor, 'name', 'Postać')} nie może teraz działać."
    )
    rendered = render_prompt_text(
        "combat.hero_incapacitated",
        state_summary=state_summary,
        recovery_message_block=recovery_message_block,
        hp_summary=hp_summary,
        dying_line=(str(dying) if dying > 0 else "brak"),
        wounded_line=(str(wounded) if wounded > 0 else "brak"),
        unconscious_line=("tak" if unconscious else "nie"),
        stable_line=("tak" if stable else "nie"),
        threshold=threshold,
    )
    body = str(rendered.get("body_markdown") or "").strip()
    details = str(rendered.get("details_markdown") or "").strip()
    summary = str(rendered.get("summary") or state_summary).strip()
    if not body:
        body = (
            f"**Aktualny stan**\n"
            f"- HP: {hp_summary}\n"
            f"- Dying: {dying if dying > 0 else 'brak'}\n"
            f"- Wounded: {wounded if wounded > 0 else 'brak'}\n"
            f"- Unconscious: {'tak' if unconscious else 'nie'}\n"
            f"- Stable: {'tak' if stable else 'nie'}\n"
            f"- Śmierć nastąpi przy Dying {threshold}."
        )
    return {
        "summary": summary,
        "body_markdown": body,
        "details_markdown": details,
    }


def _build_incapacitated_prompt_body(actor: Any, *, recovery_message: str | None = None) -> str:
    content = _build_incapacitated_prompt_content(actor, recovery_message=recovery_message)
    parts = [
        str(content.get("body_markdown") or "").strip(),
        str(content.get("details_markdown") or "").strip(),
    ]
    return "\n\n".join(part for part in parts if part)


class Combat(State):
    ACTION_LIMIT = 3

    def __init__(self, game):
        super().__init__(game)
        self.initiative_order: list[Any] = []
        self.turn_index: int = 0
        self.actions_used: dict[Any, int] = {}
        self.out_of_turn_actions_used: dict[Any, int] = {}
        self.turn_initialized: set[Any] = set()
        self._reaction_resolution_keys: set[tuple[Any, ...]] = set()
        self._reaction_event_seq: int = 0
        self.delayed: set[Any] = set()
        self._initiatives_ready = False
        self.base_initiative: dict[Any, int] = {}
        self.temp_initiative: dict[Any, int] = {}
        self.base_order: list[Any] = []      # stała kolejność bazowa
        self.round_queue: list[Any] = []     # kolejka na bieżącą rundę (konsumowana)
        self.round_index: int = 1
        self.attack_state: dict[Any, dict[str, object]] = {}
        self.status_initiative_penalty: dict[Any, int] = {}
        self.animal_companions: dict[str, Any] = {}

    def _action_limit(self, actor: Any) -> int:
        base = int(self.ACTION_LIMIT)
        try:
            from statuses import action_limit_modifier

            base += int(action_limit_modifier(actor) or 0)
        except Exception:
            pass
        return max(0, min(4, int(base)))

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
        skip_initial_initiative = bool(getattr(self.game, "_pending_preinitiative_ambush", False))
        self._reset_heroes_initiative()
        if not skip_initial_initiative:
            self._ensure_initiative_order()
        self._deploy_pending_animal_companions()

    def on_exit(self):
        logger.info("Zakończenie walki.")
        self.game.ui_log("Zakończenie walki.")
        self._cleanup_animal_companions()
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
                try:
                    remover_status("monk_stance_lock")
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
            try:
                from GameObjects.events.monk_feat_events import _clear_monk_stance_effects

                _clear_monk_stance_effects(actor)
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
                filtered = []
                for status in list(statuses):
                    data = getattr(status, "data", None) or {}
                    if bool(data.get("expire_on_combat_end", False)):
                        continue
                    filtered.append(status)
                actor.statuses = filtered

    @staticmethod
    def _actor_id(actor: Any) -> str:
        return str(getattr(actor, "object_id", None) or getattr(actor, "name", None) or id(actor))

    @staticmethod
    def _has_status(actor: Any, status_id: str) -> bool:
        checker = getattr(actor, "has_status", None)
        if callable(checker):
            try:
                return bool(checker(status_id))
            except Exception:
                return False
        for status in getattr(actor, "statuses", []) or []:
            if getattr(status, "id", status) == status_id:
                return True
        return False

    @staticmethod
    def _is_actor_dead(actor: Any) -> bool:
        if actor is None:
            return False
        try:
            from statuses import is_dead

            return bool(is_dead(actor))
        except Exception:
            return False

    @staticmethod
    def _is_actor_unconscious(actor: Any) -> bool:
        if actor is None:
            return False
        try:
            from statuses import is_unconscious

            return bool(is_unconscious(actor))
        except Exception:
            return False

    def _is_player_side_actor(self, actor: Any) -> bool:
        if actor in list(getattr(self.game, "heroes", []) or []):
            return True
        return actor in list(getattr(self, "animal_companions", {}).values())

    def _show_incapacitated_prompt(self, actor: Any, *, title: str, source: str, dedupe_key: str, recovery_message: str | None = None) -> None:
        if not self._is_player_side_actor(actor):
            return
        player_prompt = getattr(self.game, "player_prompt", None)
        if player_prompt is None:
            return
        try:
            content = _build_incapacitated_prompt_content(actor, recovery_message=recovery_message)
            player_prompt.info(
                title,
                body_markdown=content.get("body_markdown"),
                source=source,
                summary=content.get("summary"),
                details_markdown=content.get("details_markdown") or None,
                scope_key=f"hero_turn:incapacitated:{self._actor_id(actor)}",
                dedupe_key=dedupe_key,
                priority="action",
                semantic_type="required_action",
            )
        except Exception:
            logger.debug("Nie udało się pokazać promptu o stanie incapacitated dla %s.", actor, exc_info=True)

    def get_animal_companion(self, owner) -> Any | None:
        self._purge_dead_animal_companions()
        owner_id = self._actor_id(owner)
        companion = self.animal_companions.get(owner_id)
        if companion is None:
            board = getattr(self.game, "board", None)
            iterator = getattr(board, "_iter_occupants", None)
            if callable(iterator):
                for candidate in iterator():
                    if str(getattr(candidate, "owner_id", "") or "") != owner_id:
                        continue
                    if getattr(candidate, "companion_type", None) is None:
                        continue
                    if getattr(candidate, "position", None) is None:
                        continue
                    self.animal_companions[owner_id] = candidate
                    companion = candidate
                    break
            if companion is None:
                return None
        if getattr(companion, "position", None) is None:
            return None
        return companion

    def _deploy_pending_animal_companions(self) -> None:
        for hero in list(getattr(self.game, "heroes", []) or []):
            self._deploy_animal_companion_for_owner(hero)

    def _advance_companion_setup_prompt(self, owner, companion) -> None:
        owner_name = str(getattr(owner, "name", "Bohater") or "Bohater")
        companion_type = str(getattr(companion, "companion_type", "towarzysz") or "towarzysz").replace("_", " ")
        pending = [
            hero
            for hero in list(getattr(self.game, "heroes", []) or [])
            if getattr(hero, "position", None) is not None and getattr(hero, "initiative", None) is None
        ]
        if pending:
            title = "Towarzysz ustawiony"
            text = (
                f"{owner_name}: {companion_type} stoi już na planszy. "
                "Wybierz kolejnego bohatera, aby ustawić inicjatywę."
            )
            next_hint = "Kliknij figurkę kolejnego bohatera na planszy."
        else:
            title = "Towarzysz ustawiony"
            text = (
                f"{owner_name}: {companion_type} stoi już na planszy. "
                "Gra przechodzi do następnego kroku."
            )
            next_hint = "Śledź inicjatywę i wybierz akcję aktywnego aktora."
        try:
            ui_idle_hint = getattr(self.game, "ui_idle_hint", None)
            if callable(ui_idle_hint):
                ui_idle_hint(title, text)
        except Exception:
            logger.debug("Nie udało się odświeżyć idle hint po ustawieniu towarzysza.", exc_info=True)
        try:
            ui_narration = getattr(self.game, "ui_narration", None)
            if callable(ui_narration):
                ui_narration(
                    text,
                    summary="Co się dzieje",
                    source="animal_companion_setup",
                    channel="timeline",
                    blocking=False,
                    next_hint=next_hint,
                )
        except Exception:
            logger.debug("Nie udało się wysłać narracji po ustawieniu towarzysza.", exc_info=True)

    def _deploy_animal_companion_for_owner(self, owner) -> None:
        if owner is None:
            return
        if not self._has_status(owner, "animal_companion"):
            return
        if getattr(owner, "position", None) is None:
            return
        owner_id = self._actor_id(owner)
        if owner_id in self.animal_companions and getattr(self.animal_companions[owner_id], "position", None) is not None:
            return
        board = getattr(self.game, "board", None)
        if board is None:
            return
        spawn_options = self._find_spawn_positions(owner)
        if not spawn_options:
            self.game.ui_log(
                f"{getattr(owner, 'name', 'Druid')}: brak wolnego pola do ustawienia zwierzecego towarzysza."
            )
            return
        try:
            self.game.ui_log(
                f"Ustaw figurke zwierzecego towarzysza dla {getattr(owner, 'name', 'bohatera')}."
            )
        except Exception:
            pass
        try:
            ui_idle_hint = getattr(self.game, "ui_idle_hint", None)
            if callable(ui_idle_hint):
                ui_idle_hint(
                    "Ustaw figurkę towarzysza",
                    (
                        f"Gra czeka na klik pola dla zwierzęcego towarzysza bohatera "
                        f"{getattr(owner, 'name', 'Bohater')}. Kliknij jedno z podświetlonych pól obok właściciela."
                    ),
                )
        except Exception:
            pass
        selected = None
        try:
            self.game.conn.set_leds(spawn_options, consts.HERO_HIGHLIGHT_RGB)
            try:
                self.game.ui_event(
                    "board_scan_wait",
                    {
                        "kind": "animal_companion_spawn",
                        "owner_id": owner_id,
                        "positions": [list(pos) for pos in spawn_options],
                    },
                )
            except Exception:
                pass
            timeout_s = float(getattr(consts, "HERO_SELECTION_SCAN_TIMEOUT_S", None) or 45.0)
            try:
                try:
                    selected = self.game.conn.scan_board(spawn_options, timeout_s=timeout_s)
                except TypeError:
                    selected = self.game.conn.scan_board(spawn_options)
                except Exception:
                    logger.debug("Skan pola dla zwierzęcego towarzysza nie zwrócił wyniku.", exc_info=True)
                    selected = None
            finally:
                try:
                    self.game.ui_event(
                        "board_scan_result",
                        {
                            "kind": "animal_companion_spawn",
                            "owner_id": owner_id,
                            "position": list(selected) if selected is not None else None,
                        },
                    )
                except Exception:
                    pass
        finally:
            try:
                self.game.conn.leds_off()
            except Exception:
                pass
        if selected not in spawn_options or not board.can_enter(selected, allow_occupied=False):
            valid = [p for p in spawn_options if board.can_enter(p, allow_occupied=False)]
            selected = valid[0] if valid else spawn_options[0]
        companion = build_animal_companion(owner)
        try:
            board.place(companion, selected)
        except Exception as exc:
            logger.error("Nie udalo sie ustawic zwierzecego towarzysza: %s", exc)
            return
        self.animal_companions[owner_id] = companion
        self.game.ui_log(
            f"{getattr(owner, 'name', 'Bohater')}: Zwierzecy towarzysz ({getattr(companion, 'companion_type', 'wolf')}) "
            f"ustawiony na {selected}."
        )
        self._advance_companion_setup_prompt(owner, companion)
        try:
            self.game.ui_companion(
                companion,
                note=(
                    f"Towarzysz: {getattr(companion, 'companion_type', 'wolf')} · "
                    f"Właściciel: {getattr(owner, 'name', 'Bohater')}"
                ),
            )
        except Exception:
            logger.debug("Nie udało się wysłać snapshotu UI companiona.", exc_info=True)

    def _find_spawn_positions(self, owner) -> list[tuple[int, int]]:
        board = getattr(self.game, "board", None)
        owner_pos = getattr(owner, "position", None)
        if board is None or owner_pos is None:
            return []
        max_search = max(int(getattr(board, "rows", 0) or 0), int(getattr(board, "cols", 0) or 0))
        if max_search <= 0:
            return []

        # BFS from owner_pos using can_traverse to respect walls (not just can_enter).
        # Karczma-style scenarios use walls between fields, not blocked_fields/obstacles,
        # so can_enter alone would allow placing on wall-enclosed fields.
        from collections import deque

        visited: set[tuple[int, int]] = {owner_pos}
        queue: deque[tuple[tuple[int, int], int]] = deque([(owner_pos, 0)])
        best_dist: int | None = None
        result: list[tuple[int, int]] = []

        _DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))

        while queue:
            pos, dist = queue.popleft()
            if best_dist is not None and dist > best_dist:
                break
            if dist > max_search:
                break
            px, py = pos
            for dx, dy in _DIRS:
                npos = (px + dx, py + dy)
                if npos in visited:
                    continue
                if not board.in_bounds(npos):
                    continue
                visited.add(npos)
                # allow_occupied=True for BFS propagation through heroes/companions;
                # wall barriers (is_blocked) still block traversal.
                if not board.can_traverse(pos, npos, allow_occupied=True):
                    continue
                # Valid spawn only if the field is actually empty.
                if board.can_enter(npos, allow_occupied=False):
                    if best_dist is None:
                        best_dist = dist + 1
                    result.append(npos)
                # Continue BFS through this field regardless of occupancy.
                queue.append((npos, dist + 1))

        return result

    def _cleanup_animal_companions(self) -> None:
        if not self.animal_companions:
            return
        board = getattr(self.game, "board", None)
        cleanup_lines: list[str] = []
        for owner_id, companion in list(self.animal_companions.items()):
            pos = getattr(companion, "position", None)
            if board is not None and pos is not None:
                try:
                    board.remove(pos)
                except Exception:
                    pass
            owner_name = getattr(companion, "owner_name", owner_id)
            companion_name = getattr(companion, "name", "Zwierzecy towarzysz")
            prompt = f"Koniec walki: zabierz figurke {companion_name} (owner: {owner_name})."
            cleanup_lines.append(f"- {companion_name} ({owner_name})")
            self.game.ui_log(prompt)
        self.animal_companions.clear()
        if cleanup_lines:
            body = (
                "Walka dobiegła końca. Zdejmij z planszy figurki zwierzęcych towarzyszy:\n"
                + "\n".join(cleanup_lines)
            )
            player_prompt = getattr(self.game, "player_prompt", None)
            if player_prompt is not None and hasattr(player_prompt, "card"):
                try:
                    player_prompt.card(
                        kind="result",
                        title="Zwierzęcy towarzysz",
                        summary="Koniec walki",
                        body_markdown=body,
                        priority="result",
                        scope_key="combat:companion",
                        dedupe_key="companion_cleanup:combat_end",
                        prompt_id="companion.cleanup",
                        ack_required=False,
                        pause_policy="passive",
                    )
                except Exception:
                    pass
            else:
                ui = getattr(self.game, "ui", None)
                if ui is not None and hasattr(ui, "prompt_info"):
                    try:
                        ui.prompt_info("Zwierzęcy towarzysz", prompt_long=body, source="animal_companion")
                    except Exception:
                        pass

    def _purge_dead_animal_companions(self) -> None:
        if not self.animal_companions:
            return
        board = getattr(self.game, "board", None)
        for owner_id, companion in list(self.animal_companions.items()):
            dead = False
            checker = getattr(companion, "is_dead", None)
            if callable(checker):
                try:
                    dead = bool(checker())
                except Exception:
                    dead = False
            if not dead:
                try:
                    dead = int(getattr(companion, "hp", 1) or 1) <= 0
                except Exception:
                    dead = False
            if not dead:
                continue
            pos = getattr(companion, "position", None)
            if board is not None and pos is not None:
                try:
                    board.remove(pos)
                except Exception:
                    pass
            try:
                self.game.ui_companion(companion, note="Pokonany towarzysz")
            except Exception:
                logger.debug("Nie udało się odświeżyć UI dla pokonanego companiona.", exc_info=True)
            self.animal_companions.pop(owner_id, None)
            companion_name = getattr(companion, "name", "Zwierzecy towarzysz")
            owner_name = getattr(companion, "owner_name", owner_id)
            message = f"{companion_name} zostal pokonany i znika z planszy."
            self.game.ui_log(message)
            player_prompt = getattr(self.game, "player_prompt", None)
            if player_prompt is not None and hasattr(player_prompt, "card"):
                try:
                    player_prompt.card(
                        kind="result",
                        title="Towarzysz pokonany",
                        summary=f"{companion_name} wypada z walki.",
                        body_markdown=(
                            f"**{companion_name}** ({owner_name}) zostal pokonany i znika z planszy.\n\n"
                            "Zdejmij figurke z pola, na ktorym stal towarzysz. "
                            "Dalsze skutki dla towarzysza rozlicz po walce zgodnie z zasadami scenariusza."
                        ),
                        priority="result",
                        scope_key="combat:companion",
                        dedupe_key=f"companion_defeated:{owner_id}:{getattr(companion, 'object_id', id(companion))}",
                        prompt_id="companion.defeated",
                        ack_required=False,
                        pause_policy="passive",
                    )
                except Exception:
                    logger.debug("Nie udało się wysłać karty o pokonanym companionie.", exc_info=True)

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
                try:
                    self._deploy_animal_companion_for_owner(hero)
                except Exception as exc:
                    logger.error("Nie udalo sie ustawic zwierzecego towarzysza dla %s: %s", getattr(hero, "name", hero), exc)
            pending = [h for h in heroes if getattr(h, "initiative", None) is None]

    def _roll_enemy_initiatives(self) -> None:
        for enemy in self.game.enemies:
            try:
                current = getattr(enemy, "initiative", None)
                val = int(current) if current is not None else int(enemy.roll_initiative())
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
            try:
                if int(getattr(enemy, "hp", 1) or 0) <= 0:
                    continue
            except Exception:
                pass
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
        self.out_of_turn_actions_used.clear()
        self.turn_initialized.clear()
        self._reaction_resolution_keys.clear()
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
        self.out_of_turn_actions_used.clear()
        self.turn_initialized.clear()
        self._reaction_resolution_keys.clear()
        self._reaction_event_seq = 0
        self.attack_state.clear()
        self.status_initiative_penalty.clear()
        self.base_order.clear()
        self.round_queue.clear()
        self.animal_companions.clear()
        try:
            self.initiative_order.clear()
        except Exception:
            self.initiative_order = []

    def _clear_combat_ui(self) -> None:
        self._clear_initiatives()
        if getattr(self.game, "ui", None):
            try:
                self.game.ui_event("initiative", {"round": None, "order": [], "active_id": None})
            except Exception:
                logger.debug("Nie udało się wyczyścić inicjatywy w UI po walce.", exc_info=True)
        ui_active_actor = getattr(self.game, "ui_active_actor", None)
        if callable(ui_active_actor):
            try:
                ui_active_actor(None)
            except Exception:
                logger.debug("Nie udało się wyczyścić aktywnego aktora w UI po walce.", exc_info=True)

    # --- Turn helpers ---
    def _cleanup_removed(self) -> bool:
        self._purge_dead_animal_companions()

        def _alive(objs: list[Any]) -> list[Any]:
            alive: list[Any] = []
            for obj in objs:
                if obj in self.game.heroes:
                    if getattr(obj, "position", None) is None:
                        continue
                    if self._is_actor_dead(obj):
                        continue
                elif obj in self.game.enemies:
                    if getattr(obj, "position", None) is None or getattr(obj, "hp", 1) <= 0:
                        continue
                else:
                    if getattr(obj, "position", None) is None:
                        continue
                    try:
                        if hasattr(obj, "hp") and int(getattr(obj, "hp", 1) or 0) <= 0:
                            continue
                    except Exception:
                        pass
                alive.append(obj)
            return alive

        before = (len(self.base_order), len(self.round_queue), len(self.initiative_order))
        self.base_order = _alive(self.base_order)
        self.round_queue = _alive(self.round_queue)
        self.initiative_order = list(self.round_queue)
        # usuń martwe z map inicjatywy
        for mapping in (self.base_initiative, self.temp_initiative):
            for dead in [k for k in list(mapping.keys()) if k not in self.base_order]:
                mapping.pop(dead, None)
        for dead in [k for k in list(self.status_initiative_penalty.keys()) if k not in self.base_order]:
            self.status_initiative_penalty.pop(dead, None)
        for dead in [k for k in list(self.actions_used.keys()) if k not in self.base_order]:
            self.actions_used.pop(dead, None)
        for dead in [k for k in list(self.out_of_turn_actions_used.keys()) if k not in self.base_order]:
            self.out_of_turn_actions_used.pop(dead, None)
        self.turn_initialized = {actor for actor in self.turn_initialized if actor in self.base_order}
        after = (len(self.base_order), len(self.round_queue), len(self.initiative_order))
        return before != after

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
        if self._is_actor_dead(actor):
            return
        try:
            self.attack_state.pop(actor, None)
            self.attack_state.pop(f"actor:{self._actor_id(actor)}", None)
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
            try:
                statuses = list(getattr(actor, "statuses", []) or [])
                filtered = []
                for status in statuses:
                    sid = str(getattr(status, "id", "") or "").strip().lower()
                    source = str(getattr(status, "source", "") or "")
                    if sid == "speed_penalty" and source.startswith("raise_shield:"):
                        continue
                    filtered.append(status)
                actor.statuses = filtered
            except Exception:
                logger.debug("Nie udało się wyczyścić kary speed z raise_shield dla %s", actor)
            # Własny Take Cover za tower shield nie może trwać dłużej niż podniesiona tarcza.
            try:
                take_cover_remover = getattr(actor, "remove_bonuses_with_prefix", None)
                had_self_cover = any(
                    str(getattr(effect, "source", "") or "").startswith("take_cover:tower_shield")
                    for effect in list(getattr(actor, "bonuses", []) or [])
                )
                if callable(take_cover_remover):
                    try:
                        take_cover_remover("take_cover:tower_shield")
                    except Exception:
                        pass
                if had_self_cover:
                    active = [
                        effect
                        for effect in list(getattr(actor, "bonuses", []) or [])
                        if str(getattr(effect, "source", "") or "").startswith("take_cover:")
                    ]
                    if not active:
                        drop_status = getattr(actor, "remove_status", None)
                        if callable(drop_status):
                            try:
                                drop_status("covered")
                            except Exception:
                                pass
                        statuses = list(getattr(actor, "statuses", []) or [])
                        filtered = [status for status in statuses if str(getattr(status, "id", status) or "").strip().lower() != "covered"]
                        try:
                            actor.statuses = filtered
                        except Exception:
                            pass
            except Exception:
                logger.debug("Nie udało się wygasić własnego Take Cover z tower shield dla %s", actor)
            # Wygaszanie osłony "Take Cover przy cudzej tower shield" po końcu podniesienia tarczy właściciela.
            try:
                from GameObjects.items.shield import tower_shield_cover_owner_key

                owner_key = tower_shield_cover_owner_key(actor)
                shared_cover_prefix = f"take_cover:tower_shield_from:{owner_key}"
                participants = list(getattr(self.game, "heroes", [])) + list(getattr(self.game, "enemies", []))
                for participant in participants:
                    shared_remover = getattr(participant, "remove_bonuses_with_prefix", None)
                    if not callable(shared_remover):
                        continue
                    removed = int(shared_remover(shared_cover_prefix) or 0)
                    if removed <= 0:
                        continue
                    active = [
                        effect
                        for effect in list(getattr(participant, "bonuses", []) or [])
                        if str(getattr(effect, "source", "") or "").startswith("take_cover:")
                    ]
                    if active:
                        continue
                    drop_status = getattr(participant, "remove_status", None)
                    if callable(drop_status):
                        try:
                            drop_status("covered")
                        except Exception:
                            pass
                    statuses = list(getattr(participant, "statuses", []) or [])
                    filtered = [status for status in statuses if str(getattr(status, "id", status) or "").strip().lower() != "covered"]
                    try:
                        participant.statuses = filtered
                    except Exception:
                        pass
            except Exception:
                logger.debug("Nie udało się wygasić osłony z tower shield dla sojuszników.")
            try:
                from statuses import run_recovery_check

                recovery = run_recovery_check(actor, source="combat:recovery_check")
                if isinstance(recovery, dict):
                    message = str(recovery.get("message", "") or "").strip()
                    if message:
                        self.game.ui_log(f"{getattr(actor, 'name', 'Aktor')}: {message}")
                        self._show_incapacitated_prompt(
                            actor,
                            title=f"{getattr(actor, 'name', 'Aktor')}: Recovery Check",
                            source="combat_recovery_check",
                            dedupe_key=(
                                f"recovery_check:{self.round_index}:{self._actor_id(actor)}:"
                                f"{message}:{self.actions_used.get(actor, 0)}"
                            ),
                            recovery_message=message,
                        )
            except Exception as exc:
                logger.debug("Nie udało się wykonać recovery check dla %s: %s", actor, exc)

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
                tick_statuses(phase="turn_start", log_changes=True)
            except Exception:
                logger.debug("Nie udało się odliczyć statusów dla %s", actor)
        try:
            self.sync_status_initiative_penalty(actor, reorder_round_queue=False)
        except Exception:
            logger.debug("Nie udało się zsynchronizować kary do inicjatywy dla %s", actor)
        try:
            from actions.move_utils import reset_turn_movement_runtime

            reset_turn_movement_runtime(actor)
        except Exception:
            logger.debug("Nie udało się zresetować runtime ruchu dla %s", actor)

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
        if actor not in self.turn_initialized:
            self.turn_initialized.add(actor)
            self._clear_start_of_turn_effects(actor)
            base_used = self._start_turn_actions_used(actor)
            existing_used = self.actions_used.get(actor, 0)
            try:
                existing_used = int(existing_used)
            except Exception:
                existing_used = 0
            self.actions_used[actor] = min(self._action_limit(actor), max(base_used, existing_used))
            reset_react = getattr(actor, "reset_reactions", None)
            if callable(reset_react):
                try:
                    reset_react()
                except Exception as exc:
                    logger.error("Nie udało się zresetować reakcji dla %s: %s", actor, exc)
            try:
                from combat.reactions.dispatcher import clear_turn_reaction_policies

                clear_turn_reaction_policies(actor)
            except Exception:
                pass
        return actor

    def _advance_turn(self):
        if not self.round_queue:
            return
        finished_actor = self.round_queue[0]
        self._tick_end_of_turn_preparation(finished_actor)
        try:
            self.round_queue.pop(0)
        except IndexError:
            return
        # Koniec tury aktora -> następna jego tura zaczyna z nowym licznikiem akcji.
        self.actions_used.pop(finished_actor, None)
        self.turn_initialized.discard(finished_actor)
        if not self.round_queue:
            self._tick_combat_round_statuses()
            # nowa runda: reset opóźnień do bazowych inicjatyw
            self.round_index += 1
            self.temp_initiative.clear()
            self.delayed.clear()
            self.out_of_turn_actions_used.clear()
            self.turn_initialized.clear()
            self._reaction_resolution_keys.clear()
            self.round_queue = list(self.base_order)
        self.initiative_order = list(self.round_queue)
        actor = self._current_actor()
        if actor is not None:
            logger.debug("Nowa tura dla %s – reset licznika akcji.", actor)
        self._send_initiative_event()

    def _tick_combat_round_statuses(self) -> None:
        actors = list(getattr(self.game, "heroes", []) or []) + list(getattr(self.game, "enemies", []) or [])
        for actor in actors:
            statuses = getattr(actor, "statuses", None)
            if not isinstance(statuses, list) or not statuses:
                continue
            remaining = []
            changed = False
            for status in statuses:
                data = getattr(status, "data", None) or {}
                if "combat_rounds_left" not in data:
                    remaining.append(status)
                    continue
                try:
                    rounds_left = int(data.get("combat_rounds_left", 0) or 0) - 1
                except Exception:
                    rounds_left = -1
                if rounds_left <= 0:
                    clear_temp_hp = getattr(actor, "_clear_temp_hp_for_status", None)
                    if callable(clear_temp_hp):
                        try:
                            clear_temp_hp(status)
                        except Exception:
                            pass
                    changed = True
                    continue
                updated = dict(data)
                updated["combat_rounds_left"] = rounds_left
                remaining.append(replace(status, data=updated))
                changed = True
            if changed:
                try:
                    actor.statuses = remaining
                except Exception:
                    pass

    def _tick_end_of_turn_preparation(self, actor) -> None:
        if actor is None:
            return
        try:
            from statuses import decrement_end_of_turn_conditions

            decrement_end_of_turn_conditions(actor)
        except Exception:
            pass
        tick_statuses = getattr(actor, "tick_statuses_turn", None)
        if callable(tick_statuses):
            try:
                tick_statuses(phase="turn_end", log_changes=True)
            except Exception:
                logger.debug("Nie udało się odliczyć statusów end-turn dla %s", actor)
        changed = 0
        try:
            from GameObjects.items.inventory import tick_alchemical_preparation
            changed = int(tick_alchemical_preparation(actor) or 0)
        except Exception:
            changed = 0
        if changed <= 0:
            changed = self._fallback_tick_alchemical_preparation(actor)
        if changed <= 0:
            return
        try:
            self.game.ui_log(
                f"{getattr(actor, 'name', 'Aktor')}: przygotowanie przedmiotów alchemicznych zaktualizowane ({changed})."
            )
        except Exception:
            pass

    @staticmethod
    def _fallback_tick_alchemical_preparation(actor) -> int:
        """Defensywnie odlicza preparation_counter na itemach alchemicznych."""
        inventory = getattr(actor, "inventory", None)
        if not isinstance(inventory, list):
            return 0
        changed = 0
        for item in inventory:
            if not hasattr(item, "preparation_counter"):
                continue
            try:
                current = max(0, int(getattr(item, "preparation_counter", 0) or 0))
            except Exception:
                current = 0
            if current <= 0:
                continue
            try:
                setattr(item, "preparation_counter", current - 1)
                changed += 1
            except Exception:
                continue
        return changed

    def _start_turn_actions_used(self, actor) -> int:
        limit = self._action_limit(actor)
        used = 0
        try:
            from statuses import consume_stunned_actions

            used = min(limit, max(0, int(consume_stunned_actions(actor) or 0)))
        except Exception:
            used = 0
        preturn_used = self.out_of_turn_actions_used.pop(actor, 0)
        try:
            preturn_used = max(0, int(preturn_used))
        except Exception:
            preturn_used = 0
        used += preturn_used
        if used > 0:
            try:
                actor_name = getattr(actor, "name", "Aktor")
                if preturn_used > 0:
                    self.game.ui_log(
                        f"{actor_name} ma zużyte {preturn_used} akcji poza turą (reakcje). "
                        f"Na start tury: {max(0, limit - used)}/{limit}."
                    )
                if used - preturn_used > 0:
                    self.game.ui_log(f"{actor_name} jest stunned: traci {used - preturn_used} akcji.")
            except Exception:
                pass
        return min(limit, max(0, int(used)))

    def new_reaction_event_uid(self) -> str:
        self._reaction_event_seq = int(self._reaction_event_seq) + 1
        return f"r{int(self.round_index)}:{self._reaction_event_seq}"

    def actions_remaining(self, actor) -> int:
        if actor is None:
            return 0
        limit = self._action_limit(actor)
        if actor in self.turn_initialized:
            used = self.actions_used.get(actor, 0)
        else:
            used = self.out_of_turn_actions_used.get(actor, 0)
        try:
            used = int(used)
        except Exception:
            used = 0
        return max(0, int(limit) - max(0, used))

    def can_pay_reaction_action_cost(self, actor, *, cost: int = 1) -> bool:
        try:
            required = max(1, int(cost))
        except Exception:
            required = 1
        return self.actions_remaining(actor) >= required

    def consume_reaction_action_cost(self, actor, *, cost: int = 1, reason: str | None = None) -> bool:
        if actor is None:
            return False
        try:
            spent = max(1, int(cost))
        except Exception:
            spent = 1
        if not self.can_pay_reaction_action_cost(actor, cost=spent):
            return False
        limit = self._action_limit(actor)
        if actor in self.turn_initialized:
            self.actions_used[actor] = min(
                limit,
                int(self.actions_used.get(actor, 0) or 0) + spent,
            )
        else:
            self.out_of_turn_actions_used[actor] = min(
                limit,
                int(self.out_of_turn_actions_used.get(actor, 0) or 0) + spent,
            )
        try:
            remaining = self.actions_remaining(actor)
            label = reason or "Reakcja"
            self.game.ui_log(
                f"{getattr(actor, 'name', 'Aktor')}: {label} kosztuje {spent} akcję. "
                f"Pozostało {remaining}/{limit}."
            )
        except Exception:
            pass
        if actor in self.turn_initialized and self.actions_used.get(actor, 0) >= limit:
            self.game.ui_log(
                f"{getattr(actor, 'name', 'Aktor')} zużył wszystkie akcje. "
                "Tura kończy się automatycznie."
            )
            if self.round_queue and self.round_queue[0] is actor:
                self._advance_turn()
        return True

    # --- Combat flow ---
    def _end_combat_if_no_enemies(self) -> Optional[State]:
        enemies_alive = [e for e in self.game.enemies if getattr(e, "hp", 0) > 0 and getattr(e, "position", None) is not None]
        if enemies_alive:
            return None
        logger.info("Brak wrogów na planszy – koniec walki.")
        self._offer_collect_remaining_loot()
        self._clear_combat_ui()
        if getattr(self.game, "is_generated_encounter", None) and self.game.is_generated_encounter():
            return EncounterFinished(self.game)
        return HeroesTurn(self.game)

    def _loot_all_actor(self) -> Any | None:
        for hero in list(getattr(self.game, "heroes", []) or []):
            if getattr(hero, "position", None) is not None:
                return hero
        heroes = list(getattr(self.game, "heroes", []) or [])
        return heroes[0] if heroes else None

    def _remaining_loot_summary(self, piles: list[object]) -> str:
        rows: list[str] = []
        for pile in piles:
            position = getattr(pile, "position", None)
            summary_fn = getattr(pile, "loot_summary", None)
            try:
                summary = summary_fn() if callable(summary_fn) else ""
            except Exception:
                summary = ""
            rows.append(f"- pole {position}: {summary or 'loot'}")
        return "\n".join(rows) if rows else "- brak lootu"

    def _offer_collect_remaining_loot(self) -> None:
        if bool(getattr(self, "_combat_end_loot_prompt_done", False)):
            return
        self._combat_end_loot_prompt_done = True
        try:
            from party_stash import find_loot_piles
        except Exception:
            return
        piles = find_loot_piles(self.game)
        if not piles:
            return
        actor = self._loot_all_actor()
        player_prompt = getattr(self.game, "player_prompt", None)
        if player_prompt is None or not hasattr(player_prompt, "choice"):
            return
        loot_list = self._remaining_loot_summary(piles)
        prompt_text = render_prompt_text("interaction.combat_end_loot_all", loot_list=loot_list)
        body_markdown = (
            "**Na planszy został loot**\n"
            f"{loot_list}\n\n"
            "Możesz zebrać wszystko do **Party Stash** albo przejrzeć stosy przed zapisaniem."
        )
        choice_meta = [
            {
                "raw": "stash_all",
                "label": "Zbierz wszystko do Party Stash",
                "desc": "Wszystkie stosy znikną z planszy, a przedmioty i monety trafią do magazynu drużyny.",
                "key": "Enter",
            },
            {
                "raw": "review",
                "label": "Przejrzyj przed zapisaniem",
                "desc": "Przejdź przez stosy lootu i wybierz rzeczy, które od razu trafią do aktywnego bohatera.",
                "key": "R",
            },
            {
                "raw": "leave",
                "label": "Zostaw na planszy",
                "desc": "Loot zostaje tam, gdzie leży. Można go zebrać ręcznie później.",
                "key": "Esc",
            },
        ]
        try:
            answer = player_prompt.choice(
                str(prompt_text.get("title") or "Loot po walce"),
                choices=[entry["label"] for entry in choice_meta],
                source="combat_end_loot",
                subtitle=str(prompt_text.get("summary") or "Na planszy został loot."),
                body_markdown=body_markdown,
                details_markdown=str(prompt_text.get("details_markdown") or ""),
                choice_meta=choice_meta,
                scope_key="combat:end:loot",
                dedupe_key="combat_end_loot_all",
                prompt_id="interaction.combat_end_loot_all",
            )
        except Exception:
            answer = None
        normalized = str(answer or "leave").strip().lower()
        if normalized == "leave":
            return
        if normalized == "review" and actor is not None:
            for pile in list(find_loot_piles(self.game)):
                collect = getattr(pile, "collect", None)
                if callable(collect):
                    try:
                        collect(actor, self.game, allow_prompt=True)
                    except Exception:
                        logger.debug("Nie udało się przejrzeć stosu lootu po walce.", exc_info=True)
            return
        if normalized in {"stash_all", "confirm", "ok", ""}:
            for pile in list(find_loot_piles(self.game)):
                collect = getattr(pile, "collect", None)
                if callable(collect):
                    try:
                        collect(actor, self.game, allow_prompt=False)
                    except Exception:
                        logger.debug("Nie udało się zebrać stosu lootu po walce.", exc_info=True)

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
        self._cleanup_removed()
        active = self._current_actor()
        order_payload: list[dict[str, Any]] = []
        done_set = set(self.base_order) - set(self.round_queue)
        # kolejność: najpierw obecna kolejka rundy, potem już-ograne (w bazowej kolejności)
        ordered_objs = list(self.round_queue) + [obj for obj in self.base_order if obj not in self.round_queue]
        for obj in ordered_objs:
            base = self.base_initiative.get(obj, getattr(obj, "initiative", -1))
            eff = self._effective_initiative(obj)
            delta = eff - base
            status_labels: list[str] = []
            try:
                from ui_payloads import status_labels as _status_labels

                status_labels = list(_status_labels(obj) or [])
            except Exception:
                status_labels = []
            wounds = getattr(obj, "wounds", None)
            if wounds is None and hasattr(obj, "hp") and hasattr(obj, "max_hp"):
                try:
                    max_hp = int(getattr(obj, "max_hp", 0) or 0)
                    hp = int(getattr(obj, "hp", 0) or 0)
                    wounds = min(max_hp, max(0, max_hp - hp)) if max_hp > 0 else None
                except Exception:
                    wounds = None
            order_payload.append(
                {
                    "id": self._actor_id(obj),
                    "name": getattr(obj, "name", None) or getattr(obj, "object_id", "actor"),
                    "kind": "hero" if obj in self.game.heroes else "enemy",
                    "image": getattr(obj, "image", None) or getattr(obj, "portrait_image", None),
                    "asset_id": str(getattr(obj, "object_id", None) or getattr(obj, "name", "") or self._actor_id(obj)),
                    **self._actor_actions_payload(obj),
                    "base": base,
                    "current": eff,
                    "delta": delta,
                    "done": obj in done_set,
                    "wounds": wounds,
                    "max_hp": getattr(obj, "max_hp", None),
                    "statuses": status_labels,
                }
            )
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

    def _actor_actions_payload(self, actor: Any | None) -> dict[str, int]:
        if actor is None:
            return {}
        try:
            total = int(self._action_limit(actor))
        except Exception:
            total = 3
        try:
            used = int(self.actions_used.get(actor, 0) or 0)
        except Exception:
            used = 0
        total = max(0, total)
        used = max(0, min(total, used))
        return {
            "actions_used": used,
            "actions_total": total,
            "actions_remaining": max(0, total - used),
        }

    @staticmethod
    def _weapon_note(actor) -> str:
        try:
            from GameObjects.items.inventory import get_equipped_weapons, item_label
        except Exception:
            return "Weapon: -"
        equipped = list(get_equipped_weapons(actor))
        if not equipped:
            return "Weapon: brak (fallback unarmed)"
        labels = ", ".join(item_label(item) for item in equipped)
        return f"Weapon: {labels}"

    @staticmethod
    def _shield_note(actor) -> str:
        try:
            from GameObjects.items.shield import get_equipped_shield
        except Exception:
            return "Shield: brak"
        shield = get_equipped_shield(actor, create_default=False)
        if shield is None:
            return "Shield: brak"
        name = str(getattr(shield, "name", "Shield") or "Shield")
        hp = int(getattr(shield, "current_hp", 0) or 0)
        hp_max = int(getattr(shield, "max_hp", hp) or hp)
        hardness = int(getattr(shield, "hardness", 0) or 0)
        if bool(getattr(shield, "is_destroyed", False)):
            return f"Shield: {name} ZNISZCZONA ({hp}/{hp_max})"
        if bool(getattr(shield, "is_broken", False)):
            return f"Shield: {name} BROKEN ({hp}/{hp_max}, Hardness {hardness})"
        return f"Shield: {name} ({hp}/{hp_max}, Hardness {hardness})"

    def _hero_ui_note(self, actor) -> str:
        used = int(self.actions_used.get(actor, 0) or 0)
        limit = int(self._action_limit(actor) or 0)
        return "\n".join(
            [
                f"Akcje: {used}/{limit}",
                self._weapon_note(actor),
                self._shield_note(actor),
            ]
        )

    def _refresh_hero_ui_snapshot(self, actor) -> None:
        if actor not in getattr(self.game, "heroes", []):
            return
        try:
            self.game.ui_hero(actor, note=self._hero_ui_note(actor))
        except Exception:
            logger.debug("Nie udało się odświeżyć snapshotu UI bohatera %s", actor, exc_info=True)

    def _cancel_prompt_scopes(self, *scope_keys: str) -> None:
        player_prompt = getattr(self.game, "player_prompt", None)
        for scope_key in scope_keys:
            scope = str(scope_key or "").strip()
            if not scope:
                continue
            if player_prompt is not None and hasattr(player_prompt, "cancel_scope"):
                try:
                    if player_prompt.cancel_scope(scope):
                        continue
                except Exception:
                    pass
            try:
                self.game.ui_event("prompt_scope_cancel", {"scope_key": scope})
            except Exception:
                pass

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

    def add_revealed_enemy(self, enemy, *, join_current_round: bool = True) -> None:
        if enemy is None or getattr(enemy, "position", None) is None:
            return
        if enemy not in self.game.enemies:
            self.game.enemies.append(enemy)
        if not self._initiatives_ready:
            return
        if enemy not in self.base_initiative:
            try:
                self.base_initiative[enemy] = int(enemy.roll_initiative())
            except Exception:
                self.base_initiative[enemy] = int(getattr(enemy, "initiative", 0) or 0)
        if enemy not in self.base_order:
            self.base_order.append(enemy)
            self._resort_base_order()
        if join_current_round and enemy not in self.round_queue:
            self.round_queue.append(enemy)
        self.initiative_order = list(self.round_queue)
        if join_current_round:
            self.game.ui_log(
                f"{getattr(enemy, 'name', 'Enemy')} dołącza do walki i wejdzie do inicjatywy na końcu bieżącej rundy."
            )
        else:
            self.game.ui_log(
                f"{getattr(enemy, 'name', 'Enemy')} dołącza do walki i wejdzie do inicjatywy od następnej rundy."
            )
        self._send_initiative_event()

    def resolve_hidden_ambush_spawn(self, enemy, *, source_actor=None) -> None:
        if enemy is None or getattr(enemy, "position", None) is None:
            return
        if enemy not in self.game.enemies:
            self.game.enemies.append(enemy)

        behavior_fn = get_behavior(getattr(enemy, "behavior_id", None))
        try:
            behavior_fn(enemy, self.game, self, actions_left=1)
        except Exception as exc:
            logger.error("Ambush action przeciwnika (%s) nie powiodła się: %s", getattr(behavior_fn, "__name__", "behavior"), exc)
            self.game.ui_log(f"Ambush action przeciwnika nie powiodła się: {exc}")

        if getattr(enemy, "position", None) is None:
            return
        try:
            if enemy not in self.base_initiative:
                self.base_initiative[enemy] = int(getattr(enemy, "initiative", None) or enemy.roll_initiative())
        except Exception:
            pass

        if not self._initiatives_ready:
            self.game.ui_log(
                f"{getattr(enemy, 'name', 'Enemy')} wykonuje akcję z zasadzki przed ustaleniem inicjatywy."
            )
            return

        self.add_revealed_enemy(enemy, join_current_round=False)

    def _confirm_actor_position(self, actor) -> bool:
        return True

    def _show_actor_stats(self, actor) -> None:
        text = render_actor_stats(actor, combat_state=self)
        ui = getattr(self.game, "ui", None)
        if ui is not None and hasattr(ui, "prompt_info") and getattr(ui, "enabled", False):
            try:
                ui.prompt_info(
                    str(prompt_value("turns.actor_stats", "title", "Statystyki")),
                    prompt_long=text,
                    source="stats",
                    prompt_id="turns.actor_stats",
                )
                return
            except Exception:
                pass
        self.game.ui_log(text)

    def _handle_hero_decline(self, hero, *, auto_delay: bool = False) -> State:
        if not self._confirm_actor_position(hero):
            logger.info("Nie potwierdzono pozycji bohatera – przerwano wybór END/DELAY.")
            return self
        decision = "delay" if auto_delay else None
        if decision is None:
            used = self.actions_used.get(hero, 0)
            limit = self._action_limit(hero)
            remaining = limit - used
            prompt = (
                "Limit akcji wyczerpany. END – koniec tury (8), DELAY – opóźnij (7, obniża inicjatywę)"
                if remaining <= 0
                else f"Masz {remaining} niewykorzystanych akcji. END – koniec tury (8), DELAY – opóźnij (7, obniża inicjatywę)"
            )
            picked = choose_option(
                self.game,
                title="Koniec tury",
                subtitle=prompt,
                source="end_delay",
                options=[
                    {"id": "end", "label": "Koniec", "desc": "Zakończ turę."},
                    {"id": "delay", "label": "Opóźnij", "desc": "Obniż inicjatywę i zagraj później."},
                ],
                prompt_id="turns.end_delay_menu",
            )
            decision = str(picked or "end").strip().lower()

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
        limit = self._action_limit(enemy)
        behavior_fn = get_behavior(getattr(enemy, "behavior_id", None))
        try:
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
        finally:
            clear_enemy_highlight(self.game)
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
            if getattr(self.game, "is_generated_encounter", None) and self.game.is_generated_encounter():
                return EncounterFinished(self.game)
            return HeroesTurn(self.game)
        ui_active_actor = getattr(self.game, "ui_active_actor", None)
        if callable(ui_active_actor):
            ui_active_actor(actor)

        if actor in self.game.enemies:
            self._cancel_prompt_scopes("hero_turn:intent", "hero_turn:targeting", "hero_turn:resolution")
            limit = self._action_limit(actor)
            remaining = limit - self.actions_used.get(actor, 0)
            logger.info("Tura przeciwnika: %s (akcje pozostałe: %s/%s)", getattr(actor, "name", "Enemy"), remaining, limit)
            actor_pos = getattr(actor, "position", None)
            if actor_pos is not None:
                enemy_highlight(self.game, [actor_pos], [consts.ENEMY_START_RGB])
            enemy_prompt_step(
                self.game,
                f"Tura przeciwnika: {getattr(actor, 'name', 'Enemy')}",
                prompt_long=(
                    f"Przeciwnik rozpoczyna turę.\n"
                    f"Akcje pozostałe: {remaining}/{limit}.\n"
                    "Potwierdź Enterem, aby obserwować kolejne kroki przeciwnika."
                ),
                source="enemy_turn_start",
                blocking=True,
                semantic_type="required_action",
                dedupe_key=f"enemy_turn_start:{getattr(actor, 'object_id', getattr(actor, 'name', 'enemy'))}:{remaining}/{limit}",
                next_hint="Przeciwnik zacznie wykonywać akcje.",
                continue_hint="Enter rozpoczyna turę przeciwnika.",
                emit_log=False,
            )
            return self._process_enemy_turn(actor)

        # Hero turn
        self._cancel_prompt_scopes("enemy_turn")
        try:
            ensure_actor_spell_state(actor, game=self.game)
        except Exception:
            pass
        if self._is_actor_dead(actor):
            self.game.ui_log(f"{getattr(actor, 'name', 'Aktor')} jest martwy i nie może działać.")
            self._advance_turn()
            return self
        try:
            from statuses import dying_value

            if int(dying_value(actor) or 0) > 0 or self._is_actor_unconscious(actor):
                self.game.ui_log(
                    f"{getattr(actor, 'name', 'Aktor')} jest nieprzytomny/dying - tura kończy się automatycznie."
                )
                self._show_incapacitated_prompt(
                    actor,
                    title=f"{getattr(actor, 'name', 'Aktor')} nie może działać",
                    source="combat_incapacitated_turn",
                    dedupe_key=f"incapacitated_turn:{self.round_index}:{self._actor_id(actor)}",
                )
                self._advance_turn()
                return self
        except Exception:
            pass

        # Wyczyść jednorundowe bonusy osłon (np. raise_shield) na początku tury bohatera
        remover = getattr(actor, "remove_bonuses_with_prefix", None)
        if callable(remover):
            try:
                remover("raise_shield:")
            except Exception:
                logger.debug("Nie udało się wyczyścić efektów raise_shield dla %s", actor)

        used = self.actions_used.get(actor, 0)
        limit = self._action_limit(actor)
        self.actions_used[actor] = used
        logger.info("Tura bohatera (%s). Akcje: %s/%s", actor, used, limit)
        self._refresh_hero_ui_snapshot(actor)
        if used >= limit:
            logger.info("Aktor %s nie ma już akcji. Automatyczny koniec tury.", getattr(actor, "name", actor))
            self.game.ui_log("Brak dostępnych akcji. Automatyczny koniec tury.")
            self._advance_turn()
            return self

        all_events = list_events()
        available_events = {
            name: cls for name, cls in all_events.items() if getattr(cls, "available_in_combat", True)
        }
        available_events = filter_player_events(available_events, actor_is_hero=True)
        available_events = filter_events_for_actor(
            available_events,
            actor=actor,
            in_combat=True,
            game=self.game,
        )
        available_events = filter_magic_events_for_actor(
            available_events,
            actor=actor,
            game=self.game,
        )
        available_events = filter_alchemy_events_for_actor(
            available_events,
            actor=actor,
        )
        if not available_events:
            logger.warning("Brak zarejestrowanych eventów dla walki (po filtrze bohatera).")
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

        grouped = group_events(available_events, actor=actor)
        intent_options = build_intent_options(grouped, in_combat=True, actor=actor, available_events=available_events)
        logger.info("Dostępne intencje: %s", ", ".join(option["id"] for option in intent_options))
        self.game.ui_log(f"Aktywny: {getattr(actor, 'name', actor)}. Wybierz intencję akcji.")
        intent = choose_option(
            self.game,
            title="Akcje",
            subtitle="8/2 nawigacja, Enter potwierdzenie.",
            source="intent",
            options=intent_options,
            prompt_id="turns.intent_menu",
        )
        if highlighted:
            try:
                self.game.conn.leds_off()
            except Exception:
                pass

        raw_choice: str | None = None
        if not intent:
            self.game.ui_log("Nie wybrano akcji.")
            return self

        if intent == "stats":
            self._show_actor_stats(actor)
            return self

        if raw_choice is None:
            if intent == "interact":
                raw_choice = "interaction"
            elif intent == "equipment":
                raw_choice = "equip"
            elif intent == "attack":
                if "attack" in available_events:
                    raw_choice = "attack"
                else:
                    raw_choice = choose_event_from_bucket(
                        self.game,
                        bucket_id=intent,
                        available_events=available_events,
                        event_names=list(grouped.get(intent, [])),
                        source=f"intent:{intent}",
                        actor=actor,
                    )
                    if not raw_choice:
                        self.game.ui_log("Nie wybrano akcji ataku.")
                        return self
            elif intent in ("magic", "alchemy", "special"):
                raw_choice = choose_event_from_bucket(
                    self.game,
                    bucket_id=intent,
                    available_events=available_events,
                    event_names=list(grouped.get(intent, [])),
                    source=f"intent:{intent}",
                    actor=actor,
                )
                if not raw_choice:
                    self.game.ui_log(f"Nie wybrano akcji z kategorii '{intent}'.")
                    return self
            else:
                raw_choice = str(intent).strip().lower()

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

        if result.message:
            self.game.ui_log(result.message)
        else:
            status = "powiodła się" if result.success else "nie powiodła się"
            self.game.ui_log(f"Akcja '{raw_choice}' {status}.")
        try:
            self.game.ui_narration(
                narrate_action_result(actor=actor, action_id=raw_choice, result=result),
                summary="Jaki był efekt akcji",
                source=f"action_result:{raw_choice}",
                priority="result" if result.success else "warning",
                semantic_type="result",
            )
        except Exception:
            logger.debug("Nie udało się wysłać narracji wyniku akcji '%s'.", raw_choice, exc_info=True)

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
            self._refresh_hero_ui_snapshot(actor)
            if self.actions_used[actor] >= limit:
                logger.info("Wykorzystano limit %s akcji. Automatyczny koniec tury.", limit)
                self.game.ui_log("Wykorzystano wszystkie akcje. Automatyczny koniec tury.")
                self._advance_turn()
                return self
        else:
            self._refresh_hero_ui_snapshot(actor)
        # end i delay same wywołują zmianę kolejki; jeśli aktywny uległ zmianie, nie ruszaj tutaj
        if raw_choice in ("end",):
            return self
        return self
