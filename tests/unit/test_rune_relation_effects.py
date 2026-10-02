"""Execute every printed resonance bonus through dice, interrupts and saves."""
from copy import deepcopy
from dataclasses import replace
from itertools import product
from typing import Any

import pytest

from dnd_board_game.actors import Faction
from dnd_board_game.combat.charge_encounter import ChargeEncounter, hymn_sides
from dnd_board_game.rules.resonance import ChargeState, STARTER_RUNES, legal_next_runes
from dnd_board_game.world import Coordinate
from dnd_board_game.world.charge_movement import distance
from tests.unit.test_rune_relations_combat import CATALOG, game, memory


BONUSES = [(hero_id, card["id"], index)
           for hero_id, hero in CATALOG["heroes"].items()
           for card in hero["cards"] for index, _ in enumerate(card["resonance_bonuses"])]
SUPPORTED = {"attack_bonus_dice", "damage_dice_extra", "first_damage_dice", "heal_dice", "heal_flat",
             "adjacent_ally_heal_dice", "self_temp_hp", "target_temp_hp", "self_ac_next_turn", "target_ac_next_turn",
             "next_attack_advantage", "check_advantage", "hide_advantage", "no_opportunity", "enemy_save_penalty",
             "range_bonus", "move_bonus", "bonus_move", "perception_penalty", "hymn_sides", "bless_bonus",
             "enemy_move_penalty", "charge_bonus_flat", "shield_pool"}
FRIENDLY = {"bless", "healing_word", "inspiration", "passage_song", "energy_recovery", "arcane_shield"}


def _seed_bonus(e: ChargeEncounter, card_id: str, required: list[str]) -> None:
    """Find a legal preceding history that contains this printed condition."""
    pool = tuple(rune for rune in STARTER_RUNES if rune != "Fala")
    rune = e.card(card_id).rune
    relations = CATALOG["rules"]["rune_relations"]
    for length in range(1, 4):
        for path in product(pool, repeat=length):
            if set(required) <= set(path) and rune in legal_next_runes(path[-1], relations) and all(
                    right in legal_next_runes(left, relations) for left, right in zip(path, path[1:])):
                memory(e, *path)
                return
    pytest.fail(f"Unreachable bonus: {card_id} {required}")


def _restore(e: ChargeEncounter) -> ChargeEncounter:
    before = e.s.as_payload()
    state = ChargeState.from_payload(before, set(e.actors))
    state.validate_catalog(e.catalog)
    restored = ChargeEncounter(replace(e.combat_state(), resonance=state), e.board, e.catalog, e.weapons)
    assert restored.s.as_payload() == before
    assert restored.actors == e.actors
    return restored


def _resolve(e: ChargeEncounter) -> tuple[ChargeEncounter, list[dict[str, Any]]]:
    """Snapshot every physical die and follow-up decision before accepting it."""
    seen: list[dict[str, Any]] = []
    canonical_modifiers = deepcopy(e.s.action["modifiers"])
    for _ in range(150):
        e = _restore(e)
        assert e.s.action["modifiers"] == canonical_modifiers
        task = e.s.task
        if task is None:
            assert not e.s.queue and e.s.phase == "result"
            return e, seen
        seen.append(deepcopy(task))
        kind = task["type"]
        if kind == "roll":
            if e.actor(task["actor"]).faction == Faction.ENEMY:
                assert e.confirm_enemy_roll(lambda sides: 1)
            else:
                index = len(task.get("dice_results", []))
                die = e.roll_dice()[index]
                value = 16 if task["outcome"] in {"attack", "hide", "bash"} else 3
                assert e.submit_die(min(value, die["sides"]), index)
        elif kind == "relocate":
            fields = e.relocation_fields(task)
            target = e.actor(task["target"])
            # Use the granted movement rather than choosing the current field.
            destination = max(fields, key=lambda p: (distance(target.position, p),
                min((distance(p, enemy.position) for enemy in e.enemies(target)), default=0)))
            assert e.select(destination)
            e = _restore(e)
            assert e.confirm_relocation()
        elif kind == "bonus_target":
            assert e.select(e.available_fields()[0])
            e = _restore(e)
            assert e.confirm_bonus_target()
        elif kind == "recover":
            assert e.recover(False)
        elif kind == "hymn":
            assert e.decide_hymn(False)
        elif kind == "opportunity":
            assert e.opportunity(False)
        else:
            assert kind in {"enemy-result", "correction", "enemy-move"}
            assert e.acknowledge()
    pytest.fail("Bonus resolution did not settle")


