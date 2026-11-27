/* Shared presentation primitives. No game rules, transport or resource spending. */
const PlayerUi = (() => {
  const keypad = {
    Numpad0:'0', Numpad1:'1', Numpad2:'2', Numpad3:'3', Numpad4:'4',
    Numpad5:'5', Numpad6:'6', Numpad7:'7', Numpad8:'8', Numpad9:'9',
    NumpadEnter:'Enter', NumpadAdd:'+', NumpadSubtract:'-', NumpadMultiply:'*',
    NumpadDivide:'/', NumpadDecimal:'.', NumpadComma:'.', NumpadEqual:'=',
  };
  const key = event => keypad[event.code] || event.key;
  const isTyping = target => Boolean(target?.closest?.('textarea,select,input:not([type="checkbox"]):not([type="radio"]):not([type="button"]):not([type="submit"]),[contenteditable]:not([contenteditable="false"])'));
  const visible = element => Boolean(element && !element.disabled && !element.closest('[hidden],[inert]')
    && element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden');

  function nextChoice(choices, current, dx, dy) {
    if (!choices.length) return null;
    current = choices.includes(current) ? current : choices[0];
    const origin = current.getBoundingClientRect();
    // Read geometry once, then let the caller update focus and scroll.
    const candidates = choices.filter(item => item !== current).map(item => {
      const rect = item.getBoundingClientRect();
      const forward = dx ? (rect.x + rect.width/2 - origin.x - origin.width/2) * dx
        : (rect.y + rect.height/2 - origin.y - origin.height/2) * dy;
      const cross = dx ? Math.abs(rect.y + rect.height/2 - origin.y - origin.height/2)
        : Math.abs(rect.x + rect.width/2 - origin.x - origin.width/2);
      const overlap = dx ? rect.top < origin.bottom-2 && rect.bottom > origin.top+2
        : rect.left < origin.right-2 && rect.right > origin.left+2;
      return {item, forward, cross, overlap, rect};
    });
    const forward = candidates.filter(candidate => candidate.forward > 2);
    const aligned = forward.filter(candidate => candidate.overlap);
    const next = (aligned.length ? aligned : forward).sort((a,b) =>
      (a.forward+a.cross*2) - (b.forward+b.cross*2))[0]?.item;
    if (next) return next;
    // Retain left/right as aliases in a single vertical list.
    if (dx && candidates.every(({rect}) => Math.abs(rect.x+rect.width/2-origin.x-origin.width/2)<3))
      return choices[Math.max(0,Math.min(choices.length-1,choices.indexOf(current)+dx))];
    return current;
  }

  let activePanel = null;
  const panelState = new WeakMap();
  function panelChoices(panel) {
    return [...panel.querySelectorAll('button,a[href],input,select,textarea,summary,[tabindex]:not([tabindex="-1"])')]
      .filter(element=>visible(element)&&element.tabIndex>=0);
  }
  function setPanelOpen(panel, open, background) {
    if (!panel) return;
    const previous = panelState.get(panel);
    if (open && !previous) panelState.set(panel,{returnTo:document.activeElement,background});
    panel.inert = !open;
    panel.setAttribute('aria-hidden',String(!open));
    panel.setAttribute('aria-modal',String(open));
    background.forEach(element => {if(element)element.inert=open;});
    if (open) {
      activePanel=panel;
      if (!previous) requestAnimationFrame(()=>{
        if(activePanel===panel)(panel.querySelector('[role="tab"][aria-selected="true"]')||panelChoices(panel)[0]||panel).focus({preventScroll:true});
      });
    } else {
      if(activePanel===panel)activePanel=null;
      panelState.delete(panel);
      if(previous?.returnTo?.isConnected && visible(previous.returnTo)) previous.returnTo.focus({preventScroll:true});
    }
  }
  document.addEventListener('keydown',event=>{
    if(event.key!=='Tab'||!activePanel||document.querySelector('dialog[open]'))return;
    const choices=panelChoices(activePanel),index=choices.indexOf(document.activeElement);
    if(!choices.length){event.preventDefault();activePanel.focus();return;}
    if(index<0 || !event.shiftKey&&index===choices.length-1 || event.shiftKey&&index===0){
      event.preventDefault();choices[event.shiftKey?choices.length-1:0].focus();
    }
  },{capture:true});
  document.addEventListener('focusin',event=>{
    if(activePanel&&!activePanel.contains(event.target)&&!document.querySelector('dialog[open]'))
      panelChoices(activePanel)[0]?.focus({preventScroll:true});
  });

  function clearNotice() { document.getElementById('player-notice')?.remove(); }
  function notice(message) {
    const returnTo=document.activeElement;
    clearNotice();
    const notice=document.createElement('div');
    notice.id='player-notice';notice.className='player-notice';notice.setAttribute('role','alert');
    const text=document.createElement('span');text.textContent=message;
    const close=document.createElement('button');close.type='button';close.className='secondary';
    close.textContent='Zamknij';close.setAttribute('aria-label','Zamknij komunikat');
    close.onclick=()=>{clearNotice();if(returnTo?.isConnected&&visible(returnTo))returnTo.focus({preventScroll:true});};
    notice.append(text,close);
    const host=activePanel?.querySelector('[role="tabpanel"]:not([hidden])') || activePanel
      || [...document.querySelectorAll('.rc-decision')].find(visible)
      || [...document.querySelectorAll('.confrontation-controls')].find(visible)
      || [...document.querySelectorAll('#mission-panel,#encounter-panel,#action-panel')].find(visible)
      || document.querySelector('main');
    host?.prepend(notice);
    if(activePanel)notice.scrollIntoView({block:'nearest'});
  }
  return {key,isTyping,visible,nextChoice,setPanelOpen,notice,clearNotice};
})();
