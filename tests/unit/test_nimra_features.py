from dataclasses import replace

import pytest

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    ActorResourcePool,
    Faction,
    FeatureGrant,
    FeatureSourceKind,
    RecoveryPeriod,
)
from dnd_board_game.combat import AttackKind, AttackSource, AttackSourceType, DamageComponentSpec
from dnd_board_game.combat.nimra_features import (
    NIMRA_METAMAGIC_IDS,
    apply_nimra_metamagic,
    arcane_echo_block_reason,
    arcane_echo_effects,
    nimra_metamagic_compatibility_for_action,
    select_lightning_jump_target,
)
from dnd_board_game.core.damage_types import DamageType
from dnd_board_game.rules import D20RollRequest, DiceExpression
from dnd_board_game.world import Coordinate


def _feature(feature_id: str) -> FeatureGrant:
    return FeatureGrant(
        feature_id,
        feature_id,
        FeatureSourceKind.SCENARIO,
        "test",
        action_ids=(feature_id,),
        resource_ids=("metamagic_points",) if feature_id in NIMRA_METAMAGIC_IDS else (),
    )


def _actor(
    actor_id: str,
    faction: Faction,
    col: int,
    *,
    hp: int = 20,
    features: tuple[str, ...] = (),
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=12,
        hp=hp,
        max_hp=20,
        temp_hp=0,
        speed_feet=25,
        position=Coordinate(col, 0),
        faction=faction,
        ability_scores=AbilityScores(intelligence=19),
        features=tuple(_feature(item) for item in features),
        resource_pools=(
            ActorResourcePool(
                "metamagic_points",
                "Punkty Metamagii",
                4,
                4,
                RecoveryPeriod.LONG_REST,
            ),
        ),
    )


def _spell(*, area: bool = False, damage_type: DamageType = DamageType.FIRE) -> AttackSource:
    from dnd_board_game.combat import SpellArea, SpellAreaShape

    component = DamageComponentSpec(
        "base",
        damage_type,
        dice=DiceExpression(2, 6),
    )
    return AttackSource(
        "Testowy czar",
        AttackSourceType.SPELL,
        50,
        D20RollRequest(),
        id="test_spell",
        damage_hint=component.hint(),
        damage_die_sides=6,
        damage_type=damage_type.value,
        damage_components=(component,),
        save_ability="dexterity",
        save_dc=14,
        attack_kind=AttackKind.RANGED,
        area=SpellArea(SpellAreaShape.RADIUS, radius_feet=10) if area else None,
    )


def test_lightning_jump_uses_nearest_creature_even_when_it_is_an_ally() -> None:
    nimra = _actor("nimra", Faction.ALLY, 0)
    primary = _actor("primary", Faction.ENEMY, 6)
    ally = _actor("ally", Faction.ALLY, 7)
    farther_enemy = _actor("enemy", Faction.ENEMY, 8)

    jump = select_lightning_jump_target(nimra, primary, (nimra, primary, ally, farther_enemy))

    assert jump is not None
    assert (jump.target_id, jump.distance_feet, jump.is_enemy) == ("ally", 5, False)


def test_lightning_jump_prefers_enemy_only_when_distance_is_tied() -> None:
    nimra = _actor("nimra", Faction.ALLY, 0)
    primary = _actor("primary", Faction.ENEMY, 6)
    ally = _actor("ally", Faction.ALLY, 5)
    enemy_b = _actor("enemy_b", Faction.ENEMY, 7)
    enemy_a = _actor("enemy_a", Faction.ENEMY, 5)

    jump = select_lightning_jump_target(
        nimra,
        primary,
        (nimra, primary, ally, enemy_b, enemy_a),
    )

    assert jump is not None
    assert jump.target_id == "enemy_a"
    assert jump.is_enemy is True


def test_lightning_jump_stops_when_every_other_creature_is_invalid() -> None:
    nimra = _actor("nimra", Faction.ALLY, 0)
    primary = _actor("primary", Faction.ENEMY, 6)
    defeated = _actor("defeated", Faction.ENEMY, 7, hp=0)
    distant = _actor("distant", Faction.ENEMY, 10)

    assert select_lightning_jump_target(nimra, primary, (nimra, primary, defeated, distant)) is None


