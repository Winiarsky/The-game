from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(init=False)
class WatchfulMixin:
    watch_disturbed: int = 0  # 0 blokuje stealth w pokoju, >0 daje karę do testu
    watch_disabled: bool = False
    perception_bonus: int = 0

    def _log_watch_event(self, message: str, game) -> None:
        """Wyślij komunikat do logów oraz (jeśli to możliwe) do UI."""
        if not message:
            return
        logger.info(message)
        ui_log = getattr(game, "ui_log", None)
        if callable(ui_log):
            try:
                ui_log(message)
            except Exception:
                # UI jest opcjonalne; gdy nie działa, nie blokujemy gry.
                logger.debug("Nie udało się wysłać komunikatu do UI.", exc_info=True)

    def __init__(
        self,
        *,
        watch_disturbed: int = 0,
        watch_disabled: bool = False,
        perception_bonus: int = 0,
        **_kwargs,
    ) -> None:
        self.watch_disturbed = watch_disturbed
        self.watch_disabled = watch_disabled
        self.perception_bonus = perception_bonus

    def attempt_spot(self, hero, game) -> tuple[bool, str]:
        """Próba wykrycia ukrytego bohatera; zwraca (wykryto, komunikat)."""
        dc = getattr(hero, "stealth_detection_dc", None)
        if dc is None or not getattr(hero, "has_status", lambda _s: False)("stealth"):
            return False, "Cel nie jest ukryty."
        roll = random.randint(1, 20) + self.perception_bonus
        penalty = getattr(hero, "perception_penalty", 0) or 0
        roll -= penalty
        if roll >= dc:
            try:
                hero.remove_status("stealth")  # type: ignore[attr-defined]
                hero.add_status("observable")  # type: ignore[attr-defined]
            except AttributeError:
                pass
            if hasattr(hero, "stealth_bonus"):
                hero.stealth_bonus = 0
            hero.stealth_detection_dc = None
            spotted_msg = f"Wykryto bohatera (r={roll} vs DC {dc})."
            try:
                extra = self.on_spot(hero, game)
                if extra:
                    spotted_msg = f"{spotted_msg} {extra}"
            except Exception:
                pass
            self._log_watch_event(spotted_msg, game)
            return True, spotted_msg
        miss_msg = f"Nie dostrzegasz bohatera (r={roll} vs DC {dc})."
        self._log_watch_event(miss_msg, game)
        return False, miss_msg

    def on_spot(self, hero, game) -> Optional[str]:
        """Hook wywoływany przy sukcesie wykrycia."""
        return None

    def on_move_action(self, hero, game) -> Optional[str]:
        """Hook dla akcji Move (placeholder na przyszłe triggery)."""
        return None
