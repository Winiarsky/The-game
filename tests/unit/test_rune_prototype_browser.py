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
  for(const hero of window.RUNE_DATA.heroes)for(const card of hero.cards){
   assert(card.rune===window.RUNE_DATA.panel[card.slot].name,`${hero.id}:${card.id}: cost matches button`);
   assert(window.RUNE_DATA.resourceRunes.includes(card.rune),`${hero.id}:${card.id}: cost present in deck`);
  }
  assert(document.querySelectorAll('.board-pad').length===28,'28 buttons, two separate gaps');
  assert(document.querySelectorAll('.board-gap').length===2,'two empty grid squares');
  assert(document.querySelector('.board-pad[data-slot="2"]').textContent!==undefined,'item at slot 2');
  app.startScene('reaction');s.hands.garran=[];app.render();
  assert(app.bindings().get(1).enabled,'opportunity attack available with empty hand');
  assert(!app.bindings().get(app.slot('Węzeł')).enabled,'paid guard unavailable with empty hand');
  app.press(1);app.press(28);
  assert(s.hands.garran.length===0&&!s.reaction,'free opportunity spends only reaction');
  app.startScene('reaction');const before=s.hands.garran.length;
  app.press(app.slot('Węzeł'));app.press(29);
  assert(s.hands.garran.length===before&&s.reaction,'cancel reaction spends nothing');
  s.scene='reaction';s.selection=null;app.render();app.press(app.slot('Węzeł'));app.press(28);
  assert(s.hands.garran.length===before-1&&!s.reaction,'chosen special reaction spends exactly one rune');
  app.press(28);assert(s.hands.garran.length===before-1,'next accept does not duplicate reaction payment');
  app.startScene('combat');
  const star=app.slot('Gwiazda'),key=app.slot('Klucz');
  assert(document.querySelector(`.board-pad[data-slot="${star}"]`).dataset.light==='info','star uses separate information color');
  assert(getComputedStyle(document.querySelector(`.board-pad[data-slot="${star}"]`)).color!==getComputedStyle(document.querySelector(`.board-pad[data-slot="${key}"]`)).color,'information star visibly differs from action rune');
  assert(document.querySelector('.hero-info-hint').textContent.includes('Informacja o bohaterze'),'small star information legend visible');
  assert(app.bindings().get(key).title==='Żelazny bastion','key opens bastion instead of character information');
  assert(!window.RUNE_DATA.resourceRunes.includes('Gwiazda')&&window.RUNE_DATA.resourceRunes.includes('Klucz'),'star reserved for information and key replaces it in resource deck');
  const infoHand=JSON.stringify(s.hands);app.press(star);
  assert(s.scene==='hero'&&document.querySelector('[data-stat="hp"]').textContent==='23/28','star shows current and maximum HP');
  assert(document.body.innerText.includes('Ranny')&&document.querySelector('.decision').textContent.includes('Wyposażenie')&&document.querySelector('.decision').textContent.includes('Cechy'),'hero information includes status stats and equipment');
  app.press(star);assert(s.scene==='combat'&&JSON.stringify(s.hands)===infoHand&&s.special&&s.ordinary,'star toggles read-only hero view');
  app.press(1);app.previewTargetField(9,17);const selectedCard=s.selection;
  app.press(star);app.press(29);
  assert(s.scene==='combat'&&s.phase==='detail'&&s.target===0&&s.selection===selectedCard,'information roundtrip preserves selected action and board target');
  app.press(29);s.previewHp=17;s.reaction=false;s.conditions.garran=[{name:'Zatruty',description:'Utrudnienie testów',duration:'Do końca rundy'}];
  app.press(star);
  assert(document.querySelector('[data-stat="hp"]').textContent==='17/28'&&document.body.innerText.includes('Zatruty')&&document.body.innerText.includes('Do końca rundy'),'information reflects updated HP and named conditions');
  assert(document.querySelector('.hero-state-grid').textContent.includes('Wykorzystana'),'information reflects consumed reaction');
  app.press(29);app.press(3);app.press(28);app.press(star);
  assert(s.detailHero==='mira'&&document.querySelector('.decision h1').textContent==='Mira','star follows active hero rather than always Garran');
  app.press(29);app.startScene('combat');
  assert(document.querySelector('.decision h1').textContent==='Wybierz akcję','combat idle requests board action');
  assert(!document.querySelector('.decision .ability-grid')&&!document.querySelector('.decision button.action'),'idle combat has no action catalogue');
  assert([0,1,2,3,app.slot('Kotwica')].every(i=>app.bindings().get(i).enabled),'board action bindings remain available');
  app.press(0);assert(document.querySelector('[data-preview-kind="movement"]')&&s.movement===6,'movement opens range preview without moving');
  assert(!document.querySelector('.decision .target-cards')&&!document.querySelector('.decision button.action'),'movement preview has no on-screen destinations');
  assert(!app.bindings().has(5)&&!app.bindings().has(6)&&!app.bindings().get(28).enabled,'runes do not select distance; confirmation waits for board');
  assert(!app.previewMovement(7)&&!app.previewMovement(0)&&!app.previewMovement(1.5),'invalid movement input rejected');
  app.previewMovement(2);assert(s.target===2&&s.movement===6,'board selection does not spend movement');
  app.press(29);assert(s.phase==='idle'&&s.movement===6,'cancel movement is free');
  app.press(0);app.previewMovement(2);app.press(28);assert(s.movement===4&&s.phase==='idle','movement applies only after confirmation');
  const hp=s.previewHp;app.press(2);
  assert(app.bindings().get(28).enabled&&!document.querySelector('.decision button[data-slot="28"]').disabled,'single item can be confirmed immediately');
  assert(document.querySelector('.board-pad[data-slot="28"]').dataset.light==='control','item confirmation lights up on board');
  assert(s.ordinary&&s.previewHp===hp,'item preview does not heal or spend action');
  app.press(29);assert(s.ordinary&&s.previewHp===hp,'cancel item is free');
  app.press(2);app.press(28);assert(!s.ordinary&&s.previewHp>hp,'confirmed item applies effect');
  const healed=s.previewHp;app.press(28);assert(s.previewHp===healed&&!s.ordinary,'repeat confirmation cannot use item twice');
  app.startScene('combat');app.press(1);
  assert(document.querySelector('[data-preview-kind="targets"]')&&!app.bindings().get(28).enabled,'weapon preview requires legal target');
  assert(document.querySelectorAll('.legal-targets li').length===1,'melee preview excludes distant enemy');
  assert(!document.querySelector('.legal-targets button,.legal-targets [data-slot],.legal-targets svg'),'target list is informational without buttons or runes');
  assert(!app.bindings().has(19)&&!app.bindings().has(20),'targets do not bind rune controls');
  document.querySelector('.legal-targets li').click();assert(s.target===null,'clicking screen target does not select figure');
  assert(!app.previewTargetField(10,18)&&!app.previewTargetField(0,0)&&!app.bindings().get(28).enabled,'out of range and empty board fields cannot enable attack');
  app.previewTargetField(9,17);assert(s.ordinary&&s.phase==='detail','target selection alone does not attack');
  assert(app.bindings().get(28).enabled&&document.querySelector('.board-pad[data-slot="28"]').dataset.light==='control','legal board target lights confirmation');
  assert(document.querySelector('.legal-targets .selected').textContent.includes('Wybrano na planszy'),'screen acknowledges selected board figure');app.press(29);
  assert(s.ordinary&&s.phase==='idle','target preview cancels without action');
  const auraHand=s.hands.garran.length;app.press(app.slot('Klucz'));
  assert(document.querySelector('[data-preview-kind="aura"]').textContent.includes('2 pól')&&!s.aura,'aura preview displays radius before activation');
  app.press(29);assert(s.hands.garran.length===auraHand&&!s.aura&&s.special&&s.ordinary,'cancel aura preserves resources');
  const gate=s.deck.indexOf('Brama');s.hands.garran.push(s.deck.splice(gate,1)[0]);app.render();
  app.press(app.slot('Klucz'));app.press(app.slot('Brama'));
  assert(document.querySelector('[data-preview-kind="aura"]').textContent.includes('3 pól')&&!s.aura,'aura upgrade previews larger radius');
  app.press(28);assert(s.aura&&!s.special&&!s.ordinary&&s.hands.garran.length===auraHand-1,'aura activates and pays only on confirmation');
  app.press(star);
  assert(document.body.innerText.includes('Aktywna aura: promień 3 pól')&&document.querySelector('[data-stat="ac"]').textContent==='19','hero view shows current aura radius and armor bonus');
  assert(!s.special&&!s.ordinary,'reading aura state does not restore action budgets');
  app.press(29);
  app.startScene('combat');app.press(app.slot('Wieża'));app.press(28);app.press(star);
  assert(document.body.innerText.includes('Pozycja obronna')&&document.querySelector('[data-stat="ac"]').textContent==='20','activated stance appears in effects and current armor');
  app.press(29);app.press(28);app.press(0);app.previewMovement(1);app.press(28);app.press(star);
  assert(document.querySelector('[data-stat="ac"]').textContent==='18','movement removes stance armor bonus');
  app.press(29);
  app.startScene('combat');s.hands.garran.push('Klepsydra');app.render();app.press(app.slot('Klepsydra'));
  assert(document.querySelector('[data-preview-kind="targets"]').textContent.includes('12 pól')&&document.querySelectorAll('.legal-targets li').length===2,'ranged special previews legal targets immediately');
  assert(app.previewTargetField(10,18)&&s.target===1,'ranged action accepts farther legal board field');
  assert(app.previewTargetField(9,17)&&s.target===0&&s.special,'board target can change before confirming');
  app.startScene('combat');assert(!app.previewTargetField(9,17),'stale board target outside preview is ignored');const initial=s.hands.garran.length;
  app.press(app.slot('Kotwica'));app.press(app.slot('Błysk'));app.press(29);
  assert(s.hands.garran.length===initial&&s.special,'cancel ability preview keeps hand and action');
  app.press(app.slot('Kotwica'));app.press(app.slot('Błysk'));app.previewTargetField(9,17);app.press(28);
  assert(s.hands.garran.length===initial-2&&!s.special&&s.ordinary,'boosted shield costs two runes and special only');
  s.roll=20;app.render();app.press(28);app.press(28);
  assert(s.hands.garran.length===initial-2,'roll completion does not charge twice');
  assert(app.bindings().get(1).enabled,'ordinary attack remains after special');
  app.startScene('combat');app.press(1);app.previewTargetField(9,17);app.press(28);s.roll=12;app.render();app.press(28);app.press(28);
  assert(!s.ordinary&&s.special,'ordinary attack preserves special');
  assert(!app.bindings().get(app.slot('Klucz')).enabled,'bastion blocked after spending ordinary action');
  app.startScene('combat');s.hands.garran=['Kotwica','Klucz','Kielich'];app.render();
  app.press(app.slot('Kotwica'));app.press(5);app.previewTargetField(9,17);app.press(28);
  assert(s.scene==='payment'&&s.hands.garran.length===3&&s.special,'wildcard opens explicit choice before any cost');
  assert(!app.bindings().get(28).enabled&&!app.bindings().has(app.slot('Kotwica')),'named base reserved and confirmation waits for wildcard');
  app.press(app.slot('Klucz'));app.press(29);
  assert(s.paymentPrompt.picks.length===0&&s.hands.garran.includes('Klucz'),'undo changes choice without discarding');
  app.press(app.slot('Kielich'));app.press(28);
  assert(s.hands.garran.length===1&&s.hands.garran[0]==='Klucz','player preserves key by paying chosen cup');
  app.startScene('combat');s.hands.garran=['Klucz','Kielich','Wieża'];app.render();
  app.press(app.slot('Kotwica'));app.previewTargetField(9,17);app.press(28);
  assert(s.scene==='payment'&&s.paymentPrompt.wild===2,'missing base asks for two chosen replacement runes');
  app.press(app.slot('Kielich'));app.press(app.slot('Wieża'));app.press(28);
  assert(s.hands.garran.join(',')==='Klucz','two-rune substitution preserves unselected resource');
  app.startScene('draw');const total=()=>s.deck.length+s.market.length+s.discard.length+Object.values(s.hands).reduce((a,b)=>a+b.length,0);
  assert(s.round===1&&s.market.length===s.party.length+2,'opening draw only at first combat round');
  assert(document.querySelector('.scene-art').getAttribute('src').includes('posterunek'),'combat allocation shows battlefield illustration');
  assert(!document.querySelector('.scene').innerText.includes('Ness')&&!document.querySelector('.scene').innerText.includes('Gildii'),'combat allocation has no Nessa interaction text');
  const whole=total();
  s.deck.push(...s.market);s.market=[];
  for(const rune of ['Kotwica','Kotwica','Błysk','Brama','Wieża','Kielich'])s.market.push(s.deck.splice(s.deck.indexOf(rune),1)[0]);
  app.render();
  const light=rune=>document.querySelector(`.board-pad[data-slot="${app.slot(rune)}"]`).dataset.light;
  assert(s.recipient===0&&s.party[0]==='garran','allocation starts with first hero');
  app.press(26);app.press(27);assert(s.recipient===0,'plus minus no longer change recipient');
  assert(!app.bindings().get(29).enabled,'undo disabled before first pick');
  app.press(app.slot('Kotwica'));
  assert(s.hands.garran.length===1&&s.market.filter(r=>r==='Kotwica').length===1&&light('Kotwica')==='available','click assigns one rune and keeps duplicate lit');
  app.press(app.slot('Kotwica'));
  assert(s.hands.garran.length===2&&!s.market.includes('Kotwica')&&light('Kotwica')==='off','last copy extinguishes rune');
  app.press(app.slot('Kotwica'));assert(s.hands.garran.length===2,'empty rune cannot be assigned again');
  app.press(app.slot('Błysk'));app.press(29);
  assert(s.market.includes('Błysk')&&s.hands.garran.length===2,'undo restores last choice');
  app.press(29);assert(s.hands.garran.length===1&&light('Kotwica')==='available','second undo restores previous duplicate and light');
  assert(total()===whole,'allocation and undo preserve rune inventory');
  app.press(28);
  assert(s.recipient===1&&s.hands.garran.length===1&&!app.bindings().get(29).enabled,'accept locks first hero and advances sequentially');
  app.press(29);assert(s.recipient===1&&s.hands.garran.length===1,'undo cannot alter confirmed previous hero');
  while(s.market.length)app.press(app.slot(s.market[0]));
  assert(s.scene==='allocation'&&s.recipient===1,'empty pool still allows undo before confirmation');
  app.press(29);assert(s.market.length===1,'empty pool undo restores one rune');
  app.press(app.slot(s.market[0]));
  while(s.scene==='allocation')app.press(28);
  assert(s.scene==='combat'&&total()===whole,'last hero confirms allocation and enters combat');
  app.startScene('draw');const deferredMarket=JSON.stringify(s.market);
  for(let i=0;i<s.party.length;i++)app.press(28);
  assert(s.scene==='allocation'&&s.recipient===0&&JSON.stringify(s.market)===deferredMarket,'leftover pool gets another sequential pass without new draw');
  while(s.market.length)app.press(app.slot(s.market[0]));
  while(s.scene==='allocation')app.press(28);
  const originalParty=[...s.party];s.party=['garran','mira','lorian','nimra','brakka','dagna'];app.startScene('draw');
  for(let i=0;i<7;i++)app.press(app.slot(s.market[0]));
  const finalRune=s.market[0];app.press(app.slot(finalRune));
  assert(s.hands.garran.length===7&&s.market.length===1&&light(finalRune)==='off','full hand blocks eighth rune');
  app.press(29);assert(s.hands.garran.length===6&&s.market.length===2&&light(finalRune)==='available','undo reopens full hand');
  app.press(28);app.press(app.slot(s.market[0]));app.press(app.slot(s.market[0]));
  assert(s.hands.mira.length===2,'next hero can take remaining pool');
  while(s.scene==='allocation')app.press(28);
  s.party=originalParty;app.startScene('draw');
  while(s.market.length)app.press(app.slot(s.market[0]));
  while(s.scene==='allocation')app.press(28);
  const openingHands=JSON.stringify(s.hands),openingDeck=[...s.deck];
  for(let round=2;round<=3;round++){
   for(let actor=0;actor<s.party.length;actor++){app.press(3);app.press(28);}
   assert(s.scene==='combat'&&s.round===round&&s.actor===0,'later combat round skips allocation:'+round);
   assert(JSON.stringify(s.hands)===openingHands&&JSON.stringify(s.deck)===JSON.stringify(openingDeck),'later round preserves rune hands and deck:'+round);
  }
  app.startScene('combat');s.aura=true;
  for(let actor=0;actor<s.party.length;actor++){app.press(3);app.press(28);}
  assert(s.round===2&&s.scene==='aura','aura upkeep still occurs without another draw');
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
  assert(s.scene==='allocation'&&s.round===1,'cart leads to opening combat draw');
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
  for(const scene of ['start','combat','reaction','draw','talk','cart']){
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


def test_board_rune_workflows_and_reaction_choice(tmp_path: Path) -> None:
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
