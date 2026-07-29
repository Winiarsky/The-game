from dataclasses import replace
from random import Random

import pytest

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    ActorResourcePool,
    Faction,
    RecoveryPeriod,
)
from dnd_board_game.application import PlayerAreaHealingFlowService
from dnd_board_game.combat import (
    ActionUse,
    AttackSource,
    AttackSourceType,
    CombatState,
    DamageComponentSpec,
    DamageType,
    HealingSource,
    HealingSourceType,
    InitiativeEntry,
    InitiativeOrder,
    SceneObject,
    SpellArea,
    SpellAreaShape,
    current_actor,
    start_combat,
)
from dnd_board_game.combat.setup import SetupVisibility
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.world import BLOCKING_TERRAIN, BoardState, Coordinate


def _actor(
    actor_id: str,
    faction: Faction,
    position: Coordinate,
    *,
    hp: int = 10,
    max_hp: int = 10,
    spell_save_dc: int = 13,
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=hp,
        max_hp=max_hp,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
        ability_scores=AbilityScores(dexterity=14),
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


def _healing_source() -> HealingSource:
    return HealingSource(
        id="healing_word",
        name="Healing Word",
        source_type=HealingSourceType.SPELL,
        range_feet=30,
        healing_hint="1d4",
    )


def _line_spell() -> AttackSource:
    return AttackSource(
        name="Promień",
        source_type=AttackSourceType.SPELL,
        range_feet=30,
        attack_roll_request=D20RollRequest(),
        damage_hint="2d6",
        damage_type="radiant",
        id="radiant_line",
        area=SpellArea(SpellAreaShape.LINE, length_feet=15),
        save_ability="dexterity",
        save_dc=1,
        save_damage_on_success="half",
    )


def _cover(position: Coordinate, bonus: int = 2) -> SceneObject:
    return SceneObject(
        id="cover",
        name="Osłona",
        positions=(position,),
        interaction_label="",
        visibility=SetupVisibility.VISIBLE,
        projectile_cover_bonus=bonus,
    )


def test_healing_flow_selects_wounded_ally_and_applies_effective_healing() -> None:
    service = PlayerAreaHealingFlowService()
    healer = _actor("healer", Faction.ALLY, Coordinate(0, 0))
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0), hp=4)
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(3, 0))
    state = _state(healer, ally, enemy)

    selected = service.select_healing_target(
        state=state,
        board=BoardState(),
        source=_healing_source(),
        position=ally.position,
    )
    assert selected.pending is not None
    assert selected.pending.target_id == "ally"
    assert selected.event_type == "ui_combat_player_healing_target_selected"

    healed = service.submit_healing(
        state=state,
        source=_healing_source(),
        pending=selected.pending,
        healing=8,
    )

    updated_ally = next(actor for actor in healed.state.actors if actor.id == ally.id)
    assert updated_ally.hp == 10
    assert healed.state.turn_action.action_use == ActionUse.ACTION_USED
    assert healed.pending is None
    assert dict(healed.event_payload)["effective_healing"] == 6


def test_healing_flow_rejects_a_full_health_target() -> None:
    service = PlayerAreaHealingFlowService()
    healer = _actor("healer", Faction.ALLY, Coordinate(0, 0))
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(3, 0))

    with pytest.raises(ValueError, match="legalnym celem leczenia"):
        service.select_healing_target(
            state=_state(healer, ally, enemy),
            board=BoardState(),
            source=_healing_source(),
            position=ally.position,
        )


