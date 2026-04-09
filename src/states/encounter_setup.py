from __future__ import annotations

import logging
from dataclasses import asdict

from board import consts

from .start import Start

logger = logging.getLogger(__name__)


class EncounterSetupState(Start):
    initial_action_name = "run_encounter_setup"

    def _setup_batches(self):
        batches = getattr(self.game, "encounter_setup_plan", None) or []
        for raw_batch in batches:
            batch = asdict(raw_batch) if hasattr(raw_batch, "__dataclass_fields__") else dict(raw_batch)
            prompt = str(batch.get("prompt") or "Przygotuj planszę.")
            mode = str(batch.get("confirmation_mode") or "confirm_only")
            positions = [tuple(pos) for pos in list(batch.get("positions") or [])]
            self.game.ui_log(prompt)
            ui = getattr(self.game, "ui", None)
            if mode == "click_all" and positions:
                pending = list(positions)
                while pending:
                    self.game.conn.set_leds(pending, consts.MOVE_FIELD_RGB)
                    clicked = self.game.conn.scan_board(pending)
                    self.game.conn.leds_off()
                    if clicked in pending:
                        pending.remove(clicked)
                        self.game.ui_log(f"Potwierdzono pole {clicked}.")
                        continue
                    if clicked is None:
                        break
                continue
            if positions:
                try:
                    self.game.conn.set_leds(positions, consts.MOVE_FIELD_RGB)
                except Exception:
                    pass
            if ui is not None and getattr(ui, "enabled", False) and hasattr(ui, "prompt_info"):
                try:
                    ui.prompt_info("Setup encounteru", prompt_long=prompt, source="encounter_setup")
                except Exception:
                    pass
            else:
                try:
                    self.game.conn.read_card(prompt, ["ACCEPT"])
                except Exception:
                    pass
            if positions:
                try:
                    self.game.conn.leds_off()
                except Exception:
                    pass

    def run_encounter_setup(self):
        logger.info("Start setupu proceduralnego encounteru.")
        self.game.ui_log("Start setupu proceduralnego encounteru.")
        self._setup_batches()
        return self.set_heroes_starting_positions()
