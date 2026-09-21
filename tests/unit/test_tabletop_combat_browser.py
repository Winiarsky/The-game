"""Real /play, real combat transport: board inspection never resolves a target."""
from dataclasses import replace
from pathlib import Path
from threading import Event, Thread
import shutil
import subprocess

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui.routes import create_app
from dnd_board_game.world import Coordinate
from tests.unit.test_mission_zero import session, start_battle


@pytest.mark.parametrize("width", [1131, 1300])
def test_real_combat_board_flow_and_mana_layout(tmp_path: Path, width: int) -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        pytest.skip("Chrome required")
    game = session(tmp_path, 6)
    game.encounter_rng.seed(0)
    start_battle(game)
    game.configured_board_backend = "none"
    hero = next(actor for actor in game.combat_state.actors if str(actor.id) == "garran")
    target_position = Coordinate(hero.position.col - 1, hero.position.row)
    assert target_position not in {actor.position for actor in game.combat_state.actors}
    game.combat_state = replace(game.combat_state, actors=tuple(
        replace(actor, position=target_position) if str(actor.id) == "borut" else actor
        for actor in game.combat_state.actors))
    app = create_app(game, character_dir=tmp_path / "characters")
    done = Event()
    report: dict = {}

    @app.get("/__test/snapshot")
    def snapshot():
        return {"value": repr((game.combat_state, game.active_combat_effects,
                               game.pending_player_attack, game.combat_turn_preview_option_id))}

    @app.post("/__test/result")
    def result():
        report.update(request.get_json())
        done.set()
        return {"ok": True}

    harness = r'''<script>
(async()=>{
const check=(v,m)=>{if(!v)throw Error(m)};
const wait=async f=>{for(let i=0;i<160;i++){if(f())return;await new Promise(r=>setTimeout(r,25))}throw Error('timeout '+f)};
const panel=async()=>{await wait(()=>!busy&&!boardPanelSyncPromise);const p=desiredBoardPanel();if(!p)return;
 const r=await fetch('/api/board/panel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...p,revision:state.board_selection.revision})});const d=await r.json();check(r.ok,d.error);state.board_selection=d.board_selection};
const field=async(col,row)=>{await wait(()=>!busy&&!boardPanelSyncPromise);const r=await api('/api/board/select',{col,row},'');check(r.ok,'field failed');await wait(()=>!busy)};
const slot=async n=>{await panel();await field(19,29-n)};
const snapshot=async()=>JSON.stringify(await (await fetch('/__test/snapshot')).json());
const bounds=()=>{check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');const d=document.querySelector('.tt-decision');check(d.scrollHeight<=d.clientHeight+2,'decision overflow');};
try{
 await wait(()=>state?.combat?.tabletop&&!busy);
 check(state.combat.current_actor.id==='garran','expected Garran first');
 check(document.querySelectorAll('.tt-actor').length===14,'full vertical initiative');
 check(document.querySelectorAll('.tt-atlas').length===8,'eight opponent portraits');
 check(!document.querySelector('.initiative-ribbon'),'no duplicate initiative');
 await field(19,1);await wait(()=>state.combat.shared_mana.pool_view.phase==='reveal');
 await field(19,23);await field(19,19);await wait(()=>state.combat.shared_mana.pool_view.phase==='choose');
 const choices=[...document.querySelectorAll('[data-tt-pool-choice]')];
 check(choices.length===2,'two mana choices');
 check(choices.every(el=>el.querySelector('.tt-pool-symbol svg')),'symbol for each offered mana');
 const modal=document.querySelector('.tt-pool-step');check(modal.scrollHeight<=modal.clientHeight+2,'mana choices clipped');
 check(choices.every(el=>el.getBoundingClientRect().bottom<=innerHeight),'mana button below viewport');
 await field(19,5);await wait(()=>state.combat.shared_mana.pool_view.phase==='ready');
 check(document.querySelector('.tt-idle').textContent.includes('Wybierz akcję'),'clean idle');
 const before=await snapshot();await slot(27);await wait(()=>TabletopCombat.getView().inspected);
 check(TabletopCombat.panel().exclusive,'inspection has exclusive functional controls');
 check(document.querySelector('.tt-actor.is-active').dataset.ttActor==='garran','inspection changed current turn');
 await slot(29);await wait(()=>!TabletopCombat.getView().inspected);check(before===await snapshot(),'inspection changed engine state');
 await slot(1);await wait(()=>state.combat.turn_action_menu?.stage==='preview');
 check(desiredBoardPanel().slots.includes(28)&&desiredBoardPanel().slots.includes(29),'preview needs both controls');
 await slot(27);await wait(()=>TabletopCombat.getView().inspected);await slot(29);await wait(()=>!TabletopCombat.getView().inspected);
 check(state.combat.turn_action_menu.stage==='preview','inspection lost action');
 await panel();const target=state.combat.actors.find(a=>a.id==='borut');await field(...target.position);
 await wait(()=>state.combat.pending_player_attack?.stage==='confirm_attack');
 check(document.querySelector('.tt-target').dataset.ttTarget==='borut','preview selected wrong figure');
 check(!document.querySelector('.tt-action'),'target dominated by previous large header');bounds();
 const targetBefore=await snapshot();await slot(27);await wait(()=>TabletopCombat.getView().inspected);await slot(29);await wait(()=>!TabletopCombat.getView().inspected);
 check(targetBefore===await snapshot(),'target inspection changed target/resources');
 await slot(29);await wait(()=>!state.combat.pending_player_attack);check(!state.combat.shared_mana.declaration,'cancel spent cards');
 await slot(1);await wait(()=>state.combat.turn_action_menu?.stage==='preview');await panel();await field(...target.position);await wait(()=>state.combat.pending_player_attack?.stage==='confirm_attack');
 await slot(28);await wait(()=>state.combat.pending_player_attack?.stage==='attack_roll'&&keyboardRollWizard);
 check(!TabletopCombat.canBrowse(),'inspection stole dice controls');check(desiredBoardPanel().context.startsWith('dice:'),'dice must own panel');
 await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
}catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack,body:document.body.innerText.slice(-1800)})})}
})();</script>'''
    error_hook = """<script>window.alert=message=>{throw Error(message)};window.addEventListener('error',e=>fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:String(e.message)+' '+e.filename+':'+e.lineno})}));</script>"""

    @app.after_request
    def inject(response):
        if request.path == "/play" and response.status_code == 200:
            response.set_data(response.get_data(as_text=True).replace("<head>", "<head>" + error_hook).replace("</body>", harness + "</body>"))
        return response

    server = make_server("127.0.0.1", 0, app, threaded=True)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    process = None
    try:
        process = subprocess.Popen([
            chrome, "--headless", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
            "--no-first-run", "--disable-background-networking", "--no-proxy-server",
            f"--user-data-dir={tmp_path / 'chrome'}", f"--window-size={width},863",
            f"http://127.0.0.1:{server.server_port}/play"], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        assert done.wait(40), "Browser did not report"
        assert report.get("result") == "PASS", report
    finally:
        if process:
            process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5)
        server.shutdown()
        worker.join(timeout=2)
