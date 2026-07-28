from dataclasses import dataclass

import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.application import (
    PlayerMultiTargetSpellFlowService,
    ProjectileAllocation,
)
from dnd_board_game.combat import (
    ActionEconomyCost,
    ActionUse,
    CombatState,
    InitiativeEntry,
    InitiativeOrder,
    SpellSlotState,
    start_combat,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import BoardState, Coordinate


@dataclass(frozen=True)
class _Spell:
    id: str = "magic_missile"
    name: str = "Magic Missile"
    action_type: str = "multi_target_damage"
    spell_level: int = 1
    range_feet: int = 120
    action_cost: ActionEconomyCost = ActionEconomyCost.ACTION
    projectile_count: int = 3
    upcast_projectiles_per_level: int = 1
    damage_die_sides: int = 4
    damage_modifier: int = 1
    damage_type: str = "force"
    resource_pool_id: str | None = None
    resource_cost: int = 1
    cast_flag: str = "cast_magic_missile"


@dataclass(frozen=True)
class _ScorchingRay(_Spell):
    id: str = "scorching_ray"
    name: str = "Scorching Ray"
    spell_level: int = 2
    projectile_count: int = 3
    upcast_projectiles_per_level: int = 1
    damage_die_sides: int = 6
    damage_modifier: int = 0
    damage_type: str = "fire"
    cast_flag: str = "cast_scorching_ray"
    projectile_attack_roll: bool = True
    projectile_damage_dice_count: int = 2


def _actor(
    actor_id: str,
    faction: Faction,
    position: Coordinate,
    *,
    hp: int = 20,
    spell_slots: tuple[SpellSlotState, ...] = (),
    spell_save_dc: int = 14,
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=hp,
        max_hp=hp,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(),
        spell_slots=spell_slots,
        spell_save_dc=spell_save_dc,
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


def test_magic_missile_selects_each_projectile_and_spends_only_on_confirm() -> None:
    service = PlayerMultiTargetSpellFlowService()
    wizard = _actor(
        "wizard",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(1, 2, 2),),
    )
    goblin = _actor("goblin", Faction.ENEMY, Coordinate(3, 0))
    orc = _actor("orc", Faction.ENEMY, Coordinate(4, 0))
    state = _state(wizard, goblin, orc)

    started = service.start(
        state=state,
        board=BoardState(),
        action=_Spell(),
        cast_level=1,
    )

    assert started.pending is not None
    assert started.pending.projectile_count == 3
    assert set(started.pending.legal_target_ids) == {"goblin", "orc"}
    assert state.turn_action.action_use == ActionUse.ACTION_AVAILABLE
    assert wizard.spell_slots[0].remaining == 2

    pending = service.select_target(started.pending, "goblin")
    pending = service.select_target(pending, "goblin")
    pending = service.select_target(pending, "orc")
    resolved = service.confirm(
        state=state,
        action=_Spell(),
        pending=pending,
        allocations=(
            ProjectileAllocation("goblin", 1),
            ProjectileAllocation("goblin", 4),
            ProjectileAllocation("orc", 2),
        ),
    )

    actors = {str(actor.id): actor for actor in resolved.state.actors}
    assert actors["goblin"].hp == 13
    assert actors["orc"].hp == 17
    assert actors["wizard"].spell_slots[0].remaining == 1
    assert resolved.state.turn_action.action_use == ActionUse.ACTION_USED
    assert resolved.pending is None
    assert resolved.scene_flag_changes == (("cast_magic_missile", True),)


def test_scorching_ray_resolves_a_separate_spell_attack_for_each_ray() -> None:
    service = PlayerMultiTargetSpellFlowService()
    wizard = _actor(
        "wizard",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(2, 1, 1),),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(3, 0), hp=30)
    state = _state(wizard, enemy)
    started = service.start(
        state=state,
        board=BoardState(),
        action=_ScorchingRay(),
        cast_level=2,
    )
    assert started.pending is not None
    pending = started.pending
    for _ in range(3):
        pending = service.select_target(pending, "enemy")

    resolved = service.confirm(
        state=state,
        action=_ScorchingRay(),
        pending=pending,
        allocations=(
            ProjectileAllocation("enemy", 7, 20),
            ProjectileAllocation("enemy", 8, 1),
            ProjectileAllocation("enemy", 9, 12),
        ),
    )

    target = next(
        actor for actor in resolved.state.actors if str(actor.id) == "enemy"
    )
    assert target.hp == 14
    allocations = dict(resolved.event_payload)["allocations"]
    assert [entry["hit"] for entry in allocations] == [True, False, True]


def test_upcast_adds_projectile_and_cancel_is_free() -> None:
    service = PlayerMultiTargetSpellFlowService()
    wizard = _actor(
        "wizard",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(
            SpellSlotState(1, 1, 1),
            SpellSlotState(2, 1, 1),
        ),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = _state(wizard, enemy)

    started = service.start(
        state=state,
        board=BoardState(),
        action=_Spell(),
        cast_level=2,
    )
    assert started.pending is not None
    assert started.pending.projectile_count == 4

    cancelled = service.cancel(state=state, pending=started.pending)
    current_wizard = next(
        actor for actor in cancelled.state.actors if actor.id == wizard.id
    )
    assert current_wizard.spell_slots[1].remaining == 1
    assert cancelled.state.turn_action.action_use == ActionUse.ACTION_AVAILABLE


def test_magic_missile_rejects_incomplete_or_invalid_physical_rolls() -> None:
    service = PlayerMultiTargetSpellFlowService()
    wizard = _actor(
        "wizard",
        Faction.ALLY,
        Coordinate(0, 0),
        spell_slots=(SpellSlotState(1, 1, 1),),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = _state(wizard, enemy)
    started = service.start(
        state=state,
        board=BoardState(),
        action=_Spell(),
        cast_level=1,
    )
    assert started.pending is not None
    pending = service.select_target(started.pending, "enemy")

    with pytest.raises(ValueError, match="dokładnie 3"):
        service.confirm(
            state=state,
            action=_Spell(),
            pending=pending,
            allocations=(ProjectileAllocation("enemy", 2),),
        )

    pending = service.select_target(pending, "enemy")
    pending = service.select_target(pending, "enemy")
    with pytest.raises(ValueError, match="1–4"):
        service.confirm(
            state=state,
            action=_Spell(),
            pending=pending,
            allocations=(
                ProjectileAllocation("enemy", 2),
                ProjectileAllocation("enemy", 5),
                ProjectileAllocation("enemy", 1),
            ),
        )
