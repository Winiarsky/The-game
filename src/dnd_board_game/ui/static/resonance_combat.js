/* Rendering only: dice, costs, legality, queues and saves live on the server. */
const ChargeCombat = (() => {
  let rosterPage = 0, chainPage = -1, resultPage = 0, bonusPage = 0, targetPage = 0, statusPage = 0, turnKey = '', decisionKey = '';
  let renderedRoll = null;
  const enabled = () => Boolean(state?.combat?.resonance && !state?.mission?.active && !state?.exploration_mana?.active);
  const view = () => state.combat.resonance;
  const icon = slot => view().icons[String(slot)] || '';
  const rune = name => `<span class="rc-rune" title="${esc(name)}">${view().rune_icons?.[name] || esc(name)}</span>`;
  const transitions = {start:'Rozpoczyna pamięć',continue:'Podtrzymuje',reset:'Zaczyna nową pamięć',finisher:'Wyładowanie'};
  function send(command, extra = {}) {
    if (busy || !enabled()) return false;
    api('/api/combat/resonance', {command, ...extra, revision:view().revision}, 'Zatwierdzam…', {quiet:command==='adjust'});
    return true;
  }
  function handleSlot(slot) {
    if (!enabled()) return false;
    const control = view().controls.find(c => c.slot === slot);
    if (control) send(control.command, control);
    return true;
  }
  function button(c, className = '') {
    return `<button class="rc-button ${className}" data-rc-slot="${c.slot}"${c.disabled ? ` disabled title="${esc(c.disabled)}"` : ''}>${icon(c.slot)}<span>${esc(c.label)}</span></button>`;
  }
  function pages(kind, page, count) {
    if (count <= 1) return '';
    return `<div class="rc-pages"><button data-rc-page="${kind}" data-delta="-1" aria-label="Poprzednia strona" ${page === 0 ? 'disabled' : ''}>‹</button><span>${page+1}/${count}</span><button data-rc-page="${kind}" data-delta="1" aria-label="Następna strona" ${page+1 >= count ? 'disabled' : ''}>›</button></div>`;
  }
  function chainHtml(v) {
    if (v.relations) {
      if (!v.chain) return `<section class="rc-chain rc-chain-empty"><small>REZONANS</small><span>Pierwsza moc rozpocznie pamięć. Jej runa nie przyznaje jej premii.</span></section>`;
      return `<section class="rc-chain rc-memory" aria-label="Pamięć Rezonansu"><header><small>PAMIĘĆ REZONANSU · ${v.chain.entries.length}/3</small><small>OD NAJSTARSZEJ DO NAJNOWSZEJ</small></header>
        <div class="rc-memory-row"><div class="rc-memory-track">${v.chain.entries.map((r,i)=>`${i?'<span class="rc-arrow" aria-hidden="true">›</span>':''}${rune(r.rune)}`).join('')}</div>
        <div class="rc-next"><small>NASTĘPNE RUNY</small><div>${v.chain.next_runes.map(rune).join('')}</div></div></div></section>`;
    }
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
  function targetHtml(v) {
    const targets = (v.decision.target_ids || []).map(id=>v.actors.find(a=>a.id===id)).filter(Boolean);
    if (!targets.length) return '';
    const page = Math.min(targetPage, targets.length-1), actor = targets[page];
    const statuses = actor.statuses || [], count = Math.ceil(statuses.length/3), status = Math.min(statusPage,Math.max(0,count-1));
    const abilities = {strength:'SIŁ',dexterity:'ZRĘ',constitution:'KON',intelligence:'INT',wisdom:'MĄD',charisma:'CHA'};
    const simple = (v.phase==='preview'&&!v.decision.resonance) || v.decision.die?.sides===20;
    return `<aside class="rc-target-card ${simple?'rc-target-simple':''} ${v.decision.rejected_target?'rc-target-rejected':''}" aria-label="${v.decision.rejected_target?'Niedostępny cel':'Wybrany cel'}" data-rc-target="${esc(actor.id)}">
      <header><small>${v.decision.rejected_target?'NIEDOSTĘPNY CEL':targets.length>1?'WYBRANE CELE':'WYBRANY CEL'}</small>${pages('target',page,targets.length)}</header>
      <div class="rc-target-person">${TabletopCombat.portrait(actor)}<div><h3>${esc(actor.name)}</h3><div class="rc-target-stats"><span><b>${actor.hp}/${actor.max_hp}</b> PW</span><span><b>${actor.ac}</b> KP</span></div></div></div>
      ${actor.ability_scores ? `<dl class="rc-target-abilities">${Object.entries(abilities).map(([key,label])=>`<div><dt>${label}</dt><dd>${actor.ability_scores[key]}</dd></div>`).join('')}</dl>` : ''}
      ${actor.traits?.length ? `<p class="rc-target-traits">${actor.traits.map(esc).join(' · ')}</p>` : ''}
      <div class="rc-target-effects" aria-label="Aktywne efekty">${statuses.length?statuses.slice(status*3,status*3+3).map(text=>`<span>${esc(text)}</span>`).join(''):'<small>Brak dodatkowych stanów</small>'}</div>${pages('status',status,count)}
    </aside>`;
  }
  function decisionHtml(v) {
    const d = v.decision, a = v.actors.find(a => a.id === (d.actor || v.active));
    const key = `${v.phase}:${d.title}:${d.die?.index ?? ''}:${(d.target_ids || []).join(',')}`;
    if (key !== decisionKey) { resultPage = 0; bonusPage = 0; targetPage = 0; statusPage = 0; decisionKey = key; }
    const target = targetHtml(v), idle = v.phase === 'idle' && !d.inspected && a.hero;
    let content = `<header class="rc-acting">${TabletopCombat.portrait(a)}<div><b>${esc(a.name)}</b><small>${a.hero ? `Ładunki ${a.charges}/20` : a.id===v.active ? 'Tura przeciwnika' : 'Reakcja / rzut przeciwnika'}</small></div>${a.id===v.active?`<div class="rc-budget"><span>Ruch ${a.movement}</span><span class="${a.ordinary ? '' : 'rc-spent'}">Atak / przedmiot</span><span class="${a.special ? '' : 'rc-spent'}">Specjalna</span><span class="${a.reaction ? '' : 'rc-spent'}">Reakcja</span></div>`:`<small>Tura: ${esc(v.actors.find(a=>a.id===v.active).name)}</small>`}</header>
      <section class="rc-decision"><header><h2>${esc(d.title)}</h2>${d.pages ? `<small>${d.page}/${d.pages}</small>` : ''}</header><div class="rc-decision-content ${target?'rc-has-target':''}"><div class="rc-decision-text">`;
    if (idle) {
      const basic = v.basic_actions || v.controls.filter(c=>['move','attack','item','focus'].includes(c.id));
      content += `<div class="rc-basic-actions" aria-label="Akcje podstawowe">${basic.map(c=>button(c,'rc-basic')).join('')}</div>`;
    }
    if (d.mode && d.base_cost !== undefined) content += `<div class="rc-mode">${v.controls.filter(c => [26,27].includes(c.slot)).sort((a,b) => b.slot-a.slot).map(c => `<button data-rc-slot="${c.slot}" aria-pressed="${c.mode===d.mode}">${esc(c.label)}</button>`).join('')}<span>${esc(d.budget)} · ${esc(d.rune)}</span></div>`;
    if (d.cost !== undefined) content += `<div class="rc-cost">${rune(d.rune)}<b>${d.cost} ładunków</b><span>${esc(d.budget)}</span><span class="rc-transition rc-${d.resonance.transition}">${esc(transitions[d.resonance.transition])}</span></div>`;
    if (d.body) content += `<p>${esc(d.body)}</p>`;
    if (d.resonance) {
      const r=d.resonance;
      if(r.transition==='reset') content += '<p class="rc-warning">Ta runa wygasi obecną pamięć przed działaniem. Moc wykona efekt podstawowy.</p>';
      if(r.transition==='finisher') content += `<p class="rc-finisher">Wymaga: ${(v.powers.find(p=>p.name===d.title)?.requires_resonance || []).map(rune).join(' + ')}. Po całej akcji pamięć zgaśnie, także przy pudle.</p>`;
      const bonuses=[...r.active_bonuses.map(b=>({...b,active:true})),...r.missing_bonuses.map(b=>({...b,active:false}))];
      if(bonuses.length){
        const count=Math.ceil(bonuses.length/2),page=Math.min(bonusPage,count-1);
        content+=`<div class="rc-card-bonuses" aria-label="Premie tej mocy">${bonuses.slice(page*2,page*2+2).map(b=>`<div class="${b.active?'rc-bonus-active':'rc-bonus-missing'}"><span>${b.requires.map(rune).join(' + ')}</span><p>${esc(b.text)}<small>${b.active?'Aktywna':`Brak w pamięci: ${esc(b.missing.join(' + '))}`}</small></p></div>`).join('')}</div>${pages('bonus',page,count)}`;
      }
      content+=`<div class="rc-after"><small>PAMIĘĆ PO AKCJI</small>${r.memory_after.length?r.memory_after.map(e=>rune(e.rune)).join('<span aria-hidden="true">›</span>'):'<span>Pusta</span>'}</div>`;
    }
    if (d.prompt && !(d.resonance && d.prompt==='Wybór gotowy do zatwierdzenia.')) content += `<p class="rc-prompt">${esc(d.prompt)}</p>`;
    if (d.targets && !target && !(d.resonance && d.targets.length===1 && d.targets[0]===a.name)) content += `<div class="rc-targets">${esc(d.targets.join(' · '))}</div>`;
    if (d.warning) content += `<p class="rc-warning">${esc(d.warning)}</p>`;
    if (d.die) content += `<div class="rc-dice"><div><small>KOŚĆ ${d.die.index+1}/${d.die.total} · k${d.die.sides}</small><p>${esc(d.die.label)}</p></div><div class="rc-die-controls"><button data-rc-slot="27" aria-label="Zmniejsz wynik">−</button><output aria-live="polite" aria-label="Wynik kości">${d.die.value}</output><button data-rc-slot="26" aria-label="Zwiększ wynik">+</button></div></div>${d.die.accepted.length ? `<small class="rc-accepted">Zatwierdzone: ${d.die.accepted.join(', ')}</small>` : ''}`;
    if (d.dc != null) content += `<p class="rc-roll-summary">Modyfikator ${d.modifier >= 0 ? '+' : ''}${d.modifier} · ST / KP ${d.dc}${d.mode === 'advantage' ? ' · przewaga' : d.mode === 'disadvantage' ? ' · utrudnienie' : ''}</p>`;
    if (d.modifier_components?.length) content += `<p class="rc-modifier-breakdown">${d.modifier_components.map(m=>`<span title="${esc(m.label)}">${esc(m.label.replace(/:\s*[−+\-]\d.*$/, ''))} <b>${m.value>=0?'+':''}${m.value}</b></span>`).join(' · ')}</p>`;
    if (d.cover_text) content += `<p class="rc-roll-summary rc-cover-summary">${esc(d.cover_text)}</p>`;
    const lines = [...(d.details || [])];
    if (d.rolls) for (const r of d.rolls) {
      lines.push(`${r.label}: ${r.dice.flat().join(' + ')}${r.modifier ? ` ${r.modifier>=0?'+':''}${r.modifier}`:''} → ${r.total}${r.dc == null ? '' : ` / ${r.dc} · ${r.success ? 'sukces' : 'porażka'}`}`);
      lines.push(...(r.messages || []).filter(m => !m.startsWith(r.label+':')));
    }
    if (lines.length) {
      const count = Math.ceil(lines.length/3), page = Math.min(resultPage,count-1);
      content += `<ul class="rc-results">${lines.slice(page*3,page*3+3).map(line => `<li>${esc(line)}</li>`).join('')}</ul>${pages('result',page,count)}`;
    }
    if (idle) {
      content += `<div class="rc-powers">${v.powers.map(p => `<button data-rc-slot="${p.slot}" ${p.disabled ? 'disabled' : ''} title="${esc(p.disabled || p.target)}" ${v.relations?`data-transition="${p.disabled?'locked':p.resonance.transition}"`:''}>${icon(p.slot)}<span><b>${esc(p.name)}</b><small>${v.relations?`${p.cost} ładunków · ${esc(p.budget)}`:`${esc(p.rune)} · ${p.base_cost}/${p.enhanced_cost} · ${esc(p.budget)}`}</small>${v.relations?`<small class="rc-power-condition">${esc(p.disabled || transitions[p.resonance.transition])}</small>`:''}</span></button>`).join('')}</div>`;
      if(v.reserved_runes?.length) content+=`<details class="rc-reserved"><summary>Runy rozwoju · niedostępne</summary><div>${v.reserved_runes.map(name=>`<button disabled title="${esc(name)} · do zdobycia w dalszej grze">${rune(name)}</button>`).join('')}</div></details>`;
    }
    if (d.item_choices > 1) content += `<div class="rc-mode">${v.controls.filter(c=>[26,27].includes(c.slot)).map(c=>button(c)).join('')}</div>`;
    content += `</div>${target}</div></section>`;
    const actions = v.controls.filter(c => ![25,26,27].includes(c.slot) && !(idle && (v.powers.some(p=>p.slot===c.slot) || ['move','attack','item','focus'].includes(c.id))));
    content += `<div class="rc-board-error rc-warning" role="status" hidden><span></span><button data-rc-scan-retry>Spróbuj ponownie</button></div><footer class="rc-actions">${actions.map(c=>button(c,c.slot===28?'rc-primary':'')).join('')}${v.controls.filter(c=>c.slot===25).map(c=>button(c,'rc-info')).join('')}${d.inspected ? v.controls.filter(c=>[26,27].includes(c.slot)).map(c=>button(c)).join('') : ''}</footer>`;
    return content;
  }
  function html() {
    const v = view(), key = `${v.round}:${v.active}`;
    if (key !== turnKey) { rosterPage = Math.floor(v.actors.findIndex(a=>a.id===v.active)/8); chainPage = -1; turnKey=key; }
    return `<div class="rc-combat" data-phase="${esc(v.phase)}">${rosterHtml(v)}<main class="rc-main combat-current-step" tabindex="-1">${chainHtml(v)}${decisionHtml(v)}</main></div>`;
  }
  function rollSignature(v) {
    if (!v?.decision?.die) return '';
    return JSON.stringify({...v,revision:0,decision:{...v.decision,die:{...v.decision.die,value:0}}});
  }
  function afterRender() {
    document.body.classList.toggle('resonance-active',enabled());
    renderedRoll = enabled() && view().decision.die ? {signature:rollSignature(view()),revision:view().revision} : null;
    updateBoardError();
    fitTargetPortrait();
  }
  function updateBoardError() {
    const notice = document.querySelector('.rc-board-error');
    if (!notice) return;
    const transportError = boardInputPhase==='error' && boardScanError && !boardCommandError;
    const message = transportError ? boardScanError : boardCommandError;
    notice.hidden = !message;
    notice.querySelector('span').textContent = message ? `${message}${transportError?'':' Wybierz ponownie na planszy albo wróć.'}` : '';
    notice.querySelector('button').hidden = !transportError;
  }
  function fitTargetPortrait() {
    const card = document.querySelector('.rc-target-simple'), portrait = card?.querySelector('.tt-portrait');
    if (!portrait) return;
    portrait.style.removeProperty('width');
    portrait.style.removeProperty('height');
    if (innerWidth<=1000 || innerHeight<620) return;
    const decision = card.closest('.rc-decision'), bottom = decision.getBoundingClientRect().bottom;
    const base = portrait.getBoundingClientRect().width;
    const spare = bottom-card.getBoundingClientRect().bottom-12;
    const size = Math.floor(Math.min(180, card.clientWidth*.55, base+spare));
    if (size<=base) return;
    portrait.style.width = portrait.style.height = `${size}px`;
    // A longer name can wrap when the portrait grows; preserve the footer gap.
    if (card.getBoundingClientRect().bottom>bottom-8) {
      portrait.style.width = portrait.style.height = `${base}px`;
    }
  }
  function updateDie() {
    if (!enabled() || !renderedRoll || view().revision===renderedRoll.revision || rollSignature(view())!==renderedRoll.signature) return false;
    const output = document.querySelector('.rc-die-controls output');
    if (!output) return false;
    output.textContent = view().decision.die.value;
    renderedRoll.revision = view().revision;
    return true;
  }
  document.addEventListener('click', event => {
    if (!enabled() || busy) return;
    if (event.target.closest('[data-rc-scan-retry]')) { scanBoard(); return; }
    const slot = event.target.closest('[data-rc-slot]');
    if (slot) { handleSlot(Number(slot.dataset.rcSlot)); return; }
    const actor = event.target.closest('[data-rc-inspect]');
    if (actor) { send('inspect',{actor:actor.dataset.rcInspect}); return; }
    const page = event.target.closest('[data-rc-page]');
    if (page) {
      const delta = Number(page.dataset.delta);
      if (page.dataset.rcPage==='roster') rosterPage += delta;
      if (page.dataset.rcPage==='result') resultPage += delta;
      if (page.dataset.rcPage==='bonus') bonusPage += delta;
      if (page.dataset.rcPage==='target') { targetPage += delta; statusPage = 0; }
      if (page.dataset.rcPage==='status') statusPage += delta;
      if (page.dataset.rcPage==='chain') chainPage = (chainPage<0?Math.ceil(view().chain.entries.length/6)-1:chainPage)+delta;
      render();
    }
  });
  window.addEventListener('resize', fitTargetPortrait);
  return {enabled,html,afterRender,handleSlot,send,updateDie,updateBoardError};
})();
