"""Real mission session, command locking, saves and board adapter."""
from pathlib import Path
from dataclasses import replace
import pytest

from dnd_board_game.ui import resonance
from dnd_board_game.ui.routes import create_app
from tests.unit.test_mission_zero import session, start_battle
from tests.unit.test_initiative_panel import Board
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.ui.board_panel_symbols import rune_slot
from dnd_board_game.rules.resonance import PROFILE, LEGACY_PROFILE


def test_mission_starts_new_profile_and_rejects_stale_commands(tmp_path: Path) -> None:
    s = start_battle(session(tmp_path, legacy_combat=False))
    assert s.combat_state.resonance is not None
    assert s.combat_state.resonance.profile == PROFILE
    assert s.combat_state.resonance.version == 2
    assert s.combat_state.shared_mana is None
    data = s.state_payload()["combat"]["resonance"]
    assert data["active"] == "garran"
    client = create_app(s).test_client()
    command = dict(command="choose", id="focus", revision=data["revision"])
    response = client.post("/api/combat/resonance", json=command)
    assert response.status_code == 200, response.json
    assert response.json["combat"]["resonance"]["phase"] == "preview"
    stale = client.post("/api/combat/resonance", json=command)
    assert stale.status_code == 400
    assert client.post("/api/combat/shared-mana", json={}).status_code == 409


def test_free_arena_uses_charge_ui_without_mission_payload(tmp_path: Path) -> None:
    from tests.unit.test_initiative_panel import session_at_initiative
    s = session_at_initiative(tmp_path)
    s.submit_encounter_initiative_roll(20)
    data = s.state_payload()
    assert data["mission"] is None
    assert data["combat"]["resonance"]["active"] == "garran"
    assert data["combat"]["tabletop"] and data["ui_copy"]["combat"]
    client = create_app(s).test_client()
    response = client.post("/api/combat/resonance", json=dict(command="choose", id="focus", revision=data["combat"]["resonance"]["revision"]))
    assert response.status_code == 200, response.json
    assert response.json["combat"]["resonance"]["phase"] == "preview"


def test_physical_dice_save_restore_and_stale_scan(tmp_path: Path) -> None:
    s = start_battle(session(tmp_path, legacy_combat=False))
    board = Board()
    s.attach_board_connection(board, backend="simulator")
    client = create_app(s).test_client()
    def press(slot: int):
        board.selected = panel_position(slot).as_tuple()
        response = client.post("/api/board/scan", json=dict(revision=s._board_selection_payload()["revision"], automatic=True))
        assert response.status_code == 200, response.json
        return response.json
    old = s._board_selection_payload()["revision"]
    press(rune_slot("Błysk"))
    assert s.combat_state.resonance.phase == "preview"
    assert board.leds[panel_position(28).as_tuple()] == LedColor.PANEL_ACCEPT
    count = board.scans
    client.post("/api/board/scan", json=dict(revision=old, automatic=True))
    assert board.scans == count
    press(28)
    assert s.combat_state.resonance.fighters["garran"].charges == 16
    assert s.combat_state.resonance.task["parts"][0]["sides"] == 10
    press(26)
    assert s.combat_state.resonance.die_value == 6  # k10 starts at 5, then physical +.
    before = s.combat_state.resonance.as_payload()
    s.save_snapshot()
    s.load_snapshot()
    assert s.combat_state.resonance.as_payload() == before
    press(28)
    assert s.combat_state.resonance.phase == "result"
    assert s.combat_state.resonance.task is None


def test_enemy_full_turn_uses_authored_ai_and_returns_to_queue(tmp_path: Path) -> None:
    s = start_battle(session(tmp_path, legacy_combat=False))
    e = resonance.engine(s)
    e.s.index = next(i for i, key in enumerate(e.s.order) if e.actor(key).faction.value == "enemy")
    e.begin_turn()
    s.combat_state = e.combat_state()
    original_actor = e.active.id
    for _ in range(60):
        view = resonance.payload(s)
        if view["active"] != original_actor:
            break
        controls = {c["slot"]: c for c in view["controls"]}
        choice = controls.get(29) if s.combat_state.resonance.task and s.combat_state.resonance.task["type"] in {"opportunity", "recover", "hymn"} else controls.get(28)
        assert choice, view["decision"]
        resonance.command(s, dict(choice, revision=view["revision"]))
    assert s.combat_state.resonance.order[s.combat_state.resonance.index] != original_actor


