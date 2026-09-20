/* One party marker; all participants share turns and a physical deck. */
function confrontationChoice(p, c) {
  if (c.action === 'scroll') return `<button type="button" class="confrontation-scroll-button" data-mana-slot="${c.slot}" aria-label="${esc(c.label)}" onclick="scrollConfrontation(${c.extra.direction})">${c.extra.direction > 0 ? '+' : '−'}</button>`;
  return `<button class="mana-rune-choice" data-mana-slot="${c.slot}" ${c.slot===28?'data-mana-primary':''} onclick="explorationManaAction('${esc(c.action)}',${esc(JSON.stringify(c.extra))})">${c.icon}<span>${esc(c.label)}<small>Na planszy: ${esc(c.name)}</small></span></button>`;
}
function renderPartyConfrontation(panel, p) {
  panel.hidden = false;
  panel.classList.add('confrontation-view');
  panel.classList.toggle('confrontation-approach-view', p.choosing_approach);
  if (p.choosing_approach) {
    renderConfrontationApproachSelection(panel, p);
    return;
  }
  const readingKey = `${p.scene.id}:${p.actor}:${['introduction','approach','setup','result'].includes(p.phase) ? p.phase : 'play'}`;
  const turnChanged = panel.dataset.confrontationKey !== readingKey;
  const scrollTop = panel.dataset.confrontationKey === readingKey ? panel.querySelector('.confrontation-scroll')?.scrollTop || 0 : 0;
  panel.dataset.confrontationKey = readingKey;
  const effect = p.effect_name || (p.scene.kind === 'object' ? 'Postęp' : 'Wpływ');
  const buttons = p.board_choices.filter(c => !['leave','scroll','take','undo'].includes(c.action)).map(c=>confrontationChoice(p,c)).join('');
  const own = p.party.find(h=>h.id===p.actor);
  let instruction = '';
  if (p.needs_resume) instruction = 'Potwierdź, że zachowano osobiste pule, ofertę i kolejność fizycznej talii. Po ich pomieszaniu powtórz próbę.';
  else if (p.phase === 'recovery') instruction = `${p.actor_name} — ${p.recovery_label || 'Oddech'}. Weź kartę spaloną najwcześniej (${p.recovery_color_name}). Połóż ją na spodzie wspólnej talii. Potwierdź ✓. ${p.recovery_cost ? `Potem spal ${p.recovery_cost} kartę za działanie.` : 'Działanie nie wymaga spalania.'}`;
  else if (p.compromise_pending) instruction = p.mission_ui?.compromise || 'Rozmówca proponuje częściowe porozumienie. Przyjmij kompromis albo odrzuć ofertę i negocjuj dalej.';
  else if (p.phase === 'introduction') instruction = p.approaches?.length ? 'Najpierw każdy bohater wybierze swoje podejście do tej sytuacji.' : 'Przejdź do przygotowania talii many.';
  else if (p.phase === 'approach') instruction = `${p.actor_name}: wybierz podejście runą (${p.approach_index}/${p.party.length}). Sprawdź powiązania pomocy. Ten wybór zostaje na całą konfrontację; tylko opcje dla jednej postaci znikają po wyborze.`;
  else if (p.phase === 'peek_choice') instruction = 'Podejrzyj dolną kartę i wybierz runą: zostaw na spodzie albo przenieś na wierzch. Nie zgłaszaj koloru. To kończy działanie, bez spalania. Odkryta oferta pozostaje bez zmian.';
  else if (p.phase === 'setup') instruction = `${p.mana.preparation} ${p.setup.preparation.join(' ')}`;
  else if (p.phase === 'result') instruction = (p.mana.phase==='drain'?'Mana drain. ':'') + p.result + ' Zbierz wszystkie karty przed następną próbą. ' + (p.completed?'Ćwiczenie zaliczone.':'Aby zaliczyć ćwiczenie, powtórz jego cel.');
  else if (p.mana.phase === 'reveal') instruction = `Odkryj ${p.mana.offer.length ? 'drugą' : 'pierwszą'} kartę i zgłoś jej kolor runą. Wybierzesz kartę po zgłoszeniu obu kolorów. Czarna mana = fioletowe światło.`;
  else if (p.mana.phase === 'choose') instruction = `Wybierz kartę runą pod jej opisem i dodaj ją do swojej puli.${p.mana.offer.length > 1 ? ' Druga zostaje dla następnego bohatera.' : ''}`;
  else if (p.mana.phase === 'burn') instruction = `Odłóż do spalonych ${p.mana.pending} kart z wierzchu, po jednej. Zgłaszaj ich kolory runami. Osobiste pule pozostają.`;
  else if (p.phase === 'turn') instruction = `${p.actor_name}: wykonaj test lub dozwoloną pomoc (spal 1 kartę), albo podejrzyj spód talii bez spalania. ${p.mana.card_count>=6?'Masz pełną pulę 6 kart: nie dobierasz, premia do testów +6.':''}`;
  else if (p.phase === 'check') instruction = `Rzuć k20 przeciw ST ${p.dc}. Po rozstrzygnięciu spal 1 kartę, także po niepowodzeniu. Cała zgromadzona pomoc zużywa się przy tej próbie.`;
  else if (p.phase === 'impact') instruction = `Udany test. Rzuć k${p.impact_die} na ${effect.toLowerCase()}; zmniejszymy wspólny opór o wynik wraz z premiami.`;
  else if (p.phase === 'reaction') instruction = `${p.reaction}. Presja: ${p.pressure} spalonych kart. Reakcja usuwająca kartę dotyczy największej puli kart; odzysk oporu to automatyczny rzut k4. Zatwierdź reakcję.`;
  else instruction = 'Sprawdź rozstrzygnięcie i przejdź dalej.';
  if (p.mission_ui) {
    if(p.phase==='setup') instruction=p.mana.preparation;
    if(p.phase==='result') instruction=p.result+' '+p.mission_ui.mission_result;
  }
  if (p.correction_notice) instruction=p.correction_notice+' '+instruction;
  const roll = p.attempt?.phase === 'roll';
  const cardOption = p.mana.phase === 'choose' && !p.needs_resume ? `<div class="confrontation-offer">${p.mana.offer.map((c,i)=>`<article class="mana-value mana-${c}"><div>${manaCostHtml([c])}<b>+1 do testów</b></div>${manaPassiveDescriptionHtml({label:partyConfrontationPassive(p,c),display:p.passive_details?.[c]},true)}${confrontationChoice(p,p.board_choices.find(option=>option.action==='take'&&option.extra.index===i))}</article>`).join('')}</div>` : '';
  const choosingMana = p.phase === 'turn' && p.mana.phase === 'choose' && !p.needs_resume;
  const portraitUrl = choosingMana ? own?.portrait_url : p.image_url;
  const portraitName = choosingMana ? p.actor_name : p.scene.name;
  const sceneImage=portraitUrl?`<img class="confrontation-scene-image" src="${esc(portraitUrl)}" alt="${esc(portraitName)}">`:'';
  panel.innerHTML = `<div class="confrontation-scroll" tabindex="0" aria-label="Opis konfrontacji i drużyna"><div class="confrontation-scene">${sceneImage}<div><div class="training-heading"><div><small>KONFRONTACJA DRUŻYNOWA · ${p.scene.kind==='npc'?'ROZMOWA':'OBIEKT'}</small><h2>${esc(p.scene.name)}</h2></div><b>${p.choosing_approach ? 'Wybór podejść' : `Runda ${p.round}`} · ${esc(p.actor_name)}</b></div>
    <p>${esc(p.scene.goal)}</p><p class="confrontation-description">${esc(p.scene.description)}</p></div></div>
    ${p.choosing_approach ? confrontationApproaches(p, effect) : ''}
    <div class="training-progress"><b>Opór: ${p.resistance}/${p.maximum}</b><progress max="${p.maximum}" value="${p.resistance}"></progress><span>Talia: ${p.mana.deck} · spalone: ${p.mana.burned}</span></div>
    ${p.forecast?`<p class="confrontation-forecast"><b>Zwiad:</b> najbliższa reakcja — ${esc(p.forecast)}. Bazowe spalanie: ${p.pressure}; pasywy mogą je zmniejszyć.</p>`:''}
    <div class="confrontation-party">${p.party.map(h=>`<article class="${h.id===p.actor?'current':''}"><div class="confrontation-hero-heading">${h.portrait_url?`<img class="confrontation-hero-portrait" src="${esc(h.portrait_url)}" alt="${esc(h.name)}">`:""}<b>${esc(h.name)} · ${h.card_count}/6 kart · test +${h.roll_bonus}</b></div>${h.assigned ? `<small>${esc(h.method)} · ST ${h.dc} · ${effect.toLowerCase()} k${h.die}</small><small>${esc(h.ability)} · test ${h.test_modifier>=0?'+':''}${h.test_modifier} · ${effect.toLowerCase()} ${h.influence_modifier>=0?'+':''}${h.influence_modifier}</small>` : '<small>Podejście jeszcze niewybrane</small>'}${h.card_count>6?'<small>Starszy zapis: bez doboru, premia maks. +6. Nowa konfrontacja zacznie się z pustą pulą.</small>':''}<p>${manaCostHtml(h.cards)}${h.aid?` · Pomoc +${h.aid} do najbliższej próby testu`:''}</p><ul>${h.passives.map(x=>`<li><strong>${esc(x.display?.name || x.label.split(':')[0])}</strong></li>`).join('')}</ul></article>`).join('')}</div>
    ${p.first_test_bonus?`<p class="mana-obligation">${esc(p.first_test_label)}: +${p.first_test_bonus} do pierwszego testu drużyny.</p>`:''}
    ${p.last?`<p class="confrontation-result" aria-live="polite">${esc(p.last)}</p>`:''}
    ${p.obligation?'<p class="mana-obligation">Zobowiązanie: dostarcz list. Pozostaje także po porażce.</p>':''}
    <details><summary>${p.mission_ui?'Zasady konfrontacji':'Zasady i cel ćwiczenia'}</summary><p>${esc(p.reminder)}</p><p>Obwódka symbolu: gruba — kumuluje się; cienka — nie kumuluje się.</p>${p.mission_ui?'':`<p>${esc(p.lesson.objective)}</p>`}</details>
    </div><div class="confrontation-controls">${trainingCommandHtml(instruction)}${cardOption}
    ${roll?`<form id="exploration-mana-roll" onsubmit="submitExplorationManaRoll(event)"><label>${p.die_kind==='test'?'Test k20':`${effect} k${p.attempt.die}`}<input id="confrontation-${p.die_kind}-roll" aria-label="Naturalny wynik kości" data-roll-dice="1k${p.attempt.die}" data-roll-source="${esc(p.actor_name)}" type="number" min="1" max="${p.attempt.die}" required></label><button type="submit">✓ Rozstrzygnij</button></form>`:`<div class="mana-decisions">${buttons}</div>`}
    <nav class="confrontation-navigation"><div>${p.board_choices.filter(c=>c.action==='scroll').map(c=>confrontationChoice(p,c)).join('')}${p.board_choices.filter(c=>c.action==='undo').map(c=>confrontationChoice(p,c)).join('')}${p.board_choices.some(c=>c.action==='scroll')?'<small>− / + przewija opis</small>':''}</div>${confrontationChoice(p,p.board_choices.find(c=>c.action==='leave'))}</nav></div>`;
  panel.querySelector('.confrontation-scroll').scrollTop = scrollTop;
  sizeConfrontation();
  if (turnChanged && !['introduction','approach','setup','result'].includes(p.phase)) {
    const area = panel.querySelector('.confrontation-scroll');
    const current = area.querySelector('.confrontation-party .current');
    if (current) {
      const card = current.getBoundingClientRect(), view = area.getBoundingClientRect();
      if (card.top < view.top || card.bottom > view.bottom) area.scrollTop += card.top - view.top;
    }
  }
}
function partyConfrontationPassive(p,color) {
  return p.color_passives?.[color] || 'Pasyw koloru uruchomi się po doborze.';
}

