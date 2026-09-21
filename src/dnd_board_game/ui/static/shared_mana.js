function sharedManaCommand(command, extra = {}) {
  const mana = state?.combat?.shared_mana;
  if (!mana || busy) return false;
  return api('/api/combat/shared-mana', {command, revision: mana.revision, ...extra},
    ['target', 'clear_targets'].includes(command) ? 'Aktualizuję wybór celów…' : 'Rozliczam karty…');
}

function sharedManaPrimary() {
  const mana = state?.combat?.shared_mana;
  if (!mana) return false;
  if (mana.command?.stage) {
    if (mana.command.can_confirm) sharedCommandControl();
    return true;
  }
  if (mana.pool_view?.choices?.some(c => c.slot === 28)) {
    const choice = mana.pool_view.choices.find(c => c.slot === 28);
    sharedManaCommand(choice.command);
    return true;
  }
  const declaration = mana.declaration;
  const command = declaration ? (declaration.stage === 'cards' ? 'cards_done' : declaration.stage === 'effect_roll' ? 'effect' : declaration.stage === 'bonus' ? 'bonus' : 'pay') :
    {end_turn: 'refill', discard: 'discard', refresh: 'refresh_done'}[mana.phase];
  if (!command) return false;
  if (declaration?.target_selection && !declaration.target_selection.can_confirm) return true;
  if (declaration?.error && declaration.stage !== 'cards') return true;
  sharedManaCommand(command);
  return true;
}

function sharedManaDelta(delta) {
  const declaration = state?.combat?.shared_mana?.declaration;
  if (['effect_roll', 'bonus'].includes(declaration?.stage) && declaration.roll_sides) {
    const value = Math.max(1, Math.min(declaration.roll_sides, (declaration.roll || 1) + delta));
    sharedManaCommand('parameters', {natural_roll: value});
    return true;
  }
  return false;
}

function sharedManaBoostOption(slot) {
  return sharedManaCommand('boost_option', {slot});
}

function sharedManaBoostEffect(option) {
  const dice = option.effect.match(/^(\+?)(\d+)k(\d+)(.*)$/);
  if (dice) return `${dice[1]}${Number(dice[2]) * option.amount}k${dice[3]}${dice[4]}`;
  return option.amount > 1 ? `${option.amount} × (${option.effect})` : option.effect;
}

function sharedManaBoostsHtml(declaration) {
  if (declaration.stage !== 'payment' || !declaration.boost_options?.length) return '';
  return `<section class="mana-boosts" aria-label="Podbicia"><h4>Opcjonalne podbicia</h4>
    <p>Wybierz runę na planszy lub przycisk poniżej. Ponowne wybranie wyłącza wariant. Różne podbicia można łączyć w granicach kosztu.</p>
    <div class="mana-boost-options">${declaration.boost_options.map(option => `
      <button type="button" class="mana-boost-option ${option.selected ? 'selected' : ''}"
        aria-pressed="${option.selected}" ${option.enabled ? '' : 'disabled'}
        onclick="sharedManaBoostOption(${option.slot})">
        <span class="mana-boost-rune">${option.icon}</span>
        <span><b>Runa ${esc(option.rune_name)}</b><span class="mana-boost-cost">Wydaj dodatkowo ${manaCostHtml(option.cost)}</span>
        <span>${esc(sharedManaBoostEffect(option))}${declaration.ability_id === 'shield_bash' ? ' przy wygranym teście' : ''}</span>
        <small>${option.selected ? '✓ Wybrano · naciśnij ponownie, aby wyłączyć' : option.enabled ? 'Wybierz ten wariant' : esc(option.unavailable_reason)}</small></span>
      </button>`).join('')}</div></section>`;
}

function sharedManaPanel() {
  const mana = state?.combat?.shared_mana;
  if (mana?.pool_view?.choices?.length) return null;
  if (!mana || (!mana.declaration && !['end_turn', 'discard', 'refresh'].includes(mana.phase))) return null;
  const declaration = mana.declaration;
  if (declaration?.stage === 'payment' || declaration?.target_selection) return null; // Server owns targets, payment runes and controls.
  const slots = [28];
  if (["effect_roll", "bonus"].includes(declaration?.stage) && declaration.roll_sides) {
    if ((declaration.roll || 1) > 1) slots.push(26);
    if ((declaration.roll || 1) < declaration.roll_sides) slots.push(27);
  }
  return {context: `mana:${mana.revision}:${mana.phase}`, slots, exclusive: true};
}

