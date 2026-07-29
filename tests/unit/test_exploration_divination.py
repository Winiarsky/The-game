import json
from pathlib import Path

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import (
    ExplorationSpellCastingFlowService,
    RitualCastingFlowService,
)
from dnd_board_game.combat import SpellSlotState
from dnd_board_game.combat import scene_flag
from dnd_board_game.exploration import (
    DivinationTargetKind,
    ExplorationPoint,
    ExplorationState,
    PartyPosition,
    locate_authored_target,
)
from dnd_board_game.rules import SpellAccessKind, SpellAccessProfile
from dnd_board_game.inventory import InventoryItem, SpellcastingFocusKind
from dnd_board_game.scenarios.loader import _parse_spell_definition
from dnd_board_game.world import Coordinate


def test_locate_animals_or_plants_returns_nearest_matching_authored_species() -> None:
    points = (
        ExplorationPoint(
            "far_hound",
            "Daleki ogar",
            "course",
            (Coordinate(8, 8),),
            (1, 2, 3),
            divination_kind="animal",
            divination_tags=("ogar", "pies"),
        ),
        ExplorationPoint(
            "near_hound",
            "Bliski ogar",
            "course",
            (Coordinate(3, 1),),
            (1, 2, 3),
            divination_kind="animal",
            divination_tags=("ogar",),
        ),
        ExplorationPoint(
            "ivy",
            "Bluszcz",
            "course",
            (Coordinate(1, 1),),
            (1, 2, 3),
            divination_kind="plant",
            divination_tags=("bluszcz",),
        ),
    )

    result = locate_authored_target(
        points,
        query="  OGAR ",
        allowed_kinds=frozenset(
            {DivinationTargetKind.ANIMAL, DivinationTargetKind.PLANT}
        ),
        origin=Coordinate(0, 1),
        maximum_distance_feet=5 * 5280,
    )

    assert result is not None
    assert result.point_id == "near_hound"
    assert result.distance_feet == 15
    assert result.direction == "wschód"


def test_locate_animals_or_plants_ritual_records_instantaneous_query_without_slot() -> None:
    spell = _parse_spell_definition(
        json.loads(
            Path("content/spells/locate_animals_or_plants.json").read_text(
                encoding="utf-8"
            )
        ),
        "locate_animals_or_plants",
    )
    druid = Actor(
        id=ActorId("druid"),
        name="Druid",
        ac=12,
        hp=16,
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
                allowed_focus_kinds=("druidic",),
            ),
        ),
        inventory=(
            InventoryItem(
                id="druidic_focus",
                name="Druidyczne ognisko",
                kind="focus",
                spellcasting_focus_kind=SpellcastingFocusKind.DRUIDIC,
            ),
        ),
    )

    result = RitualCastingFlowService().cast(
        actors=(druid,),
        state=ExplorationState((), (), PartyPosition("course")),
        actor_id="druid",
        spell_id=spell.id,
        target_id="ogar",
    )

    assert result.elapsed_minutes == 10
    assert scene_flag(result.state.flags, "cast_locate_animals_or_plants") == "ogar"


def test_locate_object_ignores_lead_shielding_and_keeps_query_for_concentration() -> None:
    points = (
        ExplorationPoint(
            "shielded",
            "Bliski kompas",
            "course",
            (Coordinate(1, 0),),
            (1, 2, 3),
            divination_kind="object",
            divination_tags=("kompas",),
            divination_lead_shielded=True,
        ),
        ExplorationPoint(
            "open",
            "Daleki kompas",
            "course",
            (Coordinate(5, 0),),
            (1, 2, 3),
            divination_kind="object",
            divination_tags=("kompas",),
        ),
    )
    located = locate_authored_target(
        points,
        query="kompas",
        allowed_kinds=frozenset({DivinationTargetKind.OBJECT}),
        origin=Coordinate(0, 0),
        maximum_distance_feet=1000,
        blocked_by_lead=True,
    )
    assert located is not None
    assert located.point_id == "open"
    assert located.distance_feet == 25

    spell = _parse_spell_definition(
        json.loads(
            Path("content/spells/locate_object.json").read_text(encoding="utf-8")
        ),
        "locate_object",
    )
    wizard = Actor(
        id=ActorId("wizard"),
        name="Czarodziej",
        ac=12,
        hp=12,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        ability_scores=AbilityScores(intelligence=16),
        spells=(spell,),
        spell_access=(
            SpellAccessProfile(
                SpellAccessKind.KNOWN,
                (spell.id,),
                casting_ability="intelligence",
                allowed_focus_kinds=("arcane",),
            ),
        ),
        inventory=(
            InventoryItem(
                id="arcane_focus",
                name="Ognisko mistyczne",
                kind="focus",
                spellcasting_focus_kind=SpellcastingFocusKind.ARCANE,
            ),
        ),
        spell_slots=(SpellSlotState(2, 1, 1),),
    )
    cast = ExplorationSpellCastingFlowService().cast(
        actors=(wizard,),
        state=ExplorationState((), points, PartyPosition("course")),
        actor_id="wizard",
        spell_id=spell.id,
        target_id="kompas",
    )

    assert cast.timed_effect is not None
    assert cast.timed_effect.flag_value == "kompas"
    assert cast.timed_effect.expires_at_minute == 10
