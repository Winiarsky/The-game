from __future__ import annotations

import logging
from ui_client import get_ui_client

logger = logging.getLogger(__name__)


def prompt_for_roll(prompt: str, **ui_kwargs) -> int:
    """Poproś o rzut i zwróć liczbę całkowitą (UI jeśli dostępny, inaczej konsola).

    Domyślnie wysyła do UI jako layout \"test\" (check), żeby zachować spójny wygląd
    wszystkich promptów na rzuty. Można nadpisać layout/placeholder via **ui_kwargs.
    """
    ui_client = get_ui_client()
    if ui_client.enabled:
        if "layout" not in ui_kwargs:
            ui_kwargs["layout"] = "test"
        ui_kwargs.setdefault("answer_placeholder", "Podaj wynik rzutu")
        ui_answer = ui_client.prompt_roll(prompt, source="game", **ui_kwargs)
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
