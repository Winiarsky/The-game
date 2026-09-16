/* The server owns phases, values, modifiers and training completion. */
const explorationColorNames = {C:'Czerwona', B:'Biała', Z:'Zielona', F:'Czarna', N:'Niebieska'};

function explorationManaAction(action, extra = {}) {
  if (busy || !state?.exploration_mana) return false;
  api('/api/exploration-mana', {action, revision:state.exploration_mana.revision, ...extra}, 'Rozstrzygam eksplorację…');
  return true;
}

function explorationManaPrimary() {
  if (typeof keyboardRollWizard !== 'undefined' && keyboardRollWizard) return false;
  if (state?.training_arena?.mode === 'traps' && state.training_arena.trap?.pending) {
    document.getElementById('simple-trap-roll')?.requestSubmit();
    return true;
  }
  if (!state?.exploration_mana?.active) return false;
  const form = document.getElementById('exploration-mana-roll');
  if (form) {form.requestSubmit(); return true;}
  document.querySelector('#training-arena-panel [data-mana-primary]')?.click();
  return true;
}

function simpleTrapAction(action, extra = {}) {
  if (busy) return;
  api('/api/simple-trap',{action, revision:state.training_arena.trap.revision,...extra},'Rozstrzygam pułapkę…');
}

function renderSimpleTrapTraining(panel, arena) {
  const trap = arena.trap;
  panel.hidden = Boolean(arena.tutorial?.notice);
  if (panel.hidden) return;
  panel.innerHTML = `<h2>Pułapka podczas walki</h2>
    <p>Wykrycie: Mądrość i Percepcja. Dezaktywacja: Zręczność i należna biegłość narzędziowa. Każda próba zużywa akcję; między nimi zakończ turę normalnym przyciskiem walki. Bez doboru many do 21.</p>
    ${!state.combat?trainingCommandHtml('Dokończ rozstawienie poniżej i rozpocznij inicjatywę.'):
      trap.status==='hidden'?trainingCommandHtml('W swojej turze przeszukaj okolicę pułapki. Zwykły zasięg to 10 stóp; Mira wykrywa do 45 stóp.'):
      trap.status==='revealed'?trainingCommandHtml('Połóż znacznik pułapki na polu (8,18). Z sąsiedniego pola możesz wykonać dezaktywację, gdy odzyskasz akcję.'):
      trainingCommandHtml('Pułapka została rozstrzygnięta. Ćwiczenie zaliczone; możesz wrócić do wyboru ćwiczenia.')}
    ${trap.result?`<p aria-live="polite">${esc(trap.result)}</p>`:''}
    ${trap.pending?`<form id="simple-trap-roll" onsubmit="event.preventDefault();simpleTrapAction('roll',{roll:Number(this.querySelector('input').value)})">
      <p>${trap.modifiers.map(m=>`${esc(m.label)} ${m.value>=0?'+':''}${m.value}`).join(' · ')}</p>
      <label>Naturalny wynik k20 <input data-roll-dice="1k20" type="number" min="1" max="20" step="1" required aria-label="Wynik testu pułapki"></label>
      <button type="submit">✓ Rozstrzygnij test</button></form>`:
      trap.options.map(o=>`<button onclick="simpleTrapAction('${o.action}')" ${o.enabled?'':'disabled'} title="${esc(o.reason)}">${esc(o.name)}</button>`).join('')}
    <button class="secondary training-back" onclick="simpleTrapAction('leave')">↩ Wybór ćwiczenia · zachowaj zaliczenie</button>`;
}

function submitExplorationManaRoll(event) {
  event.preventDefault();
  const rolls = [...event.target.querySelectorAll('input')].map(input => Number(input.value));
  explorationManaAction('roll', {rolls});
}

function manaValuesHtml(attempt) {
  return `<div class="exploration-mana-values" aria-label="Wartości kolorów">${attempt.values.map(v =>
    `<span class="mana-value mana-${v.color}">${manaCostHtml([v.color])}<b>${esc(v.name)}: ${v.value}</b>${v.base!==v.value?`<small>bazowo ${v.base}, teraz ${v.value}</small>`:''}</span>`).join('')}</div>`;
}

