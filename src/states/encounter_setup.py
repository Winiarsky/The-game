from __future__ import annotations

import logging
from dataclasses import asdict

from board import consts

from .start import Start

logger = logging.getLogger(__name__)


def run_setup_batches(game, batches) -> None:
    for raw_batch in batches or []:
        batch = asdict(raw_batch) if hasattr(raw_batch, "__dataclass_fields__") else dict(raw_batch)
        kind = str(batch.get("kind") or "").strip().lower()
        prompt = str(batch.get("prompt") or "Przygotuj planszę.")
        mode = str(batch.get("confirmation_mode") or "confirm_only")
        positions = EncounterSetupState._unique_positions(tuple(pos) for pos in list(batch.get("positions") or []))
        color = batch.get("color") or consts.MOVE_FIELD_RGB
        edges = list(batch.get("edges") or [])
        led_colors = color
        if kind == "wall" and positions:
            led_colors = _wall_endpoint_colors(positions)
            prompt = (
                f"{prompt}\n"
                "Końce każdej ściany są rozróżnione kolorami: zielony <-> pomarańczowy. "
                "Ustaw segment ściany pomiędzy sąsiednimi LED-ami w tych dwóch kolorach."
            )
        game.ui_log(prompt)
        ui = getattr(game, "ui", None)
        if mode == "click_all" and positions:
            pending = list(positions)
            while pending:
                pending_colors = led_colors
                if kind == "wall":
                    pending_colors = _wall_endpoint_colors(pending)
                game.conn.set_leds(pending, pending_colors)
                clicked = game.conn.scan_board(pending)
                game.conn.leds_off()
                if clicked in pending:
                    pending = [pos for pos in pending if pos != clicked]
                    game.ui_log(f"Potwierdzono pole {clicked}.")
                    continue
                if clicked is None:
                    break
                game.ui_log("Nie rozpoznano poprawnego pola setupu. Potwierdź elementy w UI, aby kontynuować.")
                break
            continue
        if positions:
            try:
                game.conn.set_leds(positions, led_colors)
            except Exception:
                pass
        if edges:
            game.ui_log(f"Krawędzie: {edges}")
        if ui is not None and hasattr(ui, "prompt_info"):
            try:
                ui.prompt_info("Setup encounteru", prompt_long=prompt, source="encounter_setup")
            except Exception:
                pass
        elif not getattr(ui, "enabled", False):
            try:
                input(f"{prompt} (Enter aby kontynuować) ")
            except Exception:
                pass
        if positions:
            try:
                game.conn.leds_off()
            except Exception:
                pass


class EncounterSetupState(Start):
    initial_action_name = "run_encounter_setup"

    @staticmethod
    def _unique_positions(positions):
        unique: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()
        for pos in positions:
            normalized = tuple(pos)
            if normalized in seen:
                continue
            seen.add(normalized)
            unique.append(normalized)
        return unique


def _wall_endpoint_colors(positions: list[tuple[int, int]] | tuple[tuple[int, int], ...]) -> list[list[int]]:
    colors: list[list[int]] = []
    for col, row in positions:
        if (int(col) + int(row)) % 2 == 0:
            colors.append(list(consts.WALL_ENDPOINT_A_RGB))
        else:
            colors.append(list(consts.WALL_ENDPOINT_B_RGB))
    return colors

    def _setup_batches(self):
        batches = getattr(self.game, "encounter_setup_plan", None) or []
        run_setup_batches(self.game, batches)

    def run_encounter_setup(self):
        logger.info("Start setupu proceduralnego encounteru.")
        self.game.ui_log("Start setupu proceduralnego encounteru.")
        self._setup_batches()
        return self.set_heroes_starting_positions()
