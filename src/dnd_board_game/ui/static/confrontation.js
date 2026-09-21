/* Presentation only: legal choices and all modifiers come from the server. */
let confrontationHelpCursor = {key: '', target: null};
let confrontationDetail = null;
const confrontationText = (key, params = {}) => sessionUiText(`confrontation.${key}`, params);
const confrontationSigned = value => `${value >= 0 ? '+' : '−'}${Math.abs(value)}`;

function confrontationChoice(p, c, label = null, css = '') {
  if (!c) return '';
  const attrs = `data-mana-slot="${c.slot}" ${c.slot === 28 ? 'data-mana-primary' : ''}`;
  if (c.action === 'scroll') return `<button type="button" class="confrontation-scroll-button" ${attrs} aria-label="${esc(c.label)}" onclick="scrollConfrontation(${c.extra.direction})">${c.extra.direction > 0 ? '+' : '−'}</button>`;
  const handler = c.action === 'inspect' ? `openConfrontationDetail('${c.extra.detail}')` : `explorationManaAction('${esc(c.action)}',${esc(JSON.stringify(c.extra))})`;
  return `<button type="button" class="mana-rune-choice ${css}" ${attrs} onclick="${handler}">${c.icon}<span>${label ?? esc(c.label)}</span></button>`;
}
function confrontationIdle(p) {
  return p.phase === 'turn' && p.mana.phase === 'ready' && !p.needs_resume && !p.compromise_pending;
}
function confrontationHelpChoices(p) {
  return p.board_choices.filter(c => c.action === 'support');
}
function confrontationCurrentHelp(p) {
  const choices = confrontationHelpChoices(p), key = `${p.scene.id}:${p.actor}:${p.round}`;
  if (confrontationHelpCursor.key !== key || !choices.some(c => c.extra.target === confrontationHelpCursor.target)) {
    confrontationHelpCursor = {key, target: choices[0]?.extra.target || null};
  }
  return choices.find(c => c.extra.target === confrontationHelpCursor.target);
}
function confrontationInstruction(p) {
  const t = confrontationText;
  let text;
  if (p.needs_resume) text = t('resume');
  else if (p.phase === 'recovery') text = t('recovery', {name: p.actor_name, label: p.recovery_label}) + ' ' + t(p.recovery_cost ? 'recovery_cost' : 'recovery_free', {count: p.recovery_cost});
  else if (p.compromise_pending) text = p.mission_ui?.compromise || t('compromise');
  else if (p.phase === 'introduction') text = t(p.approaches?.length ? 'introduction' : 'introduction_legacy');
  else if (p.phase === 'peek_choice') text = t('peek_instruction');
  else if (p.phase === 'setup') text = [p.mana.preparation, ...(p.mission_ui ? [] : p.setup.preparation)].join(' ');
  else if (p.phase === 'result') text = p.mission_ui ? `${p.result} ${p.mission_ui.mission_result}` : [p.mana.phase === 'drain' ? t('drain') : '', p.result, t('result_collect'), t(p.completed ? 'lesson_completed' : 'lesson_repeat')].join(' ');
  else if (p.mana.phase === 'reveal') text = t(p.mana.offer.length ? 'reveal_second' : 'reveal_first') + ' ' + t('reveal_note');
  else if (p.mana.phase === 'choose') text = t('choose_mana') + (p.mana.offer.length > 1 ? ` ${t('other_stays')}` : '');
  else if (p.mana.phase === 'burn') text = t(p.reaction_view?.active ? 'reaction_burn_instruction' : 'burn_instruction', {count: p.mana.pending});
  else if (p.phase === 'turn') text = p.mana.card_count >= 6 ? t('full_pool') : '';
  else if (p.phase === 'check') text = t('check_instruction', {dc: p.dc});
  else if (p.phase === 'impact') text = t('impact_instruction', {die: p.impact_die, effect: p.effect_name.toLowerCase()});
  else if (p.phase === 'reaction') text = t('reaction_instruction', {description:p.reaction_view.description, count:p.reaction_view.preview_burn});
  else if (p.phase === 'after_reaction') text = t('reaction_done');
  else text = t('continue_instruction');
  return [p.correction_notice, text].filter(Boolean).join(' ');
}
function confrontationTitle(p) {
  if (p.reaction_view?.active && !p.needs_resume && p.phase !== 'result') return p.reaction_view.title;
  const keys = {introduction:'introduction_title', setup:'setup_title', recovery:'recovery_title', check:'check_title', impact:'impact_title', result:'result_title', peek_choice:'peek_title', reaction:'reaction_title', after_action:'result_title', after_reaction:'result_title'};
  const key = p.needs_resume ? 'resume_title' : p.compromise_pending ? 'compromise_title' : ['reveal','choose','burn'].includes(p.mana.phase) ? {reveal:'reveal_title',choose:'draw_title',burn:'burn_title'}[p.mana.phase] : keys[p.phase] || 'choose_action';
  return confrontationText(key, {effect: (p.effect_name || '').toLowerCase()});
}
function confrontationActorHtml(p) {
  if (p.reaction_view?.active) return `<section class="confrontation-active-hero confrontation-active-source"><div class="confrontation-hero-heading">${p.image_url ? `<img class="confrontation-hero-portrait" src="${esc(p.image_url)}" alt="${esc(p.reaction_view.source)}">` : ''}<div><small>${esc(p.reaction_view.label)}</small><h3>${esc(p.reaction_view.source)}</h3><p>${esc(confrontationText('round_end', {round:p.round}))}</p></div></div></section>`;
  const own = p.party.find(h => h.id === p.actor);
  return `<section class="confrontation-active-hero"><div class="confrontation-hero-heading">${own?.portrait_url ? `<img class="confrontation-hero-portrait" src="${esc(own.portrait_url)}" alt="${esc(own.name)}">` : ''}<div><small>${esc(confrontationText('your_turn', {name: p.actor_name}))}</small><h3>${esc(p.actor_name)}</h3><p>${esc(p.method)}</p></div></div>
    <p class="confrontation-pool">${manaCostHtml(own?.cards || [])}</p><p class="confrontation-pool-summary">${esc(confrontationText('cards', {count: own?.card_count || 0}))} · ${esc(confrontationText('test_bonus', {bonus: own?.roll_bonus || 0}))}</p>
    ${own?.aid ? `<p class="confrontation-received-aid"><b>${esc(confrontationText('received_aid', {bonus: own.aid}))}</b><small>${esc(confrontationText('received_aid_duration'))}</small></p>` : ''}
    <div class="confrontation-detail-links">${p.board_choices.filter(c => c.action === 'inspect').map(c => confrontationChoice(p, c, esc(confrontationText(c.extra.detail === 'bonus' ? 'bonus_link' : 'effects_link', {bonus: confrontationSigned(p.test_preview?.modifier_total || 0), count: own?.passives.length || 0})))).join('')}</div></section>`;
}
function confrontationManaOffers(p) {
  return `<div class="confrontation-offer">${p.mana.offer.map((color,index) => {
    const choice = p.board_choices.find(c => c.action === 'take' && c.extra.index === index);
    if (!choice) return '';
    const own = p.party.find(h => h.id === p.actor), display = p.passive_details?.[color];
    const before = p.mana.roll_bonus, after = choice.preview?.roll_bonus ?? before;
    return `<article class="mana-value mana-${color}"><div class="confrontation-offer-symbol">${manaCostHtml([color])}<b>${esc(confrontationText('card_test_change', {before,after}))}</b></div>
      <small>${esc(confrontationText(own.cards.includes(color) ? 'passive_active' : 'passive_new', {count: own.cards.filter(c => c === color).length}))}</small>
      ${manaPassiveDescriptionHtml({label: partyConfrontationPassive(p,color), display}, false)}
      ${confrontationChoice(p,choice,esc(confrontationText('take_card')))}</article>`;
  }).join('')}</div>`;
}
function confrontationActions(p) {
  const t = confrontationText, test = p.board_choices.find(c => c.action === 'test'), peek = p.board_choices.find(c => c.action === 'peek');
  const help = confrontationCurrentHelp(p), helps = confrontationHelpChoices(p), target = p.party.find(h => h.id === help?.extra.target);
  const testData = p.test_preview;
  const helpBody = help ? `<div class="confrontation-help-person">${target.portrait_url ? `<img src="${esc(target.portrait_url)}" alt="${esc(target.name)}">` : ''}<div><strong>${esc(target.name)}</strong><small>${esc(target.method)}</small></div></div><p>${esc(t('support_gain', {bonus:help.support_bonus,total:help.support_total}))}</p><small>${esc(t('support_duration',{name:target.name}))}</small>${confrontationChoice(p,help,`${esc(t('support'))} · ${esc(target.name)}`)}<small class="confrontation-action-cost">${esc(help.cost ? t('burn_cost',{count:help.cost}) : t('free'))}</small>` : `<p>${esc(t('support_none'))}</p>`;
  return `<div class="confrontation-action-grid"><article class="confrontation-test"><small>${esc(t('test'))}</small><h3>${esc(p.method)}</h3><p class="confrontation-formula">${esc(t('test_formula',{bonus:confrontationSigned(testData.modifier_total),dc:p.dc}))}</p><p>${esc(t('impact_formula',{effect:p.effect_name,die:p.impact_die,bonus:confrontationSigned(testData.impact_modifier)}))}</p>${confrontationChoice(p,test,esc(t('test')))}<small class="confrontation-action-cost">${esc(t('burn_cost',{count:testData.cost}))}</small></article>
    <article class="confrontation-help"><div class="confrontation-help-heading"><small>${esc(t('support'))}</small><div>${helps.length>1 ? `<button type="button" class="confrontation-scroll-button" onclick="scrollConfrontation(-1)" aria-label="${esc(t('scroll_up'))}">−</button><span>${esc(t('support_counter',{index:helps.indexOf(help)+1,count:helps.length}))}</span><button type="button" class="confrontation-scroll-button" onclick="scrollConfrontation(1)" aria-label="${esc(t('scroll_down'))}">+</button>` : ''}</div></div>${helpBody}</article>
    <article class="confrontation-peek"><div><h3>${esc(t('peek'))}</h3><p>${esc(t(p.mana.deck ? 'peek_short' : 'wait_empty'))}</p><small>${esc(t('peek_ends'))}</small></div>${confrontationChoice(p,peek,esc(t('peek')))}</article></div>`;
}
function renderPartyConfrontation(panel, p) {
  panel.hidden = false;
  panel.classList.add('confrontation-view');
  panel.classList.toggle('confrontation-approach-view', p.choosing_approach);
  panel.classList.toggle('tabletop-confrontation', !p.choosing_approach);
  if (confrontationDetail && confrontationDetail.revision !== p.revision) closeConfrontationDetail(false);
  if (p.choosing_approach) {renderConfrontationApproachSelection(panel,p);return;}
  const key = `${p.scene.id}:${p.actor}:${p.phase}:${p.mana.phase}`;
  const oldScroll = panel.dataset.confrontationKey === key ? panel.querySelector('.confrontation-controls')?.scrollTop || 0 : 0;
  panel.dataset.confrontationKey = key;
  const t = confrontationText, own = p.party.find(h => h.id === p.actor), idle = confrontationIdle(p);
  const choosing = p.mana.phase === 'choose' && !p.needs_resume && !p.compromise_pending;
  const image = p.image_url, imageName = p.scene.name;
  const buttons = p.board_choices.filter(c => !['leave','scroll','take','undo','inspect'].includes(c.action));
  const roll = p.attempt?.phase === 'roll';
  const instruction = confrontationInstruction(p);
  const intro = ['introduction','setup','result'].includes(p.phase);
  panel.innerHTML = `<aside class="confrontation-scroll" tabindex="0" aria-label="${esc(t('scene_label'))}"><div class="confrontation-scene">${image ? `<img class="confrontation-scene-image" src="${esc(image)}" alt="${esc(imageName)}">` : ''}<div><small>${esc(t(p.scene.kind === 'npc' ? 'talk' : 'object'))} · ${esc(t('round',{round:p.round}))}</small><h2>${esc(p.scene.name)}</h2><p>${esc(p.scene.goal)}</p></div></div>
    <div class="confrontation-pressure"><div><span>${esc(t('resistance'))}</span><b>${p.resistance} / ${p.maximum}</b></div><progress max="${p.maximum}" value="${p.resistance}"></progress><div><span>${esc(t('deck'))} <b>${p.mana.deck}</b></span><span>${esc(t('burned'))} ${p.mana.burned}</span></div></div>
    ${confrontationActorHtml(p)}
    <div class="confrontation-party-summary" aria-label="${esc(t('party_label'))}">${p.party.map(h=>`<span class="${!p.reaction_view?.active&&h.id===p.actor?'current':''}">${esc(h.name)}</span>`).join('')}</div>
    ${p.forecast ? `<p class="confrontation-forecast">${esc(t('forecast',{name:p.forecast}))}<small>${esc(t('forecast_cost',{count:p.pressure}))}</small></p>` : ''}
    ${p.obligation ? `<p class="mana-obligation">${esc(t('obligation'))}</p>` : ''}
    </aside><section class="confrontation-controls"><header><small>${esc(p.reaction_view?.active ? p.reaction_view.label : t('your_turn',{name:p.actor_name}))}</small><h2>${esc(confrontationTitle(p))}</h2></header>
    ${intro ? `<p class="confrontation-description">${esc(p.scene.description)}</p>` : ''}
    ${instruction ? `<p class="confrontation-instruction" aria-live="polite">${esc(instruction)}</p>` : ''}
    ${p.recovery_color && p.phase==='recovery' ? `<div class="confrontation-recovery-symbol">${manaCostHtml([p.recovery_color])}</div>` : ''}
    ${p.first_test_bonus && intro ? `<p class="mana-obligation">${esc(t('first_bonus',{label:p.first_test_label,bonus:p.first_test_bonus}))}</p>` : ''}
    ${p.critical && !p.needs_resume ? `<div class="confrontation-critical" role="status"><b>${esc(t(`critical_${p.critical}_title`))}</b><p>${esc(t(`critical_${p.critical}`,{effect:p.effect_name,value:p.last_impact,count:p.action_cost}))}</p></div>` : ''}
    ${p.last && !idle && p.phase !== 'reaction' && !['reveal','choose'].includes(p.mana.phase) ? `<p class="confrontation-result" aria-live="polite">${esc(p.last)}</p>` : ''}
    ${idle ? confrontationActions(p) : choosing ? confrontationManaOffers(p) : roll ? `<form id="exploration-mana-roll" onsubmit="submitExplorationManaRoll(event)"><label>${esc(p.die_kind==='test'?t('test_die'):`${p.effect_name} k${p.attempt.die}`)}<input id="confrontation-${p.die_kind}-roll" aria-label="${esc(t('natural_die'))}" data-roll-dice="1k${p.attempt.die}" data-roll-source="${esc(p.actor_name)}" type="number" min="1" max="${p.attempt.die}" required></label><button type="submit">✓ ${esc(t('resolve'))}</button></form>` : `<div class="mana-decisions">${buttons.map(c=>confrontationChoice(p,c,c.action==='color'?manaCostHtml([c.extra.color]):null,c.action==='color'?'confrontation-color-choice':'')).join('')}</div>`}
    ${idle ? `<div class="confrontation-conditional-choices">${buttons.filter(c=>!['test','support','peek'].includes(c.action)).map(c=>confrontationChoice(p,c)).join('')}</div>` : ''}
    ${intro && !p.mission_ui ? `<p class="confrontation-lesson-objective">${esc(p.lesson.objective)}</p>` : ''}
    <nav class="confrontation-navigation"><div>${p.board_choices.filter(c=>c.action==='scroll').map(c=>confrontationChoice(p,c)).join('')}<small>${esc(t(idle ? confrontationHelpChoices(p).length > 1 ? 'support_browse' : confrontationHelpChoices(p).length ? 'support_one' : 'action_hint' : 'scroll_hint'))}</small>${p.board_choices.filter(c=>c.action==='undo').map(c=>confrontationChoice(p,c)).join('')}</div>${confrontationChoice(p,p.board_choices.find(c=>c.action==='leave'))}</nav></section>`;
  panel.querySelector('.confrontation-controls').scrollTop = oldScroll;
  sizeConfrontation();
}
function partyConfrontationPassive(p,color) {
  return p.color_passives?.[color] || confrontationText('passive_fallback');
}
function scrollConfrontation(direction) {
  if (confrontationDetail) {document.querySelector('#confrontation-detail .confrontation-detail-body')?.scrollBy({top:direction*220,behavior:'instant'});return;}
  const p = state?.exploration_mana, panel=document.querySelector('.confrontation-view:not([hidden])');
  if (!panel) return;
  if (p && confrontationIdle(p)) {
    const choices=confrontationHelpChoices(p), current=confrontationCurrentHelp(p);
    if (choices.length>1) {
      confrontationHelpCursor.target=choices[(choices.indexOf(current)+direction+choices.length)%choices.length].extra.target;
      renderPartyConfrontation(panel,p);
    }
    return;
  }
  const areas=[panel.querySelector('.confrontation-controls'),panel.querySelector('.confrontation-scroll')].filter(Boolean);
  if(direction<0) areas.reverse();
  const area=areas.find(el=>direction>0?el.scrollTop+el.clientHeight<el.scrollHeight-1:el.scrollTop>0);
  area?.scrollBy({top:direction*Math.max(80,area.clientHeight*.7),behavior:'instant'});
}
function confrontationDetailPanel() {
  return confrontationDetail && state?.exploration_mana?.active && state.exploration_mana.revision===confrontationDetail.revision ? {context:`confrontation-detail:${confrontationDetail.revision}:${confrontationDetail.kind}`,slots:[26,27,28,29],exclusive:true} : null;
}
function openConfrontationDetail(kind) {
  const p=state?.exploration_mana;
  if (!p?.active || !p.board_choices.some(c=>c.action==='inspect'&&c.extra.detail===kind) || busy) return false;
  const t=confrontationText, own=p.party.find(h=>h.id===p.actor);
  let dialog=document.getElementById('confrontation-detail');
  if (!dialog) {dialog=document.createElement('dialog');dialog.id='confrontation-detail';document.body.append(dialog);dialog.addEventListener('cancel',e=>{e.preventDefault();closeConfrontationDetail();});}
  confrontationDetail={kind,revision:p.revision};
  const content=kind==='bonus' ? `<p class="confrontation-formula">${esc(t('test_formula',{bonus:confrontationSigned(p.test_preview.modifier_total),dc:p.dc}))}</p><dl>${p.test_preview.modifiers.map(m=>`<div><dt>${esc(m.label)}</dt><dd>${confrontationSigned(m.value)}</dd></div>`).join('')}</dl>${own.aid?`<p>${esc(t('support_duration',{name:own.name}))}</p>`:''}` : `<p>${esc(t('effect_not_bonus'))}</p>${own.passives.length?own.passives.map(passive=>`<article><h3>${manaCostHtml([passive.color])} ${esc(passive.display?.name||passive.label)}</h3>${manaPassiveDescriptionHtml(passive,false)}</article>`).join(''):`<p>${esc(t('no_effects'))}</p>`}<p>${esc(t('effect_end'))}</p><p>${esc(t('stacking_legend'))}</p>`;
  dialog.innerHTML=`<header><small>${esc(t('details_no_cost'))}</small><h2>${esc(t(kind==='bonus'?'bonus_title':'effects_title',{name:p.actor_name}))}</h2></header><div class="confrontation-detail-body">${content}</div><footer><small>${esc(t('details_controls'))}</small><div><button onclick="scrollConfrontation(-1)" aria-label="${esc(t('scroll_up'))}">−</button><button onclick="scrollConfrontation(1)" aria-label="${esc(t('scroll_down'))}">+</button><button onclick="closeConfrontationDetail()">✓ ${esc(t('close'))}</button></div></footer>`;
  if (!dialog.open) dialog.showModal();
  syncBrowserBoardPanel();
  return true;
}
function closeConfrontationDetail(sync=true) {
  const context=confrontationDetailPanel()?.context;
  confrontationDetail=null;
  document.getElementById('confrontation-detail')?.close();
  if(sync && context) releaseBrowserBoardPanel(context);
}
function handleConfrontationPanelEvent(event) {
  const p=state?.exploration_mana;
  if (!p?.active || p.model!=='party_confrontation') return false;
  if (event.context===`confrontation-inspect:${p.revision}`) {
    const choice=p.board_choices.find(c=>c.action==='inspect'&&c.slot===event.slot);
    if(choice) openConfrontationDetail(choice.extra.detail);
    return true;
  }
  if (event.context===confrontationDetailPanel()?.context) {
    if(event.slot===26||event.slot===27) scrollConfrontation(event.slot===27?1:-1);
    else if(event.slot===28||event.slot===29) closeConfrontationDetail();
    return true;
  }
  return false;
}
function sizeConfrontation() {
  document.querySelectorAll('.confrontation-view:not([hidden])').forEach(panel=>{
    const tools=document.getElementById('training-tools');
    const bottom=panel.id==='training-arena-panel'&&tools?.getClientRects().length?tools.getBoundingClientRect().top:innerHeight;
    panel.style.setProperty('--confrontation-room',`${Math.max(200,bottom-Math.max(0,panel.getBoundingClientRect().top)-12)}px`);
  });
}
window.addEventListener('resize',sizeConfrontation);
window.addEventListener('load',()=>{
  const observer=new ResizeObserver(sizeConfrontation);
  document.querySelectorAll('.app-shell-header,#board-disconnected-banner').forEach(element=>observer.observe(element));
});
function confrontationApproaches(p,effect) {
  const t=confrontationText, available=p.approaches.filter(a=>a.available), rune=a=>`<span class="support-rune" title="${esc(a.name)}">${a.icon}</span>`;
  return `<section class="confrontation-approaches" style="--approach-columns:${Math.min(6,available.length)}" aria-label="${esc(t('approaches_label'))}"><h3>${esc(t('approaches',{name:p.actor_name}))}</h3><div>${available.map(a=>{
    const links=a.supports.includes('*')?`<span class="support-any">${esc(t('any_approach'))}</span><span class="support-runes">${p.approaches.filter(target=>target.id!==a.id||a.repeatable).map(rune).join('')}</span>`:a.supports.map(id=>p.approaches.find(target=>target.id===id)).filter(Boolean).map(target=>`<span class="support-target">${esc(target.name)} ${rune(target)}</span>`).join('')||`<span>${esc(t('none'))}</span>`;
    return `<article><button type="button" class="approach-card" data-mana-slot="${a.slot}" onclick="explorationManaAction('approach',${esc(JSON.stringify({approach:a.id}))})"><span class="approach-title">${a.icon} ${esc(a.name)}</span><span class="approach-availability ${a.repeatable?'repeatable':'exclusive'}">${esc(t(a.repeatable?'repeatable':'exclusive'))}</span><span class="approach-description">${esc(a.description)}</span><b>${esc(a.ability)} ${confrontationSigned(a.modifier)} · ST ${a.dc}</b><span>${esc(t('impact_formula',{effect,die:a.die,bonus:confrontationSigned(a.modifier)}))}</span><span class="approach-links"><b>${esc(t('support_links'))}</b>${links}</span></button></article>`;
  }).join('')}</div></section>`;
}
function renderConfrontationApproachSelection(panel,p) {
  const t=confrontationText, image=p.image_url?`<img class="confrontation-scene-image" src="${esc(p.image_url)}" alt="${esc(p.scene.name)}">`:'',actor=p.party.find(h=>h.id===p.actor);
  panel.dataset.confrontationKey=`${p.scene.id}:${p.actor}:approach`;
  panel.innerHTML=`<div class="confrontation-scroll"><div class="confrontation-scene">${image}<div><div class="training-heading"><h2>${esc(p.scene.name)}</h2></div><p>${esc(p.scene.goal)}</p><p class="confrontation-description">${esc(p.scene.description)}</p></div></div><div class="approach-layout"><div class="approach-chooser">${actor?.portrait_url?`<img src="${esc(actor.portrait_url)}" alt="${esc(p.actor_name)}">`:''}<div><b>${esc(t('chooser',{name:p.actor_name,index:p.approach_index,count:p.party.length}))}</b>${p.correction_notice?`<p>${esc(p.correction_notice)}</p>`:''}</div></div>${confrontationApproaches(p,p.effect_name)}</div><div class="approach-party-summary" aria-label="${esc(t('party_choices'))}">${p.party.map(h=>`<span class="${h.id===p.actor?'current':''}"><b>${esc(h.name)}</b>: ${h.assigned?esc(h.method):t(h.id===p.actor?'choosing':'waiting')}</span>`).join('')}</div>${p.first_test_bonus?`<p class="approach-favor">${esc(t('first_bonus',{label:p.first_test_label,bonus:p.first_test_bonus}))}</p>`:''}</div><div class="confrontation-controls"><p class="approach-instruction">${esc(t('approach_instruction'))}</p><nav class="confrontation-navigation"><div>${p.board_choices.filter(c=>['scroll','undo'].includes(c.action)).map(c=>confrontationChoice(p,c)).join('')}</div>${confrontationChoice(p,p.board_choices.find(c=>c.action==='leave'))}</nav></div>`;
  sizeConfrontation();
}