def _prepared(hero_id: str, card_id: str, modifiers: dict[str, Any]) -> tuple[ChargeEncounter, str, str]:
    ally_id = "mira" if hero_id == "garran" else "garran"
    far_id = next(hero for hero in ("dagna", "nimra", "mira") if hero not in {hero_id, ally_id})
    e = game(hero_id, (ally_id, far_id))
    positions = {hero_id: Coordinate(3, 4), ally_id: Coordinate(2, 3), far_id: Coordinate(1, 1),
                 "enemy0": Coordinate(7 if hero_id == "erynd" else 4, 4), "enemy1": Coordinate(12, 12)}
    if card_id in {"bastion_charge", "charge", "guard_vault"}:
        positions["enemy0"], positions["enemy1"] = Coordinate(6, 4), Coordinate(3, 5)
    if card_id == "shield_bash" and modifiers.get("no_opportunity"):
        positions["enemy1"] = Coordinate(3, 5)
    if modifiers.get("range_bonus"):
        if card_id == "guard_vault":
            positions["enemy0"] = Coordinate(8, 4)  # Five fields, outside base four.
        elif card_id == "force_darts":
            positions["enemy0"] = Coordinate(10, 4)  # Seven fields, outside base six.
        elif card_id == "passage_song":
            positions[ally_id] = Coordinate(10, 4)
        elif card_id == "roar":
            positions["enemy0"] = Coordinate(6, 4)  # Three fields, outside base two.
    for actor_id, actor in list(e.actors.items()):
        e.update_actor(replace(actor, position=positions[actor_id], max_hp=500, hp=350))
        e.fighter(actor_id).turn_base = 6
    e.begin_turn()
    if card_id == "energy_recovery":
        e.fighter(ally_id).charges = 5
    return e, ally_id, far_id


@pytest.mark.parametrize("hero_id,card_id,bonus_index", BONUSES,
                         ids=[f"{hero}.{card}.{index}" for hero, card, index in BONUSES])
