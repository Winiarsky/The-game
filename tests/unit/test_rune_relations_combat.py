"""Production v0.3 powers: declared memory, card effects and interruptible queues."""
from copy import deepcopy
from dataclasses import replace

import pytest

from dnd_board_game.actors import Faction
from dnd_board_game.combat.charge_encounter import ChargeEncounter, hymn_source
from dnd_board_game.rules.resonance import (
    ChargeState, PROFILE, ResonanceChain, ResonanceEntry, STARTER_RUNES, legal_next_runes,
)
from dnd_board_game.scenarios.rune_relation_catalog import load_rune_relation_catalog
from dnd_board_game.world import Coordinate
from tests.unit.test_resonance_combat import game as legacy_game


CATALOG = load_rune_relation_catalog()
CARDS = [(hero, card["id"]) for hero, row in CATALOG["heroes"].items() for card in row["cards"]]


def game(hero: str = "garran", companions: tuple[str, ...] = ()) -> ChargeEncounter:
    engine = legacy_game(hero, companions)
    engine.s.version = 2
    engine.s.profile = PROFILE
    engine.catalog = CATALOG
    engine.original = replace(engine.original, resonance=deepcopy(engine.s))
    return engine


def memory(e: ChargeEncounter, *runes: str, contributor: str | None = None) -> None:
    owner = contributor or str(e.active.id)
    e.s.chain = ResonanceChain(1, [ResonanceEntry(rune, "nimra" if rune == "Fala" else owner, rune) for rune in runes],
                               list(dict.fromkeys("nimra" if rune == "Fala" else owner for rune in runes)))
    e.s.serial = max(e.s.serial, 1)


def prepare(e: ChargeEncounter, card_id: str) -> None:
    card = e.card(card_id)
    if card.ends_resonance:
        memory(e, *(('Wieża', 'Błysk', 'Schody') if card_id == 'powerful_strike' else
                    ('Hak', 'Schody') if card_id == 'shadow_attack' else ('Oko', 'Węzeł')))
    if card_id == "shadow_attack":
        e.fighter().hidden = ["enemy0"]
    assert e.choose(card_id), e.unavailable(card_id)
    if card_id == "flame_fan":
        assert e.select(e.actor("enemy0").position)
        assert e.exclude(str(e.active.id))
    elif card_id == "force_wave":
        assert e.exclude(None)
    elif card_id in {"misty_step", "skirmish_shot"}:
        assert e.select(Coordinate(3, 2))
        if card_id == "skirmish_shot":
            assert e.select(e.actor("enemy0").position)
    elif card_id not in {"rage", "hide", "second_wind", "roar", "preserve_life"}:
        target = next(key for key in e.legal_targets() if key != str(e.active.id))
        for _ in range(3 if card_id == "force_darts" else 2 if card_id == "double_shot" else 1):
            assert e.select(e.actor(target).position)
        if card_id == "guard_vault":
            assert e.select(e.available_fields()[0])
    assert e.ready()


def drain(e: ChargeEncounter, hero_die: int = 1) -> None:
    for _ in range(150):
        task = e.s.task
        if not task:
            assert not e.s.queue
            return
        kind = task["type"]
        if kind == "roll":
            if e.actor(task["actor"]).faction == Faction.ENEMY:
                assert e.confirm_enemy_roll(lambda sides: 1)
            else:
                die = e.roll_dice()[len(task.get("dice_results", []))]
                assert e.submit_die(min(hero_die, die["sides"]), len(task.get("dice_results", [])))
        elif kind == "recover":
            assert e.recover(False)
        elif kind == "relocate":
            assert e.select(e.relocation_fields(task)[0]) and e.confirm_relocation()
        elif kind == "bonus_target":
            assert e.select(e.available_fields()[0]) and e.confirm_bonus_target()
        elif kind == "hymn":
            assert e.decide_hymn(False)
        elif kind == "opportunity":
            assert e.opportunity(False)
        else:
            assert e.acknowledge()
    pytest.fail("Queue did not settle")


