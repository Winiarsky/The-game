/* Recruitment uses ordinary combat. Only trial setup and roster rotation live here. */
const trainingHints = {
  garran:'Sprawdź Uderzenie tarczą i pozycjonowanie. W próbie wsparcia zaczniesz ranny: przetestujesz też Drugi oddech.',
  brakka:'Uruchom Szał, sprawdź licznik przez kilka rund, a następnie Z bara i Potężne uderzenie.',
  mira:'Podejdź za pełną zasłonę i ukryj się. Sprawdź kolory obserwatorów, Atak z cienia i noże do rzucania.',
  dagna:'Próba wsparcia daje rannego sojusznika do leczenia. Wybierz cel nieumarły, aby ćwiczyć odpędzanie.',
  lorian:'Sprawdź serię zwykłych ataków. Do przekazywania many wybierz wsparcie; karty nadal przekazujecie fizycznie.',
  nimra:'Zacznij od pojedynczego czaru. Próba obszarowa daje trzy cele; sprawdź też Metamagię i koncentrację.',
  erynd:'Sprawdź strzały specjalne i Celowanie. Wypróbuj zwierzęcego towarzysza oraz zmianę pozycji za osłoną.',
};
function renderTrainingArena() {
  const panel = document.getElementById('training-arena-panel');
  const arena = state.training_arena;
  document.body.classList.toggle('training-arena-mode', Boolean(arena));
  panel.hidden = !arena;
  if (!arena) return;
  const selected = document.getElementById('training-mode')?.value || arena.mode;
  const type = document.getElementById('training-creature-type')?.value || arena.creature_type;
  panel.innerHTML = `<div class="training-heading"><div><small>MAPA 0 · REKRUTACJA</small><h2>Nessa: pokaż, co potrafisz</h2></div><b>Pokazy zakończone: ${arena.completed.length}/7</b></div>
    ${arena.can_start ? `<p>${arena.finished ? 'Próba dobiegła końca. Możesz wrócić do tej postaci albo zaprosić następną.' : 'Wybierz jedną postać. Każda próba zaczyna się od świeżej kukły i pełnego zestawu bohatera.'}</p>
      <div class="training-options"><label>Próba<select id="training-mode"><option value="basic" ${selected==='basic'?'selected':''}>Podstawowa · 1 kukła, 0 obrażeń</option><option value="support" ${selected==='support'?'selected':''}>Wsparcie · ranny pomocnik, 1 obrażenie</option><option value="area" ${selected==='area'?'selected':''}>Obszarowa · 3 kukły, 0 obrażeń</option></select></label>
      <label>Kukła naśladuje<select id="training-creature-type"><option value="humanoid" ${type==='humanoid'?'selected':''}>Humanoida</option><option value="undead" ${type==='undead'?'selected':''}>Nieumarłego</option><option value="beast" ${type==='beast'?'selected':''}>Zwierzę</option></select></label></div>
      <div class="training-roster">${arena.heroes.map(hero=>`<button onclick="startRecruitmentTrial('${esc(hero.id)}')"><b>${esc(hero.name)}</b><small>${arena.completed.includes(hero.id)?'✓ Pokaz zakończony · powtórz':'Rozpocznij pokaz'}</small></button>`).join('')}</div>`
    : `<p><b>Trwa pokaz: ${esc(arena.heroes.find(h=>h.id===arena.current_hero_id)?.name || '')}.</b> ${esc(trainingHints[arena.current_hero_id] || '')}</p>`}
    ${!arena.can_start ? `<button class="secondary" onclick="api('/api/training/nessa', {}, 'Podchodzę do rozmowy z Nessą...')" ${arena.can_talk ? '' : 'disabled'}>Porozmawiaj z Nessą · pole (3,18)</button>` : ''}
    <details ${arena.can_start?'open':''}><summary>Instrukcja Nessy i rozstawienie</summary>
      <p>Kukła ma <b>50 PW, KP 10, +5 do trafienia</b> i porusza się 20 ft: podchodzi do celu i atakuje. Zadaje 0 obrażeń; wsparcie włącza 1 obrażenie i rozpoczyna próbę z ranami bohatera oraz pomocnika. Pomocnik ma też treningowy znacznik zatrucia do usunięcia. Pomocnik jest celem zdolności i nie ma osobnej tury. Fale many działają normalnie, ale Zagrożenie i fala nie zwiększają obrażeń kukieł.</p>
      <p><b>Koniec próby:</b> pokonaj wszystkie kukły albo podejdź do Nessy na sąsiednie pole i wybierz „Nesso, kończę pokaz”. Rozmowa nie kosztuje many. Nessa nie jest celem ataków.</p>
      <p>Na nową próbę: 20 kart many, po 4 każdego koloru; rynek 5, start 3 karty. Dalej zwykły dobór i pojemność postaci. Wymiany i płatności rozliczacie na stole. Próba wsparcia nie zwiększa talii ani doboru: pomocnik nie jest drugim graczem.</p>
      <p>Szara zasłona, wysoki stos skrzyń i filar blokują ruch oraz widoczność. Na niską brązową osłonę można wejść: stojąca tam figurka ma +2 KP. Osłona między strzelcem a celem daje celowi +2 KP przeciw atakowi dystansowemu. Pomarańczowy pas gruzu podwaja koszt ruchu (prosty krok: 10 ft zamiast 5 ft), ale nie zasłania celu. Przećwicz przejście przez gruz i obejście bokiem. Postaw elementy na polach wskazanych przez setup.</p>
      <p><a href="${esc(arena.map_url)}" target="_blank" rel="noopener">Otwórz mapę 20×30 z polami rozstawienia</a> · <a href="/rules/physical-mana#${esc(arena.current_hero_id)}" target="_blank" rel="noopener">Instrukcje postaci</a></p>
      <p class="muted">To osobna próba. Bez doświadczenia i łupów; następny pokaz odnawia postać, wyposażenie, stany i kukłę. Zapis zachowuje bieżącą walkę oraz ukończone pokazy.</p>
    </details>`;
}
function startRecruitmentTrial(heroId) {
  api('/api/training/start', {hero_id:heroId, mode:document.getElementById('training-mode')?.value || 'basic',
    creature_type:document.getElementById('training-creature-type')?.value || 'humanoid'}, 'Nessa przygotowuje próbę...');
}
