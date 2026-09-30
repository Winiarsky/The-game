'use strict';
// Presentation-only state. No game endpoints, hardware, or production saves.
(() => {
  const D = window.RUNE_DATA;
  const $ = s => document.querySelector(s);
  const esc = s => String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
  const slot = name => D.panel.find(p => p.name === name).slot;
  const icon = i => `<svg class="rune" viewBox="0 0 24 24" role="img" aria-label="${esc(D.panel[i].name)}"><path d="${D.panel[i].path}"/></svg>`;
  const hero = id => D.heroes.find(h => h.id === id);
  let bindings = new Map();
  const REPUTATION = Object.freeze({start:20, cartThreshold:20, cartCost:3, missionReward:5});
  const REPUTATION_OPTIONS = Object.freeze([
    {id:'small',slot:5,cost:1,bonus:1,label:'+1 do testu'},
    {id:'large',slot:6,cost:3,bonus:5,label:'+5 do testu'},
    {id:'reroll',slot:7,cost:5,bonus:0,label:'Dodatkowa k20 · wyższy wynik'},
  ]);
  const S = {
    scene:'start', party:['garran','mira','lorian','nimra'], actor:0, round:1,
    hands:{}, deck:[], discard:[], market:[], allocationHistory:[], recipient:0,
    origin:'combat', phase:'idle', selection:null, upgrade:null, target:0,
    movement:6, ordinary:true, special:true, reaction:true, secondWind:false,
    roll:10, pending:null, track:0, talkActor:0, approach:null,
    reputation:REPUTATION.start, reputationOption:null, reputationPaid:0, extraRoll:null, lockedRoll:null, missionRewardClaimed:false,
    talkDone:false, result:'', log:[], returnScene:'start', detailHero:'garran',
    equipActor:0, previewHp:23, aura:false, auraPaid:false, afterAura:'combat',
    auraRadius:2,auraAc:1,auraGrace:0,paymentPrompt:null,usedCards:{},currentHp:{},temporaryHp:{},conditions:{},effects:{},heroReturn:null,
  };
  const active = () => hero(S.party[S.actor]);
  const hand = id => S.hands[id] || [];
  const count = (list,key) => list.filter(x => x === key).length;
  function notify(message) {
    $('#toast').textContent=message;$('#toast').hidden=false;
    clearTimeout(notify.timer);notify.timer=setTimeout(()=>$('#toast').hidden=true,3500);
  }
  function log(message) { S.log.unshift(message); }
  function bind(i,title,fn,enabled=true,selected=false) {
    bindings.set(i,{title,fn,enabled,selected});
  }
  function button(i,title,sub,fn,options={}) {
    const {enabled=true,selected=false,cost='',main=false}=options;
    bind(i,title,fn,enabled,selected);
    return `<button class="action ${main?'action-main':''} ${selected?'selected':''}" data-slot="${i}" ${enabled?'':'disabled'}>${icon(i)}<span class="action-copy"><span class="action-title">${esc(title)}</span><span class="action-sub">${esc(sub)}</span></span>${cost?`<span class="action-cost">${esc(cost)}</span>`:'<span class="arrow">›</span>'}</button>`;
  }
  function controls(label,fn,enabled=true,back=goBack,backOptions={}) {
    bind(28,label,fn,enabled);bind(29,backOptions.label??'Wróć / odrzuć',back,backOptions.enabled??true);
    return `<div class="buttons"><button class="primary" data-slot="28" ${enabled?'':'disabled'}>${icon(28)}${esc(label)}</button><button class="secondary" data-slot="29" ${backOptions.enabled===false?'disabled':''}>${icon(29)}${esc(backOptions.label??'Wróć')}</button></div>`;
  }
  function strip(list) {
    return `<div class="rune-strip">${list.length?[...new Set(list)].map(key=>`<span class="rune-token">${icon(slot(key))}<span>${esc(key)}</span><b>×${count(list,key)}</b></span>`).join(''):'<span class="rune-token empty">Pusta ręka — podstawowe akcje nadal są dostępne</span>'}</div>`;
  }
  function turn(h,sub='Wybierz działanie') {
    return `<div class="turn-line"><div class="turn-actor"><img class="avatar" src="${h.portrait}" alt=""><div><strong>${h.name}</strong><small>${esc(sub)}</small></div></div><span class="turn-number">${S.scene==='talk'?`${S.talkActor+1} z ${S.party.length} · jedna runda`:`Runda ${S.round}`}</span></div>`;
  }
  function art(kind) {
    const cart=kind==='cart'||kind==='story',combat=kind==='combat'||kind==='reaction';
    const image=cart?'road':combat?'posterunek':'nessa_portrait';
    return `<aside class="scene"><img class="scene-art" src="../../content/scenarios/misja_0_dzwon/assets/images/comic_v2/${image}.png" alt="${cart?'Droga i wóz':combat?'Posterunek':'Nessa'}"><span class="scene-heading">${cart?'Droga do posterunku':combat?'Starcie przy posterunku':'Siedziba Gildii'}</span><div class="scene-content"><div class="eyebrow">${cart?'Wyprawa':combat?'Walka':'Misja 0'}</div><h2>${cart?'Wspólnym wysiłkiem.':combat?'Utrzymajcie pozycję.':'Jeszcze jedna prośba.'}</h2><p class="scene-quote">${cart?'Koło zapadło się w koleinę. Każdy może pomóc na swój sposób.':combat?'Miecz, tarcza i to, co zostawiliście na później.':'„O tym, co zabierzecie na drogę, możemy jeszcze porozmawiać.”'}</p><p class="scene-goal">${cart?'Wydostańcie wóz i zabezpieczcie koło.':combat?'Ruch · atak lub przedmiot · jedna specjalna.':'Przekonajcie Nessę do dodatkowej mikstury.'}</p></div></aside>`;
  }
  function resetTurn() { S.movement=6;S.ordinary=true;S.special=true;S.reaction=true;S.phase='idle';S.selection=null;S.upgrade=null; }
  function shuffledDeck() {
    const result=D.resourceRunes.flatMap(key=>Array(S.party.length).fill(key));
    for(let i=result.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[result[i],result[j]]=[result[j],result[i]];}
    return result;
  }
  function drawOpeningRunes() {
    S.market=[];
    for(let i=0;i<S.party.length+2;i++){
      if(!S.deck.length&&S.discard.length){S.deck=S.discard.splice(0);for(let j=S.deck.length-1;j>0;j--){const k=Math.floor(Math.random()*(j+1));[S.deck[j],S.deck[k]]=[S.deck[k],S.deck[j]];}}
      if(S.deck.length)S.market.push(S.deck.pop());
    }
    S.allocationHistory=[];S.recipient=0;S.scene='allocation';
  }
  function freshEncounter(origin) {
    if(origin!=='combat'){
      S.origin=origin;S.scene='talk';S.track=0;S.talkActor=0;S.talkDone=false;
      S.approach=null;S.reputationOption=null;S.reputationPaid=0;S.extraRoll=null;S.lockedRoll=null;S.result='';S.phase='idle';render();return;
    }
    chargeCombat.start(S.party);S.origin='combat';S.scene='combat';S.phase='idle';render();
  }
  function combatExample() {
    freshEncounter('combat');
  }
  function startScene(scene) {
    $('#toast').hidden=true;
    if(scene==='draw'){freshEncounter('combat');return;}
    if(scene==='talk'||scene==='cart'){freshEncounter(scene);return;}
    if(scene==='combat'){combatExample();return;}
    if(scene==='reaction'){combatExample();notify('Ataki okazyjne pojawiają się podczas ruchu. Sprawdź je w symulatorze pól.');return;}
    S.scene=scene;S.phase='idle';render();
  }
  function openMenu() { if(S.scene!=='menu')S.returnScene=S.scene;S.scene='menu';render(); }
  function goBack() {
    if(S.scene==='menu'){S.scene=S.returnScene;render();return;}
    if(S.scene==='hero'){const back=S.heroReturn;S.scene=back?.scene??'combat';render();window.scrollTo(0,back?.scrollY??0);return;}
    if(S.scene==='journal'){S.scene=S.returnScene;render();return;}
    if(S.scene==='combat'&&S.phase!=='idle'){
      if(S.pending){notify('Ten rzut jest już rozpoczęty. Zakończ go przez ✓.');return;}
      S.phase='idle';S.selection=null;S.target=null;render();return;
    }
    if(S.scene==='talk'&&S.phase==='roll'){notify('Próba jest rozpoczęta; zatwierdź wynik.');return;}
    if(S.scene==='talk'&&S.phase==='reputation'){if(!S.reputationPaid)S.reputationOption=null;render();return;}
    if(S.scene==='talk'&&S.phase==='reputation-reroll'){notify('Koszt dodatkowej kości został opłacony. Wpisz wynik i zatwierdź.');return;}
    if(S.scene==='talk'&&S.phase==='cart-trade'){S.phase='idle';render();return;}
    if(S.scene==='reaction'&&S.selection){S.selection=null;render();return;}
    openMenu();
  }
  function startView() {
    return `<div class="eyebrow">Przy wspólnej planszy</div><h1>Wasza kolejna wyprawa.</h1><p class="intro">Wybierzcie drużynę, przygotujcie wyposażenie i sprawdźcie reputację drużyny oraz runy w walce.</p>`+
      button(5,'Nowa wyprawa','Wybór bohaterów i wyposażenia',()=>{S.reputation=REPUTATION.start;S.missionRewardClaimed=false;S.reputationOption=null;S.reputationPaid=0;S.extraRoll=null;S.log=[];S.scene='setup';render();},{main:true})+
      button(6,'Próba walki','20 ładunków · aktualne moce i ciągły Rezonans',()=>startScene('combat'))+
      button(7,'Próba rozmowy','Nessa · jeden test na bohatera',()=>startScene('talk'))+
      button(8,'Próba reakcji','Ataki okazyjne podczas ruchu na próbnej arenie',()=>startScene('reaction'))+
      `<p class="compact-note">Dolny panel jest klikalny. Te same symbole są przy wyborach na ekranie. To samodzielna makieta nowych zasad.</p>`;
  }
  function setupView() {
    let html=`<div class="eyebrow">Przygotowanie</div><h1>Kto wyrusza?</h1><p class="intro">Wybierzcie od 3 do 6 bohaterów. Runą dodajesz lub usuwasz postać.</p><div class="ability-grid">`;
    D.heroes.forEach((h,i)=>{const selected=S.party.includes(h.id);html+=button(i+5,h.name,h.role,()=>{
      if(selected)S.party=S.party.filter(id=>id!==h.id);else if(S.party.length<6)S.party.push(h.id);render();
    },{selected,enabled:selected||S.party.length<6});});
    return html+'</div>'+controls(`Przygotuj wyposażenie · ${S.party.length} osób`,()=>{S.equipActor=0;S.scene='equipment';render();},S.party.length>=3&&S.party.length<=6);
  }
  function equipmentView() {
    const h=hero(S.party[S.equipActor]);
    return turn(h,'Przygotowanie przed wyprawą')+`<h1>Wyposażenie na drogę.</h1><p class="intro">Startowy zestaw ${h.name}. W terenie nie ma akcji zmiany broni. Przedmioty zużywalne pozostają dostępne.</p><div class="equipment-preview">`+
      h.equipment.map(i=>`<div>${esc(i.slot)}<strong>${esc(i.name)}</strong></div>`).join('')+'</div>'+
      controls(S.equipActor<S.party.length-1?'Zatwierdź · następna postać':'Wyrusz',()=>{
        if(S.equipActor<S.party.length-1)S.equipActor++;else S.scene='story';render();
      },true,()=>{if(S.equipActor>0){S.equipActor--;render();}else{S.scene='setup';render();}});
  }
  function storyView() {
    return `<div class="eyebrow">Misja 0 · Dług za dzwon</div><h1>Nie każde zlecenie<br>zaczyna się od miecza.</h1><p class="intro">Nessa domyka szczegóły zlecenia. Na drodze może przydać się dodatkowa mikstura. Macie po jednej okazji, żeby ją przekonać.</p>`+
      button(5,'Porozmawiajcie z Nessą','Wspólna reputacja, po jednej próbie na osobę',()=>freshEncounter('talk'),{main:true})+
      button(6,'Droga i wóz','Sprawdź ten sam tor przy obiekcie',()=>freshEncounter('cart'));
  }
  function takeAllocatedRune(rune) {
    if(S.scene!=='allocation')return;
    const id=S.party[S.recipient],index=S.market.indexOf(rune);
    if(index<0||hand(id).length>=7)return;
    S.hands[id].push(S.market.splice(index,1)[0]);
    S.allocationHistory.push({rune,index});render();
  }
  function undoAllocation() {
    if(S.scene!=='allocation'||!S.allocationHistory.length)return;
    const {rune,index}=S.allocationHistory.pop(),id=S.party[S.recipient];
    S.hands[id].pop();S.market.splice(index,0,rune);render();
  }
  function confirmAllocation() {
    if(S.scene!=='allocation')return;
    const name=hero(S.party[S.recipient]).name;
    log(`${name}: zatwierdzono przydział${S.allocationHistory.length?': '+S.allocationHistory.map(entry=>entry.rune).join(', '):' bez nowych run'}.`);
    S.allocationHistory=[];
    if(S.recipient<S.party.length-1){S.recipient++;render();return;}
    if(S.market.length&&S.party.some(id=>hand(id).length<7)){
      S.recipient=0;render();return;
    }
    if(S.market.length){S.discard.push(...S.market);S.market=[];}
    S.scene='combat';resetTurn();
    if(active().id==='garran'&&S.aura)S.scene='aura';
    render();
  }
  function allocationView() {
    const recipient=hero(S.party[S.recipient]),full=hand(recipient.id).length>=7,last=S.recipient===S.party.length-1;
    let html=`<div class="eyebrow">Walka · pierwszy dobór · ${S.recipient+1} z ${S.party.length}</div>`+
      `<div class="turn-line"><div class="turn-actor"><img class="avatar" src="${recipient.portrait}" alt=""><div><strong>${recipient.name}</strong><small>Teraz przydzielacie runy tej postaci</small></div></div></div>`+
      `<h1>${recipient.name} wybiera runy.</h1><p class="intro">Kliknięcie runy przenosi jedną sztukę do ręki. ↩ cofa ostatni wybór, ✓ zatwierdza przydział.</p>`+
      `<div class="rune-label"><span>Wspólna pula: ${S.market.length} run</span><span>Limit ręki: 7</span></div><div class="market-grid">`;
    [...new Set(S.market)].forEach(rune=>{html+=button(slot(rune),rune,`Dostępne: ${count(S.market,rune)}`,()=>takeAllocatedRune(rune),{enabled:!full});});
    html+='</div>';
    if(!S.market.length)html+='<p class="compact-note">Pula jest pusta. Możesz cofnąć swój ostatni wybór lub zatwierdzić przydział.</p>';
    else if(full)html+='<p class="compact-note">Ręka jest pełna. Cofnij wybór albo zatwierdź i przekaż kolej.</p>';
    html+=`<div class="rune-label"><span>Ręka: ${recipient.name}</span><span>${hand(recipient.id).length}/7 run</span></div>`+strip(hand(recipient.id));
    const allFull=S.party.every(id=>hand(id).length>=7);
    const label=!last?`Zatwierdź · ${hero(S.party[S.recipient+1]).name}`:!S.market.length?'Zatwierdź i rozpocznij walkę':allFull?'Zatwierdź i odrzuć nadmiar':'Zatwierdź · kolejny obieg';
    if(last&&S.market.length&&!allFull)html+='<p class="compact-note">Pozostałe runy rozdzielicie w kolejnym obiegu, w tej samej kolejności.</p>';
    return html+controls(label,confirmAllocation,true,undoAllocation,{label:'Cofnij wybór',enabled:S.allocationHistory.length>0});
  }
  function paymentParts(card,upgrade=S.upgrade,id=active().id) {
    const remaining=[...hand(id)],fixed=[];
    const take=r=>{const i=remaining.indexOf(r);if(i<0)return false;fixed.push(remaining.splice(i,1)[0]);return true;};
    const boost=upgrade===null?null:card.boosts[upgrade];
    if(upgrade!==null&&!boost)return null;
    if(boost?.[0]&&boost[0]!=='*'&&!take(boost[0]))return null;
    let wild=0;
    if(!(card.free_first&&!S.usedCards[`${id}:${card.id}`])){
      if(card.rune==='*')wild++;
      else if(!take(card.rune))wild+=2;
    }
    if(boost?.[0]==='*')wild++;
    return remaining.length<wild?null:{remaining,fixed,wild};
  }
  function planPayment(card,upgrade=S.upgrade,id=active().id) {
    const parts=paymentParts(card,upgrade,id);
    return parts?[...parts.fixed,...parts.remaining.slice(0,parts.wild)]:null;
  }
  function paymentLabel(card) {
    const parts=paymentParts(card);
    if(!parts)return 'brak potrzebnych run';
    return [...parts.fixed,...(parts.wild?[`${parts.wild} × dowolna (wybierzesz przy płatności)`]:[])].join(' + ')||'0 run';
  }
  function choosePayment(id,parts,done,title='Wybierz runy do zapłaty') {
    if(!parts.wild){done(parts.fixed);return;}
    S.paymentPrompt={id,...parts,picks:[],done,title,returnScene:S.scene};
    S.scene='payment';render();
  }
  function paymentView() {
    const p=S.paymentPrompt,available=[...p.remaining];
    p.picks.forEach(r=>available.splice(available.indexOf(r),1));
    let html=turn(hero(p.id),'Wybór zasobu')+`<h1>${esc(p.title)}</h1><p>Wybierz ${p.wild} run. Wybrano ${p.picks.length}/${p.wild}. Zapłata nastąpi po zatwierdzeniu.</p>`;
    if(p.fixed.length)html+=`<p>Zarezerwowany koszt: ${p.fixed.map(esc).join(', ')}.</p>`;
    html+='<div class="ability-grid">';
    [...new Set(p.remaining)].forEach(r=>{html+=button(slot(r),r,`Pozostało: ${count(available,r)} · wybrano: ${count(p.picks,r)}`,()=>{p.picks.push(r);render();},{enabled:p.picks.length<p.wild&&available.includes(r)});});
    html+='</div>'+strip(p.picks);
    return html+controls('Zatwierdź wybór',()=>{S.scene=p.returnScene;S.paymentPrompt=null;p.done([...p.fixed,...p.picks]);},p.picks.length===p.wild,()=>{
      if(p.picks.length)p.picks.pop();else{S.scene=p.returnScene;S.paymentPrompt=null;}render();
    },{label:p.picks.length?'Cofnij ostatnią runę':'Wróć bez płatności'});
  }
  function effectiveBudget(card) {
    const upgrade=S.selection?.id===card.id?S.upgrade:null;
    const key=upgrade===null?null:card.boost_ids?.[upgrade];
    return card.boost_budgets?.[key]??card.budget;
  }
  function spend(id,payment) {
    const available=[...hand(id)];
    for(const key of payment){const i=available.indexOf(key);if(i<0)return false;available.splice(i,1);}
    S.hands[id]=available;S.discard.push(...payment);return true;
  }
  function canUse(card) {
    if(!['prototype','ready'].includes(card.status)||card.budget==='R'||!S.special)return false;
    if(effectiveBudget(card).includes('A')&&!S.ordinary)return false;
    if(effectiveBudget(card).includes('M')&&S.movement<6)return false;
    if(card.id==='second_wind'&&S.secondWind)return false;
    if(card.once&&S.usedCards[`${active().id}:${card.id}`])return false;
    return Boolean(planPayment(card,null));
  }
  function budgetHtml() {
    return `<div class="phase-pills"><span class="phase-pill ${S.movement?'':'used'}">Ruch ${S.movement}/6 pól</span><span class="phase-pill ${S.ordinary?'':'used'}">Atak / przedmiot</span><span class="phase-pill ${S.special?'':'used'}">Specjalna</span><span class="phase-pill ${S.reaction?'':'used'}">Reakcja</span></div>`;
  }
  function combatList() {
    return `<aside class="prototype-combat-list"><div class="eyebrow">Inicjatywa · posterunek</div><h2>Przy wspólnej planszy</h2>`+
      S.party.map((id,i)=>`<div class="initiative-entry ${i===S.actor?'active':''}"><img class="avatar" src="${hero(id).portrait}" alt=""><div><strong>${hero(id).name}</strong><small>${currentHp(id)}/${hero(id).hp} PW · ${hand(id).length} run</small></div><span class="initiative-value">${18-i*2}</span></div>`).join('')+
      '<div class="initiative-entry"><div class="avatar" style="display:grid;place-items:center;background:#513c32">B</div><div><strong>Borut</strong><small>Przy posterunku · 13 KP</small></div><span class="initiative-value">9</span></div><div class="initiative-entry"><div class="avatar" style="display:grid;place-items:center;background:#3b483b">P</div><div><strong>Parobek</strong><small>Przy wozie · 12 KP</small></div><span class="initiative-value">7</span></div><p class="compact-note">Figurki i mapa pozostają na stole. Cel wybierasz, klikając pole figurki na planszy.</p></aside>';
  }
  function chooseAction(card) { S.selection=card;S.upgrade=null;S.target=null;S.phase='detail';render(); }
  // Mock input from the board adapter; no destination controls on the screen.
  function previewMovement(distance) {
    if(S.scene!=='combat'||S.phase!=='move'||!Number.isInteger(distance)||distance<1||distance>S.movement)return false;
    S.target=distance;render();return true;
  }
  // Mock board field event, separate from rune/button navigation.
  function previewTargetField(row,column) {
    if(S.scene!=='combat'||S.phase!=='detail'||!S.selection||!needsCombatTarget(S.selection))return false;
    const target=legalCombatTargets(S.selection).find(entry=>entry.cell[0]===row&&entry.cell[1]===column);
    if(!target)return false;
    S.target=target.index;render();return true;
  }
  function needsCombatTarget(card) {
    return card.basic||['shield_bash','garran_command_halt','counterattack_command'].includes(card.id);
  }
  function legalCombatTargets(card) {
    if(card.id==='counterattack_command')return S.party.filter(id=>id!==active().id).map((id,index)=>({
      index,name:`${hero(id).name} · pole (8, ${17+S.party.indexOf(id)})`,cell:[8,17+S.party.indexOf(id)],detail:'Do 3 pól · własna runa i reakcja',legal:hand(id).length>0&&Math.abs(S.party.indexOf(id)-S.actor)<=3,
    })).filter(target=>target.legal);
    const enemies=[{index:0,name:'Borut · pole (9, 17)',cell:[9,17],distance:1},{index:1,name:'Parobek · pole (10, 18)',cell:[10,18],distance:2}];
    const range=card.id==='garran_command_halt'?12:1;
    return enemies.filter(target=>target.distance<=range).map(target=>({...target,detail:`Dystans: ${target.distance} pól · bez osłony`}));
  }
  function rangePreview(card) {
    let kind='self',description='Cel: twoja postać.';
    if(needsCombatTarget(card)){
      kind='targets';description=card.id==='garran_command_halt'?'Zasięg: 12 pól.':card.id==='counterattack_command'?'Zasięg: sojusznik do 3 pól.':'Zasięg: sąsiednie pole.';
    }else if(card.id==='iron_bastion'){
      kind='aura';description=`Aura: promień ${S.upgrade!==null&&card.boosts[S.upgrade][0]==='Brama'?3:2} pól wokół pola rzucenia. Krąg pozostaje w miejscu.`;
    }else if(card.id==='garran_shield_wall'){
      kind='area';description='Obszar: sąsiednie pola z sojusznikami. Bohater poza ochroną.';
    }else if(card.id==='garran_rally'){
      kind='area';description='Obszar: ty i słyszący sojusznicy do 3 pól.';
    }
    return `<div class="board-action-preview" data-preview-kind="${kind}"><strong>${description}</strong><span>${kind==='targets'?'Kliknij podświetlone pole figurki na planszy, a następnie potwierdź decyzję.':'Sprawdź obszar i zatwierdź, aby uruchomić efekt.'}</span></div>`;
  }
  function combatView() {
    const h=active();let html=turn(h)+`<h1>${S.phase==='idle'?'Wybierz akcję':S.phase==='move'?'Ruch':S.phase==='item'?'Użyj przedmiotu':S.phase==='end'?'Koniec tury':S.selection?.name||'Wybierz akcję'}</h1>`+budgetHtml();
    if(S.phase==='idle')html+=`<div class="rune-label"><span>Twoja ręka</span><span>${hand(h.id).length}/7 run</span></div>`+strip(hand(h.id));
    if(S.phase==='roll')return html+rollView('Rzut ataku',resolveCombatRoll);
    if(S.phase==='result')return html+`<div class="selection-preview"><p>${esc(S.result)}</p></div>`+controls('Wróć do swojej tury',()=>{S.phase='idle';S.selection=null;render();},true,()=>{S.phase='idle';S.selection=null;render();});
    if(S.phase==='move'){
      html+=`<div class="board-action-preview" data-preview-kind="movement"><strong>Ruch: do ${S.movement} pól.</strong><span>Przesuń figurkę na podświetlone pole planszy, kliknij je i potwierdź decyzję.</span></div>`;
      return html+controls('Potwierdź ruch',()=>{
        if(S.phase!=='move'||!Number.isInteger(S.target)||S.target<1||S.target>S.movement)return;
        const distance=S.target;S.movement-=distance;S.effects[h.id]=(S.effects[h.id]??[]).filter(effect=>!effect.endsOnMove);S.phase='idle';S.target=null;log(`${h.name}: ruch o ${distance} pól.`);render();
      },Number.isInteger(S.target)&&S.target>0&&S.target<=S.movement);
    }
    if(S.phase==='item')return html+button(5,'Mikstura leczenia','Odzyskaj 6 PW. Cel: twoja postać. Zużywa zwykłą akcję.',()=>{S.target='potion';render();},{selected:S.target==='potion'})+
      controls('Zatwierdź użycie przedmiotu',()=>{
        if(S.phase!=='item'||S.target!=='potion'||!S.ordinary)return;
        S.ordinary=false;setCurrentHp(h.id,Math.min(h.hp,currentHp(h.id)+6));S.phase='result';S.result='Użyto mikstury. Specjalna nadal jest dostępna.';render();
      },S.target==='potion'&&S.ordinary);
    if(S.phase==='end')return html+'<p class="intro">Niewydane runy zostają w ręce. Kończysz swoją turę?</p>'+controls('Zakończ turę',endTurn);
    if(S.phase==='detail'){
      const c=S.selection;html+=`<div class="selection-preview"><p>${esc(c.description)}</p></div>`+rangePreview(c);
      if(!c.basic){
        html+='<div class="ability-grid">'+button(c.slot,'Wariant podstawowy',`${c.free_first&&!S.usedCards[`${h.id}:${c.id}`]?'0 run':'1 × '+(c.rune==='*'?'dowolna':c.rune)} · ${c.budget}`,()=>{S.upgrade=null;render();},{selected:S.upgrade===null});
        c.boosts.forEach(([key,text],index)=>{const keySlot=!key?5+index:key==='*'?5:slot(key);html+=button(keySlot,key?`+ ${key==='*'?'dowolna runa':key}`:'Wariant akcji',text,()=>{S.upgrade=S.upgrade===index?null:index;render();},{selected:S.upgrade===index,enabled:Boolean(planPayment(c,index))});});
        html+='</div>';
      }
      const targets=needsCombatTarget(c)?legalCombatTargets(c):[];
      if(needsCombatTarget(c)){
        html+='<div class="section-label">Legalne cele w zasięgu</div><ul class="legal-targets">';
        targets.forEach(target=>{html+=`<li class="${S.target===target.index?'selected':''}" data-target-index="${target.index}"><strong>${esc(target.name)}</strong><span>${esc(target.detail)}</span>${S.target===target.index?'<small>Wybrano na planszy</small>':''}</li>`;});
        html+='</ul>';
        if(!targets.length)html+='<p class="compact-note">Brak legalnego celu.</p>';
      }
      const payment=c.basic?[]:planPayment(c),targetReady=!needsCombatTarget(c)||targets.some(target=>target.index===S.target);
      html+=`<p class="compact-note">${c.basic?'Atak bronią bez kosztu run.':`Koszt po zatwierdzeniu: ${esc(paymentLabel(c))}.`} ↩ anuluje podgląd bez kosztu.</p>`;
      return html+controls(targetReady?'Zatwierdź akcję':'Wskaż legalny cel',commitCombat,targetReady&&(c.basic?S.ordinary:Boolean(payment)&&canUse(c)));
    }
    bind(0,'Ruch',()=>{S.selection=null;S.target=null;S.phase='move';render();},S.movement>0);
    bind(1,'Atak bronią',()=>chooseAction({id:'weapon',name:'Atak mieczem',basic:true,description:'Zwykły atak wyposażoną bronią. k20 + 6 przeciw KP celu.',budget:'A'}),S.ordinary);
    bind(2,'Przedmiot',()=>{S.selection=null;S.target='potion';S.phase='item';render();},S.ordinary);
    bind(3,'Koniec tury',()=>{S.selection=null;S.phase='end';render();});
    h.cards.filter(c=>c.budget!=='R').forEach(c=>bind(c.slot,c.name,()=>chooseAction(c),canUse(c)));
    return html+'<p class="combat-action-prompt">Naciśnij pole na planszy. Zobaczysz podgląd przed zatwierdzeniem.</p>';
  }
  function commitCombat(selectedPayment=null,partnerPayment=null) {
    const c=S.selection,h=active();
    if(!c||S.phase!=='detail')return;
    if(needsCombatTarget(c)&&!legalCombatTargets(c).some(target=>target.index===S.target))return;
    if(c.basic){if(!S.ordinary)return;S.ordinary=false;}
    else{
      if(!canUse(c))return;
      const parts=paymentParts(c);if(!parts)return;
      if(selectedPayment===null&&parts.wild){choosePayment(h.id,parts,p=>commitCombat(p));return;}
      const pay=selectedPayment??parts.fixed;
      if(c.id==='counterattack_command'){
        const allies=S.party.filter(id=>id!==h.id),ally=allies[S.target];
        if(!ally||!hand(ally).length){notify('Wybrany sojusznik nie ma runy na tę reakcję.');return;}
        if(partnerPayment===null){choosePayment(ally,{remaining:[...hand(ally)],fixed:[],wild:1},p=>commitCombat(pay,p),'Wybierz runę sojusznika');return;}
        spend(ally,partnerPayment);
      }
      if(!spend(h.id,pay))return;S.special=false;S.usedCards[`${h.id}:${c.id}`]=true;
      if(effectiveBudget(c).includes('A'))S.ordinary=false;if(effectiveBudget(c).includes('M'))S.movement=0;
      log(`${h.name}: ${c.name}; koszt ${pay.join(', ')}.`);
    }
    if(c.basic||['shield_bash','garran_command_halt','counterattack_command'].includes(c.id)){
      S.pending={id:c.id,upgrade:S.upgrade};S.phase='roll';S.roll=10;
    }else{
      if(c.id==='second_wind'){S.secondWind=true;S.previewHp=Math.min(h.hp,S.previewHp+8);}
      const boost=S.upgrade===null?null:c.boosts[S.upgrade];
      if(c.id==='iron_bastion'){S.aura=true;S.auraGrace=1;S.auraRadius=boost?.[0]==='Brama'?3:2;S.auraAc=boost?.[0]==='Wieża'?2:1;}
      if(['defensive_stance','garran_shield_wall','garran_rally'].includes(c.id)){
        const effect={id:c.id,name:c.name,description:c.description,boost:boost?.[1]??'',endsOnMove:c.id==='defensive_stance',ac:c.id==='defensive_stance'?2:0};
        S.effects[h.id]=[...(S.effects[h.id]??[]).filter(existing=>existing.id!==c.id),effect];
      }
      if((c.id==='second_wind'&&boost?.[0]==='Wieża')||(c.id==='defensive_stance'&&boost?.[0]==='*'))S.temporaryHp[h.id]=Math.max(S.temporaryHp[h.id]??0,5);
      S.result=`${c.name}: aktywowano. ${c.id==='iron_bastion'?'Pierwsza kolejna tura bez opłaty; potem aura wymaga podtrzymania.':''}`;S.phase='result';
    }
    render();
  }
  function rollView(title,done) {
    bind(26,'Zwiększ wynik',()=>{S.roll=Math.min(20,S.roll+1);render();},S.roll<20);
    bind(27,'Zmniejsz wynik',()=>{S.roll=Math.max(1,S.roll-1);render();},S.roll>1);
    return `<p class="intro">${esc(title)} · rzuć fizyczną k20 i ustaw wynik.</p><div class="roll-input"><div class="stepper"><button data-slot="27" aria-label="Zmniejsz wynik" ${S.roll<=1?'disabled':''}>−</button><output id="die-value" aria-live="polite" style="font:38px Georgia;min-width:72px;text-align:center">${S.roll}</output><button data-slot="26" aria-label="Zwiększ wynik" ${S.roll>=20?'disabled':''}>+</button></div><span>Naturalne 1 i 20<br>pozostają krytyczne.</span></div>`+
      controls('Zatwierdź wynik',done,true,()=>notify('Popraw wynik przez + / −, potem zatwierdź.'));
  }
  function resolveCombatRoll() {
    if(!S.pending)return;
    const hit=S.roll===20||(S.roll!==1&&S.roll+6>=13);
    S.result=`${S.roll} + 6 = ${S.roll+6}. ${hit?'Udana próba.':'Próba nieudana.'} Koszt został rozliczony raz. Obrażenia i skutki w tej makiecie są podglądem karty.`;
    log(S.result);S.pending=null;S.phase='result';render();
  }
  function endTurn() {
    if(S.phase!=='end')return;
    S.actor++;
    if(S.actor>=S.party.length){S.actor=0;S.round++;}
    resetTurn();S.effects[active().id]=[];
    if(S.scene==='combat'&&active().id==='garran'&&S.aura){if(S.auraGrace)S.auraGrace--;else{S.afterAura='combat';S.scene='aura';}}
    render();
  }
  function auraView() {
    return turn(active(),'Początek tury')+'<h1>Podtrzymać bastion?</h1><p class="intro">Jedna dowolna runa utrzymuje podstawową aurę. Możesz też pozwolić jej wygasnąć.</p>'+strip(hand(active().id))+
      button(23,'Podtrzymaj aurę','1 dowolna runa · nie zużywa specjalnej',()=>choosePayment(active().id,{remaining:[...hand(active().id)],fixed:[],wild:1},p=>{if(spend(active().id,p)){S.auraRadius=2;S.auraAc=1;S.scene='combat';render();}},'Runa podtrzymania'),{enabled:hand(active().id).length>0})+
      button(5,'Zakończ aurę','Zachowaj runy na inne działania',()=>{S.aura=false;S.scene='combat';render();});
  }
  const APPROACHES=[
    ['compliments','Komplementy','Charyzma','Korona'],['logic','Logiczne argumenty','Inteligencja','Oko'],
    ['promise','Osobista gwarancja','Charyzma','Korona'],['empathy','Zrozumienie obaw','Mądrość','Oko'],
    ['bluff','Blef','Charyzma','Węzeł'],['demands','Stanowcze żądania','Kondycja','Kotwica'],
  ];
  const CART=[['lift','Uniesienie wozu','Siła','Kotwica'],['lash','Mocowanie osi','Zręczność','Węzeł'],
    ['ground','Ocena gruntu','Mądrość','Oko'],['lever','Prowizoryczna dźwignia','Inteligencja','Wieża']];
  function reputationPanel() {
    return `<div class="reputation-pool"><span>Reputacja drużyny<small>Wspólny zasób · bez odnowienia między scenami</small></span><strong>${S.reputation}</strong></div>`;
  }
  function selectedReputationOption() {
    return REPUTATION_OPTIONS.find(option=>option.id===S.reputationOption)??null;
  }
  function canChooseReputation(option) {
    if(S.origin!=='talk'||S.reputationPaid||S.reputation<option.cost||S.lockedRoll===20)return false;
    return S.lockedRoll!==1||option.id==='reroll';
  }
  function previewTalk() {
    const natural=Math.max(S.lockedRoll,S.extraRoll??S.lockedRoll);
    const bonus=selectedReputationOption()?.bonus??0,total=natural+approachModifier()+bonus;
    const delta=natural===1?-1:natural===20?2:total>=14?1:0;
    return {natural,bonus,total,delta,label:natural===1?'Krytyczna porażka':natural===20?'Krytyczny sukces':delta?'Sukces':'Porażka'};
  }
  function reputationSummary() {
    const social=S.origin==='talk',option=selectedReputationOption(),cost=S.reputationPaid?0:option?.cost??0;
    const preview=previewTalk(),modifier=approachModifier();
    let html=`<div class="selection-preview reputation-summary"><div class="eyebrow">Podsumowanie rzutu · ${esc(S.approach[1])}</div><p class="test-equation">${preview.natural} ${modifier<0?'−':'+'} ${Math.abs(modifier)} + <strong>${preview.bonus}</strong> = <strong>${preview.total}</strong><span>ST 14 · ${preview.label}</span></p><p>Tor: ${S.track} → ${Math.max(-1,Math.min(S.party.length,S.track+preview.delta))} po zatwierdzeniu.</p></div>`;
    if(S.reputationPaid){
      html+=`<p class="intro">Kości: ${S.lockedRoll} i ${S.extraRoll}. Zachowujesz ${preview.natural}.</p><p class="compact-note">Zapłacono ${S.reputationPaid} reputacji. Druga kość wyczerpuje opcję wsparcia tego testu.</p>`;
    }else if(social){
      html+='<div class="reputation-options">';
      for(const choice of REPUTATION_OPTIONS){
        html+=button(choice.slot,choice.label,`Koszt: ${choice.cost} reputacji`,()=>{
          if(!canChooseReputation(choice))return;
          S.reputationOption=S.reputationOption===choice.id?null:choice.id;render();
        },{enabled:canChooseReputation(choice),selected:choice.id===S.reputationOption});
      }
      html+='</div>';
      html+=`<p class="compact-note">Jedna opcja · ↩ usuwa wybór. Reputacja: <strong>${S.reputation} → ${S.reputation-cost}</strong>. ${S.lockedRoll===1?'Premie liczbowe nie zmienią naturalnej 1; dodatkowa kość może ją zastąpić.':S.lockedRoll===20?'Naturalna 20: krytyczny sukces, bez wydawania reputacji.':option?.id==='reroll'?'Koszt pobieramy przed dodatkowym rzutem, także gdy nie poprawi wyniku.':'Koszt pobieramy po zatwierdzeniu.'}</p>`;
    }else html+='<p class="compact-note">Próba fizyczna bez premii za reputację. Reputacja może odblokować zamianę wozu.</p>';
    if(social&&S.reputation>=REPUTATION.cartThreshold&&S.reputation-cost<REPUTATION.cartThreshold)
      html+='<p class="reputation-warning">Po tym wydatku zabraknie reputacji do zamiany wozu (wymagane 20).</p>';
    return html+controls(option?.id==='reroll'&&!S.reputationPaid?'Zapłać 5 i rzuć dodatkową k20':cost?`Zatwierdź rezultat · koszt ${cost}`:'Zatwierdź rezultat',()=>{
      if(S.phase!=='reputation')return;
      if(option?.id==='reroll'&&!S.reputationPaid){
        if(!canChooseReputation(option))return;
        S.reputation-=option.cost;S.reputationPaid=option.cost;S.phase='reputation-reroll';S.roll=10;
        log(`Dodatkowa k20: −${option.cost} reputacji; pozostało ${S.reputation}.`);render();return;
      }
      resolveTalk();
    },true,()=>{if(!S.reputationPaid)S.reputationOption=null;render();});
  }
  function cartTradeView() {
    return `<div class="selection-preview"><p><strong>Powołajcie się na reputację Gildii i zażądajcie zamiany wozu.</strong></p><p>Wóz zostaje zamieniony bez testu i zmęczenia. Nadużycie wpływów obniża reputację.</p><p>Wymagane: ${REPUTATION.cartThreshold}. Koszt: ${REPUTATION.cartCost}. Reputacja: ${S.reputation} → ${S.reputation-REPUTATION.cartCost}.</p></div>`+
      controls('Zamień wóz · −'+REPUTATION.cartCost+' reputacji',()=>{
        if(S.phase!=='cart-trade'||S.reputation<REPUTATION.cartThreshold)return;
        S.reputation-=REPUTATION.cartCost;S.phase='done';S.talkDone=true;
        S.result=`Wóz zamieniony bez zmęczenia. Reputacja −${REPUTATION.cartCost}; pozostało ${S.reputation}.`;log(S.result);render();
      },S.reputation>=REPUTATION.cartThreshold,()=>{S.phase='idle';render();});
  }
  function missionView() {
    return '<div class="eyebrow">Podsumowanie misji · przykład</div><h1>Dotrzymaliście słowa.</h1>'+reputationPanel()+
      '<p class="intro">Próba nagrody za ukończone zlecenie. Reputacja wraca dzięki działaniom drużyny, a nie na początku kolejnej rozmowy.</p>'+
      button(5,S.missionRewardClaimed?'Nagroda już odebrana':`Odbierz +${REPUTATION.missionReward} reputacji`,'Raz na tę wyprawę · robocza wartość nagrody',()=>{
        if(S.missionRewardClaimed)return;S.missionRewardClaimed=true;S.reputation+=REPUTATION.missionReward;
        log(`Ukończona misja: +${REPUTATION.missionReward} reputacji. Razem ${S.reputation}.`);render();
      },{enabled:!S.missionRewardClaimed})+controls('Wróć do menu',()=>{S.scene='menu';render();});
  }
  function progress() {
    const n=S.party.length,bonus=n===3?n:n-1,clean={3:2,4:2,5:3,6:3}[n];
    const label=i=>i<0?'Gorzej':i===0?'Początek':i===n?'Pełny sukces':i>=bonus?'Sukces +':i>=clean?'Sukces':'Z komplikacją';
    return '<div class="progress-track">'+Array.from({length:n+2},(_,i)=>i-1).map(i=>`<div class="progress-step ${i===S.track?'current':''} ${i<S.track?'reached':''}"><b>${i}</b>${label(i)}</div>`).join('')+'</div>';
  }
  function approachModifier(){return hero(S.party[S.talkActor]).abilities.find(a=>a[0]===S.approach?.[2])?.[2]??0;}
  function talkView() {
    const id=S.party[Math.min(S.talkActor,S.party.length-1)],h=hero(id),cart=S.origin==='cart';
    let html=turn(h,'Jedno podejście · jeden test')+`<h1>${cart?'Wóz w koleinie.':'Jeszcze jedna prośba.'}</h1>`+reputationPanel()+(S.phase==='reputation'?'':progress());
    if(S.talkDone)return html+`<div class="selection-preview"><p>${esc(S.result)}</p></div><p class="compact-note">Konfrontacja zakończona. Reputacja przechodzi do kolejnej sceny.</p>`+controls(cart?'Rozpocznij walkę':'Wyrusz w drogę',()=>cart?freshEncounter('combat'):freshEncounter('cart'));
    if(S.phase==='cart-trade')return html+cartTradeView();
    if(S.phase==='reputation')return html+reputationSummary();
    if(S.phase==='reputation-reroll')return html+`<p class="intro">Pierwsza kość: ${S.lockedRoll}. Zapłacono 5 reputacji. Rzuć dodatkową k20; zachowasz wyższy wynik.</p>`+rollView('Dodatkowa kość',()=>{
      if(S.phase!=='reputation-reroll')return;S.extraRoll=S.roll;S.phase='reputation';render();
    });
    if(S.phase==='roll')return html+`<p class="compact-note">${S.approach[1]} · ST 14 · ${S.approach[2]} ${approachModifier()>=0?'+':''}${approachModifier()}</p>`+rollView('Test podejścia',()=>{
      if(S.phase!=='roll')return;S.lockedRoll=S.roll;S.reputationOption=null;S.reputationPaid=0;S.extraRoll=null;S.phase='reputation';render();
    });
    if(S.phase==='talk-result')return html+`<div class="selection-preview"><p>${esc(S.result)}</p></div>`+controls('Następny bohater',()=>{S.talkActor++;S.phase='idle';S.approach=null;S.lockedRoll=null;S.reputationOption=null;S.reputationPaid=0;S.extraRoll=null;render();});
    html+='<p class="intro">Wybierz podejście i rzuć. '+(cart?'Zamiana wozu jest osobną decyzją.':'Po rzucie możesz wydać wspólną reputację, aby poprawić wynik.')+'</p><div class="ability-grid">';
    (cart?CART:APPROACHES).forEach((a,i)=>{html+=button(5+i,a[1],`${a[2]} · ST 14`,()=>{S.approach=a;S.reputationOption=null;S.reputationPaid=0;S.extraRoll=null;S.lockedRoll=null;S.phase='roll';S.roll=10;render();});});
    html+='</div>';
    if(cart)html+=button(11,'Zażądaj zamiany wozu',`Wymagane ${REPUTATION.cartThreshold} reputacji · koszt ${REPUTATION.cartCost} · macie ${S.reputation}`,()=>{S.phase='cart-trade';render();},{enabled:S.reputation>=REPUTATION.cartThreshold});
    return html+button(3,'Pas','Zachowaj aktualny poziom; zużywa twoją kolej',()=>{S.result=`${h.name} pasuje.`;advanceTalk();render();});
  }
  function outcome() {
    const n=S.party.length;
    if(S.track<0)return S.origin==='cart'?'Wóz wydobyto awaryjnie. Pogorszenie: większe zmęczenie.':'Rozmowa zakończona pogorszeniem warunków.';
    if(S.track===0)return S.origin==='cart'?'Wydobycie awaryjne z kosztem zmęczenia.':'Brak dodatkowej mikstury; kontrakt pozostaje.';
    if(S.track>=n)return S.origin==='cart'?'Pełny sukces: wóz wolny, bez zmęczenia, dodatkowa korzyść.':'Pełny sukces: mikstura i dodatkowa korzyść.';
    if(n>3&&S.track>=n-1)return S.origin==='cart'?'Sukces z bonusem: wóz wolny i ocalone wyposażenie.':'Sukces z bonusem: pełna mikstura i przydatna informacja.';
    if(S.track>=Math.ceil(n/2))return S.origin==='cart'?'Sukces: wóz wolny bez zmęczenia.':'Sukces: Nessa daje pełną miksturę.';
    return S.origin==='cart'?'Sukces z komplikacją: wóz wolny, jedna runda zmęczenia.':'Sukces z komplikacją: słabsza mikstura i zobowiązanie.';
  }
  function advanceTalk() {
    if(S.track< -1||S.track>=S.party.length||S.talkActor===S.party.length-1){S.track=Math.max(-1,Math.min(S.party.length,S.track));S.talkDone=true;S.result+=' '+outcome();S.phase='done';}
    else S.phase='talk-result';
    log(S.result);
  }
  function resolveTalk() {
    if(S.phase!=='reputation'||S.lockedRoll===null)return;
    const option=selectedReputationOption(),cost=S.reputationPaid?0:option?.cost??0;
    if(option&&!S.reputationPaid&&(!canChooseReputation(option)||option.id==='reroll'))return;
    const preview=previewTalk(),before=S.track,spent=cost+S.reputationPaid;
    S.reputation-=cost;S.track+=preview.delta;
    S.result=`${hero(S.party[S.talkActor]).name}: ${preview.label.toLowerCase()} (${preview.total}, ST 14). Tor ${before} → ${Math.max(-1,Math.min(S.party.length,S.track))}.`+
      (spent?` Reputacja −${spent}; pozostało ${S.reputation}.`:'');
    S.reputationOption=null;S.reputationPaid=0;S.extraRoll=null;S.lockedRoll=null;advanceTalk();render();
  }
  function reactionView() {
    const h=hero('garran'),special=h.cards.find(c=>c.id==='garran_guard_companion');
    let html=turn(h,'Okno reakcji')+'<h1>Wybierz reakcję.</h1><p class="intro">Przykład wyboru, gdy dostępnych jest kilka odpowiedzi. Możesz zagrać jedną albo nie reagować.</p>'+strip(hand('garran'));
    if(!S.reaction)return html+'<div class="selection-preview"><p>Reakcja została wykorzystana. Kolejna będzie dostępna na początku własnej tury.</p></div>'+controls('Wróć do walki',()=>{S.scene='combat';S.phase='idle';render();});
    html+=button(1,'Atak okazyjny bronią','Bez kosztu run · zużywa reakcję',()=>{S.selection='opportunity';render();},{selected:S.selection==='opportunity'})+
      button(special.slot,special.name,'1 × Węzeł · zużywa reakcję',()=>{S.selection='guard';render();},{selected:S.selection==='guard',enabled:hand('garran').includes('Węzeł')});
    return html+controls(S.selection==='opportunity'?'Zagraj atak · 0 run':S.selection==='guard'?'Zagraj osłonę · 1 Węzeł':'Wybierz odpowiedź',()=>{
      if(!S.reaction||!S.selection)return;
      if(S.selection==='guard'&&!spend('garran',['Węzeł']))return;
      S.reaction=false;log(S.selection==='opportunity'?'Garran: atak okazyjny, 0 run.':'Garran: Osłona towarzysza, 1 Węzeł.');render();
    },Boolean(S.selection),()=>{S.scene='combat';S.phase='idle';S.selection=null;render();});
  }
  function currentHp(id) { return id==='garran'?S.previewHp:S.currentHp[id]??hero(id).hp; }
  function setCurrentHp(id,value) { if(id==='garran')S.previewHp=value;else S.currentHp[id]=value; }
  function informationHero() {
    if(S.scene==='hero')return S.detailHero;
    if(['combat','aura'].includes(S.scene))return active().id;
    if(S.scene==='reaction')return 'garran';
    if(S.scene==='allocation')return S.party[S.recipient];
    if(S.scene==='talk')return S.party[Math.min(S.talkActor,S.party.length-1)];
    if(S.scene==='equipment')return S.party[S.equipActor];
    return null;
  }
  function showHero(id) {
    if(S.scene==='hero')return;
    S.detailHero=id;S.heroReturn={scene:S.scene,scrollY:window.scrollY};S.scene='hero';render();window.scrollTo(0,0);
  }
  function heroView() {
    const h=hero(S.detailHero),hp=currentHp(h.id),effects=S.effects[h.id]??[],conditions=S.conditions[h.id]??[];
    const ownAura=h.id==='garran'&&S.aura,acBonus=Math.max(ownAura?S.auraAc:0,...effects.map(effect=>effect.ac??0));
    const combatContext=['combat','aura','reaction'].includes(S.heroReturn?.scene),ownTurn=h.id===active().id;
    let html=`<div class="eyebrow">Informacja o bohaterze · stan bieżący</div><div class="hero-info-heading"><img class="avatar" src="${h.portrait}" alt=""><div><h1>${h.name}</h1><p class="intro">${esc(h.role)}</p></div></div>`;
    html+=`<div class="hero-preview-stats"><div><b data-stat="hp">${hp}/${h.hp}</b><small>PW — aktualne / maks.</small></div><div><b data-stat="temporary-hp">${S.temporaryHp[h.id]??0}</b><small>Tymczasowe PW</small></div><div><b data-stat="ac">${h.ac+acBonus}</b><small>KP${acBonus?` · baza ${h.ac} + ${acBonus}`:''}</small></div></div>`;
    html+='<div class="section-label">Statusy i aktywne efekty</div><ul class="hero-status-list">';
    if(hp<=0)html+='<li><strong>0 PW</strong><span>Postać wymaga pomocy.</span></li>';
    else if(hp<h.hp)html+=`<li><strong>Ranny</strong><span>Brakuje ${h.hp-hp} PW do pełnego zdrowia.</span></li>`;
    conditions.forEach(condition=>{html+=`<li><strong>${esc(condition.name)}</strong><span>${esc(condition.description??'')}${condition.duration?' · '+esc(condition.duration):''}</span></li>`;});
    effects.forEach(effect=>{html+=`<li><strong>${esc(effect.name)}</strong><span>${esc(effect.description)}${effect.boost?' Wzmocnienie: '+esc(effect.boost):''}</span></li>`;});
    if(ownAura)html+=`<li><strong>Żelazny bastion</strong><span>Aktywna aura: promień ${S.auraRadius} pól, +${S.auraAc} KP i ochrona przed przesunięciem. Podtrzymanie: 1 dowolna runa na początku własnej tury.</span></li>`;
    if(!conditions.length&&!effects.length&&!ownAura&&hp===h.hp)html+='<li>Brak aktywnych statusów i efektów.</li>';
    html+='</ul>';
    if(combatContext&&ownTurn)html+=`<div class="section-label">Bieżąca tura · runda ${S.round}</div><div class="hero-state-grid"><span>Ruch<strong>${S.movement}/${h.speed/5} pól</strong></span><span>Atak / przedmiot<strong>${S.ordinary?'Dostępne':'Wykorzystane'}</strong></span><span>Akcja specjalna<strong>${S.special?'Dostępna':'Wykorzystana'}</strong></span><span>Reakcja<strong>${S.reaction?'Dostępna':'Wykorzystana'}</strong></span></div>`;
    else html+=`<p class="compact-note">Bazowy ruch: ${h.speed/5} pól.</p>`;
    if(h.id==='garran')html+=`<p class="compact-note">Drugi oddech: ${S.secondWind?'wykorzystany w tej walce':'dostępny raz na walkę'}.</p>`;
    html+=`<div class="section-label">Zasoby · ${hand(h.id).length}/7 run</div>`+strip(hand(h.id))+`<p class="compact-note">Reputacja drużyny: ${S.reputation}.</p>`;
    html+='<div class="section-label">Cechy</div><div class="hero-state-grid">'+h.abilities.map(([name,value,modifier])=>`<span>${esc(name)}<strong>${value} (${modifier>=0?'+':''}${modifier})</strong></span>`).join('')+'</div>';
    html+='<div class="section-label">Wyposażenie</div><ul class="hero-equipment-list">'+h.equipment.map(item=>`<li><strong>${esc(item.name)}</strong><span>${esc(item.slot)}</span></li>`).join('')+'</ul>';
    html+=`<div class="section-label">Skaza · ${esc(h.flaw[0])}</div><p class="compact-note">${esc(h.flaw[1])}</p>`;
    html+=h.story.map(([name,text])=>`<div class="section-label">${esc(name)}</div><p class="compact-note">${esc(text)}</p>`).join('');
    html+='<div class="section-label">Zobowiązania</div><p class="compact-note">Bieżące zobowiązania zapisujecie na karcie postaci.</p>';
    return html+controls('Wróć do rozgrywki',goBack,true,goBack);
  }
  function menuView() {
    return '<div class="eyebrow">Menu przy stole</div><h1>Dokąd przechodzimy?</h1>'+
      button(5,'Wróć do rozgrywki','Zachowaj bieżący stan makiety',goBack,{main:true})+
      button(6,'Dziennik','Zapisane działania tej próby',()=>{S.scene='journal';render();})+
      button(7,'Start','Nowa drużyna i wyposażenie',()=>startScene('start'))+
      button(8,'Nowa próba walki','20 ładunków na bohatera, bez doboru run',()=>startScene('draw'))+
      button(9,'Rozmowa z Nessą','Jedna runda i tor postępu',()=>startScene('talk'))+
      button(10,'Wóz','Konfrontacja z obiektem',()=>startScene('cart'))+
      button(11,'Walka','Aktualne karty · Rezonans i moce',()=>startScene('combat'))+
      button(12,'Reakcje','Ataki okazyjne na próbnej arenie',()=>startScene('reaction'))+
      button(13,'Ukończona misja','Przykład jednorazowej nagrody reputacji',()=>{S.scene='mission';render();});
  }
  function render() {
    bindings=new Map();
    const resonanceCombat=S.scene==='combat';
    const previousFlow=$('.decision')?.dataset.combatFlow,previousRight=$('.decision')?.scrollTop??0,previousLeft=$('.charge-initiative')?.scrollTop??0;
    const journalEntries=[...S.log,...(chargeCombat.model?.s.history??[])];
    document.body.classList.toggle('resonance-combat',resonanceCombat);
    const views={start:startView,setup:setupView,equipment:equipmentView,story:storyView,
      allocation:allocationView,combat:combatView,talk:talkView,reaction:reactionView,
      menu:menuView,hero:heroView,aura:auraView,payment:paymentView,mission:missionView,
      journal:()=>'<div class="eyebrow">Dziennik makiety</div><h1>Wasze działania.</h1><div class="journal-list">'+(journalEntries.length?journalEntries.map(s=>`<p>${esc(s)}</p>`).join(''):'<p class="intro">Jeszcze nie wykonano żadnego działania.</p>')+'</div>'+controls('Wróć',()=>{S.scene='menu';render();})};
    const right=resonanceCombat?chargeCombat.right():views[S.scene]();
    const infoId=resonanceCombat?null:informationHero();
    if(infoId){bind(slot('Gwiazda'),'Informacja o bohaterze',S.scene==='hero'?goBack:()=>showHero(infoId),true,S.scene==='hero');bindings.get(slot('Gwiazda')).kind='info';}
    const context=S.scene==='hero'?S.heroReturn?.scene:S.scene==='payment'?S.paymentPrompt?.returnScene:S.scene;
    const left=resonanceCombat?chargeCombat.left():['combat','aura','reaction'].includes(context)?combatList():S.scene==='hero'?art(S.origin):art(['talk','allocation'].includes(S.scene)?S.origin:S.scene);
    $('#main').innerHTML=left+`<section class="decision" aria-label="Bieżąca decyzja">${right}</section>`;
    if(resonanceCombat){
      const flow=chargeCombat.flowKey();$('.decision').dataset.combatFlow=flow;
      if(flow===previousFlow)$('.decision').scrollTop=previousRight;
      $('.charge-initiative').scrollTop=previousLeft;
    }
    if(!bindings.has(26))bind(26,'Przewiń w dół',()=>scrollContent(1));
    if(!bindings.has(27))bind(27,'Przewiń w górę',()=>scrollContent(-1));
    if(!bindings.has(29))bind(29,'Menu / wróć',goBack);
    renderBoard();renderParty();
    $('#demo-nav').innerHTML=[['start','Start','Klepsydra'],['talk','Nessa','Brama'],['cart','Wóz','Romb'],['combat','Walka · Rezonans','Hak']].map(([scene,name,key])=>`<button data-scene="${scene}" data-route="menu:${scene}" aria-current="${S.scene===scene?'page':'false'}" title="Menu ↩ → ${key}">${name}<span class="route-hint">↩ → ${key}</span></button>`).join('');
  }
  function scrollContent(direction) {
    const local=S.scene==='combat'?$('.decision'):$('.journal-list');
    if(local&&local.scrollHeight>local.clientHeight)local.scrollBy({top:direction*160,behavior:'instant'});
    else window.scrollBy({top:direction*180,behavior:'instant'});
  }
  function renderBoard() {
    const selected=[...bindings.values()].some(b=>b.selected);
    const boardContext=S.scene==='combat'?'Walka · runa wybiera moc · pole wybiera cel · ✓ zatwierdza · ★ informacje':S.scene==='hero'?'Informacja o bohaterze · + / − przewija · Gwiazda / ↩ wraca':S.scene==='allocation'?`${hero(S.party[S.recipient]).name}: runa przydziela 1 · ↩ cofa wybór · ✓ następna postać`:S.phase==='reputation'?'Reputacja: wybierz jedną z trzech run · ✓ zatwierdza · ↩ usuwa wybór':['roll','reputation-reroll'].includes(S.phase)?'Wynik kości: + / − → ✓':'Kliknij podświetlone pole planszy';
    $('#board-context').innerHTML=esc(boardContext)+(bindings.get(slot('Gwiazda'))?.kind==='info'?`<span class="hero-info-hint">${icon(slot('Gwiazda'))} — Informacja o bohaterze</span>`:'');
    $('#board-pads').innerHTML=D.panel.map(p=>{
      if(!p.path)return '<div class="board-gap" aria-hidden="true"></div>';
      const b=bindings.get(p.slot),enabled=Boolean(b?.enabled);
      const light=!enabled?'off':b.kind==='info'?'info':b.selected?'selected':p.slot>=26?'control':selected?'dimmed':'available';
      return `<button class="board-pad" data-slot="${p.slot}" data-light="${light}" data-led-color="${light==='info'?'#79c9ef':''}" data-led-level="${{off:0,available:65,selected:100,dimmed:35,control:85,info:80}[light]}" aria-label="${esc(p.name)}${b?' — '+esc(b.title):' — niedostępne'}" aria-pressed="${Boolean(b?.selected)}" title="${esc(p.name)}${b?' · '+esc(b.title):''}" ${enabled?'':'disabled'}>${icon(p.slot)}</button>`;
    }).join('');
  }
  function renderParty() {
    const visible=!['start','setup','equipment','menu','hero','journal','combat','aura','mission'].includes(S.scene);
    $('#party').hidden=!visible;
    $('#party').innerHTML=visible?S.party.map((id,i)=>`<article class="party-member ${i===(S.scene==='talk'?S.talkActor:S.recipient)?'active':''}"><img class="avatar" src="${hero(id).portrait}" alt=""><span><strong>${hero(id).name}</strong><small>${currentHp(id)}/${hero(id).hp} PW</small><span class="party-stats">${S.scene==='talk'?'Wspólna reputacja: '+S.reputation:hand(id).length+'/7 run'}</span></span></article>`).join(''):'';
  }
  function press(i) {
    const b=bindings.get(i);if(!b?.enabled)return false;b.fn();return true;
  }
  document.addEventListener('click',e=>{
    const pad=e.target.closest('[data-slot]');if(pad&&pad.tagName==='BUTTON'){press(Number(pad.dataset.slot));return;}
    const nav=e.target.closest('[data-scene]');if(nav){startScene(nav.dataset.scene);return;}
    const route=e.target.closest('[data-route]');if(route?.dataset.route==='menu')openMenu();
    if(route?.dataset.route==='journal'){S.returnScene=S.scene;S.scene='journal';render();}
  });
  document.addEventListener('keydown',e=>{
    if(e.target.closest('button,input,select,textarea'))return;
    const key={'+':26,'=':26,'-':27,Enter:28,Escape:29}[e.key];
    if(key!==undefined){e.preventDefault();press(key);}
  });
  const chargeCombat=window.ResonancePrototype.create({bind,button,controls,icon,slot,render,notify,getBindings:()=>bindings,isActive:()=>S.scene==='combat'});
  window.RunePrototype={state:S,combat:chargeCombat,previewMovement,previewTargetField:(row,column)=>S.scene==='combat'?chargeCombat.selectField(column,row):previewTargetField(row,column),press,startScene,render,slot,planPayment,bindings:()=>bindings,reputationRules:REPUTATION};
  const initial=new URLSearchParams(location.search).get('scene');
  if(initial&&['combat','reaction','draw','talk','cart'].includes(initial))startScene(initial);else render();
})();