def test_nimra_metamagic_changes_preview_without_spending_pool() -> None:
    nimra = _actor(
        "nimra",
        Faction.ALLY,
        0,
        features=("nimra_distant_spell", "nimra_overcharged_spell", "nimra_energy_transmutation"),
    )
    source = _spell()

    distant = apply_nimra_metamagic(nimra, source, "nimra_distant_spell")
    overloaded = apply_nimra_metamagic(nimra, source, "nimra_overcharged_spell")
    cold = apply_nimra_metamagic(
        nimra,
        source,
        "nimra_energy_transmutation",
        transmuted_damage_type=DamageType.COLD,
    )

    assert distant.range_feet == 65
    assert distant.resource_pool_id == "metamagic_points"
    assert overloaded.damage_components[0].dice == DiceExpression(3, 6)
    assert cold.damage_components[0].damage_type == DamageType.COLD
    assert next(pool for pool in nimra.resource_pools if pool.id == "metamagic_points").current == 4


def test_nimra_allows_only_one_metamagic_and_rejects_invalid_transmutation() -> None:
    nimra = _actor(
        "nimra",
        Faction.ALLY,
        0,
        features=("nimra_distant_spell", "nimra_energy_transmutation"),
    )
    source = apply_nimra_metamagic(nimra, _spell(), "nimra_distant_spell")

    with pytest.raises(ValueError, match="tylko jedną"):
        apply_nimra_metamagic(nimra, source, "nimra_energy_transmutation", transmuted_damage_type=DamageType.COLD)
    with pytest.raises(ValueError, match="Wybierz kwas"):
        apply_nimra_metamagic(
            nimra,
            _spell(),
            "nimra_energy_transmutation",
            transmuted_damage_type=DamageType.FORCE,
        )


def test_overcharged_spell_rejects_non_damage_pool_dice() -> None:
    from dnd_board_game.scenarios.loader import ScenarioCombatActionDefinition

    nimra = _actor(
        "nimra",
        Faction.ALLY,
        0,
        features=("nimra_overcharged_spell",),
    )
    sleep = ScenarioCombatActionDefinition(
        id="nimra_sleep",
        name="Sen",
        action_type="targeted_status",
        label="Sen",
        damage_die_sides=8,
        hit_point_pool_dice_count=5,
    )

    allowed, reason = nimra_metamagic_compatibility_for_action(
        nimra,
        sleep,
        "nimra_overcharged_spell",
    )

    assert allowed is False
    assert "nie zadaje obrażeń" in reason


def test_arcane_echo_blocks_spell_and_metamagic_only_in_following_round() -> None:
    nimra = _actor("nimra", Faction.ALLY, 0, features=("flaw_arcane_echo",))
    effects = arcane_echo_effects(
        nimra,
        spell_id="nimra_lightning_path",
        metamagic_ids=("nimra_distant_spell",),
        round_number=2,
    )

    assert not arcane_echo_block_reason(nimra, effects, round_number=2, spell_id="nimra_lightning_path")
    assert "tego samego czaru" in arcane_echo_block_reason(
        nimra, effects, round_number=3, spell_id="nimra_lightning_path"
    )
    assert "Metamagii" in arcane_echo_block_reason(
        nimra, effects, round_number=3, metamagic_id="nimra_distant_spell"
    )
    assert not arcane_echo_block_reason(nimra, effects, round_number=4, spell_id="nimra_lightning_path")


def test_arcane_echo_normalizes_energy_transmutation_variant() -> None:
    nimra = _actor("nimra", Faction.ALLY, 0, features=("flaw_arcane_echo",))
    effects = arcane_echo_effects(
        nimra,
        spell_id="nimra_flame_fan",
        metamagic_ids=("nimra_energy_transmutation@cold",),
        round_number=4,
    )

    assert "Metamagii" in arcane_echo_block_reason(
        nimra,
        effects,
        round_number=5,
        metamagic_id="nimra_energy_transmutation",
    )
