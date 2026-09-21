"""Real browser automatic scans from mission initiative to the adjusted mana deck."""
from pathlib import Path
from threading import Event, Thread
from typing import Any
import shutil
import subprocess

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui.exploration_app import create_app
from tests.unit.test_mission_combat_board_input import prepared_mission
from tests.unit.test_readonly_modal_scanning_browser import WaitingBoard


@pytest.mark.parametrize('deviation', [0, 1, -1])
def test_initiative_and_deck_preparation_via_automatic_scans(tmp_path: Path, deviation: int) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome required')
    session = prepared_mission(tmp_path, deviation)
    board = WaitingBoard()
    session.attach_board_connection(board, backend='simulator')
    app = create_app(session)
    done = Event()
    report: dict[str, Any] = {}

    @app.post('/__test/press')
    def press() -> dict[str, bool]:
        return {'delivered': board.press(request.get_json()['slot'])}

    @app.post('/__test/result')
    def result() -> dict[str, bool]:
        report.update(request.get_json())
        done.set()
        return {'ok': True}

    harness = r'''<script>
    (async()=>{
      const check=(v,m)=>{if(!v)throw Error(m)};
      const wait=async(f,message)=>{for(let i=0;i<250;i++){if(f())return;await new Promise(r=>setTimeout(r,20));}throw Error(message)};
      const press=async(slot)=>{
        await wait(()=>boardScanInFlight&&!boardPanelSyncPromise&&!busy,'scanner not armed '+slot);
        const revision=state.board_selection.revision;
        let delivered=false;
        for(let i=0;i<100&&!delivered;i++){
          const r=await fetch('/__test/press',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({slot})});
          delivered=(await r.json()).delivered;
          if(!delivered)await new Promise(r=>setTimeout(r,20));
        }
        check(delivered,'no receiver '+slot);
        await wait(()=>state.board_selection.revision!==revision&&!boardPanelSyncPromise,'unresolved '+slot);
      };
      try{
        await wait(()=>state?.board_selection?.mode==='initiative_start'&&!busy,'initiative start');
        check(desiredBoardPanel()===null,'generic browser panel overrides native initiative');
        await press(28);
        for(let hero=0;hero<3;hero++){
          await wait(()=>keyboardRollWizard?.initiative,'initiative wizard');
          check(state.encounter_initiative.current_prompt_index===hero,'current hero');
          check(desiredBoardPanel()===null,'browser must leave initiative controls to server');
          await press(27);check(state.encounter_initiative.panel.values[0]===11,'plus');
          await press(26);check(state.encounter_initiative.panel.values[0]===10,'minus');
          await press(28);check(state.encounter_initiative.panel.review,'review');
          await press(29);check(!state.encounter_initiative.panel.review,'back');
          await press(27);await press(28);await press(28);
        }
        await wait(()=>state.combat?.shared_mana?.pool_view?.phase==='setup'&&document.querySelector('.tt-pool-step'),'deck setup');
        const pool=state.combat.shared_mana.pool_view;
        const notice=document.querySelector('.mana-deck-preparation');
        check(Boolean(notice)===(DEVIATION!==0),'notice only when stance deviates');
        check(pool.total===(DEVIATION===0?30:28),'actual deck total');
        if(notice){
          check(notice.innerText.includes(DEVIATION>0?'Bezwzględność':'Solidarność'),'stance label');
          check(notice.innerText.includes('28 kart'),'deck size visible');
          check(notice.querySelectorAll('.mana-deck-counts')[0].children.length===2,'two excluded colors');
          check(notice.querySelectorAll('.mana-deck-counts')[1].children.length===5,'all five deck counts');
          check(notice.innerText.includes('nie wrócą'),'exclusions persist');
        }
        const modal=document.querySelector('.tt-pool-step');
        check(modal.scrollHeight<=modal.clientHeight+1,'preparation requires unavailable scrolling');
        check(modal.getBoundingClientRect().bottom<=innerHeight,'preparation clipped');
        check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');
        check(state.board_selection.legal_positions.length===1&&state.board_selection.legal_positions[0][1]===1,'only confirm before preparation');
        await press(28);
        check(state.combat.shared_mana.pool_view.phase==='reveal','confirmation starts reveal');
        check(!document.querySelector('.mana-deck-preparation'),'notice disappears after confirmation');
        await press(6);await press(10);
        check(state.combat.shared_mana.pool_view.offer.join(',')==='C,N','physical color reporting');
        await stopBoardScanLoop();
        await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
      }catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack,phase:boardInputPhase,error:boardScanError})});}
    })();</script>'''.replace('DEVIATION', str(deviation))

    @app.after_request
    def inject(response: Any) -> Any:
        if request.path == '/play' and response.status_code == 200:
            response.set_data(response.get_data(as_text=True).replace('</body>', harness + '</body>'))
        return response

    server = make_server('127.0.0.1', 0, app, threaded=True)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    process = None
    try:
        process = subprocess.Popen([
            chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
            '--no-first-run', '--disable-background-networking', '--no-proxy-server',
            f'--user-data-dir={tmp_path / "chrome"}', '--window-size=1131,863',
            f'http://127.0.0.1:{server.server_port}/play',
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert done.wait(40), 'Browser did not report'
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
