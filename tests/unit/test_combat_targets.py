from dataclasses import replace

from dnd_board_game.actors import (
    Actor,
    ActorId,
    Faction,
    FeatureGrant,
    FeatureSourceKind,
)
from dnd_board_game.combat import (
    CombatTarget,
    CombatTargetType,
    CombatTargetVisibility,
    actor_as_combat_target,
    is_public_attack_target,
)
from dnd_board_game.world import Coordinate


def _actor(hp: int = 10) -> Actor:
    return Actor(
        id=ActorId("goblin"),
        name="Goblin",
        ac=13,
        hp=hp,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(1, 0),
        faction=Faction.ENEMY,
    )


def test_actor_enemy_maps_to_public_combat_target():
    target = actor_as_combat_target(_actor())

    assert target.id == "goblin"
    assert target.target_type == CombatTargetType.ACTOR
    assert is_public_attack_target(target) is True


def test_defeated_actor_is_not_public_attack_target():
    target = actor_as_combat_target(_actor(hp=0))

    assert target.attackable is False
    assert is_public_attack_target(target) is False


def test_attackable_false_and_hidden_visibility_block_targeting():
    object_with_hp = CombatTarget(
        id="table",
        name="Stół",
        position=Coordinate(2, 2),
        ac=10,
        hp=10,
        target_type=CombatTargetType.OBJECT,
        attackable=False,
    )
    hidden = CombatTarget(
        id="secret",
        name="Ukryty mechanizm",
        position=Coordinate(3, 3),
        ac=10,
        hp=10,
        target_type=CombatTargetType.INTERACTABLE,
        visibility=CombatTargetVisibility.HIDDEN,
    )
    conditional = CombatTarget(
        id="later",
        name="Warunkowy cel",
        position=Coordinate(4, 4),
        ac=10,
        hp=10,
        target_type=CombatTargetType.INTERACTABLE,
        visibility=CombatTargetVisibility.CONDITIONAL,
    )

    assert is_public_attack_target(object_with_hp) is False
    assert is_public_attack_target(hidden) is False
    assert is_public_attack_target(conditional) is False


def test_iron_line_protects_only_the_ally_opposite_garran() -> None:
    enemy = _actor()
    ally = replace(
        _actor(),
        id=ActorId("ally"),
        faction=Faction.ALLY,
        position=Coordinate(0, 0),
    )
    garran = replace(
        ally,
        id=ActorId("garran"),
        position=Coordinate(2, 0),
        features=(
            FeatureGrant(
                "iron_line",
                "Żelazna linia",
                FeatureSourceKind.SCENARIO,
                "test",
            ),
        ),
    )

    protected = actor_as_combat_target(
        ally,
        attacker=enemy,
        actors=(enemy, ally, garran),
    )
    broken_flank = actor_as_combat_target(
        ally,
        attacker=enemy,
        actors=(enemy, ally, replace(garran, position=Coordinate(2, 1))),
    )

    assert protected.ac == ally.ac + 1
    assert broken_flank.ac == ally.ac


def test_halfling_nimbleness_adds_ac_only_against_opportunity_attack() -> None:
    mira = replace(
        _actor(),
        id=ActorId("mira"),
        faction=Faction.ALLY,
        features=(
            FeatureGrant(
                "halfling_nimbleness",
                "Niziołcza zwinność",
                FeatureSourceKind.SPECIES,
                "halfling",
            ),
        ),
    )

    assert actor_as_combat_target(mira).ac == mira.ac
    assert actor_as_combat_target(mira, opportunity_attack=True).ac == mira.ac + 1
