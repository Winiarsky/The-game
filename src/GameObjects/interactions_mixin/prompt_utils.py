from __future__ import annotations

import logging
from ui_client import get_ui_client

logger = logging.getLogger(__name__)


def prompt_for_roll(prompt: str) -> int:
    """Poproś o rzut i zwróć liczbę całkowitą (UI jeśli dostępny, inaczej konsola)."""
    ui_client = get_ui_client()
    if ui_client.enabled:
        ui_answer = ui_client.prompt_roll(prompt, source="game")
        if isinstance(ui_answer, int):
            return ui_answer

    while True:
        raw = input(prompt).strip()
        if not raw:
            continue
        try:
            return int(raw)
        except ValueError:
            continue
