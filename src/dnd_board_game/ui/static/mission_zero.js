/* Mission prose stays in the scenario pack; controls reuse the native board. */
function missionSetupHtml(setup,title,body,controls) {
  const tiles=setup.tiles||[];
  const preview=tiles.length ? `<div class="mission-tile-gallery ${tiles.length===1?'single':''}">${tiles.map(tile=>
    `<figure data-setup-cutout="${esc(tile.id)}"><div class="mission-tile-preview">${tile.svg}</div><figcaption><b>${esc(tile.id)} · ${esc(tile.name)}</b><small>${tile.size.join(' × ')} ${esc(state.mission.ui.setup_cells)}</small></figcaption></figure>`).join('')}</div>`
    : '<div class="mission-figurine-preview" aria-hidden="true"><svg viewBox="0 0 100 120"><circle cx="50" cy="25" r="16"/><path d="M39 45h22l9 48H30ZM25 99h50v12H25Z"/></svg></div>';
  return `<article class="mission-tile-setup"><div>${preview}</div><div class="mission-tile-instruction"><small>${esc(state.mission.ui.setup_heading)}</small><h2>${esc(title)}</h2><div class="mission-prose">${esc(body).replace(/\n/g,'<br>')}</div><div class="mana-decisions">${controls}</div></div></article>`;
}

