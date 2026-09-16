// The browser owns the existing one-die wizard; the server owns legal actions.
// Both input paths use the same validators and confirmation dispatcher.
let boardPanelSyncPromise = null;
let boardPanelWizardSequence = 0;

function rollPanelSlots(wizard) {
  if (wizard.review) return wizard.steps.length ? [28, 29] : [28];
  return [26, 27, 28, ...(wizard.index > 0 ? [29] : [])];
}

function desiredBoardPanel() {
  if (state?.exploration_mana?.active && !keyboardRollWizard) return null;
  if (state?.training_arena?.tutorial?.notice) return null;
  if (state?.combat?.shared_mana?.pool_view?.choices?.length) return null;
  if (state?.combat?.shared_mana?.command?.stage) return null;
  if (!state?.board_selection?.panel_enabled || keyboardRollWizard?.initiative) return null;
  if (state.combat?.shared_mana?.declaration?.stage === 'payment'
      || state.combat?.shared_mana?.declaration?.target_selection) return null;
  const manaPanel = sharedManaPanel();
  if (manaPanel) return manaPanel;
  const wizard = keyboardRollWizard;
  if (wizard) {
    wizard.panelId ??= ++boardPanelWizardSequence;
    return {context: `dice:${wizard.panelId}:${wizard.index}:${Boolean(wizard.review)}`,
      slots: rollPanelSlots(wizard), exclusive: true};
  }
  const menu = state.combat?.turn_action_menu;
  if (menu) return null;
  const slots = state.combat?.shield_bash?.stage === 'result' ? [28] : [28, 29];
  const legal = state.board_selection.legal_positions || [];
  if (!state.board_selection.panel_context && slots.every(slot =>
    legal.some(pos => pos[0] === 19 && pos[1] === 29 - slot))) return null;
  return {context: `decision:${state.board_selection.revision}`, slots, exclusive: false};
}

function syncBrowserBoardPanel() {
  if (boardPanelSyncPromise) return true;
  if (busy) return false;
  const desired = desiredBoardPanel();
  if (!desired) return false;
  const current = state.board_selection.panel_context;
  if (desired.context === current || (!keyboardRollWizard && current?.startsWith('decision:'))) return false;
  boardPanelSyncPromise = (async () => {
    await stopBoardScanLoop();
    if (busy) return;
    const res = await fetch('/api/board/panel', {method: 'POST',
      headers: {'Content-Type': 'application/json'}, body: JSON.stringify({...desired, revision: state.board_selection.revision})});
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Nie udało się włączyć panelu.');
    state.board_selection = data.board_selection;
  })().catch(error => {
    boardScanError = error.message;
    boardInputPhase = 'error';
  }).finally(() => {
    boardPanelSyncPromise = null;
    if (boardInputPhase !== 'error') scheduleAutomaticBoardScan();
    else updateBoardInputPresentation();
  });
  return true;
}

function handleBoardPanelEvent(data) {
  const event = data.panel_event;
  const expected = state?.board_selection?.panel_context || null;
  if (event.context !== expected) return;
  state.board_selection = data.board_selection;
  if (event.context?.startsWith('mana:')) {
    if (event.slot === 28) sharedManaPrimary();
    else if (event.slot === 29) sharedManaCommand('cancel');
    else sharedManaDelta(event.slot === 27 ? 1 : -1);
    return;
  }
  if (event.slot === 26 || event.slot === 27) changeRollPanelValue(event.slot === 27 ? 1 : -1);
  else if (event.slot === 28) triggerPrimaryAction();
  else if (event.slot === 29) {
    if (keyboardRollWizard) previousKeyboardRollStep();
    else triggerSecondaryAction();
  }
}

function changeRollPanelValue(delta) {
  const wizard = keyboardRollWizard;
  if (!wizard || wizard.review || busy) return false;
  if (wizard.initiative) return sendInitiativePanelCommand(delta > 0 ? 'plus' : 'minus');
  const step = wizard.steps[wizard.index];
  const entry = document.getElementById('keyboard-roll-wizard-input');
  const value = Number(entry?.value || step.raw);
  if (!Number.isInteger(value)) return false;
  step.raw = Math.max(step.min ?? 1, Math.min(step.max ?? Infinity, value + delta));
  renderKeyboardRollWizard();
  scheduleAutomaticBoardScan();
  return true;
}

function rollPanelControlsHtml(wizard) {
  if (wizard.initiative) return initiativePanelControlsHtml();
  if (wizard.review) return '<p class="keyboard-roll-wizard-help">✓ Zatwierdź cały rzut · ↩ Popraw wynik</p>';
  const step = wizard.steps[wizard.index];
  return `<div class="roll-panel-controls">
    <button type="button" class="panel-minus" onclick="changeRollPanelValue(-1)" ${step.raw <= (step.min ?? 1) ? 'disabled' : ''} aria-label="Zmniejsz wynik">−</button>
    <button type="button" class="panel-plus" onclick="changeRollPanelValue(1)" ${Number.isFinite(step.max) && step.raw >= step.max ? 'disabled' : ''} aria-label="Zwiększ wynik">+</button>
    <button type="button" class="panel-accept" onclick="confirmKeyboardRollStep()">✓ Zatwierdź kość</button>
  </div><p class="keyboard-roll-wizard-help">− czerwony · + zielony · ✓ niebieski${wizard.index ? ' · ↩ popraw poprzednią kość' : ''}</p>`;
}
