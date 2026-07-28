from dataclasses import replace

from dnd_board_game.actors import (
    Actor,
    ActorId,
    ActorSenseProfile,
    Faction,
)
from dnd_board_game.exploration import LightLevel, exploration_visibility
from dnd_board_game.inventory import ActiveLight, LightShape
from dnd_board_game.rules import RollMode
from dnd_board_game.world import Coordinate


def _actor(
    actor_id: str = "observer",
    *,
    senses: ActorSenseProfile = ActorSenseProfile(),
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=10,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        senses=senses,
    )


def test_dim_light_disadvantages_sight_perception_and_reduces_passive() -> None:
    result = exploration_visibility(
        _actor(),
        ambient_light=LightLevel.DIM,
        distance_feet=20,
    )

    assert result.can_see is True
    assert result.perceived_light == LightLevel.DIM
    assert result.perception_roll_mode == RollMode.DISADVANTAGE
    assert result.passive_perception_adjustment == -5


def test_darkness_blocks_normal_vision() -> None:
    result = exploration_visibility(
        _actor(),
        ambient_light=LightLevel.DARKNESS,
        distance_feet=10,
    )

    assert result.can_see is False
    assert result.perceived_light == LightLevel.DARKNESS


def test_darkvision_treats_darkness_as_dim_light_within_range() -> None:
    observer = _actor(
        senses=ActorSenseProfile(darkvision_feet=60),
    )

    near = exploration_visibility(
        observer,
        ambient_light=LightLevel.DARKNESS,
        distance_feet=60,
    )
    far = exploration_visibility(
        observer,
        ambient_light=LightLevel.DARKNESS,
        distance_feet=65,
    )

    assert near.can_see is True
    assert near.sense_used == "darkvision"
    assert near.perception_roll_mode == RollMode.DISADVANTAGE
    assert far.can_see is False


def test_party_torch_illuminates_abstract_observation_distance() -> None:
    bearer = replace(
        _actor("bearer"),
        active_light=ActiveLight(
            source_item_id="torch",
            source_name="Pochodnia",
            bright_distance_feet=20,
            dim_additional_feet=20,
            remaining_minutes=60,
            shape=LightShape.RADIUS,
        ),
    )

    bright = exploration_visibility(
        _actor(),
        ambient_light=LightLevel.DARKNESS,
        distance_feet=20,
        party=(bearer,),
    )
    dim = exploration_visibility(
        _actor(),
        ambient_light=LightLevel.DARKNESS,
        distance_feet=40,
        party=(bearer,),
    )
    beyond = exploration_visibility(
        _actor(),
        ambient_light=LightLevel.DARKNESS,
        distance_feet=45,
        party=(bearer,),
    )

    assert bright.perceived_light == LightLevel.BRIGHT
    assert bright.light_source_actor_id == "bearer"
    assert dim.perceived_light == LightLevel.DIM
    assert beyond.can_see is False


def test_blindsight_bypasses_light_within_its_range() -> None:
    result = exploration_visibility(
        _actor(senses=ActorSenseProfile(blindsight_feet=10)),
        ambient_light=LightLevel.DARKNESS,
        distance_feet=10,
    )

    assert result.can_see is True
    assert result.sense_used == "blindsight"
    assert result.perception_roll_mode == RollMode.NORMAL


def test_magical_darkness_blocks_darkvision_but_not_devils_sight() -> None:
    ordinary = _actor(senses=ActorSenseProfile(darkvision_feet=120))
    devil = _actor(
        senses=ActorSenseProfile(
            darkvision_feet=120,
            magical_darkness_vision_feet=120,
        )
    )

    blocked = exploration_visibility(
        ordinary,
        ambient_light=LightLevel.BRIGHT,
        distance_feet=30,
        magical_darkness=True,
    )
    visible = exploration_visibility(
        devil,
        ambient_light=LightLevel.BRIGHT,
        distance_feet=30,
        magical_darkness=True,
    )

    assert blocked.can_see is False
    assert visible.can_see is True
    assert visible.sense_used == "devils_sight"