function missionAction(action, extra={}) {
  return api('/api/mission/action', {action, revision:state.mission.revision, ...extra}, '');
}
function missionRoll(event) {
  event.preventDefault();
  const inputs=[...event.target.querySelectorAll('input[type="number"]')];
  return missionAction('roll', state.mission.stage==='potion_roll'?{rolls:inputs.map(i=>Number(i.value))}:{roll:Number(inputs[0].value)});
}
function missionCheckpoint(id) {
  SessionNavigation.open('checkpoints');
}
function missionScrollArea() {
  const panel=document.querySelector('#mission-panel.mission-reading');
  if (!panel) return null;
  const text=panel.querySelector('.mission-narrative-text,.mission-tile-instruction');
  if (!text) return null;
  return getComputedStyle(text).overflowY==='auto' ? text : panel.querySelector('.mission-narrative,.mission-tile-setup');
}
function scrollMissionText(direction) {
  const area=missionScrollArea();
  if (area) area.scrollBy({top:direction*Math.max(80,area.clientHeight*.7),behavior:'instant'});
}
function sizeMissionReader() {
  const panel=document.querySelector('#mission-panel.mission-reading,#mission-panel.mission-equipment');
  if (!panel) return;
  panel.style.setProperty('--mission-room',`${Math.max(180,innerHeight-Math.max(0,panel.getBoundingClientRect().top)-12)}px`);
}
window.addEventListener('resize',sizeMissionReader);
window.addEventListener('load',()=>{
  const observer=new ResizeObserver(sizeMissionReader);
  document.querySelectorAll('.app-shell-header,#board-disconnected-banner').forEach(element=>observer.observe(element));
});
function renderMission() {
  const panel=document.getElementById('mission-panel');
  const p=state.mission;
  panel.classList.remove('confrontation-view','tabletop-confrontation');
  const readingKey=p?.reading ? `${p.stage}:${p.text.id||p.text.title}` : '';
  const scrollTop=readingKey && panel.dataset.readingKey===readingKey ? missionScrollArea()?.scrollTop||0 : 0;
  panel.dataset.readingKey=readingKey;
  panel.classList.toggle('mission-reading',Boolean(p?.reading));
  panel.classList.toggle('mission-equipment',Boolean(p?.equipment));
  panel.classList.toggle('has-multiple-choices',(p?.choices.length||0)>1);
  document.body.classList.toggle('mission-active',Boolean(p));
  document.body.classList.toggle('mission-story',Boolean(p?.active || (p && state.exploration_mana?.active)));
  if (!p) {panel.hidden=true;return;}
  panel.hidden=false;
  if (p.stage==='battle' && !state.combat) {panel.hidden=true;return;}
  if (state.exploration_mana?.active) {
    panel.classList.remove('mission-reading','mission-equipment');
    renderPartyConfrontation(panel,state.exploration_mana);
    return;
  }
  if (p.equipment) {renderPartyEquipment(p,panel);return;}
  const options=p.choices.map(c=>`<button class="mana-rune-choice" data-mission-slot="${c.slot}" onclick="missionAction('${esc(c.action)}',${esc(JSON.stringify(c.extra))})">${c.icon}<span>${esc(c.label)}<small>${esc(c.name)}</small></span></button>`).join('');
  const rolling=p.rolling?`<form id="mission-roll" onsubmit="missionRoll(event)">${Array.from({length:p.roll_count||1},(_,i)=>`<label>${esc(p.stage==='potion_roll'?p.ui.potion_roll:p.stage==='identify_roll'?p.ui.identify_die:p.ui.fatigue_die)}<input id="mission-roll-${i}" type="number" min="1" max="${p.roll_sides||4}" required data-roll-dice="1k${p.roll_sides||4}" data-roll-source="${esc(p.text.title)}"></label>`).join('')}<button type="submit">${esc(p.ui.submit)}</button></form>`:'';
  const scrollControls=p.reading?`<div class="mission-scroll-controls"><button type="button" onclick="scrollMissionText(-1)" aria-label="${esc(p.ui.scroll_up)}">−</button><button type="button" onclick="scrollMissionText(1)" aria-label="${esc(p.ui.scroll_down)}">+</button><small>${esc(p.ui.scroll_hint)}</small></div>`:'';
  const cargo=['explore','search_result','guild_return','summary'].includes(p.stage)?`<div class="mission-cargo"><b>${esc(p.ui.contract_status)}</b><ul>${p.recovery.cargo.map(c=>`<li>${esc(c.name)} — ${esc(c.status)}</li>`).join('')}</ul></div>`:'';
  const pending=p.recovery.open_threads.map(t=>`<p class="mission-journal">${esc(t)}</p>`).join('');
  const summary=p.stage==='summary'?`<h3>${esc(p.ui.ledger)}</h3><ul>${p.ledger.map(x=>`<li>${esc(x.name)}: ${x.amount}${x.kind==='money'?' sz':''}</li>`).join('')}</ul><p>${esc(p.ui.summary_bell)}: ${esc(p.recovery.bell)}</p>${pending}<p>${esc(p.ui.treasury)}</p><p>${esc(p.ui.completed)}</p>`:'';
  const controls=`<div class="mission-story-controls">${scrollControls}<div class="mana-decisions">${options}</div></div>`;
  panel.innerHTML=`<div class="mission-toolbar"><a class="button secondary" href="/">${esc(p.ui.menu)}</a><small>${esc(p.ui.autosave)}</small><details><summary>${esc(p.ui.restart)}</summary>${p.checkpoints.map(c=>`<button class="secondary" onclick="missionCheckpoint('${esc(c.id)}')">${esc(c.label)}</button>`).join('')}</details></div>
    ${p.setup ? missionSetupHtml(p.setup,p.text.title,p.text.body,'')+controls : p.active ? `<article class="mission-narrative mission-narrative--${esc(p.image_layout||'landscape')}">${p.image?`<img class="mission-art ${p.setup?'mission-map':''}" src="${esc(p.image)}" alt="${esc(p.text.title)}">`:''}<div class="mission-narrative-text" tabindex="0" role="region" aria-label="${esc(p.ui.reading_label)}"><small>${esc(p.text.speaker)}</small><h2>${esc(p.text.title)}</h2><div class="mission-prose">${esc(p.text.body).replace(/\n/g,'<br>')}</div>${cargo}${summary}</div></article>${rolling}${controls}` : `<details><summary>${esc(p.ui.rules)}</summary><p>${esc(p.combat_tip)}</p><p>${esc(p.ui.combat_help)}</p></details>${options}`}`;
  sizeMissionReader();
  const scrollArea=missionScrollArea();
  if (scrollArea) scrollArea.scrollTop=scrollTop;
}

