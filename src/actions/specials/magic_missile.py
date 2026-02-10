from __future__ import annotations

from damage_types import DamageType

def magic_missile_ability(*_args, **_kwargs):
    """Stub czaru Magic Missile – zwraca minimalny opis obrażeń."""
    return {"damage": f"1d4+1 {DamageType.FORCE.value}", "missiles": 1}
