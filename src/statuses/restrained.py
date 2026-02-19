from __future__ import annotations

from bonuses import BonusEffect, BonusType
from statuses.base import Status
from statuses.flat_footed import FLAT_FOOTED_STATUS


def RestrainedStatus(*, source_id: str | None = None, maintain_turns_left: int = 0) -> Status:
    """Status restrained (silniejszy chwyt)."""
    data = {
        "source_id": source_id,
        "maintain_turns_left": maintain_turns_left,
        "maintain_action_id": "grapple",
        "maintain_within_turns": 1,
        "allow_other_actions_in_meantime": False,
        "blocks_move": True,
        "flat_footed_source": "restrained",
    }
    return Status(id="restrained", label="Restrained", data=data)


RESTRAINED_STATUS = RestrainedStatus()


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


def apply_restrained_effects(target, *, source_id: str | None = None) -> None:
    """Nałóż efekty restrained (flat-footed + kara do ataków wręcz)."""
    remover = getattr(target, "remove_bonuses_by_source", None)
    if callable(remover):
        try:
            remover("restrained")
        except Exception:
            pass
    adder = getattr(target, "add_bonus", None)
    if callable(adder):
        try:
            adder(
                BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=2,
                    tag="attack_melee",
                    source="restrained",
                    label="restrained",
                    is_penalty=True,
                )
            )
        except Exception:
            pass
    if hasattr(target, "add_status"):
        try:
            target.add_status(
                Status(
                    id=FLAT_FOOTED_STATUS.id,
                    label=FLAT_FOOTED_STATUS.label,
                    data={"ac_penalty": 2, "flat_footed_source": "restrained", "source_id": source_id},
                )
            )
        except Exception:
            pass


def clear_restrained_effects(target) -> None:
    """Usuń efekty restrained (flat-footed + kara do ataków)."""
    remover = getattr(target, "remove_bonuses_by_source", None)
    if callable(remover):
        try:
            remover("restrained")
        except Exception:
            pass
    _remove_linked_flat_footed(target, "restrained")
