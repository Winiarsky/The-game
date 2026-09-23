/* Session information uses board function keys and preserves the current decision. */
const SessionNavigation = (() => {
  let view = '', index = 0, page = 0, checkpoint = null, generation = 0, retryTimer = null;
  const t = (key, params = {}) => sessionUiText(`common.${key}`, params);
  const dialog = () => document.getElementById('session-navigation');
  const context = () => `session-${view === 'menu' || view === 'checkpoints' || view === 'confirm' ? 'menu' : view === 'help' ? 'help' : 'journal'}:${generation}`;
  function panel() { return view && dialog()?.open ? {context:context(), slots:[26,27,28,29], exclusive:true} : null; }
  function choices() { return [...(dialog()?.querySelectorAll('[data-session-choice]') || [])]; }
  function highlight() {
    const all = choices();
    index = all.length ? (index + all.length) % all.length : 0;
    all.forEach((item, i) => item.classList.toggle('session-focused', i === index));
    all[index]?.scrollIntoView({block:'nearest'});
  }
  function choice(action, label) { return `<button class="secondary" data-session-choice="${esc(action)}">${esc(label)}</button>`; }
  function content() {
    if (view === 'menu') return ['resume','journal','rules','party','checkpoints','main_menu'].map(key => choice(key, t(key))).join('');
    if (view === 'checkpoints') {
      if (state.combat || state.exploration_mana?.active || state.mission?.rolling) return `<p>${esc(t('checkpoint_unavailable'))}</p>`;
      return state.mission.checkpoints.map(item => choice(`checkpoint:${item.id}`, item.label)).join('') || `<p>${esc(t('no_checkpoints'))}</p>`;
    }
    if (view === 'confirm') return `<p>${esc(t('checkpoint_warning', {name:checkpoint.label}))}</p>${choice('apply_checkpoint',t('confirm'))}${choice('resume',t('back'))}`;
    if (view === 'help') return (state.player_aid || []).map(item => `<section><h3>${esc(item.title)}</h3><p>${esc(item.lead || '')}</p>${(item.sections || []).map(section => `<h4>${esc(section.title)}</h4>${(section.paragraphs || []).map(text => `<p>${esc(text)}</p>`).join('')}${section.steps ? `<ol>${section.steps.map(text => `<li>${esc(text)}</li>`).join('')}</ol>` : ''}${section.table ? `<table>${section.table.map(row => `<tr>${row.map(cell => `<td>${esc(cell)}</td>`).join('')}</tr>`).join('')}</table>` : ''}</section>`).join('')}</section>`).join('');
    if (view === 'party') return (state.actors || []).map(actor => `<section><h3>${esc(actor.name)}</h3>${actorStatesHtml(actor)}</section>`).join('');
    const entries = [...(state.mission?.ledger || []).map(item => `${item.name}${item.amount ? ` · ${item.amount}` : ''}`), ...(state.mission?.recovery?.open_threads || []), ...(state.messages || []).slice(-20).map(item => item.content || item.text || item.message || '').filter(Boolean)];
    return entries.length ? entries.map(text => `<p>${esc(text)}</p>`).join('') : `<p>${esc(t('empty_journal'))}</p>`;
  }
  function renderDialog() {
    const titles = {menu:'menu',journal:'journal',help:'rules',party:'party',checkpoints:'checkpoints',confirm:'confirm'};
    dialog().innerHTML = `<header><h2>${esc(t(titles[view]))}</h2><button aria-label="${esc(t('back'))}">↩</button></header><div class="session-navigation-content">${content()}</div><footer></footer>`;
    // The header back control is always available through decline, not part of the choice cursor.
    dialog().querySelector('header button').removeAttribute('data-session-choice');
    dialog().querySelector('footer').textContent=t(choices().length ? 'controls' : 'reading_controls');
    dialog().querySelector('header button').onclick = back;
    highlight();
  }
  function open(next = 'menu') {
    if (!state?.mission || busy || keyboardRollWizard) return false;
    if (!dialog()) {
      const el = document.createElement('dialog');el.id='session-navigation';el.setAttribute('aria-label',t('menu'));document.body.append(el);
      el.addEventListener('cancel', event => {event.preventDefault();back();});
      el.addEventListener('click', event => {const button=event.target.closest('[data-session-choice]');if(button)activate(button.dataset.sessionChoice);});
    }
    if (!view && document.querySelector('dialog[open]')) return false;
    view=next;index=0;page=0;generation+=1;renderDialog();
    if (!dialog().open) dialog().showModal();
    scheduleAutomaticBoardScan();return true;
  }
  function close() {
    const old=context();view='';dialog()?.close();releaseBrowserBoardPanel(old);
  }
  function back() { if (view==='menu') close(); else open('menu'); }
  function activate(action) {
    if (action==='resume') return close();
    if (action==='back') return back();
    if (action==='main_menu') {close();window.location.assign('/');return;}
    if (action==='rules') return open('help');
    if (action.startsWith('checkpoint:')) {checkpoint=state.mission.checkpoints.find(item=>item.id===action.slice(11));if(checkpoint)open('confirm');return;}
    if (action==='apply_checkpoint') {const id=checkpoint.id;close();missionAction('checkpoint',{id});return;}
    open(action);
  }
  function handleSlot(slot) {
    if (!panel()) return false;
    if (slot===29) back();
    else if (slot===28) {const selected=choices()[index];if(selected)activate(selected.dataset.sessionChoice);else back();}
    else if (slot===26 || slot===27) {
      if (choices().length) {index+=slot===26?1:-1;highlight();}
      else dialog().querySelector('.session-navigation-content').scrollBy({top:slot===26?180:-180});
    } else return false;
    return true;
  }
  function handleEvent(event) {
    if (event.context?.startsWith('session-open-menu:')) return event.context===`session-open-menu:${state.mission?.revision}` ? open() : false;
    return event.context===panel()?.context ? handleSlot(event.slot) : false;
  }
  function afterRender() {
    if (!state?.mission) return;
    const menu=document.querySelector('.side-panel-toggle');
    if (menu) {menu.onclick=()=>open();menu.title=t('menu');}
    if (retryTimer) clearTimeout(retryTimer);
    const backend=state.board?.backend && state.board.backend!=='none' ? state.board.backend : state.board?.configured_backend;
    if (backend && backend!=='none' && !state.board.connected && !busy && !boardFallbackEnabled)
      retryTimer=setTimeout(()=>{if(!busy)retryBoardConnection();},2000);
  }
  return {open,close,panel,handleSlot,handleEvent,afterRender};
})();
