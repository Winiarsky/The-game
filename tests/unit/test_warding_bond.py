from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.combat import (
    ActiveCombatEffect,
    CombatState,
    DamageComponentInput,
    DamageType,
    InitiativeEntry,
    InitiativeOrder,
    apply_damage_result,
    resolve_actor_saving_throw,
    resolve_damage,
    start_combat,
    transfer_warding_bond_damage,
)
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    EffectDuration,
    SavingThrowRequest,
    resolve_d20_roll,
)
from dnd_board_game.world import Coordinate


def _actor(actor_id: str, position: Coordinate, hp: int = 20) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=hp,
        max_hp=hp,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=Faction.ALLY,
        ability_scores=AbilityScores(),
    )


def _state(*actors: Actor) -> CombatState:
    order = InitiativeOrder(
        tuple(
            InitiativeEntry(
                actor,
                resolve_d20_roll(D20RollInput(D20RollRequest(), 20 - index)),
                0,
                index,
            )
            for index, actor in enumerate(actors)
        )
    )
    return start_combat(actors, order)


def _effect() -> ActiveCombatEffect:
    return ActiveCombatEffect(
        id="warding-bond:cleric:ally",
        actor_id="ally",
        kind="warding_bond",
        label="Więź ochronna",
        object_id="combat_action:warding_bond",
        value=1,
        source_actor_id="cleric",
        target_actor_id="ally",
        duration=EffectDuration.UNTIL_SHORT_REST,
    )


def test_warding_bond_grants_save_bonus_resistance_and_linked_damage() -> None:
    cleric = _actor("cleric", Coordinate(0, 0))
    ally = _actor("ally", Coordinate(1, 0))
    actors = (cleric, ally)
    effect = _effect()

    saving_throw = resolve_actor_saving_throw(
        ally,
        SavingThrowRequest(
            ability="dexterity",
            dc=11,
            source_label="Pułapka",
        ),
        natural_roll=10,
        active_effects=(effect,),
        combat_actors=actors,
    )
    protected = apply_damage_result(
        ally,
        resolve_damage((DamageComponentInput(9, DamageType.FIRE),)),
        active_effects=(effect,),
        combat_actors=actors,
    )
    state_after_target = _state(cleric, protected.actor_after)
    transferred = transfer_warding_bond_damage(
        state_after_target,
        protected_actor=ally,
        damage_amount=protected.damage.total_applied,
        active_effects=(effect,),
    )
    cleric_after = next(
        actor
        for actor in transferred.state.actors
        if str(actor.id) == "cleric"
    )

    assert saving_throw.total == 11
    assert saving_throw.success is True
    assert protected.damage.total_applied == 4
    assert protected.hp_after == 16
    assert transferred.source_damage is not None
    assert transferred.source_damage.damage.total_applied == 4
    assert cleric_after.hp == 16


def test_warding_bond_is_inactive_beyond_sixty_feet() -> None:
    cleric = _actor("cleric", Coordinate(0, 0))
    ally = _actor("ally", Coordinate(13, 0))

    applied = apply_damage_result(
        ally,
        resolve_damage((DamageComponentInput(9, DamageType.FIRE),)),
        active_effects=(_effect(),),
        combat_actors=(cleric, ally),
    )

    assert applied.damage.total_applied == 9
