"""All four social conditions through the full browser and board API."""
from pathlib import Path
import shutil
import subprocess
from threading import Event, Thread

import pytest
from werkzeug.serving import make_server

from dnd_board_game.ui.routes import create_app
from tests.unit.test_recruitment_arena import arena


@pytest.mark.parametrize('width', [390, 1100])
def test_social_choices_use_runes_and_display_distinct_results(tmp_path: Path, width: int):
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome required')
    s=arena(tmp_path)
    app=create_app(s)
    finished=Event()
    reported={}
    @app.post('/__test/exploration-result')
    def report_result():
        from flask import request
        reported.update(request.get_json())
        finished.set()
        return {'ok': True}
    harness=r'''
<script>
(async()=>{
 const waitFor=async predicate=>{for(let i=0;i<160;i++){if(predicate())return;await new Promise(r=>setTimeout(r,25));}throw Error('Timed out');};
 const check=(ok,message)=>{if(!ok)throw Error(message);};
 const press=async(action,extra={})=>{
   await waitFor(()=>!busy);
   const c=state.exploration_mana.board_choices.find(c=>c.action===action && Object.entries(extra).every(([k,v])=>c.extra[k]===v));
   check(c,'Missing rune '+action);
   check(state.board_selection.legal_positions.some(p=>p[0]===19 && p[1]===29-c.slot),'Rune not in scan mask');
   if(!['acknowledge','leave'].includes(action))check(document.querySelector(`[data-mana-slot="${c.slot}"] svg`),'Rune not visible');
   await api('/api/board/select',{col:19,row:29-c.slot},'Runa…');
 };
 const pick=async colors=>{for(const color of colors){if(state.exploration_mana.attempt.phase==='decision')await press('draw');await press('choose',{color});}};
 let result='PASS';
 try {
   await waitFor(()=>state?.exploration_mana && !busy);
   for(const kind of ['compromise','sensitive_topic','color_goal','favor'])for(const take of [true,false]) {
     const entry=document.querySelector('.mana-hero-entry');
     const group=entry.querySelector('details');group.open=true;
     check(group.querySelector('summary').innerText==='Cztery warunki rozmów','New lessons hard to find');
     const button=[...group.querySelectorAll('button')].find(b=>b.getAttribute('onclick').includes("lesson:'condition_"+kind+"'"));
     check(button,'Lesson missing from roster');button.click();
     await waitFor(()=>state.exploration_mana.active && !busy);
     await press('acknowledge');
     while(state.exploration_mana.phase==='setup')await press('acknowledge');
     check(document.querySelector('.mana-condition').innerText.length>80,'Condition hidden before method');
     await press('start');
     if(kind==='compromise') {
       await pick('NCF');
       check(!document.querySelector('[data-mana-slot="28"]'),'Implicit confirm of bargain');
       check(document.querySelector('[data-mana-slot="24"]').innerText.includes('Klucz'),'Wrong bargain rune');
       await press(take?'accept_bargain':'decline_bargain');
       if(!take)await pick('N');
     } else if(kind==='sensitive_topic')await pick(take?'CCC':'NNNFB');
     else if(kind==='color_goal')await pick(take?'NNFC':'CCC');
     else if(take){await pick('NNNN');await press('draw');await press('arm_favor');await press('cancel_favor');await press('arm_favor');await press('choose',{color:'C'});}
     else await pick('CCC');
     const p=state.exploration_mana;
     check(p.attempt.phase==='result','Missing outcome');
     const panel=document.getElementById('training-arena-panel');
     if(kind==='compromise' && take){check(panel.innerText.includes('Porozumienie'),'Compromise labeled failure');check(!panel.innerText.includes('Dokładnie 21 —'),'Compromise pretends exact 21');}
     if(kind==='color_goal' && take)check(panel.innerText.includes('nagroda przyznana'),'Goal reward missing');
     if(kind==='favor' && take)check(panel.innerText.includes('Zobowiązanie pozostaje'),'Obligation missing');
     const f=p.followups[p.followups.length-1];
     await press('debrief',{id:f.id});
     check(panel.innerText.includes(f.message),'Followup not shown');
     check(state.exploration_mana.attempt.outcome_flags.includes(f.flag),'Followup had no persistent effect');
     check(document.documentElement.scrollWidth<=innerWidth,'Horizontal overflow');
     await press('leave');
   }
 }catch(e){result='FAIL: '+e.stack;}
 await fetch('/__test/exploration-result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result})});
})();
</script>
'''
    @app.after_request
    def inject(response):
        from flask import request
        if request.path=='/play' and response.status_code==200:
            response.set_data(response.get_data(as_text=True).replace('</body>',harness+'</body>'))
        return response
    server=make_server('127.0.0.1',0,app,threaded=True)
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    process=None
    try:
        process=subprocess.Popen([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
            '--no-first-run','--disable-background-networking','--no-proxy-server',
            f'--user-data-dir={tmp_path/"chrome"}',f'--window-size={width},1000',
            f'http://127.0.0.1:{server.server_port}/play'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        assert finished.wait(25), 'Browser did not report the lesson result'
        assert reported.get('result')=='PASS', reported
    finally:
        if process:
            process.terminate()
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate(timeout=5)
        server.shutdown()
        thread.join(timeout=3)