def restore(e: ChargeEncounter) -> ChargeEncounter:
    saved = ChargeState.from_payload(e.s.as_payload(), set(e.actors))
    return ChargeEncounter(replace(e.combat_state(), resonance=saved), e.board, e.catalog, e.weapons)


@pytest.mark.parametrize("hero,card_id", CARDS)
def test_every_power_single_payment_and_restorable_queue(hero: str, card_id: str) -> None:
    companion = "mira" if hero == "garran" else "garran"
    e = game(hero, (companion,))
    prepare(e, card_id)
    cost = e.price(e.card(card_id), "auto", e.s.preview["targets"])
    e = restore(e)
    assert e.commit()
    assert e.fighter().charges == 20-cost
    assert not e.commit()
    if e.s.task:
        e = restore(e)
    drain(e)
    e = restore(e)
    assert e.fighter().charges == 20-cost
    if e.card(card_id).ends_resonance:
        assert e.s.chain is None
    else:
        assert e.s.chain.entries[-1].rune == e.card(card_id).rune
    assert not e.fighter().special


def test_memory_eviction_checks_oldest_before_adding_and_no_global_effects() -> None:
    e = game()
    memory(e, "Wieża", "Błysk", "Schody")
    base_ac = e.ac("garran")
    assert e.bonus("garran", "Wieża") == 0
    assert e.choose("breaking_strike") and e.select(e.actor("enemy0").position)
    preview = e.resonance_preview(e.card("breaking_strike"))
    assert len(preview["active_bonuses"]) == 2
    assert e.commit()
    assert [entry.rune for entry in e.s.chain.entries] == ["Wieża", "Błysk", "Schody"]
    assert e.submit_die(1, 0)
    drain(e)
    assert [entry.rune for entry in e.s.chain.entries] == ["Błysk", "Schody", "Grot"]
    assert e.ac("garran") == base_ac+1  # Printed protection also applies on a miss.
    e.end_chain("test")
    assert e.ac("garran") == base_ac+1
    e.begin_turn()
    assert e.ac("garran") == base_ac


def test_reset_clears_before_roll_and_cannot_inherit_old_bonus() -> None:
    e = game()
    memory(e, "Wieża", "Grot")  # Grot cannot continue into Błysk.
    assert e.choose("second_wind")
    assert e.resonance_preview("second_wind")["transition"] == "reset"
    assert e.effect_modifiers() == {}
    assert e.fighter().charges == 20
    assert e.commit() and e.s.chain is None
    assert e.submit_die(1, 0)
    drain(e)
    assert [entry.rune for entry in e.s.chain.entries] == ["Błysk"]
    assert e.fighter().cup == 0


def test_empty_and_repeated_symbols_do_not_self_strengthen_or_multiply() -> None:
    e = game()
    assert e.effect_modifiers("breaking_strike") == {}
    memory(e, "Schody", "Grot", "Klepsydra")
    assert len(e.resonance_preview("breaking_strike")["active_bonuses"]) == 1
    assert e.counts() == {"Schody": 1, "Grot": 1, "Klepsydra": 1}
    # The legal cycle occupies all three slots, but presence stays a boolean.
    memory(e, "Grot", "Klepsydra", "Grot")
    assert e.counts()["Grot"] == 1


def test_finisher_requires_symbols_and_legal_last_rune_and_clears_after_miss() -> None:
    e = game("brakka")
    assert not e.choose("powerful_strike")
    memory(e, "Wieża", "Błysk")  # Both symbols, but Błysk -> Grot is illegal.
    assert "legalnej kontynuacji" in e.unavailable("powerful_strike")
    memory(e, "Wieża", "Błysk", "Schody")
    assert e.choose("powerful_strike") and e.select(e.actor("enemy0").position)
    assert e.commit() and e.s.chain
    assert e.submit_die(1, 0)
    drain(e)
    assert e.s.chain is None and e.fighter().charges == 12


