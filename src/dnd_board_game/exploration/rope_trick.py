"""Serializable runtime state for the Rope Trick extradimensional space."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace

from dnd_board_game.actors import Actor

from .models import TimedMagicEffect


@dataclass(frozen=True, slots=True)
class RopeTrickSpace:
    anchor_id: str
    rope_length_feet: int
    occupant_actor_ids: tuple[str, ...] = ()
    rope_pulled_inside: bool = False

    def __post_init__(self) -> None:
        if not self.anchor_id.strip():
            raise ValueError("Sztuczka z liną wymaga punktu zakotwiczenia.")
        if not 5 <= self.rope_length_feet <= 60:
            raise ValueError("Lina musi mieć od 5 do 60 ft długości.")
        if self.rope_length_feet % 5:
            raise ValueError("Długość liny musi być wielokrotnością 5 ft.")
        if len(self.occupant_actor_ids) != len(set(self.occupant_actor_ids)):
            raise ValueError("Lista osób w przestrzeni nie może zawierać duplikatów.")
        if len(self.occupant_actor_ids) > 8:
            raise ValueError("Przestrzeń mieści najwyżej 8 istot Medium lub mniejszych.")


def encode_rope_trick(space: RopeTrickSpace) -> str:
    return json.dumps(
        {
            "anchor_id": space.anchor_id,
            "rope_length_feet": space.rope_length_feet,
            "occupant_actor_ids": list(space.occupant_actor_ids),
            "rope_pulled_inside": space.rope_pulled_inside,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def decode_rope_trick(value: str) -> RopeTrickSpace:
    try:
        raw = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Uszkodzony zapis Sztuczki z liną.") from exc
    if not isinstance(raw, dict):
        raise ValueError("Zapis Sztuczki z liną musi być obiektem.")
    return RopeTrickSpace(
        anchor_id=str(raw.get("anchor_id", "")),
        rope_length_feet=int(raw.get("rope_length_feet", 0)),
        occupant_actor_ids=tuple(
            str(actor_id) for actor_id in raw.get("occupant_actor_ids", [])
        ),
        rope_pulled_inside=bool(raw.get("rope_pulled_inside", False)),
    )


def enter_rope_trick(
    effect: TimedMagicEffect,
    actor: Actor,
) -> TimedMagicEffect:
    space = decode_rope_trick(str(effect.flag_value))
    actor_id = str(actor.id)
    if actor_id in space.occupant_actor_ids:
        raise ValueError(f"{actor.name} już znajduje się w przestrzeni.")
    if actor.size.value not in {"tiny", "small", "medium"}:
        raise ValueError("Do przestrzeni mieszczą się tylko istoty Medium lub mniejsze.")
    if len(space.occupant_actor_ids) >= 8:
        raise ValueError("Przestrzeń Sztuczki z liną jest pełna.")
    updated = replace(
        space,
        occupant_actor_ids=(*space.occupant_actor_ids, actor_id),
    )
    return replace(effect, flag_value=encode_rope_trick(updated))


def exit_rope_trick(
    effect: TimedMagicEffect,
    actor_id: str,
) -> TimedMagicEffect:
    space = decode_rope_trick(str(effect.flag_value))
    if actor_id not in space.occupant_actor_ids:
        raise ValueError("Ta postać nie znajduje się w przestrzeni.")
    updated = replace(
        space,
        occupant_actor_ids=tuple(
            occupant
            for occupant in space.occupant_actor_ids
            if occupant != actor_id
        ),
    )
    return replace(effect, flag_value=encode_rope_trick(updated))


def set_rope_pulled_inside(
    effect: TimedMagicEffect,
    pulled_inside: bool,
) -> TimedMagicEffect:
    space = decode_rope_trick(str(effect.flag_value))
    return replace(
        effect,
        flag_value=encode_rope_trick(
            replace(space, rope_pulled_inside=bool(pulled_inside))
        ),
    )


__all__ = [
    "RopeTrickSpace",
    "decode_rope_trick",
    "encode_rope_trick",
    "enter_rope_trick",
    "exit_rope_trick",
    "set_rope_pulled_inside",
]
