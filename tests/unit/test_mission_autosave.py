"""Stage autosaves resume rewards, results and consequences without replay."""
from dataclasses import replace
from pathlib import Path

import pytest

from dnd_board_game.ui import mission_zero as mission, confrontation
from dnd_board_game.ui.exploration_app import ExplorationUiSession
from tests.unit.test_mission_zero import PACK, session, stage, send, start_battle, prepare_runes


def restored(original: ExplorationUiSession) -> ExplorationUiSession:
    loaded = ExplorationUiSession(PACK/'scenario.json', save_dir=original.save_dir,
                                  observation_dir=original.save_dir.parent/'reload_logs')
    loaded.load_snapshot()
    return loaded


def conclude(s: ExplorationUiSession, outcome: str) -> None:
    store = confrontation.read_store(s)
    store['current']['state'].update(stage='result', outcome=outcome)
    confrontation.write(s, store)
    confrontation.command(s, dict(action='next', revision=confrontation.read_store(s)['revision']))


@pytest.mark.parametrize('outcome,item', [('success','mission_potion'),('compromise','mission_weak_potion'),('failure',None)])
def test_nessa_updates_latest_save_but_preserves_start_checkpoint(tmp_path: Path, outcome: str, item: str | None) -> None:
    s = session(tmp_path)
    stage(s,'brief'); mission.checkpoint(s,mission.read(s))
    checkpoint = s.save_dir/'misja_0_dzwon.brief.checkpoint.json'
    initial = checkpoint.read_bytes()
    send(s,'negotiate'); conclude(s,outcome)
    loaded = restored(s)
    assert mission.read(loaded)['stage']=='brief'
    assert 'negotiated' in mission.read(loaded)['flags']
    assert [i.id for i in loaded.state.party_loot.items] == ([item] if item else [])
    assert checkpoint.read_bytes()==initial
    with pytest.raises(ValueError): send(loaded,'negotiate')
    before = s.snapshot_path.stat().st_mtime_ns
    s.state_payload(); s.state_payload()
    assert s.snapshot_path.stat().st_mtime_ns==before


@pytest.mark.parametrize('outcome', ['success','failure'])
def test_cart_result_and_fatigue_roll_are_saved(tmp_path: Path, outcome: str) -> None:
    s=session(tmp_path);stage(s,'road');send(s,'cart');conclude(s,outcome)
    loaded=restored(s)
    assert mission.read(loaded)['stage']==('road_success' if outcome=='success' else 'fatigue_roll')
    if outcome=='failure':
        send(loaded,'roll',roll=4)
        again=restored(loaded)
        assert mission.read(again)['fatigue']==4 and mission.read(again)['stage']=='fatigue_result'


def test_completed_confrontation_is_saved_before_leaving_result(tmp_path: Path) -> None:
    from tests.unit.test_progress_confrontation_runtime import start, attempt, command
    s=session(tmp_path);start(s)
    for index in range(3):
        attempt(s,14 if index==0 else 2);command(s,'confirm')
        if index<2:command(s,'advance')
    loaded=restored(s)
    store=confrontation.read_store(loaded)
    assert store['active'] and store['current']['state']['outcome']=='compromise'
    assert not loaded.state.party_loot.items
    confrontation.command(loaded,dict(action='next',revision=store['revision']))
    again=restored(loaded)
    assert [i.id for i in again.state.party_loot.items]==['mission_weak_potion']


def test_coerced_cart_preserves_choice_and_party_ethos(tmp_path: Path) -> None:
    from dnd_board_game.application import party_ethos
    s=session(tmp_path);stage(s,'road');send(s,'cart_coerce');send(s,'cart_exchange_confirm')
    loaded=restored(s)
    assert mission.read(loaded)['stage']=='cart_coerced'
    assert 'cart_exchanged' in mission.read(loaded)['flags']
    assert party_ethos.read(loaded.state.flags)==party_ethos.read(s.state.flags)


def test_truce_saves_completed_combat_before_exploration_setup(tmp_path: Path) -> None:
    s=start_battle(session(tmp_path));prepare_runes(s)
    enemy=next(a for a in s.combat_state.actors if a.faction.value=='enemy')
    s.combat_state=replace(s.combat_state,actors=tuple(replace(a,hp=0) if a.id==enemy.id else a for a in s.combat_state.actors))
    s.state_payload();send(s,'accept')
    loaded=restored(s)
    assert loaded.combat_state is None
    assert mission.read(loaded)['stage']=='post_battle'
    assert mission.read(loaded)['outcome']=='accepted'
    assert 'bell_battle' in loaded.resolved_encounter_trigger_ids


def test_active_progress_confrontation_is_saved_without_overwriting_start_checkpoint(tmp_path: Path) -> None:
    s=session(tmp_path);stage(s,'brief');mission.checkpoint(s,mission.read(s))
    checkpoint=s.save_dir/'misja_0_dzwon.brief.checkpoint.json'
    initial=checkpoint.read_bytes()
    send(s,'negotiate')
    assert mission.autosave(s)
    loaded=restored(s)
    assert confrontation.read_store(loaded)['current']['engine']=='progress_v1'
    assert checkpoint.read_bytes()==initial
