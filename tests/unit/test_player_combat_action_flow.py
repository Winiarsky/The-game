from dataclasses import replace
from random import Random

import pytest

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    ActorResourcePool,
    DamageAffinityProfile,
    Faction,
    FeatureGrant,
    FeatureSourceKind,
    RecoveryPeriod,
)
from dnd_board_game.application import PlayerCombatActionFlowService
from dnd_board_game.combat import (
    ActionUse,
    ActiveCombatEffect,
    AttackKind,
    AttackSource,
    AttackSourceType,
    CombatState,
    CombatCondition,
    ConditionSaveTiming,
    ConditionState,
    DamageComponentSpec,
    HealingSource,
    HealingSourceType,
    HiddenState,
    DamageType,
    InitiativeEntry,
    InitiativeOrder,
    SceneObject,
    SpellSlotState,
    current_actor,
    resolve_condition_save,
    start_attack_action,
    start_combat,
)
from dnd_board_game.rules import (
    DiceExpression,
    D20RollInput,
    D20RollRequest,
    EffectDuration,
    resolve_d20_roll,
)
from dnd_board_game.world import BoardState, Coordinate


class SequenceRng:
    def __init__(self, *values: int) -> None:
        self.values = list(values)

    def randint(self, _minimum: int, _maximum: int) -> int:
        return self.values.pop(0)


def _actor(actor_id: str, faction: Faction, position: Coordinate) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=position,
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


def _source() -> AttackSource:
    return AttackSource(
        name="Miecz",
        source_type=AttackSourceType.WEAPON,
        range_feet=5,
        attack_roll_request=D20RollRequest(),
        damage_hint="1d8",
        damage_type="slashing",
        id="sword",
    )


def _dexterity_save_source() -> AttackSource:
    return AttackSource(
        name="Święty płomień",
        source_type=AttackSourceType.SPELL,
        range_feet=60,
        attack_roll_request=D20RollRequest(),
        damage_hint="1d8",
        damage_type="radiant",
        id="sacred_flame",
        attack_kind=AttackKind.RANGED,
        save_ability="dexterity",
        save_dc=9,
        save_damage_on_success="half",
    )


def test_source_selection_validates_active_hero_and_preserves_event_contract() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, enemy)

    attack = service.select_attack_source(
        state=state,
        sources=(_source(),),
        source_id="sword",
    )
    healing = service.select_healing_source(
        state=state,
        sources=(
            HealingSource(
                id="heal",
                name="Leczenie ran",
                source_type=HealingSourceType.SPELL,
                range_feet=5,
            ),
        ),
        source_id="heal",
    )

    assert attack.actor_id == "hero"
    assert attack.event_type == "ui_combat_attack_source_selected"
    assert dict(attack.event_payload) == {"actor_id": "hero", "source_id": "sword"}
    assert healing.event_type == "ui_combat_healing_source_selected"

    with pytest.raises(ValueError, match="Nieznane źródło ataku"):
        service.select_attack_source(state=state, sources=(_source(),), source_id="missing")
    with pytest.raises(ValueError, match="To nie jest tura bohatera"):
        service.select_attack_source(
            state=_state(enemy, hero),
            sources=(_source(),),
            source_id="sword",
        )


def test_staged_attack_moves_from_target_preview_through_damage() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, enemy)
    source = _source()
    penalty = ActiveCombatEffect(
        id="penalty",
        actor_id="hero",
        kind="grant_next_attack_penalty",
        label="Kara",
        object_id="test:penalty",
        value=-1,
    )

    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=(penalty,),
    )
    assert selected.pending is not None
    assert selected.pending.stage == "confirm_attack"

    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=(penalty,),
        rng=Random(1),
    )
    assert confirmed.pending is not None
    assert confirmed.pending.stage == "attack_roll"

    rolled = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=source,
        pending=confirmed.pending,
        active_effects=(penalty,),
        natural_roll=20,
    )
    assert rolled.pending is not None
    assert rolled.pending.stage == "damage_roll"
    assert rolled.pending.critical is True
    assert rolled.active_effects == ()
    assert rolled.state.turn_action.action_use == ActionUse.ACTION_USED

    damaged = service.submit_damage(
        state=rolled.state,
        source=source,
        pending=rolled.pending,
        active_effects=rolled.active_effects,
        damage=5,
    )
    updated_enemy = next(actor for actor in damaged.state.actors if actor.id == enemy.id)
    assert updated_enemy.hp == 5
    assert damaged.pending is None
    assert damaged.applied_damage is not None
    assert damaged.event_type == "ui_combat_player_damage_roll"


