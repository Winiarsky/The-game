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

    def _apply_elixir(self, ctx, target, tier: str, tier_data: dict[str, object]) -> None:
        actor = getattr(ctx, "actor", None)
        actor_pos = getattr(actor, "position", None)
        duration = max(1, int(tier_data.get("duration_rounds", _minutes(1)) or _minutes(1)))
        radius = max(0, int(tier_data.get("radius_cells", 1) or 1))
        board = getattr(ctx.game, "board", None)

        affected = 0
        seen: set[object] = set()
        cloud_positions: list[tuple[int, int]] = []
        if board is not None and actor_pos is not None:
            positions = [actor_pos]
            if radius >= 1:
                try:
                    positions.extend(list(board.get_neighbors(actor_pos, include_position=False, diagonal=True)))
                except Exception:
                    pass
            cloud_positions = [tuple(pos) for pos in positions]
            for pos in positions:
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
        ui = getattr(ctx.game, "ui", None)
        if ui is not None and hasattr(ui, "prompt_info"):
            try:
                ui.prompt_info(
                    "Dymna fiolka",
                    prompt_long=(
                        f"Przy tobie powstaje zasłona dymna w obszarze 3x3 na {duration} rund.\n"
                        "W tej implementacji istoty stojące w chmurze dostają status Concealed. "
                        "Ataki przeciw takim celom wymagają flat checku przeciw concealment."
                    ),
                    source=self.name,
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
