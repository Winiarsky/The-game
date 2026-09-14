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

function sharedManaHtml(combat) {
  const mana = combat.shared_mana;
  if (!mana) return '';
  const declaration = mana.declaration;
  let decision = '';
  if (declaration) {
    const cards = declaration.stage === 'cards';
    decision = `<h3>${esc(declaration.name)}</h3><p>${manaTextHtml(declaration.description)}</p>
      ${cards ? '<p>Wykonaj fizyczną operację na kartach, a potem naciśnij ✓.</p>' : `
      ${sharedManaTargetsHtml(declaration)}
      ${declaration.roll_sides && ['effect_roll', 'bonus'].includes(declaration.stage) ? `<label>${esc(declaration.roll_label || `Naturalny k${declaration.roll_sides}`)}<input type="number" min="1" max="${declaration.roll_sides}" value="${declaration.roll || ''}" onchange="sharedManaCommand('parameters', {natural_roll: Number(this.value)})"></label>` : ''}
      ${declaration.substitution_available ? `<label><input type="checkbox" ${declaration.substitution ? 'checked' : ''} onchange="sharedManaCommand('substitution', {enabled: this.checked})">${esc(declaration.substitution_label)}</label>` : ''}
      <p><b>Cały koszt:</b> ${manaCostHtml(declaration.cost)}. Wybierz fizyczne kolory za symbole dowolne.</p>
      ${declaration.reminders.map(text => `<p class="mana-flaw-active" role="status">${manaTextHtml(text)}</p>`).join('')}
      ${sharedManaBoostsHtml(declaration)}
      ${declaration.extra_targets ? `<p>Dodatkowe cele: najwyżej ${declaration.extra_target_maximum}</p><div>${declaration.extra_targets.map(t => `<button class="${declaration.extra_target_ids.includes(t.id) ? 'panel-accept' : 'secondary'}" onclick="sharedManaCommand('extra_target', {target_id: '${esc(t.id)}'})">${esc(t.name)}</button>`).join('')}</div>` : ''}
      ${declaration.exclusion_fields ? `<p>Wyłącz do dwóch pól (przed opłaceniem):</p><div>${declaration.exclusion_fields.map(p => `<button class="${declaration.excluded_positions.some(e => e[0] === p[0] && e[1] === p[1]) ? 'panel-accept' : 'secondary'}" onclick="sharedManaCommand('exclude', {position: [${p[0]},${p[1]}]})">(${p.join(',')})</button>`).join('')}</div>` : ''}
      <p>${['effect_roll', 'bonus'].includes(declaration.stage) ? (declaration.roll_sides ? 'Koszt jest już odłożony. Rzuć kością efektu, ustaw wynik przyciskami − / + i zatwierdź ✓.' : 'Koszt jest już odłożony. Wybierz podświetlonych sojuszników i zatwierdź ✓. Ten efekt nie wymaga rzutu.') : 'Odłóż koszt z rynku na stos odrzuconych. ✓ potwierdza płatność przed rozstrzygnięciem zdolności.'}</p>
      ${declaration.error ? `<p role="alert">${esc(declaration.error)}</p>` : ''}`}
      <button class="panel-accept" onclick="sharedManaPrimary()" ${!cards && (declaration.error || (declaration.target_selection && !declaration.target_selection.can_confirm)) ? 'disabled' : ''}>✓ ${cards ? 'Karty ułożone' : ['effect_roll', 'bonus'].includes(declaration.stage) ? 'Zastosuj efekt' : 'Koszt odłożony — wykonaj'}</button>
      ${declaration.stage === 'payment' ? '<button class="secondary" onclick="sharedManaCommand(\'cancel\')">↩ Wróć bez płatności</button>' : ''}`;
  } else if (mana.phase === 'end_turn') {
    decision = `<h3>Koniec tury — uzupełnienie rynku</h3><p>Dobierz <b>${mana.refill_count}</b> kart z talii na puste miejsca rynku.${mana.turn_actor === 'erynd' ? ' Przed doborem możesz obejrzeć do dwóch wierzchnich kart i ustawić ich kolejność.' : ''}</p><button class="panel-accept" onclick="sharedManaPrimary()">✓ Rynek uzupełniony</button>`;
  } else if (mana.phase === 'discard') {
    decision = '<h3>Tura bez wydania many</h3><p>Talia została wyczerpana. Odrzuć jedną wybraną kartę rynku; nie dobieraj w jej miejsce.</p><button class="panel-accept" onclick="sharedManaPrimary()">✓ Karta odrzucona</button>';
  } else if (mana.phase === 'refresh') {
    decision = '<h3>Odświeżenie talii</h3><p>Zbierz i przetasuj wszystkie 25 kart, również pozostałe karty rynku. Wyłóż nowy rynek pięciu kart. Potwierdzenie zakończy efekty O.</p><button class="panel-accept" onclick="sharedManaPrimary()">✓ Nowa talia i rynek gotowe</button>';
  }
  return `<section class="physical-mana" aria-label="Wspólna mana"><div class="mana-summary"><b>Wspólna mana</b><span>Talia: ${mana.deck} · Rynek: ${mana.market}/5 · Odrzucone: ${mana.discard} · Cykl: ${mana.cycle}</span></div>
    ${combat.physical_mana?.weapon_available ? `<button onclick="api('/api/combat/mana-weapon', {}, 'Aktywuję duchowy oręż…')">Duchowy oręż · akcja dodatkowa + ${manaCostHtml(['B'])}</button>` : ''}
    <p>Zwykły atak i ruch bez many. Koszt zdolności odkładaj przed efektem; podbicia i skazy wliczaj do limitu 5 kart.</p>
    <button class="${mana.exhausted ? 'panel-accept' : 'secondary'}" onclick="sharedManaCommand('refresh')" ${!mana.refresh_available || declaration ? 'disabled' : ''}>⟳ Odśwież talię${mana.exhausted ? ' — talia wyczerpana' : ' / zgłoś rozbieżność'}</button>
    ${combat.physical_mana?.active_hero ? `<details><summary>Pasyw i skaza</summary><p>${esc(combat.physical_mana.mana_passive)}</p><p>${esc(combat.physical_mana.flaw)}</p></details>` : ''}
    ${decision ? `<div class="shared-mana-shade"><section class="shared-mana-decision" role="dialog" aria-modal="true" aria-label="Rozliczenie wspólnej many">${decision}</section></div>` : ''}
  </section>`;
}
