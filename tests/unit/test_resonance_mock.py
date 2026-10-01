"""Standalone charge/resonance mock: deterministic flows and browser presentation."""
from html import unescape
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


def browser_check(tmp_path: Path, script: str) -> dict:
    chrome = shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:
        pytest.skip("Local Chrome required")
    source = ROOT / "docs/ui/prototype.html"
    html = source.read_text().replace("<head>", f'<head><base href="{source.parent.as_uri()}/">')
    check_script = """
addEventListener('load',()=>{
 const failures=[],checks=[];
 const assert=(ok,label)=>{checks.push(label);if(!ok)throw Error(label);};
 try{
 SCRIPT
 }catch(e){failures.push(e.stack||String(e));}
 const out=document.createElement('pre');out.id='browser-check';
 out.textContent=JSON.stringify({failures,checks});document.body.append(out);
});
""".replace("SCRIPT", script)
    check = tmp_path / "check.html"
    check.write_text(html.replace("</body>", f"<script>{check_script}</script></body>"))
    result = subprocess.run(
        [chrome, "--headless", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
         "--disable-background-networking", "--allow-file-access-from-files",
         "--window-size=1131,720", "--virtual-time-budget=1500",
         f"--user-data-dir={tmp_path / 'chrome'}", "--dump-dom", check.as_uri()],
        capture_output=True, text=True, timeout=40,
    )
    assert result.returncode == 0, result.stderr[-1500:]
    found = re.search(r'<pre id="browser-check">(.*?)</pre>', result.stdout, re.S)
    assert found, result.stderr[-1500:]
    outcome = json.loads(unescape(found.group(1)))
    assert not outcome["failures"], outcome["failures"]
    return outcome


HELPERS = r"""
 const D=window.RESONANCE_DATA,E=window.ResonanceModel.Encounter;
 const create=(hero='garran')=>new E(D,[hero,...['garran','mira','lorian','nimra'].filter(id=>id!==hero)].slice(0,4));
 const drain=(m,value=1)=>{
   let count=0;
   while(m.s.task){
     assert(++count<100,'flow terminates');
     const t=m.s.task;
     if(t.type==='roll'){
       if(m.isEnemyRoll())assert(m.confirmEnemyRoll(sides=>Math.max(1,Math.min(value,sides))),'automatic enemy roll accepted');
       else {
         const die=m.rollDice()[t.diceResults?.length??0];
         assert(die?m.submitDie(Math.max(1,Math.min(value,die.sides))):m.submit([]),'roll accepted');
       }
     }
     else if(t.type==='enemy-result')m.acknowledgeEnemyResult();
     else if(t.type==='recover')m.recover(false);
     else if(t.type==='hymn')m.decideHymn(false);
     else if(t.type==='opportunity')m.opportunity(false);
     else if(t.type==='relocate'){const p=m.relocationFields(t).find(p=>window.ResonanceModel.same(p,m.actor(t.target).pos))??m.relocationFields(t)[0];m.select(p);m.confirmRelocation();}
     else throw Error('Unhandled task '+t.type);
   }
 };
 const play=(m,id,mode='base',target=null)=>{
   assert(m.choose(id),'choose '+id);m.mode(mode);if(target)assert(m.selectTarget(target),'target '+id);
   assert(m.commit(),'commit '+id);
 };
"""


