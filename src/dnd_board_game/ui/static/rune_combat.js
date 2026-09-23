/* Presentation of server-owned rune offers, payments and physical targets. */
const RuneCombat = (() => {
  const view = () => state?.combat?.shared_mana?.rune_view;
  const cost = runes => runes?.length ? runes.map(rune => `<span class="tt-rune-cost">1 × ${esc(rune === '*' ? 'Dowolna runa' : rune)}</span>`).join(' + ') : 'Bez kosztu run';
  function allocationHtml(pool) {
    const recipient = (state.combat.tabletop?.actors || state.combat.actors || []).find(actor => actor.id === pool.actor)
      || {id:pool.actor, name:pool.actor_name};
    return `<section class="tt-rune-allocation"><header class="tt-person tt-rune-recipient" data-rune-recipient="${esc(pool.actor)}">
      ${TabletopCombat.portrait(recipient)}<div><small>Początek walki · ${Number(pool.opening_count)} run dla drużyny</small>
      <h1>Przydział: ${esc(pool.actor_name)}</h1></div></header><p>${esc(pool.instruction)}</p>
      <div class="tt-rune-offer">${pool.offer.map(item => {
        const choice = pool.choices.find(c => c.rune === item.rune);
        return `<button type="button" data-rune-take="${esc(item.rune)}" ${choice ? '' : 'disabled'}>${item.icon}<strong>${esc(item.rune)}</strong><small>Dostępne: ${item.count}</small></button>`;
      }).join('') || '<p>Pula jest pusta. Zatwierdź przydział, aby przejść dalej.</p>'}</div>
      <ul class="tt-party-runes">${pool.hands.map(hand => `<li${hand.hero === pool.actor ? ' aria-current="step"' : ''}><b>${esc(hand.name)} · ${hand.count}/7</b><span>${hand.cards.map(esc).join(', ') || 'Brak run'}</span></li>`).join('')}</ul>
      <div class="tt-buttons"><button class="tt-accept" onclick="sharedManaCommand('rune_confirm')">✓ Zatwierdź i przejdź dalej</button>
      <button class="secondary" onclick="sharedManaCommand('rune_undo')" ${pool.choices.some(c => c.command === 'rune_undo') ? '' : 'disabled'}>↩ Cofnij ostatnią runę</button></div></section>`;
  }
  function paymentHtml(declaration) {
    const paid = declaration.stage !== 'payment';
    const target = declaration.target_selection;
    return `<section class="tt-rune-payment"><small>${paid ? 'Rozstrzygnięcie mocy' : 'Podgląd mocy'}</small><h1>${esc(declaration.name)}</h1>
      <p>${esc(declaration.description || '')}</p>${declaration.context ? `<p>${esc(declaration.context)}</p>` : ''}
      ${target ? sharedManaTargetsHtml(declaration) : ''}
      ${declaration.mode_options?.length ? `<div class="tt-rune-boosts">${declaration.mode_options.map(option => `<button onclick="sharedManaCommand('mode',{mode:'${esc(option.mode)}'})" aria-pressed="${Boolean(option.selected)}">${option.icon || ''}${esc(option.label)}</button>`).join('')}</div>` : ''}
      ${!paid ? `<p>Koszt: ${cost(declaration.cost)}</p>${(declaration.reminders || []).slice(1).map(note => `<p>${esc(note)}</p>`).join('')}${declaration.boost_options?.length ? '<p>Możesz wybrać jedno wzmocnienie.</p>' : ''}
        <div class="tt-rune-boosts">${(declaration.boost_options || []).map(option => `<button type="button" onclick="sharedManaBoostOption(${option.slot})" aria-pressed="${Boolean(option.selected)}" ${option.enabled ? '' : 'disabled'}>${option.icon}<span>${esc(option.effect)}<small>${option.cost.length ? cost(option.cost) : `Bez dopłaty run · ${esc(option.budget || '')}`}</small></span>${option.selected ? '✓' : ''}</button>`).join('')}</div>` : ''}
      ${declaration.roll_sides && ['effect_roll','bonus'].includes(declaration.stage) ? `<label>Naturalny k${declaration.roll_sides}<input type="number" min="1" max="${declaration.roll_sides}" value="${declaration.roll || 1}" onchange="sharedManaCommand('parameters',{natural_roll:Number(this.value)})"></label><p>Ustaw wynik przez +/− i zatwierdź.</p>` : ''}
      ${declaration.error ? `<p role="alert">${esc(declaration.error)}</p>` : ''}
      <div class="tt-buttons"><button class="tt-accept" onclick="sharedManaPrimary()" ${declaration.error || (target && !target.can_confirm) ? 'disabled' : ''}>✓ ${paid ? 'Zastosuj efekt' : 'Zatwierdź użycie'}</button>
      ${!paid ? `<button class="secondary" onclick="sharedManaCommand('cancel')">↩ Wróć bez płatności</button>` : ''}</div>
      <p class="tt-hint">${paid ? 'Runy zostały wydane.' : 'Koszt zostanie pobrany po zatwierdzeniu. Brakującą runę podstawową mogą zastąpić dwie dowolne.'}</p></section>`;
  }
  function chooseReaction(optionId = null) {
    const choices = state.combat?.reaction_choices;
    if (!choices || busy) return false;
    return api('/api/combat/reaction/choose',{option_id:optionId,confirm:optionId === null,revision:choices.revision},'');
  }
  function reactionsHtml(choices) {
    return `<section class="tt-rune-payment"><small>Reakcja · ${esc(choices.actor_name)}</small><h1>Wybierz reakcję</h1><p>${esc(choices.instruction)}</p>
      <ul class="tt-legal-targets">${choices.actors.map(actor => `<li>${esc(actor.name)} · pole (${actor.position.join(', ')})${actor.selected ? ' · wybrany' : ''}</li>`).join('')}</ul>
      <div class="tt-rune-boosts">${choices.choices.map(option => `<button onclick="RuneCombat.chooseReaction('${esc(option.id)}')" aria-pressed="${option.selected}">${option.icon}<span>${esc(option.label)}<small>${option.cost.length ? cost(option.cost) : 'Bez kosztu run'}</small></span></button>`).join('')}</div>
      <div class="tt-buttons"><button class="tt-accept" onclick="RuneCombat.chooseReaction()" ${choices.confirm_available ? '' : 'disabled'}>✓ Wybierz tę reakcję</button><button class="secondary" onclick="triggerSecondaryAction()">↩ Pomiń</button></div></section>`;
  }
  function selectionHtml(pool) {
    return `<section class="tt-rune-payment"><small>${esc(pool.actor_name)}</small><h1>${esc(pool.title)}</h1>
      <p>${esc(pool.instruction)}</p>${pool.reserved.length ? `<p>Zarezerwowane: ${cost(pool.reserved)}</p>` : ''}
      <div class="tt-rune-offer">${pool.source.map(item => `<button type="button" onclick="sharedManaCommand('rune_choice_take',{rune:'${esc(item.rune)}'})" ${item.enabled ? '' : 'disabled'} aria-pressed="${item.selected > 0}">${item.icon}<strong>${esc(item.rune)}</strong><small>Dostępne: ${item.remaining} · wybrane: ${item.selected}</small></button>`).join('')}</div>
      <p>Wybrane: ${pool.selected.length ? pool.selected.map(esc).join(', ') : 'brak'} (${pool.selected.length}/${pool.maximum})</p>
      ${pool.payment.length ? `<p>Koszt mocy: ${cost(pool.payment)}</p>` : ''}${pool.partner.length ? `<p>Runa sojusznika: ${cost(pool.partner)}</p>` : ''}
      <div class="tt-buttons"><button class="tt-accept" onclick="sharedManaCommand('rune_choice_confirm')" ${pool.can_confirm ? '' : 'disabled'}>✓ Zatwierdź wybór</button><button class="secondary" onclick="sharedManaCommand('rune_choice_back')">↩ Cofnij</button></div>
      <p class="tt-hint">Runy pozostają na rękach do ostatniego zatwierdzenia. ↩ cofa wybory i kroki aż do podglądu; tam kolejne ↩ anuluje moc.</p></section>`;
  }
  function stepHtml() {
    if (state.combat?.reaction_choices) return reactionsHtml(state.combat.reaction_choices);
    const pool = view();
    if (!pool) return null;
    if (pool.phase === 'allocation') return allocationHtml(pool);
    if (pool.phase === 'rune_choices') return selectionHtml(pool);
    if (pool.upkeep) return `<section class="tt-rune-payment"><h1>Podtrzymanie aury · ${esc(pool.actor_name)}</h1><p>${esc(pool.instruction)}</p><div class="tt-rune-boosts">${pool.choices.map(choice => `<button onclick="sharedManaCommand('${choice.command}',{rune:'${esc(choice.rune || '')}'})">${choice.icon || ''}${esc(choice.label)}</button>`).join('')}</div></section>`;
    const declaration = state.combat.shared_mana.declaration;
    return declaration ? paymentHtml(declaration) : null;
  }
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-rune-take]');
    if (button && !button.disabled && !busy) sharedManaCommand('rune_take',{rune:button.dataset.runeTake});
  });
  return {stepHtml, cost, chooseReaction};
})();
