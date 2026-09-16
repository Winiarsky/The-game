"""Deterministic timed fatigue, independent of scene transport and mana drains."""
from __future__ import annotations

from dnd_board_game.rules.effects import ActiveEffect, EffectDuration, EffectSource, EffectSourceType


def road_fatigue(actor_ids: tuple[str, ...], rounds: int, label: str) -> tuple[ActiveEffect, ...]:
    if type(rounds) is not int or not 1 <= rounds <= 4:
        raise ValueError('Zmęczenie wymaga naturalnego wyniku k4.')
    return tuple(ActiveEffect(
        id='mission_fatigue:' + actor, actor_id=actor, kind='scenario_fatigue',
        label=label, object_id='mission_road', value=-2,
        source=EffectSource(EffectSourceType.SCENE, 'mission_road'),
        duration=EffectDuration.UNTIL_ENCOUNTER_END, remaining_rounds=rounds,
    ) for actor in actor_ids)


def surrender_available(party_size: int, remaining_enemies: int, offered: bool) -> bool:
    return not offered and 0 < remaining_enemies < party_size
