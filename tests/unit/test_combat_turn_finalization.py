from dataclasses import replace

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    ActorResourcePool,
    Faction,
    RecoveryPeriod,
    ResourceRechargeRule,
)
from dnd_board_game.application import CombatTurnFinalizationService
from dnd_board_game.combat import (
    ActiveCombatEffect,
    CombatState,
    CombatStatus,
    EnemyAutoTurnResult,
    MirrorImageOutcome,
    InitiativeEntry,
    InitiativeOrder,
    actor_as_combat_target,
    current_actor,
    start_combat,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, EffectDuration, resolve_d20_roll
from dnd_board_game.world import Coordinate


def _actor(actor_id: str, faction: Faction, *, hp: int = 10) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=hp,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0 if faction == Faction.ENEMY else 1, 0),
        faction=faction,
        ability_scores=AbilityScores(dexterity=14),
    )


def _state(*actors: Actor) -> CombatState:
    order = InitiativeOrder(
        tuple(
            InitiativeEntry(
                actor,
                resolve_d20_roll(D20RollInput(D20RollRequest(), 20 - index)),
                2,
                index,
            )
            for index, actor in enumerate(actors)
        )
    )
    return start_combat(tuple(actors), order)


def _effect(
    effect_id: str,
    actor_id: str,
    kind: str,
    label: str,
    *,
    target_actor_id: str | None = None,
    duration: EffectDuration | None = None,
) -> ActiveCombatEffect:
    return ActiveCombatEffect(
        id=effect_id,
        actor_id=actor_id,
        kind=kind,
        label=label,
        object_id=f"test:{effect_id}",
        value=0,
        target_actor_id=target_actor_id,
        duration=duration,
    )


def test_turn_start_rolls_and_applies_recharge_before_turn_triggers() -> None:
    hero = _actor("hero", Faction.ALLY)
    enemy = replace(
        _actor("enemy", Faction.ENEMY),
        resource_pools=(
            ActorResourcePool(
                "special",
                "Atak specjalny",
                0,
                1,
                RecoveryPeriod.NEVER,
                ResourceRechargeRule(6, 5),
            ),
        ),
    )

    transition = CombatTurnFinalizationService().finish_active_turn(
        state=_state(hero, enemy),
        active_effects=(),
        roll_recharge=lambda _die: 6,
    )

    assert transition is not None
    current = current_actor(transition.state)
    assert current.id == enemy.id
    assert current.resource_pools[0].current == 1
    assert transition.recharge_results[0].natural_roll == 6
    assert transition.recharge_results[0].recharged is True


def test_commit_enemy_result_consumes_only_effects_for_the_resolved_attack() -> None:
    service = CombatTurnFinalizationService()
    enemy = _actor("enemy", Faction.ENEMY)
    hero = _actor("hero", Faction.ALLY)
    state = _state(enemy, hero)
    result = EnemyAutoTurnResult(
        state=state,
        enemy=enemy,
        target=actor_as_combat_target(hero),
        message="Enemy atakuje Hero.",
        attack_roll=resolve_d20_roll(D20RollInput(D20RollRequest(), 14)),
        action_used=True,
    )
    penalty = _effect("penalty", "enemy", "grant_next_attack_penalty", "Kara")
    help_effect = _effect(
        "help",
        "enemy",
        "help_attack_advantage",
        "Help",
        target_actor_id="hero",
    )
    dodge = _effect("dodge", "hero", "dodge_until_next_turn", "Dodge")

    transition = service.commit_enemy_result(
        result=result,
        active_effects=(penalty, help_effect, dodge),
    )

    assert transition.state is state
    assert transition.active_effects == (dodge,)
    assert transition.event_type == "ui_combat_enemy_turn_board_confirmed"
    assert dict(transition.event_payload) == {
        "enemy_id": "enemy",
        "target_id": "hero",
        "message": "Enemy atakuje Hero. Rzut d20: 14. wynik końcowy: 14.",
        "source_id": None,
        "resource_pool_id": None,
        "resource_cost": 0,
    }


def test_commit_enemy_result_removes_destroyed_mirror_duplicate() -> None:
    service = CombatTurnFinalizationService()
    enemy = _actor("enemy", Faction.ENEMY)
    hero = _actor("hero", Faction.ALLY)
    state = _state(enemy, hero)
    mirror = replace(
        _effect(
            "mirror",
            "hero",
            "mirror_image",
            "Lustrzane odbicia",
            duration=EffectDuration.UNTIL_ENCOUNTER_END,
        ),
        value=3,
    )
    result = EnemyAutoTurnResult(
        state=state,
        enemy=enemy,
        target=actor_as_combat_target(hero),
        message="Atak trafia duplikat.",
        attack_roll=resolve_d20_roll(D20RollInput(D20RollRequest(), 14)),
        action_used=True,
        mirror_image_outcome=MirrorImageOutcome(
            effect_id="mirror",
            redirect_roll=15,
            redirect_threshold=6,
            redirected=True,
            duplicate_ac=12,
            duplicate_hit=True,
            duplicates_before=3,
            duplicates_after=2,
        ),
    )

    transition = service.commit_enemy_result(
        result=result,
        active_effects=(mirror,),
    )

    assert len(transition.active_effects) == 1
    assert transition.active_effects[0].value == 2


