"""Confrontation layout and board input in the real Mission 0 page."""
from pathlib import Path
from threading import Event, Thread
import shutil
import subprocess

from flask import request
import pytest
from werkzeug.serving import make_server
from dnd_board_game.ui.exploration_app import create_app
from tests.unit.test_confrontation_presentation import start


@pytest.mark.parametrize('scene_name,count,width,height', [('nessa',3,1300,720), ('nessa',6,1131,720), ('cart',6,1131,720)])
def test_nessa_portraits_choices_and_board_scrolling(tmp_path: Path, width: int, height: int, scene_name: str, count: int):
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome: pytest.skip('Chrome required')
    s=start(tmp_path,count=count,scene_name=scene_name);s.configured_board_backend='none'
    app=create_app(s);done=Event();report={}
    @app.post('/__test/result')
    def report_result():
        report.update(request.get_json());done.set();return {'ok':True}
    harness=r'''<script>
(async()=>{
const check=(v,m)=>{if(!v)throw Error(m)};
const wait=async f=>{for(let i=0;i<180;i++){if(f())return;await new Promise(r=>setTimeout(r,25))}throw Error('timeout')};
const field=async(slot)=>{await wait(()=>!busy&&!boardPanelSyncPromise);const revision=state.board_selection.revision;await api('/api/board/select',{col:19,row:29-slot},'');await wait(()=>!busy&&!boardPanelSyncPromise&&state.board_selection.revision!==revision)};
const press=async(action,extra=null)=>{const c=state.exploration_mana.board_choices.find(c=>c.action===action&&(!extra||Object.entries(extra).every(([k,v])=>c.extra[k]===v)));check(c,'missing '+action);await field(c.slot)};
const checkManaPortrait=(showHero=true)=>{
 const p=state.exploration_mana, hero=p.party.find(h=>h.id===p.actor);
 const portrait=document.querySelector('.confrontation-scene-image');
 check(portrait?.getAttribute('src')===p.image_url,'portrait must match the current step');
 check(portrait.alt===p.scene.name,'portrait must name its subject');
};
const bounds=()=>{
 const panel=document.getElementById('mission-panel');
 check(panel.classList.contains('confrontation-view')&&!panel.classList.contains('mission-reading'),'dedicated layout');
 check(panel.getBoundingClientRect().bottom<=innerHeight+1,'panel clipped at bottom');
 check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');
 const controls=panel.querySelector('.confrontation-controls');
 if(state.exploration_mana.phase==='turn'&&['ready','choose','burn'].includes(state.exploration_mana.mana.phase))check(controls.scrollHeight<=controls.clientHeight+1,'decision requires scrolling '+JSON.stringify({phase:state.exploration_mana.phase,mana:state.exploration_mana.mana.phase,innerHeight,top:panel.getBoundingClientRect().top,panel:panel.clientHeight,controls:controls.clientHeight,content:controls.scrollHeight}));
};
try{
 await wait(()=>state?.exploration_mana?.active&&!busy);
 await wait(()=>[...document.querySelectorAll('.confrontation-view img')].length===2&&[...document.querySelectorAll('.confrontation-view img')].every(i=>i.complete&&i.naturalWidth));
 check(getComputedStyle(document.querySelector('.confrontation-scene-image')).objectFit==='contain','portrait cropped');
 check(!document.getElementById('mission-panel').innerText.includes('Kompromis'),'early spoiler');
 bounds();
 document.querySelector('.confrontation-controls').insertAdjacentHTML('beforeend','<p style="height:1200px;flex-shrink:0">Reading probe</p>');
 const revision=state.exploration_mana.revision;
 await field(27);await wait(()=>document.querySelector('.confrontation-controls').scrollTop>0);
 check(document.querySelector('.confrontation-controls').scrollTop>0,'board + must scroll description');
 check(state.exploration_mana.revision===revision,'scroll mutated confrontation');
 await press('acknowledge');bounds();
 check(document.querySelectorAll('.confrontation-approaches article').length===6,'six scene approaches');
 check(document.querySelector('.confrontation-approaches').textContent.includes('Wsparcie'),'support links visible');
 check(document.querySelector('.approach-chooser img')?.alt===state.exploration_mana.actor_name,'current hero portrait');
 check(document.querySelector('.approach-chooser img').getBoundingClientRect().height>=80,'larger chooser portrait');
 check(!document.querySelector('.approach-chooser').innerText.includes('Wsparcie daje sojusznikowi'),'removed support sentence');
 check(document.querySelector('.support-target .support-rune svg'),'support rune badges');
 const tiles=[...document.querySelectorAll('.approach-card')];
 check(tiles.length===6,'six clickable description tiles');
 check(document.querySelector('.approach-availability.repeatable')?.textContent==='Może się powtarzać','repeatable label');
 check(document.querySelector('.approach-availability.exclusive')?.textContent==='Dla jednej postaci','exclusive label');
 check(tiles.every(t=>Number(t.dataset.manaSlot)>=6&&Number(t.dataset.manaSlot)<26),'must use runes, not basic actions');
 check(!document.querySelector('.confrontation-controls [data-mana-slot="6"]'),'duplicate choice toolbar');
 if(innerWidth>=900){
  const area=document.querySelector('.confrontation-scroll');
  check(area.scrollHeight<=area.clientHeight+1,'approaches need scrolling '+JSON.stringify({height:area.clientHeight,content:area.scrollHeight}));
  for(const tile of tiles){
   check(tile.scrollHeight<=tile.clientHeight+1,'tile text clipped');
   check(tile.getBoundingClientRect().bottom<=area.getBoundingClientRect().bottom+1,'tile outside viewport');
  }
 }
 // The tile itself selects the approach; remaining selections use board runes.
 const firstId=state.exploration_mana.actor;
 const anySupport=state.exploration_mana.approaches.find(a=>a.supports.includes('*'));
 const firstSlot=state.exploration_mana.board_choices.find(c=>c.extra.approach===anySupport.id).slot;
 document.querySelector(`.approach-card[data-mana-slot="${firstSlot}"]`).click();
 await wait(()=>!busy&&state.exploration_mana.actor!==firstId);
 await press('undo');bounds();
 check(state.exploration_mana.actor===firstId,'undo approach actor');
 await field(firstSlot);

 check(Boolean(document.querySelector(`.approach-card[data-mana-slot="${firstSlot}"]`))===anySupport.repeatable,'availability after choice');
 check(state.exploration_mana.mana.deck===state.exploration_mana.party.length*10&&state.exploration_mana.mana.phase==='setup','assignment does not draw cards');
 while(state.exploration_mana.phase==='approach') await press('approach',{approach:state.exploration_mana.approaches.find(a=>a.available).id});bounds();
 const instruction=document.querySelector('.confrontation-controls').innerText;
 check(instruction.includes((state.exploration_mana.party.length*10)+' kart')&&instruction.includes('czerwone: '+(state.exploration_mana.party.length*2)),'deck composition');
 check(!instruction.includes('Figurka')&&!instruction.includes('(5,7)'),'setup contains coordinates');
 await press('acknowledge');bounds();
 checkManaPortrait(false);
 await press('color',{color:'F'});await press('color',{color:'B'});bounds();
 checkManaPortrait();
 const luminance=rgb=>rgb.match(/[\d.]+/g).slice(0,3).map(Number).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((sum,v,i)=>sum+v*[.2126,.7152,.0722][i],0);
 for(const color of ['F','B']){
  const card=document.querySelector(`.confrontation-offer article.mana-${color}`);
  const display=state.exploration_mana.passive_details[color];
  check(card.querySelector('.passive-name').textContent===display.name,'missing passive name');
  check(card.querySelector('.passive-effect').textContent.trim().length>0,'missing passive description');
  for(const text of card.querySelectorAll('.confrontation-offer-symbol b,.mana-passive-description strong,.mana-passive-description p')){
   const bg=luminance(getComputedStyle(card).backgroundColor),fg=luminance(getComputedStyle(text).color);
   check((Math.max(bg,fg)+.05)/(Math.min(bg,fg)+.05)>=4.5,'unreadable '+color+' mana description');
  }
 }
 await press('undo');bounds();
 check(state.exploration_mana.mana.offer.length===1,'undo wrong color');
 checkManaPortrait(false);
 check(document.querySelector('.confrontation-controls').innerText.includes('Nie dobieraj kolejnej'),'physical correction instruction');
 await press('color',{color:'N'});bounds();
 const options=[...document.querySelectorAll('.confrontation-offer [data-mana-slot]')];
 check(options.length===2,'two physical card choices');
 check(document.querySelector('.confrontation-offer .mana-passive-description'),'card choice retains passive explanations');
 check(!document.querySelector('.confrontation-offer img'),'passive choices use text without diagrams');
 check(options.every(el=>el.getBoundingClientRect().bottom<=innerHeight),'choice below viewport');
 await press('take',{index:0});bounds();
 checkManaPortrait(false);
 check(state.exploration_mana.party.some(h=>h.cards.includes('F')),'selected card not recorded');
 const p=state.exploration_mana;
 check(document.querySelectorAll('.confrontation-active-hero').length===1,'one active hero');
 check(document.querySelectorAll('.confrontation-party-summary>span').length===p.party.length,'compact party');
 check(!document.querySelector('.confrontation-party'),'old full party cards removed');
 check(document.querySelector('.confrontation-active-hero .confrontation-pool svg'),'pool symbols visible');
 check(document.querySelector('.confrontation-help-person img'),'recipient portrait');
 const beforeHelp=JSON.stringify(state.exploration_mana), helps=confrontationHelpChoices(p);
 const helpBefore=confrontationCurrentHelp(p).extra.target;
 await field(27);
 if(helps.length>1)check(confrontationCurrentHelp(p).extra.target!==helpBefore,'plus cycles helper recipient');
 check(JSON.stringify(state.exploration_mana)===beforeHelp,'browsing spends nothing');
 await field(26);check(confrontationCurrentHelp(p).extra.target===helpBefore,'minus restores recipient');
 for(const [slot,kind] of [[24,'bonus'],[25,'effects']]){
  await field(slot);await wait(()=>document.getElementById('confrontation-detail')?.open&&!boardPanelSyncPromise);
  check(confrontationDetail.kind===kind,'rune opens correct detail');
  await field(27);await field(26);
  check(JSON.stringify(state.exploration_mana)===beforeHelp,'detail spends nothing');
  await field(29);await wait(()=>!document.getElementById('confrontation-detail').open&&!boardPanelSyncPromise);
  check(!state.board_selection.panel_context?.startsWith('confrontation-detail:'),'closing releases exclusive board context');
 }
 check(state.exploration_mana.mana.offer[0]==='N','other card not retained');
 const choices=state.exploration_mana.board_choices;
 check(choices.filter(c=>c.action==='test').length===1,'one test at current charge');
 const aid=choices.find(c=>c.action==='support');
 check(aid.label.includes('spal 1'),'support shows cost');
 const target=aid.extra.target;
 await press('support',{target});bounds();
 check(state.exploration_mana.mana.phase==='burn'&&state.exploration_mana.mana.pending===1,'support must burn exactly one');
 check(state.exploration_mana.party.find(h=>h.id===target).aid>=1,'support recorded for ally');
 check(!state.exploration_mana.board_choices.some(c=>c.action==='advance'),'cannot skip burn');
 await press('color',{color:'C'});bounds();
 check(state.exploration_mana.mana.burned===1,'reported burn recorded');
 await press('advance');
 checkManaPortrait(false);
 const recipient=state.exploration_mana.party.find(h=>h.id===state.exploration_mana.actor);
 check(recipient.aid>=1&&recipient.roll_bonus===0,'recipient has help before drawing');
 check(document.querySelector('.confrontation-pool-summary').textContent.includes('Mana +0'),'card bonus is labelled as mana');
 check(document.querySelector('.confrontation-received-aid b')?.textContent===`Pomoc +${recipient.aid}`,'help is visible during reveal');
 while(state.exploration_mana.mana.phase==='reveal') await press('color');
 checkManaPortrait();
 check(document.querySelector('.confrontation-received-aid b')?.textContent===`Pomoc +${recipient.aid}`,'help is visible during card selection');
 await press('take',{index:0});await press('peek');bounds();
 check(document.querySelector('.confrontation-received-aid b')?.textContent===`Pomoc +${recipient.aid}`,'drawing and peeking do not consume help');
 check(state.exploration_mana.phase==='peek_choice','peek must go directly to position choice');
 checkManaPortrait(false);
 check(!state.exploration_mana.board_choices.some(c=>c.action==='peek_color'||c.action==='color'),'no color reporting during peek');
 check(!document.querySelector('.peeked-mana'),'no color display for physical peek');
 await press('peek_finish',{move_top:true});bounds();
 check(state.exploration_mana.phase==='after_action'&&state.exploration_mana.mana.burned===1,'peek ends action without burning');


 await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:'PASS'})});
}catch(e){await fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:e.stack,body:document.body.innerText.slice(-2400)})})}
})();</script>'''
    error_hook="""<script>window.alert=message=>{throw Error(message)};window.addEventListener('error',e=>fetch('/__test/result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({result:String(e.message)+' '+e.filename+':'+e.lineno})}));</script>"""
    @app.after_request
    def inject(response):
        if request.path=='/play' and response.status_code==200:
            response.set_data(response.get_data(as_text=True).replace('<head>','<head>'+error_hook).replace('</body>',harness+'</body>'))
        return response
    server=make_server('127.0.0.1',0,app,threaded=True);worker=Thread(target=server.serve_forever,daemon=True);worker.start();process=None
    try:
        process=subprocess.Popen([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run',
            '--disable-background-networking','--no-proxy-server',f'--user-data-dir={tmp_path/"chrome"}',f'--window-size={width},{height + 143}',
            f'http://127.0.0.1:{server.server_port}/play'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
        assert done.wait(40),'Browser did not report'
        assert report.get('result')=='PASS',report
    finally:
        if process:
            process.terminate()
            try:process.communicate(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.communicate(timeout=5)
        server.shutdown();worker.join(timeout=2)