function sharedManaTargetsHtml(declaration) {
  const selection = declaration.target_selection;
  if (!selection) return '';
  const selected = selection.targets.filter(target => target.selected).map(target => target.name);
  return `<section class="mana-target-selection" aria-label="Wybór celów">
    <p class="mana-target-instruction"><b>Teraz wybierz na planszy</b>${esc(selection.instruction)}</p>
    <p role="status"><b>Wybrano${selection.multiple ? ` ${selected.length}/${selection.maximum}` : ''}:</b> ${selected.length ? selected.map(esc).join(', ') : 'jeszcze nikogo'}</p>
    ${selection.applied_targets.length ? `<p>Efekt otrzymali: ${selection.applied_targets.map(target => esc(target.name)).join(', ')}.</p>` : ''}
    ${selection.targets.length ? '' : '<p role="alert">Brak legalnych celów w zasięgu.</p>'}
    <details><summary>Awaryjny wybór ekranowy</summary><div class="mana-target-options">
      ${selection.targets.map(target => `<button type="button" aria-pressed="${target.selected}"
        class="mana-target-option ${target.selected ? 'selected' : ''}"
        onclick="sharedManaCommand('target', {target_id: '${esc(target.id)}'})">${target.selected ? '✓ ' : ''}${esc(target.name)}</button>`).join('')}
    </div></details>
    ${declaration.stage !== 'payment' && selected.length ? '<button class="secondary" onclick="sharedManaCommand(\'clear_targets\')">↩ Wyczyść wybór</button>' : ''}
  </section>`;
}

function sharedCommandStepHtml(combat) {
  const command = combat.shared_mana?.command;
  if (!command?.stage) return '';
  const movement = command.stage === 'movement';
  return `<section class="combat-prompt shared-command-step" role="status">
    <small>Rozkaz: Kontratak! · ${command.step}/${command.total}</small>
    <b>Teraz działa: ${esc(command.actor_name)}</b>
    <div class="${movement ? 'shared-command-movement' : 'shared-command-attack'}">
      <strong>${movement ? command.movement_icon : command.attack_icon} ${movement ? 'Ruch — opcjonalnie' : command.stage === 'no_target' ? 'Brak celu ataku' : 'Atak bronią'}</strong>
      <span>${esc(command.instruction)}</span>
    </div>
    <small>Koszt jest już opłacony. ${esc(command.next_instruction)}</small>
  </section>`;
}

function sharedCommandControl(back = false) {
  if (busy) return false;
  return api('/api/combat/command', {revision: state.board_selection.revision, back}, '');
}

function sharedCommandControlsHtml(combat) {
  const command = combat.shared_mana.command;
  return `<div class="row">
    ${command.can_confirm ? `<button onclick="sharedCommandControl()">✓ ${command.stage === 'movement' ? 'Zakończ ruch — przejdź do ataku' : command.stage === 'no_target' ? 'Dalej bez ataku' : 'Potwierdź cel'}</button>` : ''}
    ${command.can_back ? '<button class="secondary" onclick="sharedCommandControl(true)">↩ Zmień wybór</button>' : ''}
  </div>`;
}

function manaDeckPreparationHtml(pool) {
  const preparation = pool.deck_preparation;
  if (!preparation) return '';
  const t = (key, params={}) => esc(sessionUiText(`combat.${key}`, params));
  const counts = values => Object.entries(values).map(([color, count]) => `<span>${manaCostHtml([color])}<b>× ${Number(count)}</b></span>`).join('');
  return `<section class="mana-deck-preparation" role="alert">
    <h3>${t('deck_ethos_title',{stance:preparation.label,steps:preparation.steps})}</h3>
    <p>${t('deck_ethos_remove')}</p><div class="mana-deck-counts">${counts(preparation.removed)}</div>
    <p>${t('deck_ethos_keep',{total:preparation.total})}</p><div class="mana-deck-counts">${counts(preparation.composition)}</div>
    <p>${t('deck_ethos_confirm')}</p></section>`;
}

