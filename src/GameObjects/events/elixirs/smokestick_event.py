from __future__ import annotations

from board import consts
from led_fx import animate_area_wave
from statuses import Status

from .base_elixir_event import BaseElixirEvent, _minutes
from ..registry import register_event


def _apply_concealed_from_smoke(target, *, duration_rounds: int) -> bool:
    if target is None:
        return False
    remover = getattr(target, "remove_status", None)
    if callable(remover):
        try:
            remover("concealed")
        except Exception:
            pass
    adder = getattr(target, "add_status", None)
    if not callable(adder):
        return False
    try:
        adder(
            Status(
                id="concealed",
                label="Concealed (Dym)",
                duration=max(1, int(duration_rounds or 1)),
                source="smokestick",
                data={"effect_tags": ["concealment", "smoke"]},
            )
        )
        return True
    except Exception:
        return False


@register_event
class SmokestickEvent(BaseElixirEvent):
    """Uproszczona implementacja smokesticka:
    nakłada concealed na istoty w polu 3x3 wokół użytkownika.
    """

    name = "smokestick"
    default_tags = ["alchemical", "tool", "manipulate", "smoke"]
    prompt_description = (
        "Lesser Smokestick: generuje zaslone dymna.\n"
        "Uproszczenie silnika: naklada concealed na istoty w obszarze 3x3 "
        "wokol uzywajacego na 1 minute."
    )
    tier_choices = ("lesser",)
    tiers = {"lesser": {"duration_rounds": _minutes(1), "radius_cells": 1}}

    def _prompt_level(self) -> str | None:
        # Jedyny wariant z tabeli CRB 6-11 dla tej implementacji.
        return "lesser"

    def _pick_target(self, ctx, actor_pos: tuple[int, int]):
        # Smokestick tworzy dym przy użytkowniku.
        return ctx.actor, actor_pos

    def _cloud_positions(self, ctx, actor_pos: tuple[int, int] | None, radius: int) -> list[tuple[int, int]]:
        board = getattr(ctx.game, "board", None)
        if board is None or actor_pos is None:
            return []
        positions = [tuple(actor_pos)]
        if radius >= 1:
            try:
                positions.extend([tuple(pos) for pos in board.get_neighbors(actor_pos, include_position=False, diagonal=True)])
            except Exception:
                pass
        seen: set[tuple[int, int]] = set()
        result: list[tuple[int, int]] = []
        for pos in positions:
            if pos in seen:
                continue
            seen.add(pos)
            result.append(pos)
        return result

    def _confirm_use(self, ctx, target, target_pos: tuple[int, int], tier: str, tier_data: dict[str, object]) -> bool:
        actor = getattr(ctx, "actor", None)
        actor_pos = getattr(actor, "position", None)
        duration = max(1, int(tier_data.get("duration_rounds", _minutes(1)) or _minutes(1)))
        radius = max(0, int(tier_data.get("radius_cells", 1) or 1))
        cloud_positions = self._cloud_positions(ctx, actor_pos, radius)
        conn = getattr(ctx.game, "conn", None)
        highlighted = False
        try:
            if conn is not None and cloud_positions:
                palette = list(getattr(consts, "SMOKE_CLOUD_PALETTE", []) or [])
                conn.set_leds(cloud_positions, palette[1] if len(palette) > 1 else consts.INTERACT_FIELD_RGB)
                highlighted = True
        except Exception:
            highlighted = False
        try:
            ui = getattr(ctx.game, "ui", None)
            if ui is not None and hasattr(ui, "prompt_info"):
                ui.prompt_info(
                    "Dymna fiolka",
                    prompt_long=(
                        "Lesser Smokestick: użycie za 1 akcję Interact.\n"
                        "Tworzy dym o promieniu 5 ft przy twojej pozycji na 1 minutę.\n"
                        "Istoty w dymie są concealed, a istoty poza dymem są concealed dla istot w dymie.\n\n"
                        f"W silniku zostanie podświetlony obszar {len(cloud_positions)} pól i aktywowany na {duration} rund. "
                        "Naciśnij Enter, aby zużyć przedmiot i zastosować efekt."
                    ),
                    source=self.name,
                )
        finally:
            if highlighted:
                try:
                    conn.leds_off()
                except Exception:
                    pass
        return True

    def _apply_elixir(self, ctx, target, tier: str, tier_data: dict[str, object]) -> None:
        actor = getattr(ctx, "actor", None)
        actor_pos = getattr(actor, "position", None)
        duration = max(1, int(tier_data.get("duration_rounds", _minutes(1)) or _minutes(1)))
        radius = max(0, int(tier_data.get("radius_cells", 1) or 1))
        board = getattr(ctx.game, "board", None)

        affected = 0
        seen: set[object] = set()
        cloud_positions: list[tuple[int, int]] = self._cloud_positions(ctx, actor_pos, radius)
        if board is not None and actor_pos is not None:
            for pos in cloud_positions:
                try:
                    occ = board.occupant_at(pos)
                except Exception:
                    occ = None
                if occ is None or occ in seen:
                    continue
                seen.add(occ)
                if _apply_concealed_from_smoke(occ, duration_rounds=duration):
                    affected += 1

        if affected == 0 and _apply_concealed_from_smoke(target, duration_rounds=duration):
            affected = 1

        try:
            clouds = getattr(ctx.game, "_smoke_clouds", None)
            if not isinstance(clouds, list):
                clouds = []
                setattr(ctx.game, "_smoke_clouds", clouds)
            round_index = getattr(getattr(ctx.game, "state", None), "round_index", None)
            expires_round = None
            try:
                if round_index is not None:
                    expires_round = int(round_index) + duration
            except Exception:
                expires_round = None
            clouds.append(
                {
                    "source": self.name,
                    "origin": tuple(actor_pos) if actor_pos is not None else None,
                    "positions": list(cloud_positions),
                    "duration_rounds": duration,
                    "expires_round": expires_round,
                }
            )
        except Exception:
            pass

        try:
            animate_area_wave(
                getattr(ctx.game, "conn", None),
                actor_pos,
                cloud_positions,
                palette=getattr(consts, "SMOKE_CLOUD_PALETTE", None),
            )
        except Exception:
            pass

        try:
            ctx.game.ui_log(
                f"Smokestick ({tier}): zaslona dymna aktywna przez {duration} rund. "
                f"Concealed na {affected} obiektach."
            )
        except Exception:
            pass
        try:
            ctx.game.events.safe_emit_action(
                actor=actor,
                action_id=self.name,
                action_tags=self.default_tags,
                summary=(
                    f"Dymna fiolka: chmura 3x3 przy {getattr(actor, 'name', 'bohaterze')} "
                    f"na {duration} rund, concealed na {affected} obiektach."
                ),
                duration_rounds=duration,
                affected_count=affected,
                area_positions=cloud_positions,
            )
        except Exception:
            pass
