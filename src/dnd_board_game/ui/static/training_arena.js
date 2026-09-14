/* Teaching overlays share the server's physical confirmation contract. */
function trainingLessonsHtml(tutorial) {
  if (!tutorial) return '';
  const next = tutorial.lessons.find(lesson => !lesson.completed);
  return `<section class="training-course" aria-label="Ćwiczenia postaci">
    <div class="training-progress"><b>Przećwiczone zdolności: ${tutorial.completed_count}/${tutorial.total}</b>
      <progress value="${tutorial.completed_count}" max="${tutorial.total}"></progress></div>
    <p>${esc(tutorial.intro)}</p>
    <p>${tutorial.complete ? '<b>✓ Wszystkie zdolności przećwiczone.</b> Podejdź do Nessy, aby zakończyć próbę i wybrać kolejną postać.'
      : 'Ćwicz w dowolnej kolejności. Zaliczenie następuje po rozstrzygnięciu, także przy pudle lub udanej obronie celu. Podbicia możesz wypróbować w ramach ćwiczenia.'}</p>
    ${next ? `<p class="training-next"><b>Następna propozycja: ${esc(next.name)}.</b> ${esc(next.instruction)}</p>` : ''}
    <details class="training-checklist"><summary>Wszystkie ćwiczenia i wskazówki</summary>
      ${tutorial.lessons.map(lesson => `<details class="training-lesson ${lesson.completed ? 'completed' : ''}">
        <summary>${lesson.icon}<span>${lesson.completed ? '✓' : '○'} ${esc(lesson.name)}</span> ${manaCostHtml(lesson.cost)}</summary>
        <p>${esc(lesson.instruction)}</p><p>${manaTextHtml(lesson.explanation)}</p></details>`).join('')}
    </details>
  </section>`;
}

function trainingCommandHtml(instruction) {
  if (!instruction) return '';
  return `<section class="training-command training-next" aria-label="Polecenie">
    <span class="training-command-label">Teraz zrób</span>
    <p>${esc(instruction)}</p>
  </section>`;
}

function renderTrainingNotice(notice) {
  const old = document.getElementById('training-notice');
  if (!notice) {old?.remove(); return;}
  if (old?.dataset.abilityId === notice.id) return;
  old?.remove();
  const overlay = document.createElement('section');
  overlay.id = 'training-notice';
  overlay.dataset.abilityId = notice.id;
  overlay.className = 'training-notice';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');
  overlay.setAttribute('aria-labelledby', 'training-notice-title');
  overlay.innerHTML = `<div class="training-notice-card"><small>NESSA · ${notice.phase === 'introduction' ? 'PRZED ĆWICZENIEM' : notice.phase === 'briefing' ? 'TWOJE ZADANIE' : notice.phase === 'retry' ? 'SPRÓBUJ PONOWNIE' : notice.phase === 'final_result' ? 'KONIEC POJEDYNKU' : 'ĆWICZENIE ZALICZONE'}</small>
    <h2 id="training-notice-title">${esc(notice.name)}</h2>
    ${notice.intro ? `<p>${esc(notice.intro)}</p>` : ''}
    ${notice.cost?.length && (!notice.phase || ['introduction', 'briefing'].includes(notice.phase)) ? `<p class="training-notice-cost">${notice.icon} Koszt: ${manaCostHtml(notice.cost)}</p>` : ''}
    ${notice.narration ? `<p>${esc(notice.narration)}</p>` : ''}
    ${notice.explanation ? `<p>${manaTextHtml(notice.explanation)}</p>` : ''}${trainingCommandHtml(notice.instruction)}
    ${notice.phase ? '' : '<p class="muted">Liczy się wykonanie i rozstrzygnięcie zdolności. Zaliczenie ćwiczenia nie oznacza automatycznie trafienia ani pokonania obrony celu.</p>'}
    <button class="panel-accept" onclick="acknowledgeTrainingNotice()">${esc(notice.button || '✓ Rozumiem — wróć do ćwiczeń')}</button>
    <p class="muted">Na planszy świeci niebieski przycisk ✓.</p></div>`;
  overlay.addEventListener('keydown', event => {
    if (event.key === 'Tab') {event.preventDefault(); overlay.querySelector('button').focus();}
    if (event.key === 'Escape' || event.key === 'Backspace') {event.preventDefault(); event.stopPropagation();}
  });
  document.body.appendChild(overlay);
  window.requestAnimationFrame(() => overlay.querySelector('button')?.focus({preventScroll:true}));
}

function acknowledgeTrainingNotice() {
  const notice = state?.training_arena?.tutorial?.notice;
  if (!notice || busy) return false;
  api('/api/training/acknowledge', {ability_id:notice.id}, 'Przechodzę dalej…');
  return true;
}

