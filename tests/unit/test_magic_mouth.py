import json
from pathlib import Path

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import RitualCastingFlowService
from dnd_board_game.exploration import (
    ExplorationState,
    MagicMouthSpecification,
    PartyPosition,
    decode_magic_mouth,
    encode_magic_mouth,
    magic_mouth_message_for_event,
)
from dnd_board_game.inventory import InventoryItem
from dnd_board_game.rules import SpellAccessKind, SpellAccessProfile
from dnd_board_game.scenarios.loader import _parse_spell_definition
from dnd_board_game.world import Coordinate


def test_magic_mouth_persists_object_message_and_repeatable_interaction_trigger() -> None:
    specification = MagicMouthSpecification(
        object_id="training_statue",
        message="Nie dotykaj nosa posągu.",
        trigger_description="Ktoś dotyka posągu",
    )
    restored = decode_magic_mouth(encode_magic_mouth(specification))

    assert restored == specification
    assert (
        magic_mouth_message_for_event(
            restored,
            object_id="training_statue",
            event="interaction",
        )
        == "Nie dotykaj nosa posągu."
    )
    assert (
        magic_mouth_message_for_event(
            restored,
            object_id="another_object",
            event="interaction",
        )
        is None
    )


def test_magic_mouth_rejects_message_longer_than_twenty_five_words() -> None:
    with pytest.raises(ValueError, match="25"):
        MagicMouthSpecification(
            object_id="statue",
            message=" ".join(f"słowo{index}" for index in range(26)),
            trigger_description="Ktoś podchodzi",
        )


def test_magic_mouth_ritual_consumes_costly_component_and_has_no_expiry() -> None:
    spell = _parse_spell_definition(
        json.loads(
            Path("content/spells/magic_mouth.json").read_text(encoding="utf-8")
        ),
        "magic_mouth",
    )
    encoded = encode_magic_mouth(
        MagicMouthSpecification(
            object_id="training_statue",
            message="Próba zakończona.",
            trigger_description="Ktoś dotyka posągu",
        )
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
            ),
        ),
        inventory=(
            InventoryItem(
                id="spell_component_magic_mouth",
                name="Plaster miodu i jadeitowy pył",
                kind="component",
                value_cp=1000,
            ),
        ),
    )

    result = RitualCastingFlowService().cast(
        actors=(wizard,),
        state=ExplorationState((), (), PartyPosition("course")),
        actor_id="wizard",
        spell_id=spell.id,
        target_id=encoded,
    )

    assert result.elapsed_minutes == 11
    assert result.state.magic_effects[0].expires_at_minute is None
    assert decode_magic_mouth(str(result.state.magic_effects[0].flag_value)).object_id == (
        "training_statue"
    )
    assert not result.actor_after.inventory