function explorationRuneButton(p, action, extra = {}, label = '', primary = false, css = '') {
  const choice = p.board_choices.find(c => c.action === action && Object.entries(extra).every(([k,v]) => c.extra[k] === v));
  const attrs = choice ? `data-mana-slot="${choice.slot}" ${primary?'data-mana-primary':''} onclick="explorationManaAction('${action}',${esc(JSON.stringify(choice.extra))})"` : 'disabled';
  return `<button class="mana-rune-choice ${css}" ${attrs}>${choice?.icon || ''}<span>${label || esc(choice?.label || '')}${choice?`<small>Na planszy: ${esc(choice.name)}</small>`:''}</span></button>`;
}

function renderExplorationMana(panel, p) {
  if (p?.model === 'party_confrontation') {renderPartyConfrontation(panel, p); return;}
  panel.hidden = false;
  const a = p.attempt;
  let content = '';
  if (p.phase === 'introduction') {
    content = `<section class="training-notice-card mana-inline-notice"><small>NESSA · PRZED ĆWICZENIEM</small>
      <h2>${esc(p.lesson.name)}</h2><p>${esc(p.lesson.narration)}</p>${trainingCommandHtml(p.lesson.objective)}
      ${explorationRuneButton(p,'acknowledge',{},'Przygotuj sytuację',true)}</section>`;
  } else if (p.phase === 'setup') {
    content = `<h2>Przygotowanie sytuacji</h2>${trainingCommandHtml(p.setup.text)}
      ${p.prepared_offers.length && !p.setup.position.length ? `<ol>${p.prepared_offers.map(offer=>`<li>${offer.map(c=>esc(explorationColorNames[c])).join(' → ')}</li>`).join('')}</ol>`:''}
      ${explorationRuneButton(p,'acknowledge',{},'Gotowe',true)}`;
  } else if (!a) {
    content = `<h2>${esc(p.scene.name)}</h2><p>${esc(p.scene.description)}</p>
      ${trainingCommandHtml(p.scene.kind==='npc'?'Wybierz sposób rozmowy z Ireną, naciskając jego podświetloną runę na planszy.':'Wybierz sposób interakcji ze skrzynią, naciskając jego podświetloną runę na planszy.')}
      <div class="mana-methods">${p.options.filter(o=>o.enabled).map(o=>`<article><h3>${esc(o.name)} · ${esc(o.hero)}</h3><p>${esc(o.description)}</p>
        <p><b>Cecha: ${esc(o.ability)}</b> · ${o.modifiers.map(m=>`${esc(m.label)} ${m.value>=0?'+':''}${m.value}`).join(', ')}</p>
        <p>${esc(o.obstacle)}</p>${o.cost?`<p><b>Koszt sposobu:</b> ${esc(o.cost)}</p>`:''}
        ${explorationRuneButton(p,'start',{method:o.id},`Rozpocznij: ${esc(o.name)}`,p.options.filter(o=>o.enabled).length===1)}</article>`).join('')}</div>
      <p class="muted">Rozpoczęcie odsłoni wartości tej metody i zobowiązuje do pierwszego doboru. Nie można podejrzeć innej metody i zacząć od nowa.</p>
      <details><summary>Inne sposoby i ich wykonawcy</summary>${p.options.filter(o=>!o.enabled).map(o=>`<p>${esc(o.name)} — ${esc(o.hero)}: ten bohater nie uczestniczy w ćwiczeniu.</p>`).join('')}</details>`;
  } else {
    const components = a.modifiers.map(m=>`${esc(m.label)} ${m.value>=0?'+':''}${m.value}`).join(' · ');
    content = `<h2>${esc(a.actor)} · ${esc(a.method)}</h2>
      <div class="mana-score"><strong>${a.total}<small> / 21</small></strong><span>${a.busted?'Utrudnienie · 2k20, niższy wynik':a.total===21?'Sukces bez rzutu':`Premia za karty: +${a.bonus}`}</span></div>
      ${manaValuesHtml(a)}<p><b>${esc(a.obstacle.name)}:</b> ${esc(a.obstacle.description)}</p>
      ${a.cards.length?`<p>Twoja pula: ${a.cards.map(c=>`${manaCostHtml([c.color])} ${c.value}`).join(' + ')}</p>`:''}`;
    if (a.phase === 'bargain') {
      content += trainingCommandHtml('Irena: „Podpiszę zeznanie, ale do Nessy z wami nie idę”. Przyjmij dokument bez rzutu albo odrzuć propozycję i wróć do pas/dobór. Odrzucona oferta nie wróci.');
      content += explorationRuneButton(p,'accept_bargain');
      content += explorationRuneButton(p,'decline_bargain',{},'Odrzuć propozycję · wróć do pas/dobór');
      if (a.needs_resume) content += `<p>Przed powrotem do doboru potwierdź zachowanie stosów.</p>${explorationRuneButton(p,'resume')}`;
    } else if (a.needs_resume) {
      content += trainingCommandHtml('Zapis zachowuje wybory, ale nie zna kolejności fizycznej talii. Kontynuuj tylko z zachowanymi stosami. Po ich pomieszaniu użyj „Powtórz lekcję”.');
      content += `${explorationRuneButton(p,'resume',{},'',true)}`;
    } else if (a.phase === 'offer') {
      content += trainingCommandHtml('Dobór został zadeklarowany. Odkryj dwie karty, wybierz jedną i naciśnij runę przypisaną do jej koloru. Resztę odrzuć.');
      if (p.condition.kind==='favor' && a.favor_status!=='used') content += `<div class="mana-condition-action">${explorationRuneButton(p,a.favor_status==='armed'?'cancel_favor':'arm_favor')}<p>${a.favor_status==='armed'?'Wybór koloru nada karcie wartość 1 i przyjmie zobowiązanie. Pozostanie ono także po porażce.':'Ustępstwo jest opcjonalne. Samo otwarcie go nie ponosi kosztu.'}</p></div>`;
      if (a.offer.length) content += `<p>Przygotowana oferta: ${a.offer.map(c=>esc(explorationColorNames[c])).join(' / ')}. Wybierz: <b>${esc(explorationColorNames[a.expected_color])}</b>.</p>`;
      content += `<div class="mana-color-buttons">${a.values.map(v=>`${explorationRuneButton(p,'choose',{color:v.color},`${manaCostHtml([v.color])}${esc(v.name)} · ${v.value}${p.condition.kind==='sensitive_topic'&&v.color===p.condition.color?' · nazwiska za cenę współpracy':''}`)}`).join('')}</div>
        <p>Przy identycznych kolorach możesz dociągać do pierwszej innej barwy. Zatrzymujesz tylko jedną kartę.</p>
        ${a.cards.length&&!a.expected_color?`${explorationRuneButton(p,'empty',{},'Talia wyczerpana — brak karty do wyboru',false,'secondary')}`:''}`;
    } else if (a.phase === 'decision') {
      content += trainingCommandHtml('Przed odkryciem następnych kart naciśnij runę: Kotwica — pas, Grot — dalszy dobór.');
      content += `<div class="mana-decisions">${explorationRuneButton(p,'stand',{},'Pas · przejdź do testu',!a.must_draw)}
        ${explorationRuneButton(p,'draw',{},'Dobierz kolejną ofertę',a.must_draw)}</div>`;
    } else if (a.phase === 'roll') {
      content += trainingCommandHtml(a.busted?'Przekroczenie: rzuć dwoma k20. Ustaw każdą kość przez − / + i potwierdź ✓. W podsumowaniu liczy się niższy wynik; bez premii za karty.':a.end_reason==='limit'?'Cztery wybory zakończone. Rzuć k20, ustaw wynik przez − / + i zatwierdź podsumowanie.':'Rzuć k20, ustaw naturalny wynik przez − / +, potwierdź kość ✓ i sprawdź podsumowanie.');
      content += `<p>${components} = <b>${a.modifier_total>=0?'+':''}${a.modifier_total}</b></p><form id="exploration-mana-roll" onsubmit="submitExplorationManaRoll(event)">
        ${Array.from({length:a.dice_count},(_,i)=>`<label>k20 ${i+1}<input aria-label="k20 ${i+1}" data-roll-dice="1k20" inputmode="numeric" type="number" min="1" max="20" step="1" required></label>`).join('')}
        <button type="submit">✓ Rozstrzygnij test</button></form>`;
    } else if (a.phase === 'reroll_choice') {
      content += `<p>Wynik ${a.roll_total}, ST ${a.dc}. Pierwszy test się nie powiódł. Konsekwencje czekają na decyzję.</p>
        ${explorationRuneButton(p,'reroll',{},'',true)}
        ${explorationRuneButton(p,'accept',{},'Przyjmij porażkę',false,'secondary')}`;
    } else if (a.phase === 'result') {
      content += `<section class="training-command" aria-live="polite"><b>${a.outcome_kind==='compromise'?'Porozumienie':a.success?'Sukces':'Porażka'}</b>
        ${a.rolls.length?`<p>Kości: ${a.rolls.join(', ')}. ${components}. Wynik: ${a.roll_total}; ST ${a.dc}.</p>`:a.outcome_kind==='compromise'?'<p>Przyjęte częściowe porozumienie — bez rzutu.</p>':'<p>Dokładnie 21 — bez końcowego rzutu.</p>'}
        <p>${esc(a.outcome)}</p><p>${a.lesson_completed?'✓ Ćwiczenie rozstrzygnięte i zaliczone.':'Powtórz lekcję, aby wykonać jej cel.'}</p></section>
        ${(p.followups||[]).length?`<section class="mana-debrief"><h3>Co dalej u Nessy?</h3>${p.followups.map(f=>f.completed?`<p>✓ ${esc(f.label)}</p>`:explorationRuneButton(p,'debrief',{id:f.id})).join('')}<p aria-live="polite">${esc(p.debrief_message)}</p></section>`:''}
        ${explorationRuneButton(p,'next',{},'',true)}`;
    }
  }
  panel.innerHTML = `<small>NESSA · EKSPLORACJA · ${esc(p.hero)}</small>
    <p>${p.run_mode === 'sequence' ? `Kurs po kolei · ćwiczenie ${p.course_index + 1}/${p.course_total}` : p.run_mode === 'single' ? 'Pojedyncze ćwiczenie' : ''}</p>
    ${p.condition?.kind && p.condition.kind!=='none'?`<aside class="mana-condition"><b>${esc(p.condition.title)}</b><p>${esc(p.condition.description)}</p>
      ${a&&p.condition.kind==='color_goal'?`<p class="mana-goal-progress">${a.goal_met?'Warunek spełniony — '+(a.phase==='result'?(a.success?'nagroda przyznana':'brak nagrody po porażce'):'uzyskaj sukces'):`Postęp: ${a.goal_progress}/${p.condition.count} · ${esc(explorationColorNames[p.condition.color])}`}</p>`:''}
      ${a?.sensitive_used?'<p>Wybrano drażliwy temat. Przy sukcesie: nazwiska, ale bez dalszej prywatnej pomocy Ireny.</p>':''}</aside>`:''}
    ${p.obligation?`<p class="mana-obligation"><b>${p.obligation.fulfilled?'✓ Zobowiązanie wykonane':'Zobowiązanie pozostaje'}:</b> ${esc(p.obligation.text)}</p>`:''}${content}
    <details class="mana-lesson-help"><summary>Zasady i opcje lekcji</summary><p>${esc(p.reminder)}</p><p>${esc(p.lesson.objective)}</p>
      ${explorationRuneButton(p,'retry',{},'Powtórz lekcję · przygotuj talię od nowa',false,'secondary')}</details>
    ${explorationRuneButton(p,'leave',{},'',false,'secondary training-back')}`;
}
