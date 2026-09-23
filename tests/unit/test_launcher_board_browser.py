"""Exercise real menu DOM events and scan cancellation in a browser."""
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from dnd_board_game.ui.routes import create_app
from tests.unit.test_launcher_ui import _session


@pytest.mark.parametrize('width', [1131, 1300])
@pytest.mark.parametrize('page_path', ['/', '/new-game'])
def test_runes_click_real_controls_and_follow_menu_changes(tmp_path: Path, width: int, page_path: str) -> None:
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Chrome is needed for browser checks')
    html = create_app(_session(tmp_path)).test_client().get(page_path).get_data(as_text=True)
    static = Path('src/dnd_board_game/ui/static')
    html = re.sub(r'<link rel="stylesheet"[^>]+>', '<style>' + (static/'launcher.css').read_text() + '</style>', html)
    html = re.sub(r'<script src="[^"]*launcher_board.js[^"]*" defer></script>',
                  lambda _: '<script>' + (static/'launcher_board.js').read_text() + '</script>', html)
    html = re.sub(r'<script src="[^"]*session_copy.js[^"]*"[^>]*></script>',
                  lambda _: '<script>' + (static/'session_copy.js').read_text() + '</script>', html)
    harness = r'''
let contract=null, selection=null, pending=null, generation=0, submission=null, released=false, staleNext=false;
const response=data=>Promise.resolve({ok:true,json:()=>Promise.resolve(data)});
window.fetch=(path, options)=>{
 const body=JSON.parse(options.body);
 if(path==='/api/board/navigation') {
  contract=body;
  selection={revision:String(++generation),navigation_token:body.token,connected:true,auto_arm:true};
  if(pending) {const old=pending;pending=null;old(staleNext
    ? {navigation_event:{token:body.token,slot:6},board_selection:selection}
    : {board_selection:selection});staleNext=false;}
  return response({board_selection:selection});
 }
 if(path.endsWith('/release')) {released=true;return response({ok:true});}
 if(path==='/api/board/scan') return new Promise(resolve=>{pending=data=>resolve({ok:true,json:()=>Promise.resolve(data)});});
 throw new Error('Unexpected request '+path);
};
const check=(ok, message)=>{if(!ok)throw new Error(message);};
const pause=()=>new Promise(resolve=>setTimeout(resolve,10));
async function until(predicate) {for(let i=0;i<100;i++){if(predicate())return;await pause();}throw new Error('Timed out');}
async function press(slot) {
 await until(()=>pending && (contract.slots.includes(slot)||contract.controls.includes(slot)||(slot===29 && contract.back)));
 const resolve=pending;pending=null;
 resolve({navigation_event:{token:contract.token,slot},board_selection:{...selection,auto_arm:false}});
 await pause();
}
document.addEventListener('submit',event=>{event.preventDefault();submission={path:new URL(event.target.action).pathname,values:[...new FormData(event.target)]};},true);
window.addEventListener('load',async()=>{
 try {
  await until(()=>pending);
  check(!contract.slots.includes(28),'menu requires confirmation');
  check(JSON.stringify(contract.controls)==='[26,27,28]','missing board cursor controls');
  check(document.documentElement.scrollWidth<=innerWidth,'horizontal overflow');
  if(PAGE==='/') {
   check(JSON.stringify(contract.slots)==='[5,6,7,8]','wrong main runes');
   check(!contract.back,'root has a nonexistent parent');
   check(document.querySelectorAll('.main-menu svg[data-panel-slot]').length===4,'missing glyphs');
   const button=document.querySelector('button.menu-action');
   check(getComputedStyle(button).color===getComputedStyle(document.querySelector('a.menu-action')).color,'arena title is dark');
   await press(26);await until(()=>contract.focused===6);
   await press(26);await until(()=>contract.focused===7);
   await press(27);await until(()=>contract.focused===6);
   await press(26);await until(()=>contract.focused===7);
   await press(28);
   await until(()=>submission);
   check(submission.path==='/training/open','rune did not open arena immediately');
  } else {
   check(contract.slots.length===7 && !contract.slots.includes(24),'empty party can continue');
   const first=document.querySelector('[data-board-rune="5"] input');
   const second=document.querySelector('[data-board-rune="6"] input');
   const scenarioRunes=[...document.querySelectorAll('#scenario-selection-step [data-board-rune]')]
     .map(card=>Number(card.dataset.boardRune));
   await press(28);
   await until(()=>first.checked && contract.slots.includes(24));
   await press(5);
   await until(()=>!first.checked && !contract.slots.includes(24));
   await until(()=>pending);
   staleNext=true;
   first.click();
   await until(()=>contract.slots.includes(24));
   check(!second.checked,'late board event overrode screen choice');
   for(const slot of [6,7,8,9,10]) await press(slot);
   await until(()=>document.querySelectorAll('input[name="character_ids"]:checked').length===6&&!contract.slots.includes(11));
   check(document.querySelectorAll('input[name="character_ids"]:checked').length===6,'six-player party is blocked');
   await press(24);
   await until(()=>JSON.stringify(contract.slots)===JSON.stringify(scenarioRunes));
   check(contract.back,'scenario has no back control');
   await press(29);
   await until(()=>contract.slots.includes(24));
   check(first.checked,'back lost selected party');
   await press(24);
   await until(()=>JSON.stringify(contract.slots)===JSON.stringify(scenarioRunes));
   await press(scenarioRunes[0]);
   await until(()=>submission);
   check(submission.path==='/new-game/start','scenario selection did not start game');
   check(submission.values.some(([key,value])=>key==='character_ids' && value===first.value),'missing selected hero');
  }
  check(released,'navigation did not release old board input');
  document.getElementById('test-result').textContent='PASS';
 } catch(error) {document.getElementById('test-result').textContent='FAIL: '+error.stack;}
});
'''
    html = html.replace('</head>', '<script>const PAGE=' + json.dumps(page_path) + ';' + harness + '</script></head>')
    html = html.replace('</body>', '<pre id="test-result">PENDING</pre></body>')
    page = tmp_path/'launcher.html'
    page.write_text(html)
    result = subprocess.run([chrome, '--headless', '--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
        '--no-first-run', '--disable-background-networking', '--no-proxy-server', '--virtual-time-budget=6000',
        f'--user-data-dir={tmp_path/"chrome"}', f'--window-size={width},1000', '--dump-dom', page.as_uri()],
        capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr[-1000:]
    assert '<pre id="test-result">PASS</pre>' in result.stdout, result.stdout[-2500:]
