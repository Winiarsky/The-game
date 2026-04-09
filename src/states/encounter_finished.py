from __future__ import annotations

import logging

from .base import State

logger = logging.getLogger(__name__)


class EncounterFinished(State):
    def on_enter(self):
        try:
            setattr(self.game, "finished", True)
        except Exception:
            pass
        logger.info("Encounter zakończony.")
        self.game.ui_log("Encounter zakończony.")
        ui = getattr(self.game, "ui", None)
        if ui is not None and getattr(ui, "enabled", False) and hasattr(ui, "prompt_info"):
            try:
                ui.prompt_info(
                    "Encounter zakończony",
                    prompt_long="Walka dobiegła końca. Proceduralny encounter został zamknięty.",
                    source="encounter_finish",
                )
            except Exception:
                pass