function sharedManaHtml(combat) {
  const mana = combat.shared_mana;
  if (!mana) return '';
  const declaration = mana.declaration;
  let decision = '';
  if (mana.pool_view?.choices?.length) {
    const pool = mana.pool_view;
    const hand = pool.hands.find(h => h.hero === pool.actor);
    decision = `<h3>${pool.phase === 'drain' ? 'Mana drain' : pool.phase === 'bard' ? 'Manipulacja many' : 'Pula many'}</h3>
      ${manaDeckPreparationHtml(pool) || `<p>${esc(pool.instruction)}</p>`}<div class="mana-boost-options">${pool.choices.map(c => {
        const button = `<button onclick="sharedManaCommand('${c.command}', {${c.index !== undefined ? `index: ${c.index}` : c.color ? `color: '${c.color}'` : ''}})">${c.icon} ${esc(c.rune)} · ${esc(c.label)}${pool.phase === 'choose' && hand ? ` · ${hand.values[c.color]===2?'Atut':'Mana'} → ${Math.min(6,hand.total + hand.values[c.color])}/6 ładunku · +1 do testów` : ''}</button>`;
        return pool.phase === 'choose' && hand ? `<article class="mana-choice-option">${button}${manaPassiveDescriptionHtml(hand.color_passives?.[c.color],true)}</article>` : button;
      }).join('')}</div>`;
  } else if (declaration) {
    const cards = declaration.stage === 'cards';
    decision = `<h3>${esc(declaration.name)}</h3>${declaration.sections ? declaration.sections.map(([label,text])=>`<p><b>${esc(label)}:</b> ${manaTextHtml(text)}</p>`).join('') : `<p>${manaTextHtml(declaration.description)}</p>`}${declaration.context&&declaration.sections?`<p>${esc(declaration.context)}</p>`:''}
      ${cards ? '<p>Wykonaj fizyczną operację na kartach, a potem naciśnij ✓.</p>' : `
      ${sharedManaTargetsHtml(declaration)}
      ${declaration.roll_sides && ['effect_roll', 'bonus'].includes(declaration.stage) ? `<label>${esc(declaration.roll_label || `Naturalny k${declaration.roll_sides}`)}<input type="number" min="1" max="${declaration.roll_sides}" value="${declaration.roll || ''}" onchange="sharedManaCommand('parameters', {natural_roll: Number(this.value)})"></label>` : ''}
      ${declaration.substitution_available ? `<label><input type="checkbox" ${declaration.substitution ? 'checked' : ''} onchange="sharedManaCommand('substitution', {enabled: this.checked})">${esc(declaration.substitution_label)}</label>` : ''}
      <p><b>${mana.pool_view ? 'Spalanie po akcji:' : 'Cały koszt:'}</b> ${manaCostHtml(declaration.cost)}${mana.pool_view ? '' : '. Wybierz fizyczne kolory za symbole dowolne.'}</p>
      ${declaration.reminders.map(text => `<p class="mana-flaw-active" role="status">${manaTextHtml(text)}</p>`).join('')}
      ${sharedManaBoostsHtml(declaration)}
      ${declaration.extra_targets ? `<p>Dodatkowe cele: najwyżej ${declaration.extra_target_maximum}</p><div>${declaration.extra_targets.map(t => `<button class="${declaration.extra_target_ids.includes(t.id) ? 'panel-accept' : 'secondary'}" onclick="sharedManaCommand('extra_target', {target_id: '${esc(t.id)}'})">${esc(t.name)}</button>`).join('')}</div>` : ''}
      ${declaration.exclusion_fields ? `<p>Wyłącz do dwóch pól (przed opłaceniem):</p><div>${declaration.exclusion_fields.map(p => `<button class="${declaration.excluded_positions.some(e => e[0] === p[0] && e[1] === p[1]) ? 'panel-accept' : 'secondary'}" onclick="sharedManaCommand('exclude', {position: [${p[0]},${p[1]}]})">(${p.join(',')})</button>`).join('')}</div>` : ''}
      <p>${['effect_roll', 'bonus'].includes(declaration.stage) ? (declaration.roll_sides ? 'Użycie jest już zatwierdzone. Rzuć kością efektu, ustaw wynik przyciskami − / + i zatwierdź ✓.' : 'Użycie jest już zatwierdzone. Wybierz podświetlonych sojuszników i zatwierdź ✓. Ten efekt nie wymaga rzutu.') : (mana.pool_view ? 'Zachowaj osobistą pulę. ✓ zatwierdza zdolność i koszt; karty z wierzchu spalisz po jej efekcie.' : 'Odłóż koszt z rynku na stos odrzuconych. ✓ potwierdza płatność przed rozstrzygnięciem zdolności.')}</p>
      ${declaration.error ? `<p role="alert">${esc(declaration.error)}</p>` : ''}`}
      <button class="panel-accept" onclick="sharedManaPrimary()" ${!cards && (declaration.error || (declaration.target_selection && !declaration.target_selection.can_confirm)) ? 'disabled' : ''}>✓ ${cards ? 'Karty ułożone' : ['effect_roll', 'bonus'].includes(declaration.stage) ? 'Zastosuj efekt' : (mana.pool_view ? 'Zatwierdź użycie' : 'Koszt odłożony — wykonaj')}</button>
      ${declaration.stage === 'payment' ? '<button class="secondary" onclick="sharedManaCommand(\'cancel\')">↩ Wróć bez płatności</button>' : ''}`;
  } else if (mana.phase === 'end_turn') {
    decision = `<h3>Koniec tury — uzupełnienie rynku</h3><p>Dobierz <b>${mana.refill_count}</b> kart z talii na puste miejsca rynku.${mana.turn_actor === 'erynd' ? ' Przed doborem możesz obejrzeć do dwóch wierzchnich kart i ustawić ich kolejność.' : ''}</p><button class="panel-accept" onclick="sharedManaPrimary()">✓ Rynek uzupełniony</button>`;
  } else if (mana.phase === 'discard') {
    decision = '<h3>Tura bez wydania many</h3><p>Talia została wyczerpana. Odrzuć jedną wybraną kartę rynku; nie dobieraj w jej miejsce.</p><button class="panel-accept" onclick="sharedManaPrimary()">✓ Karta odrzucona</button>';
  } else if (mana.phase === 'refresh') {
    decision = '<h3>Odświeżenie talii</h3><p>Zbierz i przetasuj wszystkie 25 kart, również pozostałe karty rynku. Wyłóż nowy rynek pięciu kart. Potwierdzenie zakończy efekty O.</p><button class="panel-accept" onclick="sharedManaPrimary()">✓ Nowa talia i rynek gotowe</button>';
  }
  if (mana.pool_view) {
    const pool = mana.pool_view;
    const owner = pool.hands.find(h => h.hero === pool.actor);
    const handHtml = h => `<p><b>${esc(h.name)}: ${h.cards.length}/6 kart · ładunek ${h.total}/6</b> · Naładowanie: +${h.roll_bonus ?? 0} do testów · ${manaPointCardsHtml(h.cards, h.values)}</p>`;
    return `<section class="physical-mana" aria-label="Osobiste pule many">
      <div class="mana-summary"><b>Osobiste pule many</b><span>Talia: ${pool.deck} · Spalone: ${pool.burned.length} · Wygasłe: ${(pool.expired || []).length} · Uwięzione: ${Object.values(pool.prisons).reduce((n,c)=>n+c.length,0)} · Komplet: ${pool.total}</span></div>
      <p>Odkryte: ${manaCostHtml(pool.offer)}</p>
      ${owner ? `${handHtml(owner)}<p>${Object.entries(owner.values).map(([c,v])=>`${manaCostHtml([c])}: ${v}`).join(' · ')}</p><details><summary>Pasyw i skaza</summary><p>${esc(owner.passive)}</p><p>${esc(owner.flaw)}</p></details>` : ''}
      <details><summary>Pule drużyny</summary>${pool.hands.map(handHtml).join('')}</details>
      ${combat.physical_mana?.weapon_available ? `<button onclick="api('/api/combat/mana-weapon', {}, 'Aktywuję duchowy oręż…')">Duchowy oręż · akcja dodatkowa, bez many</button>` : ''}
      <p>Zwykły atak zachowuje pulę. Ładunek pozostaje do mana draina. Zdolności spalają karty z wierzchu; podbicie kosztuje dodatkowe 2 karty.</p>
      ${decision ? `<div class="shared-mana-shade"><section class="shared-mana-decision" role="dialog" aria-modal="true">${pooledManaPointsHtml(combat, declaration?.actor_id || pool.actor)}${decision}</section></div>` : ''}
    </section>`;
  }
  return `<section class="physical-mana" aria-label="Wspólna mana"><div class="mana-summary"><b>Wspólna mana</b><span>Talia: ${mana.deck} · Rynek: ${mana.market}/5 · Odrzucone: ${mana.discard} · Cykl: ${mana.cycle}</span></div>
    ${combat.physical_mana?.weapon_available ? `<button onclick="api('/api/combat/mana-weapon', {}, 'Aktywuję duchowy oręż…')">Duchowy oręż · akcja dodatkowa + ${manaCostHtml(['B'])}</button>` : ''}
    <p>Zwykły atak i ruch bez many. Koszt zdolności odkładaj przed efektem; podbicia i skazy wliczaj do limitu 5 kart.</p>
    <button class="${mana.exhausted ? 'panel-accept' : 'secondary'}" onclick="sharedManaCommand('refresh')" ${!mana.refresh_available || declaration ? 'disabled' : ''}>⟳ Odśwież talię${mana.exhausted ? ' — talia wyczerpana' : ' / zgłoś rozbieżność'}</button>
    ${combat.physical_mana?.active_hero ? `<details><summary>Pasyw i skaza</summary><p>${esc(combat.physical_mana.mana_passive)}</p><p>${esc(combat.physical_mana.flaw)}</p></details>` : ''}
    ${decision ? `<div class="shared-mana-shade"><section class="shared-mana-decision" role="dialog" aria-modal="true" aria-label="Rozliczenie wspólnej many">${decision}</section></div>` : ''}
  </section>`;
}