def test_fala_preserves_symbols_but_never_substitutes_or_copies() -> None:
    e = game("nimra")
    memory(e, "Wieża", "Grot")
    assert e.resonance_preview("misty_step")["transition"] == "continue"
    assert e.choose("misty_step") and e.select(Coordinate(3, 2)) and e.commit()
    drain(e)
    assert e.counts() == {"Wieża": 1, "Grot": 1, "Fala": 1}
    assert set(e.next_runes()) == set(STARTER_RUNES)
    assert e.resonance_preview("flame_fan")["missing_required_runes"] == ["Oko", "Węzeł"]
    with pytest.raises(ValueError, match="runa"):
        game().add_rune("garran", "Fala")


def test_hide_combines_perception_advantage_and_post_success_movement() -> None:
    e = game("mira")
    memory(e, "Schody", "Grot", "Kielich")
    assert e.choose("hide") and e.commit()
    task = e.s.task
    assert task["mode"] == "advantage" and task["perception_penalty"] == 2
    assert e.submit_die(8, 0)
    assert e.submit_die(20, 1)
    assert e.s.task["type"] == "relocate" and e.s.task["radius"] == 2
    assert e.fighter().hidden == ["enemy0", "enemy1"]
    assert [entry.rune for entry in e.s.chain.entries] == ["Schody", "Grot", "Kielich"]
    destination = next(p for p in e.available_fields() if p != e.active.position)
    assert e.select(destination) and e.confirm_relocation()
    drain(e)
    assert e.fighter().base_spent == 0 and e.actor("mira").position == destination
    assert [entry.rune for entry in e.s.chain.entries] == ["Grot", "Kielich", "Błysk"]


def test_failed_hide_does_not_offer_bonus_movement() -> None:
    e = game("mira")
    memory(e, "Schody")
    assert e.choose("hide") and e.commit() and e.submit_die(1, 0)
    assert not e.fighter().hidden and e.s.task is None
    assert e.s.phase == "result"


def test_bash_advantage_and_extra_step_happen_after_push() -> None:
    e = game()
    memory(e, "Schody", "Oko")
    assert e.choose("shield_bash") and e.select(e.actor("enemy0").position) and e.commit()
    assert e.confirm_enemy_roll(lambda sides: 1) and e.acknowledge()
    assert e.s.task["outcome"] == "bash" and e.s.task["mode"] == "advantage"
    assert e.submit_die(20, 0) and e.submit_die(20, 1)
    assert e.submit_die(1, 0)
    assert e.s.task["label"] == "Impuls egidy"
    assert e.select(e.available_fields()[0]) and e.confirm_relocation()
    assert e.s.task["label"] == "Ruch po mocy" and not e.s.task["opportunities"]
    drain(e)
    assert e.s.chain.entries[-1].rune == "Wieża"


def test_healing_dice_temporary_hp_and_bonus_ally_target() -> None:
    e = game("dagna", ("garran",))
    memory(e, "Wieża", "Grot", "Kielich")
    e.update_actor(replace(e.actor("garran"), hp=1))
    assert e.choose("healing_word") and e.select(e.actor("garran").position) and e.commit()
    assert [(p["count"], p["sides"]) for p in e.s.task["parts"]] == [(1, 6), (1, 6)]
    assert e.submit_die(3, 0) and e.submit_die(4, 1)
    drain(e)
    assert e.actor("garran").hp == 1+7+e.ability("dagna", "wisdom")+2
    assert e.fighter("garran").cup == 4
    e.end_chain("test")
    assert e.fighter("garran").cup == 4
    e = game("garran", ("mira",))
    memory(e, "Kielich")
    assert e.choose("second_wind") and e.commit() and e.submit_die(1, 0)
    assert e.s.task["type"] == "bonus_target"
    e = restore(e)
    assert not e.confirm_bonus_target()
    assert e.select(e.actor("mira").position) and e.confirm_bonus_target()
    assert e.s.task["parts"][0]["sides"] == 6
    drain(e)


