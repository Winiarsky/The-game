"""Runtime card mechanics, interrupted queues and per-die input."""
from dataclasses import replace

import pytest

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.application.resonance_combat import apply_charge_profile, charge_weapon
from dnd_board_game.combat.charge_encounter import ChargeEncounter, hymn_source
from dnd_board_game.combat.initiative import InitiativeEntry, InitiativeOrder
from dnd_board_game.combat.session import CombatState
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.rules.resonance import ChargeActorState, ChargeState, ChargeWeapon
from dnd_board_game.scenarios.loader import compile_actor_combat_content
from dnd_board_game.scenarios.rune_charge_catalog import load_rune_charge_catalog
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.world import BoardState, Coordinate


def game(hero: str = "garran", companions: tuple[str, ...] = ()) -> ChargeEncounter:
    heroes = tuple(replace(apply_charge_profile(training_hero(h)), position=Coordinate(3+i, 3)) for i, h in enumerate((hero, *companions)))
    enemies = tuple(Actor(ActorId(f"enemy{i}"), f"Wróg {i}", 12, 100, 0, 30, Coordinate(4+i, 4), Faction.ENEMY) for i in range(2))
    actors = (*heroes, *enemies)
    roll = resolve_d20_roll(D20RollInput(D20RollRequest(), 10))
    order = InitiativeOrder(tuple(InitiativeEntry(a, roll, 0, i) for i, a in enumerate(actors)))
    state = CombatState(actors, order, resonance=ChargeState(order=[str(a.id) for a in actors], fighters={str(a.id): ChargeActorState() for a in actors}))
    weapons = {str(a.id): charge_weapon(a, next(s for s in compile_actor_combat_content(a).attack_sources if any(i.id == s.source_item_id and i.equipped for i in a.inventory))) for a in heroes}
    weapons.update({str(a.id): ChargeWeapon("spear", "Włócznia", "strength", "melee", 1,
        (dict(count=1, sides=6, modifier=2, damage_type="piercing", label="Włócznia"),), 2) for a in enemies})
    engine = ChargeEncounter(state, BoardState(), load_rune_charge_catalog(), weapons)
    engine.begin_turn()
    return engine


def cast(e: ChargeEncounter, card: str, target: str | None = None, enhanced: bool = False) -> None:
    assert e.choose(card)
    if enhanced:
        assert e.mode("enhanced")
    if target:
        assert e.select(e.actor(target).position)
    assert e.commit()


def dice(e: ChargeEncounter, value: int) -> None:
    assert e.submit_die(value, len(e.s.task.get("dice_results", [])))


def drain(e: ChargeEncounter) -> None:
    for _ in range(100):
        task = e.s.task
        if not task:
            if e.s.phase == "result":
                assert e.acknowledge()
            return
        if task["type"] == "roll":
            if e.actor(task["actor"]).faction == Faction.ENEMY:
                assert e.confirm_enemy_roll(lambda sides: 1)
            else:
                dice(e, 1)
        elif task["type"] == "recover":
            assert e.recover(False)
        elif task["type"] == "relocate":
            assert e.select(e.relocation_fields(task)[0])
            assert e.confirm_relocation()
        else:
            assert e.acknowledge()
    pytest.fail("Queue did not settle")


def test_individual_dice_cost_once_and_magic_component() -> None:
    e = game()
    cast(e, "breaking_strike", "enemy0", True)
    assert e.fighter().charges == 12
    dice(e, 20)
    assert [(p["count"], p["sides"]) for p in e.s.task["parts"]] == [(2, 8), (2, 6), (2, 4)]
    assert e.s.task["components"][1]["damage_type"] == "magic"
    before = e.actor("enemy0").hp
    dice(e, 3)
    assert e.actor("enemy0").hp == before
    assert not e.submit_die(3, 0)
    assert not e.commit()
    saved = ChargeState.from_payload(e.s.as_payload(), set(e.actors))
    restored = ChargeEncounter(replace(e.combat_state(), resonance=saved), e.board, e.catalog, e.weapons)
    for _ in range(5):
        dice(restored, 3)
    assert restored.actor("enemy0").hp == before-22
    assert restored.fighter().charges == 12


