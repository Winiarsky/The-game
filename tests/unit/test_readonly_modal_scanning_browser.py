"""Read-only dialogs must keep the automatic hardware scan loop alive."""
from pathlib import Path
from queue import Queue
from threading import Event, Lock, Thread
from typing import Any, Callable
import shutil
import subprocess

from flask import request
import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui.exploration_app import create_app
from tests.unit.test_initiative_panel import Board
from tests.unit.test_session_board_navigation import ready_conversation, game_snapshot


class WaitingBoard(Board):
    """Deliver a press only to a scan actually armed by the browser."""

    def __init__(self) -> None:
        super().__init__()
        self.lock = Lock()
        self.receiver: Queue | None = None
        self.positions: set[tuple[int, int]] = set()

    def prepare_scan(self, positions: Any, **contract: Any) -> Callable:
        receiver: Queue = Queue()
        with self.lock:
            self.receiver = receiver
            self.positions = set(map(tuple, positions))

        def receive(timeout_s: float | None = None) -> tuple[int, int] | None:
            try:
                return receiver.get(timeout=10)
            finally:
                with self.lock:
                    if self.receiver is receiver:
                        self.receiver = None

        return receive

    def cancel_scan(self) -> None:
        with self.lock:
            if self.receiver is not None:
                self.receiver.put(None)

    def press(self, slot: int) -> bool:
        with self.lock:
            position = (19, 29 - slot)
            if self.receiver is None or position not in self.positions:
                return False
            self.receiver.put(position)
            return True


@pytest.mark.parametrize('opening', ['board', 'mouse'])
def test_modal_automatic_scans_scroll_close_and_resume(tmp_path: Path, opening: str) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome required')
    session, _, _ = ready_conversation(tmp_path)
    board = WaitingBoard()
    session.attach_board_connection(board, backend='simulator')
    before = game_snapshot(session)
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

    harness = r'''<script>
    (async()=>{
      const check=(v,m)=>{if(!v)throw Error(m)};
      const wait=async(f,message)=>{for(let i=0;i<200;i++){if(f())return;await new Promise(r=>setTimeout(r,20));}throw Error(message)};
      const press=async(slot)=>{
        await wait(()=>boardScanInFlight&&!boardPanelSyncPromise&&!busy,'scanner not armed for '+slot);
        const revision=state.board_selection.revision;
        let delivered=false;
        for(let i=0;i<100&&!delivered;i++){
          const response=await fetch('/__test/press',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({slot})});
          delivered=(await response.json()).delivered;
          if(!delivered)await new Promise(r=>setTimeout(r,20));
        }
        check(delivered,'no hardware receiver for '+slot);
        await wait(()=>state.board_selection.revision!==revision&&!boardPanelSyncPromise,'press not resolved '+slot);
      };
      try {
        await wait(()=>state?.exploration_mana?.active&&!busy,'initial conversation');
        const original=JSON.stringify(state.exploration_mana);
        const help=confrontationCurrentHelp(state.exploration_mana).extra.target;
        for(const [slot,kind,close] of [[25,'effects',28],[24,'bonus',29]]){
          await wait(()=>boardScanInFlight,'initial scanner');
          if(OPENING==='board')await press(slot);
          else check(openConfrontationDetail(kind),'mouse open');
          await wait(()=>document.getElementById('confrontation-detail')?.open&&!boardPanelSyncPromise,'detail opening');
          const area=document.querySelector('.confrontation-detail-body');
          area.insertAdjacentHTML('beforeend','<p style="height:1000px">Long description</p>');
          await press(27);
          check(area.scrollTop>0,'plus scrolls modal');
          const down=area.scrollTop;
          await press(26);
          check(area.scrollTop<down,'minus scrolls modal');
          check(confrontationCurrentHelp(state.exploration_mana).extra.target===help,'modal keys changed help target');
          await press(close);
          await wait(()=>!document.getElementById('confrontation-detail').open&&!boardPanelSyncPromise,'detail close');
          check(!state.board_selection.panel_context,'detail released');
        }
        await press(27);
        check(confrontationCurrentHelp(state.exploration_mana).extra.target!==help,'conversation controls resume');
        await press(26);
        // The session menu uses the same modal scan gate.
        check(SessionNavigation.open(),'open menu');
        await wait(()=>!boardPanelSyncPromise,'menu context');
        await press(27);
        check(document.querySelector('.session-focused').dataset.sessionChoice==='journal','menu plus');
        await press(26);await press(28);
        await wait(()=>!document.getElementById('session-navigation').open&&!boardPanelSyncPromise,'menu close');
        check(JSON.stringify(state.exploration_mana)===original,'reading changed game state');
        // Unrelated screen-only dialogs must still suppress board input.
        const screen=document.createElement('dialog');document.body.append(screen);screen.showModal();
        check(!boardSelectionCanAutoArm(),'unrelated modal accepts game presses');screen.close();
        await stopBoardScanLoop();
        await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
      }catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack,phase:boardInputPhase,error:boardScanError})});}
    })();</script>'''.replace('OPENING', repr(opening))

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
            f'--user-data-dir={tmp_path / "chrome"}', '--window-size=1131,863',
            f'http://127.0.0.1:{server.server_port}/play',
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        assert done.wait(35), 'Browser did not report'
        assert report.get('result') == 'PASS', report
        assert game_snapshot(session) == before
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