def test_shield_bonus_persists_reset_has_no_refill_and_psychic_bypasses() -> None:
    e = game("nimra", ("garran",))
    memory(e, "Wieża", "Grot")
    assert e.choose("arcane_shield") and e.select(e.actor("garran").position) and e.commit()
    drain(e)
    assert e.fighter("garran").shield == 3
    e.end_chain("test")
    before = e.actor("garran").hp
    e.damage("garran", [dict(value=2, damage_type="psychic")], "enemy0")
    assert e.actor("garran").hp == before-2 and e.fighter("garran").shield == 3
    e.damage("garran", [dict(value=2, damage_type="fire")], "enemy0")
    assert e.fighter("garran").shield == 1
    e.s.index = e.s.order.index("garran")
    e.begin_turn()
    assert e.fighter("garran").shield == 1
    e.s.index = e.s.order.index("nimra")
    e.begin_turn()
    assert e.fighter("garran").shield == 0


def test_dead_source_skipped_turn_expires_wards_and_pools_without_clearing_chain() -> None:
    e = game("nimra", ("garran",))
    e.grant_pool("garran", "temporary", 4, "nimra")
    e.grant_pool("garran", "prevention", 3, "nimra")
    e.grant_ac("garran", 1, "nimra", "test")
    memory(e, "Oko")
    e.skip_turn("nimra")
    assert e.fighter("garran").cup == e.fighter("garran").shield == 0
    assert not e.status("garran", "ward:test")
    assert e.s.chain


def test_enhanced_hymn_survives_chain_and_preserves_natural_attack_failure() -> None:
    e = game("lorian", ("garran",))
    memory(e, "Kielich", "Wieża", "Grot")
    # Legal Grot -> Klepsydra -> Oko path stores a k8 Hymn.
    memory(e, "Grot", "Klepsydra", contributor="garran")
    assert e.choose("inspiration") and e.select(e.actor("garran").position) and e.commit()
    drain(e)
    assert e.hymn_sides("garran") == 8 and e.fighter().charges == 18  # 3 cost, 1 passive refund.
    e.end_chain("test")
    assert e.acknowledge()
    assert e.end_turn() and str(e.active.id) == "garran"
    assert e.choose("attack") and e.select(e.actor("enemy0").position) and e.commit()
    assert e.submit_die(1, 0) and e.s.task["type"] == "hymn"
    e = restore(e)
    assert e.decide_hymn(True) and e.s.task["parts"][0]["sides"] == 8
    assert e.submit_die(8, 0)
    drain(e)
    assert e.actor("enemy0").hp == 100 and not hymn_source(e.actor("garran"))


def test_missing_or_dead_target_rejects_before_payment() -> None:
    e = game()
    memory(e, "Wieża")
    assert e.choose("breaking_strike") and e.select(e.actor("enemy0").position)
    e.update_actor(replace(e.actor("enemy0"), hp=0))
    assert not e.commit()
    assert e.fighter().charges == 20 and e.fighter().ordinary and e.fighter().special
    assert e.s.chain.entries[-1].rune == "Wieża"


def test_focus_and_conscious_omission_clear_but_enemies_do_not() -> None:
    e = game()
    memory(e, "Wieża")
    assert e.choose("focus") and e.commit() and e.s.chain is None
    drain(e)
    assert e.acknowledge()
    memory(e, "Grot")
    assert e.end_turn() and e.s.chain is None
    memory(e, "Oko")
    assert e.active.faction == Faction.ENEMY and e.end_turn() and e.s.chain


@pytest.mark.parametrize("mutation", ["modifiers", "memory", "cost", "rune", "mode"])
def test_tampered_pending_decision_fails_before_restore(mutation: str) -> None:
    e = game()
    memory(e, "Wieża", "Błysk", "Schody")
    assert e.choose("breaking_strike") and e.select(e.actor("enemy0").position) and e.commit()
    payload = e.s.as_payload()
    if mutation == "modifiers":
        payload["action"]["modifiers"]["self_ac_next_turn"] = 9
    elif mutation == "memory":
        payload["action"]["resonance"]["memory_before"] = []
    elif mutation == "cost":
        payload["action"]["paid_cost"] = 0
    elif mutation == "rune":
        payload["chain"]["entries"][-1]["effective"] = "Fala"
    else:
        payload["action"]["mode"] = "enhanced"
    with pytest.raises(ValueError):
        saved = ChargeState.from_payload(payload, set(e.actors))
        saved.validate_catalog(e.catalog)