def test_guard_vault_moves_behind_target_even_on_miss_and_marks_only_its_oa_bonus() -> None:
    service = PlayerCombatActionFlowService()
    mira = _actor("mira", Faction.ALLY, Coordinate(1, 1))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 1))
    state = _state(mira, enemy)
    source = replace(
        _source(),
        id="guard_vault",
        name="Przeskok przez gardę",
    )

    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=(),
    )
    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=(),
        rng=Random(1),
    )
    rolled = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=source,
        pending=confirmed.pending,
        active_effects=(),
        natural_roll=1,
    )

    moved_mira = next(actor for actor in rolled.state.actors if actor.id == mira.id)
    assert rolled.pending is None
    assert moved_mira.position == Coordinate(3, 1)
    escape = next(effect for effect in rolled.active_effects if effect.kind == "guard_vault_opportunity_ac")
    assert escape.actor_id == "mira"
    assert escape.target_actor_id == "enemy"
    assert escape.value == 2


def test_piercing_attack_uses_side_engagement_and_spends_one_fortel_for_both_hits() -> None:
    service = PlayerCombatActionFlowService()
    mira = replace(
        _actor("mira", Faction.ALLY, Coordinate(1, 1)),
        features=(
            FeatureGrant(
                "mira_shadow_killer",
                "Atak z cienia",
                FeatureSourceKind.SCENARIO,
                "test:mira",
            ),
        ),
        resource_pools=(
            ActorResourcePool(
                "trick_uses", "Fortele", 4, 4, RecoveryPeriod.LONG_REST
            ),
        ),
    )
    ally = _actor("ally", Faction.ALLY, Coordinate(2, 2))
    first = _actor("first", Faction.ENEMY, Coordinate(2, 1))
    second = _actor("second", Faction.ENEMY, Coordinate(3, 1))
    state = _state(mira, ally, first, second)
    source = replace(
        _source(),
        id="piercing_attack",
        name="Przeszywający atak",
        proficiency_id="rapier",
        resource_pool_id="trick_uses",
        resource_cost=1,
        damage_components=(
            DamageComponentSpec(
                "rapier",
                DamageType.PIERCING,
                DiceExpression(1, 8),
                modifier=0,
            ),
        ),
        damage_hint="1d8",
        damage_type=DamageType.PIERCING.value,
    )

    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=first.position,
        active_effects=(),
    )
    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=(),
        rng=Random(1),
    )
    assert confirmed.pending.mira_piercing_second_target_id == "second"
    assert confirmed.pending.flanking_ally_ids == ("ally",)

    first_roll = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=source,
        pending=confirmed.pending,
        active_effects=(),
        natural_roll=15,
        natural_roll_2=10,
    )
    first_damage = service.submit_damage(
        state=first_roll.state,
        source=source,
        pending=first_roll.pending,
        active_effects=first_roll.active_effects,
        component_totals={"rapier": 1, "sneak_attack": 1},
    )
    assert first_damage.pending is not None
    assert first_damage.pending.target_id == "second"
    assert first_damage.pending.mira_piercing_second is True
    mira_after_first = next(actor for actor in first_damage.state.actors if actor.id == mira.id)
    assert next(pool for pool in mira_after_first.resource_pools if pool.id == "trick_uses").current == 3

    second_roll = service.submit_attack_roll(
        state=first_damage.state,
        board=BoardState(),
        source=source,
        pending=first_damage.pending,
        active_effects=first_damage.active_effects,
        natural_roll=15,
        natural_roll_2=10,
    )
    second_damage = service.submit_damage(
        state=second_roll.state,
        source=source,
        pending=second_roll.pending,
        active_effects=second_roll.active_effects,
        component_totals={"rapier": 1, "sneak_attack": 1},
    )
    mira_after_second = next(actor for actor in second_damage.state.actors if actor.id == mira.id)
    assert second_damage.pending is None
    assert next(pool for pool in mira_after_second.resource_pools if pool.id == "trick_uses").current == 3


def test_player_attack_uses_physical_mirror_image_roll_and_consumes_duplicate() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, enemy)
    source = _source()
    mirror = ActiveCombatEffect(
        id="mirror-image:enemy",
        actor_id="enemy",
        kind="mirror_image",
        label="Lustrzane odbicia",
        object_id="spell:mirror_image",
        value=3,
        source_actor_id="enemy",
        target_actor_id="enemy",
        duration=EffectDuration.UNTIL_ENCOUNTER_END,
    )
    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=(mirror,),
    )
    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=(mirror,),
        rng=Random(1),
    )

    with pytest.raises(ValueError, match="Lustrzanych odbić"):
        service.submit_attack_roll(
            state=state,
            board=BoardState(),
            source=source,
            pending=confirmed.pending,
            active_effects=(mirror,),
            natural_roll=15,
        )
    rolled = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=source,
        pending=confirmed.pending,
        active_effects=(mirror,),
        natural_roll=15,
        mirror_image_roll=20,
    )

    assert rolled.pending is None
    assert rolled.active_effects[0].value == 2
    assert dict(rolled.event_payload)["hit"] is False
    assert dict(rolled.event_payload)["mirror_image"]["duplicate_hit"] is True
    assert "niszczy duplikat" in rolled.message_body


