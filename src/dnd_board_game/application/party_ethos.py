"""Campaign flag boundary for the deterministic party-ethos rule."""
from __future__ import annotations

import json

from dnd_board_game.combat.scene import SceneFlags, scene_flag, set_scene_flag
from dnd_board_game.rules.party_ethos import PartyEthos, shift

KEY = 'campaign_party_ethos_v1'


def read(flags: SceneFlags) -> PartyEthos:
    raw = json.loads(str(scene_flag(flags, KEY, '{}')))
    return PartyEthos(raw.get('position', 3), tuple(raw.get('events', ())))


def apply_choice(flags: SceneFlags, event_id: str, direction: str) -> SceneFlags:
    state = shift(read(flags), event_id, direction)
    return set_scene_flag(flags, KEY, json.dumps(dict(position=state.position, events=state.events)))
