"""Magic-related events."""

from .magic_missile_event import MagicMissileEvent  # noqa: F401

__all__ = [
    "MagicMissileEvent",
    "magic_missile_event",
]

from . import magic_missile_event  # type: ignore  # noqa: F401,E402