def test_failed_sanctuary_save_blocks_target_and_board_keeps_alternative() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    protected = replace(
        _actor("protected", Faction.ENEMY, Coordinate(1, 0)),
        spell_save_dc=30,
    )
    alternative = _actor("alternative", Faction.ENEMY, Coordinate(0, 1))
    state = _state(hero, protected, alternative)
    source = _source()
    sanctuary = ActiveCombatEffect(
        id="sanctuary:protected",
        actor_id="protected",
        kind="sanctuary",
        label="Sanktuarium",
        object_id="spell:sanctuary",
        value=0,
        source_actor_id="protected",
        target_actor_id="protected",
        duration=EffectDuration.UNTIL_ENCOUNTER_END,
    )
    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=protected.position,
        active_effects=(sanctuary,),
    )
    blocked = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=(sanctuary,),
        rng=Random(1),
    )

    assert blocked.pending is None
    assert blocked.event_type == "ui_combat_sanctuary_blocked_attack"
    assert any(
        effect.kind == "sanctuary_block_target"
        for effect in blocked.active_effects
    )
    legal = start_attack_action(
        BoardState(),
        hero,
        state.actors,
        source,
        state.hidden_states,
        blocked.active_effects,
    ).legal_targets
    assert {target.id for target in legal} == {"alternative"}


def test_guiding_bolt_hit_marks_target_for_next_attack_advantage() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = _state(hero, enemy)
    source = replace(
        _source(),
        id="guiding_bolt",
        name="Guiding Bolt",
        source_type=AttackSourceType.SPELL,
        range_feet=120,
        attack_kind=AttackKind.RANGED,
        on_hit_effect_kind="guiding_bolt_mark",
    )
    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=(),
    )
    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=(),
        rng=Random(1),
    )
    rolled = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=source,
        pending=confirmed.pending,
        active_effects=(),
        natural_roll=20,
    )
    damaged = service.submit_damage(
        state=rolled.state,
        source=source,
        pending=rolled.pending,
        active_effects=rolled.active_effects,
        damage=4,
    )

    assert damaged.active_effects[0].kind == "guiding_bolt_mark"
    assert damaged.active_effects[0].actor_id == "enemy"


def test_branding_smite_hit_reveals_target_and_keeps_concentration_glow() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, enemy)
    source = replace(
        _source(),
        damage_components=(
            DamageComponentSpec(
                "sword",
                DamageType.SLASHING,
                DiceExpression(1, 8),
                label="Miecz",
            ),
        ),
    )
    branding = ActiveCombatEffect(
        id="branding-smite:hero",
        actor_id="hero",
        kind="branding_smite",
        label="Piętnujące porażenie",
        object_id="spell:branding_smite",
        value=2,
        source_actor_id="hero",
        duration=EffectDuration.CONCENTRATION,
        spell_level=2,
    )
    invisible = ActiveCombatEffect(
        id="invisibility:enemy",
        actor_id="enemy",
        kind="invisibility",
        label="Niewidzialność",
        object_id="spell:invisibility",
        value=0,
        source_actor_id="enemy",
        duration=EffectDuration.CONCENTRATION,
    )
    effects = (branding, invisible)

    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=effects,
    )
    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=effects,
        rng=Random(1),
    )
    rolled = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=source,
        pending=confirmed.pending,
        active_effects=effects,
        natural_roll=20,
        natural_roll_2=20,
    )
    damaged = service.submit_damage(
        state=rolled.state,
        source=source,
        pending=rolled.pending,
        active_effects=rolled.active_effects,
        component_totals={"sword": 4, "branding_smite": 7},
    )

    assert not any(effect.kind == "invisibility" for effect in damaged.active_effects)
    glow = next(
        effect
        for effect in damaged.active_effects
        if effect.kind == "branding_smite_glow"
    )
    assert glow.actor_id == "enemy"
    assert glow.source_actor_id == "hero"
    assert glow.duration == EffectDuration.CONCENTRATION