function missionRollSummary(wizard) {
  if (!wizard.submitButton.closest('#mission-roll')) return '';
  if (state.mission.stage==='identify_roll') {
    const raw=wizard.allSteps[0].raw||0, bonus=state.mission.roll_bonus;
    return `<p>${esc(state.mission.ui.identify_total)}: ${raw} + ${bonus} = <b>${raw+bonus}</b> · ST ${state.mission.identification_dc}</p>`;
  }
  if (state.mission.stage !== 'potion_roll') return '';
  const rolled=wizard.allSteps.reduce((sum,s)=>sum+(s.raw||0),0);
  return `<p>${esc(state.mission.ui.healing_total)}: ${rolled} + ${state.mission.roll_bonus} = <b>${rolled+state.mission.roll_bonus} PW</b></p>`;
}

function equipmentButton(c, className='') {
  return `<button type="button" class="mana-rune-choice ${className}" data-mission-slot="${c.slot}" onclick="missionAction('${esc(c.action)}',${esc(JSON.stringify(c.extra))})">${c.icon}<span>${esc(c.label)}</span></button>`;
}

function equipmentSlot(row, p) {
  const c=p.choices.find(c=>c.action==='equipment_slot'&&c.extra.gear_slot===row.id);
  const selected=p.equipment.picker?.slot===row.id;
  const item=row.item;
  return `<button type="button" class="equipment-slot ${row.linked?'equipment-slot-linked':''} ${selected?'equipment-slot-selected':''}" data-equipment-slot="${esc(row.id)}" ${c?`data-mission-slot="${c.slot}" onclick="missionAction('equipment_slot',{gear_slot:'${esc(row.id)}'})"`:'disabled'} aria-label="${esc(row.label)}: ${esc(item?.name||'Puste miejsce')}">
    <span class="equipment-slot-label">${esc(row.label)}</span>
    <span class="equipment-slot-content">${item&&!row.linked?`<span class="equipment-slot-art">${item.art}</span>`:''}<span>${esc(row.linked?'Zajęta przez broń dwuręczną':item?.name||'Puste miejsce')}${item?.quantity>1?` <small>×${item.quantity}</small>`:''}</span></span>
    <span class="equipment-slot-rune">${row.icon}</span></button>`;
}

function equipmentItemPreview(item, emptyText, handChange=false) {
  return item?`<div class="equipment-art">${item.art}</div><h3>${esc(item.name)}${item.quantity>1?` × ${item.quantity}`:''}</h3><p>${esc(item.description||'Przedmiot wyposażenia.')}</p>${item.two_handed&&handChange?'<p class="equipment-warning">Zajmie obie ręce. Obecny sprzęt z obu rąk wróci do zapasu.</p>':''}`:`<div class="equipment-empty-art" aria-hidden="true">—</div><h3>${esc(emptyText)}</h3>`;
}

