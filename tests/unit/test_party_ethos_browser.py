"""The seven-field indicator and cart choice through the real browser/board API."""
from pathlib import Path
from threading import Event, Thread
import shutil
import subprocess

from flask import request
import pytest
from werkzeug.serving import make_server
from dnd_board_game.ui.exploration_app import create_app
from dnd_board_game.ui import mission_zero
from tests.unit.test_mission_zero import session, stage


@pytest.mark.parametrize('width,count', [(390, 3), (1300, 6)])
def test_ethos_indicator_cart_rune_and_adjusted_preparation(tmp_path: Path, width: int, count: int):
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome: pytest.skip('Chrome required')
    s = session(tmp_path, count); s.configured_board_backend = 'none'
    stage(s, 'road')
    app = create_app(s); done = Event(); report = {}

    @app.post('/__test/result')
    def result():
        report.update(request.get_json()); done.set(); return {'ok': True}

    @app.post('/__test/object')
    def object_scene():
        stage(s, 'explore')
        mission_zero.launch_confrontation(s, 'armory')
        return s.state_payload()

    harness = r'''<script>
(async()=>{
const check=(v,m)=>{if(!v)throw Error(m)};
const wait=async f=>{for(let i=0;i<180;i++){if(f())return;await new Promise(r=>setTimeout(r,25))}throw Error('timeout')};
const press=async slot=>{await wait(()=>!busy&&!boardPanelSyncPromise);await api('/api/board/select',{col:19,row:29-slot},'');await wait(()=>!busy)};
try {
 await wait(()=>state?.mission?.stage==='road'&&!busy);
 const indicator=document.getElementById('party-ethos');
 check(!indicator.hidden&&indicator.querySelectorAll('.ethos-track i').length===7,'seven fields');
 check(indicator.innerText.includes('Równowaga'),'neutral start');
 check(indicator.querySelectorAll('.current').length===1,'single marker');
 check(document.documentElement.scrollWidth<=innerWidth,'header overflow');
 const button=document.querySelector('[data-mission-slot="7"]');
 check(button&&button.innerText.includes('Bezwzględność'),'choice consequence');
 check(button.getBoundingClientRect().bottom<=innerHeight,'choice clipped');
 await press(7);
 check(state.mission.stage==='cart_coerced'&&state.mission.fatigue===0,'cart bypass');
 check(!state.exploration_mana?.active,'no cart test');
 check(indicator.innerText.includes('Bezwzględność'),'marker updated');
 check(state.party_ethos.total===state.actors.length*10-2,'reduced supply');
 indicator.open=true;
 check(indicator.innerText.includes('Następna talia')&&indicator.innerText.includes('nie wracają'),'physical instructions');
 check(indicator.querySelector('.ethos-details').getBoundingClientRect().right<=innerWidth,'detail clipped');
 indicator.open=false;
 await api('/__test/object',{},'');
 const action=async name=>{const c=state.exploration_mana.board_choices.find(c=>c.action===name);check(c,'missing '+name);await press(c.slot)};
 await action('acknowledge');
 while(state.exploration_mana.phase==='approach')await action('approach');
 check(state.exploration_mana.phase==='setup','new confrontation');
 const instruction=document.querySelector('.confrontation-controls').innerText;
 check(instruction.includes(`${state.actors.length*10-2} kart`),'actual total');
 check(instruction.includes('Poza talią')&&instruction.includes('białe: 1')&&instruction.includes('niebieskie: 1'),'exclusion instructions');
 check(document.documentElement.scrollWidth<=innerWidth,'confrontation overflow');
 await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
} catch(e) {await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack,body:document.body.innerText.slice(-1800)})});}
})();</script>'''
    @app.after_request
    def inject(response):
        if request.path == '/play' and response.status_code == 200:
            response.set_data(response.get_data(as_text=True).replace('</body>', harness + '</body>'))
        return response

    server = make_server('127.0.0.1', 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    process = None
    try:
        process = subprocess.Popen([chrome, '--headless', '--no-sandbox', '--disable-gpu',
            '--disable-dev-shm-usage', '--no-first-run', '--disable-background-networking',
            '--no-proxy-server', f'--user-data-dir={tmp_path/"chrome"}',
            f'--window-size={width},800', f'http://127.0.0.1:{server.server_port}/play'],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        assert done.wait(40), 'Browser did not report'
        assert report.get('result') == 'PASS', report
    finally:
        if process:
            process.terminate()
            try: process.communicate(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.communicate(timeout=5)
        server.shutdown(); thread.join(timeout=5)