def test_v3_temporary_hp_sources_never_stack_and_keep_the_stronger_duration() -> None:
    e = game()
    e.update_actor(replace(e.active, temp_hp=7))
    e.grant_pool("garran", "temporary", 4, "garran")
    assert e.fighter().cup == 0 and e.active.temp_hp == 7
    e.begin_turn()
    assert e.active.temp_hp == 7
    e.grant_pool("garran", "temporary", 9, "garran")
    assert e.fighter().cup == 9 and e.active.temp_hp == 0
    before = e.active.hp
    e.damage("garran", [dict(value=10, damage_type="fire")], "enemy0")
    assert e.active.hp == before-1 and e.fighter().cup == 0
    e.grant_pool("garran", "temporary", 9, "garran")
    e.begin_turn()
    assert e.fighter().cup == 0


def test_hymn_from_absent_source_keeps_its_die_and_restores_during_use() -> None:
    from dnd_board_game.actors import FeatureGrant, FeatureSourceKind
    e = game()
    e.update_actor(replace(e.active, features=(*e.active.features,
        FeatureGrant("resonance_hymn", "Hymn odwagi · 1k8", FeatureSourceKind.SCENARIO, "lorian"))))
    assert e.choose("attack") and e.select(e.actor("enemy0").position) and e.commit()
    assert e.submit_die(1, 0) and e.decide_hymn(True)
    assert e.s.task["parts"][0]["sides"] == 8
    e = restore(e)
    assert e.submit_die(8, 0)
    drain(e)
    assert not e.fighter().regeneration_reason


def test_lethal_opportunity_interrupts_bonus_walk_and_preserves_paid_action() -> None:
    e = game("mira", ("garran",))
    e.update_actor(replace(e.actor("garran"), position=Coordinate(10, 10)))
    enemy = e.actor("enemy1")
    e.update_actor(replace(enemy, position=Coordinate(4, 3), ability_scores=replace(enemy.ability_scores, wisdom=30)))
    e.update_actor(replace(e.active, hp=1))
    memory(e, "Schody")
    assert e.choose("hide") and e.commit() and e.submit_die(10, 0)
    assert e.fighter().hidden == ["enemy0"]
    assert e.s.task["type"] == "relocate"
    origin = e.active.position
    assert e.select(Coordinate(2, 3)) and e.confirm_relocation()
    assert e.s.task["outcome"] == "attack" and e.s.task["actor"] == "enemy1"
    assert e.confirm_enemy_roll(lambda sides: sides) and e.acknowledge()
    assert e.s.task["type"] == "correction" and e.active.hp == 0
    assert e.active.position == origin
    assert e.acknowledge()
    drain(e)
    assert e.fighter().charges == 16 and e.s.chain.entries[-1].rune == "Błysk"
    assert e.fighter().base_spent == 0


@pytest.mark.parametrize("mutation", ["bool_version", "unknown_task", "numeric_budget"])
def test_malformed_snapshot_cannot_choose_rules_or_leave_unresolvable_task(mutation: str) -> None:
    e = game()
    assert e.choose("second_wind") and e.commit()
    payload = e.s.as_payload()
    if mutation == "bool_version":
        payload["version"] = True
    elif mutation == "unknown_task":
        payload["task"]["type"] = "invented_bonus"
    else:
        payload["fighters"]["garran"]["special"] = 1
    with pytest.raises(ValueError):
        ChargeState.from_payload(payload, set(e.actors))


