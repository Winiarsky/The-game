from dataclasses import replace

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import LongRestFlowService, rest_policy_count
from dnd_board_game.exploration import (
    ExplorationState,
    ExplorationZone,
    LongRestPolicy,
    PartyPosition,
    RestSafety,
)
from dnd_board_game.world import Coordinate


def _actor() -> Actor:
    return Actor(
        id=ActorId("hero"),
        name="Hero",
        faction=Faction.ALLY,
        position=Coordinate(0, 0),
        ability_scores=AbilityScores(10, 10, 10, 10, 10, 10),
        max_hp=12,
        hp=3,
        temp_hp=0,
        ac=12,
        speed_feet=30,
    )


def _zone(*, with_rest: bool = True) -> ExplorationZone:
    return ExplorationZone(
        id="inn",
        name="Karczma",
        positions=(Coordinate(0, 0),),
        color=(120, 90, 40),
        long_rest_policy=(
            LongRestPolicy("inn:long", RestSafety.SAFE, max_completions=1)
            if with_rest
            else None
        ),
    )


def test_long_rest_is_content_gated_and_recovers_party() -> None:
    zone = _zone()
    state = ExplorationState((zone,), (), PartyPosition("inn"))

    transition = LongRestFlowService().complete(
        state=state,
        zone=zone,
        actors=(_actor(),),
        encounter_pending=False,
    )

    assert transition.actors[0].hp == 12
    assert transition.state.elapsed_minutes == 480
    assert rest_policy_count(transition.state, "inn:long") == 1


def test_long_rest_rejects_missing_or_exhausted_policy() -> None:
    service = LongRestFlowService()
    state = ExplorationState((_zone(),), (), PartyPosition("inn"))
    try:
        service.complete(
            state=state,
            zone=_zone(with_rest=False),
            actors=(_actor(),),
            encounter_pending=False,
        )
    except ValueError as exc:
        assert "nie ma warunków" in str(exc)
    else:
        raise AssertionError("missing policy should fail")

    exhausted = replace(state, short_rest_counts=(("inn:long", 1),))
    try:
        service.complete(
            state=exhausted,
            zone=_zone(),
            actors=(_actor(),),
            encounter_pending=False,
        )
    except ValueError as exc:
        assert "wykorzystany" in str(exc)
    else:
        raise AssertionError("exhausted policy should fail")
