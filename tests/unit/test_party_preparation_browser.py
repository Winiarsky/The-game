"""Preparation instructions, portraits and board controls at laptop sizes."""
from dataclasses import replace
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


@pytest.mark.parametrize('width,height', [(1268,736), (1131,863)])
def test_preparation_instruction_and_hero_portraits_via_board(tmp_path: Path, width: int, height: int) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome required')
    session = party(tmp_path, heroes=('garran', 'lorian', 'nimra'))
    stage(session, 'brief')
    send(session, 'depart')
    from dnd_board_game.ui.training_arena import training_hero
    from dnd_board_game.ui import mission_zero as mission
    axe = next(i for i in training_hero('brakka').inventory if i.id == 'greataxe')
    session.state = replace(session.state, party_loot=replace(session.state.party_loot, items=(replace(axe, equipped=False, held_in=()),)))
    data = mission.read(session); mission.grant(session, data, 'key'); mission.write(session, data)
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

    @app.post('/__test/return')
    def return_to_base() -> dict[str, Any]:
        stage(session, 'explore', equipment_locked=True)
        data = mission.read(session)
        mission.grant(session, data, 'medallion')
        mission.write(session, data)
        stage(session, 'guild_return', equipment_locked=False)
        return session.state_payload()

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
        await wait(()=>state?.mission?.equipment&&!busy&&document.querySelector('.equipment-body'),'initial rendering');
        check(state.mission.stage==='equipment','preparation opens on filled sheet');bounds();
        check(document.querySelector('[data-equipment-slot="main_hand"]').textContent.includes('Miecz'),'starter weapon missing');
        check(document.querySelectorAll('[data-equipment-slot]').length===15,'missing equipment places');
        check(new Set(state.mission.choices.map(c=>c.slot)).size===state.mission.choices.length,'duplicate runes');
        check(!state.mission.choices.some(c=>[26,27].includes(c.slot)),'sheet asks to browse items first');
        check(!document.querySelector('.equipment-workspace').textContent.includes('Klucz do posterunku'),'quest key is personal gear');
        await press(17);
        check(state.mission.equipment.picker.slot==='main_hand','Grot opens hand');
        check(state.mission.equipment.item.id==='longsword','current weapon is first');
        check(state.mission.choices.every(c=>[26,27,28,29].includes(c.slot)),'picker has extra active runes');bounds();
        await press(26);check(state.mission.equipment.item.id==='greataxe','plus browses a matching stash weapon');
        check(document.querySelector('.equipment-picker').scrollTop===0,'picker heading scrolled out of view');
        await press(29);check(document.querySelector('[data-equipment-slot="main_hand"]').textContent.includes('Miecz'),'cancel changed equipment');
        await press(17);await press(26);await press(28);
        check(document.querySelector('[data-equipment-slot="main_hand"]').textContent.includes('Wielki topór'),'confirmed weapon missing');
        check(document.querySelector('[data-equipment-slot="off_hand"]').textContent.includes('Zajęta'),'second hand not linked');bounds();
        await press(23);await press(7);
        check(state.mission.equipment.item.id==='mission_key','shared quest item missing');
        check(!state.mission.choices.some(c=>c.action==='equipment_sell'),'quest item can be sold');
        await press(29);
        for(const hero of ['garran','lorian','nimra']){
          check(state.mission.equipment.hero_id===hero,'wrong active hero');
          await wait(()=>document.querySelector('.equipment-hero-portrait')?.complete&&document.querySelector('.equipment-hero-portrait').naturalWidth,'portrait loading');
          const image=document.querySelector('.equipment-hero-portrait');
          check(image.src.includes('/'+hero+'.png?')&&image.alt===state.mission.equipment.hero,'wrong portrait');bounds();
          if(hero==='nimra'){
            const selection=JSON.stringify(state.mission.equipment);
            await press(25);check(state.mission.stage==='equipment_intro','help rune');
            await press(26);check(missionScrollArea().scrollTop>0,'help scrolling');
            await press(29);check(JSON.stringify(state.mission.equipment)===selection,'help lost selected item or hero');bounds();
          }
          await press(28);
        }
        check(state.mission.stage==='departure','ready leaves preparation');
        await api('/__test/return',{},'');
        await press(state.mission.choices.find(c=>c.action==='equipment_open').slot);
        await press(23);await press(6);
        check(state.mission.equipment.item.id==='mission_medallion','discovery missing at base');
        check(state.mission.equipment.item.needs_identification,'discovery prematurely identified');
        await press(28);
        check(state.mission.equipment.groups.found===0,'identification did not clear discovery');
        await press(5);
        check(!state.mission.equipment.item.needs_identification,'identified item unavailable');
        await press(29);await press(20);
        check(state.mission.equipment.item.id==='mission_medallion','identified necklace not offered');
        await press(28);
        check(document.querySelector('[data-equipment-slot="neck"]').textContent.includes('Medalik'),'necklace missing from sheet');
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
            f'--user-data-dir={tmp_path / "chrome"}', f'--window-size={width},{height}',
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
