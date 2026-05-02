from __future__ import annotations

import logging
from dataclasses import asdict

from board import consts
from communication import make_debug_communication, make_setup_step_communication
from prompt_copy import prompt_value

from .start import Start

logger = logging.getLogger(__name__)


def run_setup_batches(game, batches) -> None:
    prepared_batches = list(batches or [])
    total_steps = len(prepared_batches)
    for idx, raw_batch in enumerate(prepared_batches, start=1):
        batch = asdict(raw_batch) if hasattr(raw_batch, "__dataclass_fields__") else dict(raw_batch)
        kind = str(batch.get("kind") or "").strip().lower()
        prompt = str(batch.get("prompt") or "Przygotuj planszę.")
        mode = str(batch.get("confirmation_mode") or "confirm_only")
        positions = EncounterSetupState._unique_positions(tuple(pos) for pos in list(batch.get("positions") or []))
        color = batch.get("color") or consts.MOVE_FIELD_RGB
        colors = list(batch.get("colors") or [])
        edges = list(batch.get("edges") or [])
        progress = {
            "current": idx,
            "total": total_steps,
            "label": f"Krok {idx}/{total_steps}",
        }
        led_colors = _led_colors_for_positions(positions, colors, color)
        if kind == "wall" and positions:
            led_colors = _wall_endpoint_colors(positions)
            prompt = (
                f"{prompt}\n"
                "Końce każdej ściany są rozróżnione kolorami: zielony <-> pomarańczowy. "
                "Ustaw segment ściany pomiędzy sąsiednimi LED-ami w tych dwóch kolorach."
            )
        ui = getattr(game, "ui", None)
        if mode == "click_all" and positions:
            pending = list(positions)
            while pending:
                pending_colors = led_colors
                if kind == "wall":
                    pending_colors = _wall_endpoint_colors(pending)
                elif colors:
                    pending_colors = _led_colors_for_positions(pending, colors, color, all_positions=positions)
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
            try:
                game.player_prompt.card(
                    kind="debug",
                    title=str(prompt_value("setup.encounter_edges_debug", "title", "Krawędzie setupu")),
                    body_markdown=str(
                        prompt_value(
                            "setup.encounter_edges_debug",
                            "body_markdown",
                            "Dane techniczne ścian dostępne w szczegółach.",
                        )
                    ),
                    details_markdown=f"Krawędzie: {edges}",
                    priority="debug",
                    scope_key="setup",
                    dedupe_key=f"setup_edges:{idx}",
                )
            except Exception:
                try:
                    game.ui_log(
                        "Dane techniczne ścian dostępne w szczegółach.",
                        communication=make_debug_communication(
                            title=str(prompt_value("setup.encounter_edges_debug", "title", "Krawędzie setupu")),
                            details_markdown=f"Krawędzie: {edges}",
                            dedupe_key=f"setup_edges:{idx}",
                        ),
                    )
                except TypeError:
                    game.ui_log(f"Krawędzie: {edges}")
        setup_communication = make_setup_step_communication(
            title=str(prompt_value("setup.encounter_step", "title", "Setup encounteru")),
            body_markdown=prompt,
            progress=progress,
            details_markdown=(f"Krawędzie: {edges}" if edges else None),
            blocking=True,
        )
        prompt_handled = False
        try:
            prompt_handled = game.player_prompt.info(
                str(prompt_value("setup.encounter_step", "title", "Setup encounteru")),
                body_markdown=prompt,
                summary=str(prompt_value("setup.encounter_step", "summary", "Setup encounteru")),
                details_markdown=(f"Krawędzie: {edges}" if edges else None),
                source="encounter_setup",
                scope_key="setup",
                dedupe_key=f"setup:{idx}/{total_steps}",
                progress=progress,
            ) is not None
        except Exception:
            prompt_handled = False
        if not prompt_handled:
            try:
                game.ui_log(
                    prompt,
                    communication=setup_communication,
                )
            except TypeError:
                game.ui_log(prompt)
            if ui is not None and getattr(ui, "enabled", False) and hasattr(ui, "prompt_info"):
                try:
                    ui.prompt_info(
                        str(prompt_value("setup.encounter_step", "title", "Setup encounteru")),
                        prompt_long=prompt,
                        source="encounter_setup",
                        communication=setup_communication,
                        prompt_id="setup.encounter_step",
                    )
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

    def _setup_batches(self):
        batches = getattr(self.game, "encounter_setup_plan", None) or []
        run_setup_batches(self.game, batches)

    def run_encounter_setup(self):
        logger.info("Start setupu proceduralnego encounteru.")
        self.game.ui_log("Start setupu proceduralnego encounteru.")
        self._setup_batches()
        return self.set_heroes_starting_positions()


def _wall_endpoint_colors(positions: list[tuple[int, int]] | tuple[tuple[int, int], ...]) -> list[list[int]]:
    colors: list[list[int]] = []
    for col, row in positions:
        if (int(col) + int(row)) % 2 == 0:
            colors.append(list(consts.WALL_ENDPOINT_A_RGB))
        else:
            colors.append(list(consts.WALL_ENDPOINT_B_RGB))
    return colors


def _normalize_color(color) -> list[int] | None:
    if not isinstance(color, (list, tuple)) or len(color) < 3:
        return None
    try:
        return [int(color[0]), int(color[1]), int(color[2])]
    except Exception:
        return None


def _led_colors_for_positions(
    positions: list[tuple[int, int]],
    colors: list[object],
    fallback,
    *,
    all_positions: list[tuple[int, int]] | None = None,
) -> list[int] | list[list[int]]:
    fallback_color = _normalize_color(fallback) or list(consts.MOVE_FIELD_RGB)
    if not colors:
        return fallback_color
    reference = list(all_positions or positions)
    color_by_position: dict[tuple[int, int], list[int]] = {}
    for idx, pos in enumerate(reference):
        if idx >= len(colors):
            break
        color = _normalize_color(colors[idx])
        if color is not None:
            color_by_position[tuple(pos)] = color
    if not color_by_position:
        return fallback_color
    return [color_by_position.get(tuple(pos), fallback_color) for pos in positions]
