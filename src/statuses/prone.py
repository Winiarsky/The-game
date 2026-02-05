from __future__ import annotations

from bonuses import BonusEffect, BonusType
from statuses.base import Status


def ProneStatus() -> Status:
    """Status leżenia (prone)."""
    return Status(id="prone", label="Prone", data={"attack_penalty": 2})


PRONE_STATUS = ProneStatus()


def apply_prone_effects(target) -> None:
    """Nałóż kary związane z prone na obiekt wspierający bonusy."""
    remover = getattr(target, "remove_bonuses_by_source", None)
    if callable(remover):
        try:
            remover("prone")
        except Exception:
            pass

    adder = getattr(target, "add_bonus", None)
    if not callable(adder):
        return

    penalty = 2
    for tag in ("attack_melee", "attack_ranged"):
        try:
            adder(
                BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=penalty,
                    tag=tag,
                    source="prone",
                    label="prone",
                    is_penalty=True,
                )
            )
        except Exception:
            continue


def clear_prone_effects(target) -> None:
    """Usuń kary prone z obiektu."""
    remover = getattr(target, "remove_bonuses_by_source", None)
    if callable(remover):
        try:
            remover("prone")
        except Exception:
            pass
