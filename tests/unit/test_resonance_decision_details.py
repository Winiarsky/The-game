"""Attack explanations and physical dice preserve the existing combat rules."""
from copy import deepcopy
from dataclasses import asdict, replace

import pytest

from dnd_board_game.application.resonance_combat import charge_weapon
from dnd_board_game.combat.charge_encounter import ChargeEncounter
from dnd_board_game.combat.mission_effects import road_fatigue
from dnd_board_game.combat.scene_interactions import attack_source_with_combat_effects
from dnd_board_game.inventory import InventoryItem
from dnd_board_game.rules.resonance import ChargeState, ChargeWeapon
from dnd_board_game.scenarios.loader import compile_actor_combat_content
from dnd_board_game.world import Coordinate
from dnd_board_game.world.terrain import BLOCKING_TERRAIN
from tests.unit.test_rune_relations_combat import game, memory


@pytest.mark.parametrize("hero,ability,expected,damage", (
    ("garran", "Siła", 4, 4),
    ("brakka", "Siła", 4, 4),
    ("mira", "Zręczność", 4, 4),
    ("dagna", "Siła", 1, 1),
    ("lorian", "Zręczność", 2, 2),
    ("nimra", "Siła", -1, -1),
    ("erynd", "Zręczność", 5, 4),
))
def test_all_starter_attacks_show_ability_and_existing_passives(
    hero: str, ability: str, expected: int, damage: int,
) -> None:
    e = game(hero)
    if hero == "lorian":
        # The training fixture has a crossbow but no bolts; keep its ammo gate.
        actor = e.active
        bolt = InventoryItem("test_bolt", "Bełt", "ammunition", equipped=False, ammunition_type="bolt")
        e.update_actor(replace(actor, inventory=(*actor.inventory, bolt)))
    assert e.choose("attack") and e.select(e.actor("enemy0").position) and e.commit()
    task = e.s.task
    assert task["modifier"] == expected
    assert task["modifier_components"][0] == {"label": ability, "value": damage}
    assert sum(part["value"] for part in task["modifier_components"]) == expected
    assert e.weapons[hero].components[0]["modifier"] == damage
    assert e.s.die_value == 10


@pytest.mark.parametrize("hero", ("erynd", "brakka"))
def test_cart_fatigue_explains_plus_two_without_changing_the_bonus(hero: str) -> None:
    e = game(hero)
    a = e.actor(hero)
    source = next(s for s in compile_actor_combat_content(a).attack_sources
                  if any(i.id == s.source_item_id and i.equipped for i in a.inventory))
    source = attack_source_with_combat_effects(a, source, road_fatigue((hero,), 1, "Zmęczenie po wydobyciu wozu"))
    e.weapons[hero] = charge_weapon(a, source)
    e.fighter().moved = True  # Erynd moved before the reported first bow attack.
    assert e.choose("attack") and e.select(e.actor("enemy0").position) and e.commit()
    assert e.s.task["modifier"] == 2
    assert e.s.task["modifier_components"] == [
        {"label": "Zręczność" if hero == "erynd" else "Siła", "value": 4},
        {"label": "Zmęczenie po wydobyciu wozu", "value": -2},
    ]
    assert e.weapons[hero].components[0]["modifier"] == 2


def test_erynd_stationary_first_shot_and_later_shot_have_separate_breakdowns() -> None:
    e = game("erynd")
    for expected in (5, 4):
        e.attack_task(dict(actor="erynd", target="enemy0", power="attack"))
        roll = e.s.queue.pop(0)
        assert roll["modifier"] == expected
        assert any(part["label"].startswith("Czysty strzał") for part in roll["modifier_components"]) == (expected == 5)


def test_each_new_die_starts_at_midpoint_but_saved_input_is_preserved() -> None:
    e = game()
    task = e.dice_task("Dwie różne kości", "garran", 1, 8, "charges", target="garran")
    task["parts"].append(dict(count=1, sides=6, label="Druga kość"))
    e.s.queue.append(task)
    e.advance()
    assert e.s.die_value == 4
    e.s.die_value = 7
    saved = ChargeState.from_payload(e.s.as_payload(), set(e.actors))
    restored = ChargeEncounter(replace(e.combat_state(), resonance=saved), e.board, e.catalog, e.weapons)
    assert restored.s.die_value == 7
    assert restored.submit_die(7, 0)
    assert restored.s.die_value == 3
    assert restored.s.task["dice_results"] == [7]
    assert not restored.submit_die(7, 0)
    assert restored.s.die_value == 3


@pytest.mark.parametrize("action", ("attack", "hunters_mark"))
def test_occluded_targets_remain_inspectable_but_cannot_be_selected(action: str) -> None:
    e = game("erynd")
    e.update_actor(replace(e.actor("enemy0"), position=Coordinate(8, 3)))
    e.board.set_terrain(Coordinate(5, 3), BLOCKING_TERRAIN)
    assert e.choose(action)
    before = deepcopy(e.s.as_payload())
    assert "enemy0" in e.target_candidates()
    assert "enemy0" not in e.legal_targets()
    assert e.target_rejection("enemy0") == "Przeszkoda zasłania linię widzenia do celu."
    assert not e.select(e.actor("enemy0").position)
    assert e.s.as_payload() == before
    assert e.target_rejection("enemy1") == ""


def test_target_reasons_distinguish_range_faction_and_defeat() -> None:
    e = game("erynd", ("garran",))
    e.update_actor(replace(e.actor("enemy0"), position=Coordinate(17, 3)))
    assert e.choose("hunters_mark")
    assert "poza zasięgiem" in e.target_rejection("enemy0")
    assert "przeciwnika" in e.target_rejection("garran")
    e.update_actor(replace(e.actor("enemy1"), hp=0))
    assert "pokonany" in e.target_rejection("enemy1")
    assert e.target_candidates() == ["enemy0"]


@pytest.mark.parametrize("hero,action", (("erynd", "move"), ("erynd", "skirmish_shot"), ("nimra", "flame_fan"), ("brakka", "rage")))
def test_field_and_area_actions_do_not_offer_creature_rejections(hero: str, action: str) -> None:
    e = game(hero)
    if action == "flame_fan":
        memory(e, "Oko", "Węzeł")
    assert e.choose(action)
    assert e.target_candidates() == []


def test_old_pending_weapon_payload_still_loads_without_breakdown() -> None:
    weapon = game("erynd").weapons["erynd"]
    saved = asdict(weapon)
    saved.pop("attack_modifiers")
    restored = ChargeWeapon(**saved)
    assert restored.attack_bonus == weapon.attack_bonus
    assert restored.attack_modifiers == ()