def test_shared_mission_potion_is_paid_once_and_rolls_individual_dice(tmp_path: Path) -> None:
    from dnd_board_game.inventory import InventoryItem
    s = start_battle(session(tmp_path, legacy_combat=False))
    s.state = replace(s.state, party_loot=replace(s.state.party_loot, items=(InventoryItem("mission_potion", "Mikstura leczenia", "potion"),)))
    e = resonance.engine(s)
    e.update_actor(replace(e.active, hp=1))
    s.combat_state = e.combat_state()
    def send(command: str, **extra):
        return resonance.command(s, dict(command=command, revision=s.combat_state.resonance.revision, **extra))
    send("choose", id="item")
    send("accept")
    assert not s.state.party_loot.items
    assert not s.combat_state.resonance.fighters["garran"].ordinary
    send("die", value=4, index=0)
    assert next(a.hp for a in s.combat_state.actors if a.id == "garran") == 1
    s.save_snapshot()
    s.load_snapshot()
    send("die", value=4, index=1)
    assert next(a.hp for a in s.combat_state.actors if a.id == "garran") == 13
    assert not s.state.party_loot.items


def test_road_fatigue_is_applied_to_attack_and_damage(tmp_path: Path) -> None:
    s = start_battle(session(tmp_path, legacy_combat=False))
    e = resonance.engine(s)
    assert e.weapons["garran"].attack_bonus == -2
    assert e.weapons["garran"].components[0]["modifier"] == e.ability("garran", "strength")-2


def test_authored_stealth_cover_is_injected_without_open_space_restriction(tmp_path: Path) -> None:
    from dnd_board_game.combat.scene import SceneObject
    s = start_battle(session(tmp_path, 4, legacy_combat=False))
    e = resonance.engine(s)
    e.s.index = e.s.order.index("mira")
    e.begin_turn()
    s.combat_state = e.combat_state()
    source = s._active_encounter()
    cover = SceneObject("crates", "Skrzynie", (e.active.position,), "Obejrzyj", stealth_bonus=3)
    s._replace_active_encounter(replace(source, scene_objects=(*source.scene_objects, cover)))
    e = resonance.engine(s)
    assert e.choose("hide") and e.commit()
    assert e.s.task["modifier"] == e.ability("mira", "dexterity")+3


def test_snapshot_rejects_charge_turn_that_disagrees_with_initiative(tmp_path: Path) -> None:
    import pytest
    from dnd_board_game.save.session_snapshot import _combat_payload, _combat_from_payload, SnapshotValidationError
    s = start_battle(session(tmp_path, legacy_combat=False))
    saved = _combat_payload(s.combat_state)
    saved["resonance"]["index"] += 1
    with pytest.raises(SnapshotValidationError, match="inicjatywie"):
        _combat_from_payload(saved)


def test_finished_combat_returns_to_mission_without_clearing_hymn(tmp_path: Path) -> None:
    from dnd_board_game.actors import FeatureGrant, FeatureSourceKind
    s = start_battle(session(tmp_path, legacy_combat=False))
    encounter = s._active_encounter()
    e = resonance.engine(s)
    for a in list(e.actors.values()):
        if a.faction.value == "enemy":
            e.update_actor(replace(a, hp=0))
    garran = e.actor("garran")
    e.update_actor(replace(garran, features=(*garran.features, FeatureGrant("resonance_hymn", "Hymn odwagi · 1k8", FeatureSourceKind.SCENARIO, "lorian"))))
    e.s.phase = "result"
    assert e.acknowledge()
    assert e.s.phase == "finished"
    s.combat_state = e.combat_state()
    data = resonance.command(s, dict(command="accept", revision=e.s.revision))
    assert s.combat_state is None
    assert data["mission"]["stage"] == "post_battle"
    assert any(f.feature_id == "resonance_hymn" for a in s.exploration.actors if a.id == "garran" for f in a.features)
    from dnd_board_game.ui.exploration_app import _encounter_with_session_actor_state
    from dnd_board_game.combat.charge_encounter import hymn_source, hymn_sides
    refreshed = _encounter_with_session_actor_state(encounter, s.exploration.actors)
    assert hymn_source(next(a for a in refreshed.actors if a.id == "garran")) == "lorian"
    assert hymn_sides(next(a for a in refreshed.actors if a.id == "garran")) == 8


