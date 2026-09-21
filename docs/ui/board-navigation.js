/* Local board input demonstration; no hardware or saved-session writes. */
const BoardNavigation = (() => {
  let startIndex = 0;
  let drawIndex = 0;
  let dialogIndex = 0;
  const starts = [
    { title: 'Rozpocznij wyprawę', detail: 'Misja 0 · Dług za dzwon', scene: 'story', slot: 6 },
    { title: 'Wczytaj przykładową walkę', detail: 'Zapis pokazowy · runda 3', scene: 'combat', slot: 7 },
    { title: 'Jak sterować planszą', detail: 'Runy · − / + · accept · decline', slot: 8 },
  ];
  const control = (slot, label, disabled=false) => `<button data-board-slot="${slot}" aria-label="${label}" title="${label}" ${disabled?'disabled':''}>${rune(slot)}<span>${label}</span></button>`;
  const controls = () => `<div class="nav-controls">${control(26,'−')}${control(27,'+')}${control(28,'accept')}${control(29,'decline')}</div>`;
  function reset() { startIndex = 0; drawIndex = 0; dialogIndex = 0; }
  function startHtml() {
    return `<div class="eyebrow">Dług za dzwon</div><h1>Witajcie przy planszy.</h1><p class="intro">Wybierz pozycję runą albo przyciskami − / + i zatwierdź accept.</p><div class="start-options">${starts.map((item,index)=>`<button class="start-option ${index===startIndex?'is-focused':''}" data-start-option="${index}" aria-current="${index===startIndex?'true':'false'}">${rune(item.slot)}<span><strong>${item.title}</strong><small>${item.detail}</small></span></button>`).join('')}</div><p class="decision-note">Całą makietę możesz obsłużyć przyciskami planszy z paska u góry.</p>`;
  }
  function chooseStart(index) {
    const item=starts[index]; if(!item)return;
    if(item.scene)selectScene(item.scene);
    else modal('Sterowanie planszą', '<p><b>Runy</b> wybierają działania z kart postaci albo widoczne opcje.</p><p><b>− / +</b> przegląda pozycje w bieżącym kroku. <b>Accept</b> zatwierdza wskazany wybór, <b>decline</b> cofa jeden krok.</p><p>W walce wskazujesz figurkę na fizycznej planszy. W makiecie służy do tego pasek „Pola planszy”. Przed wykonaniem zawsze widzisz wybrany cel.</p>');
  }
  function openMenu() {
    modal('Menu sesji', `<button class="modal-action" data-do="close"><b>Wróć do gry</b></button><button class="modal-action" data-modal="journal"><b>Dziennik</b></button><button class="modal-action" data-modal="rules"><b>Pomoc w grze</b></button><button class="modal-action" data-scene="start"><b>Wróć do ekranu startowego</b><small>Makieta · ponowne wejście rozpocznie przykład od nowa</small></button>`);
  }
  function dialogChoices() { return [...document.querySelectorAll('#dialog-content button:not(:disabled)')]; }
  function focusDialogChoice() {
    const choices=dialogChoices(); dialogIndex=choices.length?(dialogIndex+choices.length)%choices.length:0;
    choices.forEach((b,i)=>b.classList.toggle('board-choice',i===dialogIndex));
    choices[dialogIndex]?.scrollIntoView({block:'nearest'});
  }
  function decorateDialog() {
    dialogIndex=0;
    let panel=document.querySelector('#dialog-board');
    if(!panel){panel=document.createElement('div');panel.id='dialog-board';panel.className='dialog-board';document.querySelector('#details').append(panel);}
    panel.innerHTML=`<span>Przyciski planszy · makieta</span>${controls()}`;
    focusDialogChoice();
  }
  function handleDialog(slot) {
    if(!document.querySelector('#details').open)return false;
    const choices=dialogChoices();
    if(slot===29){ if(!state.helpPending)document.querySelector('#details').close(); return true; }
    if(slot===26||slot===27){
      if(choices.length){dialogIndex+=slot===26?-1:1;focusDialogChoice();}
      else document.querySelector('#details').scrollBy({top:slot===26?-140:140,behavior:'auto'});
      return true;
    }
    if(slot===28){if(choices.length)choices[dialogIndex].click();else document.querySelector('#details').close();return true;}
    choices.find(b=>b.querySelector(`[data-panel-slot="${slot}"]`))?.click();
    return true;
  }
  function handleRune(slot) {
    if(handleDialog(slot))return;
    if(state.scene==='start'){
      if(slot===26||slot===27){startIndex=(startIndex+(slot===26?-1:1)+starts.length)%starts.length;render();}
      else if(slot===28)chooseStart(startIndex);
      else if(slot>=6&&slot<=8)chooseStart(slot-6);
      return;
    }
    if(slot===29){openMenu();return;}
    if(state.scene==='story'){
      if(slot===6||slot===28)action('story-talk');
      else if(slot===26||slot===27)document.querySelector('#main').scrollBy({top:slot===26?-120:120});
    } else if(state.scene==='draw'){
      if(slot===26||slot===27){drawIndex=1-drawIndex;render();}
      else if(slot===6||slot===7||slot===28)action((slot===6?0:slot===7?1:drawIndex)===0?'take-red':'take-blue');
    } else if(state.scene==='talk'){
      const detail=talkDetails().find(item=>item.slot===slot);
      if(detail){openModal(detail.modal);return;}
      if(state.spent)return;
      if(slot===26||slot===27)cycleHelp(slot===26?-1:1);
      else if(slot===18)action('test');
      else if(slot===19)action('peek');
      else {const t=helpTargets().find(t=>t.slot===slot);if(t)action('help-'+t.id);}
    } else if(state.scene==='roll'){
      if(slot===26||slot===27){if(document.querySelector('#die'))action(slot===26?'minus':'plus');}
      else if(slot===28){if(document.querySelector('#die'))action('submit-roll');else if(['result','failed'].includes(state.step))action('next-hero');}
      else if(slot>=13&&slot<=17&&state.step==='burn')action('burn');
    }
  }
  function toolbarHtml() {
    if(state.scene==='talk'){
      const targets=helpTargets(),preview=targets[state.helpIndex%targets.length],details=talkDetails();
      return `<span>Runy planszy · makieta</span><div class="board-runes">${[6,7,8,9,10,11,18,19,...details.map(item=>item.slot)].map(slot=>{
        const target=targets.find(t=>t.slot===slot),helpSlot=slot<12,detail=details.find(item=>item.slot===slot);
        const label=detail?detail.label+' — runa '+RUNES[slot][0]:helpSlot?(target?'Pomóż '+HELP_NAMES[target.id]:HEROES[slot-6][1]+' — pomoc niedostępna'):slot===18?'Podejmij próbę':'Podejrzyj spód talii';
        return `<button data-board-slot="${slot}" aria-label="${label}" title="${label}" data-preview="${preview?.slot===slot}" ${(!detail&&state.spent)||(helpSlot&&!target)?'disabled':''}>${rune(slot)}</button>`;
      }).join('')}</div><div class="nav-controls">${control(26,'−',state.spent||targets.length<2)}${control(27,'+',state.spent||targets.length<2)}${control(28,'accept',true)}${control(29,'decline')}</div>`;
    }
    const slots=state.scene==='start'?[6,7,8]:state.scene==='story'?[6]:state.scene==='draw'?[6,7]:state.scene==='talk'?[6,7,8,9,10,11,18,19]:state.step==='burn'?[13,14,15,16,17]:[];
    return `<span>Runy planszy · makieta</span><div class="board-runes">${slots.map(slot=>`<button data-board-slot="${slot}" aria-label="Runa ${RUNES[slot][0]}" title="${RUNES[slot][0]}">${rune(slot)}</button>`).join('')}</div>${controls()}`;
  }
  function afterRender() {
    if(state.scene==='draw')document.querySelectorAll('.offer').forEach((offer,i)=>offer.classList.toggle('board-choice',i===drawIndex));
  }
  return { reset,startHtml,chooseStart,openMenu,decorateDialog,handleDialog,handleRune,toolbarHtml,afterRender };
})();
