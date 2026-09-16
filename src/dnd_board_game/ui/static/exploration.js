let state = null;
let busy = false;
let resultAck = null;
let boardScanInFlight = false;
let boardScanPromise = null;
let boardScanStopPromise = null;
let boardScanToken = 0;
let combatTurnActionMoveDelta = 0;
let combatTurnActionMoveTimer = null;
let combatTurnActionMoveInFlight = false;
let combatScreenFallbackOpen = false;
let combatActorDetailsActorId = '';
let boardInputPhase = 'idle';
let boardListeningRevision = '';
let lastAttemptedBoardRevision = '';
let boardScanError = '';
let boardAutoArmTimer = null;
let lastBoardSelectionRevision = 0;
let sessionLog = null;
let decisionCorrectionOpen = false;
let chatInstanceOpen = true;
let activeInteractionId = null;
let waitingForGm = false;
let optimisticPlayerMessage = null;
const slashCommands = [];
let selectedInteractionGoalId = null;
let selectedInteractionCheckParticipants = null;
let selectedInteractionActorIds = [];
let selectedSocialSkill = null;
let interactionComposerStep = 'participants';
let interactionDescriptionDraft = '';
let selectedInteractionActionSourceId = null;
let selectedZoneOptionId = null;
let selectedZoneOptionActorId = null;
let selectedPointPreviewId = null;
let selectedTradeActorId = '';
let selectedDowntimeActorId = '';
let downtimePanelOpen = false;
let continuationPanelOpen = false;
let selectedContinuationPace = 'normal';
let selectedContinuationNavigatorId = '';
let continuationStep = 'pace';
let filteredSlashCommands = [];
let activeSlashCommandIndex = 0;
let sidePanelOpen = localStorage.getItem('explorationSidePanelOpen') === 'true';
let sidePanelTab = localStorage.getItem('explorationSidePanelTab') || 'game';
let selectedPanelActorId = localStorage.getItem('explorationPanelActorId') || '';
let boardFallbackEnabled = localStorage.getItem('explorationBoardFallback') === 'true';
let pendingClassFeatureActionId = '';
let boardConnectionNotice = '';
let boardConnectionInFlight = false;
let selectedPlaygroundAuditCaseId = '';
let physicalCardStatusTimer = null;
let physicalCardScanInFlight = false;
let lastPhysicalCardPayload = '';
let lastPhysicalCardScanAt = 0;
let physicalCardKeyBuffer = '';
let physicalCardKeyTarget = null;
let physicalCardLastKeyAt = 0;
let physicalCardKeyTimer = null;
let physicalCardRecentKeys = '';
let physicalCardRecentKeyAt = 0;
let spellPreparationDraft = null;
let keyboardRollWizard = null;

const PHYSICAL_CARD_PREFIX = 'dndbg:';
const PHYSICAL_CARD_MAX_KEY_GAP_MS = 100;
const PHYSICAL_CARD_BUFFER_TIMEOUT_MS = 140;
const PHYSICAL_CARD_REPEAT_GUARD_MS = 1200;
const PHYSICAL_CARD_RECENT_KEY_GAP_MS = 2000;
const PHYSICAL_CARD_PAYLOAD_PATTERN = /dndbg:v[0-9]+:(?:action:[a-z0-9_]+:[a-z][a-z0-9_]*(?::[a-z][a-z0-9_]*)?|actor:[a-z][a-z0-9_]*)/;

function closeSlashCommandMenu() {
  const menu = document.getElementById('slash-command-menu');
  const input = document.getElementById('action');
  filteredSlashCommands = [];
  activeSlashCommandIndex = 0;
  if (menu) menu.hidden = true;
  if (input) input.setAttribute('aria-expanded', 'false');
}
function slashCommandQuery(value) {
  if (!value.startsWith('/')) return null;
  const token = value.slice(1);
  if (/\s/.test(token)) return null;
  return token.toLocaleLowerCase('pl');
}
function renderSlashCommandMenu() {
  const menu = document.getElementById('slash-command-menu');
  const input = document.getElementById('action');
  if (!menu || !input) return;
  const query = slashCommandQuery(input.value);
  if (query === null) {
    closeSlashCommandMenu();
    return;
  }
  filteredSlashCommands = slashCommands.filter(command => command.name.toLocaleLowerCase('pl').startsWith(query));
  if (!filteredSlashCommands.length) {
    closeSlashCommandMenu();
    return;
  }
  activeSlashCommandIndex = Math.min(activeSlashCommandIndex, filteredSlashCommands.length - 1);
  menu.replaceChildren(...filteredSlashCommands.map((command, index) => {
    const option = document.createElement('button');
    option.type = 'button';
    option.className = `slash-command-option${index === activeSlashCommandIndex ? ' active' : ''}`;
    option.setAttribute('role', 'option');
    option.setAttribute('aria-selected', index === activeSlashCommandIndex ? 'true' : 'false');
    option.innerHTML = `<span class="slash-command-name">/${esc(command.name)}</span><span class="slash-command-copy"><b>${esc(command.label)}</b><span>${esc(command.description)}</span></span>`;
    option.addEventListener('mousedown', event => event.preventDefault());
    option.addEventListener('click', () => selectSlashCommand(index));
    return option;
  }));
  menu.hidden = false;
  input.setAttribute('aria-expanded', 'true');
}
function selectSlashCommand(index) {
  const input = document.getElementById('action');
  const command = filteredSlashCommands[index];
  if (!input || !command) return false;
  input.value = `/${command.name}${command.intent === 'help' ? '' : ' '}`;
  input.placeholder = command.placeholder || 'Napisz wiadomość do MG...';
  closeSlashCommandMenu();
  input.focus();
  input.setSelectionRange(input.value.length, input.value.length);
  return true;
}
function handleSlashCommandInput() {
  activeSlashCommandIndex = 0;
  const input = document.getElementById('action');
  if (input && !input.value.startsWith('/')) input.placeholder = 'Napisz wiadomość do MG...';
  renderSlashCommandMenu();
}
function handleSlashCommandKeydown(event) {
  const menu = document.getElementById('slash-command-menu');
  if (!menu || menu.hidden || !filteredSlashCommands.length) return;
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    const direction = event.key === 'ArrowDown' ? 1 : -1;
    activeSlashCommandIndex = (activeSlashCommandIndex + direction + filteredSlashCommands.length) % filteredSlashCommands.length;
    renderSlashCommandMenu();
    const active = menu.querySelector('.slash-command-option.active');
    if (active) active.scrollIntoView({block: 'nearest'});
    event.preventDefault();
    return;
  }
  if (event.key === 'Enter' && !event.shiftKey) {
    if (selectSlashCommand(activeSlashCommandIndex)) event.preventDefault();
    return;
  }
  if (event.key === 'Escape') {
    closeSlashCommandMenu();
    event.preventDefault();
  }
}
function setSidePanelOpen(open) {
  sidePanelOpen = Boolean(open);
  localStorage.setItem('explorationSidePanelOpen', sidePanelOpen ? 'true' : 'false');
  document.body.classList.toggle('side-panel-open', sidePanelOpen);
  const panel = document.getElementById('side-panel');
  const toggle = document.getElementById('side-panel-toggle');
  if (panel) panel.setAttribute('aria-hidden', sidePanelOpen ? 'false' : 'true');
  if (toggle) toggle.setAttribute('aria-expanded', sidePanelOpen ? 'true' : 'false');
  if (sidePanelOpen && panel) window.requestAnimationFrame(() => panel.querySelector('[data-side-panel-tab].active')?.focus());
}
function toggleSidePanel() {
  setSidePanelOpen(!sidePanelOpen);
}
function setSidePanelTab(tab) {
  const allowed = new Set(['game', 'party', 'states', 'spells', 'inventory', 'developer']);
  sidePanelTab = allowed.has(tab) ? tab : 'game';
  localStorage.setItem('explorationSidePanelTab', sidePanelTab);
  document.querySelectorAll('[data-side-panel-tab]').forEach(button => {
    const active = button.dataset.sidePanelTab === sidePanelTab;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', active ? 'true' : 'false');
  });
  document.querySelectorAll('[data-side-panel-content]').forEach(panel => {
    panel.hidden = panel.dataset.sidePanelContent !== sidePanelTab;
  });
  renderPanelActorSelector();
}
function handleSidePanelTabKeydown(event) {
  if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
  const tabs = Array.from(document.querySelectorAll('[data-side-panel-tab]'));
  const current = tabs.indexOf(document.activeElement);
  if (current < 0) return;
  const direction = event.key === 'ArrowRight' ? 1 : -1;
  const next = tabs[(current + direction + tabs.length) % tabs.length];
  setSidePanelTab(next.dataset.sidePanelTab);
  next.focus();
  event.preventDefault();
}
function setBusy(message) {
  busy = Boolean(message);
  waitingForGm = Boolean(message && (message.includes('MG') || message.includes('NPC')));
  const status = document.getElementById('status');
  status.hidden = !busy;
  status.textContent = message || '';
  const typing = document.getElementById('chat-typing');
  if (typing) typing.hidden = !waitingForGm;
  const typingLabel = document.getElementById('chat-typing-label');
  if (typingLabel && waitingForGm) {
    const npcName = state && state.active_point && state.active_point.npc
      ? state.active_point.npc.name
      : '';
    typingLabel.textContent = npcName
      ? `${npcName} zastanawia się nad odpowiedzią…`
      : 'MG zastanawia się nad odpowiedzią…';
  }
  const leaveButton = document.getElementById('leave-interaction-button');
  if (leaveButton) {
    const unresolved = Boolean(state && state.pending && state.pending.stage) || Boolean(state && state.required_rolls && state.required_rolls.length);
    leaveButton.disabled = busy || unresolved;
  }
  document.querySelectorAll('button, textarea, input').forEach(el => {
    if (el.closest('.developer-panel')) return;
    if (el.dataset.allowBusy === 'true') return;
    if (!busy) {
      if (Object.hasOwn(el.dataset, 'busyWasDisabled')) {
        el.disabled = el.dataset.busyWasDisabled === 'true';
        delete el.dataset.busyWasDisabled;
      }
      return;
    }
    if (!Object.hasOwn(el.dataset, 'busyWasDisabled')) {
      el.dataset.busyWasDisabled = el.disabled ? 'true' : 'false';
    }
    const gameplayControl = Boolean(el.closest(
      '#action-panel, #flow-panel, #encounter-panel, #pending-panel, #roll-panel, #result-panel'
    ));
    el.disabled = el.disabled || !waitingForGm || gameplayControl;
  });
  document.body.classList.toggle('gm-request-pending', waitingForGm);
}
let lastFailedGmRequest = null;
let gmSlowResponseTimer = null;
function setChatRetry(request, message) {
  lastFailedGmRequest = request;
  const panel = document.getElementById('chat-retry');
  const copy = document.getElementById('chat-retry-message');
  if (copy) copy.textContent = message || 'Nie udało się uzyskać odpowiedzi MG.';
  if (panel) panel.hidden = !request;
}
async function retryLastGmRequest() {
  if (!lastFailedGmRequest) return;
  const request = lastFailedGmRequest;
  setChatRetry(null, '');
  await api(request.path, request.body, request.busyMessage);
}
function resetInteractionSelection() {
  selectedInteractionGoalId = null;
  selectedInteractionCheckParticipants = null;
  selectedInteractionActorIds = [];
  selectedSocialSkill = null;
  interactionComposerStep = 'participants';
  interactionDescriptionDraft = '';
  selectedInteractionActionSourceId = null;
  selectedZoneOptionId = null;
  selectedZoneOptionActorId = null;
  selectedPointPreviewId = null;
  downtimePanelOpen = false;
  continuationPanelOpen = false;
}
function synchronizeBoardSelection({force = false} = {}) {
  const boardInteraction = state && state.flow ? state.flow.board_interaction : null;
  if (!boardInteraction) return false;
  const revision = Number(boardInteraction.selection_revision || 0);
  if (!force && revision <= lastBoardSelectionRevision) return false;
  lastBoardSelectionRevision = revision;
  const actorSelection = boardInteraction.actor_selection || {};
  const selectedActorId = actorSelection.selected_actor_id
    ? String(actorSelection.selected_actor_id)
    : '';
  if (selectedActorId || actorSelection.role === 'whole_party') {
    const goalId = String(actorSelection.goal_id || boardInteraction.selected_goal_id || '');
    const goal = currentInteractionGoals().find(item => String(item.id) === goalId);
    if (!goal) return false;
    if (selectedInteractionGoalId !== goalId) {
      resetInteractionSelection();
      selectedInteractionGoalId = goalId;
      selectedSocialSkill = null;
    }
    if (actorSelection.role === 'whole_party') {
      selectedInteractionActorIds = [];
      selectedInteractionCheckParticipants = 'whole_party';
    } else if (actorSelection.role === 'helper') {
      selectedInteractionActorIds = [
        ...selectedInteractionActorIds.filter(id => id !== selectedActorId),
        selectedActorId,
      ].slice(0, 2);
      selectedInteractionCheckParticipants = 'lead_with_help';
    } else {
      selectedInteractionActorIds = [selectedActorId];
      const options = goal.allowed_check_participants || [goal.check_participants || 'single_actor'];
      selectedInteractionCheckParticipants = options.includes('single_actor')
        ? 'single_actor'
        : 'lead_with_help';
    }
    prepareObviousInteractionChoices(goal);
    if ((goal.social_skill_options || []).length && selectedInteractionActorIds.length) {
      interactionComposerStep = 'approach';
    }
    scheduleImmediateInteractionGoal(goal);
    return true;
  }
  resetInteractionSelection();
  if (boardInteraction.selected_goal_id) {
    const boardGoalId = String(boardInteraction.selected_goal_id);
    const goal = currentInteractionGoals().find(item => String(item.id) === boardGoalId);
    if (goal) {
      selectedInteractionGoalId = boardGoalId;
      selectedInteractionCheckParticipants = goal.participant_mode === 'must'
        ? goal.check_participants
        : null;
      selectedSocialSkill = null;
      prepareObviousInteractionChoices(goal);
      if ((goal.social_skill_options || []).length && selectedInteractionActorIds.length) {
        interactionComposerStep = 'approach';
      }
      scheduleImmediateInteractionGoal(goal);
    }
  }
  if (boardInteraction.selected_panel === 'downtime') downtimePanelOpen = true;
  if (boardInteraction.selected_panel === 'continuation') {
    if (!continuationPanelOpen) {
      continuationStep = 'pace';
      selectedContinuationPace = 'normal';
      selectedContinuationNavigatorId = '';
    }
    continuationPanelOpen = true;
  }
  if (
    boardInteraction.selected_action_kind === 'zone_option'
    && boardInteraction.selected_action_id
  ) {
    selectedZoneOptionId = String(boardInteraction.selected_action_id);
    const selectedOption = (((state || {}).flow || {}).zone_options || []).find(
      option => String(option.id) === selectedZoneOptionId
    );
    selectedZoneOptionActorId = selectedOption && selectedOption.assigned_actor_id
      ? String(selectedOption.assigned_actor_id)
      : '';
  }
  if (
    boardInteraction.selected_action_kind === 'point'
    && boardInteraction.selected_action_id
  ) {
    selectedPointPreviewId = String(boardInteraction.selected_action_id);
  }
  return Boolean(
    boardInteraction.selected_goal_id
    || boardInteraction.selected_panel
    || boardInteraction.selected_action_id
  );
}
async function api(path, body, busyMessage) {
  const previousStage = state && state.flow ? state.flow.stage : null;
  const previousInteractionId = state && state.conversation ? state.conversation.interaction_id : null;
  const previousMessageCount = state && state.messages ? state.messages.length : 0;
  const gmRequest = Boolean(busyMessage && (busyMessage.includes('MG') || busyMessage.includes('NPC')));
  const retryRequest = gmRequest ? {path, body: body || {}, busyMessage} : null;
  setBusy(busyMessage || 'Czekam na odpowiedź...');
  clearTimeout(boardAutoArmTimer);
  boardAutoArmTimer = null;
  if (boardPanelSyncPromise) await boardPanelSyncPromise;
  if (boardScanInFlight && path !== '/api/board/reset-scan') {
    await stopBoardScanLoop();
  }
  if (gmRequest) {
    setChatRetry(null, '');
    clearTimeout(gmSlowResponseTimer);
    gmSlowResponseTimer = setTimeout(() => {
      const label = document.getElementById('chat-typing-label');
      if (label && waitingForGm) {
        label.textContent = 'Odpowiedź trwa dłużej niż zwykle — nadal czekam…';
      }
    }, 15000);
  }
  try {
    const res = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body || {})});
    const data = await res.json();
    if (!res.ok) {
      if (retryRequest) {
        setChatRetry(retryRequest, 'MG nie zwrócił poprawnej odpowiedzi. Możecie bezpiecznie ponowić zapytanie.');
      } else {
        alert(data.error || 'Błąd');
      }
    }
    if (res.ok && data.redirect) { window.location.assign(data.redirect); return {ok:true}; }
    if (res.ok && data.panel_event) {
      window.setTimeout(() => { handleBoardPanelEvent(data); scheduleAutomaticBoardScan(); }, 0);
      return {ok: true};
    }
    state = data.state || data;
    const nextStage = state && state.flow ? state.flow.stage : null;
    const nextInteractionId = state && state.conversation ? state.conversation.interaction_id : null;
    if (nextStage === 'location_active' && (previousStage !== 'location_active' || nextInteractionId !== previousInteractionId)) {
      chatInstanceOpen = true;
    }
    if (nextInteractionId !== previousInteractionId) {
      resetInteractionSelection();
    }
    synchronizeBoardSelection();
    if (path === '/api/action' && res.ok && !(body && body.conversation_only)) {
      selectedInteractionGoalId = null;
      selectedInteractionCheckParticipants = null;
      selectedInteractionActorIds = [];
      selectedSocialSkill = null;
      selectedInteractionActionSourceId = null;
    }
    if (path === '/api/exploration/option' && res.ok) {
      selectedZoneOptionId = null;
      selectedZoneOptionActorId = null;
    }
    activeInteractionId = nextInteractionId;
    optimisticPlayerMessage = null;
    if (path === '/api/rolls' && res.ok) {
      resultAck = state.flow && state.flow.stage === 'interaction_result'
        ? null
        : latestResultMessageSince(state, previousMessageCount);
    } else if (path === '/api/combat/skill-check' && res.ok) {
      resultAck = latestMessageWithTitleSince(state, 'Ukrycie Miry', previousMessageCount);
    } else if (path === '/api/combat/opportunity-movement/confirm' && res.ok) {
      resultAck = latestMessageWithTitle(state, 'Atak okazyjny');
    } else if (path === '/api/combat/player-attack-confirm' && res.ok) {
      const spellResult = latestMessageWithTitleSince(state, 'Czar', previousMessageCount);
      resultAck = spellResult && spellResult.body.includes('rzut obronny')
        ? {title: 'Rzut obronny przeciwnika', body: spellResult.body}
        : null;
    } else if (path === '/api/combat/player-damage' && res.ok) {
      const damageResult = latestMessageWithTitle(state, 'Obrażenia');
      resultAck = damageResult && damageResult.body.includes('Cel zostaje pokonany')
        ? {title: 'PRZECIWNIK POKONANY', body: damageResult.body}
        : null;
    } else if (path !== '/api/decision') {
      resultAck = null;
    }
    render();
    refreshSessionLog();
    return {ok: res.ok, data};
  } catch (error) {
    if (retryRequest) {
      setChatRetry(
        retryRequest,
        'Połączenie z MG zostało przerwane lub przekroczono timeout dostawcy. Spróbujcie ponownie.'
      );
      optimisticPlayerMessage = null;
      render();
      return {ok: false, error};
    }
    alert('Nie udało się połączyć z aplikacją.');
    return {ok: false, error};
  } finally {
    clearTimeout(gmSlowResponseTimer);
    setBusy('');
    initializeKeyboardRollWizard();
    focusCombatDecision();
    scheduleAutomaticBoardScan();
  }
}
async function loadState() {
  const res = await fetch('/api/state');
  state = await res.json();
  activeInteractionId = state.conversation ? state.conversation.interaction_id : null;
  lastBoardSelectionRevision = -1;
  synchronizeBoardSelection({force: true});
  chatInstanceOpen = true;
  const board = state.board || {};
  // A reload loses the browser promise, but its server scan can still wait.
  if (board.connected) await stopBoardScanLoop({force: true});
  if (!board.connected && !boardFallbackEnabled
      && ['hardware', 'simulator'].includes(board.configured_backend)) {
    await retryBoardConnection();
  } else {
    render();
  }
  refreshSessionLog();
  focusCombatDecision();
  scheduleAutomaticBoardScan();
}
function render() {
  closeKeyboardRollWizard();
  const existingConversationScroll = document.getElementById('chat-conversation-scroll');
  const followChatTail = !existingConversationScroll
    || existingConversationScroll.scrollHeight - existingConversationScroll.scrollTop - existingConversationScroll.clientHeight < 120;
  const inCombat = Boolean(state.combat);
  renderTrainingArena();
  renderMission();
  const interactionId = state.conversation ? state.conversation.interaction_id : null;
  if (activeInteractionId === null) activeInteractionId = interactionId;
  if (interactionId && interactionId !== activeInteractionId) {
    activeInteractionId = interactionId;
    chatInstanceOpen = true;
    selectedInteractionGoalId = null;
    selectedInteractionCheckParticipants = null;
    selectedInteractionActorIds = [];
    selectedSocialSkill = null;
    selectedInteractionActionSourceId = null;
  }
  const modeLabel = currentModeLabel();
  document.getElementById('app-mode-label').textContent = modeLabel;
  document.getElementById('encounter-title').textContent = inCombat ? 'Walka'
    : state.training_arena?.mode === 'walkthrough' ? 'Przygotowanie ćwiczenia' : 'Nadchodzi starcie';
  document.getElementById('scenario').textContent = state.scenario.name;
  document.getElementById('zone').textContent = state.current_zone.name;
  document.getElementById('panel-zone-name').textContent = state.current_zone.name;
  document.getElementById('scene-status-summary').innerHTML = sceneStatusSummaryHtml();
  document.getElementById('briefing-contract').innerHTML = briefingContractHtml();
  renderPartyShell();
  document.getElementById('challenge').textContent = state.active_challenge
    ? state.active_challenge.uses_progress
      ? `${state.active_challenge.name}: ${state.active_challenge.current_progress}/${state.active_challenge.progress_required}, hałas ${state.active_challenge.noise}`
      : `${state.active_challenge.name}: stan oparty na elementach bramy, czujność ${state.active_challenge.noise}/3`
    : 'Brak';
  document.getElementById('visible-environment').innerHTML = visibleEnvironmentHtml();
  document.getElementById('resources').innerHTML = state.resources.map(r => {
    const kind = r.temporary ? ' · przedmiot sceny' : (r.consume_on_use ? ' · jednorazowy' : '');
    const uses = r.temporary ? ` · użycia ${Number(r.uses_remaining || 0)}` : '';
    const risk = r.risk ? `<br><span class="muted">Ryzyko: ${esc(r.risk)}</span>` : '';
    const dismantle = r.temporary && r.purpose_id && !r.dismantled
      ? `<br><button class="secondary" onclick="dismantleCraftedItem('${esc(r.id)}')">Rozmontuj</button>`
      : '';
    return `<div>${esc(r.label)}${kind}${uses}${risk}${dismantle}</div>`;
  }).join('') || 'Brak';
  document.getElementById('discovered-sources').innerHTML = discoveredSourcesHtml();
  document.getElementById('active-effects').innerHTML = activeEffectsHtml();
  renderSnapshotPanel();
  const finishScenarioButton = document.getElementById('finish-scenario-button');
  const continuation = state.flow.continuation;
  finishScenarioButton.disabled = Boolean(state.combat)
    || ['spell_preparation','short_rest','game_over','scenario_complete'].includes(state.flow.stage)
    || Boolean(continuation && !continuation.available);
  finishScenarioButton.textContent = state.flow.stage === 'scenario_complete'
    ? 'Scenariusz zakończony'
    : continuation
      ? (continuation.available ? continuation.label : 'Najpierw ukończ przygotowania')
      : 'Zakończ scenariusz';
  renderBoardPanel();
  renderBoardConnectionIndicator();
  renderBoardFallback();
  document.getElementById('flow-panel').innerHTML = flowPanelHtml();
  const sceneHtml = sceneDescriptionHtml(state);
  document.getElementById('scene-description').innerHTML = sceneHtml;
  document.getElementById('scene-description-card').hidden = !sceneHtml;
  const conversation = document.getElementById('scene-conversation');
  renderExplorationCardPrompt();
  conversation.innerHTML = sceneConversationHtml();
  document.getElementById('chat-typing').hidden = !waitingForGm;
  document.getElementById('messages').innerHTML = state.messages.map(message => messageCardHtml(message)).join('');
  document.getElementById('pending').innerHTML = pendingHtml(state.pending);
  document.getElementById('pending-title').textContent = pendingTitle(state.pending);
  document.getElementById('pending-accept-button').textContent = state.pending && state.pending.kind === 'source_selection' ? 'Wybierz' : state.pending && state.pending.kind === 'collection' ? 'Zabierz' : 'Akceptuj';
  document.getElementById('pending-reject-button').textContent = state.pending && state.pending.kind === 'source_selection' ? 'Nie wybieram' : 'Odrzuć';
  document.getElementById('lead-actor-choice').innerHTML = leadActorChoiceHtml();
  document.getElementById('result').innerHTML = resultAck ? messageCardHtml(resultAck, 'interaction-result-summary') : '';
  const resultAckButton = document.getElementById('result-ack-button');
  if (resultAckButton) resultAckButton.textContent = state.combat ? 'Przeczytałem — wróć do tury' : 'Kontynuuj rozmowę';
  document.getElementById('encounter').innerHTML = encounterHtml();
  document.getElementById('travel-options').innerHTML = travelOptionsHtml();
  document.getElementById('point-options').innerHTML = pointOptionsHtml();
  document.getElementById('roll-prompt').innerHTML = rollPromptHtml();
  document.getElementById('rolls').innerHTML = state.required_rolls.map(r => {
    const sides = Number(r.die_sides || 20);
    const value = sides === 100 ? 50 : 10;
    const plan = state.pending && state.pending.stage === 'roll' ? (state.pending.check_plan || {}) : {};
    const actor = actorById(r.actor_id);
    const namedCheck = actor?.uses_charge && plan.ability ? abilityLabel(plan.ability) : plan.skill ? skillLabel(plan.skill) : '';
    const rollLabel = namedCheck ? `${namedCheck} d20` : (r.label || `d${sides}`);
    const inspiration = r.bardic_inspiration;
    const inspirationInput = inspiration ? `<label class="roll-entry">${actorPortraitHtml(actor, 'roll')}<span>${esc(r.actor_name)} — ${esc(inspiration.label || 'Bardic Inspiration')} (opcjonalnie):</span> <input data-actor="${esc(r.actor_id)}" data-roll-kind="bardic-inspiration" type="number" min="1" max="${Number(inspiration.die_sides)}" placeholder="nie używaj"></label>` : '';
    const guidance = r.guidance;
    const guidanceInput = guidance ? `<label class="roll-entry">${actorPortraitHtml(actor, 'roll')}<span>${esc(r.actor_name)} — ${esc(guidance.label || 'Wskazówki')} (opcjonalnie k4):</span> <input data-actor="${esc(r.actor_id)}" data-roll-kind="guidance" type="number" min="1" max="${Number(guidance.die_sides)}" placeholder="nie używaj"></label>` : '';
    const improvisation = r.improvisation;
    const improvisationInput = improvisation ? `<label class="roll-entry">${actorPortraitHtml(actor, 'roll')}<span>${esc(r.actor_name)} — ${esc(improvisation.label || 'Improwizacja')} (tylko po porażce):</span> <input data-actor="${esc(r.actor_id)}" data-roll-kind="improvisation" type="number" min="1" max="20" placeholder="bez przerzutu"></label>` : '';
    if (r.requires_second_roll) {
      return `<label class="roll-entry">${actorPortraitHtml(actor, 'roll')}<span>${esc(r.actor_name)} — ${esc(rollLabel)} #1:</span> <input data-actor="${esc(r.actor_id)}" data-roll-index="1" type="number" min="1" max="${sides}" value="${value}"></label>
        <label class="roll-entry">${actorPortraitHtml(actor, 'roll')}<span>${esc(r.actor_name)} — ${esc(rollLabel)} #2:</span> <input data-actor="${esc(r.actor_id)}" data-roll-index="2" type="number" min="1" max="${sides}" value="${value + 3 > sides ? value - 3 : value + 3}"></label>${inspirationInput}${guidanceInput}${improvisationInput}`;
    }
    return `<label class="roll-entry">${actorPortraitHtml(actor, 'roll')}<span>${esc(r.actor_name)} — ${esc(rollLabel)}:</span> <input data-actor="${esc(r.actor_id)}" data-roll-index="1" type="number" min="1" max="${sides}" value="${value}"></label>${inspirationInput}${guidanceInput}${improvisationInput}`;
  }).join(' ');
  document.getElementById('debug-payload').textContent = JSON.stringify(state, null, 2);
  renderPlaygroundPanel();
  renderSessionLogMeta();
  document.getElementById('action-title').textContent = state.active_point
    ? state.active_point.name
    : state.current_zone.name;
  document.getElementById('conversation-meta').innerHTML = conversationMetaHtml();
  renderInteractionWorkspace();
  document.getElementById('interaction-goals').innerHTML = interactionGoalsHtml();
  updateActivePanel();
  updateBoardInputPresentation();
  initializeKeyboardRollWizard();
  scheduleAutomaticBoardScan();
  scrollChatToBottom(followChatTail);
  focusCombatDecision();
}

function isKeyboardRollInput(input) {
  if (!input || input.type !== 'number' || input.disabled) return false;
  if (input.closest('#rolls, .precombat-stealth-roll, #exploration-mana-roll, #mission-roll, #simple-trap-roll')) return true;
  if (!input.closest('#encounter')) return false;
  const id = String(input.id || '');
  return (
    /(?:^|-)roll(?:-|$)/.test(id)
    || /(?:^|-)damage(?:-|$)/.test(id)
    || input.classList.contains('physical-feature-saving-roll')
    || input.classList.contains('class-feature-saving-roll')
  );
}

function visibleKeyboardRollInputs() {
  return Array.from(document.querySelectorAll('input[type="number"]')).filter(input => (
    isKeyboardRollInput(input)
    && input.offsetParent !== null
  ));
}

function keyboardRollSubmitButton(inputs) {
  const first = inputs[0];
  if (!first) return null;
  const root = first.closest('#roll-panel, .combat-action-card, .precombat-stealth-roll, #exploration-mana-roll, #mission-roll, #simple-trap-roll, #encounter');
  if (!root) return null;
  if (root.matches('#exploration-mana-roll, #mission-roll, #simple-trap-roll')) return root.querySelector('button[type="submit"]');
  const buttons = Array.from(root.querySelectorAll('button')).filter(button => (
    !button.disabled
    && !button.classList.contains('secondary')
    && button.dataset.primaryScan !== 'true'
    && button.offsetParent !== null
  ));
  const preferred = buttons.filter(button => /^(submit|confirm|send|spend|resolve|return)/i.test(
    String(button.getAttribute('onclick') || '')
  ));
  return preferred.length === 1 ? preferred[0] : (buttons.length === 1 ? buttons[0] : null);
}

function parseKeyboardDice(dice) {
  const match = String(dice || '').match(/(\d+)\s*[dk]\s*(\d+)/i);
  if (!match) return null;
  const count = Number(match[1]);
  const sides = Number(match[2]);
  if (!Number.isInteger(count) || !Number.isInteger(sides) || count < 1 || sides < 2) return null;
  return {count, sides, label: `${count}k${sides}`};
}

function keyboardRollInputLabel(input, index) {
  if (input.dataset.rollLabel) return input.dataset.rollLabel;
  const label = input.closest('label');
  if (label) {
    const clone = label.cloneNode(true);
    clone.querySelectorAll('input, select, button, small').forEach(element => element.remove());
    const text = clone.textContent.replace(/\s+/g, ' ').trim().replace(/:\s*$/, '');
    if (text) return text;
  }
  return `Rzut ${index + 1}`;
}

function keyboardRollStep(input, index) {
  const dice = parseKeyboardDice(input.dataset.rollDice);
  const modifier = Number(input.dataset.rollModifier || 0);
  const fixedText = input.dataset.rollFixed;
  const fixed = fixedText === undefined ? null : Number(fixedText);
  const optional = !input.required && Boolean(input.placeholder);
  const originalMin = input.min === '' ? null : Number(input.min);
  const originalMax = input.max === '' ? null : Number(input.max);
  return {
    input,
    label: keyboardRollInputLabel(input, index),
    dice,
    modifier,
    fixed,
    source: input.dataset.rollSource || '',
    optional,
    min: dice ? dice.count : originalMin,
    max: dice ? dice.count * dice.sides : originalMax,
    raw: null,
    total: null,
  };
}

function keyboardRollContextLines(root) {
  if (root.id === 'mission-roll') return [state.mission.text.body];
  if (root.id === 'exploration-mana-roll') {
    const a = state.exploration_mana.attempt;
    if (state.exploration_mana.model === 'party_confrontation') return [`${a.actor} · ${a.method}`, state.exploration_mana.die_kind === 'test' ? 'Test przeciw ST. Wpisz naturalny wynik k20; premie doliczamy w podsumowaniu.' : `Wpływ: rzuć k${a.die}. Modyfikator cechy i pasywy doliczamy raz.`];
    return [`${a.actor} · ${a.method}`, a.busted
      ? 'Utrudnienie: dwie k20, liczy się niższa. Premię doliczamy raz do niższego wyniku. Bez premii za karty.'
      : 'Test k20. Po ustawieniu kości sprawdź podsumowanie i zatwierdź cały rzut.'];
  }
  const nodes = [];
  const prompt = document.querySelector('.combat-current-step .combat-prompt');
  if (prompt && root.closest('.combat-current-step')) nodes.push(prompt);
  if (root.id === 'roll-panel') {
    const rollPrompt = document.getElementById('roll-prompt');
    if (rollPrompt) nodes.push(...rollPrompt.querySelectorAll('p'));
  } else {
    nodes.push(...root.querySelectorAll(':scope > p, :scope > .combat-action-box > p, :scope > .combat-warning'));
  }
  const seen = new Set();
  return nodes.map(node => node.textContent.replace(/\s+/g, ' ').trim()).filter(text => {
    if (!text || seen.has(text)) return false;
    seen.add(text);
    return true;
  }).slice(0, 5);
}

function activeKeyboardRollPending(input) {
  if (input.closest('#exploration-mana-roll')) {
    const a = state.exploration_mana.attempt;
    return {modifier_total:a.modifier_total, active_modifiers:a.modifiers};
  }
  if (input.closest('#simple-trap-roll')) {
    const items = state.training_arena.trap.modifiers;
    return {modifier_total:items.reduce((sum,m)=>sum+m.value,0), active_modifiers:items};
  }
  const combat = (state && state.combat) || {};
  const id = String(input.id || '');
  if (id.startsWith('shield-bash-') && combat.shield_bash) {
    const modifier = combat.shield_bash.attacker_modifier;
    return {modifier_total:modifier, active_modifiers:[{label:'Siła', value:modifier}]};
  }
  if (input.dataset.rollKind || /(?:inspiration|bless|mirror-image)/.test(id)) return {};
  if (input.closest('#rolls')) {
    return (state.required_rolls || []).find(required => (
      String(required.actor_id) === String(input.dataset.actor || '')
    )) || {};
  }
  if (id.startsWith('combat-attack-') || id.startsWith('combat-damage-')) return combat.pending_player_attack || {};
  if (id.startsWith('area-spell-')) return combat.pending_area_spell || {};
  if (id.startsWith('ready-')) return combat.pending_ready_attack || {};
  if (id.startsWith('enemy-opportunity-')) return combat.pending_enemy_opportunity_attack || {};
  if (id.startsWith('enemy-saving-throw-')) return combat.pending_enemy_saving_throw || {};
  if (id.startsWith('combat-condition-save-')) return (combat.condition_saves || [])[0] || {};
  if (id.startsWith('concentration-check-')) return combat.pending_concentration_check || {};
  if (id.startsWith('combat-shove-')) return combat.pending_combat_shove || {};
  if (id.startsWith('combat-grapple-')) return combat.pending_combat_grapple || {};
  if (id.startsWith('combat-skill-check-')) return combat.pending_combat_skill_check || {};
  return {};
}

function keyboardRollModifierSummary(step) {
  if (step.input.id.startsWith('encounter-initiative-roll')) {
    const modifier = Number(state?.encounter_initiative?.current_prompt?.dexterity_modifier || 0);
    return {total: modifier, items: [`Inicjatywa ${signedNumber(modifier)}`]};
  }
  if (step.input.dataset.rollModifier !== undefined) {
    return {
      total: step.modifier,
      items: step.modifier
        ? [`${step.source || 'Modyfikator składnika'} ${signedNumber(step.modifier)}`]
        : [],
    };
  }
  const pending = activeKeyboardRollPending(step.input);
  const items = pending.active_modifiers || pending.modifier_components || [];
  const total = pending.attack_modifier ?? pending.modifier_total ?? pending.modifier ?? null;
  return {
    total: total === null ? null : Number(total),
    items: items.map(item => `${item.label || item.name || 'Modyfikator'} ${signedNumber(item.value || 0)}`),
  };
}

function closeKeyboardRollWizard() {
  const overlay = document.getElementById('keyboard-roll-wizard');
  if (overlay) overlay.remove();
  keyboardRollWizard = null;
}

function initializeKeyboardRollWizard() {
  if (state?.training_arena?.tutorial?.notice) return false;
  if (!state || busy || keyboardRollWizard || document.querySelector('dialog[open]')) return false;
  const inputs = visibleKeyboardRollInputs();
  const submitButton = keyboardRollSubmitButton(inputs);
  if (!inputs.length || !submitButton) return false;
  const allSteps = inputs.map(keyboardRollStep);
  const automatic = allSteps.filter(step => step.fixed !== null && Number.isFinite(step.fixed));
  automatic.forEach(step => {
    step.raw = step.fixed;
    step.total = Math.max(0, step.fixed + step.modifier);
    step.input.value = String(step.total);
  });
  const steps = allSteps.filter(step => step.fixed === null || !Number.isFinite(step.fixed)).flatMap(step => {
    if (!step.dice || step.dice.count === 1) return [step];
    step.parts = Array.from({length: step.dice.count}, (_, index) => ({
      ...step, parent: step, label: `${step.label} · kość ${index + 1}/${step.dice.count}`,
      dice: {...step.dice, count: 1, label: `1k${step.dice.sides}`},
      modifier: 0, min: 1, max: step.dice.sides,
    }));
    return step.parts;
  });
  steps.forEach(step => { step.input.value = ''; step.raw = Math.max(step.min ?? 1, Math.floor((rollStepDieSides(step) || step.max || 20) / 2)); });
  keyboardRollWizard = {
    allSteps,
    steps,
    automatic,
    index: 0,
    review: steps.length === 0,
    submitButton,
    contextLines: keyboardRollContextLines(submitButton.closest('#roll-panel, .combat-action-card, .precombat-stealth-roll, #exploration-mana-roll, #mission-roll, #simple-trap-roll, #encounter')),
  };
  const panel = state.encounter_initiative?.panel;
  if (panel && allSteps.every(step => step.input.id.startsWith('encounter-initiative-roll'))) {
    keyboardRollWizard.initiative = true;
    keyboardRollWizard.index = panel.index;
    keyboardRollWizard.review = panel.review;
    steps.forEach((step, index) => {
      step.raw = panel.values[index];
      step.total = step.raw;
      step.input.value = String(step.raw);
    });
    keyboardRollWizard.contextLines = [state.encounter_initiative.current_prompt.message];
  }
  const overlay = document.createElement('div');
  overlay.id = 'keyboard-roll-wizard';
  overlay.className = 'keyboard-roll-wizard';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');
  overlay.setAttribute('aria-labelledby', 'keyboard-roll-wizard-title');
  overlay.addEventListener('keydown', handleKeyboardRollWizardKeydown);
  document.body.appendChild(overlay);
  renderKeyboardRollWizard();
  scheduleAutomaticBoardScan();
  return true;
}

function keyboardRollStepPrompt(step) {
  if (step.input.id === 'shield-bash-attacker-roll') {
    return 'Rzuć fizyczną k20 za bohatera. Ustaw wynik przyciskami − / + i zatwierdź ✓. Początkowe 10 to tylko ustawienie licznika, nie wylosowany wynik. Aplikacja doliczy Siłę i rzuci za przeciwnika po zatwierdzeniu podsumowania.';
  }
  const sides = rollStepDieSides(step);
  if (sides) return `Rzuć k${sides}. Ustaw naturalny wynik przyciskami − / + i zatwierdź ✓.`;
  const maximum = Number.isFinite(step.max) ? ` (od ${step.min ?? 0} do ${step.max})` : '';
  return `Wpisz wynik rzutu${maximum}.`;
}

function renderKeyboardRollWizard(message = '') {
  const wizard = keyboardRollWizard;
  const overlay = document.getElementById('keyboard-roll-wizard');
  if (!wizard || !overlay) return;
  const totalSteps = wizard.steps.length;
  const manaAttempt = wizard.submitButton.closest('#exploration-mana-roll') ? state.exploration_mana.attempt : null;
  if (wizard.review) {
    const rows = wizard.allSteps.map(step => {
      const identity = `<span class="keyboard-roll-summary-identity">${rollStepDiceIconHtml(step)}<span>${esc(step.label)}</span></span>`;
      if (step.raw === null) return `<li>${identity}<b>pominięto</b></li>`;
      const modifier = keyboardRollModifierSummary(step);
      const appliedModifier = manaAttempt ? 0 : step.modifier || (modifier.total !== null ? modifier.total : 0);
      const rolled = step.parts ? step.parts.map(part => part.raw ?? '—').join(' + ') : step.raw;
      const calculation = appliedModifier
        ? `${rolled} ${signedNumber(appliedModifier)} = ${step.modifier ? step.total : step.raw + appliedModifier}`
        : `${rolled}${step.parts ? ` = ${step.total}` : ''}`;
      const source = !manaAttempt && modifier.items.length ? `<small>${esc(modifier.items.join(' · '))}</small>` : '';
      return `<li><span>${identity}${source}</span><b>${esc(calculation)}</b></li>`;
    }).join('');
    overlay.innerHTML = `
      <div class="keyboard-roll-wizard-backdrop"></div>
      <section class="keyboard-roll-wizard-card" tabindex="-1">
        <span class="keyboard-roll-wizard-kicker">Podsumowanie rzutu</span>
        <h2 id="keyboard-roll-wizard-title">Sprawdź wpisane wyniki</h2>
        <ul class="keyboard-roll-wizard-summary">${rows}</ul>
        ${manaAttempt ? `<div class="keyboard-roll-combined-summary"><p>${manaAttempt.busted?'Niższy wynik':'Wynik kości'}:
          <b>${Math.min(...wizard.allSteps.map(step=>step.raw))} ${signedNumber(manaAttempt.modifier_total)} = ${Math.min(...wizard.allSteps.map(step=>step.raw))+manaAttempt.modifier_total}</b></p>
          <p>${esc(manaAttempt.modifiers.map(m=>`${m.label} ${signedNumber(m.value)}`).join(' · '))}. Premia doliczona raz.</p></div>` : ''}
        ${missionRollSummary(wizard)}${rollPanelControlsHtml(wizard)}

        <div class="keyboard-roll-wizard-actions">${wizard.steps.length ? '<button type="button" class="secondary" onclick="previousKeyboardRollStep()">↩ Wróć</button>' : ''}<button type="button" class="panel-accept" onclick="submitKeyboardRollWizard()">✓ Zastosuj wyniki</button></div>
      </section>`;
    window.requestAnimationFrame(() => {
      const card = overlay.querySelector('.keyboard-roll-wizard-card');
      if (card) card.focus();
    });
    return;
  }
  const step = wizard.steps[wizard.index];
  const modifier = keyboardRollModifierSummary(step.parent || step);
  const modifierText = modifier.items.length
    ? modifier.items.join(' · ')
    : (modifier.total !== null ? `Łączna premia ${signedNumber(modifier.total)}` : 'Brak automatycznych premii do tego pola.');
  const context = wizard.contextLines.map(line => `<p>${esc(line)}</p>`).join('');
  const bonusChoices = wizard.index === 0 && state?.combat?.pending_player_attack?.stage === 'damage_roll'
    ? physicalDamageBonusChoicesHtml(state.combat.pending_player_attack) : '';
  overlay.innerHTML = `
    <div class="keyboard-roll-wizard-backdrop"></div>
    <section class="keyboard-roll-wizard-card">
      <div class="keyboard-roll-wizard-heading">
        ${rollStepDiceIconHtml(step)}
        <div><span class="keyboard-roll-wizard-kicker">Rzut ${wizard.index + 1} z ${totalSteps}</span>
        <h2 id="keyboard-roll-wizard-title">${esc(step.label)}</h2></div>
      </div>
      <div class="keyboard-roll-wizard-context">${context}</div>
      ${bonusChoices}
      <p class="keyboard-roll-wizard-instruction">${esc(keyboardRollStepPrompt(step))}</p>
      <label class="keyboard-roll-wizard-entry">
        <span>Wynik kości${step.optional ? ' (opcjonalnie)' : ''}</span>
        <input id="keyboard-roll-wizard-input" type="number" inputmode="numeric" autocomplete="off"
          ${Number.isFinite(step.min) ? `min="${step.min}"` : ''}
          ${Number.isFinite(step.max) ? `max="${step.max}"` : ''}
          value="${step.raw === null ? '' : esc(step.raw)}"
          placeholder="${step.optional ? '✓ = pomiń' : 'wpisz wynik'}">
      </label>
      <p class="keyboard-roll-wizard-modifiers"><b>Aplikacja doliczy${manaAttempt?.busted ? ' raz do niższej kości' : step.parent ? ' raz do sumy kości' : ''}:</b> ${esc(modifierText)}</p>
      ${rollPanelControlsHtml(wizard)}
      <p id="keyboard-roll-wizard-error" class="keyboard-roll-wizard-error" aria-live="assertive">${esc(message)}</p>

      <div class="keyboard-roll-wizard-actions">${wizard.index ? '<button type="button" class="secondary" onclick="previousKeyboardRollStep()">↩ Wróć</button>' : ''}<button type="button" class="panel-accept" onclick="confirmKeyboardRollStep()">✓ ${wizard.index + 1 === totalSteps ? 'Podsumowanie' : 'Dalej'}</button></div>
    </section>`;
  const entry = document.getElementById('keyboard-roll-wizard-input');
  if (entry) {
    entry.addEventListener('input', () => {
      const error = document.getElementById('keyboard-roll-wizard-error');
      if (error) error.textContent = '';
      scheduleAutomaticBoardScan();
    });
    window.requestAnimationFrame(() => {
      entry.focus();
      entry.select();
    });
  }
}

function sendInitiativePanelCommand(command) {
  if (!keyboardRollWizard?.initiative || busy) return false;
  const entry = document.getElementById('keyboard-roll-wizard-input');
  const body = {command, revision: state.board_selection?.revision || ''};
  if (!keyboardRollWizard.review && command !== 'back') {
    const text = entry?.value.trim() || '';
    const value = Number(text);
    if (!text || !Number.isInteger(value) || value < 1 || value > 20) {
      const error = document.getElementById('keyboard-roll-wizard-error');
      if (error) error.textContent = 'Wpisz naturalny wynik k20 od 1 do 20.';
      return false;
    }
    body.value = value;
  }
  api('/api/encounter/initiative/panel', body, 'Aktualizuję wynik inicjatywy…');
  return true;
}
function initiativePanelControlsHtml() {
  const panel = state.encounter_initiative?.panel;
  if (!panel) return '';
  const buttons = panel.review ? [] : [[26, 'minus', '−', 'czerwony', '#e65d5d'], [27, 'plus', '+', 'zielony', '#62cf83']];
  return `<div class="keyboard-roll-wizard-actions">${buttons.map(([slot, command, symbol, label, color]) =>
    `<button type="button" class="secondary" style="border-color:${color};color:${color};min-width:56px" onclick="sendInitiativePanelCommand('${command}')" ${panel.enabled_slots.includes(slot)?'':'disabled'} aria-label="${command==='plus'?'Zwiększ':'Zmniejsz'} wynik">${symbol} ${label}</button>`).join('')}</div>
    <p class="keyboard-roll-wizard-help">Plansza: <b>− czerwony</b> · <b>+ zielony</b> · <b>✓ niebieski</b>${panel.enabled_slots.includes(29)?' · ↩ pomarańczowy — popraw':''}. ${panel.review?'Niebieski zatwierdza cały rzut.':'Start k20: 10. Niebieski potwierdza tę kość.'}</p>`;
}
function confirmKeyboardRollStep() {
  if (keyboardRollWizard?.initiative) return sendInitiativePanelCommand('accept');
  const wizard = keyboardRollWizard;
  const entry = document.getElementById('keyboard-roll-wizard-input');
  if (!wizard || wizard.review || !entry) return false;
  const step = wizard.steps[wizard.index];
  const valueText = entry.value.trim();
  if (!valueText && step.optional) {
    step.raw = null;
    step.total = null;
    step.input.value = '';
  } else {
    const value = Number(valueText);
    if (!valueText || !Number.isInteger(value)) {
      renderKeyboardRollWizard('Wpisz pełną liczbę i naciśnij ✓.');
      return false;
    }
    if (Number.isFinite(step.min) && value < step.min) {
      renderKeyboardRollWizard(`Najmniejszy możliwy wynik tego rzutu to ${step.min}.`);
      return false;
    }
    if (Number.isFinite(step.max) && value > step.max) {
      renderKeyboardRollWizard(`Największy możliwy wynik tego rzutu to ${step.max}.`);
      return false;
    }
    step.raw = value;
    step.total = Math.max(0, value + step.modifier);
    step.input.value = String(step.total);
  }
  if (step.parent) {
    const parent = step.parent;
    if (step.raw === null) {
      parent.parts.forEach(part => {part.raw = null; part.total = null;});
      parent.raw = parent.total = null;
      parent.input.value = '';
      wizard.index = wizard.steps.lastIndexOf(parent.parts[parent.parts.length - 1]);
    } else {
      parent.raw = parent.parts.reduce((sum, part) => sum + (part.raw || 0), 0);
      parent.total = Math.max(0, parent.raw + parent.modifier);
      parent.input.value = String(parent.total);
    }
  }
  if (wizard.index + 1 < wizard.steps.length) wizard.index += 1;
  else wizard.review = true;
  renderKeyboardRollWizard();
  scheduleAutomaticBoardScan();
  return true;
}

function previousKeyboardRollStep() {
  if (keyboardRollWizard?.initiative) return sendInitiativePanelCommand('back');
  const wizard = keyboardRollWizard;
  if (!wizard || !wizard.steps.length) return false;
  if (wizard.review) {
    wizard.review = false;
    wizard.index = Math.max(0, wizard.steps.length - 1);
  } else if (wizard.index > 0) {
    wizard.index -= 1;
  } else {
    return false;
  }
  renderKeyboardRollWizard();
  scheduleAutomaticBoardScan();
  return true;
}

function submitKeyboardRollWizard() {
  if (keyboardRollWizard?.initiative) return sendInitiativePanelCommand('accept');
  const wizard = keyboardRollWizard;
  if (!wizard || !wizard.review || busy) return false;
  const submitButton = wizard.submitButton;
  closeKeyboardRollWizard();
  submitButton.click();
  return true;
}

function cancelKeyboardRollWizard() {
  if (!keyboardRollWizard) return false;
  const precombat = keyboardRollWizard.submitButton.closest('.precombat-stealth-roll');
  if (precombat) {
    precombat.hidden = true;
    closeKeyboardRollWizard();
    return true;
  }
  if (state && state.combat && cancelCurrentCombatStep()) {
    closeKeyboardRollWizard();
    return true;
  }
  renderKeyboardRollWizard('Ten rzut jest obowiązkowy. Wpisz wynik albo wróć do wcześniejszej decyzji.');
  return false;
}

function handleKeyboardRollWizardKeydown(event) {
  if (!keyboardRollWizard) return;
  if (!keyboardRollWizard.review && ['ArrowUp','ArrowDown','+','-'].includes(event.key)) {
    event.preventDefault(); event.stopPropagation();
    changeRollPanelValue(['ArrowUp','+'].includes(event.key) ? 1 : -1);
    return;
  }
  if (event.key === 'Escape') {
    event.preventDefault();
    event.stopPropagation();
    cancelKeyboardRollWizard();
    return;
  }
  if (event.key === 'Backspace') {
    const entry = document.getElementById('keyboard-roll-wizard-input');
    if (keyboardRollWizard.review || (entry && !entry.value && keyboardRollWizard.index > 0)) {
      event.preventDefault();
      event.stopPropagation();
      previousKeyboardRollStep();
    }
    return;
  }
  if (event.key !== 'Enter') return;
  event.preventDefault();
  event.stopPropagation();
  if (keyboardRollWizard.review) submitKeyboardRollWizard();
  else confirmKeyboardRollStep();
}
function renderExplorationCardPrompt() {
  const panel = document.getElementById('exploration-card-prompt');
  if (!panel) return;
  const cardState = state.exploration_card || {};
  const pendingCard = cardState.pending;
  panel.hidden = !pendingCard;
  if (!pendingCard) {
    panel.innerHTML = '';
    return;
  }
  const actor = actorById(pendingCard.actor_id);
  panel.innerHTML = `<div class="exploration-card-prompt-head">
      ${actorPortraitHtml(actor, 'roll')}
      <div><span class="muted">Aktualna decyzja — wybierz ✓ lub ↩</span><h4>${esc(pendingCard.label || identifierLabel(pendingCard.card_action_id))}</h4></div>
    </div>
    <p>Efekt zostanie rozliczony przed powrotem do poprzedniego promptu.</p>
    <div class="numpad-combat-hint"><span><span class="board-control-symbol">✓</span> akceptuj</span><span><span class="board-control-symbol">↩</span> odrzuć / wróć</span></div>
    <div class="row">
      <button onclick="handlePhysicalCardScan('dndbg:v1:action:universal:accept')">Akceptuj</button>
      <button class="secondary" onclick="handlePhysicalCardScan('dndbg:v1:action:universal:decline')">Odrzuć</button>
    </div>`;
}
function setPlaygroundField(id, value) {
  const field = document.getElementById(id);
  if (field) field.value = String(value);
}
function renderPlaygroundPanel() {
  const panel = document.getElementById('playground-panel');
  if (!panel) return;
  const playground = state.playground;
  panel.hidden = !playground;
  if (!playground) return;
  const config = playground.config || {};
  setPlaygroundField('playground-dummy-count', config.dummy_count ?? 3);
  setPlaygroundField('playground-ac', config.armor_class ?? 12);
  setPlaygroundField('playground-hp', config.hit_points ?? 20);
  setPlaygroundField('playground-speed', config.speed_feet ?? 10);
  setPlaygroundField('playground-ability-score', config.ability_score ?? 10);
  setPlaygroundField('playground-creature-type', config.creature_type || 'construct');
  setPlaygroundField('playground-affinity', config.affinity || 'none');
  setPlaygroundField('playground-damage-type', config.damage_type || 'fire');
  setPlaygroundField('playground-condition-immunity', config.condition_immunity || '');
  const summary = document.getElementById('playground-summary');
  if (summary) {
    const modules = (playground.modules || []).map(item => esc(item.label)).join(' · ');
    summary.innerHTML = `${playground.trial_active ? '<b>Próba aktywna.</b> ' : ''}${modules}`;
  }
}
function applyPlaygroundPreset(prefix = 'playground', forcedPreset = '') {
  const presetField = document.getElementById(`${prefix}-preset`);
  if (forcedPreset && presetField) presetField.value = forcedPreset;
  const preset = forcedPreset || presetField?.value || 'standard';
  const presets = {
    standard: {count: 1, ac: 12, hp: 20, speed: 10, ability: 10, type: 'construct', affinity: 'none', damage: 'fire', condition: ''},
    armored: {count: 1, ac: 20, hp: 40, speed: 10, ability: 10, type: 'construct', affinity: 'none', damage: 'fire', condition: ''},
    resistant: {count: 1, ac: 12, hp: 40, speed: 10, ability: 10, type: 'construct', affinity: 'resistance', damage: 'fire', condition: ''},
    immune: {count: 1, ac: 12, hp: 40, speed: 10, ability: 10, type: 'construct', affinity: 'immunity', damage: 'fire', condition: ''},
    vulnerable: {count: 1, ac: 12, hp: 40, speed: 10, ability: 10, type: 'construct', affinity: 'vulnerability', damage: 'radiant', condition: ''},
    condition: {count: 1, ac: 12, hp: 40, speed: 10, ability: 10, type: 'construct', affinity: 'none', damage: 'fire', condition: 'poisoned'},
    undead: {count: 1, ac: 13, hp: 35, speed: 10, ability: 12, type: 'undead', affinity: 'vulnerability', damage: 'radiant', condition: 'poisoned'},
    swarm: {count: 6, ac: 12, hp: 20, speed: 0, ability: 10, type: 'construct', affinity: 'none', damage: 'fire', condition: ''}
  };
  const selected = presets[preset] || presets.standard;
  setPlaygroundField(`${prefix}-dummy-count`, selected.count);
  setPlaygroundField(`${prefix}-ac`, selected.ac);
  setPlaygroundField(`${prefix}-hp`, selected.hp);
  setPlaygroundField(`${prefix}-speed`, selected.speed);
  setPlaygroundField(`${prefix}-ability-score`, selected.ability);
  setPlaygroundField(`${prefix}-creature-type`, selected.type);
  setPlaygroundField(`${prefix}-affinity`, selected.affinity);
  setPlaygroundField(`${prefix}-damage-type`, selected.damage);
  setPlaygroundField(`${prefix}-condition-immunity`, selected.condition);
}
function configurePlaygroundTrial(prefix = 'playground') {
  api('/api/playground/configure', {
    dummy_count: Number(document.getElementById(`${prefix}-dummy-count`).value),
    armor_class: Number(document.getElementById(`${prefix}-ac`).value),
    hit_points: Number(document.getElementById(`${prefix}-hp`).value),
    speed_feet: Number(document.getElementById(`${prefix}-speed`).value),
    ability_score: Number(document.getElementById(`${prefix}-ability-score`).value),
    creature_type: document.getElementById(`${prefix}-creature-type`).value,
    affinity: document.getElementById(`${prefix}-affinity`).value,
    damage_type: document.getElementById(`${prefix}-damage-type`).value,
    condition_immunity: document.getElementById(`${prefix}-condition-immunity`).value
  }, 'Konfiguruję manekiny i przygotowuję arenę...');
}
function startPlaygroundPreset(prefix, preset) {
  applyPlaygroundPreset(prefix, preset);
  configurePlaygroundTrial(prefix);
}
function resetPlaygroundTrial() {
  api('/api/playground/reset', {}, 'Przywracam stan początkowy próby...');
}
function scrollChatToBottom(shouldFollow = true) {
  const chatStream = document.getElementById('chat-conversation-scroll');
  const indicator = document.getElementById('chat-new-message');
  if (!chatStream) return;
  if (!shouldFollow) {
    if (indicator) indicator.hidden = false;
    return;
  }
  if (indicator) indicator.hidden = true;
  const applyScroll = () => { chatStream.scrollTop = chatStream.scrollHeight; };
  window.requestAnimationFrame(() => window.requestAnimationFrame(applyScroll));
  chatStream.querySelectorAll('img:not([data-chat-scroll-bound])').forEach(image => {
    image.dataset.chatScrollBound = 'true';
    if (!image.complete) image.addEventListener('load', applyScroll, {once: true});
  });
}
function currentModeLabel() {
  if (state.combat) return 'Walka';
  if (state.pending_encounter) return 'Początek encountera';
  const stage = state.flow ? state.flow.stage : '';
  if (stage === 'spell_preparation') return 'Przygotowanie czarów';
  if (stage === 'short_rest') return 'Krótki odpoczynek';
  if (stage === 'party_setup') return 'Przygotowanie planszy';
  if (stage === 'location_preview') return 'Wybór lokacji';
  if (stage === 'game_over') return 'Game Over';
  if (stage === 'scenario_complete') return 'Koniec scenariusza';
  if (state.trade) return 'Handel';
  if (state.active_point && state.active_point.npc) return 'Rozmowa';
  return 'Eksploracja';
}
function sceneStatusSummaryHtml() {
  const entries = state.scene_status || [];
  if (!entries.length) return '<span class="muted">Brak zmian w scenie.</span>';
  return entries.slice(0, 6).map(entry => `
    <div class="panel-data-row">
      <span>${esc(entry.label)}</span>
      <strong>${esc(entry.value)}</strong>
    </div>
  `).join('') + (entries.length > 6 ? `<span class="muted">+${entries.length - 6} kolejnych wpisów</span>` : '');
}
function renderPartyShell() {
  const actors = state.actors || [];
  const summary = document.getElementById('party-summary');
  const details = document.getElementById('party-details');
  if (!summary || !details) return;
  if (!actors.length) {
    summary.innerHTML = '<span class="muted">Brak drużyny</span>';
    details.innerHTML = '<span class="muted">Brak danych postaci.</span>';
    renderPanelActorSelector();
    return;
  }
  if (!actors.some(actor => String(actor.id) === selectedPanelActorId)) selectedPanelActorId = String(actors[0].id);
  summary.innerHTML = actors.map(actor => partySummaryActorHtml(currentActorState(actor))).join('');
  const actor = selectedPanelActor();
  details.innerHTML = actor ? partyDetailActorHtml(actor) : '<span class="muted">Brak danych postaci.</span>';
  document.getElementById('actor-states').innerHTML = actor ? actorStatesHtml(actor) : '<span class="muted">Brak danych postaci.</span>';
  document.getElementById('actor-spells').innerHTML = actor ? actorSpellsHtml(actor) : '<span class="muted">Brak danych postaci.</span>';
  document.getElementById('actor-inventory').innerHTML = actor ? actorInventoryPanelHtml(actor) : '<span class="muted">Brak danych postaci.</span>';
  renderPanelActorSelector();
}
function selectedPanelActor() {
  if (!state) return null;
  const base = (state.actors || []).find(actor => String(actor.id) === selectedPanelActorId) || (state.actors || [])[0] || null;
  return currentActorState(base);
}
function currentActorState(base) {
  if (!base || !state) return base || null;
  const combatActor = state.combat && (state.combat.actors || []).find(actor => String(actor.id) === String(base.id));
  return combatActor ? {...base, ...combatActor} : base;
}
function portraitActors() {
  const actors = [...((state && state.actors) || []), ...((state && state.combat && state.combat.actors) || [])];
  return [...new Map(actors.map(actor => [String(actor.id), actor])).values()];
}
function actorById(actorId) {
  return portraitActors().find(actor => String(actor.id) === String(actorId)) || null;
}
function actorPortraitHtml(actor, variant = '') {
  if (!actor || !actor.portrait_url) return '';
  const modifier = variant ? ` actor-portrait-${variant}` : '';
  return `<img class="actor-portrait${modifier}" src="${esc(actor.portrait_url)}" alt="Portret: ${esc(actor.name || 'postać')}" loading="lazy">`;
}
function actorIdentityColor(actor) {
  const rgb = actor && actor.party_color_rgb;
  return Array.isArray(rgb) && rgb.length === 3
    ? `rgb(${Number(rgb[0])}, ${Number(rgb[1])}, ${Number(rgb[2])})`
    : '#d6a72e';
}
function actorIdentityStyle(actor) {
  return `--actor-identity:${actorIdentityColor(actor)}`;
}
function partyPortraitStackHtml(actors) {
  const portraits = actors.filter(actor => actor.portrait_url);
  if (!portraits.length) return '';
  return `<span class="party-portrait-stack" aria-hidden="true">${portraits.map(actor => actorPortraitHtml(actor, 'party')).join('')}</span>`;
}
function actorForMessage(message) {
  const title = String((message && message.title) || '');
  const body = String((message && message.body) || '');
  const matches = portraitActors().filter(actor => actor.portrait_url && actor.name).map(actor => {
    const titleIndex = title.indexOf(actor.name);
    const bodyIndex = body.indexOf(actor.name);
    return {
      actor,
      index: titleIndex >= 0 ? titleIndex : bodyIndex >= 0 ? title.length + 1 + bodyIndex : Number.MAX_SAFE_INTEGER,
    };
  }).filter(match => match.index !== Number.MAX_SAFE_INTEGER);
  matches.sort((left, right) => left.index - right.index);
  return matches.length ? matches[0].actor : null;
}
function messageCardHtml(message, extraClass = '') {
  const actor = actorForMessage(message);
  const nessa = state.active_point?.npc?.briefing_contract;
  const npcSpeech = nessa && ['Nessa', 'Odpowiedź NPC'].includes(message.title);
  const title = npcSpeech ? 'Nessa' : message.title;
  const tone = nessa ? (npcSpeech ? ' npc-speech' : message.title === 'Narracja MG' ? ' npc-gesture' : /Wynik interakcji|Rezultat mechaniczny/.test(message.title || '') ? ' npc-outcome' : '') : '';
  return `<div class="${extraClass || 'message'}${actor ? ' with-portrait' : ''}${tone}">
    ${actorPortraitHtml(actor, 'message')}
    <div class="message-copy"><b>${esc(title || '')}</b><span>${esc(message.body || '')}</span></div>
  </div>`;
}
function selectPanelActor(actorId) {
  selectedPanelActorId = String(actorId || '');
  localStorage.setItem('explorationPanelActorId', selectedPanelActorId);
  renderPartyShell();
}
function renderPanelActorSelector() {
  const selector = document.getElementById('panel-actor-selector');
  if (!selector) return;
  const actorTabs = new Set(['party', 'states', 'spells', 'inventory']);
  selector.hidden = !actorTabs.has(sidePanelTab);
  if (selector.hidden || !state) return;
  const actors = state.actors || [];
  selector.innerHTML = `<span>Wybierz bohatera</span><div role="listbox" aria-label="Bohater">${actors.map(actor => `<button class="${String(actor.id) === selectedPanelActorId ? 'active' : ''}" data-allow-busy="true" onclick="selectPanelActor('${esc(actor.id)}')" aria-selected="${String(actor.id) === selectedPanelActorId ? 'true' : 'false'}">${actorPortraitHtml(actor, 'tab')}<span>${esc(actor.name)}</span></button>`).join('')}</div>`;
}
function actorHealthTone(actor) {
  const maximum = Math.max(1, Number(actor.max_hp || 1));
  const ratio = Number(actor.hp || 0) / maximum;
  if (ratio <= 0.25) return 'critical';
  if (ratio <= 0.55) return 'wounded';
  return 'healthy';
}
function actorConditionLabels(actor) {
  return (actor.conditions || []).map(condition => condition.label || condition.condition || condition.id).filter(Boolean);
}
function partySummaryActorHtml(actor) {
  const hp = Number(actor.hp || 0);
  const maximum = Number(actor.max_hp || 0);
  const temporary = Number(actor.temp_hp || 0);
  const percentage = maximum > 0 ? Math.max(0, Math.min(100, Math.round((hp / maximum) * 100))) : 0;
  const conditions = actorConditionLabels(actor);
  const hpText = `${hp}/${maximum} PW${temporary > 0 ? ` +${temporary}` : ''}`;
  return `
    <button class="party-summary-actor ${actorHealthTone(actor)}" style="${actorIdentityStyle(actor)}" data-allow-busy="true" onclick="openActorPanel('${esc(actor.id)}', 'party')" title="${esc(actor.name)}: ${esc(hpText)} · kolor drużyny: ${esc(actor.party_color || '')}${conditions.length ? ` · ${esc(conditions.join(', '))}` : ''}">
      ${actorPortraitHtml(actor, 'summary')}
      <span class="party-summary-content">
        <span class="party-summary-main">
          <span class="party-summary-name">${esc(actor.name)}</span>
          <span class="party-summary-hp-value">${esc(hpText)}</span>
        </span>
        <span class="party-summary-hp" role="meter" aria-label="${esc(actor.name)}: ${hp} z ${maximum} punktów życia" aria-valuemin="0" aria-valuemax="${maximum}" aria-valuenow="${hp}"><i style="width:${percentage}%"></i></span>
      </span>
      ${conditions.length ? `<span class="party-summary-condition" aria-label="Aktywne stany">${conditions.length}</span>` : ''}
    </button>
  `;
}
function partyDetailActorHtml(actor) {
  const hp = Number(actor.hp || 0);
  const maximum = Number(actor.max_hp || 0);
  const percentage = maximum > 0 ? Math.max(0, Math.min(100, Math.round((hp / maximum) * 100))) : 0;
  const abilities = actor.ability_scores || {};
  const resources = actor.resource_pools || [];
  const hitDice = actor.hit_dice || [];
  const features = actor.features || [];
  return `
    <article class="party-detail-card ${actorHealthTone(actor)}">
      <div class="party-detail-heading">${actorPortraitHtml(actor, 'detail')}<strong>${esc(actor.name)}</strong><span>${hp}/${maximum} PW</span></div>
      <div class="party-detail-hp" aria-label="${percentage}% punktów życia"><i style="width:${percentage}%"></i></div>
      <div class="character-vitals"><span><b>KP</b>${esc(actor.ac ?? '-')}</span><span><b>Szybkość</b>${esc(actor.speed_feet ?? '-')} ft</span><span><b>Temp HP</b>${esc(actor.temp_hp || 0)}</span><span><b>${actor.uses_charge ? 'Naładowanie' : 'Biegłość'}</b>${signedNumber(actor.uses_charge ? actor.charge_roll_bonus || 0 : actor.proficiency_bonus || 0)}</span></div>
      <div class="ability-grid">${['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma'].map(ability => {
        const score = abilities[ability] ?? 10;
        return `<span><b>${esc(abilityAbbreviation(ability))}</b>${esc(score)} <small>${esc(signedNumber(Math.floor((Number(score) - 10) / 2)))}</small></span>`;
      }).join('')}</div>
      ${hitDice.length ? `<p class="party-detail-resources"><b>Kości Wytrzymałości:</b> ${hitDice.map(pool => `${esc(pool.remaining)}/${esc(pool.maximum)} k${esc(pool.die_sides)}`).join(' · ')}</p>` : ''}
      ${resources.length ? `<div class="panel-card-list compact">${resources.map(pool => `<div class="panel-info-card"><b>${esc(pool.label)}</b><span>${esc(pool.current)}/${esc(pool.maximum)} · ${esc(recoveryLabel(pool.recovery))}</span></div>`).join('')}</div>` : ''}
      ${features.length ? `<div class="character-features"><span class="panel-section-label">Cechy</span>${features.map(feature => `<div class="panel-info-card"><b>${esc(feature.label)}</b><span>${esc(feature.description || '')}</span><small><b>Mechanika:</b> ${esc(feature.mechanics || 'Działa pasywnie lub kontekstowo.')}</small></div>`).join('')}</div>` : ''}
    </article>
  `;
}
function abilityAbbreviation(ability) {
  return ({strength:'SIŁ', dexterity:'ZRĘ', constitution:'KON', intelligence:'INT', wisdom:'MĄD', charisma:'CHA'})[ability] || String(ability).slice(0, 3).toUpperCase();
}
function recoveryLabel(recovery) {
  return ({short_rest:'krótki odpoczynek', long_rest:'długi odpoczynek', scenario_end:'koniec scenariusza'})[recovery] || recovery || 'bez odnowienia';
}
function openActorPanel(actorId, tab = 'party') {
  if (actorId) selectPanelActor(actorId);
  setSidePanelTab(tab);
  setSidePanelOpen(true);
}
function openPartyPanel() { openActorPanel(selectedPanelActorId, 'party'); }
function actorStatesHtml(actor) {
  const conditions = actor.conditions || [];
  const effects = actor.effects || [];
  const concentration = actor.concentration || null;
  const lifeChips = combatActorChips(actor).filter(chip => !isTurnResourceChip(chip));
  const cards = [];
  conditions.forEach(condition => cards.push({
    tone: 'danger',
    label: condition.label || condition.condition || condition.id || 'Stan',
    body: condition.description || condition.instruction || condition.source_label || 'Aktywny stan mechaniczny.',
    meta: condition.expires || condition.save_label || '',
  }));
  effects.forEach(effect => cards.push({
    tone: effectChipTone(effect.kind),
    label: effect.label || effect.kind || 'Efekt',
    body: effect.value_label || (effect.value === undefined ? 'Aktywny efekt.' : signedNumber(effect.value)),
    meta: effect.expires || '',
  }));
  if (concentration) cards.push({tone: 'magic', label: `Koncentracja: ${concentration.label || '-'}`, body: concentration.value_label || 'Efekt wymaga koncentracji.', meta: concentration.expires || ''});
  lifeChips.forEach(chip => {
    if (cards.some(card => card.label === chip.label)) return;
    cards.push({tone: chip.tone || 'neutral', label: chip.label, body: chip.title || 'Aktywny stan postaci.', meta: ''});
  });
  const globalEffects = state.active_effects || [];
  return `
    <div class="actor-panel-summary"><b>${esc(actor.name)}</b><span>${cards.length ? `${cards.length} aktywnych stanów i efektów` : 'Brak aktywnych stanów'}</span></div>
    ${cards.length ? cards.map(card => `<article class="panel-info-card state ${esc(card.tone)}"><b>${esc(card.label)}</b><span>${esc(card.body)}</span>${card.meta ? `<small>${esc(card.meta)}</small>` : ''}</article>`).join('') : '<div class="panel-empty-state"><b>Wszystko w porządku</b><span>Postać nie ma aktywnych stanów ani efektów.</span></div>'}
    ${globalEffects.length ? `<div class="panel-subsection"><span class="panel-section-label">Efekty scenariusza</span>${globalEffects.map(effect => `<article class="panel-info-card"><b>${esc(effect.label || 'Efekt')}</b><span>${esc(effect.value_label || '')}</span><small>${esc(effect.expires || '')}</small>${effect.rope_trick ? `<div class="panel-actions"><button class="secondary" onclick="enterRopeTrick('${esc(effect.id)}')">Wejdź</button><button class="secondary" onclick="exitRopeTrick('${esc(effect.id)}')">Wyjdź</button></div>` : ''}</article>`).join('')}</div>` : ''}
  `;
}
function isTurnResourceChip(chip) {
  const prefixes = ['Akcja ', 'Ataki ', 'Bonus ', 'Darmowa interakcja ', 'Reakcja ', 'Ruch '];
  return prefixes.some(prefix => String((chip || {}).label || '').startsWith(prefix));
}
function actorSpellSourceMap() {
  const sources = [];
  if (state && state.combat) {
    sources.push(...(state.combat.available_attack_sources || []), ...(state.combat.available_healing_sources || []), ...(state.combat.combat_actions || []));
  }
  const result = new Map();
  sources.forEach(source => {
    const id = String(source.id || source.source_id || '');
    if (id) result.set(id, source);
  });
  return result;
}
function actorSpellsHtml(actor) {
  const preparationActor = (((state.spell_preparation || {}).actors) || []).find(candidate => String(candidate.actor_id) === String(actor.id));
  const preparationById = new Map(((preparationActor || {}).spells || []).map(spell => [String(spell.id), spell]));
  const sourceById = actorSpellSourceMap();
  const definitionById = new Map((actor.spells || []).map(spell => [String(spell.id), spell]));
  const spellIds = actor.spell_ids || [];
  const slots = (actor.spell_slots || []).filter(slot => Number(slot.maximum || 0) > 0);
  const spellCards = spellIds.map(spellId => {
    const prepared = preparationById.get(String(spellId));
    const source = sourceById.get(String(spellId)) || {};
    const definition = definitionById.get(String(spellId)) || {};
    const level = prepared ? Number(prepared.level || 0) : Number(definition.level ?? source.spell_level ?? 0);
    const label = prepared?.label || definition.name || source.name || source.label || identifierLabel(spellId);
    const isPrepared = prepared ? Boolean(prepared.prepared || prepared.always_prepared) : Boolean(definition.castable || level === 0);
    const status = level === 0 ? 'Sztuczka · zawsze dostępna' : isPrepared ? `Poziom ${level} · dostępny` : `Poziom ${level} · nieprzygotowany`;
    const ritualButton = definition.ritual && !state.combat
      ? `<button class="secondary" ${definition.ritual_castable ? '' : 'disabled'} onclick="castExplorationRitual('${esc(actor.id)}', '${esc(spellId)}')">Rzuć jako rytuał · ${esc(definition.ritual_casting_minutes || 10)} min</button>`
      : '';
    const explorationButton = definition.exploration_castable && !state.combat
      ? `<button class="secondary" ${definition.castable ? '' : 'disabled'} onclick="castExplorationSpell('${esc(actor.id)}', '${esc(spellId)}', ${Number((definition.available_cast_levels || [definition.level])[0] || 0)})">Rzuć w eksploracji</button>`
      : '';
    return `<article class="panel-info-card spell${isPrepared ? ' prepared' : ' unavailable'}"><div><b>${esc(label)}</b><span>${esc(status)}</span></div>${definition.concentration || source.concentration ? '<small>Koncentracja</small>' : ''}${definition.ritual ? '<small>Rytuał</small>' : ''}${ritualButton}${explorationButton}</article>`;
  }).join('');
  return `
    <div class="actor-panel-summary"><b>${esc(actor.name)}</b><span>${spellIds.length ? `${spellIds.length} znanych czarów` : 'Nie zna czarów'}</span></div>
    ${slots.length ? `<div class="spell-slot-list">${slots.map(slot => `<span><b>${esc(slot.level)}. poziom</b><i>${Array.from({length:Number(slot.maximum || 0)}, (_, index) => `<em class="${index < Number(slot.remaining || 0) ? 'available' : 'spent'}"></em>`).join('')}</i><small>${esc(slot.remaining)}/${esc(slot.maximum)}</small></span>`).join('')}</div>` : ''}
    ${spellCards || '<div class="panel-empty-state"><b>Brak czarów</b><span>Ta postać nie ma obecnie listy czarów.</span></div>'}
  `;
}
function identifierLabel(identifier) {
  const text = String(identifier || '').replaceAll('_', ' ').trim();
  return text ? text.charAt(0).toLocaleUpperCase('pl') + text.slice(1) : '-';
}
function actorSensesText(actor) {
  const senses = actor.senses || {};
  const labels = [
    ['Widzenie w ciemności', senses.darkvision_feet],
    ['Ślepowidzenie', senses.blindsight_feet],
    ['Wyczucie drgań', senses.tremorsense_feet],
    ['Prawdziwe widzenie', senses.truesight_feet],
  ].filter(([, distance]) => Number(distance || 0) > 0)
    .map(([label, distance]) => `${label} ${distance} ft`);
  return labels.join(', ') || 'zwykły wzrok';
}
function actorInventoryPanelHtml(actor) {
  const items = actor.inventory || [];
  const hands = actor.hands || {};
  const currency = actor.currency || {};
  const carrying = actor.carrying || {};
  const activeLight = actor.active_light || null;
  const awareness = ((state.flow || {}).awareness) || {};
  const hiddenState = (awareness.hidden_actor_states || []).find(item => String(item.actor_id) === String(actor.id));
  const canUseAwareness = !state.combat && (state.flow || {}).stage === 'location_active';
  const awarenessButtons = !canUseAwareness ? '' : `
    <div class="panel-actions">
      ${awareness.search_available ? `<button type="button" class="secondary" onclick="startExplorationSearch('${esc(actor.id)}')">Przeszukaj · ${esc(awareness.search_minutes)} min</button>` : ''}
      ${awareness.allows_hiding && !activeLight ? `<button type="button" class="secondary" onclick="startExplorationHide('${esc(actor.id)}')">${hiddenState ? `Ukryty · ${esc(hiddenState.stealth_total)}` : 'Ukryj się'}</button>` : ''}
    </div>`;
  const fixtureCards = !canUseAwareness ? '' : ((state.flow || {}).fixtures || []).map(fixture => {
    const hp = fixture.maximum_hit_points !== null && fixture.maximum_hit_points !== undefined
      ? ` · HP ${esc(fixture.current_hit_points)}/${esc(fixture.maximum_hit_points)} · KP ${esc(fixture.armor_class)}`
      : '';
    const stateLabel = fixture.destroyed
      ? 'zniszczony'
      : fixture.locked
        ? 'zamknięty na zamek'
        : fixture.opened
          ? 'otwarty'
          : identifierLabel(fixture.condition);
    const actions = (fixture.actions || []).map(action => action.operation === 'damage'
      ? `<button type="button" class="secondary" onclick="damageExplorationFixture('${esc(actor.id)}','${esc(fixture.id)}')">${esc(action.label)}</button>`
      : `<button type="button" class="secondary" onclick="startExplorationFixtureAction('${esc(actor.id)}','${esc(fixture.id)}','${esc(action.operation)}')">${esc(action.label)}${action.requires_roll ? ' · rzut' : ''}</button>`
    ).join('');
    return `<article class="panel-info-card fixture${fixture.destroyed ? ' unavailable' : ''}"><div><b>${esc(fixture.name)}</b><span>${esc(stateLabel)}${hp}</span></div><p class="muted">${esc(fixture.description || identifierLabel(fixture.kind))}</p>${actions ? `<div class="panel-actions">${actions}</div>` : ''}</article>`;
  }).join('');
  const handLabel = hand => hand && hand.item_name ? hand.item_name : 'wolna';
  const coinText = ['pp', 'gp', 'ep', 'sp', 'cp'].filter(key => Number(currency[key] || 0) > 0).map(key => `${esc(currency[key])} ${key}`).join(', ') || 'brak monet';
  const carryingText = `${Number(carrying.weight_lb || 0).toFixed(1)} / ${Number(carrying.capacity_lb || 0).toFixed(1)} lb`;
  return `
    <div class="actor-panel-summary"><b>${esc(actor.name)}</b><span>${items.length} ${items.length === 1 ? 'przedmiot' : 'przedmiotów'} · ${esc(carryingText)}</span></div>
    <p class="muted"><b>Monety:</b> ${coinText}. <b>Udźwig:</b> ${esc(carryingText)}${carrying.over_capacity ? ' — przeciążenie' : ''}. <b>Zmysły:</b> ${esc(actorSensesText(actor))}.${activeLight ? ` <b>Światło:</b> ${esc(activeLight.source_name)} ${esc(activeLight.bright_distance_feet)}/${esc(activeLight.dim_additional_feet)} ft, ${esc(activeLight.remaining_minutes)} min.` : ''}</p>
    ${awarenessButtons}
    ${fixtureCards}
    <div class="hands-summary"><span><b>Główna ręka</b>${esc(handLabel(hands.main_hand))}</span><span><b>Druga ręka</b>${esc(handLabel(hands.off_hand))}</span></div>
    ${items.length ? items.map(item => {
      const held = (item.held_in || []).map(hand => hand === 'main_hand' ? 'główna ręka' : hand === 'off_hand' ? 'druga ręka' : hand).join(', ');
      const armorCategory = ({light: 'lekki', medium: 'średni', heavy: 'ciężki'})[item.armor_category] || '';
      const armorFormula = item.armor_category
        ? `KP ${item.armor_base_ac}${item.armor_dexterity_cap === 0 ? '' : item.armor_dexterity_cap === null || item.armor_dexterity_cap === undefined ? ' + Zr' : ` + Zr (maks. +${item.armor_dexterity_cap})`}`
        : '';
      const chargeLabel = item.charges_maximum !== null && item.charges_maximum !== undefined
        ? `ładunki ${item.charges_current}/${item.charges_maximum}`
        : '';
      const attunementLabel = item.requires_attunement
        ? (item.attuned ? 'dostrojony' : 'wymaga dostrojenia')
        : '';
      const effectLabels = (item.magic_effects || []).map(effect => {
        const label = ({
          armor_class_bonus: 'KP',
          saving_throw_bonus: 'rzuty obronne',
          ability_check_bonus: 'testy cech',
          attack_roll_bonus: 'ataki',
          speed_bonus_feet: 'szybkość'
        })[effect.kind] || identifierLabel(effect.kind);
        const value = Number(effect.value || 0);
        return `${value >= 0 ? '+' : ''}${value} ${label}${effect.kind === 'speed_bonus_feet' ? ' ft' : ''}`;
      });
      const magicInactive = effectLabels.length && (item.available === false || (item.requires_attunement && !item.attuned) || (item.magic_effects || []).every(effect => effect.requires_equipped && !item.equipped))
        ? 'efekty nieaktywne'
        : '';
      const weaponCategory = ({simple: 'broń prosta', martial: 'broń żołnierska'})[item.weapon_category] || '';
      const weaponProperties = (item.weapon_properties || []).map(identifierLabel);
      const gearCategory = item.gear_category ? identifierLabel(item.gear_category) : '';
      const focusKind = item.spellcasting_focus_kind ? `focus: ${identifierLabel(item.spellcasting_focus_kind)}` : '';
      const capacity = item.container_capacity || null;
      const capacityLabel = capacity
        ? [
            capacity.maximum_weight_lb ? `${capacity.maximum_weight_lb} lb` : '',
            capacity.liquid_pints ? `${capacity.liquid_pints} pint` : '',
            capacity.ammunition_count ? `${capacity.ammunition_count} szt. ${identifierLabel(capacity.ammunition_type)}` : '',
            capacity.sheet_count ? `${capacity.sheet_count} arkuszy` : ''
          ].filter(Boolean).join(' / ')
        : '';
      const light = item.light_source || null;
      const lightLabel = light
        ? `światło ${light.bright_distance_feet}/${light.dim_additional_feet} ft · ${light.duration_minutes} min${light.fuel_item_id ? ` · paliwo: ${identifierLabel(light.fuel_item_id)}` : ''}`
        : '';
      const bundleLabel = (item.bundle_contents || []).length
        ? `pakiet: ${(item.bundle_contents || []).reduce((sum, entry) => sum + Number(entry.quantity || 1), 0)} elementów`
        : '';
      const tags = [item.equipped ? 'wyposażony' : '', held, weaponCategory, ...weaponProperties, gearCategory, focusKind, capacityLabel ? `pojemność ${capacityLabel}` : '', lightLabel, item.tool_proficiency_id ? `narzędzie: ${identifierLabel(item.tool_proficiency_id)}` : '', bundleLabel, armorCategory ? `pancerz ${armorCategory}` : '', armorFormula, item.armor_strength_requirement ? `Siła ${item.armor_strength_requirement}` : '', item.stealth_disadvantage ? 'utrudnienie Stealth' : '', chargeLabel, attunementLabel, ...effectLabels, magicInactive, item.broken ? 'uszkodzony' : '', item.available === false ? 'niedostępny' : '', `${Number(item.total_weight_lb || 0).toFixed(1)} lb`, Number(item.total_value_cp || 0) > 0 ? `${esc(item.total_value_cp)} cp` : ''].filter(Boolean);
      const canChangeArmor = item.kind === 'armor' && item.armor_category && item.available !== false && !item.broken && !state.combat && (state.flow || {}).stage === 'location_active';
      const armorButton = canChangeArmor
        ? `<button type="button" class="secondary" onclick="changeActorArmor('${esc(actor.id)}','${esc(item.id)}',${item.equipped ? 'false' : 'true'})">${item.equipped ? 'Zdejmij pancerz' : 'Załóż pancerz'}</button>`
        : '';
      const litHere = activeLight && activeLight.source_item_id === item.id;
      const canChangeLight = item.light_source && item.available !== false && !item.broken && !state.combat && (state.flow || {}).stage === 'location_active';
      const lightButtons = !canChangeLight ? '' : litHere
        ? `<button type="button" class="secondary" onclick="changeActorLight('${esc(actor.id)}','${esc(item.id)}','extinguish')">Zgaś</button>${item.light_source.hooded_dim_distance_feet !== null && item.light_source.hooded_dim_distance_feet !== undefined ? `<button type="button" class="secondary" onclick="changeActorLight('${esc(actor.id)}','${esc(item.id)}','toggle_hood')">Przełącz osłonę</button>` : ''}`
        : `<button type="button" class="secondary" onclick="changeActorLight('${esc(actor.id)}','${esc(item.id)}','ignite')">Zapal</button>`;
      return `<article class="panel-info-card inventory${item.broken || item.available === false ? ' unavailable' : ''}"><div><b>${esc(item.name || identifierLabel(item.id))}${Number(item.quantity || 1) > 1 ? ` ×${esc(item.quantity)}` : ''}</b><span>${esc(item.description || identifierLabel(item.kind))}</span></div>${tags.length ? `<div class="panel-item-tags">${tags.map(tag => `<small>${esc(tag)}</small>`).join('')}</div>` : ''}${(item.properties || []).length ? `<p>${item.properties.map(property => `<span class="property-chip">${esc(identifierLabel(property))}</span>`).join('')}</p>` : ''}${armorButton}${lightButtons}</article>`;
    }).join('') : '<div class="panel-empty-state"><b>Pusty ekwipunek</b><span>Postać nie niesie żadnych przedmiotów.</span></div>'}
  `;
}
async function changeActorArmor(actorId, armorId, equip) {
  await api('/api/equipment/armor', {
    actor_id: actorId,
    armor_id: armorId,
    equip: Boolean(equip),
  }, equip ? 'Zakładanie pancerza...' : 'Zdejmowanie pancerza...');
}
async function changeActorLight(actorId, itemId, action) {
  await api('/api/equipment/light', {
    actor_id: actorId,
    item_id: itemId,
    action,
  }, action === 'ignite' ? 'Zapalanie światła...' : 'Zmiana światła...');
}
async function startExplorationSearch(actorId) {
  await api('/api/exploration/search/start', {actor_id: actorId}, 'Przygotowuję aktywne przeszukiwanie...');
}
async function startExplorationHide(actorId) {
  await api('/api/exploration/hide/start', {actor_id: actorId}, 'Przygotowuję próbę ukrycia...');
}
async function startExplorationFixtureAction(actorId, fixtureId, operation) {
  await api('/api/exploration/fixture/action', {
    actor_id: actorId,
    fixture_id: fixtureId,
    operation,
  }, 'Przygotowuję interakcję z obiektem...');
}
async function damageExplorationFixture(actorId, fixtureId) {
  const rawAttackTotal = prompt('Podaj łączny wynik ataku przeciw KP obiektu:');
  if (rawAttackTotal === null) return;
  const attackTotal = Number(rawAttackTotal);
  if (!Number.isInteger(attackTotal) || attackTotal < 0) return;
  const rawDamage = prompt('Podaj obrażenia:');
  if (rawDamage === null) return;
  const damage = Number(rawDamage);
  if (!Number.isInteger(damage) || damage < 0) return;
  await api('/api/exploration/fixture/damage', {
    actor_id: actorId,
    fixture_id: fixtureId,
    attack_total: attackTotal,
    damage,
  }, 'Rozliczam atak na obiekt...');
}
function renderSnapshotPanel() {
  const snapshot = state.snapshot || {};
  const status = document.getElementById('snapshot-status');
  const saveButton = document.getElementById('snapshot-save-button');
  const loadButton = document.getElementById('snapshot-load-button');
  if (!status || !saveButton || !loadButton) return;
  status.innerHTML = snapshot.exists
    ? `Dostępny zapis v${esc(snapshot.schema_version)}.<br><span class="muted">${esc(snapshot.path || '')}</span>`
    : `Brak zapisu dla tego scenariusza.<br><span class="muted">${esc(snapshot.path || '')}</span>`;
  if (snapshot.blocker) status.innerHTML += `<br><span class="status">${esc(snapshot.blocker)}</span>`;
  saveButton.disabled = !snapshot.can_save;
  loadButton.disabled = !snapshot.exists;
}
async function saveSnapshot() {
  await api('/api/snapshot/save', {}, 'Zapisuję stan gry...');
}
async function loadSnapshot() {
  if (!confirm('Wczytanie zastąpi aktualny stan scenariusza. Kontynuować?')) return;
  await api('/api/snapshot/load', {}, 'Wczytuję stan gry...');
}
function renderBoardPanel() {
  const board = state.board || {};
  document.getElementById('board-status').textContent = `${board.message || 'Plansza niepodłączona.'} Domyślny backend z configu: ${board.configured_backend || '-'}.`;
  document.getElementById('board-backend').value = board.backend || 'none';
  document.getElementById('board-url').value = board.board_url || 'http://127.0.0.1:5000';
  document.getElementById('board-serial-port').value = board.board_serial_port || '';
  document.getElementById('wled-url').value = board.wled_url || '';
  document.getElementById('scan-timeout').value = board.scan_timeout_s || 300;
}
function renderBoardConnectionIndicator() {
  const indicator = document.getElementById('board-connection-indicator');
  if (!indicator) return;
  const board = state.board || {};
  const backend = board.backend || 'none';
  const connected = Boolean(board.connected);
  indicator.classList.toggle('connected', connected);
  indicator.classList.toggle('simulator', connected && backend === 'simulator');
  const label = connected ? (backend === 'simulator' ? 'Symulator' : 'Plansza połączona')
    : boardConnectionInFlight ? 'Łączę z planszą…' : 'Plansza rozłączona';
  indicator.querySelector('span:last-child').textContent = label;
  indicator.title = board.message || label;
}
function renderBoardFallback() {
  const board = state.board || {};
  const connected = Boolean(board.connected);
  if (connected) boardConnectionNotice = '';
  if (connected && boardFallbackEnabled) {
    boardFallbackEnabled = false;
    localStorage.removeItem('explorationBoardFallback');
  }
  const banner = document.getElementById('board-disconnected-banner');
  const panel = document.getElementById('board-fallback-panel');
  const toggle = document.getElementById('board-fallback-toggle');
  const copy = document.getElementById('board-disconnected-copy');
  if (banner) banner.hidden = connected || boardConnectionInFlight;
  if (panel) panel.hidden = connected || !boardFallbackEnabled;
  if (toggle) toggle.textContent = boardFallbackEnabled ? 'Sterowanie awaryjne aktywne' : 'Tryb awaryjny';
  if (copy) copy.textContent = boardConnectionNotice || (boardFallbackEnabled ? 'Sterowanie awaryjne jest aktywne. Właściwe połączenie można ponowić w dowolnym momencie.' : 'Możecie ponowić połączenie albo jawnie przejść na sterowanie awaryjne.');
  document.body.classList.toggle('board-fallback-active', !connected && boardFallbackEnabled);
  document.body.classList.toggle('board-disconnected', !connected);
}
async function retryBoardConnection() {
  if (boardConnectionInFlight) return;
  boardConnectionInFlight = true;
  const board = state.board || {};
  const backend = board.backend && board.backend !== 'none' ? board.backend : (board.configured_backend || 'hardware');
  setBusy('Łączę z planszą…');
  renderBoardConnectionIndicator();
  renderBoardFallback();
  try {
    await stopBoardScanLoop();
    const response = await fetch('/api/board/configure', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({backend, board_url: board.board_url || '', board_serial_port: board.board_serial_port || '', wled_url: board.wled_url || '', scan_timeout_s: Number(board.scan_timeout_s || 300)}),
    });
    const data = await response.json();
    state = data.state || data;
    boardConnectionNotice = response.ok ? '' : 'Nie udało się połączyć. Możecie spróbować ponownie albo kontynuować w trybie awaryjnym.';
  } catch (_error) {
    boardConnectionNotice = 'Nie udało się połączyć. Możecie spróbować ponownie albo kontynuować w trybie awaryjnym.';
  } finally {
    boardConnectionInFlight = false;
    setBusy('');
    render();
    scheduleAutomaticBoardScan();
  }
}
function toggleBoardFallback(force) {
  boardFallbackEnabled = typeof force === 'boolean' ? force : !boardFallbackEnabled;
  localStorage.setItem('explorationBoardFallback', boardFallbackEnabled ? 'true' : 'false');
  renderBoardFallback();
  if (boardFallbackEnabled) {
    setSidePanelTab('game');
    setSidePanelOpen(true);
    window.requestAnimationFrame(() => document.getElementById('fallback-board-col')?.focus());
  }
}
function manualBoardSelect() {
  const col = Number(document.getElementById('fallback-board-col')?.value);
  const row = Number(document.getElementById('fallback-board-row')?.value);
  api('/api/board/select', {col, row}, `Wskazuję pole (${col}, ${row}) w trybie awaryjnym...`);
}
function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
}
function activeEffectsHtml() {
  const effects = state.active_effects || [];
  return effects.map(effect => {
    const source = effect.source || {};
    const sourceLabel = source.label || source.id || 'nieznane';
    return `<div class="effect-chip"><b>${esc(effect.label)}</b><br>${esc(effect.value_label)}<br><span class="muted">Źródło: ${esc(sourceLabel)} · ${esc(effect.expires)}</span></div>`;
  }).join('') || '<span class="muted">Brak</span>';
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
  if (type === 'ui_short_rest_completed') return `Short rest: ${esc(payload.zone_id || '')}; czas: ${esc(payload.elapsed_minutes || 0)} min`;
  if (type === 'ui_short_rest_hit_die_spent') return `Hit Die: ${esc(payload.actor_id || '')}; leczenie: ${esc(payload.effective_healing || 0)} HP`;
  if (type === 'ui_effects_expired') return `Wygasłe efekty (${esc(payload.event || '')}): ${esc((payload.effect_ids || []).join(', ') || 'brak')}`;
  if (type === 'ui_scenario_completed') return `Scenariusz zakończony; czas: ${esc(payload.elapsed_minutes || 0)} min; wygasłe efekty: ${esc((payload.expired_effect_ids || []).join(', ') || 'brak')}`;
  return '';
}
function sceneStatusHtml() {
  const items = state.scene_status || [];
  const recoverable = (state.actors || []).flatMap(actor =>
    (actor.conditions || [])
      .filter(condition => condition.recoverable)
      .map(condition => `<button class="secondary" onclick="recoverExplorationCondition('${esc(actor.id)}','${esc(condition.id)}')">${esc(actor.name)}: wstań</button>`)
  );
  if (!items.length && !recoverable.length) return '<span class="muted">Brak zmian.</span>';
  return `<div class="status-list">${items.map(item => `
    <div class="status-item"><b>${esc(item.label)}</b><span>${esc(item.value)}</span></div>
  `).join('')}</div>${recoverable.length ? `<div class="row">${recoverable.join('')}</div>` : ''}`;
}

async function recoverExplorationCondition(actorId, condition) {
  await api('/api/exploration/condition/recover', {actor_id: actorId, condition}, 'Usuwanie stanu...');
}
function flowPanelHtml() {
  const flow = state.flow || {};
  const stage = flow.stage || 'waiting_for_board';
  if (stage === 'spell_preparation') {
    return spellPreparationHtml();
  }
  if (stage === 'short_rest') {
    return shortRestHtml();
  }
  if (stage === 'game_over') {
    const result = flow.interaction_result || {};
    const retry = flow.encounter_retry || {};
    return `
      <div class="start-panel"><div class="inner">
        <h2>Game Over</h2>
        <p>${esc(result.body || 'Drużyna została pokonana.')}</p>
        ${retry.available
          ? '<button class="start-button" onclick="retryEncounter()">Ponów walkę</button>'
          : `<p class="muted">${esc(retry.reason || 'Ponowienie walki jest niedostępne.')}</p>`}
        <a class="start-button" href="/">Wróć do menu</a>
      </div></div>
    `;
  }
  if (stage === 'scenario_complete') {
    const handoff = flow.scenario_handoff;
    const outcome = handoff && handoff.outcome;
    const completedTravel = handoff && handoff.travel;
    const outcomeKindLabels = {
      success: 'Sukces',
      partial_success: 'Sukces z konsekwencją',
      fail_forward: 'Niepowodzenie — historia toczy się dalej',
    };
    const objectiveStatusLabels = {
      completed: 'ukończony',
      failed: 'nieudany',
      active: 'nierozstrzygnięty',
      hidden: 'nieodkryty',
    };
    const objectives = handoff && handoff.source_objectives || flow.objectives || [];
    const lootMessages = (state.messages || [])
      .filter(message => {
        const title = String(message.title || '').toLocaleLowerCase('pl');
        return title.includes('łup') || title.includes('zebrano') || title.includes('zabezpieczono');
      })
      .slice(-5);
    const arrivalTimingLabels = {
      early: 'wcześnie',
      on_time: 'o czasie',
      late: 'późno',
    };
    return `
      <div class="start-panel"><div class="inner">
        <h2>Scenariusz zakończony</h2>
        <p>Efekty trwające do końca scenariusza zostały wygaszone.</p>
        ${outcome ? `
          <div class="status-item">
            <b>${esc(outcome.label)}</b>
            <span>${esc(outcomeKindLabels[outcome.kind] || outcome.kind)}</span>
          </div>
          ${outcome.narration ? `<p>${esc(outcome.narration)}</p>` : ''}
        ` : ''}
        ${completedTravel ? `
          <h3>Skutek podróży</h3>
          <div class="status-list">
            <div class="status-item"><b>Czas drogi</b><span>${esc(completedTravel.total_minutes)} min · ${esc(arrivalTimingLabels[completedTravel.arrival_timing] || completedTravel.arrival_timing || '-')}</span></div>
            <div class="status-item"><b>Nawigacja</b><span>${completedTravel.navigation && completedTravel.navigation.success ? 'sukces' : `porażka · ${esc((completedTravel.navigation || {}).delay_minutes || 0)} min opóźnienia`}</span></div>
            <div class="status-item"><b>Wpływ na dalszą przygodę</b><span>Okno przybycia, czujność i możliwość skradania zostały zapisane dla kolejnej mapy.</span></div>
          </div>
        ` : ''}
        ${objectives.length ? `
          <h3>Podsumowanie celów</h3>
          <div class="status-list">${objectives.map(objective => `
            <div class="status-item">
              <b>${esc(objective.name)}</b>
              <span>${esc(objectiveStatusLabels[objective.status] || objective.status)}</span>
            </div>
          `).join('')}</div>
        ` : ''}
        ${lootMessages.length ? `
          <h3>Zdobyte i zabezpieczone rzeczy</h3>
          <div class="status-list">${lootMessages.map(message => `
            <div class="status-item"><b>${esc(message.title)}</b><span>${esc(message.body)}</span></div>
          `).join('')}</div>
        ` : ''}
        ${handoff ? `<p><b>Kolejna lokacja:</b> ${esc(handoff.target_scenario_name || handoff.target_scenario_id)}</p><p class="muted">To dalsza część tej samej przygody. Drużyna, ekwipunek, czas i konsekwencje podróży zostaną przeniesione automatycznie.</p><button class="start-button" onclick="startScenarioHandoff()">Rozłóż mapę kolejnej lokacji</button>` : '<p class="muted">Możecie rozpocząć scenariusz ponownie od automatycznego long resta, konfiguracji planszy i setupu zakończonego przygotowaniem czarów.</p><button class="start-button" onclick="resetSession()">Rozpocznij ponownie</button>'}
      </div></div>
    `;
  }
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
      const requiresBoardAssignment = Boolean(step.requires_board_assignment);
      const positions = (step.positions || []).map(pos => `(${pos[0]},${pos[1]})`).join(', ');
      const paperMap = setup.paper_map || null;
      const paperMapHtml = paperMap ? `
        <div class="paper-map-setup">
          <img src="${esc(paperMap.preview_url)}" alt="Podgląd papierowej mapy">
          <div>
            <p><b>Mapa papierowa ${esc(paperMap.width_cm)} × ${esc(paperMap.height_cm)} cm</b></p>
            <p>Usuń poprzednią mapę, połącz wydrukowane kartki i połóż nową mapę na całej planszy zgodnie ze znacznikami rogów.</p>
            <div class="row">
              <a class="button-link" href="${esc(paperMap.a4_pdf_url)}" target="_blank" rel="noopener">Pobierz PDF A4</a>
              <a class="button-link secondary" href="${esc(paperMap.full_size_pdf_url)}" target="_blank" rel="noopener">PDF 50 × 75 cm</a>
            </div>
          </div>
        </div>
      ` : '';
      const fallbackButtons = (step.available_positions || []).map(pos =>
        `<button class="secondary" onclick="selectBoardPosition(${Number(pos[0])}, ${Number(pos[1])})">(${Number(pos[0])},${Number(pos[1])})</button>`
      ).join('');
      return `
        <h3>Setup mapy ${Number(setup.current_index) + 1}/${setup.step_count}</h3>
        <p><b>${esc(step.label || '')}</b></p>
        <p>${esc(step.message || '')}</p>
        ${paperMapHtml}
        ${hasPositions ? `<p><b>Kolor:</b> ${esc(step.color || '-')}</p><p><b>Pola:</b> ${esc(positions)}</p>` : '<p class="muted">Ten krok jest tylko instrukcją i nie podświetla pól na planszy.</p>'}
        <p class="muted">${requiresBoardAssignment ? `Ustaw figurkę ${esc(step.assignment_point_name || '')} i kliknij wybrane podświetlone pole.` : hasPositions ? 'Rozstaw elementy na fizycznej planszy. Jeśli potwierdzasz planszą, najpierw kliknij Skanuj planszę.' : 'Potwierdź, żeby przejść do pierwszego podświetlanego elementu mapy.'}</p>
        ${requiresBoardAssignment
          ? `<div class="row"><button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button></div><details class="encounter-position-fallback"><summary>Awaryjny wybór bez skanu</summary><div class="row">${fallbackButtons}</div></details>`
          : `<div class="row"><button onclick="confirmExplorationSetup()">Potwierdź setup</button>${hasPositions ? '<button class="secondary" data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>' : ''}</div>`}
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
        <p>Wskaż podświetloną lokację figurką, aby zobaczyć jej podgląd.</p>
        <button class="secondary" data-primary-scan="true" onclick="scanBoard()">Awaryjnie odczytaj planszę</button>
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
        <p>Wskaż inną podświetloną lokację na planszy, aby zmienić podgląd.</p>
        <button class="secondary" data-allow-busy="true" onclick="cancelLocationPreview()">Wyczyść podgląd</button>
      `;
    }
    return `
      <h3>Podgląd elementu</h3>
      ${image}
      <p><b>${esc(preview.name)}</b></p>
      <p>${esc(preview.description || preview.summary || '')}</p>
      <p><b>Kliknij ponownie pole tej lokacji, aby wejść.</b> Możesz też wskazać inną podświetloną lokację i przełączyć podgląd.</p>
      <div class="row"><button onclick="confirmLocationPreview()">Wejdź awaryjnie z ekranu</button><button class="secondary" data-allow-busy="true" onclick="cancelLocationPreview()">Wyczyść podgląd</button></div>
    `;
  }
  if (stage === 'interaction_result') {
    const result = flow.interaction_result || {};
    const unlocked = result.unlocked_zones || [];
    const points = result.revealed_points || [];
    const experience = result.experience || null;
    const levelUpActors = experience ? (experience.level_up_actors || []) : [];
    return `
      <h3>${esc(result.title || 'Wynik interakcji')}</h3>
      <div class="result">${esc(result.body || '')}</div>
      ${experience ? `
        <div class="result">
          <b>Doświadczenie: +${esc(experience.per_actor)} XP dla każdego bohatera.</b>
          ${levelUpActors.length ? `
            <p><b>Awans jest dostępny:</b> ${levelUpActors.map(actor => esc(actor.name)).join(', ')}.</p>
            <div class="row">
              ${levelUpActors.filter(actor => actor.can_open_level_up).map(actor => `
                <a class="button" href="/characters/${encodeURIComponent(String(actor.id))}/level-up">
                  Awansuj: ${esc(actor.name)}
                </a>
              `).join('')}
            </div>
          ` : ''}
        </div>
      ` : ''}
      ${unlocked.length ? `<p><b>Odblokowano lokacje:</b></p><ul>${unlocked.map(zone => `<li>${esc(zone.name)}</li>`).join('')}</ul>` : ''}
      ${points.length ? `<p><b>Ujawniono punkty:</b></p><ul>${points.map(point => `<li>${esc(point.name)}</li>`).join('')}</ul>` : ''}
      <p class="muted">${esc(result.next_instruction || 'Zakończ interakcję, aby wrócić do wyboru lokacji.')}</p>
      <button onclick="finishInteraction()">Zakończ interakcję</button>
    `;
  }
  return '';
}
function spellPreparationHtml() {
  const preparation = state.spell_preparation || {};
  const actor = (preparation.actors || []).find(entry => String(entry.actor_id) === String(preparation.current_actor_id));
  if (!actor) return '<p>Przygotowanie czarów zakończone.</p>';
  synchronizeSpellPreparationDraft(actor);
  const selectable = (actor.spells || []).filter(spell => !spell.always_prepared);
  const alwaysPrepared = (actor.spells || []).filter(spell => spell.always_prepared);
  const selectedIds = new Set((spellPreparationDraft && spellPreparationDraft.spellIds) || []);
  const selected = selectable.filter(spell => selectedIds.has(String(spell.id)));
  const customMode = spellPreparationDraft && spellPreparationDraft.mode === 'custom';
  const cards = selected.map(spell => spellPreparationCardHtml(spell)).join('');
  return `
    <div class="start-panel"><div class="inner">
      <span class="eyebrow">OSTATNI KROK SETUPU</span>
      <h2>Przygotowanie czarów — ${esc(actor.actor_name)}</h2>
      <p>${customMode
        ? 'Skanuj kolejno fizyczne karty czarów. Po osiągnięciu limitu zestaw zostanie zapisany automatycznie.'
        : 'Poniżej znajduje się proponowany zestaw po długim odpoczynku. Zeskanuj AKCEPTUJ, aby go zachować, albo ODRZUĆ, aby przygotować własny zestaw.'}</p>
      <p>Źródło: <b>${esc(actor.source_label)}</b>.</p>
      <p><b>${customMode ? 'Zeskanowano' : 'Zestaw domyślny'}:</b> <span id="spell-preparation-count">${esc(selected.length)}</span>/${esc(actor.preparation_limit)}</p>
      <div class="spell-preparation-grid${customMode ? ' custom' : ''}">
        ${cards || `<div class="spell-preparation-empty"><b>Czekam na pierwszą kartę czaru</b><span>Zeskanuj kartę należącą do listy ${esc(actor.actor_name)}.</span></div>`}
      </div>
      ${alwaysPrepared.length ? `<div class="spell-always-prepared"><b>Zawsze przygotowane — nie zajmują limitu:</b><div class="spell-preparation-grid always">${alwaysPrepared.map(spell => spellPreparationCardHtml(spell, {alwaysPrepared: true})).join('')}</div></div>` : ''}
      <p class="muted">Po rozpoczęciu scenariusza zestaw pozostaje zablokowany do następnego długiego odpoczynku.</p>
      <div class="row spell-preparation-fallback">
        ${customMode
          ? '<button class="secondary" onclick="startCustomSpellPreparation()">Wyczyść i zacznij ponownie</button>'
          : '<button id="spell-preparation-confirm" class="start-button" onclick="confirmSpellPreparation()">Zaakceptuj zestaw domyślny</button><button class="secondary" onclick="startCustomSpellPreparation()">Przygotuj własny zestaw</button>'}
      </div>
    </div></div>
  `;
}
function spellPreparationCardHtml(spell, {alwaysPrepared = false} = {}) {
  const school = String(spell.school || 'magic').replaceAll('_', '-');
  return `<article class="spell-preparation-card-tile school-${esc(school)}${alwaysPrepared ? ' always-prepared' : ''}">
    <div class="spell-preparation-art" aria-hidden="true"><span>${esc(spell.level)}</span></div>
    <div class="spell-preparation-copy">
      <span class="spell-preparation-heading"><b>${esc(spell.label)}</b><span>${esc(spell.level)}. poziom${spell.concentration ? ' · koncentracja' : ''}${spell.ritual ? ' · rytuał' : ''}</span></span>
      <span class="spell-flavor">${esc(spell.flavor_description || '')}</span>
      <span class="spell-mechanics"><b>W grze:</b> ${esc(spell.mechanical_description || 'Szczegóły mechaniczne nie są dostępne.')}</span>
    </div>
  </article>`;
}
function synchronizeSpellPreparationDraft(actor) {
  if (spellPreparationDraft && String(spellPreparationDraft.actorId) === String(actor.actor_id)) return;
  spellPreparationDraft = {
    actorId: String(actor.actor_id),
    mode: 'default',
    spellIds: (actor.spells || [])
      .filter(spell => spell.prepared && !spell.always_prepared)
      .map(spell => String(spell.id)),
  };
}
function startCustomSpellPreparation() {
  const preparation = state.spell_preparation || {};
  const actor = (preparation.actors || []).find(entry => String(entry.actor_id) === String(preparation.current_actor_id));
  if (!actor) return false;
  spellPreparationDraft = {actorId: String(actor.actor_id), mode: 'custom', spellIds: []};
  render();
  setPhysicalCardStatus(`Własny zestaw ${actor.actor_name}: zeskanuj ${actor.preparation_limit} różnych kart czarów.`);
  return true;
}
function selectSpellPreparationCard(data) {
  const preparation = state.spell_preparation || {};
  const actor = (preparation.actors || []).find(entry => String(entry.actor_id) === String(preparation.current_actor_id));
  if (!actor) return false;
  synchronizeSpellPreparationDraft(actor);
  if (!spellPreparationDraft || spellPreparationDraft.mode !== 'custom') return false;
  if (String(data.actor_id) !== String(actor.actor_id)) return false;
  const spellId = String(data.spell_id || '');
  if (!spellId || spellPreparationDraft.spellIds.includes(spellId)) {
    setPhysicalCardStatus('Ten czar jest już w przygotowywanym zestawie.', {error: true});
    return false;
  }
  if (spellPreparationDraft.spellIds.length >= Number(actor.preparation_limit || 0)) {
    setPhysicalCardStatus('Limit przygotowanych czarów został już osiągnięty.', {error: true});
    return false;
  }
  spellPreparationDraft.spellIds.push(spellId);
  const complete = spellPreparationDraft.spellIds.length === Number(actor.preparation_limit || 0);
  render();
  if (complete) {
    confirmSpellPreparation();
  }
  return true;
}
function shortRestHtml() {
  const rest = state.short_rest || {};
  const policy = rest.policy || {};
  const pending = rest.pending || {};
  const safety = policy.safety === 'safe' ? 'bezpieczne' : 'ryzykowne';
  if (!pending.completed) {
    const attunement = (pending.actors || []).map(actor => {
      const items = (actor.attunement_items || []).filter(item => item.available);
      if (!items.length) return '';
      const options = items.map(item => {
        const value = `${item.action}:${item.item_id}`;
        const label = item.action === 'unattune'
          ? `Zerwij więź: ${item.item_name}`
          : `Dostrój: ${item.item_name}`;
        return `<option value="${esc(value)}">${esc(label)}</option>`;
      }).join('');
      return `<label class="field"><span>${esc(actor.actor_name)} — attunement ${esc(actor.attunement_count)}/${esc(actor.attunement_maximum)}</span><select data-short-rest-attunement="${esc(actor.actor_id)}"><option value="">Bez zmiany</option>${options}</select></label>`;
    }).join('');
    return `
      <div class="start-panel"><div class="inner">
        <h2>Krótki odpoczynek</h2>
        <p><b>Czas:</b> ${esc(policy.duration_label || '1 godz.')}</p>
        <p><b>Warunki:</b> ${esc(safety)}</p>
        ${policy.risk_summary ? `<div class="status"><b>Koszt lub zagrożenie:</b> ${esc(policy.risk_summary)}</div>` : ''}
        ${attunement ? `<div class="status"><b>Dostrajanie magicznych przedmiotów</b><p class="muted">Każdy bohater może podczas tego odpoczynku dostroić albo odstroić jeden przedmiot.</p>${attunement}</div>` : ''}
        <p class="muted">Hit Dice będą wydawane dopiero po ukończeniu odpoczynku. Anulowanie teraz nie przesuwa czasu.</p>
        <div class="row"><button onclick="confirmShortRest()">Rozpocznij godzinny odpoczynek</button><button class="secondary" data-allow-busy="true" onclick="cancelShortRest()">Anuluj</button></div>
      </div></div>
    `;
  }
  const actors = (pending.actors || []).map(actor => {
    const dice = (actor.hit_dice || []).map(pool => {
      const inputId = `short-rest-${actor.actor_id}-d${pool.die_sides}`;
      const disabled = !actor.can_spend_hit_die || Number(pool.remaining || 0) <= 0;
      const song = actor.song_of_rest || {};
      const songInput = song.available
        ? `<label>Song of Rest k${esc(song.die_sides)} (opcjonalnie)<input id="short-rest-song-${esc(actor.actor_id)}" type="number" min="1" max="${esc(song.die_sides)}" placeholder="nie używaj"${disabled ? ' disabled' : ''}></label>`
        : song.used ? '<span class="muted">Song of Rest już wykorzystane.</span>' : '';
      return `<div class="row"><span>d${esc(pool.die_sides)}: ${esc(pool.remaining)}/${esc(pool.maximum)}</span><input id="${esc(inputId)}" type="number" min="1" max="${esc(pool.die_sides)}" placeholder="wynik"${disabled ? ' disabled' : ''}>${songInput}<button class="secondary"${disabled ? ' disabled' : ''} onclick="spendShortRestHitDie('${esc(actor.actor_id)}', ${esc(pool.die_sides)})">Wydaj Hit Die</button></div>`;
    }).join('');
    const resources = (actor.short_rest_resources || []).map(pool => `${esc(pool.label)} ${esc(pool.current)}/${esc(pool.maximum)}`).join(', ');
    const recovery = actor.slot_recovery || null;
    const recoveryHtml = recovery && recovery.available
      ? `<div><b>${esc(recovery.label)}</b><div class="row">${(recovery.options || []).map(option => `<button class="secondary" data-allow-busy="true" onclick='recoverShortRestSpellSlots(${JSON.stringify(String(actor.actor_id))}, ${JSON.stringify(option.slot_levels || [])})'>${esc(option.label)}</button>`).join('')}</div></div>`
      : recovery ? `<span class="muted">${esc(recovery.label)}: brak legalnych slotów do odzyskania.</span>` : '';
    return `<div class="status-item"><b>${esc(actor.actor_name)}</b><span>HP ${esc(actor.hp)}/${esc(actor.max_hp)} · CON ${signedNumber(actor.constitution_modifier)}</span>${dice || '<span class="muted">Brak Hit Dice.</span>'}${resources ? `<span>Odnowione zasoby: ${resources}</span>` : ''}${recoveryHtml}</div>`;
  }).join('');
  return `
    <div class="start-panel"><div class="inner">
      <h2>Krótki odpoczynek ukończony</h2>
      <p>Minęła ${esc(policy.duration_label || '1 godz.')}. Każdy gracz może wydawać Hit Dice pojedynczo i po każdym rzucie zdecydować, czy rzuca następną.</p>
      <div class="status-list">${actors}</div>
      <button onclick="finishShortRest()">Zakończ odpoczynek</button>
    </div></div>
  `;
}
function availableLocationsHtml(locations) {
  if (!locations.length) return '<p>Brak jawnych elementów sceny.</p>';
  return `<div class="available-location-grid">${locations.map(zone => {
    const rgb = Array.isArray(zone.color_rgb) ? zone.color_rgb.map(Number) : [];
    const validRgb = rgb.length === 3 && rgb.every(value => Number.isFinite(value) && value >= 0 && value <= 255);
    const frameColor = validRgb ? `rgb(${rgb.map(value => Math.round(value)).join(', ')})` : '#d6a72e';
    const locked = zone.available === false;
    const image = zone.image_url
      ? `<img src="${esc(zone.image_url)}" alt="Widok lokacji: ${esc(zone.name)}" loading="lazy">`
      : `<span class="available-location-image-fallback">Brak grafiki</span>`;
    return `<article class="available-location-card${locked ? ' locked' : ''}" style="--location-frame-color: ${frameColor}">
      <b>${esc(zone.name)}</b>
      <div class="available-location-thumbnail">${image}</div>
      ${locked
        ? `<small>Zablokowane · ${esc(zone.locked_reason || 'jeszcze niedostępne')}</small>`
        : '<small>Dostępne na planszy</small>'}
    </article>`;
  }).join('')}</div>`;
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
  const stage = state.flow ? state.flow.stage : 'location_active';
  if (stage !== 'location_active') {
    return '';
  }
  const parts = [
    zone.image_url ? `<img class="scene-image" src="${esc(zone.image_url)}" alt="${esc(zone.name)}">` : '',
    `<h2>${esc(zone.name)}</h2>`,
    zone.description ? `<p class="scene-lead">${esc(zone.description)}</p>` : '',
    zone.summary ? `<p>${esc(zone.summary)}</p>` : '',
  ];
  if (state.active_point) {
    const point = state.active_point;
    parts.push(`<p><b>${esc(point.name)}</b></p>`);
    parts.push(point.description ? `<p>${esc(point.description)}</p>` : '');
    if (point.npc) {
      parts.push(`<p>${esc(point.npc.public_description)}</p>`);
      const runtime = point.npc.runtime_state || null;
      if (runtime) {
        const attitudeLabels = { hostile: 'wrogi', indifferent: 'obojętny', friendly: 'przyjazny' };
        parts.push(`<p><b>Nastawienie:</b> ${esc(attitudeLabels[runtime.attitude] || runtime.attitude || '-')}</p>`);
        if (runtime.physical_state) parts.push(`<p><b>Stan fizyczny:</b> ${esc(runtime.physical_state)}</p>`);
        if (runtime.emotional_state) parts.push(`<p><b>Stan emocjonalny:</b> ${esc(runtime.emotional_state)}</p>`);
        if ((runtime.relationship_events || []).length) {
          const lastEvent = runtime.relationship_events[runtime.relationship_events.length - 1];
          parts.push(`<p class="muted"><b>Ostatnia ważna interakcja:</b> ${esc(lastEvent.summary)}</p>`);
        }
        if ((runtime.used_attempt_ids || []).length) {
          parts.push(`<p class="muted"><b>Wykorzystane próby:</b> ${runtime.used_attempt_ids.map(esc).join(', ')}</p>`);
        }
        if ((runtime.revealed_information_ids || []).length) {
          parts.push(`<p class="muted"><b>Zdobyte informacje:</b> ${esc(runtime.revealed_information_ids.length)}</p>`);
        }
      } else if (point.npc.current_state) {
        parts.push(`<p><b>Stan NPC:</b> ${esc(point.npc.current_state)}</p>`);
      }
    }
  }
  const html = parts.filter(Boolean).join('');
  return html.trim() ? html : '';
}
function sceneConversationHtml() {
  const entries = [...((state.conversation && state.conversation.entries) || [])];
  if (resultAck) {
    for (let index = entries.length - 1; index >= 0; index -= 1) {
      if (entries[index].title === resultAck.title && entries[index].body === resultAck.body) {
        entries.splice(index, 1);
        break;
      }
    }
  }
  if (optimisticPlayerMessage) entries.push(optimisticPlayerMessage);
  let latestGmIndex = -1;
  for (let index = entries.length - 1; index >= 0; index -= 1) {
    if (entries[index].role !== 'player') {
      latestGmIndex = index;
      break;
    }
  }
  const transition = state.pending_npc_transition;
  const transitionHtml = transition ? `
    <div class="conversation-entry gm npc-transition-card">
      <b>${esc(transition.title)}</b>
      <span>${esc(transition.narration)}</span>
      <div class="npc-transition-reactions">
        ${(transition.reactions || []).map(reaction => `
          <button onclick="resolveNpcTransition('${esc(reaction.id)}')">
            ${esc(reaction.label)}
            <small>${esc(reaction.description)}</small>
          </button>
        `).join('')}
      </div>
    </div>` : '';
  return `<div class="scene-conversation-list">
    ${sceneIntroMessageHtml()}
    ${entries.map((message, index) => `
    ${index === latestGmIndex ? '<div class="latest-response-marker"><span>Najnowsza odpowiedź</span></div>' : ''}
    ${messageCardHtml(message, `conversation-entry ${message.role === 'player' ? 'player' : 'gm'}${index === latestGmIndex ? ' latest-response' : ''}`)}
  `).join('')}${transitionHtml}</div>`;
}
function resolveNpcTransition(reactionId) {
  api('/api/npc-transition/resolve', {reaction_id: reactionId}, 'Rozstrzygam reakcję drużyny...');
}
function sceneIntroMessageHtml() {
  const briefingPoint = state.active_point;
  if (briefingPoint?.npc?.briefing_contract) {
    const npc = briefingPoint.npc;
    const entries = state.conversation?.entries || [];
    const hasIntro = entries.some(entry => entry.body === npc.dialogue_intro);
    return `<article class="briefing-npc-intro">
      ${scenarioInteractionImage(briefingPoint.image, npc.name, 'portrait')}
      <div><span class="eyebrow">Odprawa w Gildii</span><h3>${esc(npc.name)}</h3>
        <p>${esc(npc.public_description)}</p></div>
      ${!hasIntro && !entries.length ? `<p class="briefing-opening">${esc(npc.dialogue_intro)}</p>` : ''}
    </article>`;
  }
  const zone = state.current_zone || {};
  const point = state.active_point || null;
  const title = point ? point.name : zone.name;
  const descriptions = point
    ? [point.description, point.npc && point.npc.public_description]
    : [zone.description, zone.summary];
  const image = zone.image_url
    ? `<img class="conversation-scene-image" src="${esc(zone.image_url)}" alt="${esc(title)}">`
    : '';
  return `
    <div class="conversation-entry gm scene-intro-message">
      <b>MG · ${esc(title || 'Eksploracja')}</b>
      ${image}
      ${descriptions.filter(Boolean).map(description => `<span>${esc(description)}</span>`).join('')}
    </div>
  `;
}
function conversationMetaHtml() {
  const point = state.active_point || null;
  const npc = point && point.npc ? point.npc : null;
  if (!npc) return '<span class="conversation-context-chip neutral">Eksploracja swobodna</span>';
  const runtime = npc.runtime_state || {};
  const attitudeLabels = {hostile: 'wrogi', indifferent: 'obojętny', friendly: 'przyjazny'};
  const attitude = attitudeLabels[runtime.attitude] || runtime.attitude || npc.current_state || 'nieznane';
  const attitudeClass = ['hostile', 'indifferent', 'friendly'].includes(runtime.attitude) ? runtime.attitude : 'unknown';
  const chips = [
    `<span class="conversation-context-chip attitude-${attitudeClass}">Nastawienie: ${esc(attitude)}</span>`,
  ];
  if (runtime.physical_state) chips.push(`<span class="conversation-context-chip">${esc(runtime.physical_state)}</span>`);
  if (runtime.emotional_state) chips.push(`<span class="conversation-context-chip">${esc(runtime.emotional_state)}</span>`);
  return chips.join('');
}
function currentInteractionGoals() {
  const point = state.active_point || null;
  if (point && point.npc) return point.npc.goals || [];
  return state.active_challenge ? (state.active_challenge.goals || []) : [];
}
function briefingContractHtml() {
  const contract = state.active_point?.npc?.briefing_contract;
  if (!contract) return '';
  const expanded = document.querySelector('.briefing-contract')?.open;
  return `<details class="briefing-contract"${expanded ? ' open' : ''}>
    <summary>Umowa z Gildią <span>${esc(contract.status)}</span></summary>
    <dl>${contract.rows.map(row => `<div><dt>${esc(row.label)}</dt><dd>${esc(row.value)}</dd></div>`).join('')}</dl>
  </details>`;
}
function briefingRecapHtml(goal) {
  const recap = goal.recap || {};
  return `<article class="briefing-recap" aria-live="polite">
    <span class="eyebrow">${esc(goal.topic_status)} · przypomnienie</span>
    <h3>${esc(goal.label)}</h3>
    ${recap.narration ? `<p class="npc-gesture">${esc(recap.narration)}</p>` : ''}
    ${recap.speech ? `<blockquote>${esc(recap.speech)}</blockquote>` : ''}
    <p class="npc-outcome">${esc(recap.result || '')}</p>
    <button type="button" class="secondary" onclick="cancelInteractionGoal()">Wróć do tematów</button>
  </article>`;
}
function briefingArgumentHelpHtml(goal) {
  if (!goal.negotiation_targets) return '';
  const targets = goal.negotiation_targets.filter(target => target.skill === selectedSocialSkill);
  return `<div class="briefing-argument-help">
    <b>O co możecie się ubiegać?</b>
    ${targets.map(target => `<p><strong>${esc(target.label)}</strong> — ${esc(target.description)}</p>`).join('')}
    ${goal.known_arguments?.length ? `<b>Poznane fakty, których możecie użyć</b><ul>${goal.known_arguments.map(fact => `<li>${esc(fact)}</li>`).join('')}</ul>` : ''}
    <small>Liczy się sens argumentu. Nie musicie pisać długiej przemowy. Jedna rozstrzygnięta negocjacja zamyka warunki umowy.</small>
  </div>`;
}
function currentInteractionPointCards() {
  if (state.active_point) return [];
  return (state.current_zone_points || []).filter(point => point && (point.has_npc || point.has_merchant));
}
function selectPointPreview(pointId) {
  resetInteractionSelection();
  selectedPointPreviewId = String(pointId || '');
  render();
}
function cancelPointPreview() {
  selectedPointPreviewId = null;
  api('/api/board/clear-selection', {}, 'Wracam do wyboru hotspotów...');
}
function pointPreviewHtml(point) {
  if (!point) return '';
  const npc = point.npc || null;
  const position = (point.positions || [])[0] || [];
  const boardInstruction = position.length === 2
    ? `Pole ${esc(position[0])},${esc(position[1])} wskazane. Na planszy kliknij ponownie pole ${esc(position[0])},${esc(position[1])}, aby wejść w interakcję.`
    : 'Hotspot wskazany. Na planszy kliknij ponownie pole hotspotu, aby wejść w interakcję.';
  return `<div class="goal-action-composer point-preview-card">
    ${scenarioInteractionImage(point.image, point.name, 'preview')}
    <h3>${esc(point.name || point.interaction_label || 'Punkt interakcji')}</h3>
    <p>${esc(point.description || '')}</p>
    ${npc && npc.public_description ? `<p class="muted">${esc(npc.public_description)}</p>` : ''}
    <div class="point-preview-confirmation">
      <b>${boardInstruction}</b>
      <span>Wskazanie innego hotspotu zmieni podgląd.</span>
    </div>
    <span class="point-preview-waiting">Oczekuje na potwierdzenie</span>
  </div>`;
}

function selectedPointPreview() {
  if (!selectedPointPreviewId || state.active_point) return null;
  return currentInteractionPointCards().find(
    point => String(point.id) === String(selectedPointPreviewId)
  ) || null;
}

function renderInteractionWorkspace() {
  const preview = selectedPointPreview();
  const previewPane = document.getElementById('point-preview-pane');
  const conversationContent = document.getElementById('conversation-content');
  const conversationTitle = document.getElementById('conversation-pane-title');
  const conversationStatus = document.getElementById('conversation-pane-status');
  const actionsTitle = document.getElementById('actions-pane-title');
  const kicker = document.getElementById('chat-instance-kicker');
  if (!previewPane || !conversationContent) return;
  previewPane.hidden = !preview;
  previewPane.innerHTML = preview ? pointPreviewHtml(preview) : '';
  conversationContent.hidden = Boolean(preview);
  conversationTitle.textContent = preview ? 'Podgląd hotspotu' : 'Rozmowa';
  conversationStatus.textContent = preview ? 'Pierwsze wskazanie pola' : 'Historia interakcji';
  actionsTitle.textContent = state.active_point ? 'Dostępne działania' : 'Hotspoty na mapie';
  kicker.textContent = state.active_point ? 'Rozmowa z MG' : 'Eksploracja swobodna';
  document.body.classList.toggle('point-preview-mode', Boolean(preview));
}
function boardInteractionState() {
  return (state.flow && state.flow.board_interaction) || null;
}
function boardPadFor(actionKind, targetId) {
  const interaction = boardInteractionState();
  if (!interaction) return null;
  return (interaction.pads || []).find(pad =>
    pad.action_kind === actionKind && String(pad.target_id) === String(targetId)
  ) || null;
}
function boardPadCss(pad) {
  if (!pad || !pad.color_rgb) return '';
  return `--board-pad-color:rgb(${pad.color_rgb.map(Number).join(',')})`;
}
function boardPadBadge(pad) {
  if (!pad) return '';
  return `<span class="board-pad-badge" style="${boardPadCss(pad)}">
    <strong>${esc(pad.symbol)}</strong>
    ${esc(pad.color)} · pole ${esc(pad.coordinate_label)}
  </span>`;
}
function numpadChoiceBadge(key) {
  return `<span class="numpad-choice-badge" aria-hidden="true">${esc(key)}</span>`;
}
function numpadChoiceHint(keysOrCount, label = 'Wybierz opcję') {
  const keys = Array.isArray(keysOrCount)
    ? [...new Set(keysOrCount.map(Number).filter(key => key >= 1 && key <= 9))].sort((left, right) => left - right)
    : Array.from({length: Math.min(9, Math.max(1, Number(keysOrCount) || 1))}, (_unused, index) => index + 1);
  return `<div class="numpad-choice-hint">
    <span><b>NUMPAD</b> · ${esc(label)}: ${keys.map(key => `<kbd>${esc(key)}</kbd>`).join(' ')}</span>
    <span>${state.active_point ? '<kbd>0</kbd> zakończ rozmowę · ' : ''}<span class="board-control-symbol">↩</span> wróć · <span class="board-control-symbol">✓</span> akceptuj / dalej</span>
  </div>`;
}
function scenarioInteractionImage(imagePath, altText, variant = 'tile') {
  if (!imagePath) return '';
  const normalized = String(imagePath).replace(/^\/+/, '');
  const filename = normalized.split('/').pop() || '';
  const focusByFilename = {
    'nessa_portrait.png': variant === 'preview' ? '50% 9%' : '50% 14%',
    'tile_disappearance.png': '50% 46%',
    'tile_cargo.png': '50% 48%',
    'tile_people_alven.png': '50% 42%',
    'tile_insight.png': '50% 45%',
    'tile_erynd_documents.png': '50% 44%',
    'tile_negotiation.png': '50% 44%',
    'tile_departure.png': '50% 42%',
  };
  const focus = focusByFilename[filename] || '50% 50%';
  return `<img class="interaction-goal-image interaction-goal-image-${esc(variant)}" style="--interaction-image-position:${esc(focus)}" src="/scenario-assets/${esc(normalized)}" alt="${esc(altText || '')}" loading="eager">`;
}
function boardChoiceToolbarHtml() {
  const interaction = boardInteractionState();
  if (!interaction || state.flow.stage !== 'location_active') return '';
  if (boardSelectionPausedForScreenInput()) return '';
  if (interaction.mode === 'navigation') {
    return `<div class="board-choice-toolbar">
      <span><b>Wybierz drogę</b><small>Kliknij lokację tutaj albo jej znacznik na planszy.</small></span>
      <div data-board-input-status>${boardSelectionStatusHtml(true)}</div>
    </div>`;
  }
  return `<div class="board-choice-toolbar">
    <span><b>Wybierz kafelek</b><small>Kliknij działanie albo czerwone pole wyjścia.</small></span>
    <div data-board-input-status>${boardSelectionStatusHtml(true)}</div>
  </div>`;
}
function navigationLocationBadge(zone) {
  const position = zone.marker_position || [];
  const color = zone.color_rgb || [];
  const style = color.length === 3
    ? `--board-pad-color:rgb(${color.map(Number).join(',')})`
    : '';
  const coordinate = position.length === 2 ? ` · pole ${esc(position[0])},${esc(position[1])}` : '';
  return `<span class="board-pad-badge" style="${style}">
    <strong>●</strong>${esc(zone.color || 'znacznik')}${coordinate}
  </span>`;
}
function navigationChoicesHtml() {
  const current = state.current_zone || {};
  const options = state.travel_options || [];
  const cards = [
    `<button type="button" class="interaction-goal-card navigation-current-card" onclick="setBoardSelectionMode(false)">
      ${navigationLocationBadge(current)}
      <b>Pozostańcie: ${esc(current.name || 'obecna lokacja')}</b>
      <span>Wróćcie do rozmów i działań dostępnych w tej lokacji.</span>
      <small>Wróć do działań</small>
    </button>`,
    ...options.map(zone => {
      const position = zone.marker_position || [];
      const action = position.length === 2
        ? `selectBoardPosition(${Number(position[0])}, ${Number(position[1])})`
        : `travel('${esc(zone.id)}')`;
      return `<button type="button" class="interaction-goal-card board-linked-tile" style="${navigationLocationBadgeStyle(zone)}" onclick="${action}">
        ${navigationLocationBadge(zone)}
        <b>${esc(zone.name)}</b>
        <span>${esc(zone.description || zone.summary || '')}</span>
        <small>Podgląd lokacji · wskaż ponownie, aby wejść</small>
      </button>`;
    }),
  ];
  return `<div class="interaction-goals-head">
    <b>Dokąd idziecie?</b>
    <span>Najpierw wybierzcie drogę. Gra pokaże podgląd i poprosi o potwierdzenie.</span>
  </div>
  <div class="interaction-goal-grid">${cards.join('')}</div>`;
}
function navigationLocationBadgeStyle(zone) {
  const color = zone.color_rgb || [];
  return color.length === 3
    ? `--board-pad-color:rgb(${color.map(Number).join(',')})`
    : '';
}
function zoneOptionCardsHtml(options) {
  return options.map(option => {
    const pad = boardPadFor('zone_option', option.id);
    const check = option.check || null;
    const assignedActor = option.assigned_actor || null;
    const checkText = check
      ? `${abilityLabel(check.ability)}${check.skill ? ` (${skillLabel(check.skill)})` : ''}${check.tool_label ? ` + ${esc(check.tool_label)}` : ''}, ST ${esc(check.dc)}`
      : 'Bez rzutu';
    const stakes = Number(option.entry_cost_cp || 0) > 0
      ? `Stawka ${esc(option.entry_cost_cp)} cp${Number(option.success_reward_cp || 0) > 0 ? ` · wypłata za wygraną ${esc(option.success_reward_cp)} cp` : ''}`
      : '';
    const timeCost = Number(option.time_cost_minutes || 0) > 0
      ? `${esc(option.time_cost_minutes)} min`
      : '';
    return `<button type="button" class="interaction-goal-card zone-option-card${option.character_moment ? ' character-moment-card' : ''}${option.completed ? ' completed' : ''}${option.id === selectedZoneOptionId ? ' selected' : ''}${pad ? ' board-linked-tile' : ''}"${pad ? ` style="${boardPadCss(pad)}"` : ''}${option.completed ? ' disabled' : ` onclick="selectZoneOptionGoal('${esc(option.id)}')"`}>
      ${boardPadBadge(pad)}
      ${scenarioInteractionImage(option.image, option.label)}
      ${assignedActor ? actorPortraitHtml(assignedActor, 'choice') : ''}
      <b>${esc(option.label)}</b>
      <span>${esc(option.description || option.message || '')}</span>
      <small>${option.completed ? 'Ukończone' : esc([
        assignedActor ? `Indywidualna interakcja · ${assignedActor.name}` : '',
        checkText,
        stakes,
        timeCost,
      ].filter(Boolean).join(' · '))}</small>
    </button>`;
  }).join('');
}
function selectZoneOptionGoal(optionId) {
  selectedInteractionGoalId = null;
  selectedZoneOptionId = optionId;
  selectedZoneOptionActorId = '';
  const option = (((state || {}).flow || {}).zone_options || []).find(
    candidate => String(candidate.id) === String(optionId)
  );
  const eligibleActors = (state.actors || []).filter(
    actor => actor.faction === 'ally' && !actor.defeated
  );
  if (option && option.assigned_actor_id) {
    selectedZoneOptionActorId = String(option.assigned_actor_id);
  } else if (option && option.check && eligibleActors.length === 1) {
    selectedZoneOptionActorId = String(eligibleActors[0].id);
  }
  pauseBoardForScreenInput();
  const panel = document.getElementById('interaction-goals');
  if (panel) panel.innerHTML = interactionGoalsHtml();
}
function selectZoneOptionActor(actorId) {
  const option = (((state || {}).flow || {}).zone_options || []).find(
    candidate => String(candidate.id) === String(selectedZoneOptionId)
  );
  const actor = (state.actors || []).find(
    candidate => String(candidate.id) === String(actorId)
      && candidate.faction === 'ally'
      && !candidate.defeated
  );
  if (
    !option
    || !option.check
    || !actor
    || (option.assigned_actor_id && String(option.assigned_actor_id) !== String(actorId))
  ) return false;
  selectedZoneOptionActorId = String(actorId || '');
  const panel = document.getElementById('interaction-goals');
  if (panel) panel.innerHTML = interactionGoalsHtml();
  const input = document.getElementById('zone-option-description');
  if (input) input.focus();
  return true;
}
function zoneOptionComposerHtml(option) {
  if (!option) return '';
  const allies = (state.actors || []).filter(actor => actor.faction === 'ally' && !actor.defeated);
  const assignedActor = option.assigned_actor || null;
  const needsActor = Boolean(option.check);
  const descriptionMode = option.description_mode || 'required';
  const actorReady = !needsActor || Boolean(selectedZoneOptionActorId);
  const descriptionStepLabel = needsActor && !assignedActor ? '2. Jak to robicie?' : 'Jak to robicie?';
  const descriptionControl = descriptionMode === 'none' ? '' : `
    <label for="zone-option-description"><b>${descriptionMode === 'required' ? descriptionStepLabel : 'Opcjonalnie: jak to robicie?'}</b>
      <span>${descriptionMode === 'required'
        ? 'Krótko opiszcie sposób działania.'
        : 'Możecie dodać metodę dla narracji lub autorskiej premii. Puste pole oznacza standardowe wykonanie.'}</span>
    </label>
    <textarea id="zone-option-description" placeholder="${descriptionMode === 'required' ? 'Opiszcie sposób działania…' : 'Opcjonalny opis metody…'}"></textarea>
  `;
  return `<div class="goal-action-composer">
    ${assignedActor ? `<b>Ta scena należy do tej postaci</b>
      <div class="interaction-actor-grid">
        <div class="interaction-actor-card selected">${actorPortraitHtml(assignedActor, 'choice')}<span><b>${esc(assignedActor.name)}</b><small>automatyczny wykonawca</small></span></div>
      </div>` : needsActor ? `<b>1. Kto podejmuje działanie?</b>
      <span>Ta postać wykona test i poniesie jego konsekwencje.</span>
      <div class="interaction-actor-grid">
        ${allies.map(actor => `<button type="button" class="interaction-actor-card${String(actor.id) === String(selectedZoneOptionActorId) ? ' selected' : ''}" onclick="selectZoneOptionActor('${esc(actor.id)}')">${actorPortraitHtml(actor, 'choice')}<span><b>${esc(actor.name)}</b><small>${String(actor.id) === String(selectedZoneOptionActorId) ? 'wykonuje' : 'wybierz'}</small></span></button>`).join('')}
      </div>` : ''}
    ${actorReady ? `
      ${descriptionControl}
      <div class="row">
        <button type="button" onclick="submitZoneOption()">${option.resolution_mode === 'automatic' ? 'Wykonaj' : 'Przejdź do testu'}</button>
        <button type="button" class="secondary" onclick="cancelZoneOptionGoal()">Wróć</button>
      </div>
    ` : `
      <p class="flow-note">Najpierw wybierzcie postać wykonującą test.</p>
      <button type="button" class="secondary" onclick="cancelZoneOptionGoal()">Wróć</button>
    `}
  </div>`;
}
function cancelZoneOptionGoal() {
  selectedZoneOptionId = null;
  selectedZoneOptionActorId = null;
  api('/api/board/clear-selection', {}, 'Wracam do wyboru działania...');
}
function submitZoneOption() {
  const option = ((((state || {}).flow || {}).zone_options) || []).find(
    candidate => String(candidate.id) === String(selectedZoneOptionId)
  );
  if (!option) return;
  if (option.check && !selectedZoneOptionActorId) {
    alert('Najpierw wybierz postać, która podejmuje działanie.');
    return;
  }
  const input = document.getElementById('zone-option-description');
  const description = input ? input.value.trim() : '';
  if (!description && option.description_mode === 'required') {
    alert('Najpierw opiszcie, jak wykonujecie to działanie.');
    return;
  }
  api('/api/exploration/option', {
    option_id: selectedZoneOptionId,
    actor_id: selectedZoneOptionActorId || null,
    player_description: description,
  }, 'Przygotowuję rozstrzygnięcie...');
}
function continuationPanelHtml(continuation) {
  if (!continuationPanelOpen || !continuation) return '';
  if (!continuation.available) {
    return `<div class="goal-action-composer continuation-composer">
      <h3>🔒 ${esc(continuation.label)}</h3>
      <p>${esc(continuationUnavailableText(continuation))}</p>
      <div class="flow-note">Brama jest widocznym hotspotem, ale wyjazd odblokuje się dopiero po zakończeniu odprawy z Nessą.</div>
      <button type="button" class="secondary" onclick="closeContinuationPanel()">Wróć do Gildii</button>
    </div>`;
  }
  const travel = continuation.travel || {};
  const allies = (state.actors || []).filter(actor => actor.faction === 'ally' && !actor.defeated);
  const navigator = allies.find(actor => String(actor.id) === String(selectedContinuationNavigatorId)) || null;
  const naturalExplorer = allies.find(actor => (travel.natural_explorer_actor_ids || []).map(String).includes(String(actor.id))) || null;
  const baseMinutes = Number(continuation.travel_minutes || 0);
  const paceMinutes = continuationPaceMinutes(baseMinutes, selectedContinuationPace);
  const worstMinutes = paceMinutes + Number(travel.navigation_failure_delay_minutes || 0);
  const forcedCount = Math.max(0, Math.ceil((worstMinutes - Number(travel.safe_travel_minutes || 480)) / 60));
  const steps = [
    ['pace', '1', 'Tempo'],
    ['navigator', '2', travel.navigation_automatic || travel.navigation_dc === null || travel.navigation_dc === undefined ? 'Prowadzenie automatyczne' : 'Prowadzący'],
    ['roll', '3', 'Rzut i wymarsz'],
  ];
  const departureSummary = (continuation.departure_summary || []).filter(item => item.known);
  const departureSummaryHtml = departureSummary.length
    ? `<div class="continuation-summary"><b>Ustalenia przed wymarszem</b>${departureSummary.map(item => `<span>• ${esc(item.label)}</span>`).join('')}</div>`
    : '';
  const stepIndex = Math.max(0, steps.findIndex(([id]) => id === continuationStep));
  const progress = `<div class="continuation-steps">${steps.map(([id, number, label], index) => `
    <div class="continuation-step${id === continuationStep ? ' active' : ''}${index < stepIndex ? ' complete' : ''}">
      <span>${esc(number)}</span><b>${esc(label)}</b>
    </div>`).join('')}</div>`;
  const authoredPaces = new Map((travel.paces || []).map(option => [String(option.id), option]));
  const paceOptions = [
    {id: 'fast', label: 'Szybkie', tone: 'danger'},
    {id: 'normal', label: 'Normalne', tone: 'normal'},
    {id: 'slow', label: 'Wolne', tone: 'safe'},
  ].map(base => {
    const authored = authoredPaces.get(base.id) || {};
    const perceptionModifier = Number(authored.passive_perception_modifier || 0);
    const allowsStealth = Boolean(authored.allows_stealth);
    return {
      ...base,
      label: authored.label || base.label,
      minutes: continuationPaceMinutes(baseMinutes, base.id),
      detail: `${perceptionModifier ? `Pasywna Percepcja ${signedNumber(perceptionModifier)}` : 'Pełna Pasywna Percepcja'} · ${allowsStealth ? 'możliwy Stealth' : 'bez Stealth podczas drogi'}`,
      approachConsequence: authored.approach_consequence || '',
      combatConsequence: authored.combat_consequence || '',
      campaignConsequence: authored.campaign_consequence || '',
    };
  });
  const paceBody = `<div class="continuation-stage">
    <span class="eyebrow">ETAP 1 Z 3</span>
    <h4>Jak szybko maszerujecie?</h4>
    <p>Tempo zmienia czas podróży, czujność drużyny i możliwość skradania się.</p>
    <div class="continuation-pace-grid">${paceOptions.map(option => `
      <button type="button" class="continuation-pace-card ${esc(option.tone)}${selectedContinuationPace === option.id ? ' selected' : ''}${boardPadFor('continuation_pace', option.id) ? ' board-linked-tile' : ''}" style="${boardPadCss(boardPadFor('continuation_pace', option.id))}" onclick="selectContinuationPace('${esc(option.id)}')">
        ${boardPadBadge(boardPadFor('continuation_pace', option.id))}
        <b>${esc(option.label)}</b>
        <strong>${esc(option.minutes)} min</strong>
        <span>Dotarcie około ${esc(continuationArrivalTime(option.minutes))}</span>
        <small>${esc(option.detail)}</small>
        <ul class="continuation-pace-consequences">
          ${option.approachConsequence ? `<li><b>Droga:</b> ${esc(option.approachConsequence)}</li>` : ''}
          ${option.combatConsequence ? `<li><b>Najbliższa walka:</b> ${esc(option.combatConsequence)}</li>` : ''}
          ${option.campaignConsequence ? `<li><b>Dalsze skutki:</b> ${esc(option.campaignConsequence)}</li>` : ''}
        </ul>
      </button>`).join('')}</div>
    <div class="flow-note"><b>Okno przybycia:</b> względem planu tempo szybkie oznacza wcześniejsze dotarcie, normalne — dotarcie o czasie, a wolne — późne. Porażka nawigatora doda ${esc(travel.navigation_failure_delay_minutes || 0)} min i może przesunąć wyprawę do późniejszego okna. ${forcedCount ? `Najgorszy wariant wymaga ${esc(forcedCount)} testów wymuszonego marszu na bohatera.` : 'Ta trasa nie przekracza bezpiecznego limitu marszu.'}</div>
    <div class="row"><button type="button" onclick="advanceContinuationStep()">Dalej: wybór prowadzącego</button><button type="button" class="secondary" onclick="closeContinuationPanel()">Anuluj</button></div>
  </div>`;
  const navigationModifier = navigator
    ? continuationNavigationModifier(navigator, travel.navigation_ability || 'wisdom', travel.navigation_skill)
    : 0;
  const navigatorBody = `<div class="continuation-stage">
    <span class="eyebrow">ETAP 2 Z 3</span>
    <h4>Kto prowadzi drużynę?</h4>
    ${travel.navigation_automatic ? `
      <div class="continuation-navigator-selected"><b>${esc(naturalExplorer ? naturalExplorer.name : 'Natural Explorer')}</b><span>Znajomy teren: ${esc(travel.terrain || '-')}. Drużyna nie może zgubić się niemagicznie.</span></div>
      <div class="row"><button type="button" onclick="advanceContinuationStep()">Dalej: podsumowanie</button></div>
    ` : travel.navigation_dc === null || travel.navigation_dc === undefined ? `
      <div class="flow-note">Ta droga nie wymaga testu nawigacji ani wskazania prowadzącego.</div>
      <div class="row"><button type="button" onclick="advanceContinuationStep()">Dalej: podsumowanie</button></div>
    ` : `
      <p>Zeskanuj kartę bohatera. Wybrana postać wykona test ${esc(abilityLabel(travel.navigation_ability || 'wisdom'))}${travel.navigation_skill ? ` (${esc(skillLabel(travel.navigation_skill))})` : ''} przeciw ST ${esc(travel.navigation_dc)}.</p>
      <div class="continuation-navigator-grid">${allies.map(actor => `
        <article class="continuation-navigator-card${navigator && String(actor.id) === String(navigator.id) ? ' selected' : ''}">
          ${actor.portrait_url ? `<img src="${esc(actor.portrait_url)}" alt="">` : ''}
          <b>${esc(actor.name)}</b>
          <span>Modyfikator ${signedNumber(continuationNavigationModifier(actor, travel.navigation_ability || 'wisdom', travel.navigation_skill))}</span>
          ${Number(actor.exhaustion_level || 0) >= 1 ? '<small>Utrudnienie przez wyczerpanie</small>' : '<small>Zeskanuj kartę bohatera</small>'}
        </article>`).join('')}</div>
      ${navigator ? `<div class="continuation-navigator-selected"><b>Wybrano: ${esc(navigator.name)}</b><span>Test ${signedNumber(navigationModifier)} przeciw ST ${esc(travel.navigation_dc)}.</span></div>` : '<div class="flow-note">Czytnik czeka na kartę prowadzącego.</div>'}
    `}
    <div class="row"><button type="button" class="secondary" onclick="retreatContinuationStep()">Wróć do tempa</button></div>
  </div>`;
  const forcedInputs = forcedCount ? allies.map(actor => `
    <div class="status-item"><b>${esc(actor.name)} — wymuszony marsz</b>
      ${Array.from({length: forcedCount}, (_unused, index) => `
        <label>Godzina ${index + 1}, Constitution save ST ${11 + index}:
          <input id="forced-${esc(actor.id)}-${index}-1" type="number" min="1" max="20" value="10">
          ${Number(actor.exhaustion_level || 0) >= 1 ? `<input id="forced-${esc(actor.id)}-${index}-2" type="number" min="1" max="20" value="10" aria-label="Drugi rzut z utrudnienia">` : ''}
        </label>
      `).join('')}
    </div>
  `).join('') : '';
  const rollBody = `<div class="continuation-stage">
    <span class="eyebrow">ETAP 3 Z 3</span>
    <h4>Rzut podróży</h4>
    <div class="continuation-summary">
      <span><b>Tempo:</b> ${esc(paceOptions.find(option => option.id === selectedContinuationPace)?.label || 'Normalne')} · ${esc(paceMinutes)} min</span>
      <span><b>Przewidywane dotarcie:</b> ${esc(continuationArrivalTime(paceMinutes))}</span>
      <span><b>Okno przybycia przy udanej nawigacji:</b> ${esc(continuationScheduleLabel(baseMinutes, paceMinutes))}</span>
      ${navigator ? `<span><b>Prowadzący:</b> ${esc(navigator.name)} · test ${signedNumber(navigationModifier)}</span>` : naturalExplorer ? `<span><b>Prowadzący:</b> ${esc(naturalExplorer.name)} · automatyczny sukces Natural Explorer</span>` : ''}
    </div>
    <div class="interaction-participants">
      ${travel.navigation_automatic ? `
        <p class="flow-note"><b>Bez rzutu na nawigację:</b> Natural Explorer zapobiega niemagicznemu zgubieniu drogi.</p>
      ` : travel.navigation_dc !== null && travel.navigation_dc !== undefined ? `
        <label>Naturalny wynik d20 — ${esc(skillLabel(travel.navigation_skill || 'survival'))}, ST ${esc(travel.navigation_dc)}:
          <input id="continuation-navigation-roll-1" type="number" min="1" max="20" value="10" autofocus>
        </label>
        ${navigator && Number(navigator.exhaustion_level || 0) >= 1 ? `<label>Drugi d20 z utrudnienia:
          <input id="continuation-navigation-roll-2" type="number" min="1" max="20" value="10">
        </label>` : ''}
        <p class="muted">Nieudana nawigacja nie zatrzyma wyprawy, ale doda ${esc(travel.navigation_failure_delay_minutes || 0)} min opóźnienia.</p>
      ` : '<p class="flow-note">Ta trasa nie wymaga rzutu na nawigację.</p>'}
      ${forcedInputs ? `<h4>Wymuszony marsz</h4><p class="muted">Wpisz zapasowe rzuty wymagane tylko wtedy, gdy ostateczny czas przekroczy bezpieczny limit.</p>${forcedInputs}` : ''}
    </div>
    <div class="row"><button type="button" onclick="submitContinuation()">Wyrusz i zapisz scenę</button><button type="button" class="secondary" onclick="retreatContinuationStep()">Wróć</button></div>
  </div>`;
  return `<div class="goal-action-composer continuation-composer">
    <h3>${esc(continuation.label)}</h3>
    <p>${esc(continuation.description || '')}</p>
    ${departureSummaryHtml}
    ${progress}
    ${continuationStep === 'pace' ? paceBody : continuationStep === 'navigator' ? navigatorBody : rollBody}
  </div>`;
}
function simpleContinuationPanelHtml(continuation) {
  if (!continuationPanelOpen || !continuation) return '';
  if (!continuation.available) {
    return `<div class="goal-action-composer continuation-composer">
      <h3>🔒 ${esc(continuation.label)}</h3>
      <p>${esc(continuationUnavailableText(continuation))}</p>
      <button type="button" class="secondary" onclick="closeContinuationPanel()">Wróć</button>
    </div>`;
  }
  const departureSummary = (continuation.departure_summary || []).filter(item => item.known);
  const duration = Number(continuation.travel_minutes || 0);
  return `<div class="goal-action-composer continuation-composer">
    <h3>${esc(continuation.label)}</h3>
    <p>${esc(continuation.description || '')}</p>
    ${departureSummary.length ? `<div class="continuation-summary"><b>Ustalenia przed wymarszem</b>${departureSummary.map(item => `<span>• ${esc(item.label)}</span>`).join('')}</div>` : ''}
    <div class="flow-note">Przejście do kolejnej lokacji zajmie ${esc(duration)} min. Nie wymaga wyboru tempa ani rzutu podróży.</div>
    <div class="row"><button type="button" onclick="submitContinuation()">Wyrusz</button><button type="button" class="secondary" onclick="closeContinuationPanel()">Anuluj</button></div>
  </div>`;
}
function continuationPaceMinutes(baseMinutes, pace) {
  if (pace === 'fast') return Math.ceil(Number(baseMinutes || 0) * 3 / 4);
  if (pace === 'slow') return Math.ceil(Number(baseMinutes || 0) * 4 / 3);
  return Number(baseMinutes || 0);
}
function continuationArrivalTime(durationMinutes) {
  const clock = (state.flow && state.flow.clock) || {};
  const start = Number(clock.hour || 0) * 60 + Number(clock.minute || 0);
  const total = (start + Number(durationMinutes || 0)) % (24 * 60);
  const hour = Math.floor(total / 60);
  const minute = total % 60;
  return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
}
function continuationScheduleLabel(baseMinutes, totalMinutes) {
  const delta = Number(totalMinutes || 0) - Number(baseMinutes || 0);
  if (delta < 0) return `wcześnie (${Math.abs(delta)} min zysku)`;
  if (delta > 0) return `późno (${delta} min opóźnienia)`;
  return 'o czasie';
}
function continuationNavigationModifier(actor, ability, skill) {
  const score = Number(((actor || {}).ability_scores || {})[ability] || 10);
  let modifier = Math.floor((score - 10) / 2);
  const proficiencies = (actor || {}).proficiencies || {};
  if ((proficiencies.expertise || []).includes(skill)) modifier += Number(actor.proficiency_bonus || 0) * 2;
  else if ((proficiencies.skills || []).includes(skill)) modifier += Number(actor.proficiency_bonus || 0);
  return modifier;
}
function continuationUnavailableText(continuation) {
  const locations = (state.flow && state.flow.available_locations) || [];
  const departure = locations.find(zone => String(zone.id) === String(continuation.departure_zone_id));
  if (continuation.missing_flags && continuation.missing_flags.length) {
    return continuation.unavailable_hint || 'Dokończcie przygotowania fabularne przed wymarszem.';
  }
  if (continuation.requires_departure_zone) {
    return `Wyruszyć można z lokacji „${departure ? departure.name : continuation.departure_zone_id}”.`;
  }
  return continuation.unavailable_hint || 'Ta droga nie jest jeszcze dostępna.';
}
function interactionGoalsHtml() {
  if (state.trade) return tradePanelHtml();
  if (downtimePanelOpen && state.downtime) return downtimePanelHtml();
  if (
    state.playground
    && state.current_zone
    && ['control_room', 'combat_arena'].includes(state.current_zone.id)
    && !state.playground.trial_active
  ) {
    return playgroundChatControlsHtml();
  }
  const boardToolbar = boardChoiceToolbarHtml();
  const boardInteraction = boardInteractionState();
  if (
    boardInteraction
    && boardInteraction.mode === 'navigation'
    && state.flow.stage === 'location_active'
    && !state.active_point
  ) {
    return `${boardToolbar}${navigationChoicesHtml()}`;
  }
  const goals = currentInteractionGoals();
  const pointCards = currentInteractionPointCards();
  const hasDowntime = Boolean(state.downtime && !state.active_point);
  const zoneOptions = !state.active_point ? ((state.flow && state.flow.zone_options) || []) : [];
  const continuation = !state.active_point && state.flow ? state.flow.continuation : null;
  const hasContinuation = Boolean(continuation);
  const auxiliaryPads = ((boardInteractionState() || {}).pads || []).filter(
    pad => ['short_rest', 'long_rest', 'search'].includes(pad.action_kind)
  );
  const exitPad = ((boardInteractionState() || {}).pads || []).find(
    pad => pad.action_kind === 'exit'
  ) || null;
  const goalNumpadChoices = goals.slice(0, 9).map((goal, index) => {
    const pad = boardPadFor('goal', goal.id);
    const stableSymbol = String((pad && pad.symbol) || '');
    return {
      goal,
      pad,
      numpadKey: /^[1-9]$/.test(stableSymbol) ? Number(stableSymbol) : (goal.slot || index + 1),
    };
  });
  const occupiedGoalNumpadKeys = new Set(
    goalNumpadChoices.map(choice => choice.numpadKey)
  );
  if ((!goals.length && !pointCards.length && !hasDowntime && !zoneOptions.length && !hasContinuation && !auxiliaryPads.length && !exitPad && !boardToolbar) || state.pending || (state.required_rolls || []).length || resultAck) return '';
  const selected = goals.find(goal => goal.id === selectedInteractionGoalId) || null;
  if (selected?.read_only) return `${boardToolbar}${briefingRecapHtml(selected)}`;
  const selectedZoneOption = zoneOptions.find(option => option.id === selectedZoneOptionId) || null;
  const selectedParticipants = selected ? selectedGoalCheckParticipants(selected) : null;
  const participantsReady = Boolean(
    selected
    && (
      ['no_actor', 'whole_party'].includes(selectedParticipants)
      || (
        selectedParticipants
        && selectedInteractionActorIds.length > 0
      )
    )
  );
  const actionSourceReady = Boolean(
    selected
    && (
      !selected.source_required
      || selectedInteractionActionSourceId
    )
  );
  const socialSkillLabels = {
    persuasion: 'Perswazja',
    deception: 'Oszustwo',
    intimidation: 'Zastraszanie',
  };
  const socialSkillOptions = selected ? (selected.social_skill_options || []) : [];
  const socialFlow = Boolean(selected && socialSkillOptions.length);
  const socialStep = !participantsReady
    ? 'participants'
    : interactionComposerStep === 'description'
      ? 'description'
      : 'approach';
  const descriptionMode = selected ? (selected.description_mode || 'required') : 'required';
  return `
    ${boardToolbar}
    <div class="interaction-goals-head">
      <b>${continuationPanelOpen ? 'Wymarsz drużyny' : selected || selectedZoneOption ? 'Wybrane działanie' : 'Co chcecie zrobić?'}</b>
      <span>${continuationPanelOpen
        ? 'Ustalcie tempo, prowadzącego i wynik nawigacji.'
        : selected
        ? descriptionMode === 'none'
          ? selectedParticipants === 'no_actor'
            ? 'To wspólna decyzja drużyny. Wybór bohatera nie jest wymagany.'
            : 'Wybierzcie wykonawcę i potrzebne źródło. Opis nie jest wymagany.'
          : esc(selected.followup_prompt)
        : selectedZoneOption
          ? 'Wybierzcie postać i wykonajcie wymagane kroki.'
          : 'Wybierzcie działanie. Formularz pokaże tylko kroki, które mają znaczenie.'}</span>
    </div>
    ${selectedZoneOption || selected || continuationPanelOpen ? '' : `<div class="interaction-goal-grid">
      ${pointCards.map(point => {
        const pad = boardPadFor('point', point.id);
        return `
        <button type="button" class="interaction-goal-card npc-point-card${String(point.id) === String(selectedPointPreviewId) ? ' selected' : ''}${pad ? ' board-linked-tile' : ''}"${pad ? ` style="${boardPadCss(pad)}"` : ''}
          onclick="selectPointPreview('${esc(point.id)}')">
          ${boardPadBadge(pad)}
          ${scenarioInteractionImage(point.image, point.name)}
          <b>${esc(point.interaction_label || point.name)}</b>
          <span>${esc(point.description || 'Podejdźcie i rozpocznijcie rozmowę.')}</span>
          <small>${point.has_merchant ? 'Handel' : 'Interakcja z NPC'}</small>
        </button>`;
      }).join('')}
      ${hasDowntime ? `
        <button type="button" class="interaction-goal-card${boardPadFor('panel', 'downtime') ? ' board-linked-tile' : ''}" style="${boardPadCss(boardPadFor('panel', 'downtime'))}" onclick="openDowntimePanel()">
          ${boardPadBadge(boardPadFor('panel', 'downtime'))}
          <b>Rzemiosło w downtime</b>
          <span>Wykorzystaj warsztat, materiały i pełne dni pracy, aby stworzyć trwały przedmiot.</span>
          <small>${esc((state.downtime.recipes || []).map(recipe => recipe.workshop_label).join(' · '))}</small>
        </button>
      ` : ''}
      ${zoneOptionCardsHtml(zoneOptions)}
      ${hasContinuation && continuation.available ? `
        <button type="button" class="interaction-goal-card continuation-card${boardPadFor('panel', 'continuation') ? ' board-linked-tile' : ''}" style="${boardPadCss(boardPadFor('panel', 'continuation'))}" onclick="openContinuationPanel()">
          ${boardPadBadge(boardPadFor('panel', 'continuation'))}
          <b>${esc(continuation.label)}</b>
          <span>${esc(continuation.description || 'Wyruszcie do kolejnej sceny.')}</span>
          <small>Dalsza podróż · ${esc(continuation.travel_minutes || 0)} min w normalnym tempie</small>
        </button>
      ` : hasContinuation ? `
        <button type="button" class="interaction-goal-card continuation-card locked${boardPadFor('panel', 'continuation') ? ' board-linked-tile' : ''}" style="${boardPadCss(boardPadFor('panel', 'continuation'))}" onclick="openContinuationPanel()">
          ${boardPadBadge(boardPadFor('panel', 'continuation'))}
          <b>🔒 ${esc(continuation.label)}</b>
          <span>${esc(continuationUnavailableText(continuation))}</span>
          <small>${continuation.requires_departure_zone ? 'Najpierw dotrzyjcie do lokacji wyjścia' : 'Brakuje przygotowania fabularnego'}</small>
        </button>
      ` : ''}
      ${auxiliaryPads.map(pad => `
        <button type="button" class="interaction-goal-card board-linked-tile" style="${boardPadCss(pad)}"
          onclick="${pad.action_kind === 'short_rest'
            ? 'startShortRest()'
            : pad.action_kind === 'long_rest'
            ? 'completeLongRest()'
            : `startExplorationSearch('${esc((boardInteractionState() || {}).selected_actor_id || '')}')`}">
          ${boardPadBadge(pad)}
          <b>${esc(pad.label)}</b>
          <span>${esc(pad.description || '')}</span>
          <small>${['short_rest','long_rest'].includes(pad.action_kind) ? 'Odpoczynek drużyny' : 'Test wybranej postaci'}</small>
        </button>
      `).join('')}
      ${goals.length ? `<div class="interaction-numpad-grid">
      ${goalNumpadChoices.map(({goal, pad, numpadKey}) => {
        return `
        <button type="button" class="interaction-goal-card interaction-numpad-choice${goal.read_only ? ' topic-reviewed' : ''}${goal.id === selectedInteractionGoalId ? ' selected' : ''}${pad ? ' board-linked-tile' : ''}" data-numpad-key="${numpadKey}"${pad ? ` style="${boardPadCss(pad)}"` : ''}
          onclick="selectInteractionGoal('${esc(goal.id)}')">
          ${numpadChoiceBadge(numpadKey)}
          ${scenarioInteractionImage(goal.image, goal.label)}
          <b>${esc(goal.label)}</b>
          <span>${esc(goal.description)}</span>
          <small>${esc(goal.badge ? `${goal.topic_status || goal.badge}${goal.read_only ? ' · przypomnij' : ''}` : `${interactionContractLabel(goal)} · ${goalParticipantLabel(goal)}`)}</small>
        </button>`;
      }).join('')}
      ${Array.from({length: 9}, (_unused, offset) => offset + 1).filter(
        key => !occupiedGoalNumpadKeys.has(key)
      ).map(key => {
        return `<span class="interaction-numpad-empty" data-numpad-key-slot="${key}" aria-hidden="true">${numpadChoiceBadge(key)}</span>`;
      }).join('')}
      </div>${numpadChoiceHint(goalNumpadChoices.map(choice => choice.numpadKey), 'wybierz działanie')}` : ''}
      ${exitPad && !state.active_point ? `
        <button type="button" class="interaction-goal-card board-linked-tile system-exit-card${exitPad.enabled === false ? ' locked' : ''}" style="${boardPadCss(exitPad)}"
          ${exitPad.enabled === false ? 'disabled' : 'onclick="leaveChatInstance()"'}>
          ${boardPadBadge(exitPad)}
          <b>${esc(exitPad.label)}</b>
          <span>${esc(exitPad.enabled === false ? (exitPad.unavailable_reason || 'Najpierw zakończ bieżące działanie.') : exitPad.description || '')}</span>
          <small>${exitPad.enabled === false ? 'Wyjście chwilowo zablokowane' : 'Systemowe wyjście'}</small>
        </button>` : ''}
    </div>`}
    ${zoneOptionComposerHtml(selectedZoneOption)}
    ${simpleContinuationPanelHtml(continuation)}
    ${socialFlow ? socialInteractionProgressHtml(socialStep, selected) : ''}
    ${selected && (!socialFlow || socialStep === 'participants') ? interactionParticipantPickerHtml(selected) : ''}
    ${selected && participantsReady && (!socialFlow || socialStep === 'description') ? interactionActionSourcePickerHtml(selected) : ''}
    ${socialFlow && socialStep === 'approach' ? interactionSocialApproachHtml(socialSkillOptions, socialSkillLabels, selected) : ''}
    ${selected && !participantsReady ? `<p class="flow-note">Najpierw wskażcie postać. Potem opiszecie jej podejście.</p>` : ''}
    ${selected && participantsReady && !actionSourceReady ? `<p class="flow-note">Wybierzcie wymagany czar, przedmiot albo narzędzie. Potem opiszcie jego użycie.</p>` : ''}
    ${selected && participantsReady && actionSourceReady && (!socialFlow || socialStep === 'description') && !interactionGoalExecutesImmediately(selected) ? `<div class="goal-action-composer">
      ${briefingArgumentHelpHtml(selected)}
      ${selected.confirmation_note ? `<p class="flow-note">${esc(selected.confirmation_note)}</p>` : ''}
      ${selected.resolution_mode === 'llm_rubric' && (selected.llm_rubric || []).length ? `
        <div class="flow-note">
          <b>Na co zwróci uwagę MG:</b>
          <ul>${selected.llm_rubric.map(criterion => `<li>${esc(criterion)}</li>`).join('')}</ul>
        </div>
      ` : ''}
      ${descriptionMode === 'none' ? '' : `
        <label for="goal-action"><b>${descriptionMode === 'required' ? 'Jak to robicie?' : 'Opcjonalnie: jak to robicie?'}</b>
          <span>${descriptionMode === 'required'
            ? esc(selected.followup_prompt || 'Opiszcie metodę działania.')
            : 'Opis może wpłynąć tylko na dozwolone przez scenę premie lub konsekwencje. Możecie zostawić pole puste.'}</span>
        </label>
        <textarea id="goal-action" oninput="interactionDescriptionDraft = this.value" placeholder="${descriptionMode === 'required' ? esc(selected.followup_prompt || 'Opiszcie metodę działania...') : 'Opcjonalny opis metody…'}">${esc(interactionDescriptionDraft)}</textarea>
      `}
      <div class="row">
        <button type="button" onclick="sendGoalAction()">${descriptionMode === 'optional' ? 'Wykonaj bez opisu lub z opisem' : selected.resolution_mode === 'automatic' ? 'Wykonaj' : selected.resolution_mode === 'llm_rubric' ? 'Przekaż opis MG' : socialFlow ? 'Przejdź do warunków testu' : 'Przejdź dalej'}</button>
        ${socialFlow ? '<button type="button" class="secondary" onclick="returnToSocialApproach()">Wstecz</button>' : ''}
        <button type="button" class="secondary" onclick="cancelInteractionGoal()">Anuluj wybór</button>
      </div>
    </div>` : ''}`;
}

function socialInteractionProgressHtml(step, goal) {
  const fixedActor = Boolean(goal && goal.assigned_actor_id);
  const steps = fixedActor
    ? [['approach', '1. Podejście'], ['description', '2. Opis']]
    : [['participants', '1. Bohater'], ['approach', '2. Podejście'], ['description', '3. Opis']];
  return `<div class="social-flow-progress" aria-label="Etapy testu społecznego">
    ${steps.map(([id, label]) => `<span class="${id === step ? 'active' : ''}">${esc(label)}</span>`).join('')}
  </div>`;
}

function interactionSocialApproachHtml(options, labels, goal) {
  const actor = (state.actors || []).find(item => String(item.id) === String(selectedInteractionActorIds[0] || ''));
  const descriptions = {
    persuasion: 'Przedstawcie szczere argumenty, wspólny interes albo rozsądną prośbę.',
    deception: 'Zbudujcie wiarygodne kłamstwo lub ukryjcie niewygodną część prawdy.',
    intimidation: 'Wywrzyjcie presję groźbą, przewagą albo pokazem zdecydowania.',
  };
  return `<div class="interaction-participants social-approach-step">
    <b>Jak chcecie wpłynąć na NPC?</b>
    <span>${actor ? `Test wykona ${esc(actor.name)}. ` : ''}Ten wybór należy do graczy i ustali umiejętność testu Charyzmy.</span>
    <div class="social-approach-grid">
      ${options.slice(0, 9).map((skill, index) => `<button type="button" class="social-approach-card" data-numpad-key="${index + 1}" onclick="selectInteractionSocialSkill('${esc(skill)}')">
        ${numpadChoiceBadge(index + 1)}
        <b>${esc(labels[skill] || skill)}</b>
        <span>${esc(descriptions[skill] || 'Opiszcie, jak wywieracie wpływ na rozmówcę.')}</span>
        ${goal.negotiation_targets ? `<small>${esc(goal.negotiation_targets.filter(target => target.skill === skill).map(target => target.label).join(' · '))}</small>` : ''}
      </button>`).join('')}
    </div>
    ${numpadChoiceHint(options.length, 'wybierz podejście')}
    <div class="row">
      ${goal && goal.assigned_actor_id ? '' : '<button type="button" class="secondary" onclick="returnToInteractionParticipants()">Wstecz</button>'}
      <button type="button" class="secondary" onclick="cancelInteractionGoal()">Anuluj wybór</button>
    </div>
  </div>`;
}

function selectInteractionSocialSkill(skill) {
  const goal = currentInteractionGoals().find(item => item.id === selectedInteractionGoalId);
  if (!goal || !(goal.social_skill_options || []).includes(skill)) return;
  selectedSocialSkill = skill;
  interactionComposerStep = 'description';
  const panel = document.getElementById('interaction-goals');
  if (panel) panel.innerHTML = interactionGoalsHtml();
  const input = document.getElementById('goal-action');
  if (input) input.focus();
}

function returnToSocialApproach() {
  interactionComposerStep = 'approach';
  const panel = document.getElementById('interaction-goals');
  if (panel) panel.innerHTML = interactionGoalsHtml();
}

function returnToInteractionParticipants() {
  interactionComposerStep = 'participants';
  selectedSocialSkill = null;
  const panel = document.getElementById('interaction-goals');
  if (panel) panel.innerHTML = interactionGoalsHtml();
}
function playgroundOptionsHtml(prefix) {
  const config = (state.playground && state.playground.config) || {};
  const audit = (state.playground && state.playground.audit) || {};
  const auditCases = audit.cases || [];
  const progress = audit.progress || {};
  const selected = (value, expected) => String(value) === String(expected) ? ' selected' : '';
  return `
    <div class="flow-note">
      <b>Audyt Areny: ${esc(progress.resolved || 0)}/${esc(progress.total || 0)} (${esc(progress.percent || 0)}%)</b>
      <progress max="${esc(progress.total || 1)}" value="${esc(progress.resolved || 0)}"></progress>
      <span>Automatycznie: ${esc(progress.tested || 0)} · pominięte z uzasadnieniem: ${esc(progress.skipped || 0)}</span>
    </div>
    <label>Odtwarzalny przypadek audytu
      <select id="${prefix}-audit-case" onchange="applyPlaygroundAuditCase('${prefix}', this.value)">
        <option value="">— wybierz sprawdzony przypadek —</option>
        ${auditCases.map(item => `<option value="${esc(item.id)}"${selected(selectedPlaygroundAuditCaseId, item.id)}>✅ ${esc(item.label)}</option>`).join('')}
      </select>
    </label>
    <div id="${prefix}-audit-case-details" class="flow-note"></div>
    <label>Profil próby
      <select id="${prefix}-preset" onchange="applyPlaygroundPreset('${prefix}')">
        <option value="standard">Standardowy cel</option>
        <option value="armored">Opancerzony cel</option>
        <option value="resistant">Odporność na obrażenia</option>
        <option value="immune">Niewrażliwość na obrażenia</option>
        <option value="vulnerable">Podatność na obrażenia</option>
        <option value="condition">Odporność na stan</option>
        <option value="undead">Nieumarły cel</option>
        <option value="swarm">Grupa celów obszarowych</option>
      </select>
    </label>
    <div class="form-grid">
      <label>Liczba manekinów
        <input id="${prefix}-dummy-count" type="number" min="1" max="6" value="${esc(config.dummy_count ?? 3)}">
      </label>
      <label>KP
        <input id="${prefix}-ac" type="number" min="5" max="30" value="${esc(config.armor_class ?? 12)}">
      </label>
      <label>PW każdego celu
        <input id="${prefix}-hp" type="number" min="1" max="999" value="${esc(config.hit_points ?? 20)}">
      </label>
      <label>Szybkość
        <input id="${prefix}-speed" type="number" min="0" max="60" step="5" value="${esc(config.speed_feet ?? 10)}">
      </label>
      <label>Wszystkie cechy
        <input id="${prefix}-ability-score" type="number" min="1" max="30" value="${esc(config.ability_score ?? 10)}">
      </label>
    </div>
    <details>
      <summary>Odporności i typ celu</summary>
      <label>Typ stworzenia
        <select id="${prefix}-creature-type">
          <option value="construct"${selected(config.creature_type, 'construct')}>Konstrukt</option>
          <option value="humanoid"${selected(config.creature_type, 'humanoid')}>Humanoid</option>
          <option value="undead"${selected(config.creature_type, 'undead')}>Nieumarły</option>
          <option value="beast"${selected(config.creature_type, 'beast')}>Bestia</option>
          <option value="fey"${selected(config.creature_type, 'fey')}>Fey</option>
          <option value="fiend"${selected(config.creature_type, 'fiend')}>Czart</option>
          <option value="dragon"${selected(config.creature_type, 'dragon')}>Smok</option>
          <option value="monstrosity"${selected(config.creature_type, 'monstrosity')}>Monstrualność</option>
          <option value="plant"${selected(config.creature_type, 'plant')}>Roślina</option>
        </select>
      </label>
      <label>Reakcja na obrażenia
        <select id="${prefix}-affinity">
          <option value="none"${selected(config.affinity, 'none')}>Brak</option>
          <option value="resistance"${selected(config.affinity, 'resistance')}>Odporność — połowa</option>
          <option value="immunity"${selected(config.affinity, 'immunity')}>Niewrażliwość — 0</option>
          <option value="vulnerability"${selected(config.affinity, 'vulnerability')}>Podatność — podwójne</option>
        </select>
      </label>
      <label>Typ obrażeń
        <select id="${prefix}-damage-type">
          ${[
            ['fire','Ogień'],['cold','Zimno'],['lightning','Błyskawice'],
            ['poison','Trucizna'],['necrotic','Nekrotyczne'],['radiant','Promieniste'],
            ['force','Moc'],['psychic','Psychiczne'],['slashing','Cięte'],
            ['piercing','Kłute'],['bludgeoning','Obuchowe']
          ].map(([value, label]) => `<option value="${value}"${selected(config.damage_type, value)}>${label}</option>`).join('')}
        </select>
      </label>
      <label>Odporność na stan
        <select id="${prefix}-condition-immunity">
          ${[
            ['','Brak'],['charmed','Zauroczony'],['frightened','Przerażony'],
            ['poisoned','Zatruty'],['prone','Powalony'],['restrained','Unieruchomiony'],
            ['stunned','Ogłuszony'],['paralyzed','Sparaliżowany'],['unconscious','Nieprzytomny']
          ].map(([value, label]) => `<option value="${value}"${selected(config.condition_immunity, value)}>${label}</option>`).join('')}
        </select>
      </label>
    </details>`;
}
function applyPlaygroundAuditCase(prefix, caseId) {
  selectedPlaygroundAuditCaseId = caseId || '';
  const auditCases = (((state || {}).playground || {}).audit || {}).cases || [];
  const auditCase = auditCases.find(item => item.id === caseId);
  const details = document.getElementById(`${prefix}-audit-case-details`);
  if (!auditCase) {
    if (details) details.innerHTML = '';
    return;
  }
  const config = auditCase.arena_config || {};
  const mappings = {
    'dummy-count': config.dummy_count,
    ac: config.armor_class,
    hp: config.hit_points,
    speed: config.speed_feet,
    'ability-score': config.ability_score,
    'creature-type': config.creature_type,
    affinity: config.affinity,
    'damage-type': config.damage_type,
    'condition-immunity': config.condition_immunity
  };
  Object.entries(mappings).forEach(([field, value]) => setPlaygroundField(`${prefix}-${field}`, value));
  if (details) {
    details.innerHTML = `
      <b>${esc(auditCase.label)} · ${esc(auditCase.module)}</b>
      <ol>${(auditCase.manual_steps || []).map(step => `<li>${esc(step)}</li>`).join('')}</ol>
      <b>Oczekiwany rezultat</b>
      <ul>${(auditCase.expected_results || []).map(step => `<li>${esc(step)}</li>`).join('')}</ul>
      ${auditCase.notes ? `<span>${esc(auditCase.notes)}</span>` : ''}`;
  }
}
function playgroundChatControlsHtml() {
  return `
    <div class="conversation-system-card chat-flow-entry playground-chat-card">
      <div class="interaction-goals-head">
        <div>
          <b>Przygotuj próbę areny</b>
          <span>Najpierw ustaw cele. Po zatwierdzeniu gra przejdzie do zwykłego setupu figurek, inicjatywy i walki sterowanej planszą.</span>
        </div>
      </div>
      ${playgroundOptionsHtml('arena')}
      <div class="flow-note">
        <b>Co wydarzy się dalej?</b>
        Manekiny pojawią się jako fizyczne cele. Gra podświetli ich pola podczas setupu,
        a ataki, czary i obszary będziecie wybierać na planszy.
      </div>
      <div class="row conversation-system-actions">
        <button type="button" onclick="configurePlaygroundTrial('arena')">Ustaw manekiny i rozpocznij setup</button>
        <button type="button" class="secondary" onclick="startPlaygroundPreset('arena', 'swarm')">Szybki test obszarowy</button>
      </div>
    </div>`;
}
function interactionContractLabel(goal) {
  const resolution = {
    automatic: 'Bez rzutu',
    check: 'Test D&D',
    llm_rubric: 'Ocena opisu przez MG',
    conversation: 'Rozmowa',
  }[goal.resolution_mode] || 'Interakcja';
  const description = {
    none: 'bez opisu',
    optional: 'opis opcjonalny',
    required: 'opis wymagany',
  }[goal.description_mode] || 'opis wymagany';
  return `${resolution}, ${description}`;
}
function tradeMoneyLabel(totalCp) {
  let remaining = Math.max(0, Math.floor(Number(totalCp || 0)));
  const pp = Math.floor(remaining / 1000); remaining %= 1000;
  const gp = Math.floor(remaining / 100); remaining %= 100;
  const sp = Math.floor(remaining / 10); remaining %= 10;
  return [[pp, 'pp'], [gp, 'gp'], [sp, 'sp'], [remaining, 'cp']]
    .filter(entry => entry[0] > 0)
    .map(entry => `${entry[0]} ${entry[1]}`)
    .join(', ') || '0 cp';
}
function activeDowntimeActor(downtime) {
  const actors = downtime.actors || [];
  if (!actors.some(actor => String(actor.id) === String(selectedDowntimeActorId))) {
    selectedDowntimeActorId = actors.length ? String(actors[0].id) : '';
  }
  return actors.find(actor => String(actor.id) === String(selectedDowntimeActorId)) || null;
}
function downtimePanelHtml() {
  const downtime = state.downtime || {};
  const actor = activeDowntimeActor(downtime);
  if (!actor) return '<p>Brak postaci zdolnej do pracy.</p>';
  const actorOptions = (downtime.actors || []).map(candidate => `
    <option value="${esc(candidate.id)}"${String(candidate.id) === String(actor.id) ? ' selected' : ''}>${esc(candidate.name)}</option>
  `).join('');
  const recipes = (downtime.recipes || []).map(recipe => {
    const availability = (recipe.availability || []).find(
      entry => String(entry.actor_id) === String(actor.id)
    ) || {available: false, reason: 'Ta postać nie może wykonać receptury.'};
    return `
      <div class="status-item">
        <b>${esc(recipe.label)}</b>
        <span>${esc(recipe.description || (recipe.product || {}).description || '')}</span>
        <span><b>Rezultat:</b> ${esc((recipe.product || {}).name)} ×${esc((recipe.product || {}).quantity)}</span>
        <span><b>Materiały:</b> ${esc(tradeMoneyLabel(recipe.material_cost_cp))} · <b>praca:</b> ${esc(recipe.work_days)} dzień (${esc(recipe.time_cost_minutes / 60)} godz.)</span>
        <span><b>Warsztat:</b> ${esc(recipe.workshop_label)} · <b>biegłość i narzędzia:</b> ${esc(recipe.required_tool_id)}</span>
        ${availability.available ? '' : `<span class="muted">${esc(availability.reason)}</span>`}
        <button type="button" onclick="completeDowntimeCrafting('${esc(recipe.id)}')"
          ${availability.available ? '' : 'disabled'}>Rozpocznij i ukończ pracę</button>
      </div>
    `;
  }).join('') || '<p class="muted">Brak dostępnych receptur.</p>';
  return `
    <div class="trade-panel">
      <div class="interaction-goals-head">
        <b>Rzemiosło w downtime</b>
        <span>Praca zużywa materiały, przesuwa wspólny zegar i daje trwały przedmiot.</span>
      </div>
      <label>Pracująca postać:
        <select onchange="selectDowntimeActor(this.value)">${actorOptions}</select>
      </label>
      <span><b>Portfel:</b> ${esc(tradeMoneyLabel((actor.currency || {}).total_cp))}</span>
      <div class="status-list">${recipes}</div>
      <button type="button" class="secondary" onclick="closeDowntimePanel()">Wróć</button>
    </div>
  `;
}
function openDowntimePanel() {
  downtimePanelOpen = true;
  pauseBoardForScreenInput();
  document.getElementById('interaction-goals').innerHTML = interactionGoalsHtml();
}
function closeDowntimePanel() {
  downtimePanelOpen = false;
  api('/api/board/clear-selection', {}, 'Wracam do wyboru działania...');
}
function selectDowntimeActor(actorId) {
  selectedDowntimeActorId = String(actorId || '');
  document.getElementById('interaction-goals').innerHTML = interactionGoalsHtml();
}
function completeDowntimeCrafting(recipeId) {
  const downtime = state.downtime || {};
  const actor = activeDowntimeActor(downtime);
  const recipe = (downtime.recipes || []).find(
    candidate => String(candidate.id) === String(recipeId)
  );
  if (!actor || !recipe) return;
  const prompt = `${actor.name} wykona: ${(recipe.product || {}).name}. ` +
    `Koszt materiałów: ${tradeMoneyLabel(recipe.material_cost_cp)}, czas: ${recipe.time_cost_minutes / 60} godz. Kontynuować?`;
  if (!window.confirm(prompt)) return;
  api('/api/downtime/crafting/complete', {
    actor_id: actor.id,
    recipe_id: recipe.id,
  }, 'Rozliczam dzień pracy...');
}
function activeTradeActor(trade) {
  const actors = trade.actors || [];
  if (!actors.some(actor => String(actor.id) === String(selectedTradeActorId))) {
    selectedTradeActorId = actors.length ? String(actors[0].id) : '';
  }
  return actors.find(actor => String(actor.id) === String(selectedTradeActorId)) || null;
}
function tradePanelHtml() {
  const trade = state.trade || {};
  const actors = trade.actors || [];
  const actor = activeTradeActor(trade);
  if (!actor) return '<p>Brak postaci zdolnej do handlu.</p>';
  const actorOptions = actors.map(candidate => `
    <option value="${esc(candidate.id)}"${String(candidate.id) === String(actor.id) ? ' selected' : ''}>${esc(candidate.name)}</option>
  `).join('');
  const stock = (trade.stock || []).map(item => tradeItemRowHtml('buy', item, actor, trade)).join('')
    || '<p class="muted">Sprzedawca nie ma już towaru.</p>';
  const sellable = (actor.sellable_items || []).map(item => tradeItemRowHtml('sell', item, actor, trade)).join('')
    || '<p class="muted">Ta postać nie ma przedmiotów możliwych do sprzedaży.</p>';
  return `
    <div class="trade-panel">
      <div class="interaction-goals-head">
        <b>${esc(trade.merchant_name || 'Sprzedawca')}</b>
        <span>Sprzedawca odkupuje przedmioty za ${esc(trade.buyback_percent)}% wartości katalogowej.</span>
      </div>
      <div class="row">
        <label>Handlująca postać:
          <select onchange="selectTradeActor(this.value)">${actorOptions}</select>
        </label>
        <span><b>Portfel:</b> ${esc(tradeMoneyLabel((actor.currency || {}).total_cp))}</span>
        <span><b>Udźwig:</b> ${esc((actor.carrying || {}).weight_lb)} / ${esc((actor.carrying || {}).capacity_lb)} lb</span>
        <span><b>Kasa kupca:</b> ${esc(tradeMoneyLabel((trade.currency || {}).total_cp))}</span>
      </div>
      <h4>Kup</h4>
      <div class="status-list">${stock}</div>
      <h4>Sprzedaj</h4>
      <div class="status-list">${sellable}</div>
      <button type="button" class="secondary" onclick="selectPoint(&quot;&quot;)">Odejdź od stoiska</button>
    </div>
  `;
}
function tradeItemRowHtml(direction, item, actor, trade) {
  const inputId = `trade-${direction}-${item.id}`;
  const quoteId = `${inputId}-quote`;
  const actionLabel = direction === 'buy' ? 'Kup' : 'Sprzedaj';
  const unitPrice = Number(item.unit_price_cp || 0);
  return `
    <div class="status-item">
      <b>${esc(item.name)} ×${esc(item.quantity)}</b>
      <span>Cena za sztukę: ${esc(tradeMoneyLabel(unitPrice))} · masa ${esc(item.weight_lb)} lb</span>
      <div class="row">
        <label>Ilość:
          <input id="${esc(inputId)}" type="number" min="1" max="${esc(item.quantity)}" value="1"
            oninput="updateTradeQuote('${direction}', '${esc(item.id)}')">
        </label>
        <button onclick="${direction === 'buy' ? 'buyTradeItem' : 'sellTradeItem'}('${esc(item.id)}')">${actionLabel}</button>
      </div>
      <span id="${esc(quoteId)}" class="muted">${esc(tradeQuoteText(direction, item, 1, actor, trade))}</span>
    </div>
  `;
}
function tradeQuoteText(direction, item, quantity, actor, trade) {
  const count = Math.max(0, Number(quantity || 0));
  const total = count * Number(item.unit_price_cp || 0);
  const mass = count * Number(item.weight_lb || 0);
  const actorCp = Number((actor.currency || {}).total_cp || 0);
  const currentWeight = Number((actor.carrying || {}).weight_lb || 0);
  if (direction === 'buy') {
    const afterCp = actorCp - total;
    const afterWeight = currentWeight + mass;
    const capacity = Number((actor.carrying || {}).capacity_lb || 0);
    const warning = afterCp < 0
      ? ' · brak środków'
      : afterWeight > capacity
        ? ' · przekroczony udźwig'
        : '';
    return `Razem ${tradeMoneyLabel(total)} · portfel po zakupie ${tradeMoneyLabel(Math.max(0, afterCp))} · masa po zakupie ${afterWeight.toFixed(3)} lb${warning}`;
  }
  const merchantAfter = Number((trade.currency || {}).total_cp || 0) - total;
  return `Razem ${tradeMoneyLabel(total)} · portfel po sprzedaży ${tradeMoneyLabel(actorCp + total)} · masa po sprzedaży ${Math.max(0, currentWeight - mass).toFixed(3)} lb${merchantAfter < 0 ? ' · kupiec nie ma dość monet' : ''}`;
}
function selectTradeActor(actorId) {
  selectedTradeActorId = String(actorId || '');
  const panel = document.getElementById('interaction-goals');
  if (panel) panel.innerHTML = interactionGoalsHtml();
}
function updateTradeQuote(direction, itemId) {
  const trade = state.trade || {};
  const actor = activeTradeActor(trade);
  if (!actor) return;
  const items = direction === 'buy' ? (trade.stock || []) : (actor.sellable_items || []);
  const item = items.find(candidate => String(candidate.id) === String(itemId));
  const input = document.getElementById(`trade-${direction}-${itemId}`);
  const quote = document.getElementById(`trade-${direction}-${itemId}-quote`);
  if (!item || !input || !quote) return;
  quote.textContent = tradeQuoteText(direction, item, Number(input.value || 0), actor, trade);
}
function buyTradeItem(itemId) {
  const trade = state.trade || {};
  const actor = activeTradeActor(trade);
  const input = document.getElementById(`trade-buy-${itemId}`);
  if (!actor || !input) return;
  api('/api/trade/buy', {
    merchant_id: trade.merchant_id,
    actor_id: actor.id,
    item_id: itemId,
    quantity: Number(input.value || 0),
  }, 'Finalizuję zakup...');
}
function sellTradeItem(itemId) {
  const trade = state.trade || {};
  const actor = activeTradeActor(trade);
  const input = document.getElementById(`trade-sell-${itemId}`);
  if (!actor || !input) return;
  api('/api/trade/sell', {
    merchant_id: trade.merchant_id,
    actor_id: actor.id,
    item_id: itemId,
    quantity: Number(input.value || 0),
  }, 'Finalizuję sprzedaż...');
}
function selectInteractionGoal(goalId) {
  const goal = currentInteractionGoals().find(item => item.id === goalId);
  if (!goal) return;
  if (selectedInteractionGoalId !== goalId) {
    selectedInteractionActorIds = [];
    selectedInteractionCheckParticipants = goal.participant_mode === 'must'
      ? goal.check_participants
      : null;
    selectedSocialSkill = null;
    interactionComposerStep = 'participants';
    interactionDescriptionDraft = '';
    selectedInteractionActionSourceId = null;
  }
  selectedInteractionGoalId = goalId;
  pauseBoardForScreenInput();
  if (goal.read_only) {
    const panel = document.getElementById('interaction-goals');
    if (panel) panel.innerHTML = interactionGoalsHtml();
    return;
  }
  prepareObviousInteractionChoices(goal);
  if ((goal.social_skill_options || []).length && selectedInteractionActorIds.length) {
    interactionComposerStep = 'approach';
  }
  if (interactionGoalExecutesImmediately(goal)) {
    sendGoalAction();
    return;
  }
  const panel = document.getElementById('interaction-goals');
  if (panel) panel.innerHTML = interactionGoalsHtml();
  const options = goal.allowed_check_participants || [goal.check_participants || 'single_actor'];
  const actors = (state.actors || []).filter(actor => !actor.defeated);
  const eligibleIds = new Set((goal.eligible_actor_ids || actors.map(actor => actor.id)).map(String));
  const eligible = actors.filter(actor => eligibleIds.has(String(actor.id)));
  if (!goal.assigned_actor_id && (options.includes('single_actor') || options.includes('lead_with_help')) && eligible.length > 1) {
    const panel = document.getElementById('interaction-goals');
    if (panel) panel.innerHTML = interactionGoalsHtml();
  } else {
    const input = document.getElementById('goal-action');
    if (input) input.focus();
  }
}

function interactionGoalExecutesImmediately(goal) {
  if (goal?.read_only || goal?.confirmation_note) return false;
  if (!goal || goal.description_mode !== 'none') return false;
  if ((goal.social_skill_options || []).length) return false;
  if ((goal.accepted_source_tags || []).length) {
    if (!goal.source_required || !selectedInteractionActionSourceId) return false;
  }
  if (goal.participant_mode !== 'must') return false;
  const participants = selectedGoalCheckParticipants(goal);
  if (!participants) return false;
  return ['no_actor', 'whole_party'].includes(participants)
    || selectedInteractionActorIds.length > 0;
}

function scheduleImmediateInteractionGoal(goal) {
  if (!interactionGoalExecutesImmediately(goal)) return false;
  const goalId = String(goal.id);
  window.setTimeout(() => {
    if (
      selectedInteractionGoalId === goalId
      && !state.pending
      && !(state.required_rolls || []).length
    ) sendGoalAction();
  }, 0);
  return true;
}
function cancelInteractionGoal() {
  selectedInteractionGoalId = null;
  selectedInteractionCheckParticipants = null;
  selectedInteractionActorIds = [];
  selectedSocialSkill = null;
  interactionComposerStep = 'participants';
  interactionDescriptionDraft = '';
  selectedInteractionActionSourceId = null;
  api('/api/board/clear-selection', {}, 'Wracam do wyboru działania...');
}
function checkParticipantLabel(mode) {
  if (mode === 'no_actor') return 'Decyzja drużyny';
  if (mode === 'whole_party') return 'Test grupowy';
  if (mode === 'lead_with_help') return 'Jedna postać z pomocą';
  return 'Jedna postać';
}
function goalParticipantLabel(goal) {
  const options = goal.allowed_check_participants || [goal.check_participants || 'single_actor'];
  if (goal.participant_mode === 'must' && goal.check_participants === 'no_actor') {
    return 'Decyzja drużyny';
  }
  if (goal.participant_mode === 'allow') return `Wybór: ${options.map(checkParticipantLabel).join(' / ')}`;
  return `Wymagany: ${checkParticipantLabel(goal.check_participants)}`;
}
function selectedGoalCheckParticipants(goal) {
  return goal.participant_mode === 'must'
    ? (goal.check_participants || 'single_actor')
    : selectedInteractionCheckParticipants;
}
function prepareObviousInteractionChoices(goal) {
  if (!goal) return;
  const participantOptions = goal.allowed_check_participants || [goal.check_participants || 'single_actor'];
  if (goal.participant_mode === 'must') {
    selectedInteractionCheckParticipants = goal.check_participants || participantOptions[0] || 'single_actor';
  } else if (!selectedInteractionCheckParticipants && participantOptions.length === 1) {
    selectedInteractionCheckParticipants = participantOptions[0];
  }
  if (goal.assigned_actor_id) {
    const assigned = (state.actors || []).find(actor => (
      String(actor.id) === String(goal.assigned_actor_id) && !actor.defeated
    ));
    selectedInteractionActorIds = assigned ? [String(assigned.id)] : [];
  } else if (['no_actor', 'whole_party'].includes(selectedInteractionCheckParticipants)) {
    selectedInteractionActorIds = [];
  } else if (!selectedInteractionActorIds.length) {
    const actors = (state.actors || []).filter(actor => !actor.defeated);
    const eligibleIds = new Set((goal.eligible_actor_ids || actors.map(actor => actor.id)).map(String));
    const eligible = actors.filter(actor => eligibleIds.has(String(actor.id)));
    if (eligible.length === 1) selectedInteractionActorIds = [String(eligible[0].id)];
  }
  if (goal.source_required && !selectedInteractionActionSourceId) {
    const leadId = selectedInteractionActorIds.length ? String(selectedInteractionActorIds[0]) : null;
    const available = (goal.action_sources || []).filter(source => (
      source.available
      && (!source.owner_actor_id || !leadId || String(source.owner_actor_id) === leadId)
    ));
    if (available.length === 1) selectedInteractionActionSourceId = available[0].id;
  }
}
function interactionParticipantPickerHtml(goal) {
  if (!state.active_challenge && !(state.active_point && state.active_point.npc)) return '';
  if (goal.assigned_actor_id) return '';
  const mode = selectedGoalCheckParticipants(goal);
  if (mode === 'no_actor') return '';
  const actors = state.actors || [];
  const options = goal.allowed_check_participants || [goal.check_participants || 'single_actor'];
  const singleAllowed = options.includes('single_actor');
  const helpAllowed = options.includes('lead_with_help');
  const wholePartyAllowed = options.includes('whole_party');
  const eligibleIds = new Set((goal.eligible_actor_ids || actors.map(actor => actor.id)).map(String));
  const actorSelectionAllowed = singleAllowed || helpAllowed;
  const instruction = [
    actorSelectionAllowed
      ? helpAllowed
        ? 'Wybierz prowadzącego i pomocnika na ekranie albo naciśnij ✓, aby kontynuować bez pomocy.'
        : 'Wybierz na ekranie postać, która wykona test.'
      : '',
    wholePartyAllowed
      ? 'Możecie też wybrać całą drużynę — wtedy każdy rzuca.'
      : '',
  ].filter(Boolean).join(' ');
  return `<div class="interaction-participants">
    <b>Kto wykonuje test?</b>
    <span>${instruction}</span>
    <div class="interaction-actor-grid">${actorSelectionAllowed ? actors.slice(0, 9).map((actor, actorIndex) => {
      const index = selectedInteractionActorIds.indexOf(String(actor.id));
      const eligible = eligibleIds.has(String(actor.id));
      const role = index === 0 ? 'prowadzi' : index === 1 ? 'pomaga' : 'wybierz';
      const numpadKey = actorIndex + 1;
      return `<button type="button" class="interaction-actor-card actor-identity${index >= 0 ? ' selected' : ''}${eligible ? '' : ' unavailable'}"
        data-numpad-key="${numpadKey}" onclick="toggleInteractionActor('${esc(actor.id)}')"${eligible ? '' : ' disabled'}
        style="${actorIdentityStyle(actor)}" aria-selected="${index >= 0 ? 'true' : 'false'}">${numpadChoiceBadge(numpadKey)}${actorPortraitHtml(actor, 'choice')}<span><b>${esc(actor.name)}</b><small>${eligible ? role : 'brak wymaganych zdolności lub narzędzi'}</small></span></button>`;
    }).join('') : ''}
    ${wholePartyAllowed && actors.length < 9 ? `<button type="button" class="interaction-actor-card whole-party${mode === 'whole_party' ? ' selected' : ''}" data-numpad-key="${actors.length + 1}" onclick="selectWholePartyForInteraction()">
      ${numpadChoiceBadge(actors.length + 1)}${partyPortraitStackHtml(actors)}<span><b>Cała drużyna</b><small>${mode === 'whole_party' ? 'wszyscy rzucają' : 'wybierz test grupowy'}</small></span></button>` : ''}
    </div>
    ${actorSelectionAllowed ? numpadChoiceHint(Math.min(9, actors.length + (wholePartyAllowed ? 1 : 0)), 'wybierz wykonawcę') : ''}
  </div>`;
}
function interactionActionSourcePickerHtml(goal) {
  const sources = goal.action_sources || [];
  if (!goal.accepted_source_tags || !goal.accepted_source_tags.length) return '';
  const leadId = selectedInteractionActorIds.length ? String(selectedInteractionActorIds[0]) : null;
  const kindLabels = {
    resource: 'zasób drużyny',
    item: 'przedmiot',
    tool: 'narzędzie',
    weapon: 'broń',
    spell: 'czar',
  };
  const consequenceLabels = {
    loud: 'głośne',
    very_loud: 'bardzo głośne',
    fire: 'ogień',
  };
  return `<div class="interaction-participants">
    <b>Czego używacie?</b>
    <span>Źródło ustala legalne możliwości, właściciela i konsekwencje — Gemini nie może go podmienić. W wyzwaniu eksploracyjnym broń lub czar wspiera test celu; nie jest to bojowy rzut przeciw AC ani obrażenia fixture.</span>
    <div class="interaction-actor-grid">
      ${goal.source_required ? '' : `<button type="button" class="interaction-actor-card${selectedInteractionActionSourceId ? '' : ' selected'}"
        data-numpad-key="1" onclick="selectInteractionActionSource(null)">${numpadChoiceBadge(1)}<span><b>Bez dodatkowego źródła</b><small>zwykła próba</small></span></button>`}
      ${sources.slice(0, goal.source_required ? 9 : 8).map((source, sourceIndex) => {
        const numpadKey = sourceIndex + (goal.source_required ? 1 : 2);
        const wrongOwner = Boolean(source.owner_actor_id && leadId && String(source.owner_actor_id) !== leadId);
        const disabled = !source.available || wrongOwner;
        const owner = source.owner_name ? ` · ${source.owner_name}` : '';
        const modifier = Number(source.modifier || 0)
          ? ` · ${Number(source.modifier) > 0 ? '+' : ''}${source.modifier} do testu`
          : '';
        const consequences = (source.consequence_tags || [])
          .map(tag => consequenceLabels[tag] || tag)
          .join(', ');
        const reason = wrongOwner
          ? `${source.owner_name} musi prowadzić próbę.`
          : source.unavailable_reason || '';
        return `<button type="button" class="interaction-actor-card${source.id === selectedInteractionActionSourceId ? ' selected' : ''}${disabled ? ' unavailable' : ''}"
          data-numpad-key="${numpadKey}" onclick="selectInteractionActionSource('${esc(source.id)}')"${disabled ? ` disabled title="${esc(reason)}"` : ''}>
          ${numpadChoiceBadge(numpadKey)}<span><b>${esc(source.label)}</b><small>${esc(kindLabels[source.kind] || source.kind)}${esc(owner)}${esc(modifier)}${consequences ? ` · ${esc(consequences)}` : ''}${reason ? ` · ${esc(reason)}` : ''}</small></span>
        </button>`;
      }).join('') || '<span class="muted">Brak pasujących źródeł w drużynie.</span>'}
    </div>
    ${numpadChoiceHint(Math.min(9, sources.length + (goal.source_required ? 0 : 1)), 'wybierz źródło')}
  </div>`;
}
function selectInteractionActionSource(sourceId) {
  selectedInteractionActionSourceId = sourceId || null;
  const goal = currentInteractionGoals().find(item => item.id === selectedInteractionGoalId) || null;
  if (interactionGoalExecutesImmediately(goal)) {
    sendGoalAction();
    return;
  }
  const panel = document.getElementById('interaction-goals');
  if (panel) panel.innerHTML = interactionGoalsHtml();
}
function toggleInteractionActor(actorId) {
  const goal = currentInteractionGoals().find(item => item.id === selectedInteractionGoalId);
  if (!goal) return;
  const options = goal.allowed_check_participants || [goal.check_participants || 'single_actor'];
  const singleAllowed = options.includes('single_actor');
  const helpAllowed = options.includes('lead_with_help');
  if (!singleAllowed && !helpAllowed) return;
  const id = String(actorId);
  if (goal.eligible_actor_ids && !goal.eligible_actor_ids.map(String).includes(id)) return;
  if (selectedInteractionCheckParticipants === 'whole_party') selectedInteractionActorIds = [];
  const currentIndex = selectedInteractionActorIds.indexOf(id);
  if (currentIndex >= 0) {
    selectedInteractionActorIds.splice(currentIndex, 1);
  } else {
    if (helpAllowed && selectedInteractionActorIds.length === 1) {
      selectedInteractionActorIds.push(id);
    } else {
      selectedInteractionActorIds = [id];
    }
  }
  if (goal.participant_mode === 'must') {
    selectedInteractionCheckParticipants = goal.check_participants;
  } else if (selectedInteractionActorIds.length >= 2) {
    selectedInteractionCheckParticipants = 'lead_with_help';
  } else if (selectedInteractionActorIds.length === 1) {
    selectedInteractionCheckParticipants = singleAllowed ? 'single_actor' : 'lead_with_help';
  } else {
    selectedInteractionCheckParticipants = null;
  }
  const selectedSource = (goal.action_sources || []).find(
    source => source.id === selectedInteractionActionSourceId
  );
  if (
    selectedSource
    && selectedSource.owner_actor_id
    && selectedInteractionActorIds.length
    && String(selectedSource.owner_actor_id) !== String(selectedInteractionActorIds[0])
  ) {
    selectedInteractionActionSourceId = null;
  }
  prepareObviousInteractionChoices(goal);
  const panel = document.getElementById('interaction-goals');
  if (panel) panel.innerHTML = interactionGoalsHtml();
}
function selectWholePartyForInteraction() {
  const goal = currentInteractionGoals().find(item => item.id === selectedInteractionGoalId);
  if (!goal) return;
  const options = goal.allowed_check_participants || [goal.check_participants || 'single_actor'];
  if (!options.includes('whole_party')) return;
  api('/api/exploration/actor-selection/select', {
    goal_id: goal.id,
    actor_id: '',
    role: 'whole_party',
  }, 'Wybieram całą drużynę...');
}
function startInteractionHelperBoardSelection() {
  const goal = currentInteractionGoals().find(item => item.id === selectedInteractionGoalId);
  if (!goal || selectedInteractionActorIds.length !== 1) return;
  api('/api/exploration/actor-selection/start', {
    goal_id: goal.id,
    role: 'helper',
    excluded_actor_ids: [selectedInteractionActorIds[0]],
  }, 'Podświetlam wybór pomocnika...');
}
function pendingHtml(pending) {
  if (!pending) return '';
  const proposal = pending.proposal || {};
  const option = pending.option || {};
  const lines = [];
  if (pending.kind === 'source_selection' && pending.source_selection) {
    const selection = pending.source_selection;
    if (selection.requested_name) {
      lines.push(`<p>Nie znaleziono elementu nazwanego dokładnie <b>${esc(selection.requested_name)}</b>. MG proponuje najbliższe funkcjonalnie możliwości.</p>`);
    } else if (selection.purpose) {
      lines.push(`<p><b>Szukana funkcja:</b> ${esc(selection.purpose)}.</p>`);
    }
    const candidates = (selection.candidates || []).map((candidate, index) => {
      const properties = (candidate.properties || []).map(item => `<span class="property-chip">${esc(item.label || item.id)}</span>`).join('');
      const status = candidate.portable ? 'można przenieść w obrębie sceny' : (candidate.detachable ? 'najpierw trzeba odłączyć' : 'stały element sceny');
      return `<label class="source-candidate-card">
        <input type="radio" name="source-selection-choice" value="${esc(candidate.id)}"${index === 0 ? ' checked' : ''}>
        <span><b>${esc(candidate.label)}</b>${Number(candidate.quantity || 1) > 1 ? ` ×${esc(candidate.quantity)}` : ''}<br>
        <span class="muted">Stan: ${esc(candidate.condition || 'normal')} · ${esc(status)}</span><br>
        <span class="property-chip-list">${properties}</span></span>
      </label>`;
    }).join('');
    lines.push(`<div class="source-candidate-list">${candidates}</div>`);
    lines.push('<p class="muted">Wybór zapisze element jako znaleziony w tej lokacji. Nie trafi on automatycznie do ekwipunku.</p>');
    return lines.join('');
  }
  if (pending.source_use) {
    const source = pending.source_use;
    const properties = (source.properties || []).map(item => `<span class="property-chip">${esc(item.label || item.id)}</span>`).join('');
    const location = source.remains_in_scene ? 'pozostaje elementem sceny' : 'zasób drużyny lub ekwipunku';
    lines.push(`<div class="source-use-card">
      <b>Używany element: ${esc(source.label)}</b>${Number(source.quantity || 1) > 1 ? ` ×${esc(source.quantity)}` : ''}<br>
      <span class="muted">Stan: ${esc(source.condition || 'normal')} · ${esc(location)}</span>
      <div class="property-chip-list">${properties}</div>
    </div>`);
  }
  if (pending.kind === 'collection' && pending.collection) {
    const collection = pending.collection;
    const properties = (collection.properties || []).map(item => `<span class="property-chip">${esc(item.label || item.id)}</span>`).join('');
    const destination = {
      actor_inventory: 'ekwipunek wybranego bohatera',
      party_treasure: 'wspólne łupy drużyny',
      scenario_quest: 'zasoby fabularne scenariusza'
    }[collection.destination] || collection.destination;
    const quantity = Number(collection.available_quantity || 1);
    lines.push(`<div class="source-use-card">
      <b>Zabierany element: ${esc(collection.label)}</b><br>
      <span class="muted">Z lokacji: ${esc(collection.zone_id)} · stan: ${esc(collection.condition || 'normal')}</span>
      <div class="property-chip-list">${properties}</div>
      <p><b>Dokąd:</b> ${esc(destination)}.</p>
      <label><b>Ile?</b> <input id="collection-quantity" type="number" min="1" max="${esc(quantity)}" value="${esc(collection.quantity || 1)}"></label>
      <p class="muted">Po zatwierdzeniu wybrana liczba zniknie z dostępnych elementów sceny.</p>
    </div>`);
    return lines.join('');
  }
  if (pending.fixture_action) {
    const action = pending.fixture_action;
    const operation = {
      detach: 'odłączenie', damage: 'uszkodzenie', destroy: 'zniszczenie',
      move: 'przesunięcie', open: 'otwarcie', close: 'zamknięcie', repair: 'naprawa'
    }[action.operation] || action.operation;
    const yields = (action.release_yield_item_ids || []).length
      ? `<p><b>Po sukcesie pojawią się:</b> ${(action.release_yield_item_ids || []).map(esc).join(', ')}.</p>`
      : '';
    lines.push(`<div class="source-use-card">
      <b>Zmiana obiektu: ${esc(action.fixture_label)}</b><br>
      <span class="muted">${esc(operation)} · ${esc(action.current_condition)} → ${esc(action.result_condition)}</span>
      ${yields}
      <p><b>Trwałość:</b> udany wynik zostanie zapisany w stanie sceny i w zapisie gry.</p>
    </div>`);
  }
  if (pending.kind === 'observation' && pending.observation) {
    const observation = pending.observation;
    const skill = observation.skill ? `/${esc(observation.skill)}` : '';
    const thresholds = (observation.thresholds || []).map(value => esc(value)).join(', ');
    lines.push(`<p><b>${esc(observation.label)}</b><br>${esc(observation.description)}</p>`);
    lines.push(`<p><b>Test:</b> ${esc(observation.ability)}${skill}, podstawowe ST ${esc(observation.dc)}.</p>`);
    lines.push(`<p><b>Stopniowane informacje:</b> jeden rzut; wyższy wynik może ujawnić kolejne warstwy informacji${thresholds ? ` (progi: ${thresholds})` : ''}.</p>`);
    lines.push('<p>Porażka oznacza brak rozstrzygającej informacji, a nie potwierdzenie, że zagrożenia nie ma.</p>');
    return lines.join('');
  }
  if (pending.kind === 'trap' && pending.trap) {
    const trap = pending.trap;
    if (pending.stage === 'hazard_save' && pending.hazard) {
      const save = pending.hazard.saving_throw || {};
      return `<p><b>${esc(trap.name)} została uruchomiona.</b><br>${esc(pending.hazard.narration || '')}</p>
        <p><b>Rzut obronny:</b> ${esc(save.ability_label || save.ability || '')}, ST ${esc(save.dc || '')}.</p>
        <p>Wpisz fizyczny wynik d20, aby rozstrzygnąć alarm.</p>`;
    }
    const actionLabel = {
      disarm: 'Rozbrojenie',
      bypass: 'Bezpieczne ominięcie',
      trigger: 'Celowe uruchomienie'
    }[trap.action] || trap.action;
    lines.push(`<p><b>${esc(trap.name)}</b><br>${esc(trap.description)}</p>`);
    lines.push(`<p><b>Działanie:</b> ${esc(actionLabel)}.</p>`);
    if (trap.dc != null) {
      const skill = trap.skill ? `/${esc(trap.skill)}` : '';
      const tool = trap.tool ? `, narzędzie: ${esc(trap.tool)}` : '';
      lines.push(`<p><b>Test:</b> ${esc(trap.ability)}${skill}${tool}, ST ${esc(trap.dc)}.</p>`);
      lines.push('<p><b>Porażka:</b> mechanizm zostanie uruchomiony i pojawi się osobny rzut obronny.</p>');
    } else {
      lines.push('<p>Ta decyzja nie wymaga testu, ale uruchomi mechanizm pułapki.</p>');
    }
    if (trap.required_item_id) lines.push(`<p><b>Wymaga:</b> ${esc(trap.required_item_id)}.</p>`);
    return lines.join('');
  }
  if (pending.kind === 'crafting' && pending.crafting) {
    const crafting = pending.crafting;
    const components = (crafting.components || []).map(component => {
      const disposition = component.disposition === 'consumed' ? 'zużyte' : 'zarezerwowane do rozmontowania';
      return `${esc(component.label)} ×${esc(component.quantity)} (${disposition})`;
    }).join('; ');
    lines.push(`<p><b>${esc(crafting.label)}</b><br>${esc(crafting.description)}</p>`);
    lines.push(`<p><b>Cel:</b> ${esc(crafting.purpose_label)}.</p>`);
    lines.push(`<p><b>Materiały:</b> ${components || 'brak'}.</p>`);
    if (crafting.auto_selected_components) lines.push('<p><b>Dobór:</b> silnik uzupełnił brakujące komponenty z dostępnych elementów sceny.</p>');
    lines.push(`<p><b>Koszt czasu:</b> ${esc(crafting.time_cost_minutes)} min.</p>`);
    lines.push(`<p><b>Efekt:</b> ${signedNumber(Number(crafting.modifier || 0))} do pasującego użycia, ${esc(crafting.uses)} użycia.</p>`);
    lines.push(`<p><b>Zakres:</b> ${crafting.scope === 'scenario' ? 'do końca scenariusza' : 'w tej scenie'}.</p>`);
    if (crafting.risk) lines.push(`<p><b>Ryzyko przy użyciu:</b> ${esc(crafting.risk)}</p>`);
    lines.push('<p><b>Budowa:</b> bez rzutu. Test pojawi się dopiero, gdy użycie konstrukcji będzie niepewne.</p>');
    return lines.join('');
  }
  if (option.label) {
    const skill = option.skill ? `/${esc(option.skill)}` : '';
    const toolProficiency = option.tool ? `, narzędzie: ${esc(option.tool_label || option.tool)}` : '';
    if (option.mechanic) lines.push(`<p><b>Mechanika:</b> ${esc(option.mechanic.label || option.mechanic.id)}.</p>`);
    lines.push(`<p><b>Podejście:</b> ${esc(option.label)}. Test: ${esc(option.ability)}${skill}${toolProficiency}, ST ${esc(option.dc)}.</p>`);
    if (option.roll_mode && option.roll_mode !== 'normal') lines.push(`<p><b>Tryb rzutu:</b> ${esc(option.roll_mode)}.</p>`);
    if (option.situational_modifiers && option.situational_modifiers.length) {
      lines.push(`<p><b>Modyfikatory sytuacyjne:</b> ${option.situational_modifiers.map(mod => `${esc(mod.label)} ${signedNumber(Number(mod.modifier || 0))}${mod.roll_mode && mod.roll_mode !== 'normal' ? `, ${esc(mod.roll_mode)}` : ''} (${esc(mod.source)}: ${esc(mod.reason)})`).join('; ')}</p>`);
    }
    if (option.improvised_tool) {
      const tool = option.improvised_tool;
      lines.push(`<p><b>Improwizowane narzędzie:</b> ${esc(tool.label)} ${signedNumber(Number(tool.effect_modifier || 0))} (${esc(tool.source)}: ${esc(tool.source_detail)}${tool.risk ? `, ryzyko: ${esc(tool.risk)}` : ''}). ${esc(tool.reason)}</p>`);
    }
    const selectedResource = pending.resources && pending.resources.length ? pending.resources[0] : null;
    if (selectedResource) {
      lines.push(`<p><b>Zasób sceny:</b> ${resourceSummary(selectedResource)}.</p>`);
    }
    if (!state.active_challenge || state.active_challenge.uses_progress) {
      lines.push(`<p><b>Postęp:</b> sukces +${Number(option.progress_on_success || 0)}, porażka +${Number(option.progress_on_failure || 0)}.</p>`);
    }
    if (pending.kind === 'challenge' && pending.stage === 'decision' && !pending.fixture_action) {
      lines.push(`<button class="secondary" onclick="toggleDecisionCorrection()">Popraw decyzję MG</button>`);
      if (decisionCorrectionOpen) lines.push(decisionCorrectionHtml(option, pending));
    }
  } else if (proposal.action_type) {
    const actionTypeLabels = {
      information: 'Zdobycie informacji',
      commitment: 'Podjęcie zobowiązania',
      travel: 'Przygotowanie do drogi',
      social: 'Wpływ społeczny',
      hospitality: 'Gościnność',
      beer_tasting: 'Opinia o piwie',
      medical: 'Pomoc medyczna',
      trade: 'Handel',
    };
    const actionTypeLabel = actionTypeLabels[proposal.action_type] || proposal.action_type;
    const attemptBlocked = pending.attempt_plan && !pending.attempt_plan.available;
    if (pending.npc_action_plan) {
      const action = pending.npc_action_plan;
      const outcomes = action.outcomes || {};
      lines.push(`<p><b>Cel:</b> ${esc(action.target_label)}${Number(action.quantity || 1) > 1 ? ` ×${esc(action.quantity)}` : ''}. ${esc(action.description || '')}</p>`);
      if (action.reward_label) lines.push(`<p><b>Możliwy efekt:</b> ${esc(action.reward_label)}.</p>`);
      if (action.risk_summary) lines.push(`<p><b>Ryzyko:</b> ${esc(action.risk_summary)}</p>`);
      const outcomeLabels = { critical_success: 'Krytyczny sukces', success: 'Sukces', failure: 'Porażka', critical_failure: 'Krytyczna porażka' };
      const outcomeOrder = ['critical_success', 'success', 'failure', 'critical_failure'];
      lines.push(`<div class="npc-outcome-preview">${outcomeOrder.filter(key => outcomes[key]).map(key => `<p><b>${esc(outcomeLabels[key])}:</b> ${esc(outcomes[key].preview)}</p>`).join('')}</div>`);
    }
    if (pending.attempt_plan) {
      const attempt = pending.attempt_plan;
      if (!attempt.available) {
        lines.push(`<p><b>Dostępność podejścia:</b> ${esc(attempt.blocked_reason)}</p>`);
      } else {
        const attemptNumber = Number(attempt.attempts_used || 0) + 1;
        const retryLabel = attempt.is_retry ? 'Ponowienie próby' : 'Pierwsza próba';
        const lastLabel = attemptNumber === Number(attempt.max_attempts || 0) ? ' To ostatnia dostępna próba tego podejścia.' : '';
        lines.push(`<p><b>${esc(retryLabel)}:</b> ${esc(attemptNumber)}/${esc(attempt.max_attempts)}.${esc(lastLabel)}</p>`);
      }
    }
    if (!attemptBlocked && pending.social_plan) {
      const social = pending.social_plan;
      const attitudeLabels = { hostile: 'wrogi', indifferent: 'obojętny', friendly: 'przyjazny' };
      const riskLabels = { no_risk: 'bez ryzyka', minor_risk: 'niewielkie ryzyko', significant_risk: 'znaczące ryzyko' };
      lines.push(`<p><b>Nastawienie NPC:</b> ${esc(attitudeLabels[social.attitude] || social.attitude)}.</p>`);
      lines.push(`<p><b>Zakres prośby:</b> ${esc(riskLabels[social.request_risk] || social.request_risk)} dla NPC.</p>`);
      if (!social.possible) {
        lines.push('<p><b>Reakcja:</b> przy obecnym nastawieniu NPC odmówi. Zmiana podejścia lub nastawienia może otworzyć tę możliwość.</p>');
      } else if (social.requires_roll) {
        const skill = proposal.skill ? `/${esc(proposal.skill)}` : '';
        lines.push(`<p><b>Test społeczny:</b> ${esc(proposal.ability)}${skill}, ST ${esc(social.dc)}.</p>`);
      } else {
        lines.push('<p><b>Reakcja:</b> NPC zgodzi się bez rzutu.</p>');
      }
    } else if (!attemptBlocked && proposal.requires_roll) {
      const skill = proposal.skill ? `/${esc(proposal.skill)}` : '';
      lines.push(`<p><b>Rodzaj działania:</b> ${esc(actionTypeLabel)}. Test: ${esc(proposal.ability)}${skill}, ST ${esc(proposal.dc)}.</p>`);
    } else if (!attemptBlocked) {
      lines.push(`<p><b>Rodzaj działania:</b> ${esc(actionTypeLabel)}. Bez rzutu.</p>`);
    }
  }
  return lines.join('') || '<p>MG proponuje interpretację deklaracji.</p>';
}
function pendingTitle(pending) {
  if (!pending) return 'Warunki próby';
  if (pending.kind === 'crafting') return 'Warunki konstrukcji';
  if (pending.kind === 'npc') return 'Warunki interakcji';
  if (pending.kind === 'observation') return 'Warunki rozpoznania';
  if (pending.kind === 'trap') return 'Interakcja z pułapką';
  if (pending.kind === 'source_selection') return 'Wybór znalezionego elementu';
  if (pending.kind === 'collection') return 'Potwierdzenie zabrania';
  return 'Warunki próby';
}
function discoveredSourcesHtml() {
  const sources = state.discovered_sources || [];
  if (!sources.length) return '<span class="muted">Jeszcze niczego nie znaleziono.</span>';
  return `<div class="discovered-source-list">${sources.map(source => {
    const properties = (source.properties || []).map(item => `<span class="property-chip">${esc(item.label || item.id)}</span>`).join('');
    const purpose = source.purpose ? `<div class="muted">Przydatne do: ${esc(source.purpose)}</div>` : '';
    const status = source.available ? 'dostępny w scenie' : 'obecnie niedostępny';
    const collections = (source.collections || []).map(item => {
      const destination = {
        actor_inventory: 'ekwipunek bohatera',
        party_treasure: 'łupy drużyny',
        scenario_quest: 'zasoby fabularne'
      }[item.destination] || item.destination;
      return `zabrano ×${esc(item.quantity)} → ${esc(destination)}`;
    }).join('; ');
    return `<div class="discovered-source-card${source.available ? '' : ' unavailable'}">
      <b>${esc(source.label)}</b>${Number(source.quantity || 1) > 1 ? ` ×${esc(source.quantity)}` : ''}
      <div class="muted">${esc(status)} · poza ekwipunkiem</div>
      ${collections ? `<div class="muted">${collections}</div>` : ''}
      ${purpose}<div class="property-chip-list">${properties}</div>
    </div>`;
  }).join('')}</div>`;
}
function resourceSummary(resource) {
  const effects = [];
  if (Number(resource.modifier || 0) !== 0) effects.push(`rzut ${signedNumber(Number(resource.modifier || 0))}`);
  if (resource.advantage) effects.push('przewaga');
  if (Number(resource.mitigates_noise || 0) > 0) effects.push(`hałas -${Number(resource.mitigates_noise)}`);
  if (resource.mitigates_complications && resource.mitigates_complications.length) {
    effects.push(`chroni przed: ${resource.mitigates_complications.map(esc).join(', ')}`);
  }
  effects.push(resource.consume_on_use ? 'zostanie zużyty po rzucie' : 'wielokrotnego użytku');
  return `${esc(resource.label || resource.id)} (${effects.join(', ')})`;
}
function leadActorChoiceHtml() {
  if (!state.pending || !['challenge', 'observation', 'collection', 'trap'].includes(state.pending.kind) || state.pending.stage !== 'decision' || !state.actors || !state.actors.length) return '';
  if (state.pending.kind === 'collection' && state.pending.collection && state.pending.collection.destination !== 'actor_inventory') return '';
  if (['challenge', 'observation'].includes(state.pending.kind) && (state.pending.participant_actor_ids || []).length) {
    const ids = state.pending.participant_actor_ids.map(String);
    const mode = state.pending.option ? state.pending.option.check_participants : 'single_actor';
    const names = ids.map((id, index) => {
      const actor = state.actors.find(item => String(item.id) === id);
      const role = mode === 'whole_party' ? 'rzuca' : index === 0 ? 'prowadzi' : 'pomaga';
      return `${actor ? actor.name : id} — ${role}`;
    });
    return `<div class="interaction-participant-summary"><b>Uczestnicy ustaleni przed deklaracją:</b> ${esc(names.join(', '))}</div>`;
  }
  const selectedId = state.selected_lead_actor_id || (state.actors[0] && state.actors[0].id) || '';
  const options = state.actors.map(actor => `<option value="${esc(actor.id)}"${String(actor.id) === String(selectedId) ? ' selected' : ''}>${esc(actor.name)}</option>`).join('');
  const label = state.pending.kind === 'collection' ? 'Kto zabiera?' : 'Kto prowadzi test?';
  return `<label><b>${label}</b> <select id="lead-actor">${options}</select></label>`;
}
function decisionCorrectionHtml(option, pending) {
  const mechanicId = option.mechanic && option.mechanic.id ? option.mechanic.id : 'single_actor_check';
  const actorOptions = (selectedId, allowEmpty=false) => `${allowEmpty ? '<option value="">-</option>' : ''}${(state.actors || []).map(actor => `<option value="${esc(actor.id)}"${String(actor.id) === String(selectedId || '') ? ' selected' : ''}>${esc(actor.name)}</option>`).join('')}`;
  const mechanicOptions = (state.allowed_mechanics || []).map(tool => `<option value="${esc(tool.id)}"${tool.id === mechanicId ? ' selected' : ''}>${esc(tool.label || tool.id)}</option>`).join('');
  const participants = option.check_participants || (option.mechanic && option.mechanic.participants ? option.mechanic.participants : 'single_actor');
  const lockedParticipantIds = (pending.participant_actor_ids || []).map(String);
  const lockedParticipantSummary = lockedParticipantIds.map((id, index) => {
    const actor = (state.actors || []).find(item => String(item.id) === id);
    const role = participants === 'whole_party' ? 'rzuca' : index === 0 ? 'prowadzi' : 'pomaga';
    return `${actor ? actor.name : id} — ${role}`;
  }).join(', ');
  const aggregation = option.check_aggregation || (participants === 'whole_party' ? 'highest' : 'lead_result');
  const abilityOptions = ['strength','dexterity','constitution','intelligence','wisdom','charisma'].map(ability => `<option value="${ability}"${ability === option.ability ? ' selected' : ''}>${ability}</option>`).join('');
  const rollMode = option.roll_mode || 'normal';
  const rollModeOptions = ['normal','advantage','disadvantage'].map(mode => `<option value="${mode}"${mode === rollMode ? ' selected' : ''}>${mode}</option>`).join('');
  const sourceOptions = selectedSource => ['scenario_context','zone_context','challenge_context','interaction_object','player_declaration','dynamic_state','gm'].map(source => `<option value="${source}"${source === selectedSource ? ' selected' : ''}>${source}</option>`).join('');
  const situational = option.situational_modifiers || [];
  const improvised = option.improvised_tool || {};
  const selectedResourceId = pending.resources && pending.resources.length ? String(pending.resources[0].id) : '';
  const optionTags = new Set(option.tags || []);
  const matchingResourceOptions = (state.resources || []).filter(resource =>
    String(resource.id) === selectedResourceId || (resource.bonus_tags || []).some(tag => optionTags.has(tag))
  );
  const resourceOptions = `<option value="">bez zasobu</option>${matchingResourceOptions.map(resource =>
    `<option value="${esc(resource.id)}"${String(resource.id) === selectedResourceId ? ' selected' : ''}>${resourceSummary(resource)}</option>`
  ).join('')}`;
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
      ${lockedParticipantIds.length ? `<div class="interaction-participant-summary"><b>Uczestnicy ustaleni przed deklaracją:</b> ${esc(lockedParticipantSummary)}</div>` : `<label>Uczestnicy
        <select id="correction-participants">
          <option value="single_actor"${participants === 'single_actor' ? ' selected' : ''}>jedna postać</option>
          <option value="lead_with_help"${participants === 'lead_with_help' ? ' selected' : ''}>prowadzący z pomocą</option>
          <option value="whole_party"${participants === 'whole_party' ? ' selected' : ''}>cała drużyna</option>
          <option value="selected_actors"${participants === 'selected_actors' ? ' selected' : ''}>wybrane postacie</option>
        </select>
      </label>`}
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
      ${lockedParticipantIds.length ? '' : `<label>Prowadzący <select id="correction-lead">${actorOptions(state.selected_lead_actor_id)}</select></label>
      <label>Pomocnik <select id="correction-helper">${actorOptions(state.selected_helper_actor_id, true)}</select></label>`}
      <label>Cecha <select id="correction-ability">${abilityOptions}</select></label>
      <label>Skill <input id="correction-skill" value="${esc(option.skill || '')}" placeholder="np. athletics"></label>
      <label>ST <input id="correction-dc" type="number" min="5" max="25" value="${esc(option.dc || 10)}"></label>
      <label>Tryb rzutu <select id="correction-roll-mode">${rollModeOptions}</select></label>
      <label>Zasób sceny <select id="correction-resource">${resourceOptions}</select></label>
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
  if (state.pending.stage === 'hazard_save') {
    const hazard = state.pending.hazard || {};
    const save = hazard.saving_throw || {};
    const damage = hazard.damage || {};
    const required = (state.required_rolls || [])[0] || {};
    const modifiers = required.active_modifiers || [];
    const featherFallOptions = state.pending.feather_fall_options || [];
    const featherFallHtml = featherFallOptions.length ? `
      <div class="flow-note">
        <b>Reakcja dostępna: Powolne opadanie</b>
        <span>Zamiast rzutu obronnego wybrany czarujący zużyje reakcję i slot 1. poziomu; spadający bohater wyląduje bez obrażeń.</span>
        <label>Rzucający
          <select id="hazard-feather-fall-caster">
            ${featherFallOptions.map(option => `<option value="${esc(option.actor_id)}">${esc(option.actor_name)}</option>`).join('')}
          </select>
        </label>
        <button type="button" onclick="castHazardFeatherFall()">Rzuć Powolne opadanie</button>
      </div>` : '';
    return `
      <p><b>Zagrożenie: ${esc(hazard.label || '-')}</b></p>
      <p>${esc(hazard.narration || '')}</p>
      <p><b>Rzut obronny:</b> ${esc(save.ability_label || abilityLabel(save.ability))} przeciw ST ${esc(save.dc)}.</p>
      <p><b>Modyfikator:</b> ${esc(signedNumber(required.modifier_total || 0))} — ${modifiers.map(mod => `${esc(mod.label)} ${esc(signedNumber(mod.value || 0))}`).join(', ') || 'bez premii'}.</p>
      <p><b>Sukces:</b> ${esc(save.success_effect_label || 'brak efektu')}. <b>Porażka:</b> ${esc(save.failure_effect_label || 'pełny efekt')}.</p>
      <p><b>Ryzyko obrażeń:</b> ${esc(damage.dice || damage.fixed || 0)}${Number(damage.modifier || 0) ? ` ${esc(signedNumber(damage.modifier))}` : ''} ${esc(damage.damage_type || '')}.</p>
      ${featherFallHtml}
    `;
  }
  if (state.pending.stage === 'breakage') {
    const info = state.pending.breakage || {};
    return `<p><b>Test trwałości:</b> rzuć k100 dla ${esc(info.item_label || info.item_id || 'przedmiotu')}. Wynik ${esc(info.chance_percent || 0)} lub mniej oznacza uszkodzenie.</p>`;
  }
  if (state.pending.stage !== 'roll') return '';
  const plan = state.pending.check_plan || {};
  const participants = {
    single_actor: 'rzuca jeden wybrany bohater',
    lead_with_help: 'prowadzący wykonuje test, pomocnik nie rzuca osobno',
    whole_party: 'rzuca cała drużyna',
    selected_actors: 'rzucają wybrani bohaterowie'
  }[plan.participants] || plan.participants || 'rzut eksploracyjny';
  const aggregation = {
    lead_result: 'liczy się wynik prowadzącego',
    highest: 'liczy się najwyższy wynik',
    lowest: 'liczy się najniższy wynik',
    majority: 'sukces, jeśli zda co najmniej połowa'
  }[plan.aggregation] || plan.aggregation || '';
  const lead = (state.actors || []).find(actor => String(actor.id) === String(plan.lead_actor_id || ''));
  const cechaOnly = lead?.uses_charge || (state.actors || []).some(actor => actor.uses_charge);
  const checkName = skillLabel(plan.skill);
  const abilityName = abilityLabel(plan.ability);
  const checkLabel = cechaOnly ? abilityName : plan.skill
    ? `${checkName} (${abilityName})`
    : plan.tool
      ? `${plan.tool_label || plan.tool} (${abilityName})`
      : abilityName;
  const helper = (state.actors || []).find(actor => String(actor.id) === String(plan.helper_actor_id || ''));
  const rollingNames = (state.required_rolls || []).map(r => r.actor_name).join(', ');
  const roleHtml = plan.participants === 'lead_with_help'
    ? `<p><b>Test wykonuje:</b> ${esc((lead && lead.name) || rollingNames || '-')} — ${esc(checkLabel)} przeciw ST ${esc(plan.dc)}.</p>
       <p><b>Pomaga:</b> ${esc((helper && helper.name) || '-')} — nie rzuca osobno; jego pomoc daje prowadzącemu przewagę.</p>`
    : `<p><b>Test:</b> ${esc(checkLabel)} przeciw ST ${esc(plan.dc)}. <b>Rzucają:</b> ${esc(rollingNames || '-')}.</p>`;
  const rollBreakdowns = (state.required_rolls || []).map(required => {
    const active = required.active_modifiers || [];
    const ignored = required.ignored_modifiers || [];
    const ignoredText = ignored.length
      ? `; nie sumuje się: ${ignored.map(mod => `${esc(mod.label)} ${esc(signedNumber(mod.value))}`).join(', ')}`
      : '';
    return `<li><b>${esc(required.actor_name)}:</b> ${esc(signedNumber(required.modifier_total || 0))} — ${active.map(mod => `${esc(mod.label)} ${esc(signedNumber(mod.value))}`).join(', ') || 'bez premii'}${ignoredText}</li>`;
  }).join('');
  const mechanic = plan.mechanic || {};
  const mechanicHtml = mechanic.id ? `<p><b>Mechanika:</b> ${esc(mechanic.label || mechanic.id)}</p>` : '';
  const rollModeHtml = plan.roll_mode && plan.roll_mode !== 'normal' ? `<p><b>Tryb rzutu:</b> ${esc(rollModeLabel(plan.roll_mode))}.</p>` : '';
  const situationalHtml = plan.situational_modifiers && plan.situational_modifiers.length
    ? `<p><b>Modyfikatory sytuacyjne:</b> ${plan.situational_modifiers.map(mod => `${esc(mod.label)} ${signedNumber(Number(mod.modifier || 0))}${mod.roll_mode && mod.roll_mode !== 'normal' ? `, ${esc(mod.roll_mode)}` : ''} (${esc(mod.reason)})`).join('; ')}</p>`
    : '';
  const tool = plan.improvised_tool || null;
  const improvisedHtml = tool
    ? `<p><b>Improwizowane narzędzie:</b> ${esc(tool.label)} ${signedNumber(Number(tool.effect_modifier || 0))} (${esc(tool.source_detail)}${tool.risk ? `, ryzyko: ${esc(tool.risk)}` : ''}).</p>`
    : '';
  const resourceHtml = plan.resource
    ? `<p><b>Zasób sceny:</b> ${resourceSummary(plan.resource)}.</p>`
    : '';
  const bonuses = (plan.option_bonuses || []).filter(bonus => Number(bonus.modifier || 0) !== 0);
  const bonusHtml = bonuses.length
    ? `<p><b>Aktywne premie:</b> ${bonuses.map(bonus => {
        const spellLevel = Number(bonus.spell_level || 0);
        const spellCost = bonus.source_type === 'spell' ? (spellLevel > 0 ? `, zużyje slot ${spellLevel}. poziomu` : ', cantrip bez slota') : '';
        return `${esc(bonus.actor_name || '')}: ${esc(bonus.label || bonus.source_id)} ${signedNumber(Number(bonus.modifier || 0))}${spellCost}`;
      }).join('; ')}</p>`
    : '';
  const toolProficiencyHtml = plan.tool ? `<p><b>Narzędzie:</b> ${esc(plan.tool_label || plan.tool)}.</p>` : '';
  return `${mechanicHtml}${roleHtml}${rollModeHtml}<p><b>Rozstrzygnięcie:</b> ${esc(participants)}${aggregation ? `; ${esc(aggregation)}` : ''}.</p>${toolProficiencyHtml}${rollBreakdowns ? `<ul>${rollBreakdowns}</ul>` : ''}${resourceHtml}${situationalHtml}${improvisedHtml}${bonusHtml}`;
}
function latestResultMessageSince(state, startIndex) {
  const messages = state.messages || [];
  const firstNewMessage = Math.max(0, Number(startIndex || 0));
  for (let i = messages.length - 1; i >= firstNewMessage; i -= 1) {
    if (messages[i].title && messages[i].title.startsWith('Wynik')) return messages[i];
  }
  return messages.length > firstNewMessage ? messages[messages.length - 1] : null;
}
function latestMessageWithTitle(state, title) {
  const messages = state.messages || [];
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (messages[i].title === title) return messages[i];
  }
  return messages[messages.length - 1] || null;
}
function latestMessageWithTitleSince(state, title, startIndex) {
  const messages = state.messages || [];
  for (let i = messages.length - 1; i >= Math.max(0, Number(startIndex || 0)); i -= 1) {
    if (messages[i].title === title) return messages[i];
  }
  return null;
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
function explorationMenuLocationsHtml() {
  const locations = (state.flow && state.flow.available_locations) || [];
  const travelIds = new Set((state.travel_options || []).map(zone => String(zone.id)));
  const currentId = String((state.current_zone || {}).id || '');
  if (!locations.length) return '<p class="muted">Brak jawnych lokacji.</p>';
  return `<div class="status-list">${locations.map(zone => {
    const id = String(zone.id || '');
    let action = '';
    if (id === currentId) action = '<button class="secondary" onclick="openChatInstance()">Otwórz rozmowę</button>';
    else if (travelIds.has(id)) action = `<button onclick="travel('${esc(id)}')">Przejdź</button>`;
    else if (zone.available === false) action = `<span class="muted">${esc(zone.locked_reason || 'Jeszcze niedostępne.')}</span>`;
    else action = '<span class="muted">Wybierz tę lokację na planszy.</span>';
    return `<div class="status-item"><b>${esc(zone.name)}</b><span>${esc(zone.description || zone.summary || '')}</span><div class="row" style="margin-top:7px">${action}</div></div>`;
  }).join('')}</div><button class="secondary" data-primary-scan="true" onclick="scanBoard()">Wybierz lokację na planszy</button>`;
}
function encounterHtml() {
  const encounter = state.pending_encounter;
  if (!encounter) return '';
  if (state.combat) return combatStartHtml();
  const setup = state.encounter_setup;
  if (state.training_arena?.mode === 'walkthrough' && state.training_arena.tutorial?.phase === 'setup') {
    return `<div class="encounter-transition-shell training-setup-focus">
      <div class="encounter-transition-current">${encounterSetupHtml(setup)}
        <div class="board-choice-toolbar" data-board-input-status>${boardSelectionStatusHtml(true)}</div>
        <details><summary>Opcje samouczka</summary>
          <button class="secondary" onclick="api('/api/training/leave', {}, 'Wracam do wyboru postaci…')">↩ Wybór postaci · zachowaj postęp</button>
        </details>
      </div></div>`;
  }
  const stealth = state.encounter_stealth;
  const initiative = state.encounter_initiative;
  const opening = encounter.opening || {};
  const openingComplete = !opening.required || opening.resolved;
  const setupComplete = Boolean(setup && setup.status === 'completed');
  const stealthComplete = !stealth || stealth.completed;
  let currentStepHtml = encounterOpeningHtml(opening);
  if (openingComplete) currentStepHtml = encounterSetupHtml(setup);
  if (setupComplete && !stealthComplete) currentStepHtml = encounterStealthHtml(setup, stealth);
  if (setupComplete && stealthComplete) currentStepHtml = encounterInitiativeHtml(setup, initiative, stealth);
  return `
    <div class="encounter-transition-shell">
      <header class="encounter-transition-head">
        <span class="panel-kicker">Przejście do walki</span>
        <h2>${esc(encounter.name)}</h2>
        <p>${esc(encounter.description)}</p>
      </header>
      ${encounterProgressHtml(opening, setup, stealth, initiative)}
      <div class="encounter-transition-current">
        <div data-board-input-status>${boardSelectionStatusHtml()}</div>
        ${currentStepHtml}
      </div>
      <details class="debug-panel encounter-technical-details">
        <summary>Dane techniczne encountera</summary>
        <p><b>Powód:</b> ${esc(encounter.reason)}</p>
        <p><b>Scenariusz:</b> ${esc(encounter.encounter_scenario)}</p>
        <pre>${esc(encounter.command)}</pre>
      </details>
    </div>
  `;
}
function encounterProgressHtml(opening, setup, stealth, initiative) {
  const openingComplete = !opening.required || opening.resolved;
  const setupComplete = Boolean(setup && setup.status === 'completed');
  const stealthAvailable = Boolean(stealth);
  const stealthComplete = !stealthAvailable || Boolean(stealth.completed);
  const initiativeComplete = Boolean(initiative && initiative.status === 'completed');
  let active = 'opening';
  if (openingComplete) active = setupComplete ? (stealthComplete ? 'initiative' : 'stealth') : 'setup';
  if (initiativeComplete) active = 'initiative';
  const steps = [
    {id: 'opening', label: 'Wejście', complete: openingComplete},
    {id: 'setup', label: 'Plansza', complete: setupComplete},
    {id: 'stealth', label: stealthAvailable ? 'Skradanie' : 'Skradanie opcj.', complete: setupComplete && stealthComplete},
    {id: 'initiative', label: 'Inicjatywa', complete: initiativeComplete},
  ];
  return `<ol class="encounter-progress" aria-label="Przygotowanie do walki">${steps.map((step, index) => {
    const classNames = [step.complete ? 'complete' : '', step.id === active && !step.complete ? 'active' : ''].filter(Boolean).join(' ');
    return `<li class="${classNames}"><span>${step.complete ? '✓' : index + 1}</span><b>${esc(step.label)}</b></li>`;
  }).join('')}</ol>`;
}
function encounterOpeningHtml(opening) {
  if (!opening.required) return '';
  if (!opening.resolved) {
    return `
      <div class="message"><b>Rozpoczęcie starcia</b><br>Sprawdźcie, jak działania w eksploracji wpłynęły na gotowość obu stron, zanim rozpocznie się setup i inicjatywa.</div>
      <button onclick="resolveEncounterOpening()">Rozstrzygnij rozpoczęcie starcia</button>
    `;
  }
  return `
    <div class="result">
      <b>${esc(opening.title || 'Rozpoczęcie starcia')}</b><br>
      ${esc(opening.narration || '')}
      <p><b>Efekt:</b> ${esc(opening.outcome_label || '')}</p>
      <p class="muted">Hałas sceny: ${Number(opening.noise || 0)}</p>
    </div>
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
  const terrainGuide = setup.battle_briefing?.length
    ? '<p><b>Legenda:</b> czerwony ciągły obrys — blokada ruchu i widoczności; złoty przerywany — osłona kierunkowa; niebieski kropkowany — trudny teren. Pozostałe pola są przechodnie.</p><p>Siatka 20 × 30; wydruk 50 × 75 cm (pole 2,5 cm). Obrysy wyznaczają pola terenu, a LED wskazuje obiekty.</p><a href="/game-assets/maps/ostatni_transport_01/glodne_cienie_print_v6.html" target="_blank" rel="noopener">Wersja do druku — skala 100%, bez marginesów</a> · <a href="/game-assets/maps/ostatni_transport_01/glodne_cienie_print_v6.pdf" target="_blank" rel="noopener">Pobierz PDF 50 × 75 cm</a>'
    : '';
  const mapPreview = setup.map_asset_url
    ? `<details class="battle-map-preview"><summary>Mapa i obrysy terenu</summary><img class="location-preview-image" src="${esc(setup.map_asset_url)}" alt="Mapa encountera: ${esc(setup.scenario_name || '')}"><a href="${esc(setup.map_asset_url)}" target="_blank" rel="noopener">Otwórz mapę w pełnym rozmiarze</a>${terrainGuide}</details>`
    : '';
  const hasPositions = Boolean(step.has_positions);
  const requiresBoardAssignment = Boolean(step.requires_board_assignment);
  const canConfirm = Boolean(step.can_confirm);
  const selectedPosition = step.selected_position;
  const mechanics = Array.isArray(step.mechanics) ? step.mechanics : [];
  const mechanicsHtml = mechanics.length
    ? `<div class="setup-mechanics"><b>Zasady tego kroku</b><ul>${mechanics.map(item => `<li>${esc(item)}</li>`).join('')}</ul></div>`
    : '';
  const assignmentButtons = (step.available_positions || []).map(pos =>
    `<button class="secondary" onclick="selectBoardPosition(${Number(pos[0])}, ${Number(pos[1])})">(${Number(pos[0])},${Number(pos[1])})</button>`
  ).join('');
  return `
    <div class="message setup-current-command" tabindex="-1">
      <b>Krok ${Number(setup.current_index) + 1}/${setup.step_count}: ${esc(step.label || '')}</b><br>
      ${esc(step.message || '')}
      ${requiresBoardAssignment ? `<p><b>Aktualnie ustaw:</b> ${esc(step.assignment_actor_name || '-')}</p><p>${(step.available_positions || []).length > 1 ? 'Kliknij jedno z podświetlonych wolnych pól na planszy. Możesz zmienić wybór przed zatwierdzeniem.' : 'Dostępne jest jedno pole — ustaw na nim figurkę i zatwierdź.'}</p>` : ''}
      ${requiresBoardAssignment && setup.battle_briefing?.length ? '<p><b>Wybór szyku:</b> lewy bok prowadzi do osłon, środek do krótkiego podejścia przez koleiny, prawy bok do suchego obejścia. Możecie swobodnie rozdzielić bohaterów w całej strefie.</p>' : ''}
      ${hasPositions && !requiresBoardAssignment ? `<p>Sprawdź pola podświetlone na planszy kolorem ${esc(step.color || 'wskazanym przez grę')}.</p>` : ''}
      ${mechanicsHtml}
      ${selectedPosition ? `<p><b>Wybrane pole:</b> (${selectedPosition.join(', ')}). Ustaw tutaj figurkę.</p>` : ''}
      <p>${canConfirm ? 'Naciśnij niebieski przycisk <b>✓ Potwierdź</b> na planszy.' : 'Najpierw wybierz pole. Przycisk ✓ zaświeci się po wyborze.'}</p>
    </div>
    <details class="encounter-position-fallback"><summary>Awaryjne sterowanie ekranowe</summary>
      ${requiresBoardAssignment ? `<div class="row">${assignmentButtons}</div>` : ''}
      <button onclick="confirmEncounterSetup()" ${canConfirm ? '' : 'disabled'}>✓ Potwierdź ustawienie</button>
    </details>
    ${mapPreview}
  `;
}
function encounterStealthHtml(setup, stealth) {
  if (!setup || setup.status !== 'completed' || !stealth || state.combat) return '';
  if (stealth.completed) {
    const attempts = (stealth.actors || []).filter(actor => actor.attempted).length;
    return `<div class="result"><b>Skradanie przed walką zakończone</b><br>Zapisane próby: ${attempts}. Wyniki przejdą do pierwszej rundy.</div>`;
  }
  const actors = (stealth.actors || []).map(actor => {
    const result = actor.result || null;
    if (result) {
      const hidden = (result.hidden_from || []).map(item => item.actor_name).join(', ') || 'nikt';
      const detected = (result.detected_by || []).map(item => item.actor_name).join(', ') || 'nikt';
      return `<div class="status-item"><b>${esc(actor.actor_name)}</b><span>Stealth ${Number(result.total)} — ukryty przed: ${esc(hidden)}; wykrywają: ${esc(detected)}.</span></div>`;
    }
    return `<div class="status-item"><b>${esc(actor.actor_name)}</b><span>Modyfikator Stealth: ${signedNumber(Number(actor.modifier || 0))}${actor.roll_mode === 'disadvantage' ? ' · utrudnienie' : ''}</span>${actor.can_attempt ? `<button onclick="startPrecombatStealthRoll('${esc(actor.actor_id)}')">Spróbuj się ukryć</button><div class="precombat-stealth-roll" id="precombat-roll-${esc(actor.actor_id)}" hidden>${d20RollInputsHtml(`precombat-stealth-${actor.actor_id}`, actor.roll_mode)}<button onclick="submitPrecombatStealth('${esc(actor.actor_id)}')">Zapisz rzut</button></div>` : ''}</div>`;
  }).join('');
  return `
    <div class="message"><b>Skradanie przed walką</b><br>${esc(stealth.instruction || '')}</div>
    <div class="status-list">${actors}</div>
    <button class="secondary" onclick="finishPrecombatStealth()">Zakończ etap i przejdź do inicjatywy</button>
    <p class="muted">Niewykorzystane próby przepadają po zakończeniu tego etapu.</p>
  `;
}
function encounterInitiativeHtml(setup, initiative, stealth) {
  if (!setup || setup.status !== 'completed' || state.combat) return '';
  if (stealth && !stealth.completed) return '';
  if (!initiative) {
    return `
      <div class="message"><b>Inicjatywa</b><br>Setup zakończony. Teraz ustalcie kolejność tur.<p>Naciśnij niebieski przycisk <b>✓ Potwierdź</b> na planszy, aby rozpocząć inicjatywę.</p></div>
      <details class="encounter-position-fallback"><summary>Awaryjne sterowanie ekranowe</summary><button onclick="startEncounterInitiative()">✓ Rozpocznij inicjatywę</button></details>
    `;
  }
  if (initiative.status === 'completed') return '';
  const prompt = initiative.current_prompt || {};
  const hasSecondRoll = Boolean(prompt.requires_second_roll);
  const edge = prompt.encounter_edge || null;
  return `
    <div class="message">
      <b>Rzut inicjatywy ${Number(initiative.current_prompt_index) + 1}/${initiative.prompt_count}</b><br>
      ${esc(prompt.message || 'Wpisz naturalny wynik d20.')}
      ${edge ? `<p><b>Przewaga z eksploracji:</b> ${esc(edge.label || '')}. Rzuć dwiema kośćmi d20; gra wybierze wyższy wynik.</p>` : ''}
    </div>
    <div class="row">
      <label>${hasSecondRoll ? 'Pierwszy wynik d20' : 'Wynik d20'}: <input id="encounter-initiative-roll" type="number" min="1" max="20" value="10"></label>
      ${hasSecondRoll ? '<label>Drugi wynik d20: <input id="encounter-initiative-roll-2" type="number" min="1" max="20" value="10"></label>' : ''}
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
  const interrupt = combatInterruptPresentation(combat);
  return `
    <div class="combat-shell${interrupt ? ' has-interrupt' : ''}">
      ${combatInitiativeRibbonHtml(combat, order)}
      ${combat.battle_briefing?.length ? `<details class="battle-rules"><summary>Cel starcia i zasady terenu</summary><ul>${combat.battle_briefing.map(rule => `<li>${esc(rule)}</li>`).join('')}</ul></details>` : ''}
      ${combatTurnHudHtml(combat)}
      ${pooledManaPointsHtml(combat, null, true)}
      ${miraStealthStatusHtml(combat)}
      <div class="combat-stage">
        <div data-board-input-status>${boardSelectionStatusHtml()}</div>
        ${interrupt ? `<div class="combat-interrupt-banner"><span>Przerwanie</span><b>${esc(interrupt)}</b></div>` : ''}
        ${combatCurrentStepHtml(combat, finished, isAllyTurn, isEnemyTurn, interrupt)}
      </div>
      ${physicalManaHtml(combat)}
      ${combatTurnActorStatsHtml(combat)}
    </div>
    <details class="combat-details">
      <summary>Pole walki, ostatni wynik i szczegóły</summary>
      <section class="combat-section">
        <h4>Ostatni rezultat</h4>
        ${latestCombatMessageHtml()}
      </section>
      ${combatDroppedWeaponsHtml(combat)}
      ${combatBattlefieldLootHtml(combat)}
      ${combatActiveEffectsHtml(combat)}
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
            <span>${esc(actor.faction)} | rozmiar ${esc(actor.size_label || actor.size || '-')} | HP ${esc(actorHpLabel(actor))} / AC ${esc(actorAcLabel(actor))} | pole (${esc(actor.position[0])},${esc(actor.position[1])})</span>
            ${damageAffinitiesHtml(actor)}
            ${statusChipsHtml(combatActorChips(actor), 'Brak aktywnych statusów.')}
          </div>
        `).join('')}
      </div>
    </details>
  `;
}
function miraStealthStatusHtml(combat) {
  const actor = combat.current_actor || {};
  if (actor.id !== 'mira' || !actor.hidden) return '';
  const observers = actor.hidden.observers || [];
  const list = sees => observers.filter(o => Boolean(o.sees_actor) === sees).map(o => esc(o.name)).join(', ') || 'nikt';
  const passive = combat.physical_mana ? '+1k6 za ukrycie przed celem lub flankę; +2k6 za oba, raz we własnej turze.' : 'Premia Ataku z cienia zależy od ukrycia przed wybranym celem i flanki.';
  return `<aside class="mira-stealth-status" role="status"><b>Ukrycie Miry · wynik ${actor.hidden.stealth_total}</b>
    <span class="stealth-unaware">Turkusowe · nie widzą Miry: ${list(false)}</span><span class="stealth-aware">Pomarańczowe · widzą Mirę: ${list(true)}</span>
    <details><summary>Atak z cienia i kolory planszy</summary><p>${passive} Atak kończy ukrycie. Podgląd akcji zastępuje kolory obserwatorów; po anulowaniu wracają.</p></details></aside>`;
}
function focusCombatDecision() {
  if (state?.training_arena?.tutorial?.notice) return;
  const settingUp = !state?.combat && state?.encounter_setup?.status !== 'completed' && state?.encounter_setup?.current_step;
  if ((!state?.combat && !settingUp) || keyboardRollWizard || busy) return;
  requestAnimationFrame(() => {
    if (state?.training_arena?.tutorial?.notice) return;
    if (settingUp) {
      const card = document.querySelector('.setup-current-command');
      if (!card || card.closest('[hidden]')) return;
      const key = `${state.training_arena?.tutorial?.index}:${state.encounter_setup.scenario_name}:${state.encounter_setup.current_index}:${state.encounter_setup.current_step.label}`;
      const rect = card.getBoundingClientRect();
      const header = document.querySelector('.app-shell-header')?.getBoundingClientRect().bottom || 0;
      if (focusCombatDecision.setupKey !== key || rect.top < header || rect.top > window.innerHeight * .5) {
        card.focus({preventScroll:true});
        card.scrollIntoView({block:'start', behavior:'auto'});
      }
      focusCombatDecision.setupKey = key;
      return;
    }
    const card = document.querySelector('.combat-current-step');
    if (!card) return;
    const idle = Boolean(card.querySelector('.combat-keyboard-waiting'));
    const anchor = idle ? document.querySelector('.combat-turn-hud') || card : card;
    const rect = anchor.getBoundingClientRect();
    const header = document.querySelector('.app-shell-header')?.getBoundingClientRect().bottom || 0;
    if (rect.top < header || card.getBoundingClientRect().bottom > window.innerHeight || rect.top > window.innerHeight * .5) anchor.scrollIntoView({block:'start', behavior:'auto'});
  });
}

function combatInitiativeRibbonHtml(combat, order) {
  const actors = combat.actors || [];
  const actorById = new Map(actors.map(actor => [String(actor.id), actor]));
  const entries = (order && order.length ? order : actors).map(entry => {
    const id = String(entry.actor_id || entry.id || '');
    const actor = actorById.get(id) || entry;
    return {
      id,
      name: entry.actor_name || actor.name || '-',
      portrait_url: actor.portrait_url || null,
      total: entry.total === undefined ? null : entry.total,
      faction: actor.faction || 'neutral',
      defeated: Boolean(actor.defeated),
    };
  });
  if (!entries.length) return '';
  const currentId = String((combat.current_actor || {}).id || '');
  return `
    <div class="initiative-ribbon" aria-label="Kolejność inicjatywy">
      <span class="initiative-ribbon-label">Inicjatywa</span>
      <div class="initiative-ribbon-order">${entries.map(entry => `
        <div class="initiative-actor ${esc(entry.faction)}${entry.id === currentId ? ' current' : ''}${entry.defeated ? ' defeated' : ''}"${entry.id === currentId ? ' aria-current="step"' : ''}>
          ${actorPortraitHtml(entry, 'initiative')}<span>${esc(entry.name)}</span>${entry.total === null ? '' : `<b>${esc(entry.total)}</b>`}
        </div>
      `).join('')}</div>
    </div>
  `;
}
function combatTurnHudHtml(combat) {
  const actor = combat.current_actor || {};
  const hp = Math.max(0, Number(actor.hp || 0));
  const maxHp = Math.max(1, Number(actor.max_hp === undefined || actor.max_hp === null ? actor.hp || 1 : actor.max_hp));
  const hpPercent = Math.max(0, Math.min(100, Math.round((hp / maxHp) * 100)));
  return `
    <div class="combat-turn-hud ${esc(actor.faction || 'neutral')}">
      <div class="combat-turn-identity">
        ${actorPortraitHtml(actor, 'turn')}
        <div>
        <span>Aktywna tura · runda ${esc(combat.round_number || '-')}</span>
        <b>${esc(actor.name || '-')}</b>
        </div>
      </div>
      <div class="combat-hp" aria-label="Punkty życia ${esc(actorHpLabel(actor))}">
        <span><b>PW ${esc(actorHpLabel(actor))}</b><small>KP ${esc(actorAcLabel(actor))}</small></span>
        <i><em style="width:${hpPercent}%"></em></i>
      </div>
      <div class="combat-turn-resources">${combatMiniStatusHtml(combat)}</div>
    </div>
  `;
}
function combatInterruptPresentation(combat) {
  if (defensiveSpellReaction(combat)) return 'Możesz rzucić czar obronny po trafieniu';
  if (combat.pending_ready_attack) return 'Przygotowana akcja czeka na decyzję';
  if (combat.pending_enemy_opportunity_attack) return 'Możliwy atak okazyjny bohatera';
  if (combat.pending_opportunity_movement) return 'Ruch może wywołać atak okazyjny';
  if (combat.pending_concentration_check) return 'Obowiązkowy test koncentracji';
  if (combat.death_save_required) return 'Obowiązkowy rzut śmierci';
  if ((combat.condition_saves || []).length) return 'Obowiązkowy rzut obronny';
  return '';
}
function combatDroppedWeaponsHtml(combat) {
  const dropped = combat.dropped_weapons || [];
  if (!dropped.length) return '';
  return `
    <div class="combat-last-result">
      <h4>Broń na planszy</h4>
      ${dropped.map(item => `<p><b>${esc(item.name)}</b> — pole (${esc(item.position[0])},${esc(item.position[1])}), upuszczono w rundzie ${esc(item.dropped_round)}</p>`).join('')}
      <p class="muted">Podnoszenie i interakcję z tym polem dodamy po ustaleniu docelowego modelu interakcji.</p>
    </div>
  `;
}
function combatBattlefieldLootHtml(combat) {
  const loot = combat.battlefield_loot || [];
  if (!loot.length) return '';
  return `
    <div class="combat-last-result">
      <h4>Łup pola walki</h4>
      ${loot.map(bundle => `
        <p><b>${esc(bundle.label)}</b> — pole (${esc(bundle.position[0])},${esc(bundle.position[1])}):
        ${(bundle.items || []).map(item => `${esc(item.name)} ×${esc(item.quantity)}`).join(', ')}</p>
      `).join('')}
      <p class="muted">Kliknij podświetlone pole na planszy, aby zebrać odzyskaną amunicję.</p>
    </div>
  `;
}
function combatCurrentStepHtml(combat, finished, isAllyTurn, isEnemyTurn, interrupt = '') {
  const phase = combatPresentationPhase(combat, finished, isAllyTurn, isEnemyTurn);
  const actionMenuStep = Boolean(isAllyTurn && combat.turn_action_menu && phase === 'choice' && !interrupt);
  return `
    <div class="combat-current-step${interrupt ? ' combat-interrupt-dialog' : ''}${combat.enemy_turn_result ? ' enemy-attack-result' : ''}${actionMenuStep ? ' action-menu-step' : ''}" data-stage="${esc(phase)}"${interrupt ? ' role="dialog" aria-modal="true" aria-label="Przerwanie walki"' : ''}>
      ${sharedCommandStepHtml(combat)}
      ${actionMenuStep ? '' : combatPhaseStepsHtml(phase)}
      ${resultAck || actionMenuStep || combat.enemy_turn_result || combat.shared_mana?.command?.stage ? '' : combatMainPromptHtml(combat, finished, isAllyTurn, isEnemyTurn)}
      ${phase === 'result' && !resultAck && !combat.enemy_turn_result && !combat.shield_bash ? `<div class="combat-inline-result">${latestCombatMessageHtml()}</div>` : ''}
      ${combat.shared_mana?.command?.stage ? '' : combatCardReminderHtml(combat, phase, isAllyTurn)}
      <div class="combat-action-card">
        ${finished ? '<button onclick="resolveCombatOutcome()">Zastosuj wynik encountera</button>' : combatPrimaryActionHtml(combat, isAllyTurn, isEnemyTurn)}
      </div>
    </div>
  `;
}
function combatCardReminderHtml(combat, phase, isAllyTurn) {
  const reminders = (combat.card_reminders || []).filter(reminder => {
    if (reminder.trigger_window === 'action_selection') return isAllyTurn && phase === 'choice' && !combat.turn_action_menu;
    return true;
  });
  if (!reminders.length) return '';
  const reactions = reminders.filter(reminder => reminder.trigger_window !== 'action_selection');
  if (reactions.length) {
    return reactions.map(reminder => `
      <aside class="combat-card-reminder reaction" role="status" aria-label="Możliwa reakcja kartą">
        <span class="combat-card-reminder-icon" aria-hidden="true"></span>
        <div>
          <small>Możliwa reakcja</small>
          <b>${esc(reminder.owner_actor_name)} — ${esc(reminder.label)}${reminder.resource_note ? ` (${esc(reminder.resource_note)})` : ''}</b>
          <p>Zeskanuj kartę albo kontynuuj bez niej.</p>
        </div>
      </aside>
    `).join('');
  }
  const names = reminders.map(reminder =>
    reminder.resource_note
      ? `${reminder.label} (${reminder.resource_note})`
      : reminder.label
  );
  return `
    <aside class="combat-card-reminder action" role="status" aria-label="Dostępne karty walki">
      <span class="combat-card-reminder-icon" aria-hidden="true"></span>
      <div>
        <small>Dostępne karty ${esc(reminders[0].owner_actor_name)}</small>
        <b>${names.map(manaTextHtml).join(' · ')}</b>
        <p>Możesz zeskanować kartę albo wybrać zwykłą akcję na planszy.</p>
      </div>
    </aside>
  `;
}
function combatPresentationPhase(combat, finished, isAllyTurn, isEnemyTurn) {
  if (resultAck) return 'result';
  if (combat.shield_bash) return combat.shield_bash.stage === 'result' ? 'result' : 'roll';
  if (finished || combat.enemy_turn_result) return 'result';
  if (defensiveSpellReaction(combat) || combat.death_save_required || combat.pending_concentration_check || combat.pending_enemy_saving_throw || (combat.pending_spell_dispel && combat.pending_spell_dispel.stage === 'ability_check') || (combat.condition_saves || []).length) return 'roll';
  const rollPending = [
    combat.pending_player_attack,
    combat.pending_area_spell,
    combat.pending_enemy_opportunity_attack,
    combat.pending_ready_attack,
  ].find(pending => pending && (pending.stage === 'attack_roll' || pending.stage === 'damage_roll'));
  if (rollPending || combat.pending_player_healing || combat.pending_combat_skill_check || combat.pending_combat_shove || combat.pending_combat_grapple) return 'roll';
  if (combat.movement_preview || combat.pending_opportunity_movement || combat.enemy_turn_intent || combat.enemy_turn_preview || combat.pending_combat_interaction || combat.pending_combat_help || combat.class_feature_targeting || combat.pending_concentration_action || combat.pending_multi_target_damage_spell || combat.pending_summon || combat.pending_magic_movement || combat.pending_spell_debuff || combat.pending_spell_dispel || combat.pending_combat_ready) return 'preview';
  if (combat.pending_player_attack || combat.pending_area_spell) return 'preview';
  if (isEnemyTurn) return 'preview';
  return 'choice';
}
function combatPhaseStepsHtml(activePhase) {
  const phases = [
    {id: 'choice', label: 'Wybór'},
    {id: 'preview', label: 'Podgląd'},
    {id: 'roll', label: 'Rzut'},
    {id: 'result', label: 'Wynik'},
  ];
  const activeIndex = phases.findIndex(phase => phase.id === activePhase);
  return `<div class="combat-phase-steps" aria-label="Przebieg decyzji">${phases.map((phase, index) => `<span class="${index < activeIndex ? 'complete' : ''}${index === activeIndex ? ' active' : ''}">${esc(phase.label)}</span>`).join('')}</div>`;
}
function combatMainPromptHtml(combat, finished, isAllyTurn, isEnemyTurn) {
  return `
    <div class="combat-prompt">
      <b>${esc(combatPromptTitle(combat, finished, isAllyTurn, isEnemyTurn))}</b>
      <span>${manaTextHtml(combatInstructionText(combat, finished, isAllyTurn, isEnemyTurn))}</span>
    </div>
  `;
}
function combatPromptTitle(combat, finished, isAllyTurn, isEnemyTurn) {
  if (resultAck) return resultAck.title || 'Wynik';
  if (finished) return 'Walka zakończona';
  const actor = combat.current_actor || {};
  if (combat.death_save_required) return `${actor.name || 'Bohater'}: rzut śmierci`;
  if (combat.pending_concentration_check) {
    const pendingActor = combat.pending_concentration_check.actor || {};
    return `${pendingActor.name || 'Bohater'}: test koncentracji`;
  }
  if (isEnemyTurn) {
    const defensiveSpell = defensiveSpellReaction(combat);
    if (defensiveSpell) return `${defensiveSpell.label || 'Czar obronny'}: reakcja po trafieniu`;
    if (combat.pending_ready_attack) return `Tura ${actor.name || 'przeciwnika'}: Ready`;
    if (combat.pending_enemy_opportunity_attack) return `Tura ${actor.name || 'przeciwnika'}: reakcja bohatera`;
    if (combat.pending_enemy_saving_throw) return `${(combat.pending_enemy_saving_throw.target || {}).name || 'Bohater'}: rzut obronny`;
    if (combat.enemy_turn_result) {
      const result = combat.enemy_turn_result;
      const outcome = result.hit === true ? (result.critical ? 'TRAFIENIE KRYTYCZNE' : 'TRAFIENIE') : (result.hit === false ? 'PUDŁO' : 'WYNIK');
      return `ATAK PRZECIWNIKA — ${outcome}`;
    }
    const retaliationSpell = classFeatureReaction(combat, 'retaliation_spell');
    if (retaliationSpell) {
      return `
        <p><b>${esc(retaliationSpell.label || 'Czar odwetowy')}</b></p>
        <p>Otrzymałeś obrażenia od napastnika. Możesz zużyć reakcję i slot, aby odpowiedzieć czarem.</p>
        <div class="row">
          <button data-allow-busy="true" onclick="castRetaliationSpellReaction()">Rzuć czar</button>
          <button class="secondary" data-allow-busy="true" onclick="skipRetaliationSpellReaction()">Nie reaguj</button>
        </div>
      `;
    }
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
  if (isAllyTurn && combat.pending_summon) return `Tura ${actor.name || 'gracza'}: wybierz pole przywołania`;
  if (isAllyTurn && combat.pending_magic_movement) return `Tura ${actor.name || 'gracza'}: magiczny ruch`;
  if (isAllyTurn && combat.pending_spell_debuff) return `Tura ${actor.name || 'gracza'}: wybierz cel osłabienia`;
  if (isAllyTurn && combat.pending_spell_dispel) {
    return combat.pending_spell_dispel.stage === 'ability_check'
      ? `Tura ${actor.name || 'gracza'}: test rozproszenia`
      : `Tura ${actor.name || 'gracza'}: wybierz cel rozproszenia`;
  }
  if (combat.shield_bash) return combat.shield_bash.stage === 'result' ? 'Uderzenie tarczą: wynik' : 'Uderzenie tarczą: wpisz rzuty';
  if (isAllyTurn && combat.class_feature_targeting) return `${combat.class_feature_targeting.label}: wybierz cel`;
  if (isAllyTurn && combat.context_menu) return `Tura ${actor.name || 'gracza'}: wybierz akcję`;
  if (isAllyTurn && combat.targeting) {
    return combat.targeting.kind === 'area'
      ? `Tura ${actor.name || 'gracza'}: wybierz obszar czaru`
      : `Tura ${actor.name || 'gracza'}: wybierz cel`;
  }
  if (isAllyTurn && combat.pending_opportunity_movement) return `Tura ${actor.name || 'gracza'}: atak okazyjny`;
  if (isAllyTurn && combat.pending_combat_help) return `Tura ${actor.name || 'gracza'}: Help`;
  if (isAllyTurn && combat.pending_combat_shove) return `Tura ${actor.name || 'gracza'}: Shove`;
  if (isAllyTurn && combat.pending_combat_grapple) return `Tura ${actor.name || 'gracza'}: Grapple`;
  if (isAllyTurn && combat.pending_combat_skill_check) {
    return `Tura ${actor.name || 'gracza'}: ${combat.pending_combat_skill_check.action === 'hide' ? 'Hide' : 'Search'}`;
  }
  if (isAllyTurn && combat.pending_concentration_action) return `Tura ${actor.name || 'gracza'}: koncentracja`;
  if (isAllyTurn && combat.pending_multi_target_damage_spell) return `Tura ${actor.name || 'gracza'}: rozdziel pociski`;
  if (isAllyTurn && combat.pending_combat_ready) return `Tura ${actor.name || 'gracza'}: Ready`;
  if (isAllyTurn && combat.pending_combat_interaction) return `Tura ${actor.name || 'gracza'}: wybierz interakcję`;
  if (isAllyTurn && combat.movement_preview) return `Tura ${actor.name || 'gracza'}: potwierdź ruch`;
  if (isAllyTurn) return `Tura ${actor.name || 'gracza'}: wybierz pole na planszy`;
  return `Tura ${actor.name || '-'}`;
}
function combatInstructionText(combat, finished, isAllyTurn, isEnemyTurn) {
  if (combat.shield_bash) return combat.shield_bash.stage === 'result' ? 'Sprawdź test sporny, obrażenia i pole odepchnięcia. ✓ na planszy zastosuje wynik.' : 'Rzuć wskazaną kością. Ustaw naturalny wynik przyciskami − / + i potwierdź ✓ na planszy.';
  if (resultAck) return resultAck.body || 'Przeczytaj wynik i potwierdź.';
  if (finished) {
    const result = combat.encounter_result || {};
    const recovery = combat.ammunition_recovery || {};
    const recoveryText = Number(recovery.recoverable || 0) > 0
      ? ` Po minucie przeszukiwania pola walki można odzyskać ${recovery.recoverable} z ${recovery.fired} wystrzelonych pocisków. Kliknij podświetlony stos, aby go zebrać.`
      : '';
    return (result.message || 'Zastosuj wynik encountera, żeby wrócić do eksploracji.') + recoveryText;
  }
  if (isAllyTurn && combat.class_feature_targeting) return 'Wybierz podświetlony cel na planszy. ✓ potwierdza, ↩ anuluje.';
  const actor = combat.current_actor || {};
  if (combat.physical_mana?.needs_attack_count) return "Zadeklaruj liczbę oddzielnych ataków. Każdy kosztuje 1 dowolną manę.";
  if (combat.death_save_required) {
    const saves = actor.death_saves || {};
    return `Rzuć d20. Wynik 10 lub więcej to sukces. Sukcesy: ${saves.successes || 0}/3, porażki: ${saves.failures || 0}/3.`;
  }
  if (combat.pending_concentration_check) {
    return combat.pending_concentration_check.instruction || 'Rzuć CON save, żeby utrzymać koncentrację.';
  }
  if (isEnemyTurn) {
    const defensiveSpell = defensiveSpellReaction(combat);
    if (defensiveSpell) {
      const preview = combat.enemy_turn_preview || {};
      return `${preview.target_name || 'Bohater'} został trafiony. ${defensiveSpell.label || 'Czar obronny'} podniesie AC o ${defensiveSpell.value || 0} i może zamienić trafienie w pudło.`;
    }
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
    if (combat.pending_enemy_saving_throw) {
      return combat.pending_enemy_saving_throw.instruction || 'Rzuć fizyczne d20 i wpisz naturalny wynik rzutu obronnego.';
    }
    if (combat.enemy_turn_result) {
      const result = combat.enemy_turn_result;
      const damage = result.damage === null || result.damage === undefined ? 0 : result.damage;
      const hp = result.damage_result
        ? ` HP celu: ${result.damage_result.hp_before} → ${result.damage_result.hp_after}.`
        : '';
      return `Silnik wykonał rzut przeciwnika automatycznie. Obrażenia: ${damage}.${hp} Dopiero potem potwierdź zakończenie jego tury.`;
    }
    const intent = combat.enemy_turn_intent || null;
    if (intent) return `${intent.message || 'Przeciwnik deklaruje zamiar.'} Potwierdź, żeby przejść do wykonania na planszy.`;
    const preview = combat.enemy_turn_preview || null;
    if (preview && preview.kind === 'movement') {
      return `Przestaw ${preview.enemy_name} na pole (${preview.destination[0]},${preview.destination[1]}), uruchom skan i kliknij pole docelowe.`;
    }
    if (preview && preview.kind === 'attack') {
      return `${preview.enemy_name} atakuje ${preview.target_name}. Uruchom skan i kliknij podświetlony cel.`;
    }
    return 'Naciśnij ✓ albo przycisk, żeby gra pokazała zamiar przeciwnika.';
  }
  if (!isAllyTurn) return 'Ten aktor nie ma automatycznych kontrolek w MVP. Możesz zakończyć turę.';
  if (combat.context_menu) {
    return 'Wybierz podświetloną runę akcji na planszy albo przycisk na ekranie. ✓ zatwierdza, ↩ wraca.';
  }
  if (combat.targeting) {
    const targeting = combat.targeting;
    const choice = targeting.kind === 'area'
      ? 'Kliknij podświetlony kierunek lub środek obszaru.'
      : 'Kliknij podświetlonego przeciwnika.';
    return `${targeting.source_name || 'Wybrany czar'} — ${targeting.kind === 'area' ? 'czar obszarowy' : 'pojedynczy cel'}. ${choice} Pola ruchu są wyłączone. Kliknij pole aktywnego bohatera, aby wrócić do menu.`;
  }
  if (combat.pending_opportunity_movement) {
    const pendingOpportunity = combat.pending_opportunity_movement;
    const names = (pendingOpportunity.threats || []).map(actor => actor.name).join(', ') || 'wróg';
    return `Ten ruch opuszcza zasięg: ${names}. Potwierdź, żeby rozstrzygnąć ataki okazyjne i wykonać ruch.`;
  }
  if (combat.pending_combat_help) {
    return 'Wybierz sojusznika i przeciwnika. Sojusznik dostanie przewagę na następny atak przeciw temu celowi.';
  }
  if (combat.pending_combat_shove) {
    const shove = combat.pending_combat_shove;
    return `${shove.attacker_name || 'Bohater'} wykonuje Strength (Athletics), a ${shove.target_name || 'cel'} broni się automatycznie przez ${(shove.defender_check || {}).label || 'Athletics/Acrobatics'}.`;
  }
  if (combat.pending_combat_grapple) {
    const grapple = combat.pending_combat_grapple;
    return `${grapple.actor_name || 'Bohater'} wykonuje ${(grapple.actor_check || {}).label || 'Athletics'}, a ${grapple.opponent_name || 'przeciwnik'} odpowiada automatycznie przez ${(grapple.opponent_check || {}).label || 'Athletics/Acrobatics'}.`;
  }
  if (combat.pending_combat_skill_check) {
    return combat.pending_combat_skill_check.instruction || 'Rzuć d20 i wpisz naturalny wynik.';
  }
  if (combat.pending_concentration_action) {
    return 'Wybierz sojusznika. Czar zużyje akcję i slot, a wcześniejsza koncentracja tego aktora zostanie zakończona.';
  }
  if (combat.pending_multi_target_damage_spell) {
    const pending = combat.pending_multi_target_damage_spell;
    return `Wskaż na planszy cel każdego pocisku (${pending.selected_count || 0}/${pending.projectile_count || 0}). Ten sam przeciwnik może zostać wskazany kilka razy.`;
  }
  if (combat.pending_summon) {
    return 'Wybierz wolne, widoczne pole w zasięgu. Slot i akcja zostaną zużyte dopiero po potwierdzeniu.';
  }
  if (combat.pending_magic_movement) {
    if (combat.pending_magic_movement.action_id === 'field_medic_step') {
      return 'Krok ratowniczki: wybierz sąsiednie pole, aby wykonać darmowy ruch 5 stóp bez ataku okazyjnego, albo wybierz Nie.';
    }
    return combat.pending_magic_movement.kind === 'teleport'
      ? 'Wybierz widoczne, wolne pole teleportacji. Teleport nie zużyje ruchu.'
      : 'Wybierz podświetlony cel. Po nieudanym save zostanie przesunięty do ostatniego legalnego pola.';
  }
  if (combat.pending_spell_debuff) {
    const pendingDebuff = combat.pending_spell_debuff;
    return `Wybierz podświetlonego przeciwnika. Wykona automatyczny ${pendingDebuff.save_ability || ''} save przeciw ST ${pendingDebuff.save_dc || '-'}.`;
  }
  if (combat.pending_spell_dispel) {
    const pendingDispel = combat.pending_spell_dispel;
    const check = pendingDispel.current_check || {};
    if (pendingDispel.stage === 'ability_check') {
      return `Rzuć fizyczne d20 dla testu cechy rzucania czarów. ${check.label || 'Efekt'} wymaga wyniku ST ${check.dc || '-'}.`;
    }
    return 'Wybierz podświetloną istotę z aktywnym efektem czaru. Slot i akcja zostaną zużyte po potwierdzeniu celu.';
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
    const threats = ((pending.positioning || {}).ranged_threats || []);
    const threatText = threats.length
      ? ` Utrudnienie powoduje przeciwnik w zwarciu: ${threats.map(actor => `${actor.name} (${actor.position[0]},${actor.position[1]})`).join(', ')}.`
      : '';
    return `Wybrano cel ${target.name || '-'}. Rzuć d20 na atak ${source.name || ''} i wpisz naturalny wynik.${threatText}`;
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
    return `Wybrano obszar ${source.name || 'czaru'}. Cele: ${targets}. Wskaż inne legalne pole albo potwierdź aktualny podgląd przyciskiem ✓.`;
  }
  if (combat.pending_combat_interaction) {
    const pendingInteraction = combat.pending_combat_interaction;
    return `Wybrano obiekt ${pendingInteraction.object_name || '-'}. Wybierz interakcję i potwierdź przyciskiem ✓.`;
  }
  const movement = combat.movement || {};
  const preview = combat.movement_preview || null;
  const remaining = Number(movement.remaining_feet || 0);
  const extraMovement = Number((combat.turn_action && combat.turn_action.extra_movement_feet) || 0);
  const actionUsed = combat.turn_action && combat.turn_action.action_use === 'action_used';
  if (preview) {
    const dragged = preview.dragged_actor || null;
    const draggedInstruction = dragged
      ? ` Następnie przestaw ${dragged.name || 'chwytaną figurkę'} na różowe pole (${dragged.destination[0]},${dragged.destination[1]}).`
      : '';
    return `Wybrano ruch na (${preview.destination[0]},${preview.destination[1]}). Uruchom skan i kliknij pole docelowe, żeby zatwierdzić.${draggedInstruction}`;
  }
  if (combat.turn_action_menu) {
    const menu = combat.turn_action_menu;
    const selected = (menu.options || [])[Number(menu.selected_index || 0)] || {};
    return menu.stage === 'preview'
      ? `${selected.label || 'Akcja'} — podgląd aktywny. Wskaż cel lub pole na planszy, następnie naciśnij ✓. ↩ anuluje bez kosztu.`
      : 'Wybierz dostępną ikonę na ekranie. Otworzysz podgląd bez zużywania akcji ani zasobu.';
  }
  const selfActionHint = ` Kliknij pole ${actor.name || 'aktywnego bohatera'}, aby otworzyć jego czary, akcje i ekwipunek. Turę możesz zakończyć także przyciskiem obok skanowania.`;
  if (actionUsed && remaining > 0) return `Akcja zużyta. Możesz jeszcze ruszyć się (${remaining} ft).${selfActionHint}`;
  if (actionUsed) return `Akcja zużyta.${selfActionHint}`;
  if (remaining > 0) return `Kliknij Skanuj planszę, a potem wybierz niebieskie pole ruchu, czerwony cel, turkusowego rannego sojusznika albo zielony obiekt.${selfActionHint}`;
  return `Ruch wykorzystany. Możesz wybrać cel albo obiekt.${selfActionHint}`;
}
function combatMiniStatusHtml(combat) {
  const actor = combat.current_actor || {};
  const movement = combat.movement || {};
  const remaining = Number(movement.remaining_feet || 0);
  const extraMovement = Number((combat.turn_action && combat.turn_action.extra_movement_feet) || 0);
  const actionUsed = combat.turn_action && combat.turn_action.action_use === 'action_used';
  const bonusActionUsed = combat.turn_action && combat.turn_action.bonus_action_use === 'action_used';
  const reactionAvailable = !combat.turn_action || combat.turn_action.reaction_available !== false;
  const twoWeapon = combat.two_weapon || {};
  const objectInteractionAvailable = !combat.turn_action || combat.turn_action.object_interaction_available !== false;
  return `
    <div class="combat-mini-status">
      ${actor.faction === 'ally' ? `<span class="${actionUsed ? 'spent' : 'ready'}">Akcja <b>${actionUsed ? 'zużyta' : 'gotowa'}</b></span><span class="${bonusActionUsed ? 'spent' : 'ready'}">Bonus <b>${bonusActionUsed ? 'zużyty' : 'gotowy'}</b></span><span class="${objectInteractionAvailable ? 'ready' : 'spent'}">Interakcja <b>${objectInteractionAvailable ? 'gotowa' : 'zużyta'}</b></span><span class="${reactionAvailable ? 'ready' : 'spent'}">Reakcja <b>${reactionAvailable ? 'gotowa' : 'zużyta'}</b></span><span class="movement">Ruch <b>${esc(remaining)} ft${extraMovement > 0 ? ` +${esc(extraMovement)}` : ''}</b>${movement.speed_reduction === 'grappling' ? `<small>Grapple ${esc(movement.base_speed_feet)}→${esc(movement.effective_speed_feet)} ft</small>` : ''}</span>` : '<span class="enemy-turn">Tura przeciwnika</span>'}
    </div>
    ${statusChipsHtml(combatHudConditionChips(actor), '')}
  `;
}
function combatHudConditionChips(actor) {
  const priority = {danger: 0, penalty: 1, magic: 2, defense: 3, offense: 4, ready: 5, neutral: 6};
  const chips = combatActorChips(actor)
    .filter(chip => !isTurnResourceChip(chip))
    .map((chip, index) => ({...chip, _index: index}))
    .sort((left, right) => (priority[left.tone] ?? 6) - (priority[right.tone] ?? 6) || left._index - right._index);
  const visible = chips.slice(0, 3);
  if (chips.length > visible.length) visible.push({label: `+${chips.length - visible.length}`, tone: 'more', title: 'Pokaż wszystkie stany i efekty.', panelTab: 'states', actorId: actor.id});
  return visible;
}
function combatActorStatusHtml(combat) {
  const actor = combat.current_actor || {};
  const movement = combat.movement || {};
  const remaining = Number(movement.remaining_feet || 0);
  const objectInteractionAvailable = !combat.turn_action || combat.turn_action.object_interaction_available !== false;
  const extraMovement = Number((combat.turn_action && combat.turn_action.extra_movement_feet) || 0);
  const actionUsed = combat.turn_action && combat.turn_action.action_use === 'action_used';
  const bonusActionUsed = combat.turn_action && combat.turn_action.bonus_action_use === 'action_used';
  const reactionAvailable = !combat.turn_action || combat.turn_action.reaction_available !== false;
  const twoWeapon = combat.two_weapon || {};
  return `
    <p><b>${esc(actor.name || '-')}</b> (${esc(actor.faction || '-')}, rozmiar ${esc(actor.size_label || actor.size || '-')})</p>
    <p>Runda ${esc(combat.round_number || '-')}, pole (${esc(actor.position ? actor.position[0] : '-')},${esc(actor.position ? actor.position[1] : '-')})</p>
    <p>HP ${esc(actorHpLabel(actor))} / AC ${esc(actorAcLabel(actor))}</p>
    ${damageAffinitiesHtml(actor)}
    ${combatAurasHtml(combat)}
    ${combatTriggersHtml(actor)}
    ${combatFeaturesHtml(actor)}
    ${actorInventoryHtml(actor)}
    ${actor.faction === 'ally' ? `<p>Akcja: ${actionUsed ? 'zużyta' : 'dostępna'} | Bonus action: ${bonusActionUsed ? 'zużyta' : 'dostępna'} | Darmowa interakcja: ${objectInteractionAvailable ? 'dostępna' : 'zużyta'} | Reakcja: ${reactionAvailable ? 'dostępna' : 'zużyta'} | Ruch: ${esc(remaining)} ft${extraMovement > 0 ? ` (+${esc(extraMovement)} Dash)` : ''}${movement.speed_reduction === 'grappling' ? ` | Grapple: szybkość ${esc(movement.base_speed_feet)} → ${esc(movement.effective_speed_feet)} ft` : ''}</p>${twoWeapon.available ? `<p><b>Atak drugą bronią dostępny:</b> ${(twoWeapon.source_names || []).map(esc).join(', ')} — wybierz przeciwnika.</p>` : ''}` : ''}
    ${statusChipsHtml(combatActorChips(actor), 'Brak statusów aktywnego aktora.')}
  `;
}
function combatActorChips(actor) {
  const chips = [...((actor && actor.status_chips) || actorEffectChips(actor || {}))];
  if (actor && actor.hidden) {
    const observerStates = actor.hidden.observers || [];
    const hiddenFrom = observerStates.filter(observer => !observer.sees_actor);
    const detectedBy = observerStates.filter(observer => observer.sees_actor);
    const exposedPanic = Boolean(actor.hidden.visible_observer_attack_advantage) && detectedBy.length > 0;
    const hiddenNames = hiddenFrom.map(observer => observer.name || observer.actor_id).join(', ');
    const detectingNames = detectedBy.map(observer => observer.name || observer.actor_id).join(', ');
    const hiddenLabel = String(actor.id) === 'mira' ? 'Ukryta' : 'Ukryty';
    chips.push({
      label: exposedPanic
        ? `Panika po zdemaskowaniu (${actor.hidden.stealth_total})`
        : `${hiddenLabel} przed ${hiddenFrom.length}/${observerStates.length} wrogów`,
      tone: exposedPanic ? 'danger' : 'ready',
      title: exposedPanic
        ? `Widzą Mirę: ${detectingNames}. Mają przewagę w atakach przeciw niej w tej sesji skradania.${hiddenNames ? ` Nadal ukryta przed: ${hiddenNames}.` : ''}`
        : (hiddenNames ? `${hiddenLabel} przed: ${hiddenNames}. Wynik ukrycia: ${actor.hidden.stealth_total}.` : 'Tryb skradania aktywny'),
    });
  }
  return chips;
}

function combatAurasHtml(combat) {
  const auras = (combat && combat.auras) || [];
  if (!auras.length) return '';
  const descriptions = {
    saving_throw_bonus: aura => `+${aura.value} do rzutów obronnych`,
    bless_aura_source: aura => `+1k${aura.die_sides || 4} do ataków i rzutów obronnych`,
    divine_care_aura_source: aura => `-${Math.abs(Number(aura.value || 0))} do ataku i obrażeń wrogów`,
    healing_grace_aura_source: aura => `premia 1k${aura.die_sides || 8}${Number(aura.modifier || 0) >= 0 ? '+' : ''}${aura.modifier || 0} do leczenia`,
  };
  return `<div class="combat-aura-list"><b>Aktywne aury</b>${auras.map(aura => {
    const describe = descriptions[aura.effect_kind];
    const effect = describe ? describe(aura) : `${aura.value || 0} ${aura.effect_kind || ''}`;
    const rounds = aura.remaining_rounds == null ? '' : ` · ${aura.remaining_rounds} rund`;
    const uses = aura.uses_maximum ? ` · aktywacje ${aura.value}/${aura.uses_maximum}` : '';
    const preview = aura.temporary
      ? `<button class="secondary aura-preview-button${aura.preview_selected ? ' selected' : ''}" data-allow-busy="true" onclick="previewCombatAura('${esc(aura.id)}')">${aura.preview_selected ? 'Ukryj zasięg' : 'Pokaż zasięg'}</button>`
      : '';
    return `<div class="combat-aura-row"><span><strong>${esc(aura.label)}</strong> · ${esc(aura.radius_feet)} ft · ${esc(effect)}${esc(rounds)}${esc(uses)}<small>${esc(aura.source_actor_name)} · obejmuje ${esc((aura.affected_actor_ids || []).length)} figurki</small></span>${preview}</div>`;
  }).join('')}</div>`;
}

async function previewCombatAura(auraId) {
  try {
    const res = await fetch('/api/combat/aura-preview', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({aura_id: auraId || ''}),
    });
    const data = await res.json();
    if (!res.ok) alert(data.error || 'Nie udało się włączyć podglądu aury.');
    state = data.state || data;
    synchronizeBoardSelection({force: true});
    render();
  } catch (_error) {
    alert('Nie udało się połączyć z aplikacją podczas podglądu aury.');
  }
}

function combatTriggersHtml(actor) {
  const triggers = (actor && actor.triggers) || [];
  if (!triggers.length) return '';
  const eventLabels = {
    attack_hit: 'po trafieniu',
    damage_taken: 'po otrzymaniu obrażeń',
    actor_moved: 'po ruchu',
    turn_start: 'na początku tury',
    turn_end: 'na końcu tury',
    short_rest_completed: 'po short reście',
    long_rest_completed: 'po long reście',
    encounter_ended: 'po encounterze',
  };
  return `<p class="muted"><b>Triggery:</b> ${triggers.map(trigger => `${esc(trigger.label)} (${esc(eventLabels[trigger.event_type] || trigger.event_type)})`).join(', ')}</p>`;
}

function combatFeaturesHtml(actor) {
  const features = (actor && actor.features) || [];
  if (!features.length) return '';
  const sourceLabels = {
    monster: 'potwór',
    item: 'przedmiot',
    race: 'rasa',
    species: 'rasa/gatunek',
    background: 'pochodzenie',
    class: 'klasa',
    subclass: 'podklasa',
    feat: 'feat',
    scenario: 'scenariusz',
  };
  const resourceById = new Map(((actor && actor.resource_pools) || []).map(pool => [pool.id, pool]));
  return `<div class="actor-features"><b>Cechy:</b>${features.map(feature => {
    const mechanics = [];
    if ((feature.resource_ids || []).length) mechanics.push(`zasoby: ${(feature.resource_ids || []).map(resourceId => {
      const pool = resourceById.get(resourceId);
      if (!pool) return esc(resourceId);
      const recharge = pool.recharge ? `, Recharge ${esc(pool.recharge.minimum_roll)}–${esc(pool.recharge.die_sides)}` : '';
      return `${esc(pool.label)} ${esc(pool.current)}/${esc(pool.maximum)}${recharge}`;
    }).join(', ')}`);
    if ((feature.action_ids || []).length) mechanics.push(`akcje: ${(feature.action_ids || []).map(esc).join(', ')}`);
    if ((feature.trigger_ids || []).length) mechanics.push(`triggery: ${(feature.trigger_ids || []).map(esc).join(', ')}`);
    if ((feature.aura_ids || []).length) mechanics.push(`aury: ${(feature.aura_ids || []).map(esc).join(', ')}`);
    const source = sourceLabels[feature.source_kind] || feature.source_kind || '-';
    return `<p class="muted"><b>${esc(feature.label)}</b> — ${esc(feature.description || 'Brak opisu.')} <span><b>Mechanika:</b> ${esc(feature.mechanics || 'Działa pasywnie lub kontekstowo.')} Źródło: ${esc(source)} (${esc(feature.source_ref || '-')})${mechanics.length ? `; ${mechanics.join('; ')}` : ''}.</span></p>`;
  }).join('')}</div>`;
}

function damageAffinitiesHtml(actor) {
  const profile = (actor && actor.damage_affinities) || {};
  const rows = [
    ['Odporności', profile.resistances || []],
    ['Niewrażliwości', profile.immunities || []],
    ['Podatności', profile.vulnerabilities || []],
  ].filter(([, values]) => values.length);
  if (!rows.length) return '';
  return `<p class="muted">${rows.map(([label, values]) => `${esc(label)}: ${values.map(value => esc(value.label || value.id)).join(', ')}`).join(' | ')}</p>`;
}
function actorInventoryHtml(actor) {
  const items = actor && actor.inventory ? actor.inventory : [];
  const hands = (actor && actor.hands) || {};
  const currency = (actor && actor.currency) || {};
  const carrying = (actor && actor.carrying) || {};
  const handItem = slot => slot && slot.item_name ? esc(slot.item_name) : 'wolna';
  const heldLabel = item => {
    const slots = item.held_in || [];
    if (slots.length === 2) return ' (obie ręce)';
    if (slots[0] === 'main_hand') return ' (główna ręka)';
    if (slots[0] === 'off_hand') return ' (druga ręka)';
    return item.equipped === false ? ' (niezałożone)' : '';
  };
  const handsHtml = `<p><b>Ręce:</b> główna — ${handItem(hands.main_hand)}, druga — ${handItem(hands.off_hand)}${Number(hands.reserved_hands || 0) > 0 ? `; chwyt: ${esc(hands.reserved_hands)} ręka` : ''}. Wolne: ${esc(hands.free_hands === undefined ? '-' : hands.free_hands)}.</p>`;
  const coins = ['pp', 'gp', 'ep', 'sp', 'cp'].filter(key => Number(currency[key] || 0) > 0).map(key => `${esc(currency[key])} ${key}`).join(', ') || 'brak';
  const economyHtml = `<p><b>Monety:</b> ${coins}. <b>Udźwig:</b> ${Number(carrying.weight_lb || 0).toFixed(1)} / ${Number(carrying.capacity_lb || 0).toFixed(1)} lb.</p>`;
  if (!items.length) return `${handsHtml}${economyHtml}`;
  return `${handsHtml}${economyHtml}<p><b>Ekwipunek:</b> ${items.map(item => `${esc(item.name || item.id)}${item.quantity !== undefined ? ` x${esc(item.quantity)}` : ''}${heldLabel(item)}`).join(', ')}</p>`;
}
function statusChipsHtml(chips, emptyText) {
  const items = chips || [];
  if (!items.length) return emptyText ? `<p class="combat-empty">${esc(emptyText)}</p>` : '';
  return `<div class="status-chips">${items.map(chip => {
    const tone = chip.tone || 'neutral';
    const title = chip.title ? ` title="${esc(chip.title)}"` : '';
    if (chip.panelTab) return `<button class="status-chip ${esc(tone)}" data-allow-busy="true" onclick="openActorPanel('${esc(chip.actorId || '')}', '${esc(chip.panelTab)}')"${title}>${esc(chip.label || '')}</button>`;
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
  let stateLabel = '';
  if (actor.dead) stateLabel = ' (martwy)';
  else if (actor.death_saves && actor.death_saves.stable && actor.hp <= 0) stateLabel = ' (stabilny)';
  else if (actor.death_save_required) stateLabel = ' (nieprzytomny)';
  else if (actor.defeated) stateLabel = ' (pokonany)';
  return `${actor.hp} / ${maxHp}${temp > 0 ? ` + ${temp} temp` : ''}${stateLabel}`;
}
function actorAcLabel(actor) {
  if (!actor) return '-';
  const ac = Number(actor.ac || 0);
  const base = Number(actor.base_ac === undefined ? ac : actor.base_ac);
  const equipmentBonus = Number(actor.equipment_ac_bonus || 0);
  return equipmentBonus > 0 ? `${ac} (${base} + ekwipunek ${equipmentBonus})` : `${ac}`;
}
function latestCombatMessageHtml() {
  const combatTitles = new Set(['Uderzenie tarczą', 'Atak', 'Czar', 'Obrażenia', 'Kontrczar', 'Ruch', 'Koniec tury', 'Atak przeciwnika', 'Efekt przeciwnika', 'Obrażenia przeciwnika', 'Ruch przeciwnika', 'Tura przeciwnika', 'Rzut obronny', 'Atak okazyjny', 'Pomoc', 'Ready', 'Leczenie', 'Eliksir', 'Rzut śmierci', 'Stabilizacja']);
  const messages = state.messages || [];
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    if (!combatTitles.has(messages[i].title)) continue;
    return `<p><b>${esc(messages[i].title)}</b></p><p>${esc(messages[i].body)}</p>`;
  }
  return '<p class="combat-empty">Brak rezultatu w tej walce.</p>';
}
function combatPrimaryActionHtml(combat, isAllyTurn, isEnemyTurn) {
  if (combat.shared_mana?.command?.stage) return sharedCommandControlsHtml(combat);
  if (!resultAck && combat.physical_mana?.needs_attack_count) return physicalAttackSeriesHtml(combat);
  if (resultAck) {
    return `
      <div class="combat-result-ack"><b>${esc(resultAck.title || 'Wynik')}</b><p>${esc(resultAck.body || '')}</p></div>
      <button data-allow-busy="true" onclick="ackResult()">Przeczytałem — wróć do tury</button>
    `;
  }
  if (combat.death_save_required) {
    const saves = (combat.current_actor && combat.current_actor.death_saves) || {};
    return `
      <p>Sukcesy: ${esc(saves.successes || 0)}/3 | Porażki: ${esc(saves.failures || 0)}/3</p>
      <div class="row">
        <label>Wynik d20: <input id="combat-death-save-roll" type="number" min="1" max="20" value="10"></label>
        <button data-allow-busy="true" onclick="submitDeathSave()">Rozstrzygnij rzut śmierci</button>
      </div>
    `;
  }
  const conditionSave = isAllyTurn ? ((combat.condition_saves || [])[0] || null) : null;
  if (conditionSave) {
    const timing = conditionSave.timing === 'turn_end' ? 'na końcu tury' : 'na początku tury';
    const secondRoll = conditionSave.roll_mode === 'normal' ? '' : `
      <label>Drugi wynik d20: <input id="combat-condition-save-roll-2" type="number" min="1" max="20" value="10"></label>
    `;
    const inspiration = conditionSave.bardic_inspiration;
    const inspirationInput = inspiration ? `
      <label>${esc(inspiration.label || 'Bardic Inspiration')} (opcjonalnie):
        <input id="combat-condition-save-inspiration" type="number" min="1" max="${Number(inspiration.die_sides)}" placeholder="nie używaj">
      </label>
    ` : '';
    const bless = conditionSave.bless;
    const blessInput = bless ? `
      <label>${esc(bless.label || 'Bless')} (k4):
        <input id="combat-condition-save-bless" type="number" min="1" max="${Number(bless.die_sides)}" required>
      </label>
    ` : '';
    return `
      <p><b>${esc(conditionSave.label)}</b>: wykonaj ${esc(conditionSave.ability)} save ST ${esc(conditionSave.dc)} ${esc(timing)}.</p>
      <p class="muted">${esc(conditionSave.instruction || '')}</p>
      <div class="row">
        <label>Wynik d20: <input id="combat-condition-save-roll" type="number" min="1" max="20" value="10"></label>
        ${secondRoll}
        ${inspirationInput}
        ${blessInput}
        <button data-allow-busy="true" onclick="submitCombatConditionSave('${esc(conditionSave.condition)}')">Rozstrzygnij save</button>
      </div>
    `;
  }
  if (combat.pending_concentration_check) {
    return pendingConcentrationCheckHtml(combat.pending_concentration_check);
  }
  if (combat.long_cast && isAllyTurn) {
    return longCastHtml(combat.long_cast, combat);
  }
  if (combat.pending_ready_attack && combat.pending_ready_attack.trigger === 'inspired_ally_dealt_direct_damage') {
    return pendingReadyAttackHtml(combat.pending_ready_attack);
  }
  if (isEnemyTurn) {
    const counterspell = counterspellReaction(combat);
    if (counterspell) {
      return counterspellReactionHtml(counterspell, combat.reaction_window || {}, combat.enemy_turn_preview || {});
    }
    const cuttingWords = classFeatureReaction(combat, 'cutting_words');
    if (cuttingWords) {
      return cuttingWordsReactionHtml(cuttingWords, combat.enemy_turn_preview || {});
    }
    const distractingShout = classFeatureReaction(combat, 'distracting_shout');
    if (distractingShout) {
      return distractingShoutReactionHtml(distractingShout, combat.enemy_turn_preview || {});
    }
    const defensiveSpell = defensiveSpellReaction(combat);
    if (defensiveSpell) {
      return defensiveSpellReactionHtml(defensiveSpell, combat.enemy_turn_preview || {});
    }
    const deflectMissiles = classFeatureReaction(combat, 'deflect_missiles');
    if (deflectMissiles) {
      return deflectMissilesReactionHtml(deflectMissiles, combat.reaction_window || {}, combat.enemy_turn_preview || {});
    }
    const instinctiveDodge = classFeatureReaction(combat, 'instinctive_dodge');
    if (instinctiveDodge) {
      return `
        <p><b>Unik instynktowny Miry</b></p>
        <p>${combat.physical_mana ? 'Wydaj Z (zieloną manę) i reakcję. Ten jeden atak otrzymuje utrudnienie.' : 'Wydaj 1 Fortel i reakcję, aby nadać temu jednemu atakowi utrudnienie. Premia +2 ze skazy nadal obowiązuje.'}</p>
        <div class="row">
          <button data-allow-busy="true" onclick="useInstinctiveDodgeReaction()">Wykonaj unik</button>
          <button class="secondary" data-allow-busy="true" onclick="skipInstinctiveDodgeReaction()">Nie reaguj</button>
        </div>
      `;
    }
    if (combat.pending_ready_attack) {
      return pendingReadyAttackHtml(combat.pending_ready_attack);
    }
    if (combat.pending_enemy_opportunity_attack) {
      return pendingEnemyOpportunityAttackHtml(combat.pending_enemy_opportunity_attack);
    }
    if (combat.pending_enemy_saving_throw) {
      return pendingEnemySavingThrowHtml(combat.pending_enemy_saving_throw);
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
      <button data-allow-busy="true" data-card-action="accept" onclick="resolveEnemyTurn()">Rozegraj turę przeciwnika</button>
    `;
  }
  if (!isAllyTurn) {
    return '<p class="muted">Ten aktor nie ma automatycznych kontrolek w MVP.</p><button data-allow-busy="true" onclick="finishCombatTurn()">Zakończ turę</button>';
  }
  if (((combat.stabilization || {}).selected_target)) {
    return combatStabilizationHtml(combat);
  }
  if (((combat.stabilization || {}).targeting_method)) {
    return `
      <p><b>Stabilizacja:</b> kliknij podświetlonego nieprzytomnego sojusznika.</p>
      <button data-primary-scan="true" onclick="scanBoard()">Pokaż legalne cele</button>
    `;
  }
  if (combat.context_menu) {
    const stabilization = combat.context_menu.is_self_menu ? combatStabilizationHtml(combat) : '';
    return `${combatContextMenuHtml(combat.context_menu)}${stabilization}`;
  }
  if (combat.pending_opportunity_movement) {
    return pendingOpportunityMovementHtml(combat.pending_opportunity_movement);
  }
  if (combat.pending_combat_help) {
    return pendingCombatHelpHtml(combat.pending_combat_help);
  }
  if (combat.shield_bash) return shieldBashHtml(combat.shield_bash);
  if (combat.class_feature_targeting) {
    return pendingClassFeatureTargetingHtml(combat.class_feature_targeting);
  }
  if (combat.pending_combat_shove) {
    return pendingCombatShoveHtml(combat.pending_combat_shove);
  }
  if (combat.pending_combat_grapple) {
    return pendingCombatGrappleHtml(combat.pending_combat_grapple);
  }
  if (combat.pending_combat_skill_check) {
    return pendingCombatSkillCheckHtml(combat.pending_combat_skill_check);
  }
  if (combat.pending_concentration_action) {
    return pendingConcentrationActionHtml(combat.pending_concentration_action);
  }
  if (combat.pending_multi_target_damage_spell) {
    return pendingMultiTargetDamageSpellHtml(combat.pending_multi_target_damage_spell);
  }
  if (combat.pending_summon) {
    return pendingSummonHtml(combat.pending_summon);
  }
  if (combat.pending_magic_movement) {
    return pendingMagicMovementHtml(combat.pending_magic_movement);
  }
  if (combat.pending_spell_debuff) {
    return pendingSpellDebuffHtml(combat.pending_spell_debuff);
  }
  if (combat.pending_spell_dispel) {
    return pendingSpellDispelHtml(combat.pending_spell_dispel);
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
  if (combat.item_targeting) {
    return pendingCombatItemTargetHtml(combat.item_targeting);
  }
  if (combat.turn_action_menu) {
    return combatTurnActionMenuHtml(combat.turn_action_menu, combat);
  }
  const movement = combat.movement || {remaining_feet: 0, destinations: []};
  const preview = combat.movement_preview || null;
  const targeting = combat.targeting || null;
  return `
    ${targeting
      ? `<p>Celowanie: <b>${esc(targeting.source_name || '-')}</b>. ${targeting.kind === 'area' ? 'Wybierz podświetlony obszar.' : 'Wybierz podświetlonego przeciwnika.'}</p>`
      : preview
        ? `<p>Potwierdź pole: (${esc(preview.destination[0])},${esc(preview.destination[1])}), koszt ${esc(preview.cost_feet)} ft.</p>`
        : `<p>Ruch dostępny: ${esc(movement.remaining_feet || 0)} ft.</p>`}
    <div class="row">
      <button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>
      ${!targeting && !preview ? '<button class="secondary" data-allow-busy="true" onclick="finishCombatTurn()">Zakończ turę</button>' : ''}
      ${!targeting && !preview ? '<button class="secondary" data-allow-busy="true" onclick="retreatFromCombat()">Odwrót</button>' : ''}
      ${!targeting && !preview ? '<button class="secondary" data-allow-busy="true" onclick="surrenderCombat()">Kapitulacja</button>' : ''}
    </div>
  `;
}
function pendingCombatItemTargetHtml(pending) {
  const target = pending.selected_target || null;
  return `
    <div class="combat-action-box">
      <p><b>${esc(pending.label || 'Użycie przedmiotu')}</b></p>
      <p>${target
        ? `Wybrany cel: <b>${esc(target.name)}</b>. Przedmiot nie został jeszcze zużyty.`
        : 'Kliknij podświetlony legalny cel na planszy.'}</p>
      <div class="row">
        <button data-allow-busy="true" onclick="confirmCombatItemTarget()"${target ? '' : ' disabled'}>✓ Potwierdź</button>
        <button class="secondary" data-allow-busy="true" onclick="cancelCombatItemTargeting()">Wróć bez kosztu</button>
      </div>
    </div>`;
}
function combatStabilizationHtml(combat) {
  const stabilization = combat.stabilization || {};
  const targets = stabilization.targets || [];
  if (!targets.length) return '';
  const selected = stabilization.selected_target || null;
  const kitUses = Number(stabilization.healers_kit_uses || 0);
  const spareTheDying = Boolean(stabilization.spare_the_dying_available);
  const modifier = Number(stabilization.medicine_modifier || 0);
  const modifierLabel = modifier >= 0 ? `+${modifier}` : `${modifier}`;
  return `
    <div class="combat-action-box">
      <p><b>Stabilizacja nieprzytomnego sojusznika w zasięgu 5 ft</b></p>
      <p>${selected ? `Wybrano na planszy: <b>${esc(selected.name)}</b>.` : 'Najpierw wybierz metodę, potem kliknij podświetloną figurkę na planszy.'}</p>
      <div class="row">
        ${selected ? `<label>d20 Medicine: <input id="combat-stabilization-roll" type="number" min="1" max="20" value="10"></label>
          <button class="secondary" data-allow-busy="true" onclick="confirmBoardStabilization()">Rozstrzygnij Medicine ${esc(modifierLabel)} · ST ${esc(stabilization.dc || 10)}</button>`
          : `<button class="secondary" data-allow-busy="true" onclick="startStabilizationTargeting('medicine')">Medicine ${esc(modifierLabel)} · ST ${esc(stabilization.dc || 10)}</button>
          ${kitUses > 0 ? `<button class="secondary" data-allow-busy="true" onclick="startStabilizationTargeting('healers_kit')">Zestaw uzdrowiciela (${esc(kitUses)})</button>` : ''}
          ${spareTheDying ? '<button class="secondary" data-allow-busy="true" onclick="startStabilizationTargeting(\'spare_the_dying\')">Spare the Dying</button>' : ''}`}
      </div>
    </div>
  `;
}

function pendingCombatSkillCheckHtml(pending) {
  const label = pending.action === 'hide' ? 'Stealth' : 'Perception';
  return `
    <div class="combat-action-box">
      <p><b>${esc(pending.action === 'hide' ? 'Hide' : 'Search')}:</b> ${esc(pending.instruction || '')}</p>
      <div class="row">
        ${d20RollInputsHtml('combat-skill-check-roll', pending.roll_mode)}
        <button onclick="submitCombatSkillCheck()">Rozstrzygnij</button>
        <button class="secondary" onclick="cancelCombatSkillCheck()">Anuluj</button>
      </div>
    </div>
  `;
}
function pendingCombatShoveHtml(pending) {
  const attacker = pending.attacker_check || {};
  const defender = pending.defender_check || {};
  const activeModifiers = (attacker.active_modifiers || [])
    .map(mod => `${esc(mod.label)} ${signedNumber(Number(mod.value || 0))}`)
    .join(', ');
  return `
    <div class="combat-action-box">
      <p><b>Shove — ${esc(pending.mode_label || pending.mode)}:</b> ${esc(pending.attacker_name)} przeciw ${esc(pending.target_name)}.</p>
      <p><b>Atakujący:</b> Strength (Athletics) ${signedNumber(Number(attacker.modifier_total || 0))}${activeModifiers ? ` (${activeModifiers})` : ''}.</p>
      <p><b>Obrońca:</b> ${esc(defender.label || 'Athletics/Acrobatics')} ${signedNumber(Number(defender.modifier_total || 0))}; rzut wykona silnik.</p>
      ${pending.push_destination ? `<p><b>Planowane pole po odepchnięciu:</b> (${esc(pending.push_destination[0])}, ${esc(pending.push_destination[1])}).</p>` : ''}
      <div class="row">
        <label>d20 Athletics: <input id="combat-shove-roll" type="number" min="1" max="20" value="10"></label>
        <button onclick="submitCombatShove()">Rozstrzygnij</button>
        <button class="secondary" onclick="cancelCombatShove()">Anuluj</button>
      </div>
    </div>
  `;
}
function pendingCombatGrappleHtml(pending) {
  const actor = pending.actor_check || {};
  const opponent = pending.opponent_check || {};
  const activeModifiers = (actor.active_modifiers || [])
    .map(mod => `${esc(mod.label)} ${signedNumber(Number(mod.value || 0))}`)
    .join(', ');
  return `
    <div class="combat-action-box">
      <p><b>Grapple — ${esc(pending.mode_label || pending.mode)}:</b> ${esc(pending.actor_name)} przeciw ${esc(pending.opponent_name)}.</p>
      <p><b>Aktywny bohater:</b> ${esc(actor.label || 'Athletics')} ${signedNumber(Number(actor.modifier_total || 0))}${activeModifiers ? ` (${activeModifiers})` : ''}.</p>
      <p><b>Przeciwnik:</b> ${esc(opponent.label || 'Athletics/Acrobatics')} ${signedNumber(Number(opponent.modifier_total || 0))}; rzut wykona silnik.</p>
      <div class="row">
        <label>d20 ${esc(actor.label || 'Athletics')}: <input id="combat-grapple-roll" type="number" min="1" max="20" value="10"></label>
        <button onclick="submitCombatGrapple()">Rozstrzygnij</button>
        <button class="secondary" onclick="cancelCombatGrapple()">Anuluj</button>
      </div>
    </div>
  `;
}
function combatActionDetailsHtml(combat, isAllyTurn, isEnemyTurn) {
  if (combat.death_save_required) return '<p>Naturalne 1 daje dwie porażki. Naturalne 20 przywraca 1 HP. Trzy sukcesy stabilizują, a trzy porażki oznaczają śmierć.</p>';
  if (combat.context_menu) return combatContextMenuDetailsHtml(combat.context_menu);
  if (combat.pending_concentration_check) return pendingConcentrationCheckDetailsHtml(combat.pending_concentration_check);
  if (combat.physical_feature_prompt) return physicalFeaturePromptHtml(combat.physical_feature_prompt);
  if (isEnemyTurn && combat.pending_enemy_saving_throw) return pendingEnemySavingThrowDetailsHtml(combat.pending_enemy_saving_throw);
  if (isEnemyTurn) return enemyTurnDetailsHtml(combat);
  if (!isAllyTurn) return '<p class="muted">Brak dodatkowych szczegółów dla tego aktora.</p>';
  if (combat.pending_opportunity_movement) return pendingOpportunityMovementDetailsHtml(combat.pending_opportunity_movement);
  if (combat.pending_combat_help) return pendingCombatHelpDetailsHtml(combat.pending_combat_help);
  if (combat.pending_concentration_action) return pendingConcentrationActionDetailsHtml(combat.pending_concentration_action);
  if (combat.pending_multi_target_damage_spell) return pendingMultiTargetDamageSpellDetailsHtml(combat.pending_multi_target_damage_spell);
  if (combat.pending_summon) return '<p>Przywołana istota dołącza do inicjatywy zaraz po właścicielu i znika po utracie koncentracji.</p>';
  if (combat.pending_magic_movement) return '<p>Teleport i wymuszony ruch nie zużywają szybkości przemieszczanego aktora oraz nie wywołują ataków okazyjnych.</p>';
  if (combat.pending_spell_debuff) return '<p>Po nieudanym pierwszym save stan zostaje zapisany we wspólnym systemie kondycji. Kolejne save są rozstrzygane w turach celu.</p>';
  if (combat.pending_spell_dispel) return '<p>Efekty o poziomie nie wyższym od użytego slotu kończą się automatycznie. Każdy silniejszy efekt wymaga osobnego testu przeciw ST 10 + jego poziom.</p>';
  if (combat.pending_combat_ready) return pendingCombatReadyDetailsHtml(combat.pending_combat_ready);
  if (combat.pending_player_attack) return pendingPlayerAttackDetailsHtml(combat.pending_player_attack);
  if (combat.pending_player_healing) return pendingPlayerHealingDetailsHtml(combat.pending_player_healing);
  if (combat.pending_area_spell) return pendingAreaSpellDetailsHtml(combat.pending_area_spell);
  if (combat.pending_combat_interaction) return pendingCombatInteractionDetailsHtml(combat.pending_combat_interaction);
  return playerTurnDetailsHtml(combat);
}
function physicalFeaturePromptHtml(prompt) {
  const actionId = prompt.action_id || '';
  const ability = (state?.combat?.physical_mana?.abilities || []).find(a => a.id === actionId);
  let controls = '';
  if (prompt.input_kind === 'mana_target') {
    controls = `<label>Bohater w 30 ft<select id="physical-feature-mana-target" required>${(prompt.targets || []).map(t => `<option value="${esc(t.id)}">${esc(t.name)}</option>`).join('')}</select></label>`;
  } else if (prompt.input_kind === 'die') {
    controls = `<label>Wynik k${Number(prompt.die_sides || 10)}<input id="physical-feature-roll" type="number" min="1" max="${Number(prompt.die_sides || 10)}" required></label>`;
  } else if (prompt.input_kind === 'weapon') {
    controls = `<label>Broń<select id="physical-feature-weapon" required>${(prompt.weapons || []).map(item => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('')}</select></label>`;
  } else if (prompt.input_kind === 'slot') {
    controls = `<label>Poziom slotu<select id="physical-feature-slot" required>${(prompt.available_slot_levels || []).map(level => `<option value="${Number(level)}">${Number(level)}. poziom</option>`).join('')}</select></label>`;
  } else if (prompt.input_kind === 'saving_rolls') {
    controls = (prompt.targets || []).length
      ? `<div class="status-list">${(prompt.targets || []).map(target => `<label>${esc(target.name)} · Mądrość ST ${Number(target.dc || 0)}<input class="physical-feature-saving-roll" data-target-id="${esc(target.id)}" type="number" min="1" max="20" required></label>`).join('')}</div>`
      : '<p>Brak właściwych celów w zasięgu. Potwierdzenie nadal zużyje akcję i Boską Moc.</p>';
  } else if (prompt.input_kind === 'form') {
    controls = `<label>Forma<select id="physical-feature-form" required>${(prompt.forms || []).map(item => `<option value="${esc(item.id)}">${esc(item.name)}${item.role ? ` · ${esc(item.role)}` : ''}${item.hit_points ? ` · KP ${Number(item.ac)} · PW ${Number(item.hit_points)}` : ''}</option>`).join('')}</select></label>`;
  } else if (prompt.input_kind === 'mode') {
    controls = `<label>Wariant<select id="physical-feature-mode" required>${(prompt.modes || []).map(item => `<option value="${esc(item.id)}">${esc(item.name)}</option>`).join('')}</select></label>`;
  }
  return `
    <div class="status-item">
      <h3>${esc(prompt.label || identifierLabel(actionId))}</h3>
      ${ability ? `<p class="mana-prompt-cost">${manaCostHtml(ability.cost)} · ${esc(ability.timing)}</p>` : ''}
      ${prompt.incoming_damage ? `<p>Ujawnione obrażenia pocisku: <b>${Number(prompt.incoming_damage)}</b>.</p>` : ''}
      ${controls}
      <div class="panel-actions">
        <button class="secondary" onclick="cancelPhysicalFeaturePrompt()">Anuluj</button>
        <button onclick="submitPhysicalFeaturePrompt('${esc(actionId)}')">Potwierdź</button>
      </div>
    </div>`;
}
function submitPhysicalFeaturePrompt(actionId) {
  const roll = Number((document.getElementById('physical-feature-roll') || {}).value || 0);
  if (actionId === 'divine_smite') {
    const slot = Number((document.getElementById('physical-feature-slot') || {}).value || 0);
    api('/api/combat/divine-smite', {slot_level: slot}, 'Dodaję Divine Smite...');
    return;
  }
  if (actionId === 'deflect_missiles') {
    api('/api/combat/deflect-missiles/roll', {die_roll: roll}, 'Redukuję obrażenia pocisku...');
    return;
  }
  const payload = {action_id: actionId};
  if (actionId.startsWith('mana_')) payload.target_id = (document.getElementById('physical-feature-mana-target') || {}).value || '';
  if (['second_wind', 'hard_as_rock', 'anchoring_arrow', 'exposing_arrow'].includes(actionId)) payload.natural_roll = roll;
  if (actionId === 'sacred_weapon') payload.source_item_id = (document.getElementById('physical-feature-weapon') || {}).value || '';
  if (actionId === 'turn_the_unholy' || actionId === 'turn_undead') {
    payload.saving_rolls = Array.from(document.querySelectorAll('.physical-feature-saving-roll')).map(input => ({
      target_id: input.dataset.targetId,
      natural_roll: Number(input.value),
    }));
  }
  if (actionId === 'wild_shape' || actionId === 'pact_weapon') payload.form_id = (document.getElementById('physical-feature-form') || {}).value || '';
  if (actionId === 'cunning_action') payload.mode = (document.getElementById('physical-feature-mode') || {}).value || '';
  api('/api/combat/class-feature', payload, 'Rozstrzygam kartę cechy klasowej...');
}
function cancelPhysicalFeaturePrompt() {
  api('/api/combat/physical-feature/cancel', {}, 'Anuluję kartę cechy klasowej...');
}
function combatSourceButtonsHtml(combat) {
  const attacks = combat.available_attack_sources || [];
  const selectedAttack = combat.selected_attack_source_id || '';
  const actor = combat.current_actor || {};
  const attackButtons = attacks.flatMap(source => {
    const disabledReason = sourceUnavailableReason(source, actor);
    const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
    const levels = Number(source.spell_level || 0) > 0 ? (source.available_cast_levels || []) : [null];
    return levels.flatMap(level => {
      const baseSelectionId = level === null ? source.id : `${source.id}@${level}`;
      const levelLabel = level === null || state.combat?.physical_mana ? '' : ` · slot ${level}`;
      const argument = level === null ? 'null' : Number(level);
      const variants = [{ids: [], label: ''}];
      return variants.map(variant => {
        const selectionId = variant.ids.length ? `${baseSelectionId}#${variant.ids.join(',')}` : baseSelectionId;
        const selected = selectionId === selectedAttack ? ' selected' : '';
        const ids = JSON.stringify(variant.ids).replace(/"/g, '&quot;');
        return `<button class="secondary${selected}" data-allow-busy="true"${disabled} onclick="selectCombatAttackSource('${esc(source.id)}', ${argument}, ${ids})">${sourceButtonLabel(source)}${esc(levelLabel)}${esc(variant.label)}</button>`;
      });
    });
  }).join('');
  const healing = combat.available_healing_sources || [];
  const selectedHealing = combat.selected_healing_source_id || '';
  const healingButtons = healing.flatMap(source => {
    const disabledReason = sourceUnavailableReason(source, actor);
    const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
    const levels = Number(source.spell_level || 0) > 0 ? (source.available_cast_levels || []) : [null];
    return levels.flatMap(level => {
      const baseSelectionId = level === null ? source.id : `${source.id}@${level}`;
      const levelLabel = level === null || state.combat?.physical_mana ? '' : ` · slot ${level}`;
      const argument = level === null ? 'null' : Number(level);
      const variants = [{ids: [], label: ''}];
      return variants.map(variant => {
        const selectionId = variant.ids.length ? `${baseSelectionId}#${variant.ids.join(',')}` : baseSelectionId;
        const selected = selectionId === selectedHealing ? ' selected' : '';
        const ids = JSON.stringify(variant.ids).replace(/"/g, '&quot;');
        return `<button class="secondary${selected}" data-allow-busy="true"${disabled} onclick="selectCombatHealingSource('${esc(source.id)}', ${argument}, ${ids})">${sourceButtonLabel(source)}${esc(levelLabel)}${esc(variant.label)}</button>`;
      });
    });
  }).join('');
  const actionButtons = (combat.combat_actions || []).map(action => {
    if (action.action_type === 'multi_target_damage') {
      const disabledReason = sourceUnavailableReason(action, actor);
      const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
      const label = esc(action.name || action.label || action.id);
      const levels = Number(action.spell_level || 0) > 0 ? (action.available_cast_levels || []) : [0];
      return levels.map(level => {
        const levelLabel = !state.combat?.physical_mana && Number(action.spell_level || 0) > 0 ? ` · slot ${level}` : '';
        const missiles = Number(action.projectile_count || 0)
          + Math.max(0, Number(level) - Number(action.spell_level || 0))
          * Number(action.upcast_projectiles_per_level || 0);
        return `<button class="secondary"${disabled} data-allow-busy="true" onclick="startMultiTargetDamageSpell('${esc(action.id)}', ${Number(level)})">${label}${esc(levelLabel)} · ${missiles} pociski</button>`;
      }).join('');
    }
    if (action.action_type === 'assisted_spell') {
      const disabledReason = sourceUnavailableReason(action, actor);
      const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
      const label = esc(action.name || action.label || action.id);
      const hint = action.instructions ? ` title="${esc(action.instructions)}"` : '';
      const levels = Number(action.spell_level || 0) > 0 ? (action.available_cast_levels || []) : [0];
      return levels.flatMap(level => {
        const levelLabel = !state.combat?.physical_mana && Number(action.spell_level || 0) > 0 ? ` · slot ${level}` : '';
        const variants = [{ids: [], label: ''}];
        return variants.map(variant => {
          const ids = JSON.stringify(variant.ids).replace(/"/g, '&quot;');
          return `<button class="secondary"${disabled}${hint} data-allow-busy="true" onclick="useAssistedSpell('${esc(action.id)}', ${Number(level)}, ${ids})">${label}${esc(levelLabel)}${esc(variant.label)} · rozstrzygnij przy stole</button>`;
        });
      }).join('');
    }
    if (action.action_type === 'strength_potion') {
      const disabledReason = sourceUnavailableReason(action, actor);
      const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
      const label = sourceButtonLabel(action);
      return `<button class="secondary"${disabled} data-allow-busy="true" onclick="useStrengthPotion('${esc(action.id)}')">${label}</button>`;
    }
    if (action.action_type === 'concentration_attack_bonus' || action.action_type === 'targeted_status') {
      const disabledReason = sourceUnavailableReason(action, actor);
      const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
      const label = esc(action.name || action.label || action.id);
      const levels = Number(action.spell_level || 0) > 0 ? (action.available_cast_levels || []) : [0];
      return levels.map(level => {
        const levelLabel = !state.combat?.physical_mana && Number(action.spell_level || 0) > 0 ? ` · slot ${level}` : '';
        return `<button class="secondary"${disabled} data-allow-busy="true" onclick="startConcentrationAction('${esc(action.id)}', ${Number(level)})">${label}${esc(levelLabel)}</button>`;
      }).join('');
    }
    if (action.action_type === 'long_cast_effect') {
      const disabledReason = sourceUnavailableReason(action, actor);
      const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
      const label = esc(action.name || action.label || action.id);
      const levels = Number(action.spell_level || 0) > 0 ? (action.available_cast_levels || []) : [0];
      return levels.map(level => {
        const levelLabel = !state.combat?.physical_mana && Number(action.spell_level || 0) > 0 ? ` · slot ${level}` : '';
        return `<button class="secondary"${disabled} data-allow-busy="true" onclick="startLongCast('${esc(action.id)}', ${Number(level)})">${label}${esc(levelLabel)} · rozpocznij</button>`;
      }).join('');
    }
    if (action.action_type === 'summon') {
      const disabledReason = sourceUnavailableReason(action, actor);
      const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
      const label = esc(action.name || action.label || action.id);
      const levels = Number(action.spell_level || 0) > 0 ? (action.available_cast_levels || []) : [0];
      return levels.map(level => {
        const levelLabel = !state.combat?.physical_mana && Number(action.spell_level || 0) > 0 ? ` · slot ${level}` : '';
        return `<button class="secondary"${disabled} data-allow-busy="true" onclick="startSummon('${esc(action.id)}', ${Number(level)})">${label}${esc(levelLabel)} · wybierz pole</button>`;
      }).join('');
    }
    if (action.action_type === 'spell_movement') {
      const disabledReason = sourceUnavailableReason(action, actor);
      const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
      const label = esc(action.name || action.label || action.id);
      const levels = Number(action.spell_level || 0) > 0 ? (action.available_cast_levels || []) : [0];
      return levels.map(level => {
        const levelLabel = !state.combat?.physical_mana && Number(action.spell_level || 0) > 0 ? ` · slot ${level}` : '';
        return `<button class="secondary"${disabled} data-allow-busy="true" onclick="startMagicMovement('${esc(action.id)}', ${Number(level)})">${label}${esc(levelLabel)} · wybierz</button>`;
      }).join('');
    }
    if (action.action_type === 'spell_debuff') {
      const disabledReason = sourceUnavailableReason(action, actor);
      const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
      const label = esc(action.name || action.label || action.id);
      const levels = Number(action.spell_level || 0) > 0 ? (action.available_cast_levels || []) : [0];
      return levels.map(level => {
        const levelLabel = !state.combat?.physical_mana && Number(action.spell_level || 0) > 0 ? ` · slot ${level}` : '';
        return `<button class="secondary"${disabled} data-allow-busy="true" onclick="startSpellDebuff('${esc(action.id)}', ${Number(level)})">${label}${esc(levelLabel)} · wybierz cel</button>`;
      }).join('');
    }
    if (action.action_type === 'spell_dispel') {
      const disabledReason = sourceUnavailableReason(action, actor);
      const disabled = disabledReason ? ' disabled title="' + esc(disabledReason) + '"' : '';
      const label = esc(action.name || action.label || action.id);
      const levels = Number(action.spell_level || 0) > 0 ? (action.available_cast_levels || []) : [0];
      return levels.map(level => {
        const levelLabel = !state.combat?.physical_mana && Number(action.spell_level || 0) > 0 ? ` · slot ${level}` : '';
        return `<button class="secondary"${disabled} data-allow-busy="true" onclick="startSpellDispel('${esc(action.id)}', ${Number(level)})">${label}${esc(levelLabel)} · wybierz cel</button>`;
      }).join('');
    }
    return '';
  }).join('');
  const classFeatureButtons = (combat.class_feature_actions || []).map(action => {
    const disabled = action.implemented ? '' : ' disabled title="Ta cecha działa pasywnie, w reakcji albo przy rozstrzyganiu innej akcji."';
    return `<button class="secondary"${disabled} data-allow-busy="true" onclick="useClassFeature('${esc(action.id)}')">${esc(action.label)} · ${esc(action.source_feature)}</button>`;
  }).join('');
  const spellZoneButtons = (combat.movable_spell_zones || []).map(zone => (
    `<button class="secondary" data-allow-busy="true" onclick="startMoonbeamMove('${esc(zone.effect_id)}')">Przesuń ${esc(zone.label)} · ${esc(zone.action_cost_label || 'akcja')} · do ${esc(zone.distance_feet)} ft</button>`
  )).join('');
  return `${attackButtons}${healingButtons}${actionButtons}${classFeatureButtons}${spellZoneButtons}`;
}
function sourceButtonLabel(source) {
  const resource = source.resource_label ? ` · ${esc(source.resource_label)}` : '';
  return `${esc(source.name)}${resource}`;
}
function sourceUnavailableReason(source, actor) {
  if (source.unavailable_reason) return source.unavailable_reason;
  if (source.prepared === false) return 'Ten czar nie jest przygotowany.';
  if (source.available === false) {
    if (source.source_item_id) return 'Ten przedmiot został zużyty.';
    return 'Ta opcja nie jest dostępna.';
  }
  if ((source.resource_label || '').startsWith('Mana:')) return '';
  const spellLevel = Number(source.spell_level || 0);
  if (spellLevel <= 0) return '';
  const slots = actor.spell_slots || [];
  const slot = slots.find(item => Number(item.level) >= spellLevel && Number(item.remaining || 0) > 0);
  if (!slot) return `Brak slotów czaru ${spellLevel}. poziomu lub wyższego.`;
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
  if (source.area) {
    const area = source.area;
    const dimensions = area.shape === 'radius'
      ? `promień ${area.radius_feet} ft`
      : `${area.length_feet} ft${area.shape === 'line' ? ` × ${area.width_feet} ft` : ''}`;
    parts.push(`obszar ${areaShapeLabel(area.shape)} ${dimensions}`);
    if (area.target_mode === 'all_creatures') parts.push('friendly fire');
  }
  if (source.attack_kind === 'melee' && source.reach_feet) parts.push(`reach ${source.reach_feet} ft`);
  else if (source.range_feet) parts.push(source.long_range_feet ? `${source.range_feet}/${source.long_range_feet} ft` : `${source.range_feet} ft`);
  if ((source.tabletop_riders || []).length) parts.push(`przy stole: ${(source.tabletop_riders || []).join(' ')}`);
  return parts.join(' · ');
}
function noLegalAttackTargetGuidance(combat) {
  const source = combat.available_attack || {};
  const targets = combat.legal_targets || [];
  if (targets.length || !source.id || (combat.turn || {}).action_used) return '';
  const movement = combat.movement || {};
  const canMove = Number(movement.remaining_feet || 0) > 0 && (movement.destinations || []).length > 0;
  if (source.attack_kind === 'melee') {
    return canMove
      ? 'Brak celu w zasięgu wręcz. Podejdź do przeciwnika na niebieskie pole albo wybierz broń dystansową.'
      : 'Brak celu w zasięgu wręcz i nie pozostał ruch. Wybierz broń dystansową lub zakończ turę.';
  }
  return canMove
    ? 'Brak legalnego celu dla ataku dystansowego. Zmień pozycję, aby uzyskać zasięg lub linię widzenia.'
    : 'Brak legalnego celu: przeciwnicy są poza zasięgiem albo linią widzenia. Wybierz inne źródło ataku lub zakończ turę.';
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
  const objectInteractionAvailable = !combat.turn_action || combat.turn_action.object_interaction_available !== false;
  const remaining = Number(movement.remaining_feet || 0);
  const extraMovement = Number((combat.turn_action && combat.turn_action.extra_movement_feet) || 0);
  const moveCount = (movement.destinations || []).length;
  const slotSummary = spellSlotSummaryHtml(actor);
  const concentration = actor.concentration || null;
  const inventory = actorInventoryHtml(actor);
  const targetText = targets.length
    ? targets.map(target => `${target.name} (${target.position[0]},${target.position[1]})`).join(', ')
    : 'brak';
  const noTargetGuidance = noLegalAttackTargetGuidance(combat);
  return `
    <p><b>Tura gracza:</b> ${esc(actor.name || '-')}</p>
    <p><b>Akcja:</b> ${actionUsed ? 'zużyta' : 'dostępna'} | <b>Bonus action:</b> ${bonusActionUsed ? 'zużyta' : 'dostępna'} | <b>Darmowa interakcja:</b> ${objectInteractionAvailable ? 'dostępna' : 'zużyta'} | <b>Reakcja:</b> ${reactionAvailable ? 'dostępna' : 'zużyta'} | <b>Ruch:</b> ${esc(remaining)} ft${extraMovement > 0 ? ` (+${esc(extraMovement)} Dash)` : ''}${movement.speed_reduction === 'grappling' ? ` | <b>Grapple:</b> szybkość ${esc(movement.base_speed_feet)} → ${esc(movement.effective_speed_feet)} ft` : ''}</p>
    ${inventory}
    ${slotSummary || concentration ? `<p><b>Magia:</b> ${slotSummary ? `ST czarów ${esc(actor.spell_save_dc || '-')}; ${slotSummary}` : ''}${concentration ? ` | Koncentracja: ${esc(concentration.label || '-')}` : ''}</p>` : ''}
    <p>Niebieskie pola: ruch (${esc(moveCount)} pól). Czerwone pola: legalne cele ataku. Turkusowe pola: legalne cele leczenia. Zielone pola: interakcje sceny. Żółte pola: środek albo kierunek czaru obszarowego.</p>
    ${preview ? `<p>Wybrana ścieżka: (${esc(preview.destination[0])},${esc(preview.destination[1])}), koszt ${esc(preview.cost_feet)} ft.${preview.dragged_actor ? ` Przestaw ${esc(preview.dragged_actor.name)} na różowe pole (${esc(preview.dragged_actor.destination[0])},${esc(preview.dragged_actor.destination[1])}).` : ''}</p>` : ''}
    <p><b>Atak:</b> ${esc(source.name || '-')}${source.damage_hint ? `, po trafieniu rzuć ${esc(source.damage_hint)}` : ''}</p>
    <p><b>Źródła ataku:</b> ${attackSources.map(sourceSummaryText).map(esc).join(', ') || 'brak'}</p>
    <p><b>Leczenie:</b> ${healingSources.map(item => `${sourceSummaryText(item)}${item.healing_hint ? ` · ${item.healing_hint}` : ''}`).map(esc).join(', ') || 'brak'}</p>
    <p><b>Cele w zasięgu:</b> ${esc(targetText)}</p>
    ${noTargetGuidance ? `<p class="combat-warning"><b>Dlaczego nie ma celu?</b> ${esc(noTargetGuidance)}</p>` : ''}
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
      ? `<p><b>Atak:</b> ${esc(source.name || '-')} ${targetText}. Premia do rzutu: ${esc(signedNumber(intent.attack_modifier || 0))}.</p>${attackPositioningText(intent.positioning)}`
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
    const save = result.saving_throw_result || null;
    const hitText = save ? (save.success ? 'SUKCES RZUTU OBRONNEGO' : 'PORAŻKA RZUTU OBRONNEGO') : (result.hit === true ? (result.critical ? 'TRAFIENIE KRYTYCZNE' : 'TRAFIENIE') : (result.hit === false ? 'PUDŁO' : 'BRAK ATAKU'));
    const rollHtml = result.natural_roll !== null && result.natural_roll !== undefined
      ? `<p><b>Rzut d20:</b> ${d20RollResultText(result)} | <b>Wynik końcowy:</b> ${esc(result.total)}</p>`
      : '';
    const damageHtml = result.damage !== null && result.damage !== undefined
      ? `<p><b>Obrażenia:</b> ${esc(result.damage)}</p>`
      : '';
    const damageResult = result.damage_result || null;
    const damageBreakdown = damageResult ? damageBreakdownHtml(damageResult) : '';
    const hpHtml = damageResult
      ? `<p><b>HP celu:</b> ${esc(damageResult.hp_before)} -> ${esc(damageResult.hp_after)}${damageResult.defeated_by_damage ? ' | cel pokonany' : ''}</p>`
      : '';
    return `
      <p><b>Wynik tury przeciwnika:</b> ${hitText}</p>
      <p>${esc(result.enemy_name || 'Przeciwnik')}${target}</p>
      ${rollHtml}
      ${save ? spellSavesHtml([save]) : ''}
      ${attackPositioningText(result.positioning)}
      ${damageHtml}
      ${damageBreakdown}
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
  return '<p>✓ lub przycisk na ekranie od razu wyliczy ruch i atak przeciwnika. Przestaw figurkę, a potem jednym kliknięciem planszy potwierdź cały zamiar.</p>';
}
function attackPositioningText(positioning) {
  if (!positioning) return '';
  const coverNames = {none: 'brak', half: 'połowa', three_quarters: '3/4', total: 'pełna'};
  const sources = positioning.cover_sources || [];
  return `<p><b>Warunki pozycyjne:</b> osłona ${esc(coverNames[positioning.cover_level] || positioning.cover_level || 'brak')}${Number(positioning.cover_bonus || 0) ? ` (AC +${esc(positioning.cover_bonus)})` : ''}${sources.length ? ` — ${sources.map(esc).join(', ')}` : ''}; atak dystansowy w zwarciu: ${positioning.ranged_in_melee ? 'tak, utrudnienie' : 'nie'}; flankowanie: ${positioning.flanking ? 'tak, przewaga' : 'nie'}.</p>`;
}
function damageBreakdownHtml(result) {
  const breakdown = (result && result.damage_breakdown) || {};
  const components = breakdown.components || [];
  if (!components.length) return '';
  const adjustmentLabels = {
    normal: 'bez modyfikacji',
    resistance: 'odporność',
    immunity: 'niewrażliwość',
    vulnerability: 'podatność',
    resistance_and_vulnerability: 'odporność i podatność',
  };
  const rows = components.map(component => {
    const changed = Number(component.amount_before) !== Number(component.amount_applied);
    const amounts = changed
      ? `${esc(component.amount_before)} → ${esc(component.amount_applied)}`
      : `${esc(component.amount_applied)}`;
    return `${amounts} ${esc(component.damage_type_label || component.damage_type)}${component.adjustment !== 'normal' ? ` (${esc(adjustmentLabels[component.adjustment] || component.adjustment)})` : ''}`;
  });
  return `<p><b>Rozliczenie obrażeń:</b> ${rows.join(', ')}; razem ${esc(breakdown.total_before_reduction)} → ${esc(breakdown.total_applied)}.</p>`;
}
function enemyTurnIntentHtml(intent) {
  return `
    <button data-allow-busy="true" data-card-action="accept" onclick="resolveEnemyTurn()">Potwierdź zamiar przeciwnika</button>
  `;
}
function enemyTurnResultHtml(result) {
  const target = result.target_name || 'cel';
  const hasAttack = result.hit !== null && result.hit !== undefined;
  const save = result.saving_throw_result;
  const outcome = save ? (save.success ? 'UDANA OBRONA' : 'NIEUDANA OBRONA') : hasAttack ? (result.hit ? (result.critical ? 'TRAFIENIE KRYTYCZNE' : 'TRAFIENIE') : 'PUDŁO') : 'BRAK ATAKU';
  const damage = result.damage === null || result.damage === undefined ? 0 : result.damage;
  const roll = result.natural_roll === null || result.natural_roll === undefined
    ? ''
    : `<p><b>Rzut:</b> d20 ${esc(d20RollResultText(result))}, razem ${esc(result.total)} — ${outcome}.</p>`;
  const hp = result.damage_result
    ? `<p><b>PW ${esc(target)}:</b> ${esc(result.damage_result.hp_before)} → ${esc(result.damage_result.hp_after)}${result.damage_result.defeated_by_damage ? ' — cel pokonany' : ''}.</p>`
    : '';
  return `
    <div class="enemy-attack-summary">
      <h3 class="enemy-outcome">${outcome}</h3>
      <p><b>${esc(result.enemy_name || 'Przeciwnik')} → ${esc(target)}</b></p>
      ${roll}
      ${save ? spellSavesHtml([save]) : ''}
      <p class="enemy-damage-value"><b>Obrażenia: ${esc(damage)}</b></p>
      ${hp}
      <details><summary>Szczegóły trafienia i obrażeń</summary>${damageBreakdownHtml(result.damage_result)}<p>${esc(result.message || '')}</p></details>
      <button data-allow-busy="true" data-card-action="accept" onclick="confirmEnemyTurnResult()">✓ Dalej</button>
    </div>
  `;
}
function longCastHtml(cast, combat) {
  const actionSpent = ((combat.turn_action || {}).action_use || '') !== 'action_available';
  return `
    <div class="combat-action-box">
      <p><b>Rzucanie: ${esc(cast.label || cast.spell_id)}</b></p>
      <p>Postęp ${esc(cast.completed_actions)}/${esc(cast.required_actions)} akcji (${esc(cast.progress_percent)}%). Pozostało: ${esc(cast.remaining_actions)}.</p>
      <p class="muted">Musisz poświęcić akcję w każdej swojej turze i utrzymać koncentrację. Slot zostanie zużyty dopiero po ukończeniu.</p>
      <div class="row">
        <button data-allow-busy="true" ${actionSpent ? 'disabled title="Akcja w tej turze została już zużyta."' : ''} onclick="continueLongCast()">Kontynuuj rzucanie</button>
        <button class="secondary" data-allow-busy="true" onclick="cancelLongCast()">Przerwij bez zużycia slotu</button>
      </div>
    </div>
  `;
}
function pendingSummonHtml(pending) {
  const positions = pending.legal_positions || [];
  const selected = (((state || {}).combat || {}).pending_board_selection) || null;
  return `
    <div class="combat-action-box">
      <p><b>Wybierz pole przywołania</b></p>
      <p class="muted">Plansza pokaże ${esc(positions.length)} wolnych i widocznych pól w zasięgu. Kliknięcie wybiera pole; ✓ wykonuje przywołanie.</p>
      <div class="row">
        <button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>
        <button data-allow-busy="true" onclick="confirmCombatPendingBoardSelection()"${selected ? '' : ' disabled'}>✓ Potwierdź</button>
        <button class="secondary" data-allow-busy="true" onclick="cancelSummon()">Anuluj</button>
      </div>
    </div>
  `;
}
function pendingMagicMovementHtml(pending) {
  const selected = (((state || {}).combat || {}).pending_board_selection) || null;
  if (pending.action_id === 'field_medic_step') {
    return `
      <div class="combat-action-box field-medic-step-prompt">
        <p><b>Krok ratowniczki</b></p>
        <p>Czy chcesz przesunąć Dagnę o 5 stóp bez prowokowania ataku okazyjnego?</p>
        <div class="row">
          <button data-primary-scan="true" onclick="scanBoard()">Tak — wybierz pole</button>
          <button data-allow-busy="true" onclick="confirmCombatPendingBoardSelection()"${selected ? '' : ' disabled'}>✓ Potwierdź</button>
          <button class="secondary" data-allow-busy="true" onclick="cancelMagicMovement()">Nie</button>
        </div>
      </div>
    `;
  }
  if (pending.kind === 'teleport') {
    const positions = pending.legal_positions || [];
    return `
      <div class="combat-action-box">
        <p><b>Wybierz pole teleportacji</b></p>
        <div class="row">
          <button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>
          <span class="muted">Kliknij podświetlone pole, a potem zatwierdź przyciskiem ✓.</span>
          <button data-allow-busy="true" onclick="confirmCombatPendingBoardSelection()"${selected ? '' : ' disabled'}>Potwierdź</button>
          <button class="secondary" data-allow-busy="true" onclick="cancelMagicMovement()">Anuluj</button>
        </div>
      </div>
    `;
  }
  return `
    <div class="combat-action-box">
      <p><b>${pending.kind === 'push' ? 'Odepchnij' : 'Przyciągnij'} cel</b></p>
      <p class="muted">Cel wykona automatyczny rzut obronny po potwierdzeniu.</p>
      <div class="row">
        <button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>
        <span class="muted">Kliknij podświetloną figurkę celu, a potem zatwierdź przyciskiem ✓.</span>
        <button data-allow-busy="true" onclick="confirmCombatPendingBoardSelection()"${selected ? '' : ' disabled'}>Potwierdź</button>
        <button class="secondary" data-allow-busy="true" onclick="cancelMagicMovement()">Anuluj</button>
      </div>
    </div>
  `;
}
function pendingSpellDebuffHtml(pending) {
  const selected = (((state || {}).combat || {}).pending_board_selection) || null;
  const conditionOptions = pending.condition_options || [];
  const conditionSelect = conditionOptions.length
    ? `<label>Efekt czaru<select id="spell-debuff-condition" onchange="selectSpellDebuffCondition(this.value)">
        <option value="">— wybierz efekt —</option>${conditionOptions.map(value => (
        `<option value="${esc(value)}"${pending.selected_condition === value ? ' selected' : ''}>${esc(value)}</option>`
      )).join('')}</select></label>`
    : '';
  const conditionLabel = pending.condition || conditionOptions.join(' / ') || '-';
  return `
    <div class="combat-action-box">
      <p><b>${esc(pending.label || 'Czar osłabiający')}</b></p>
      ${pending.instructions ? `<p><b>Efekt w grze:</b> ${esc(pending.instructions)}</p>` : ''}
      <p class="muted">Stan: ${esc(conditionLabel)}; save ${esc(pending.save_ability || '-')} przeciw ST ${esc(pending.save_dc || '-')}.</p>
      <div class="row">
        <button data-primary-scan="true" onclick="scanBoard()"${conditionOptions.length && !pending.selected_condition ? ' disabled' : ''}>Skanuj planszę</button>
        ${conditionSelect}
        <span class="muted">Wybierz figurkę, a potem zatwierdź przyciskiem ✓.</span>
        <button data-allow-busy="true" onclick="confirmCombatPendingBoardSelection()"${selected ? '' : ' disabled'}>Potwierdź</button>
        <button class="secondary" data-allow-busy="true" onclick="cancelSpellDebuff()">Anuluj</button>
      </div>
    </div>
  `;
}
function pendingSpellDispelHtml(pending) {
  const selected = (((state || {}).combat || {}).pending_board_selection) || null;
  if (pending.stage === 'ability_check') {
    const check = pending.current_check || {};
    const modifier = Number(pending.check_modifier || 0);
    return `
      <div class="combat-action-box">
        <p><b>Test rozproszenia: ${esc(check.label || 'efekt czaru')}</b></p>
        <p class="muted">Poziom efektu ${esc(check.spell_level || '-')}; d20 ${signedNumber(modifier)} przeciw ST ${esc(check.dc || '-')}.</p>
        <div class="row">
          <label>Naturalny d20: <input id="spell-dispel-roll" type="number" min="1" max="20" value="10"></label>
          <button data-allow-busy="true" onclick="submitSpellDispelCheck()">Rozstrzygnij</button>
        </div>
      </div>
    `;
  }
  return `
    <div class="combat-action-box">
      <p><b>${esc(pending.label || 'Rozproszenie magii')}</b></p>
      ${pending.instructions ? `<p><b>Efekt w grze:</b> ${esc(pending.instructions)}</p>` : ''}
      <p class="muted">Wybierz istotę z co najmniej jednym aktywnym efektem czaru.</p>
      <div class="row">
        <button data-primary-scan="true" onclick="scanBoard()">Skanuj planszę</button>
        <span class="muted">Wybierz figurkę, a potem zatwierdź przyciskiem ✓.</span>
        <button data-allow-busy="true" onclick="confirmCombatPendingBoardSelection()"${selected ? '' : ' disabled'}>Potwierdź</button>
        <button class="secondary" data-allow-busy="true" onclick="cancelSpellDispel()">Anuluj</button>
      </div>
    </div>
  `;
}
function defensiveSpellReaction(combat) {
  const window = combat && combat.reaction_window;
  if (!window) return null;
  const options = window.options || [];
  return options.find(option => option.id === window.current_option_id && option.kind === 'defensive_spell') || null;
}
function classFeatureReaction(combat, kind) {
  const window = combat && combat.reaction_window;
  if (!window) return null;
  const options = window.options || [];
  return options.find(option => option.id === window.current_option_id && option.kind === kind) || null;
}
function cuttingWordsReactionHtml(option, preview) {
  const damageStage = option.trigger_event === 'damage_roll_revealed';
  const attackTotal = preview.total === undefined || preview.total === null ? '?' : preview.total;
  const damageTotal = ((preview.damage || {}).total_before_reduction
    ?? (preview.damage || {}).total_applied
    ?? '?');
  return `
    <p><b>${damageStage
      ? `Wrogi atak zadaje ${esc(damageTotal)} obrażeń.`
      : `Wrogi atak uzyskał ${esc(attackTotal)}.`}</b></p>
    <p>${esc(option.label || 'Cutting Words')} może obniżyć ${damageStage ? 'obrażenia przed ich zastosowaniem' : 'test ataku przed rozliczeniem trafienia'}. Zużywa reakcję i jedno użycie Bardic Inspiration.</p>
    <div class="row">
      <label>Wynik k${esc(option.value || 6)}:
        <input id="cutting-words-roll" type="number" min="1" max="${esc(option.value || 6)}" value="1">
      </label>
      <button data-allow-busy="true" onclick="submitCuttingWordsReaction()">Użyj Cutting Words</button>
      <button class="secondary" data-allow-busy="true" onclick="skipCuttingWordsReaction()">${damageStage ? 'Przyjmij obrażenia' : 'Nie obniżaj trafienia'}</button>
    </div>
  `;
}
function distractingShoutReactionHtml(option, preview) {
  const damageTotal = ((preview.damage || {}).total_before_reduction
    ?? (preview.damage || {}).total_applied
    ?? '?');
  return `
    <p><b>Wrogi atak zadaje ${esc(damageTotal)} obrażeń zainspirowanemu sojusznikowi.</b></p>
    <p>Rozpraszający okrzyk zużywa reakcję Loriena, ale nie zużywa kości Inspiracji. Redukcja wynosi k6+2, minimum do 0.</p>
    <div class="row">
      <label>Wynik k6:
        <input id="distracting-shout-roll" type="number" min="1" max="6" value="1">
      </label>
      <button data-allow-busy="true" onclick="submitDistractingShoutReaction()">Krzyknij</button>
      <button class="secondary" data-allow-busy="true" onclick="skipDistractingShoutReaction()">Nie reaguj</button>
    </div>
  `;
}
function deflectMissilesReactionHtml(option, window, preview) {
  if (window.stage === 'attack_roll') {
    return `
      <p><b>Pocisk został złapany.</b></p>
      <p>Możesz wydać 1 Ki i odrzucić go w napastnika jako atak bronią mnicha o zasięgu 20/60 ft. Dalszy zasięg wymaga dwóch k20 i wybiera niższy.</p>
      <div class="row">
        <label>k20: <input id="deflected-missile-roll" type="number" min="1" max="20" value="10"></label>
        <label>drugie k20 (jeśli wymagane): <input id="deflected-missile-roll-2" type="number" min="1" max="20"></label>
        <button data-allow-busy="true" onclick="returnDeflectedMissile()">Wydaj 1 Ki i odrzuć</button>
        <button class="secondary" data-allow-busy="true" onclick="skipDeflectMissilesReaction()">Zatrzymaj pocisk</button>
      </div>
    `;
  }
  if (window.stage === 'damage_roll') {
    return `
      <p><b>Odrzucony pocisk trafił.</b></p>
      <p>Rzuć ${window.critical ? '2k4' : '1k4'} + modyfikator DEX mnicha i wpisz sumę obrażeń.</p>
      <div class="row">
        <label>Obrażenia: <input id="deflected-missile-damage" type="number" min="0" value="1"></label>
        <button data-allow-busy="true" onclick="submitDeflectedMissileDamage()">Zapisz obrażenia</button>
      </div>
    `;
  }
  const damage = ((preview.damage || {}).total_applied ?? option.value ?? '?');
  return `
    <p><b>Trafienie dystansową bronią zadaje ${esc(damage)} obrażeń.</b></p>
    <p>Deflect Missiles zmniejsza obrażenia o k10 + DEX + poziom mnicha. Gdy redukcja wyzeruje obrażenia i mnich ma wolną rękę, łapie pocisk.</p>
    <div class="row">
      <label>Wynik k10: <input id="deflect-missiles-roll" type="number" min="1" max="10" value="1"></label>
      <button data-allow-busy="true" onclick="submitDeflectMissilesReaction()">Odbij pocisk</button>
      <button class="secondary" data-allow-busy="true" onclick="skipDeflectMissilesReaction()">Przyjmij obrażenia</button>
    </div>
  `;
}
function counterspellReaction(combat) {
  const window = combat && combat.reaction_window;
  if (!window) return null;
  const options = window.options || [];
  return options.find(option => option.id === window.current_option_id && option.kind === 'spell_counter') || null;
}
function counterspellReactionHtml(option, window, preview) {
  const source = preview.source || {};
  const enemySpellLevel = Number(source.cast_level || source.spell_level || 0);
  if (window.stage === 'ability_check') {
    return `
      <p><b>${esc(option.label || 'Kontrczar')} wymaga testu cechy rzucania czarów.</b></p>
      <p>Wrogi czar: ${esc(source.name || 'nieznany')} · poziom ${esc(enemySpellLevel)} · ST ${esc(window.dc || 10 + enemySpellLevel)} · modyfikator ${esc(signedNumber(window.modifier || 0))}.</p>
      <div class="row">
        <label>Naturalny wynik d20: <input id="counterspell-roll" type="number" min="1" max="20" value="10"></label>
        <button data-allow-busy="true" onclick="submitCounterspellCheck()">Rozstrzygnij Kontrczar</button>
      </div>
    `;
  }
  const levels = option.cast_levels || [];
  const choices = levels.map(level => `<option value="${esc(level)}">slot ${esc(level)}. poziomu</option>`).join('');
  return `
    <p><b>${esc(preview.enemy_name || 'Przeciwnik')} rzuca ${esc(source.name || 'czar')}.</b></p>
    <p>${esc(option.label || 'Kontrczar')} automatycznie przerwie czar do poziomu użytego slotu. Silniejszy czar wymaga testu cechy rzucania czarów ST 10 + poziom czaru.</p>
    <div class="row">
      <label>Slot: <select id="counterspell-cast-level">${choices}</select></label>
      <button data-allow-busy="true" onclick="castCounterspellReaction()">Rzuć ${esc(option.label || 'Kontrczar')}</button>
      <button class="secondary" data-allow-busy="true" onclick="skipCounterspellReaction()">Nie kontruj</button>
    </div>
  `;
}
function defensiveSpellReactionHtml(option, preview) {
  const attackTotal = preview.total === undefined || preview.total === null ? '?' : preview.total;
  const currentAc = preview.target_ac === undefined || preview.target_ac === null ? '?' : preview.target_ac;
  const nextAc = currentAc === '?' ? '?' : Number(currentAc) + Number(option.value || 0);
  return `
    <p><b>Atak ${esc(attackTotal)} przeciw AC ${esc(currentAc)} trafił.</b></p>
    <p>${state.combat?.physical_mana ? `Tarcza: +3 KP przeciw temu jednemu atakowi. Wydaj ${manaCostHtml(['B'])} i reakcję. KP: ${currentAc === '?' ? '?' : Number(currentAc)+3}.` : `${esc(option.label || 'Czar obronny')} podniesie AC do ${esc(nextAc)} aż do początku następnej tury bohatera. Zużyje reakcję i slot poziomu ${esc(option.spell_level || 1)}.`}</p>
    <div class="row">
      <button data-allow-busy="true" onclick="castDefensiveSpellReaction()">Rzuć ${esc(option.label || 'czar obronny')}</button>
      <button class="secondary" data-allow-busy="true" onclick="skipDefensiveSpellReaction()">Przyjmij trafienie</button>
    </div>
  `;
}
function pendingEnemySavingThrowHtml(pending) {
  const request = pending.request || {};
  const target = pending.target || {};
  const secondRoll = pending.roll_mode === 'normal' ? '' : `
    <label>Drugi wynik d20: <input id="enemy-saving-throw-roll-2" type="number" min="1" max="20" value="10"></label>
  `;
  const inspiration = pending.bardic_inspiration;
  const inspirationInput = inspiration ? `
    <label>${esc(inspiration.label || 'Bardic Inspiration')} (opcjonalnie):
      <input id="enemy-saving-throw-inspiration" type="number" min="1" max="${Number(inspiration.die_sides)}" placeholder="nie używaj">
    </label>
  ` : '';
  const bless = pending.bless;
  const blessInput = bless ? `
    <label>${esc(bless.label || 'Bless')} (k4):
      <input id="enemy-saving-throw-bless" type="number" min="1" max="${Number(bless.die_sides)}" required>
    </label>
  ` : '';
  return `
    <p>${esc(pending.instruction || '')}</p>
    <div class="row">
      <label>Naturalny wynik d20: <input id="enemy-saving-throw-roll" type="number" min="1" max="20" value="10"></label>
      ${secondRoll}
      ${inspirationInput}
      ${blessInput}
      <button data-allow-busy="true" onclick="submitEnemySavingThrow()">Rozstrzygnij rzut</button>
    </div>
    <p class="muted">${esc(target.name || 'Bohater')} · ${esc(request.ability_label || abilityLabel(request.ability))} ${esc(signedNumber(pending.modifier || 0))} · ST ${esc(request.dc)}</p>
  `;
}
function pendingEnemySavingThrowDetailsHtml(pending) {
  const request = pending.request || {};
  const components = pending.modifier_components || [];
  return `
    <p><b>Źródło:</b> ${esc(request.source_label || '-')}</p>
    <p><b>Rzut:</b> ${esc(request.ability_label || abilityLabel(request.ability))} przeciw ST ${esc(request.dc)}.</p>
    <p><b>Modyfikatory:</b> ${components.map(item => `${esc(item.label)} ${esc(signedNumber(item.value || 0))}`).join(', ') || esc(signedNumber(pending.modifier || 0))}.</p>
    <p><b>Sukces:</b> ${esc(request.success_effect_label || 'brak efektu')}. <b>Porażka:</b> ${esc(request.failure_effect_label || 'pełny efekt')}.</p>
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
      ${physicalDamageBonusChoicesHtml(pending)}
      <div class="row">
        ${damageComponentInputsHtml(pending, 'enemy-opportunity-damage', source)}
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
  const selected = pending.selected_ally || null;
  return `
    <p><b>Help:</b> najpierw wskaż na planszy sojusznika, a potem przeciwnika, przeciw któremu otrzyma przewagę na następny atak.</p>
    ${selected ? `<p>Wybrany sojusznik: <b>${esc(selected.name)}</b>. Teraz wskaż przeciwnika.</p>` : ''}
    <div class="row">
      <button data-primary-scan="true" onclick="scanBoard()">${selected ? 'Pokaż przeciwników' : 'Pokaż sojuszników'}</button>
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
function pendingClassFeatureTargetingHtml(pending) {
  const selected = pending.selected_target || null;
  const selectedDestination = pending.selected_destination || null;
  const selectingDestination = Boolean(pending.selecting_destination);
  const selectedTargets = pending.selected_targets || [];
  const needsPoints = ['lay_on_hands', 'preserve_life'].includes(pending.action_id);
  const preserveLife = pending.action_id === 'preserve_life';
  let remainingHealing = Number(pending.healing_pool || 0);
  const allocationRows = selectedTargets.map(target => {
    const maximum = Number(target.maximum_healing || 0);
    const suggested = Math.min(maximum, remainingHealing);
    remainingHealing = Math.max(0, remainingHealing - suggested);
    return `
      <label>${esc(target.name)} · ${esc(target.hp)}/${esc(target.max_hp)} PW
        <input class="preserve-life-allocation" data-target-id="${esc(target.id)}" type="number" min="0" max="${esc(maximum)}" value="${esc(suggested)}" required>
      </label>`;
  }).join('');
  const healingInputs = preserveLife && selectedTargets.length ? `
    <p><b>Pula leczenia:</b> ${esc(pending.healing_pool || 0)} PW. Każdy cel można uleczyć najwyżej do połowy maksymalnych PW.</p>
    <div class="status-list">
      ${allocationRows}
    </div>` : '';
  return `
    <div class="combat-action-box">
      <p><b>${esc(pending.label || 'Cecha klasowa')}</b></p>
      <p><b>Efekt w grze:</b> ${esc(pending.instructions || '')}</p>
      <p><b>Koszt:</b> ${pending.mana_cost ? manaCostHtml(pending.mana_cost) : manaTextHtml(pending.cost || '-')}</p>
      <p class="muted">Legalne figurki zostaną podświetlone. Kliknięcie wybiera cel; dopiero ✓ wykonuje albo rozwija akcję.</p>
      ${preserveLife
        ? `<p><b>Wybrane cele:</b> ${selectedTargets.map(target => esc(target.name)).join(', ') || 'brak'}</p>`
        : selected ? `<p><b>Wybrany cel:</b> ${esc(selected.name)}</p>` : ''}
      ${healingInputs}
      ${selectedDestination ? `<p><b>Pole odepchnięcia:</b> (${esc(selectedDestination.col)}, ${esc(selectedDestination.row)})</p>` : ''}
      <div class="row">
        <button data-primary-scan="true" onclick="scanBoard()">Pokaż legalne cele</button>
        ${needsPoints && !preserveLife ? `<label>Punkty leczenia<input id="class-feature-board-points" type="number" min="1" required></label>` : ''}
        ${needsPoints
          ? `<button data-allow-busy="true" onclick="confirmClassFeatureBoardTarget()"${(preserveLife ? selectedTargets.length : selected) ? '' : ' disabled'}>Potwierdź użycie</button>`
          : `<button data-allow-busy="true" onclick="confirmClassFeatureTargetSelection()"${(selectingDestination ? selectedDestination : selected) ? '' : ' disabled'}>✓ Potwierdź</button>`}
        <button class="secondary" data-allow-busy="true" onclick="cancelClassFeatureTargeting()">Anuluj</button>
      </div>
    </div>
  `;
}
function pendingConcentrationActionHtml(pending) {
  const action = pending.action || {};
  if (pending.casting_ready) {
    return `
      <div class="combat-action-box">
        <p><b>${esc(action.label || action.name || 'Czar')}</b> jest przygotowany.</p>
        <p>Wybrane cele i wynik rzutu zostały zapisane. Ukończenie przesunie zegar scenariusza o ${esc(pending.casting_minutes || 10)} minut, następnie zużyje slot i zastosuje leczenie.</p>
        <p class="muted">Jeżeli modlitwa została przerwana przez zagrożenie, ruch albo inną czynność, anuluj ją — slot nie zostanie zużyty.</p>
        <div class="row">
          <button data-allow-busy="true" onclick="completeTimedCombatSpell()">Minęło 10 minut — ukończ</button>
          <button class="secondary" data-allow-busy="true" onclick="cancelConcentrationAction()">Przerwij bez zużycia slotu</button>
        </div>
      </div>`;
  }
  const targets = pending.targets || [];
  const selected = new Set(pending.selected_target_ids || []);
  const selectedTargets = targets.filter(actor => selected.has(actor.id));
  const dieSides = Number(action.damage_die_sides || 0);
  const poolDice = Number(action.hit_point_pool_dice_count || 0)
    + Math.max(0, Number(pending.cast_level || 0) - Number(action.spell_level || 0))
      * Number(action.upcast_hit_point_pool_dice_per_level || 0);
  const enhanceAbilityRoll = action.id === 'enhance_ability';
  const valueDice = enhanceAbilityRoll ? 2 : poolDice;
  const manualValueRoll = poolDice > 0 || action.effect_kind === 'temporary_hit_points' || enhanceAbilityRoll;
  const rollInput = dieSides && manualValueRoll
    ? `<label>${enhanceAbilityRoll ? '2k6 tylko dla wariantu Kondycja' : 'Suma fizycznego rzutu'} ${valueDice ? `${valueDice}k${dieSides}` : `k${dieSides}`}<input id="combat-status-roll" type="number" min="${Math.max(1, valueDice)}" max="${dieSides * Math.max(1, valueDice)}" inputmode="numeric"></label>`
    : '';
  const effectOptions = Array.isArray(pending.removable_effect_options)
    ? pending.removable_effect_options
    : (action.effect_options || []);
  const effectOptionLabels = {
    blinded: 'Oślepiony',
    deafened: 'Ogłuchnięty',
    paralyzed: 'Sparaliżowany',
    poisoned: 'Zatruty',
  };
  const weaponOptions = pending.weapon_options || [];
  const effectSelect = weaponOptions.length
    ? `<label>Niemagiczna broń<select id="combat-status-effect-option">${weaponOptions.map(value => (
        `<option value="${esc(value.id)}">${esc(value.name)}</option>`
      )).join('')}</select></label>`
    : effectOptions.length && !(action.effect_kind === 'remove_condition' && effectOptions.length === 1)
    ? `<label>Wariant efektu<select id="combat-status-effect-option">${effectOptions.map(value => (
        `<option value="${esc(value)}">${esc(effectOptionLabels[value] || value.replaceAll('_', ' '))}</option>`
      )).join('')}</select></label>`
    : '';
  const choosingArea = pending.selection_mode === 'area' && !pending.anchor;
  const chosenNames = selectedTargets.map(actor => esc(actor.name)).join(', ');
  const hasSelection = selected.size > 0;
  return `
    <p><b>${esc(action.label || action.name || 'Czar')}</b> ${state.combat?.physical_mana ? '' : `· slot ${esc(pending.cast_level || action.spell_level || '-')}`} </p>
    <p><b>Efekt w grze:</b> ${esc(action.instructions || 'Brak opisu mechanicznego — zgłoś błąd zawartości.')}</p>
    <p>${choosingArea
      ? 'Zeskanuj planszę i kliknij podświetlony środek albo kierunek obszaru.'
      : pending.selection_mode === 'area'
        ? `<b>Cele objęte obszarem:</b> ${chosenNames || 'brak'}`
        : `<b>Wybrane cele:</b> ${chosenNames || 'brak'} (maks. ${esc(pending.maximum_targets || 1)})`
    }</p>
    <div class="row">
      <button data-primary-scan="true" onclick="scanBoard()">${choosingArea ? 'Pokaż legalny obszar' : 'Pokaż legalne cele'}</button>
      ${rollInput}
      ${effectSelect}
      <button data-allow-busy="true" onclick="confirmConcentrationAction()"${choosingArea || !hasSelection ? ' disabled' : ''}>Potwierdź czar</button>
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
    <p><b>Czar:</b> ${esc(action.label || action.name || '-')} ${state.combat?.physical_mana ? '' : `· slot ${esc(pending.cast_level || action.spell_level || '-')}`} </p>
    <p><b>Koncentracja:</b> ${action.concentration ? 'tak' : 'nie'} | <b>Efekt:</b> ${esc(signedNumber(action.value || 0))} do ataku celu</p>
    <p><b>Limit celów:</b> ${esc(pending.maximum_targets || 1)}</p>
    <p><b>Legalni sojusznicy:</b> ${targets.map(actor => `${esc(actor.name)} (${esc(actor.position[0])},${esc(actor.position[1])})`).join(', ') || 'brak'}</p>
  `;
}
function pendingMultiTargetDamageSpellHtml(pending) {
  const selected = pending.selected_targets || [];
  const complete = Number(pending.selected_count || 0) === Number(pending.projectile_count || 0);
  const attackRoll = Boolean(pending.projectile_attack_roll);
  const diceCount = Number(pending.damage_dice_count || 1);
  const dieSides = Number(pending.damage_die_sides || 4);
  const rolls = selected.map((target, index) => `
    <label>Pocisk ${index + 1} → ${esc(target.name)}
      ${attackRoll ? `<span>d20 ataku</span><input id="multi-target-spell-attack-${index}" type="number" min="1" max="20"${complete ? ' required' : ' disabled'}>` : ''}
      <span>${diceCount}k${dieSides} obrażeń</span>
      <input id="multi-target-spell-roll-${index}" type="number" min="${diceCount}" max="${diceCount * dieSides}"${complete ? ' required' : ' disabled'}>
    </label>
  `).join('');
  return `
    <p>Wybrano ${esc(pending.selected_count || 0)} z ${esc(pending.projectile_count || 0)} pocisków. Klikaj podświetlone cele na planszy; jeden cel możesz wybrać wielokrotnie.</p>
    ${rolls ? `<div class="status-list">${rolls}</div>` : '<p class="muted">Nie wybrano jeszcze celu.</p>'}
    <div class="row">
      <button data-primary-scan="true" onclick="scanBoard()"${complete ? ' disabled' : ''}>Skanuj cel pocisku</button>
      <button class="secondary" data-allow-busy="true" onclick="clearMultiTargetDamageSpellTargets()">Wyczyść cele</button>
      <button data-allow-busy="true" onclick="confirmMultiTargetDamageSpell()"${complete ? '' : ' disabled'}>Rzuć czar</button>
      <button class="secondary" data-allow-busy="true" onclick="cancelMultiTargetDamageSpell()">Anuluj</button>
    </div>
  `;
}
function pendingMultiTargetDamageSpellDetailsHtml(pending) {
  const targetNames = (pending.selected_targets || []).map(target => esc(target.name));
  return `
    <p><b>Slot:</b> ${esc(pending.cast_level || '-')} · <b>Pociski:</b> ${esc(pending.projectile_count || 0)}</p>
    <p><b>Kolejność celów:</b> ${targetNames.join(' → ') || 'jeszcze nie wybrano'}</p>
    <p>${pending.projectile_attack_roll
      ? `Każdy promień wymaga osobnego fizycznego d20 i rzutu ${esc(pending.damage_dice_count || 1)}k${esc(pending.damage_die_sides || 4)} po trafieniu.`
      : 'Każdy pocisk trafia automatycznie i wymaga osobnego fizycznego rzutu obrażeń.'}</p>
  `;
}
function pendingConcentrationCheckHtml(pending) {
  const actor = pending.actor || {};
  const modifier = Number(pending.modifier || 0);
  const components = pending.modifier_components || [];
  return `
    <p>${esc(actor.name || 'Bohater')} utrzymuje koncentrację: ST ${esc(pending.dc)}.</p>
    <div class="row">
      <label>Wynik d20: <input id="concentration-check-roll" type="number" min="1" max="20" value="10"></label>
      ${pending.roll_mode && pending.roll_mode !== 'normal' ? '<label>Drugi wynik d20: <input id="concentration-check-roll-2" type="number" min="1" max="20" value="10"></label>' : ''}
      <button onclick="submitConcentrationCheck()">Zapisz rzut</button>
    </div>
    <p class="muted">Premia CON: ${esc(signedNumber(modifier))}${components.length ? ` (${components.map(item => `${esc(item.label)} ${esc(signedNumber(item.value))}`).join(', ')})` : ''}. Sukces utrzymuje efekt, porażka go kończy.</p>
  `;
}
function pendingConcentrationCheckDetailsHtml(pending) {
  const actor = pending.actor || {};
  const effects = pending.effects || [];
  return `
    <p><b>Koncentrujący:</b> ${esc(actor.name || '-')}</p>
    <p><b>Obrażenia:</b> ${esc(pending.damage)} | <b>ST:</b> ${esc(pending.dc)} | <b>Premia CON:</b> ${esc(signedNumber(pending.modifier || 0))}</p>
    <p><b>Składniki:</b> ${(pending.modifier_components || []).map(item => `${esc(item.label)} ${esc(signedNumber(item.value))}`).join(', ') || 'brak'}</p>
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
        ${damageComponentInputsHtml(pending, 'ready-damage', source)}
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
      <button data-allow-busy="true" onclick="confirmOpportunityMovement()">Rozstrzygnij atak okazyjny i wykonaj ruch</button>
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
  const rangedThreatWarning = rangedThreatWarningHtml(pending);
  const twinned = pending.twinned_spell || {};
  const twinnedControls = twinned.available
    ? `<div class="status"><b>${esc(twinned.label || 'Twinned Spell')}</b>
        <p>${twinned.selected_target_id ? 'Drugi cel został wskazany na planszy.' : `${twinned.optional ? 'Opcjonalnie wskaż' : 'Wskaż'} na planszy drugi legalny cel.`}</p>
        <button class="secondary" data-allow-busy="true" onclick="startAuxTargeting('twinned_attack')">Pokaż legalne drugie cele</button></div>`
    : '';
  if (pending.stage === 'open_hand_choice') {
    const technique = pending.open_hand_technique || {};
    return `
      <p><b>Open Hand Technique:</b> wybierz dodatkowy efekt trafienia Flurry of Blows przeciw ${esc(technique.target_name || target.name || 'celowi')}.</p>
      <p>ST Ki: ${esc(technique.save_dc || '-')}.</p>
      <div class="row">
        <button data-allow-busy="true" onclick="resolveOpenHandTechnique('prone')">DEX save lub powalenie</button>
        <button data-allow-busy="true" onclick="resolveOpenHandTechnique('push')">STR save lub odepchnięcie 15 ft</button>
        <button data-allow-busy="true" onclick="resolveOpenHandTechnique('no_reactions')">Bez reakcji</button>
        <button class="secondary" data-allow-busy="true" onclick="skipOpenHandTechnique()">Pomiń</button>
      </div>
    `;
  }
  if (pending.stage === 'repelling_blast_choice') {
    const repelling = pending.repelling_blast || {};
    return `
      <p><b>Repelling Blast:</b> możesz odepchnąć ${esc(repelling.target_name || target.name || 'cel')} o 10 ft bez rzutu obronnego.</p>
      <div class="row">
        <button data-allow-busy="true" onclick="resolveRepellingBlast(true)">Odepchnij 10 ft</button>
        <button class="secondary" data-allow-busy="true" onclick="resolveRepellingBlast(false)">Nie odpychaj</button>
      </div>
    `;
  }
  if (pending.stage === 'confirm_attack') {
    const modifierLabel = signedNumber(pending.attack_modifier || 0);
    if (source.save_ability) {
      const coverBonus = source.save_ability === 'dexterity' ? Number((pending.positioning || {}).cover_bonus || 0) : 0;
      return `
        <p>Cel: ${esc(target.name || '-')} | rzut obronny ${esc(abilityLabel(source.save_ability))} przeciw ST ${esc(pending.spell_save_dc || source.save_dc || '-')}</p>
        ${source.source_type === 'spell' ? spellMechanicalEffectHtml(source) : ''}
        ${coverBonus ? `<p>Osłona celu: +${esc(coverBonus)} do tego rzutu obronnego.</p>` : ''}
        ${twinnedControls}
        <div class="row">
          <button data-allow-busy="true" onclick="confirmPlayerAttackTarget()">Potwierdź czar</button>
          <button class="secondary" data-allow-busy="true" onclick="cancelPlayerAttackTarget()">Anuluj wybór celu</button>
        </div>
      `;
    }
    return `
      <p>Cel: ${esc(target.name || '-')} | AC ${esc(target.ac || '-')} | premia ${esc(modifierLabel)}</p>
      ${source.source_type === 'spell' ? spellMechanicalEffectHtml(source) : ''}
      ${rangedThreatWarning}
      ${twinnedControls}
      <div class="row">
        <button data-allow-busy="true" onclick="confirmPlayerAttackTarget()">Potwierdź atak</button>
        <button class="secondary" data-allow-busy="true" onclick="cancelPlayerAttackTarget()">Anuluj wybór celu</button>
      </div>
    `;
  }
  if (pending.stage === 'damage_roll') {
    const smiteLevels = pending.divine_smite_available_levels || [];
    const selectedSmite = Number(pending.divine_smite_slot_level || 0);
    const smiteControls = smiteLevels.length
      ? `<div class="row">
          <span>${selectedSmite ? `Divine Smite: slot ${esc(selectedSmite)}` : 'Divine Smite dostępny po trafieniu:'}</span>
          ${smiteLevels.map(level => `<button class="secondary" data-allow-busy="true" onclick="selectDivineSmite(${Number(level)})">slot ${esc(level)}</button>`).join('')}
        </div>`
      : '';
    const empowered = pending.empowered_spell || {};
    const empoweredControls = empowered.available
      ? `<button class="secondary" data-allow-busy="true" onclick="activateEmpoweredSpell()">Empowered Spell · przerzuć do ${esc(empowered.maximum_rerolled_dice)} kości (1 SP)</button>`
      : empowered.active
        ? `<p><b>Empowered Spell:</b> wpisz wynik po przerzuceniu do ${esc(empowered.maximum_rerolled_dice)} kości.</p>`
        : '';
    return `
      <p>${esc(pending.damage_instruction || 'Wpisz obrażenia po trafieniu.')}</p>
      ${spellSavesHtml(pending.saving_throws || [])}
      ${smiteControls}
      ${empoweredControls}
      <div class="row">
        ${damageComponentInputsHtml(pending, 'combat-damage', source)}
        <button onclick="submitPlayerDamageRoll()">Zapisz obrażenia</button>
        <button class="secondary" data-allow-busy="true" onclick="finishCombatTurn()">Zakończ turę</button>
      </div>
    `;
  }
  return `
    <p>${esc(pending.attack_instruction || 'Rzuć 1d20 i wpisz wynik.')}</p>
    ${rangedThreatWarning}
    <div class="row">
      ${d20RollInputsHtml('combat-attack-natural-roll', pending.attack_mode)}
      ${pending.bardic_inspiration ? `<label>${esc(pending.bardic_inspiration.label)} (opcjonalnie)
        <input id="combat-bardic-inspiration-roll" type="number" min="1" max="${Number(pending.bardic_inspiration.die_sides)}" placeholder="nie używaj">
      </label>` : ''}
      ${pending.bless ? `<label>${esc(pending.bless.label)} (k4)
        <input id="combat-bless-roll" type="number" min="1" max="${Number(pending.bless.die_sides)}" required>
      </label>` : ''}
      ${pending.mirror_image ? `<label>Lustrzane odbicia — dodatkowe k20
        <input id="combat-mirror-image-roll" type="number" min="1" max="20" required>
        <small>${esc(pending.mirror_image.duplicates)} duplikaty; przekierowanie od ${esc(pending.mirror_image.redirect_threshold)}+, KP duplikatu ${esc(pending.mirror_image.duplicate_ac)}.</small>
      </label>` : ''}
      <button onclick="submitPlayerAttackRoll()">Zapisz rzut</button>
      <button class="secondary" data-allow-busy="true" onclick="finishCombatTurn()">Zakończ turę</button>
    </div>
  `;
}
function rangedThreatWarningHtml(pending) {
  const threats = (((pending || {}).positioning || {}).ranged_threats || []);
  if (!threats.length) return '';
  const names = threats.map(actor => `${actor.name} na (${actor.position[0]},${actor.position[1]})`).join(', ');
  return `<p class="combat-warning"><b>Utrudnienie do ataku dystansowego:</b> ${esc(names)} znajduje się 5 ft od strzelca. Przeciwnik nie musi być celem tego ataku.</p>`;
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
  const isSpell = source.source_type === 'spell';
  const targets = pending.targets || [];
  const auxMode = (((state || {}).combat || {}).aux_targeting_mode) || '';
  const targetText = targets.map(target => `${target.name} (${target.position[0]},${target.position[1]})`).join(', ') || 'brak celów';
  const friendlyFire = areaSpellFriendlyFireHtml(pending);
  const sculpt = pending.sculpt_spells || {};
  const sculptControls = sculpt.available
    ? `<div class="status"><b>Sculpt Spells</b><p>Wskaż na planszy do ${esc(sculpt.maximum_targets)} chronionych sojuszników.</p>
        <p>Chronieni: ${(pending.protected_targets || []).map(target => esc(target.name)).join(', ') || 'brak'}.</p>
        <button class="secondary" data-allow-busy="true" onclick="startAuxTargeting('sculpt_spells')">Wybierz na planszy</button>
        ${auxMode === 'sculpt_spells' ? '<button class="secondary" data-allow-busy="true" onclick="finishAuxTargeting()">Zakończ wybór</button>' : ''}</div>`
    : (pending.protected_targets || []).length
      ? `<p><b>Sculpt Spells:</b> ochronieni: ${(pending.protected_targets || []).map(target => esc(target.name)).join(', ')}</p>`
      : '';
  const metamagic = pending.metamagic || {};
  const careful = metamagic.careful || {};
  const heightened = metamagic.heightened || {};
  const metamagicControls = careful.available || heightened.available
    ? `<div class="status"><b>Metamagic</b>
        ${careful.available ? `<p>Careful Spell: wskaż na planszy do ${esc(careful.maximum_targets)} istot. Wybrane: ${(pending.careful_targets || []).map(target => esc(target.name)).join(', ') || 'brak'}.</p>
          <button class="secondary" data-allow-busy="true" onclick="startAuxTargeting('careful_spell')">Wybierz cele Careful</button>` : ''}
        ${heightened.available ? `<p>Heightened Spell: wskaż na planszy jedną istotę, która wykona pierwszy save z utrudnieniem.</p>
          <button class="secondary" data-allow-busy="true" onclick="startAuxTargeting('heightened_spell')">Wybierz cel Heightened</button>` : ''}
        ${['careful_spell', 'heightened_spell'].includes(auxMode) ? '<button class="secondary" data-allow-busy="true" onclick="finishAuxTargeting()">Zakończ wybór</button>' : ''}
      </div>`
    : '';
  if (pending.stage === 'attack_roll') {
    const mode = pending.volley_mode || 'normal';
    return `<p>Deszcz strzał: jeden wspólny test łuku przeciw KP każdego wroga w obszarze 3×3. ${mode === 'advantage' ? 'Przewaga.' : mode === 'disadvantage' ? 'Utrudnienie.' : ''}</p><label>k20<input type="number" id="volley-roll" min="1" max="20" required data-roll-label="Deszcz strzał · wspólny test"></label>${mode !== 'normal' ? '<label>Drugi k20<input type="number" id="volley-roll-2" min="1" max="20" required data-roll-label="Deszcz strzał · drugi k20"></label>' : ''}<button onclick="submitVolleyRoll()">✓ Potwierdź k20</button>`;
  }
  const volleySummary = pending.volley_hits?.length ? `<p>Wspólny wynik: <b>${pending.volley_total}</b></p><ul>${pending.volley_hits.map(h => `<li>${esc(pending.targets.find(t => t.id === h.actor_id)?.name || h.actor_id)} · KP ${h.armor_class} (osłona +${h.cover}): ${h.hit ? (h.critical ? 'krytyk' : 'trafienie') : 'pudło'}</li>`).join('')}</ul>` : '';
  if (pending.stage === 'volley_miss') return `${volleySummary}<button onclick="submitAreaSpellDamage()">✓ Zatwierdź wynik</button>`;
  if (pending.stage === 'damage_roll') {
    const empowered = pending.empowered_spell || {};
    const empoweredControls = empowered.available
      ? `<button class="secondary" data-allow-busy="true" onclick="activateEmpoweredSpell()">Empowered Spell · przerzuć do ${esc(empowered.maximum_rerolled_dice)} kości (1 SP)</button>`
      : empowered.active
        ? `<p><b>Empowered Spell:</b> wpisz wynik po przerzuceniu do ${esc(empowered.maximum_rerolled_dice)} kości.</p>`
        : '';
    return `
      ${volleySummary}${(pending.volley_bonuses || []).map(b => `<p>${esc(b.label)}: ${esc(pending.targets.find(t => t.id === b.target_id)?.name || b.target_id)} — premia tylko do tego celu.</p>`).join('')}<p>${esc(pending.damage_instruction || 'Wpisz obrażenia czaru obszarowego.')}</p>
      <p>Cele w obszarze: ${esc(targetText)}</p>
      ${friendlyFire}
      ${spellSavesHtml(pending.saving_throws || [])}
      ${empoweredControls}
      <div class="row">
        ${damageComponentInputsHtml(pending, 'area-spell-damage', source)}
        <button onclick="submitAreaSpellDamage()">Zapisz obrażenia</button>
        <button class="secondary" data-allow-busy="true" onclick="finishCombatTurn()">Zakończ turę</button>
      </div>
    `;
  }
  return `
    ${spellMechanicalEffectHtml(source)}
    <p>Obszar: ${esc((pending.area_positions || []).map(position => `(${position[0]},${position[1]})`).join(', ') || '-')}</p>
    <p>Cele w obszarze: ${esc(targetText)}</p>
    ${friendlyFire}
    ${sculptControls}
    ${metamagicControls}
    ${areaSpellCoverHtml(pending)}
    ${source.save_ability ? `<p>Rzut obronny: ${esc(abilityLabel(source.save_ability))} przeciw ST ${esc(pending.spell_save_dc || source.save_dc || '-')} | ${esc(saveSuccessLabel(source.save_damage_on_success))}</p>` : ''}
    <p class="board-confirm-instruction"><b>Podgląd obszaru:</b> kliknij ponownie jego środek na planszy, aby ${isSpell ? 'rzucić czar' : 'wykonać atak'}, albo kliknij inne podświetlone pole, aby zmienić podgląd.</p>
    <div class="row">
      <button class="secondary" data-allow-busy="true" onclick="confirmAreaSpell()"${auxMode ? ' disabled' : ''}>Potwierdź awaryjnie w UI</button>
      <button class="secondary" data-allow-busy="true" onclick="cancelAreaSpell()">Cofnij wybór obszaru</button>
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
    ${areaSpellFriendlyFireHtml(pending)}
    ${areaSpellCoverHtml(pending)}
    ${spellSavesHtml(pending.saving_throws || [])}
  `;
}
function areaSpellFriendlyFireHtml(pending) {
  const caster = pending.caster || {};
  const allies = (pending.targets || []).filter(target => target.faction === caster.faction);
  if (!allies.length) return '';
  return `<p class="combat-warning"><b>Friendly fire:</b> czar obejmie także ${allies.map(target => esc(target.name)).join(', ')}.</p>`;
}
function areaSpellCoverHtml(pending) {
  if (!pending.source || pending.source.save_ability !== 'dexterity') return '';
  const entries = pending.target_cover || [];
  const targets = pending.targets || [];
  const covered = entries.filter(entry => Number(entry.cover_bonus || 0) > 0);
  if (!covered.length) return '';
  const names = new Map(targets.map(target => [String(target.id), target.name]));
  return `<p><b>Osłona do rzutu na Zręczność:</b> ${covered.map(entry => {
    const sources = (entry.cover_sources || []).length ? ` (${entry.cover_sources.map(esc).join(', ')})` : '';
    return `${esc(names.get(String(entry.actor_id)) || entry.actor_id)} +${esc(entry.cover_bonus)}${sources}`;
  }).join('; ')}</p>`;
}
function pendingPlayerHealingHtml(pending) {
  const target = pending.target || {};
  const source = pending.source || {};
  const twinned = pending.twinned_spell || {};
  const twinnedControls = twinned.available
    ? `<div class="status"><b>Twinned Spell</b><p>Wskaż drugi cel leczenia na planszy.</p>
        <button class="secondary" data-allow-busy="true" onclick="startAuxTargeting('twinned_healing')">Pokaż legalne drugie cele</button></div>`
    : '';
  return `
    ${source.source_type === 'spell' ? `<p><b>Efekt w grze:</b> ${esc(source.healing_hint || pending.healing_instruction || '-')} punktów leczenia wybranemu celowi.</p>` : ''}
    <p>${esc(pending.healing_instruction || 'Rzuć leczenie i wpisz wynik.')}</p>
    ${twinnedControls}
    <div class="row">
      <label>Leczenie: <input id="combat-healing-roll" type="number" min="0" inputmode="numeric" value="${esc(defaultHealingValue(source))}" data-roll-label="Leczenie" data-roll-dice="${esc(source.healing_die_sides ? `${source.healing_dice_count || 1}d${source.healing_die_sides}` : '')}" data-roll-modifier="${esc(source.healing_modifier || 0)}" data-roll-source="${esc(source.name || 'Źródło leczenia')}"${source.healing_fixed !== null && source.healing_fixed !== undefined ? ` data-roll-fixed="${esc(source.healing_fixed)}"` : ''}></label>
      <button onclick="submitPlayerHealingRoll()">Zapisz leczenie</button>
      <button class="secondary" data-allow-busy="true" onclick="cancelPlayerHealing()">Anuluj</button>
    </div>
    <p class="muted">Cel: ${esc(target.name || '-')}.</p>
  `;
}
function spellMechanicalEffectHtml(source) {
  const parts = [];
  if (source.damage_hint) parts.push(`${source.damage_hint} obrażeń${source.damage_type ? ` typu ${source.damage_type}` : ''}`);
  if (source.area && source.area.shape) parts.push(`obszar: ${source.area.shape}`);
  if (source.save_ability) parts.push(`rzut obronny: ${abilityLabel(source.save_ability)}, ${saveSuccessLabel(source.save_damage_on_success)}`);
  (source.tabletop_riders || []).forEach(rider => parts.push(rider));
  return `<p><b>Efekt w grze:</b> ${esc(parts.join('; ') || 'Efekt zostanie rozstrzygnięty zgodnie z opisem czaru.')}</p>`;
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

function combatMenuCategoryLabel(category) {
  return ({field: 'Pole', attack: 'Ataki bronią', maneuver: 'Manewry', magic: 'Czary', item: 'Przedmioty', support: 'Wsparcie i leczenie', equipment: 'Ekwipunek', basic: 'Akcje podstawowe', turn: 'Tura'})[category] || 'Inne';
}
function combatContextMenuHtml(menu) {
  const options = menu.options || [];
  if (!options.length) {
    return `<p>Brak dostępnych akcji.</p><button class="secondary" data-allow-busy="true" onclick="cancelCombatContextMenu()">Wróć</button>`;
  }
  const selectedIndex = Math.max(0, Math.min(options.length - 1, Number(menu.selected_index || 0)));
  const windowSize = 5;
  const windowStart = Math.max(0, Math.min(
    selectedIndex - Math.floor(windowSize / 2),
    Math.max(0, options.length - windowSize),
  ));
  const visibleOptions = options.slice(windowStart, windowStart + windowSize);
  const hiddenBefore = windowStart;
  const hiddenAfter = Math.max(0, options.length - windowStart - visibleOptions.length);
  let previousCategory = '';
  const rows = visibleOptions.map((option, visibleIndex) => {
    const index = windowStart + visibleIndex;
    const groupLabel = option.group_label || combatMenuCategoryLabel(option.category);
    const heading = groupLabel !== previousCategory
      ? `<div class="combat-context-category">${esc(groupLabel)}</div>`
      : '';
    previousCategory = groupLabel;
    const selected = index === Number(menu.selected_index || 0);
    if (option.loot_quantity_max !== null && option.loot_quantity_max !== undefined) {
      return `${heading}${combatLootQuantityOptionHtml(option, index, selected)}`;
    }
    return `${heading}<button class="combat-context-option${selected ? ' selected' : ''}" data-allow-busy="true" onclick="confirmCombatContextMenu('${esc(option.id)}', ${index})" aria-current="${selected ? 'true' : 'false'}"><b>${manaTextHtml(option.label)}</b><span>${manaTextHtml(option.description || '')}</span></button>`;
  }).join('');
  return `
    <div class="combat-context-heading"><span>Wskazane pole na planszy · opcja ${esc(selectedIndex + 1)} z ${esc(options.length)}</span><b>${esc(menu.title || 'Dostępne akcje')}</b></div>
    ${menu.notice ? `<p class="combat-warning"><b>Ograniczenie rozmiaru:</b> ${esc(menu.notice)}</p>` : ''}
    ${hiddenBefore ? `<div class="combat-context-overflow">▲ jeszcze ${esc(hiddenBefore)} wyżej</div>` : ''}
    <div class="combat-context-menu">${rows}</div>
    ${hiddenAfter ? `<div class="combat-context-overflow">▼ jeszcze ${esc(hiddenAfter)} niżej</div>` : ''}
    <div class="numpad-combat-hint"><span>Wybierz opcję na ekranie</span><span>✓ potwierdź</span><span>↩ wróć</span></div>
    <div class="row combat-fallback-actions"><button data-allow-busy="true" onclick="confirmCombatContextMenu('')">Wybierz zaznaczone</button><button class="secondary" data-allow-busy="true" onclick="cancelCombatContextMenu()">Wróć</button></div>
  `;
}
function combatTurnActionUnavailableHtml(menu, combat) {
  if (menu.stage !== 'preview') return '';
  const options = menu.options || [];
  const selected = options[Math.max(0, Math.min(options.length - 1, Number(menu.selected_index || 0)))] || {};
  let message = '';
  if (selected.action === 'select_attack_source') {
    const hasTarget = (combat.legal_targets || []).length > 0;
    const hasArea = (combat.legal_area_positions || []).length > 0;
    if (!hasTarget && !hasArea) {
      message = 'Brak legalnych celów dla tej akcji. Zatwierdzenie nie uruchomi skanowania; wybierz inną dostępną ikonę albo najpierw zmień pozycję.';
    }
  } else if (selected.action === 'select_healing_source' && !(combat.legal_healing_targets || []).length) {
    message = 'Brak rannego, legalnego celu leczenia w zasięgu. Skan planszy został zatrzymany — wybierz inną dostępną ikonę.';
  } else if (selected.action === 'move' && !(combat.movement && (combat.movement.destinations || []).length)) {
    message = 'Brak legalnego pola ruchu. Wybierz inną dostępną ikonę.';
  }
  return message ? `<div class="combat-action-unavailable" role="status"><b>Ta akcja jest teraz niedostępna</b><span>${esc(message)}</span></div>` : '';
}
function rememberCombatActorDetails(details) {
  if (details.isConnected) combatActorDetailsActorId = details.open ? details.dataset.actorId : '';
}
function combatTurnActorStatsHtml(combat) {
  const actor = combat.current_actor || {};
  const manaHand = combat.shared_mana?.pool_view?.hands.find(h => h.hero === actor.id);
  const slots = (actor.spell_slots || []).filter(slot => Number(slot.maximum || 0) > 0);
  const pools = (actor.resource_pools || []).filter(pool => Number(pool.maximum || 0) > 0);
  const slotText = slots.length
    ? slots.map(slot => `${esc(slot.level)}. poziom ${esc(slot.remaining)}/${esc(slot.maximum)}`).join(' · ')
    : 'brak slotów';
  const poolText = pools.length
    ? pools.map(pool => `${esc(pool.label)} ${esc(pool.current)}/${esc(pool.maximum)}`).join(' · ')
    : 'brak zasobów specjalnych';
  return `
    <details class="combat-actor-details" data-actor-id="${esc(actor.id || '')}" ontoggle="rememberCombatActorDetails(this)"${combatActorDetailsActorId === String(actor.id) ? ' open' : ''}>
      <summary data-allow-busy="true">Szczegóły postaci · ${esc(actor.name || '-')}</summary>
      <div class="combat-turn-actor-stats">
        <div class="combat-turn-stat-block"><small>Poziom</small><span>${esc(actor.level || '-')}</span></div>
        ${manaHand ? `<div class="combat-turn-stat-block"><small>Mana z kart</small><span>${esc(manaHand.total)} pkt · ${manaHand.cards.length} kart</span></div>` : combat.physical_mana?.active_hero ? `<div class="combat-turn-stat-block"><small>Mana fizyczna</small><span>Karty na stole · pojemność ${combat.physical_mana.supply.capacity}</span></div>` : `<div class="combat-turn-stat-block"><small>Sloty czarów</small><span>${slotText}</span></div><div class="combat-turn-stat-block"><small>Zasoby</small><span>${poolText}</span></div>`}
        <div class="combat-turn-stat-block combat-turn-all-effects"><small>Stany i efekty</small>${statusChipsHtml(combatActorChips(actor).filter(chip => !isTurnResourceChip(chip)), 'Brak aktywnych efektów.')}</div>
      </div>
    </details>
  `;
}
function rememberCombatScreenFallback(details) {
  if (details.isConnected) combatScreenFallbackOpen = details.open;
}
function combatScreenFallbackHtml(content) {
  return `<details class="combat-touch-fallback" ontoggle="rememberCombatScreenFallback(this)"${combatScreenFallbackOpen ? ' open' : ''}>
    <summary data-allow-busy="true">Awaryjny wybór ekranowy</summary>
    ${content}
  </details>`;
}
function combatEconomyGroupsHtml(options, renderOption) {
  const order = ['action', 'bonus_action', 'reaction', 'modifier', 'free', 'object_interaction', 'movement', 'control'];
  const sorted = [...options].sort((a, b) => order.indexOf(a.action_economy || 'action') - order.indexOf(b.action_economy || 'action'));
  return `<div class="combat-keyboard-action-index" aria-label="Dostępne działania">${sorted.map(renderOption).join('')}</div>`;
}
function combatKeyboardTileHtml(option) {
  return `<span class="combat-keyboard-action-index-item economy-${esc(option.action_economy || 'action')}${option.panel_unavailable_reason ? ' unavailable' : ''}" title="${esc(option.panel_unavailable_reason || '')}" data-option-id="${esc(option.id)}">
    <span class="combat-panel-icon">${option.panel_icon || ''}</span>
    <span class="combat-action-tile-content"><small class="combat-tile-economy" title="${esc(option.action_economy_label || 'Akcja główna')}">${esc(option.action_economy === 'modifier' ? 'Wzmocnienie' : option.action_economy_label || 'Akcja główna')}</small><b>${manaTextHtml(combatActionTileLabel(option))}</b>${actionManaCostHtml(option)}</span>
  </span>`;
}
function combatTurnActionMenuHtml(menu, combat = {}) {
  const options = menu.options || [];
  if (!options.length) return '<p>Brak dostępnych działań.</p>';
  const selectedIndex = Math.max(0, Math.min(options.length - 1, Number(menu.selected_index || 0)));
  const previewActive = menu.stage === 'preview';
  const selected = options[selectedIndex] || {};
  if (!previewActive) {
    const keyboardOptions = options.filter(option => option.panel_slot !== null && option.panel_slot !== undefined);
    const shortcutIndex = keyboardOptions.length ? combatEconomyGroupsHtml(keyboardOptions, combatKeyboardTileHtml) : '';
    const fallbackRows = combatEconomyGroupsHtml(options, option => `
      <button class="combat-keyboard-fallback-option economy-${esc(option.action_economy || 'action')}" data-option-id="${esc(option.id)}" data-allow-busy="true" onclick="confirmCombatTurnAction('${esc(option.id)}')">
        <span class="combat-panel-icon">${option.panel_icon || '<small>Ekran</small>'}</span>
        <span><b>${manaTextHtml(combatActionTileLabel(option))}</b>${actionManaCostHtml(option)}<small>${manaTextHtml(option.description || '')}</small></span>
      </button>`);
    return `
      <div class="combat-turn-command-layout combat-keyboard-idle">
        <section class="combat-keyboard-waiting" role="status" aria-live="polite">
          <h3>Wybierz akcję na panelu planszy</h3>
          <p>Wybierz ikonę na ekranie. ✓ zatwierdza, ↩ wraca. Dolny pasek run jest wyłączony.</p>
          ${shortcutIndex}
          ${keyboardOptions.length < options.length ? '<p class="muted">Warianty bez przypisanej runy są dostępne w wyborze awaryjnym poniżej.</p>' : ''}
          ${combatScreenFallbackHtml(fallbackRows)}
        </section>
      </div>`;
  }
  return `
    <div class="combat-turn-command-layout">
      <div class="combat-turn-command-list">
        <div class="combat-context-heading"><span>Podgląd działania <span class="combat-panel-icon">${selected.panel_icon || ''}</span></span></div>
        <div id="combat-turn-action-availability">${combatTurnActionUnavailableHtml(menu, combat)}</div>
        <div class="combat-keyboard-preview economy-${esc(selected.action_economy || 'action')}">${selected.action_economy_label ? `<small class="combat-preview-economy">${esc(selected.action_economy_label)}</small>` : ''}<b>${manaTextHtml(combatActionTileLabel(selected) || '')}</b>${actionManaCostHtml(selected)}<p>${manaTextHtml(selected.description || '')}</p></div>
        <div class="numpad-combat-hint"><span><kbd>plansza</kbd> wskaż cel / pole</span><span>✓ wykonaj</span><span>↩ wróć bez kosztu</span></div>
        ${combatScreenFallbackHtml(`<div class="row combat-fallback-actions">
          <button type="button" data-allow-busy="true" onclick="confirmCombatTurnAction()">✓ Potwierdź</button>
          <button type="button" class="secondary" data-allow-busy="true" onclick="cancelCombatTurnActionPreview()">↩ Wróć</button>
        </div>`)}
      </div>
    </div>
  `;
}
function combatLootQuantityOptionHtml(option, index, selected) {
  const available = Math.max(0, Number(option.loot_quantity_max || 0));
  const unitWeight = Math.max(0, Number(option.loot_unit_weight_lb || 0));
  const remaining = Math.max(0, Number(option.recipient_remaining_capacity_lb || 0));
  const capacityMaximum = unitWeight > 0
    ? Math.max(0, Math.floor((remaining + 1e-9) / unitWeight))
    : available;
  const maximum = Math.min(available, capacityMaximum);
  if (maximum < 1) {
    return `
      <div class="combat-context-option${selected ? ' selected' : ''}" aria-current="${selected ? 'true' : 'false'}">
        <b>${manaTextHtml(option.label)}</b>
        <span>${manaTextHtml(option.description || '')}</span>
        <span class="combat-warning">Brak wolnego udźwigu na choćby jedną sztukę.</span>
      </div>
    `;
  }
  const selectedWeight = maximum * unitWeight;
  return `
    <div class="combat-context-option${selected ? ' selected' : ''}" aria-current="${selected ? 'true' : 'false'}">
      <b>${manaTextHtml(option.label)}</b>
      <span>${manaTextHtml(option.description || '')}</span>
      <div class="row">
        <label>Ilość:
          <input id="combat-loot-quantity-${index}" type="number" min="1" max="${esc(maximum)}" value="${esc(maximum)}" oninput="updateCombatLootQuantity(${index})">
        </label>
        <button data-allow-busy="true" onclick="confirmCombatContextMenu('${esc(option.id)}', ${index})">Zabierz wybraną ilość</button>
      </div>
      <span id="combat-loot-summary-${index}" class="muted">Wybrana masa: ${esc(selectedWeight.toFixed(3))} lb · udźwig po zabraniu: ${esc(Math.max(0, remaining - selectedWeight).toFixed(3))} lb.</span>
    </div>
  `;
}
function updateCombatLootQuantity(index) {
  const menu = ((state.combat || {}).context_menu) || {};
  const option = (menu.options || [])[index] || {};
  const input = document.getElementById(`combat-loot-quantity-${index}`);
  const summary = document.getElementById(`combat-loot-summary-${index}`);
  if (!input || !summary) return;
  const quantity = Math.max(0, Number(input.value || 0));
  const unitWeight = Math.max(0, Number(option.loot_unit_weight_lb || 0));
  const remaining = Math.max(0, Number(option.recipient_remaining_capacity_lb || 0));
  const selectedWeight = quantity * unitWeight;
  summary.textContent = `Wybrana masa: ${selectedWeight.toFixed(3)} lb · udźwig po zabraniu: ${Math.max(0, remaining - selectedWeight).toFixed(3)} lb.`;
}
function combatContextMenuDetailsHtml(menu) {
  const selected = (menu.options || [])[Number(menu.selected_index || 0)] || null;
  if (!selected) return '<p>Brak wybranej akcji.</p>';
  return `<p><b>${manaTextHtml(selected.label)}</b></p><p>${manaTextHtml(selected.description || '')}</p><p><b>Kategoria:</b> ${esc(combatMenuCategoryLabel(selected.category))}</p>`;
}
function pendingCombatInteractionDetailsHtml(pending) {
  const options = pending.options || [];
  if (!options.length) return '<p>Brak szczegółów interakcji.</p>';
  return options.map(option => `
    <p><b>${manaTextHtml(option.label)}</b></p>
    <p>${manaTextHtml(option.description || '')}</p>
    <p><b>Warunki:</b> ${(option.conditions || []).map(condition => esc(condition)).join(', ') || 'brak'}</p>
  `).join('');
}
function pendingPlayerAttackDetailsHtml(pending) {
  const target = pending.target || {};
  const source = pending.source || {};
  const positioning = pending.positioning || {};
  const coverNames = {none: 'brak', half: 'połowa osłony', three_quarters: '3/4 osłony', total: 'pełna osłona'};
  if (pending.stage === 'confirm_attack') {
    if (source.save_ability) {
      const coverBonus = source.save_ability === 'dexterity' ? Number(positioning.cover_bonus || 0) : 0;
      return `
        <p><b>Potwierdzenie czaru</b></p>
        <p><b>Cel:</b> ${esc(target.name || '-')} | <b>Rzut obronny:</b> ${esc(abilityLabel(source.save_ability))} przeciw ST ${esc(pending.spell_save_dc || source.save_dc || '-')}</p>
        <p><b>Osłona:</b> ${esc(coverNames[positioning.cover_level] || positioning.cover_level || 'brak')}${coverBonus ? `, do rzutu +${esc(coverBonus)}` : ' — bez wpływu na ten rzut'}${(positioning.cover_sources || []).length ? ` (${(positioning.cover_sources || []).map(esc).join(', ')})` : ''}</p>
        <p><b>Przy sukcesie:</b> ${esc(saveSuccessLabel(source.save_damage_on_success))}</p>
      `;
    }
    const active = pending.active_modifiers || [];
    const ignored = pending.ignored_modifiers || [];
    const modifierLabel = signedNumber(pending.attack_modifier || 0);
    return `
      <p><b>${pending.two_weapon_bonus ? 'Potwierdzenie ataku drugą bronią' : 'Potwierdzenie ataku'}</b></p>
      <p><b>Cel:</b> ${esc(target.name || '-')} | <b>Efektywne AC:</b> ${esc(pending.target_ac || target.ac || '-')} | <b>Pole:</b> (${esc(target.position ? target.position[0] : '-')},${esc(target.position ? target.position[1] : '-')})</p>
      <p><b>Atak:</b> ${esc(source.name || '-')} | <b>${source.attack_kind === 'melee' ? 'Reach' : 'Zasięg'}:</b> ${esc(source.attack_kind === 'melee' ? (source.reach_feet || source.range_feet || 0) : (source.long_range_feet ? `${source.range_feet}/${source.long_range_feet}` : (source.range_feet || 0)))} ft | <b>Premia końcowa:</b> ${esc(modifierLabel)}</p>
      <p><b>Osłona:</b> ${esc(coverNames[positioning.cover_level] || positioning.cover_level || 'brak')}${Number(positioning.cover_bonus || 0) ? `, AC +${esc(positioning.cover_bonus)}` : ''}${(positioning.cover_sources || []).length ? ` (${(positioning.cover_sources || []).map(esc).join(', ')})` : ''}</p>
      <p><b>Atak dystansowy w zwarciu:</b> ${positioning.ranged_in_melee ? 'tak — utrudnienie' : 'nie'}</p>
      <p><b>Flankowanie:</b> ${positioning.flanking ? 'tak — przewaga' : 'nie'}</p>
      <p><b>Aktywne premie/kary:</b> ${active.length ? active.map(mod => mod.stacking_key === 'flanking_advantage' ? `${esc(mod.label)} — przewaga` : `${esc(mod.label)} ${esc(signedNumber(mod.value))}`).join(', ') : 'brak'}</p>
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
          ${esc(save.actor_name || save.actor_id)}: ${esc(abilityLabel(save.ability))} d20 ${esc(save.natural_roll)}, ${saveModifierComponentsHtml(save)}, razem ${esc(save.total)} / ST ${esc(save.dc)} - ${save.success ? 'sukces' : 'porażka'}${save.success ? `, ${esc(saveSuccessLabel(save.damage_multiplier === 0.5 ? 'half' : 'none'))}` : ', pełne obrażenia'}
        </span>
      `).join('')}
    </div>
  `;
}
function saveModifierComponentsHtml(save) {
  const components = save.modifier_components || [];
  if (!components.length) return `mod ${esc(signedNumber(save.modifier || 0))}`;
  return components
    .map(component => `${esc(component.label)} ${esc(signedNumber(component.value || 0))}`)
    .join(', ');
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
function skillLabel(skill) {
  const labels = {
    acrobatics: 'Akrobatyka',
    animal_handling: 'Opieka nad zwierzętami',
    arcana: 'Wiedza tajemna',
    athletics: 'Atletyka',
    deception: 'Oszustwo',
    history: 'Historia',
    insight: 'Intuicja',
    intimidation: 'Zastraszanie',
    investigation: 'Śledztwo',
    medicine: 'Medycyna',
    nature: 'Natura',
    perception: 'Spostrzegawczość',
    performance: 'Występy',
    persuasion: 'Perswazja',
    religion: 'Religia',
    sleight_of_hand: 'Zwinne dłonie',
    stealth: 'Skradanie się',
    survival: 'Sztuka przetrwania'
  };
  return labels[skill] || skill || '';
}
function rollModeLabel(mode) {
  return {
    advantage: 'przewaga — rzuć 2k20 i wybierz wyższy wynik',
    disadvantage: 'utrudnienie — rzuć 2k20 i wybierz niższy wynik'
  }[mode] || mode || 'zwykły';
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
function damageComponentInputsHtml(pending, prefix, source) {
  const components = (pending && pending.damage_components) || [];
  if (!components.length) {
    return `<label>Obrażenia: <input id="${esc(prefix)}-legacy" type="number" min="0" value="${esc(defaultDamageValue(source))}" data-roll-label="Obrażenia" data-roll-source="${esc((source && source.name) || 'Źródło obrażeń')}"></label>`;
  }
  return components.map((component, index) => {
    const fixed = component.fixed;
    const modifier = Number(component.modifier || 0);
    const value = fixed !== null && fixed !== undefined
      ? Math.max(0, Number(fixed) + modifier)
      : Math.max(0, modifier);
    const label = component.label || component.damage_type_label || component.damage_type || `Składnik ${index + 1}`;
    const dice = component.dice || '';
    const fixedAttribute = fixed !== null && fixed !== undefined ? ` data-roll-fixed="${esc(fixed)}"` : '';
    return `<label>${esc(label)} (${esc(component.formula || '')}): <input id="${esc(prefix)}-${index}" type="number" min="0" value="${esc(value)}" data-roll-label="${esc(label)}" data-roll-dice="${esc(dice)}" data-roll-modifier="${esc(modifier)}" data-roll-source="${esc((source && source.name) || label)}"${fixedAttribute}></label>`;
  }).join('');
}
function damageComponentPayload(pending, prefix) {
  const components = (pending && pending.damage_components) || [];
  if (!components.length) {
    const legacy = document.getElementById(`${prefix}-legacy`);
    return {damage: Number(legacy ? legacy.value : 0)};
  }
  const totals = {};
  components.forEach((component, index) => {
    const input = document.getElementById(`${prefix}-${index}`);
    totals[component.id] = Number(input ? input.value : 0);
  });
  return {components: totals};
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
  const hasPendingResolution = Boolean(state.pending);
  const hasPendingDecision = state.pending && state.pending.stage === 'decision';
  const hasNpcTransition = Boolean(state.pending_npc_transition);
  const hasRolls = state.required_rolls && state.required_rolls.length > 0;
  const hasResult = Boolean(resultAck) && !state.combat;
  const hasEncounter = Boolean(state.pending_encounter);
  const interactionStage = stage === 'location_active' || stage === 'interaction_result';
  const chatMode = interactionStage && !hasEncounter && !state.combat;
  document.body.classList.toggle('chat-instance-mode', chatMode);
  document.body.classList.toggle(
    'interaction-grid-mode',
    chatMode && Boolean(document.querySelector('#interaction-goals .interaction-goal-grid'))
  );
  const flowPanel = document.getElementById('flow-panel');
  flowPanel.hidden = chatMode || hasEncounter || !flowPanel.innerHTML.trim();
  document.getElementById('result-panel').hidden = !hasResult;
  document.getElementById('encounter-panel').hidden = !hasEncounter || hasResult || Boolean(state.training_arena?.tutorial?.notice);
  document.getElementById('travel-panel').hidden = true;
  document.getElementById('points-panel').hidden = true;
  document.getElementById('pending-panel').hidden = !hasPendingDecision;
  document.getElementById('roll-panel').hidden = !hasRolls;
  const interactionCard = document.getElementById('interaction-state-card');
  interactionCard.hidden = !hasPendingDecision && !hasRolls && !hasResult;
  updateInteractionStateCard(hasPendingDecision, hasRolls, hasResult);
  document.getElementById('action-panel').hidden = !chatMode;
  document.getElementById('scene-description-card').hidden = interactionStage || !document.getElementById('scene-description').innerHTML.trim();
  const canAskGm = stage === 'location_active'
    && !hasPendingResolution
    && !hasNpcTransition
    && !hasRolls
    && !hasResult
    && !state.trade;
  const gmChatUtility = document.getElementById('chat-utility-actions');
  if (gmChatUtility) gmChatUtility.hidden = !canAskGm;
  const gmChatDialog = document.getElementById('gm-chat-dialog');
  if (!canAskGm && gmChatDialog && gmChatDialog.open) gmChatDialog.close();
  const leaveButton = document.getElementById('leave-interaction-button');
  const leaveButtonLabel = stage === 'interaction_result'
    ? 'Zakończ interakcję'
    : state.active_point
      ? (state.active_point.npc?.briefing_contract ? 'Wróć do Gildii' : 'Zakończ rozmowę')
      : ((boardInteractionState() || {}).mode === 'navigation'
        ? 'Wróć do działań'
        : 'Menu lokacji');
  leaveButton.innerHTML = `<kbd aria-hidden="true">0</kbd> ${esc(leaveButtonLabel)}`;
  leaveButton.disabled = hasPendingDecision || hasNpcTransition || hasRolls || busy;
}
function updateInteractionStateCard(hasPendingDecision, hasRolls, hasResult) {
  const activeStep = hasResult ? 'result' : hasRolls ? 'roll' : hasPendingDecision ? 'decision' : '';
  const title = hasResult
    ? (resultAck.title || 'Wynik')
    : hasRolls
      ? (state.pending && state.pending.stage === 'hazard_save' ? 'Rzut obronny' : 'Wykonaj fizyczny rzut')
      : pendingTitle(state.pending);
  const titleElement = document.getElementById('interaction-state-title');
  if (titleElement) titleElement.textContent = title;
  document.querySelectorAll('[data-interaction-step]').forEach(step => {
    const order = {decision: 1, roll: 2, result: 3};
    const stepName = step.dataset.interactionStep;
    step.classList.toggle('active', stepName === activeStep);
    step.classList.toggle('complete', activeStep && order[stepName] < order[activeStep]);
  });
  const card = document.getElementById('interaction-state-card');
  if (card) card.dataset.stage = activeStep;
}
async function openChatInstance() {
  chatInstanceOpen = true;
  await api('/api/exploration/board-selection', {enabled: false}, 'Otwieram interakcję...');
}
async function setBoardSelectionMode(enabled) {
  chatInstanceOpen = true;
  resetInteractionSelection();
  return api(
    '/api/exploration/board-selection',
    {enabled: Boolean(enabled)},
    enabled ? 'Pokazuję dostępne drogi...' : 'Wracam do działań w lokacji...'
  );
}
async function leaveChatInstance() {
  const stage = state.flow ? state.flow.stage : 'location_active';
  if (stage === 'interaction_result') {
    finishInteraction();
    return;
  }
  if ((state.pending && state.pending.stage) || (state.required_rolls || []).length) return;
  if (state.active_point) {
    await api('/api/point/leave', {}, 'Wracam do działań w lokacji...');
    return;
  }
  const navigationActive = (boardInteractionState() || {}).mode === 'navigation';
  await setBoardSelectionMode(!navigationActive);
}
function closeCurrentExplorationInstance() {
  const flow = state.flow || {};
  const unresolved = Boolean(
    (state.pending && state.pending.stage)
    || state.pending_npc_transition
    || (state.required_rolls || []).length
  );
  if (unresolved || state.combat) return false;
  if (flow.stage === 'interaction_result') {
    finishInteraction();
    return true;
  }
  if (flow.stage === 'location_active') {
    leaveChatInstance();
    return true;
  }
  return false;
}
async function sendAction() {
  const input = document.getElementById('action');
  const text = input ? input.value.trim() : '';
  if (!text) return;
  closeGmChatDialog();
  optimisticPlayerMessage = {role: 'player', title: 'Gracze', body: text};
  if (input) input.value = '';
  closeSlashCommandMenu();
  render();
  const result = await api(
    '/api/action',
    {text, conversation_only: true},
    'MG poprawia płaszcz i zastanawia się nad odpowiedzią...'
  );
  if (result && !result.ok && input) input.value = text;
}
function openGmChatDialog() {
  const utility = document.getElementById('chat-utility-actions');
  const dialog = document.getElementById('gm-chat-dialog');
  if (!dialog || (utility && utility.hidden)) return;
  if (!dialog.open) dialog.showModal();
  window.requestAnimationFrame(() => document.getElementById('action')?.focus());
}
function closeGmChatDialog() {
  closeSlashCommandMenu();
  const dialog = document.getElementById('gm-chat-dialog');
  if (dialog && dialog.open) dialog.close();
  window.setTimeout(scheduleAutomaticBoardScan, 0);
}
function submitGmChat(event) {
  event.preventDefault();
  sendAction();
}
async function sendGoalAction() {
  if (state.pending) {
    alert('Najpierw rozstrzygnij widoczną decyzję, pułapkę albo rzut.');
    return;
  }
  const input = document.getElementById('goal-action');
  const selectedGoal = currentInteractionGoals().find(goal => goal.id === selectedInteractionGoalId) || null;
  if (!selectedGoal) return;
  const enteredText = input ? input.value.trim() : interactionDescriptionDraft.trim();
  if (!enteredText && selectedGoal.description_mode === 'required') {
    alert('Najpierw opiszcie sposób działania.');
    return;
  }
  const text = enteredText || selectedGoal.default_declaration || selectedGoal.label;
  const selectedCheckParticipants = selectedGoal ? selectedGoalCheckParticipants(selectedGoal) : null;
  if (selectedGoal && !selectedCheckParticipants) {
    alert('Najpierw wybierz typ testu.');
    return;
  }
  if (
    selectedGoal
    && !['no_actor', 'whole_party'].includes(selectedCheckParticipants)
    && selectedInteractionActorIds.length < 1
  ) {
    alert('Najpierw wybierz postać, która wykonuje test.');
    return;
  }
  if (selectedGoal.source_required && !selectedInteractionActionSourceId) {
    alert('Najpierw wybierz czar, przedmiot albo narzędzie.');
    return;
  }
  optimisticPlayerMessage = selectedGoal.description_mode === 'none'
    ? null
    : {role: 'player', title: 'Gracze', body: text};
  if (input) input.value = '';
  interactionDescriptionDraft = '';
  if (optimisticPlayerMessage) render();
  const result = await api(
    '/api/action',
    {
      text,
      selected_goal_id: selectedInteractionGoalId,
      check_participants: selectedCheckParticipants,
      participant_actor_ids: selectedGoal
        && ['no_actor', 'whole_party'].includes(selectedCheckParticipants)
        ? []
        : selectedInteractionActorIds,
      selected_social_skill: (selectedGoal.social_skill_options || []).length
        ? selectedSocialSkill
        : null,
      selected_action_source_id: selectedInteractionActionSourceId,
    },
    selectedGoal.resolution_mode === 'llm_rubric'
      ? 'Czekam na odpowiedź MG...'
      : 'Rozstrzygam działanie...'
  );
  if (result && !result.ok && input) input.value = text;
}
function startShortRest() { api('/api/rest/short/start', {}, 'Przygotowuję podgląd odpoczynku...'); }
function completeLongRest() {
  if (!window.confirm('Długi odpoczynek przesunie czas o 8 godzin i odnowi zasoby drużyny. Kontynuować?')) return;
  api('/api/rest/long/complete', {}, 'Mija osiem godzin odpoczynku...');
}
function confirmShortRest() {
  const attunementChoices = [...document.querySelectorAll('[data-short-rest-attunement]')]
    .filter(select => select.value)
    .map(select => {
      const separator = select.value.indexOf(':');
      return {
        actor_id: select.dataset.shortRestAttunement,
        action: select.value.slice(0, separator),
        item_id: select.value.slice(separator + 1),
      };
    });
  api('/api/rest/short/confirm', {attunement_choices: attunementChoices}, 'Mija godzina odpoczynku...');
}
function cancelShortRest() { api('/api/rest/short/cancel', {}, 'Anuluję odpoczynek...'); }
function finishShortRest() { api('/api/rest/short/finish', {}, 'Wracam do eksploracji...'); }
function spendShortRestHitDie(actorId, dieSides) {
  const input = document.getElementById(`short-rest-${actorId}-d${dieSides}`);
  const song = document.getElementById(`short-rest-song-${actorId}`);
  const payload = {actor_id: actorId, die_sides: dieSides, natural_roll: Number(input ? input.value : 0)};
  if (song && song.value !== '') payload.song_of_rest_roll = Number(song.value);
  api('/api/rest/short/hit-die', payload, 'Rozliczam Hit Die...');
}
function recoverShortRestSpellSlots(actorId, slotLevels) {
  api('/api/rest/short/spell-recovery', {actor_id: actorId, slot_levels: slotLevels}, 'Odzyskuję sloty...');
}
function dismantleCraftedItem(itemId) {
  api('/api/crafting/dismantle', {item_id:itemId}, 'Rozmontowuję konstrukcję...');
}
function signedNumber(value) {
  const number = Number(value || 0);
  return number >= 0 ? `+${number}` : String(number);
}
function confirmSpellPreparation() {
  const preparation = state.spell_preparation || {};
  const actor = (preparation.actors || []).find(entry => String(entry.actor_id) === String(preparation.current_actor_id));
  if (!actor) return false;
  synchronizeSpellPreparationDraft(actor);
  const spell_ids = [...((spellPreparationDraft && spellPreparationDraft.spellIds) || [])];
  if (spell_ids.length !== Number(actor.preparation_limit || 0)) {
    setPhysicalCardStatus(`Zeskanuj dokładnie ${actor.preparation_limit} różnych kart czarów.`, {error: true});
    return false;
  }
  api('/api/spell-preparation/confirm', {actor_id: preparation.current_actor_id, spell_ids}, 'Zapisuję przygotowane czary...');
  return true;
}
function decision(value) {
  const labels = {
    accept: 'Przyjmuję decyzję MG...',
    reject: 'Odrzucam decyzję MG...',
    explain: 'Proszę MG o wyjaśnienie...'
  };
  const leadActor = document.getElementById('lead-actor');
  const selectedSource = document.querySelector('input[name="source-selection-choice"]:checked');
  const collectionQuantity = document.getElementById('collection-quantity');
  api('/api/decision', {
    decision:value,
    lead_actor_id: leadActor ? leadActor.value : null,
    source_id: selectedSource ? selectedSource.value : null,
    quantity: collectionQuantity ? Number(collectionQuantity.value) : null
  }, labels[value] || 'Czekam na MG...');
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
    check_participants: document.getElementById('correction-participants')?.value || state.pending.option?.check_participants || 'single_actor',
    check_aggregation: document.getElementById('correction-aggregation').value,
    lead_actor_id: document.getElementById('correction-lead')?.value || (state.pending.participant_actor_ids || [])[0] || '',
    helper_actor_id: document.getElementById('correction-helper')?.value || (state.pending.participant_actor_ids || [])[1] || '',
    ability: document.getElementById('correction-ability').value,
    skill: document.getElementById('correction-skill').value,
    dc: Number(document.getElementById('correction-dc').value),
    roll_mode: document.getElementById('correction-roll-mode').value,
    resource_id: document.getElementById('correction-resource').value,
    situational_modifiers,
    improvised_tool
  }, 'Zapisuję korektę decyzji MG...');
}
function sendRolls() {
  const rolls = {};
  document.querySelectorAll('#rolls input').forEach(input => {
    const actorId = input.dataset.actor;
    if (input.dataset.rollKind === 'bardic-inspiration') {
      if (input.value !== '') {
        if (!rolls[actorId] || typeof rolls[actorId] !== 'object') {
          rolls[actorId] = {natural_roll: Number(rolls[actorId] || 0)};
        }
        rolls[actorId].bardic_inspiration_roll = Number(input.value);
      }
      return;
    }
    if (input.dataset.rollKind === 'guidance') {
      if (input.value !== '') {
        if (!rolls[actorId] || typeof rolls[actorId] !== 'object') {
          rolls[actorId] = {natural_roll: Number(rolls[actorId] || 0)};
        }
        rolls[actorId].guidance_roll = Number(input.value);
      }
      return;
    }
    if (input.dataset.rollKind === 'improvisation') {
      if (input.value !== '') {
        if (!rolls[actorId] || typeof rolls[actorId] !== 'object') {
          rolls[actorId] = {natural_roll: Number(rolls[actorId] || 0)};
        }
        rolls[actorId].improvisation_roll = Number(input.value);
      }
      return;
    }
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
function startScenarioHandoff() {
  api('/api/scenario/handoff/start', {}, 'Przenoszę drużynę i przygotowuję kolejną mapę...');
}
function openContinuationPanel() {
  continuationPanelOpen = true;
  pauseBoardForScreenInput();
  chatInstanceOpen = true;
  setSidePanelOpen(false);
  render();
  window.requestAnimationFrame(() => document.querySelector('.continuation-composer')?.scrollIntoView({behavior: 'smooth', block: 'start'}));
}
function closeContinuationPanel() {
  continuationPanelOpen = false;
  api('/api/board/clear-selection', {}, 'Wracam do wyboru działania...');
}
function selectContinuationPace(pace) {
  if (!['fast', 'normal', 'slow'].includes(pace)) return false;
  selectedContinuationPace = pace;
  continuationStep = continuationRequiresNavigator() ? 'navigator' : 'roll';
  pauseBoardForScreenInput();
  render();
  return true;
}
function continuationRequiresNavigator() {
  const continuation = state.flow && state.flow.continuation;
  const travel = (continuation && continuation.travel) || {};
  return !travel.navigation_automatic
    && travel.navigation_dc !== null
    && travel.navigation_dc !== undefined;
}
function advanceContinuationStep() {
  if (!continuationPanelOpen || !((state.flow || {}).continuation || {}).available) return false;
  submitContinuation();
  return true;
}
function retreatContinuationStep() {
  if (!continuationPanelOpen) return false;
  closeContinuationPanel();
  return true;
}
function selectContinuationNavigator(actorId) {
  if (!continuationPanelOpen || continuationStep !== 'navigator') return false;
  const actor = (state.actors || []).find(
    candidate => String(candidate.id) === String(actorId)
      && candidate.faction === 'ally'
      && !candidate.defeated
  );
  if (!actor) return false;
  selectedContinuationNavigatorId = String(actor.id);
  continuationStep = 'roll';
  render();
  window.requestAnimationFrame(() => document.getElementById('continuation-navigation-roll-1')?.focus());
  return true;
}
function requiredD20Value(id) {
  const input = document.getElementById(id);
  const value = Number(input && input.value);
  if (!Number.isInteger(value) || value < 1 || value > 20) {
    throw new Error('Każdy naturalny wynik d20 musi być liczbą od 1 do 20.');
  }
  return value;
}
function submitContinuation() {
  const continuation = state.flow && state.flow.continuation;
  if (!continuation || !continuation.available) return;
  continuationPanelOpen = false;
  api('/api/scenario/continue', {}, 'Przygotowuję kolejną lokację...');
}
function finishScenario() {
  const continuation = state.flow && state.flow.continuation;
  if (continuation) {
    if (!continuation.available) return;
    openContinuationPanel();
    return;
  }
  if (!window.confirm('Zakończyć scenariusz i wygasić efekty trwające do jego końca?')) return;
  api('/api/scenario/finish', {}, 'Kończę scenariusz...');
}
function travel(zoneId) { api('/api/travel', {zone_id: zoneId}, 'Przechodzę do wybranej lokacji...'); }
function selectPoint(pointId) {
  selectedPointPreviewId = null;
  api('/api/point', {point_id: pointId}, pointId ? 'Otwieram punkt eksploracji...' : 'Wracam do lokacji...');
}
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
    scan_timeout_s: Number(document.getElementById('scan-timeout').value || 300)
  }, 'Łączę z planszą...');
}
function startSession() { api('/api/start', {}, 'Rozpoczynam sesję...'); }
function currentBoardSelection() {
  return (state && state.board_selection) || null;
}
function boardSelectionPausedForScreenInput() {
  if (state?.training_arena?.tutorial?.notice) return false;
  if (state?.board_selection?.mode === 'mana_targets') return false;
  if (state?.board_selection?.panel_enabled && keyboardRollWizard) return false;
  if (resultAck || (keyboardRollWizard && !keyboardRollWizard.initiative)) return true;
  const boardInteraction = state && state.flow
    ? state.flow.board_interaction
    : null;
  const boardHotspotPreview = Boolean(
    boardInteraction
    && ['point', 'zone_option'].includes(boardInteraction.selected_action_kind)
    && boardInteraction.selected_action_id
    && !boardInteraction.selected_action_confirmed
  );
  const actorBoardSelection = Boolean(
    state
    && state.flow
    && state.flow.board_interaction
    && state.flow.board_interaction.actor_selection
    && state.flow.board_interaction.actor_selection.active
  );
  if (
    (selectedInteractionGoalId && !actorBoardSelection)
    || (selectedZoneOptionId && !boardHotspotPreview)
    || downtimePanelOpen
    || (continuationPanelOpen && continuationStep !== 'pace')
    || (state && state.trade)
  ) return true;
  const focused = document.activeElement;
  return Boolean(
    focused
    && focused.closest
    && focused.closest('#action-panel')
    && focused.matches('input, textarea, select')
  );
}
function pauseBoardForScreenInput() {
  clearTimeout(boardAutoArmTimer);
  boardAutoArmTimer = null;
  if (boardScanInFlight) {
    stopBoardScanLoop();
    return;
  }
  boardInputPhase = 'idle';
  boardListeningRevision = '';
  updateBoardInputPresentation();
}
function boardSelectionStatusHtml(compact = false) {
  const selection = currentBoardSelection();
  if (boardSelectionPausedForScreenInput()) return '';
  if (!selection || !Number(selection.legal_position_count || 0)) return '';
  const connected = Boolean(selection.connected);
  const revision = String(selection.revision || '');
  const activeRevision = boardListeningRevision === revision;
  const phase = activeRevision ? boardInputPhase : (
    revision === lastAttemptedBoardRevision && boardScanError ? 'error' : 'ready'
  );
  const labels = {
    arming: ['Przygotowuję planszę…', 'Za chwilę zacznie nasłuchiwać.'],
    listening: ['Plansza nasłuchuje', selection.prompt || 'Przestaw figurkę na podświetlone pole.'],
    resolved: ['Wybór odczytany', 'Przechodzę do kolejnego kroku.'],
    error: ['Nie odczytano wyboru', boardScanError || 'Spróbuj jeszcze raz albo użyj wyboru awaryjnego.'],
    ready: connected
      ? ['Plansza gotowa', selection.prompt || 'Przestaw figurkę na podświetlone pole.']
      : ['Plansza nie jest połączona', 'Możesz użyć awaryjnego wyboru pola w panelu gry.'],
  };
  const [title, copy] = labels[phase] || labels.ready;
  const retry = phase === 'error' || !connected;
  return `<div class="board-listening-card ${esc(phase)}${compact ? ' compact' : ''}" aria-live="polite">
    <span class="board-listening-pulse" aria-hidden="true"></span>
    <span class="board-listening-copy"><b>${esc(title)}</b>${compact ? '' : `<small>${esc(copy)}</small>`}</span>
    ${retry ? `<button type="button" class="secondary" onclick="scanBoard()">${connected ? 'Spróbuj ponownie' : 'Wybór awaryjny'}</button>` : ''}
  </div>`;
}
function updateBoardInputPresentation() {
  const selection = currentBoardSelection();
  const hasBoardContract = Boolean(
    selection
    && Number(selection.legal_position_count || 0)
    && !boardSelectionPausedForScreenInput()
  );
  document.body.classList.toggle('board-auto-selection', hasBoardContract);
  document.querySelectorAll('[data-board-input-status]').forEach(container => {
    const compact = Boolean(container.closest('.board-choice-toolbar'));
    container.innerHTML = boardSelectionStatusHtml(compact);
  });
  const globalStatus = document.getElementById('board-input-global');
  if (globalStatus) {
    globalStatus.hidden = Boolean(
      document.body.classList.contains('chat-instance-mode')
      || (document.getElementById('encounter-panel') && !document.getElementById('encounter-panel').hidden)
    );
  }
  document.querySelectorAll('button[data-primary-scan="true"]').forEach(button => {
    button.hidden = hasBoardContract;
  });
}
function boardSelectionCanAutoArm(selection = currentBoardSelection()) {
  if (!selection || !selection.auto_arm || !selection.connected) return false;
  if (!Number(selection.legal_position_count || 0)) return false;
  if (combatTurnActionMoveInFlight || combatTurnActionMoveTimer || combatTurnActionMoveDelta) return false;
  if (boardSelectionPausedForScreenInput()) return false;
  if (document.hidden || busy || waitingForGm) return false;
  const openDialog = document.querySelector('dialog[open]');
  return !openDialog;
}
function scheduleAutomaticBoardScan() {
  clearTimeout(boardAutoArmTimer);
  boardAutoArmTimer = null;
  if (syncBrowserBoardPanel()) return;
  const selection = currentBoardSelection();
  if (!boardSelectionCanAutoArm(selection)) {
    if (
      boardScanInFlight
      && selection
      && boardListeningRevision
      && boardListeningRevision !== String(selection.revision || '')
    ) {
      stopBoardScanLoop();
    }
    updateBoardInputPresentation();
    return;
  }
  const revision = String(selection.revision || '');
  if (!revision || revision === lastAttemptedBoardRevision) {
    updateBoardInputPresentation();
    return;
  }
  if (boardScanInFlight) {
    if (boardListeningRevision !== revision) stopBoardScanLoop();
    return;
  }
  boardInputPhase = 'arming';
  boardListeningRevision = revision;
  updateBoardInputPresentation();
  boardAutoArmTimer = setTimeout(() => {
    boardAutoArmTimer = null;
    const current = currentBoardSelection();
    if (boardPanelSyncPromise || boardScanStopPromise || boardScanInFlight
        || !boardSelectionCanAutoArm(current)
        || String(current?.revision || '') !== revision) return;
    scanBoardOnce({revision, automatic: true});
  }, selection.input_mode === 'stream' ? 0 : 120);
}
async function scanBoard() {
  if (!Boolean((state.board || {}).connected)) {
    if (!boardFallbackEnabled) toggleBoardFallback(true);
    else {
      setSidePanelTab('game');
      setSidePanelOpen(true);
      window.requestAnimationFrame(() => document.getElementById('fallback-board-col')?.focus());
    }
    return;
  }
  if (await stopBoardScanLoop({force: true}) === false) return;
  const selection = currentBoardSelection();
  const revision = String((selection || {}).revision || '');
  lastAttemptedBoardRevision = '';
  boardScanError = '';
  await scanBoardOnce({revision, automatic: false});
}
function scanBoardOnce({revision = '', automatic = false} = {}) {
  if (boardScanInFlight) return boardScanPromise || Promise.resolve();
  const token = ++boardScanToken;
  const previousInteractionId = state && state.conversation ? state.conversation.interaction_id : null;
  boardScanInFlight = true;
  boardInputPhase = 'listening';
  boardListeningRevision = revision;
  boardScanError = '';
  lastAttemptedBoardRevision = revision;
  updateBoardInputPresentation();
  boardScanPromise = performBoardScan({revision, automatic, token, previousInteractionId});
  return boardScanPromise;
}
async function performBoardScan({revision, automatic, token, previousInteractionId}) {
  let panelEventPending = false;
  try {
    const res = await fetch('/api/board/scan', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({revision, automatic})
    });
    const data = await res.json();
    if (token !== boardScanToken) return;
    // The transport has finished. Rendering may change panel controls, but
    // must not send a serial reset for a scan whose response is already here.
    boardScanInFlight = false;
    boardScanPromise = null;
    if (res.ok && data.navigate === '/') {
      ++boardScanToken;
      window.location.assign('/');
      return;
    }
    if (res.ok && data.redirect) { window.location.assign(data.redirect); return {ok:true}; }
    if (res.ok && data.panel_event) {
      boardInputPhase = 'resolved';
      panelEventPending = true;
      window.setTimeout(() => {
        if (token !== boardScanToken) return;
        handleBoardPanelEvent(data);
        scheduleAutomaticBoardScan();
      }, 0);
      return;
    }
    if (!res.ok) {
      boardInputPhase = 'error';
      boardScanError = data.error || 'Nie udało się odczytać planszy.';
      if (!automatic) alert(boardScanError);
    }
    state = data.state || data;
    const returnedRevision = String(((state || {}).board_selection || {}).revision || '');
    // This scan has already returned. Rendering the next input must not cancel
    // it and leave a stale STOP queued for the next button press.
    if (res.ok) boardListeningRevision = returnedRevision;
    const nextInteractionId = state && state.conversation ? state.conversation.interaction_id : null;
    if (nextInteractionId !== previousInteractionId) resetInteractionSelection();
    activeInteractionId = nextInteractionId;
    optimisticPlayerMessage = null;
    resultAck = null;
    chatInstanceOpen = true;
    const boardSelectionActivated = synchronizeBoardSelection({force: true});
    if (res.ok && revision && returnedRevision === revision) {
      boardInputPhase = 'error';
      boardScanError = 'Nie wykryto zmiany na żadnym z podświetlonych pól.';
    } else if (res.ok) {
      boardInputPhase = 'resolved';
    }
    render();
    if (boardSelectionActivated) scrollChatToBottom(true);
    refreshSessionLog();
  } catch (error) {
    if (token !== boardScanToken) return;
    boardInputPhase = 'error';
    boardScanError = 'Połączenie z planszą zostało przerwane.';
    updateBoardInputPresentation();
    if (!automatic) alert(boardScanError);
  } finally {
    if (token === boardScanToken) {
      boardScanInFlight = false;
      boardScanPromise = null;
      if (boardInputPhase !== 'error') boardInputPhase = 'idle';
      boardListeningRevision = '';
      updateBoardInputPresentation();
      if (!panelEventPending) {
        initializeKeyboardRollWizard();
        focusCombatDecision();
        scheduleAutomaticBoardScan();
      }
    }
  }
}
function stopBoardScanLoop({force = false} = {}) {
  if (boardScanStopPromise) return boardScanStopPromise;
  const stopPromise = stopBoardScanLoopOnce(force);
  boardScanStopPromise = stopPromise;
  stopPromise.finally(() => {
    if (boardScanStopPromise === stopPromise) boardScanStopPromise = null;
  });
  return stopPromise;
}
async function stopBoardScanLoopOnce(force = false) {
  clearTimeout(boardAutoArmTimer);
  boardAutoArmTimer = null;
  const stoppedToken = ++boardScanToken;
  boardListeningRevision = '';
  const pendingScan = boardScanPromise;
  if (force || pendingScan || currentBoardSelection()?.input_mode === 'stream') {
    try {
      const response = await fetch('/api/board/reset-scan', {method:'POST',
        headers:{'Content-Type':'application/json'}, body: JSON.stringify({}),
        signal: AbortSignal.timeout(8000)});
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Nie udało się zakończyć poprzedniego skanu.');
      }
    } catch (error) {
      // Do not wait forever on an orphan or arm over its server lock.
      boardScanError = error.message || 'Nie udało się ponowić oczekiwania planszy.';
      boardInputPhase = 'error';
      lastAttemptedBoardRevision = String(currentBoardSelection()?.revision || '');
      updateBoardInputPresentation();
      return false;
    }
    try {
      await pendingScan;
    } catch (_error) {
      // scanBoardOnce already owns presentation of transport errors.
    }
  }
  // The old receiver deliberately ignores responses after token changes.
  // Cancellation therefore owns cleanup, while preserving any newer scan.
  if (boardScanToken !== stoppedToken) return;
  boardScanInFlight = false;
  boardScanPromise = null;
  // A cancelled attempt must never suppress re-arming the same logical
  // contract. This is the single reset point used by action changes, cancel
  // buttons and area-preview repositioning.
  lastAttemptedBoardRevision = '';
  boardScanError = '';
  boardInputPhase = 'idle';
  updateBoardInputPresentation();
  window.setTimeout(scheduleAutomaticBoardScan, 0);
}
function selectBoardPosition(col, row) { api('/api/board/select', {col, row}, 'Wybieram pole planszy...'); }
async function resetBoardScan() {
  if (await stopBoardScanLoop({force: true}) === false) return;
  scheduleAutomaticBoardScan();
}
function startEncounterSetup() { api('/api/encounter/setup/start', {}, 'Przygotowuję kroki setupu encountera...'); }
function resolveEncounterOpening() { api('/api/encounter/opening/resolve', {}, 'Rozstrzygam rozpoczęcie starcia...'); }
function confirmEncounterSetup() { api('/api/encounter/setup/confirm', {}, 'Potwierdzam krok setupu...'); }
function startEncounterInitiative() { api('/api/encounter/initiative/start', {}, 'Rozpoczynam inicjatywę...'); }
function startPrecombatStealthRoll(actorId) {
  if (busy || keyboardRollWizard) return;
  const root = document.getElementById(`precombat-roll-${actorId}`);
  if (!root) return;
  root.hidden = false;
  initializeKeyboardRollWizard();
}
function submitPrecombatStealth(actorId) {
  api('/api/encounter/stealth/roll', {
    actor_id: actorId,
    ...d20RollPayload(`precombat-stealth-${actorId}`),
  }, 'Rozstrzygam skradanie przed walką...');
}
function finishPrecombatStealth() { api('/api/encounter/stealth/finish', {}, 'Kończę etap skradania...'); }
function submitEncounterInitiativeRoll() {
  const input = document.getElementById('encounter-initiative-roll');
  const input2 = document.getElementById('encounter-initiative-roll-2');
  const payload = {natural_roll: Number(input ? input.value : 0)};
  if (input2) payload.natural_roll_2 = Number(input2.value || 0);
  api('/api/encounter/initiative/roll', payload, 'Zapisuję rzut inicjatywy...');
}
function submitPlayerAttackRoll() {
  const payload = d20RollPayload('combat-attack-natural-roll');
  const inspiration = document.getElementById('combat-bardic-inspiration-roll');
  if (inspiration && inspiration.value !== '') payload.bardic_inspiration_roll = Number(inspiration.value);
  const bless = document.getElementById('combat-bless-roll');
  if (bless && bless.value !== '') payload.bless_roll = Number(bless.value);
  const mirrorImage = document.getElementById('combat-mirror-image-roll');
  if (mirrorImage && mirrorImage.value !== '') payload.mirror_image_roll = Number(mirrorImage.value);
  api('/api/combat/player-attack-roll', payload, 'Rozstrzygam rzut ataku...');
}
function selectCombatAttackSource(sourceId, castLevel = null, metamagicIds = []) { api('/api/combat/attack-source', {source_id: sourceId, cast_level: castLevel, metamagic_ids: metamagicIds}, 'Wybieram źródło ataku...'); }
function selectCombatHealingSource(sourceId, castLevel = null, metamagicIds = []) { api('/api/combat/healing-source', {source_id: sourceId, cast_level: castLevel, metamagic_ids: metamagicIds}, 'Wybieram leczenie...'); }
function requestTextInput(title, defaultValue = '', options = {}) {
  return new Promise((resolve) => {
    const dialog = document.createElement('dialog');
    dialog.className = 'gm-chat-dialog';
    const form = document.createElement('form');
    form.method = 'dialog';
    const heading = document.createElement('h3');
    heading.textContent = title;
    const input = document.createElement(options.multiline ? 'textarea' : 'input');
    input.value = String(defaultValue ?? '');
    if (!options.multiline) input.type = options.type || 'text';
    if (options.min !== undefined) input.min = String(options.min);
    if (options.max !== undefined) input.max = String(options.max);
    if (options.step !== undefined) input.step = String(options.step);
    if (options.maxLength !== undefined) input.maxLength = Number(options.maxLength);
    input.required = options.required !== false;
    const actions = document.createElement('div');
    actions.className = 'dialog-actions';
    const cancel = document.createElement('button');
    cancel.type = 'button';
    cancel.className = 'secondary';
    cancel.textContent = 'Anuluj';
    const confirm = document.createElement('button');
    confirm.type = 'submit';
    confirm.textContent = 'Zatwierdź';
    actions.append(cancel, confirm);
    form.append(heading, input, actions);
    dialog.append(form);
    document.body.append(dialog);
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      dialog.remove();
      window.setTimeout(scheduleAutomaticBoardScan, 0);
      resolve(value);
    };
    cancel.addEventListener('click', () => {
      dialog.close();
      finish(null);
    });
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      dialog.close();
      finish(input.value);
    });
    dialog.addEventListener('cancel', (event) => {
      event.preventDefault();
      dialog.close();
      finish(null);
    });
    dialog.addEventListener('close', () => finish(null));
    dialog.showModal();
    input.focus();
    input.select();
  });
}
async function explorationDivinationQuery(spellId) {
  if (!['locate_animals_or_plants', 'locate_object'].includes(String(spellId))) return '';
  return requestTextInput(
    spellId === 'locate_object'
      ? 'Jaki znany przedmiot lub rodzaj przedmiotu chcesz odnaleźć?'
      : 'Jaki znany gatunek zwierzęcia albo rośliny chcesz odnaleźć?',
    ''
  );
}
async function explorationSpellDetails(spellId, castLevel = null) {
  if (String(spellId) === 'rope_trick') {
    const length = await requestTextInput(
      'Podaj długość liny: wielokrotność 5 ft, od 5 do 60 ft.',
      '60',
      {type: 'number', min: 5, max: 60, step: 5}
    );
    if (length === null) return null;
    return {target_id: '', rope_length_feet: Number(length)};
  }
  if (String(spellId) === 'protection_from_poison') {
    const actors = (state.actors || []).filter(actor => !actor.defeated);
    const answer = await requestTextInput(
      `Wybierz sprzymierzeńca w zasięgu dotyku:\n${actors.map((actor, index) => `${index + 1}. ${actor.name}`).join('\n')}`,
      '1',
      {type: 'number', min: 1, max: actors.length}
    );
    if (answer === null) return null;
    const selected = actors[Number(answer) - 1];
    if (!selected) {
      window.alert('Wybierz numer postaci z listy.');
      return null;
    }
    return {target_id: selected.id};
  }
  if (String(spellId) === 'prayer_of_healing') {
    const diceCount = 2 + Math.max(0, Number(castLevel || 2) - 2);
    const healingRoll = await requestTextInput(
      `Rzuć ${diceCount}k8. Modlitwa automatycznie obejmie do 6 legalnych sojuszników w 30 ft. Wpisz sumę kości:`,
      '',
      {type: 'number', min: diceCount, max: diceCount * 8}
    );
    if (healingRoll === null) return null;
    return {target_id: '', target_ids: [], healing_roll: Number(healingRoll)};
  }
  if (String(spellId) !== 'magic_mouth') {
    return {target_id: await explorationDivinationQuery(spellId)};
  }
  const activePoint = state.active_point || {};
  if (!activePoint.id) {
    window.alert('Najpierw wejdź w interakcję z przedmiotem lub punktem, który chcesz zaczarować.');
    return null;
  }
  const message = await requestTextInput(
    'Jaką wiadomość (maksymalnie 25 słów) mają wypowiedzieć Magiczne usta?',
    '',
    {multiline: true, maxLength: 240}
  );
  if (message === null) return null;
  const triggerDescription = await requestTextInput(
    'Opisz widzialny albo słyszalny warunek. Na Arenie wyzwoli go interakcja z tym obiektem.',
    'Ktoś wchodzi w interakcję z obiektem',
    {multiline: true}
  );
  if (triggerDescription === null) return null;
  return {target_id: activePoint.id, message, trigger_description: triggerDescription};
}
async function castExplorationRitual(actorId, spellId) {
  const details = await explorationSpellDetails(spellId);
  if (details === null || details.target_id === null) return;
  api('/api/exploration/ritual', {actor_id: actorId, spell_id: spellId, ...details}, 'Odprawiam rytuał...');
}
function castHazardFeatherFall() {
  const caster = document.getElementById('hazard-feather-fall-caster');
  api(
    '/api/exploration/hazard/feather-fall',
    {caster_id: caster ? caster.value : ''},
    'Rzucam Powolne opadanie...'
  );
}
async function castExplorationSpell(actorId, spellId, castLevel) {
  const details = await explorationSpellDetails(spellId, castLevel);
  if (details === null || details.target_id === null) return;
  api('/api/exploration/spell', {actor_id: actorId, spell_id: spellId, cast_level: castLevel, ...details}, 'Rzucam czar w eksploracji...');
}
async function ropeTrickActor(effectId, mode) {
  const actors = state.actors || [];
  const answer = await requestTextInput(
    `${mode === 'enter' ? 'Kto wchodzi' : 'Kto wychodzi'}?\n${actors.map((actor, index) => `${index + 1}. ${actor.name}`).join('\n')}`,
    '1',
    {type: 'number', min: 1, max: actors.length}
  );
  if (answer === null) return;
  const actor = actors[Number(answer) - 1];
  if (!actor) {
    window.alert('Wybierz numer postaci z listy.');
    return;
  }
  api(`/api/exploration/rope-trick/${mode}`, {effect_id: effectId, actor_id: actor.id}, mode === 'enter' ? 'Wchodzę do przestrzeni...' : 'Wychodzę z przestrzeni...');
}
function enterRopeTrick(effectId) { ropeTrickActor(effectId, 'enter'); }
function exitRopeTrick(effectId) { ropeTrickActor(effectId, 'exit'); }
function confirmPlayerAttackTarget() { api('/api/combat/player-attack-confirm', {}, 'Potwierdzam atak...'); }
function startAuxTargeting(mode) { api('/api/combat/aux-targeting/start', {mode}, 'Podświetlam legalne cele...'); }
function finishAuxTargeting() { api('/api/combat/aux-targeting/finish', {}, 'Kończę wybór celów...'); }
function cancelPlayerAttackTarget() { api('/api/combat/player-attack-cancel', {}, 'Anuluję wybór celu...'); }
function confirmCombatInteraction(interactionId) { api('/api/combat/interaction/confirm', {interaction_id: interactionId}, 'Potwierdzam interakcję...'); }
function cancelCombatInteraction() { api('/api/combat/interaction/cancel', {}, 'Anuluję interakcję...'); }
function moveCombatContextMenu(delta) { api('/api/combat/context-menu/select', {delta}, ''); }
function applyOptimisticCombatTurnActionDelta(delta) {
  const menu = state && state.combat ? state.combat.turn_action_menu : null;
  const options = menu ? (menu.options || []) : [];
  if (!options.length) return false;
  const selectedIndex = (Number(menu.selected_index || 0) + Number(delta) + options.length) % options.length;
  menu.selected_index = selectedIndex;
  menu.selected_option_id = options[selectedIndex].id;
  return true;
}
function updateCombatTurnActionSelectionDom({ensureVisible = true} = {}) {
  const menu = state && state.combat ? state.combat.turn_action_menu : null;
  const list = document.querySelector('.combat-turn-action-list');
  if (!menu || !list) return false;
  const options = menu.options || [];
  const selectedIndex = Math.max(0, Math.min(options.length - 1, Number(menu.selected_index || 0)));
  const buttons = list.querySelectorAll('.combat-turn-action[data-action-index]');
  let selectedButton = null;
  buttons.forEach(button => {
    const selected = Number(button.dataset.actionIndex) === selectedIndex;
    button.classList.toggle('selected', selected);
    button.setAttribute('aria-current', selected ? 'true' : 'false');
    if (selected) selectedButton = button;
  });
  const position = document.getElementById('combat-turn-action-position');
  if (position) {
    const stageLabel = menu.stage === 'preview' ? 'Podgląd działania' : 'Lista działań';
    position.textContent = `${stageLabel} · ${selectedIndex + 1} z ${options.length}`;
  }
  const availability = document.getElementById('combat-turn-action-availability');
  if (availability) availability.innerHTML = combatTurnActionUnavailableHtml(menu, state.combat || {});
  if (ensureVisible && selectedButton) {
    const listRect = list.getBoundingClientRect();
    const buttonRect = selectedButton.getBoundingClientRect();
    if (buttonRect.top < listRect.top) {
      list.scrollTop -= listRect.top - buttonRect.top;
    } else if (buttonRect.bottom > listRect.bottom) {
      list.scrollTop += buttonRect.bottom - listRect.bottom;
    }
  }
  return true;
}
function moveCombatTurnAction(delta) {
  const menu = state && state.combat ? state.combat.turn_action_menu : null;
  if (!menu || menu.stage !== 'list') return;
  if (!applyOptimisticCombatTurnActionDelta(delta)) return;
  combatTurnActionMoveDelta += Number(delta);
  updateCombatTurnActionSelectionDom();
  clearTimeout(combatTurnActionMoveTimer);
  combatTurnActionMoveTimer = setTimeout(flushCombatTurnActionMove, 45);
}
async function flushCombatTurnActionMove() {
  combatTurnActionMoveTimer = null;
  if (combatTurnActionMoveInFlight || !combatTurnActionMoveDelta) return;
  const delta = combatTurnActionMoveDelta;
  combatTurnActionMoveDelta = 0;
  combatTurnActionMoveInFlight = true;
  try {
    const res = await fetch('/api/combat/turn-actions/select', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({delta})
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.error || 'Nie udało się zmienić podglądu akcji.');
    }
    state = data.state || data;
    if (combatTurnActionMoveDelta) {
      applyOptimisticCombatTurnActionDelta(combatTurnActionMoveDelta);
    }
    synchronizeBoardSelection();
    updateCombatTurnActionSelectionDom();
    updateBoardInputPresentation();
    refreshSessionLog();
  } catch (_error) {
    alert('Nie udało się połączyć z aplikacją podczas zmiany akcji.');
  } finally {
    combatTurnActionMoveInFlight = false;
    if (combatTurnActionMoveDelta) {
      combatTurnActionMoveTimer = setTimeout(flushCombatTurnActionMove, 0);
    } else {
      scheduleAutomaticBoardScan();
    }
  }
}
async function settleCombatTurnActionMove() {
  clearTimeout(combatTurnActionMoveTimer);
  combatTurnActionMoveTimer = null;
  while (combatTurnActionMoveInFlight || combatTurnActionMoveDelta) {
    if (!combatTurnActionMoveInFlight && combatTurnActionMoveDelta) {
      await flushCombatTurnActionMove();
      continue;
    }
    await new Promise(resolve => window.setTimeout(resolve, 10));
  }
}
async function confirmCombatTurnAction(optionId = '') {
  const menu = state && state.combat ? state.combat.turn_action_menu : null;
  const selectedOptionId = optionId || String((menu || {}).selected_option_id || '');
  await settleCombatTurnActionMove();
  api('/api/combat/turn-actions/confirm', {option_id: selectedOptionId}, '');
}
function cancelCombatTurnActionPreview() {
  api('/api/combat/turn-actions/cancel-preview', {}, 'Anuluję podgląd bez kosztu...');
}
function combatShortcutFromEvent(event) {
  if (event.code === 'Space') return 'SPACE';
  if (/^(Digit|Numpad)[0-9]$/.test(event.code)) return event.code.slice(-1);
  if (/^Key[A-Z]$/.test(event.code)) {
    const letter = event.code.slice(-1);
    return event.shiftKey ? `SHIFT+${letter}` : letter;
  }
  return '';
}
function triggerCombatActionShortcut(event) {
  if (busy || event.repeat || event.ctrlKey || event.metaKey || event.altKey) return false;
  return triggerCombatActionShortcutKey(combatShortcutFromEvent(event));
}
function triggerCombatActionShortcutKey(shortcut) {
  const combat = state && state.combat ? state.combat : null;
  if (!combat || combat.context_menu) return false;
  const menu = state && state.combat ? state.combat.turn_action_menu : null;
  if (!menu || menu.stage !== 'list') return false;
  if (!shortcut) return false;
  const option = (menu.options || []).find(candidate => candidate.shortcut === shortcut);
  if (!option) {
    const isKnownShortcut = (menu.bindings || []).some(binding => binding.key === shortcut)
      || shortcut === 'SPACE';
    if (!isKnownShortcut) return false;
    window.alert('Ta akcja nie jest teraz dostępna. Wybierz inną dostępną ikonę.');
    return true;
  }
  confirmCombatTurnAction(option.id);
  return true;
}
function confirmCombatItemTarget() {
  api('/api/combat/item-target/confirm', {}, 'Potwierdzam użycie przedmiotu...');
}
function cancelCombatItemTargeting() {
  api('/api/combat/item-target/cancel', {}, 'Anuluję użycie przedmiotu...');
}
function confirmCombatPendingBoardSelection() {
  api('/api/combat/pending-board-selection/confirm', {}, 'Potwierdzam wybór na planszy...');
}
function confirmCombatContextMenu(optionId, optionIndex = null) {
  const menu = ((state.combat || {}).context_menu) || {};
  const options = menu.options || [];
  const index = optionIndex === null
    ? Number(menu.selected_index || 0)
    : Number(optionIndex);
  const option = options[index] || {};
  if (option.provider === 'class_feature' && option.action_id) {
    useClassFeature(option.action_id);
    return;
  }
  const payload = {option_id: optionId || ''};
  if (option.loot_quantity_max !== null && option.loot_quantity_max !== undefined) {
    const input = document.getElementById(`combat-loot-quantity-${index}`);
    if (!input) return;
    payload.quantity = Number(input ? input.value : 0);
  }
  api('/api/combat/context-menu/confirm', payload, 'Zabieram wybraną część łupu...');
}
function cancelCombatContextMenu() { api('/api/combat/context-menu/cancel', {}, ''); }
function submitPlayerDamageRoll() {
  const pending = ((state.combat || {}).pending_player_attack) || {};
  api('/api/combat/player-damage', damageComponentPayload(pending, 'combat-damage'), 'Zapisuję obrażenia...');
}
function selectDivineSmite(slotLevel) {
  api('/api/combat/divine-smite', {slot_level: Number(slotLevel)}, 'Dodaję Divine Smite...');
}
function resolveOpenHandTechnique(mode) {
  api('/api/combat/open-hand-technique', {mode}, 'Rozstrzygam Open Hand Technique...');
}
function resolveRepellingBlast(push) {
  api('/api/combat/repelling-blast', {push}, push ? 'Odpycham cel...' : 'Pomijam odepchnięcie...');
}
function skipOpenHandTechnique() {
  api('/api/combat/open-hand-technique/skip', {}, 'Pomijam Open Hand Technique...');
}
function submitPlayerHealingRoll() {
  const healing = document.getElementById('combat-healing-roll');
  api('/api/combat/player-healing', {healing: Number(healing ? healing.value : 0)}, 'Zapisuję leczenie...');
}
function cancelPlayerHealing() { api('/api/combat/player-healing-cancel', {}, 'Anuluję leczenie...'); }
function confirmAreaSpell() { api('/api/combat/area-spell/confirm', {}, 'Potwierdzam czar obszarowy...'); }
function activateEmpoweredSpell() {
  api('/api/combat/metamagic/empowered', {}, 'Aktywuję Empowered Spell...');
}
function submitAreaSpellDamage() {
  const pending = ((state.combat || {}).pending_area_spell) || {};
  api('/api/combat/area-spell/damage', damageComponentPayload(pending, 'area-spell-damage'), 'Zapisuję obrażenia obszarowe...');
}
function cancelAreaSpell() { api('/api/combat/area-spell/cancel', {}, 'Anuluję czar obszarowy...'); }
function useStrengthPotion(actionId) { api('/api/combat/strength-potion', {action_id: actionId}, 'Używam eliksiru...'); }
function useAssistedSpell(actionId, castLevel, metamagicIds = []) {
  api('/api/combat/assisted-spell', {action_id: actionId, cast_level: castLevel, metamagic_ids: metamagicIds}, 'Rzucam czar...');
}
function startMultiTargetDamageSpell(actionId, castLevel) {
  api('/api/combat/multi-target-spell/start', {action_id: actionId, cast_level: castLevel}, 'Przygotowuję wybór pocisków...');
}
function clearMultiTargetDamageSpellTargets() {
  api('/api/combat/multi-target-spell/clear', {}, 'Czyszczę cele pocisków...');
}
function confirmMultiTargetDamageSpell() {
  const pending = ((state.combat || {}).pending_multi_target_damage_spell) || {};
  const dieRolls = Array.from({length: Number(pending.projectile_count || 0)}, (_, index) =>
    Number((document.getElementById(`multi-target-spell-roll-${index}`) || {}).value || 0)
  );
  const naturalRolls = pending.projectile_attack_roll
    ? Array.from({length: Number(pending.projectile_count || 0)}, (_, index) =>
        Number((document.getElementById(`multi-target-spell-attack-${index}`) || {}).value || 0)
      )
    : [];
  api('/api/combat/multi-target-spell/confirm', {die_rolls: dieRolls, natural_rolls: naturalRolls}, 'Rozstrzygam pociski...');
}
function cancelMultiTargetDamageSpell() {
  api('/api/combat/multi-target-spell/cancel', {}, 'Anuluję czar...');
}
function useClassFeature(actionId) {
  const action = (((state || {}).combat || {}).class_feature_actions || [])
    .find(item => item.id === actionId) || {};
  const needsRoll = ['second_wind', 'anchoring_arrow', 'exposing_arrow'].includes(actionId);
  const dieSides = actionId === 'anchoring_arrow' ? 4 : actionId === 'exposing_arrow' ? 8 : 10;
  const needsTarget = ['bardic_inspiration', 'lay_on_hands', 'preserve_life'].includes(actionId);
  const needsPoints = ['lay_on_hands', 'preserve_life'].includes(actionId);
  const needsFont = actionId === 'font_of_magic';
  const needsWildShape = actionId === 'wild_shape' && !action.wild_shape_revert;
  const needsSavingRolls = ['turn_undead', 'turn_the_unholy'].includes(actionId);
  const needsPrimevalAwareness = actionId === 'primeval_awareness';
  const needsPactWeapon = actionId === 'pact_weapon';
  const needsCunningAction = actionId === 'cunning_action';
  if (needsTarget) {
    api('/api/combat/class-feature/targeting', {action_id: actionId}, 'Podświetlam legalne cele zdolności...');
    return;
  }
  if (!needsRoll && !needsTarget && !needsPoints && !needsFont && !needsWildShape && !needsSavingRolls && !needsPrimevalAwareness && !needsPactWeapon && !needsCunningAction) {
    api('/api/combat/class-feature', {action_id: actionId}, 'Używam cechy klasowej...');
    return;
  }
  pendingClassFeatureActionId = actionId;
  let dialog = document.getElementById('class-feature-dialog');
  if (!dialog) {
    dialog = document.createElement('dialog');
    dialog.id = 'class-feature-dialog';
    document.body.appendChild(dialog);
  }
  dialog.innerHTML = `
    <form method="dialog" class="modal-card" onsubmit="submitClassFeatureDialog(event)">
      <h2>${esc(action.label || identifierLabel(actionId))}</h2>
      ${needsRoll ? `<label>Wynik k${dieSides}<input id="class-feature-roll" type="number" min="1" max="${dieSides}" required></label>` : ''}
      ${needsPoints ? '<label>Punkty leczenia<input id="class-feature-points" type="number" min="1" required></label>' : ''}
      ${needsFont ? `<label>Kierunek konwersji<select id="class-feature-mode" required>
        <option value="slot_to_points">Slot → Sorcery Points</option>
        <option value="points_to_slot">Sorcery Points → slot</option>
      </select></label>
      <label>Poziom slotu<input id="class-feature-slot-level" type="number" min="1" max="5" required></label>` : ''}
      ${needsWildShape ? `<label>Forma bestii<select id="class-feature-form-id" required>
        ${(action.wild_shape_forms || []).map(form => `<option value="${esc(form.id)}">${esc(form.name)} · CR ${esc(form.challenge_rating)} · HP ${esc(form.hit_points)} · KP ${esc(form.ac)} · ${esc(form.speed_feet)} ft</option>`).join('')}
      </select></label>` : ''}
      ${needsSavingRolls ? (
        (action.saving_throw_targets || []).length
          ? `<div class="status-list">${(action.saving_throw_targets || []).map(target => `
              <label>${esc(target.name)} · Wisdom ST ${esc(target.dc)}
                <input class="class-feature-saving-roll" data-target-id="${esc(target.id)}" type="number" min="1" max="20" required>
              </label>`).join('')}</div>`
          : '<p>Brak właściwych celów w zasięgu 30 stóp. Użycie nadal zużyje akcję i Channel Divinity.</p>'
      ) : ''}
      ${needsPrimevalAwareness ? `<label>Slot czaru<select id="class-feature-slot-level" required>
        ${(action.available_slot_levels || []).map(level => `<option value="${Number(level)}">${esc(level)}. poziom · ${esc(level)} min</option>`).join('')}
      </select></label>` : ''}
      ${needsPactWeapon ? `<label>Forma Pact Weapon<select id="class-feature-form-id" required>
        ${(action.pact_weapon_forms || []).map(form => `<option value="${esc(form.id)}">${esc(form.name)}</option>`).join('')}
      </select></label>` : ''}
      ${needsCunningAction ? `<label>Wariant Sprytnej akcji<select id="class-feature-mode" required>
        <option value="dash">Sprint</option>
        <option value="disengage">Odwrót</option>
        <option value="hide">Ukrycie</option>
      </select></label>` : ''}
      <div class="panel-actions">
        <button type="button" class="secondary" onclick="closeClassFeatureDialog()">Anuluj</button>
        <button type="submit">Potwierdź</button>
      </div>
    </form>`;
  dialog.showModal();
}
function cancelClassFeatureTargeting() {
  api('/api/combat/class-feature/targeting/cancel', {}, 'Anuluję wybór celu...');
}
function confirmClassFeatureTargetSelection() {
  api('/api/combat/class-feature/targeting/confirm', {}, 'Potwierdzam wybrany cel...');
}
function confirmClassFeatureBoardTarget() {
  const pending = (((state || {}).combat || {}).class_feature_targeting) || {};
  const selected = pending.selected_target || {};
  const points = Number((document.getElementById('class-feature-board-points') || {}).value || 0);
  if (pending.action_id === 'preserve_life') {
    const allocations = Array.from(document.querySelectorAll('.preserve-life-allocation'))
      .map(input => ({target_id: input.dataset.targetId, points: Number(input.value || 0)}))
      .filter(entry => entry.target_id && entry.points > 0);
    if (!allocations.length) return;
    api('/api/combat/class-feature', {
      action_id: pending.action_id,
      allocations,
    }, 'Rozdzielam pulę Zachowania życia...');
    return;
  }
  if (!selected.id || points < 1) return;
  api('/api/combat/class-feature', {
    action_id: pending.action_id,
    target_id: selected.id,
    points,
  }, 'Używam cechy klasowej...');
}
function closeClassFeatureDialog() {
  document.getElementById('class-feature-dialog')?.close();
  pendingClassFeatureActionId = '';
}
function submitClassFeatureDialog(event) {
  event.preventDefault();
  const payload = {action_id: pendingClassFeatureActionId};
  const roll = document.getElementById('class-feature-roll');
  const target = document.getElementById('class-feature-target');
  const points = document.getElementById('class-feature-points');
  const mode = document.getElementById('class-feature-mode');
  const slotLevel = document.getElementById('class-feature-slot-level');
  const formId = document.getElementById('class-feature-form-id');
  if (roll) payload.natural_roll = Number(roll.value);
  if (target) payload.target_id = target.value.trim();
  if (points) payload.points = Number(points.value);
  if (mode) payload.mode = mode.value;
  if (slotLevel) payload.slot_level = Number(slotLevel.value);
  if (formId) payload.form_id = formId.value;
  payload.saving_rolls = Array.from(document.querySelectorAll('.class-feature-saving-roll')).map(input => ({
    target_id: input.dataset.targetId,
    natural_roll: Number(input.value),
  }));
  closeClassFeatureDialog();
  api('/api/combat/class-feature', payload, 'Używam cechy klasowej...');
}
function startLongCast(actionId, castLevel = null) { api('/api/combat/long-cast/start', {action_id: actionId, cast_level: castLevel}, 'Rozpoczynam długie rzucanie...'); }
function continueLongCast() { api('/api/combat/long-cast/continue', {}, 'Kontynuuję długie rzucanie...'); }
function cancelLongCast() { api('/api/combat/long-cast/cancel', {}, 'Przerywam długie rzucanie...'); }
function startSummon(actionId, castLevel = null) { api('/api/combat/summon/start', {action_id: actionId, cast_level: castLevel}, 'Wybieram pole przywołania...'); }
function cancelSummon() { api('/api/combat/summon/cancel', {}, 'Anuluję przywołanie...'); }
function startMagicMovement(actionId, castLevel = null) { api('/api/combat/magic-movement/start', {action_id: actionId, cast_level: castLevel}, 'Wybieram magiczny ruch...'); }
function startMoonbeamMove(effectId) { api('/api/combat/moonbeam/move/start', {effect_id: effectId}, 'Wybieram nowy środek strefy czaru...'); }
function cancelMagicMovement() { api('/api/combat/magic-movement/cancel', {}, 'Anuluję magiczny ruch...'); }
function startSpellDebuff(actionId, castLevel = null) { api('/api/combat/spell-debuff/start', {action_id: actionId, cast_level: castLevel}, 'Wybieram cel osłabienia...'); }
function selectSpellDebuffCondition(condition) {
  if (!condition) return;
  api('/api/combat/spell-debuff/condition', {condition}, 'Ustawiam wariant efektu...');
}
function cancelSpellDebuff() { api('/api/combat/spell-debuff/cancel', {}, 'Anuluję czar osłabiający...'); }
function startSpellDispel(actionId, castLevel = null) { api('/api/combat/spell-dispel/start', {action_id: actionId, cast_level: castLevel}, 'Wybieram cel rozproszenia...'); }
function submitSpellDispelCheck() {
  const naturalRoll = Number((document.getElementById('spell-dispel-roll') || {}).value || 0);
  api('/api/combat/spell-dispel/check', {natural_roll: naturalRoll}, 'Rozstrzygam test rozproszenia...');
}
function cancelSpellDispel() { api('/api/combat/spell-dispel/cancel', {}, 'Anuluję rozproszenie magii...'); }
function startConcentrationAction(actionId, castLevel = null) { api('/api/combat/concentration/start', {action_id: actionId, cast_level: castLevel}, 'Przygotowuję czar koncentracyjny...'); }
function confirmConcentrationAction() {
  const roll = (document.getElementById('combat-status-roll') || {}).value || null;
  const effectOption = (document.getElementById('combat-status-effect-option') || {}).value || '';
  api('/api/combat/concentration/confirm', {roll_total: roll, effect_option: effectOption}, 'Potwierdzam czar...');
}
function cancelConcentrationAction() { api('/api/combat/concentration/cancel', {}, 'Anuluję czar koncentracyjny...'); }
function completeTimedCombatSpell() { api('/api/combat/timed-cast/complete', {}, 'Kończę dziesięciominutowe rzucanie...'); }
function submitConcentrationCheck() {
  const roll = document.getElementById('concentration-check-roll');
  const roll2 = document.getElementById('concentration-check-roll-2');
  api('/api/combat/concentration-check', {
    natural_roll: Number(roll ? roll.value : 0),
    natural_roll_2: roll2 ? Number(roll2.value || 0) : null,
  }, 'Rozstrzygam koncentrację...');
}
function submitDeathSave() {
  const roll = document.getElementById('combat-death-save-roll');
  api('/api/combat/death-save', {natural_roll: Number(roll ? roll.value : 0)}, 'Rozstrzygam rzut śmierci...');
}
function submitCombatConditionSave(condition) {
  const roll = document.getElementById('combat-condition-save-roll');
  const roll2 = document.getElementById('combat-condition-save-roll-2');
  const inspiration = document.getElementById('combat-condition-save-inspiration');
  const bless = document.getElementById('combat-condition-save-bless');
  api('/api/combat/condition-save', {
    condition,
    natural_roll: Number(roll ? roll.value : 0),
    natural_roll_2: roll2 ? Number(roll2.value || 0) : null,
    bardic_inspiration_roll: inspiration && inspiration.value !== '' ? Number(inspiration.value) : null,
    bless_roll: bless && bless.value !== '' ? Number(bless.value) : null,
  }, 'Rozstrzygam rzut przeciw warunkowi...');
}
function startStabilizationTargeting(method) {
  api('/api/combat/stabilize/targeting', {method}, 'Podświetlam cele stabilizacji...');
}
function confirmBoardStabilization() {
  const stabilization = (((state || {}).combat || {}).stabilization) || {};
  const target = stabilization.selected_target || {};
  const roll = document.getElementById('combat-stabilization-roll');
  api('/api/combat/stabilize', {
    target_id: target.id || '',
    method: 'medicine',
    natural_roll: Number(roll ? roll.value : 0),
  }, 'Stabilizuję sojusznika...');
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
function startCombatHide() { api('/api/combat/hide/start', {}, 'Przygotowuję Hide...'); }
function startCombatSearch() { api('/api/combat/search/start', {}, 'Przygotowuję Search...'); }
function submitCombatSkillCheck() {
  api('/api/combat/skill-check', d20RollPayload('combat-skill-check-roll'), 'Rozstrzygam test...');
}
function cancelCombatSkillCheck() { api('/api/combat/skill-check/cancel', {}, 'Anuluję test...'); }
function submitCombatShove() {
  const roll = document.getElementById('combat-shove-roll');
  api('/api/combat/shove/resolve', {natural_roll: Number(roll ? roll.value : 0)}, 'Rozstrzygam Shove...');
}
function cancelCombatShove() { api('/api/combat/shove/cancel', {}, 'Anuluję Shove...'); }
function submitCombatGrapple() {
  const roll = document.getElementById('combat-grapple-roll');
  api('/api/combat/grapple/resolve', {natural_roll: Number(roll ? roll.value : 0)}, 'Rozstrzygam Grapple...');
}
function cancelCombatGrapple() { api('/api/combat/grapple/cancel', {}, 'Anuluję Grapple...'); }
function startCombatHelp() { api('/api/combat/help/start', {}, 'Przygotowuję Help...'); }
function confirmCombatHelp() {
  const pending = ((state || {}).combat || {}).pending_combat_help || {};
  const allyId = pending.selected_ally_id || ((pending.selected_ally || {}).id) || '';
  const targetId = pending.selected_target_id || ((pending.selected_target || {}).id) || '';
  api(
    '/api/combat/help/confirm',
    {ally_id: allyId, target_id: targetId},
    'Potwierdzam akcję Help...'
  );
}
function cancelCombatHelp() { api('/api/combat/help/cancel', {}, 'Anuluję Help...'); }
function startCombatReady() { api('/api/combat/ready/start', {}, 'Przygotowuję Ready...'); }
function confirmCombatReady() {
  const trigger = document.getElementById('combat-ready-trigger');
  api('/api/combat/ready/confirm', {trigger: trigger ? trigger.value : ''}, 'Potwierdzam Ready...');
}
function cancelCombatReady() { api('/api/combat/ready/cancel', {}, 'Anuluję Ready...'); }
function resolveEnemyTurn() { api('/api/combat/enemy-turn', {}, 'Rozgrywam turę przeciwnika...'); }
function useInstinctiveDodgeReaction() { api('/api/combat/instinctive-dodge/use', {}, 'Mira wykonuje unik...'); }
function skipInstinctiveDodgeReaction() { api('/api/combat/instinctive-dodge/skip', {}, 'Mira nie wykonuje uniku...'); }
function castDefensiveSpellReaction() { api('/api/combat/defensive-spell/cast', {}, 'Rzucam czar obronny...'); }
function skipDefensiveSpellReaction() { api('/api/combat/defensive-spell/skip', {}, 'Przyjmuję trafienie...'); }
function castRetaliationSpellReaction() { api('/api/combat/retaliation-spell/cast', {}, 'Odpowiadam czarem...'); }
function skipRetaliationSpellReaction() { api('/api/combat/retaliation-spell/skip', {}, 'Nie używam reakcji...'); }
function submitCuttingWordsReaction() {
  const input = document.getElementById('cutting-words-roll');
  api('/api/combat/cutting-words/roll', {die_roll: Number(input ? input.value : 0)}, 'Rozstrzygam Cutting Words...');
}
function skipCuttingWordsReaction() { api('/api/combat/cutting-words/skip', {}, 'Pomijam Cutting Words...'); }
function submitDistractingShoutReaction() {
  const input = document.getElementById('distracting-shout-roll');
  api('/api/combat/distracting-shout/roll', {die_roll: Number(input ? input.value : 0)}, 'Rozstrzygam Rozpraszający okrzyk...');
}
function skipDistractingShoutReaction() { api('/api/combat/distracting-shout/skip', {}, 'Pomijam Rozpraszający okrzyk...'); }
function submitDeflectMissilesReaction() {
  const input = document.getElementById('deflect-missiles-roll');
  api('/api/combat/deflect-missiles/roll', {die_roll: Number(input ? input.value : 0)}, 'Rozstrzygam Deflect Missiles...');
}
function skipDeflectMissilesReaction() { api('/api/combat/deflect-missiles/skip', {}, 'Przyjmuję trafienie pociskiem...'); }
function returnDeflectedMissile() {
  const first = document.getElementById('deflected-missile-roll');
  const second = document.getElementById('deflected-missile-roll-2');
  const payload = {natural_roll: Number(first ? first.value : 0)};
  if (second && second.value !== '') payload.natural_roll_2 = Number(second.value);
  api('/api/combat/deflect-missiles/return', payload, 'Odrzucam pocisk...');
}
function submitDeflectedMissileDamage() {
  const input = document.getElementById('deflected-missile-damage');
  api('/api/combat/deflect-missiles/damage', {damage: Number(input ? input.value : 0)}, 'Rozliczam odrzucony pocisk...');
}
function castCounterspellReaction() {
  const input = document.getElementById('counterspell-cast-level');
  api('/api/combat/counterspell/cast', {cast_level: Number(input ? input.value : 0)}, 'Rzucam Kontrczar...');
}
function submitCounterspellCheck() {
  const input = document.getElementById('counterspell-roll');
  api('/api/combat/counterspell/roll', {natural_roll: Number(input ? input.value : 0)}, 'Rozstrzygam Kontrczar...');
}
function skipCounterspellReaction() { api('/api/combat/counterspell/skip', {}, 'Pomijam Kontrczar...'); }
function startEnemyOpportunityAttack() { api('/api/combat/enemy-opportunity/start', {}, 'Rozpoczynam atak okazyjny...'); }
function skipEnemyOpportunityAttack() { api('/api/combat/enemy-opportunity/skip', {}, 'Pomijam reakcję...'); }
function submitEnemyOpportunityAttackRoll() {
  api('/api/combat/enemy-opportunity/roll', d20RollPayload('enemy-opportunity-natural-roll'), 'Rozstrzygam atak okazyjny...');
}
function submitEnemyOpportunityDamageRoll() {
  const pending = ((state.combat || {}).pending_enemy_opportunity_attack) || {};
  api('/api/combat/enemy-opportunity/damage', damageComponentPayload(pending, 'enemy-opportunity-damage'), 'Zapisuję obrażenia ataku okazyjnego...');
}
function startReadyAttack() { api('/api/combat/ready-attack/start', {}, 'Używam przygotowanej akcji...'); }
function skipReadyAttack() { api('/api/combat/ready-attack/skip', {}, 'Pomijam przygotowaną akcję...'); }
function submitReadyAttackRoll() {
  api('/api/combat/ready-attack/roll', d20RollPayload('ready-natural-roll'), 'Rozstrzygam przygotowaną akcję...');
}
function submitReadyDamageRoll() {
  const pending = ((state.combat || {}).pending_ready_attack) || {};
  api('/api/combat/ready-attack/damage', damageComponentPayload(pending, 'ready-damage'), 'Zapisuję obrażenia przygotowanej akcji...');
}
function confirmEnemyTurnResult() { api('/api/combat/enemy-turn/confirm', {}, 'Potwierdzam wynik przeciwnika...'); }
function submitEnemySavingThrow() {
  const roll = document.getElementById('enemy-saving-throw-roll');
  const roll2 = document.getElementById('enemy-saving-throw-roll-2');
  const inspiration = document.getElementById('enemy-saving-throw-inspiration');
  const bless = document.getElementById('enemy-saving-throw-bless');
  api('/api/combat/enemy-saving-throw', {
    natural_roll: Number(roll ? roll.value : 0),
    natural_roll_2: roll2 ? Number(roll2.value || 0) : null,
    bardic_inspiration_roll: inspiration && inspiration.value !== '' ? Number(inspiration.value) : null,
    bless_roll: bless && bless.value !== '' ? Number(bless.value) : null,
  }, 'Rozstrzygam rzut obronny...');
}
async function finishCombatTurn() {
  await settleCombatTurnActionMove();
  await stopBoardScanLoop();
  api('/api/combat/end-turn', {}, 'Kończę turę...');
}
function retreatFromCombat() {
  if (!window.confirm('Czy cała drużyna wycofuje się z tego encountera?')) return;
  api('/api/combat/retreat', {}, 'Drużyna wycofuje się...');
}
function surrenderCombat() {
  if (!window.confirm('Czy cała drużyna kapituluje?')) return;
  api('/api/combat/surrender', {}, 'Drużyna kapituluje...');
}
function resolveCombatOutcome() { api('/api/encounter/combat/resolve', {}, 'Zastosowuję wynik walki w eksploracji...'); }
function retryEncounter() { api('/api/encounter/retry', {}, 'Przywracam początek walki...'); }
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
function visibleSingleAcceptButton() {
  const roots = ['flow-panel', 'encounter-panel', 'points-panel', 'pending-panel', 'roll-panel', 'result-panel'];
  const visibleButtons = roots.flatMap(id => {
    const root = document.getElementById(id);
    if (!root || root.hidden || root.offsetParent === null) return [];
    return Array.from(root.querySelectorAll('button')).filter(button => (
      !button.disabled && button.offsetParent !== null
    ));
  });
  const explicit = visibleButtons.filter(button => button.dataset.cardAction === 'accept');
  if (explicit.length === 1) return explicit[0];
  if (explicit.length > 1) return null;
  const backwardLabel = /^(anuluj|cofnij|wróć|odrzuć|nie|pomiń)/i;
  const candidates = visibleButtons.filter(button => (
    button.dataset.cardAction !== 'decline'
    && !button.classList.contains('secondary')
    && !backwardLabel.test((button.textContent || '').trim())
  ));
  return candidates.length === 1 ? candidates[0] : null;
}
function triggerPrimaryAction() {
  if (explorationManaPrimary()) return true;
  if (state?.training_arena?.tutorial?.notice) return acknowledgeTrainingNotice();
  if (sharedManaPrimary()) return true;
  if (busy) return false;
  if (!state) return false;
  if (keyboardRollWizard) {
    return keyboardRollWizard.review
      ? submitKeyboardRollWizard()
      : confirmKeyboardRollStep();
  }
  if (isVisible('result-panel')) { ackResult(); return true; }
  if (isVisible('pending-panel')) { decision('accept'); return true; }
  if (isVisible('roll-panel')) { sendRolls(); return true; }
  const gmChatDialog = document.getElementById('gm-chat-dialog');
  if (gmChatDialog && gmChatDialog.open) { sendAction(); return true; }
  const openDialog = document.querySelector('dialog[open]');
  const dialogForm = openDialog ? openDialog.querySelector('form') : null;
  if (dialogForm) {
    dialogForm.requestSubmit();
    return true;
  }
  if (state.combat?.physical_mana?.needs_attack_count) return declareManaAttackSeries();
  if (selectedZoneOptionId) { submitZoneOption(); return true; }
  if (selectedInteractionGoalId) { sendGoalAction(); return true; }
  if (continuationPanelOpen) return advanceContinuationStep();
  if (state.flow && state.flow.stage === 'short_rest') {
    if (state.short_rest && state.short_rest.pending && state.short_rest.pending.completed) finishShortRest();
    else confirmShortRest();
    return true;
  }
  if (isVisible('flow-panel')) {
    const stage = state.flow ? state.flow.stage : '';
    const preview = state.flow ? state.flow.preview_zone : null;
    if (stage === 'spell_preparation') { confirmSpellPreparation(); return true; }
    if (stage === 'location_preview' && preview && preview.available !== false) { confirmLocationPreview(); return true; }
    if (stage === 'party_setup' && state.exploration_setup) {
      const step = state.exploration_setup.current_step || {};
      if (step.requires_board_assignment) scanBoard();
      else confirmExplorationSetup();
      return true;
    }
    if (stage === 'interaction_result') { finishInteraction(); return true; }
    if (stage === 'ready_to_start') { startSession(); return true; }
  }
  const singleAcceptButton = visibleSingleAcceptButton();
  if (singleAcceptButton) { singleAcceptButton.click(); return true; }
  const scanButton = visiblePrimaryScanButton();
  if (scanButton) { scanButton.click(); return true; }
  const setup = state.encounter_setup;
  const stealth = state.encounter_stealth;
  const initiative = state.encounter_initiative;
  const combat = state.combat;
  const opening = (state.pending_encounter && state.pending_encounter.opening) || {};
    if (isVisible('encounter-panel')) {
    if (combat && combat.status === 'finished') { resolveCombatOutcome(); return true; }
    if (combat && combat.status === 'active') {
      if (resultAck) { ackResult(); return true; }
      if (combat.context_menu) { confirmCombatContextMenu(''); return true; }
      if (combat.turn_action_menu) {
        if (combat.turn_action_menu.stage === 'preview') {
          confirmCombatTurnAction('');
          return true;
        }
        return false;
      }
      if (combat.item_targeting) { confirmCombatItemTarget(); return true; }
      if (combat.shield_bash) {
        if (combat.shield_bash.stage === 'result') confirmShieldBashResult();
        else submitShieldBashRolls();
        return true;
      }
      if (combat.class_feature_targeting) {
        if (['lay_on_hands', 'preserve_life'].includes(combat.class_feature_targeting.action_id)) {
          confirmClassFeatureBoardTarget();
        } else {
          confirmClassFeatureTargetSelection();
        }
        return true;
      }
      if (combat.death_save_required) { submitDeathSave(); return true; }
      if (combat.pending_concentration_check) { submitConcentrationCheck(); return true; }
      if (combat.long_cast && combat.current_actor && combat.long_cast.caster_id === combat.current_actor.id) {
        continueLongCast();
        return true;
      }
      if (combat.pending_enemy_saving_throw) { submitEnemySavingThrow(); return true; }
      if (counterspellReaction(combat)) {
        if (combat.reaction_window.stage === 'ability_check') submitCounterspellCheck();
        else castCounterspellReaction();
        return true;
      }
      if (defensiveSpellReaction(combat)) { castDefensiveSpellReaction(); return true; }
      if (classFeatureReaction(combat, 'retaliation_spell')) { castRetaliationSpellReaction(); return true; }
      if (classFeatureReaction(combat, 'instinctive_dodge')) { useInstinctiveDodgeReaction(); return true; }
      if (classFeatureReaction(combat, 'cutting_words')) { submitCuttingWordsReaction(); return true; }
      if (classFeatureReaction(combat, 'distracting_shout')) { submitDistractingShoutReaction(); return true; }
      if (classFeatureReaction(combat, 'deflect_missiles')) {
        if (combat.reaction_window.stage === 'attack_roll') returnDeflectedMissile();
        else if (combat.reaction_window.stage === 'damage_roll') submitDeflectedMissileDamage();
        else submitDeflectMissilesReaction();
        return true;
      }
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
      if (combat.pending_combat_help) { scanBoard(); return true; }
      if (combat.pending_combat_shove) { submitCombatShove(); return true; }
      if (combat.pending_combat_grapple) { submitCombatGrapple(); return true; }
      if (combat.pending_combat_skill_check) { submitCombatSkillCheck(); return true; }
      if (combat.pending_concentration_action) {
        if (combat.pending_concentration_action.casting_ready) completeTimedCombatSpell();
        else confirmConcentrationAction();
        return true;
      }
      if (combat.pending_multi_target_damage_spell) {
        if (Number(combat.pending_multi_target_damage_spell.selected_count || 0) === Number(combat.pending_multi_target_damage_spell.projectile_count || 0)) confirmMultiTargetDamageSpell();
        else scanBoard();
        return true;
      }
      if (combat.pending_summon) {
        if (combat.pending_board_selection) confirmCombatPendingBoardSelection();
        else scanBoard();
        return true;
      }
      if (combat.pending_magic_movement) {
        if (combat.pending_board_selection) confirmCombatPendingBoardSelection();
        else scanBoard();
        return true;
      }
      if (combat.pending_spell_debuff) {
        if (combat.pending_board_selection) confirmCombatPendingBoardSelection();
        else scanBoard();
        return true;
      }
      if (combat.pending_spell_dispel) {
        if (combat.pending_spell_dispel.stage === 'ability_check') submitSpellDispelCheck();
        else if (combat.pending_board_selection) confirmCombatPendingBoardSelection();
        else scanBoard();
        return true;
      }
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
        if (combat.pending_area_spell.stage === 'attack_roll') submitVolleyRoll();
        else if (['damage_roll', 'volley_miss'].includes(combat.pending_area_spell.stage)) submitAreaSpellDamage();
        else confirmAreaSpell();
        return true;
      }
      if (combat.enemy_turn_preview) return false;
      const actor = combat.current_actor || {};
      if (actor.faction === 'enemy') { resolveEnemyTurn(); return true; }
      return false;
    }
    if (opening.required && !opening.resolved) { resolveEncounterOpening(); return true; }
    if (initiative && initiative.status !== 'completed') { submitEncounterInitiativeRoll(); return true; }
    if (setup && setup.status === 'completed' && stealth && !stealth.completed) return false;
    if (setup && setup.status === 'completed' && !initiative) { startEncounterInitiative(); return true; }
    if (setup && setup.status === 'active' && !setup.current_step?.can_confirm) return false;
    if (setup && setup.status === 'active') { confirmEncounterSetup(); return true; }
    if (!setup) { startEncounterSetup(); return true; }
  }
  return false;
}
function cancelCurrentCombatStep() {
  const combat = state && state.combat ? state.combat : null;
  if (!combat) return false;
  if (combat.context_menu) { cancelCombatContextMenu(); return true; }
  if (combat.turn_action_menu && combat.turn_action_menu.stage === 'preview') {
    cancelCombatTurnActionPreview();
    return true;
  }
  if (
    combat.turn_action_menu
    && (combat.turn_action_menu.options || []).some(option => option.action_id === 'nimra_metamagic_cancel')
  ) {
    cancelCombatTurnActionPreview();
    return true;
  }
  if (combat.item_targeting) { cancelCombatItemTargeting(); return true; }
  if (combat.shield_bash?.stage === 'result') return true;
  if (combat.class_feature_targeting) { cancelClassFeatureTargeting(); return true; }
  if (combat.pending_opportunity_movement) { cancelOpportunityMovement(); return true; }
  if (combat.pending_combat_help) { cancelCombatHelp(); return true; }
  if (combat.pending_combat_shove) { cancelCombatShove(); return true; }
  if (combat.pending_combat_grapple) { cancelCombatGrapple(); return true; }
  if (combat.pending_combat_skill_check) { cancelCombatSkillCheck(); return true; }
  if (combat.pending_concentration_action) { cancelConcentrationAction(); return true; }
  if (combat.pending_multi_target_damage_spell) { cancelMultiTargetDamageSpell(); return true; }
  if (combat.pending_summon) { cancelSummon(); return true; }
  if (combat.pending_magic_movement) { cancelMagicMovement(); return true; }
  if (combat.pending_spell_debuff) { cancelSpellDebuff(); return true; }
  if (combat.pending_spell_dispel && combat.pending_spell_dispel.stage === 'target_selection') { cancelSpellDispel(); return true; }
  if (combat.pending_combat_ready) { cancelCombatReady(); return true; }
  if (combat.pending_combat_interaction) { cancelCombatInteraction(); return true; }
  if (combat.pending_player_attack) { cancelPlayerAttackTarget(); return true; }
  if (combat.pending_player_healing) { cancelPlayerHealing(); return true; }
  if (combat.pending_area_spell) { cancelAreaSpell(); return true; }
  return false;
}
function triggerSecondaryAction() {
  if (state?.exploration_mana?.active) return explorationManaAction('leave');
  if (state?.combat?.shared_mana?.command?.stage) {
    if (state.combat.shared_mana.command.can_back) sharedCommandControl(true);
    return true;
  }
  if (state?.training_arena?.tutorial?.notice) return false;
  if (state?.combat?.shared_mana?.declaration?.stage === 'payment') {
    sharedManaCommand('cancel');
    return true;
  }
  if (busy || !state) return false;
  if (keyboardRollWizard) return cancelKeyboardRollWizard();
  if (isVisible('pending-panel')) { decision('reject'); return true; }
  if (state.flow && state.flow.stage === 'spell_preparation') {
    return startCustomSpellPreparation();
  }
  const gmChatDialog = document.getElementById('gm-chat-dialog');
  if (gmChatDialog && gmChatDialog.open) { closeGmChatDialog(); return true; }
  const openDialog = document.querySelector('dialog[open]');
  if (openDialog) {
    openDialog.dispatchEvent(new Event('cancel', {cancelable: true}));
    if (openDialog.open) openDialog.close();
    return true;
  }
  const combat = state.combat;
  if (combat && combat.status === 'active') {
    if (counterspellReaction(combat)) { skipCounterspellReaction(); return true; }
    if (defensiveSpellReaction(combat)) { skipDefensiveSpellReaction(); return true; }
    if (classFeatureReaction(combat, 'retaliation_spell')) { skipRetaliationSpellReaction(); return true; }
    if (classFeatureReaction(combat, 'instinctive_dodge')) { skipInstinctiveDodgeReaction(); return true; }
    if (classFeatureReaction(combat, 'cutting_words')) { skipCuttingWordsReaction(); return true; }
    if (classFeatureReaction(combat, 'distracting_shout')) { skipDistractingShoutReaction(); return true; }
    if (classFeatureReaction(combat, 'deflect_missiles')) { skipDeflectMissilesReaction(); return true; }
    if (combat.pending_ready_attack && combat.pending_ready_attack.stage === 'choice') {
      skipReadyAttack();
      return true;
    }
    if (
      combat.pending_enemy_opportunity_attack
      && combat.pending_enemy_opportunity_attack.stage === 'choice'
    ) {
      skipEnemyOpportunityAttack();
      return true;
    }
    if (combat.pending_player_attack && combat.pending_player_attack.stage === 'open_hand_choice') {
      skipOpenHandTechnique();
      return true;
    }
    if (combat.pending_player_attack && combat.pending_player_attack.stage === 'repelling_blast_choice') {
      resolveRepellingBlast(false);
      return true;
    }
  }
  if (cancelCurrentCombatStep()) return true;
  if (continuationPanelOpen) return retreatContinuationStep();
  if (downtimePanelOpen) { closeDowntimePanel(); return true; }
  if (selectedZoneOptionId) { cancelZoneOptionGoal(); return true; }
  if (selectedInteractionGoalId) { cancelInteractionGoal(); return true; }
  const flow = state.flow || {};
  if (closeCurrentExplorationInstance()) return true;
  if (flow.stage === 'location_preview') { cancelLocationPreview(); return true; }
  if (
    flow.stage === 'short_rest'
    && state.short_rest
    && state.short_rest.pending
    && !state.short_rest.pending.completed
  ) {
    cancelShortRest();
    return true;
  }
  return false;
}
function setPhysicalCardStatus(message, {error = false} = {}) {
  const status = document.getElementById('physical-card-status');
  if (!status) return;
  clearTimeout(physicalCardStatusTimer);
  status.textContent = message;
  status.classList.toggle('error', error);
  status.hidden = false;
  physicalCardStatusTimer = window.setTimeout(() => {
    status.hidden = true;
  }, 3200);
}
async function handlePhysicalCardScan(payload) {
  const now = Date.now();
  if (
    physicalCardScanInFlight
    || (payload === lastPhysicalCardPayload && now - lastPhysicalCardScanAt < PHYSICAL_CARD_REPEAT_GUARD_MS)
  ) {
    return;
  }
  physicalCardScanInFlight = true;
  lastPhysicalCardPayload = payload;
  lastPhysicalCardScanAt = now;
  try {
    const preparationActor = state && state.spell_preparation
      ? (state.spell_preparation.actors || []).find(
        actor => String(actor.actor_id) === String(state.spell_preparation.current_actor_id)
      )
      : null;
    const scanContext = selectedZoneOptionId
      ? {zone_option_id: selectedZoneOptionId}
      : {};
    if (
      state
      && state.flow
      && state.flow.stage === 'spell_preparation'
      && preparationActor
      && spellPreparationDraft
      && spellPreparationDraft.mode === 'custom'
    ) {
      scanContext.spell_preparation_mode = 'custom';
      scanContext.spell_preparation_actor_id = String(preparationActor.actor_id);
    }
    if (continuationPanelOpen && continuationStep === 'navigator') {
      scanContext.continuation_stage = 'navigator';
    }
    const response = await fetch('/api/physical-cards/scan', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        payload,
        context: scanContext,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      setPhysicalCardStatus(data.error || 'Nie udało się odczytać karty.', {error: true});
      return;
    }
    const clientActorSelectionApplied = data.effect === 'select_zone_option_actor'
      ? selectZoneOptionActor(data.actor_id)
      : false;
    const clientSpellPreparationApplied = data.effect === 'select_preparation_spell'
      ? selectSpellPreparationCard(data)
      : false;
    const clientContinuationNavigatorApplied = data.effect === 'select_continuation_navigator'
      ? selectContinuationNavigator(data.actor_id)
      : false;
    let applied = Boolean(
      data.applied
      || clientActorSelectionApplied
      || clientSpellPreparationApplied
      || clientContinuationNavigatorApplied
    );
    if (data.applied && data.state) {
      state = data.state;
      synchronizeBoardSelection();
      render();
      refreshSessionLog();
      scheduleAutomaticBoardScan();
    } else if (
      !clientActorSelectionApplied
      && !clientSpellPreparationApplied
      && !clientContinuationNavigatorApplied
    ) {
      const flowStage = state && state.flow ? state.flow.stage : '';
      const boardInteraction = state && state.flow
        ? (state.flow.board_interaction || {})
        : {};
      const explorationNavigationCardBlocked = Boolean(
        !state.combat
        && (
          flowStage === 'location_preview'
          || (flowStage === 'location_active' && boardInteraction.mode === 'navigation')
        )
        && !(state.pending && state.pending.stage === 'decision')
        && !continuationPanelOpen
        && ['accept', 'decline'].includes(data.action)
      );
      applied = explorationNavigationCardBlocked
        ? false
        : data.action === 'accept'
          ? triggerPrimaryAction()
          : data.action === 'decline'
            ? triggerSecondaryAction()
            : false;
      if (explorationNavigationCardBlocked) {
        setPhysicalCardStatus(
          'Nawigację i wychodzenie z instancji obsługuje teraz plansza. Karty ACCEPT/DECLINE działają przy właściwych decyzjach.',
          {error: true},
        );
        return;
      }
    }
    const resourceText = data.feedback && Array.isArray(data.feedback.resources)
      ? data.feedback.resources
        .filter(item => Number(item.maximum || 0) > 0)
        .map(item => `${item.label || identifierLabel(item.id)} ${Number(item.current || 0)}/${Number(item.maximum || 0)}`)
        .join(' · ')
      : '';
    setPhysicalCardStatus(
      applied
        ? `${((data.feedback && data.feedback.message)
          || `Karta ${data.label}: wykonano aktualną akcję.`)}${resourceText ? ` · ${resourceText}` : ''}`
        : `Karta ${data.label}: teraz nie ma pasującej akcji.`,
      {error: !applied},
    );
  } catch (_error) {
    setPhysicalCardStatus('Czytnik wysłał kartę, ale aplikacja nie odpowiedziała.', {error: true});
  } finally {
    if (lastPhysicalCardPayload === payload) {
      lastPhysicalCardScanAt = Date.now();
    }
    physicalCardScanInFlight = false;
  }
}
function physicalCardEditableTarget(target) {
  return Boolean(
    target
    && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')
    && !target.readOnly
    && !target.disabled
  );
}
function insertPhysicalCardBufferFallback(text, target = physicalCardKeyTarget) {
  if (!text || !physicalCardEditableTarget(target)) return;
  const start = Number.isInteger(target.selectionStart) ? target.selectionStart : target.value.length;
  const end = Number.isInteger(target.selectionEnd) ? target.selectionEnd : start;
  target.setRangeText(text, start, end, 'end');
  target.dispatchEvent(new Event('input', {bubbles: true}));
}
function clearPhysicalCardKeyBuffer() {
  clearTimeout(physicalCardKeyTimer);
  physicalCardKeyTimer = null;
  physicalCardKeyBuffer = '';
  physicalCardKeyTarget = null;
  physicalCardLastKeyAt = 0;
}
function flushPhysicalCardKeyBuffer() {
  const text = physicalCardKeyBuffer;
  const target = physicalCardKeyTarget;
  clearPhysicalCardKeyBuffer();
  if (triggerBufferedCombatShortcut(text, target)) return;
  insertPhysicalCardBufferFallback(text, target);
}
function triggerBufferedCombatShortcut(text, target) {
  if (physicalCardEditableTarget(target)) return false;
  if (String(text || '').toLocaleUpperCase('en') !== 'D') return false;
  return triggerCombatActionShortcutKey('D');
}
function schedulePhysicalCardBufferFlush() {
  clearTimeout(physicalCardKeyTimer);
  physicalCardKeyTimer = window.setTimeout(
    flushPhysicalCardKeyBuffer,
    PHYSICAL_CARD_BUFFER_TIMEOUT_MS,
  );
}
function normalizePhysicalCardScannerText(value) {
  let normalized = String(value || '').trim().toLocaleLowerCase('en');
  if (normalized.startsWith('dndbg>')) normalized = normalized.replaceAll('>', ':');
  if (normalized.startsWith(PHYSICAL_CARD_PREFIX)) normalized = normalized.replaceAll('?', '_');
  return normalized;
}
function physicalCardPayloadFromRecentKeys() {
  const normalized = normalizePhysicalCardScannerText(physicalCardRecentKeys);
  const match = normalized.match(PHYSICAL_CARD_PAYLOAD_PATTERN);
  physicalCardRecentKeys = '';
  physicalCardRecentKeyAt = 0;
  return match ? match[0] : '';
}
function consumePhysicalCardKey(event) {
  if (event.defaultPrevented || event.isComposing || event.repeat) return false;
  if (event.ctrlKey || event.metaKey || event.altKey) return false;
  const now = performance.now();
  if (
    physicalCardRecentKeys
    && now - physicalCardRecentKeyAt > PHYSICAL_CARD_RECENT_KEY_GAP_MS
  ) {
    physicalCardRecentKeys = '';
  }
  if (event.key.length === 1) {
    physicalCardRecentKeys += event.key;
    physicalCardRecentKeyAt = now;
  }
  if (event.key === 'Enter') {
    const recentPayload = physicalCardPayloadFromRecentKeys();
    if (recentPayload) {
      clearPhysicalCardKeyBuffer();
      event.preventDefault();
      event.stopImmediatePropagation();
      handlePhysicalCardScan(recentPayload);
      return true;
    }
  }
  if (
    physicalCardKeyBuffer
    && now - physicalCardLastKeyAt > PHYSICAL_CARD_MAX_KEY_GAP_MS
  ) {
    flushPhysicalCardKeyBuffer();
  }
  if (event.key === 'Enter' && physicalCardKeyBuffer) {
    const payload = normalizePhysicalCardScannerText(physicalCardKeyBuffer);
    const target = physicalCardKeyTarget;
    clearPhysicalCardKeyBuffer();
    if (/^dndbg:v[0-9]+:(?:action:[a-z0-9_]+:[a-z][a-z0-9_]*(?::[a-z][a-z0-9_]*)?|actor:[a-z][a-z0-9_]*)$/.test(payload)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      handlePhysicalCardScan(payload);
      return true;
    }
    insertPhysicalCardBufferFallback(payload, target);
    return false;
  }
  if (event.key.length !== 1) return false;
  const key = event.key;
  if (physicalCardKeyBuffer) {
    const candidate = normalizePhysicalCardScannerText(physicalCardKeyBuffer + key);
    const continuesCardPayload = (
      PHYSICAL_CARD_PREFIX.startsWith(candidate)
      || (
        candidate.startsWith(PHYSICAL_CARD_PREFIX)
        && /^[a-z0-9_:>]+$/.test(candidate)
      )
    );
    if (!continuesCardPayload) {
      const bufferedText = physicalCardKeyBuffer;
      const bufferedTarget = physicalCardKeyTarget;
      clearPhysicalCardKeyBuffer();
      if (!triggerBufferedCombatShortcut(bufferedText, bufferedTarget)) {
        insertPhysicalCardBufferFallback(bufferedText, bufferedTarget);
      }
      return false;
    }
  }
  if (!physicalCardKeyBuffer) {
    if (key.toLocaleLowerCase('en') !== PHYSICAL_CARD_PREFIX[0]) return false;
    physicalCardKeyTarget = event.target;
  }
  physicalCardKeyBuffer += key;
  physicalCardLastKeyAt = now;
  const normalized = normalizePhysicalCardScannerText(physicalCardKeyBuffer);
  const possiblePrefix = PHYSICAL_CARD_PREFIX.startsWith(normalized);
  const possiblePayload = (
    normalized.startsWith(PHYSICAL_CARD_PREFIX)
    && /^[a-z0-9_:>]+$/.test(normalized)
  );
  event.preventDefault();
  event.stopImmediatePropagation();
  if (!possiblePrefix && !possiblePayload) {
    flushPhysicalCardKeyBuffer();
    return true;
  }
  schedulePhysicalCardBufferFlush();
  return true;
}
document.addEventListener('keydown', consumePhysicalCardKey, {capture: true});
document.addEventListener('keydown', event => {
  if (event.defaultPrevented) return;
  const target = event.target;
  const combatMenu = state && state.combat ? state.combat.context_menu : null;
  const combatTurnMenu = state && state.combat ? state.combat.turn_action_menu : null;
  const typing = target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT');
  if (!typing && !combatMenu && triggerCombatActionShortcut(event)) {
    event.preventDefault();
    return;
  }
  if (!typing && combatMenu && (event.code === 'Numpad2' || event.code === 'Numpad8')) {
    moveCombatContextMenu(event.code === 'Numpad2' ? 1 : -1);
    event.preventDefault();
    return;
  }
  if (combatMenu && !typing && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
    moveCombatContextMenu(event.key === 'ArrowDown' ? 1 : -1);
    event.preventDefault();
    return;
  }
  if (!typing && /^Numpad[0-9]$/.test(event.code)) {
    const key = event.code.slice(-1);
    const choice = Array.from(document.querySelectorAll(`[data-numpad-key="${key}"]`))
      .find(element => !element.disabled && element.offsetParent !== null);
    if (choice) {
      choice.click();
      event.preventDefault();
      return;
    }
  }
  if (
    event.code === 'NumpadSubtract'
    && !typing
  ) {
    if (triggerSecondaryAction()) event.preventDefault();
    return;
  }
  if (event.code === 'NumpadEnter') {
    if (target && target.closest && target.closest('details.debug-panel')) return;
    if (triggerPrimaryAction()) event.preventDefault();
    return;
  }
  if (!typing && event.key.toLocaleLowerCase('pl') === 'i' && !event.ctrlKey && !event.metaKey && !event.altKey) {
    toggleSidePanel();
    event.preventDefault();
    return;
  }
  if (!typing && (event.key === 'Escape' || event.key === 'Backspace')) {
    if (sidePanelOpen) setSidePanelOpen(false);
    else if (!cancelCurrentCombatStep()) return;
    event.preventDefault();
    return;
  }
  if (event.key !== 'Enter') return;
  if (target && target.tagName === 'TEXTAREA' && event.shiftKey) return;
  if (target && target.closest && target.closest('details.debug-panel')) return;
  if (target && target.closest && target.closest('button, a, summary')) return;
  if (triggerPrimaryAction()) {
    event.preventDefault();
  }
});
document.addEventListener('visibilitychange', () => {
  if (document.hidden) stopBoardScanLoop();
  else scheduleAutomaticBoardScan();
});
document.addEventListener('focusin', event => {
  const target = event.target;
  if (
    target
    && target.closest
    && target.closest('#action-panel')
    && target.matches('input, textarea, select')
  ) {
    pauseBoardForScreenInput();
  }
});
document.addEventListener('focusout', event => {
  const target = event.target;
  if (
    target
    && target.closest
    && target.closest('#action-panel')
    && target.matches('input, textarea, select')
  ) {
    window.setTimeout(scheduleAutomaticBoardScan, 0);
  }
});
const actionInput = document.getElementById('action');
if (actionInput) {
  actionInput.addEventListener('input', handleSlashCommandInput);
  actionInput.addEventListener('focus', renderSlashCommandMenu);
  actionInput.addEventListener('keydown', handleSlashCommandKeydown);
  actionInput.addEventListener('blur', () => window.setTimeout(closeSlashCommandMenu, 100));
}
setSidePanelOpen(sidePanelOpen);
setSidePanelTab(sidePanelTab);
loadState();

function submitVolleyRoll() {
  return api('/api/combat/area-spell/volley-roll', {natural_roll: Number(document.getElementById('volley-roll').value), natural_roll_2: document.getElementById('volley-roll-2') ? Number(document.getElementById('volley-roll-2').value) : null}, 'Rozstrzygam wspólny atak…');
}
