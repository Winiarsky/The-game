"""Preparation instructions, portraits and board controls at laptop sizes."""
from pathlib import Path
from threading import Event, Thread
from typing import Any
import shutil
import subprocess

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui.exploration_app import create_app
from tests.unit.test_mission_recovery import party
from tests.unit.test_mission_zero import stage, send
from tests.unit.test_readonly_modal_scanning_browser import WaitingBoard


@pytest.mark.parametrize('width', [1131, 1300])
def test_preparation_instruction_and_hero_portraits_via_board(tmp_path: Path, width: int) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome required')
    session = party(tmp_path, heroes=('garran', 'lorian', 'nimra'))
    stage(session, 'brief')
    send(session, 'depart')
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
      const bounds=()=>{
        const panel=document.getElementById('mission-panel');
        check(panel.getBoundingClientRect().bottom<=innerHeight+1,'panel clipped');
        check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');
        for(const c of panel.querySelectorAll('[data-mission-slot]'))check(c.getBoundingClientRect().bottom<=innerHeight,'controls clipped');
      };
      try{
        await wait(()=>state?.mission&&!busy&&document.querySelector('.mission-prose'),'initial rendering');
        check(state.mission.stage==='equipment_intro','intro must precede equipment');bounds();
        check(document.querySelector('.mission-prose').textContent.includes('Garran ma miecz'),'example missing');
        const intro=missionScrollArea();
        check(intro.clientWidth>innerWidth*.7,'instruction left in half-width image column');
        await press(27);check(intro.scrollTop>0,'board scrolls instruction');
        await press(26);check(intro.scrollTop===0,'board scrolls back');
        await press(28);
        for(const hero of ['garran','lorian','nimra']){
          check(state.mission.equipment.hero_id===hero,'wrong active hero');
          await wait(()=>document.querySelector('.equipment-hero-portrait')?.complete&&document.querySelector('.equipment-hero-portrait').naturalWidth,'portrait loading');
          const image=document.querySelector('.equipment-hero-portrait');
          check(image.src.includes('/'+hero+'.png?')&&image.alt===state.mission.equipment.hero,'wrong portrait');
          check(image.getBoundingClientRect().height>=64,'portrait too small');bounds();
          if(hero==='nimra'){
            await press(7);await press(27);
            const selection=JSON.stringify(state.mission.equipment);
            await press(25);check(state.mission.stage==='equipment_intro','help rune');
            await press(27);check(missionScrollArea().scrollTop>0,'help scrolling');
            await press(29);check(JSON.stringify(state.mission.equipment)===selection,'help lost selected item or hero');bounds();
          }
          await press(28);
        }
        check(state.mission.stage==='departure','ready leaves preparation');
        await stopBoardScanLoop();
        await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
      }catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack,phase:boardInputPhase,error:boardScanError})});}
    })();</script>'''

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
            f'--user-data-dir={tmp_path / "chrome"}', f'--window-size={width},863',
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
