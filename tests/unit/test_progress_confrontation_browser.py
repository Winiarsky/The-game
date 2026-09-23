"""Real mission page: physical rune choices, post-roll reputation and replay safety."""
from pathlib import Path
from threading import Event, Thread
import shutil
import subprocess

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui.exploration_app import create_app
from tests.unit.test_mission_zero import session, stage, send


def test_one_round_mission_reputation_through_live_board_controls(tmp_path: Path):
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:pytest.skip('Chrome required')
    s=session(tmp_path);stage(s,'brief');send(s,'negotiate');s.configured_board_backend='none'
    app=create_app(s);done=Event();report={}
    @app.post('/__test/result')
    def result():
        report.update(request.get_json());done.set();return {'ok':True}
    harness=r'''<script>
(async()=>{
const check=(v,m)=>{if(!v)throw Error(m)};
const wait=async f=>{for(let i=0;i<200;i++){if(f())return;await new Promise(r=>setTimeout(r,25))}throw Error('timeout')};
const field=async slot=>{await wait(()=>!busy&&!boardPanelSyncPromise);const rev=state.board_selection.revision;await api('/api/board/select',{col:19,row:29-slot},'');await wait(()=>!busy&&!boardPanelSyncPromise&&state.board_selection.revision!==rev)};
const press=async action=>{const c=state.exploration_mana.board_choices.find(c=>c.action===action);check(c,'missing '+action);await field(c.slot)};
const roll=async value=>{await wait(()=>!busy&&!boardPanelSyncPromise);await api('/api/exploration-mana',{action:'roll',revision:state.exploration_mana.revision,rolls:[value]},'');await wait(()=>!busy&&!boardPanelSyncPromise&&state.exploration_mana.phase==='summary')};
try{
 await wait(()=>state?.exploration_mana?.engine==='progress_v1'&&!busy&&!boardPanelSyncPromise);
 check(!document.getElementById('mission-panel').innerText.includes('Tasowanie'),'no mana preparation');
 await press('acknowledge');
 check(state.exploration_mana.phase==='approach','one hero approach');
 check(document.querySelectorAll('.progress-confrontation-options article').length===6,'six authored approaches');
 await press('approach');
 check(state.exploration_mana.phase==='check','approach immediately opens die');
 check(document.getElementById('exploration-mana-roll'),'natural d20 form');
 await roll(10);
 check(document.querySelectorAll('.reputation-options button').length===3,'exact three exclusive options');
 check(state.exploration_mana.reputation.points===20,'shared opening balance');
 await field(5);check(state.exploration_mana.preview.bonus===1,'plus one selected');
 await field(6);check(state.exploration_mana.preview.bonus===5,'selection replaces rather than stacks');
 await field(29);check(state.exploration_mana.reputation.selected==='','back removes choice');
 await field(6);await field(28);
 check(state.exploration_mana.reputation.points===17,'one payment after confirm');
 check(state.exploration_mana.phase==='after_action','one check resolves progress without impactdie');
 await press('advance');await press('approach');await roll(1);
 check(state.exploration_mana.board_choices.filter(c=>c.action==='reputation').length===1,'naturalone only extra die');
 await field(7);await field(28);
 check(state.exploration_mana.phase==='extra_check'&&state.exploration_mana.reputation.points===12,'pay before extra die');
 await roll(20);await field(28);
 check(state.exploration_mana.reputation.points===12,'extra die never charged twice');
 check(state.exploration_mana.phase==='result','scaled maximum ends early');
 check(document.documentElement.scrollWidth<=innerWidth,'no horizontal overflow');
 await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
}catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack,body:document.body.innerText.slice(-2000)})})}
})();</script>'''
    @app.after_request
    def inject(response):
        if request.path=='/play' and response.status_code==200:
            response.set_data(response.get_data(as_text=True).replace('</body>',harness+'</body>'))
        return response
    server=make_server('127.0.0.1',0,app,threaded=True);worker=Thread(target=server.serve_forever,daemon=True);worker.start();process=None
    try:
        process=subprocess.Popen([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run',
            '--disable-background-networking','--no-proxy-server',f'--user-data-dir={tmp_path/"chrome"}','--window-size=1300,863',
            f'http://127.0.0.1:{server.server_port}/play'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        assert done.wait(40),'Browser did not report'
        assert report.get('result')=='PASS',report
    finally:
        if process:
            process.terminate()
            try:process.communicate(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.communicate(timeout=5)
        server.shutdown();worker.join(timeout=2)