def test_finalize_enemy_turn_expires_end_and_next_turn_start_effects() -> None:
    service = CombatTurnFinalizationService()
    enemy = _actor("enemy", Faction.ENEMY)
    hero = _actor("hero", Faction.ALLY)
    state = _state(enemy, hero)
    disengage = _effect("disengage", "enemy", "disengage_until_turn_end", "Disengage")
    dodge = _effect("dodge", "hero", "dodge_until_next_turn", "Dodge")
    persistent = _effect("persistent", "enemy", "grant_ac_bonus_until_move", "Osłona")
    result = EnemyAutoTurnResult(
        state=state,
        enemy=enemy,
        target=None,
        message="Enemy kończy akcję.",
        action_used=True,
    )

    transition = service.finalize_enemy_turn(
        result=result,
        active_effects=(disengage, dodge, persistent),
    )

    assert current_actor(transition.state).id == hero.id
    assert transition.active_effects == (persistent,)
    assert [notice.message_prefix for notice in transition.expired_effects] == [
        "Wygasły efekty końca tury: Enemy",
        "Wygasły efekty początku tury: Hero",
    ]
    assert [notice.effects for notice in transition.expired_effects] == [
        (disengage,),
        (dodge,),
    ]
    assert transition.message_title == "Tura przeciwnika"
    assert dict(transition.event_payload)["action_used"] is True


def test_finish_active_turn_advances_state_and_preserves_observation_contract() -> None:
    service = CombatTurnFinalizationService()
    hero = _actor("hero", Faction.ALLY)
    enemy = _actor("enemy", Faction.ENEMY)
    state = _state(hero, enemy)
    disengage = _effect("disengage", "hero", "disengage_until_turn_end", "Disengage")

    transition = service.finish_active_turn(
        state=state,
        active_effects=(disengage,),
    )

    assert transition is not None
    assert current_actor(transition.state).id == enemy.id
    assert transition.active_effects == ()
    assert transition.message_body == "Zakończono turę: Hero."
    assert transition.event_type == "ui_combat_turn_finished"
    assert dict(transition.event_payload) == {"actor_id": "hero"}


def test_finish_last_turn_of_round_expires_round_bound_effects() -> None:
    service = CombatTurnFinalizationService()
    hero = _actor("hero", Faction.ALLY)
    enemy = _actor("enemy", Faction.ENEMY)
    initial = _state(hero, enemy)
    state = replace(
        initial,
        initiative_order=replace(initial.initiative_order, current_index=1),
    )
    effect = _effect(
        "round-effect",
        "hero",
        "round_bonus",
        "Premia rundy",
        duration=EffectDuration.UNTIL_ROUND_END,
    )

    transition = service.finish_active_turn(state=state, active_effects=(effect,))

    assert transition is not None
    assert transition.state.round_number == 2
    assert transition.active_effects == ()
    assert transition.expired_effects[0].effects == (effect,)
    assert transition.expired_effects[0].message_prefix == "Wygasły efekty końca rundy 1"


def test_finalize_enemy_turn_does_not_expire_turn_start_effects_after_combat_ends() -> None:
    service = CombatTurnFinalizationService()
    enemy = _actor("enemy", Faction.ENEMY)
    defeated_hero = _actor("hero", Faction.ALLY, hp=0)
    state = _state(enemy, defeated_hero)
    disengage = _effect("disengage", "enemy", "disengage_until_turn_end", "Disengage")
    dodge = _effect("dodge", "hero", "dodge_until_next_turn", "Dodge")
    result = EnemyAutoTurnResult(
        state=state,
        enemy=enemy,
        target=None,
        message="Enemy kończy walkę.",
    )

    transition = service.finalize_enemy_turn(
        result=result,
        active_effects=(disengage, dodge),
    )

    assert transition.state.status == CombatStatus.FINISHED
    assert transition.active_effects == (dodge,)
    assert len(transition.expired_effects) == 1
    assert transition.expired_effects[0].effects == (disengage,)


def test_finish_active_turn_is_a_noop_for_inactive_combat() -> None:
    service = CombatTurnFinalizationService()
    hero = _actor("hero", Faction.ALLY)
    enemy = _actor("enemy", Faction.ENEMY)
    state = replace(_state(hero, enemy), status=CombatStatus.STOPPED)

    transition = service.finish_active_turn(state=state, active_effects=())

    assert transition is None
