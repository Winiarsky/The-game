from dataclasses import replace

from dnd_board_game.actors import Actor, ActorId, Faction, FeatureGrant, FeatureSourceKind
from dnd_board_game.combat.archetype_flaws import (
    dynamic_flaw_activations,
    flaw_blocks_equipment_use,
    flaw_saving_throw_modifiers,
    synchronize_dynamic_flaw_effects,
)
from dnd_board_game.combat.conditions import CombatCondition, ConditionState
from dnd_board_game.rules import ActiveEffect
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


def test_garran_guilt_activates_for_distant_downed_ally_and_breaks_when_adjacent() -> None:
    garran = _actor("garran", Coordinate(0, 0), feature_id="flaw_command_guilt")
    ally = _actor("ally", Coordinate(3, 0), hp=0)

    active = dynamic_flaw_activations((garran, ally))
    adjacent = dynamic_flaw_activations((replace(garran, position=Coordinate(2, 0)), ally))

    assert [(item.actor_id, item.kind, item.value) for item in active] == [
        ("garran", "flaw_command_guilt_active", -1)
    ]
    assert adjacent == ()


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


def test_synchronization_replaces_dynamic_effects_and_exposes_garran_save_penalty() -> None:
    garran = _actor("garran", Coordinate(0, 0), feature_id="flaw_command_guilt")
    ally = _actor("ally", Coordinate(3, 0), hp=0)

    effects = synchronize_dynamic_flaw_effects((garran, ally), (), ())
    modifiers = flaw_saving_throw_modifiers(garran, effects)
    healed = synchronize_dynamic_flaw_effects((garran, replace(ally, hp=1)), (), effects)

    assert [(item.label, item.value) for item in modifiers] == [("Wina dowódcy", -1)]
    assert all(not effect.kind.startswith("flaw_command_guilt") for effect in healed)
