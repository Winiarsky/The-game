from __future__ import annotations

import logging

from board import consts
from localization import localize_term_pl
from skills import Skill
from statuses.familiar import (
    FamiliarGuidanceStatus,
    FamiliarScoutStatus,
    FAMILIAR_DISTRACT_STATUS,
    FAMILIAR_TOUCH_DELIVERY_STATUS,
)
from ui_client import get_ui_client

from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class CommandFamiliarEvent(GameEvent):
    name = "commandfamilair"
    default_tags = ["familiar", "command"]
    consumes_action = True

    def execute(self, ctx: EventContext) -> EventResult:
        game = ctx.game
        actor = ctx.actor
        if actor not in getattr(game, "heroes", []) or getattr(actor, "position", None) is None:
            actor = self._pick_hero(game)
        if actor is None:
            return EventResult.cancelled(message="Nie wybrano bohatera.")
        if not actor.has_status("FamiliarOwner") and not actor.has_status("alchemist_familiar_guidance"):
            return EventResult.cancelled(message="Bohater nie ma familiara.")

        status = actor.get_status("FamiliarOwner") or actor.get_status("alchemist_familiar_guidance")
        if status is None:
            return EventResult.cancelled(message="Brak statusu FamiliarOwner.")
        data = getattr(status, "data", None) or {}
        mode = data.get("familiar_mode")
        if not mode:
            mode = self._prompt_mode(game, data)
            if not mode:
                return EventResult.cancelled(message="Familiar: nie ustawiono trybu.")

        if mode == "scout":
            added = actor.add_status(FamiliarScoutStatus())
            if not added:
                return EventResult.noop(message="Familiar: Scout już aktywny.")
            return EventResult(success=True, consumed_action=self.consumes_action, message="Familiar: Scout aktywny.")

        if mode == "guidance":
            skill_id = data.get("familiar_guidance_skill")
            if not skill_id:
                skill_id = self._prompt_guidance_skill(game)
                if not skill_id:
                    return EventResult.cancelled(message="Familiar: brak wybranego skilla dla Guidance.")
                data["familiar_guidance_skill"] = skill_id
            added = actor.add_status(FamiliarGuidanceStatus(skill_id))
            if not added:
                return EventResult.noop(message="Familiar: Guidance już aktywny.")
            return EventResult(success=True, consumed_action=self.consumes_action, message="Familiar: Guidance aktywny.")

        if mode == "distract":
            enemy = self._pick_enemy(game)
            if enemy is None:
                return EventResult.cancelled(message="Brak celu do Distract.")
            try:
                added = enemy.add_status(FAMILIAR_DISTRACT_STATUS)
            except Exception:
                added = False
            if not added:
                return EventResult.noop(message="Familiar: Distract już aktywny na celu.")
            return EventResult(success=True, consumed_action=self.consumes_action, message="Familiar: Distract aktywny.")

        if mode == "deliver_touch":
            added = actor.add_status(FAMILIAR_TOUCH_DELIVERY_STATUS)
            if not added:
                return EventResult.noop(message="Familiar: Touch Delivery już aktywny.")
            return EventResult(success=True, consumed_action=self.consumes_action, message="Familiar: Touch Delivery aktywny.")

        if mode == "scent_seek":
            found = self._sense_hidden_nearby(game, actor)
            msg = "Familiar wyczuwa coś w pobliżu." if found else "Familiar nic nie wyczuwa."
            try:
                ui = get_ui_client()
                if ui.enabled:
                    ui.prompt_info("Scent/Seek", prompt_long=msg, source="familiar")
            except Exception:
                pass
            game.ui_log(msg)
            return EventResult(success=True, consumed_action=self.consumes_action, message=msg)

        return EventResult.cancelled(message="Familiar: nieznany tryb.")

    @staticmethod
    def _structured_desc(*, fluff: str, mechanics: str, when: str) -> str:
        return "\n".join(
            [
                f"Fluff: {str(fluff or '').strip() or '-'}",
                "Mechanika:",
                f"- Kiedy: {str(when or '').strip() or 'Po wybraniu tej opcji.'}",
                f"- Efekt: {str(mechanics or '').strip() or 'Brak dodatkowego opisu mechaniki.'}",
            ]
        )

    def _mode_choice_entries(self) -> list[dict]:
        rows = [
            (
                "Scout (Perception)",
                "scout",
                "Familiar obserwuje pole walki i wypatruje zagrożeń.",
                "Po aktywacji dostajesz jednorazowy +2 circumstance do najbliższego testu Percepcji.",
            ),
            (
                "Guidance (Skill)",
                "guidance",
                "Familiar pomaga przy konkretnym rodzaju testu umiejętności.",
                "Po aktywacji dostajesz jednorazowy +1 circumstance do wybranego skilla.",
            ),
            (
                "Distract (Enemy)",
                "distract",
                "Familiar rozprasza przeciwnika w kluczowym momencie.",
                "Wybierasz jednego wroga; jego najbliższy atak wręcz ma karę -1 i efekt znika po tym ataku.",
            ),
            (
                "Deliver Touch Spell",
                "deliver_touch",
                "Familiar dostarcza czar dotykowy do celu.",
                "Najbliższy touch spell (zasięg 5 ft) może sięgnąć 10 ft i zużywa ten efekt.",
            ),
            (
                "Scent/Seek",
                "scent_seek",
                "Familiar używa węchu i instynktu do namierzania ukrytych rzeczy.",
                "Natychmiastowy skan otoczenia; gra wyświetla informację, czy w pobliżu są ukryte obiekty.",
            ),
        ]
        out: list[dict] = []
        for idx, (label, mode, fluff, mechanics) in enumerate(rows, start=1):
            out.append(
                {
                    "raw": mode,
                    "label": label,
                    "desc": self._structured_desc(
                        fluff=fluff,
                        mechanics=mechanics,
                        when="Przy pierwszym użyciu Command Familiar lub po zmianie trybu.",
                    ),
                    "key": str(idx),
                }
            )
        return out

    def _prompt_mode(self, game, status_data: dict) -> str | None:
        entries = self._mode_choice_entries()
        labels = [str(item["label"]) for item in entries]
        raw_answer: str | None = None
        ui = getattr(game, "ui", None)
        prompt = "Familiar: wybierz tryb działania dla akcji Command Familiar."
        if ui is not None and hasattr(ui, "prompt_choice"):
            raw_answer = ui.prompt_choice(
                prompt,
                choices=labels,
                source="familiar",
                layout="menu_numpad",
                choice_meta=entries,
            )
        elif ui is None or getattr(ui, "allow_cli_fallback", False):
            try:
                raw_answer = input(prompt + " ").strip() or None
            except Exception:
                raw_answer = None
        if not raw_answer:
            return None
        raw = str(raw_answer).strip().lower()
        by_raw = {str(item["raw"]).strip().lower(): str(item["raw"]).strip().lower() for item in entries}
        by_label = {str(item["label"]).strip().lower(): str(item["raw"]).strip().lower() for item in entries}
        mode = by_raw.get(raw) or by_label.get(raw)
        if not mode and raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(entries):
                mode = str(entries[idx]["raw"]).strip().lower()
        if not mode:
            return None
        status_data["familiar_mode"] = mode
        try:
            game.ui_log(f"Familiar: wybrany tryb: {localize_term_pl(mode) or mode}.")
        except Exception:
            pass
        return mode

    @staticmethod
    def _prompt_guidance_skill(game) -> str | None:
        choices = [str(item.value) for item in Skill]
        raw_answer: str | None = None
        ui = getattr(game, "ui", None)
        prompt = "Guidance: wybierz skill dla stałego bonusu +1."
        if ui is not None and hasattr(ui, "prompt_choice"):
            entries = [
                {
                    "raw": skill_id,
                    "label": localize_term_pl(skill_id) or skill_id,
                    "desc": "\n".join(
                        [
                            f"Fluff: Familiar wspiera cię w testach {localize_term_pl(skill_id) or skill_id}.",
                            "Mechanika:",
                            "- Kiedy: Przy aktywacji trybu Guidance.",
                            "- Efekt: Jednorazowy +1 circumstance do wybranego skilla.",
                        ]
                    ),
                    "key": str(idx + 1),
                }
                for idx, skill_id in enumerate(choices)
            ]
            raw_answer = ui.prompt_choice(
                prompt,
                choices=[str(item["label"]) for item in entries],
                source="familiar",
                layout="menu_numpad",
                choice_meta=entries,
            )
        elif ui is None or getattr(ui, "allow_cli_fallback", False):
            try:
                raw_answer = input(prompt + " ").strip() or None
            except Exception:
                raw_answer = None
        if not raw_answer:
            return None
        raw = str(raw_answer).strip().lower().replace(" ", "_")
        if raw in set(choices):
            return raw
        for skill_id in choices:
            if raw == (localize_term_pl(skill_id) or "").strip().lower().replace(" ", "_"):
                return skill_id
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return str(choices[idx])
        return None

    # --- helpers ---
    def _pick_hero(self, game):
        heroes = [h for h in getattr(game, "heroes", []) if getattr(h, "position", None) is not None]
        if not heroes:
            return None
        positions = [h.position for h in heroes]
        try:
            game.conn.set_leds(positions, consts.HERO_HIGHLIGHT_RGB)
            pos = game.conn.scan_board(positions)
        finally:
            try:
                game.conn.leds_off()
            except Exception:
                pass
        return game.board.occupant_at(pos)

    def _pick_enemy(self, game):
        enemies = [e for e in getattr(game, "enemies", []) if getattr(e, "position", None) is not None]
        if not enemies:
            return None
        positions = [e.position for e in enemies]
        if len(positions) == 1:
            return enemies[0]
        try:
            game.conn.set_leds(positions, consts.INTERACT_FIELD_RGB)
            pos = game.conn.scan_board(positions)
        finally:
            try:
                game.conn.leds_off()
            except Exception:
                pass
        return game.board.occupant_at(pos)

    def _sense_hidden_nearby(self, game, actor) -> bool:
        hero_pos = getattr(actor, "position", None)
        if hero_pos is None:
            return False
        board = game.board
        radius_cells = 3  # 15 ft
        cx, cy = hero_pos
        for dx in range(-radius_cells, radius_cells + 1):
            for dy in range(-radius_cells, radius_cells + 1):
                if max(abs(dx), abs(dy)) > radius_cells:
                    continue
                pos = (cx + dx, cy + dy)
                if not board.in_bounds(pos):
                    continue
                for obj in board.interactables_at(pos):
                    if not getattr(obj, "hidden", False):
                        continue
                    if getattr(obj, "revealed", False):
                        continue
                    if not getattr(obj, "seekable", True):
                        continue
                    logger.info("Familiar wyczuwa ukryty obiekt w pobliżu.")
                    return True
        return False
