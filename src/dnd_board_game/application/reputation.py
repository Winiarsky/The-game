"""Campaign flag boundary for shared reputation; snapshots preserve the ledger."""
from __future__ import annotations

import json

from dnd_board_game.combat.scene import SceneFlags, scene_flag, set_scene_flag
from dnd_board_game.rules.reputation import Reputation, STARTING_REPUTATION, change

KEY = "campaign_reputation_v1"


def read(flags: SceneFlags) -> Reputation:
    data = json.loads(str(scene_flag(flags, KEY, "{}")))
    return Reputation(data.get("points", STARTING_REPUTATION),
                      tuple((entry[0], entry[1]) for entry in data.get("events", ())))


def apply(flags: SceneFlags, event_id: str, amount: int, *, minimum: int = 0) -> SceneFlags:
    state = change(read(flags), event_id, amount, minimum=minimum)
    return set_scene_flag(flags, KEY, json.dumps(dict(points=state.points, events=state.events)))


def initialize(flags: SceneFlags) -> SceneFlags:
    state = read(flags)
    return set_scene_flag(flags, KEY, json.dumps(dict(points=state.points, events=state.events)))
