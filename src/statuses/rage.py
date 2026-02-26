from __future__ import annotations

from statuses.base import Status

RAGE_DURATION_TURNS = 10
RAGE_DEFAULT_DAMAGE_BONUS = 2
RAGE_DEFAULT_AC_PENALTY = 1

RAGE_PROMPT = (
    "Rage: wpadasz w szał na 1 minutę (10 tur).\n"
    "Szał kończy się, gdy nie widzisz wrogów lub upadniesz nieprzytomny (pilnuj ręcznie).\n"
    "Zyskujesz tymczasowe HP = poziom + modyfikator z Kondycji (opisowo).\n"
    "Podczas szału:\n"
    "- +2 do obrażeń ataków wręcz (jeśli broń/agile: połowa).\n"
    "- -1 do AC.\n"
    "- Nie możesz używać akcji z traitem concentrate (pilnuj ręcznie)."
)


def RageStatus(
    *,
    duration: int | None = None,
    damage_bonus: int = RAGE_DEFAULT_DAMAGE_BONUS,
    ac_penalty: int = RAGE_DEFAULT_AC_PENALTY,
) -> Status:
    """Status Rage."""
    data = {
        "ui_prompt": RAGE_PROMPT,
        "effect_tags": ["rage"],
        "rage_damage_bonus": int(damage_bonus),
        "rage_ac_penalty": int(ac_penalty),
        "rage_agile_halved": True,
    }
    return Status(
        id="rage",
        label="Rage",
        duration=duration,
        data=data,
    )


RAGE_STATUS = RageStatus()


def rage_damage_bonus(attacker, *, is_agile: bool) -> int:
    """Zwróć bonus do obrażeń dla Rage (wręcz), z uwzględnieniem agile."""
    if attacker is None:
        return 0
    getter = getattr(attacker, "get_status_data", None)
    if callable(getter):
        bonus = getter("rage", "rage_damage_bonus", RAGE_DEFAULT_DAMAGE_BONUS)
        override = getter("dragon_instinct_active", "rage_damage_bonus_override", None)
        if override is not None:
            bonus = override
        agile_halved = getter("rage", "rage_agile_halved", True)
    else:
        bonus = RAGE_DEFAULT_DAMAGE_BONUS
        agile_halved = True
        override = None
        for status in getattr(attacker, "statuses", []) or []:
            if getattr(status, "id", None) == "dragon_instinct_active":
                data = getattr(status, "data", None) or {}
                override = data.get("rage_damage_bonus_override")
            if getattr(status, "id", None) != "rage":
                continue
            data = getattr(status, "data", None) or {}
            bonus = data.get("rage_damage_bonus", RAGE_DEFAULT_DAMAGE_BONUS)
            agile_halved = data.get("rage_agile_halved", True)
            break
        if override is not None:
            bonus = override
    try:
        bonus_val = int(bonus)
    except Exception:
        bonus_val = 0
    if is_agile and agile_halved:
        return max(0, bonus_val // 2)
    return max(0, bonus_val)


__all__ = [
    "RAGE_DURATION_TURNS",
    "RAGE_DEFAULT_DAMAGE_BONUS",
    "RAGE_DEFAULT_AC_PENALTY",
    "RAGE_PROMPT",
    "RageStatus",
    "RAGE_STATUS",
    "rage_damage_bonus",
]
