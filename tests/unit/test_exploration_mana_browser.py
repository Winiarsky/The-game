"""Render and operate actual lesson controls at desktop and phone widths."""
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from tests.unit.test_recruitment_arena import arena
from tests.unit.test_exploration_mana_runtime import prepared, send


@pytest.mark.parametrize('width', [390, 1100])
def test_exploration_roster_methods_cards_and_two_physical_dice(tmp_path: Path, width: int):
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome required')
    s = arena(tmp_path)
    frames = [s.state_payload()]
    send(s, 'open', hero='brakka', lesson='bust')
    frames.append(s.state_payload())
    send(s, 'acknowledge')
    frames.append(s.state_payload())
    while s.state_payload()['exploration_mana']['phase'] == 'setup':
        send(s, 'acknowledge')
    frames.append(s.state_payload())
    send(s, 'start', method='force')
    frames.append(s.state_payload())
    for i, color in enumerate('CCNF'):
        if i:
            send(s, 'draw')
        send(s, 'choose', color=color)
    frames.append(s.state_payload())
    send(s, 'roll', rolls=[20, 1])
    frames.append(s.state_payload())
    static = Path('src/dnd_board_game/ui/static')
    scripts = '\n'.join((static/name).read_text() for name in ('physical_mana.js','training_arena.js','exploration_mana.js'))
    css = '\n'.join((static/name).read_text() for name in ('exploration.css','physical_mana.css','training_arena.css'))
    harness = r'''
let state=frames[0], busy=false, call=null;
function esc(v) {return String(v??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');}
function api(path,body) {call={path,body};}
function check(value,message) {if(!value) throw Error(message);}
try {
  renderTrainingArena();
  check(document.querySelectorAll('.mana-hero-entry').length===7,'seven exploration entries missing');
  for(const entry of document.querySelectorAll('.mana-hero-entry')) {
    check(entry.innerText.includes('Porozmawiaj z NPC'),'NPC entry missing');
    check(entry.innerText.includes('Interakcja z obiektem'),'object entry missing');
    check(entry.innerText.includes('Pułapka w walce'),'trap entry missing');
  }
  document.querySelector('.mana-hero-entry button').click();
  check(call.path==='/api/exploration-mana' && call.body.lesson==='npc','wrong entry route');
  for(let i=1;i<frames.length;i++) {
    state=frames[i];renderTrainingArena();
    check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow at phase '+i);
    check(!document.getElementById('training-arena-panel').hidden,'lesson panel hidden');
    if(i===1) {
      explorationManaPrimary();
      check(call.body.action==='acknowledge','primary action skips introduction');
    }
    if(i===3) {
      check(document.querySelectorAll('.mana-methods article').length===1,'wrong eligible actor');
      check(!document.querySelector('.exploration-mana-values'),'profile leaked before commitment');
      const choice=document.querySelector('.mana-methods button');
      check(choice.dataset.manaSlot==='7' && choice.querySelector('svg')?.getAttribute('data-panel-slot')==='7','Brakka rune differs from board');
      check(choice.innerText.includes('Wieża'),'rune name missing');
      choice.click();check(call.body.action==='start' && call.body.method==='force','rune fallback selects wrong method');
    }
    if(i===4) {
      check(document.querySelectorAll('.mana-value').length===5,'profile missing');
      check(document.querySelectorAll('.mana-color-buttons button').length===5,'missing color input');
      check(!document.querySelector('.mana-decisions'),'can pass after seeing offer');
      const color=document.querySelector('.mana-color-buttons button:not(:disabled)');
      check(color.dataset.manaSlot==='13' && color.querySelector('svg[data-panel-slot="13"]'),'red rune missing');
      color.click();check(call.body.action==='choose' && call.body.color==='C','wrong selected color');
    }
    if(i===5) {
      const form=document.getElementById('exploration-mana-roll');
      check(form.querySelectorAll('input').length===2,'bust needs two physical dice');
      const inputs=form.querySelectorAll('input');inputs[0].value=20;inputs[1].value=1;
      form.requestSubmit();
      check(call.body.action==='roll' && call.body.rolls.join(',')==='20,1','wrong physical results');
      check(call.body.revision===state.exploration_mana.revision,'missing stale-input protection');
    }
    if(i===6) {
      check(document.getElementById('training-arena-panel').innerText.includes('Porażka'),'missing failed result');
      check(document.getElementById('training-arena-panel').innerText.includes('zaliczone'),'failure lesson not completed');
    }
  }
  document.getElementById('result').textContent='PASS';
} catch(e) {document.getElementById('result').textContent='FAIL: '+e.stack;}
'''
    page=tmp_path/'lesson.html'
    page.write_text('<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        +'<style>'+css+'</style><div id="training-arena-panel"></div><pre id="result">PENDING</pre>'
        +'<script>const frames='+json.dumps(frames).replace('</','<\\/')+';'+scripts+harness+'</script>')
    result=subprocess.run([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
        '--no-first-run','--disable-background-networking','--no-proxy-server',
        f'--user-data-dir={tmp_path/"chrome"}',f'--window-size={width},1000','--dump-dom',page.as_uri()],
        capture_output=True,text=True,timeout=25)
    assert result.returncode==0,result.stderr[-1000:]
    status=re.search(r'<pre id="result">(.*?)</pre>',result.stdout,re.S)
    assert status and status.group(1)=='PASS',status.group(1) if status else result.stdout[-1500:]