function renderPartyEquipment(p, panel) {
  const e=p.equipment;
  const t=(key,params={})=>sessionUiText(`equipment.${key}`,params);
  const inStash=['equipment_stash','equipment_sell'].includes(e.view);
  const body=e.loadout.filter(row=>!row.id.startsWith('pack_'));
  const pack=e.loadout.filter(row=>row.id.startsWith('pack_'));
  const footerChoices=p.choices.filter(c=>!['equipment_slot','equipment_group','equipment_pack_previous','equipment_pack_next'].includes(c.action));
  let aside;
  if(e.picker) {
    const pick=e.picker;
    aside=`<section class="equipment-picker" aria-label="${esc(t('choose_for',{slot:pick.label}))}"><small>${esc(t('choose_for',{slot:pick.label}))}</small><div class="equipment-picker-position">${esc(t('item_count',{index:pick.index,count:pick.count}))} · ${esc(t(pick.current?'current':pick.source==='hero'?'own_item':pick.source==='stash'?'base_item':'empty_item'))}</div>
      ${equipmentItemPreview(e.item,t('empty_item'),!pick.current&&['main_hand','off_hand'].includes(pick.slot))}<p>${esc(t(pick.source==='empty'?'empty_hint':pick.current?'keep_hint':'picker_hint'))}</p>
      <div class="equipment-candidate-list" aria-label="${esc(t('available_items'))}">${pick.names.map((name,index)=>`<span ${index===pick.index-1?'aria-current="true"':''}>${esc(name)}</span>`).join('')}</div></section>`;
  } else {
    aside=`<section class="equipment-pack"><div class="equipment-section-title"><h3>${esc(t('pack'))}</h3><small>${e.pack_pages>1?esc(t('page',{page:e.pack_page,pages:e.pack_pages})):esc(t('pack_hint'))}</small></div><div class="equipment-pack-grid">${pack.map(row=>equipmentSlot(row,p)).join('')}</div>
      ${e.pack_pages>1?`<div class="equipment-pack-pages">${p.choices.filter(c=>c.action.startsWith('equipment_pack_')).map(c=>equipmentButton(c)).join('')}</div>`:''}</section>`;
  }
  let workspace=`<div class="equipment-workspace"><section class="equipment-body" aria-label="${esc(t('worn'))}">${body.map(row=>equipmentSlot(row,p)).join('')}</section>${aside}</div>`;
  if(inStash) {
    workspace=`<div class="equipment-stash"><nav class="equipment-stash-tabs" aria-label="${esc(t('shared'))}">${p.choices.filter(c=>c.action==='equipment_group').map(c=>equipmentButton({...c,label:`${c.label} · ${e.groups[c.extra.group]}`},c.extra.group===e.group?'selected':'')).join('')}</nav>
      <section class="equipment-stash-preview">${equipmentItemPreview(e.item,t(`${e.group}_empty`))}<p>${esc(t(`${e.group}_hint`))}</p>${e.group==='found'&&!e.can_identify?`<p>${esc(t('identify_at_base'))}</p>`:''}<small>${esc(t('item_count',{index:e.stash_index,count:e.groups[e.group]}))}</small></section></div>`;
  }
  panel.innerHTML=`<div class="mission-toolbar"><span class="equipment-stage-label">${esc(t('title'))}</span><small>${esc(p.ui.autosave)}</small><span>${esc(t('treasury',{gold:e.gold}))}</span></div>
    <div class="equipment-heading"><div class="equipment-hero">${e.portrait_url?`<img class="equipment-hero-portrait" src="${esc(e.portrait_url)}" alt="${esc(e.hero)}">`:''}<div><small>${esc(t('hero_step',{index:e.hero_index,count:e.hero_count}))}</small><h2>${esc(e.hero)}</h2><span>${esc(sessionUiText('common.equipment_stats',{strength:e.strength,ac:e.ac}))}</span></div></div>
      <ol class="equipment-party" aria-label="${esc(t('order'))}">${e.party.map((hero,index)=>`<li ${index===e.hero_index-1?'aria-current="step"':''}>${index<e.hero_index-1?'✓ ':''}${esc(hero.name)}</li>`).join('')}</ol></div>
    ${workspace}<p class="equipment-notice" role="status">${esc(e.notice||(e.view==='equipment'?t(e.groups.available===0?'starter_hint':'sheet_hint'):e.view==='equipment_sell'?t('sale_hint'):e.picker?t('picker_controls'):''))}</p>
    <div class="mana-decisions equipment-controls">${footerChoices.map(c=>equipmentButton(c)).join('')}</div>`;
  sizeMissionReader();
  const candidates=panel.querySelector('.equipment-candidate-list');
  const selected=candidates?.querySelector('[aria-current]');
  if(selected) candidates.scrollLeft+=selected.getBoundingClientRect().left-candidates.getBoundingClientRect().left-candidates.clientWidth/2+selected.clientWidth/2;
}