def test_each_printed_bonus_executes_and_survives_pending_save(
    hero_id: str, card_id: str, bonus_index: int,
) -> None:
    row = next(card for card in CATALOG["heroes"][hero_id]["cards"] if card["id"] == card_id)
    bonus = row["resonance_bonuses"][bonus_index]
    modifiers = bonus["modifiers"]
    assert set(modifiers) <= SUPPORTED
    e, ally_id, far_id = _prepared(hero_id, card_id, modifiers)
    _seed_bonus(e, card_id, bonus["requires"])
    assert bonus in e.resonance_preview(card_id)["active_bonuses"]
    initial_position = e.active.position
    initial_ac = {actor_id: e.ac(actor_id) for actor_id in e.actors}
    initial_movement = e.movement("enemy0")
    assert e.choose(card_id)
    if card_id == "misty_step":
        assert e.select(Coordinate(10, 4) if modifiers.get("range_bonus") else Coordinate(3, 5))
    elif card_id == "guard_vault":
        assert e.select(e.actor("enemy0").position)
        assert e.select(Coordinate(e.actor("enemy0").position.col, 3))
    elif card_id == "skirmish_shot":
        assert e.select(Coordinate(3, 7) if modifiers.get("move_bonus") else Coordinate(3, 5))
        assert e.select(e.actor("enemy0").position)
    elif card_id == "force_darts":
        for _ in range(3):
            assert e.select(e.actor("enemy0").position)
    elif card_id == "force_wave":
        assert e.exclude(None)
    elif not e.ready():
        assert e.select(e.actor(ally_id if card_id in FRIENDLY else "enemy0").position)
    cost = e.price(e.card(card_id), "auto", e.s.preview["targets"])
    assert e.commit()
    assert e.fighter(hero_id).charges == 20-cost
    e, seen = _resolve(e)
    assert e.fighter(hero_id).charges == 20-cost
    assert e.s.action["resonance_applied"]
    assert e.s.chain.entries[-1].rune == e.card(card_id).rune
    rolls = [task for task in seen if task["type"] == "roll" and not task.get("dice_results")]

    if "attack_bonus_dice" in modifiers:
        damage = next(task for task in rolls if task["outcome"] == "damage" and task.get("power") == card_id)
        assert any(part.get("label") == "Rezonans · moc" for part in damage["components"])
        weapon_base = sum(part["count"]*3+part.get("modifier", 0) if part.get("count") else part.get("value", 0)
                          for part in e.weapons[hero_id].components)
        base_extra = 3 if card_id == "breaking_strike" else 0
        assert e.actor("enemy0").hp == 350-weapon_base-base_extra-3
    if "damage_dice_extra" in modifiers:
        damage = next(task for task in rolls if task["outcome"] == "area_damage")
        assert len(damage["parts"]) == 2 and sum(part["count"] for part in damage["parts"]) == 3
        assert e.actor("enemy0").hp == 341 and e.actor("enemy1").hp == 350
    if "first_damage_dice" in modifiers:
        damage = [task for task in rolls if task["outcome"] == "damage"]
        assert [len(task["parts"]) for task in damage] == [2, 1, 1]
        assert e.actor("enemy0").hp == 335 and e.actor("enemy1").hp == 350
    if "heal_dice" in modifiers:
        assert any(task["outcome"] == "heal_group" and len(task["parts"]) == 2 for task in rolls)
        assert e.actor(ally_id).hp == 350+6+e.ability(hero_id, "wisdom")+2
        assert e.actor(far_id).hp == 350
    if "heal_flat" in modifiers:
        assert any(task["outcome"] == "heal_group" and task["modifier"] == 2 for task in rolls)
        assert e.actor(hero_id).hp == 355 and e.actor(ally_id).hp == 357 and e.actor(far_id).hp == 350
    if "adjacent_ally_heal_dice" in modifiers:
        assert any(task["type"] == "bonus_target" for task in seen)
        assert e.actor(ally_id).hp == 353 and e.actor(far_id).hp == 350
    if "self_temp_hp" in modifiers:
        assert e.fighter(hero_id).cup == modifiers["self_temp_hp"] and e.fighter(ally_id).cup == 0
    if "target_temp_hp" in modifiers:
        assert e.fighter(ally_id).cup == modifiers["target_temp_hp"] and e.fighter(far_id).cup == 0
    if "self_ac_next_turn" in modifiers:
        assert e.ac(hero_id) == initial_ac[hero_id]+modifiers["self_ac_next_turn"]
    if "target_ac_next_turn" in modifiers:
        base_arcane = 2 if card_id == "arcane_shield" else 0
        assert e.ac(ally_id) == initial_ac[ally_id]+base_arcane+modifiers["target_ac_next_turn"]
        assert e.ac(far_id) == initial_ac[far_id]
    if "next_attack_advantage" in modifiers:
        assert e.status(hero_id, "next_attack")
    if "check_advantage" in modifiers:
        assert any(task["outcome"] in {"attack", "bash"} and task["mode"] == "advantage"
                   and len(task["parts"]) == 2 for task in rolls)
    if "hide_advantage" in modifiers:
        assert any(task["outcome"] == "hide" and task["mode"] == "advantage" for task in rolls)
    if "enemy_save_penalty" in modifiers:
        ability = {"bastion_charge": "constitution", "sacred_flame": "dexterity", "mockery": "wisdom"}[card_id]
        assert any(task["outcome"] == "save" and task["modifier"] == e.ability(task["actor"], ability)-2 for task in rolls)
    if "no_opportunity" in modifiers:
        assert not any(task.get("power") == "opportunity" for task in seen)
        assert e.fighter("enemy1").reaction
        assert distance(e.active.position, e.actor("enemy1").position) > 1
    if "range_bonus" in modifiers:
        if card_id == "misty_step":
            assert distance(initial_position, e.active.position) == 7
        elif card_id in {"force_darts", "guard_vault"}:
            assert distance(initial_position, e.actor("enemy0").position) > (4 if card_id == "guard_vault" else 6)
        elif card_id == "roar":
            assert e.status("enemy0", "fear") and distance(initial_position, e.actor("enemy0").position) == 3
        else:
            assert card_id == "passage_song" and distance(initial_position, e.actor(ally_id).position) > 6
    if "move_bonus" in modifiers:
        assert (any(task["type"] == "relocate" and task["radius"] == 3 for task in seen)
                if card_id == "passage_song" else e.active.position == Coordinate(3, 7))
    if "bonus_move" in modifiers:
        assert any(task["type"] == "relocate" and task["target"] == hero_id and task["radius"] == modifiers["bonus_move"] for task in seen)
        assert distance(initial_position, e.active.position) == modifiers["bonus_move"]
        assert e.fighter(hero_id).base_spent == 0
    if "perception_penalty" in modifiers:
        assert any(task["outcome"] == "hide" and task["perception_penalty"] == 2 for task in rolls)
        assert "enemy0" in e.fighter(hero_id).hidden
    if "hymn_sides" in modifiers:
        assert hymn_sides(e.actor(ally_id)) == 8 and e.status(ally_id, "hymn")["sides"] == 8
    if "bless_bonus" in modifiers:
        assert e.status(ally_id, "bless")["value"] == 2 and e.status(far_id, "bless") is None
    if "enemy_move_penalty" in modifiers:
        assert e.status("enemy0", "move_penalty")["value"] == 2
        assert e.movement("enemy0") < initial_movement and e.status("enemy1", "move_penalty") is None
    if "charge_bonus_flat" in modifiers:
        assert e.fighter(ally_id).charges == 10 and e.fighter(far_id).charges == 20
    if "shield_pool" in modifiers:
        assert e.fighter(ally_id).shield == 3 and e.fighter(hero_id).shield == e.fighter(far_id).shield == 0

    # Finishing the chain cannot erase a timed card effect or a persistent Hymn.
    assert e.acknowledge()
    if "next_attack_advantage" in modifiers:
        assert e.choose("attack") and e.select(e.actor("enemy0").position) and e.commit()
        assert e.s.task["outcome"] == "attack" and e.s.task["mode"] == "advantage"
        assert len(e.s.task["parts"]) == 2 and e.status(hero_id, "next_attack") is None
        e, _ = _resolve(e)
        assert e.acknowledge()
    before_effects = {actor_id: (e.ac(actor_id), deepcopy(e.fighter(actor_id).statuses),
                               e.fighter(actor_id).cup, e.fighter(actor_id).shield) for actor_id in e.actors}
    e.end_chain("test")
    assert before_effects == {actor_id: (e.ac(actor_id), e.fighter(actor_id).statuses,
                                       e.fighter(actor_id).cup, e.fighter(actor_id).shield) for actor_id in e.actors}
    if "shield_pool" in modifiers:
        hp = e.actor(ally_id).hp
        e.damage(ally_id, [dict(damage_type="psychic", value=2)], "enemy0")
        assert e.actor(ally_id).hp == hp-2 and e.fighter(ally_id).shield == 3
        e.damage(ally_id, [dict(damage_type="bludgeoning", value=2)], "enemy0")
        assert e.actor(ally_id).hp == hp-2 and e.fighter(ally_id).shield == 1
    e.begin_turn()
    for actor_id in e.actors:
        assert not any(status.get("until_start") == hero_id for status in e.fighter(actor_id).statuses)
        if "self_temp_hp" in modifiers or "target_temp_hp" in modifiers:
            assert e.fighter(actor_id).cup == 0
        if "shield_pool" in modifiers:
            assert e.fighter(actor_id).shield == 0
    if "hymn_sides" in modifiers:
        assert hymn_sides(e.actor(ally_id)) == 8


def test_execution_matrix_contains_all_fifty_one_printed_bonuses() -> None:
    assert len(BONUSES) == 51