function renderTrainingArena() {
  const panel = document.getElementById('training-arena-panel');
  const arena = state.training_arena;
  document.body.classList.toggle('training-arena-mode', Boolean(arena));
  document.body.classList.toggle('training-exploration-mode', Boolean(state.exploration_mana?.active));
  document.body.classList.toggle('training-guided-mode', arena?.mode === 'walkthrough');
  document.body.classList.toggle('training-notice-active', Boolean(arena?.tutorial?.notice));
  document.body.classList.toggle('training-setup-active', arena?.mode === 'walkthrough' && arena.tutorial?.phase === 'setup');
  panel.hidden = !arena;
  renderTrainingNotice(arena?.tutorial?.notice);
  if (!arena) return;
  if (arena.mode === 'exploration') {renderExplorationMana(panel, state.exploration_mana); return;}
  if (arena.mode === 'traps') {renderSimpleTrapTraining(panel, arena); return;}
  if (arena.mode === 'walkthrough') {renderGuidedArena(panel, arena); return;}
  const selected = document.getElementById('training-mode')?.value || arena.mode;
  const type = document.getElementById('training-creature-type')?.value || arena.creature_type;
  panel.innerHTML = `<div class="training-heading"><div><small>MAPA 0 · ARENA NESSY</small><h2>Poznaj swoją postać</h2></div><b>${arena.tutorial ? 'Samouczki ukończone' : 'Pokazy zakończone'}: ${arena.completed.length}/7</b></div>
    ${arena.can_start ? `<p>Wybierz postać. Samouczek dobiera figurki i cele do jej zdolności. Rozpoczęte ćwiczenia możesz kontynuować po ponownym rozstawieniu.</p>
      <div class="training-options"><label>Tryb<select id="training-mode" onchange="document.getElementById('training-type-label').hidden=this.value==='tutorial'">
        <option value="tutorial" ${selected==='tutorial'?'selected':''}>Samouczek postaci · wszystkie zdolności</option>
        <option value="basic" ${selected==='basic'?'selected':''}>Swobodny trening · 1 kukła</option>
        <option value="support" ${selected==='support'?'selected':''}>Swobodny trening · wsparcie</option>
        <option value="area" ${selected==='area'?'selected':''}>Swobodny trening · obszary</option></select></label>
      <label id="training-type-label" ${selected==='tutorial'?'hidden':''}>Kukła naśladuje<select id="training-creature-type">
        <option value="humanoid" ${type==='humanoid'?'selected':''}>Humanoida</option><option value="undead" ${type==='undead'?'selected':''}>Nieumarłego</option><option value="beast" ${type==='beast'?'selected':''}>Zwierzę</option></select></label></div>
      <div class="training-roster">${arena.heroes.map(hero=>`<button onclick="startRecruitmentTrial('${esc(hero.id)}')"><b>${esc(hero.name)}</b><small>${hero.tutorial_count}/${hero.tutorial_total} zdolności · ${hero.tutorial_count===hero.tutorial_total?'powtórz samouczek':'rozpocznij / kontynuuj'}</small></button>`).join('')}</div>`
    : `<p><b>Trwa próba: ${esc(arena.heroes.find(h=>h.id===arena.current_hero_id)?.name || '')}.</b></p>`}
    ${!arena.can_start ? trainingLessonsHtml(arena.tutorial) : ''}
    ${!arena.can_start ? `<button class="secondary" onclick="api('/api/training/nessa', {}, 'Podchodzę do rozmowy z Nessą…')" ${arena.can_talk ? '' : 'disabled'}>Porozmawiaj z Nessą · pole (3,18)</button>` : ''}
    <details><summary>Zasady próby i rozstawienie</summary>
      <p>${arena.tutorial ? 'Każdy samouczek ma trzech przeciwników (180 PW, KP 10, +5 do trafienia) i rannego pomocnika; Garran ma dwóch pomocników do ćwiczenia podbić osłony. Kukła napastnika podchodzi i zadaje niewielkie obrażenia, umożliwiając reakcje; pozostałe cele stoją i zadają 0 obrażeń. Dokładne ustawienie wskaże plansza podczas przygotowania.'
        : 'Swobodna próba: kukła ma 50 PW, KP 10, +5 do trafienia i 20 ft ruchu. Wsparcie dodaje rannego, zatrutego pomocnika i 1 obrażenie kukły; wariant obszarowy ma trzy kukły.'}</p>
      <p>Pomocnik nie ma osobnej tury, ale może przyjmować wsparcie, flankować i wykonać atak na rozkaz Garrana. Fale i Zagrożenie nie zwiększają obrażeń treningowych.</p>
      <p><b>Samouczek zaliczasz po przećwiczeniu każdej zdolności.</b> Pokonanie kukieł lub wcześniejsza rozmowa z Nessą kończy podejście, ale nie zalicza brakujących ćwiczeń. W swobodnym treningu wystarczy pokonać kukły albo porozmawiać z Nessą.</p>
      <p>Na nową próbę przygotuj 25 kart many, po 5 każdego koloru: 5 na rynku, 20 w talii. Nie ma prywatnej ręki. Koszt odkładaj przed efektem; rynek uzupełniaj na końcu tury według instrukcji. Pomocnik nie powiększa talii.</p>
      <p>Zasłona, skrzynie i filar blokują ruch i widoczność. Niska osłona daje +2 KP; gruz podwaja koszt ruchu. Wszystkie postacie korzystają z tych samych elementów terenu.</p>
      <p><a href="${esc(arena.map_url)}" target="_blank" rel="noopener">Mapa terenu 20×30</a> · <a href="/rules/physical-mana#${esc(arena.current_hero_id)}" target="_blank" rel="noopener">Instrukcje postaci</a>. Figurki ustawiaj według bieżącego setupu, który uwzględnia wariant postaci.</p>
    </details>`;
}
function startRecruitmentTrial(heroId) {
  const hero = state.training_arena.heroes.find(item => item.id===heroId);
  api('/api/training/start', {hero_id:heroId, mode:document.getElementById('training-mode')?.value || 'tutorial',
    reset_progress:hero?.tutorial_count===hero?.tutorial_total,
    creature_type:document.getElementById('training-creature-type')?.value || 'humanoid'}, 'Nessa przygotowuje próbę…');
}