function scrollConfrontation(direction) {
  const panel=document.querySelector('.confrontation-view:not([hidden])');
  if (!panel) return;
  const areas=[panel.querySelector('.confrontation-scroll'),panel.querySelector('.confrontation-controls')];
  if (direction < 0) areas.reverse();
  const area=areas.find(el=>direction > 0 ? el.scrollTop+el.clientHeight < el.scrollHeight-1 : el.scrollTop > 0);
  if (area) area.scrollBy({top:direction*Math.max(80,area.clientHeight*.7),behavior:'instant'});
}
function sizeConfrontation() {
  document.querySelectorAll('.confrontation-view:not([hidden])').forEach(panel=>{
    const tools=document.getElementById('training-tools');
    const bottom=panel.id==='training-arena-panel' && tools?.getClientRects().length ? tools.getBoundingClientRect().top : innerHeight;
    panel.style.setProperty('--confrontation-room',`${Math.max(200,bottom-Math.max(0,panel.getBoundingClientRect().top)-12)}px`);
  });
}
window.addEventListener('resize',sizeConfrontation);
window.addEventListener('load',()=>{
  const observer=new ResizeObserver(sizeConfrontation);
  document.querySelectorAll('.app-shell-header,#board-disconnected-banner').forEach(element=>observer.observe(element));
});