def test_new_profile_removes_legacy_grants_and_preserves_hymn() -> None:
    from dnd_board_game.actors import FeatureGrant, FeatureSourceKind
    from dnd_board_game.application.resonance_combat import apply_charge_profile
    from dnd_board_game.combat.charge_encounter import hymn_sides
    from dnd_board_game.ui.training_arena import training_hero
    for hero_id in ("garran", "brakka", "mira", "dagna", "lorian", "nimra", "erynd"):
        legacy = apply_charge_profile(training_hero(hero_id), profile=LEGACY_PROFILE)
        hymn = FeatureGrant("resonance_hymn", "Hymn odwagi · 1k8", FeatureSourceKind.SCENARIO, "lorian")
        actor = apply_charge_profile(replace(legacy, features=(*legacy.features, hymn)))
        assert actor.hp == legacy.hp and actor.inventory == legacy.inventory
        assert not any(f.source_ref == LEGACY_PROFILE for f in actor.features)
        assert not any(f.feature_id in {"rune_resource_v01", "physical_mana_v02", "mana_passives_v1"} for f in actor.features)
        assert len([f for f in actor.features if f.feature_id == PROFILE]) == 1
        assert len([f for f in actor.features if f.feature_id == f"{PROFILE}_passive"]) == 1
        assert hymn in actor.features and hymn_sides(actor) == 8
        assert apply_charge_profile(actor) == actor


def test_schema_34_restore_keeps_started_legacy_profile(tmp_path: Path) -> None:
    from copy import deepcopy
    from dnd_board_game.application.resonance_combat import apply_charge_profile
    from dnd_board_game.rules.resonance import ResonanceChain, ResonanceEntry
    from dnd_board_game.save.session_snapshot import SessionSnapshot, SNAPSHOT_SCHEMA_VERSION
    s = start_battle(session(tmp_path, legacy_combat=False))
    legacy = deepcopy(s.combat_state.resonance)
    legacy.version, legacy.profile = 1, LEGACY_PROFILE
    legacy.chain = ResonanceChain(1, [ResonanceEntry("Wieża", "garran", "Wieża"),
                                   ResonanceEntry("Fala", "brakka", "Wieża")], ["garran", "brakka"])
    actors = tuple(apply_charge_profile(a, profile=LEGACY_PROFILE) if a.faction.value == "ally" else a
                   for a in s.combat_state.actors)
    s.combat_state = replace(s.combat_state, actors=actors, resonance=legacy)
    raw = s.create_snapshot().as_dict()
    raw["schema_version"] = 34
    raw["combat"]["resonance"].pop("profile")
    restored = SessionSnapshot.from_dict(raw, base_state=s.state)
    assert restored.as_dict()["schema_version"] == SNAPSHOT_SCHEMA_VERSION == 35
    assert restored.combat_state.resonance.version == 1
    assert restored.combat_state.resonance.profile == LEGACY_PROFILE
    assert restored.combat_state.resonance.chain == legacy.chain
    assert restored.combat_state.resonance.queue == legacy.queue
    s.combat_state = restored.combat_state
    assert resonance.engine(s).catalog["profile"] == LEGACY_PROFILE


