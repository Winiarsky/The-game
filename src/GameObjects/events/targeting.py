from __future__ import annotations


def _has_status(target, status_id: str) -> bool:
    has_status = getattr(target, "has_status", None)
    if callable(has_status):
        try:
            return bool(has_status(status_id))
        except Exception:
            return False
    statuses = getattr(target, "statuses", None)
    if not statuses:
        return False
    for status in statuses:
        if getattr(status, "id", None) == status_id:
            return True
    return False


def is_target_blocked_by_tags(target, tags: list[str] | tuple[str, ...] | None) -> bool:
    if not tags:
        return False
    statuses = getattr(target, "statuses", None) or []
    for status in statuses:
        data = getattr(status, "data", None) or {}
        immune_tags = set(data.get("immune_status_tags", []) or [])
        if immune_tags and immune_tags.intersection(tags):
            return True
    return False
