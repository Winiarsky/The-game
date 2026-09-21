"""Natural extremes display their result and lead directly to board burn runes."""
from pathlib import Path
from threading import Event, Thread
import shutil
import subprocess

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui.exploration_app import create_app
from tests.unit.test_confrontation_criticals_ui import critical_session


@pytest.mark.parametrize('natural', [1, 20])
def test_critical_result_and_burn_runes_in_browser(tmp_path: Path, natural: int) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome required')
    session = critical_session(tmp_path, natural)
    session.configured_board_backend = 'none'
    app = create_app(session)
    done, report = Event(), {}

    @app.post('/__test/result')
    def result():
        report.update(request.get_json())
        done.set()
        return {'ok': True}

    harness = '''<script>
(async()=>{
 const check=(v,m)=>{if(!v)throw Error(m)};
 const wait=async f=>{for(let i=0;i<240;i++){if(f())return;await new Promise(r=>setTimeout(r,25))}throw Error('timeout')};
 try{
  await wait(()=>state?.exploration_mana?.phase==='check'&&!busy&&!boardPanelSyncPromise);
  check(document.querySelector('.confrontation-instruction').textContent.includes('Naturalne 20'),'critical rules missing');
  await api('/api/exploration-mana',{action:'roll',rolls:[NATURAL],revision:state.exploration_mana.revision},'');
  await wait(()=>!busy&&!boardPanelSyncPromise&&state.exploration_mana.phase==='after_action');
  const box=document.querySelector('.confrontation-critical');
  check(box?.textContent.includes(NATURAL===20?'Krytyczny sukces!':'Krytyczna porażka!'),'critical banner missing');
  check(box.textContent.includes(NATURAL===20?'Wpływ: 10':'Spalanie: 2'),'critical amount missing');
  check(!document.querySelector('#exploration-mana-roll'),'unexpected second roll');
  check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');
  check(box.getBoundingClientRect().bottom<innerHeight,'critical banner off screen');
  const p=state.exploration_mana, choice=p.board_choices.find(c=>c.action==='color'&&c.extra.color==='C');
  check(choice,'missing physical burn rune');
  const button=document.querySelector(`.confrontation-controls [data-mana-slot="${choice.slot}"]`);
  check(button.getBoundingClientRect().bottom<innerHeight,'burn rune off screen');
  await api('/api/board/select',{col:19,row:29-choice.slot},'');
  await wait(()=>!busy&&!boardPanelSyncPromise&&state.exploration_mana.mana.burned===1);
  check(state.exploration_mana.mana.pending===(NATURAL===20?0:1),'incorrect remaining burn');
  check(document.querySelector('.confrontation-critical'),'result disappeared before next turn');
  await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
 }catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack})})}
})();</script>'''.replace('NATURAL', str(natural))

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