function renderGuidedArena(panel, arena) {
  const tutorial = arena.tutorial;
  panel.hidden = !arena.can_start && Boolean(tutorial?.notice || tutorial?.phase === 'setup'
    || state.combat?.shared_mana?.declaration || state.combat?.shield_bash);
  if (panel.hidden) {panel.innerHTML = ''; return;}
  panel.innerHTML = `<div class="training-heading"><div><small>ARENA · SAMOUCZEK Z NESSĄ</small><h2>${arena.can_start ? 'Wybierz postać' : esc(arena.heroes.find(h => h.id === arena.current_hero_id)?.name || '')}</h2></div><b>Ćwiczenia walki: ${arena.completed.length}/7</b></div>
    ${arena.can_start ? `<p>Wybierz bohatera jego podświetloną runą — samouczek rozpocznie się od razu. ↩ wraca do menu głównego.</p>
      <div class="training-roster">${arena.heroes.map(hero => `<button onclick="startGuidedTrial('${esc(hero.id)}', ${Boolean(hero.completed)})">${hero.icon || ''}<b>${esc(hero.name)}</b><small>${hero.completed ? '✓ Ukończono · zagraj ponownie' : hero.tutorial_count ? `Kontynuuj · ${hero.tutorial_count}/${hero.tutorial_total} ćwiczeń` : `${hero.tutorial_total} ćwiczeń + pojedynek`}</small></button>`).join('')}</div>
      ${explorationManaRosterHtml(arena)}<a class="secondary training-back" href="/">↩ Menu główne</a>`
    : `<section class="training-course"><div class="training-progress"><b>${tutorial.current ? `Ćwiczenie ${tutorial.index + 1}/${tutorial.total} · ${esc(tutorial.current.name)}` : 'Finał · samodzielny pojedynek'}</b><progress value="${tutorial.index}" max="${tutorial.total}"></progress></div>
      <details class="training-lesson-help"><summary>Cel ćwiczenia i opcje samouczka</summary>
      ${tutorial.current ? `${trainingCommandHtml(tutorial.current.instruction)}<p>${manaTextHtml(tutorial.current.explanation)}</p><p>Koszt: ${manaCostHtml(tutorial.current.cost)} · mana do ćwiczenia jest zapewniona.</p>`
      : '<p>Pokonaj kukłę: 30 PW · KP 13 · atak wręcz +3 · obrażenia 1k6. Korzystaj z pełnego zestawu zdolności i normalnie rozliczaj manę.</p>'}
      ${tutorial.can_retry ? '<button class="secondary" onclick="api(\'/api/training/leave\', {retry:true}, \'Przygotowuję ponowną próbę…\')">↻ Powtórz tę sytuację</button>' : ''}
      <button class="secondary" onclick="api('/api/training/leave', {}, 'Wracam do wyboru postaci…')">↩ Wybór postaci · zachowaj postęp</button>
      <p>We wszystkich ćwiczeniach korzystamy z tego samego terenu.</p><a href="${esc(arena.map_url)}" target="_blank" rel="noopener">Mapa terenu 20×30</a>
      </details></section>`}`;
}

function startGuidedTrial(heroId, resetProgress) {
  api('/api/training/start', {hero_id:heroId, mode:'walkthrough', reset_progress:resetProgress}, 'Nessa przygotowuje ćwiczenia…');
}
