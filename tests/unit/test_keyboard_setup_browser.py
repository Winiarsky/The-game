"""Manual keyboard setup must advance through placements into initiative."""
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


@pytest.mark.parametrize('width,height', [(1268, 800), (1131, 720), (1221, 656)])
def test_keyboard_manual_setup_primary_advances_all_heroes_and_starts_initiative(
    tmp_path: Path, width: int, height: int,
) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome required for manual setup keyboard check')
    game = prepare_session(tmp_path, ('garran', 'brakka', 'nimra'), arena=True)
    board = Board()
    game.attach_board_connection(board, backend='simulator')
    game._sync_board_leds()
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
        for(let i=0;i<350;i++){if(predicate())return;await pause();}
        throw Error('timeout '+message+' · step '+state?.encounter_setup?.current_index);
      };
      const key=value=>{
        (document.activeElement||document.body).dispatchEvent(new KeyboardEvent('keydown',{
          key:value,code:value,bubbles:true,cancelable:true,
        }));
        document.dispatchEvent(new KeyboardEvent('keyup',{key:value,code:value,bubbles:true}));
      };
      const visible=element=>Boolean(element&&!element.disabled&&element.getClientRects().length
        &&!element.closest('details:not([open])'));
      const idle=()=>wait(()=>!busy&&!boardPanelSyncPromise
        &&document.querySelector('[data-keyboard-sync]')?.hidden,'input idle');
      const primary=()=>document.querySelector('[data-setup-accept]');
      const checkOnScreen=(element,label)=>{
        check(visible(element),label+' is unavailable');
        const rect=element.getBoundingClientRect();
        check(rect.top>=0&&rect.bottom<=innerHeight,label+' is outside the viewport '+JSON.stringify({top:rect.top,bottom:rect.bottom,innerHeight}));
      };
      try{
        window.alert=message=>{throw Error('Unexpected alert '+message)};
        await wait(()=>state?.input?.mode==='keyboard'&&state.encounter_setup?.status==='active'&&!busy,'setup start');
        let batches=0;
        while(state.encounter_setup.current_step?.tiles?.length){
          await idle();
          check(visible(primary()),'terrain confirmation is hidden or disabled');
          const index=state.encounter_setup.current_index;
          if(batches===1){
            const back=document.querySelector('[data-setup-back]');
            check(visible(back),'back control missing');
            await wait(()=>document.activeElement===primary(),'primary setup focus');
            key('ArrowDown');check(document.activeElement===back,'arrow did not deliberately select Back');
            key('Enter');await wait(()=>!busy&&state.encounter_setup.current_index===index-1,'explicit previous element');
            await idle();key('Enter');
            await wait(()=>!busy&&state.encounter_setup.current_index===index,'return to corrected batch');
            await idle();
          }
          if(batches%2)primary().click();else key('Enter');
          await wait(()=>!busy&&state.encounter_setup.current_index===index+1,'next terrain batch');
          batches++;
          check(batches<15,'terrain loop did not finish');
        }
        check(batches===8,'manual terrain setup was skipped');
        const placed=[];
        while(state.encounter_setup.current_step?.requires_board_assignment){
          await idle();
          const actor=state.encounter_setup.current_step.assignment_actor_id;
          const start=[...state.input.cursor];
          const direction=start[0]<18?'ArrowRight':'ArrowLeft';
          const opposite=direction==='ArrowRight'?'ArrowLeft':'ArrowRight';
          key(direction);await idle();key(opposite);await idle();
          check(state.encounter_setup.current_step.assignment_actor_id===actor,'cursor prematurely assigned hero');
          key('Enter');
          await wait(()=>!busy&&state.encounter_setup.current_step?.selected_position,'selected start field');
          check(state.encounter_setup.current_step.assignment_actor_id===actor,'selection skipped placement confirmation');
          check(visible(primary()),'selected hero has no visible confirmation');
          check(!primary().closest('details'),'hero confirmation is hidden in fallback');
          checkOnScreen(primary(),'hero placement confirm');
          const instruction=document.querySelector('.setup-current-command').textContent;
          check(instruction.includes('strzałkami')||instruction.includes('Strzałkami'),'missing keyboard placement instruction');
          check(!instruction.includes('Naciśnij niebieski przycisk'),'keyboard setup still asks for physical confirm');
          if(placed.length===1)primary().click();else key('Enter');
          await wait(()=>!busy&&state.encounter_setup.current_step?.assignment_actor_id!==actor,'confirm hero '+actor);
          placed.push(actor);
        }
        check(JSON.stringify(placed)===JSON.stringify(['garran','brakka','nimra']),'not all selected heroes were placed');
        check(state.encounter_setup.status==='active','final enemy setup unexpectedly skipped');
        const finalIndex=state.encounter_setup.current_index;
        await wait(()=>visible(primary())&&!busy,'visible final confirmation');
        check(!primary().closest('details'),'final confirmation hidden in emergency controls');
        checkOnScreen(primary(),'final setup confirm');
        // Simulate the stale Back focus reported after the last hero's map step.
        document.querySelector('[data-setup-back]').focus();
        key('Enter');
        await wait(()=>!busy&&state.encounter_setup.status==='completed','final setup completion');
        check(state.encounter_setup.current_index===finalIndex,'Enter silently reopened the preceding step');
        await wait(()=>visible(document.querySelector('[data-setup-start-initiative]'))&&!busy,'initiative primary');
        check(!document.querySelector('[data-setup-start-initiative]').closest('details'),'initiative start is hidden');
        checkOnScreen(document.querySelector('[data-setup-start-initiative]'),'initiative start');
        document.querySelector('[data-setup-back]').focus();
        key('Enter');
        await wait(()=>state.encounter_initiative?.status==='active'&&!busy,'initiative start');
        await wait(()=>keyboardRollWizard?.initiative&&!busy,'first initiative die');
        check(state.encounter_setup.status==='completed','initiative Enter went back into setup');
        check(state.encounter_initiative.current_prompt.actor_id==='garran','wrong first initiative participant');
        check(!state.board_selection.auto_arm&&!boardScanInFlight,'keyboard setup started a physical scan');
        check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');
        await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({result:'PASS',placed,batches})});
      }catch(error){
        await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({result:String(error.stack),step:state?.encounter_setup,
            input:state?.input,body:document.body.innerText.slice(-1700)})});
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
            f'--user-data-dir={tmp_path / "chrome"}', f'--window-size={width},{height}',
            f'http://127.0.0.1:{server.server_port}/play',
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert done.wait(40), 'Setup browser did not report'
        assert report.get('result') == 'PASS', report
        assert game.encounter_setup_flow.completed
        assert set(game.encounter_setup_flow.player_start_assignments) == {'garran', 'brakka', 'nimra'}
        assert game.encounter_initiative_flow is not None
        assert board.scans == 0
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
