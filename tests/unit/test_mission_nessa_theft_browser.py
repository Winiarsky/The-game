"""The optional post-defeat theft is readable and selectable by board runes."""
from pathlib import Path
from threading import Event, Thread
import shutil
import subprocess

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui.exploration_app import create_app
from tests.unit.test_mission_nessa_theft import failed_negotiation


@pytest.mark.parametrize('steal', [False, True])
def test_mira_theft_choice_by_board_rune(tmp_path: Path, steal: bool) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome required')
    session = failed_negotiation(tmp_path)
    session.configured_board_backend = 'none'
    app = create_app(session)
    done, report = Event(), {}

    @app.post('/__test/result')
    def result():
        report.update(request.get_json())
        done.set()
        return {'ok': True}

    harness = r'''<script>
(async()=>{
 const check=(v,m)=>{if(!v)throw Error(m)};
 const wait=async f=>{for(let i=0;i<240;i++){if(f())return;await new Promise(r=>setTimeout(r,25))}throw Error('timeout')};
 try{
  await wait(()=>state?.mission?.stage==='nessa_theft'&&!busy&&!boardPanelSyncPromise);
  const panel=document.querySelector('#mission-panel');
  check(panel.textContent.includes('Mira')&&panel.textContent.includes('1k8 + 2 PW'),'story/reward missing');
  check(panel.textContent.includes('Bezwzględności'),'cost missing');
  check(!panel.textContent.includes('**'),'raw Markdown visible');
  check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');
  for(const slot of [6,7]){
   const button=panel.querySelector(`[data-mission-slot="${slot}"]`);
   check(button&&button.querySelector('svg'),'missing rune icon');
   check(button.getBoundingClientRect().bottom<innerHeight,'choice offscreen');
  }
  const slot=STEAL?6:7;
  await api('/api/board/select',{col:19,row:29-slot},'');
  await wait(()=>!busy&&!boardPanelSyncPromise&&state.mission.stage===(STEAL?'nessa_theft_taken':'brief'));
  check(state.party_ethos.position===(STEAL?4:3),'ethos not updated');
  check(state.mission.ledger.filter(e=>e.id==='weak_potion').length===(STEAL?1:0),'wrong reward count');
  if(STEAL){
   check(document.querySelector('.mission-prose').textContent.includes('1 słabszą miksturę'),'reward receipt missing');
   await api('/api/board/select',{col:19,row:1},'');
   await wait(()=>!busy&&state.mission.stage==='brief');
  }
  check(!state.mission.choices.some(c=>c.action==='nessa_steal_potion'||c.action==='negotiate'),'theft can be repeated');
  await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
 }catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack})})}
})();</script>'''.replace('STEAL', 'true' if steal else 'false')

    @app.after_request
    def inject(response):
        if request.path == '/play' and response.status_code == 200:
            response.set_data(response.get_data(as_text=True).replace('</body>', harness + '</body>'))
        return response

    server = make_server('127.0.0.1', 0, app, threaded=True)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    process = None
    try:
        process = subprocess.Popen([chrome, '--headless', '--no-sandbox', '--disable-gpu',
            '--disable-dev-shm-usage', '--no-first-run', '--disable-background-networking',
            '--no-proxy-server', f'--user-data-dir={tmp_path / "chrome"}', '--window-size=1131,863',
            f'http://127.0.0.1:{server.server_port}/play'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        server.shutdown()
        worker.join(timeout=2)
