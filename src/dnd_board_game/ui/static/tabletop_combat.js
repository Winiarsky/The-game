/* Presentation only. All declarations, legality and confirmations remain server-owned. */
const TabletopCombat = (() => {
  let inspected = '', effectPage = 0, turnKey = '', scrollTop = 0, scrollActor = '';
  const copy = (key, params = {}) => sessionUiText(`combat.${key}`, params);
  const text = (key, params = {}) => esc(copy(key, params));
  const roster = () => state?.combat?.tabletop?.actors || [];
  const current = () => state?.combat?.tabletop?.active_actor_id || '';
  const find = id => roster().find(actor => String(actor.id) === String(id));
  const enabled = () => Boolean(state?.combat?.tabletop && state?.ui_copy?.combat);
  const sign = value => `${Number(value) >= 0 ? '+' : ''}${Number(value)}`;

  function portrait(actor, extra = '') {
    const atlas = state.ui_copy.combat.portraits?.[actor.id];
    const alt = text('portrait', {name: actor.name});
    if (atlas) {
      const columns = Math.max(1, Number(atlas.columns)), rows = Math.max(1, Number(atlas.rows));
      const x = Number(atlas.column) * 100 / Math.max(1, columns - 1);
      const y = Number(atlas.row) * 100 / Math.max(1, rows - 1);
      return `<span class="tt-portrait tt-atlas ${extra}" role="img" aria-label="${alt}" style="background-image:url('${esc(atlas.url)}');background-size:${columns * 100}% ${rows * 100}%;background-position:${x}% ${y}%"></span>`;
    }
    return actor.portrait_url
      ? `<img class="tt-portrait ${extra}" src="${esc(actor.portrait_url)}" alt="${alt}">`
      : `<span class="tt-portrait tt-silhouette ${extra}" role="img" aria-label="${alt}"><svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="13" r="8"/><path d="M5 39v-5a15 15 0 0 1 30 0v5Z"/></svg></span>`;
  }
  function health(actor) {
    const max = actor.effective_max_hp ?? actor.max_hp ?? actor.hp;
    const status = actor.dead ? 'dead' : actor.unconscious ? 'unconscious' : actor.defeated ? 'defeated' : '';
    return `<span>${text('hp', {hp: actor.hp, max})}</span>${Number(actor.temp_hp) > 0 ? `<small>${text('temp_hp', {hp: actor.temp_hp})}</small>` : ''}${status ? `<small class="tt-danger">${text(status)}</small>` : ''}`;
  }
  function badges(actor) {
    const details = actor.details || [];
    const labels = [...new Set(details.map(effect => effect.concentration ? copy('concentration') : String(effect.label || '').split(':')[0].replace(/^Aktywne\s*[·—-]\s*/, '')).filter(Boolean))];
    return labels.length ? `<div class="tt-statuses">${labels.slice(0, 3).map(label => `<span>${esc(label)}</span>`).join('')}${labels.length > 3 ? `<span>+${labels.length - 3}</span>` : ''}</div>` : '';
  }
  function manaLine(actor) {
    const pool = state.combat.shared_mana?.pool_view;
    const hand = pool?.hands?.find(item => item.hero === actor.id);
    return hand ? `<small class="tt-mana-line">${text('mana', {cards: hand.cards.length, bonus: hand.roll_bonus ?? 0, charge: hand.total})}</small>` : '';
  }
  function initiativeHtml(combat) {
    return `<aside class="tt-initiative"><header><small>${text('round', {round: combat.round_number})}</small><h2>${text('initiative')}</h2></header>
      <div class="tt-roster" role="list" aria-label="${text('initiative')}">${roster().map(actor => {
        const active = actor.id === current(), viewing = actor.id === inspected;
        const hp = Math.max(0, Math.min(100, 100 * Number(actor.hp) / Math.max(1, Number(actor.effective_max_hp ?? actor.max_hp ?? actor.hp))));
        return `<button type="button" role="listitem" data-tt-actor="${esc(actor.id)}" class="tt-actor${active ? ' is-active' : ''}${viewing ? ' is-inspected' : ''}${actor.defeated ? ' is-defeated' : ''}"${active ? ' aria-current="step"' : ''}>
          ${portrait(actor)}<span class="tt-actor-content"><span class="tt-name"><strong>${esc(actor.name)}</strong><small>${active ? text('now') : viewing ? text('inspected') : esc(actor.initiative ?? '')}</small></span>
          <span class="tt-hp">${health(actor)}</span>${active || viewing ? `<i class="tt-health-track"><i style="width:${hp}%"></i></i>${manaLine(actor)}<small>${text('ac', {ac: actor.ac})}</small>${badges(actor)}` : badges(actor)}</span></button>`;
      }).join('')}</div><footer>${text('browse_hint')}</footer></aside>`;
  }
  function button(slot, label, disabled = false) {
    return `<button type="button" data-tt-slot="${slot}"${disabled ? ' disabled' : ''} class="${slot === 28 ? 'tt-accept' : 'secondary'}">${slot === 28 ? '✓' : '↩'} ${text(label)}</button>`;
  }
  function actorHeader(actor, label = '') {
    return `<header class="tt-person">${portrait(actor)}<div>${label ? `<small>${text(label)}</small>` : ''}<h2>${esc(actor.name)}</h2><div class="tt-hp">${health(actor)}</div></div></header>`;
  }
  function auraDescription(aura) {
    const params = {value: Math.abs(Number(aura.value || 0)), die: aura.die_sides || 4, modifier: sign(aura.modifier || 0)};
    const key = {bless_aura_source: 'aura_bless', saving_throw_bonus: 'aura_saves', divine_care_aura_source: 'aura_divine_care', healing_grace_aura_source: 'aura_healing'}[aura.effect_kind];
    return key ? text(key, params) : '';
  }
  function inspectionHtml() {
    const actor = find(inspected);
    if (!actor) { inspected = ''; return ''; }
    const details = actor.details || [];
    effectPage = Math.min(effectPage, Math.max(0, details.length - 1));
    const effect = details[effectPage];
    return `<section class="tt-inspection" data-tt-inspection="${esc(actor.id)}">${actorHeader(actor, 'inspected')}
      <div class="tt-inspection-facts"><span>${text('ac', {ac: actor.ac})}</span>${manaLine(actor)}</div>
      <div class="tt-effect"><small>${details.length ? text('effect_page', {page: effectPage + 1, total: details.length}) : text('effects_count', {count: 0})}</small>
      ${effect ? `<h3>${effect.concentration ? `${text('concentration')} · ` : ''}${esc(effect.label)}</h3>
        ${effect.body ? `<p>${esc(effect.body)}</p>` : ''}
        ${effect.source_name ? `<p class="tt-effect-source">${text('effect_source', {name: effect.source_name})}</p>` : ''}
        ${effect.expires ? `<p>${text('effect_expiry', {expiry: effect.expires})}</p>` : ''}
        ${effect.duration && !effect.save_timing ? `<p>${text(`duration_${effect.duration}`, {name: effect.expiration_actor, count: effect.expiration_count})}</p>` : ''}
        ${effect.save_timing ? `<p>${text('condition_save', {ability: abilityLabel(effect.save_ability), dc: effect.save_dc, timing: copy(`save_${effect.save_timing}`)})}</p>` : ''}
        ${effect.aura ? `<p>${text(effect.aura_source ? 'aura_source' : 'aura_receives')} · ${text('aura_radius', {radius: effect.aura.radius_feet})}</p><p>${auraDescription(effect.aura)}</p>${effect.aura_receives ? `<p>${text('aura_exit')}</p>` : ''}` : ''}` : `<p>${text('no_effects')}</p>`}</div>
      <div class="tt-buttons">${button(28, effectPage + 1 < details.length ? 'next_effect' : 'close_inspection')}${button(29, 'back')}</div><p class="tt-hint">${text('inspect_hint')}</p></section>`;
  }
  function fact(label, value) { return `<div><dt>${text(label)}</dt><dd>${value}</dd></div>`; }
  function targetFactsHtml(pending, target) {
    const projected = state.combat.tabletop.target || {};
    const source = pending.source || {}, positioning = pending.positioning || {};
    const range = source.attack_kind === 'melee' ? source.reach_feet || source.range_feet : source.long_range_feet ? `${source.range_feet}/${source.long_range_feet}` : source.range_feet;
    const cover = positioning.cover_level || 'none';
    const distance = projected.distance_feet;
    const coverLabel = text(`cover_${cover === 'full' ? 'total' : cover}`);
    const sourceNames = (positioning.cover_sources || []).map(esc).join(', ');
    return `<dl class="tt-facts">${distance !== null && distance !== undefined ? fact(range ? 'distance_range' : 'distance', text('feet', {value: `${distance}${range ? ` / ${range}` : ''}`})) : range ? fact('range', text('feet', {value: range})) : ''}
      ${pending.source ? fact('cover', `${coverLabel}${sourceNames ? `<small>${sourceNames}</small>` : ''}`) : ''}
      ${pending.source && !source.save_ability ? fact('armor_class', esc(pending.target_ac ?? target.ac)) : ''}
      ${pending.attack_mode && !source.save_ability ? fact('roll', text(`roll_${pending.attack_mode}`)) : ''}</dl>
      ${source.save_ability ? `<p class="tt-roll">${text('save', {ability: abilityLabel(source.save_ability), dc: pending.spell_save_dc || source.save_dc})}</p>` : pending.attack_instruction ? `<p class="tt-roll">${esc(pending.attack_instruction)}</p>` : ''}
      ${positioning.ranged_in_melee ? `<p class="tt-condition">${text('ranged_threat')}</p>` : ''}${positioning.flanking ? `<p class="tt-condition">${text('flanking')}</p>` : ''}
      ${(pending.active_modifiers || []).length ? `<p class="tt-condition">${pending.active_modifiers.map(mod => `${esc(mod.label)} ${sign(mod.value || 0)}`).join(' · ')}</p>` : ''}`;
  }
  function simpleFeature(combat) {
    const feature = combat.class_feature_targeting;
    return feature && !['lay_on_hands', 'preserve_life'].includes(feature.action_id);
  }
  function targetHtml(combat) {
    const pending = combat.pending_player_attack;
    const feature = combat.class_feature_targeting;
    const ref = pending?.target || feature?.selected_target;
    const actor = ref ? find(ref.id) : null;
    const name = pending?.source?.name || feature?.label || combat.targeting?.source_name || '';
    const hasSelection = Boolean(ref);
    const invalid = hasSelection && !actor;
    const allowed = pending ? pending.stage === 'confirm_attack' && Boolean(actor) : feature ? (feature.selecting_destination ? Boolean(feature.selected_destination) : Boolean(actor)) : false;
    const cost = feature?.mana_cost ? manaCostHtml(feature.mana_cost) : feature?.cost ? text('cost', {cost: feature.cost}) : '';
    return `<section class="tt-target" data-tt-target="${esc(actor?.id || '')}"><h1 class="tt-target-title">${esc(name)} <span>· ${text('choose_target')}</span></h1>
      ${actor ? `${actorHeader(actor, 'target_selected')}${badges(actor)}${targetFactsHtml(pending || {}, actor)}` : `<div class="tt-target-empty"><h2>${text(invalid ? 'target_unavailable' : 'choose_target_title')}</h2><p>${text('target_hint')}</p></div>`}
      ${feature?.instructions ? `<p class="tt-action-description">${manaTextHtml(feature.instructions)}</p>` : ''}
      ${feature?.selected_destination ? `<p>(${Number(feature.selected_destination.col)}, ${Number(feature.selected_destination.row)})</p>` : ''}
      ${pending?.source?.source_type === 'spell' ? spellMechanicalEffectHtml(pending.source) : ''}
      ${pending?.twinned_spell?.available ? pendingPlayerAttackHtml(pending) : `<div class="tt-buttons">${button(28, 'confirm_target', !allowed)}${button(29, hasSelection ? 'change_target' : 'back')}${cost ? `<span class="tt-cost">${cost}</span>` : ''}</div>`}
      <p class="tt-hint">${text('action_hint')}</p></section>`;
  }
  function actionHtml(menu, combat) {
    const selected = menu.options?.[Number(menu.selected_index || 0)] || {};
    if (menu.stage !== 'preview') return `<section class="tt-idle combat-keyboard-waiting"><h1>${text('choose_action')}</h1><p>${text('choose_action_hint')}</p><p class="tt-hint">${text('action_hint')}</p></section>`;
    return `<section class="tt-action"><small>${text('action_preview')}</small><h1><span class="combat-panel-icon">${selected.panel_icon || ''}</span>${manaTextHtml(combatActionTileLabel(selected) || '')}</h1>
      ${actionManaCostHtml(selected)}<p class="tt-action-description">${manaTextHtml(selected.description || '')}</p>${combatTurnActionUnavailableHtml(menu, combat)}
      <div class="tt-buttons">${button(28, 'confirm', Boolean(selected.panel_unavailable_reason))}${button(29, 'back')}</div><p class="tt-hint">${text('action_hint')}</p></section>`;
  }
  function decisionHtml(combat) {
    if (inspected) return inspectionHtml();
    const actor = combat.current_actor || {};
    const finished = combat.status === 'finished';
    // Interrupts and physical dice retain their established handlers and dialogs.
    if (!resultAck && !combatInterruptPresentation(combat)) {
      if (combat.pending_player_attack?.stage === 'confirm_attack' || simpleFeature(combat)) return targetHtml(combat);
      if (combat.turn_action_menu && !combat.physical_mana?.needs_attack_count) return actionHtml(combat.turn_action_menu, combat);
      if (combat.targeting && !combat.pending_player_attack && !combat.pending_player_healing && !combat.pending_area_spell) return targetHtml(combat);
    }
    if (finished) return `<div class="tt-buttons"><button onclick="resolveCombatOutcome()">✓ ${text('end_combat')}</button></div>`;
    return combatCurrentStepHtml(combat, finished, actor.faction === 'ally', actor.faction === 'enemy', combatInterruptPresentation(combat));
  }
  function manaLayerHtml(combat) {
    const original = physicalManaHtml(combat);
    const pool = combat.shared_mana?.pool_view;
    if (!pool?.choices?.length) return original;
    const template = document.createElement('template');
    template.innerHTML = original;
    const decision = template.content.querySelector('.shared-mana-decision');
    if (!decision) return original;
    const owner = pool.hands?.find(hand => hand.hero === pool.actor);
    const choosing = pool.phase === 'choose';
    decision.classList.add('tt-pool-step');
    decision.innerHTML = `<header class="tt-pool-heading"><small>${['setup','drain'].includes(pool.phase) ? text('whole_party') : esc(owner?.name || combat.current_actor?.name || '')}</small><h2>${text(choosing ? 'choose_mana' : pool.phase === 'setup' ? 'prepare_mana' : pool.phase === 'drain' ? 'mana_drain' : 'mana_operation')}</h2>
      ${owner ? `<span>${text('mana', {cards: owner.cards.length, bonus: owner.roll_bonus ?? 0, charge: owner.total})}</span>` : ''}</header>
      ${manaDeckPreparationHtml(pool) || `<p class="tt-pool-instruction">${esc(pool.instruction)}</p>`}<div class="tt-pool-choices${choosing ? ' is-draw' : ''}">${pool.choices.map((choice, index) => {
        const passive = choosing ? owner?.color_passives?.[choice.color] : null;
        const display = passive?.display;
        const value = owner?.values?.[choice.color] || 1;
        return `<article><button type="button" data-tt-pool-choice="${index}" aria-label="${esc(choice.label)}">
          ${choice.color ? `<span class="tt-pool-symbol">${manaCostHtml([choice.color])}</span>` : ''}
          <span class="tt-pool-rune">${choice.icon || ''}</span><span>${choosing ? text('take_mana') : choice.color ? '' : esc(choice.label)}</span></button>
          ${choosing && owner ? `<p class="tt-pool-gain">${text('mana_gain', {charge: Math.min(6, owner.total + value), bonus: Math.min(6, owner.cards.length + 1)})}</p>` : ''}
          ${display ? `<div class="tt-pool-passive"><h3>${esc(display.name)}</h3><p>${esc(display.when)}</p><p>${manaPassiveRuleHtml(display.effect)}</p></div>` : passive ? `<p>${esc(passive.label)}</p>` : ''}</article>`;
      }).join('')}</div>`;
    return template.innerHTML;
  }
  function html(view) {
    const combat = view.combat;
    const key = `${combat.round_number}:${combat.current_actor?.id}`;
    if (key !== turnKey) { inspected = ''; effectPage = 0; scrollActor = combat.current_actor?.id || ''; turnKey = key; }
    if (inspected && !find(inspected)) inspected = '';
    return `<div class="tt-combat">${initiativeHtml(combat)}<main class="tt-decision combat-current-step" data-tt-decision tabindex="-1">${decisionHtml(combat)}</main></div>
      <div class="tt-mana-layer">${manaLayerHtml(combat)}</div>`;
  }
  function canBrowse() {
    if (!enabled() || keyboardRollWizard || resultAck || document.querySelector('dialog[open]')) return false;
    const combat = state.combat, mana = combat.shared_mana;
    if (combat.status !== 'active' || combat.shield_bash || combatInterruptPresentation(combat)) return false;
    if (mana?.declaration || mana?.pool_view?.choices?.length || mana?.command?.stage || sharedManaPanel()) return false;
    if (combatPresentationPhase(combat, false, combat.current_actor?.faction === 'ally', combat.current_actor?.faction === 'enemy') === 'roll') return false;
    return roster().length > 0;
  }
  function panel() {
    if (!canBrowse()) return null;
    const combat = state.combat, menu = combat.turn_action_menu;
    const option = menu?.options?.[Number(menu.selected_index || 0)]?.id || '';
    const target = combat.pending_player_attack?.target?.id || combat.class_feature_targeting?.selected_target?.id || '';
    const stage = combat.pending_player_attack?.stage || combat.class_feature_targeting?.action_id || menu?.stage || combatPresentationPhase(combat, false, combat.current_actor?.faction === 'ally', combat.current_actor?.faction === 'enemy');
    const idle = menu && menu.stage !== 'preview';
    return {context: `combat-inspect:${combat.round_number}:${current()}:${stage}:${option}:${target}:${inspected || 'closed'}`,
      slots: !inspected && idle ? [26, 27, 29] : [26, 27, 28, 29], exclusive: Boolean(inspected)};
  }
  function repaint() {
    const element = document.querySelector('.tt-roster');
    if (element) scrollTop = element.scrollTop;
    render();
    if (typeof scheduleAutomaticBoardScan === 'function') scheduleAutomaticBoardScan();
  }
  function inspect(actorId) {
    if (!canBrowse() || !find(actorId)) return false;
    inspected = actorId; effectPage = 0; scrollActor = actorId; repaint(); return true;
  }
  function handleSlot(slot) {
    if (!canBrowse()) return false;
    if (slot === 26 || slot === 27) {
      const all = roster(), from = Math.max(0, all.findIndex(actor => actor.id === (inspected || current())));
      return inspect(all[(from + (slot === 26 ? -1 : 1) + all.length) % all.length].id);
    }
    if (!inspected || ![28, 29].includes(slot)) return false;
    if (slot === 28 && effectPage + 1 < (find(inspected)?.details || []).length) effectPage += 1;
    else { inspected = ''; effectPage = 0; scrollActor = current(); }
    repaint(); return true;
  }
  function afterRender() {
    const list = document.querySelector('.tt-roster');
    if (!list) return;
    list.scrollTop = scrollTop;
    if (scrollActor) {
      const row = [...list.querySelectorAll('[data-tt-actor]')].find(item => item.dataset.ttActor === scrollActor);
      if (row) {
        const a = row.getBoundingClientRect(), b = list.getBoundingClientRect();
        if (a.top < b.top) list.scrollTop -= b.top - a.top;
        else if (a.bottom > b.bottom) list.scrollTop += a.bottom - b.bottom;
      }
      scrollActor = '';
    }
    scrollTop = list.scrollTop;
  }
  document.addEventListener('click', event => {
    const poolChoice = event.target.closest('[data-tt-pool-choice]');
    if (poolChoice && !busy) {
      const choice = state.combat?.shared_mana?.pool_view?.choices?.[Number(poolChoice.dataset.ttPoolChoice)];
      if (choice) sharedManaCommand(choice.command, choice.index !== undefined ? {index: choice.index} : choice.color ? {color: choice.color} : {});
      return;
    }
    const row = event.target.closest('[data-tt-actor]');
    if (row) { inspect(row.dataset.ttActor); return; }
    const control = event.target.closest('[data-tt-slot]');
    if (!control || control.disabled || busy) return;
    const slot = Number(control.dataset.ttSlot);
    if (handleSlot(slot)) return;
    const combat = state.combat;
    if (slot === 28) {
      if (combat.pending_player_attack?.stage === 'confirm_attack') confirmPlayerAttackTarget();
      else if (simpleFeature(combat)) confirmClassFeatureTargetSelection();
      else if (combat.turn_action_menu?.stage === 'preview') confirmCombatTurnAction('');
      else triggerPrimaryAction();
    } else if (slot === 29) {
      if (combat.pending_player_attack) cancelPlayerAttackTarget();
      else if (simpleFeature(combat)) cancelClassFeatureTargeting();
      else if (combat.turn_action_menu?.stage === 'preview') cancelCombatTurnActionPreview();
      else triggerSecondaryAction();
    }
  });
  return {enabled, html, afterRender, canBrowse, panel, handleSlot, inspect, portrait, getView: () => ({inspected, effectPage})};
})();
