"""Real mission session, command locking, saves and board adapter."""
from pathlib import Path
from dataclasses import replace

from dnd_board_game.ui import resonance
from dnd_board_game.ui.routes import create_app
from tests.unit.test_mission_zero import session, start_battle
from tests.unit.test_initiative_panel import Board
from dnd_board_game.hardware.board_panel import panel_position
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.ui.board_panel_symbols import rune_slot


def test_mission_starts_new_profile_and_rejects_stale_commands(tmp_path: Path) -> None:
    s = start_battle(session(tmp_path, legacy_combat=False))
    assert s.combat_state.resonance is not None
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
    press(26)
    press(28)
    assert s.combat_state.resonance.fighters["garran"].charges == 12
    press(26)
    assert s.combat_state.resonance.die_value == 2
    before = s.combat_state.resonance.as_payload()
    s.save_snapshot()
    s.load_snapshot()
    assert s.combat_state.resonance.as_payload() == before
    press(28)
    assert s.combat_state.resonance.task["parts"][0]["sides"] == 10
    assert s.combat_state.resonance.die_value == 1


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
    e.update_actor(replace(garran, features=(*garran.features, FeatureGrant("resonance_hymn", "Hymn", FeatureSourceKind.SCENARIO, "lorian"))))
    e.s.phase = "result"
    assert e.acknowledge()
    assert e.s.phase == "finished"
    s.combat_state = e.combat_state()
    data = resonance.command(s, dict(command="accept", revision=e.s.revision))
    assert s.combat_state is None
    assert data["mission"]["stage"] == "post_battle"
    assert any(f.feature_id == "resonance_hymn" for a in s.exploration.actors if a.id == "garran" for f in a.features)
    from dnd_board_game.ui.exploration_app import _encounter_with_session_actor_state
    from dnd_board_game.combat.charge_encounter import hymn_source
    refreshed = _encounter_with_session_actor_state(encounter, s.exploration.actors)
    assert hymn_source(next(a for a in refreshed.actors if a.id == "garran")) == "lorian"
