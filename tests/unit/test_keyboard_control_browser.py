"""Keyboard events exercise the real browser, preview transport and combat UI."""
from pathlib import Path
import shutil
import subprocess
from threading import Event, Thread
from typing import Any

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui.routes import create_app
from tests.integration.test_combat_board_feedback import combat


def test_keyboard_preview_commit_panels_and_action_menu(tmp_path: Path) -> None:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        pytest.skip("Chrome required for browser input check")
    game, board, _, _ = combat(tmp_path)
    game.configure_input_mode("keyboard")
    scans: list[object] = []
    original_scan = getattr(board, "scan_board", None)

    def unexpected_scan(*args: object, **kwargs: object) -> object:
        scans.append((args, kwargs))
        if original_scan:
            return original_scan(*args, **kwargs)
        raise AssertionError("Keyboard mode must not scan the board")

    board.scan_board = unexpected_scan
    app = create_app(game, character_dir=tmp_path / "characters")
    done = Event()
    report: dict[str, Any] = {}

    @app.get("/__test/domain")
    def domain() -> dict[str, str]:
        return {"value": repr(game.combat_state)}

    @app.post("/__test/result")
    def result() -> dict[str, bool]:
        report.update(request.get_json())
        done.set()
        return {"ok": True}

    harness = r'''<script>
    (async()=>{
      const check=(value,message)=>{if(!value)throw Error(message)};
      const pause=()=>new Promise(resolve=>setTimeout(resolve,20));
      const wait=async(predicate,message)=>{
        for(let i=0;i<350;i++){if(predicate())return;await pause();}
        throw Error('timeout '+message);
      };
      const key=(value,repeat=false)=>{
        const code=value.length===1 ? 'Key'+value.toUpperCase() : value;
        (document.activeElement||document.body).dispatchEvent(new KeyboardEvent('keydown',{
          key:value,code,bubbles:true,cancelable:true,repeat,
        }));
        document.dispatchEvent(new KeyboardEvent('keyup',{key:value,code,bubbles:true}));
      };
      const settle=()=>wait(()=>!busy&&document.querySelector('[data-keyboard-sync]').hidden,'input idle');
      const snapshot=async()=>JSON.stringify(await(await fetch('/__test/domain')).json());
      const actor=()=>state.combat.resonance.actors.find(actor=>actor.id==='erynd');
      try {
        window.alert=message=>{throw Error('Unexpected alert: '+message)};
        await wait(()=>state?.input?.mode==='keyboard'&&!busy,'keyboard mode');
        check(!state.board_selection.auto_arm,'scanner automatically armed');
        check(!document.getElementById('keyboard-control-bar').hidden,'keyboard instructions missing');
        state.board.led_output={pending:true,error:'Próba: WLED bez odpowiedzi'};
        renderBoardConnectionIndicator();
        const indicator=document.getElementById('board-connection-indicator');
        check(indicator.textContent.includes('LED-y niedostępne'),'offline LEDs reported connected');
        check(indicator.title.includes('WLED bez odpowiedzi'),'LED error explanation missing');
        const origin=JSON.stringify(actor().position);
        key('m');
        await wait(()=>state.input.kind==='map'&&!busy,'movement preview');
        const preview=await snapshot();
        for(const [direction,expected] of [
          ['ArrowRight',[3,2]], ['ArrowLeft',[3,3]],
          ['ArrowDown',[4,3]], ['ArrowUp',[3,3]], ['ArrowUp',[2,3]],
        ]){
          key(direction);await settle();
          check(JSON.stringify(state.input.cursor)===JSON.stringify(expected),
            'board orientation incorrect for '+direction+': '+JSON.stringify(state.input.cursor));
        }
        check(JSON.stringify(state.input.cursor)!==origin,'arrows did not move cursor');
        check(document.querySelector('[data-keyboard-status]').textContent.includes('Koszt ruchu:'),'movement preview cost missing');
        check(JSON.stringify(actor().position)===origin,'preview moved actor');
        check(await snapshot()===preview,'arrow changed authoritative combat state');
        key('Tab');
        document.querySelector('.rc-actions [data-rc-slot="29"]').focus();
        key('Enter');await wait(()=>state.combat.resonance.phase==='idle'&&!busy,'explicit Tab control');
        check(JSON.stringify(actor().position)===origin,'Tab-focused Back committed movement');
        key('m');await wait(()=>state.input.kind==='map'&&!busy,'preview for Escape');
        key('ArrowUp');await settle();
        key('Escape');await wait(()=>state.combat.resonance.phase==='idle'&&!busy,'cancel');
        check(JSON.stringify(actor().position)===origin,'cancel changed position');
        key('m');await wait(()=>state.input.kind==='map'&&!busy,'second preview');
        key('ArrowUp');await settle();
        const target=JSON.stringify(state.input.cursor);
        key('Enter');await wait(()=>JSON.stringify(actor().position)===target&&!busy,'commit movement');
        const committed=await snapshot();
        key('Enter',true);await pause();
        check(await snapshot()===committed,'repeated Enter performed another action');
        check(state.combat.resonance.phase==='result','movement did not keep its existing result acknowledgement');
        key('Enter');await wait(()=>state.combat.resonance.phase==='idle'&&!busy,'acknowledge movement result');
        const idle=await snapshot();
        key('Tab');document.getElementById('side-panel-toggle').focus();
        key('Enter');
        check(document.getElementById('session-navigation')?.open,'Tab-focused header menu did not open');
        key('Escape');
        check(!document.getElementById('session-navigation')?.open,'Esc did not close session menu');
        check(await snapshot()===idle,'session menu changed combat state');
        key('i');
        check(document.body.classList.contains('side-panel-open'),'inventory did not open');
        check(sidePanelTab==='inventory','wrong side panel');
        key('m');await pause();
        check(await snapshot()===idle,'shortcut acted underneath inventory');
        key('Escape');
        check(!document.body.classList.contains('side-panel-open'),'Esc did not close inventory');
        key('r');
        check(document.activeElement.closest('.rc-powers'),'R did not focus powers');
        key('ArrowDown');
        check(document.activeElement.classList.contains('keyboard-choice-focused'),'menu focus missing');
        key('Enter');await wait(()=>state.combat.resonance.phase==='preview'&&!busy,'power selected');
        key('Escape');await wait(()=>state.combat.resonance.phase==='idle'&&!busy,'cancel power');
        const beforeTyping=await snapshot();
        const text=document.createElement('div');
        text.contentEditable='true';document.body.append(text);text.focus();
        key('m');key('d');
        check(await snapshot()===beforeTyping,'typing activated a game shortcut');
        check(physicalCardKeyBuffer==='','keyboard-wedge captured normal typing');
        text.remove();
        check(!boardScanInFlight,'board scan running in keyboard mode');
        check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');
        await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
      } catch(error) {
        await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:String(error.stack)})});
      }
    })();</script>'''

    @app.after_request
    def inject(response: Any) -> Any:
        if request.path == "/play" and response.status_code == 200:
            response.set_data(response.get_data(as_text=True).replace("</body>", harness + "</body>"))
        return response

    server = make_server("127.0.0.1", 0, app, threaded=True)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    process = None
    try:
        process = subprocess.Popen([
            chrome, "--headless", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
            "--no-first-run", "--disable-background-networking", "--no-proxy-server",
            f"--user-data-dir={tmp_path / 'chrome'}", "--window-size=1268,800",
            f"http://127.0.0.1:{server.server_port}/play",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert done.wait(45), "Browser did not report"
        assert report.get("result") == "PASS", report
        assert not scans, "Keyboard browser started a physical scan"
    finally:
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
