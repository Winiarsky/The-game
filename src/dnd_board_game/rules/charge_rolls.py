"""Charge replaces proficiency for the board-game profile's d20 tests."""
from __future__ import annotations
from dataclasses import replace
from .dice import D20RollRequest, RollModifier, RollModifierType


def uses_charge(actor: object) -> bool:
    return any(getattr(f, "feature_id", "") == "pooled_mana_v01"
               for f in getattr(actor, "features", ()))


def replace_proficiency(request: D20RollRequest, bonus: int = 0) -> D20RollRequest:
    modifiers = tuple(m for m in request.modifiers
                      if m.modifier_type not in {RollModifierType.PROFICIENCY, RollModifierType.EXPERTISE}
                      and m.stacking_key not in {"proficiency", "charge_accuracy"})
    return replace(request, modifiers=(*modifiers, RollModifier(
        "Naładowanie", bonus, RollModifierType.CUSTOM, "charge_accuracy")))