def test_brakka_critical_adds_two_weapon_dice_once() -> None:
    e = game("brakka")
    cast(e, "powerful_strike", "enemy0")
    dice(e, 20)
    assert e.s.task["components"][0]["count"] == e.weapons["brakka"].components[0]["count"]+2
    assert e.s.task["components"][0]["modifier"] == e.ability("brakka", "strength")


def test_live_shield_and_enemy_miss_recovery() -> None:
    from dnd_board_game.inventory.armor import effective_armor_class
    e = game("garran", ("mira",))
    assert e.shielded("mira") and not e.shielded("garran")
    assert e.ac("mira") == effective_armor_class(e.actor("mira"))+1
    e.fighter("garran").charges = 10
    e.s.queue.append(dict(type="attack", actor="enemy0", target="mira", power="opportunity", reaction_pending=True))
    e.advance()
    assert not e.submit_die(10, 0)
    assert e.confirm_enemy_roll(lambda sides: 1)
    assert e.s.task["type"] == "enemy-result"
    assert not e.fighter("enemy0").reaction
    assert e.fighter("garran").regeneration_reason


def test_chain_membership_wave_pools_and_no_refill() -> None:
    e = game("garran", ("mira",))
    e.add_rune("garran", "Kielich")
    e.add_rune("garran", "Fala")
    e.add_rune("garran", "Fala")
    assert e.counts() == {"Kielich": 3}
    assert e.fighter("garran").cup == 6 and e.fighter("mira").cup == 0
    e.damage("garran", [dict(value=4, damage_type="slashing")], "enemy0")
    e.join("garran")
    assert e.fighter("garran").cup == 2
    e.join("mira")
    assert e.fighter("mira").cup == 6
    e.end_chain("test")
    assert all(f.cup == 0 for f in e.s.fighters.values())


def test_rage_resistance_and_shield_psychic_bypass() -> None:
    e = game("brakka")
    e.add_status("brakka", "rage", remaining=5)
    e.add_rune("brakka", "Klepsydra")
    loss = e.damage("brakka", [dict(value=4, damage_type="piercing")], "enemy0")
    assert loss["received"] == 0 and not e.fighter().regeneration_reason
    e.add_rune("brakka", "Klepsydra")
    before = e.actor("brakka").hp
    e.damage("brakka", [dict(value=3, damage_type="psychic")], "enemy0")
    assert e.actor("brakka").hp == before-3 and e.fighter().shield == 2
    assert e.fighter().regeneration_reason


def test_bastion_charge_consumes_all_movement_and_uses_distance_dc() -> None:
    e = game()
    e.update_actor(replace(e.actor("enemy0"), position=Coordinate(7, 3)))
    e.update_actor(replace(e.actor("enemy1"), position=Coordinate(15, 20)))
    e.begin_turn()
    assert e.choose("bastion_charge") and e.select(e.actor("enemy0").position)
    path = e.s.preview["path"]["cells"]
    assert e.commit()
    assert e.movement() == 0
    assert e.s.task["dc"] == 10+e.ability("garran", "strength")+len(path)
    assert e.confirm_enemy_roll(lambda sides: 1)
    assert e.status("enemy0", "prone")
    drain(e)
    e.s.index = e.s.order.index("enemy0")
    e.begin_turn()
    assert e.movement() == 0 and e.fighter().ordinary and e.fighter().special


def test_parkour_crosses_obstacle_and_only_seen_enemies_react() -> None:
    e = game("mira")
    e.update_actor(replace(e.actor("enemy1"), position=Coordinate(7, 3)))
    e.fighter().hidden = ["enemy0", "enemy1"]
    assert e.choose("guard_vault") and e.select(e.actor("enemy1").position)
    assert Coordinate(8, 3) in e.available_fields()
    assert e.select(Coordinate(8, 3)) and e.commit()
    assert e.actor("mira").position == Coordinate(8, 3)
    assert e.fighter().base_spent == 0 and e.fighter().hidden == ["enemy0", "enemy1"]