@pytest.mark.parametrize("card_flag", [True, False])
def test_snapshot_rejects_modified_paid_bonus_before_session_commit(tmp_path: Path, card_flag: bool) -> None:
    import json
    import pytest
    from dnd_board_game.rules.resonance import ResonanceChain, ResonanceEntry
    from dnd_board_game.save.session_snapshot import SnapshotValidationError
    s = start_battle(session(tmp_path, legacy_combat=False))
    e = resonance.engine(s)
    e.s.chain = ResonanceChain(1, [ResonanceEntry("Wieża", "garran", "Wieża")], ["garran"])
    assert e.choose("second_wind") and e.commit()
    assert e.s.action["modifiers"]["self_temp_hp"] == 4
    s.combat_state = e.combat_state()
    before = s.combat_state.resonance.as_payload()
    s.save_snapshot()
    saved = json.loads(s.snapshot_path.read_text(encoding="utf-8"))
    saved["combat"]["resonance"]["action"]["modifiers"]["self_temp_hp"] = 999
    saved["combat"]["resonance"]["action"]["card"] = card_flag
    s.snapshot_path.write_text(json.dumps(saved), encoding="utf-8")
    with pytest.raises(SnapshotValidationError, match="Rezonansu"):
        s.load_snapshot()
    assert s.combat_state.resonance.as_payload() == before
def test_reserved_runes_are_silent_and_loading_rearms_board_context(tmp_path: Path) -> None:
    import pytest
    s = start_battle(session(tmp_path, legacy_combat=False))
    class CountingBoard(Board):
        def __init__(self) -> None:
            super().__init__()
            self.cancellations = 0
        def cancel_scan(self) -> None:
            self.cancellations += 1
    board = CountingBoard()
    s.attach_board_connection(board, backend="simulator")
    s._sync_board_leds()
    old_mask = s._board_selection_payload()
    before = s.combat_state.resonance.as_payload()
    for rune in resonance.engine(s).catalog["rules"]["reserved_runes"]:
        position = panel_position(rune_slot(rune))
        assert position.as_tuple() not in board.leds
        assert position not in resonance.scan_target(s).positions
        with pytest.raises(ValueError, match="dostępny"):
            resonance.select_position(s, position)
    assert s.combat_state.resonance.as_payload() == before
    s.save_snapshot()
    s._board_scan_context_key = old_mask["revision"]
    cancellations = board.cancellations
    s.load_snapshot()
    assert board.cancellations == cancellations + 1
    assert s._board_scan_context_key == ""
    assert s._board_selection_payload()["revision"] != old_mask["revision"]
    assert s.combat_state.resonance.as_payload() == before
    scans = board.scans
    s.scan_board_selection(expected_revision=old_mask["revision"], automatic=True)
    assert board.scans == scans


def test_live_v03_help_and_api_exclude_retired_mana_panels(tmp_path: Path) -> None:
    import json
    from dnd_board_game.scenarios.rune_relation_catalog import load_rune_relation_player_aid
    s = start_battle(session(tmp_path, legacy_combat=False))
    before = s.combat_state.resonance.as_payload()
    response = create_app(s).test_client().get("/api/state")
    assert response.status_code == 200
    data = response.json
    assert data["player_aid"] == load_rune_relation_player_aid()
    aid = json.dumps(data["player_aid"], ensure_ascii=False)
    assert "pamięć trzech run" in aid and "Klepsydra" in aid and "Wieża" in aid
    help_text = data["mission"]["ui"]["combat_help"].lower()
    assert "jeden koszt" in help_text and "ostatnia runa" in help_text
    assert not any(retired in help_text for retired in ("mana", "drain", "6 kart"))
    assert data["combat"]["resonance"]["profile"] == PROFILE
    assert data["combat"]["physical_mana"] is None
    assert data["combat"]["shared_mana"] is None
    for actor in data["combat"]["actors"]:
        if actor["faction"] != "ally":
            continue
        assert not any(feature["source_ref"].startswith(("physical_mana:", "shared_mana:", "runes:", "mana_saturation:"))
                       or feature["source_ref"] == LEGACY_PROFILE for feature in actor["features"])
        assert len([feature for feature in actor["features"] if feature["id"] == f"{PROFILE}_passive"]) == 1
    assert s.combat_state.resonance.as_payload() == before