def test_ray_of_enfeeblement_hit_creates_end_turn_constitution_save() -> None:
    service = PlayerCombatActionFlowService()
    hero = replace(
        _actor("hero", Faction.ALLY, Coordinate(0, 0)),
        spell_save_dc=14,
        spell_slots=(SpellSlotState(2, 1, 1),),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = _state(hero, enemy)
    source = replace(
        _source(),
        id="ray_of_enfeeblement",
        name="Promień osłabienia",
        source_type=AttackSourceType.SPELL,
        range_feet=60,
        attack_kind=AttackKind.RANGED,
        spell_level=2,
        concentration=True,
        on_hit_effect_kind="ray_of_enfeeblement",
        on_hit_effect_duration=EffectDuration.CONCENTRATION,
    )
    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=(),
    )
    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=(),
        rng=Random(1),
    )
    rolled = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=source,
        pending=confirmed.pending,
        active_effects=(),
        natural_roll=20,
    )
    damaged = service.submit_damage(
        state=rolled.state,
        source=source,
        pending=rolled.pending,
        active_effects=rolled.active_effects,
        damage=0,
    )

    effect = next(
        item
        for item in damaged.active_effects
        if item.kind == "ray_of_enfeeblement"
    )
    condition = next(
        item
        for item in damaged.state.condition_states
        if item.condition == CombatCondition.ENFEEBLED
    )
    assert effect.duration == EffectDuration.CONCENTRATION
    assert condition.save_ability == "constitution"
    assert condition.save_dc == 14
    assert condition.save_timing == ConditionSaveTiming.TURN_END
    save = resolve_condition_save(
        damaged.state.condition_states,
        enemy,
        condition,
        natural_roll=14,
    )
    assert save.removed is True


def test_player_damage_accepts_independent_multicomponent_totals() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = replace(
        _actor("enemy", Faction.ENEMY, Coordinate(1, 0)),
        hp=20,
        damage_affinities=DamageAffinityProfile(
            resistances=(DamageType.FIRE,)
        ),
    )
    state = _state(hero, enemy)
    source = replace(
        _source(),
        damage_components=(
            DamageComponentSpec(
                "blade",
                DamageType.SLASHING,
                dice=DiceExpression.parse("1d8"),
            ),
            DamageComponentSpec(
                "flame",
                DamageType.FIRE,
                dice=DiceExpression.parse("1d6"),
            ),
        ),
    )
    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=(),
    )
    assert selected.pending is not None
    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=(),
        rng=Random(1),
    )
    assert confirmed.pending is not None
    rolled = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=source,
        pending=confirmed.pending,
        active_effects=(),
        natural_roll=15,
    )
    assert rolled.pending is not None

    damaged = service.submit_damage(
        state=rolled.state,
        source=source,
        pending=rolled.pending,
        active_effects=(),
        component_totals={"blade": 6, "flame": 5},
    )

    assert damaged.applied_damage is not None
    assert damaged.applied_damage.damage.total_before_reduction == 11
    assert damaged.applied_damage.damage.total_applied == 8
    assert next(
        actor for actor in damaged.state.actors if actor.id == enemy.id
    ).hp == 12


def test_single_target_dexterity_save_uses_scene_cover_bonus() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(4, 0))
    state = _state(hero, enemy)
    source = replace(
        _dexterity_save_source(),
        id="generic_dexterity_save",
        name="Generyczny czar obszarowy",
    )
    cover = SceneObject(
        id="cart",
        name="Wóz",
        positions=(Coordinate(2, 0),),
        interaction_label="",
        projectile_cover_bonus=2,
    )

    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=(),
        scene_objects=(cover,),
    )
    assert selected.pending is not None
    assert selected.pending.cover_bonus == 2

    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=(),
        rng=Random(1),
        scene_objects=(cover,),
    )

    assert confirmed.pending is not None
    save = confirmed.pending.saving_throws[0]
    assert save.total == 9
    assert save.success is True
    assert any(
        modifier.label == "Połowa osłony" and modifier.value == 2
        for modifier in save.modifiers
    )


def test_sacred_flame_ignores_scene_cover_bonus_on_dexterity_save() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(4, 0))
    state = _state(hero, enemy)
    source = _dexterity_save_source()
    cover = SceneObject(
        id="cart",
        name="Wóz",
        positions=(Coordinate(2, 0),),
        interaction_label="",
        projectile_cover_bonus=2,
    )
    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=(),
        scene_objects=(cover,),
    )
    assert selected.pending is not None
    assert selected.pending.cover_bonus == 2

    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=(),
        rng=Random(1),
        scene_objects=(cover,),
    )

    assert confirmed.pending is not None
    save = confirmed.pending.saving_throws[0]
    assert save.total == 7
    assert save.success is False
    assert not any(modifier.label == "Połowa osłony" for modifier in save.modifiers)


