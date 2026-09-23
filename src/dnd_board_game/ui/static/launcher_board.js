/* One document owns a rune mask. Page changes cannot reuse an old scan. */
(() => {
  const controls = document.querySelector('[data-launcher-token]');
  if (!controls) return;
  const token = controls.dataset.launcherToken;
  const status = controls.querySelector('[data-board-status]');
  const retry = controls.querySelector('button');
  let stopped = false, syncing = false, scanning = false, scheduled = null;
  let selection = null, signature = '', epoch = 0, focused = null;

  const visible = element => element && !element.closest('[hidden]') && element.getClientRects().length > 0;
  function choices() {
    const selectedCount = document.querySelectorAll('input[name="character_ids"]:checked').length;
    return [...document.querySelectorAll('[data-board-rune]')].filter(element => {
      const checkbox = element.querySelector('input[type="checkbox"]');
      return visible(element) && !element.disabled && element.getAttribute('aria-disabled') !== 'true'
        && !(checkbox && !checkbox.checked && selectedCount >= 6);
    });
  }
  const back = () => [...document.querySelectorAll('[data-board-back]')].find(visible);
  function desired() {
    const entries = choices();
    if (!entries.some(e => Number(e.dataset.boardRune) === focused)) focused = entries.length ? Number(entries[0].dataset.boardRune) : null;
    entries.forEach(e => e.classList.toggle('board-focused', Number(e.dataset.boardRune) === focused));
    return {token, controls: entries.length ? [26,27,28] : [], focused, slots: entries.map(e => Number(e.dataset.boardRune)),
      selected: entries.filter(e => e.querySelector('input:checked')).map(e => Number(e.dataset.boardRune)),
      back: Boolean(back())};
  }
  function report(message, failed = false) {
    if (status.textContent !== message) status.textContent = message;
    retry.hidden = !failed;
  }
  async function post(path, body, keepalive = false) {
    const response = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body), keepalive});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || sessionUiText('navigation.connect_error'));
    return data;
  }
  function stop() {
    if (stopped) return;
    stopped = true;
    ++epoch;
    clearTimeout(scheduled);
    post('/api/board/navigation/release', {token}, true).catch(() => {});
  }
  function queueSync() {
    clearTimeout(scheduled);
    if (!stopped) scheduled = setTimeout(sync, 0);
  }
  async function sync() {
    if (stopped || syncing) return;
    const contract = desired(), key = JSON.stringify(contract);
    if (key === signature) return;
    syncing = true;
    const version = ++epoch;
    try {
      const data = await post('/api/board/navigation', contract);
      if (stopped || version !== epoch) return;
      signature = key;
      selection = data.board_selection;
      if (!selection.connected) throw new Error(sessionUiText('navigation.disconnected'));
      report(sessionUiText('navigation.board_hint') + (contract.back ? ' · ' + sessionUiText('navigation.back_hint') : ''));
    } catch (error) {
      if (!stopped) {signature = key; selection = null; report(error.message, true);
        setTimeout(() => {if (!stopped && !selection) {signature='';queueSync();}}, 2000);}
    } finally {
      syncing = false;
      if (!stopped) {
        if (JSON.stringify(desired()) !== signature) queueSync();
        else read();
      }
    }
  }
  async function read() {
    if (stopped || syncing || scanning || !selection?.auto_arm) return;
    scanning = true;
    const version = epoch, revision = selection.revision;
    try {
      const data = await post('/api/board/scan', {revision, automatic:true});
      if (stopped || version !== epoch) return;
      const event = data.navigation_event;
      if (event?.token === token) {
        selection = null;
        const entries = choices();
        if (event.slot === 26 || event.slot === 27) {
          const index = Math.max(0, entries.findIndex(e => Number(e.dataset.boardRune) === focused));
          const next = entries[(index + (event.slot === 26 ? 1 : -1) + entries.length) % entries.length];
          if (next) {focused = Number(next.dataset.boardRune);next.scrollIntoView({block:'nearest'});}
        } else {
          const slot = event.slot === 28 ? focused : event.slot;
          const element = slot === 29 ? back() : entries.find(e => Number(e.dataset.boardRune) === slot);
          if (element) element.click();
        }
        signature = '';
        queueSync();
      } else if (data.board_selection?.navigation_token === token) {
        selection = data.board_selection;
      }
    } catch (error) {
      if (!stopped && version === epoch) {selection = null; report(error.message, true);
        setTimeout(() => {if (!stopped && !selection) {signature='';queueSync();}}, 2000);}
    } finally {
      scanning = false;
      if (!stopped) setTimeout(read, 100);
    }
  }

  document.addEventListener('click', event => {
    const element = event.target.closest('[data-board-rune], [data-board-back]');
    if (!element) return;
    ++epoch;
    signature = '';
    if (element.matches('a[href]') || element.matches('button[type="submit"]')) stop();
    else queueSync();
  }, true);
  document.addEventListener('submit', stop, true);
  document.addEventListener('change', () => {++epoch; signature = ''; queueSync();});
  new MutationObserver(queueSync).observe(document.querySelector('main'), {
    subtree:true, childList:true, attributes:true, attributeFilter:['hidden', 'disabled', 'class'],
  });
  retry.addEventListener('click', () => {signature = ''; queueSync();});
  window.addEventListener('pagehide', stop);
  window.addEventListener('pageshow', event => {if (event.persisted) window.location.reload();});
  queueSync();
})();