def test_hymn_survives_turns_and_preserves_natural_failure() -> None:
    e = game("lorian", ("garran",))
    cast(e, "inspiration", "garran")
    drain(e)
    assert hymn_source(e.actor("garran")) == "lorian"
    assert e.end_turn()
    cast(e, "attack", "enemy0")
    dice(e, 1)
    assert e.s.task["type"] == "hymn"
    assert e.decide_hymn(True)
    dice(e, 6)
    assert not hymn_source(e.actor("garran"))
    assert e.actor("enemy0").hp == 100


def test_nimra_area_requires_explicit_exclusion_before_payment() -> None:
    e = game("nimra")
    assert e.choose("flame_fan")
    assert e.select(Coordinate(4, 4))
    assert not e.ready() and not e.commit()
    assert e.fighter().charges == 20
    assert e.exclude(None) and e.commit()
    dice(e, 4)
    assert e.actor("enemy0").hp == 100
    dice(e, 4)
    assert e.s.task["outcome"] == "save"


def test_recovery_is_optional_and_shared_once_per_round() -> None:
    e = game()
    e.fighter().charges = 8
    e.offer_regeneration("garran", "test")
    e.s.queue.append(dict(type="recover", actor="garran"))
    e.advance()
    assert e.recover(False)
    assert e.fighter().regeneration_round == 0
    e.offer_regeneration("garran", "test")
    e.s.queue.append(dict(type="recover", actor="garran"))
    e.advance()
    assert e.recover(True)
    dice(e, 4)
    assert e.fighter().charges == 12
    e.offer_regeneration("garran", "again")
    assert not e.fighter().regeneration_reason


@pytest.mark.parametrize("hero,card", [(hero, card["id"]) for hero, row in load_rune_charge_catalog()["heroes"].items() for card in row["cards"]])
def test_all_twenty_nine_cards_resolve_through_runtime_queue(hero: str, card: str) -> None:
    e = game(hero, ("garran" if hero != "garran" else "mira",))
    if card == "shadow_attack":
        e.fighter().hidden = ["enemy0"]
    assert e.choose(card)
    assert e.mode("enhanced")
    p = e.s.preview
    if card == "flame_fan":
        assert e.select(e.actor("enemy0").position)
    if card in {"force_wave", "flame_fan"}:
        assert e.exclude(None)
    if card == "guard_vault":
        assert e.select(e.actor("enemy0").position)
        assert e.select(e.available_fields()[0])
    if card in {"skirmish_shot", "misty_step"}:
        assert e.select(e.available_fields()[0])
    while not e.ready():
        targets = e.legal_targets()
        assert targets, card
        assert e.select(e.actor(targets[0]).position)
    assert e.commit()
    drain(e)
    assert e.s.phase == "idle"
    assert not e.fighter().special
    assert e.s.chain and len(e.s.chain.entries) == 1


def test_enemy_opportunity_result_is_frozen_until_acknowledged() -> None:
    e = game("mira")
    assert e.choose("move") and e.select(Coordinate(1, 3)) and e.commit()
    assert e.s.task["reaction_pending"]
    stopped = e.actor("mira").position
    rolls = []
    def roll(sides: int) -> int:
        rolls.append(sides)
        return 20 if sides == 20 else 2
    assert e.confirm_enemy_roll(roll)
    assert rolls == [20, 6, 6]
    saved = e.combat_state()
    restored = ChargeEncounter(saved, e.board, e.catalog, e.weapons)
    assert not restored.confirm_enemy_roll(roll)
    assert restored.actor("mira").position == stopped
    assert restored.s.task["rolls"] == e.s.task["rolls"]
    assert restored.acknowledge()
    assert restored.actor("mira").position == Coordinate(1, 3)


