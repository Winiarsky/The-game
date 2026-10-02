"""Target context and stable dice entry through the real physical scan transport."""
from dataclasses import replace
from pathlib import Path
from threading import Event, Thread
from typing import Any
import shutil
import subprocess

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui import resonance
from dnd_board_game.ui.routes import create_app
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.world import Coordinate, line_of_sight_clear
from dnd_board_game.world.charge_movement import distance
from dnd_board_game.combat.scene import SceneObject
from tests.unit.test_mission_zero import session, start_battle
from tests.unit.test_tabletop_combat_browser import CombatBoard


@pytest.mark.parametrize("width,height", [(1268, 736), (1131, 720)])
def test_actions_target_and_dice_stay_visible_without_replacing_controls(
    tmp_path: Path, width: int, height: int, monkeypatch: pytest.MonkeyPatch,
) -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        pytest.skip("Chrome required")
    game = session(tmp_path, legacy_combat=False)
    game.configure_custom_party(tuple(training_hero(key) for key in ("erynd", "nimra", "brakka")))
    game = start_battle(game)
    engine = resonance.engine(game)
    engine.s.index = engine.s.order.index("erynd")
    engine.s.queue.clear()
    engine.s.task = engine.s.action = engine.s.preview = None
    engine.s.phase = "idle"
    engine.begin_turn()
    target = engine.enemies()[0]
    position = next(
        pos for col in range(19) for row in range(30)
        if 2 <= distance(engine.active.position, pos := Coordinate(col, row)) <= 4
        and engine.free(pos, str(target.id))
        and line_of_sight_clear(engine.board, engine.active.position, pos)
    )
    engine.update_actor(replace(target, position=position))
    encounter = game._active_encounter()
    cover = SceneObject("test_cover", "Niski murek", (position,), "", cover_bonus=2)
    monkeypatch.setattr(game, "_active_encounter", lambda: replace(encounter, scene_objects=(*encounter.scene_objects, cover)))
    engine.fighter("erynd").mark = str(target.id)
    engine.add_status(str(target.id), "broken", until_end="erynd")
    engine.s.revision += 1
    game.combat_state = engine.combat_state()
    board = CombatBoard()
    game.attach_board_connection(board, backend="simulator")
    app = create_app(game, character_dir=tmp_path / "characters")
    done, report = Event(), {}

    @app.post("/__test/press")
    def press() -> dict[str, bool]:
        return dict(delivered=board.press_field(tuple(request.get_json()["position"])))

    @app.get("/__test/target")
    def target_details() -> dict[str, Any]:
        return dict(id=str(target.id), position=list(position))

    @app.post("/__test/result")
    def result() -> dict[str, bool]:
        report.update(request.get_json())
        done.set()
        return dict(ok=True)

    harness = r"""<script>
(async()=>{
 const check=(value,message)=>{if(!value)throw Error(message)};
 const wait=async(fn,label)=>{for(let i=0;i<250;i++){if(fn())return;await new Promise(r=>setTimeout(r,20))}throw Error('timeout '+label)};
 const v=()=>state.combat.resonance;
 const bounds=label=>{
   const root=document.querySelector('.rc-combat');
   check(root.getBoundingClientRect().bottom<=innerHeight+2,label+' viewport bottom');
   check(document.documentElement.scrollWidth<=innerWidth,label+' horizontal overflow');
   for(const el of root.querySelectorAll('.rc-main,.rc-decision,.rc-roster,.rc-decision-content'))
     check(el.scrollHeight<=el.clientHeight+2,label+' overflow '+el.className+' '+el.scrollHeight+'/'+el.clientHeight);
 };
 const press=async position=>{
   await wait(()=>boardScanInFlight&&!busy&&!boardPanelSyncPromise,'armed '+position);
   const revision=v().revision;
   let delivered=false;
   for(let i=0;i<150&&!delivered;i++){
     delivered=(await(await fetch('/__test/press',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({position})})).json()).delivered;
     if(!delivered)await new Promise(r=>setTimeout(r,20));
   }
   check(delivered,'physical input delivered');
   await wait(()=>v().revision!==revision&&!busy&&!boardPanelSyncPromise,'physical input resolved');
 };
 const slot=n=>press([19,29-n]);
 try {
   await wait(()=>state?.combat?.resonance&&!busy&&document.querySelector('.rc-combat'),'opening');
   const target=await(await fetch('/__test/target')).json();
   check(v().active==='erynd','Erynd active');
   check(v().basic_actions.length===4,'four basic actions exposed');
   check(document.querySelectorAll('.rc-basic-actions button').length===4,'all basic actions visible');
   for(const action of v().basic_actions){
     const button=document.querySelector('.rc-basic-actions [data-rc-slot="'+action.slot+'"]');
     check(Boolean(button.disabled)===Boolean(action.disabled),'availability follows rules '+action.id);
     if(action.disabled)check(button.title===action.disabled,'disabled action reason');
   }
   bounds('idle');
   await slot(1);await press(target.position);bounds('target');
   const card=document.querySelector('.rc-target-card');
   check(card?.dataset.rcTarget===target.id,'selected target card');
   check(card.querySelector('.tt-portrait').getBoundingClientRect().width>=100,'large portrait');
   check(card.innerText.includes('Piętno łowcy'),'hunter mark visible on target');
   check(card.innerText.includes('Przełamana obrona'),'other effects visible');
   check(card.innerText.includes('PW')&&card.innerText.includes('KP'),'target defenses and health');
   await slot(28);bounds('attack roll');
   check(v().decision.die.sides===20&&v().decision.die.value===10,'attack die starts at midpoint');
   check(v().decision.cover_text.includes('+2 KP')&&v().decision.cover_text.includes('Niski murek'),'authored cover enters attack');
   check(document.querySelector('.rc-cover-summary').textContent===v().decision.cover_text,'cover reason visible beside roll');
   check(document.querySelector('.rc-target-card')?.dataset.rcTarget===target.id,'target retained during roll');
   const root=document.querySelector('.rc-combat'),output=document.querySelector('.rc-die-controls output');
   const plus=document.querySelector('.rc-die-controls [data-rc-slot="26"]');
   plus.focus();
   await slot(26);
   check(v().decision.die.value===11,'physical plus');
   check(document.querySelector('.rc-combat')===root&&document.querySelector('.rc-die-controls output')===output,'physical plus updates in place');
   check(document.activeElement===plus,'physical plus preserves focus');
   await slot(27);check(output.textContent==='10','physical minus updates existing output');
   const revision=v().revision;
   plus.click();
   check(document.getElementById('status').hidden&&!plus.disabled,'screen plus has no flashing busy overlay');
   await wait(()=>v().revision!==revision&&!busy,'screen plus');
   check(document.querySelector('.rc-combat')===root&&document.activeElement===plus,'screen plus preserves DOM and focus');
   check(output.textContent==='11','screen plus updates value');bounds('adjusted roll');
   await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
 }catch(error){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:error.stack,body:document.body.innerText.slice(-3500),view:state?.combat?.resonance?.decision})})}
})();</script>"""
    error_hook = """<script>window.alert=message=>{throw Error(message)};window.addEventListener('error',event=>fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:event.message+' '+event.filename+':'+event.lineno})}));</script>"""

    @app.after_request
    def inject(response: Any) -> Any:
        if request.path == "/play" and response.status_code == 200:
            response.set_data(response.get_data(as_text=True).replace("<head>", "<head>"+error_hook).replace("</body>", harness+"</body>"))
        return response

    server = make_server("127.0.0.1", 0, app, threaded=True)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    process = None
    try:
        process = subprocess.Popen([
            chrome, "--headless", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
            "--no-first-run", "--disable-background-networking", "--no-proxy-server",
            f"--user-data-dir={tmp_path / 'chrome'}", f"--window-size={width},{height}",
            f"http://127.0.0.1:{server.server_port}/play",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert done.wait(35), "Browser did not report"
        assert report.get("result") == "PASS", report
    finally:
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        board.cancel_scan()
        server.shutdown()
        worker.join(timeout=2)
