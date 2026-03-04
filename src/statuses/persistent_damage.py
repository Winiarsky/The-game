from __future__ import annotations

from typing import Iterable
import random

from damage_types import DamageType

from .base import Status

PERSISTENT_DAMAGE_STATUS = Status(id="persistent_damage", label="Persistent Damage", stacks=True)


def prompt_for_roll(*args, **kwargs):
    from GameObjects.interactions_mixin.prompt_utils import prompt_for_roll as _prompt_for_roll

    return _prompt_for_roll(*args, **kwargs)


def make_persistent_damage(amount: int, damage_type: str = DamageType.NORMAL.value, *, source: str | None = None) -> Status:
    """Helper do tworzenia statusu obrażeń ciągłych."""
    label = f"Persistent {damage_type} {amount}"
    return Status(
        id=PERSISTENT_DAMAGE_STATUS.id,
        label=label,
        stacks=True,
        source=source,
        data={"amount": int(amount), "damage_type": damage_type},
    )


def _iter_persistent(statuses: Iterable[Status]) -> list[Status]:
    return [s for s in statuses if getattr(s, "id", None) == PERSISTENT_DAMAGE_STATUS.id]


def _has_status_id(actor, status_id: str, statuses: Iterable[Status]) -> bool:
    has_status = getattr(actor, "has_status", None)
    if callable(has_status):
        try:
            return bool(has_status(status_id))
        except Exception:
            pass
    for status in statuses:
        if getattr(status, "id", None) == status_id or status == status_id:
            return True
    return False


def process_persistent_damage(actor, game) -> None:
    """Zastosuj obrażenia ciągłe na początku inicjatywy aktora."""
    statuses = getattr(actor, "statuses", []) or []
    persistent_list = _iter_persistent(statuses)
    if not persistent_list:
        return

    is_hero = actor in getattr(game, "heroes", [])
    ui_log = getattr(game, "ui_log", lambda msg: None)

    # zsumuj obrażenia per typ, ale utrzymaj oddzielne instancje różnych typów
    by_type: dict[str, list[Status]] = {}
    for status in persistent_list:
        damage_type = getattr(status, "data", {}).get("damage_type", DamageType.NORMAL.value)
        by_type.setdefault(str(damage_type), []).append(status)

    for damage_type, statuses_same_type in by_type.items():
        amount = sum(int(getattr(s, "data", {}).get("amount", 0)) for s in statuses_same_type)
        if amount <= 0:
            continue

        if is_hero:
            try:
                prompt_for_roll(
                    f"Persistent damage: otrzymujesz {amount} {damage_type}. "
                    "Podaj dowolną liczbę aby potwierdzić: ",
                    layout="info",
                )
            except Exception:
                pass
        ui_log(f"{getattr(actor, 'name', 'Aktor')} otrzymuje {amount} obrażeń ({damage_type}) z persistent.")

        apply = getattr(actor, "apply_damage", None)
        if callable(apply):
            try:
                apply(amount, damage_type)
            except Exception:
                pass

        # flat check: domyślnie DC 15 (zmiany dla wybranych heritage)
        dc = 15
        if damage_type == DamageType.FIRE.value and _has_status_id(actor, "charhide_goblin", statuses):
            dc = 10
        elif damage_type == DamageType.COLD.value and _has_status_id(actor, "snow_goblin", statuses):
            dc = 10

        if is_hero:
            try:
                roll = int(
                    prompt_for_roll(
                        f"Flat check na zakończenie persistent (DC {dc}): ",
                        layout="test",
                        answer_placeholder="Wynik rzutu",
                    )
                    or 0
                )
            except Exception:
                roll = 0
        else:
            roll = int(random.randint(1, 20))

        if roll >= dc:
            for st in list(statuses_same_type):
                try:
                    actor.remove_status(st)  # type: ignore[arg-type]
                except Exception:
                    try:
                        actor.remove_status(getattr(st, "id", PERSISTENT_DAMAGE_STATUS.id))  # type: ignore[arg-type]
                    except Exception:
                        pass
            ui_log("Persistent damage ustaje.")
        else:
            ui_log("Persistent damage utrzymuje się.")