def test_lethal_reaction_requires_correction_and_stops_entire_path() -> None:
    e = game("mira")
    e.update_actor(replace(e.actor("mira"), hp=1))
    assert e.choose("move") and e.select(Coordinate(1, 3)) and e.commit()
    stopped = e.actor("mira").position
    assert e.confirm_enemy_roll(lambda sides: 20 if sides == 20 else 3)
    assert e.actor("mira").hp == 0
    assert e.acknowledge()
    assert e.s.task["type"] == "correction"
    assert e.actor("mira").position == stopped


def test_healing_circle_revives_unconscious_ally() -> None:
    e = game("dagna", ("mira",))
    e.update_actor(replace(e.actor("mira"), hp=0))
    cast(e, "preserve_life")
    dice(e, 4)
    assert e.actor("mira").hp == 6


def test_enemy_pack_heals_after_attack_and_life_drain() -> None:
    e = game()
    e.s.index = e.s.order.index("enemy0")
    e.begin_turn()
    e.update_actor(replace(e.active, hp=50))
    e.update_actor(replace(e.actor("enemy1"), hp=40))
    assert e.prepare_enemy_turn(target_id="garran", heal_target="enemy1", life_drain=True)
    assert e.s.task["outcome"] == "attack"
    assert e.confirm_enemy_roll(lambda sides: 19 if sides == 20 else 4)
    assert e.actor("enemy0").hp == 53
    assert e.actor("enemy1").hp == 40
    assert e.acknowledge()
    assert e.s.task["outcome"] == "heal"
    assert e.confirm_enemy_roll(lambda sides: 4)
    assert e.actor("enemy1").hp == 46


def test_enemy_spell_uses_hero_save_instead_of_attack_roll() -> None:
    e = game()
    weapon = replace(e.weapons["enemy0"], spell_save_ability="dexterity", spell_save_dc=10, spell_save_half=True)
    e.weapons["enemy0"] = weapon
    e.s.queue.append(dict(type="attack", actor="enemy0", target="garran", power="attack"))
    before = e.actor("garran").hp
    e.advance()
    assert e.s.task["outcome"] == "enemy_spell"
    assert e.confirm_enemy_roll(lambda sides: 4)
    assert e.actor("garran").hp == before
    assert e.acknowledge()
    assert e.s.task["outcome"] == "save" and e.s.task["actor"] == "garran"
    dice(e, 20)
    assert e.actor("garran").hp == before-3


def test_enemy_guard_stays_at_authored_position() -> None:
    e = game()
    e.s.index = e.s.order.index("enemy0")
    e.begin_turn()
    initial = e.active.position
    assert e.prepare_enemy_turn(target_id="garran", intent="guard")
    assert e.active.position == initial
    assert not e.s.task


def test_kielich_prevents_false_massive_damage_death() -> None:
    e = game()
    e.update_actor(replace(e.active, hp=1))
    e.fighter().cup = 20
    e.damage("garran", [dict(value=20+e.active.max_hp, damage_type="slashing")], "enemy0")
    assert e.active.hp == 0
    assert not e.active.death_saves.dead


def test_led_opportunity_focus_result_and_clear_on_resume() -> None:
    from dnd_board_game.hardware.resonance_feedback import resonance_feedback
    from dnd_board_game.hardware.board_session import BoardSessionAdapter
    from dnd_board_game.hardware.led_palette import LedColor
    from dnd_board_game.ui.resonance import presentation
    from tests.unit.test_initiative_panel import Board
    e, board = game(), Board()
    adapter = BoardSessionAdapter(board)
    e.s.queue.append(dict(type="opportunity", actor="enemy0", target="garran"))
    e.advance()
    def show() -> None:
        _, view = presentation(e)
        adapter.show_feedback(resonance_feedback(view))
    show()
    enemy = e.actor("enemy0").position.as_tuple()
    assert board.leds[enemy] == LedColor.ENEMY
    assert e.confirm_enemy_roll(lambda sides: 1)
    show()
    assert board.leds[enemy] == LedColor.ATTACK_MISS
    assert e.acknowledge()
    show()
    assert enemy not in board.leds


