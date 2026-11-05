"""A real keyboard carries Mission 0 from its introduction through departure."""
from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from threading import Event, Thread
from typing import Any

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui.routes import create_app
from scripts.keyboard_playtest import prepare_session
from tests.unit.test_initiative_panel import Board


def test_keyboard_mission_intro_map_confrontation_equipment_and_departure(tmp_path: Path) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome required for full mission keyboard check')
    game = prepare_session(tmp_path, ('garran', 'brakka', 'nimra'))
    board = Board()
    game.attach_board_connection(board, backend='simulator')
    scans: list[object] = []

    def unexpected_scan(*args: object, **kwargs: object) -> None:
        scans.append((args, kwargs))
        raise AssertionError('Keyboard mission must not scan the physical board')

    board.scan_board = unexpected_scan
    app = create_app(game, character_dir=tmp_path / 'characters')
    done = Event()
    report: dict[str, Any] = {}

    @app.post('/__test/result')
    def result() -> dict[str, bool]:
        report.update(request.get_json())
        done.set()
        return {'ok': True}

    harness = r'''<script>
    (async()=>{
      const pause=()=>new Promise(resolve=>setTimeout(resolve,20));
      const check=(value,message)=>{if(!value)throw Error(message)};
      const wait=async(predicate,message)=>{
        for(let i=0;i<400;i++){if(predicate())return;await pause();}
        throw Error('timeout '+message+' · '+state?.mission?.stage+' · '+state?.exploration_mana?.phase);
      };
      const key=(value,repeat=false)=>{
        const code=value.length===1?'Key'+value.toUpperCase():value;
        (document.activeElement||document.body).dispatchEvent(new KeyboardEvent('keydown',{
          key:value,code,repeat,bubbles:true,cancelable:true,
        }));
        document.dispatchEvent(new KeyboardEvent('keyup',{key:value,code,bubbles:true}));
      };
      const idle=()=>wait(()=>!busy&&!boardPanelSyncPromise
        &&document.querySelector('[data-keyboard-sync]')?.hidden,'input idle');
      const choose=async(selector)=>{
        await idle();
        const target=document.querySelector(selector);
        check(target&&!target.disabled,'missing enabled choice '+selector);
        for(let i=0;i<45;i++)key('ArrowUp');
        for(let i=0;i<45&&document.activeElement!==target;i++)key('ArrowDown');
        check(document.activeElement===target,'keyboard cannot focus '+selector);
        key('Enter');
        await idle();
      };
      const missionChoice=async(action)=>{
        const choice=state.mission.choices.find(choice=>choice.action===action);
        check(choice,'mission action missing '+action);
        await choose(`[data-mission-slot="${choice.slot}"]`);
      };
      const confrontationChoice=async(action)=>{
        const choice=state.exploration_mana.board_choices.find(choice=>choice.action===action);
        check(choice,'confrontation action missing '+action);
        await choose(`[data-mana-slot="${choice.slot}"]`);
      };
      try{
        window.alert=message=>{throw Error('Unexpected alert '+message)};
        await wait(()=>state?.input?.mode==='keyboard'&&!busy,'initial keyboard mission');
        check(state.mission.stage==='world','full mission does not start at world introduction');
        check(!state.board_selection.auto_arm,'intro armed scanner');
        const introduced=[];
        for(let i=0;i<24&&state.mission.stage!=='guild_hub';i++){
          if(state.mission.stage==='heroes')introduced.push(state.mission.text.id);
          await missionChoice('next');
        }
        check(JSON.stringify(introduced)===JSON.stringify(['hero_garran','hero_brakka','hero_nimra']),
          'keyboard skipped or reordered hero introductions');
        check(state.mission.stage==='guild_hub','keyboard did not finish guild setup');
        check(state.input.kind==='map','guild destinations missing cursor');
        const field=[...state.input.cursor],stage=state.mission.stage;
        key('ArrowRight');await idle();
        check(state.mission.stage===stage,'cursor entered a destination without confirmation');
        key('ArrowLeft');await idle();
        check(JSON.stringify(state.input.cursor)===JSON.stringify(field),'cursor did not return to destination');
        key('Enter');await wait(()=>state.mission.stage==='brief'&&!busy,'Nessa destination');
        await missionChoice('negotiate');
        await wait(()=>state.exploration_mana?.active&&!busy,'Nessa confrontation');
        await confrontationChoice('acknowledge');
        await wait(()=>state.exploration_mana.phase==='approach'&&!busy,'approach choices');
        await confrontationChoice('approach');
        await wait(()=>keyboardRollWizard&&!keyboardRollWizard.review&&!busy,'physical dice wizard');
        const input=document.getElementById('keyboard-roll-wizard-input');
        const before=Number(input.value);
        key('ArrowUp');await idle();
        check(Number(document.getElementById('keyboard-roll-wizard-input').value)===before+1,
          'keyboard did not adjust physical die');
        key('Enter');await wait(()=>keyboardRollWizard?.review&&!busy,'die review');
        key('Enter');await wait(()=>state.exploration_mana.phase==='summary'&&!busy,'roll summary');
        await confrontationChoice('confirm');
        await wait(()=>state.exploration_mana.phase==='after_action'&&!busy,'confirmed result');
        await confrontationChoice('advance');
        await wait(()=>state.exploration_mana.phase==='approach'&&!busy,'next participant');
        await confrontationChoice('leave');
        await wait(()=>!state.exploration_mana?.active&&!busy,'leave confrontation');
        check(!state.mission.choices.some(choice=>choice.action==='depart'),
          'unfinished negotiation should retain its departure gate');
        await missionChoice('negotiate');
        await wait(()=>state.exploration_mana?.active&&!busy,'resume negotiation');
        check(state.exploration_mana.phase==='approach','resume lost the next participant');
        for(let i=0;i<6&&state.exploration_mana.phase!=='result';i++){
          const phase=state.exploration_mana.phase;
          check(['approach','after_action'].includes(phase),'unexpected resumed phase '+phase);
          await confrontationChoice(phase==='approach'?'pass':'advance');
        }
        check(state.exploration_mana.phase==='result','remaining participants did not finish negotiation');
        await confrontationChoice('next');
        await wait(()=>!state.exploration_mana?.active&&!busy,'apply negotiation result');
        await missionChoice('depart');
        await wait(()=>state.mission.stage==='equipment'&&!busy,'equipment sheet');
        const mainHand=document.querySelector('[data-equipment-slot="main_hand"]').textContent;
        await choose('[data-equipment-slot="main_hand"]');
        await wait(()=>state.mission.stage==='equipment_item'&&!busy,'equipment picker');
        const item=state.mission.equipment.item?.id;
        if(state.mission.choices.some(choice=>choice.action==='equipment_next')){
          await missionChoice('equipment_next');
          check(state.mission.equipment.item?.id!==item,'equipment browse did not change preview');
        }
        key('Escape');await wait(()=>state.mission.stage==='equipment'&&!busy,'cancel equipment');
        check(document.querySelector('[data-equipment-slot="main_hand"]').textContent===mainHand,
          'cancel changed equipped weapon');
        for(let i=0;i<3;i++)await missionChoice('equipment_accept');
        await wait(()=>state.mission.stage==='departure'&&!busy,'party ready');
        key('Enter');await wait(()=>state.mission.stage==='road'&&!busy,'departure');
        check(!state.board_selection.auto_arm&&!boardScanInFlight,'scanner ran during mission');
        check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');
        await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({result:'PASS',introduced})});
      }catch(error){
        await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({result:String(error.stack),stage:state?.mission?.stage,
            phase:state?.exploration_mana?.phase,body:document.body.innerText.slice(-1600)})});
      }
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
            f'--user-data-dir={tmp_path / "chrome"}', '--window-size=1268,800',
            f'http://127.0.0.1:{server.server_port}/play',
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert done.wait(45), 'Mission keyboard browser did not report'
        assert report.get('result') == 'PASS', report
        assert not scans, 'Mission keyboard browser requested a physical scan'
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
