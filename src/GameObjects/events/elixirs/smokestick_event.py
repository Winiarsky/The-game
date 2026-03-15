from __future__ import annotations

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
        if board is not None and actor_pos is not None:
            positions = [actor_pos]
            if radius >= 1:
                try:
                    positions.extend(list(board.get_neighbors(actor_pos, include_position=False, diagonal=True)))
                except Exception:
                    pass
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
            ctx.game.ui_log(
                f"Smokestick ({tier}): zaslona dymna aktywna przez {duration} rund. "
                f"Concealed na {affected} obiektach."
            )
        except Exception:
            pass

