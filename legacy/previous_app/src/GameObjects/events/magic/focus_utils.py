from __future__ import annotations


def focus_spell_rank(actor, *, minimum: int = 1) -> int:
    """Focus spells auto-heighten to ceil(level/2)."""
    level = getattr(actor, "level", 1)
    try:
        lvl = int(level or 1)
    except Exception:
        lvl = 1
    rank = max(int(minimum), (max(1, lvl) + 1) // 2)

    # Optional developer override for tests/debug.
    override = getattr(actor, "focus_spell_rank_override", None)
    if override is not None:
        try:
            rank = max(int(minimum), int(override))
        except Exception:
            pass
    return rank


__all__ = ["focus_spell_rank"]