def test_area_spell_flow_previews_confirms_and_applies_save_adjusted_damage() -> None:
    service = PlayerAreaHealingFlowService()
    caster = _actor("caster", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = _state(caster, enemy)
    source = _line_spell()

    selected = service.select_area_spell(
        state=state,
        board=BoardState(),
        source=source,
        position=Coordinate(1, 0),
    )
    assert selected.pending is not None
    assert selected.pending.target_ids == ("enemy",)
    assert Coordinate(2, 0) in selected.pending.area_positions

    confirmed = service.confirm_area_spell(
        state=state,
        source=source,
        pending=selected.pending,
        rng=Random(1),
    )
    assert confirmed.pending is not None
    assert confirmed.pending.stage == "damage_roll"
    assert confirmed.pending.saving_throws[0].success is True
    assert confirmed.state.turn_action.action_use == ActionUse.ACTION_USED

    damaged = service.submit_area_damage(
        state=confirmed.state,
        source=source,
        pending=confirmed.pending,
        damage=5,
    )

    updated_enemy = next(actor for actor in damaged.state.actors if actor.id == enemy.id)
    assert updated_enemy.hp == 8
    assert damaged.pending is None
    assert len(damaged.applied_damages) == 1
    assert dict(damaged.event_payload)["base_damage"] == 5


def test_area_spell_applies_save_to_each_typed_damage_component() -> None:
    service = PlayerAreaHealingFlowService()
    caster = _actor("caster", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = _state(caster, enemy)
    source = replace(
        _line_spell(),
        damage_components=(
            DamageComponentSpec(
                id="radiance",
                label="Blask",
                damage_type=DamageType.RADIANT,
                fixed=5,
            ),
            DamageComponentSpec(
                id="flame",
                label="Płomień",
                damage_type=DamageType.FIRE,
                fixed=3,
            ),
        ),
    )
    selected = service.select_area_spell(
        state=state,
        board=BoardState(),
        source=source,
        position=Coordinate(1, 0),
    )
    assert selected.pending is not None
    confirmed = service.confirm_area_spell(
        state=state,
        source=source,
        pending=selected.pending,
        rng=Random(1),
    )
    assert confirmed.pending is not None
    assert confirmed.pending.saving_throws[0].success is True

    damaged = service.submit_area_damage(
        state=confirmed.state,
        source=source,
        pending=confirmed.pending,
        component_totals={"radiance": 5, "flame": 3},
    )

    applied = damaged.applied_damages[0]
    assert applied.hp_after == 7
    assert [
        (component.damage_type, component.amount_before)
        for component in applied.damage.resolved_components
    ] == [(DamageType.RADIANT, 2), (DamageType.FIRE, 1)]
    assert dict(damaged.event_payload)["base_damage"] == 8


def test_area_spell_includes_allies_in_friendly_fire_targets() -> None:
    service = PlayerAreaHealingFlowService()
    caster = _actor("caster", Faction.ALLY, Coordinate(0, 0))
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = _state(caster, ally, enemy)

    selected = service.select_area_spell(
        state=state,
        board=BoardState(),
        source=_line_spell(),
        position=Coordinate(1, 0),
    )

    assert selected.pending is not None
    assert selected.pending.target_ids == ("ally", "enemy")

    confirmed = service.confirm_area_spell(
        state=state,
        source=_line_spell(),
        pending=selected.pending,
        rng=Random(1),
    )
    assert confirmed.pending is not None
    assert {save.actor_id for save in confirmed.pending.saving_throws} == {
        "ally",
        "enemy",
    }


def test_area_spell_applies_visible_half_cover_bonus_to_dexterity_save() -> None:
    service = PlayerAreaHealingFlowService()
    caster = _actor("caster", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = _state(caster, enemy)
    source = replace(_line_spell(), save_dc=9)

    selected = service.select_area_spell(
        state=state,
        board=BoardState(),
        source=source,
        position=Coordinate(1, 0),
        scene_objects=(_cover(Coordinate(1, 0)),),
    )
    assert selected.pending is not None
    positioning = dict(selected.pending.target_positioning)["enemy"]
    assert positioning.cover_bonus == 2

    confirmed = service.confirm_area_spell(
        state=state,
        source=source,
        pending=selected.pending,
        rng=Random(1),
    )

    assert confirmed.pending is not None
    save = confirmed.pending.saving_throws[0]
    assert save.natural_roll == 5
    assert save.total == 9
    assert save.success is True
    assert [(modifier.label, modifier.value) for modifier in save.modifiers][-1] == (
        "Połowa osłony",
        2,
    )


def test_radius_spell_excludes_target_with_total_cover_from_effect_origin() -> None:
    service = PlayerAreaHealingFlowService()
    caster = _actor("caster", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(4, 0))
    board = BoardState()
    board.set_terrain(Coordinate(3, 0), BLOCKING_TERRAIN)
    source = replace(
        _line_spell(),
        area=SpellArea(SpellAreaShape.RADIUS, radius_feet=10),
    )

    selected = service.select_area_spell(
        state=_state(caster, enemy),
        board=board,
        source=source,
        position=Coordinate(2, 0),
    )

    assert selected.pending is not None
    assert enemy.position not in selected.pending.area_positions
    assert selected.pending.target_ids == ("caster",)


def test_shatter_construct_save_uses_disadvantage() -> None:
    class _SequenceRandom:
        def __init__(self) -> None:
            self.values = [10, 18, 2]

        def randint(self, _minimum: int, _maximum: int) -> int:
            return self.values.pop(0)

    service = PlayerAreaHealingFlowService()
    caster = _actor("caster", Faction.ALLY, Coordinate(0, 0))
    construct = replace(
        _actor("construct", Faction.ENEMY, Coordinate(2, 0)),
        creature_type="construct",
    )
    state = _state(caster, construct)
    source = replace(
        _line_spell(),
        id="shatter",
        name="Roztrzaskanie",
        area=SpellArea(SpellAreaShape.RADIUS, radius_feet=10),
        save_ability="constitution",
        save_dc=12,
        save_disadvantage_creature_types=("construct",),
    )

    selected = service.select_area_spell(
        state=state,
        board=BoardState(),
        source=source,
        position=Coordinate(2, 0),
    )
    assert selected.pending is not None

    rng = _SequenceRandom()
    confirmed = service.confirm_area_spell(
        state=state,
        source=source,
        pending=selected.pending,
        rng=rng,
    )

    assert confirmed.pending is not None
    save = next(
        result
        for result in confirmed.pending.saving_throws
        if result.actor_id == "construct"
    )
    assert save.natural_roll == 2
    assert save.success is False
    assert rng.values == []


def test_area_metamagic_careful_auto_succeeds_and_heightened_uses_disadvantage() -> None:
    class _CountingRandom:
        def __init__(self) -> None:
            self.calls = 0

        def randint(self, _minimum: int, _maximum: int) -> int:
            self.calls += 1
            return 10

    service = PlayerAreaHealingFlowService()
    caster = replace(
        _actor("caster", Faction.ALLY, Coordinate(0, 0)),
        resource_pools=(
            ActorResourcePool(
                "sorcery_points",
                "Punkty magii",
                4,
                4,
                RecoveryPeriod.LONG_REST,
            ),
        ),
    )
    protected = _actor("protected", Faction.ALLY, Coordinate(1, 0))
    hindered = _actor("hindered", Faction.ENEMY, Coordinate(2, 0))
    state = _state(caster, protected, hindered)
    source = replace(
        _line_spell(),
        metamagic_ids=("metamagic_careful", "metamagic_heightened"),
        resource_pool_id="sorcery_points",
        resource_cost=4,
    )
    selected = service.select_area_spell(
        state=state,
        board=BoardState(),
        source=source,
        position=Coordinate(1, 0),
    )
    assert selected.pending is not None
    pending = replace(
        selected.pending,
        careful_target_ids=("protected",),
        heightened_target_id="hindered",
    )

    rng = _CountingRandom()
    confirmed = service.confirm_area_spell(
        state=state,
        source=source,
        pending=pending,
        rng=rng,
    )
    assert confirmed.pending is not None
    saves = {
        save.actor_id: save
        for save in confirmed.pending.saving_throws
    }
    assert saves["protected"].success is True
    assert rng.calls == len(saves) + 1


def test_sculpt_spells_protected_ally_is_excluded_from_saves_and_damage() -> None:
    service = PlayerAreaHealingFlowService()
    caster = _actor("caster", Faction.ALLY, Coordinate(0, 0))
    ally = _actor("ally", Faction.ALLY, Coordinate(1, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = _state(caster, ally, enemy)
    source = _line_spell()
    selected = service.select_area_spell(
        state=state,
        board=BoardState(),
        source=source,
        position=Coordinate(1, 0),
    )
    assert selected.pending is not None
    assert selected.pending.target_ids == ("ally", "enemy")
    sculpted = replace(
        selected.pending,
        target_ids=("enemy",),
        protected_target_ids=("ally",),
    )

    confirmed = service.confirm_area_spell(
        state=state,
        source=source,
        pending=sculpted,
        rng=Random(1),
    )

    assert confirmed.pending is not None
    assert confirmed.pending.protected_target_ids == ("ally",)
    assert [save.actor_id for save in confirmed.pending.saving_throws] == ["enemy"]
    damaged = service.submit_area_damage(
        state=confirmed.state,
        source=source,
        pending=confirmed.pending,
        damage=6,
    )
    actors = {str(actor.id): actor for actor in damaged.state.actors}
    assert actors["ally"].hp == 10
    assert actors["enemy"].hp < 10


def test_cancel_transitions_leave_combat_state_unchanged() -> None:
    service = PlayerAreaHealingFlowService()
    caster = _actor("caster", Faction.ALLY, Coordinate(0, 0))
    ally = _actor("ally", Faction.ALLY, Coordinate(0, 1), hp=5)
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = _state(caster, ally, enemy)
    healing = service.select_healing_target(
        state=state,
        board=BoardState(),
        source=_healing_source(),
        position=ally.position,
    )
    area = service.select_area_spell(
        state=state,
        board=BoardState(),
        source=_line_spell(),
        position=Coordinate(1, 0),
    )
    assert healing.pending is not None
    assert area.pending is not None

    cancelled_healing = service.cancel_healing(state=state, pending=healing.pending)
    cancelled_area = service.cancel_area_spell(state=state, pending=area.pending)

    assert cancelled_healing.state is state
    assert cancelled_healing.pending is None
    assert cancelled_area.state is state
    assert cancelled_area.pending is None
    assert current_actor(cancelled_area.state).id == caster.id
