"""All seven choices and navigation stay reachable without any list scrolling."""
from pathlib import Path
import re
import html as html_module
import shutil
import subprocess
import pytest
from dnd_board_game.ui.routes import create_app
from tests.unit.test_launcher_ui import _session


@pytest.mark.parametrize('width,height',[(1280,720),(1131,670),(1024,768),(900,650),(390,844),(320,650),(844,480),(1440,1000),(500,507)])
def test_party_choices_fit_viewport(tmp_path: Path,width: int,height: int) -> None:
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:pytest.skip('Chrome required')
    page=create_app(_session(tmp_path)).test_client().get('/new-game').get_data(as_text=True)
    css=Path('src/dnd_board_game/ui/static/launcher.css').read_text()
    page=re.sub(r'<link rel="stylesheet"[^>]+>',lambda _: '<style>'+css+'</style>',page)
    page=re.sub(r'<script src="[^"]*launcher_board.js[^>]+></script>','',page)
    harness=r'''<script>
window.addEventListener('load',()=>{
 const check=(v,m)=>{if(!v)throw Error(m)};
 const fit=()=>{
  const section=document.getElementById('party-selection-step');
  const box=section.getBoundingClientRect();
  const cards=[...document.querySelectorAll('.roster-card')];
  check(cards.length===7,'seven heroes');
  for(const el of [document.documentElement,document.body,section,document.querySelector('.roster-grid'),...cards]){
   check(el.scrollHeight<=el.clientHeight+1,el.className+' vertical '+el.scrollHeight+'/'+el.clientHeight);
   check(el.scrollWidth<=el.clientWidth+1,el.className+' horizontal');
  }
  for(const card of cards){
   const r=card.getBoundingClientRect();
   check(r.top>=box.top&&r.bottom<=box.bottom+1,'card clipped '+card.dataset.actorId);
   const choice=card.querySelector('.hero-choice').getBoundingClientRect();
   const role=card.querySelector('.hero-role').getBoundingClientRect();
   check(choice.top>=r.top&&role.bottom<=r.bottom+1,'content clipped '+card.dataset.actorId);
   const overview=card.querySelector('.hero-overview').getBoundingClientRect();
   check(overview.bottom<=r.bottom+1,'description clipped '+card.dataset.actorId);
   if(r.width>=222&&r.height>=182){
    check(card.querySelector('.roster-avatar').getBoundingClientRect().width>=64,'portrait too small');
    check(getComputedStyle(card.querySelector('.hero-play-style')).display!=='none','missing introduction');
   }
  }
  const next=document.getElementById('continue-to-scenario').getBoundingClientRect();
  check(next.bottom<=innerHeight&&next.top>=box.bottom-1,'navigation clipped/overlapping');
 };
 try{
  fit();
  const inputs=[...document.querySelectorAll('input[name=character_ids]')];
  check(document.getElementById('continue-to-scenario').disabled,'empty selection');
  inputs.slice(0,6).forEach(i=>i.click());inputs[6].click();
  check(inputs.filter(i=>i.checked).length===6,'party limit');fit();
  document.getElementById('continue-to-scenario').click();
  check(document.getElementById('party-selection-step').hidden,'next');
  document.getElementById('back-to-party').click();fit();
  check(inputs.filter(i=>i.checked).length===6,'selection retained');
  document.getElementById('result').textContent='PASS';parent.postMessage('PASS','*');
 }catch(e){const message='FAIL '+e.message+' viewport '+innerWidth+'x'+innerHeight;document.getElementById('result').textContent=message;parent.postMessage(message,'*');}
});</script><output id="result" style="position:fixed;top:0;right:0;font-size:10px"></output>'''
    page=page.replace('</body>',harness+'</body>')
    # A sized iframe gives exact CSS viewports, including widths below Chrome's window minimum.
    outer='<html><body><output id="result">PENDING</output><script>addEventListener("message",e=>document.getElementById("result").textContent=e.data);</script>'
    outer+=f'<iframe style="width:{width}px;height:{height}px;border:0" srcdoc="{html_module.escape(page,quote=True)}"></iframe></body></html>'
    html=tmp_path/'party.html';html.write_text(outer)
    result=subprocess.run([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run',
        '--disable-background-networking','--force-device-scale-factor=1','--virtual-time-budget=1200',
        f'--user-data-dir={tmp_path/"chrome"}',f'--window-size={width},{height}','--dump-dom',html.as_uri()],
        capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr[-700:]
    report=re.search(r'<output id="result"[^>]*>(.*?)</output>',result.stdout)
    assert report and report.group(1)=='PASS',report.group(1) if report else result.stdout[-1000:]
