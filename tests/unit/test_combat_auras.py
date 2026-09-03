from dataclasses import replace
from random import Random

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorAura,
    ActorId,
    AuraEffectKind,
    AuraTarget,
    Faction,
)
from dnd_board_game.combat import (
    active_auras,
    active_spell_auras,
    resolve_actor_saving_throw,
    resolve_healing_grace_bonus,
    synchronize_spell_aura_effects,
)
from dnd_board_game.rules import ActiveEffect, EffectDuration, SavingThrowRequest
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


def test_exhaustion_level_three_gives_saving_throw_disadvantage() -> None:
    actor = replace(_actor("target", Coordinate(0, 0)), exhaustion_level=3)

    result = resolve_actor_saving_throw(
        actor,
        SavingThrowRequest(ability="dexterity", dc=10, source_label="Test"),
        natural_roll=18,
        natural_roll_2=4,
    )

    assert result.natural_roll == 4
    assert "Exhaustion" in {modifier.label for modifier in result.modifiers}


def _spell_aura(
    kind: str,
    *,
    radius_feet: int,
    value: int,
    die_sides: int = 0,
    modifier: int = 0,
    uses_maximum: int = 0,
) -> ActiveEffect:
    return ActiveEffect(
        id=f"{kind}:dagna",
        actor_id="dagna",
        source_actor_id="dagna",
        kind=kind,
        label=kind,
        object_id=f"spell:{kind}",
        value=value,
        duration=EffectDuration.CONCENTRATION,
        radius_feet=radius_feet,
        die_sides=die_sides,
        modifier=modifier,
        uses_maximum=uses_maximum,
        remaining_rounds=3,
    )


def test_spell_aura_statuses_follow_movement_and_faction() -> None:
    dagna = _actor("dagna", Coordinate(0, 0))
    ally = _actor("ally", Coordinate(2, 0))
    far_ally = _actor("far", Coordinate(3, 0))
    enemy = _actor("enemy", Coordinate(1, 0), Faction.ENEMY)
    bless = _spell_aura(
        "bless_aura_source",
        radius_feet=10,
        value=4,
        die_sides=4,
    )

    synchronized = synchronize_spell_aura_effects(
        (dagna, ally, far_ally, enemy),
        (bless,),
    )

    members = {
        effect.actor_id
        for effect in synchronized
        if effect.kind == "bless_roll_bonus"
    }
    assert members == {"dagna", "ally"}

    moved = synchronize_spell_aura_effects(
        (dagna, replace(ally, position=Coordinate(3, 0)), far_ally, enemy),
        synchronized,
    )
    assert {
        effect.actor_id for effect in moved if effect.kind == "bless_roll_bonus"
    } == {"dagna"}
    assert active_spell_auras((replace(dagna, hp=0), ally), (bless,)) == ()


def test_divine_care_marks_only_nearby_living_enemies_with_negative_value() -> None:
    dagna = _actor("dagna", Coordinate(0, 0))
    ally = _actor("ally", Coordinate(1, 0))
    enemy = _actor("enemy", Coordinate(1, 0), Faction.ENEMY)
    far_enemy = _actor("far_enemy", Coordinate(2, 0), Faction.ENEMY)
    aura = _spell_aura(
        "divine_care_aura_source",
        radius_feet=5,
        value=2,
    )

    effects = synchronize_spell_aura_effects(
        (dagna, ally, enemy, far_enemy),
        (aura,),
    )

    penalties = [
        effect for effect in effects if effect.kind == "divine_care_aura_penalty"
    ]
    assert [(effect.actor_id, effect.value) for effect in penalties] == [
        ("enemy", -2)
    ]


def test_healing_grace_spends_one_activation_and_expires_after_last_use() -> None:
    dagna = _actor("dagna", Coordinate(0, 0))
    ally = replace(_actor("ally", Coordinate(2, 0)), hp=1)
    aura = _spell_aura(
        "healing_grace_aura_source",
        radius_feet=10,
        value=2,
        die_sides=8,
        modifier=4,
        uses_maximum=2,
    )
    rng = Random(7)

    first = resolve_healing_grace_bonus((dagna, ally), (aura,), ally, rng=rng)
    assert first.bonus == first.die_roll + 4
    assert 1 <= first.die_roll <= 8
    remaining_source = next(
        effect
        for effect in first.active_effects
        if effect.kind == "healing_grace_aura_source"
    )
    assert remaining_source.value == 1

    second = resolve_healing_grace_bonus(
        (dagna, ally), first.active_effects, ally, rng=rng
    )
    assert second.bonus == second.die_roll + 4
    assert not any(
        effect.kind == "healing_grace_aura_source"
        for effect in second.active_effects
    )
    exhausted = resolve_healing_grace_bonus(
        (dagna, ally), second.active_effects, ally, rng=rng
    )
    assert exhausted.bonus == 0
