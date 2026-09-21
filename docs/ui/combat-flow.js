/* Static board-input demonstration. Values describe prepared UI examples, not a rules engine. */
const CombatFlow = (() => {
  const ACTIVE = 'garran';
  const ORDER = COMBAT_INITIATIVE.map(([id]) => id);
  const GEOMETRY = {
    borut: {melee:5, ranged:30, ac:13, cover:'none'},
    drwal: {melee:5, ranged:40, ac:12, cover:'half', coverSource:'niski mur'},
    parobek: {melee:5, ranged:120, ac:14, cover:'three_quarters', coverSource:'wóz'},
    procarz: {melee:35, ranged:70, ac:12, cover:'none'},
    woznica: {melee:20, ranged:50, ac:12, cover:'full', coverSource:'mur'},
    pomocnik: {melee:10, ranged:10, ac:12, cover:'none'},
    procarz_drugi: {melee:25, ranged:25, ac:12, cover:'none'},
    drwal_drugi: {melee:15, ranged:15, ac:12, cover:'none'},
    garran: {melee:0, ranged:0, ac:19, cover:'none'},
    brakka: {melee:5, ranged:5, ac:14, cover:'none'},
    mira: {melee:5, ranged:5, ac:14, cover:'none'},
    dagna: {melee:10, ranged:10, ac:16, cover:'none'},
    lorian: {melee:15, ranged:15, ac:14, cover:'none'},
    nimra: {melee:20, ranged:20, ac:12, cover:'none'}
  };
  let flow;
  let savedScroll = 0;
  let scrollToActor = ACTIVE;

  function reset(mode = 'melee') {
    flow = {
      phase:'idle', slot:null, target:null, inspected:null, effectPage:0,
      attackMode:mode === 'ranged' ? 'ranged' : 'melee',
      targetVersion:0, approvedTargetVersion:null,
      executionCount:0, deckSpent:0, confirmedTarget:null,
      threatened:false, attackerProne:false, rallied:false
    };
    state.combatSlot = null;
    savedScroll = 0;
    scrollToActor = ACTIVE;
  }

  function repaint() {
    const list = document.querySelector('.cf-initiative-list');
    if (list) savedScroll = list.scrollTop;
    render();
  }

  function setAttackMode(mode) {
    reset(mode);
    repaint();
  }

  function setAttackConditions(conditions) {
    if (flow.phase === 'resolved') return;
    for (const key of ['threatened', 'attackerProne', 'rallied']) {
      if (typeof conditions[key] === 'boolean') flow[key] = conditions[key];
    }
    flow.targetVersion += 1;
    flow.approvedTargetVersion = null;
    repaint();
  }

  function actionSpec() {
    const source = COMBAT_ACTIONS[flow.slot];
    if (!source) return null;
    if (flow.attackMode === 'ranged' && flow.slot === 8) {
      return {...source, blocked:'W tym przykładzie Garran trzyma oburącz kuszę. Ta zdolność wymaga założonej tarczy.'};
    }
    if (flow.slot === 1 && flow.attackMode === 'ranged') {
      return {...source, name:'Atak kuszą lekką', body:'Kusza jest założona, tarcza odłożona. Wskaż przeciwnika. Podgląd celu pokaże zasięg, osłonę i warunki rzutu.', cost:'Akcja główna · bez spalania · 1 bełt'};
    }
    return source;
  }

  function targetKind() {
    if (flow.slot === 0) return 'field';
    if ([1, 8, 10].includes(flow.slot)) return 'enemy';
    if (flow.slot === 14) return 'ally';
    return 'self';
  }

  function targetInstruction() {
    if (flow.slot === 0) return 'Wskaż podświetlone pole ruchu.';
    if (flow.slot === 8) return 'Wskaż sąsiadującego przeciwnika.';
    if (flow.slot === 14) return 'Wskaż sojusznika w zasięgu 15 ft.';
    if (flow.slot === 10) return 'Wskaż przeciwnika w zasięgu 60 ft.';
    return flow.attackMode === 'ranged' ? 'Wskaż pole wybranego przeciwnika.' : 'Wskaż przeciwnika w zasięgu miecza.';
  }

  function runeButton(slot, label, primary = false, disabled = false) {
    return `<button class="${primary ? 'primary' : 'secondary'}" data-board-slot="${slot}" ${disabled ? 'disabled' : ''}>${rune(slot)}${label}</button>`;
  }

  function listHtml() {
    return `<aside class="cf-initiative" aria-label="Tor inicjatywy"><div class="cf-initiative-head"><div><span class="cf-kicker">Runda 3</span><h2>Tor inicjatywy</h2></div><p>Teraz <strong>Garran</strong><br><small>Następny: Procarz 1</small></p></div><ol class="cf-initiative-list">${COMBAT_INITIATIVE.map(([id, score]) => {
      const a = combatActor(id);
      const active = id === ACTIVE;
      const inspected = id === flow.inspected;
      const targeted = id === flow.target;
      return `<li><button class="cf-actor-row ${a.enemy ? 'is-enemy' : ''} ${active ? 'is-active' : ''} ${inspected ? 'is-inspected' : ''} ${targeted ? 'is-target' : ''} ${a.defeated ? 'is-defeated' : ''}" data-combat-actor="${id}" aria-current="${active ? 'step' : 'false'}" aria-label="${a.name}, ${a.hp} z ${a.max} PW${active ? ', aktywna tura' : ''}${inspected ? ', oglądasz' : ''}${targeted ? ', wybrany cel' : ''}">${combatPortrait(id, 'cf-portrait')}<span class="cf-row-main"><span class="cf-row-name"><strong>${a.short}</strong><small>${active ? 'TERAZ' : a.defeated ? 'Pokonany' : score}</small></span><span class="cf-row-health">${a.hp}<small> / ${a.max} PW</small>${inspected ? '<em>Podgląd</em>' : targeted ? '<em>Cel</em>' : ''}</span>${active ? hpBar(a) + `<span class="cf-row-meta">4/6 kart · test +4 · ładunek 6/6<br>${flow.attackMode === 'ranged' ? 'Kusza · bez tarczy · KP 17' : 'Miecz i tarcza · KP 19'}</span>` : ''}${effectBadges(a.effects, active ? 3 : 2)}</span></button></li>`;
    }).join('')}</ol><p class="cf-control-hint">${rune(26)} ${rune(27)} Przeglądaj uczestników</p></aside>`;
  }

  function personHeading(id, label = '') {
    const a = combatActor(id);
    return `<div class="cf-person-heading">${combatPortrait(id, 'cf-detail-portrait')}<div>${label ? `<span class="cf-kicker">${label}</span>` : ''}<h2>${a.name}</h2><p class="cf-person-health">${a.hp} <span>/ ${a.max} PW</span></p>${effectBadges(a.effects, 3)}</div></div>`;
  }

  function actorDetails(id) {
    const a = combatActor(id);
    const hasMore = flow.effectPage + 1 < a.effects.length;
    return `<section class="cf-context cf-inspector" aria-label="Podgląd uczestnika">${personHeading(id, id === ACTIVE ? 'Aktywny bohater · podgląd' : 'Podgląd uczestnika')}${a.defeated ? '<p class="notice">Pokonany. Pomijany przy przekazywaniu tury.</p>' : ''}${a.effects.length > 1 ? `<p class="cf-cost">Efekt ${flow.effectPage + 1} z ${a.effects.length}</p>` : ''}${a.effects.length ? a.effects.slice(flow.effectPage, flow.effectPage + 1).map(key => {
      const e = EFFECTS[key];
      return `<section class="cf-effect"><h3>${effectIcon(e)}${e.label}</h3><p>${e.body}</p><p class="cf-effect-source"><strong>Źródło:</strong> ${e.source}</p><p class="cf-effect-source"><strong>Do kiedy:</strong> ${e.duration}</p></section>`;
    }).join('') : '<p class="cf-copy">Brak aktywnych stanów i aur.</p>'}${!a.enemy ? `<p class="cf-cost">${a.cards}/6 kart · premia do testów +${a.cards}</p>` : ''}<p class="cf-control-hint">${rune(26)} ${rune(27)} Inny uczestnik · ${rune(28)} ${hasMore ? 'Następny efekt' : 'Wróć'} · ${rune(29)} Wróć do ${flow.phase === 'idle' ? 'aktywnej postaci' : 'akcji'}</p></section>`;
  }

  function targetFacts(id) {
    const a = combatActor(id);
    const geometry = GEOMETRY[id];
    const distance = geometry[flow.attackMode];
    const ranged = flow.slot === 1 && flow.attackMode === 'ranged';
    const range = flow.slot === 10 ? 60 : flow.slot === 14 ? 15 : ranged ? 320 : 5;
    const cover = ranged ? geometry.cover : 'none';
    const lineBlocked = flow.attackMode === 'ranged' && geometry.cover === 'full';
    const coverBonus = cover === 'half' ? 2 : cover === 'three_quarters' ? 5 : 0;
    const blockers = [];
    if (a.defeated) blockers.push('Cel został pokonany.');
    if (targetKind() === 'enemy' && !a.enemy) blockers.push('Ta akcja wymaga przeciwnika.');
    if (targetKind() === 'ally' && (a.enemy || id === ACTIVE)) blockers.push('Wybierz innego bohatera z drużyny.');
    if (distance > range) blockers.push(`Poza zasięgiem: ${distance} ft; maksymalnie ${range} ft.`);
    if (lineBlocked) blockers.push('Pełna osłona blokuje linię widzenia do celu.');
    const advantages = [];
    const disadvantages = [];
    if (flow.slot === 1 && flow.rallied) advantages.push('Mowa dowódcy: przewaga pierwszego ataku.');
    if (flow.slot === 1 && flow.attackerProne) disadvantages.push('Atakujący jest powalony.');
    if (ranged && flow.threatened) disadvantages.push('Wróg w odległości 5 ft od strzelca.');
    if (flow.slot === 1 && a.effects.includes('prone')) {
      if (distance <= 5) advantages.push('Cel powalony w zasięgu 5 ft.');
      else disadvantages.push('Powalony cel dalej niż 5 ft.');
    }
    if (ranged && distance > 80 && distance <= range) disadvantages.push('Daleki zasięg kuszy: powyżej 80 ft.');
    const rollMode = advantages.length && disadvantages.length ? 'Zwykły rzut' : advantages.length ? 'Przewaga' : disadvantages.length ? 'Utrudnienie' : 'Zwykły rzut';
    const coverText = (cover === 'full' ? 'Pełna · atak zablokowany' : cover === 'half' ? 'Połowa · +2 KP' : cover === 'three_quarters' ? 'Trzy czwarte · +5 KP' : 'Brak · +0 KP') + (cover !== 'none' && geometry.coverSource ? ` · ${geometry.coverSource}` : '');
    return {a, distance, range, ranged, cover, lineBlocked, coverBonus, coverText, blockers, advantages, disadvantages, rollMode, legal:!blockers.length, ac:geometry.ac + coverBonus, pushBlocked:flow.slot === 8 && id === 'drwal'};
  }

  function resolutionCopy(facts) {
    if (flow.slot === 8) return `<strong>Test przeciwstawny:</strong> k20 + 4 Siła + 4 z kart przeciw testowi Siły celu.<br>Wyższy wynik: k6 + 4 obrażeń${facts.pushBlocked ? '. Za celem brak wolnego pola — bez odepchnięcia.' : ' i odepchnięcie o 1 wolne pole.'} Remis: niepowodzenie.`;
    if (flow.slot === 10) return '<strong>Obrona Mądrości celu · ST 14.</strong><br>Porażka: ruch o połowę mniejszy i brak reakcji do początku następnej tury Garrana.';
    if (flow.slot === 14) return '<strong>Garran, potem wybrany sojusznik:</strong> ruch do 10 ft i atak bronią.<br>Sojusznik zużyje reakcję. Każdy atak otrzyma osobny podgląd celu.';
    const die = facts.rollMode === 'Przewaga' ? '2k20 (wyższy)' : facts.rollMode === 'Utrudnienie' ? '2k20 (niższy)' : 'k20';
    if (facts.ranged) return `<strong>Atak: ${die} + 6 + k4 z Błogosławieństwa</strong> przeciw KP ${facts.ac}.<br>Obrażenia: k8 + 2.`;
    return `<strong>Atak: ${die} + 8 + k4 z Błogosławieństwa</strong> przeciw KP ${facts.ac}.<br>Obrażenia: k8 + 5 · w tym +1 z Natarcia.`;
  }

  function targetDetails() {
    if (flow.target === 'field_north') {
      return `<section class="cf-context"><span class="cf-kicker">Wybrane pole</span><h2>Pole obok Garrana</h2><dl class="cf-facts"><div><dt>Koszt ruchu</dt><dd>1 pole z pozostałych 3</dd></div><div><dt>Przejście</dt><dd>Wolne · zwykły teren</dd></div></dl><p class="cf-verdict">Przestaw figurkę po zatwierdzeniu.</p></section>`;
    }
    const f = targetFacts(flow.target);
    return `<section class="cf-context cf-target-preview" aria-label="Podgląd celu">${personHeading(flow.target, 'Wybrany cel')}<dl class="cf-facts"><div><dt>Odległość / zasięg</dt><dd>${f.distance} ft / ${f.ranged ? '80 / 320' : f.range} ft</dd></div><div><dt>Linia widzenia</dt><dd>${f.lineBlocked ? 'Zablokowana' : 'Widoczny'}</dd></div>${flow.slot === 1 ? `<div><dt>Osłona</dt><dd>${f.coverText}</dd></div><div><dt>Klasa pancerza</dt><dd>${f.ac}${f.coverBonus ? ` = ${GEOMETRY[flow.target].ac} + ${f.coverBonus} osłony` : ''}</dd></div><div><dt>Warunki rzutu</dt><dd>${f.rollMode}</dd></div>` : ''}</dl>${flow.slot === 1 ? `<div class="cf-roll-reasons">${[...f.advantages, ...f.disadvantages].map(reason => `<p>${reason}</p>`).join('')}${f.advantages.length && f.disadvantages.length ? '<p>Przewaga i utrudnienie wzajemnie się znoszą.</p>' : ''}</div>` : ''}<p class="cf-roll-formula">${resolutionCopy(f)}</p><p class="cf-verdict ${f.legal ? '' : 'is-illegal'}">${f.legal ? 'Cel dostępny. Zatwierdź, aby rozpocząć rozstrzygnięcie.' : f.blockers.join(' ')}</p></section>`;
  }

  function stepper() {
    const current = flow.phase === 'action' ? 0 : flow.phase === 'target_select' ? 1 : 2;
    return `<ol class="cf-stepper" aria-label="Etap akcji">${['Akcja', targetKind() === 'self' ? 'Efekt' : 'Cel', 'Zatwierdzenie'].map((name, i) => `<li class="${i === current ? 'is-current' : i < current ? 'is-done' : ''}">${name}</li>`).join('')}</ol>`;
  }

  function panelHtml() {
    if (!flow) reset();
    if (flow.phase === 'idle') {
      return `<div class="cf-layout" data-step="${flow.inspected ? 'inspect' : 'idle'}"><section class="cf-action cf-idle"><span class="cf-kicker">Tura Garrana</span><h1>Wybierz akcję.</h1><p class="intro">Naciśnij na planszy runę z karty postaci.</p><p class="turn-resources">Akcja dostępna · Ruch 3/6 · Reakcja dostępna</p>${flow.inspected ? '' : '<p class="cf-control-hint">−/+ na planszy: obejrzyj uczestników i ich efekty.<br>×: menu gry</p>'}</section>${flow.inspected ? actorDetails(flow.inspected) : ''}</div>`;
    }
    const a = actionSpec();
    if (flow.phase === 'resolved') {
      const target = flow.confirmedTarget && flow.confirmedTarget !== 'field_north' ? combatActor(flow.confirmedTarget) : null;
      const confirmedMode = target && flow.slot === 1 ? targetFacts(target.id).rollMode : 'Zwykły rzut';
      const attackDice = confirmedMode === 'Przewaga' ? 'Rzuć 2k20, wybierz wyższy wynik, i rzuć k4 z Błogosławieństwa.' : confirmedMode === 'Utrudnienie' ? 'Rzuć 2k20, wybierz niższy wynik, i rzuć k4 z Błogosławieństwa.' : 'Rzuć k20 i k4 z Błogosławieństwa.';
      return `<div class="cf-layout" data-step="resolved"><section class="cf-action"><span class="cf-kicker">Zatwierdzona deklaracja</span><h1>${a.name}</h1><p class="cf-copy">${target ? `Cel: <strong>${target.name}</strong>. ` : ''}${flow.slot === 8 ? 'Rzuć k20 dla testu przeciwstawnego.' : flow.slot === 1 ? attackDice : flow.slot === 10 ? 'Rozstrzygnij obronę Mądrości celu, ST 14.' : a.next || a.body}</p><p class="cf-cost">${flow.deckSpent ? `Do opłacenia: ${flow.deckSpent} karta ze wspólnej talii.` : 'Bez spalania kart.'}</p><p class="cf-control-hint">Kolejny etap: rozstrzygnięcie w aplikacji gry.</p><div class="cf-buttons">${runeButton(29, 'Wróć do przykładu')}</div></section>${flow.inspected ? actorDetails(flow.inspected) : target ? `<section class="cf-context">${personHeading(target.id, 'Zatwierdzony cel')}</section>` : ''}</div>`;
    }
    let content = '';
    let buttons = '';
    if (flow.inspected) {
      content = actorDetails(flow.inspected);
      const hasMore = flow.effectPage + 1 < combatActor(flow.inspected).effects.length;
      buttons = runeButton(28, hasMore ? 'Następny efekt' : 'Wróć do akcji', true) + runeButton(29, 'Wróć do akcji');
    } else if (flow.phase === 'action') {
      content = a.blocked ? `<p class="notice">${a.blocked}</p>` : '';
      buttons = runeButton(28, targetKind() === 'self' ? 'Sprawdź efekt' : 'Wskaż cel', true, !!a.blocked) + runeButton(29, 'Wróć');
    } else if (flow.phase === 'target_select') {
      content = `<section class="cf-context cf-target-empty"><span class="cf-kicker">Wybór na planszy</span><h2>${targetInstruction()}</h2><p>Naciśnij pole przy figurce. Tutaj zobaczysz cel i warunki przed zatwierdzeniem.</p></section>`;
      buttons = runeButton(29, 'Wróć do akcji');
    } else if (flow.phase === 'target_preview') {
      content = targetDetails();
      const legal = flow.target === 'field_north' || targetFacts(flow.target).legal;
      buttons = runeButton(28, 'Zatwierdź cel i wykonaj', true, !legal) + runeButton(29, 'Zmień cel');
    } else if (flow.phase === 'self_preview') {
      content = `<section class="cf-context"><span class="cf-kicker">Potwierdzenie</span><h2>${flow.slot === 5 ? 'Zakończyć turę Garrana?' : 'Zastosować ten efekt?'}</h2><p class="cf-copy">${a.next || a.body}</p></section>`;
      buttons = runeButton(28, flow.slot === 5 ? 'Zatwierdź koniec tury' : 'Zatwierdź i wykonaj', true) + runeButton(29, 'Wróć');
    }
    const choosingTarget = ['target_select', 'target_preview'].includes(flow.phase);
    const header = flow.inspected ? '' : choosingTarget
      ? `<h1 class="cf-target-label">${a.name} <span>· Wybór celu</span></h1>`
      : `<section class="cf-action"><span class="cf-kicker">Tura Garrana · podgląd akcji</span>${stepper()}<div class="cf-action-title">${rune(flow.slot)}<h1>${a.name}</h1></div><p class="cf-cost">${a.cost}</p>${flow.phase === 'action' ? `<p class="cf-copy">${a.body}</p>` : ''}</section>`;
    const confirmationCost = !flow.inspected && flow.phase === 'target_preview'
      ? `<span class="cf-confirm-cost">${a.cost}</span>` : '';
    return `<div class="cf-layout" data-step="${flow.inspected ? 'inspect' : flow.phase}">${header}${content}<div class="cf-buttons">${buttons}${confirmationCost}</div><p class="cf-control-hint">${flow.inspected ? '−/+ : inny uczestnik. Podgląd nie zmienia celu ani tury.' : flow.phase === 'target_preview' ? 'Inne pole figurki: zmień cel · −/+ : podgląd uczestników' : '−/+ : podgląd uczestników · ✓ : dalej · × : wstecz'}</p></div>`;
  }

  function controlsHtml() {
    return `<span>Runy planszy · makieta</span><div class="board-runes cf-board-controls">${[0, 1, 6, 7, 8, 9, 10, 11, 12, 13, 14, 5, 26, 27, 28, 29].map(slot => {
      const label = slot === 26 ? 'Poprzedni uczestnik' : slot === 27 ? 'Następny uczestnik' : slot === 28 ? 'Akceptuj' : slot === 29 ? 'Wstecz / menu' : slot === 1 && flow.attackMode === 'ranged' ? 'Atak kuszą lekką' : COMBAT_ACTIONS[slot].name;
      return `<button data-board-slot="${slot}" aria-label="${label}" title="${label}" aria-pressed="${flow.slot === slot}">${rune(slot)}</button>`;
    }).join('')}</div><span>−/+ : tor inicjatywy · ✓ akceptuj · × wstecz</span>`;
  }

  function targetMockHtml() {
    if (!['target_select', 'target_preview'].includes(flow.phase) || flow.inspected) return '';
    const ids = targetKind() === 'ally' ? HEROES.filter(([id]) => id !== ACTIVE).map(([id]) => id) : targetKind() === 'field' ? [] : COMBAT_ENEMIES.filter(a => a.hp > 0).map(a => a.id);
    return `<div class="cf-target-mock"><span>Pola planszy · makieta</span>${targetKind() === 'field' ? '<button data-combat-target="field_north">Pole obok Garrana</button>' : ids.map(id => `<button data-combat-target="${id}" aria-pressed="${flow.target === id}">${combatPortrait(id, 'cf-target-token')}${combatActor(id).short}</button>`).join('')}<small>Symulacja naciśnięcia pola figurki</small></div>`;
  }

  function selectActor(id) {
    if (!ORDER.includes(id)) return;
    flow.inspected = id;
    flow.effectPage = 0;
    scrollToActor = id;
    repaint();
  }

  function browse(direction) {
    const from = ORDER.indexOf(flow.inspected || ACTIVE);
    selectActor(ORDER[(from + direction + ORDER.length) % ORDER.length]);
  }

  function selectTarget(id) {
    if (!['target_select', 'target_preview'].includes(flow.phase) || flow.inspected) return;
    if (targetKind() === 'field' ? id !== 'field_north' : !ORDER.includes(id)) return;
    flow.target = id;
    flow.targetVersion += 1;
    flow.approvedTargetVersion = null;
    flow.phase = 'target_preview';
    repaint();
  }

  function confirm() {
    const a = actionSpec();
    if (!a || a.blocked) return;
    if (flow.inspected) {
      advanceInspection();
      return;
    }
    if (flow.phase === 'action') flow.phase = targetKind() === 'self' ? 'self_preview' : 'target_select';
    else if (flow.phase === 'target_preview' || flow.phase === 'self_preview') {
      if (flow.phase === 'target_preview' && flow.target !== 'field_north' && !targetFacts(flow.target).legal) return;
      flow.confirmedTarget = flow.target;
      flow.approvedTargetVersion = flow.targetVersion;
      flow.executionCount += 1;
      flow.deckSpent = a.cost.includes('spal 1 kartę') ? 1 : 0;
      flow.phase = 'resolved';
    } else return;
    repaint();
  }

  function back() {
    if (flow.inspected) {
      flow.inspected = null;
      scrollToActor = ACTIVE;
    } else if (flow.phase === 'idle') {
      if (typeof BoardNavigation !== 'undefined') BoardNavigation.openMenu();
      return;
    } else if (flow.phase === 'target_preview') {
      flow.target = null;
      flow.phase = 'target_select';
      flow.approvedTargetVersion = null;
    } else if (flow.phase === 'target_select' || flow.phase === 'self_preview') {
      flow.target = null;
      flow.phase = 'action';
    } else reset(flow.attackMode);
    repaint();
  }

  function handleRune(slot) {
    if (!flow) reset();
    if (slot === 26 || slot === 27) { browse(slot === 26 ? -1 : 1); return true; }
    if (slot === 29) { back(); return true; }
    if (slot === 28) {
      if (flow.inspected) advanceInspection();
      else confirm();
      return true;
    }
    if (!COMBAT_ACTIONS[slot]) return false;
    flow.slot = slot;
    state.combatSlot = slot;
    flow.phase = 'action';
    flow.inspected = null;
    flow.target = null;
    flow.confirmedTarget = null;
    flow.approvedTargetVersion = null;
    repaint();
    return true;
  }

  function advanceInspection() {
    if (flow.effectPage + 1 < combatActor(flow.inspected).effects.length) flow.effectPage += 1;
    else { flow.inspected = null; flow.effectPage = 0; scrollToActor = ACTIVE; }
    repaint();
  }

  function afterRender() {
    const list = document.querySelector('.cf-initiative-list');
    if (!list) return;
    list.scrollTop = savedScroll;
    if (!scrollToActor) return;
    const row = list.querySelector(`[data-combat-actor="${scrollToActor}"]`);
    if (row) {
      const boundary = list.getBoundingClientRect();
      const rect = row.getBoundingClientRect();
      if (rect.top < boundary.top) list.scrollTop -= boundary.top - rect.top;
      else if (rect.bottom > boundary.bottom) list.scrollTop += rect.bottom - boundary.bottom;
    }
    savedScroll = list.scrollTop;
    scrollToActor = null;
  }

  function action(name) {
    if (name === 'combat-back') { back(); return true; }
    if (name === 'combat-use') { confirm(); return true; }
    return false;
  }

  function getState() { return {...flow, active:ACTIVE, order:[...ORDER]}; }

  reset();
  return {reset, listHtml, panelHtml, controlsHtml, targetMockHtml, handleRune, selectTarget, selectActor, setAttackMode, setAttackConditions, afterRender, action, getState};
})();
