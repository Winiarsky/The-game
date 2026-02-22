from __future__ import annotations

from bonuses import compute_total_modifier
from hero import Hero
from skills import Skill
from GameObjects.Enemies.basic_enemy import BasicEnemy
from GameObjects.events.attack.basic_melee_attack_event import BasicMeleeAttackEvent
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll
from statuses.clumsy import (
    ClumsyStatus,
    clumsy_ac_penalty,
    clumsy_reflex_penalty,
    clumsy_ranged_penalty,
    clumsy_finesse_penalty,
    clumsy_stealth_penalty,
    clumsy_ac_penalty_effect,
    clumsy_attack_penalty_effects,
)


class DummyActor:
    def __init__(self, statuses):
        self.statuses = statuses


def test_clumsy_penalty_helpers_pick_highest():
    actor = DummyActor(
        [
            ClumsyStatus(ac_penalty=1, reflex_penalty=2, ranged_penalty=1, finesse_penalty=0, stealth_penalty=1),
            ClumsyStatus(ac_penalty=3, reflex_penalty=1, ranged_penalty=2, finesse_penalty=4, stealth_penalty=2),
        ]
    )
    assert clumsy_ac_penalty(actor) == 3
    assert clumsy_reflex_penalty(actor) == 2
    assert clumsy_ranged_penalty(actor) == 2
    assert clumsy_finesse_penalty(actor) == 4
    assert clumsy_stealth_penalty(actor) == 2


def test_clumsy_reflex_penalty_auto_for_enemy_prompt_only_for_hero():
    hero = Hero(statuses=[ClumsyStatus(reflex_penalty=2)])
    res_hero = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.REFLEX.value,
        dc=10,
        actor=hero,
        tags=[Skill.REFLEX.value],
        roll=10,
        apply_modifiers=True,
    )
    assert res_hero.modifier == 0

    enemy = BasicEnemy(statuses=[ClumsyStatus(reflex_penalty=2)])
    res_enemy = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.REFLEX.value,
        dc=10,
        actor=enemy,
        tags=[Skill.REFLEX.value],
        roll=10,
        apply_modifiers=True,
    )
    assert res_enemy.modifier == -2


def test_clumsy_stealth_penalty_applies_to_skill_check():
    hero = Hero(statuses=[ClumsyStatus(stealth_penalty=2)])
    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.STEALTH.value,
        dc=10,
        actor=hero,
        tags=[Skill.STEALTH.value],
        roll=10,
        apply_modifiers=True,
    )
    assert res.modifier == -2


def test_clumsy_attack_penalties_apply_to_ranged_and_finesse():
    hero = Hero(statuses=[ClumsyStatus(ranged_penalty=2, finesse_penalty=1)])
    effects_ranged = clumsy_attack_penalty_effects(
        hero,
        action_tag="attack_ranged",
        is_ranged=True,
        is_finesse=False,
    )
    assert compute_total_modifier(effects_ranged, "attack_ranged") == -2

    effects_finesse = clumsy_attack_penalty_effects(
        hero,
        action_tag="attack_melee",
        is_ranged=False,
        is_finesse=True,
    )
    assert compute_total_modifier(effects_finesse, "attack_melee") == -1


def test_clumsy_ac_penalty_effect_lowers_target_ac():
    enemy = BasicEnemy(ac=15, statuses=[ClumsyStatus(ac_penalty=2)])
    event = BasicMeleeAttackEvent()
    extra = clumsy_ac_penalty_effect(enemy)
    target_ac, _base, _mod = event._ac_with_bonuses(
        enemy,
        attacker=None,
        extra_bonuses=[extra] if extra else None,
    )
    assert target_ac == 13
