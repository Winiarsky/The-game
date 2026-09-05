from dataclasses import replace

from dnd_board_game.actors import Actor, ActorId, Faction, FeatureGrant, FeatureSourceKind
from dnd_board_game.combat.archetype_flaws import (
    attack_source_with_exposed_mira_bonus,
    dynamic_flaw_activations,
    flaw_ability_check_modifiers,
    flaw_attack_roll_modifiers,
    flaw_blocks_equipment_use,
    flaw_saving_throw_modifiers,
    synchronize_dynamic_flaw_effects,
)
from dnd_board_game.combat import AttackKind, AttackSource, AttackSourceType
from dnd_board_game.combat.conditions import CombatCondition, ConditionState
from dnd_board_game.combat.stealth import HiddenState
from dnd_board_game.rules import ActiveEffect, D20RollRequest, RollMode
from dnd_board_game.world import Coordinate


def _actor(actor_id: str, position: Coordinate, *, feature_id: str = "", hp: int = 10) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id.title(),
        ac=14,
        hp=hp,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=Faction.ALLY,
        uses_death_saves=True,
        features=(
            FeatureGrant(
                feature_id,
                feature_id,
                FeatureSourceKind.SCENARIO,
                "test",
            ),
        ) if feature_id else (),
    )


def test_garran_remorse_activates_only_when_he_took_the_least_damage() -> None:
    garran = _actor("garran", Coordinate(0, 0), feature_id="flaw_remorse")
    ally = _actor("ally", Coordinate(3, 0))

    active = dynamic_flaw_activations((garran, ally), (), (("garran", 2), ("ally", 5)))
    tied = dynamic_flaw_activations((garran, ally), (), (("garran", 5), ("ally", 5)))

    assert [(item.actor_id, item.kind, item.value) for item in active] == [
        ("garran", "flaw_remorse_active", -2)
    ]
    assert tied == ()


def test_dagna_triage_tracks_visible_downed_ally() -> None:
    dagna = _actor("dagna", Coordinate(0, 0), feature_id="flaw_leave_no_one")
    ally = _actor("ally", Coordinate(4, 0), hp=0)

    assert {item.kind for item in dynamic_flaw_activations((dagna, ally))} == {
        "flaw_triage_active"
    }


def test_brakka_flaw_blocks_equipment_only_during_rage() -> None:
    brakka = _actor("brakka", Coordinate(0, 0), feature_id="flaw_chains")
    enemy = replace(_actor("enemy", Coordinate(1, 0)), faction=Faction.ENEMY)
    grapple = ConditionState(
        "brakka",
        CombatCondition.GRAPPLED,
        source_actor_id="enemy",
    )

    rage = ActiveEffect(
        id="rage:brakka",
        actor_id="brakka",
        kind="rage",
        label="Szał",
        object_id="class_feature:rage",
        value=2,
    )

    assert dynamic_flaw_activations((brakka, enemy), (grapple,)) == ()
    assert flaw_blocks_equipment_use(brakka, ()) is False
    assert flaw_blocks_equipment_use(brakka, (rage,)) is True


def test_synchronization_exposes_remorse_penalty_to_every_d20_category() -> None:
    garran = _actor("garran", Coordinate(0, 0), feature_id="flaw_remorse")
    ally = _actor("ally", Coordinate(3, 0))

    effects = synchronize_dynamic_flaw_effects(
        (garran, ally), (), (), (("garran", 0), ("ally", 4))
    )
    save_modifiers = flaw_saving_throw_modifiers(garran, effects)
    attack_modifiers = flaw_attack_roll_modifiers(garran, effects)
    check_modifiers = flaw_ability_check_modifiers(garran, effects)
    inactive = synchronize_dynamic_flaw_effects(
        (garran, ally), (), effects, (("garran", 4), ("ally", 4))
    )

    assert [(item.label, item.value) for item in save_modifiers] == [("Wyrzuty sumienia", -2)]
    assert attack_modifiers == save_modifiers
    assert check_modifiers == save_modifiers
    assert all(effect.kind != "flaw_remorse_active" for effect in inactive)