def test_dagna_triage_gives_target_advantage_against_save_spell() -> None:
    service = PlayerCombatActionFlowService()
    dagna = _actor("dagna", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(4, 0))
    state = _state(dagna, enemy)
    source = _dexterity_save_source()
    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=(),
    )
    assert selected.pending is not None

    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=(
            ActiveCombatEffect(
                id="flaw_triage_active:dagna",
                actor_id="dagna",
                kind="flaw_triage_active",
                label="Nikogo nie zostawiam",
                object_id="feature:flaw_triage_active",
                value=0,
            ),
        ),
        rng=Random(1),
    )

    assert confirmed.pending is not None
    assert confirmed.pending.saving_throws[0].natural_roll == 19


def test_dagna_triage_advantage_cancels_restrained_save_disadvantage() -> None:
    service = PlayerCombatActionFlowService()
    dagna = _actor("dagna", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(4, 0))
    state = replace(
        _state(dagna, enemy),
        condition_states=(
            ConditionState(
                str(enemy.id),
                CombatCondition.RESTRAINED,
                source_actor_id="trap",
            ),
        ),
    )
    source = _dexterity_save_source()
    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=(),
    )
    assert selected.pending is not None

    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=(
            ActiveCombatEffect(
                id="flaw_triage_active:dagna",
                actor_id="dagna",
                kind="flaw_triage_active",
                label="Nikogo nie zostawiam",
                object_id="feature:flaw_triage_active",
                value=0,
            ),
        ),
        rng=Random(1),
    )

    assert confirmed.pending is not None
    assert confirmed.pending.saving_throws[0].natural_roll == 5


def test_twinned_save_spell_spends_one_action_and_damages_two_targets() -> None:
    service = PlayerCombatActionFlowService()
    hero = replace(
        _actor("hero", Faction.ALLY, Coordinate(0, 0)),
        level=3,
        ability_scores=AbilityScores(charisma=16, dexterity=14),
        features=(
            FeatureGrant(
                "dark_ones_blessing",
                "Błogosławieństwo Mrocznego",
                FeatureSourceKind.SUBCLASS,
                "the_fiend",
            ),
        ),
    )
    first = _actor("first", Faction.ENEMY, Coordinate(2, 0))
    second = replace(
        _actor("second", Faction.ENEMY, Coordinate(3, 0)),
        hp=3,
    )
    state = _state(hero, first, second)
    source = replace(
        _dexterity_save_source(),
        save_dc=30,
        metamagic_ids=("metamagic_twinned",),
    )
    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=first.position,
        active_effects=(),
    )
    assert selected.pending is not None
    pending = replace(
        selected.pending,
        twinned_target_id=str(second.id),
    )

    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=pending,
        active_effects=(),
        rng=Random(4),
    )
    assert confirmed.pending is not None
    assert len(confirmed.pending.saving_throws) == 2
    damaged = service.submit_damage(
        state=confirmed.state,
        source=source,
        pending=confirmed.pending,
        active_effects=(),
        damage=4,
    )

    assert damaged.state.turn_action.action_use == ActionUse.ACTION_USED
    assert next(actor for actor in damaged.state.actors if actor.id == first.id).hp == 6
    assert next(actor for actor in damaged.state.actors if actor.id == second.id).hp == 0
    assert next(actor for actor in damaged.state.actors if actor.id == hero.id).temp_hp == 6
    assert len(damaged.additional_applied_damages) == 1


def test_acid_splash_optional_second_adjacent_target_shares_one_action() -> None:
    service = PlayerCombatActionFlowService()
    caster = _actor("caster", Faction.ALLY, Coordinate(0, 0))
    first = _actor("first", Faction.ENEMY, Coordinate(2, 0))
    second = _actor("second", Faction.ENEMY, Coordinate(2, 1))
    state = _state(caster, first, second)
    source = replace(
        _dexterity_save_source(),
        id="acid_splash",
        name="Kwasowy rozprysk",
        damage_type="acid",
        save_dc=30,
    )
    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=first.position,
        active_effects=(),
    )
    assert selected.pending is not None
    pending = replace(
        selected.pending,
        twinned_target_id=str(second.id),
    )

    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=pending,
        active_effects=(),
        rng=Random(4),
    )
    assert confirmed.pending is not None
    assert len(confirmed.pending.saving_throws) == 2
    damaged = service.submit_damage(
        state=confirmed.state,
        source=source,
        pending=confirmed.pending,
        active_effects=(),
        damage=4,
    )

    assert damaged.state.turn_action.action_use == ActionUse.ACTION_USED
    assert next(actor for actor in damaged.state.actors if actor.id == first.id).hp == 6
    assert next(actor for actor in damaged.state.actors if actor.id == second.id).hp == 6
    assert len(damaged.additional_applied_damages) == 1


