"""Presentation must retain the engine's actor identity, effects and target state."""
from copy import deepcopy
from typing import Any

from dnd_board_game.ui.tabletop_combat import tabletop_combat_payload


def actor(actor_id: str, hp: int = 10, **extra: Any) -> dict[str, Any]:
    return {"id": actor_id, "name": actor_id.title(), "hp": hp, "max_hp": 20,
            "ac": 14, "position": [1, 1], "effects": [], "status_chips": [], **extra}


def test_roster_uses_initiative_keeps_defeated_and_appends_new_summon() -> None:
    combat = {"actors": [actor("hero"), actor("enemy", 0, defeated=True), actor("summon")],
              "current_actor": actor("hero", 8)}
    order = [{"actor_id": "enemy", "total": 19}, {"actor_id": "hero", "total": 12},
             {"actor_id": "removed", "total": 5}, {"actor_id": "hero", "total": 12}]
    view = tabletop_combat_payload(combat, order)
    assert [entry["id"] for entry in view["actors"]] == ["enemy", "hero", "summon"]
    assert view["actors"][0]["hp"] == 0
    assert view["actors"][0]["defeated"]
    assert view["actors"][1]["hp"] == 8
    assert [entry["id"] for entry in view["actors"] if entry["active"]] == ["hero"]
    assert view["actors"][2]["initiative"] is None


def test_target_enrichment_uses_live_roster_and_does_not_mutate_pending() -> None:
    combat = {"actors": [actor("hero"), actor("enemy", 3, position=[4, 1],
              status_chips=[{"label": "Powalony", "title": "Źródło: Nimra"}])],
              "current_actor": actor("hero"),
              "pending_player_attack": {"target": actor("enemy", 20), "target_ac": 19,
                  "attack_mode": "disadvantage", "positioning": {"cover_level": "three_quarters", "cover_bonus": 5}}}
    snapshot = deepcopy(combat)
    view = tabletop_combat_payload(combat)
    assert combat == snapshot
    assert view["target"] == {"actor_id": "enemy", "distance_feet": 15}
    assert view["actors"][1]["hp"] == 3
    assert view["actors"][1]["details"][0]["label"] == "Powalony"


def test_missing_target_is_not_resurrected_from_pending_snapshot() -> None:
    combat = {"actors": [actor("hero")], "current_actor": actor("hero"),
              "pending_player_attack": {"target": actor("removed")}}
    assert tabletop_combat_payload(combat)["target"] is None


def test_feature_target_has_same_identity_as_attack_target() -> None:
    combat = {"actors": [actor("hero"), actor("enemy")], "current_actor": actor("hero"),
              "class_feature_targeting": {"action_id": "garran_command_halt", "selected_target": {"id": "enemy", "name": "Enemy"}}}
    assert tabletop_combat_payload(combat)["target"]["actor_id"] == "enemy"


def test_aura_membership_source_and_expiry_follow_engine_payload() -> None:
    source = actor("dagna")
    combat = {"actors": [source, actor("hero"), actor("outside")], "current_actor": source,
              "active_effects": [{"id": "bless", "expires": "do mana draina albo utraty koncentracji"}],
              "auras": [{"id": "bless", "label": "Błogosławieństwo", "source_actor_id": "dagna",
                         "source_actor_name": "Dagna", "radius_feet": 10, "affected_actor_ids": ["hero"]}]}
    by_id = {item["id"]: item for item in tabletop_combat_payload(combat)["actors"]}
    assert by_id["dagna"]["details"][0]["aura_source"]
    assert not by_id["dagna"]["details"][0]["aura_receives"]
    assert by_id["hero"]["details"][0]["source_name"] == "Dagna"
    assert by_id["hero"]["details"][0]["expires"] == "do mana draina albo utraty koncentracji"
    assert by_id["outside"]["details"] == []
    combat["auras"] = []
    assert all(not item["details"] for item in tabletop_combat_payload(combat)["actors"])


def test_effect_source_and_concentration_survive_projection() -> None:
    hero = actor("hero", effects=[{"id": "buff", "kind": "concentration_attack_bonus", "label": "Pomoc",
                                  "value_label": "+1k4", "source_actor_id": "dagna", "expires": "do następnego ataku"},
                                 {"id": "internal", "kind": "mana_series_source"}],
                 concentration={"label": "Czar", "expires": "do utraty koncentracji"})
    view = tabletop_combat_payload({"actors": [hero, actor("dagna")], "current_actor": hero})
    assert len(view["actors"][0]["details"]) == 2
    assert view["actors"][0]["details"][0]["source_name"] == "Dagna"
    assert view["actors"][0]["details"][1]["concentration"]


def test_condition_preserves_real_expiration_owner_and_avoids_duplicate_chip() -> None:
    from dnd_board_game.combat.conditions import CombatCondition, ConditionState
    from dnd_board_game.rules import EffectDuration

    target = actor("enemy", status_chips=[{"label": "Powalony", "title": "Opis"}])
    state = ConditionState(actor_id="enemy", condition=CombatCondition.PRONE,
                           source_actor_id="nimra", source_label="Lepka matryca",
                           duration=EffectDuration.UNTIL_TURN_START,
                           expiration_actor_id="nimra", expiration_event_count=2)
    view = tabletop_combat_payload({"actors": [target, actor("nimra")], "current_actor": target},
                                   conditions=(state,))
    details = view["actors"][0]["details"]
    assert len(details) == 1
    assert details[0]["source_name"] == "Nimra"
    assert details[0]["source_label"] == "Lepka matryca"
    assert details[0]["duration"] == "until_turn_start"
    assert details[0]["expiration_actor"] == "Nimra"
    assert details[0]["expiration_count"] == 2


def test_status_chip_does_not_repeat_the_same_effect_with_numeric_suffix() -> None:
    hero = actor("hero", effects=[{"id": "fatigue", "kind": "scenario_fatigue",
                                   "label": "Zmęczenie", "value_label": "-2"}],
                 status_chips=[{"label": "Zmęczenie: -2", "title": "Kara"}])
    view = tabletop_combat_payload({"actors": [hero], "current_actor": hero})
    assert len(view["actors"][0]["details"]) == 1
