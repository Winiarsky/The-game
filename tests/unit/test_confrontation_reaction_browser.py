"""Scene reactions retain their identity through physical burn rune input."""
from pathlib import Path
from threading import Event, Thread
import shutil
import subprocess

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui.exploration_app import create_app
from tests.unit.test_confrontation_reaction_presentation import reaction_session


@pytest.mark.parametrize('scene_name', ['nessa', 'cart'])
def test_reaction_stage_and_burn_runes_in_browser(tmp_path: Path, scene_name: str) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome required')
    session = reaction_session(tmp_path, scene_name)
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
 const press=async(action)=>{
  await wait(()=>!busy&&!boardPanelSyncPromise);
  const p=state.exploration_mana, choice=p.board_choices.find(c=>c.action===action);
  check(choice,'missing rune '+action);
  await api('/api/board/select',{col:19,row:29-choice.slot},'');
  await wait(()=>!busy&&!boardPanelSyncPromise&&state.exploration_mana.revision!==p.revision);
 };
 const identity=()=>{
  const p=state.exploration_mana, controls=document.querySelector('.confrontation-controls');
  check(controls.querySelector('header').textContent.includes(p.reaction_view.title),'reaction title missing');
  check(!controls.querySelector('header').textContent.includes('Nimra'),'reaction labelled Nimra');
  check(document.querySelector('.confrontation-active-source h3').textContent===p.reaction_view.source,'scene identity missing');
  check(!document.querySelector('.confrontation-party-summary .current'),'hero highlighted during reaction');
  check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');
 };
 try{
  await wait(()=>state?.exploration_mana?.phase==='after_action'&&!busy&&!boardPanelSyncPromise);
  check(document.querySelector('.confrontation-controls header').textContent.includes('Nimra'),'initial hero missing');
  await press('advance'); identity();
  const title=state.exploration_mana.reaction_view.title;
  check(state.exploration_mana.phase==='reaction','no separate reaction step');
  check(!document.querySelector('.confrontation-result'),'previous hero result leaked into reaction');
  check(document.querySelector('.confrontation-instruction').textContent.includes('Spalanie ze wspólnej talii: 3'),'reaction preview count');
  await press('react'); identity();
  for(const remaining of [3,2,1]){
   check(state.exploration_mana.reaction_view.title===title,'reaction name lost');
   check(document.querySelector('.confrontation-instruction').textContent.includes('pozostało: '+remaining),'remaining burn count');
   const choices=[...document.querySelectorAll('.confrontation-color-choice')];
   check(choices.length>0&&choices.every(c=>c.getBoundingClientRect().bottom<innerHeight),'burn runes offscreen');
   await press('color'); identity();
  }
  check(document.querySelector('.confrontation-instruction').textContent.includes('Reakcja rozliczona'),'reaction completion missing');
  await press('advance');
  check(state.exploration_mana.round===2&&!state.exploration_mana.reaction_view.active,'reaction did not finish');
  check(document.querySelector('.confrontation-controls header').textContent.includes('Brakka'),'next hero missing');
  await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
 }catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack})})}
})();</script>'''

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
