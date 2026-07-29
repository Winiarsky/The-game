import pytest

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    CreatureSize,
    Faction,
)
from dnd_board_game.combat import (
    ActiveCombatEffect,
    AttackSource,
    AttackSourceType,
    start_attack_action,
)
from dnd_board_game.exploration import (
    RopeTrickSpace,
    TimedMagicEffect,
    decode_rope_trick,
    encode_rope_trick,
    enter_rope_trick,
    exit_rope_trick,
)
from dnd_board_game.rules import D20RollRequest, EffectDuration
from dnd_board_game.world import BoardState, Coordinate


def _actor(
    actor_id: str,
    faction: Faction,
    position: Coordinate,
    *,
    size: CreatureSize = CreatureSize.MEDIUM,
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(),
        size=size,
    )


def _effect() -> TimedMagicEffect:
    return TimedMagicEffect(
        id="rope-space",
        actor_id="wizard",
        spell_id="rope_trick",
        label="Sztuczka z liną",
        flag_key="cast_rope_trick",
        flag_value=encode_rope_trick(RopeTrickSpace("spell_lab", 60)),
        started_at_minute=0,
        expires_at_minute=60,
    )


def test_rope_trick_tracks_entry_exit_and_capacity() -> None:
    effect = _effect()
    occupants = tuple(
        _actor(f"hero_{index}", Faction.ALLY, Coordinate(index, 0))
        for index in range(8)
    )
    for actor in occupants:
        effect = enter_rope_trick(effect, actor)

    space = decode_rope_trick(str(effect.flag_value))
    assert len(space.occupant_actor_ids) == 8
    with pytest.raises(ValueError, match="pełna"):
        enter_rope_trick(
            effect,
            _actor("ninth", Faction.ALLY, Coordinate(0, 1)),
        )

    effect = exit_rope_trick(effect, "hero_3")
    assert "hero_3" not in decode_rope_trick(str(effect.flag_value)).occupant_actor_ids


def test_rope_trick_rejects_large_creatures_and_invalid_rope_length() -> None:
    with pytest.raises(ValueError, match="od 5 do 60"):
        RopeTrickSpace("spell_lab", 65)
    with pytest.raises(ValueError, match="Medium"):
        enter_rope_trick(
            _effect(),
            _actor(
                "ogre",
                Faction.ALLY,
                Coordinate(0, 0),
                size=CreatureSize.LARGE,
            ),
        )


def test_attacks_cannot_cross_rope_trick_entrance() -> None:
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    source = AttackSource(
        "Łuk",
        AttackSourceType.WEAPON,
        60,
        D20RollRequest(),
    )
    space_effect = ActiveCombatEffect(
        id="rope:hero",
        actor_id="hero",
        kind="extradimensional_space",
        label="Sztuczka z liną",
        object_id="spell:rope_trick:space",
        value=0,
        source_actor_id="wizard",
        duration=EffectDuration.UNTIL_ENCOUNTER_END,
    )

    from_inside = start_attack_action(
        BoardState(),
        hero,
        (hero, enemy),
        source,
        active_effects=(space_effect,),
    )
    from_outside = start_attack_action(
        BoardState(),
        enemy,
        (hero, enemy),
        source,
        active_effects=(space_effect,),
    )

    assert from_inside.legal_targets == ()
    assert from_outside.legal_targets == ()
