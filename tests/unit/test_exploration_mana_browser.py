"""New party-confrontation controls at desktop and phone widths."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import pytest
from tests.unit.test_recruitment_arena import arena
from tests.unit.test_exploration_training_menu import send
from dnd_board_game.ui import confrontation as exploration, training_menu as menu

@pytest.mark.parametrize('width',[390,1100])
def test_party_panels_runes_and_two_stage_roll_forms(tmp_path: Path,width: int):
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:pytest.skip('Chrome required')
    s=arena(tmp_path)
    frames=[s.state_payload()]
    menu_frames=[]
    for action in ('hero:brakka','subject:exploration','party','back','cases','next'):
        menu_frames.append(menu.command(s,dict(action=action,revision=menu.payload(s)['revision'])))
    exploration.start_course(s,'brakka',case_id='object')
    frames.append(s.state_payload())
    for action,extra in [('acknowledge',{}),('acknowledge',{}),('color',{'color':'C'}),('color',{'color':'B'}),('take',{'index':0}),('test',{'bonus':2}),('roll',{'rolls':[20]}),('roll',{'rolls':[8]})]:
        send(s,action,**extra);frames.append(s.state_payload())
    static=Path('src/dnd_board_game/ui/static')
    scripts='\n'.join((static/name).read_text() for name in ('physical_mana.js','training_arena.js','confrontation.js','exploration_mana.js'))
    css='\n'.join((static/name).read_text() for name in ('exploration.css','physical_mana.css','training_arena.css'))
    harness=r'''
let state=frames[0],busy=false,call=null;
function esc(v){return String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');}
function api(path,body){call={path,body};}
function check(value,message){if(!value)throw Error(message);}
try {
 renderTrainingArena();
 check(document.querySelectorAll('.training-roster button').length===7,'missing heroes');
 for(const frame of menuFrames){state=frame;renderTrainingArena();check(document.documentElement.scrollWidth<=innerWidth,'menu overflow');}
 for(const frame of frames.slice(1)){
  state=frame;renderTrainingArena();const p=state.exploration_mana;
  check(document.querySelectorAll('.confrontation-party article').length===3,'party missing');
  check(p.effect_name==='Postęp','object effect name');
  if(p.party.some(h=>h.assigned))check(document.querySelector('.confrontation-party').innerText.includes('postęp'),'object method label');
  if(p.phase==='impact')check(p.attempt.modifiers.some(m=>m.label==='Pasywy postępu'),'object modifier label');
  check(document.documentElement.scrollWidth<=innerWidth,'overflow '+p.phase);
  check(document.querySelectorAll('#training-tools button').length===2,'retry/back missing');
  document.querySelectorAll('#training-tools button')[1].click();check(call.body.action==='leave','wrong back');
  if(p.phase==='introduction'){explorationManaPrimary();check(call.body.action==='acknowledge','missing confirm rune');}
  if(p.mana.phase==='choose'){
   check(document.querySelectorAll('.confrontation-offer article').length===2,'offer missing');
   check(document.querySelector('.confrontation-offer').innerText.includes('Stanowczość'),'passive preview missing');
   document.querySelector('[data-mana-slot="6"]').click();check(call.body.action==='take'&&call.body.index===0,'wrong take');
  }
  if(p.attempt.phase==='roll'){
   const f=document.getElementById('exploration-mana-roll'),input=f.querySelector('input');
   check(input.max===String(p.attempt.die),'wrong die limit');
   input.value=p.attempt.die;f.requestSubmit();
   check(call.body.action==='roll'&&call.body.rolls[0]===p.attempt.die,'wrong natural result');
   check(call.body.revision===p.revision,'stale protection missing');
  }
  if(p.phase==='after_action')check(document.querySelector('#training-arena-panel').innerText.includes('Postęp:'),'result missing');
 }
 document.getElementById('result').textContent='PASS';
}catch(e){document.getElementById('result').textContent='FAIL: '+e.stack;}
'''
    page=tmp_path/'lesson.html'
    page.write_text('<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        +'<style>'+css+'</style><div id="training-arena-panel"></div><pre id="result">PENDING</pre>'
        +'<script>const menuFrames='+json.dumps(menu_frames).replace('</','<\\/')+';const frames='+json.dumps(frames).replace('</','<\\/')+';'+scripts+harness+'</script>')
    result=subprocess.run([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
        '--no-first-run','--disable-background-networking','--no-proxy-server',
        f'--user-data-dir={tmp_path/"chrome"}',f'--window-size={width},1000','--dump-dom',page.as_uri()],
        capture_output=True,text=True,timeout=25)
    assert result.returncode==0,result.stderr[-1000:]
    status=re.search(r'<pre id="result">(.*?)</pre>',result.stdout,re.S)
    assert status and status.group(1)=='PASS',status.group(1) if status else result.stdout[-1500:]
