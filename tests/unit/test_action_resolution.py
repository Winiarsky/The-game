import random
from dataclasses import replace

import pytest

from dnd_board_game.actions import (
    ActionResourceResolver,
    AreaSpellResolver,
    HealingActionResolver,
    SpellSaveAttackResolver,
)
from dnd_board_game.actors import AbilityScores, Actor, ActorId, DamageAffinityProfile, Faction
from dnd_board_game.combat import (
    AttackSource,
    AttackSourceType,
    DamageType,
    HealingSource,
    HealingSourceType,
    InitiativeEntry,
    InitiativeOrder,
    SpellSaveResult,
    SpellSlotState,
    start_combat,
    ActionEconomyCost,
    apply_healing_result,
    legal_healing_targets,
)
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    SpellCastingTime,
    SpellAccessKind,
    SpellAccessProfile,
    SpellComponents,
    SpellDefinition,
    SpellDuration,
    SpellDurationKind,
    SpellRange,
    SpellRangeKind,
    SpellSchool,
    resolve_d20_roll,
)
from dnd_board_game.world import BoardState, Coordinate


def _actor(actor_id: str, faction: Faction, col: int, *, hp: int = 10, max_hp: int = 10) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=hp,
        max_hp=max_hp,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(col, 0),
        faction=faction,
        ability_scores=AbilityScores(dexterity=10),
    )


def _order(*actors: Actor) -> InitiativeOrder:
    request = D20RollRequest()
    entries = []
    for index, actor in enumerate(actors):
        roll = resolve_d20_roll(D20RollInput(request, 20 - index))
        entries.append(InitiativeEntry(actor, roll, 0, index))
    return InitiativeOrder(tuple(entries))


def _state(*actors: Actor):
    return start_combat(tuple(actors), _order(*actors))


def _save(actor_id: str, *, success: bool, multiplier: float) -> SpellSaveResult:
    return SpellSaveResult(
        actor_id=actor_id,
        actor_name=actor_id,
        ability="dexterity",
        dc=13,
        natural_roll=17 if success else 5,
        modifier=0,
        total=17 if success else 5,
        success=success,
        damage_multiplier=multiplier,
    )


def _spell(spell_id: str, level: int) -> SpellDefinition:
    return SpellDefinition(
        id=spell_id,
        name=spell_id,
        level=level,
        school=SpellSchool.EVOCATION,
        casting_time=SpellCastingTime.ACTION,
        range=SpellRange(SpellRangeKind.DISTANCE, 30),
        components=SpellComponents(verbal=True),
        duration=SpellDuration(SpellDurationKind.INSTANTANEOUS),
        effect_kind="attack",
    )


def test_spell_save_attack_resolver_consumes_action_and_applies_damage():
    caster = replace(_actor("cleric", Faction.ALLY, 0), spell_save_dc=13)
    target = _actor("goblin", Faction.ENEMY, 1)
    state = _state(caster, target)
    source = AttackSource(
        "Święty płomień",
        AttackSourceType.SPELL,
        60,
        D20RollRequest(),
        damage_type="radiant",
        save_ability="dexterity",
        save_dc=99,
    )
    resolver = SpellSaveAttackResolver()

    confirmation = resolver.confirm_target_save_spell(state, caster=caster, target=target, source=source, rng=random.Random(3))
    damage = resolver.apply_target_damage(
        confirmation.state,
        target_id=str(target.id),
        source=source,
        base_damage=7,
        saving_throw=confirmation.saving_throw,
    )

    updated_target = next(actor for actor in damage.state.actors if actor.id == target.id)
    assert confirmation.state.turn_action.action_use.value == "action_used"
    assert confirmation.saving_throw.success is False
    assert damage.applied_damage.applied_to_hp == 7
    assert updated_target.hp == 3


def test_area_spell_resolver_applies_save_adjusted_damage_to_targets():
    caster = _actor("wizard", Faction.ALLY, 0)
    first = replace(
        _actor("goblin_a", Faction.ENEMY, 1),
        damage_affinities=DamageAffinityProfile(resistances=(DamageType.RADIANT,)),
    )
    second = _actor("goblin_b", Faction.ENEMY, 2)
    state = _state(caster, first, second)
    source = AttackSource(
        "Smuga światła",
        AttackSourceType.SPELL,
        30,
        D20RollRequest(),
        damage_type="radiant",
        save_ability="dexterity",
        save_damage_on_success="half",
    )
    resolver = AreaSpellResolver()

    result = resolver.apply_area_damage(
        state,
        source=source,
        target_ids=(str(first.id), str(second.id)),
        base_damage=9,
        saving_throws=(_save(str(first.id), success=True, multiplier=0.5), _save(str(second.id), success=False, multiplier=1.0)),
    )

    hp_by_id = {str(actor.id): actor.hp for actor in result.state.actors}
    assert hp_by_id[str(first.id)] == 8
    assert hp_by_id[str(second.id)] == 1
    assert [target.applied_damage.damage.total_applied for target in result.targets] == [2, 9]
    assert result.targets[0].applied_damage.damage.total_before_reduction == 4