def test_erynd_trauma_is_target_specific_and_only_counts_conscious_player_allies() -> None:
    from dnd_board_game.combat.scene_interactions import (
        attack_source_with_combat_effects, attack_source_with_target_combat_effects,
    )

    erynd = _actor("erynd", Coordinate(0, 0), feature_id="flaw_friendly_fire_trauma")
    near_archer = _actor("near_archer", Coordinate(1, 0))
    target = replace(_actor("target", Coordinate(8, 8)), faction=Faction.ENEMY)
    clear_target = replace(target, id=ActorId("clear_target"), position=Coordinate(12, 8))
    ally = _actor("ally", Coordinate(7, 8))
    diagonal = _actor("diagonal", Coordinate(9, 9))
    downed = _actor("downed", Coordinate(8, 7), hp=0)
    asleep = _actor("asleep", Coordinate(8, 9))
    summon = replace(_actor("summon", Coordinate(9, 8)), uses_death_saves=False)
    actors = (erynd, near_archer, target, clear_target, ally, diagonal, downed, asleep, summon)
    conditions = (ConditionState("asleep", CombatCondition.UNCONSCIOUS),)
    effects = synchronize_dynamic_flaw_effects(actors, conditions, ())
    bow = AttackSource(
        "Długi łuk", AttackSourceType.WEAPON, 75, D20RollRequest(),
        source_item_id="longbow", attack_kind=AttackKind.RANGED,
    )
    knife = replace(bow, source_item_id="hunting_knife", attack_kind=AttackKind.MELEE)
    spell = replace(bow, source_type=AttackSourceType.SPELL)

    assert len(effects) == 1
    assert effects[0].target_actor_id == "target"
    assert effects[0].value == -2
    assert flaw_attack_roll_modifiers(erynd, effects, bow) == ()
    assert flaw_attack_roll_modifiers(erynd, effects, bow, target=clear_target) == ()
    assert flaw_attack_roll_modifiers(erynd, effects, knife, target=target) == ()
    assert flaw_attack_roll_modifiers(erynd, effects, spell, target=target) == ()
    assert [m.value for m in attack_source_with_target_combat_effects(
        erynd, target, bow, effects
    ).attack_roll_request.modifiers] == [-2]
    assert attack_source_with_combat_effects(erynd, bow, effects) == bow
    assert attack_source_with_target_combat_effects(erynd, clear_target, bow, effects) == bow

    # Changing positions recalculates the penalty and removes stale saved effects.
    moved = tuple(replace(a, position=Coordinate(15, 15)) if a.id in {"ally", "diagonal"} else a for a in actors)
    legacy = replace(effects[0], target_actor_id=None)
    assert synchronize_dynamic_flaw_effects(moved, conditions, (legacy, *effects)) == ()


def test_erynd_trauma_has_distinct_effect_ids_for_each_target() -> None:
    erynd = _actor("erynd", Coordinate(0, 0), feature_id="flaw_friendly_fire_trauma")
    ally = _actor("ally", Coordinate(5, 5))
    first = replace(_actor("first", Coordinate(4, 5)), faction=Faction.ENEMY)
    second = replace(first, id=ActorId("second"), position=Coordinate(6, 5))
    effects = synchronize_dynamic_flaw_effects((erynd, ally, first, second), (), ())
    assert {e.target_actor_id for e in effects} == {"first", "second"}
    assert len({e.id for e in effects}) == 2


def test_exposed_mira_flaw_benefits_only_an_enemy_who_sees_her_during_stealth() -> None:
    mira = _actor(
        "mira",
        Coordinate(0, 0),
        feature_id="flaw_exposed_panic",
    )
    enemy = replace(
        _actor("shadow", Coordinate(2, 0)),
        faction=Faction.ENEMY,
    )
    source = AttackSource(
        "Rozdarcie cienia",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
        attack_kind=AttackKind.MELEE,
    )
    hidden_from_enemy = HiddenState("mira", 18, ("shadow",))
    detected_by_enemy = HiddenState("mira", 18, ("other_enemy",))

    outside_stealth = attack_source_with_exposed_mira_bonus(
        (), enemy, mira, source
    )
    still_hidden = attack_source_with_exposed_mira_bonus(
        (hidden_from_enemy,), enemy, mira, source
    )
    exposed = attack_source_with_exposed_mira_bonus(
        (detected_by_enemy,), enemy, mira, source
    )

    assert outside_stealth == source
    assert still_hidden == source
    assert exposed.attack_roll_request.mode == RollMode.NORMAL
    assert [(modifier.label, modifier.value, modifier.stacking_key) for modifier in exposed.attack_roll_request.modifiers] == [
        (
            "Panika Miry po zdemaskowaniu",
            2,
            "flaw_exposed_panic_bonus",
        )
    ]
