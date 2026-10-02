"""The rune engine uses the existing terrain and line-of-effect cover rules."""
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.combat.charge_encounter import ChargeEncounter
from dnd_board_game.combat.scene import SceneObject
from dnd_board_game.inventory.armor import effective_armor_class
from dnd_board_game.rules.resonance import ChargeState
from dnd_board_game.ui import resonance
from dnd_board_game.world import Coordinate
from tests.unit.test_mission_zero import session, start_battle
from tests.unit.test_rune_relations_combat import game, memory


def cover_object(position: Coordinate, *, bonus: int = 2, projectile: int = 0, name: str = "Niski murek") -> SceneObject:
    return SceneObject(name, name, (position,), "", cover_bonus=bonus, projectile_cover_bonus=projectile)


def test_actual_borut_cover_survives_rebuilding_the_engine_and_ends_on_leaving(tmp_path: Path) -> None:
    s = start_battle(session(tmp_path, legacy_combat=False))
    e = resonance.engine(s)
    assert e.actor("borut").ac == 13
    assert e.ac("borut") == 13
    e.update_actor(replace(e.actor("borut"), position=Coordinate(8, 13)))
    assert e.ac("borut") == 15
    assert e.cover("borut").cover_sources == ("Niski murek",)
    view = resonance.actor_view(e, "borut")
    assert view["ac"] == 15 and view["cover_bonus"] == 2
    assert "Osłona terenu · +2 KP · Niski murek" in view["statuses"]
    s.combat_state = e.combat_state()
    rebuilt = resonance.engine(s)
    assert rebuilt.ac("borut") == 15
    rebuilt.update_actor(replace(rebuilt.actor("borut"), position=Coordinate(9, 13)))
    assert rebuilt.ac("borut") == 13
    assert resonance.actor_view(rebuilt, "borut")["cover_bonus"] == 0


@pytest.mark.parametrize("target,attacker", (("garran", "enemy0"), ("enemy0", "garran")))
def test_defensive_field_changes_player_and_enemy_attack_dc(target: str, attacker: str) -> None:
    e = game("garran")
    base_ac = e.ac(target)
    e.scene_objects = (cover_object(e.actor(target).position),)
    e.attack_task(dict(actor=attacker, target=target, power="attack"))
    roll = e.s.queue[0]
    assert e.ac(target) == base_ac+2
    assert roll["dc"] == base_ac+2
    assert roll["cover_bonus"] == 2 and roll["cover_sources"] == ["Niski murek"]


def test_player_attack_misses_when_cover_raises_armor_above_the_total() -> None:
    e = game("garran")
    e.scene_objects = (cover_object(e.actor("enemy0").position),)
    assert e.choose("attack") and e.select(e.actor("enemy0").position) and e.commit()
    assert e.s.task["dc"] == 14
    assert resonance.decision(e)["cover_text"] == "Osłona: +2 KP celu · Niski murek"
    assert e.submit_die(9, 0)  # 9 + Strength 4 would hit the uncovered AC 12.
    assert e.actor("enemy0").hp == 100
    assert any("13 / ST 14 · porażka" in message for message in e.s.history)
    assert e.s.task is None


def test_strongest_line_or_field_cover_is_used_without_stacking() -> None:
    e = game("erynd")
    e.update_actor(replace(e.actor("enemy0"), position=Coordinate(8, 3)))
    e.scene_objects = (
        cover_object(Coordinate(8, 3), name="Worki"),
        cover_object(Coordinate(5, 3), bonus=0, projectile=5, name="Blanki"),
    )
    assert e.ac("enemy0") == 14
    assert e.ac("enemy0", e.active.position) == 17
    e.attack_task(dict(actor="erynd", target="enemy0", power="attack"))
    assert e.s.queue[0]["dc"] == 17
    assert e.s.queue[0]["cover_sources"] == ["Blanki"]
    e.scene_objects = (*e.scene_objects, cover_object(Coordinate(8, 3), bonus=5, name="Wieża"))
    assert e.ac("enemy0", e.active.position) == 17
    assert e.cover("enemy0", e.active.position).cover_sources == ("Blanki", "Wieża")


def test_intervening_creature_gives_cover_only_from_that_attack_line() -> None:
    e = game("erynd")
    e.update_actor(replace(e.actor("enemy0"), position=Coordinate(8, 3)))
    e.update_actor(replace(e.actor("enemy1"), position=Coordinate(5, 3)))
    assert e.ac("enemy0") == 12
    assert e.ac("enemy0", e.active.position) == 14
    assert e.cover("enemy0", e.active.position).cover_sources == ("Wróg 1",)
    e.update_actor(replace(e.actor("enemy1"), position=Coordinate(5, 4)))
    assert e.ac("enemy0", e.active.position) == 12


@pytest.mark.parametrize("ability,expected", (("dexterity", 2), ("strength", 0), ("wisdom", 0)))
def test_projectile_cover_modifies_only_dexterity_saves(ability: str, expected: int) -> None:
    e = game("erynd")
    e.update_actor(replace(e.actor("enemy0"), position=Coordinate(8, 3)))
    e.scene_objects = (cover_object(Coordinate(5, 3), bonus=0, projectile=2),)
    e.s.queue.append(e.save_task("enemy0", ability, 14, dict(kind="root", source="erynd")))
    e.advance()
    assert e.s.task["modifier"] == e.ability("enemy0", ability)+expected
    assert e.s.task["cover_bonus"] == expected
    if expected:
        assert resonance.decision(e)["cover_text"] == "Osłona: +2 do obrony · Niski murek"


def test_defensive_spot_alone_does_not_add_to_saves_under_existing_rules() -> None:
    e = game("erynd")
    e.scene_objects = (cover_object(e.actor("enemy0").position),)
    e.s.queue.append(e.save_task("enemy0", "dexterity", 14, dict(kind="root", source="erynd")))
    e.advance()
    assert e.s.task["modifier"] == e.ability("enemy0", "dexterity")
    assert e.s.task["cover_bonus"] == 0


def test_area_save_cover_uses_the_area_center_instead_of_the_caster() -> None:
    e = game("nimra")
    e.update_actor(replace(e.actor("enemy0"), position=Coordinate(8, 3)))
    e.scene_objects = (cover_object(Coordinate(5, 3), bonus=0, projectile=2),)
    memory(e, "Oko", "Węzeł")
    assert e.choose("flame_fan") and e.select(Coordinate(8, 4)) and e.exclude(None) and e.commit()
    for index in range(4):
        assert e.submit_die(1, index)
    assert e.s.task["outcome"] == "save"
    assert e.s.task["effect"]["origin"] == [8, 4]
    assert e.s.task["cover_bonus"] == 0


def test_snapshot_keeps_pending_attack_dc_and_recomputes_current_field_cover() -> None:
    e = game("garran")
    e.scene_objects = (cover_object(e.actor("enemy0").position),)
    assert e.choose("attack") and e.select(e.actor("enemy0").position) and e.commit()
    state = ChargeState.from_payload(e.s.as_payload(), set(e.actors))
    restored = ChargeEncounter(replace(e.combat_state(), resonance=state), e.board, e.catalog, e.weapons,
                               scene_objects=e.scene_objects)
    assert restored.s.task["dc"] == 14
    assert restored.s.task["cover_sources"] == ["Niski murek"]
    assert restored.actor("enemy0").ac == effective_armor_class(e.actor("enemy0")) == 12
    assert restored.ac("enemy0") == 14