def test_movement_destination_led_is_blue_over_path() -> None:
    from dnd_board_game.hardware.resonance_feedback import resonance_feedback
    from dnd_board_game.hardware.led_feedback import BoardLedAdapter
    from dnd_board_game.hardware.led_palette import LedColor
    from dnd_board_game.ui.resonance import presentation
    from tests.unit.test_initiative_panel import Board
    e, board = game(), Board()
    assert e.choose("move")
    destination = Coordinate(2, 2)
    assert e.select(destination)
    _, view = presentation(e)
    BoardLedAdapter(board).show_feedback(resonance_feedback(view), replace=True)
    assert board.leds[destination.as_tuple()] == LedColor.SELECTED_ATTACK_TARGET


def test_unconscious_turn_does_not_break_another_heros_chain() -> None:
    e = game("garran", ("mira",))
    e.add_rune("garran", "Wieża")
    e.fighter().continued = True
    e.update_actor(replace(e.actor("mira"), hp=0))
    assert e.end_turn()
    assert e.active.id == "mira"
    dice(e, 10)
    assert e.end_turn()
    assert e.s.chain and e.counts() == {"Wieża": 1}


def test_enemy_damage_summary_includes_fixed_modifier() -> None:
    e = game()
    e.s.queue.append(dict(type="attack", actor="enemy0", target="garran", power="attack"))
    e.advance()
    assert e.confirm_enemy_roll(lambda sides: 19 if sides == 20 else 4)
    assert e.s.task["rolls"][1]["total"] == 6


def test_map_stealth_bonus_is_optional_and_data_driven() -> None:
    from dnd_board_game.scenarios.loader import _parse_environment
    raw = dict(id="crates", name="Skrzynie", type="obstacle", positions=[[2, 3]], stealth_bonus=3)
    entry = _parse_environment(raw)
    assert entry.stealth_bonus == 3
    with pytest.raises(ValueError, match="stealth_bonus"):
        _parse_environment(dict(raw, stealth_bonus=-1))
    e = game("mira")
    e.cover_bonuses = {e.active.position: entry.stealth_bonus}
    cast(e, "hide")
    assert e.s.task["modifier"] == e.ability("mira", "dexterity")+3


@pytest.mark.parametrize("hero", ["garran", "brakka", "mira", "dagna", "lorian", "nimra", "erynd"])
def test_equipment_ac_and_movement_are_kept_under_new_profile(hero: str) -> None:
    from dnd_board_game.inventory.armor import effective_armor_class, effective_speed_feet
    e = game(hero)
    assert e.ac(hero) == effective_armor_class(e.active)
    expected = effective_speed_feet(e.active)//5
    assert e.fighter().turn_base == (expected//2 if hero == "garran" else expected)


def test_longbow_retains_authored_range_and_shooting_powers_require_bow() -> None:
    e = game("erynd")
    assert e.weapons["erynd"].range == 30
    e.update_actor(replace(e.actor("enemy0"), position=Coordinate(3, 25)))
    assert e.choose("anchoring_arrow")
    assert "enemy0" in e.legal_targets()
    assert e.cancel()
    e.weapons["erynd"] = replace(e.weapons["erynd"], proficiency_id="light_crossbow")
    assert e.unavailable("anchoring_arrow") == "Wymaga łuku"


def test_unarmed_critical_has_no_impossible_zero_sided_dice() -> None:
    e = game("brakka")
    e.weapons["brakka"] = ChargeWeapon("unarmed", "Bez broni", "strength", "melee", 1,
        (dict(count=0, sides=0, value=5, damage_type="bludgeoning", label="Bez broni"),), source_type="unarmed")
    assert e.unavailable("powerful_strike") == "Wymaga broni"
    cast(e, "attack", "enemy0")
    dice(e, 20)
    assert e.actor("enemy0").hp == 95
    assert not e.s.task or e.s.task["type"] != "roll"
