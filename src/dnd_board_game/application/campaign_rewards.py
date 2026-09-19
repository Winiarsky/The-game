"""Persistable delayed rewards; future scenario completion calls this once."""
from __future__ import annotations

from dataclasses import replace
import json

from dnd_board_game.actors import Actor
from dnd_board_game.combat.scene import SceneFlags, scene_flag, set_scene_flag
from dnd_board_game.inventory.economy import CurrencyWallet

KEY = 'campaign_delayed_rewards_v1'


def defer_reward(flags: SceneFlags, reward_id: str, after_mission: str, gp: int, narrative_id: str) -> SceneFlags:
    entries = json.loads(str(scene_flag(flags, KEY, '{}')))
    entries.setdefault(reward_id, dict(after_mission=after_mission, gp=gp, narrative_id=narrative_id, paid=False))
    return set_scene_flag(flags, KEY, json.dumps(entries, ensure_ascii=False))


def complete_mission(flags: SceneFlags, actors: tuple[Actor, ...], mission_id: str) -> tuple[SceneFlags, tuple[Actor, ...], tuple[dict, ...]]:
    """Credit the shared treasury and return narration events atomically and idempotently."""
    entries = json.loads(str(scene_flag(flags, KEY, '{}')))
    paid = []
    for key, entry in entries.items():
        if entry['after_mission'] == mission_id and not entry['paid']:
            if not actors: raise ValueError('Nagroda wymaga drużyny.')
            owner = actors[0]
            actors = (replace(owner, currency=owner.currency.add(CurrencyWallet(gp=entry['gp']))), *actors[1:])
            entry['paid'] = True
            paid.append(dict(id=key, **entry))
    return set_scene_flag(flags, KEY, json.dumps(entries, ensure_ascii=False)), actors, tuple(paid)
