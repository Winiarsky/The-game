/* One party marker; all participants share turns and a physical deck. */
function confrontationChoice(p, c) {
  return `<button class="mana-rune-choice" data-mana-slot="${c.slot}" ${c.slot===28?'data-mana-primary':''} onclick="explorationManaAction('${esc(c.action)}',${esc(JSON.stringify(c.extra))})">${c.icon}<span>${esc(c.label)}<small>Na planszy: ${esc(c.name)}</small></span></button>`;
}
function renderPartyConfrontation(panel, p) {
  panel.hidden = false;
  const buttons = p.board_choices.filter(c => c.action !== 'leave').map(c=>confrontationChoice(p,c)).join('');
  const own = p.party.find(h=>h.id===p.actor);
  let instruction = '';
  if (p.needs_resume) instruction = 'Potwierdź, że zachowano osobiste pule, ofertę i kolejność fizycznej talii. Po ich pomieszaniu powtórz próbę.';
  else if (p.phase === 'introduction') instruction = p.lesson.objective;
  else if (p.phase === 'setup') instruction = `Ustaw jedną figurkę drużyny na (9,18), a znacznik celu na (9,17). Zbierz ${p.mana.copies*5} kart — po ${p.mana.copies} każdego koloru — i przetasuj. ${p.setup.preparation.length?p.setup.preparation.join(' '):'Wszystkie osobiste pule są puste.'} Nie rozstawiaj osobnych figurek bohaterów.`;
  else if (p.phase === 'result') instruction = (p.mana.phase==='drain'?'Mana drain. ':'') + p.result + ' Zbierz wszystkie karty przed następną próbą. ' + (p.completed?'Ćwiczenie zaliczone.':'Aby zaliczyć ćwiczenie, powtórz jego cel.');
  else if (p.mana.phase === 'reveal') instruction = 'Uzupełnij ofertę do dwóch kart, o ile talia na to pozwala. Odkrywaj po jednej i zgłaszaj kolor runą.';
  else if (p.mana.phase === 'choose') instruction = 'Obowiązkowo wybierz jedną kartę. Druga pozostaje dla następnego bohatera. Pasyw zadziała po wyborze.';
  else if (p.mana.phase === 'burn') instruction = `Odłóż do spalonych ${p.mana.pending} kart z wierzchu, po jednej. Zgłaszaj ich kolory runami. Osobiste pule pozostają.`;
  else if (p.phase === 'turn') instruction = `${p.actor_name}: wybierz siłę własnego testu albo pomóż sojusznikowi. ${p.mana.points>=21?'Masz 21+ pkt, nie dobierasz. Możesz wybrać tańszą próbę.':''}`;
  else if (p.phase === 'check') instruction = `Rzuć k20 przeciw ST ${p.dc}. Koszt zadeklarowany przed rzutem; obowiązuje także po niepowodzeniu.`;
  else if (p.phase === 'impact') instruction = `Udany test. Rzuć k${p.impact_die} na wpływ; zmniejszymy wspólny opór o wynik wraz z premiami.`;
  else if (p.phase === 'reaction') instruction = `${p.reaction}. Presja: ${p.pressure} spalonych kart. Reakcja usuwająca kartę dotyczy największego ładunku; odzysk oporu to automatyczny rzut k4. Zatwierdź reakcję.`;
  else instruction = 'Sprawdź rozstrzygnięcie i przejdź dalej.';
  if (p.mission_ui) {
    if(p.phase==='setup') instruction=p.mission_ui.setup_confrontation.replace('{copies}',p.mana.copies).replace('{party}',`(${p.setup.position})`).replace('{target}',`(${p.scene.position})`);
    if(p.phase==='result') instruction=p.result+' '+p.mission_ui.mission_result;
    if(p.phase==='turn' && p.board_choices.some(c=>c.action==='compromise')) instruction+=' '+p.mission_ui.compromise;
  }
  const roll = p.attempt?.phase === 'roll';
  const cardOption = p.mana.phase === 'choose' && !p.needs_resume ? `<div class="confrontation-offer">${p.mana.offer.map(c=>`<article class="mana-value mana-${c}">${manaCostHtml([c])}<b>${own.values[c]} pkt</b><p>${esc(partyConfrontationPassive(p,c))}</p></article>`).join('')}</div>` : '';
  panel.innerHTML = `<div class="training-heading"><div><small>KONFRONTACJA DRUŻYNOWA · ${p.scene.kind==='npc'?'ROZMOWA':'OBIEKT'}</small><h2>${esc(p.scene.name)}</h2></div><b>Runda ${p.round} · ${esc(p.actor_name)}</b></div>
    <p>${esc(p.scene.goal)}</p><p>${esc(p.scene.description)}</p>
    <div class="training-progress"><b>Opór: ${p.resistance}/${p.maximum}</b><progress max="${p.maximum}" value="${p.resistance}"></progress><span>Talia: ${p.mana.deck} · spalone: ${p.mana.burned}</span></div>
    <div class="confrontation-party">${p.party.map(h=>`<article class="${h.id===p.actor?'current':''}"><b>${esc(h.name)} · ${h.points} pkt</b><small>${esc(h.method)} · ST ${h.dc} · wpływ k${h.die}</small><small>${esc(h.ability)} · test ${h.test_modifier>=0?'+':''}${h.test_modifier} · wpływ ${h.influence_modifier>=0?'+':''}${h.influence_modifier}</small><p>${manaCostHtml(h.cards)}${h.aid?` · Pomoc +${h.aid}`:''}</p><ul>${h.passives.map(x=>`<li>${manaCostHtml([x.color])} ×${x.count} ${esc(x.label)}</li>`).join('')}</ul></article>`).join('')}</div>
    ${p.last?`<p class="confrontation-result" aria-live="polite">${esc(p.last)}</p>`:''}
    ${p.obligation?'<p class="mana-obligation">Zobowiązanie: dostarcz list. Pozostaje także po porażce.</p>':''}
    ${trainingCommandHtml(instruction)}${cardOption}
    ${roll?`<form id="exploration-mana-roll" onsubmit="submitExplorationManaRoll(event)"><label>${p.die_kind==='test'?'Test k20':`Wpływ k${p.attempt.die}`}<input id="confrontation-${p.die_kind}-roll" aria-label="Naturalny wynik kości" data-roll-dice="1k${p.attempt.die}" data-roll-source="${esc(p.actor_name)}" type="number" min="1" max="${p.attempt.die}" required></label><button type="submit">✓ Rozstrzygnij</button></form>`:`<div class="mana-decisions">${buttons}</div>`}
    <details><summary>${p.mission_ui?'Zasady konfrontacji':'Zasady i cel ćwiczenia'}</summary><p>${esc(p.reminder)}</p><p>${esc(p.lesson.objective)}</p></details>
    ${confrontationChoice(p,p.board_choices.find(c=>c.action==='leave'))}`;
}
function partyConfrontationPassive(p,color) {
  return p.color_passives?.[color] || 'Pasyw koloru uruchomi się po doborze.';
}
