/* Rendering only: dice, costs, legality, queues and saves live on the server. */
const ChargeCombat = (() => {
  let rosterPage = 0, chainPage = -1, resultPage = 0, turnKey = '', decisionKey = '';
  const enabled = () => Boolean(state?.combat?.resonance && !state?.mission?.active && !state?.exploration_mana?.active);
  const view = () => state.combat.resonance;
  const icon = slot => view().icons[String(slot)] || '';
  function send(command, extra = {}) {
    if (busy || !enabled()) return false;
    api('/api/combat/resonance', {command, ...extra, revision:view().revision}, 'Zatwierdzam…');
    return true;
  }
  function handleSlot(slot) {
    if (!enabled()) return false;
    const control = view().controls.find(c => c.slot === slot);
    if (control) send(control.command, control);
    return true;
  }
  function button(c, className = '') {
    return `<button class="rc-button ${className}" data-rc-slot="${c.slot}">${icon(c.slot)}<span>${esc(c.label)}</span></button>`;
  }
  function pages(kind, page, count) {
    if (count <= 1) return '';
    return `<div class="rc-pages"><button data-rc-page="${kind}" data-delta="-1" aria-label="Poprzednia strona" ${page === 0 ? 'disabled' : ''}>‹</button><span>${page+1}/${count}</span><button data-rc-page="${kind}" data-delta="1" aria-label="Następna strona" ${page+1 >= count ? 'disabled' : ''}>›</button></div>`;
  }
  function chainHtml(v) {
    if (!v.chain) return `<section class="rc-chain rc-chain-empty"><small>REZONANS</small><span>Moc wzmocniona rozpoczyna lub przedłuża łańcuch.</span></section>`;
    const count = Math.ceil(v.chain.entries.length/6);
    const page = chainPage < 0 ? count-1 : Math.min(chainPage, count-1);
    return `<section class="rc-chain" aria-label="Aktywny Rezonans"><header><small>REZONANS AKTYWNY · ${v.chain.entries.length} RUN · ${v.chain.members.length} UCZESTNIKÓW</small>${pages('chain', page, count)}</header>
      <div class="rc-track">${v.chain.entries.slice(page*6,page*6+6).map((r,i) => `<span>${page*6+i+1}. ${esc(r.rune)}${r.rune === 'Fala' ? ` → ${esc(r.effective || 'brak')}` : ''}</span>`).join('')}</div>
      <div class="rc-bonuses">${v.chain.bonuses.map(b => `<span><b>${esc(b.rune)} ×${b.count}</b> ${esc(b.text)}</span>`).join('') || '<span>Brak bonusu do skopiowania.</span>'}</div>
      <p>Objęci: ${esc(v.actors.filter(a => v.chain.members.includes(a.id)).map(a => a.name).join(', '))}. Pozostali dołączą na początku swojej tury.</p></section>`;
  }
  function rosterHtml(v) {
    const count = Math.ceil(v.actors.length/8), page = Math.min(rosterPage,count-1);
    return `<aside class="rc-roster" aria-label="Kolejność tury"><header><span>RUNDA ${v.round}</span>${pages('roster',page,count)}</header>
      ${v.actors.slice(page*8,page*8+8).map(a => `<button class="rc-actor ${a.active ? 'rc-current' : ''} ${a.hp <= 0 ? 'rc-defeated' : ''}" data-rc-inspect="${esc(a.id)}" ${a.active ? 'aria-current="true"' : ''}>
      ${TabletopCombat.portrait(a)}<span><b>${esc(a.name)}</b><small>${a.hp}/${a.max_hp} PW · KP ${a.ac}${a.hero ? ` · ⚡ ${a.charges}/20` : ''}</small><span class="rc-actor-state">${esc(a.statuses.slice(0,2).join(' · '))}${a.statuses.length > 2 ? ` +${a.statuses.length-2}` : ''}</span></span>${a.member ? '<i title="Objęty Rezonansem">✦</i>' : ''}</button>`).join('')}
      <footer>Gwiazda: szczegóły postaci i mocy</footer></aside>`;
  }
  function decisionHtml(v) {
    const d = v.decision, a = v.actors.find(a => a.id === (d.actor || v.active));
    const key = `${v.phase}:${d.title}:${d.die?.index ?? ''}`;
    if (key !== decisionKey) { resultPage = 0; decisionKey = key; }
    let content = `<header class="rc-acting">${TabletopCombat.portrait(a)}<div><b>${esc(a.name)}</b><small>${a.hero ? `Ładunki ${a.charges}/20` : a.id===v.active ? 'Tura przeciwnika' : 'Reakcja / rzut przeciwnika'}</small></div>${a.id===v.active?`<div class="rc-budget"><span>Ruch ${a.movement}</span><span class="${a.ordinary ? '' : 'rc-spent'}">Atak / przedmiot</span><span class="${a.special ? '' : 'rc-spent'}">Specjalna</span><span class="${a.reaction ? '' : 'rc-spent'}">Reakcja</span></div>`:`<small>Tura: ${esc(v.actors.find(a=>a.id===v.active).name)}</small>`}</header>
      <section class="rc-decision" aria-live="polite"><header><h2>${esc(d.title)}</h2>${d.pages ? `<small>${d.page}/${d.pages}</small>` : ''}</header>`;
    if (d.mode && d.base_cost !== undefined) content += `<div class="rc-mode">${v.controls.filter(c => [26,27].includes(c.slot)).sort((a,b) => b.slot-a.slot).map(c => `<button data-rc-slot="${c.slot}" aria-pressed="${c.mode===d.mode}">${esc(c.label)}</button>`).join('')}<span>${esc(d.budget)} · ${esc(d.rune)}</span></div>`;
    if (d.body) content += `<p>${esc(d.body)}</p>`;
    if (d.prompt) content += `<p class="rc-prompt">${esc(d.prompt)}</p>`;
    if (d.targets) content += `<div class="rc-targets">${esc(d.targets.join(' · '))}</div>`;
    if (d.warning) content += `<p class="rc-warning">${esc(d.warning)}</p>`;
    if (d.die) content += `<div class="rc-dice"><div><small>KOŚĆ ${d.die.index+1}/${d.die.total} · k${d.die.sides}</small><p>${esc(d.die.label)}</p></div><div class="rc-die-controls"><button data-rc-slot="27" aria-label="Zmniejsz wynik">−</button><output>${d.die.value}</output><button data-rc-slot="26" aria-label="Zwiększ wynik">+</button></div></div>${d.die.accepted.length ? `<small class="rc-accepted">Zatwierdzone: ${d.die.accepted.join(', ')}</small>` : ''}`;
    if (d.dc != null) content += `<p class="rc-roll-summary">Modyfikator ${d.modifier >= 0 ? '+' : ''}${d.modifier} · ST / KP ${d.dc}${d.mode === 'advantage' ? ' · przewaga' : d.mode === 'disadvantage' ? ' · utrudnienie' : ''}</p>`;
    const lines = [...(d.details || [])];
    if (d.rolls) for (const r of d.rolls) {
      lines.push(`${r.label}: ${r.dice.flat().join(' + ')}${r.modifier ? ` ${r.modifier>=0?'+':''}${r.modifier}`:''} → ${r.total}${r.dc == null ? '' : ` / ${r.dc} · ${r.success ? 'sukces' : 'porażka'}`}`);
      lines.push(...(r.messages || []).filter(m => !m.startsWith(r.label+':')));
    }
    if (lines.length) {
      const count = Math.ceil(lines.length/3), page = Math.min(resultPage,count-1);
      content += `<ul class="rc-results">${lines.slice(page*3,page*3+3).map(line => `<li>${esc(line)}</li>`).join('')}</ul>${pages('result',page,count)}`;
    }
    if (v.phase === 'idle' && !d.inspected && a.hero) content += `<div class="rc-powers">${v.powers.map(p => `<button data-rc-slot="${p.slot}" ${p.disabled ? 'disabled' : ''} title="${esc(p.disabled || p.target)}">${icon(p.slot)}<span><b>${esc(p.name)}</b><small>${esc(p.rune)} · ${p.base_cost}/${p.enhanced_cost} · ${esc(p.budget)}</small></span></button>`).join('')}</div>`;
    if (d.item_choices > 1) content += `<div class="rc-mode">${v.controls.filter(c=>[26,27].includes(c.slot)).map(c=>button(c)).join('')}</div>`;
    content += '</section>';
    const actions = v.controls.filter(c => ![25,26,27].includes(c.slot) && !(v.phase==='idle' && v.powers.some(p=>p.slot===c.slot)));
    content += `<footer class="rc-actions">${actions.map(c=>button(c,c.slot===28?'rc-primary':'')).join('')}${v.controls.filter(c=>c.slot===25).map(c=>button(c,'rc-info')).join('')}${d.inspected ? v.controls.filter(c=>[26,27].includes(c.slot)).map(c=>button(c)).join('') : ''}</footer>`;
    return content;
  }
  function html() {
    const v = view(), key = `${v.round}:${v.active}`;
    if (key !== turnKey) { rosterPage = Math.floor(v.actors.findIndex(a=>a.id===v.active)/8); chainPage = -1; turnKey=key; }
    return `<div class="rc-combat">${rosterHtml(v)}<main class="rc-main combat-current-step" tabindex="-1">${chainHtml(v)}${decisionHtml(v)}</main></div>`;
  }
  function afterRender() { document.body.classList.toggle('resonance-active',enabled()); }
  document.addEventListener('click', event => {
    if (!enabled() || busy) return;
    const slot = event.target.closest('[data-rc-slot]');
    if (slot) { handleSlot(Number(slot.dataset.rcSlot)); return; }
    const actor = event.target.closest('[data-rc-inspect]');
    if (actor) { send('inspect',{actor:actor.dataset.rcInspect}); return; }
    const page = event.target.closest('[data-rc-page]');
    if (page) {
      const delta = Number(page.dataset.delta);
      if (page.dataset.rcPage==='roster') rosterPage += delta;
      if (page.dataset.rcPage==='result') resultPage += delta;
      if (page.dataset.rcPage==='chain') chainPage = (chainPage<0?Math.ceil(view().chain.entries.length/6)-1:chainPage)+delta;
      render();
    }
  });
  return {enabled,html,afterRender,handleSlot,send};
})();