function confrontationApproaches(p, effect) {
  const available=p.approaches.filter(a=>a.available);
  const rune=a=>`<span class="support-rune" title="${esc(a.name)}">${a.icon}</span>`;
  return `<section class="confrontation-approaches" style="--approach-columns:${Math.min(6,available.length)}" aria-label="Podejścia i powiązania pomocy"><h3>Podejścia · ${esc(p.actor_name)}</h3><div>${available.map(a=>{
    const links=a.supports.includes('*')
      ? `<span class="support-any">Dowolne inne podejście</span><span class="support-runes">${p.approaches.filter(t=>t.id!==a.id||a.repeatable).map(rune).join('')}</span>`
      : a.supports.map(id=>p.approaches.find(t=>t.id===id)).filter(Boolean).map(t=>`<span class="support-target">${esc(t.name)} ${rune(t)}</span>`).join('') || '<span>Brak</span>';
    const mod=`${a.modifier>=0?'+':''}${a.modifier}`;
    return `<article><button type="button" class="approach-card" data-mana-slot="${a.slot}" onclick="explorationManaAction('approach',${esc(JSON.stringify({approach:a.id}))})"><span class="approach-title">${a.icon} ${esc(a.name)}</span><span class="approach-availability ${a.repeatable?'repeatable':'exclusive'}">${a.repeatable?'Może się powtarzać':'Dla jednej postaci'}</span><span class="approach-description">${esc(a.description)}</span><b>${esc(a.ability)} ${mod} · ST ${a.dc}</b><span>${esc(effect)}: k${a.die} ${mod}</span><span class="approach-links"><b>Wsparcie</b>${links}</span></button></article>`;
  }).join('')}</div></section>`;
}


