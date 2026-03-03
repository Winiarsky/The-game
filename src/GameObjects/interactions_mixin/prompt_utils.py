from __future__ import annotations

import logging
from ui_client import get_ui_client
from combat.degree_of_success import natural_mode_from_shift, natural_shift_from_mode, natural_shift_from_roll

logger = logging.getLogger(__name__)


def _parse_roll_details(answer, *, infer_natural_from_roll: bool = False) -> dict[str, object]:
    roll = 0
    shift = 0

    if isinstance(answer, dict):
        roll_val = answer.get("roll", answer.get("value", answer.get("result", 0)))
        try:
            roll = int(roll_val or 0)
        except Exception:
            roll = 0
        mode = answer.get("natural_mode", answer.get("natural", answer.get("nat", None)))
        shift = natural_shift_from_mode(mode)
        if shift == 0 and infer_natural_from_roll:
            shift = natural_shift_from_roll(roll)
    else:
        try:
            roll = int(answer or 0)
        except Exception:
            roll = 0
        if infer_natural_from_roll:
            shift = natural_shift_from_roll(roll)

    return {
        "roll": int(roll),
        "natural_shift": int(shift),
        "natural_mode": natural_mode_from_shift(shift),
    }


def prompt_for_roll(prompt: str, *, return_details: bool = False, infer_natural_from_roll: bool = False, **ui_kwargs):
    """Poproś o rzut i zwróć liczbę całkowitą (UI; CLI tylko gdy ALLOW_CLI_FALLBACK=1).

    Domyślnie wysyła do UI jako layout \"test\" (check), żeby zachować spójny wygląd
    wszystkich promptów na rzuty. Można nadpisać layout/placeholder via **ui_kwargs.
    """
    ui_client = get_ui_client()
    if ui_client.enabled:
        if "layout" not in ui_kwargs:
            ui_kwargs["layout"] = "test"
        ui_kwargs.setdefault("answer_placeholder", "Podaj wynik rzutu")
        ui_answer = ui_client.prompt_roll(
            prompt,
            source="game",
            return_meta=bool(return_details),
            **ui_kwargs,
        )
        if return_details:
            return _parse_roll_details(ui_answer, infer_natural_from_roll=infer_natural_from_roll)
        details = _parse_roll_details(ui_answer, infer_natural_from_roll=infer_natural_from_roll)
        return int(details.get("roll", 0) or 0)

    if not getattr(ui_client, "allow_cli_fallback", False):
        raise RuntimeError("UI-only mode: prompt_for_roll wymaga aktywnego UI.")

    while True:
        raw = input(prompt).strip()
        if not raw:
            continue
        try:
            value = int(raw)
            if return_details:
                return _parse_roll_details(value, infer_natural_from_roll=infer_natural_from_roll)
            return value
        except ValueError:
            continue
