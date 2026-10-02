"""A rejected physical command reports the error and waits for a fresh press."""
from pathlib import Path
from threading import Event, Thread
from typing import Any
import shutil
import subprocess
import time

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui.routes import create_app
from dnd_board_game.world import Coordinate
from tests.unit.test_mission_zero import session, start_battle
from tests.unit.test_tabletop_combat_browser import CombatBoard


def test_rejected_command_rearms_without_replay_and_transport_error_waits_for_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        pytest.skip("Chrome required")
    game = start_battle(session(tmp_path, legacy_combat=False))
    board = CombatBoard()
    game.attach_board_connection(board, backend="simulator")
    app = create_app(game, character_dir=tmp_path / "characters")
    done, report = Event(), {}
    control: dict[str, Any] = dict(failure="command", handled=[], rejected_at=0)
    handle = game._handle_board_position

    def reject_once(position: Coordinate) -> dict[str, object]:
        control["handled"].append(list(position))
        if control["failure"] == "command" and position == Coordinate(19, 1):
            control.update(failure="", rejected_at=time.monotonic())
            raise ValueError("Bieżący wybór wymaga ponownego wskazania.")
        if control["failure"] == "transport":
            control["failure"] = ""
            raise ConnectionError("Utracono połączenie z kontrolerem.")
        return handle(position)

    monkeypatch.setattr(game, "_handle_board_position", reject_once)

    @app.post("/__test/press")
    def press() -> dict[str, bool]:
        return dict(delivered=board.press_field(tuple(request.get_json()["position"])))

    @app.get("/__test/handled")
    def handled() -> dict[str, Any]:
        return dict(count=len(control["handled"]), since_rejected=time.monotonic()-control["rejected_at"])

    @app.post("/__test/transport")
    def fail_transport() -> dict[str, bool]:
        control["failure"] = "transport"
        return dict(ok=True)

    @app.post("/__test/result")
    def result() -> dict[str, bool]:
        report.update(request.get_json())
        done.set()
        return dict(ok=True)

    harness = r"""<script>
(async()=>{
 const check=(value,message)=>{if(!value)throw Error(message)};
 const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
 const wait=async(fn,label)=>{for(let i=0;i<300;i++){if(fn())return;await pause(20)}throw Error('timeout '+label)};
 const v=()=>state.combat.resonance;
 const deliver=async slot=>{
   await wait(()=>boardScanInFlight&&!busy&&!boardPanelSyncPromise,'armed '+slot);
   let delivered=false;
   for(let i=0;i<150&&!delivered;i++){
     delivered=(await(await fetch('/__test/press',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({position:[19,29-slot]})})).json()).delivered;
     if(!delivered)await pause(20);
   }
   check(delivered,'physical press delivered');
 };
 const slot=async n=>{const revision=v().revision;await deliver(n);await wait(()=>v().revision!==revision&&!busy,'changed '+n)};
 try {
   await wait(()=>state?.combat?.resonance&&!busy&&document.querySelector('.rc-combat'),'opening');
   await slot(12);
   const before=JSON.stringify(v()), revision=v().revision;
   await deliver(28);
   await wait(()=>boardCommandError&&document.querySelector('.rc-board-error')?.hidden===false,'visible command rejection');
   check(document.querySelector('.rc-board-error').innerText.includes('ponownego wskazania'),'error reason visible');
   check(v().revision===revision&&JSON.stringify(v())===before,'rejection left combat unchanged');
   await wait(()=>boardScanInFlight&&boardInputPhase==='listening','automatic rearm');
   const recovered=await(await fetch('/__test/handled')).json();
   check(recovered.count===2,'rearm did not replay rejected accept');
   check(recovered.since_rejected>=.6,'bounded retry delay');
   await pause(900);
   check((await(await fetch('/__test/handled')).json()).count===2,'waits for a new physical press');
   check(!document.querySelector('.rc-board-error').hidden,'reason remains visible while waiting');
   await slot(29);
   check(v().phase==='idle'&&v().actors.find(a=>a.id==='garran').charges===20,'physical back works without paying');
   check(document.querySelector('.rc-board-error').hidden,'successful command clears notice');
   await slot(12);await slot(28);
   check(v().decision.die.value===5,'fresh command reaches healing roll');
   check(v().actors.find(a=>a.id==='garran').charges===16,'exactly one successful charge payment');
   await fetch('/__test/transport',{method:'POST'});
   await deliver(26);
   await wait(()=>boardInputPhase==='error'&&!boardScanInFlight,'transport error');
   check(!boardCommandError,'transport failure not treated as command rejection');
   check(!document.querySelector('.rc-board-error').hidden,'transport error visible');
   check(!document.querySelector('[data-rc-scan-retry]').hidden,'manual retry visible');
   const handledBefore=(await(await fetch('/__test/handled')).json()).count;
   await pause(1100);
   check(!boardScanInFlight,'transport does not auto rearm');
   check((await(await fetch('/__test/handled')).json()).count===handledBefore,'no transport replay');
   document.querySelector('[data-rc-scan-retry]').click();
   await wait(()=>boardScanInFlight&&boardInputPhase==='listening','manual retry rearmed');
   check(v().decision.die.value===5,'retry did not repeat plus');
   await slot(26);check(v().decision.die.value===6,'fresh plus after manual retry');
   check(document.querySelector('.rc-board-error').hidden,'transport notice cleared');
   await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
 }catch(error){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:error.stack,body:document.body.innerText.slice(-3000),phase:boardInputPhase,scanError:boardScanError,commandError:boardCommandError})})}
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
            f"--user-data-dir={tmp_path / 'chrome'}", "--window-size=1268,736",
            f"http://127.0.0.1:{server.server_port}/play",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert done.wait(40), "Browser did not report"
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
