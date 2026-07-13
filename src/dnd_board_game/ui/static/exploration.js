let state = null;
let busy = false;
let resultAck = null;
let playerTurnScanLoop = false;
let boardScanInFlight = false;
let boardScanToken = 0;
let sessionLog = null;
let decisionCorrectionOpen = false;
let sidePanelOpen = localStorage.getItem('explorationSidePanelOpen') === 'true';
function setSidePanelOpen(open) {
  sidePanelOpen = Boolean(open);
  localStorage.setItem('explorationSidePanelOpen', sidePanelOpen ? 'true' : 'false');
  document.body.classList.toggle('side-panel-open', sidePanelOpen);
  const panel = document.getElementById('side-panel');
  const toggle = document.getElementById('side-panel-toggle');
  if (panel) panel.setAttribute('aria-hidden', sidePanelOpen ? 'false' : 'true');
  if (toggle) toggle.setAttribute('aria-expanded', sidePanelOpen ? 'true' : 'false');
}
function toggleSidePanel() {
  setSidePanelOpen(!sidePanelOpen);
}
function setBusy(message) {
  busy = Boolean(message);
  const status = document.getElementById('status');
  status.hidden = !busy;
  status.textContent = message || '';
  document.querySelectorAll('button, textarea, input').forEach(el => {
    if (el.closest('details.debug-panel')) return;
    if (el.dataset.allowBusy === 'true') return;
    el.disabled = busy;
  });
}
async function api(path, body, busyMessage) {
  setBusy(busyMessage || 'Czekam na odpowiedź...');
  try {
    const res = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body || {})});
    const data = await res.json();
    if (!res.ok) alert(data.error || 'Błąd');
    state = data.state || data;
  if (path === '/api/rolls' && res.ok) {
      resultAck = state.flow && state.flow.stage === 'interaction_result' ? null : latestResultMessage(state);
    } else if (path !== '/api/decision') {
      resultAck = null;
    }
    render();
    refreshSessionLog();
  } finally {
    setBusy('');
  }
}
async function loadState() {
  const res = await fetch('/api/state');
  state = await res.json();
  render();
  refreshSessionLog();
}
function render() {
  const inCombat = Boolean(state.combat);
  document.getElementById('page-title').textContent = inCombat ? 'Walka' : 'Eksploracja';
  document.getElementById('encounter-title').textContent = inCombat ? 'Walka' : 'Zaczyna się encounter';
  document.getElementById('scenario').textContent = state.scenario.name;
  document.getElementById('zone').textContent = state.current_zone.name;
  document.getElementById('challenge').textContent = state.active_challenge ? `${state.active_challenge.name}: ${state.active_challenge.current_progress}/${state.active_challenge.progress_required}, hałas ${state.active_challenge.noise}` : 'Brak';
  document.getElementById('visible-environment').innerHTML = visibleEnvironmentHtml();
  document.getElementById('resources').innerHTML = state.resources.map(r => `<div>${r.label}</div>`).join('') || 'Brak';
  renderBoardPanel();
  document.getElementById('flow-panel').innerHTML = flowPanelHtml();
  const sceneHtml = sceneDescriptionHtml(state);
  document.getElementById('scene-description').innerHTML = sceneHtml;
  document.getElementById('scene-description-card').hidden = !sceneHtml;
  document.getElementById('messages').innerHTML = state.messages.map(m => `<div class="message"><b>${m.title}</b><br>${m.body}</div>`).join('');
  document.getElementById('pending').innerHTML = pendingHtml(state.pending);
  document.getElementById('lead-actor-choice').innerHTML = leadActorChoiceHtml();
  document.getElementById('result').innerHTML = resultAck ? `<div class="result"><b>${esc(resultAck.title)}</b><br>${esc(resultAck.body)}</div>` : '';
  document.getElementById('encounter').innerHTML = encounterHtml();
  document.getElementById('travel-options').innerHTML = travelOptionsHtml();
  document.getElementById('point-options').innerHTML = pointOptionsHtml();
  document.getElementById('roll-prompt').innerHTML = rollPromptHtml();
  document.getElementById('rolls').innerHTML = state.required_rolls.map(r => {
    const sides = Number(r.die_sides || 20);
    const value = sides === 100 ? 50 : 10;
    if (r.requires_second_roll) {
      return `<label>${esc(r.actor_name)} ${esc(r.label || `d${sides}`)} #1: <input data-actor="${esc(r.actor_id)}" data-roll-index="1" type="number" min="1" max="${sides}" value="${value}"></label>
        <label>${esc(r.actor_name)} ${esc(r.label || `d${sides}`)} #2: <input data-actor="${esc(r.actor_id)}" data-roll-index="2" type="number" min="1" max="${sides}" value="${value + 3 > sides ? value - 3 : value + 3}"></label>`;
    }
    return `<label>${esc(r.actor_name)} ${esc(r.label || `d${sides}`)}: <input data-actor="${esc(r.actor_id)}" data-roll-index="1" type="number" min="1" max="${sides}" value="${value}"></label>`;
  }).join(' ');
  document.getElementById('debug-payload').textContent = JSON.stringify(state, null, 2);
  renderSessionLogMeta();
  document.getElementById('action-title').textContent = state.active_point && state.active_point.has_npc ? 'Co robicie wobec NPC?' : 'Co robi drużyna?';
  updateActivePanel();
}
function renderBoardPanel() {
  const board = state.board || {};
  document.getElementById('board-status').textContent = `${board.message || 'Plansza niepodłączona.'} Domyślny backend z configu: ${board.configured_backend || '-'}.`;
  document.getElementById('board-backend').value = board.backend || 'none';
  document.getElementById('board-url').value = board.board_url || 'http://127.0.0.1:5000';
  document.getElementById('board-serial-port').value = board.board_serial_port || '';
  document.getElementById('wled-url').value = board.wled_url || '';
  document.getElementById('scan-timeout').value = board.scan_timeout_s || 30;
}
function esc(value) {
  return String(value || '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}
async function refreshSessionLog() {
  const res = await fetch('/api/session-log');
  sessionLog = await res.json();
  renderSessionLog();
}
function renderSessionLogMeta() {
  const meta = document.getElementById('session-log-meta');
  if (!meta || !state || !state.session_log) return;
  meta.innerHTML = `Session: <code>${esc(state.session_log.session_id)}</code><br>Plik: <code>${esc(state.session_log.path)}</code>`;
}
function renderSessionLog() {
  renderSessionLogMeta();
  const container = document.getElementById('session-log-events');
  if (!container) return;
  if (!sessionLog) {
    container.innerHTML = '<span class="muted">Log nie został jeszcze wczytany.</span>';
    return;
  }
  const filter = (document.getElementById('session-log-filter')?.value || '').trim().toLowerCase();
  const events = (sessionLog.events || []).filter(event => !filter || String(event.event_type || '').toLowerCase().includes(filter));
  if (!events.length) {
    container.innerHTML = '<span class="muted">Brak eventów dla aktualnego filtra.</span>';
    return;
  }
  container.innerHTML = events.slice().reverse().map(event => sessionLogEventHtml(event)).join('');
}
function sessionLogEventHtml(event) {
  const type = String(event.event_type || '');
  const payload = event.payload || {};
  const classes = ['log-event'];
  if (type === 'ui_effect_applied') classes.push('effect');
  if (['ui_action_submitted','ui_npc_proposal_validated','ui_gm_proposal_validated','ui_rolls_resolved','ui_effect_applied','ui_challenge_resolved'].includes(type)) {
    classes.push('important');
  }
  const summary = sessionLogSummary(type, payload);
  return `
    <div class="${classes.join(' ')}">
      <div class="event-head">
        <div><code>${esc(type)}</code> <span class="muted">#${esc(event.seq)}</span></div>
        <div class="muted">${esc(event.ts || '')}</div>
      </div>
      ${summary ? `<div>${summary}</div>` : ''}
      <details><summary>Payload JSON</summary><pre>${esc(JSON.stringify(payload, null, 2))}</pre></details>
    </div>
  `;
}
function sessionLogSummary(type, payload) {
  if (type === 'ui_action_submitted') return `Deklaracja: ${esc(payload.text || '')}`;
  if (type === 'ui_effect_applied') {
    const effect = payload.effect || {};
    return `Efekt: ${esc(payload.effect_type || effect.type || '')}; źródło: ${esc(payload.source || '')}; zmiana stanu: ${payload.changed ? 'tak' : 'nie'}`;
  }
  if (type === 'ui_npc_proposal_validated') return `NPC point: ${esc(payload.point_id || '')}`;
  if (type === 'ui_gm_proposal_validated') return `Challenge: ${esc(payload.challenge_id || '')}`;
  if (type === 'ui_rolls_resolved') return `Rzuty dla: ${esc(payload.pending_kind || '')}`;
  if (type === 'ui_challenge_resolved') return `Challenge: ${esc(payload.challenge_id || '')}; completed: ${payload.completed ? 'tak' : 'nie'}`;
  if (type === 'ui_message_added') return `${esc(payload.title || '')}: ${esc(payload.body || '')}`;
  return '';
}
function listHtml(items) {
  if (!items || !items.length) return '';
  return `<ul>${items.map(item => `<li>${esc(item)}</li>`).join('')}</ul>`;
}
function sceneStatusHtml() {
  const items = state.scene_status || [];
  if (!items.length) return '<span class="muted">Brak zmian.</span>';
  return `<div class="status-list">${items.map(item => `
    <div class="status-item"><b>${esc(item.label)}</b><span>${esc(item.value)}</span></div>
  `).join('')}</div>`;
}
function flowPanelHtml() {
  const flow = state.flow || {};
  const stage = flow.stage || 'waiting_for_board';
  if (stage === 'waiting_for_board') {
    return `
      <div class="start-panel"><div class="inner">
        <h2>Wybierz planszę</h2>
        <p>Najpierw wybierz backend planszy w panelu po lewej: <b>symulator</b> albo <b>hardware</b>, a potem kliknij <b>Zastosuj</b>.</p>
        <p class="muted">Tryb „brak” zostaje tylko do testów technicznych i nie uruchamia normalnej sesji gracza.</p>
        <button class="start-button" disabled>Start</button>
      </div></div>
    `;
  }
  if (stage === 'ready_to_start') {
    return `
      <div class="start-panel"><div class="inner">
        <h2>Plansza gotowa</h2>
        <p>Backend planszy jest podłączony. Kliknij Start, żeby pokazać jawne elementy sceny na planszy.</p>
        <button class="start-button" onclick="startSession()">Start</button>
      </div></div>
    `;
  }
  if (stage === 'party_setup') {
    const setup = state.exploration_setup;
    if (setup && setup.current_step) {
      const step = setup.current_step || {};
      const hasPositions = Boolean(step.has_positions);
      const positions = (step.positions || []).map(pos => `(${pos[0]},${pos[1]})`).join(', ');
      return `
        <h3>Setup mapy ${Number(setup.current_index) + 1}/${setup.step_count}</h3>
        <p><b>${esc(step.label || '')}</b></p>
        <p>${esc(step.message || '')}</p>
        ${hasPositions ? `<p><b>Kolor:</b> ${esc(step.color || '-')}</p><p><b>Pola:</b> ${esc(positions)}</p>` : '<p class="muted">Ten krok jest tylko instrukcją i nie podświetla pól na planszy.</p>'}
        <p class="muted">${hasPositions ? 'Rozstaw elementy na fizycznej planszy. Jeśli potwierdzasz planszą, najpierw kliknij Skanuj planszę.' : 'Potwierdź, żeby przejść do pierwszego podświetlanego elementu mapy.'}</p>
        <div class="row"><button onclick="confirmExplorationSetup()">Potwierdź setup</button>${hasPositions ? '<button class="secondary" data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>' : ''}</div>
      `;
    }
    return `
      <h3>Setup drużyny</h3>
      <p>Ustaw figurkę drużyny na podświetlonym polu.</p>
      <button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>
      <p class="muted">Po uruchomieniu skanu kliknij podświetlone pole.</p>
    `;
  }
  if (stage === 'location_preview') {
    const preview = flow.preview_zone;
    if (!preview) {
      return `
        <h3>Jawne elementy sceny</h3>
        ${availableLocationsHtml(flow.available_locations || [])}
        <p>Kliknij Skanuj planszę, a potem wskaż element sceny.</p>
        <button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>
      `;
    }
    const image = preview.image_url ? `<img class="location-preview-image" src="${esc(preview.image_url)}" alt="${esc(preview.name)}">` : '';
    if (preview.available === false) {
      return `
        <h3>Podgląd elementu</h3>
        ${image}
        <p><b>${esc(preview.name)}</b></p>
        <p>${esc(preview.description || preview.summary || '')}</p>
        <div class="status">${esc(preview.locked_reason || 'Ten element jest jeszcze zablokowany.')}</div>
        <button class="secondary" data-allow-busy="true" onclick="cancelLocationPreview()">Wróć do wyboru elementów</button>
      `;
    }
    return `
      <h3>Podgląd elementu</h3>
      ${image}
      <p><b>${esc(preview.name)}</b></p>
      <p>${esc(preview.description || preview.summary || '')}</p>
      <p><b>Czy chcesz wejść w interakcję?</b> Potwierdź Enterem albo przyciskiem.</p>
      <div class="row"><button onclick="confirmLocationPreview()">Wejdź w eksplorację</button><button class="secondary" data-allow-busy="true" onclick="cancelLocationPreview()">Wróć do wyboru elementów</button></div>
    `;
  }
  if (stage === 'interaction_result') {
    const result = flow.interaction_result || {};
    const unlocked = result.unlocked_zones || [];
    const points = result.revealed_points || [];
    return `
      <h3>${esc(result.title || 'Wynik interakcji')}</h3>
      <div class="result">${esc(result.body || '')}</div>
      ${unlocked.length ? `<p><b>Odblokowano lokacje:</b></p><ul>${unlocked.map(zone => `<li>${esc(zone.name)}</li>`).join('')}</ul>` : ''}
      ${points.length ? `<p><b>Ujawniono punkty:</b></p><ul>${points.map(point => `<li>${esc(point.name)}</li>`).join('')}</ul>` : ''}
      <p class="muted">${esc(result.next_instruction || 'Zakończ interakcję, aby wrócić do wyboru lokacji.')}</p>
      <button onclick="finishInteraction()">Zakończ interakcję</button>
    `;
  }
  return '';
}
function availableLocationsHtml(locations) {
  if (!locations.length) return '<p>Brak jawnych elementów sceny.</p>';
  return `<ul>${locations.map(zone => {
    const status = zone.available === false ? `zablokowane: ${esc(zone.locked_reason || '')}` : 'dostępne';
    return `<li><b>${esc(zone.name)}</b>: kolor ${esc(colorNameForZone(zone))}, ${status}</li>`;
  }).join('')}</ul>`;
}
function colorNameForZone(zone) {
  return zone.color || 'kolor specjalny';
}
function visibleEnvironmentHtml() {
  const entries = state.visible_environment || [];
  if (!entries.length) return '<div class="muted">Brak jawnych elementów.</div>';
  return entries.map(entry => {
    const positions = (entry.positions || []).map(pos => `(${pos[0]},${pos[1]})`).join(', ');
    const blocked = entry.blocks_movement ? 'blokuje ruch' : 'można wejść';
    return `
      <div class="status-item" style="margin:6px 0">
        <b>${esc(entry.name)}</b>
        <span>${esc(entry.label || entry.type || '')}${entry.color ? ` | ${esc(entry.color)}` : ''}</span>
        <span>${positions ? `pola ${esc(positions)} | ` : ''}${esc(blocked)}</span>
      </div>
    `;
  }).join('');
}
function sceneDescriptionHtml(state) {
  const zone = state.current_zone || {};
  const challenge = state.active_challenge;
  const stage = state.flow ? state.flow.stage : 'location_active';
  if (stage !== 'location_active') {
    return '';
  }
  const parts = [
    `<p><b>${esc(zone.name)}</b></p>`,
    zone.image_url ? `<img class="scene-thumb" src="${esc(zone.image_url)}" alt="${esc(zone.name)}">` : '',
    zone.description ? `<p>${esc(zone.description)}</p>` : '',
    zone.summary ? `<p>${esc(zone.summary)}</p>` : '',
  ];
  if (zone.available_materials && zone.available_materials.length) {
    parts.push(`<p><b>Widoczne elementy otoczenia:</b></p>${listHtml(zone.available_materials)}`);
  }
    if (challenge) {
    parts.push(`<p><b>${esc(challenge.name)}</b></p>`);
    if (challenge.summary) parts.push(`<p>${esc(challenge.summary)}</p>`);
    parts.push(`<p><b>Postęp:</b> ${challenge.current_progress}/${challenge.progress_required}. <b>Hałas:</b> ${challenge.noise}.</p>`);
    if (challenge.complications && challenge.complications.length) {
      parts.push(`<p><b>Komplikacje:</b> ${challenge.complications.map(esc).join(', ')}</p>`);
    }
    if (challenge.options && challenge.options.length) {
      parts.push(challengeOptionsHtml(challenge.options));
    }
    const hasHints = (challenge.reasonable_approaches && challenge.reasonable_approaches.length)
      || (challenge.risk_notes && challenge.risk_notes.length);
    if (hasHints) {
      const hints = [];
      if (challenge.reasonable_approaches && challenge.reasonable_approaches.length) {
        hints.push(`<p><b>Sensowne podejścia:</b></p>${listHtml(challenge.reasonable_approaches)}`);
      }
      if (challenge.risk_notes && challenge.risk_notes.length) {
        hints.push(`<p><b>Ryzyka:</b></p>${listHtml(challenge.risk_notes)}`);
      }
      parts.push(`
        <button class="secondary" type="button" onclick="toggleHints()">Pokaż wskazówki MG</button>
        <div id="gm-hints" class="hint-panel" hidden>${hints.join('')}</div>
      `);
    }
  }
  if (state.active_point) {
    const point = state.active_point;
    parts.push(`<p><b>${esc(point.name)}</b></p>`);
    parts.push(point.description ? `<p>${esc(point.description)}</p>` : '');
    if (point.npc) {
      parts.push(`<p>${esc(point.npc.public_description)}</p>`);
      if (point.npc.current_state) parts.push(`<p><b>Stan NPC:</b> ${esc(point.npc.current_state)}</p>`);
    }
  }
  if (!challenge && state.travel_options && state.travel_options.length) {
    parts.push(`<p><b>Droga dalej jest otwarta.</b> Zakończ interakcję albo wybierz lokację na planszy.</p>`);
  }
  const html = parts.filter(Boolean).join('');
  return html.trim() ? html : '';
}
function challengeOptionsHtml(options) {
  return `
    <div class="status-list">
      ${options.map(option => {
        const skill = option.skill ? `/${esc(option.skill)}` : '';
        const requirements = challengeOptionRequirementsText(option);
        const actors = (option.eligible_actors || []).map(actor => actor.name).join(', ');
        return `
          <div class="status-item">
            <b>${esc(option.label)}</b>
            <div>${esc(option.description || '')}</div>
            ${option.mechanic ? `<div class="muted">Mechanika: ${esc(option.mechanic.label || option.mechanic.id)}</div>` : ''}
            <div class="muted">Test: ${esc(option.ability)}${skill}, ST ${esc(option.dc)}. Sukces +${esc(option.progress_on_success)}, porażka +${esc(option.progress_on_failure)}.</div>
            ${requirements ? `<div class="muted">Wymaga: ${requirements}</div>` : ''}
            ${challengeOptionBonusesText(option) ? `<div class="muted">Premie: ${challengeOptionBonusesText(option)}</div>` : ''}
            ${actors ? `<div class="muted">Może wykonać: ${esc(actors)}</div>` : ''}
          </div>
        `;
      }).join('')}
    </div>
  `;
}
function challengeOptionRequirementsText(option) {
  const parts = [];
  if (option.requires_item_ids && option.requires_item_ids.length) parts.push(`item ${option.requires_item_ids.map(esc).join(', ')}`);
  if (option.requires_spell_ids && option.requires_spell_ids.length) parts.push(`czar ${option.requires_spell_ids.map(esc).join(', ')}`);
  if (option.requires_ability_scores && option.requires_ability_scores.length) {
    parts.push(option.requires_ability_scores.map(req => `${esc(req.ability)} ${esc(req.minimum)}`).join(', '));
  }
  return parts.join('; ');
}
function challengeOptionBonusesText(option) {
  const bonuses = option.bonuses || [];
  return bonuses.map(bonus => {
    const mod = Number(bonus.modifier || 0);
    const breakage = bonus.breakage_risk ? `, ryzyko uszkodzenia ${esc(bonus.breakage_risk.chance_percent)}% przy krytycznej porażce` : '';
    const spellLevel = Number(bonus.spell_level || 0);
    const spellCost = bonus.source_type === 'spell' ? (spellLevel > 0 ? `, zużywa slot ${spellLevel}. poziomu` : ', cantrip bez slota') : '';
    return `${esc(bonus.label || bonus.source_id)} ${signedNumber(mod)}${spellCost}${breakage}`;
  }).join('; ');
}
function toggleHints() {
  const panel = document.getElementById('gm-hints');
  if (!panel) return;
  panel.hidden = !panel.hidden;
  const button = panel.previousElementSibling;
  if (button) button.textContent = panel.hidden ? 'Pokaż wskazówki MG' : 'Ukryj wskazówki MG';
}
function pendingHtml(pending) {
  if (!pending) return '';
  const proposal = pending.proposal || {};
  const option = pending.option || {};
  const lines = [];
  if (proposal.player_narration) lines.push(`<p>${esc(proposal.player_narration)}</p>`);
  if (proposal.npc_response) lines.push(`<p><b>NPC:</b> ${esc(proposal.npc_response)}</p>`);
  if (option.label) {
    const skill = option.skill ? `/${esc(option.skill)}` : '';
    if (option.mechanic) lines.push(`<p><b>Mechanika:</b> ${esc(option.mechanic.label || option.mechanic.id)}.</p>`);
    lines.push(`<p><b>Podejście:</b> ${esc(option.label)}. Test: ${esc(option.ability)}${skill}, ST ${esc(option.dc)}.</p>`);
    if (option.roll_mode && option.roll_mode !== 'normal') lines.push(`<p><b>Tryb rzutu:</b> ${esc(option.roll_mode)}.</p>`);
    if (option.situational_modifiers && option.situational_modifiers.length) {
      lines.push(`<p><b>Modyfikatory sytuacyjne:</b> ${option.situational_modifiers.map(mod => `${esc(mod.label)} ${signedNumber(Number(mod.modifier || 0))}${mod.roll_mode && mod.roll_mode !== 'normal' ? `, ${esc(mod.roll_mode)}` : ''} (${esc(mod.source)}: ${esc(mod.reason)})`).join('; ')}</p>`);
    }
    if (option.improvised_tool) {
      const tool = option.improvised_tool;
      lines.push(`<p><b>Improwizowane narzędzie:</b> ${esc(tool.label)} ${signedNumber(Number(tool.effect_modifier || 0))} (${esc(tool.source)}: ${esc(tool.source_detail)}${tool.risk ? `, ryzyko: ${esc(tool.risk)}` : ''}). ${esc(tool.reason)}</p>`);
    }
    lines.push(`<p><b>Postęp:</b> sukces +${esc(option.progress_on_success)}, porażka +${esc(option.progress_on_failure)}.</p>`);
    if (pending.kind === 'challenge' && pending.stage === 'decision') {
      lines.push(`<button class="secondary" onclick="toggleDecisionCorrection()">Popraw decyzję MG</button>`);
      if (decisionCorrectionOpen) lines.push(decisionCorrectionHtml(option));
    }
  } else if (proposal.action_type) {
    if (proposal.requires_roll) {
      const skill = proposal.skill ? `/${esc(proposal.skill)}` : '';
      lines.push(`<p><b>Akcja:</b> ${esc(proposal.action_type)}. Test: ${esc(proposal.ability)}${skill}, ST ${esc(proposal.dc)}.</p>`);
    } else {
      lines.push(`<p><b>Akcja:</b> ${esc(proposal.action_type)}. Bez rzutu.</p>`);
    }
  }
  return lines.join('') || '<p>MG proponuje interpretację deklaracji.</p>';
}
function leadActorChoiceHtml() {
  if (!state.pending || state.pending.stage !== 'decision' || !state.actors || state.actors.length < 2) return '';
  const selectedId = state.selected_lead_actor_id || (state.actors[0] && state.actors[0].id) || '';
  const options = state.actors.map(actor => `<option value="${esc(actor.id)}"${String(actor.id) === String(selectedId) ? ' selected' : ''}>${esc(actor.name)}</option>`).join('');
  return `<label><b>Kto prowadzi test?</b> <select id="lead-actor">${options}</select></label>`;
}
function decisionCorrectionHtml(option) {
  const mechanicId = option.mechanic && option.mechanic.id ? option.mechanic.id : 'single_actor_check';
  const actorOptions = (selectedId, allowEmpty=false) => `${allowEmpty ? '<option value="">-</option>' : ''}${(state.actors || []).map(actor => `<option value="${esc(actor.id)}"${String(actor.id) === String(selectedId || '') ? ' selected' : ''}>${esc(actor.name)}</option>`).join('')}`;
  const mechanicOptions = (state.allowed_mechanics || []).map(tool => `<option value="${esc(tool.id)}"${tool.id === mechanicId ? ' selected' : ''}>${esc(tool.label || tool.id)}</option>`).join('');
  const participants = option.check_participants || (option.mechanic && option.mechanic.participants ? option.mechanic.participants : 'single_actor');
  const aggregation = option.check_aggregation || (participants === 'whole_party' ? 'highest' : 'lead_result');
  const abilityOptions = ['strength','dexterity','constitution','intelligence','wisdom','charisma'].map(ability => `<option value="${ability}"${ability === option.ability ? ' selected' : ''}>${ability}</option>`).join('');
  const rollMode = option.roll_mode || 'normal';
  const rollModeOptions = ['normal','advantage','disadvantage'].map(mode => `<option value="${mode}"${mode === rollMode ? ' selected' : ''}>${mode}</option>`).join('');
  const sourceOptions = selectedSource => ['scenario_context','zone_context','challenge_context','interaction_object','player_declaration','dynamic_state','gm'].map(source => `<option value="${source}"${source === selectedSource ? ' selected' : ''}>${source}</option>`).join('');
  const situational = option.situational_modifiers || [];
  const improvised = option.improvised_tool || {};
  const modifierRows = [0,1,2].map(index => {
    const mod = situational[index] || {};
    const modMode = mod.roll_mode || 'normal';
    const modModeOptions = ['normal','advantage','disadvantage'].map(mode => `<option value="${mode}"${mode === modMode ? ' selected' : ''}>${mode}</option>`).join('');
    return `<div class="card" data-situational-row="${index}">
      <label>Etykieta <input class="correction-sit-label" value="${esc(mod.label || '')}" placeholder="np. Mokra lina"></label>
      <label>Premia/kara <input class="correction-sit-modifier" type="number" min="-2" max="2" value="${esc(mod.modifier || 0)}"></label>
      <label>Tryb <select class="correction-sit-roll-mode">${modModeOptions}</select></label>
      <label>Źródło <select class="correction-sit-source">${sourceOptions(mod.source || 'gm')}</select></label>
      <label>Powód <input class="correction-sit-reason" value="${esc(mod.reason || '')}" placeholder="Dlaczego ten fakt wpływa na test"></label>
    </div>`;
  }).join('');
  return `
    <div class="card" style="margin-top:10px">
      <h4>Korekta przed rzutem</h4>
      <label>Mechanika <select id="correction-mechanic">${mechanicOptions}</select></label>
      <label>Uczestnicy
        <select id="correction-participants">
          <option value="single_actor"${participants === 'single_actor' ? ' selected' : ''}>jedna postać</option>
          <option value="lead_with_help"${participants === 'lead_with_help' ? ' selected' : ''}>prowadzący z pomocą</option>
          <option value="whole_party"${participants === 'whole_party' ? ' selected' : ''}>cała drużyna</option>
          <option value="selected_actors"${participants === 'selected_actors' ? ' selected' : ''}>wybrane postacie</option>
        </select>
      </label>
      <label>Agregacja
        <select id="correction-aggregation">
          <option value="lead_result"${aggregation === 'lead_result' ? ' selected' : ''}>wynik prowadzącego</option>
          <option value="highest"${aggregation === 'highest' ? ' selected' : ''}>najwyższy wynik</option>
          <option value="lowest"${aggregation === 'lowest' ? ' selected' : ''}>najniższy wynik</option>
          <option value="majority"${aggregation === 'majority' ? ' selected' : ''}>większość sukcesów</option>
          <option value="all_must_succeed"${aggregation === 'all_must_succeed' ? ' selected' : ''}>wszyscy muszą zdać</option>
          <option value="any_success"${aggregation === 'any_success' ? ' selected' : ''}>wystarczy jeden sukces</option>
          <option value="sum_progress"${aggregation === 'sum_progress' ? ' selected' : ''}>suma postępu</option>
        </select>
      </label>
      <label>Prowadzący <select id="correction-lead">${actorOptions(state.selected_lead_actor_id)}</select></label>
      <label>Pomocnik <select id="correction-helper">${actorOptions(state.selected_helper_actor_id, true)}</select></label>
      <label>Cecha <select id="correction-ability">${abilityOptions}</select></label>
      <label>Skill <input id="correction-skill" value="${esc(option.skill || '')}" placeholder="np. athletics"></label>
      <label>ST <input id="correction-dc" type="number" min="5" max="25" value="${esc(option.dc || 10)}"></label>
      <label>Tryb rzutu <select id="correction-roll-mode">${rollModeOptions}</select></label>
      <details>
        <summary>Modyfikatory sytuacyjne</summary>
        ${modifierRows}
      </details>
      <details>
        <summary>Improwizowane narzędzie</summary>
        <label>Nazwa <input id="improvised-tool-label" value="${esc(improvised.label || '')}" placeholder="np. Stara deska"></label>
        <label>Źródło <select id="improvised-tool-source">${sourceOptions(improvised.source || 'interaction_object')}</select></label>
        <label>Szczegół źródła <input id="improvised-tool-source-detail" value="${esc(improvised.source_detail || '')}" placeholder="np. rumowisko przy bramie"></label>
        <label>Efekt <input id="improvised-tool-effect" type="number" min="-2" max="2" value="${esc(improvised.effect_modifier || 0)}"></label>
        <label>Ryzyko <input id="improvised-tool-risk" value="${esc(improvised.risk || '')}" placeholder="np. pęka przy krytycznej porażce"></label>
        <label>Powód <input id="improvised-tool-reason" value="${esc(improvised.reason || '')}" placeholder="Dlaczego to działa jak prowizoryczne narzędzie"></label>
      </details>
      <div class="row" style="margin-top:8px">
        <button onclick="submitDecisionCorrection()">Zapisz korektę</button>
      </div>
    </div>`;
}
function toggleDecisionCorrection() {
  decisionCorrectionOpen = !decisionCorrectionOpen;
  render();
}
function rollPromptHtml() {
  if (!state.pending) return '';
  if (state.pending.stage === 'breakage') {
    const info = state.pending.breakage || {};
    return `<p><b>Test trwałości:</b> rzuć k100 dla ${esc(info.item_label || info.item_id || 'przedmiotu')}. Wynik ${esc(info.chance_percent || 0)} lub mniej oznacza uszkodzenie.</p>`;
  }
  if (state.pending.stage !== 'roll') return '';
  const plan = state.pending.check_plan || {};
  const participants = {
    single_actor: 'rzuca jeden wybrany bohater',
    lead_with_help: 'rzuca prowadzący z pomocą',
    whole_party: 'rzuca cała drużyna',
    selected_actors: 'rzucają wybrani bohaterowie'
  }[plan.participants] || plan.participants || 'rzut eksploracyjny';
  const aggregation = {
    lead_result: 'liczy się wynik prowadzącego',
    highest: 'liczy się najwyższy wynik',
    lowest: 'liczy się najniższy wynik',
    majority: 'sukces, jeśli zda co najmniej połowa'
  }[plan.aggregation] || plan.aggregation || '';
  const names = (state.required_rolls || []).map(r => r.actor_name).join(', ');
  const mechanic = plan.mechanic || {};
  const mechanicHtml = mechanic.id ? `<p><b>Mechanika:</b> ${esc(mechanic.label || mechanic.id)}</p>` : '';
  const rollModeHtml = plan.roll_mode && plan.roll_mode !== 'normal' ? `<p><b>Tryb rzutu:</b> ${esc(plan.roll_mode)}.</p>` : '';
  const situationalHtml = plan.situational_modifiers && plan.situational_modifiers.length
    ? `<p><b>Modyfikatory sytuacyjne:</b> ${plan.situational_modifiers.map(mod => `${esc(mod.label)} ${signedNumber(Number(mod.modifier || 0))}${mod.roll_mode && mod.roll_mode !== 'normal' ? `, ${esc(mod.roll_mode)}` : ''} (${esc(mod.reason)})`).join('; ')}</p>`
    : '';
  const tool = plan.improvised_tool || null;
  const improvisedHtml = tool
    ? `<p><b>Improwizowane narzędzie:</b> ${esc(tool.label)} ${signedNumber(Number(tool.effect_modifier || 0))} (${esc(tool.source_detail)}${tool.risk ? `, ryzyko: ${esc(tool.risk)}` : ''}).</p>`
    : '';
  const bonuses = (plan.option_bonuses || []).filter(bonus => Number(bonus.modifier || 0) !== 0);
  const bonusHtml = bonuses.length
    ? `<p><b>Aktywne premie:</b> ${bonuses.map(bonus => {
        const spellLevel = Number(bonus.spell_level || 0);
        const spellCost = bonus.source_type === 'spell' ? (spellLevel > 0 ? `, zużyje slot ${spellLevel}. poziomu` : ', cantrip bez slota') : '';
        return `${esc(bonus.actor_name || '')}: ${esc(bonus.label || bonus.source_id)} ${signedNumber(Number(bonus.modifier || 0))}${spellCost}`;
      }).join('; ')}</p>`
    : '';
  return `${mechanicHtml}${rollModeHtml}<p><b>Format rzutu:</b> ${esc(participants)}${aggregation ? `, ${esc(aggregation)}` : ''}.</p><p><b>Rzucają:</b> ${esc(names || '-')}</p>${situationalHtml}${improvisedHtml}${bonusHtml}`;
}
function latestResultMessage(state) {
  const messages = state.messages || [];
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (messages[i].title && messages[i].title.startsWith('Wynik')) return messages[i];
  }
  return messages[messages.length - 1] || null;
}
function travelOptionsHtml() {
  const zones = state.travel_options || [];
  if (!zones.length) return '<p>Brak dostępnych przejść z tej lokacji.</p>';
  return zones.map(zone => `
    <div class="row" style="justify-content:space-between; margin: 6px 0">
      <div><b>${esc(zone.name)}</b><br><span class="muted">${esc(zone.description)}</span></div>
      <button onclick="travel('${esc(zone.id)}')">Przejdź</button>
    </div>
  `).join('');
}
function encounterHtml() {
  const encounter = state.pending_encounter;
  if (!encounter) return '';
  if (state.combat) return combatStartHtml();
  const setup = state.encounter_setup;
  const initiative = state.encounter_initiative;
  const setupHtml = encounterSetupHtml(setup);
  const initiativeHtml = encounterInitiativeHtml(setup, initiative);
  const combatHtml = combatStartHtml();
  return `
    <p><b>${esc(encounter.name)}</b></p>
    <p>${esc(encounter.description)}</p>
    <p><b>Powód:</b> ${esc(encounter.reason)}</p>
    <p><b>Scenariusz encountera:</b> ${esc(encounter.encounter_scenario)}</p>
    ${setupHtml}
    ${initiativeHtml}
    ${combatHtml}
    ${state.combat ? '' : `<details class="debug-panel"><summary>Komenda awaryjna terminala</summary><pre>${esc(encounter.command)}</pre></details>`}
  `;
}
function encounterSetupHtml(setup) {
  if (!setup) {
    return `
      <div class="message"><b>Setup przed walką</b><br>Rozpocznijcie setup encountera. Jawne elementy sceny są już na planszy.</div>
      <button onclick="startEncounterSetup()">Rozpocznij setup</button>
    `;
  }
  if (setup.status === 'completed') {
    return '<div class="result"><b>Setup zakończony</b><br>Plansza jest przygotowana do inicjatywy i walki.</div>';
  }
  const step = setup.current_step || {};
  const hasPositions = Boolean(step.has_positions);
  const requiresBoardAssignment = Boolean(step.requires_board_assignment);
  const positions = (step.positions || []).map(pos => `(${pos[0]},${pos[1]})`).join(', ');
  const availablePositions = (step.available_positions || step.positions || []).map(pos => `(${pos[0]},${pos[1]})`).join(', ');
  const assignmentButtons = (step.available_positions || []).map(pos =>
    `<button class="secondary" onclick="selectBoardPosition(${Number(pos[0])}, ${Number(pos[1])})">(${Number(pos[0])},${Number(pos[1])})</button>`
  ).join('');
  return `
    <div class="message">
      <b>Krok ${Number(setup.current_index) + 1}/${setup.step_count}: ${esc(step.label || '')}</b><br>
      ${esc(step.message || '')}
      ${requiresBoardAssignment ? `<p><b>Aktualnie ustaw:</b> ${esc(step.assignment_actor_name || '-')}</p><p><b>Wolne pola:</b> ${esc(availablePositions || '-')}</p>` : ''}
      ${hasPositions && !requiresBoardAssignment ? `<p><b>Kolor:</b> ${esc(step.color || '-')}</p><p><b>Pola:</b> ${esc(positions)}</p>` : ''}
      ${!hasPositions ? '<p class="muted">Ten krok jest tylko instrukcją i nie podświetla pól na planszy.</p>' : ''}
    </div>
    ${requiresBoardAssignment
      ? `<div class="row"><button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>${assignmentButtons}</div><p class="muted">Postaw figurkę wskazanego bohatera na podświetlonym polu i uruchom skan. Przyciski pól są awaryjnym wyborem bez skanu planszy. Po ostatnim bohaterze gra przejdzie dalej.</p>`
      : '<button onclick="confirmEncounterSetup()">Potwierdź krok setupu</button>'}
  `;
}
function encounterInitiativeHtml(setup, initiative) {
  if (!setup || setup.status !== 'completed' || state.combat) return '';
  if (!initiative) {
    return `
      <div class="message"><b>Inicjatywa</b><br>Setup zakończony. Teraz ustalcie kolejność tur.</div>
      <button onclick="startEncounterInitiative()">Rozpocznij inicjatywę</button>
    `;
  }
  if (initiative.status === 'completed') return '';
  const prompt = initiative.current_prompt || {};
  return `
    <div class="message">
      <b>Rzut inicjatywy ${Number(initiative.current_prompt_index) + 1}/${initiative.prompt_count}</b><br>
      ${esc(prompt.message || 'Wpisz naturalny wynik d20.')}
    </div>
    <div class="row">
      <label>Wynik d20: <input id="encounter-initiative-roll" type="number" min="1" max="20" value="10"></label>
      <button onclick="submitEncounterInitiativeRoll()">Zapisz rzut</button>
    </div>
  `;
}
function combatStartHtml() {
  const combat = state.combat;
  if (!combat) return '';
  const order = state.encounter_initiative && state.encounter_initiative.order ? state.encounter_initiative.order : [];
  const actors = combat.actors || [];
  const finished = combat.status === 'finished';
  const actor = combat.current_actor || {};
  const isAllyTurn = actor.faction === 'ally';
  const isEnemyTurn = actor.faction === 'enemy';
  return `
    <div class="combat-stage">
      ${combatCurrentStepHtml(combat, finished, isAllyTurn, isEnemyTurn)}
      ${combatActiveEffectsHtml(combat)}
      ${combatLastResultHtml()}
    </div>
    <details class="combat-details">
      <summary>Szczegóły walki</summary>
      <section class="combat-section">
        <h4>Aktualny aktor</h4>
        ${combatActorStatusHtml(combat)}
      </section>
      <section class="combat-section">
        <h4>Szczegóły aktualnego kroku</h4>
        ${combatActionDetailsHtml(combat, isAllyTurn, isEnemyTurn)}
      </section>
      <section class="combat-section">
        <h4>Wszystkie aktywne efekty</h4>
        ${combatAllEffectsHtml(combat)}
      </section>
      <p><b>Kolejność inicjatywy:</b> ${order.map(entry => `${esc(entry.actor_name)} (${entry.total})`).join(', ')}</p>
      <div class="status-list">
        ${actors.map(actor => `
          <div class="status-item${actor.defeated ? ' defeated' : ''}">
            <b>${esc(actor.name)} ${actor.id === combat.current_actor.id ? '(tura)' : ''}</b>
            <span>${esc(actor.faction)} | HP ${esc(actorHpLabel(actor))} / AC ${esc(actor.ac)} | pole (${esc(actor.position[0])},${esc(actor.position[1])})</span>
            ${statusChipsHtml(actor.status_chips || actorEffectChips(actor), 'Brak aktywnych statusów.')}
          </div>
        `).join('')}
      </div>
    </details>
  `;
}
function combatCurrentStepHtml(combat, finished, isAllyTurn, isEnemyTurn) {
  return `
    <div class="combat-current-step">
      ${combatMainPromptHtml(combat, finished, isAllyTurn, isEnemyTurn)}
      ${combatMiniStatusHtml(combat)}
      <div class="combat-action-card">
        ${finished ? '<button onclick="resolveCombatOutcome()">Zastosuj wynik walki</button>' : combatPrimaryActionHtml(combat, isAllyTurn, isEnemyTurn)}
      </div>
    </div>
  `;
}
function combatMainPromptHtml(combat, finished, isAllyTurn, isEnemyTurn) {
  return `
    <div class="combat-prompt">
      <b>${esc(combatPromptTitle(combat, finished, isAllyTurn, isEnemyTurn))}</b>
      <span>${esc(combatInstructionText(combat, finished, isAllyTurn, isEnemyTurn))}</span>
    </div>
  `;
}
function combatPromptTitle(combat, finished, isAllyTurn, isEnemyTurn) {
  if (finished) return 'Walka zakończona';
  const actor = combat.current_actor || {};
  if (combat.pending_concentration_check) {
    const pendingActor = combat.pending_concentration_check.actor || {};
    return `${pendingActor.name || 'Bohater'}: test koncentracji`;
  }
  if (isEnemyTurn) {
    if (combat.pending_ready_attack) return `Tura ${actor.name || 'przeciwnika'}: Ready`;
    if (combat.pending_enemy_opportunity_attack) return `Tura ${actor.name || 'przeciwnika'}: reakcja bohatera`;
    if (combat.enemy_turn_result) return `Tura ${actor.name || 'przeciwnika'}: potwierdź wynik`;
    if (combat.enemy_turn_intent) return `Tura ${actor.name || 'przeciwnika'}: zamiar`;
    if (combat.enemy_turn_preview) return `Tura ${actor.name || 'przeciwnika'}: potwierdź planszą`;
    return `Tura ${actor.name || 'przeciwnika'}: rozegraj zamiar`;
  }
  if (isAllyTurn && combat.pending_player_attack) {
    if (combat.pending_player_attack.stage === 'confirm_attack') return `Tura ${actor.name || 'gracza'}: potwierdź atak`;
    return combat.pending_player_attack.stage === 'damage_roll'
      ? `Tura ${actor.name || 'gracza'}: wpisz obrażenia`
      : `Tura ${actor.name || 'gracza'}: rzuć d20`;
  }
  if (isAllyTurn && combat.pending_player_healing) return `Tura ${actor.name || 'gracza'}: wpisz leczenie`;
  if (isAllyTurn && combat.pending_area_spell) {
    return combat.pending_area_spell.stage === 'damage_roll'
      ? `Tura ${actor.name || 'gracza'}: obrażenia obszarowe`
      : `Tura ${actor.name || 'gracza'}: potwierdź obszar`;
  }
  if (isAllyTurn && combat.pending_opportunity_movement) return `Tura ${actor.name || 'gracza'}: atak okazyjny`;
  if (isAllyTurn && combat.pending_combat_help) return `Tura ${actor.name || 'gracza'}: Help`;
  if (isAllyTurn && combat.pending_concentration_action) return `Tura ${actor.name || 'gracza'}: koncentracja`;
  if (isAllyTurn && combat.pending_combat_ready) return `Tura ${actor.name || 'gracza'}: Ready`;
  if (isAllyTurn && combat.pending_combat_interaction) return `Tura ${actor.name || 'gracza'}: wybierz interakcję`;
  if (isAllyTurn && combat.movement_preview) return `Tura ${actor.name || 'gracza'}: potwierdź ruch`;
  if (isAllyTurn) return `Tura ${actor.name || 'gracza'}: wybierz ruch, cel albo obiekt`;
  return `Tura ${actor.name || '-'}`;
}
function combatInstructionText(combat, finished, isAllyTurn, isEnemyTurn) {
  if (finished) return 'Zastosuj wynik walki, żeby wrócić do eksploracji.';
  const actor = combat.current_actor || {};
  if (combat.pending_concentration_check) {
    return combat.pending_concentration_check.instruction || 'Rzuć CON save, żeby utrzymać koncentrację.';
  }
  if (isEnemyTurn) {
    if (combat.pending_ready_attack) {
      const pendingReady = combat.pending_ready_attack;
      const attacker = pendingReady.attacker || {};
      const target = pendingReady.target || {};
      if (pendingReady.stage === 'choice') return `Warunek Ready został spełniony. ${attacker.name || 'Bohater'} może zaatakować ${target.name || 'przeciwnika'}.`;
      if (pendingReady.stage === 'damage_roll') return `Trafienie przygotowaną akcją. Rzuć obrażenia ${pendingReady.damage_instruction || ''} i wpisz wynik.`;
      return `${attacker.name || 'Bohater'} używa przygotowanej akcji. Rzuć d20 i wpisz naturalny wynik.`;
    }
    if (combat.pending_enemy_opportunity_attack) {
      const pendingOpportunity = combat.pending_enemy_opportunity_attack;
      const attacker = pendingOpportunity.attacker || {};
      const target = pendingOpportunity.target || {};
      if (pendingOpportunity.stage === 'choice') return `${target.name || 'Przeciwnik'} opuszcza zasięg ${attacker.name || 'bohatera'}. Wykonaj atak okazyjny albo pomiń reakcję.`;
      if (pendingOpportunity.stage === 'damage_roll') return `Trafienie atakiem okazyjnym. Rzuć obrażenia ${pendingOpportunity.damage_instruction || ''} i wpisz wynik.`;
      return `${attacker.name || 'Bohater'} wykonuje atak okazyjny. Rzuć d20 i wpisz naturalny wynik.`;
    }
    if (combat.enemy_turn_result) return 'Przeczytaj wynik tury przeciwnika i potwierdź go Enterem albo przyciskiem.';
    const intent = combat.enemy_turn_intent || null;
    if (intent) return `${intent.message || 'Przeciwnik deklaruje zamiar.'} Potwierdź, żeby przejść do wykonania na planszy.`;
    const preview = combat.enemy_turn_preview || null;
    if (preview && preview.kind === 'movement') {
      return `Przestaw ${preview.enemy_name} na pole (${preview.destination[0]},${preview.destination[1]}), uruchom skan i kliknij pole docelowe.`;
    }
    if (preview && preview.kind === 'attack') {
      return `${preview.enemy_name} atakuje ${preview.target_name}. Uruchom skan i kliknij podświetlony cel.`;
    }
    return 'Naciśnij Enter albo przycisk, żeby gra pokazała zamiar przeciwnika.';
  }
  if (!isAllyTurn) return 'Ten aktor nie ma automatycznych kontrolek w MVP. Możesz zakończyć turę.';
  if (combat.pending_opportunity_movement) {
    const pendingOpportunity = combat.pending_opportunity_movement;
    const names = (pendingOpportunity.threats || []).map(actor => actor.name).join(', ') || 'wróg';
    return `Ten ruch opuszcza zasięg: ${names}. Potwierdź, żeby rozstrzygnąć ataki okazyjne i wykonać ruch.`;
  }
  if (combat.pending_combat_help) {
    return 'Wybierz sojusznika i przeciwnika. Sojusznik dostanie przewagę na następny atak przeciw temu celowi.';
  }
  if (combat.pending_concentration_action) {
    return 'Wybierz sojusznika. Czar zużyje akcję i slot, a wcześniejsza koncentracja tego aktora zostanie zakończona.';
  }
  if (combat.pending_combat_ready) {
    return 'Wybierz warunek. Akcja zostanie zużyta teraz, a atak będzie można wykonać później reakcją.';
  }
  const pending = combat.pending_player_attack || null;
  if (pending) {
    const target = pending.target || {};
    const source = pending.source || {};
    if (pending.stage === 'confirm_attack') {
      if (source.save_ability) {
        return `Wybrano ${target.name || '-'}. Potwierdź czar, żeby przeciwnik wykonał automatyczny rzut obronny.`;
      }
      return `Wybrano ${target.name || '-'}. Potwierdź atak, żeby przejść do rzutu d20.`;
    }
    if (pending.stage === 'damage_roll') {
      return `Trafiono ${target.name || 'cel'}. Rzuć obrażenia ${pending.damage_instruction || source.damage_hint || ''} i wpisz wynik.`;
    }
    return `Wybrano cel ${target.name || '-'}. Rzuć d20 na atak ${source.name || ''} i wpisz naturalny wynik.`;
  }
  const pendingHealing = combat.pending_player_healing || null;
  if (pendingHealing) {
    const target = pendingHealing.target || {};
    const source = pendingHealing.source || {};
    return `Wybrano ${target.name || '-'}. Rzuć leczenie ${source.healing_hint || ''} i wpisz sumę.`;
  }
  const pendingArea = combat.pending_area_spell || null;
  if (pendingArea) {
    const source = pendingArea.source || {};
    const targets = (pendingArea.targets || []).map(target => target.name).join(', ') || 'brak celów';
    if (pendingArea.stage === 'damage_roll') return `Rzuć obrażenia ${source.damage_hint || ''} i wpisz sumę dla celów w obszarze.`;
    return `Wybrano obszar ${source.name || 'czaru'}. Cele: ${targets}. Potwierdź Enterem albo przyciskiem.`;
  }
  if (combat.pending_combat_interaction) {
    const pendingInteraction = combat.pending_combat_interaction;
    return `Wybrano obiekt ${pendingInteraction.object_name || '-'}. Wybierz interakcję i potwierdź przyciskiem albo Enterem.`;
  }
  const movement = combat.movement || {};
  const preview = combat.movement_preview || null;
  const remaining = Number(movement.remaining_feet || 0);
  const extraMovement = Number((combat.turn_action && combat.turn_action.extra_movement_feet) || 0);
  const actionUsed = combat.turn_action && combat.turn_action.action_use === 'action_used';
  if (preview) {
    return `Wybrano ruch na (${preview.destination[0]},${preview.destination[1]}). Uruchom skan i kliknij pole docelowe, żeby zatwierdzić.`;
  }
  if (actionUsed && remaining > 0) return `Akcja zużyta. Możesz jeszcze ruszyć się (${remaining} ft) albo zakończyć turę.`;
  if (actionUsed) return 'Akcja zużyta. Możesz zakończyć turę.';
  if (remaining > 0) return `Kliknij Skanuj planszę, a potem wybierz niebieskie pole ruchu, czerwony cel, turkusowego rannego sojusznika albo zielony obiekt.`;
  return 'Ruch wykorzystany. Możesz zaatakować czerwony cel, uleczyć turkusowego sojusznika, użyć zielonego obiektu albo zakończyć turę.';
}
function combatMiniStatusHtml(combat) {
  const actor = combat.current_actor || {};
  const movement = combat.movement || {};
  const remaining = Number(movement.remaining_feet || 0);
  const extraMovement = Number((combat.turn_action && combat.turn_action.extra_movement_feet) || 0);
  const actionUsed = combat.turn_action && combat.turn_action.action_use === 'action_used';
  const bonusActionUsed = combat.turn_action && combat.turn_action.bonus_action_use === 'action_used';
  const reactionAvailable = !combat.turn_action || combat.turn_action.reaction_available !== false;
  const position = actor.position || ['-', '-'];
  return `
    <div class="combat-mini-status">
      <span>Runda ${esc(combat.round_number || '-')}</span>
      <span>${esc(actor.name || '-')}</span>
      <span>HP ${esc(actorHpLabel(actor))} / AC ${esc(actor.ac)}</span>
      <span>Pole (${esc(position[0])},${esc(position[1])})</span>
      ${actor.faction === 'ally' ? `<span>Akcja: ${actionUsed ? 'zużyta' : 'dostępna'}</span><span>Bonus: ${bonusActionUsed ? 'zużyta' : 'dostępna'}</span><span>Reakcja: ${reactionAvailable ? 'dostępna' : 'zużyta'}</span><span>Ruch: ${esc(remaining)} ft${extraMovement > 0 ? ` (+${esc(extraMovement)} Dash)` : ''}</span>` : ''}
    </div>
    ${statusChipsHtml(actor.status_chips || [], 'Brak statusów aktywnego aktora.')}
  `;
}
function combatActorStatusHtml(combat) {
  const actor = combat.current_actor || {};
  const movement = combat.movement || {};
  const remaining = Number(movement.remaining_feet || 0);
  const extraMovement = Number((combat.turn_action && combat.turn_action.extra_movement_feet) || 0);
  const actionUsed = combat.turn_action && combat.turn_action.action_use === 'action_used';
  const bonusActionUsed = combat.turn_action && combat.turn_action.bonus_action_use === 'action_used';
  const reactionAvailable = !combat.turn_action || combat.turn_action.reaction_available !== false;
  return `
    <p><b>${esc(actor.name || '-')}</b> (${esc(actor.faction || '-')})</p>
    <p>Runda ${esc(combat.round_number || '-')}, pole (${esc(actor.position ? actor.position[0] : '-')},${esc(actor.position ? actor.position[1] : '-')})</p>
    <p>HP ${esc(actorHpLabel(actor))} / AC ${esc(actor.ac)}</p>
    ${actorInventoryHtml(actor)}
    ${actor.faction === 'ally' ? `<p>Akcja: ${actionUsed ? 'zużyta' : 'dostępna'} | Bonus action: ${bonusActionUsed ? 'zużyta' : 'dostępna'} | Reakcja: ${reactionAvailable ? 'dostępna' : 'zużyta'} | Ruch: ${esc(remaining)} ft${extraMovement > 0 ? ` (+${esc(extraMovement)} Dash)` : ''}</p>` : ''}
    ${statusChipsHtml(actor.status_chips || [], 'Brak statusów aktywnego aktora.')}
  `;
}
function actorInventoryHtml(actor) {
  const items = actor && actor.inventory ? actor.inventory : [];
  if (!items.length) return '';
  return `<p><b>Ekwipunek:</b> ${items.map(item => `${esc(item.name || item.id)}${item.quantity !== undefined ? ` x${esc(item.quantity)}` : ''}${item.equipped === false ? ' (niezałożone)' : ''}`).join(', ')}</p>`;
}
function statusChipsHtml(chips, emptyText) {
  const items = chips || [];
  if (!items.length) return emptyText ? `<p class="combat-empty">${esc(emptyText)}</p>` : '';
  return `<div class="status-chips">${items.map(chip => {
    const tone = chip.tone || 'neutral';
    const title = chip.title ? ` title="${esc(chip.title)}"` : '';
    return `<span class="status-chip ${esc(tone)}"${title}>${esc(chip.label || '')}</span>`;
  }).join('')}</div>`;
}
function actorEffectChips(actor) {
  const chips = [];
  if (actor.defeated) chips.push({label: 'Pokonany', tone: 'danger'});
  (actor.effects || []).forEach(effect => {
    const label = `${effect.label || effect.kind || 'Efekt'}${effect.value_label ? `: ${effect.value_label}` : ''}`;
    chips.push({label, tone: effectChipTone(effect.kind), title: effect.expires || ''});
  });
  if (actor.concentration) chips.push({label: `Koncentracja: ${actor.concentration.label || '-'}`, tone: 'magic', title: actor.concentration.expires || ''});
  return chips;
}
function effectChipTone(kind) {
  if (kind === 'grant_ac_bonus_until_move' || kind === 'dodge_until_next_turn' || kind === 'disengage_until_turn_end') return 'defense';
  if (kind === 'grant_attack_bonus_while_on_object' || kind === 'help_attack_advantage' || kind === 'strength_potion' || kind === 'concentration_attack_bonus') return 'offense';
  if (kind === 'grant_next_attack_penalty') return 'penalty';
  if (kind === 'ready_attack') return 'ready';
  return 'neutral';
}
function combatActiveEffectsHtml(combat) {
  const effects = relevantCombatEffects(combat);
  return `
    <div class="combat-effects">
      <h4>Aktywne efekty</h4>
      ${effects.length ? `<div class="combat-effect-list">${effects.map(item => combatEffectHtml(item)).join('')}</div>` : '<p class="combat-empty">Brak aktywnych efektów dla aktualnego kroku.</p>'}
    </div>
  `;
}
function combatAllEffectsHtml(combat) {
  const actors = combat.actors || [];
  const items = [];
  actors.forEach(actor => {
    (actor.effects || []).forEach(effect => items.push({actor, effect, role: actor.name || 'Aktor'}));
  });
  if (!items.length) return '<p class="combat-empty">Brak aktywnych efektów.</p>';
  return `<div class="combat-effect-list">${items.map(item => combatEffectHtml(item)).join('')}</div>`;
}
function relevantCombatEffects(combat) {
  const actors = combat.actors || [];
  const current = combat.current_actor || {};
  const items = [];
  const seen = new Set();
  const addActorEffects = (actorId, role) => {
    if (!actorId) return;
    const actor = actors.find(candidate => candidate.id === actorId);
    if (!actor) return;
    (actor.effects || []).forEach(effect => {
      const key = `${actor.id}:${effect.id}`;
      if (seen.has(key)) return;
      seen.add(key);
      items.push({actor, effect, role});
    });
  };
  addActorEffects(current.id, 'Aktywny aktor');
  const pending = combat.pending_player_attack || null;
  if (pending && pending.target) addActorEffects(pending.target.id, 'Cel ataku');
  if (pending && pending.attacker) addActorEffects(pending.attacker.id, 'Atakujący');
  const intent = combat.enemy_turn_intent || combat.enemy_turn_preview || combat.enemy_turn_result || null;
  if (intent && intent.target_id) addActorEffects(intent.target_id, 'Cel przeciwnika');
  if (intent && intent.enemy_id) addActorEffects(intent.enemy_id, 'Przeciwnik');
  return items;
}
function combatEffectHtml(item) {
  const effect = item.effect || {};
  const actor = item.actor || {};
  const value = effect.value_label || signedNumber(effect.value || 0);
  const expires = effect.expires || 'czas trwania zależy od efektu';
  return `
    <div class="combat-effect">
      <b>${esc(item.role || 'Efekt')}: ${esc(actor.name || '-')}</b>
      <span>${esc(effect.label || effect.kind || '-')} | ${esc(value)} | ${esc(expires)}</span>
    </div>
  `;
}
function actorHpLabel(actor) {
  if (!actor) return '-';
  const maxHp = actor.max_hp !== null && actor.max_hp !== undefined ? actor.max_hp : actor.hp;
  const temp = Number(actor.temp_hp || 0);
  return `${actor.hp} / ${maxHp}${temp > 0 ? ` + ${temp} temp` : ''}${actor.defeated ? ' (pokonany)' : ''}`;
}
function combatLastResultHtml() {
  return `
    <div class="combat-last-result">
      <h4>Ostatni rezultat</h4>
      ${latestCombatMessageHtml()}
    </div>
  `;
}
function latestCombatMessageHtml() {
  const combatTitles = new Set(['Atak', 'Obrażenia', 'Ruch', 'Koniec tury', 'Atak przeciwnika', 'Obrażenia przeciwnika', 'Ruch przeciwnika', 'Tura przeciwnika', 'Atak okazyjny', 'Pomoc', 'Ready', 'Leczenie', 'Eliksir']);
  const messages = state.messages || [];
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (!combatTitles.has(messages[i].title)) continue;
    return `<p><b>${esc(messages[i].title)}</b></p><p>${esc(messages[i].body)}</p>`;
  }
  return '<p class="combat-empty">Brak rezultatu w tej walce.</p>';
}
function combatPrimaryActionHtml(combat, isAllyTurn, isEnemyTurn) {
  if (combat.pending_concentration_check) {
    return pendingConcentrationCheckHtml(combat.pending_concentration_check);
  }
  if (isEnemyTurn) {
    if (combat.pending_ready_attack) {
      return pendingReadyAttackHtml(combat.pending_ready_attack);
    }
    if (combat.pending_enemy_opportunity_attack) {
      return pendingEnemyOpportunityAttackHtml(combat.pending_enemy_opportunity_attack);
    }
    if (combat.enemy_turn_intent) {
      return enemyTurnIntentHtml(combat.enemy_turn_intent);
    }
    if (combat.enemy_turn_result) {
      return enemyTurnResultHtml(combat.enemy_turn_result);
    }
    const preview = combat.enemy_turn_preview || null;
    if (preview && preview.kind === 'movement') {
      return `
        <p>Oczekiwane pole: (${esc(preview.destination[0])},${esc(preview.destination[1])})</p>
        <button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>
      `;
    }
    if (preview && preview.kind === 'attack') {
      return `
        <p>Oczekiwany cel: ${esc(preview.target_name)}</p>
        <button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>
      `;
    }
    return `
      <button data-allow-busy="true" onclick="resolveEnemyTurn()">Rozegraj turę przeciwnika</button>
    `;
  }
  if (!isAllyTurn) {
    return '<p class="muted">Ten aktor nie ma automatycznych kontrolek w MVP.</p><button data-allow-busy="true" onclick="finishCombatTurn()">Zakończ turę</button>';
  }
  if (combat.pending_opportunity_movement) {
    return pendingOpportunityMovementHtml(combat.pending_opportunity_movement);
  }
  if (combat.pending_combat_help) {
    return pendingCombatHelpHtml(combat.pending_combat_help);
  }
  if (combat.pending_concentration_action) {
    return pendingConcentrationActionHtml(combat.pending_concentration_action);
  }
  if (combat.pending_combat_ready) {
    return pendingCombatReadyHtml(combat.pending_combat_ready);
  }
  if (combat.pending_player_attack) {
    return pendingPlayerAttackHtml(combat.pending_player_attack);
  }
  if (combat.pending_player_healing) {
    return pendingPlayerHealingHtml(combat.pending_player_healing);
  }
  if (combat.pending_area_spell) {
    return pendingAreaSpellHtml(combat.pending_area_spell);
  }
  if (combat.pending_combat_interaction) {
    return pendingCombatInteractionHtml(combat.pending_combat_interaction);
  }
  const movement = combat.movement || {remaining_feet: 0, destinations: []};
  const preview = combat.movement_preview || null;
  const actionUsed = combat.turn_action && combat.turn_action.action_use === 'action_used';
  return `
    ${preview ? `<p>Potwierdź pole: (${esc(preview.destination[0])},${esc(preview.destination[1])}), koszt ${esc(preview.cost_feet)} ft.</p>` : `<p>Ruch dostępny: ${esc(movement.remaining_feet || 0)} ft.</p>`}
    <div class="row">
      <button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>
      ${!actionUsed ? combatSourceButtonsHtml(combat) : ''}
      ${!actionUsed ? '<button class="secondary" data-allow-busy="true" onclick="startCombatReady()">Ready</button><button class="secondary" data-allow-busy="true" onclick="startCombatHelp()">Help</button><button class="secondary" data-allow-busy="true" onclick="useCombatDash()">Dash</button><button class="secondary" data-allow-busy="true" onclick="useCombatDodge()">Unik</button><button class="secondary" data-allow-busy="true" onclick="useCombatDisengage()">Odwrót</button>' : ''}
      <button class="secondary" data-allow-busy="true" onclick="finishCombatTurn()">Zakończ turę</button>
    </div>
  `;
}
function combatActionDetailsHtml(combat, isAllyTurn, isEnemyTurn) {
  if (combat.pending_concentration_check) return pendingConcentrationCheckDetailsHtml(combat.pending_concentration_check);
  if (isEnemyTurn) return enemyTurnDetailsHtml(combat);
  if (!isAllyTurn) return '<p class="muted">Brak dodatkowych szczegółów dla tego aktora.</p>';
  if (combat.pending_opportunity_movement) return pendingOpportunityMovementDetailsHtml(combat.pending_opportunity_movement);
  if (combat.pending_combat_help) return pendingCombatHelpDetailsHtml(combat.pending_combat_help);
  if (combat.pending_concentration_action) return pendingConcentrationActionDetailsHtml(combat.pending_concentration_action);
  if (combat.pending_combat_ready) return pendingCombatReadyDetailsHtml(combat.pending_combat_ready);
  if (combat.pending_player_attack) return pendingPlayerAttackDetailsHtml(combat.pending_player_attack);
  if (combat.pending_player_healing) return pendingPlayerHealingDetailsHtml(combat.pending_player_healing);
  if (combat.pending_area_spell) return pendingAreaSpellDetailsHtml(combat.pending_area_spell);
  if (combat.pending_combat_interaction) return pendingCombatInteractionDetailsHtml(combat.pending_combat_interaction);
  return playerTurnDetailsHtml(combat);
}
function combatSourceButtonsHtml(combat) {
  const attacks = combat.available_attack_sources || [];
  const selectedAttack = combat.selected_attack_source_id || '';
  const actor = combat.current_actor || {};
  const attackButtons = attacks.map(source => {
    const selected = source.id === selectedAttack ? ' selected' : '';
    const disabledReason = sourceUnavailableReason(source, actor);
    const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
    const label = sourceButtonLabel(source);
    return `<button class="secondary${selected}" data-allow-busy="true"${disabled} onclick="selectCombatAttackSource('${esc(source.id)}')">${label}</button>`;
  }).join('');
  const healing = combat.available_healing_sources || [];
  const selectedHealing = combat.selected_healing_source_id || '';
  const healingButtons = healing.map(source => {
    const selected = source.id === selectedHealing ? ' selected' : '';
    const disabledReason = sourceUnavailableReason(source, actor);
    const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
    const label = sourceButtonLabel(source);
    return `<button class="secondary${selected}" data-allow-busy="true"${disabled} onclick="selectCombatHealingSource('${esc(source.id)}')">${label}</button>`;
  }).join('');
  const actionButtons = (combat.combat_actions || []).map(action => {
    if (action.action_type === 'strength_potion') {
      const disabledReason = sourceUnavailableReason(action, actor);
      const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
      const label = sourceButtonLabel(action);
      return `<button class="secondary"${disabled} data-allow-busy="true" onclick="useStrengthPotion('${esc(action.id)}')">${label}</button>`;
    }
    if (action.action_type === 'concentration_attack_bonus') {
      const disabledReason = sourceUnavailableReason(action, actor);
      const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
      const label = sourceButtonLabel(action);
      return `<button class="secondary"${disabled} data-allow-busy="true" onclick="startConcentrationAction('${esc(action.id)}')">${label}</button>`;
    }
    return '';
  }).join('');
  return `${attackButtons}${healingButtons}${actionButtons}`;
}
function sourceButtonLabel(source) {
  const resource = source.resource_label ? ` · ${esc(source.resource_label)}` : '';
  return `${esc(source.name)}${resource}`;
}
function sourceUnavailableReason(source, actor) {
  if (source.prepared === false) return 'Ten czar nie jest przygotowany.';
  if (source.available === false) {
    if (source.source_item_id) return 'Ten przedmiot został zużyty.';
    return 'Ta opcja nie jest dostępna.';
  }
  const spellLevel = Number(source.spell_level || 0);
  if (spellLevel <= 0) return '';
  const slots = actor.spell_slots || [];
  const slot = slots.find(item => Number(item.level) === spellLevel);
  if (!slot || Number(slot.remaining || 0) <= 0) return `Brak slotów czaru ${spellLevel}. poziomu.`;
  return '';
}
function spellSlotSummaryHtml(actor) {
  const slots = actor.spell_slots || [];
  if (!slots.length) return '';
  return slots.map(slot => `slot ${esc(slot.level)}: ${esc(slot.remaining)}/${esc(slot.maximum)}`).join(', ');
}
function sourceSummaryText(source) {
  const parts = [source.name || '-'];
  if (source.resource_label) parts.push(source.resource_label);
  if (source.prepared === false) parts.push('nieprzygotowany');
  if (source.save_ability) parts.push(`save ${abilityLabel(source.save_ability)} ST ${source.save_dc || '-'}`);
  if (source.area) parts.push(`obszar ${areaShapeLabel(source.area.shape)}`);
  if (source.range_feet) parts.push(`${source.range_feet} ft`);
  return parts.join(' · ');
}
function playerTurnDetailsHtml(combat) {
  const source = combat.available_attack || {};
  const attackSources = combat.available_attack_sources || [];
  const healingSources = combat.available_healing_sources || [];
  const targets = combat.legal_targets || [];
  const healingTargets = combat.legal_healing_targets || [];
  const areaPositions = combat.legal_area_positions || [];
  const actor = combat.current_actor || {};
  const movement = combat.movement || {};
  const preview = combat.movement_preview || null;
  const actionUsed = combat.turn_action && combat.turn_action.action_use === 'action_used';
  const bonusActionUsed = combat.turn_action && combat.turn_action.bonus_action_use === 'action_used';
  const reactionAvailable = !combat.turn_action || combat.turn_action.reaction_available !== false;
  const remaining = Number(movement.remaining_feet || 0);
  const extraMovement = Number((combat.turn_action && combat.turn_action.extra_movement_feet) || 0);
  const moveCount = (movement.destinations || []).length;
  const slotSummary = spellSlotSummaryHtml(actor);
  const concentration = actor.concentration || null;
  const inventory = actorInventoryHtml(actor);
  const targetText = targets.length
    ? targets.map(target => `${target.name} (${target.position[0]},${target.position[1]})`).join(', ')
    : 'brak';
  return `
    <p><b>Tura gracza:</b> ${esc(actor.name || '-')}</p>
    <p><b>Akcja:</b> ${actionUsed ? 'zużyta' : 'dostępna'} | <b>Bonus action:</b> ${bonusActionUsed ? 'zużyta' : 'dostępna'} | <b>Reakcja:</b> ${reactionAvailable ? 'dostępna' : 'zużyta'} | <b>Ruch:</b> ${esc(remaining)} ft${extraMovement > 0 ? ` (+${esc(extraMovement)} Dash)` : ''}</p>
    ${inventory}
    ${slotSummary || concentration ? `<p><b>Magia:</b> ${slotSummary ? `ST czarów ${esc(actor.spell_save_dc || '-')}; ${slotSummary}` : ''}${concentration ? ` | Koncentracja: ${esc(concentration.label || '-')}` : ''}</p>` : ''}
    <p>Niebieskie pola: ruch (${esc(moveCount)} pól). Czerwone pola: legalne cele ataku. Turkusowe pola: legalne cele leczenia. Zielone pola: interakcje sceny. Żółte pola: środek albo kierunek czaru obszarowego.</p>
    ${preview ? `<p>Wybrana ścieżka: (${esc(preview.destination[0])},${esc(preview.destination[1])}), koszt ${esc(preview.cost_feet)} ft.</p>` : ''}
    <p><b>Atak:</b> ${esc(source.name || '-')}${source.damage_hint ? `, po trafieniu rzuć ${esc(source.damage_hint)}` : ''}</p>
    <p><b>Źródła ataku:</b> ${attackSources.map(sourceSummaryText).map(esc).join(', ') || 'brak'}</p>
    <p><b>Leczenie:</b> ${healingSources.map(item => `${sourceSummaryText(item)}${item.healing_hint ? ` · ${item.healing_hint}` : ''}`).map(esc).join(', ') || 'brak'}</p>
    <p><b>Cele w zasięgu:</b> ${esc(targetText)}</p>
    <p><b>Pola czaru obszarowego:</b> ${areaPositions.map(position => `(${esc(position[0])},${esc(position[1])})`).join(', ') || 'brak'}</p>
    <p><b>Ranni sojusznicy w zasięgu:</b> ${healingTargets.map(target => `${esc(target.name)} (${esc(target.position[0])},${esc(target.position[1])})`).join(', ') || 'brak'}</p>
  `;
}
function enemyTurnDetailsHtml(combat) {
  const pendingReady = combat.pending_ready_attack || null;
  if (pendingReady) {
    return pendingReadyAttackDetailsHtml(pendingReady);
  }
  const pendingOpportunity = combat.pending_enemy_opportunity_attack || null;
  if (pendingOpportunity) {
    return pendingEnemyOpportunityAttackDetailsHtml(pendingOpportunity, combat.enemy_turn_preview || null);
  }
  const intent = combat.enemy_turn_intent || null;
  if (intent) {
    const source = intent.source || {};
    const targetText = intent.target_name ? ` przeciwko ${esc(intent.target_name)}` : '';
    const moveText = intent.kind === 'movement'
      ? `<p><b>Ruch:</b> (${esc(intent.destination[0])},${esc(intent.destination[1])}), koszt ${esc(intent.cost_feet)} ft.</p>`
      : '';
    const attackText = intent.target_name
      ? `<p><b>Atak:</b> ${esc(source.name || '-')} ${targetText}. Premia do rzutu: ${esc(signedNumber(intent.attack_modifier || 0))}.</p>`
      : '';
    return `
      <p><b>Zamiar przeciwnika:</b> ${esc(intent.message || '')}</p>
      ${combatActiveEffectsHtml(combat)}
      ${moveText}
      ${attackText}
    `;
  }
  const result = combat.enemy_turn_result || null;
  if (result) {
    const target = result.target_name ? ` przeciwko ${esc(result.target_name)}` : '';
    const hitText = result.hit === true ? (result.critical ? 'TRAFIENIE KRYTYCZNE' : 'TRAFIENIE') : (result.hit === false ? 'PUDŁO' : 'BRAK ATAKU');
    const rollHtml = result.natural_roll !== null && result.natural_roll !== undefined
      ? `<p><b>Rzut d20:</b> ${d20RollResultText(result)} | <b>Wynik końcowy:</b> ${esc(result.total)}</p>`
      : '';
    const damageHtml = result.damage !== null && result.damage !== undefined
      ? `<p><b>Obrażenia:</b> ${esc(result.damage)}</p>`
      : '';
    const damageResult = result.damage_result || null;
    const hpHtml = damageResult
      ? `<p><b>HP celu:</b> ${esc(damageResult.hp_before)} -> ${esc(damageResult.hp_after)}${damageResult.defeated_by_damage ? ' | cel pokonany' : ''}</p>`
      : '';
    return `
      <p><b>Wynik tury przeciwnika:</b> ${hitText}</p>
      <p>${esc(result.enemy_name || 'Przeciwnik')}${target}</p>
      ${rollHtml}
      ${damageHtml}
      ${hpHtml}
      <p class="muted">${esc(result.message || '')}</p>
    `;
  }
  const preview = combat.enemy_turn_preview || null;
  if (preview && preview.kind === 'movement') {
    return `<p><b>Ruch przeciwnika:</b> ${esc(preview.enemy_name)} porusza się na (${esc(preview.destination[0])},${esc(preview.destination[1])}). Przestaw figurkę po ścieżce i potwierdź pole planszą.${enemyRollSummaryHtml(preview)}</p>${combatActiveEffectsHtml(combat)}`;
  }
  if (preview && preview.kind === 'attack') {
    return `<p><b>Atak przeciwnika:</b> ${esc(preview.enemy_name)} atakuje ${esc(preview.target_name)}. Potwierdź podświetlony cel planszą.${enemyRollSummaryHtml(preview)}</p>${combatActiveEffectsHtml(combat)}`;
  }
  return '<p>Enter albo przycisk wyliczy zamiar przeciwnika. Potem potwierdzisz ruch lub atak kliknięciem na planszy.</p>';
}
function enemyTurnIntentHtml(intent) {
  return `
    <button data-allow-busy="true" onclick="resolveEnemyTurn()">Potwierdź zamiar przeciwnika</button>
  `;
}
function enemyTurnResultHtml(result) {
  return `
    <button data-allow-busy="true" onclick="confirmEnemyTurnResult()">Potwierdź wynik przeciwnika</button>
  `;
}
function pendingEnemyOpportunityAttackHtml(pending) {
  const attacker = pending.attacker || {};
  const target = pending.target || {};
  const source = pending.source || {};
  if (pending.stage === 'choice') {
    return `
      <p>${esc(target.name || 'Przeciwnik')} opuszcza zasięg: ${esc(attacker.name || 'bohater')}.</p>
      <div class="row">
        <button data-allow-busy="true" onclick="startEnemyOpportunityAttack()">Wykonaj atak okazyjny</button>
        <button class="secondary" data-allow-busy="true" onclick="skipEnemyOpportunityAttack()">Pomiń reakcję</button>
      </div>
    `;
  }
  if (pending.stage === 'damage_roll') {
    return `
      <p>${esc(pending.damage_instruction || 'Wpisz obrażenia po trafieniu.')}</p>
      <div class="row">
        <label>Obrażenia: <input id="enemy-opportunity-damage-roll" type="number" min="0" value="${esc(defaultDamageValue(source))}"></label>
        <button onclick="submitEnemyOpportunityDamageRoll()">Zapisz obrażenia</button>
      </div>
    `;
  }
  return `
    <p>${esc(pending.attack_instruction || 'Rzuć 1d20 i wpisz wynik.')}</p>
    <div class="row">
      ${d20RollInputsHtml('enemy-opportunity-natural-roll', pending.attack_mode)}
      <button onclick="submitEnemyOpportunityAttackRoll()">Zapisz rzut</button>
    </div>
  `;
}
function pendingEnemyOpportunityAttackDetailsHtml(pending, preview) {
  const attacker = pending.attacker || {};
  const target = pending.target || {};
  const active = pending.active_modifiers || [];
  const ignored = pending.ignored_modifiers || [];
  const path = preview && preview.path ? preview.path.map(position => `(${position[0]},${position[1]})`).join(' -> ') : '';
  return `
    <p><b>Atak okazyjny bohatera:</b> ${esc(attacker.name || '-')} przeciwko ${esc(target.name || '-')}</p>
    ${path ? `<p><b>Ruch przeciwnika:</b> ${esc(path)}</p>` : ''}
    <p><b>Premia do rzutu:</b> ${esc(signedNumber(pending.attack_modifier || 0))} | <b>AC celu:</b> ${esc(pending.target_ac || '-')}</p>
    <p><b>Aktywne modyfikatory:</b> ${active.map(mod => `${esc(mod.label)} ${esc(signedNumber(mod.value))}`).join(', ') || 'brak'}</p>
    ${ignored.length ? `<p><b>Pominięte modyfikatory:</b> ${ignored.map(mod => `${esc(mod.label)} ${esc(signedNumber(mod.value))}`).join(', ')}</p>` : ''}
    <p><b>Obrażenia:</b> ${esc(pending.damage_instruction || '-')}</p>
  `;
}
function pendingCombatHelpHtml(pending) {
  const allies = pending.allies || [];
  const targets = pending.targets || [];
  const allyOptions = allies.map(actor => `<option value="${esc(actor.id)}">${esc(actor.name)} (${esc(actor.position[0])},${esc(actor.position[1])})</option>`).join('');
  const targetOptions = targets.map(actor => `<option value="${esc(actor.id)}">${esc(actor.name)} (${esc(actor.position[0])},${esc(actor.position[1])})</option>`).join('');
  return `
    <p>Wybierz sojusznika i przeciwnika dla akcji Help.</p>
    <div class="row">
      <label>Sojusznik: <select id="combat-help-ally">${allyOptions}</select></label>
      <label>Cel: <select id="combat-help-target">${targetOptions}</select></label>
      <button data-allow-busy="true" onclick="confirmCombatHelp()">Potwierdź Help</button>
      <button class="secondary" data-allow-busy="true" onclick="cancelCombatHelp()">Anuluj</button>
    </div>
  `;
}
function pendingCombatHelpDetailsHtml(pending) {
  const helper = pending.helper || {};
  const allies = pending.allies || [];
  const targets = pending.targets || [];
  return `
    <p><b>Pomagający:</b> ${esc(helper.name || '-')}</p>
    <p><b>Legalni sojusznicy:</b> ${allies.map(actor => esc(actor.name)).join(', ') || 'brak'}</p>
    <p><b>Cele w zasięgu 5 ft pomagającego:</b> ${targets.map(actor => `${esc(actor.name)} (${esc(actor.position[0])},${esc(actor.position[1])})`).join(', ') || 'brak'}</p>
    <p>Efekt: wybrany sojusznik ma przewagę na następny atak przeciw wybranemu celowi.</p>
  `;
}
function pendingConcentrationActionHtml(pending) {
  const action = pending.action || {};
  const targets = pending.targets || [];
  const targetOptions = targets.map(actor => `<option value="${esc(actor.id)}">${esc(actor.name)} (${esc(actor.position[0])},${esc(actor.position[1])})</option>`).join('');
  return `
    <p>${esc(action.label || action.name || 'Czar koncentracyjny')}: wybierz sojusznika dla efektu.</p>
    <div class="row">
      <label>Cel: <select id="combat-concentration-target">${targetOptions}</select></label>
      <button data-allow-busy="true" onclick="confirmConcentrationAction()">Potwierdź czar</button>
      <button class="secondary" data-allow-busy="true" onclick="cancelConcentrationAction()">Anuluj</button>
    </div>
  `;
}
function pendingConcentrationActionDetailsHtml(pending) {
  const caster = pending.caster || {};
  const action = pending.action || {};
  const targets = pending.targets || [];
  return `
    <p><b>Rzucający:</b> ${esc(caster.name || '-')}</p>
    <p><b>Czar:</b> ${esc(action.label || action.name || '-')} ${action.resource_label ? `(${esc(action.resource_label)})` : ''}</p>
    <p><b>Koncentracja:</b> ${action.concentration ? 'tak' : 'nie'} | <b>Efekt:</b> ${esc(signedNumber(action.value || 0))} do ataku celu</p>
    <p><b>Legalni sojusznicy:</b> ${targets.map(actor => `${esc(actor.name)} (${esc(actor.position[0])},${esc(actor.position[1])})`).join(', ') || 'brak'}</p>
  `;
}
function pendingConcentrationCheckHtml(pending) {
  const actor = pending.actor || {};
  const modifier = Number(pending.modifier || 0);
  return `
    <p>${esc(actor.name || 'Bohater')} utrzymuje koncentrację: ST ${esc(pending.dc)}.</p>
    <div class="row">
      <label>Wynik d20: <input id="concentration-check-roll" type="number" min="1" max="20" value="10"></label>
      <button onclick="submitConcentrationCheck()">Zapisz rzut</button>
    </div>
    <p class="muted">Premia CON: ${esc(signedNumber(modifier))}. Sukces utrzymuje efekt, porażka go kończy.</p>
  `;
}
function pendingConcentrationCheckDetailsHtml(pending) {
  const actor = pending.actor || {};
  const effects = pending.effects || [];
  return `
    <p><b>Koncentrujący:</b> ${esc(actor.name || '-')}</p>
    <p><b>Obrażenia:</b> ${esc(pending.damage)} | <b>ST:</b> ${esc(pending.dc)} | <b>Premia CON:</b> ${esc(signedNumber(pending.modifier || 0))}</p>
    <p><b>Efekty zagrożone:</b> ${effects.map(effect => esc(effect.label || effect.kind || effect.id)).join(', ') || 'brak'}</p>
  `;
}
function pendingCombatReadyHtml(pending) {
  const triggerOptions = (pending.triggers || []).map(trigger => `<option value="${esc(trigger.id)}">${esc(trigger.label)}</option>`).join('');
  return `
    <p>Przygotuj atak jako reakcję na wybrany warunek.</p>
    <div class="row">
      <label>Warunek: <select id="combat-ready-trigger">${triggerOptions}</select></label>
      <button data-allow-busy="true" onclick="confirmCombatReady()">Potwierdź Ready</button>
      <button class="secondary" data-allow-busy="true" onclick="cancelCombatReady()">Anuluj</button>
    </div>
  `;
}
function pendingCombatReadyDetailsHtml(pending) {
  const actor = pending.actor || {};
  return `
    <p><b>Przygotowujący:</b> ${esc(actor.name || '-')}</p>
    <p>Ready zużywa akcję główną teraz. Jeśli wybrany warunek zajdzie przed następną turą aktora, gracz może użyć reakcji i wykonać przygotowany atak.</p>
  `;
}
function pendingReadyAttackHtml(pending) {
  const attacker = pending.attacker || {};
  const target = pending.target || {};
  const source = pending.source || {};
  if (pending.stage === 'choice') {
    return `
      <p>${esc(pending.trigger_label || 'Warunek Ready')} | ${esc(attacker.name || 'Bohater')} może zaatakować ${esc(target.name || 'przeciwnika')}.</p>
      <div class="row">
        <button data-allow-busy="true" onclick="startReadyAttack()">Użyj przygotowanej akcji</button>
        <button class="secondary" data-allow-busy="true" onclick="skipReadyAttack()">Pomiń reakcję</button>
      </div>
    `;
  }
  if (pending.stage === 'damage_roll') {
    return `
      <p>${esc(pending.damage_instruction || 'Wpisz obrażenia po trafieniu.')}</p>
      <div class="row">
        <label>Obrażenia: <input id="ready-damage-roll" type="number" min="0" value="${esc(defaultDamageValue(source))}"></label>
        <button onclick="submitReadyDamageRoll()">Zapisz obrażenia</button>
      </div>
    `;
  }
  return `
    <p>${esc(pending.attack_instruction || 'Rzuć 1d20 i wpisz wynik.')}</p>
    <div class="row">
      ${d20RollInputsHtml('ready-natural-roll', pending.attack_mode)}
      <button onclick="submitReadyAttackRoll()">Zapisz rzut</button>
    </div>
  `;
}
function pendingReadyAttackDetailsHtml(pending) {
  const attacker = pending.attacker || {};
  const target = pending.target || {};
  const active = pending.active_modifiers || [];
  return `
    <p><b>Ready:</b> ${esc(attacker.name || '-')} przeciwko ${esc(target.name || '-')}</p>
    <p><b>Warunek:</b> ${esc(pending.trigger_label || '-')}</p>
    <p><b>Premia do rzutu:</b> ${esc(signedNumber(pending.attack_modifier || 0))} | <b>AC celu:</b> ${esc(pending.target_ac || '-')}</p>
    <p><b>Aktywne modyfikatory:</b> ${active.map(mod => `${esc(mod.label)} ${esc(signedNumber(mod.value))}`).join(', ') || 'brak'}</p>
  `;
}
function pendingOpportunityMovementHtml(pending) {
  const names = (pending.threats || []).map(actor => actor.name).join(', ') || 'wróg';
  return `
    <p>Ruch na (${esc(pending.destination[0])},${esc(pending.destination[1])}) prowokuje: ${esc(names)}.</p>
    <div class="row">
      <button data-allow-busy="true" onclick="confirmOpportunityMovement()">Potwierdź ruch mimo ryzyka</button>
      <button class="secondary" data-allow-busy="true" onclick="cancelOpportunityMovement()">Anuluj ruch</button>
    </div>
  `;
}
function pendingOpportunityMovementDetailsHtml(pending) {
  const threats = pending.threats || [];
  const threatText = threats.length
    ? threats.map(actor => `${actor.name} (${actor.position[0]},${actor.position[1]})`).join(', ')
    : 'brak';
  return `
    <p><b>Atak okazyjny:</b> wybrany ruch opuszcza zasięg wroga.</p>
    <p><b>Zagrożenia:</b> ${esc(threatText)}</p>
    <p><b>Ścieżka:</b> ${(pending.path || []).map(position => `(${position[0]},${position[1]})`).join(' -> ')}</p>
  `;
}
function pendingPlayerAttackHtml(pending) {
  const target = pending.target || {};
  const source = pending.source || {};
  if (pending.stage === 'confirm_attack') {
    const modifierLabel = signedNumber(pending.attack_modifier || 0);
    if (source.save_ability) {
      return `
        <p>Cel: ${esc(target.name || '-')} | rzut obronny ${esc(abilityLabel(source.save_ability))} przeciw ST ${esc(pending.spell_save_dc || source.save_dc || '-')}</p>
        <div class="row">
          <button data-allow-busy="true" onclick="confirmPlayerAttackTarget()">Potwierdź czar</button>
          <button class="secondary" data-allow-busy="true" onclick="cancelPlayerAttackTarget()">Anuluj wybór celu</button>
        </div>
      `;
    }
    return `
      <p>Cel: ${esc(target.name || '-')} | AC ${esc(target.ac || '-')} | premia ${esc(modifierLabel)}</p>
      <div class="row">
        <button data-allow-busy="true" onclick="confirmPlayerAttackTarget()">Potwierdź atak</button>
        <button class="secondary" data-allow-busy="true" onclick="cancelPlayerAttackTarget()">Anuluj wybór celu</button>
      </div>
    `;
  }
  if (pending.stage === 'damage_roll') {
    return `
      <p>${esc(pending.damage_instruction || 'Wpisz obrażenia po trafieniu.')}</p>
      ${spellSavesHtml(pending.saving_throws || [])}
      <div class="row">
        <label>Obrażenia: <input id="combat-damage-roll" type="number" min="0" value="${esc(defaultDamageValue(source))}"></label>
        <button onclick="submitPlayerDamageRoll()">Zapisz obrażenia</button>
        <button class="secondary" data-allow-busy="true" onclick="finishCombatTurn()">Zakończ turę</button>
      </div>
    `;
  }
  return `
    <p>${esc(pending.attack_instruction || 'Rzuć 1d20 i wpisz wynik.')}</p>
    <div class="row">
      ${d20RollInputsHtml('combat-attack-natural-roll', pending.attack_mode)}
      <button onclick="submitPlayerAttackRoll()">Zapisz rzut</button>
      <button class="secondary" data-allow-busy="true" onclick="finishCombatTurn()">Zakończ turę</button>
    </div>
  `;
}
function d20RollInputsHtml(baseId, mode) {
  const second = mode === 'advantage' || mode === 'disadvantage';
  const label = mode === 'advantage' ? 'Przewaga' : (mode === 'disadvantage' ? 'Utrudnienie' : 'Wynik d20');
  return `
    <label>${esc(second ? `${label} 1` : label)}: <input id="${esc(baseId)}" type="number" min="1" max="20" value="10"></label>
    ${second ? `<label>${esc(label)} 2: <input id="${esc(baseId)}-2" type="number" min="1" max="20" value="10"></label>` : ''}
  `;
}
function d20RollPayload(baseId) {
  const roll = document.getElementById(baseId);
  const roll2 = document.getElementById(`${baseId}-2`);
  const payload = {natural_roll: Number(roll ? roll.value : 0)};
  if (roll2) payload.natural_roll_2 = Number(roll2.value || 0);
  return payload;
}
function d20RollResultText(result) {
  const rolls = result && result.natural_rolls ? result.natural_rolls : [];
  if (rolls.length > 1) return `${rolls.map(esc).join(' / ')} -> ${esc(result.natural_roll || '')}`;
  return result && result.natural_roll !== null && result.natural_roll !== undefined ? esc(result.natural_roll) : '';
}
function pendingAreaSpellHtml(pending) {
  const source = pending.source || {};
  const targets = pending.targets || [];
  const targetText = targets.map(target => `${target.name} (${target.position[0]},${target.position[1]})`).join(', ') || 'brak celów';
  if (pending.stage === 'damage_roll') {
    return `
      <p>${esc(pending.damage_instruction || 'Wpisz obrażenia czaru obszarowego.')}</p>
      <p>Cele w obszarze: ${esc(targetText)}</p>
      ${spellSavesHtml(pending.saving_throws || [])}
      <div class="row">
        <label>Obrażenia: <input id="area-spell-damage-roll" type="number" min="0" value="${esc(defaultDamageValue(source))}"></label>
        <button onclick="submitAreaSpellDamage()">Zapisz obrażenia</button>
        <button class="secondary" data-allow-busy="true" onclick="finishCombatTurn()">Zakończ turę</button>
      </div>
    `;
  }
  return `
    <p>Obszar: ${esc((pending.area_positions || []).map(position => `(${position[0]},${position[1]})`).join(', ') || '-')}</p>
    <p>Cele w obszarze: ${esc(targetText)}</p>
    ${source.save_ability ? `<p>Rzut obronny: ${esc(abilityLabel(source.save_ability))} przeciw ST ${esc(pending.spell_save_dc || source.save_dc || '-')} | ${esc(saveSuccessLabel(source.save_damage_on_success))}</p>` : ''}
    <div class="row">
      <button data-allow-busy="true" onclick="confirmAreaSpell()">Potwierdź czar</button>
      <button class="secondary" data-allow-busy="true" onclick="cancelAreaSpell()">Anuluj czar</button>
    </div>
  `;
}
function pendingAreaSpellDetailsHtml(pending) {
  const source = pending.source || {};
  const targets = pending.targets || [];
  return `
    <p><b>Czar:</b> ${esc(source.name || '-')} | ${esc(source.damage_hint || '-')}</p>
    <p><b>Zakotwiczenie:</b> (${esc(pending.anchor ? pending.anchor[0] : '-')},${esc(pending.anchor ? pending.anchor[1] : '-')})</p>
    <p><b>Obszar:</b> ${esc((pending.area_positions || []).map(position => `(${position[0]},${position[1]})`).join(', ') || '-')}</p>
    <p><b>Cele:</b> ${targets.map(target => `${esc(target.name)} (${esc(target.position[0])},${esc(target.position[1])})`).join(', ') || 'brak'}</p>
    ${spellSavesHtml(pending.saving_throws || [])}
  `;
}
function pendingPlayerHealingHtml(pending) {
  const target = pending.target || {};
  const source = pending.source || {};
  return `
    <p>${esc(pending.healing_instruction || 'Rzuć leczenie i wpisz wynik.')}</p>
    <div class="row">
      <label>Leczenie: <input id="combat-healing-roll" type="number" min="0" value="${esc(defaultHealingValue(source))}"></label>
      <button onclick="submitPlayerHealingRoll()">Zapisz leczenie</button>
      <button class="secondary" data-allow-busy="true" onclick="cancelPlayerHealing()">Anuluj</button>
    </div>
    <p class="muted">Cel: ${esc(target.name || '-')}.</p>
  `;
}
function pendingPlayerHealingDetailsHtml(pending) {
  const healer = pending.healer || {};
  const target = pending.target || {};
  const source = pending.source || {};
  return `
    <p><b>Leczenie:</b> ${esc(healer.name || '-')} używa ${esc(source.name || '-')} na ${esc(target.name || '-')}</p>
    <p><b>HP celu:</b> ${esc(actorHpLabel(target))}</p>
    <p><b>Rzut:</b> ${esc(pending.healing_instruction || '-')}</p>
  `;
}
function pendingCombatInteractionHtml(pending) {
  const options = pending.options || [];
  if (!options.length) return '<p>Brak dostępnych opcji interakcji.</p>';
  const primary = options[0];
  const buttons = options.map(option => `<button data-allow-busy="true" onclick="confirmCombatInteraction('${esc(option.id)}')">${esc(option.label)}</button>`).join('');
  return `
    <p>Obiekt: ${esc(pending.object_name || '-')} | pole (${esc(pending.target_position ? pending.target_position[0] : '-')},${esc(pending.target_position ? pending.target_position[1] : '-')})</p>
    <p>${esc(primary.description || 'Interakcja zużywa akcję główną.')}</p>
    <div class="row">${buttons}<button class="secondary" data-allow-busy="true" onclick="cancelCombatInteraction()">Anuluj</button></div>
  `;
}
function pendingCombatInteractionDetailsHtml(pending) {
  const options = pending.options || [];
  if (!options.length) return '<p>Brak szczegółów interakcji.</p>';
  return options.map(option => `
    <p><b>${esc(option.label)}</b></p>
    <p>${esc(option.description || '')}</p>
    <p><b>Warunki:</b> ${(option.conditions || []).map(condition => esc(condition)).join(', ') || 'brak'}</p>
  `).join('');
}
function pendingPlayerAttackDetailsHtml(pending) {
  const target = pending.target || {};
  const source = pending.source || {};
  if (pending.stage === 'confirm_attack') {
    const active = pending.active_modifiers || [];
    const ignored = pending.ignored_modifiers || [];
    const modifierLabel = signedNumber(pending.attack_modifier || 0);
    return `
      <p><b>Potwierdzenie ataku</b></p>
      <p><b>Cel:</b> ${esc(target.name || '-')} | <b>AC celu:</b> ${esc(target.ac || '-')} | <b>Pole:</b> (${esc(target.position ? target.position[0] : '-')},${esc(target.position ? target.position[1] : '-')})</p>
      <p><b>Atak:</b> ${esc(source.name || '-')} | <b>Zasięg:</b> ${esc(source.range_feet || 0)} ft | <b>Premia końcowa:</b> ${esc(modifierLabel)}</p>
      <p><b>Aktywne premie/kary:</b> ${active.length ? active.map(mod => `${esc(mod.label)} ${esc(signedNumber(mod.value))}`).join(', ') : 'brak'}</p>
      ${attackEffectsDetailsHtml(pending)}
      ${ignored.length ? `<p><b>Odrzucone duplikaty:</b> ${ignored.map(mod => `${esc(mod.label)} ${esc(signedNumber(mod.value))}`).join(', ')}</p>` : ''}
      <p><b>Rzut:</b> ${esc(pending.attack_instruction || 'Rzuć 1d20 i wpisz wynik.')}</p>
      <p><b>Po trafieniu:</b> ${esc(pending.damage_instruction || source.damage_hint || '')}</p>
    `;
  }
  if (pending.stage === 'damage_roll') {
    if (pending.saving_throws && pending.saving_throws.length) {
      return `
        <p><b>Tura gracza: wpisz obrażenia czaru</b></p>
        <p><b>Cel:</b> ${esc(target.name || '-')} | <b>Czar:</b> ${esc(source.name || '-')}</p>
        ${spellSavesHtml(pending.saving_throws || [])}
        <p><b>Co teraz:</b> ${esc(pending.damage_instruction || '')}</p>
      `;
    }
    return `
      <p><b>Tura gracza: wpisz obrażenia</b></p>
      <p><b>Cel:</b> ${esc(target.name || '-')} | <b>Trafienie:</b> ${pending.critical ? 'krytyczne' : 'zwykłe'}</p>
      ${attackEffectsDetailsHtml(pending)}
      <p><b>Rzut d20:</b> ${d20RollResultText(pending)} | <b>Wynik końcowy:</b> ${esc(pending.total || '')}</p>
      <p><b>Co teraz:</b> ${esc(pending.damage_instruction || '')}</p>
    `;
  }
  return `
    <p><b>Tura gracza: wybrano cel</b></p>
    <p><b>Cel:</b> ${esc(target.name || '-')} | <b>Atak:</b> ${esc(source.name || '-')}</p>
    ${attackEffectsDetailsHtml(pending)}
    <p><b>Co teraz:</b> ${source.save_ability ? `Potwierdź czar. Cel wykona automatyczny rzut obronny na ${esc(abilityLabel(source.save_ability))} przeciw ST ${esc(pending.spell_save_dc || source.save_dc || '-')}.` : esc(pending.attack_instruction || 'Rzuć 1d20 i wpisz wynik.')}</p>
    <p><b>Po trafieniu:</b> ${esc(pending.damage_instruction || source.damage_hint || '')}</p>
  `;
}
function attackEffectsDetailsHtml(pending) {
  const items = [];
  const attacker = pending.attacker || {};
  const target = pending.target || {};
  (attacker.effects || []).forEach(effect => items.push({actor: attacker, effect, role: 'Atakujący'}));
  (target.effects || []).forEach(effect => items.push({actor: target, effect, role: 'Cel'}));
  if (!items.length) return '<p><b>Efekty ataku:</b> brak</p>';
  return `
    <div>
      <p><b>Efekty ataku:</b></p>
      <div class="combat-effect-list">${items.map(item => combatEffectHtml(item)).join('')}</div>
    </div>
  `;
}
function enemyRollSummaryHtml(preview) {
  if (!preview || preview.natural_roll === null || preview.natural_roll === undefined) return '';
  const outcome = preview.hit ? (preview.critical ? 'trafienie krytyczne' : 'trafienie') : 'pudło';
  const damage = preview.damage !== null && preview.damage !== undefined ? `<br>Obrażenia: ${esc(preview.damage)}.` : '';
  return `<br>Automatyczny rzut przeciwnika: d20 ${d20RollResultText(preview)}, razem ${esc(preview.total)} (${outcome}).${damage}`;
}
function spellSavesHtml(saves) {
  if (!saves || !saves.length) return '';
  return `
    <div class="combat-effect-list">
      ${saves.map(save => `
        <span class="combat-effect">
          ${esc(save.actor_name || save.actor_id)}: ${esc(abilityLabel(save.ability))} d20 ${esc(save.natural_roll)}, mod ${esc(signedNumber(save.modifier || 0))}, razem ${esc(save.total)} / ST ${esc(save.dc)} - ${save.success ? 'sukces' : 'porażka'}${save.success ? `, ${esc(saveSuccessLabel(save.damage_multiplier === 0.5 ? 'half' : 'none'))}` : ', pełne obrażenia'}
        </span>
      `).join('')}
    </div>
  `;
}
function abilityLabel(ability) {
  const labels = {
    strength: 'Siła',
    dexterity: 'Zręczność',
    constitution: 'Kondycja',
    intelligence: 'Inteligencja',
    wisdom: 'Mądrość',
    charisma: 'Charyzma'
  };
  return labels[ability] || ability || '-';
}
function saveSuccessLabel(value) {
  if (value === 'half') return 'połowa obrażeń przy sukcesie';
  return 'brak obrażeń przy sukcesie';
}
function areaShapeLabel(shape) {
  const labels = {
    line: 'linia',
    cone: 'stożek',
    radius: 'okrąg'
  };
  return labels[shape] || shape || '-';
}
function defaultDamageValue(source) {
  if (!source) return 0;
  if (source.damage_fixed !== null && source.damage_fixed !== undefined) return Number(source.damage_fixed) + Number(source.damage_modifier || 0);
  return Math.max(0, Number(source.damage_modifier || 0));
}
function defaultHealingValue(source) {
  if (!source) return 0;
  if (source.healing_fixed !== null && source.healing_fixed !== undefined) return Number(source.healing_fixed) + Number(source.healing_modifier || 0);
  return Math.max(0, Number(source.healing_modifier || 0));
}
function signedNumber(value) {
  const number = Number(value || 0);
  return number >= 0 ? `+${number}` : `${number}`;
}
function pointOptionsHtml() {
  const points = state.current_zone_points || [];
  if (!points.length) return '<p>Brak odkrytych punktów w tej lokacji.</p>';
  const rows = points.map(point => {
    const active = state.active_point && state.active_point.id === point.id;
    const positions = (point.positions || []).map(pos => `(${pos[0]},${pos[1]})`).join(', ');
    return `
      <div class="status-item" style="margin: 6px 0">
        <b>${esc(point.name)}${active ? ' (aktywny)' : ''}</b>
        <div class="muted">${esc(point.description)}</div>
        <div>LED: ${esc(point.color || 'kolor specjalny')}${positions ? `, pole ${esc(positions)}` : ''}. Przestaw pionek drużyny na to pole, kliknij Skanuj planszę i wskaż pole.</div>
      </div>
    `;
  });
  if (state.active_point) {
    rows.push('<button class="secondary" onclick="selectPoint(&quot;&quot;)">Wróć do lokacji</button>');
  }
  rows.unshift('<button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>');
  return rows.join('');
}
function updateActivePanel() {
  const stage = state.flow ? state.flow.stage : 'location_active';
  const flowActive = stage !== 'location_active';
  const hasPendingDecision = state.pending && state.pending.stage === 'decision';
  const hasRolls = state.required_rolls && state.required_rolls.length > 0;
  const hasResult = Boolean(resultAck);
  const hasEncounter = Boolean(state.pending_encounter);
  const hasTravel = false;
  const hasPoints = !flowActive && !hasEncounter && !hasResult && !hasPendingDecision && !hasRolls && state.current_zone_points && state.current_zone_points.length > 0;
  const flowPanel = document.getElementById('flow-panel');
  flowPanel.hidden = hasEncounter || !flowPanel.innerHTML.trim();
  document.getElementById('result-panel').hidden = !hasResult;
  document.getElementById('encounter-panel').hidden = !hasEncounter || hasResult;
  document.getElementById('travel-panel').hidden = !hasTravel;
  document.getElementById('points-panel').hidden = !hasPoints;
  document.getElementById('pending-panel').hidden = !hasPendingDecision;
  document.getElementById('roll-panel').hidden = !hasRolls;
  document.getElementById('action-panel').hidden = flowActive || hasEncounter || hasResult || hasTravel || hasPendingDecision || hasRolls;
}
function sendAction() { api('/api/action', {text: document.getElementById('action').value}, 'Czekam na decyzję MG...'); }
function decision(value) {
  const labels = {
    accept: 'Przyjmuję decyzję MG...',
    reject: 'Odrzucam decyzję MG...',
    explain: 'Proszę MG o wyjaśnienie...'
  };
  const leadActor = document.getElementById('lead-actor');
  api('/api/decision', {decision:value, lead_actor_id: leadActor ? leadActor.value : null}, labels[value] || 'Czekam na MG...');
}
function submitDecisionCorrection() {
  const situational_modifiers = Array.from(document.querySelectorAll('[data-situational-row]')).map(row => ({
    label: row.querySelector('.correction-sit-label').value,
    modifier: Number(row.querySelector('.correction-sit-modifier').value || 0),
    roll_mode: row.querySelector('.correction-sit-roll-mode').value,
    source: row.querySelector('.correction-sit-source').value,
    reason: row.querySelector('.correction-sit-reason').value
  })).filter(mod => mod.label || mod.reason || Number(mod.modifier || 0) !== 0 || mod.roll_mode !== 'normal');
  const improvised_tool = {
    label: document.getElementById('improvised-tool-label').value,
    source: document.getElementById('improvised-tool-source').value,
    source_detail: document.getElementById('improvised-tool-source-detail').value,
    effect_modifier: Number(document.getElementById('improvised-tool-effect').value || 0),
    risk: document.getElementById('improvised-tool-risk').value,
    reason: document.getElementById('improvised-tool-reason').value
  };
  api('/api/decision/correction', {
    mechanic_id: document.getElementById('correction-mechanic').value,
    check_participants: document.getElementById('correction-participants').value,
    check_aggregation: document.getElementById('correction-aggregation').value,
    lead_actor_id: document.getElementById('correction-lead').value,
    helper_actor_id: document.getElementById('correction-helper').value,
    ability: document.getElementById('correction-ability').value,
    skill: document.getElementById('correction-skill').value,
    dc: Number(document.getElementById('correction-dc').value),
    roll_mode: document.getElementById('correction-roll-mode').value,
    situational_modifiers,
    improvised_tool
  }, 'Zapisuję korektę decyzji MG...');
}
function sendRolls() {
  const rolls = {};
  document.querySelectorAll('#rolls input').forEach(input => {
    const actorId = input.dataset.actor;
    const index = input.dataset.rollIndex || '1';
    if (index === '2') {
      if (!rolls[actorId] || typeof rolls[actorId] !== 'object') rolls[actorId] = {natural_roll: Number(rolls[actorId] || 0)};
      rolls[actorId].natural_roll_2 = Number(input.value);
    } else {
      rolls[actorId] = Number(input.value);
    }
  });
  api('/api/rolls', {rolls}, 'Rozstrzygam wynik rzutu...');
}
function resetSession() { api('/api/reset', {}, 'Resetuję scenę...'); }
function travel(zoneId) { api('/api/travel', {zone_id: zoneId}, 'Przechodzę do wybranej lokacji...'); }
function selectPoint(pointId) { api('/api/point', {point_id: pointId}, pointId ? 'Otwieram punkt eksploracji...' : 'Wracam do lokacji...'); }
function finishInteraction() { api('/api/interaction/finish', {}, 'Wracam do wyboru lokacji...'); }
function cancelLocationPreview() { api('/api/location/cancel-preview', {}, 'Wracam do wyboru lokacji...'); }
function confirmLocationPreview() { api('/api/location/confirm-preview', {}, 'Wchodzę w eksplorację...'); }
function confirmExplorationSetup() { api('/api/exploration/setup/confirm', {}, 'Potwierdzam setup mapy...'); }
function configureBoard() {
  api('/api/board/configure', {
    backend: document.getElementById('board-backend').value,
    board_url: document.getElementById('board-url').value,
    board_serial_port: document.getElementById('board-serial-port').value,
    wled_url: document.getElementById('wled-url').value,
    scan_timeout_s: Number(document.getElementById('scan-timeout').value || 30)
  }, 'Łączę z planszą...');
}
function startSession() { api('/api/start', {}, 'Rozpoczynam sesję...'); }
function isAllyCombatTurnActive() {
  const combat = state && state.combat ? state.combat : null;
  const actor = combat && combat.current_actor ? combat.current_actor : {};
  return Boolean(combat && combat.status === 'active' && actor.faction === 'ally' && !combat.enemy_turn_preview && !combat.pending_player_attack && !combat.pending_player_healing && !combat.pending_area_spell && !combat.pending_combat_interaction && !combat.pending_combat_help && !combat.pending_concentration_action && !combat.pending_concentration_check && !combat.pending_combat_ready);
}
async function scanBoard() {
  if (boardScanInFlight) return;
  const continuous = isAllyCombatTurnActive();
  if (continuous) playerTurnScanLoop = true;
  await scanBoardOnce();
}
async function scanBoardOnce() {
  if (boardScanInFlight) return;
  const token = boardScanToken;
  boardScanInFlight = true;
  setBusy('Czekam na kliknięcie pola na planszy...');
  try {
    const res = await fetch('/api/board/scan', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({})});
    const data = await res.json();
    if (token !== boardScanToken) return;
    if (!res.ok) {
      playerTurnScanLoop = false;
      alert(data.error || 'Błąd');
    }
    state = data.state || data;
    if (!isAllyCombatTurnActive()) playerTurnScanLoop = false;
    render();
    refreshSessionLog();
  } finally {
    if (token === boardScanToken) {
      boardScanInFlight = false;
      setBusy('');
    }
  }
  if (token === boardScanToken && playerTurnScanLoop && isAllyCombatTurnActive()) {
    setTimeout(scanBoardOnce, 50);
  }
}
async function stopBoardScanLoop() {
  playerTurnScanLoop = false;
  boardScanToken += 1;
  if (boardScanInFlight) {
    try {
      await fetch('/api/board/reset-scan', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({})});
    } catch (_error) {
      // Best effort: the next stale scan response is ignored by boardScanToken.
    }
    boardScanInFlight = false;
    setBusy('');
  }
}
function selectBoardPosition(col, row) { api('/api/board/select', {col, row}, 'Wybieram pole planszy...'); }
function resetBoardScan() { api('/api/board/reset-scan', {}, 'Resetuję oczekiwanie planszy...'); }
function startEncounterSetup() { api('/api/encounter/setup/start', {}, 'Przygotowuję kroki setupu encountera...'); }
function confirmEncounterSetup() { api('/api/encounter/setup/confirm', {}, 'Potwierdzam krok setupu...'); }
function startEncounterInitiative() { api('/api/encounter/initiative/start', {}, 'Rozpoczynam inicjatywę...'); }
function submitEncounterInitiativeRoll() {
  const input = document.getElementById('encounter-initiative-roll');
  api('/api/encounter/initiative/roll', {natural_roll: Number(input ? input.value : 0)}, 'Zapisuję rzut inicjatywy...');
}
function submitPlayerAttackRoll() {
  api('/api/combat/player-attack-roll', d20RollPayload('combat-attack-natural-roll'), 'Rozstrzygam rzut ataku...');
}
function selectCombatAttackSource(sourceId) { api('/api/combat/attack-source', {source_id: sourceId}, 'Wybieram źródło ataku...'); }
function selectCombatHealingSource(sourceId) { api('/api/combat/healing-source', {source_id: sourceId}, 'Wybieram leczenie...'); }
function confirmPlayerAttackTarget() { api('/api/combat/player-attack-confirm', {}, 'Potwierdzam atak...'); }
function cancelPlayerAttackTarget() { api('/api/combat/player-attack-cancel', {}, 'Anuluję wybór celu...'); }
function confirmCombatInteraction(interactionId) { api('/api/combat/interaction/confirm', {interaction_id: interactionId}, 'Potwierdzam interakcję...'); }
function cancelCombatInteraction() { api('/api/combat/interaction/cancel', {}, 'Anuluję interakcję...'); }
function submitPlayerDamageRoll() {
  const damage = document.getElementById('combat-damage-roll');
  api('/api/combat/player-damage', {damage: Number(damage ? damage.value : 0)}, 'Zapisuję obrażenia...');
}
function submitPlayerHealingRoll() {
  const healing = document.getElementById('combat-healing-roll');
  api('/api/combat/player-healing', {healing: Number(healing ? healing.value : 0)}, 'Zapisuję leczenie...');
}
function cancelPlayerHealing() { api('/api/combat/player-healing-cancel', {}, 'Anuluję leczenie...'); }
function confirmAreaSpell() { api('/api/combat/area-spell/confirm', {}, 'Potwierdzam czar obszarowy...'); }
function submitAreaSpellDamage() {
  const damage = document.getElementById('area-spell-damage-roll');
  api('/api/combat/area-spell/damage', {damage: Number(damage ? damage.value : 0)}, 'Zapisuję obrażenia obszarowe...');
}
function cancelAreaSpell() { api('/api/combat/area-spell/cancel', {}, 'Anuluję czar obszarowy...'); }
function useStrengthPotion(actionId) { api('/api/combat/strength-potion', {action_id: actionId}, 'Używam eliksiru...'); }
function startConcentrationAction(actionId) { api('/api/combat/concentration/start', {action_id: actionId}, 'Przygotowuję czar koncentracyjny...'); }
function confirmConcentrationAction() {
  const target = document.getElementById('combat-concentration-target');
  api('/api/combat/concentration/confirm', {target_id: target ? target.value : ''}, 'Potwierdzam czar koncentracyjny...');
}
function cancelConcentrationAction() { api('/api/combat/concentration/cancel', {}, 'Anuluję czar koncentracyjny...'); }
function submitConcentrationCheck() {
  const roll = document.getElementById('concentration-check-roll');
  api('/api/combat/concentration-check', {natural_roll: Number(roll ? roll.value : 0)}, 'Rozstrzygam koncentrację...');
}
function submitCombatMove() {
  const destination = document.getElementById('combat-move-destination');
  const parts = destination && destination.value ? destination.value.split(',') : ['0', '0'];
  api('/api/combat/move', {col: Number(parts[0]), row: Number(parts[1])}, 'Wykonuję ruch...');
}
function confirmOpportunityMovement() { api('/api/combat/opportunity-movement/confirm', {}, 'Rozstrzygam ataki okazyjne...'); }
function cancelOpportunityMovement() { api('/api/combat/opportunity-movement/cancel', {}, 'Anuluję ryzykowny ruch...'); }
function useCombatDash() { api('/api/combat/dash', {}, 'Wykonuję Dash...'); }
function useCombatDodge() { api('/api/combat/dodge', {}, 'Wykonuję Unik...'); }
function useCombatDisengage() { api('/api/combat/disengage', {}, 'Wykonuję Odwrót...'); }
function startCombatHelp() { api('/api/combat/help/start', {}, 'Przygotowuję Help...'); }
function confirmCombatHelp() {
  const ally = document.getElementById('combat-help-ally');
  const target = document.getElementById('combat-help-target');
  api('/api/combat/help/confirm', {ally_id: ally ? ally.value : '', target_id: target ? target.value : ''}, 'Potwierdzam Help...');
}
function cancelCombatHelp() { api('/api/combat/help/cancel', {}, 'Anuluję Help...'); }
function startCombatReady() { api('/api/combat/ready/start', {}, 'Przygotowuję Ready...'); }
function confirmCombatReady() {
  const trigger = document.getElementById('combat-ready-trigger');
  api('/api/combat/ready/confirm', {trigger: trigger ? trigger.value : ''}, 'Potwierdzam Ready...');
}
function cancelCombatReady() { api('/api/combat/ready/cancel', {}, 'Anuluję Ready...'); }
function resolveEnemyTurn() { api('/api/combat/enemy-turn', {}, 'Rozgrywam turę przeciwnika...'); }
function startEnemyOpportunityAttack() { api('/api/combat/enemy-opportunity/start', {}, 'Rozpoczynam atak okazyjny...'); }
function skipEnemyOpportunityAttack() { api('/api/combat/enemy-opportunity/skip', {}, 'Pomijam reakcję...'); }
function submitEnemyOpportunityAttackRoll() {
  api('/api/combat/enemy-opportunity/roll', d20RollPayload('enemy-opportunity-natural-roll'), 'Rozstrzygam atak okazyjny...');
}
function submitEnemyOpportunityDamageRoll() {
  const damage = document.getElementById('enemy-opportunity-damage-roll');
  api('/api/combat/enemy-opportunity/damage', {damage: Number(damage ? damage.value : 0)}, 'Zapisuję obrażenia ataku okazyjnego...');
}
function startReadyAttack() { api('/api/combat/ready-attack/start', {}, 'Używam przygotowanej akcji...'); }
function skipReadyAttack() { api('/api/combat/ready-attack/skip', {}, 'Pomijam przygotowaną akcję...'); }
function submitReadyAttackRoll() {
  api('/api/combat/ready-attack/roll', d20RollPayload('ready-natural-roll'), 'Rozstrzygam przygotowaną akcję...');
}
function submitReadyDamageRoll() {
  const damage = document.getElementById('ready-damage-roll');
  api('/api/combat/ready-attack/damage', {damage: Number(damage ? damage.value : 0)}, 'Zapisuję obrażenia przygotowanej akcji...');
}
function confirmEnemyTurnResult() { api('/api/combat/enemy-turn/confirm', {}, 'Potwierdzam wynik przeciwnika...'); }
async function finishCombatTurn() {
  await stopBoardScanLoop();
  api('/api/combat/end-turn', {}, 'Kończę turę...');
}
function resolveCombatOutcome() { api('/api/encounter/combat/resolve', {}, 'Zastosowuję wynik walki w eksploracji...'); }
function ackResult() {
  resultAck = null;
  render();
}
function isVisible(id) {
  const el = document.getElementById(id);
  return Boolean(el && !el.hidden && el.offsetParent !== null);
}
function visiblePrimaryScanButton() {
  const containers = ['flow-panel', 'encounter-panel', 'points-panel'];
  for (const id of containers) {
    const container = document.getElementById(id);
    if (!container || container.hidden || container.offsetParent === null) continue;
    const button = container.querySelector('button[data-primary-scan="true"]');
    if (button && !button.disabled && button.offsetParent !== null) return button;
  }
  return null;
}
function triggerPrimaryAction() {
  if (busy) return false;
  if (isVisible('result-panel')) { ackResult(); return true; }
  if (isVisible('pending-panel')) { decision('accept'); return true; }
  if (isVisible('roll-panel')) { sendRolls(); return true; }
  if (isVisible('action-panel')) { sendAction(); return true; }
  const scanButton = visiblePrimaryScanButton();
  if (scanButton) { scanButton.click(); return true; }
  const setup = state.encounter_setup;
  const initiative = state.encounter_initiative;
  const combat = state.combat;
    if (isVisible('encounter-panel')) {
    if (combat && combat.status === 'finished') { resolveCombatOutcome(); return true; }
    if (combat && combat.status === 'active') {
      if (combat.pending_concentration_check) { submitConcentrationCheck(); return true; }
      if (combat.enemy_turn_result) { confirmEnemyTurnResult(); return true; }
      if (combat.pending_ready_attack) {
        if (combat.pending_ready_attack.stage === 'choice') startReadyAttack();
        else if (combat.pending_ready_attack.stage === 'damage_roll') submitReadyDamageRoll();
        else submitReadyAttackRoll();
        return true;
      }
      if (combat.pending_enemy_opportunity_attack) {
        if (combat.pending_enemy_opportunity_attack.stage === 'choice') startEnemyOpportunityAttack();
        else if (combat.pending_enemy_opportunity_attack.stage === 'damage_roll') submitEnemyOpportunityDamageRoll();
        else submitEnemyOpportunityAttackRoll();
        return true;
      }
      if (combat.pending_opportunity_movement) { confirmOpportunityMovement(); return true; }
      if (combat.pending_combat_help) { confirmCombatHelp(); return true; }
      if (combat.pending_concentration_action) { confirmConcentrationAction(); return true; }
      if (combat.pending_combat_ready) { confirmCombatReady(); return true; }
      if (combat.pending_combat_interaction) {
        const options = combat.pending_combat_interaction.options || [];
        if (options.length) confirmCombatInteraction(options[0].id);
        return true;
      }
      if (combat.pending_player_attack) {
        if (combat.pending_player_attack.stage === 'confirm_attack') confirmPlayerAttackTarget();
        else if (combat.pending_player_attack.stage === 'damage_roll') submitPlayerDamageRoll();
        else submitPlayerAttackRoll();
        return true;
      }
      if (combat.pending_player_healing) { submitPlayerHealingRoll(); return true; }
      if (combat.pending_area_spell) {
        if (combat.pending_area_spell.stage === 'damage_roll') submitAreaSpellDamage();
        else confirmAreaSpell();
        return true;
      }
      if (combat.enemy_turn_preview) return false;
      const actor = combat.current_actor || {};
      if (actor.faction === 'enemy') { resolveEnemyTurn(); return true; }
      return false;
    }
    if (initiative && initiative.status !== 'completed') { submitEncounterInitiativeRoll(); return true; }
    if (setup && setup.status === 'completed' && !initiative) { startEncounterInitiative(); return true; }
    if (setup && setup.current_step && setup.current_step.requires_board_assignment) return false;
    if (setup && setup.status === 'active') { confirmEncounterSetup(); return true; }
    if (!setup) { startEncounterSetup(); return true; }
  }
  if (isVisible('flow-panel')) {
    const stage = state.flow ? state.flow.stage : '';
    const preview = state.flow ? state.flow.preview_zone : null;
    if (stage === 'location_preview' && preview && preview.available !== false) { confirmLocationPreview(); return true; }
    if (stage === 'party_setup' && state.exploration_setup) { confirmExplorationSetup(); return true; }
    if (stage === 'interaction_result') { finishInteraction(); return true; }
    if (stage === 'ready_to_start') { startSession(); return true; }
  }
  return false;
}
document.addEventListener('keydown', event => {
  if (event.key !== 'Enter') return;
  const target = event.target;
  if (target && target.tagName === 'TEXTAREA' && event.shiftKey) return;
  if (target && target.closest && target.closest('details.debug-panel')) return;
  if (triggerPrimaryAction()) {
    event.preventDefault();
  }
});
setSidePanelOpen(sidePanelOpen);
loadState();
