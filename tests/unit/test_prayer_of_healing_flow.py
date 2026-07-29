import json
from pathlib import Path

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import ExplorationSpellCastingFlowService
from dnd_board_game.combat import SpellSlotState
from dnd_board_game.exploration import ExplorationState, PartyPosition
from dnd_board_game.rules import SpellAccessKind, SpellAccessProfile
from dnd_board_game.scenarios.loader import _parse_spell_definition
from dnd_board_game.world import Coordinate


def _actor(
    actor_id: str,
    *,
    position: Coordinate,
    creature_type: str = "humanoid",
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=1,
        max_hp=30,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=Faction.ALLY,
        ability_scores=AbilityScores(wisdom=10),
        creature_type=creature_type,
    )


def _cleric() -> Actor:
    spell = _parse_spell_definition(
        json.loads(
            Path("content/spells/prayer_of_healing.json").read_text(
                encoding="utf-8"
            )
        ),
        "prayer_of_healing",
    )
    return Actor(
        id=ActorId("cleric"),
        name="Kleryk",
        ac=16,
        hp=1,
        max_hp=30,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        ability_scores=AbilityScores(wisdom=16),
        spells=(spell,),
        spell_access=(
            SpellAccessProfile(
                SpellAccessKind.KNOWN,
                (spell.id,),
                casting_ability="wisdom",
            ),
        ),
        spell_slots=(SpellSlotState(3, 1, 1),),
    )


def test_prayer_of_healing_heals_up_to_six_legal_targets_after_ten_minutes() -> None:
    actors = (
        _cleric(),
        *(
            _actor(f"ally_{index}", position=Coordinate(index, 0))
            for index in range(1, 6)
        ),
        _actor(
            "undead_ally",
            position=Coordinate(1, 1),
            creature_type="undead",
        ),
        _actor("far_ally", position=Coordinate(7, 0)),
    )
    state = ExplorationState(
        (),
        (),
        PartyPosition("spell_lab"),
        elapsed_minutes=5,
    )

    result = ExplorationSpellCastingFlowService().cast(
        actors=actors,
        state=state,
        actor_id="cleric",
        spell_id="prayer_of_healing",
        cast_level=3,
        healing_roll=12,
    )

    assert result.elapsed_minutes == 10
    assert result.state.elapsed_minutes == 15
    assert result.actor_after.spell_slots[0].remaining == 0
    assert len(result.healing_results) == 6
    assert {str(item.actor_before.id) for item in result.healing_results} == {
        "cleric",
        "ally_1",
        "ally_2",
        "ally_3",
        "ally_4",
        "ally_5",
    }
    assert all(item.amount == 15 for item in result.healing_results)
    assert next(actor for actor in result.actors if str(actor.id) == "undead_ally").hp == 1
    assert next(actor for actor in result.actors if str(actor.id) == "far_ally").hp == 1


def test_prayer_of_healing_rejects_illegal_explicit_target_without_spending_slot() -> None:
    cleric = _cleric()
    actors = (cleric, _actor("far_ally", position=Coordinate(7, 0)))

    with pytest.raises(ValueError, match="Nielegalne cele"):
        ExplorationSpellCastingFlowService().cast(
            actors=actors,
            state=ExplorationState((), (), PartyPosition("spell_lab")),
            actor_id="cleric",
            spell_id="prayer_of_healing",
            cast_level=3,
            target_ids=("far_ally",),
            healing_roll=12,
        )

    assert cleric.spell_slots[0].remaining == 1
