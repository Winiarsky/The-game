from __future__ import annotations

from statuses.base import Status

SNAGGING_STRIKE_DESCRIPTION = (
    "Snagging Strike: Strike z wolną ręką. "
    "Na trafieniu cel staje się flat-footed do początku twojej następnej tury (v1)."
)


def SnaggingStrikeStatus() -> Status:
    return Status(
        id="snagging_strike",
        label="Snagging Strike",
        data={"ui_description": SNAGGING_STRIKE_DESCRIPTION, "ui_prompt": SNAGGING_STRIKE_DESCRIPTION},
    )


SNAGGING_STRIKE_STATUS = SnaggingStrikeStatus()


def _actor_id(actor) -> str | None:
    if actor is None:
        return None
    return getattr(actor, "object_id", None) or getattr(actor, "name", None) or str(id(actor))


def _iter_statuses(target):
    statuses = getattr(target, "statuses", None)
    if not isinstance(statuses, list):
        return []
    return list(statuses)


def clear_snagging_flat_footed(target, *, source_id: str | None = None) -> int:
    statuses = getattr(target, "statuses", None)
    if not isinstance(statuses, list) or not statuses:
        return 0
    kept: list[object] = []
    removed = 0
    for status in statuses:
        sid = getattr(status, "id", status)
        if sid != "flat_footed":
            kept.append(status)
            continue
        data = getattr(status, "data", None) or {}
        if data.get("flat_footed_source") != "snagging_strike":
            kept.append(status)
            continue
        if source_id is not None and data.get("source_id") != source_id:
            kept.append(status)
            continue
        removed += 1
    if removed:
        try:
            target.statuses = kept
        except Exception:
            pass
    return int(removed)


def apply_snagging_flat_footed(target, *, source_actor, source_turns_left: int = 1, reach: int = 1) -> bool:
    source_id = _actor_id(source_actor)
    if source_id is None:
        return False
    clear_snagging_flat_footed(target, source_id=source_id)
    adder = getattr(target, "add_status", None)
    status = Status(
        id="flat_footed",
        label="Snagging Strike",
        source="snagging_strike",
        data={
            "ac_penalty": 2,
            "flat_footed_source": "snagging_strike",
            "source_id": source_id,
            "source_turns_left": max(1, int(source_turns_left or 1)),
            "reach": max(1, int(reach or 1)),
        },
    )
    if callable(adder):
        try:
            adder(status)
            return True
        except Exception:
            return False
    statuses = getattr(target, "statuses", None)
    if isinstance(statuses, list):
        statuses.append(status)
        return True
    return False


def cleanup_snagging_flat_footed(game) -> int:
    actors = list(getattr(game, "heroes", []) or []) + list(getattr(game, "enemies", []) or [])
    by_id = {_actor_id(actor): actor for actor in actors}
    total_removed = 0
    for target in actors:
        statuses = _iter_statuses(target)
        if not statuses:
            continue
        target_pos = getattr(target, "position", None)
        kept: list[object] = []
        removed = 0
        for status in statuses:
            sid = getattr(status, "id", status)
            if sid != "flat_footed":
                kept.append(status)
                continue
            data = getattr(status, "data", None) or {}
            if data.get("flat_footed_source") != "snagging_strike":
                kept.append(status)
                continue
            source_id = data.get("source_id")
            source_actor = by_id.get(source_id)
            source_pos = getattr(source_actor, "position", None) if source_actor is not None else None
            try:
                reach = max(1, int(data.get("reach", 1) or 1))
            except Exception:
                reach = 1
            out_of_reach = (
                source_actor is None
                or target_pos is None
                or source_pos is None
                or max(abs(int(target_pos[0]) - int(source_pos[0])), abs(int(target_pos[1]) - int(source_pos[1]))) > reach
            )
            if out_of_reach:
                removed += 1
            else:
                kept.append(status)
        if removed:
            total_removed += removed
            try:
                target.statuses = kept
            except Exception:
                pass
    return int(total_removed)


__all__ = [
    "SnaggingStrikeStatus",
    "SNAGGING_STRIKE_STATUS",
    "SNAGGING_STRIKE_DESCRIPTION",
    "apply_snagging_flat_footed",
    "clear_snagging_flat_footed",
    "cleanup_snagging_flat_footed",
]
