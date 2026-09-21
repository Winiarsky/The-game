"""A player can read session help and return to narration using only board slots."""
from pathlib import Path
from threading import Event, Thread
import shutil
import subprocess

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui.routes import create_app
from tests.unit.test_mission_zero import session


def test_board_menu_help_and_return_preserve_narration(tmp_path: Path) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome required')
    game = session(tmp_path, 6)
    game.configured_board_backend = 'none'
    app = create_app(game)
    finished = Event()
    report = {}

    @app.post('/__test/result')
    def result():
        report.update(request.get_json())
        finished.set()
        return {'ok': True}

    harness = r'''<script>
    (async () => {
      const check=(value,message)=>{if(!value)throw Error(message)};
      const wait=async predicate=>{for(let i=0;i<200;i++){if(predicate())return;await new Promise(r=>setTimeout(r,20));}throw Error('Timed out');};
      const press=async slot=>{await wait(()=>!busy&&!boardPanelSyncPromise);const revision=state.board_selection.revision;await api('/api/board/select',{col:19,row:29-slot},'');await wait(()=>!busy&&!boardPanelSyncPromise&&state.board_selection.revision!==revision);};
      try {
        await wait(()=>state?.mission&&!busy);
        const original=JSON.stringify(state.mission);
        check(state.player_aid.length===4,'canonical player aid missing');
        check(document.querySelector('[data-mission-slot="28"] svg'),'narration uses physical accept symbol');
        await press(29);
        await wait(()=>document.getElementById('session-navigation')?.open&&state.board_selection.panel_context?.startsWith('session-menu:'));
        check(document.querySelectorAll('#session-navigation .session-focused').length===1,'one menu cursor');
        await press(27);await press(27);await press(28);
        await wait(()=>state.board_selection.panel_context?.startsWith('session-help:'));
        check(document.querySelectorAll('#session-navigation .session-navigation-content>section').length===4,'rules are rendered from all four pages');
        check(document.querySelectorAll('#session-navigation ol li').length===state.player_aid.flatMap(page=>page.sections||[]).flatMap(section=>section.steps||[]).length,'step-by-step rules are complete');
        await press(27);
        {const area=document.querySelector('#session-navigation .session-navigation-content');check(area.scrollTop>0,'board plus scrolls the rules '+JSON.stringify({scroll:area.scrollTop,height:area.clientHeight,total:area.scrollHeight,context:state.board_selection.panel_context,open:document.getElementById('session-navigation').open}));}
        await press(29);
        await wait(()=>state.board_selection.panel_context?.startsWith('session-menu:'));
        await press(27);await press(27);await press(27);await press(28);
        await wait(()=>document.querySelector('#session-navigation h2')?.textContent===sessionUiText('common.party'));
        check(document.querySelectorAll('#session-navigation .session-navigation-content>section').length===6,'six party members');
        await press(28);
        await wait(()=>state.board_selection.panel_context?.startsWith('session-menu:'));
        await press(28);
        await wait(()=>!document.getElementById('session-navigation').open&&!state.board_selection.panel_context);
        check(JSON.stringify(state.mission)===original,'reading changed the mission');
        check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');
        await press(28);
        check(state.mission.text.id==='hero_garran','accept after closing menu advances narration');
        await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
      } catch(error) {
        await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:error.stack,body:document.body.innerText.slice(-1800)})});
      }
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
        process = subprocess.Popen([
            chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
            '--no-first-run', '--disable-background-networking', '--no-proxy-server',
            f'--user-data-dir={tmp_path / "chrome"}', '--window-size=1131,863',
            f'http://127.0.0.1:{server.server_port}/play',
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert finished.wait(35), 'Browser did not report'
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
