"""Build the live one-round rules state from actors and authored scene data."""
from __future__ import annotations

from typing import Any, Mapping

from dnd_board_game.actors import Actor
from dnd_board_game.core.player_labels_pl import ABILITY_LABELS_PL
from dnd_board_game.inventory.magic_items import effective_ability_modifier
from dnd_board_game.rules import progress_confrontation as rules

ENGINE = "progress_v1"


def build(actors: tuple[Actor, ...], scene: Mapping[str, Any]) -> rules.Confrontation:
    adjustment = scene.get("progress_dc_adjustment", 0)
    participants = tuple(rules.Participant(str(actor.id), actor.name, tuple(
        rules.Approach(option["id"], option["name"], option["description"], ABILITY_LABELS_PL[option["ability"]],
                       effective_ability_modifier(actor, option["ability"]),
                       option.get("progress_dc", scene.get("progress_dc", 14)) + adjustment,
                       option.get("repeatable", False))
        for option in scene["approaches"])) for actor in actors)
    return rules.Confrontation(participants, social=scene["kind"] == "npc",
                              first_test_bonus=scene.get("first_test_bonus", 0),
                              first_test_label=scene.get("first_test_label", ""))
