/* Input transport only. The server owns legality, previews and resolution. */
const KeyboardInput = (() => {
  let context = '', generation = 0, inFlight = false, pendingCursor = null;
  let desiredCursor = null, pendingBack = '', lastNavigationAt = 0, message = '', actionList = false;
  let tabNavigation = false, explicitChoice = null;
  let menuFocusScheduled = false, menuNavigationContext = '';
  const menuMemory = new Map();
  const held = new Set(), blocked = new Set();
  const enabled = () => typeof state !== 'undefined' && state?.input?.mode === 'keyboard';
  const contract = () => state?.input || {};
  const visible = element => Boolean(element && !element.disabled && !element.closest('[hidden]')
    && element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden');
  const modal = () => [...document.querySelectorAll('dialog[open]')].at(-1);
  const typing = target => Boolean(target?.closest('input,textarea,select,[contenteditable]:not([contenteditable="false"])'));
  const escape = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
  const sideOpen = () => typeof sidePanelOpen !== 'undefined' && sidePanelOpen;

  function currentContext() {
    return `${contract().context || ''}:${modal()?.id || ''}:${sideOpen() ? 'side' : ''}`;
  }
  function invalidate() {
    generation += 1;
    pendingCursor = desiredCursor = null;
    pendingBack = '';
    tabNavigation = false;
    explicitChoice = null;
    menuNavigationContext = '';
    for (const key of held) blocked.add(key);
    actionList = false;
    message = '';
  }
  function refresh() {
    document.body.classList.toggle('keyboard-control-mode', enabled());
    const setupMode = Boolean(enabled() && state.encounter_setup
      && !state.combat && !state.encounter_initiative
      && (state.encounter_setup.status !== 'completed' || !state.encounter_stealth || state.encounter_stealth.completed)
      && !state.training_arena?.tutorial?.notice
      && state.training_arena?.tutorial?.phase !== 'introduction');
    document.body.classList.toggle('keyboard-setup-active', setupMode);
    const bar = document.getElementById('keyboard-control-bar');
    if (!bar) return;
    bar.hidden = !enabled();
    if (!enabled()) return;
    const nextContext = currentContext();
    if (nextContext !== context) { invalidate(); context = nextContext; }
    const input = contract(), cursor = desiredCursor || input.cursor;
    const point = cursor ? `Pole (${cursor[0]}, ${cursor[1]})` : '';
    const cost = input.valid !== false && input.preview?.path?.length && Number.isFinite(input.preview.cost)
      ? `Koszt ruchu: ${input.preview.cost}` : '';
    const notice = message || input.notice || (setupMode
      ? input.kind === 'map' ? 'Strzałki wybierają pole · Enter wybiera i potwierdza ustawienie · Esc cofa.' : 'Enter przechodzi dalej · Esc wraca do poprzedniego elementu.'
      : input.kind === 'menu'
      ? 'Strzałki wybierają opcję, Enter otwiera. PageUp/PageDown przewija opis.'
      : input.prompt || 'Wybierz dostępną opcję.');
    bar.querySelector('[data-keyboard-status]').textContent = [point, cost, notice].filter(Boolean).join(' · ');
    bar.querySelector('[data-keyboard-multiple]').hidden = input.selection_mode !== 'multiple';
    bar.querySelector('[data-keyboard-sync]').hidden = !inFlight && !pendingCursor;
    document.body.style.setProperty('--keyboard-control-height', `${bar.getBoundingClientRect().height}px`);
    const selector = document.getElementById('input-mode');
    if (selector && document.activeElement !== selector) selector.value = input.mode;
    scheduleMenuFocus();
  }
  function status(text) { message = text; refresh(); }

  async function send(command, extra = {}) {
    if (!enabled() || inFlight || busy) return false;
    const input = contract(), version = generation;
    inFlight = true;
    refresh();
    try {
      const result = await api('/api/input/command', {
        command, ...extra, context:input.context, revision:input.revision,
      }, '', {quiet:command === 'cursor' || command === 'adjust'});
      if (version === generation && result?.ok) message = '';
      return Boolean(result?.ok);
    } finally {
      inFlight = false;
      refresh();
      if (pendingBack && pendingBack === contract().context) {
        pendingBack = '';
        send('back');
      }
      if (command !== 'cursor' && pendingCursor) flushCursor();
    }
  }
  async function flushCursor() {
    if (!pendingCursor || inFlight || busy || !enabled()) return;
    const position = pendingCursor;
    pendingCursor = null;
    const version = generation;
    const ok = await send('cursor', {position});
    if (version !== generation) return;
    if (!ok) pendingCursor = desiredCursor = null;
    else if (!pendingCursor && desiredCursor?.[0] === position[0] && desiredCursor?.[1] === position[1]) desiredCursor = null;
    refresh();
    if (pendingCursor) flushCursor();
  }
  function navigateMap(dx, dy) {
    const input = contract();
    if (input.kind !== 'map') return false;
    explicitChoice = null;
    if (nativeChoice()) document.activeElement.blur();
    if (busy && !inFlight) return true;
    const origin = desiredCursor || input.cursor || input.origin || input.fields?.[0];
    if (!origin) { status('Nie ma teraz pola do wskazania.'); return true; }
    const bounds = input.bounds || {};
    const cols = Number(bounds.cols || input.cols || 19), rows = Number(bounds.rows || input.rows || 30);
    const position = [Math.max(0, Math.min(cols - 1, origin[0] + dx)),
      Math.max(0, Math.min(rows - 1, origin[1] + dy))];
    if (position[0] === 19) position[0] = 18;
    if (position[0] === origin[0] && position[1] === origin[1]) return true;
    desiredCursor = pendingCursor = position;
    message = '';
    refresh();
    flushCursor();
    return true;
  }

  function menuButtons() {
    const open = modal();
    if (open) return [...open.querySelectorAll('button,a[href],summary,input[type="checkbox"]')].filter(visible);
    if (sideOpen()) return [...document.querySelectorAll('#side-panel button,#side-panel a[href],#side-panel summary')].filter(visible);
    const selectors = actionList
      ? '.rc-powers button,.rc-basic-actions button,.rc-actions button'
      : '#mission-panel button,#training-arena-panel button,#flow-panel button,#flow-panel a[href],'
        + '#encounter button,#interaction-goals button,#point-options button,#travel-options button,'
        + '#pending-panel button,#result-panel button,#roll-panel button';
    return [...document.querySelectorAll(selectors)].filter(element => visible(element)
      && !element.matches('[data-primary-scan="true"],[data-rc-scan-retry]')
      && !element.closest('.mission-toolbar,.mission-scroll-controls'));
  }
  function menuKey() { return `${currentContext()}:${actionList ? 'actions' : 'menu'}`; }
  function choiceKey(element) {
    return element.dataset.keyboardChoice || element.dataset.equipmentSlot
      || (element.dataset.rcSlot ? `combat:${element.dataset.rcSlot}` : '')
      || element.getAttribute('onclick') || element.id || element.getAttribute('href')
      || element.textContent.trim();
  }
  function rememberChoice(element) {
    if (!menuButtons().includes(element)) return;
    menuMemory.set(menuKey(), choiceKey(element));
    if (menuMemory.size > 32) menuMemory.delete(menuMemory.keys().next().value);
  }
  function rememberedChoice(choices) {
    const primary = automaticSetupPrimary(choices);
    if (primary) return primary;
    const remembered = menuMemory.get(menuKey());
    return choices.find(element => choiceKey(element) === remembered)
      || (state.encounter_initiative?.panel?.review
        ? choices.find(element => element.matches('.panel-accept,[data-mana-primary]')) : null)
      || choices.find(element => element.matches('[data-keyboard-primary="true"]')) || choices[0];
  }
  function automaticSetupPrimary(choices) {
    if (contract().kind !== 'menu' || state.combat || !state.encounter_setup
        || menuNavigationContext === contract().context
        || (explicitChoice?.context === contract().context && nativeChoice())) return null;
    return choices.find(element => element.matches('[data-keyboard-primary="true"]')) || null;
  }
  function clearChoiceHighlight() {
    document.querySelectorAll('.keyboard-choice-focused').forEach(item => {
      item.classList.remove('keyboard-choice-focused');
      item.removeAttribute('aria-current');
    });
  }
  function restoreMenuFocus() {
    if (!enabled() || busy || inFlight || pendingCursor || contract().kind !== 'menu'
        || keyboardRollWizard || modal() || sideOpen() || typing(document.activeElement)
        || tabNavigation || (explicitChoice?.element === document.activeElement && nativeChoice())) return;
    // Combat result/dice/turn confirmations keep their existing primary action.
    if (state.combat && !state.mission?.active && !state.exploration_mana?.active && !actionList) return;
    const choices = menuButtons();
    if (!choices.length) return;
    const current = automaticSetupPrimary(choices)
      || (choices.includes(document.activeElement) ? document.activeElement : rememberedChoice(choices));
    if (current) focusChoice(current);
  }
  function scheduleMenuFocus() {
    if (menuFocusScheduled) return;
    menuFocusScheduled = true;
    // Run after the existing render focus tasks, with the current DOM/context.
    requestAnimationFrame(() => requestAnimationFrame(() => {
      menuFocusScheduled = false;
      restoreMenuFocus();
    }));
  }
  function focusChoice(element) {
    clearChoiceHighlight();
    if (!element) return false;
    element.classList.add('keyboard-choice-focused');
    element.setAttribute('aria-current', 'true');
    rememberChoice(element);
    element.focus({preventScroll:true});
    element.scrollIntoView({block:'nearest'});
    return true;
  }
  function navigateMenu(delta) {
    if (modal()?.id === 'session-navigation') return handleReadOnlyPanelSlot(delta > 0 ? 26 : 27);
    const choices = menuButtons();
    if (!choices.length) {
      const container = modal()?.querySelector('.session-navigation-content')
        || document.querySelector('.mission-narrative-text,.confrontation-scroll');
      container?.scrollBy({top:delta * 150});
      return true;
    }
    const index = choices.indexOf(choices.includes(document.activeElement) ? document.activeElement : rememberedChoice(choices));
    menuNavigationContext = contract().context;
    return focusChoice(choices[Math.max(0, Math.min(choices.length - 1, index + delta))]);
  }
  function nativeChoice(allowHeader = false) {
    const focused = document.activeElement;
    const deliberateHeader = allowHeader || (explicitChoice?.element === focused
      && explicitChoice.context === contract().context);
    return visible(focused) && focused.matches('button,a[href],summary,input[type="checkbox"]')
      && !focused.closest('#keyboard-control-bar')
      && (!focused.closest('.app-shell-header') || deliberateHeader);
  }
  function activateMenu() {
    if (modal()?.id === 'session-navigation') return handleReadOnlyPanelSlot(28);
    if (nativeChoice()) { document.activeElement.click(); return true; }
    const choices = menuButtons();
    if (choices.length) {
      const selected = rememberedChoice(choices);
      focusChoice(selected);
      selected.click();
      return true;
    }
    return false;
  }
  function closePanel() {
    const open = modal();
    if (open) {
      if (['session-navigation','confrontation-detail'].includes(open.id)) return handleReadOnlyPanelSlot(29);
      const close = [...open.querySelectorAll('button')].find(button => /zamknij|anuluj|wróć/i.test(button.getAttribute('aria-label') || button.textContent));
      if (close) close.click(); else open.close();
      refresh();
      return true;
    }
    if (sideOpen()) { setSidePanelOpen(false); refresh(); return true; }
    return false;
  }
  function openInfo(tab) {
    if (busy || inFlight || keyboardRollWizard || modal()) return false;
    if (sideOpen() && sidePanelTab === tab) setSidePanelOpen(false);
    else { setSidePanelTab(tab); setSidePanelOpen(true); }
    refresh();
    return true;
  }
  function help() {
    if (busy || inFlight || keyboardRollWizard || modal()) return false;
    if (typeof SessionNavigation !== 'undefined' && SessionNavigation.open('help')) {refresh(); return true;}
    const previous = document.getElementById('keyboard-shortcuts');
    if (previous) previous.remove();
    const dialog = document.createElement('dialog');
    dialog.id = 'keyboard-shortcuts';
    dialog.setAttribute('aria-label', 'Sterowanie klawiaturą');
    dialog.innerHTML = '<h2>Sterowanie klawiaturą</h2><p>Strzałki wybierają opcję lub pole. Enter zatwierdza podgląd; Esc cofa.</p>'
      + '<p>M — ruch · A — atak · I — ekwipunek · R — runy i akcje · C — postać · J — dziennik · H — pomoc · 0 — koniec tury.</p>'
      + '<p>Zmiana celu pokazuje podgląd na LED-ach i nie wydaje zasobów. Spacja zaznacza cele wielokrotne; +/− zmienia wynik kości. PageUp/PageDown przewija tekst.</p><button autofocus>Zamknij</button>';
    dialog.querySelector('button').onclick = () => {dialog.close(); refresh();};
    dialog.addEventListener('close', () => {dialog.remove(); refresh();});
    document.body.append(dialog);
    dialog.showModal();
    refresh();
    return true;
  }
  function journal() {
    if (busy || inFlight || keyboardRollWizard || modal()) return false;
    if (typeof SessionNavigation !== 'undefined' && SessionNavigation.open('journal')) {refresh(); return true;}
    const dialog = document.createElement('dialog');
    dialog.id = 'keyboard-journal';
    dialog.setAttribute('aria-label', 'Dziennik');
    dialog.innerHTML = `<h2>Dziennik</h2><div class="keyboard-journal-entries">${(state.messages || []).map(item =>
      `<article><b>${escape(item.title || '')}</b><p>${escape(item.body || item.content || '')}</p></article>`).join('') || '<p>Brak wpisów.</p>'}</div><button autofocus>Zamknij</button>`;
    dialog.querySelector('button').onclick = () => dialog.close();
    dialog.addEventListener('close', () => {dialog.remove(); refresh();});
    document.body.append(dialog); dialog.showModal(); refresh(); return true;
  }
  function scrollReading(direction) {
    const root = modal() || (sideOpen() ? document.getElementById('side-panel') : document);
    const equipmentSelector = '.equipment-picker,.equipment-stash-preview,.equipment-body-list,.equipment-pack-grid';
    const activeEquipment = root === document ? document.activeElement?.closest(equipmentSelector) : null;
    const equipmentArea = visible(activeEquipment) ? activeEquipment
      : root === document ? [...root.querySelectorAll(equipmentSelector)].find(visible) : null;
    const setupArea = root === document ? [...root.querySelectorAll('.keyboard-setup-description,.keyboard-setup-active .mission-tile-instruction .mission-prose')].find(visible) : null;
    const area = equipmentArea || setupArea || [...root.querySelectorAll('.session-navigation-content,.keyboard-journal-entries,.confrontation-detail-body,.confrontation-controls,.mission-narrative-text,.mission-tile-instruction,.side-panel-content')]
      .find(visible);
    if (area) area.scrollBy({top:direction * Math.max(120, area.clientHeight * .7)});
    else window.scrollBy({top:direction * innerHeight * .7});
    return true;
  }
  function showActions() {
    if (busy || inFlight || keyboardRollWizard || modal()) return false;
    if (state.combat?.resonance && state.combat.resonance.phase !== 'idle') {
      status('Najpierw zakończ albo cofnij bieżący podgląd.');
      return true;
    }
    if (sideOpen()) setSidePanelOpen(false);
    actionList = true;
    const choices = menuButtons();
    if (!choices.length) { actionList = false; status('Brak menu run w bieżącym kroku.'); return false; }
    focusChoice(choices.find(button => button.closest('.rc-powers')) || choices[0]);
    status('Runy i akcje: strzałki wybierają, Enter otwiera podgląd.');
    return true;
  }
  function dispatch(command, extra = {}) {
    if (!enabled()) return false;
    if (command === 'navigate' && contract().kind === 'dice' && !modal() && !sideOpen()) {
      if (extra.dy) dispatch('adjust', {delta:extra.dy < 0 ? 1 : -1});
      return true;
    }
    if (command === 'navigate') return contract().kind === 'map' && !modal() && !sideOpen() && !actionList
      ? navigateMap(extra.dx || 0, extra.dy || 0) : navigateMenu(extra.dy || extra.dx || 1);
    if (command === 'inventory') return openInfo('inventory');
    if (command === 'character') return openInfo('party');
    if (command === 'journal') return journal();
    if (command === 'help') return help();
    if (command === 'actions') return showActions();
    if (command === 'back') {
      pendingCursor = desiredCursor = null;
      if (inFlight) {pendingBack = contract().context; status('Cofam podgląd…'); return true;}
    }
    if (command === 'back' && closePanel()) return true;
    if (command === 'back' && actionList) {
      actionList = false;
      document.activeElement?.blur();
      clearChoiceHighlight();
      status('Menu run zamknięte.');
      return true;
    }
    if (command === 'accept' && (pendingCursor || inFlight || busy)) {
      status('Czekam na aktualny podgląd.');
      return true;
    }
    const localMenu = modal() || sideOpen() || actionList;
    if (command === 'accept' && !localMenu) {
      const primary = automaticSetupPrimary(menuButtons());
      if (primary) {focusChoice(primary); primary.click(); return true;}
    }
    if (command === 'accept' && !localMenu && contract().kind === 'map'
        && explicitChoice?.element === document.activeElement
        && explicitChoice.context === contract().context && nativeChoice()) {
      const element = explicitChoice.element;
      explicitChoice = null;
      element.click();
      return true;
    }
    if (command === 'accept' && !localMenu && contract().kind !== 'map' && nativeChoice()) return activateMenu();
    const serverPrimary = !localMenu && state.combat?.resonance && contract().can_accept;
    if (command === 'accept' && (localMenu || (contract().kind !== 'map' && contract().kind !== 'dice' && !serverPrimary))) {
      if (activateMenu()) return true;
    }
    if (command === 'back' && state.combat?.resonance && contract().can_back === false) {
      status('Tego kroku nie można teraz cofnąć.');
      return true;
    }
    if (pendingCursor || inFlight || busy) { status('Czekam na aktualny podgląd.'); return true; }
    if (command === 'accept' && contract().kind === 'map' && contract().can_accept === false) {
      status(contract().notice || 'Wskaż dozwolone pole przed zatwierdzeniem.');
      return true;
    }
    if (command === 'accept') actionList = false;
    if (command === 'select') extra = {position:contract().cursor, ...extra};
    send(command, extra);
    return true;
  }
  function handleKeydown(event) {
    if (!enabled() || event.defaultPrevented || event.isComposing || event.ctrlKey || event.metaKey || event.altKey) return;
    if (event.key === 'Tab') {tabNavigation = true; return;}
    if (event.shiftKey && event.key !== '+') return;
    const wizard = typeof keyboardRollWizard !== 'undefined' && keyboardRollWizard;
    if (wizard && ['Enter','Escape','ArrowUp','ArrowDown','+','-'].includes(event.key)) {
      event.preventDefault(); event.stopImmediatePropagation();
      if (!event.repeat && !busy) handleKeyboardRollWizardKeydown(event);
      return;
    }
    if (wizard) return;
    if (typing(event.target)) return;
    const key = event.key.toLowerCase();
    const directions = {arrowup:[0,-1], arrowdown:[0,1], arrowleft:[-1,0], arrowright:[1,0]};
    const shortcuts = {m:'move', a:'attack', '0':'end'};
    const panels = {i:'inventory', c:'character', j:'journal', h:'help', r:'actions'};
    if (!(key in directions) && !(key in shortcuts) && !(key in panels)
        && !['enter','escape','backspace','+','=','-',' ','pageup','pagedown'].includes(key)) return;
    event.preventDefault(); event.stopImmediatePropagation();
    held.add(event.code || key);
    if (blocked.has(event.code || key)) return;
    if (event.repeat && !(key in directions)) return;
    if (event.repeat && performance.now() - lastNavigationAt < 120) return;
    if (key in directions) {
      lastNavigationAt = performance.now();
      const [dx,dy] = directions[key]; dispatch('navigate', {dx,dy}); return;
    }
    if (key === 'pageup' || key === 'pagedown') {scrollReading(key === 'pageup' ? -1 : 1); return;}
    if (key === 'escape' || key === 'backspace') { dispatch('back'); return; }
    if (key === 'enter') { dispatch('accept'); return; }
    if (key === ' ') {
      if (!modal() && !sideOpen() && contract().kind === 'map' && contract().selection_mode === 'multiple') dispatch('select');
      return;
    }
    if (modal() || sideOpen()) {
      if (key === 'i' && sideOpen()) dispatch('inventory');
      return;
    }
    if (key in panels) { dispatch(panels[key]); return; }
    if (key in shortcuts) { dispatch('shortcut', {id:shortcuts[key]}); return; }
    dispatch('adjust', {delta:key === '-' ? -1 : 1});
  }
  document.addEventListener('keydown', handleKeydown, {capture:true});
  document.addEventListener('focusin', event => {
    if (!enabled()) return;
    rememberChoice(event.target);
    if (!tabNavigation) return;
    tabNavigation = false;
    explicitChoice = nativeChoice(true) ? {element:event.target, context:contract().context} : null;
  }, {capture:true});
  document.addEventListener('keyup', event => {held.delete(event.code || event.key.toLowerCase()); blocked.delete(event.code || event.key.toLowerCase());}, {capture:true});
  window.addEventListener('blur', () => {invalidate(); held.clear();});
  document.addEventListener('visibilitychange', () => {if (document.hidden) {invalidate(); held.clear();}});
  return {enabled, refresh, dispatch, invalidate};
})();
