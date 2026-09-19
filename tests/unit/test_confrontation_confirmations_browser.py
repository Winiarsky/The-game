"""Visible physical instructions and rune decisions in Chrome."""
from threading import Event, Thread
from pathlib import Path
import shutil
import subprocess

import pytest
from flask import request
from werkzeug.serving import make_server
from dnd_board_game.ui.exploration_app import create_app
from tests.unit.test_confrontation_confirmations import prepared


@pytest.mark.parametrize('recovery', [True, False])
@pytest.mark.parametrize('width,height', [(1300, 657), (390, 800)])
def test_confirmation_visible_and_operable(tmp_path: Path, recovery: bool, width: int, height: int):
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome: pytest.skip('Chrome unavailable')
    session = prepared(tmp_path, recovery)
    app = create_app(session)
    done, report = Event(), {}

    @app.post('/__test/result')
    def result():
        report.update(request.get_json()); done.set(); return {'ok': True}

    harness = '''<script>
(async()=>{
 const check=(v,m)=>{if(!v)throw Error(m)};
 const wait=async f=>{for(let i=0;i<200;i++){if(f())return;await new Promise(r=>setTimeout(r,25))}throw Error('timeout')};
 try{
  await wait(()=>state?.exploration_mana?.active&&!busy&&!boardPanelSyncPromise);
  const panel=document.querySelector('.confrontation-view'), p=state.exploration_mana;
  const controls=panel.querySelector('.confrontation-controls');
  check(panel.getBoundingClientRect().bottom<=innerHeight+1,'panel clipped');
  check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');
  check(controls.scrollHeight<=controls.clientHeight+1,'controls clipped');
  const recovery=p.phase==='recovery';
  check(controls.textContent.includes(recovery?'kartę spaloną najwcześniej':'Nessa stawia'),'instruction outside fixed controls');
  check(!controls.textContent.includes('Test: mana'),'test must not bypass confirmation');
  if(recovery){
   const diagram=controls.querySelector('.mana-recovery-diagram');
   check(diagram,'recovery diagram missing');
   await wait(()=>diagram.complete&&diagram.naturalWidth>0);
  }
  const action=recovery?'confirm_recovery':'decline_compromise';
  const choice=p.board_choices.find(c=>c.action===action);
  const button=controls.querySelector(`[data-mana-slot="${choice.slot}"]`);
  check(button&&button.getBoundingClientRect().bottom<=innerHeight,'decision offscreen');
  await api('/api/board/select',{col:19,row:29-choice.slot},'');
  await wait(()=>!busy);
  check(recovery?state.exploration_mana.mana.phase==='burn':!state.exploration_mana.compromise_pending,'board confirmation failed');
  await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
 }catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack})})}
})();</script>'''

    @app.after_request
    def inject(response):
        if request.path == '/play' and response.status_code == 200:
            response.set_data(response.get_data(as_text=True).replace('</body>', harness+'</body>'))
        return response

    server = make_server('127.0.0.1', 0, app, threaded=True)
    worker = Thread(target=server.serve_forever, daemon=True); worker.start()
    process = None
    try:
        process = subprocess.Popen([chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
            '--no-first-run', '--disable-background-networking', '--no-proxy-server',
            f'--user-data-dir={tmp_path/"chrome"}', f'--window-size={width},{height+143}',
            f'http://127.0.0.1:{server.server_port}/play'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert done.wait(40), 'Browser did not report'
        assert report.get('result') == 'PASS', report
    finally:
        if process:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        server.shutdown(); worker.join(timeout=2)