def test_generated_mock_data_matches_current_cards() -> None:
    spec = importlib.util.spec_from_file_location("build_resonance_mock", ROOT / "scripts/build_resonance_mock.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.OUTPUT.read_text() == module.render_data()
    payload = module.build_payload()
    assert sum(len(h["cards"]) for h in payload["heroes"].values()) == 29
    assert payload["rules"]["regeneration_die"] == 4
    assert payload["heroes"]["brakka"]["weapon"]["sides"] == 12
    assert payload["heroes"]["erynd"]["abilities"]["dexterity"] == 4


def test_resonance_lifecycle_and_resource_pools(tmp_path: Path) -> None:
    browser_check(tmp_path, HELPERS + r"""
 const m=create(),a=m.active,b=m.actor('mira');
 const hp=a.hp;a.hp-=8;
 m.addRune(a,'Wieża');assert(m.ac(a)===a.ac+1&&!m.member(b),'only first participant joins');
 a.continued=true;m.endTurn();assert(m.member(b)&&m.ac(b)===b.ac+1,'next turn joins');
 m.addRune(b,'Wieża');assert(m.ac(a)===a.ac+2,'growth reaches existing participant');
 m.addRune(b,'Fala');m.addRune(b,'Fala');assert(m.counts()['Wieża']===4,'waves copy a single previous effective rune');
 m.addRune(b,'Kielich');m.addRune(b,'Klepsydra');
 m.damage(b,[{value:3,damage_type:'piercing'}],a);
 assert(b.shield===0&&b.cup===1&&b.hp===b.maxHp,'prevention before temporary HP before HP');
 m.addRune(b,'Kielich');assert(b.cup===3,'growth does not refill old missing points');
 m.addRune(b,'Klepsydra');m.damage(b,[{value:1,damage_type:'psychic'}],a);
 assert(b.shield===2&&b.cup===2,'psychic bypasses prevention only');
 m.addRune(b,'Węzeł');assert(m.movement(m.actor('enemy1'))===5,'global enemy slow without a hit');
 m.endChain('test');assert(a.hp===hp-8&&b.cup===0&&b.shield===0&&m.ac(a)===a.ac,'global cleanup preserves actual HP');
 m.addRune(b,'Fala');assert(!Object.keys(m.counts()).length,'first wave does not invent a predecessor');m.endChain('test');
 const f=create();f.active.hp-=10;f.addRune(f.active,'Błysk');f.advance();
 assert(f.s.task.parts[0].count===1,'new flash only one die');f.submit([3]);assert(f.active.hp===f.active.maxHp-7,'flash heals');
 f.addRune(f.active,'Błysk');f.advance();f.submit([2]);assert(f.active.hp===f.active.maxHp-5,'second flash does not reroll previous');
 const snapshot=f.snapshot();f.restore(snapshot);assert(f.snapshot()===snapshot,'snapshot restoration is effect-free');
 f.active.charges=4;f.active.hymn={source:'lorian'};play(f,'focus');assert(!f.s.chain&&!f.active.special,'focus ends chain before roll');
 f.submit([20]);drain(f);assert(f.active.charges===20,'focus clamps at twenty');
 assert(f.active.hymn,'resource d20 is not a check and cannot consume Hymn');
 const p=create('lorian');p.addRune(p.active,'Wieża');p.active.charges=20;
 play(p,'inspiration','base','garran');drain(p);
 assert(!p.s.chain&&p.active.charges===17&&p.actor('garran').hymn,'basic power then Lorian refund then chain closure');
 assert(!p.commit()&&p.active.charges===17,'duplicate commit has no effect');
 const stairs=create();stairs.addRune(stairs.active,'Schody');const old=stairs.movement();
 play(stairs,'move');
 """.replace("play(stairs,'move');", r"""
 assert(stairs.choose('move')&&stairs.select({x:3,y:4})&&stairs.commit(),'ordinary movement preview and commit');drain(stairs);
 assert(stairs.active.tempMove===1&&stairs.active.baseSpent===0,'temporary movement spent first');
 stairs.endChain('test');assert(stairs.movement()===old-2,'unused stairs removed without reverting position');
 """))


def test_updated_hero_powers_and_pending_decisions(tmp_path: Path) -> None:
    browser_check(tmp_path, HELPERS + r"""
 const g=create();g.actor('mira').pos={x:2,y:3};assert(g.shielded(g.actor('mira')),'living shield derived from adjacency');
 g.actor('mira').pos={x:0,y:0};assert(!g.shielded(g.actor('mira')),'living shield removed after move');
 assert(g.choose('bastion_charge')&&g.selectTarget('enemy1'),'charge target selected');
 const destination=g.s.preview.destination;assert(destination.x===3&&destination.y===3,'deterministic nearest legal adjacent tile');
 const before=g.snapshot();assert(g.active.charges===20&&!g.active.moved,'preview spends nothing');g.cancel();assert(g.active.charges===20,'cancel free');
 assert(g.choose('bastion_charge')&&g.selectTarget('enemy1')&&g.commit(),'charge commit');
 assert(g.movement()===0&&g.active.ordinary&&!g.active.special,'charge spends all movement and special only');
 assert(g.s.task.dc===15,'charge DC is base + strength + steps');drain(g);
 assert(g.status(g.actor('enemy1'),'prone'),'failed save applies prone');
 const b=create('brakka');b.actor('enemy1').pos={x:3,y:4};
 play(b,'rage');drain(b,3);assert(b.status(b.active,'rage').remaining===7,'rage strength + constitution turns');b.acknowledge();
 play(b,'attack','base','enemy1');b.submit([20]);
 assert(b.s.task.parts.some(p=>p.sides===12&&p.count===3),'Brakka crit has two extra weapon dice');
 assert(b.s.task.parts.some(p=>p.sides===6),'rage adds melee die');drain(b,3);
 const hp=b.active.hp;b.damage(b.active,[{value:8,damage_type:'slashing'},{value:3,damage_type:'fire'}],b.actor('enemy1'));
 assert(b.active.hp===hp-7,'rage halves physical only');
 const mira=create('mira');mira.actor('enemy1').pos={x:4,y:4};mira.actor('enemy2').pos={x:6,y:4};
 play(mira,'hide');mira.submit([9]);drain(mira);assert(mira.active.hidden.includes('enemy1')&&!mira.active.hidden.includes('enemy3'),'hide per observer without cover');
 mira.acknowledge();mira.active.special=true;
 assert(mira.choose('guard_vault')&&mira.selectTarget('enemy2')&&mira.select({x:7,y:4}),'Parkour destination may be five tiles away');
 assert(mira.s.preview.path.cells.some(p=>p.x===5),'Parkour crosses obstacle column');
 const snap=mira.snapshot();mira.restore(snap);assert(!mira.active.moved&&mira.active.charges===16,'preview save does not commit movement');
 assert(mira.commit(),'Parkour commits');drain(mira);assert(mira.active.pos.x===7&&mira.active.hidden.length>0,'Parkour moves and preserves hiding');
 const n=create('nimra');assert(n.choose('flame_fan')&&n.select({x:4,y:4}),'fire center selected');
 assert(!n.ready(),'explicit weave decision required');n.exclude('enemy1');assert(n.ready(),'chosen tile completes weave');
 assert(n.commit(),'fire commits');drain(n);assert(n.actor('enemy1').hp===45,'excluded target unaffected');
 const hymn=create();hymn.actor('enemy1').pos={x:3,y:4};hymn.active.hymn={source:'lorian'};
 play(hymn,'attack','base','enemy1');hymn.submit([8]);assert(hymn.s.task.type==='hymn'&&hymn.actor('enemy1').hp===45,'failed roll pauses before consequences');
 const save=hymn.snapshot();hymn.restore(save);hymn.decideHymn(true);hymn.submit([3]);
 assert(!hymn.active.hymn&&hymn.s.task.outcome==='damage','hymn can turn miss into hit without another k20');drain(hymn);
 assert(hymn.actor('lorian').regenReason===null,'recovery handled after action');
 """)


def test_combat_ui_and_social_isolation(tmp_path: Path) -> None:
    browser_check(tmp_path, r"""
 const app=window.RunePrototype;app.startScene('combat');const m=app.combat.model;
 assert(m&&document.querySelector('.resonance-chain'),'charge combat mounted');
 assert(!document.querySelector('.rune-strip'),'no old rune hands in combat');
 assert(document.querySelectorAll('.board-pad').length===29,'physical panel preserved');
 assert(app.bindings().get(app.slot('Schody')).title.includes('Szarża bastionu'),'current card binding');
 assert(!document.querySelector('.decision .ability-grid'),'idle view is not an action catalogue');
 app.press(app.slot('Schody'));assert(m.s.phase==='preview','rune opens power');
 app.combat.selectField(4,4);assert(document.querySelector('.destination-preview'),'target previews destination');
 const snapshot=m.snapshot();app.press(app.slot('Gwiazda'));
 assert(document.querySelector('.board-pad[data-slot="25"]').dataset.light==='info','information star remains blue while open');
 app.press(29);assert(m.snapshot()===snapshot,'information roundtrip read only');
 app.press(29);assert(m.active.charges===20,'cancel preserves charges');
 app.combat.openLab();assert(document.querySelectorAll('[data-field]').length===120,'clickable simulated board available');
 app.press(app.slot('Schody'));document.querySelector('[data-field="4,4"]').click();app.press(8);
 assert(m.s.preview.mode==='enhanced'&&m.active.charges===20,'mode is still a preview');app.press(28);
 assert(m.active.charges===12&&m.s.chain.entries[0].rune==='Schody','commit pays once and appends rune');
 assert(document.querySelector('.enemy-roll-notice')&&!document.querySelector('.physical-dice'),'enemy save uses automatic roll UI');
 document.querySelector('.decision [data-slot="28"]').click();
 assert(m.s.task.type==='enemy-result'&&m.active.charges===12,'one click resolves enemy save without duplicate charge');
 app.press(28);assert(m.s.phase==='result','acknowledging enemy save finishes charge');
 assert(document.documentElement.scrollWidth<=innerWidth+1,'no horizontal overflow');
 const pane=document.querySelector('.decision'),board=document.getElementById('rune-board');
 assert(pane.getBoundingClientRect().bottom<=board.getBoundingClientRect().top,'decision is not hidden behind fixed controller');
 const state=m.snapshot();app.startScene('talk');
 assert(!document.querySelector('.resonance-chain')&&!document.body.classList.contains('resonance-combat'),'combat UI absent from conversation');
 app.state.reputation=20;app.press(5);app.state.roll=10;app.render();app.press(28);
 assert(app.state.phase==='reputation'&&document.querySelectorAll('.reputation-options button').length===3,'existing reputation decisions unchanged');
 app.press(6);app.press(28);assert(app.state.reputation===17,'existing reputation cost unchanged');
 assert(m.snapshot()===state,'conversation does not mutate combat mock');
 """)


def test_chain_summary_shows_combined_bonuses_and_wave_copies(tmp_path: Path) -> None:
    browser_check(tmp_path, r"""
 const app=window.RunePrototype;app.startScene('combat');const m=app.combat.model;
 const summary=()=>document.querySelector('.chain-bonus-summary');
 const bonus=name=>document.querySelector(`[data-chain-bonus="${name}"] dd`)?.textContent;
 assert(!summary(),'inactive resonance has no bonus summary');
 m.addRune(m.active,'Schody');m.addRune(m.active,'Błysk');app.render();
 assert(summary()&&summary().textContent.includes('Podsumowanie bonusów'),'visible summary inside resonance section');
 assert(bonus('Schody').includes('+2 pkt ruchu')&&bonus('Błysk').includes('1k4 PW na początku tury'),'screenshot example explains movement and healing');
 assert(document.querySelectorAll('[data-chain-bonus]').length===2,'only present bonuses shown');
 m.addRune(m.active,'Schody');m.addRune(m.active,'Fala');m.addRune(m.active,'Fala');app.render();
 assert(bonus('Schody').includes('+8 pkt ruchu'),'duplicate stairs and chained waves summed');
 assert(!bonus('Fala')&&summary().textContent.includes('Kopie z Fali są już wliczone'),'wave counted in copied bonus, not as another effect');
 for(const rune of ['Wieża','Grot','Hak','Oko','Kielich','Węzeł','Klepsydra']){
   m.addRune(m.active,rune);m.addRune(m.active,rune);
 }
 m.damage(m.active,[{value:5,damage_type:'piercing'}],m.actor('enemy1'));
 const before=m.snapshot();app.render();
 assert(m.snapshot()===before,'rendering summary changes no resources, dice, queue or membership');
 for(const [rune,text] of Object.entries({'Wieża':'+2 KP','Grot':'+2k4 obrażeń','Hak':'do 2 pól','Oko':'+2 do własnych rzutów k20','Kielich':'4 tymczasowych PW','Węzeł':'−2 pkt ruchu','Klepsydra':'4 pkt'})){
   assert(bonus(rune)?.includes(text),'numeric combined bonus '+rune);
 }
 assert(document.querySelectorAll('[data-chain-bonus]').length===9,'one summary row per effective rune');
 assert(bonus('Kielich').includes('Limit puli')&&bonus('Klepsydra').includes('Limit osłony'),'summary distinguishes pool limits from remaining amounts');
 assert(m.active.cup===3&&m.active.shield===0,'showing full pool limit does not refill consumed shields');
 assert(bonus('Klepsydra').includes('psychicznymi')&&bonus('Oko').includes('nie do ST'),'important exceptions remain visible');
 assert(document.querySelector('.resonance-chain').textContent.includes('Pozostali dołączą na początku swojej tury'),'membership scope still explained');
 assert(document.documentElement.scrollWidth<=innerWidth+1,'summary does not create horizontal overflow');
 m.restore(before);app.render();assert(bonus('Schody').includes('+8 pkt ruchu'),'summary survives save restoration');
 m.endChain('test');app.render();assert(!summary()&&!document.querySelector('[data-chain-bonus]'),'expired bonuses disappear');
 m.addRune(m.active,'Fala');app.render();
 assert(summary().textContent.includes('Brak bonusów')&&!document.querySelector('[data-chain-bonus]'),'leading wave explicitly grants no bonus');
 """)


def test_weave_parkour_and_hymn_ui_decisions(tmp_path: Path) -> None:
    browser_check(tmp_path, r"""
 const app=window.RunePrototype;app.startScene('combat');
 app.combat.start(['nimra','garran','mira','lorian']);app.render();app.combat.openLab();
 let m=app.combat.model;app.press(app.slot('Kielich'));
 assert(app.combat.selectField(3,4)&&document.querySelector('.weave-prompt'),'area leads to explicit weave prompt');
 assert(!app.bindings().get(28).enabled&&m.active.charges===20,'cannot pay before exclusion decision');
 app.combat.selectField(2,4);assert(m.s.preview.exclude==='nimra','figure tile selects excluded creature');
 document.querySelector('[data-combat="area-reset"]').click();
 assert(!m.s.preview.center&&m.s.preview.exclude===undefined,'changing area clears previous exception');
 app.combat.selectField(3,4);app.press(5);assert(m.s.preview.exclude===null,'none is an explicit choice');
 app.press(8);app.press(28);assert(m.active.charges===12&&document.querySelector('.physical-dice'),'enhanced area starts resolution');
 app.combat.start(['mira','garran','lorian','nimra']);app.render();m=app.combat.model;
 app.press(app.slot('Schody'));app.combat.selectField(4,4);
 assert(m.s.preview.targets[0]==='enemy1'&&!app.bindings().get(28).enabled,'Parkour first chooses enemy, not destination');
 app.combat.selectField(4,3);assert(m.s.preview.destination.x===4&&app.bindings().get(28).enabled,'second tile enables preview confirmation');
 app.press(29);assert(!m.active.moved&&m.active.charges===20,'cancelling Parkour is free');
 app.combat.start(['garran','lorian','mira']);app.render();m=app.combat.model;
 m.active.hymn={source:'lorian'};m.actor('enemy1').pos={x:3,y:4};app.render();
 app.press(1);app.combat.selectField(3,4);app.press(28);
 const input=document.querySelector('[data-die]');input.value='8';input.dispatchEvent(new Event('input',{bubbles:true}));app.press(28);
 assert(document.querySelector('.weave-prompt').textContent.includes('Czy chcesz dodać 1k6'),'failed attack opens hymn decision');
 app.press(8);assert(m.active.hymn&&m.s.phase==='result','UI decline preserves hymn');
 for(const id of Object.keys(window.RESONANCE_DATA.heroes)){
   app.combat.start([id,...['garran','mira','nimra'].filter(x=>x!==id)]);app.render();
   for(const card of window.RESONANCE_DATA.heroes[id].cards)assert(app.bindings().get(card.slot).title.includes(card.name),'binding uses card name '+id+':'+card.id);
 }
 """)


def test_all_current_powers_resolve_and_pay_once(tmp_path: Path) -> None:
    browser_check(tmp_path, HELPERS + r"""
 for(const [heroId,hero] of Object.entries(D.heroes))for(const card of hero.cards){
   const m=create(heroId),a=m.active;
   for(const b of Object.values(m.s.actors)){b.maxHp=500;b.hp=350;}
   m.actor('enemy1').pos={x:3,y:4};
   m.actor('enemy2').pos={x:4,y:3};m.actor('enemy3').pos={x:4,y:6};
   if(card.id==='shadow_attack')a.hidden=['enemy1'];
   assert(m.choose(card.id),'select '+heroId+':'+card.id);m.mode('enhanced');
   if(card.id==='flame_fan')m.select({x:3,y:4});
   if(['flame_fan','force_wave'].includes(card.id))m.exclude(null);
   else if(['move','misty_step','skirmish_shot'].includes(card.id)){
     assert(m.select({x:2,y:5}),'movement destination '+card.id);
     if(card.id==='skirmish_shot')m.selectTarget('enemy1');
   }else if(card.id==='guard_vault'){
     m.selectTarget('enemy1');assert(m.select({x:3,y:3}),'Parkour free destination');
   }else if(['double_shot','force_darts'].includes(card.id)){
     for(let i=0;i<(card.id==='double_shot'?2:3);i++)m.selectTarget('enemy1');
   }else if(!m.ready()){
     const target=m.legalTargets()[0];assert(target,'legal target '+card.id);m.selectTarget(target.id);
   }
   const price=m.price(card,'enhanced',m.s.preview.targets);
   assert(m.commit(),'commit '+heroId+':'+card.id);
   assert(a.charges===20-price&&!a.special,'exact cost and special '+card.id);
   assert(m.s.chain?.entries.length===1&&m.s.chain.entries[0].rune===card.rune,'rune precedes resolution '+card.id);
   assert(!m.commit()&&a.charges===20-price,'duplicate commit rejected '+card.id);
   const pending=m.snapshot();m.restore(pending);assert(m.snapshot()===pending,'pending snapshot stable '+card.id);
   drain(m,12);assert(m.s.phase==='result','power reaches result '+heroId+':'+card.id);
   assert(m.active.ordinary===!card.budget.includes('A'),'attack budget '+card.id);
   if(card.id==='bastion_charge')assert(m.movement()===0,'all movement consumed by charge');
   assert(m.s.chain?.entries.length===1,'enhanced power continues chain '+card.id);
 }
 """)


def test_dice_are_confirmed_individually_and_partial_rolls_survive_reload(tmp_path: Path) -> None:
    browser_check(tmp_path, HELPERS + r"""
 const app=window.RunePrototype;app.startScene('combat');
 app.combat.start(['mira','garran','lorian']);const m=app.combat.model;
 m.actor('enemy1').pos={x:3,y:4};m.active.hidden=['enemy1'];app.render();
 app.press(1);app.combat.selectField(3,4);app.press(28);
 const input=()=>document.querySelector('.physical-dice input');
 const roll=value=>{input().value=String(value);input().dispatchEvent(new Event('input',{bubbles:true}));app.press(28);};
 assert(document.querySelectorAll('.physical-dice input').length===1,'one visible die for advantage');
 assert(document.querySelector('[data-dice-progress]').textContent.includes('1 z 2'),'first d20 counter');
 input().value='0';input().dispatchEvent(new Event('input',{bubbles:true}));
 assert(!app.bindings().get(28).enabled,'invalid physical die disables confirmation');
 const attack=m.s.task;roll(14);
 assert(m.s.task===attack&&attack.diceResults[0]===14&&m.actor('enemy1').hp===45,'first accept stores die without resolving attack');
 assert(document.querySelector('[data-dice-progress]').textContent.includes('2 z 2'),'accept shows second d20');
 roll(8);
 assert(m.s.task.outcome==='damage'&&m.s.task.parts.length===2,'advantage selects best die then opens weapon and sneak dice');
 assert(input().max==='8'&&!app.bindings().has(5),'rapier die only; no manual die-switching rune');
 assert(!document.querySelector('.decision').textContent.includes('Edytowana kość'),'old switching control removed');
 const hp=m.actor('enemy1').hp,charges=m.active.charges;roll(4);
 assert(m.actor('enemy1').hp===hp&&m.active.charges===charges,'weapon die alone does not apply damage or charge again');
 assert(input().max==='6'&&input().min==='1','next input is sneak d6');
 assert(document.querySelector('[data-confirmed-dice]').textContent.includes('k8: 4'),'confirmed weapon roll remains visible');
 const snapshot=m.snapshot();m.restore(snapshot);app.render();
 assert(input().max==='6'&&m.s.task.diceResults[0]===4,'reload resumes second die with first result locked');
 assert(!m.submitDie(6,0)&&!m.submitDie(7,1),'stale die index and out-of-range value rejected');
 const partial=m.snapshot();app.press(app.slot('Gwiazda'));app.press(29);
 assert(m.snapshot()===partial,'information roundtrip preserves partial roll');
 roll(3);assert(m.actor('enemy1').hp===hp-11&&m.s.phase==='result','last accept applies 4 + strength modifier 4 + sneak 3 once');
 app.press(28);assert(m.actor('enemy1').hp===hp-11,'result confirmation never applies damage again');
 // A single 2k4 component also means two separate accepts, with its modifier once.
 const heal=create();heal.active.hp=5;play(heal,'item');
 assert(heal.rollDice().length===2,'2k4 expands to two physical dice');
 const noInput=heal.snapshot();
 for(const value of [0,5,1.5,NaN])assert(!heal.submitDie(value),'invalid d4 rejected');
 assert(heal.snapshot()===noInput,'invalid inputs leave partial state untouched');
 heal.submitDie(2);assert(heal.active.hp===5,'no healing before both dice');
 heal.restore(heal.snapshot());heal.submitDie(4);drain(heal);
 assert(heal.active.hp===13,'2k4 summed and +2 healing modifier added once');
 // Individual d20s remain separate for disadvantage and for the later Hymn decision.
 const save=create('mira');save.active.hidden=['enemy1'];save.active.hymn={source:'lorian'};
 save.s.queue.push(save.saveTask(save.active.id,'dexterity',14,{kind:'fear',source:save.active.id}));save.advance();
 save.submitDie(19);assert(save.s.task.type==='roll'&&save.active.hymn,'Hymn waits for both d20s');
 save.submitDie(2);assert(save.s.task.type==='hymn'&&save.s.task.natural===2&&save.s.task.total===6,'disadvantage uses lower die plus modifier once');
 save.decideHymn(false);assert(save.status(save.active,'fear'),'failed save applied only after complete roll and Hymn decision');
 // Legacy snapshots without partial dice state start at the first die.
 const old=create();play(old,'item');const legacy=old.snapshot();old.restore(legacy);
 assert(old.submitDie(1)&&old.s.task.diceResults.length===1,'old pending roll remains compatible');
 """)


def test_enemy_rolls_pause_movement_and_store_results_once(tmp_path: Path) -> None:
    browser_check(tmp_path, HELPERS + r"""
 const moving=()=>{
   const m=create();m.actor('enemy1').pos={x:3,y:4};m.actor('enemy3').pos={x:3,y:3};
   assert(m.choose('move')&&m.select({x:1,y:4})&&m.commit(),'movement triggers two enemy reactions');
   return m;
 };
 const m=moving(),hp=m.active.hp,position={...m.active.pos};
 assert(m.isEnemyRoll()&&m.s.task.power==='opportunity'&&m.s.task.actor==='enemy1','first enemy is announced');
 assert(m.actor('enemy1').reaction&&m.active.hp===hp&&m.active.pos.x===position.x,'notice has no reaction cost, damage or movement');
 const pending=m.snapshot();m.restore(pending);
 assert(!m.submitDie(20)&&!m.submit([20]),'enemy cannot use manual player input');
 let bad=[16,0];assert(!m.confirmEnemyRoll(()=>bad.shift())&&m.snapshot()===pending,'invalid generated damage rolls back attack and reaction');
 let dice=[16,4],calls=0;
 assert(m.confirmEnemyRoll(()=>{calls++;return dice.shift();}),'one accept resolves attack and damage');
 assert(calls===2&&m.s.task.type==='enemy-result'&&m.s.task.rolls.length===2,'complete automatic attack result');
 assert(m.s.task.rolls[0].total===18&&m.s.task.rolls[1].loss.hp===6,'modifier and damage applied correctly');
 assert(m.active.hp===hp-6&&!m.actor('enemy1').reaction&&m.actor('enemy3').reaction,'only first reaction consumed');
 assert(m.active.pos.x===position.x,'movement waits while result is shown');
 const result=m.snapshot();m.restore(result);
 assert(!m.confirmEnemyRoll(()=>{throw Error('reroll');})&&m.snapshot()===result,'result reload and repeated roll cannot change outcome');
 m.acknowledgeEnemyResult();assert(m.isEnemyRoll()&&m.s.task.actor==='enemy3','next opponent waits for its own accept');
 calls=0;m.confirmEnemyRoll(()=>{calls++;return 1;});
 assert(calls===1&&!m.s.task.rolls[0].success&&m.s.task.rolls.length===1,'natural-one miss never rolls damage');
 assert(m.active.hp===hp-6&&m.active.pos.x===position.x,'miss result also pauses movement');
 m.acknowledgeEnemyResult();drain(m);
 assert(m.active.pos.x===1&&m.active.charges===20&&m.active.ordinary&&m.active.special,'both reactions finish before movement; no action/charge cost');
 assert(!m.actor('enemy1').reaction&&!m.actor('enemy3').reaction,'both reactions spent exactly once');
 // A lethal reaction stops the path and skips later reactions against the downed hero.
 const lethal=moving();lethal.active.hp=1;dice=[20,6,6];lethal.confirmEnemyRoll(()=>dice.shift());
 assert(lethal.active.hp===0&&lethal.s.task.rolls[1].parts[0].count===2,'enemy natural 20 rolls critical damage automatically');
 lethal.acknowledgeEnemyResult();drain(lethal);
 assert(lethal.active.pos.x===2&&lethal.actor('enemy3').reaction,'downed hero stays at interruption tile; later enemy does not react');
 // Ordinary enemy attacks also use application rolls, with advantage/disadvantage.
 const enemyTurn=()=>{
   const e=create();e.actor('enemy1').pos={x:3,y:4};e.s.index=e.s.order.indexOf('enemy1');e.beginTurn();return e;
 };
 const adv=enemyTurn();adv.active.hidden=['garran'];play(adv,'attack','base','garran');
 // An older partial manual enemy roll is retained, but remaining dice are automatic.
 adv.s.task.diceResults=[2];adv.restore(adv.snapshot());dice=[20,4,3];adv.confirmEnemyRoll(()=>dice.shift());
 assert(adv.s.task.rolls[0].natural===20&&adv.s.task.rolls[0].dice.flat().join(',')==='2,20','advantage and saved first die respected');
 assert(adv.s.task.rolls[1].loss.hp===9&&!adv.active.ordinary&&adv.active.reaction,'ordinary attack costs no reaction');
 const dis=enemyTurn();dis.addStatus(dis.active,'fear');play(dis,'attack','base','garran');dice=[20,1];dis.confirmEnemyRoll(()=>dice.shift());
 assert(dis.s.task.rolls[0].natural===1&&!dis.s.task.rolls[0].success&&!dis.status(dis.active,'fear'),'disadvantage and single-use fear respected');
 // Automatic physical damage still passes through rage and both resonance pools.
 const protectedHero=create('brakka');protectedHero.actor('enemy1').pos={x:3,y:4};
 protectedHero.addStatus(protectedHero.active,'rage',{remaining:7});protectedHero.addRune(protectedHero.active,'Kielich');protectedHero.addRune(protectedHero.active,'Klepsydra');
 assert(protectedHero.choose('move')&&protectedHero.select({x:1,y:4})&&protectedHero.commit(),'protected hero provokes attack');
 dice=[20,6,5];protectedHero.confirmEnemyRoll(()=>dice.shift());const damage=protectedHero.s.task.rolls[1];
 assert(damage.components[0].value===13&&damage.loss.hp===2&&damage.loss.cup===2&&damage.loss.shield===2,'13 damage halves then consumes shield and temporary HP');
 """)


def test_enemy_opportunity_notice_highlight_and_result_ui(tmp_path: Path) -> None:
    browser_check(tmp_path, r"""
 const app=window.RunePrototype;app.startScene('combat');const m=app.combat.model;
 m.actor('enemy1').pos={x:3,y:4};const hp=m.active.hp;app.render();
 let calls=0;const random=Math.random;Math.random=()=>{calls++;return calls===1?0.775:0.584;};
 try{
   app.press(0);app.combat.selectField(1,4);
   document.querySelector('.charge-initiative').scrollTop=400;app.press(28);
   assert(document.querySelector('.decision h1').textContent==='Atak okazyjny przeciwnika','enemy opportunity notice title');
   assert(document.querySelector('.enemy-roll-notice')&&!document.querySelector('[data-die]'),'no physical die input for enemy');
   assert(document.querySelector('.combat-lab').open&&document.querySelector('.charge-initiative').scrollTop===0,'board opens and scrolls into view');
   assert(document.querySelector('.mock-cell.enemy-focus').dataset.field==='3,4','attacking enemy highlighted on board');
   assert(document.querySelector('.initiative-entry.enemy-focus').textContent.includes('Strażnik'),'enemy also identified in initiative');
   assert(m.active.id==='garran'&&calls===0&&m.active.hp===hp,'notice does not change turn or roll dice');
   const pending=m.snapshot();app.press(29);app.press(app.slot('Gwiazda'));app.press(29);app.render();
   assert(m.snapshot()===pending&&calls===0,'back, information and rendering do not roll');
   const accept=app.bindings().get(28);document.querySelector('.decision').scrollTop=100;app.press(28);
   assert(calls===2&&document.querySelector('.enemy-roll-result'),'accept automatically rolls attack and damage');
   assert(document.querySelector('.decision').scrollTop===0,'result starts at top after scrolled notice');
   accept.fn();assert(calls===2&&m.s.task.type==='enemy-result','stale accept callback cannot reroll or advance result');
   assert(document.querySelector('.enemy-roll-result').textContent.includes('Trafienie')&&document.querySelector('.enemy-roll-result').textContent.includes('Utrata PW: 6'),'hit and actual damage shown');
   assert(!document.querySelector('[data-die]')&&document.querySelector('.mock-cell.enemy-focus'),'result has no editable dice and keeps highlight');
   assert(m.active.hp===hp-6&&m.active.pos.x===2,'damage applied but movement still paused');
   const result=m.snapshot();m.restore(result);app.render();app.press(app.slot('Gwiazda'));app.press(29);
   assert(calls===2&&m.snapshot()===result,'reloaded result and information never reroll');
   app.press(28);
   assert(m.active.pos.x===1&&m.active.hp===hp-6&&calls===2,'second accept continues movement without rerolling');
   assert(!document.querySelector('.mock-cell.enemy-focus')&&!document.querySelector('.initiative-entry.enemy-focus'),'highlight cleared after reaction');
   assert(document.documentElement.scrollWidth<=innerWidth+1,'enemy result does not cause horizontal overflow');
 }finally{Math.random=random;}
 """)


def test_hooks_reactions_rounds_and_failure_boundaries(tmp_path: Path) -> None:
    browser_check(tmp_path, HELPERS + r"""
 // Basic area resolves all damage, then one Hook per distinct victim, then closes.
 const n=create('nimra');n.active.pos={x:3,y:4};n.actor('enemy2').pos={x:4,y:3};
 n.addRune(n.active,'Hak');n.addRune(n.active,'Hak');
 assert(n.choose('force_wave')&&n.exclude(null)&&n.commit(),'basic area with inherited Hooks');
 let count=0;while(['roll','enemy-result'].includes(n.s.task?.type)){
   assert(++count<40,'area roll loop bounded');
   if(n.s.task.type==='enemy-result')n.acknowledgeEnemyResult();
   else if(n.isEnemyRoll())n.confirmEnemyRoll(()=>1);
   else n.submit(n.s.task.parts.map(p=>p.count));
 }
 assert(n.s.task.type==='relocate'&&n.s.task.radius===2&&n.s.chain,'Hooks wait until all damage; two copies extend range');
 const victim=n.actor(n.s.task.target),original={...victim.pos},hp=victim.hp,charges=n.active.charges;
 const fields=n.relocationFields(n.s.task);n.select(fields[0]);n.cancel();
 assert(!n.s.task.destination&&victim.hp===hp&&n.active.charges===charges,'Hook back clears preview only');
 n.select(original);n.confirmRelocation();assert(n.s.task.type==='relocate'&&n.s.task.target!==victim.id,'next unique victim');
 drain(n);assert(!n.s.chain,'chain closes after entire Hook queue');
 // Miss has no Hook. Successful bash displaces before Hook from the new position.
 const g=create();g.actor('enemy1').pos={x:3,y:4};g.addRune(g.active,'Hak');
 play(g,'shield_bash','base','enemy1');g.confirmEnemyRoll(()=>1);g.acknowledgeEnemyResult();g.submit([20]);g.submit(g.s.task.parts.map(p=>p.count));
 assert(g.s.task.label==='Impuls egidy','power relocation before Hook');
 g.select({x:4,y:4});g.confirmRelocation();assert(g.s.task.label==='Rezonans runy Hak'&&g.actor('enemy1').pos.x===4,'Hook starts at displaced position');
 drain(g);
 // One regeneration pool per hero and round; skipping a full pool preserves eligibility.
 const r=create();r.active.charges=19;r.offerRegen(r.active,'test');
 play(r,'second_wind');r.submit([1]);assert(r.s.task.type==='recover','recovery offered after effect');
 r.recover(true);r.submit([4]);assert(r.active.charges===19&&r.active.regenRound===1,'recovery cost and cap');
 r.offerRegen(r.active,'second event');assert(!r.active.regenReason,'second event cannot recover twice');
 // Losing move for prone does not lose attack or special.
 const p=create();p.addStatus(p.actor('enemy1'),'prone');p.s.index=p.s.order.indexOf('enemy1');p.beginTurn();
 assert(!p.status(p.active,'prone')&&p.movement()===0&&p.active.ordinary&&p.active.special,'standing loses only movement');
 // Opportunity reaction can be declined; hiding suppresses only its observers.
 const o=create('mira');o.active.hidden=['enemy1'];o.actor('enemy1').pos={x:3,y:4};o.actor('enemy3').pos={x:3,y:3};
 assert(o.choose('guard_vault')&&o.selectTarget('enemy2')&&o.select({x:7,y:3})&&o.commit(),'mixed-observer Parkour');
 assert(o.s.task?.outcome==='attack'&&o.s.task.actor==='enemy3','visible observer can react while hidden observer cannot');
 assert(o.actor('enemy1').reaction&&o.actor('enemy3').reaction,'reaction waits for enemy attack confirmation');
 o.confirmEnemyRoll(()=>1);
 assert(o.actor('enemy1').reaction&&!o.actor('enemy3').reaction,'per-observer reaction budgets');
 drain(o);
 const e=create();e.actor('enemy1').pos={x:3,y:4};e.s.index=e.s.order.indexOf('enemy1');e.beginTurn();
 assert(e.choose('move')&&e.select({x:4,y:4})&&e.commit(),'enemy leaves hero reach');
 assert(e.s.task.type==='opportunity','player gets optional reaction prompt');const responder=e.actor(e.s.task.actor);
 e.opportunity(false);drain(e);assert(responder.reaction,'decline retains reaction');
 // Pending result with a hymn is not applied twice after reload/decline.
 const h=create();h.active.hymn={source:'lorian'};h.actor('enemy1').pos={x:3,y:4};
 play(h,'attack','base','enemy1');h.submit([1]);h.decideHymn(false);drain(h);
 assert(h.active.hymn&&h.actor('enemy1').hp===45,'declined natural-one result preserves Hymn and misses');
 """)
