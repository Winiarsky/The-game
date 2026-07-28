"""Deterministic permission gates granted by character backgrounds."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BackgroundPermissionResolution:
    actor_id: str
    permission_id: str
    allowed: bool
    feature_id: str | None
    message: str


def actor_background_permission_ids(actor: object) -> tuple[str, ...]:
    permissions: list[str] = []
    for feature in getattr(actor, "features", ()):
        source_kind = getattr(getattr(feature, "source_kind", None), "value", "")
        if source_kind != "background":
            continue
        permissions.extend(getattr(feature, "action_ids", ()))
    return tuple(dict.fromkeys(permissions))


def resolve_background_permission(
    actor: object,
    permission_id: str,
    *,
    scene_permission_ids: tuple[str, ...],
) -> BackgroundPermissionResolution:
    """Require both an actor grant and an authored scene opportunity."""
    actor_id = str(getattr(actor, "id", ""))
    if not permission_id.strip():
        raise ValueError("Background permission id cannot be empty.")
    feature = next(
        (
            grant
            for grant in getattr(actor, "features", ())
            if permission_id in getattr(grant, "action_ids", ())
            and getattr(getattr(grant, "source_kind", None), "value", "") == "background"
        ),
        None,
    )
    if feature is None:
        return BackgroundPermissionResolution(
            actor_id,
            permission_id,
            False,
            None,
            "Background postaci nie zapewnia tego uprawnienia.",
        )
    if permission_id not in scene_permission_ids:
        return BackgroundPermissionResolution(
            actor_id,
            permission_id,
            False,
            getattr(feature, "feature_id", None),
            "Ta scena nie udostępnia okazji do użycia tego uprawnienia.",
        )
    return BackgroundPermissionResolution(
        actor_id,
        permission_id,
        True,
        getattr(feature, "feature_id", None),
        "Uprawnienie backgroundu może zostać użyte w tej scenie.",
    )


__all__ = [
    "BackgroundPermissionResolution",
    "actor_background_permission_ids",
    "resolve_background_permission",
]
