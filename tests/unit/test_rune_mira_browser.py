"""Real board scans reject visible targets and toggle Mira's hiding rune."""
import json
from pathlib import Path
import shutil
import subprocess
from threading import Event, Thread
from typing import Any

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui.routes import create_app
from tests.unit.test_rune_mira import hidden_mira
from tests.unit.test_tabletop_combat_browser import CombatBoard


def test_mira_target_lights_and_fork_toggle_in_browser(tmp_path: Path) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome required')
    game, hidden_id, visible_id = hidden_mira(tmp_path)
    positions = {str(a.id): list(a.position.as_tuple()) for a in game.combat_state.actors}
    board = CombatBoard()
    game.attach_board_connection(board, backend='simulator')
    app = create_app(game, character_dir=tmp_path/'characters')
    done = Event()
    report: dict[str, Any] = {}

    @app.post('/__test/press')
    def press() -> dict[str, object]:
        return {'delivered': board.press_field(tuple(request.get_json()['position']))}

    @app.post('/__test/result')
    def result() -> dict[str, bool]:
        report.update(request.get_json())
        done.set()
        return {'ok': True}

    harness = r'''<script>
    (async()=>{
      const check=(v,m)=>{if(!v)throw Error(m)};
      const wait=async(f,m)=>{for(let i=0;i<300;i++){if(f())return;await new Promise(r=>setTimeout(r,20))}throw Error('timeout '+m)};
      const legal=p=>(state.board_selection.legal_positions||[]).some(q=>p[0]===q[0]&&p[1]===q[1]);
      const press=async position=>{
        await wait(()=>boardScanInFlight&&!busy&&!boardPanelSyncPromise,'scan');
        const revision=state.board_selection.revision;
        let delivered=false;
        for(let i=0;i<150&&!delivered;i++){
          const r=await fetch('/__test/press',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({position})});
          delivered=(await r.json()).delivered;
          if(!delivered)await new Promise(r=>setTimeout(r,20));
        }
        check(delivered,'field not armed '+position);
        await wait(()=>state.board_selection.revision!==revision&&!busy&&!boardPanelSyncPromise,'field resolved');
      };
      const slot=n=>press([19,29-n]);
      try{
        await wait(()=>state?.combat?.current_actor?.id==='mira'&&!busy,'Mira');
        const hands=JSON.stringify(state.combat.shared_mana.rune_view.hands);
        await slot(11);
        check(legal(HIDDEN_POSITION),'unaware target not lit');
        check(!legal(VISIBLE_POSITION),'visible target lit');
        await slot(29);
        await wait(()=>!state.combat.targeting,'cancel attack');
        await slot(5);
        check(document.querySelector('.tt-action').textContent.includes('Przerwij skradanie'),'fork did not preview exit');
        check(legal([19,1]),'accept dark');
        await slot(29);
        check(state.combat.current_actor.hidden,'cancel lost hiding');
        await slot(5);await slot(28);
        await wait(()=>!state.combat.current_actor.hidden,'exit hiding');
        check(JSON.stringify(state.combat.shared_mana.rune_view.hands)===hands,'exit spent runes');
        check(!state.combat.shared_mana.rune_view.special_used,'exit spent special');
        await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
      }catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:String(e.stack)})});}
    })();</script>'''.replace('HIDDEN_POSITION', json.dumps(positions[hidden_id])).replace('VISIBLE_POSITION', json.dumps(positions[visible_id]))

    @app.after_request
    def inject(response: Any) -> Any:
        if request.path == '/play' and response.status_code == 200:
            response.set_data(response.get_data(as_text=True).replace('</body>', harness+'</body>'))
        return response

    server = make_server('127.0.0.1', 0, app, threaded=True)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    process = None
    try:
        process = subprocess.Popen([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
            '--no-first-run','--disable-background-networking','--no-proxy-server',
            f'--user-data-dir={tmp_path/"chrome"}','--window-size=1131,863',
            f'http://127.0.0.1:{server.server_port}/play'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert done.wait(45), 'Browser did not report'
        assert report.get('result') == 'PASS', report
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
