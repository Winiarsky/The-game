from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import ExplorationSpellCastingFlowService
from dnd_board_game.combat import SpellSlotState, scene_flag
from dnd_board_game.exploration import ExplorationState, PartyPosition
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
from dnd_board_game.world import Coordinate


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
