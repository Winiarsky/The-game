/* Physical cards stay at the table. This view contains no hand or payment ledger. */
const manaSymbols = {C:'czerwona',N:'niebieska',Z:'zielona',B:'biała',F:'czarna','*':'dowolna'};
const manaPaths = {
  C:'M12 2C14 8 20 8 20 15a8 8 0 0 1-16 0c0-3 2-6 5-8-1 5 2 6 3 4 2-3 1-6 0-9Z',
  N:'M12 2C10 6 5 11 5 15a7 7 0 0 0 14 0c0-4-5-9-7-13ZM8 15c0 2 1 3 3 3',
  Z:'M9 22h6M10 22v-7H6a3 3 0 0 1-1-6 4 4 0 0 1 4-6 4 4 0 0 1 7 1 4 4 0 0 1 4 5 3 3 0 0 1-2 6h-4v7M10 16l-2-3M14 17l3-4',
  B:'M16 12a4 4 0 1 0-8 0 4 4 0 1 0 8 0M12 1v4M12 19v4M1 12h4M19 12h4M4 4l3 3M17 17l3 3M4 20l3-3M17 7l3-3',
  F:'M8 21v-4C2 16 2 3 12 3s10 13 4 14v4ZM9 21v-3M12 21v-3M15 21v-3M9 11a1.5 1.5 0 1 0-3 0 1.5 1.5 0 1 0 3 0M18 11a1.5 1.5 0 1 0-3 0 1.5 1.5 0 1 0 3 0M11 15l1-2 1 2Z',
  '*':'M22 12a10 10 0 1 0-20 0 10 10 0 1 0 20 0M9 9l3-3v12M9 18h6',
};
function manaCostHtml(cost) {
  return (cost || []).map(color => `<span class="mana-chip mana-${color === '*' ? 'any' : color}" role="img" aria-label="1 mana ${manaSymbols[color] || color}" title="1 mana ${manaSymbols[color] || color}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="${manaPaths[color] || manaPaths['*']}"/></svg></span>`).join('<span class="mana-plus" aria-hidden="true">+</span>');
}
function manaPassiveSymbolHtml(color, stackable) {
  return `<span class="mana-passive-symbol" data-stackable="${!!stackable}" title="${stackable ? 'Kumuluje się' : 'Nie kumuluje się'}">${manaCostHtml([color])}</span>`;
}
function manaPassiveRuleHtml(text) {
  const source = String(text || '');
  let html = '', offset = 0;
  for (const match of source.matchAll(/k20|[+−]?\d+(?:k\d+)?(?:\s*(?:PW|KP|ft))?|✓/g)) {
    html += esc(source.slice(offset, match.index)) + `<strong>${esc(match[0])}</strong>`;
    offset = match.index + match[0].length;
  }
  return html + esc(source.slice(offset));
}
function manaPassiveDescriptionHtml(passive, compact = false) {
  const d = passive?.display;
  if (!d) return `<p>${esc(passive?.label || '')}</p>`;
  const details = [d.note, d.stacking].filter(Boolean).map(t=>`<p>${esc(t)}</p>`).join('');
  return `<div class="mana-passive-description"><strong class="passive-name">${esc(d.name)}</strong>
    <p class="passive-trigger">${esc(d.when)}</p><p class="passive-effect">${manaPassiveRuleHtml(d.effect)}</p>
    ${d.instruction ? `<p class="passive-instruction">${esc(d.instruction)}</p>` : ''}
    ${details ? compact ? `<details><summary>Szczegóły i kumulacja</summary>${details}</details>` : `<div class="passive-details">${details}</div>` : ''}</div>`;
}
function manaPointCardsHtml(cards, values) {
  return (cards || []).map(color => `<span class="mana-valued-card">${manaCostHtml([color])}<b>${values[color]===2?'Atut · 2 ładunku':'1 ładunku'}</b></span>`).join(' ');
}
function pooledManaPointsHtml(combat, actorId, compact = false) {
  const pool = combat.shared_mana?.pool_view;
  if (!pool) return '';
  const hand = pool.hands.find(h => h.hero === (actorId || combat.current_actor?.id || pool.actor));
  if (!hand) return '';
  return `<section class="mana-points" aria-label="Karty many i ładunek">
    <div class="mana-points-total"><span>${esc(hand.name)} · mana z kart</span><strong>${hand.cards.length}/6 kart</strong><small>${hand.cards.length >= 6 ? "Pełna pula · bez doboru" : "Dobór na początku swojej tury"}</small></div>
    <div class="mana-charge-statuses">${Object.entries(hand.color_passives || {}).filter(([c]) => !['setup','drain'].includes(pool.phase) && hand.cards.includes(c)).map(([c,p]) => `<details class="effect-chip"><summary>${manaPassiveSymbolHtml(c, p.stackable)} ${p.stackable ? `×${hand.cards.filter(x=>x===c).length}` : ''} · ${esc(p.label.split(':')[0])} · ${esc(p.status || 'Aktywne')}</summary>${manaPassiveDescriptionHtml(p)}</details>`).join('')}</div>
    ${pool.phase === 'drain' ? '<p>Mana drain — pasywy nieaktywne. Tasowanie odnowi ich użycia.</p>' : ''}
    <small>Obwódka symbolu: gruba — kumuluje się; cienka — nie kumuluje się.</small>
    ${hand.legacy_overflow?'<p>Starszy zapis zawiera ponad 6 kart. Zachowaj stosy do draina; nie dobieraj. Premia do testów: maks. +6.</p>':''}
    <p class="mana-points-summary"><b>Testy +${hand.roll_bonus || 0} · Ładunek ${hand.total}/6</b></p>
    ${compact ? '' : `<div class="mana-points-cards">${hand.cards.length ? manaPointCardsHtml(hand.cards, hand.values) : 'Pula jest pusta.'}</div>
    <div class="mana-points-values"><p>Atut: ${manaCostHtml([hand.trump_color])} liczy się jako 2 do progów 2/4/6. Pozostałe karty jako 1. Do testów każda karta daje +1.</p></div>`}
  </section>`;
}
function actionManaCostHtml(option) {
  if (!Array.isArray(option.mana_cost)) return '';
  const icons = manaCostHtml(option.mana_cost);
  const note = option.mana_cost_note || (icons ? '' : 'bez many');
  return `<span class="combat-action-mana" aria-label="Koszt many"><span class="combat-action-mana-symbols">${icons}</span>${note ? `<small>${esc(note)}</small>` : ''}</span>`;
}
function combatActionTileLabel(option) {
  return option.action === 'move' && Array.isArray(option.mana_cost) ? 'Ruch' : option.label;
}
function manaTextHtml(text) {
  const colors = {czerwona:'C',niebieska:'N',zielona:'Z',biała:'B',czarna:'F',dowolna:'*'};
  const pattern = /(\d+) dowoln(?:a|ą|e|ej|ych) man(?:a|ę|y|ie|ach)?|\b(czerwona|niebieska|zielona|biała|czarna|dowolna)\b/gi;
  const source = String(text || '');
  let result = '', offset = 0;
  for (const match of source.matchAll(pattern)) {
    result += esc(source.slice(offset, match.index));
    result += match[1] ? `${match[1]} × ${manaCostHtml(['*'])}` : manaCostHtml([colors[match[2].toLowerCase()]]);
    offset = match.index + match[0].length;
  }
  return (result + esc(source.slice(offset))).replace(/\(([CNZBF*])\)/g, (_, color) => manaCostHtml([color]));
}
function manaWaveLabel(wave) {
  // Older saves can still contain the former display name.
  return String(wave.label || '').replace('Fioletowe zakłócenie', 'Czarne zakłócenie');
}
function physicalManaHtml(combat) {
  if (combat.shared_mana) return sharedManaHtml(combat);
  const mana = combat.physical_mana;
  if (!mana) return '';
  const supply = mana.supply;
  const active = mana.active_hero;
  const series = mana.series || {};
  return `<section class="physical-mana" aria-label="Fizyczna mana">
    <div class="mana-summary"><b>Mana na stole</b><span>${active ? `Koniec tury: zachowaj do <b>${supply.keep}</b> starych + dobierz do <b>${supply.draw}</b> · pojemność <b>${supply.capacity}</b>` : mana.weapon_control ? 'Aktywacja duchowej broni jest opłacona. Dobór nastąpi po turze Dagny.' : 'Trwa tura przeciwnika. Karty na reakcje wydajecie fizycznie.'}</span><span>Zagrożenie: <b>${mana.threat}/3</b></span></div>
    ${active && mana.actor_id === 'garran' && mana.movement ? `<p class="mana-movement${mana.movement.steadfast && !mana.movement.started ? ' mana-flaw-active' : ''}" role="status"><b>${manaTextHtml(mana.movement.label)}</b><br>${manaTextHtml(mana.movement.description)}</p>` : ''}
    ${active && series.declared ? `<p class="mana-series">Seria ${series.declared} ataków · rozstrzygnięto ${series.used} · pozostało ${Math.max(0, series.declared-series.used)}. Kolejny cel wybierz po wyniku poprzedniego ataku.</p>` : ''}
    ${active ? `<details><summary>Pasyw many i skaza · ${esc(mana.actor_name)}</summary><p>${manaTextHtml(mana.mana_passive)}</p><p><b>Skaza:</b> ${manaTextHtml(mana.flaw)} Limity oznaczajcie przy stole.</p></details>` : ''}
    ${(mana.waves || []).map(w => `<p class="mana-wave"><b>${esc(manaWaveLabel(w))}</b>: ${esc((mana.wave_rules.find(r => `mana_wave_${r.number}` === w.kind) || {}).description || '')}</p>`).join('')}
    ${(mana.pending_waves || []).map(w => `<p role="status">${esc(manaWaveLabel(w))} — oczekuje na koniec rundy.</p>`).join('')}
    ${mana.weapon_available ? `<button onclick="api('/api/combat/mana-weapon', {}, 'Aktywuję duchową broń...')">Aktywuj duchową broń · D · ${manaCostHtml(['B'])}</button>` : ''}
    ${mana.weapon_control ? '<p><b>Aktywacja duchowej broni:</b> ruch do 20 ft i jeden atak w cenie. Zakończ aktywację, aby wrócić do Dagny.</p>' : ''}
    ${mana.loan_available ? `<button class="secondary" onclick="api('/api/combat/mana-loan', {}, 'Lorian przekazuje kartę...')">Awaryjna pożyczka Loriana · R · ${manaCostHtml(['B'])} + przekazana karta</button>` : ''}
    <details><summary>Zasady many, zdolności i zgłoszenie fali</summary><p class="mana-legend">${Object.entries(manaSymbols).map(([key,label]) => `${manaCostHtml([key])} ${label}`).join(" · ")}</p>
      <p><a href="/rules/physical-mana" target="_blank" rel="noopener">Otwórz instrukcję i pełne talie do wydruku</a></p>
      <p><b>Przygotowanie:</b> ${mana.setup.deck} kart, po ${mana.setup.deck/5} każdego koloru. Rynek: ${mana.setup.market}. Start: po 3 karty, wybierane po jednej w kolejności inicjatywy; uzupełniaj rynek po wyborze.</p>
      <p><b>Tura:</b> 1 akcja główna, 1 dodatkowa, ruch i 1 reakcja. Zwykły Atak: jedno uderzenie za 1 dowolną manę. Tylko Lorian wybiera liczbę zwykłych ataków, płacąc po 1 dowolnej za każdy. Ruch: bazowo 1 dowolna raz na turę; Nieustępliwość Garrana: 2 przy rozpoczęciu obok wroga. Inne podstawowe działania i atak okazyjny: 1 dowolna. Pas, anulowanie podglądu i rzuty ratunkowe: bez many.</p>
      <p><b>Na końcu tury:</b> rozlicz skazę, odrzuć nadmiar starej rezerwy, wybierz do 3 kart z rynku, potem uzupełnij rynek. Na początku tury nie dobierasz. Nieprzytomny/obezwładniony nie dobiera. Na końcu rundy odrzuć skrajną lewą kartę rynku i uzupełnij.</p>
      <p><b>Zamienniki:</b> 2 dowolne zastępują 1 kolor. Raz we własnej turze przeciąż jedną własną kartę: wydaj ją jako dowolny kolor i odrzuć 2 karty z góry talii (3 podczas Czarnego zakłócenia). Karty i znaczniki limitów obsługujecie przy stole.</p>
      <p>Koszt techniki zawiera jej ataki i ruch. Nie dodawaj kosztu zwykłego ataku. Pudło nie zwraca many. Niewykorzystane ataki zadeklarowanej serii przepadają. Aplikacja sprawdza czas, cel i skutki; nie sprawdza fizycznej płatności.</p>
      ${active ? `<details><summary>Pełna talia · ${esc(mana.actor_name)}</summary><p class="mana-hero-notes">${esc(mana.hero_notes)}</p><div class="mana-ability-list">${mana.abilities.map(a => `<article><b>${esc(a.name)}</b> <small>${esc(a.timing)}</small>${a.sections ? a.sections.map(([label,text])=>`<p><b>${esc(label)}:</b> ${manaTextHtml(text)}</p>`).join('') : `<div>${manaCostHtml(a.cost)}</div><p>${esc(a.description)}</p>`}</article>`).join('')}</div></details>` : ''}
      <div class="mana-wave-report"><p><b>Przewinięto talię?</b> Zgłoś numer zapowiedzianego wydarzenia. Fala zadziała na końcu rundy; rzucicie k6 na następną zapowiedź. Zagrożenie rośnie do 3.</p>
      <form onsubmit="event.preventDefault(); reportManaWave(this)"><label>Zapowiedziane wydarzenie<select name="event">${mana.wave_rules.map(w => `<option value="${w.number}">${w.number}. ${esc(w.name)}</option>`).join('')}</select></label><button type="submit">Zgłoś jedną falę</button></form></div>
      ${active && mana.waves.some(w => w.kind === 'mana_wave_2') && mana.movement?.steadfast ? '<p>Nieustępliwość: ruch za niebieską + 1 dowolną pozwala ominąć Ciężkie powietrze.</p>' : ''}
      ${active && mana.waves.some(w => w.kind === 'mana_wave_2') ? '<button onclick="api(\'/api/combat/mana-blue-movement\', {}, \'Wybieram ruch za niebieską manę...\')">Ruch opłacony niebieską maną · pomiń Ciężkie powietrze</button>' : ''}
    </details>
  </section>`;
}
function physicalAttackSeriesHtml(combat) {
  if (!combat.physical_mana?.needs_attack_count || combat.physical_mana.actor_id !== 'lorian') return '';
  return `<form class="mana-attack-declaration" onsubmit="event.preventDefault(); declareManaAttackSeries()"><b>Ile ataków wykonujesz?</b><p>Lorian: cała seria zajmuje jedną akcję główną. Wydaj po jednej dowolnej manie za każdy atak. Każdy ma osobny cel, test trafienia i obrażenia.</p><label>Liczba ataków<input id="mana-attack-count" type="number" min="1" step="1" value="1" required inputmode="numeric"></label><button type="submit">Rozpocznij serię · ✓</button><button type="button" class="secondary" onclick="cancelCombatTurnActionPreview()">Anuluj · ↩</button></form>`;
}
function declareManaAttackSeries() {
  const input = document.getElementById('mana-attack-count');
  if (!input || !input.reportValidity()) return false;
  const count = Number(input.value);
  if (!Number.isSafeInteger(count) || count < 1) return false;
  api('/api/combat/attack-series', {count}, 'Deklaruję serię ataków...');
  return true;
}
function reportManaWave(form) {
  api('/api/combat/mana-wave', {event: Number(new FormData(form).get('event'))}, 'Zgłaszam falę na koniec rundy...');
}
function physicalDamageBonusChoicesHtml(pending) {
  if (!state.combat?.physical_mana?.active_hero) return '';
  const choices = [];
  if (pending.sneak_attack) choices.push(['sneak_attack', 'Atak z cienia']);
  if (pending.first_blood) choices.push(['first_blood', 'Pierwsza krew']);
  for (const component of pending.source?.damage_components || []) {
    if (['hunters_mark','mana_double_shot'].includes(component.id)) choices.push([component.id, component.label]);
  }
  return choices.length ? `<details><summary>Premie raz na turę · wybierz przed rzutem obrażeń</summary><p>Widoczne premie zostaną doliczone do tego trafienia. Możesz zachować wybraną na późniejsze trafienie.</p>${choices.map(([id,name]) => `<button class="secondary" onclick="api('/api/combat/mana-damage-bonus/skip', {bonus_id:'${id}'}, 'Zachowuję premię...')">Zachowaj: ${esc(name)}</button>`).join('')}</details>` : '';
}