def test_lightning_chain_forced_weave_hampers_only_primary_target() -> None:
    service = PlayerCombatActionFlowService()
    caster = _actor("nimra", Faction.ALLY, Coordinate(0, 0))
    primary = _actor("primary", Faction.ENEMY, Coordinate(2, 0))
    jumped = _actor("jumped", Faction.ENEMY, Coordinate(3, 0))
    state = _state(caster, primary, jumped)
    source = replace(
        _dexterity_save_source(),
        id="nimra_lightning_path",
        name="Piorunowy szlak",
        damage_hint="3d6",
        metamagic_ids=("nimra_forced_weave",),
    )
    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=primary.position,
        active_effects=(),
    )
    assert selected.pending is not None
    pending = replace(selected.pending, twinned_target_id=str(jumped.id))
    rng = SequenceRng(20, 1, 20)

    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=pending,
        active_effects=(),
        rng=rng,
    )

    assert confirmed.pending is not None
    saves = {save.actor_id: save for save in confirmed.pending.saving_throws}
    assert saves["primary"].natural_roll == 1
    assert saves["primary"].success is False
    assert saves["jumped"].natural_roll == 20
    assert saves["jumped"].success is True
    assert rng.values == []


def test_twinned_attack_spell_resolves_second_attack_without_second_action() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    first = _actor("first", Faction.ENEMY, Coordinate(2, 0))
    second = _actor("second", Faction.ENEMY, Coordinate(3, 0))
    state = _state(hero, first, second)
    source = AttackSource(
        id="test_bolt",
        name="Test Bolt",
        source_type=AttackSourceType.SPELL,
        range_feet=60,
        attack_kind=AttackKind.RANGED,
        attack_roll_request=D20RollRequest(),
        damage_hint="1d6",
        damage_die_sides=6,
        damage_type="force",
        metamagic_ids=("metamagic_twinned",),
    )
    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=first.position,
        active_effects=(),
    )
    assert selected.pending is not None
    pending = replace(selected.pending, twinned_target_id=str(second.id))
    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=pending,
        active_effects=(),
        rng=Random(1),
    )
    assert confirmed.pending is not None
    first_roll = service.submit_attack_roll(
        state=confirmed.state,
        board=BoardState(),
        source=source,
        pending=confirmed.pending,
        active_effects=(),
        natural_roll=20,
    )
    assert first_roll.pending is not None
    first_damage = service.submit_damage(
        state=first_roll.state,
        source=source,
        pending=first_roll.pending,
        active_effects=(),
        damage=3,
    )
    assert first_damage.pending is not None
    assert first_damage.pending.twinned_second_attack

    second_roll = service.submit_attack_roll(
        state=first_damage.state,
        board=BoardState(),
        source=source,
        pending=first_damage.pending,
        active_effects=(),
        natural_roll=20,
    )
    assert second_roll.pending is not None
    second_damage = service.submit_damage(
        state=second_roll.state,
        source=source,
        pending=second_roll.pending,
        active_effects=(),
        damage=3,
    )
    assert second_damage.pending is None
    assert second_damage.state.turn_action.action_use == ActionUse.ACTION_USED


def test_repelling_blast_opens_push_choice_after_damage() -> None:
    service = PlayerCombatActionFlowService()
    hero = replace(
        _actor("hero", Faction.ALLY, Coordinate(0, 0)),
        features=(
            FeatureGrant(
                "repelling_blast",
                "Repelling Blast",
                FeatureSourceKind.CLASS,
                "warlock",
            ),
        ),
    )
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 0))
    state = _state(hero, enemy)
    source = AttackSource(
        id="eldritch_blast",
        name="Eldritch Blast",
        source_type=AttackSourceType.SPELL,
        range_feet=120,
        attack_kind=AttackKind.RANGED,
        attack_roll_request=D20RollRequest(),
        damage_hint="1d10",
        damage_die_sides=10,
        damage_type="force",
    )
    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        position=enemy.position,
        active_effects=(),
    )
    assert selected.pending is not None
    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=source,
        pending=selected.pending,
        active_effects=(),
        rng=Random(1),
    )
    assert confirmed.pending is not None
    rolled = service.submit_attack_roll(
        state=confirmed.state,
        board=BoardState(),
        source=source,
        pending=confirmed.pending,
        active_effects=(),
        natural_roll=20,
    )
    assert rolled.pending is not None
    damaged = service.submit_damage(
        state=rolled.state,
        source=source,
        pending=rolled.pending,
        active_effects=(),
        damage=1,
    )
    assert damaged.pending is not None
    assert damaged.pending.stage == "repelling_blast_choice"


