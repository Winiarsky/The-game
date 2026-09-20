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
  if (window.confirm(state.mission.ui.restart_warning)) missionAction('checkpoint',{id});
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
  panel.classList.remove('confrontation-view');
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

function renderPartyEquipment(p, panel) {
  const e=p.equipment;
  const controls=p.choices.map(c=>`<button class="mana-rune-choice" data-mission-slot="${c.slot}" onclick="missionAction('${esc(c.action)}',${esc(JSON.stringify(c.extra))})">${c.icon}<span>${esc(c.label)}</span></button>`).join('');
  panel.innerHTML=`<div class="mission-toolbar"><a class="button secondary" href="/">Menu główne</a><small>${esc(p.ui.autosave)}</small><span>Przygotowanie ${e.hero_index}/${e.hero_count} · Skarbiec: ${e.gold} sz</span></div>
    <div class="equipment-heading"><h2>${esc(e.hero)}</h2><span>Siła ${e.strength} · KP ${e.ac}</span></div>
    <div class="equipment-layout"><section class="equipment-preview">${e.item?`<div class="equipment-art">${e.item.art}</div><h3>${esc(e.item.name)} ${e.item.quantity>1?`× ${e.item.quantity}`:''}</h3><p>${esc(e.item.description||'Przedmiot ze wspólnego wyposażenia drużyny.')}</p>${e.item.usage?`<p><b>${esc(e.item.usage)}</b></p>`:''}`:'<h3>Zapas jest pusty</h3><p>Możecie odłożyć tu przedmioty z wyposażenia postaci.</p>'}<strong>${esc(e.source)} · ${e.index}/${e.count}</strong></section>
    <section class="equipment-loadout" aria-label="Sloty postaci">${e.loadout.map(row=>`<div><b>${esc(row.slot)}</b><span>${esc(row.items)}</span></div>`).join('')}</section></div>
    <p class="equipment-notice" role="status">${p.stage==='equipment_sell'?'Sprzedaż zabierze cały wybrany stos. Potwierdźcie albo wróćcie.':esc(e.notice||'−/+ wybiera przedmiot. Runa wybiera działanie. Zmiana slotu oddaje poprzedni przedmiot do zapasu.')}</p>
    <div class="mana-decisions equipment-controls">${controls}</div>`;
  sizeMissionReader();
}
