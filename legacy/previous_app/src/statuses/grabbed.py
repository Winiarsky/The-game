from __future__ import annotations

from bonuses import BonusEffect, BonusType
from statuses.base import Status
from statuses.flat_footed import FLAT_FOOTED_STATUS


def GrabbedStatus(*, source_id: str | None = None, maintain_turns_left: int = 0) -> Status:
    """Status grabbed (chwyt)."""
    data = {
        "source_id": source_id,
        "maintain_turns_left": maintain_turns_left,
        "maintain_action_id": "grapple",
        "maintain_within_turns": 1,
        "allow_other_actions_in_meantime": False,
        "blocks_move": True,
        "flat_footed_source": "grabbed",
        "effect_tags": ["grabbed", "immobilized", "off_guard"],
    }
    return Status(id="grabbed", label="Grabbed", data=data)


GRABBED_STATUS = GrabbedStatus()


def _remove_linked_flat_footed(target, source_tag: str) -> None:
    remover = getattr(target, "remove_status", None)
    statuses = getattr(target, "statuses", None)
    if not isinstance(statuses, list):
        return
    for status in list(statuses):
        if getattr(status, "id", None) != FLAT_FOOTED_STATUS.id:
            continue
        data = getattr(status, "data", None) or {}
        if data.get("flat_footed_source") != source_tag:
            continue
        if callable(remover):
            try:
                remover(status)
                continue
            except Exception:
                pass
        try:
            statuses.remove(status)
        except ValueError:
            pass


def apply_grabbed_effects(target, *, source_id: str | None = None) -> None:
    """Nałóż efekty grabbed (flat-footed)."""
    if not hasattr(target, "add_status"):
        return
    try:
        target.add_status(
            Status(
                id=FLAT_FOOTED_STATUS.id,
                label=FLAT_FOOTED_STATUS.label,
                data={"ac_penalty": 2, "flat_footed_source": "grabbed", "source_id": source_id},
            )
        )
    except Exception:
        pass


def clear_grabbed_effects(target) -> None:
    """Usuń efekty grabbed (flat-footed powiązany z grabbed)."""
    _remove_linked_flat_footed(target, "grabbed")
