from __future__ import annotations

import logging

from board import consts
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
            return EventResult.cancelled(message="Familiar: nie ustawiono trybu w setupie.")

        if mode == "scout":
            added = actor.add_status(FamiliarScoutStatus())
            if not added:
                return EventResult.noop(message="Familiar: Scout już aktywny.")
            return EventResult(success=True, consumed_action=self.consumes_action, message="Familiar: Scout aktywny.")

        if mode == "guidance":
            skill_id = data.get("familiar_guidance_skill")
            if not skill_id:
                return EventResult.cancelled(message="Familiar: brak wybranego skilla dla Guidance.")
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
