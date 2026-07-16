from dataclasses import replace

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorAura,
    ActorId,
    AuraEffectKind,
    AuraTarget,
    Faction,
)
from dnd_board_game.combat import active_auras, resolve_actor_saving_throw
from dnd_board_game.rules import SavingThrowRequest
from dnd_board_game.world import Coordinate


def _actor(
    actor_id: str,
    position: Coordinate,
    faction: Faction = Faction.ALLY,
    *,
    auras: tuple[ActorAura, ...] = (),
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(dexterity=10),
        auras=auras,
    )


def _saving_aura(value: int = 2) -> ActorAura:
    return ActorAura(
        id="protective_presence",
        label="Ochronna obecność",
        radius_feet=10,
        target=AuraTarget.SELF_AND_ALLIES,
        effect_kind=AuraEffectKind.SAVING_THROW_BONUS,
        value=value,
    )


def test_aura_coverage_tracks_positions_faction_and_source_state() -> None:
    source = _actor("source", Coordinate(0, 0), auras=(_saving_aura(),))
    near_ally = _actor("near", Coordinate(2, 0))
    far_ally = _actor("far", Coordinate(3, 0))
    enemy = _actor("enemy", Coordinate(1, 0), Faction.ENEMY)

    coverage = active_auras((source, near_ally, far_ally, enemy))

    assert coverage[0].affected_actor_ids == ("source", "near")
    assert active_auras((replace(source, hp=0), near_ally)) == ()


def test_saving_throw_uses_position_dependent_aura_bonus() -> None:
    source = _actor("source", Coordinate(0, 0), auras=(_saving_aura(),))
    target = _actor("target", Coordinate(2, 0))
    request = SavingThrowRequest(
        ability="dexterity",
        dc=12,
        source_label="Pułapka",
    )

    protected = resolve_actor_saving_throw(
        target,
        request,
        natural_roll=10,
        combat_actors=(source, target),
    )
    unprotected = resolve_actor_saving_throw(
        replace(target, position=Coordinate(3, 0)),
        request,
        natural_roll=10,
        combat_actors=(source, replace(target, position=Coordinate(3, 0))),
    )

    assert protected.total == 12
    assert protected.success is True
    assert [modifier.label for modifier in protected.modifiers] == [
        "Zręczność",
        "Ochronna obecność",
    ]
    assert unprotected.total == 10
    assert unprotected.success is False


def test_same_named_auras_do_not_stack_and_stronger_value_wins() -> None:
    weak = _actor("weak", Coordinate(0, 0), auras=(_saving_aura(1),))
    strong = _actor("strong", Coordinate(1, 0), auras=(_saving_aura(3),))
    target = _actor("target", Coordinate(2, 0))

    result = resolve_actor_saving_throw(
        target,
        SavingThrowRequest(ability="dexterity", dc=20, source_label="Test"),
        natural_roll=10,
        combat_actors=(weak, strong, target),
    )

    assert result.total == 13
    assert [modifier.value for modifier in result.modifiers] == [0, 3]