def test_roots_block_ordinary_movement_but_allow_special_movement_and_teleport() -> None:
    e = game("brakka")
    e.add_status("brakka", "root", until_end="brakka", turn=e.fighter().turn+1)
    assert e.movement() == 0 and not e.choose("move")
    e.update_actor(replace(e.actor("enemy0"), position=Coordinate(6, 3)))
    e.update_actor(replace(e.actor("enemy1"), position=Coordinate(12, 12)))
    assert e.choose("charge") and e.select(e.actor("enemy0").position) and e.commit()
    assert e.active.position != Coordinate(3, 3)
    assert e.s.task["outcome"] == "attack"
    assert e.movement() == 0
    e = game("nimra")
    e.add_status("nimra", "root", until_end="nimra", turn=e.fighter().turn+1)
    assert not e.choose("move")
    assert e.choose("misty_step") and e.select(Coordinate(3, 2)) and e.commit()
    assert e.active.position == Coordinate(3, 2) and e.movement() == 0


def test_a_newly_blocked_destination_interrupts_the_saved_walk() -> None:
    e = game()
    e.s.action = dict(id="move", actor="garran", card=False, mode="auto", closed=False,
                      harmed=[], damage_groups={}, handled_hooks=[], results=[])
    e.s.queue = [dict(type="move_step", actor="garran", origin=[3, 3], position=[4, 3],
                     cost=1, opportunities=False), dict(type="finish")]
    e.update_actor(replace(e.actor("enemy0"), position=Coordinate(4, 3)))
    e.advance()
    assert e.active.position == Coordinate(3, 3)
    assert e.s.task["type"] == "correction" and e.fighter().base_spent == 0


def test_invalid_automatic_enemy_damage_roll_rolls_back_attack_and_reaction() -> None:
    e = game()
    e.s.queue = [dict(type="attack", actor="enemy0", target="garran", power="opportunity", reaction_pending=True)]
    e.advance()
    checkpoint = e.s.as_payload(), e.actor("garran")
    assert not e.confirm_enemy_roll(lambda sides: 20 if sides == 20 else 0)  # Valid hit, invalid damage.
    assert e.s.as_payload() == checkpoint[0] and e.actor("garran") == checkpoint[1]
    assert e.fighter("enemy0").reaction


@pytest.mark.parametrize("card_flag", [False, 1])
def test_card_flag_cannot_bypass_canonical_paid_power_validation(card_flag: bool | int) -> None:
    e = game()
    memory(e, "Wieża")
    assert e.choose("second_wind") and e.commit()
    payload = e.s.as_payload()
    payload["action"]["card"] = card_flag
    payload["action"]["modifiers"]["self_temp_hp"] = 999
    with pytest.raises(ValueError, match="Oznaczenie"):
        saved = ChargeState.from_payload(payload, set(e.actors))
        saved.validate_catalog(e.catalog)


def test_ordinary_action_cannot_receive_card_modifiers_in_saved_state() -> None:
    e = game()
    assert e.choose("attack") and e.select(e.actor("enemy0").position) and e.commit()
    payload = e.s.as_payload()
    payload["action"]["modifiers"] = {"attack_bonus_dice": [{"count": 3, "sides": 6, "damage_type": "force"}]}
    with pytest.raises(ValueError, match="poza kartami"):
        saved = ChargeState.from_payload(payload, set(e.actors))
        saved.validate_catalog(e.catalog)



def test_malformed_area_center_is_rejected_before_loading_preview() -> None:
    e = game("nimra")
    assert e.choose("force_wave")
    payload = e.s.as_payload()
    payload["preview"]["center"] = [3, 3, 3]
    with pytest.raises(ValueError, match="współrzędnych"):
        ChargeState.from_payload(payload, set(e.actors))


def test_boolean_cell_in_pending_saved_path_is_not_an_integer_coordinate() -> None:
    e = game()
    assert e.choose("move") and e.select(Coordinate(2, 3)) and e.commit()
    assert e.s.task["type"] == "roll"  # Enemy reaction has suspended the path.
    payload = e.s.as_payload()
    payload["action"]["path"]["cells"][0][0] = True
    with pytest.raises(ValueError, match="współrzędnych"):
        ChargeState.from_payload(payload, set(e.actors))
