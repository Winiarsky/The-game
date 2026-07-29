from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import ExplorationSpellCastingFlowService
from dnd_board_game.combat import SpellSlotState, scene_flag
from dnd_board_game.exploration import ExplorationState, PartyPosition
from dnd_board_game.inventory import InventoryItem, SpellcastingFocusKind
from dnd_board_game.rules import (
    SpellAccessKind,
    SpellAccessProfile,
    SpellCastingTime,
    SpellComponents,
    SpellDefinition,
    SpellDuration,
    SpellDurationKind,
    SpellExplorationEffect,
    SpellExplorationEffectKind,
    SpellRange,
    SpellRangeKind,
    SpellSchool,
)
from dnd_board_game.scenarios.loader import _parse_spell_definition
from dnd_board_game.world import Coordinate
import json
from pathlib import Path


def test_animal_friendship_cast_records_target_and_24_hour_marker() -> None:
    spell = SpellDefinition(
        id="animal_friendship",
        name="Animal Friendship",
        level=1,
        school=SpellSchool.ENCHANTMENT,
        casting_time=SpellCastingTime.ACTION,
        range=SpellRange(SpellRangeKind.DISTANCE, 30),
        components=SpellComponents(verbal=True),
        duration=SpellDuration(SpellDurationKind.TWENTY_FOUR_HOURS),
        effect_kind="exploration",
        exploration_effect=SpellExplorationEffect(
            SpellExplorationEffectKind.SET_FLAG,
            "cast_animal_friendship",
        ),
    )
    hero = Actor(
        id=ActorId("druid"),
        name="Druid",
        ac=12,
        hp=10,
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
        spell_slots=(SpellSlotState(1, 1, 1),),
    )
    state = ExplorationState((), (), PartyPosition("yard"), elapsed_minutes=7)

    result = ExplorationSpellCastingFlowService().cast(
        actors=(hero,),
        state=state,
        actor_id="druid",
        spell_id="animal_friendship",
        target_id="guard_dog",
    )

    assert result.actor_after.spell_slots[0].remaining == 0
    assert scene_flag(result.state.flags, "cast_animal_friendship") == "guard_dog"
    assert result.timed_effect is not None
    assert result.timed_effect.expires_at_minute == 7 + 24 * 60


def test_gentle_repose_targets_corpse_for_ten_days_without_concentration() -> None:
    data = json.loads(
        Path("content/spells/gentle_repose.json").read_text(encoding="utf-8")
    )
    spell = _parse_spell_definition(data, "gentle_repose")
    cleric = Actor(
        id=ActorId("cleric"),
        name="Kleryk",
        ac=16,
        hp=18,
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
                allowed_focus_kinds=("holy_symbol",),
            ),
        ),
        inventory=(
            InventoryItem(
                id="holy_symbol",
                name="Święty symbol",
                kind="focus",
                spellcasting_focus_kind=SpellcastingFocusKind.HOLY_SYMBOL,
            ),
        ),
        spell_slots=(SpellSlotState(2, 1, 1),),
    )
    state = ExplorationState(
        (),
        (),
        PartyPosition("exploration_course"),
        elapsed_minutes=30,
    )

    result = ExplorationSpellCastingFlowService().cast(
        actors=(cleric,),
        state=state,
        actor_id="cleric",
        spell_id="gentle_repose",
        target_id="training_corpse",
    )

    assert spell.concentration is False
    assert result.actor_after.spell_slots[0].remaining == 0
    assert scene_flag(result.state.flags, "cast_gentle_repose") == "training_corpse"
    assert result.timed_effect is not None
    assert result.timed_effect.expires_at_minute == 30 + 10 * 24 * 60


def test_pass_without_trace_can_start_before_encounter_and_lasts_one_hour() -> None:
    data = json.loads(
        Path("content/spells/pass_without_trace.json").read_text(encoding="utf-8")
    )
    spell = _parse_spell_definition(data, "pass_without_trace")
    druid = Actor(
        id=ActorId("druid"),
        name="Druid",
        ac=14,
        hp=18,
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
                name="Ognisko druida",
                kind="focus",
                spellcasting_focus_kind=SpellcastingFocusKind.DRUIDIC,
            ),
        ),
        spell_slots=(SpellSlotState(2, 1, 1),),
    )
    state = ExplorationState(
        (),
        (),
        PartyPosition("exploration_course"),
        elapsed_minutes=12,
    )

    result = ExplorationSpellCastingFlowService().cast(
        actors=(druid,),
        state=state,
        actor_id="druid",
        spell_id="pass_without_trace",
    )

    assert spell.concentration is True
    assert result.actor_after.spell_slots[0].remaining == 0
    assert result.timed_effect is not None
    assert result.timed_effect.expires_at_minute == 72
