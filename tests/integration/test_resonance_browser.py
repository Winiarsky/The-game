"""Actual /play, automatic physical scans and compact laptop presentation."""
from pathlib import Path
from threading import Event, Thread
from typing import Any
import shutil
import subprocess

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui.routes import create_app
from tests.unit.test_mission_zero import session, start_battle
from tests.unit.test_tabletop_combat_browser import CombatBoard


@pytest.mark.parametrize("width,height", [(1366, 768), (1131, 720)])
def test_real_panel_dice_and_no_laptop_scrolling(tmp_path: Path, width: int, height: int) -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        pytest.skip("Chrome required")
    from dnd_board_game.ui.training_arena import training_hero
    game = session(tmp_path, 6, legacy_combat=False)
    game.configure_custom_party(tuple(training_hero(key) for key in ("garran", "brakka", "dagna", "mira", "lorian", "nimra")))
    game = start_battle(game)
    board = CombatBoard()
    game.attach_board_connection(board, backend="simulator")
    app = create_app(game, character_dir=tmp_path / "characters")
    done, report = Event(), {}

    @app.post("/__test/press")
    def press() -> dict[str, Any]:
        return dict(delivered=board.press_field(tuple(request.get_json()["position"])))

    @app.post("/__test/result")
    def result() -> dict[str, bool]:
        report.update(request.get_json())
        done.set()
        return dict(ok=True)

    @app.post("/__test/dense")
    def dense() -> dict[str, Any]:
        from dnd_board_game.ui import resonance
        e = resonance.engine(game)
        e.s.index = e.s.order.index("nimra")
        e.s.queue.clear()
        e.s.task = e.s.action = e.s.preview = None
        e.s.phase = "idle"
        e.begin_turn()
        for rune in e.catalog["rules"]["starter_runes"]:
            e.add_rune("nimra", rune)
        e.s.queue.clear()
        e.s.task = None
        e.s.phase = "idle"
        game.combat_state = e.combat_state()
        return game.state_payload()

    harness = r"""<script>
(async()=>{
 const check=(v,m)=>{if(!v)throw Error(m)};
 const wait=async(f,m)=>{for(let i=0;i<250;i++){if(f())return;await new Promise(r=>setTimeout(r,20))}throw Error('timeout '+m)};
 const v=()=>state.combat.resonance;
 const bounds=label=>{
   const box=document.querySelector('.rc-combat').getBoundingClientRect();
   check(box.bottom<=innerHeight+2,label+' bottom '+box.bottom+'/'+innerHeight);
   check(document.documentElement.scrollWidth<=innerWidth,label+' horizontal overflow');
   for(const s of document.querySelectorAll('.rc-main,.rc-decision,.rc-roster'))check(s.scrollHeight<=s.clientHeight+2,label+' internal overflow '+s.className+' '+s.scrollHeight+'/'+s.clientHeight);
 };
 const slot=async n=>{
   await wait(()=>boardScanInFlight&&!busy&&!boardPanelSyncPromise,'arm '+n);
   const revision=v().revision;
   let delivered=false;
   for(let i=0;i<150&&!delivered;i++){
     delivered=(await(await fetch('/__test/press',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({position:[19,29-n]})})).json()).delivered;
     if(!delivered)await new Promise(r=>setTimeout(r,20));
   }
   check(delivered,'delivery '+n);
   await wait(()=>v().revision!==revision&&!busy&&!boardPanelSyncPromise,'resolved '+n);
 };
 try {
   await wait(()=>state?.combat?.resonance&&!busy&&document.querySelector('.rc-combat'),'opening');
   check(v().active==='garran','Garran first');
   check(document.querySelectorAll('.rc-powers button').length===4,'Garran powers');
   check(document.querySelectorAll('.rc-powers svg').length===4,'rune icons');
   check(!document.querySelector('.tt-legal-targets'),'no redundant field list');
   bounds('idle');
   await slot(25);check(v().decision.inspected==='garran','star');bounds('info');
   await slot(26);check(v().decision.title==='Żywa osłona','passive page');bounds('passive');
   await slot(29);await slot(12);bounds('preview'); // Błysk / Żar odnowy
   await slot(26);await slot(28);check(v().decision.die.sides===4,'flash before power');bounds('flash die');
   await slot(26);check(v().decision.die.value===2,'physical plus');
   await slot(28);check(v().decision.die.sides===10,'second independent die');bounds('heal die');
   await slot(28);check(v().phase==='result','result');bounds('result');
   await slot(28);check(v().chain.bonuses[0].text.includes('1k4'),'numeric resonance bonus');bounds('chain idle');
   await slot(3);await slot(28);check(v().active!=='garran','next actor');bounds('next turn');
   await stopBoardScanLoop();
   state=await(await fetch('/__test/dense',{method:'POST'})).json();render();
   check(document.querySelectorAll('.rc-bonuses>span').length===9,'all nine effects');
   check(document.querySelectorAll('.rc-powers button').length===5,'Nimra five powers');bounds('dense resonance');
   await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
 }catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack,body:document.body.innerText.slice(-2500),phase:boardInputPhase,error:boardScanError})})}
})();</script>"""
    error_hook = """<script>window.alert=message=>{throw Error(message)};window.addEventListener('error',e=>fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:String(e.message)+' '+e.filename+':'+e.lineno})}));</script>"""

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
        process = subprocess.Popen([chrome, "--headless", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage", "--no-first-run",
            "--disable-background-networking", "--no-proxy-server", f"--user-data-dir={tmp_path / 'chrome'}", f"--window-size={width},{height}",
            f"http://127.0.0.1:{server.server_port}/play"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert done.wait(45), "Browser did not report"
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