def test_missed_attack_spends_action_and_finishes_pending_flow() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = _state(hero, enemy)
    pending = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        position=enemy.position,
        active_effects=(),
    ).pending
    assert pending is not None
    pending = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=pending,
        active_effects=(),
        rng=Random(1),
    ).pending
    assert pending is not None

    transition = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=pending,
        active_effects=(),
        natural_roll=1,
    )

    assert transition.pending is None
    assert transition.state.turn_action.action_use == ActionUse.ACTION_USED
    assert "pudłuje" in transition.message_body
    assert dict(transition.event_payload)["hit"] is False


def test_direct_attack_compatibility_transition_applies_damage() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))

    transition = service.resolve_direct_attack(
        state=_state(hero, enemy),
        board=BoardState(),
        source=_source(),
        target_id="enemy",
        active_effects=(),
        natural_roll=20,
        damage=4,
    )

    assert current_actor(transition.state).id == hero.id
    assert transition.state.turn_action.action_use == ActionUse.ACTION_USED
    assert next(actor for actor in transition.state.actors if actor.id == enemy.id).hp == 6
    assert transition.applied_damage is not None
    assert transition.event_type == "ui_combat_player_attack"


def test_extra_attack_actor_can_change_target_between_weapon_attacks() -> None:
    service = PlayerCombatActionFlowService()
    hero = replace(
        _actor("hero", Faction.ALLY, Coordinate(0, 0)),
        attacks_per_action=2,
    )
    first_enemy = _actor("enemy_1", Faction.ENEMY, Coordinate(1, 0))
    second_enemy = _actor("enemy_2", Faction.ENEMY, Coordinate(0, 1))
    state = _state(hero, first_enemy, second_enemy)

    first = service.resolve_direct_attack(
        state=state,
        board=BoardState(),
        source=_source(),
        target_id="enemy_1",
        active_effects=(),
        natural_roll=20,
        damage=1,
    )
    second = service.resolve_direct_attack(
        state=first.state,
        board=BoardState(),
        source=_source(),
        target_id="enemy_2",
        active_effects=(),
        natural_roll=20,
        damage=1,
    )

    assert first.state.turn_action.attacks_used == 1
    assert second.state.turn_action.attacks_used == 2
    assert next(actor for actor in second.state.actors if str(actor.id) == "enemy_1").hp == 9
    assert next(actor for actor in second.state.actors if str(actor.id) == "enemy_2").hp == 9


def test_direct_attack_applies_target_resistance_and_exposes_breakdown() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = replace(
        _actor("enemy", Faction.ENEMY, Coordinate(1, 0)),
        damage_affinities=DamageAffinityProfile(resistances=(DamageType.SLASHING,)),
    )

    transition = service.resolve_direct_attack(
        state=_state(hero, enemy),
        board=BoardState(),
        source=_source(),
        target_id="enemy",
        active_effects=(),
        natural_roll=20,
        damage=9,
    )

    assert next(actor for actor in transition.state.actors if actor.id == enemy.id).hp == 6
    assert transition.applied_damage is not None
    assert transition.applied_damage.damage.total_before_reduction == 9
    assert transition.applied_damage.damage.total_applied == 4
    payload = dict(transition.event_payload)["damage_result"]
    assert payload["damage_before_affinities"] == 9
    assert payload["damage_breakdown"]["components"][0]["adjustment"] == "resistance"
    assert "odporność" in transition.message_body


def test_ranged_attack_flow_applies_cover_ac_and_melee_disadvantage() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    target = _actor("target", Faction.ENEMY, Coordinate(4, 0))
    threat = _actor("threat", Faction.ENEMY, Coordinate(0, 1))
    state = _state(hero, target, threat)
    crossbow = AttackSource(
        name="Kusza",
        source_type=AttackSourceType.WEAPON,
        range_feet=80,
        attack_roll_request=D20RollRequest(),
        id="crossbow",
        attack_kind=AttackKind.RANGED,
    )
    cart = SceneObject(
        "cart",
        "Wóz",
        (Coordinate(2, 0),),
        "",
        projectile_cover_bonus=2,
    )

    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=crossbow,
        position=target.position,
        active_effects=(),
        scene_objects=(cart,),
    )
    assert selected.pending is not None
    assert selected.pending.cover_bonus == 2
    assert selected.pending.cover_sources == ("Wóz",)
    assert selected.pending.ranged_threat_actor_ids == ("threat",)

    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=crossbow,
        pending=selected.pending,
        active_effects=(),
        rng=Random(1),
        scene_objects=(cart,),
    )
    assert confirmed.pending is not None

    rolled = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=crossbow,
        pending=confirmed.pending,
        active_effects=(),
        natural_roll=15,
        natural_roll_2=13,
        scene_objects=(cart,),
    )

    assert rolled.pending is None
    payload = dict(rolled.event_payload)
    assert payload["natural_rolls"] == [15, 13]
    assert payload["total"] == 13
    assert payload["hit"] is False


