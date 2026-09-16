/* Mission prose stays in the scenario pack; controls reuse the native board. */
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
function renderMission() {
  const panel=document.getElementById('mission-panel');
  const p=state.mission;
  document.body.classList.toggle('mission-active',Boolean(p));
  document.body.classList.toggle('mission-story',Boolean(p?.active || (p && state.exploration_mana?.active)));
  if (!p) {panel.hidden=true;return;}
  panel.hidden=false;
  if (state.exploration_mana?.active) {
    renderPartyConfrontation(panel,state.exploration_mana);
    panel.insertAdjacentHTML('beforeend',`<a class="button secondary" href="/">${esc(p.ui.menu)}</a>`);
    return;
  }
  const options=p.choices.map(c=>`<button class="mana-rune-choice" data-mission-slot="${c.slot}" onclick="missionAction('${esc(c.action)}',${esc(JSON.stringify(c.extra))})">${c.icon}<span>${esc(c.label)}<small>${esc(c.name)}</small></span></button>`).join('');
  const rolling=p.rolling?`<form id="mission-roll" onsubmit="missionRoll(event)">${Array.from({length:p.roll_count||1},(_,i)=>`<label>${esc(p.stage==='potion_roll'?p.ui.potion_roll:p.ui.fatigue_die)}<input id="mission-roll-${i}" type="number" min="1" max="${p.roll_sides||4}" required data-roll-dice="1k${p.roll_sides||4}" data-roll-source="${esc(p.text.title)}"></label>`).join('')}<button type="submit">${esc(p.ui.submit)}</button></form>`:'';
  const journal=p.debt?`<p class="mission-journal">${esc(p.ui['journal_'+p.debt])}</p>`:'';
  panel.innerHTML=`<div class="mission-toolbar"><a class="button secondary" href="/">${esc(p.ui.menu)}</a>${p.can_save?`<button class="secondary" onclick="api('/api/snapshot/save',{},'')">${esc(p.ui.save)}</button>`:''}<details><summary>${esc(p.ui.restart)}</summary>${p.checkpoints.map(c=>`<button class="secondary" onclick="missionCheckpoint('${esc(c.id)}')">${esc(c.label)}</button>`).join('')}</details></div>
    ${p.active?`${p.image?`<img class="mission-art ${p.setup?'mission-map':''}" src="${esc(p.image)}" alt="${esc(p.text.title)}">`:''}<small>${esc(p.text.speaker)}</small><h2>${esc(p.text.title)}</h2><div class="mission-prose">${esc(p.text.body).replace(/\n/g,'<br>')}</div>${p.setup?`<a href="${esc(p.print_map)}" target="_blank" rel="noopener">${esc(p.ui.print_map)}</a>`:''}${rolling}<div class="mana-decisions">${options}</div>`:`<details ${state.combat?'':'open'}><summary>${esc(p.ui.rules)}</summary><p>${esc(p.combat_tip)}</p><p>${esc(p.ui.combat_help)}</p><a href="${esc(p.print_map)}" target="_blank" rel="noopener">${esc(p.ui.print_map)}</a><img class="mission-map" src="/scenario-assets/maps/outpost.svg" alt="Mapa posterunku"></details>${options}`}
    ${p.stage==='summary'?`<h3>${esc(p.ui.ledger)}</h3><ul>${p.ledger.map(x=>`<li>${esc(x.name)}: ${x.amount}${x.kind==='money'?' sz':''}</li>`).join('')}</ul>${journal}<p>${esc(p.ui.treasury)}</p><p>${esc(p.ui.completed)}</p>`:''}`;
}

function missionRollSummary(wizard) {
  if (!wizard.submitButton.closest('#mission-roll') || state.mission.stage !== 'potion_roll') return '';
  const rolled=wizard.allSteps.reduce((sum,s)=>sum+(s.raw||0),0);
  return `<p>${esc(state.mission.ui.healing_total)}: ${rolled} + ${state.mission.roll_bonus} = <b>${rolled+state.mission.roll_bonus} PW</b></p>`;
}