function renderConfrontationApproachSelection(panel, p) {
  const effect = p.effect_name || (p.scene.kind === 'npc' ? 'Wpływ' : 'Postęp');
  const image = p.image_url ? `<img class="confrontation-scene-image" src="${esc(p.image_url)}" alt="${esc(p.scene.name)}">` : '';
  const actor=p.party.find(h=>h.id===p.actor);
  panel.dataset.confrontationKey = `${p.scene.id}:${p.actor}:approach`;
  panel.innerHTML = `<div class="confrontation-scroll"><div class="confrontation-scene">${image}<div>
    <div class="training-heading"><h2>${esc(p.scene.name)}</h2></div>
    <p>${esc(p.scene.goal)}</p><p class="confrontation-description">${esc(p.scene.description)}</p>
    </div></div><div class="approach-layout"><div class="approach-chooser">${actor?.portrait_url?`<img src="${esc(actor.portrait_url)}" alt="${esc(p.actor_name)}">`:''}<div><b>Wybiera ${esc(p.actor_name)} · ${p.approach_index}/${p.party.length}</b>${p.correction_notice?`<p>${esc(p.correction_notice)}</p>`:''}</div></div>${confrontationApproaches(p, effect)}</div>
    <div class="approach-party-summary" aria-label="Wybrane podejścia drużyny">${p.party.map(h=>`<span class="${h.id===p.actor?'current':''}"><b>${esc(h.name)}</b>: ${h.assigned?esc(h.method):h.id===p.actor?'wybiera…':'czeka'}</span>`).join('')}</div>
    ${p.first_test_bonus?`<p class="approach-favor">${esc(p.first_test_label)}: +${p.first_test_bonus} do pierwszego testu drużyny.</p>`:''}
    </div><div class="confrontation-controls"><p class="approach-instruction">Wybierz podejście runą na planszy lub kliknij kafelek. Wybór zostaje na całą konfrontację. Znikają tylko opcje oznaczone „Dla jednej postaci”.</p>
    <nav class="confrontation-navigation"><div><span class="approach-small-screen-scroll">${p.board_choices.filter(c=>c.action==='scroll').map(c=>confrontationChoice(p,c)).join('')}</span>${p.board_choices.filter(c=>c.action==='undo').map(c=>confrontationChoice(p,c)).join('')}</div>${confrontationChoice(p,p.board_choices.find(c=>c.action==='leave'))}</nav></div>`;
  sizeConfrontation();
}
