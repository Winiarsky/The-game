"""The live /play client consumes physical board events for personal baskets."""
import json
import shutil
import subprocess
from pathlib import Path
from threading import Event, Thread
from typing import Any

import pytest
from flask import request
from werkzeug.serving import make_server
from tests.unit.test_mission_zero import session,start_battle
from tests.unit.test_tabletop_combat_browser import CombatBoard
from dnd_board_game.ui.routes import create_app


def test_live_board_preparation_payment_and_layout(tmp_path: Path) -> None:
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:pytest.skip('Chrome required')
    game=session(tmp_path,3);game.encounter_rng.seed(0);start_battle(game)
    board=CombatBoard();game.attach_board_connection(board,backend='simulator')
    app=create_app(game,character_dir=tmp_path/'characters');done=Event();report={}

    @app.post('/__test/press')
    def press():return {'delivered':board.press_field(tuple(request.get_json()['position']))}

    @app.post('/__test/result')
    def result():report.update(request.get_json());done.set();return {'ok':True}

    harness=r'''<script>(async()=>{
const check=(v,m)=>{if(!v)throw Error(m)};
const wait=async(f,m)=>{for(let i=0;i<300;i++){if(f())return;await new Promise(r=>setTimeout(r,20))}throw Error('timeout '+m)};
const slot=async n=>{
 await wait(()=>boardScanInFlight&&!busy&&!boardPanelSyncPromise,'armed');
 const rev=state.board_selection.revision;
 let delivered=false;
 for(let i=0;i<150&&!delivered;i++){delivered=(await(await fetch('/__test/press',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({position:[19,29-n]})})).json()).delivered;if(!delivered)await new Promise(r=>setTimeout(r,20))}
 check(delivered,'field '+n+' not selectable');
 await wait(()=>state.board_selection.revision!==rev&&!busy&&!boardPanelSyncPromise,'result '+n);
};
try{
 await wait(()=>state?.combat?.shared_mana?.rune_view?.model==='baskets_v02'&&document.querySelector('.tt-baskets'),'basket UI');
 check(document.body.innerText.includes('Zadeklaruj żetony'),'declaration visible');
 while(state.combat.shared_mana.runes.phase==='allocation'){
  const choices=state.combat.shared_mana.rune_view.choices;
  const next=choices.find(c=>c.command==='basket_take')||choices.find(c=>c.slot===28);
  await slot(next.slot);
 }
 await wait(()=>document.querySelector('.tt-idle'),'action menu');
 check(document.querySelector('.tt-basket-counts').textContent.includes('Obrona 4/4'),'individual limits');
 const before=JSON.stringify(state.combat.shared_mana.runes.hands);
 await slot(6);
 await wait(()=>state.combat.shared_mana.declaration,'power preview');
 await slot(28);await wait(()=>document.querySelector('.tt-baskets'),'base chooser');
 await slot(6);await slot(28);await slot(28);
 check(document.body.innerText.includes('Koszt:'),'summary');
 check(before===JSON.stringify(state.combat.shared_mana.runes.hands),'early charge');
 check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');
 await slot(28);await wait(()=>document.querySelector('.tt-idle'),'completed power');
 check(state.combat.shared_mana.rune_view.hands[0].baskets[1].count===3,'paid own category');
 check(state.combat.shared_mana.rune_view.special_used,'special budget');
 await stopBoardScanLoop();
 await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
}catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack,body:document.body.innerText.slice(-2400),error:boardScanError})})}
})();</script>'''
    error_hook="""<script>window.alert=m=>{throw Error(m)};window.addEventListener('error',e=>fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.message+' '+e.filename+':'+e.lineno})}));</script>"""
    @app.after_request
    def inject(response: Any):
        if request.path=='/play':response.set_data(response.get_data(as_text=True).replace('<head>','<head>'+error_hook).replace('</body>',harness+'</body>'))
        return response
    server=make_server('127.0.0.1',0,app,threaded=True);worker=Thread(target=server.serve_forever,daemon=True);worker.start();process=None
    try:
        process=subprocess.Popen([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--disable-background-networking','--no-proxy-server',f'--user-data-dir={tmp_path/"chrome"}','--window-size=1131,800',f'http://127.0.0.1:{server.server_port}/play'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        assert done.wait(75),'Browser did not report'
        assert report.get('result')=='PASS',report
    finally:
        if process:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        board.cancel_scan();server.shutdown();worker.join(timeout=2)