def test_healing_action_resolver_consumes_spell_slot_and_caps_hp():
    healer = replace(
        _actor("cleric", Faction.ALLY, 0),
        spell_slots=(SpellSlotState(level=1, remaining=1, maximum=1),),
    )
    wounded = _actor("fighter", Faction.ALLY, 1, hp=4, max_hp=12)
    enemy = _actor("goblin", Faction.ENEMY, 2)
    state = _state(healer, wounded, enemy)
    source = HealingSource("healing_word", "Słowo leczenia", HealingSourceType.SPELL, 60, spell_level=1)
    resolver = HealingActionResolver()

    result = resolver.apply_healing(state, healer=healer, target_id=str(wounded.id), source=source, amount=20)

    updated_healer = next(actor for actor in result.state.actors if actor.id == healer.id)
    updated_wounded = next(actor for actor in result.state.actors if actor.id == wounded.id)
    assert result.state.turn_action.action_use.value == "action_used"
    assert updated_healer.spell_slots[0].remaining == 0
    assert updated_wounded.hp == 12
    assert result.applied_healing.effective_healing == 8


def test_bonus_action_spell_allows_only_an_action_cantrip_afterward() -> None:
    caster = replace(
        _actor("sorcerer", Faction.ALLY, 0),
        spells=(_spell("quickened_spell", 1), _spell("cantrip", 0)),
        spell_access=(
            SpellAccessProfile(
                SpellAccessKind.KNOWN,
                ("quickened_spell", "cantrip"),
            ),
        ),
        spell_slots=(SpellSlotState(level=1, remaining=2, maximum=2),),
    )
    enemy = _actor("enemy", Faction.ENEMY, 1)
    resolver = ActionResourceResolver()
    first = resolver.consume_action_and_source_resource(
        _state(caster, enemy),
        caster,
        spell_level=1,
        spell_id="quickened_spell",
        action_cost=ActionEconomyCost.BONUS_ACTION,
    )
    updated_caster = next(
        actor for actor in first.state.actors if actor.id == caster.id
    )

    with pytest.raises(ValueError, match="wyłącznie cantrip"):
        resolver.consume_action_and_source_resource(
            first.state,
            updated_caster,
            spell_level=1,
            spell_id="quickened_spell",
            action_cost=ActionEconomyCost.ACTION,
        )

    cantrip = resolver.consume_action_and_source_resource(
        first.state,
        updated_caster,
        spell_level=0,
        spell_id="cantrip",
        action_cost=ActionEconomyCost.ACTION,
    )

    assert cantrip.state.turn_action.bonus_action_spell_cast is True
    assert cantrip.state.turn_action.action_use.value == "action_used"


def test_leveled_action_spell_blocks_later_bonus_action_spell() -> None:
    caster = replace(
        _actor("sorcerer", Faction.ALLY, 0),
        spells=(_spell("leveled_spell", 1),),
        spell_access=(
            SpellAccessProfile(
                SpellAccessKind.KNOWN,
                ("leveled_spell",),
            ),
        ),
        spell_slots=(SpellSlotState(level=1, remaining=2, maximum=2),),
    )
    enemy = _actor("enemy", Faction.ENEMY, 1)
    resolver = ActionResourceResolver()
    first = resolver.consume_action_and_source_resource(
        _state(caster, enemy),
        caster,
        spell_level=1,
        spell_id="leveled_spell",
        action_cost=ActionEconomyCost.ACTION,
    )
    updated_caster = next(
        actor for actor in first.state.actors if actor.id == caster.id
    )

    with pytest.raises(ValueError, match="akcją bonusową"):
        resolver.consume_action_and_source_resource(
            first.state,
            updated_caster,
            spell_level=1,
            spell_id="leveled_spell",
            action_cost=ActionEconomyCost.BONUS_ACTION,
        )


def test_healing_spell_excludes_constructs_and_undead_in_domain_and_targeting() -> None:
    healer = _actor("cleric", Faction.ALLY, 0)
    living = replace(_actor("living", Faction.ALLY, 1, hp=2), creature_type="humanoid")
    undead = replace(_actor("undead", Faction.ALLY, 2, hp=2), creature_type="undead")
    source = HealingSource(
        "cure_wounds",
        "Leczenie ran",
        HealingSourceType.SPELL,
        15,
        excluded_creature_types=("construct", "undead"),
    )

    targets = legal_healing_targets(
        BoardState(),
        healer,
        (healer, living, undead),
        source,
    )
    blocked = apply_healing_result(undead, source, 8)

    assert {target.id for target in targets} == {"living"}
    assert blocked.effective_healing == 0
    assert blocked.actor_after.hp == 2