def test_melee_attack_flow_records_default_flanking_and_rolls_with_advantage() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(1, 2))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(2, 2))
    ally = _actor("ally", Faction.ALLY, Coordinate(3, 2))
    state = _state(hero, enemy, ally)

    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        position=enemy.position,
        active_effects=(),
    )
    assert selected.pending is not None
    assert selected.pending.flanking_ally_ids == ("ally",)
    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=selected.pending,
        active_effects=(),
        rng=Random(1),
    )
    assert confirmed.pending is not None

    rolled = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=confirmed.pending,
        active_effects=(),
        natural_roll=5,
        natural_roll_2=15,
    )

    payload = dict(rolled.event_payload)
    assert payload["natural_rolls"] == [5, 15]
    assert payload["total"] == 15


def test_attack_from_hidden_has_advantage_and_reveals_attacker() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = replace(
        _state(hero, enemy),
        hidden_states=(HiddenState("hero", 18, ("enemy",)),),
    )

    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        position=enemy.position,
        active_effects=(),
    )
    assert selected.pending is not None
    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=selected.pending,
        active_effects=(),
        rng=Random(1),
    )
    assert confirmed.pending is not None
    rolled = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=confirmed.pending,
        active_effects=(),
        natural_roll=5,
        natural_roll_2=15,
    )

    assert dict(rolled.event_payload)["natural_rolls"] == [5, 15]
    assert rolled.state.hidden_states == ()


def test_prone_attacker_rolls_with_disadvantage() -> None:
    service = PlayerCombatActionFlowService()
    hero = _actor("hero", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", Faction.ENEMY, Coordinate(1, 0))
    state = replace(
        _state(hero, enemy),
        condition_states=(ConditionState("hero", CombatCondition.PRONE),),
    )

    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        position=enemy.position,
        active_effects=(),
    )
    assert selected.pending is not None
    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=selected.pending,
        active_effects=(),
        rng=Random(1),
    )
    assert confirmed.pending is not None
    rolled = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=confirmed.pending,
        active_effects=(),
        natural_roll=17,
        natural_roll_2=4,
    )

    assert dict(rolled.event_payload)["natural_rolls"] == [17, 4]
    assert dict(rolled.event_payload)["total"] == 4


def test_horde_breaker_queues_one_attack_against_adjacent_second_target() -> None:
    service = PlayerCombatActionFlowService()
    ranger = replace(
        _actor("ranger", Faction.ALLY, Coordinate(0, 0)),
        features=(
            FeatureGrant(
                "horde_breaker",
                "Horde Breaker",
                FeatureSourceKind.SUBCLASS,
                "hunter",
            ),
        ),
    )
    first = _actor("first", Faction.ENEMY, Coordinate(1, 0))
    second = _actor("second", Faction.ENEMY, Coordinate(1, 1))
    state = _state(ranger, first, second)
    selected = service.select_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        position=first.position,
        active_effects=(),
    )
    confirmed = service.confirm_attack_target(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=selected.pending,
        active_effects=(),
        rng=Random(1),
    )
    rolled = service.submit_attack_roll(
        state=state,
        board=BoardState(),
        source=_source(),
        pending=confirmed.pending,
        active_effects=(),
        natural_roll=1,
    )

    assert rolled.state.turn_action.bonus_attacks_remaining == 1
    assert any(
        effect.kind == "horde_breaker_pending"
        for effect in rolled.active_effects
    )
    second_selected = service.select_attack_target(
        state=rolled.state,
        board=BoardState(),
        source=_source(),
        position=second.position,
        active_effects=rolled.active_effects,
        class_bonus_attack=True,
    )
    second_confirmed = service.confirm_attack_target(
        state=rolled.state,
        board=BoardState(),
        source=_source(),
        pending=second_selected.pending,
        active_effects=rolled.active_effects,
        rng=Random(1),
    )
    second_roll = service.submit_attack_roll(
        state=rolled.state,
        board=BoardState(),
        source=_source(),
        pending=second_confirmed.pending,
        active_effects=rolled.active_effects,
        natural_roll=1,
    )

    assert second_roll.state.turn_action.bonus_attacks_remaining == 0
    assert any(
        effect.kind == "horde_breaker_used"
        for effect in second_roll.active_effects
    )
