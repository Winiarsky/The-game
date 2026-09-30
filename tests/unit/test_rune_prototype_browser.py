"""Exercise paper-controller clicks in the standalone mockup, never live hardware."""
from html import unescape
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]

CHECK = r'''
addEventListener('load',()=>{
 const failures=[],checks=[];
 const assert=(ok,label)=>{checks.push(label);if(!ok)failures.push(label);};
 try{
  const app=window.RunePrototype,s=app.state;
  assert(Boolean(app),'app loaded');
  // Combat is covered by test_resonance_mock.py; keep the original social regression scenarios.
  const startTest=(die,rep=20,scene='talk')=>{s.reputation=rep;app.startScene(scene);app.press(5);s.roll=die;app.render();app.press(28);};
  s.reputation=20;app.startScene('talk');
  assert(s.scene==='talk'&&s.phase==='idle','social confrontation skips rune draw');
  app.press(5);assert(s.phase==='roll','approach immediately opens roll');
  s.roll=10;app.render();app.press(28);
  assert(s.phase==='reputation'&&s.track===0&&s.reputation===20,'roll opens uncommitted reputation summary');
  assert([5,6,7].every(i=>app.bindings().get(i).enabled),'three affordable reputation choices are lit');
  assert(document.querySelectorAll('.reputation-options button').length===3,'exactly three reputation options');
  for(const element of document.querySelectorAll('.reputation-options button,.decision>.buttons')){
   for(let scroll=0;scroll<4&&element.getBoundingClientRect().bottom>document.getElementById('rune-board').getBoundingClientRect().top;scroll++)app.press(26);
   assert(element.getBoundingClientRect().bottom<=document.getElementById('rune-board').getBoundingClientRect().top&&element.getBoundingClientRect().top>=0,'reputation choice/confirmation accessible with board scrolling');
  }
  for(let scroll=0;scroll<4;scroll++)app.press(27);
  const natural=s.lockedRoll;
  app.press(5);assert(s.reputationOption==='small'&&s.reputation===20,'plus one costs one only on confirmation');
  app.press(6);assert(s.reputationOption==='large'&&s.reputation===20,'plus five replaces plus one without stacking');
  assert(s.lockedRoll===natural,'choosing reputation does not change original die');
  app.press(26);app.press(27);
  assert(s.reputationOption==='large'&&s.reputation===20,'plus and minus do not buy reputation bonuses');
  assert(document.body.innerText.includes('zabraknie reputacji do zamiany wozu'),'spending warns about losing cart threshold');
  app.press(29);assert(s.reputationOption===null&&s.phase==='reputation','decline clears proposed spending and preserves roll');
  app.press(6);app.press(6);assert(s.reputationOption===null,'same rune toggles bonus off');
  app.press(6);app.press(28);
  assert(s.reputation===17&&s.track===1&&s.phase==='talk-result','plus five costs three and advances track');
  app.press(28);assert(s.reputation===17&&s.talkActor===1,'next accept cannot double-spend');
  app.startScene('cart');assert(s.reputation===17&&!app.bindings().get(11).enabled,'cart exchange locked below twenty across scenes');
  assert(!document.body.innerText.includes('Wsparcie runiczne'),'no rune support in confrontation');
  s.reputation=20;app.render();app.press(11);app.press(29);
  assert(s.reputation===20&&s.phase==='idle'&&!s.talkDone,'cart exchange can be cancelled free');
  app.press(11);app.press(28);
  assert(s.reputation===17&&s.talkDone,'cart exchange spends three once and ends confrontation');
  app.press(28);assert(s.reputation===17,'cart result transition preserves paid reputation');
  assert(s.scene==='combat'&&app.combat.state.round===1,'cart leads directly to charge combat without rune draw');
  startTest(10,1);
  assert(app.bindings().get(5).enabled&&!app.bindings().get(6).enabled&&!app.bindings().get(7).enabled,'unaffordable reputation options are disabled');
  app.press(5);app.press(28);assert(s.reputation===0,'small bonus spends one shared point');
  startTest(10,0);
  assert([5,6,7].every(i=>!app.bindings().get(i).enabled),'zero reputation still permits ordinary result');
  app.press(28);assert(s.reputation===0&&s.phase==='talk-result','test can finish without spending');
  startTest(1);app.press(7);app.press(29);
  assert(s.reputation===20&&s.reputationOption===null,'unconfirmed extra die can be cancelled free');
  app.press(7);app.press(28);
  assert(s.phase==='reputation-reroll'&&s.reputation===15&&s.lockedRoll===1,'extra die costs five before its result is known');
  app.press(29);assert(s.phase==='reputation-reroll'&&s.reputation===15,'paid reroll cannot be refunded');
  s.roll=20;app.render();app.press(28);
  assert(s.extraRoll===20&&s.reputation===15&&s.phase==='reputation','extra die returns to summary without another charge');
  assert(!app.bindings().has(5)&&!app.bindings().has(6)&&!app.bindings().has(7),'paid extra die cannot combine with numeric bonus');
  app.press(29);assert(s.extraRoll===20&&s.reputation===15,'decline after reroll preserves paid result');
  app.press(28);assert(s.track===2&&s.reputation===15,'higher extra natural twenty replaces critical failure');
  startTest(12);app.press(7);app.press(28);s.roll=2;app.render();app.press(28);
  assert(document.body.innerText.includes('Zachowujesz 12'),'lower extra roll retains original die');
  app.press(28);assert(s.reputation===15,'unsuccessful extra die still costs five');
  startTest(1);assert(!app.bindings().get(5).enabled&&!app.bindings().get(6).enabled&&app.bindings().get(7).enabled,'critical one permits only extra die');
  app.press(28);assert(s.track===-1&&s.reputation===20,'unmodified critical failure preserved');
  startTest(20);assert([5,6,7].every(i=>!app.bindings().get(i).enabled),'natural twenty needs no paid option');
  app.press(28);assert(s.track===2&&s.reputation===20,'critical success preserved');
  s.reputation=20;app.startScene('talk');
  for(let i=0;i<s.party.length;i++){
   app.press(5);s.roll=10;app.render();app.press(28);app.press(28);
   if(!s.talkDone)app.press(28);
  }
  assert(s.talkDone&&s.talkActor===s.party.length-1,'NPC ends after one party round');
  assert(!document.body.innerText.includes('Rzuć na wpływ'),'no second influence roll');
  app.startScene('cart');
  for(let i=0;i<2;i++){app.press(5);s.roll=1;app.render();app.press(28);
   assert(!app.bindings().has(5)&&!app.bindings().has(6)&&!app.bindings().has(7),'physical cart test has no reputation purchase');
   app.press(28);if(!s.talkDone)app.press(28);}
  assert(s.talkDone&&s.track===-1&&s.talkActor===1,'second critical failure ends below minus one');
  app.press(29);app.press(13);const rewardBefore=s.reputation;app.press(5);app.press(5);
  assert(s.reputation===rewardBefore+5&&s.missionRewardClaimed,'mission reward claimed once');
  app.startScene('talk');assert(s.reputation===rewardBefore+5,'scene start does not reset campaign reputation');
  app.startScene('start');app.press(5);assert(s.scene==='setup','start through board opens party setup');
  assert(s.reputation===20&&!s.missionRewardClaimed,'new expedition resets reputation and reward');
  app.press(28);for(let i=0;i<s.party.length;i++)app.press(28);
  assert(s.scene==='story','board confirms equipment for every hero');
  for(const scene of ['start','talk','cart']){
   app.startScene(scene);
   assert(document.documentElement.scrollWidth<=innerWidth+1,'no horizontal overflow:'+scene);
   const board=document.getElementById('rune-board').getBoundingClientRect();
   assert(board.bottom<=innerHeight+1&&board.top>=0,'rune panel visible:'+scene);
   assert(document.querySelectorAll('button:not([data-slot]):not([data-route])').length===0,'every button has a board route:'+scene);
  }
 }catch(e){failures.push(e.stack||String(e));}
 const out=document.createElement('pre');out.id='browser-check';out.textContent=JSON.stringify({failures,checks});document.body.append(out);
});
'''


def test_existing_reputation_and_expedition_workflows(tmp_path: Path) -> None:
    chrome=shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        pytest.skip('Local Chrome required')
    source=ROOT/'docs/ui/prototype.html'
    html=source.read_text().replace('<head>','<head><base href="'+source.parent.as_uri()+'/">')
    html=html.replace('</body>','<script>'+CHECK+'</script></body>')
    check=tmp_path/'check.html';check.write_text(html)
    run=subprocess.run([chrome,'--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
        '--disable-background-networking','--allow-file-access-from-files','--window-size=1131,720','--virtual-time-budget=4000',
        f'--user-data-dir={tmp_path/"chrome"}','--dump-dom',check.as_uri()],
        capture_output=True,text=True,timeout=40)
    assert run.returncode==0,run.stderr[-1500:]
    found=re.search(r'<pre id="browser-check">(.*?)</pre>',run.stdout,re.S)
    assert found,'Browser did not finish the interaction check: '+run.stderr[-1000:]
    result=json.loads(unescape(found.group(1)))
    assert not result['failures'],result['failures']
    assert len(result['checks'])>=30
