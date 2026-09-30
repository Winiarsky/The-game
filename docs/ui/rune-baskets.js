/* Standalone tabletop prototype. No live game state or hardware is accessed.
 * Public test API: window.RuneBaskets; state is serializable and versioned.
 * Costs are committed only by the review transition; k4 input is never random.
 */
(() => {
  'use strict';
  const D = window.RUNE_BASKET_DATA;
  if (!D) { document.getElementById('app').textContent = 'Brak danych kart. Uruchom generator kart koszyków run.'; return; }
  const VERSION = 1, KEY = 'rune-baskets-v01-session', WIDTH = 9, HEIGHT = 7;
  const categories = D.categories, heroes = D.heroes, panel = D.panel;
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clone = value => JSON.parse(JSON.stringify(value));
  const hero = id => heroes.find(h => h.id === id);
  const category = id => categories.find(c => c.id === id);
  const runeCategory = rune => categories.find(c => c.runes.includes(rune));
  const slot = name => panel.find(p => p.name === name)?.slot;
  const icon = name => { const p = typeof name === 'number' ? panel.find(p => p.slot === name) : panel.find(p => p.name === name); return p ? `<svg class="rune" viewBox="0 0 24 24" aria-hidden="true"><path d="${esc(p.path)}"/></svg>` : ''; };
  const counts = list => [...new Set(list)].map(r => [r, list.filter(v => v === r).length]);
  const distance = (a, b) => Math.max(Math.abs(a.x - b.x), Math.abs(a.y - b.y));
  const color = id => `style="--category-color:var(--${esc(id)})"`;
  const positions = [[3,2],[2,2],[3,3],[2,3],[1,2],[1,3]];
  const phaseNames = {party:'Wybierz drużynę',prepare:'Przygotuj własne runy',idle:'Wybierz akcję na planszy',target:'Wskaż cel na planszy',base:'Wybierz własną runę',surcharge:'Wybierz runy dopłaty skazy',resonance:'Rezonans i zatwierdzenie',support:'Wskaż wspierającego sojusznika',review:'Sprawdź i zatwierdź',move:'Wskaż docelowe pole',end_turn:'Zakończyć turę?',focus_pick:'Wybierz rozładowane miejsca',recharge:'Wpisz wynik fizycznej k4',resolution:'Rozstrzygnij przy stole',push:'Wskaż pole odrzutu',tune_pick:'Wybierz strojoną runę',tune_symbol:'Wybierz nowy symbol',result:'Akcja rozstrzygnięta'};
  function fresh() {
    return {version:VERSION,revision:0,phase:'party',party:['garran','mira','lorian'],active:'garran',round:1,
      resources:{},actors:{},budgets:{ordinary:true,special:true,movement:6},preparations:Object.fromEntries(heroes.map(h => [h.id,clone(h.preparation)])),
      prepIndex:0,prepCategory:categories[0].id,pending:null,regenUsed:{},onceUsed:[],echo:{},journal:[],rechargeQueue:[],lastResult:'',infoHero:null};
  }
  let state = fresh();
  function validate(s) {
    if (!s || s.version !== VERSION || !Number.isInteger(s.revision) || !phaseNames[s.phase] || !Array.isArray(s.party) || s.party.length > 6 || new Set(s.party).size !== s.party.length || s.party.some(id => !hero(id))) return false;
    if (!s.preparations || !s.resources || !s.actors || !Array.isArray(s.journal) || !Array.isArray(s.onceUsed) || !s.regenUsed || !Array.isArray(s.rechargeQueue)) return false;
    for (const h of heroes) for (const c of categories) {
      const prepared = s.preparations[h.id]?.[c.id];
      if (!Array.isArray(prepared) || prepared.length > h.capacities[c.id] || prepared.some(r => !c.runes.includes(r))) return false;
    }
    if (!['party','prepare'].includes(s.phase)) {
      if (s.party.length < 3 || s.party.length > 6 || !s.party.includes(s.active) || !Number.isInteger(s.round) || s.round < 1) return false;
      for (const id of s.party) {
        if (!s.actors[id] || !Number.isInteger(s.actors[id].x) || !Number.isInteger(s.actors[id].y) || s.actors[id].x < 0 || s.actors[id].x >= WIDTH || s.actors[id].y < 0 || s.actors[id].y >= HEIGHT || typeof s.actors[id].reaction !== 'boolean') return false;
        for (const c of categories) {
          const b = s.resources[id]?.[c.id];
          if (!b || b.capacity !== hero(id).capacities[c.id] || !Array.isArray(b.charged) || b.charged.length > b.capacity || b.charged.some(r => !c.runes.includes(r))) return false;
        }
      }
      if (!s.budgets || typeof s.budgets.ordinary !== 'boolean' || typeof s.budgets.special !== 'boolean' || !Number.isInteger(s.budgets.movement) || s.budgets.movement < 0) return false;
      if (s.phase === 'recharge' && (!s.rechargeQueue.length || !Number.isInteger(s.die) || s.die < 1 || s.die > 4)) return false;
      for (const q of s.rechargeQueue) if (!s.party.includes(q.actor) || !category(q.category)) return false;
      for (const id of s.party) for (const c of categories) if (s.rechargeQueue.filter(q => q.actor === id && q.category === c.id).length > s.resources[id][c.id].capacity-s.resources[id][c.id].charged.length) return false;
      if (!['idle','result','end_turn','recharge'].includes(s.phase) && (!s.pending || s.pending.actor !== s.active)) return false;
      if (s.pending?.kind === 'card' && !hero(s.pending.actor)?.cards.some(c => c.id === s.pending.cardId)) return false;
      if (s.phase === 'surcharge' && !Array.isArray(s.pending.surcharge)) return false;
      if (['resolution','push','tune_pick','tune_symbol'].includes(s.phase) && !s.pending.committed) return false;
    }
    return true;
  }
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify(state)); $('save-status').textContent = 'Zapisano w tej przeglądarce'; }
    catch (_) { $('save-status').textContent = 'Zapis lokalny niedostępny'; }
  }
  function restore() {
    try { const value = JSON.parse(localStorage.getItem(KEY)); if (validate(value)) { state = value; return true; } }
    catch (_) { /* An incompatible or incomplete save never refills a live encounter. */ }
    return false;
  }
  function log(text) { state.journal.unshift(`R${state.round} · ${text}`); state.journal = state.journal.slice(0,70); }
  function notice(text) { $('toast').textContent = text; $('toast').hidden = false; clearTimeout(notice.timer); notice.timer = setTimeout(() => { $('toast').hidden = true; }, 3500); }
  function update() { state.revision += 1; save(); render(); }
  function run(fn, expected) {
    if (expected !== undefined && expected !== state.revision) { notice('Ten widok jest już nieaktualny. Użyj bieżącego wyboru.'); return false; }
    const before = clone(state);
    try { const accepted = fn(); if (accepted === false) return false; if (!validate(state)) throw new Error('Stan koszyków nie spełnia zasad.'); update(); return true; }
    catch (e) { state = before; notice(e.message); render(); return false; }
  }
  function actor(id = state.active) { return state.actors[id]; }
  function healingPower(id) { return ['second_wind','healing_word'].includes(id); }
  function turnMovement(id) { const full = Math.floor((hero(id).speed || 30)/5); return id === 'garran' && Object.values(state.actors).some(a => a.enemy && a.hp > 0 && distance(actor(id),a) <= 1) ? Math.floor(full/2) : full; }
  function bucket(id, cat) { return state.resources[id][cat]; }
  function empty(id, cat) { const b = bucket(id,cat); return b.capacity - b.charged.length; }
  function cardFor(p = state.pending) { return p && hero(p.actor)?.cards.find(c => c.id === p.cardId); }
  function resonanceFor(p = state.pending) { return cardFor(p)?.resonances.find(r => r.id === p.resonance); }
  function costBudget(card, p = state.pending) { return resonanceFor(p)?.budget || card.budget; }
  function canBudget(card, p = null) {
    if (!actor() || actor().hp <= 0) return false;
    const b = costBudget(card,p);
    return (!b.includes('S') || state.budgets.special) && (!b.includes('A') || state.budgets.ordinary) && (!b.includes('M') || state.budgets.movement === (state.budgets.maximumMovement ?? Math.floor((hero(state.active).speed || 30)/5))) && (!b.includes('R') || actor().reaction) && (!card.once || !state.onceUsed.includes(`${state.active}:${card.id}`));
  }
  function canCard(card) { return canBudget(card) && bucket(state.active,card.category).charged.length > 0 && (card.effect?.type !== 'hidden_attack' || actor().hidden); }
  function consume(id,rune) { const c = runeCategory(rune); const list = c && bucket(id,c.id).charged; const i = list?.indexOf(rune); if (!list || i < 0) throw new Error(`${hero(id).name}: brak naładowanej runy ${rune}.`); list.splice(i,1); }
  function spendBudget(card) {
    const b = costBudget(card);
    if (b.includes('S')) state.budgets.special = false;
    if (b.includes('A')) state.budgets.ordinary = false;
    if (b.includes('M')) state.budgets.movement = 0;
    if (b.includes('R')) actor().reaction = false;
  }
  function living(id) { return actor(id) && actor(id).hp > 0; }
  function eligibleSupport(r = resonanceFor()) {
    if (!r) return [];
    return state.party.filter(id => id !== state.active && living(id) && actor(id).reaction && distance(actor(id),actor()) <= 3 && bucket(id,runeCategory(r.rune).id).charged.includes(r.rune));
  }
  function remainingOwn(p = state.pending) {
    const runes = categories.flatMap(c => bucket(p.actor,c.id).charged);
    for (const r of [p.base,...(p.surcharge || [])].filter(Boolean)) { const i = runes.indexOf(r); if (i >= 0) runes.splice(i,1); }
    return runes;
  }
  function ownsResonance(r) { return !!r && runeCategory(r.rune)?.id !== cardFor()?.category && remainingOwn().includes(r.rune); }
  function surchargeCount(p = state.pending) {
    const c = cardFor(p), spec = hero(p?.actor)?.flaw?.surcharge;
    if (!c || !spec) return 0;
    const allies = state.party.filter(id => id !== p.actor && living(id));
    if (spec.condition === 'adjacent_injured_ally') return c.category === spec.power_category && allies.some(id => distance(actor(p.actor),actor(id)) <= 1 && actor(id).hp*2 < actor(id).maxHp) ? 1 : 0;
    if (spec.condition === 'isolated') return allies.some(id => distance(actor(p.actor),actor(id)) <= 2) ? 0 : 1;
    if (spec.condition === 'repeat_power') return state.echo?.[p.actor]?.id === c.id ? Math.min(spec.max,state.echo[p.actor].count) : 0;
    if (spec.condition === 'ally_adjacent_to_target') { const target = typeof p.target === 'string' ? actor(p.target) : p.target; return target && (!spec.cards || spec.cards.includes(c.id)) && allies.some(id => distance(actor(id),target) <= 1) ? 1 : 0; }
    return 0;
  }
  function afterBase() { const p = state.pending; p.surcharge = []; state.phase = surchargeCount() ? 'surcharge' : 'resonance'; }
  function afterTarget() {
    const p = state.pending, c = cardFor();
    if (!c) { state.phase = 'review'; return; }
    const distinct = [...new Set(bucket(p.actor,c.category).charged)];
    if (!distinct.length) throw new Error('Brak własnej runy podstawowej kategorii.');
    p.base = distinct.length === 1 ? distinct[0] : null; p.autoBase = distinct.length === 1;
    if (p.autoBase) afterBase(); else state.phase = 'base';
  }
  function canResonance(r) { return runeCategory(r.rune)?.id !== cardFor()?.category && (ownsResonance(r) || eligibleSupport(r).length > 0) && canBudget(cardFor(),{...state.pending,resonance:r.id}); }
  function validTarget(idOrPosition, p = state.pending) {
    if (!p) return false;
    const card = cardFor(p), type = card?.target || (p.kind === 'item' ? 'self' : 'enemy');
    const range = card?.range ?? (p.kind === 'attack' && p.actor === 'erynd' ? 8 : 1);
    if (type === 'position' || type === 'area') return !!idOrPosition && typeof idOrPosition === 'object' && Number.isInteger(idOrPosition.x) && Number.isInteger(idOrPosition.y) && idOrPosition.x >= 0 && idOrPosition.x < WIDTH && idOrPosition.y >= 0 && idOrPosition.y < HEIGHT && distance(actor(p.actor),idOrPosition) <= range;
    const target = actor(idOrPosition);
    if (!target || (target.hp <= 0 && !(type === 'ally' && healingPower(card?.id))) || distance(actor(p.actor),target) > range) return false;
    if (type === 'self') return idOrPosition === p.actor;
    return type === 'ally' ? state.party.includes(idOrPosition) && (idOrPosition !== p.actor || !!card.allow_self) : target.enemy;
  }
  function targetName(p = state.pending) { return p?.target && typeof p.target === 'object' ? `pole ${p.target.x+1}, ${p.target.y+1}` : actor(p?.target)?.name || '—'; }
  function actionLabel(p = state.pending) { return cardFor(p)?.name || ({attack:'Zwykły atak',item:'Przedmiot: mikstura',focus:'Skupienie',move:'Ruch'}[p?.kind] || 'Akcja'); }
  function startCombat(options = {}) {
    return run(() => {
      const party = options.party || state.party;
      if (party.length < 3 || party.length > 6 || new Set(party).size !== party.length || party.some(id => !hero(id))) throw new Error('Wybierz od 3 do 6 różnych bohaterów.');
      const preparations = clone(state.preparations);
      state = {...fresh(),preparations,party:[...party],phase:'idle',active:options.active || party[0],revision:state.revision};
      party.forEach((id,i) => {
        const h = hero(id), [x,y] = positions[i];
        state.resources[id] = Object.fromEntries(categories.map(c => { const prepared = preparations[id][c.id]; if (prepared.length !== h.capacities[c.id]) throw new Error(`${h.name}: uzupełnij ${c.name}.`); return [c.id,{capacity:h.capacities[c.id],charged:[...prepared]}]; }));
        state.actors[id] = {x,y,hp:h.hp,maxHp:h.hp,reaction:true,hidden:false,moved:false,name:h.name,armor:0};
      });
      state.actors.enemy_1 = {x:4,y:2,hp:36,maxHp:36,reaction:true,name:'Drwal',enemy:true};
      state.actors.enemy_2 = {x:6,y:4,hp:28,maxHp:28,reaction:true,name:'Procarz',enemy:true};
      state.budgets.movement = turnMovement(state.active); state.budgets.maximumMovement = state.budgets.movement;
      log('Walka przygotowana. Każdy bohater ma własne, pełne koszyki.');
    });
  }
  function toggleHero(id) {
    return run(() => { if (state.phase !== 'party' || !hero(id)) return false; if (state.party.includes(id)) state.party = state.party.filter(h => h !== id); else if (state.party.length < 6) state.party.push(id); else throw new Error('Drużyna może liczyć najwyżej 6 bohaterów.'); state.active = id; });
  }
  function beginPreparation() {
    if (state.party.length < 3 || state.party.length > 6) throw new Error('Wybierz od 3 do 6 bohaterów.');
    state.phase = 'prepare'; state.prepIndex = 0; state.active = state.party[0]; state.prepCategory = categories[0].id;
  }
  function chooseAction(id) {
    return run(() => {
      if (state.phase !== 'idle') return false;
      const card = hero(state.active).cards.find(c => c.id === id);
      if (!card || !canCard(card)) throw new Error('Ta moc wymaga własnej runy i wolnego budżetu.');
      state.pending = {kind:'card',actor:state.active,cardId:id,target:null,base:null,surcharge:[],resonance:null,payer:null,committed:false};
      state.phase = 'target';
      if (card.target === 'self') { state.pending.target = state.active; afterTarget(); }
    });
  }
  function startOrdinary(kind) {
    if (state.phase !== 'idle' || !living(state.active)) return false;
    if (kind === 'move') { if (!state.budgets.movement) return false; state.pending = {kind,actor:state.active,target:null}; state.phase = 'move'; return; }
    if (!state.budgets.ordinary) return false;
    state.pending = {kind,actor:state.active,target:kind === 'item' ? state.active : null,committed:false}; state.phase = kind === 'item' ? 'review' : 'target';
  }
  function focusStart() {
    if (!state.budgets.special || !categories.some(c => empty(state.active,c.id))) return false;
    state.pending = {kind:'focus',actor:state.active,selections:[],limit:2,recipient:state.active,committed:false}; state.phase = 'focus_pick';
  }
  function fieldActor(x,y) { return Object.keys(state.actors).find(id => actor(id).x === x && actor(id).y === y && (actor(id).hp > 0 || state.party.includes(id))); }
  function isFlanking(id) {
    const own = actor(id);
    return Object.values(state.actors).filter(a => a.enemy && a.hp > 0 && distance(own,a) === 1).some(enemy => state.party.some(other => {
      const ally = actor(other);
      return other !== id && ally.hp > 0 && distance(ally,enemy) === 1 && (own.x-enemy.x)*(ally.x-enemy.x) + (own.y-enemy.y)*(ally.y-enemy.y) < 0;
    }));
  }
  function validPush(x,y) {
    const p = state.pending, target = actor(p.target), origin = p.pushOrigin;
    if (!origin || fieldActor(x,y)) return false;
    const dx = Math.sign(origin.x-actor().x), dy = Math.sign(origin.y-actor().y);
    for (let n=1;n<=p.pushDistance;n++) {
      const px = origin.x+dx*n, py = origin.y+dy*n;
      if (px < 0 || py < 0 || px >= WIDTH || py >= HEIGHT || (fieldActor(px,py) && fieldActor(px,py) !== p.target)) break;
      if (x === px && y === py) return true;
    }
    return false;
  }
  function legalField(x,y) {
    if (!Number.isInteger(x) || !Number.isInteger(y) || x < 0 || x >= WIDTH || y < 0 || y >= HEIGHT) return false;
    const id = fieldActor(x,y);
    if (state.phase === 'support') return eligibleSupport().includes(id);
    if (state.phase === 'target') return validTarget(['area','position'].includes(cardFor()?.target) ? {x,y} : id);
    if (state.phase === 'move') return !id && distance(actor(),{x,y}) > 0 && distance(actor(),{x,y}) <= state.budgets.movement;
    if (state.phase === 'push') return validPush(x,y);
    return false;
  }
  function selectField(x,y,revision) {
    return run(() => {
      if (!legalField(x,y)) return false;
      const id = fieldActor(x,y);
      if (state.phase === 'support') { state.pending.payer = id; state.phase = 'resonance'; }
      else if (state.phase === 'push') state.pending.pushTarget = {x,y};
      else { const wasTarget = state.phase === 'target'; state.pending.target = state.phase === 'move' || ['area','position'].includes(cardFor()?.target) ? {x,y} : id; if (wasTarget) afterTarget(); }
    },revision);
  }
  function chooseBase(rune) {
    const p = state.pending, card = cardFor();
    if (runeCategory(rune)?.id !== card.category || !bucket(p.actor,card.category).charged.includes(rune)) return false;
    p.base = rune; afterBase();
  }
  function chooseResonance(id) {
    const p = state.pending, r = cardFor().resonances.find(v => v.id === id);
    if (!r || !canResonance(r)) return false;
    if (p.resonance === id) { p.resonance = null; p.payer = null; return; }
    p.resonance = id; p.payer = ownsResonance(r) ? state.active : null;
    if (!p.payer) state.phase = 'support';
  }
  function selectCharge(cat) {
    const p = state.pending, id = p.recipient, selected = p.selections.filter(c => c === cat).length;
    const available = p.allowed ? p.allowed[cat] : empty(id,cat);
    if (p.selections.length >= p.limit || selected >= available || selected >= empty(id,cat)) return false;
    p.selections.push(cat);
  }
  function queueCharges(id, list, reason) {
    list.forEach(cat => state.rechargeQueue.push({actor:id,category:cat,reason}));
  }
  function startRecharge(after = 'result') {
    if (!state.rechargeQueue.length) { state.phase = after; return; }
    state.phase = 'recharge'; state.afterRecharge = after; state.die = 1;
  }
  function triggerEvent(id,eventId) {
    const rule = hero(id)?.regeneration.find(r => r.event === eventId || r.id === eventId);
    if (!rule || !living(id)) return false;
    const key = `${id}:${rule.id}`;
    if (state.regenUsed[key] === state.round) return false;
    state.regenUsed[key] = state.round;
    const amount = Math.min(rule.count || 1,empty(id,rule.category));
    if (amount) { queueCharges(id,Array(amount).fill(rule.category),rule.label); log(`${hero(id).name}: ${rule.label} · ${amount} × k4.`); }
    else log(`${hero(id).name}: ${rule.label} · pełny koszyk, limit tej rundy zużyty.`);
    return true;
  }
  function recordEvent(id,eventId) {
    return run(() => {
      if (state.phase !== 'idle' || !state.party.includes(id)) return false;
      if (!triggerEvent(id,eventId)) throw new Error('Ten warunek wykorzystano już w tej rundzie.');
      startRecharge('idle');
    });
  }
  function validatePayment() {
    const p = state.pending, card = cardFor();
    if (!card || p.committed || !validTarget(p.target) || !canBudget(card,p) || (card.effect?.type === 'hidden_attack' && !actor().hidden)) throw new Error('Akcja, jej warunek lub cel nie są już dostępne.');
    if (runeCategory(p.base)?.id !== card.category || !bucket(p.actor,card.category).charged.includes(p.base)) throw new Error('Podstawę opłać własną naładowaną runą odpowiedniej kategorii.');
    const r = resonanceFor();
    if (p.resonance && (!r || runeCategory(r.rune)?.id === card.category)) throw new Error('Rezonans musi pochodzić z innej kategorii.');
    if (r && !(p.payer === p.actor ? ownsResonance(r) : eligibleSupport(r).includes(p.payer))) throw new Error('Płatnik nie może już opłacić Rezonansu.');
    if ((p.surcharge || []).length !== surchargeCount(p)) throw new Error('Wybierz wszystkie własne runy wymagane przez skazę.');
    const available = categories.flatMap(c => bucket(p.actor,c.id).charged);
    for (const rune of [p.base,...(p.surcharge || []),...(r && p.payer === p.actor ? [r.rune] : [])]) { const i = available.indexOf(rune); if (i < 0) throw new Error('Nie można użyć jednej runy dwukrotnie w tej płatności.'); available.splice(i,1); }
  }
  function commit() {
    const p = state.pending, card = cardFor();
    if (card) {
      validatePayment();
      p.wasHidden = actor().hidden;
      p.allowed = Object.fromEntries(categories.map(c => [c.id,empty(typeof p.target === 'string' && state.party.includes(p.target) ? p.target : p.actor,c.id)]));
      consume(p.actor,p.base);
      for (const rune of p.surcharge || []) consume(p.actor,rune);
      const r = resonanceFor();
      if (r) { consume(p.payer,r.rune); if (p.payer !== p.actor) actor(p.payer).reaction = false; }
      spendBudget(card);
      if (card.once) state.onceUsed.push(`${p.actor}:${card.id}`);
      log(`${hero(p.actor).name}: ${card.name}; ${p.base}${p.surcharge?.length ? ` + skaza: ${p.surcharge.join(', ')}` : ''}${r ? ` + ${r.rune} (${hero(p.payer).name}${p.payer !== p.actor ? ', reakcja' : ''})` : ''}.`);
      state.echo ||= {}; state.echo[p.actor] = {id:card.id,count:state.echo[p.actor]?.id === card.id ? state.echo[p.actor].count+1 : 1};
      p.committed = true;
      if (r && p.payer === 'lorian' && p.payer !== p.actor) triggerEvent(p.payer,'ally_support');
      if (card.effect?.type === 'recharge') {
        p.recipient = p.target; p.selections = []; p.limit = (card.effect.count || 2) + (r?.effect?.extraCharges || 0);
        if (!Object.values(p.allowed).some(Boolean)) { state.lastResult = 'Przed zapłatą cel nie miał rozładowanych miejsc.'; finishAction(); }
        else state.phase = 'focus_pick';
        return;
      }
      if (card.effect?.type === 'tune') { p.recipient = p.target; state.phase = 'tune_pick'; return; }
    } else {
      if (p.committed || !state.budgets.ordinary || !validTarget(p.target)) throw new Error('Zwykła akcja lub jej cel nie są już dostępne.');
      p.wasHidden = actor().hidden; p.committed = true; state.budgets.ordinary = false; log(`${hero(p.actor).name}: ${actionLabel()}.`);
    }
    p.success = true; p.amount = 0; state.phase = 'resolution';
  }
  function finishAction() {
    state.pending = null;
    startRecharge('result');
  }
  function resolvePhysical() {
    const p = state.pending, card = cardFor(), r = resonanceFor(), target = typeof p.target === 'string' ? actor(p.target) : null;
    if (!p.committed || p.resolved) return false;
    p.resolved = true;
    const amount = Math.max(0,Math.min(99,Number(p.amount) || 0)), success = p.success;
    const healing = p.kind === 'item' || healingPower(p.cardId);
    let effective = 0;
    if (success && target && amount) {
      if (healing) { effective = Math.min(amount,target.maxHp-target.hp); target.hp += effective; }
      else if (target.enemy) { effective = Math.min(amount,target.hp); target.hp -= effective; }
    }
    const isAttack = p.kind === 'attack' || ['push_attack','hidden_attack'].includes(card?.effect?.type) || card?.category === 'offense';
    if (success && isAttack && target?.enemy) {
      if (p.actor === 'brakka' && distance(actor(),target) <= 1) triggerEvent(p.actor,'melee_hit');
      if (p.actor === 'mira' && p.wasHidden) triggerEvent(p.actor,'hidden_hit');
      if (p.actor === 'erynd' && actor().moved && distance(actor(),target) > 1) triggerEvent(p.actor,'ranged_hit_after_move');
    }
    if (success && healing && effective > 0 && p.actor === 'dagna' && p.target !== p.actor) triggerEvent(p.actor,'effective_heal');
    if (isAttack) actor().hidden = !!(r?.effect?.retainHidden && p.wasHidden);
    const afterAttack = success || card?.effect?.type === 'hidden_attack';
    if (afterAttack && r?.effect?.armor) { actor().armor = r.effect.armor; actor().armorUntilTurn = true; }
    if (afterAttack && r?.effect?.mark && target) target.markedBy = p.actor;
    state.lastResult = `${actionLabel()}: ${success ? 'powodzenie' : 'niepowodzenie'}${effective ? ` · ${healing ? 'odzyskano' : 'zadano'} ${effective} PW` : ''}.`;
    log(state.lastResult);
    if (success && card?.effect?.type === 'push_attack' && target && target.hp > 0) {
      p.pushDistance = (card.effect.push || 1) + (r?.effect?.push || 0); p.pushOrigin = {x:target.x,y:target.y}; p.pushTarget = null;
      state.phase = 'push';
      if (Array.from({length:WIDTH*HEIGHT},(_,i) => validPush(i%WIDTH,Math.floor(i/WIDTH))).some(Boolean)) return;
      log('Brak wolnego pola na linii odrzutu. Cel pozostaje na miejscu.');
    }
    finishAction();
  }
  function nextTurn() {
    const i = state.party.indexOf(state.active), next = (i+1)%state.party.length;
    if (next === 0) { state.round++; state.party.forEach(id => { actor(id).reaction = true; }); log('Nowa runda: wszyscy bohaterowie odzyskują reakcję.'); }
    state.active = state.party[next]; const movement = turnMovement(state.active); state.budgets = {ordinary:true,special:true,movement,maximumMovement:movement};
    actor().moved = false; actor().armor = 0; actor().armorUntilTurn = false;
    state.pending = null; state.phase = 'idle'; log(`Tura: ${hero(state.active).name}. Przeciwników rozstrzygnij przy stole między turami.`);
  }
  function confirm() {
    const p = state.pending;
    if (state.phase === 'party') return beginPreparation();
    if (state.phase === 'prepare') {
      const id = state.party[state.prepIndex];
      if (categories.some(c => state.preparations[id][c.id].length !== hero(id).capacities[c.id])) throw new Error('Uzupełnij dokładnie wszystkie cztery koszyki tej postaci.');
      if (state.prepIndex < state.party.length-1) { state.prepIndex++; state.active = state.party[state.prepIndex]; state.prepCategory = categories[0].id; }
      else { const options = {party:[...state.party]}; return startCombat(options); }
    } else if (state.phase === 'target') {
      if (!validTarget(p.target)) throw new Error('Wskaż legalny cel na planszy.');
      const card = cardFor();
      if (!card) { state.phase = 'review'; return; }
      afterTarget();
    } else if (state.phase === 'base') {
      if (!p.base) throw new Error('Wybierz własną runę.'); afterBase();
    } else if (state.phase === 'resonance') {
      if (p.resonance && !p.payer) { state.phase = 'support'; return; } commit();
    } else if (state.phase === 'support') {
      if (!eligibleSupport().includes(p.payer)) throw new Error('Wskaż sojusznika do 3 pól z runą i reakcją.'); state.phase = 'resonance';
    } else if (state.phase === 'review') commit();
    else if (state.phase === 'move') {
      if (!p.target || !legalField(p.target.x,p.target.y)) throw new Error('Wskaż wolne pole w zasięgu ruchu.');
      const before = isFlanking(state.active), steps = distance(actor(),p.target);
      actor().x = p.target.x; actor().y = p.target.y; actor().moved = true; state.budgets.movement -= steps;
      log(`${hero(state.active).name}: ruch o ${steps} pól.`);
      if (state.active === 'mira' && !before && isFlanking(state.active)) triggerEvent(state.active,'flank_entry');
      state.pending = null; startRecharge('idle');
    } else if (state.phase === 'focus_pick') {
      if (!p.selections.length) throw new Error('Wybierz co najmniej jedno rozładowane miejsce.');
      if (!p.committed) { if (!state.budgets.special) throw new Error('Brak akcji specjalnej.'); state.budgets.special = false; p.committed = true; log(`${hero(p.actor).name}: Skupienie, ${p.selections.length} runy.`); }
      queueCharges(p.recipient,p.selections,actionLabel()); state.lastResult = `${actionLabel()}: ładowanie zakończone.`; state.pending = null; startRecharge();
    } else if (state.phase === 'recharge') {
      const q = state.rechargeQueue[0], c = category(q.category);
      if (!q || !Number.isInteger(state.die) || state.die < 1 || state.die > 4) throw new Error('Wpisz wynik k4 od 1 do 4.');
      if (empty(q.actor,q.category) <= 0) throw new Error('Koszyk jest już pełny.');
      const rune = c.runes[state.die-1]; bucket(q.actor,q.category).charged.push(rune); state.rechargeQueue.shift();
      log(`${hero(q.actor).name}: k4 = ${state.die} → ${rune} (${c.name}).`);
      if (state.rechargeQueue.length) state.die = 1; else state.phase = state.afterRecharge || 'result';
    } else if (state.phase === 'resolution') resolvePhysical();
    else if (state.phase === 'push') {
      if (!p.pushTarget || !validPush(p.pushTarget.x,p.pushTarget.y)) throw new Error('Wskaż podświetlone pole odrzutu.');
      const moved = distance(p.pushOrigin,p.pushTarget); actor(p.target).x = p.pushTarget.x; actor(p.target).y = p.pushTarget.y;
      log(`${targetName()}: odrzut o ${moved} pól.`); state.lastResult += ` Odrzut: ${moved} pól.`; finishAction();
    } else if (state.phase === 'tune_pick') { if (!p.tuneRune) throw new Error('Wybierz naładowaną runę celu.'); state.phase = 'tune_symbol'; }
    else if (state.phase === 'tune_symbol') {
      if (!p.tuneResult || runeCategory(p.tuneResult).id !== runeCategory(p.tuneRune).id) throw new Error('Nowy symbol musi należeć do tej samej kategorii.');
      consume(p.recipient,p.tuneRune); bucket(p.recipient,runeCategory(p.tuneResult).id).charged.push(p.tuneResult);
      state.lastResult = `${hero(p.recipient).name}: ${p.tuneRune} → ${p.tuneResult}.`; log(state.lastResult); finishAction();
    } else if (state.phase === 'end_turn') nextTurn();
    else if (state.phase === 'result') { state.phase = 'idle'; state.lastResult = ''; }
    else return false;
  }
  function back() {
    const p = state.pending;
    if (state.phase === 'prepare') { const list = state.preparations[state.active][state.prepCategory]; if (list.length) list.pop(); return; }
    if (state.phase === 'review') { state.phase = cardFor() ? 'resonance' : 'target'; return; }
    if (state.phase === 'support') { p.payer = ownsResonance(resonanceFor()) ? state.active : null; if (!p.payer) p.resonance = null; state.phase = 'resonance'; return; }
    if (state.phase === 'resonance') { p.resonance = null; p.payer = null; if (p.surcharge?.length) { p.surcharge.pop(); state.phase = 'surcharge'; } else state.phase = p.autoBase ? 'target' : 'base'; return; }
    if (state.phase === 'surcharge') { if (p.surcharge.length) p.surcharge.pop(); else state.phase = p.autoBase ? 'target' : 'base'; return; }
    if (state.phase === 'base') { p.base = null; state.phase = 'target'; return; }
    if (state.phase === 'focus_pick') { if (p.selections.length) p.selections.pop(); else if (!p.committed) { state.pending = null; state.phase = 'idle'; } return; }
    if (state.phase === 'tune_symbol') { p.tuneResult = null; state.phase = 'tune_pick'; return; }
    if (['target','move','end_turn','result'].includes(state.phase)) { state.pending = null; state.phase = 'idle'; return; }
    return false;
  }
  function adjust(delta) {
    if (state.phase === 'recharge') state.die = Math.max(1,Math.min(4,state.die+delta));
    else if (state.phase === 'resolution') state.pending.amount = Math.max(0,Math.min(99,state.pending.amount+delta));
    else if (state.phase === 'prepare') { const i = categories.findIndex(c => c.id === state.prepCategory); state.prepCategory = categories[(i+delta+4)%4].id; }
    else if (state.phase === 'party') { const i = heroes.findIndex(h => h.id === state.active); state.active = heroes[(i+delta+heroes.length)%heroes.length].id; }
    else return false;
  }
  function showInfo(id = state.active) {
    const h = hero(id); if (!h) return;
    const a = actor(id), flaw = h.flaw;
    $('info-content').innerHTML = `<div class="info-head"><img class="avatar" src="${esc(h.portrait)}" alt=""><div><div class="eyebrow">Karta bohatera</div><h1>${esc(h.name)}</h1><p>${esc(h.role)}</p></div></div><div class="stats"><span><b data-stat="hp">${a ? `${a.hp}/${a.maxHp}` : h.hp}</b><small>PW</small></span><span><b data-stat="ac">${h.ac+(a?.armor || 0)}</b><small>KP</small></span><span><b>${Math.floor(h.speed/5)}</b><small>ruch w polach</small></span><span><b>${a ? a.reaction ? '✓' : '—' : '✓'}</b><small>reakcja</small></span></div><p>${a?.hidden ? 'Ukryty · ' : ''}${a?.armor ? `Premia KP +${a.armor} · ` : ''}${a?.hp === 0 ? 'Nieprzytomny · ' : ''}Pojemności: ${categories.map(c => `${c.name} ${h.capacities[c.id]}`).join(' · ')}</p><h2>Regeneracja</h2>${h.regeneration.map(r => `<p>${esc(r.label)} Naładuj ${r.count || 1} ${esc(category(r.category).name)}.</p>`).join('')}<h2>Skaza: ${esc(flaw?.name || flaw?.[0] || '')}</h2><p>${esc(flaw?.description || flaw?.body || flaw?.[1] || '')}</p><h2>Wyposażenie</h2><ul class="info-cards">${(h.equipment || []).map(e => `<li><strong>${esc(e.name)}</strong> <small>${esc(e.slot)}</small><p>${esc(e.effect || e.detail || '')}</p></li>`).join('')}</ul><h2>Moce i Rezonanse</h2><ul class="info-cards">${h.cards.map(c => `<li><strong>${esc(c.name)}</strong> <small>${esc(category(c.category)?.name)} · ${esc(c.budget)} · przycisk ${esc(c.button)}</small><p>${esc(c.description)}</p>${c.resonances.map(r => `<p><b>${esc(r.rune)}</b>: ${esc(r.description)}</p>`).join('')}</li>`).join('')}</ul>`;
    $('info-dialog').showModal();
  }
  function canConfirm() {
    const p = state.pending;
    if (state.phase === 'party') return state.party.length >= 3 && state.party.length <= 6;
    if (state.phase === 'prepare') return categories.every(c => state.preparations[state.active][c.id].length === hero(state.active).capacities[c.id]);
    if (state.phase === 'target') return validTarget(p?.target);
    if (state.phase === 'base' || state.phase === 'surcharge') return false;
    if (state.phase === 'support') return eligibleSupport().includes(p?.payer);
    if (state.phase === 'move') return !!p?.target && legalField(p.target.x,p.target.y);
    if (state.phase === 'focus_pick') return !!p?.selections.length;
    if (state.phase === 'push') return !!p?.pushTarget;
    if (state.phase === 'tune_pick') return !!p?.tuneRune;
    if (state.phase === 'tune_symbol') return !!p?.tuneResult;
    if (state.phase === 'review' || state.phase === 'resonance') { if (!cardFor()) return validTarget(p.target) && state.budgets.ordinary; try { validatePayment(); return true; } catch (_) { return false; } }
    return ['recharge','resolution','end_turn','result'].includes(state.phase);
  }
  function bindings() {
    const map = new Map(), p = state.pending;
    const put = (n,title,enabled,fn,selected=false,light='available') => map.set(n,{title,enabled:!!enabled,fn,selected,light});
    put(25,'Informacja o bohaterze',!!hero(state.active),() => showInfo(),false,'info');
    put(28,'Zatwierdź',canConfirm(),confirm,false,'control');
    put(29,'Wróć / cofnij ostatni wybór',['prepare','target','base','surcharge','resonance','support','review','move','end_turn','focus_pick','tune_symbol','result'].includes(state.phase),back,false,'control');
    put(26,'Zwiększ / następny',['party','prepare','recharge','resolution'].includes(state.phase),() => adjust(1),false,'control');
    put(27,'Zmniejsz / poprzedni',['party','prepare','recharge','resolution'].includes(state.phase),() => adjust(-1),false,'control');
    if (state.phase === 'party') put(slot('Most'),'Dodaj / usuń wybranego bohatera',state.party.includes(state.active) || state.party.length < 6,() => { if (state.party.includes(state.active)) state.party = state.party.filter(h => h !== state.active); else state.party.push(state.active); });
    if (state.phase === 'prepare') for (const r of category(state.prepCategory).runes) put(slot(r),`Przygotuj: ${r}`,state.preparations[state.active][state.prepCategory].length < hero(state.active).capacities[state.prepCategory],() => { state.preparations[state.active][state.prepCategory].push(r); });
    if (state.phase === 'idle') {
      put(0,'Ruch',state.budgets.movement > 0 && living(state.active),() => startOrdinary('move'));
      put(1,'Zwykły atak',state.budgets.ordinary && living(state.active),() => startOrdinary('attack'));
      put(2,'Przedmiot: mikstura',state.budgets.ordinary && living(state.active),() => startOrdinary('item'));
      put(3,'Koniec tury',true,() => { state.phase = 'end_turn'; });
      put(19,'Skupienie: naładuj do 2 run',state.budgets.special && categories.some(c => empty(state.active,c.id)) && living(state.active),focusStart);
      hero(state.active).cards.forEach(c => put(c.slot,c.name,canCard(c),() => chooseAction(c.id)));
    }
    if (state.phase === 'base') for (const [r] of counts(bucket(state.active,cardFor().category).charged)) put(slot(r),`Podstawa: ${r}`,true,() => chooseBase(r),p.base === r);
    if (state.phase === 'surcharge') for (const [r] of counts(remainingOwn())) put(slot(r),`Dopłata skazy: ${r}`,true,() => { p.surcharge.push(r); if (p.surcharge.length === surchargeCount()) state.phase = 'resonance'; });
    if (state.phase === 'resonance') {
      cardFor().resonances.forEach(r => put(slot(r.rune),`${r.rune}: ${r.description}`,canResonance(r),() => chooseResonance(r.id),p.resonance === r.id));
      put(21,'Wsparcie sojusznika: wskaż figurkę',!!p.resonance && eligibleSupport().length > 0,() => { p.payer = null; state.phase = 'support'; });
    }
    if (state.phase === 'support') put(21,'Zrezygnuj ze wsparcia',true,back,true);
    if (state.phase === 'focus_pick') categories.forEach(c => put(slot(c.runes[0]),`Ładuj ${c.name}`,p.selections.length < p.limit && p.selections.filter(x => x === c.id).length < Math.min(empty(p.recipient,c.id),p.allowed?.[c.id] ?? Infinity),() => selectCharge(c.id),p.selections.includes(c.id)));
    if (state.phase === 'tune_pick') categories.forEach(c => counts(bucket(p.recipient,c.id).charged).forEach(([r]) => put(slot(r),`Zmień ${r}`,true,() => { p.tuneRune = r; },p.tuneRune === r)));
    if (state.phase === 'tune_symbol') runeCategory(p.tuneRune).runes.forEach(r => put(slot(r),`Ustaw ${r}`,true,() => { p.tuneResult = r; },p.tuneResult === r));
    return map;
  }
  function press(n,revision) {
    if ($('help-dialog').open || $('info-dialog').open) { if (n === 25 || n === 29 || n === 28) { $('help-dialog').close(); $('info-dialog').close(); return true; } return false; }
    const binding = bindings().get(Number(n));
    if (!binding?.enabled) return false;
    return run(binding.fn,revision);
  }
  function token(r,n=1,selected=false) { return `<span class="token ${selected ? 'selected' : ''}">${icon(r)}${esc(r)}${n>1 ? ` ×${n}` : ''}</span>`; }
  function buckets(id,prep=false) {
    const h = hero(id);
    return categories.map(c => {
      const list = prep ? state.preparations[id][c.id] : bucket(id,c.id).charged, cap = h.capacities[c.id], remaining = cap-list.length;
      return `<section class="bucket ${prep && state.prepCategory === c.id ? 'active' : ''}" ${color(c.id)}><div class="bucket-head">${prep ? `<button data-prep-category="${c.id}"><strong>${esc(c.name)}</strong></button>` : `<strong>${esc(c.name)}</strong>`}<small>${list.length}/${cap} ${prep ? 'przygotowane' : 'naładowane'}</small></div><div class="rune-strip">${counts(list).map(([r,n]) => token(r,n)).join('')}${remaining ? `<span class="token empty">${remaining} ${prep ? 'wolne' : 'rozładowane'}</span>` : ''}</div>${prep ? `<div class="prep-symbols">${c.runes.map(r => `<button data-prepare="${esc(r)}" data-category="${c.id}" ${list.length >= cap ? 'disabled' : ''}>${icon(r)}${esc(r)}</button>`).join('')}</div><small>${prep && state.prepCategory === c.id ? '↩ usuwa ostatnią runę · duplikaty dozwolone' : 'Wybierz kategorię, aby edytować preset'}</small>` : ''}</section>`;
    }).join('');
  }
  function renderParty() {
    $('app').innerHTML = `<div class="heading"><div><div class="eyebrow">Nowa próba · krok 1 z 2</div><h1>Zbierz drużynę</h1><p>Wybierz 3–6 spośród siedmiu bohaterów. Każdy ma własne koszyki i sposób odnowienia.</p></div><strong>${state.party.length}/6</strong></div><div class="hero-grid">${heroes.map(h => `<button class="hero-choice ${state.party.includes(h.id) ? 'selected' : ''}" data-hero="${h.id}" aria-pressed="${state.party.includes(h.id)}"><img class="avatar" src="${esc(h.portrait)}" alt=""><span><strong>${esc(h.name)}</strong><small>${esc(h.role)}</small><small>${categories.map(c => `${c.name} ${h.capacities[c.id]}`).join(' · ')}</small><span class="chosen">${state.party.includes(h.id) ? '✓ W drużynie' : 'Dodaj do drużyny'}</span></span></button>`).join('')}</div><div class="setup-footer"><p>+ / − wybiera bohatera do informacji: <b>${esc(hero(state.active)?.name)}</b> · ★ karta · Most dodaje / usuwa.</p><button class="primary" data-slot="28" ${canConfirm() ? '' : 'disabled'}>Przygotuj runy →</button></div>`;
  }
  function renderPreparation() {
    const h = hero(state.active);
    $('app').innerHTML = `<div class="heading"><div><div class="eyebrow">Krok 2 z 2 · bohater ${state.prepIndex+1}/${state.party.length}</div><h1>Przygotowanie: ${esc(h.name)}</h1><p>Preset jest gotowy. Możesz zmienić dowolne symbole, zachowując pojemność każdej kategorii.</p></div><button class="primary" data-slot="28" ${canConfirm() ? '' : 'disabled'}>${state.prepIndex === state.party.length-1 ? 'Rozpocznij walkę' : 'Następny bohater'} ✓</button></div><div class="setup-preview"><aside class="hero-summary"><img class="avatar" src="${esc(h.portrait)}" alt=""><h2>${esc(h.name)}</h2><small>${esc(h.role)}</small><p>${h.regeneration.map(r => esc(r.label)).join('<br>')}</p><button data-info="${h.id}">★ Pełna karta postaci</button></aside><div><div class="prep-categories">${buckets(h.id,true)}</div><p class="prep-note">Bieżąca kategoria: <b>${esc(category(state.prepCategory).name)}</b>. + / − przełącza kategorię. ↩ usuwa ostatnią runę; jej miejsce uzupełniasz symbolem na panelu. Możesz wybierać ten sam symbol kilka razy.</p><button data-preset>Przywróć proponowane przygotowanie tej postaci</button></div></div>`;
  }
  function boardHtml() {
    const p = state.pending;
    return `<div class="board-label"><h2>Plansza próby</h2><small>9 × 7 pól · zasięg z przekątnymi</small></div><div class="map" role="group" aria-label="Wybór figurki lub pola na planszy">${Array.from({length:WIDTH*HEIGHT},(_,i) => {
      const x = i%WIDTH, y = Math.floor(i/WIDTH), id = fieldActor(x,y), a = id && actor(id), legal = legalField(x,y);
      const selected = (state.phase === 'support' && p?.payer === id && id) || (p?.target === id && id) || (typeof p?.target === 'object' && p.target?.x === x && p.target?.y === y) || (p?.pushTarget?.x === x && p?.pushTarget?.y === y);
      return `<button class="cell ${a?.enemy ? 'enemy' : ''} ${legal ? 'legal' : ''} ${selected ? 'selected' : ''}" data-field="${x},${y}" title="${esc(a ? `${a.name}: ${a.hp}/${a.maxHp} PW` : `Pole ${x+1}, ${y+1}`)}" aria-label="${esc(a?.name || 'Puste pole')} ${x+1}, ${y+1}" ${legal ? '' : 'disabled'}>${a ? a.enemy ? `⚔<span>${esc(a.name)} ${a.hp}</span>` : `<img src="${esc(hero(id).portrait)}" alt=""><span>${esc(a.name)}</span>` : ''}</button>`;
    }).join('')}</div><p class="map-legend">${['target','support','move','push'].includes(state.phase) ? 'Turkus: legalne pola. Wskaż figurkę lub pole; ✓ zatwierdza.' : 'Wybierz akcję na dolnym panelu, aby podświetlić cele.'}</p><ul class="legal-targets">${Object.keys(state.actors).filter(id => state.phase === 'support' ? eligibleSupport().includes(id) : state.phase === 'target' && validTarget(id)).map(id => `<li class="${p?.target === id || p?.payer === id ? 'selected' : ''}">${esc(actor(id).name)} · ${actor(id).hp} PW ${p?.target === id || p?.payer === id ? '· wybrano na planszy' : ''}</li>`).join('')}</ul><div class="journal"><h3>Ostatnie zdarzenia</h3><ol>${state.journal.slice(0,7).map(t => `<li>${esc(t)}</li>`).join('')}</ol></div>`;
  }
  function preview() {
    const card = cardFor(), p = state.pending, r = resonanceFor();
    if (!p) return '';
    const push = card?.effect?.type === 'push_attack' ? (card.effect.push || 1)+(r?.effect?.push || 0) : null;
    return `<div class="card-preview"><h2>${esc(actionLabel())}</h2><small>${card ? `${esc(category(card.category).name)} · ${esc(costBudget(card))} · przycisk ${esc(card.button)}` : p.kind === 'move' ? 'Ruch zwykły' : 'Akcja zwykła'}</small><p>${esc(card?.description || (p.kind === 'item' ? 'Rozstrzygnij użycie własnej mikstury przy stole i wpisz odzyskane PW.' : 'Rozstrzygnij zwykły atak własną bronią przy stole.'))}</p>${push ? `<p class="push-preview"><b>Odrzut po powodzeniu: ${push} ${push === 1 ? 'pole' : 'pola'}${r ? ` · Rezonans ${esc(r.rune)}` : ''}.</b></p>` : ''}${r ? `<p><b>${esc(r.rune)}:</b> ${esc(r.description)}</p>` : ''}</div>`;
  }
  function controls() {
    const bs = bindings(), backEnabled = bs.get(29)?.enabled;
    return `<div class="actions">${backEnabled ? '<button data-slot="29">↩ Cofnij</button>' : ''}${!['base','surcharge'].includes(state.phase) ? `<button class="primary" data-slot="28" ${canConfirm() ? '' : 'disabled'}>✓ ${['review','resonance'].includes(state.phase) ? 'Opłać i wykonaj' : state.phase === 'recharge' ? 'Zatwierdź wynik k4' : state.phase === 'resolution' ? 'Zatwierdź rozstrzygnięcie' : 'Dalej'}</button>` : ''}</div>`;
  }
  function paymentSummary() {
    const p = state.pending, r = resonanceFor();
    return `<div class="payment-summary"><p>Cel: <b>${esc(targetName())}</b></p>${cardFor() ? `<p>Podstawa: <b>${esc(hero(p.actor).name)} → ${esc(p.base || 'wybierz runę')} (${esc(category(cardFor().category).name)})</b></p>${p.surcharge?.length ? `<p>Skaza: <b>${esc(p.surcharge.join(' + '))}</b> · ${esc(hero(p.actor).name)}</p>` : ''}<p>Rezonans: <b>${r ? `${esc(r.rune)} · płaci ${esc(hero(p.payer)?.name || 'wybierz płatnika')}${p.payer && p.payer !== p.actor ? ' + reakcja' : ''}` : 'bez Rezonansu'}</b></p>` : '<p>Koszt: własna akcja zwykła.</p>'}<small>Do zatwierdzenia nie zużyto żadnych zasobów.</small></div>`;
  }
  function decisionHtml() {
    const h = hero(state.active), p = state.pending, card = cardFor();
    let body = '';
    if (state.phase === 'idle') {
      body = `<p class="instruction">Wybierz moc jej stałym symbolem na dolnym panelu. Podstawowy koszt to <b>dowolna własna runa kategorii</b>.</p><div class="card-preview"><h2>Ruch, atak i przedmiot</h2><p>Pierwsze cztery pola panelu zawsze oznaczają ruch, zwykły atak, przedmiot i koniec tury. Nie wymagają run.</p><p>Spirala: <b>Skupienie</b> · S · naładuj do 2 run.<br>Gwiazda: opis postaci, wyposażenie i wszystkie moce.</p></div><p class="fine">Moc → figurka celu → własna runa kategorii → opcjonalny Rezonans → ✓. Możesz cofać wybory bez kosztu.</p><details class="event-controls"><summary>Fizyczne rozstrzygnięcia i warunki regeneracji</summary><p class="fine">Potwierdź tylko zdarzenie, które nastąpiło przy stole. Nie oznacza wykonania darmowej akcji.</p>${h.regeneration.map(r => `<button data-event="${esc(r.event || r.id)}" ${state.regenUsed[`${h.id}:${r.id}`] === state.round ? 'disabled' : ''}>Potwierdź zdarzenie: ${esc(r.label)}</button>`).join('')}${h.id === 'mira' ? `<button data-hidden>Potwierdź stan po teście przy stole: ${actor().hidden ? 'Mira odkryta' : 'Mira Ukryta'}</button>` : ''}<button data-injury>Obrażenia z fizycznej tury przeciwnika: −1 PW</button></details>`;
    } else if (state.phase === 'target') body = `${preview()}<p class="instruction">${card?.target === 'self' || p.kind === 'item' ? 'Cel: aktywna postać. Potwierdź ✓.' : `Wskaż ${card?.target === 'ally' ? 'figurkę sojusznika' : ['area','position'].includes(card?.target) ? 'pole' : 'figurkę przeciwnika'} na planszy. Zasięg: ${card?.range ?? (p.actor === 'erynd' ? 8 : 1)} pól.`}</p>${controls()}`;
    else if (state.phase === 'base') body = `${preview()}<p class="instruction">${h.name} opłaca podstawę własną runą <b>${esc(category(card.category).name)}</b>. Zachowaj symbol przydatny do późniejszego Rezonansu.</p><div class="choices">${counts(bucket(h.id,card.category).charged).map(([r,n]) => `<button data-slot="${slot(r)}" class="${p.base === r ? 'chosen' : ''}">${icon(r)}${esc(r)} ×${n}</button>`).join('')}</div>${controls()}`;
    else if (state.phase === 'surcharge') body = `${preview()}<p class="instruction">${esc(h.flaw.name)}: dopłać <b>${surchargeCount()} własne runy dowolnych kategorii</b>. Wybierz każdą konkretną runę.</p><p class="fine">${esc(h.flaw.description)}</p><p>Wybrano: ${esc(p.surcharge.join(' + ') || '—')}</p><div class="choices">${counts(remainingOwn()).map(([r,n]) => `<button data-slot="${slot(r)}">${icon(r)}${esc(r)} ×${n}</button>`).join('')}</div>${controls()}`;
    else if (state.phase === 'resonance') body = `${preview()}<p class="fine">Opcjonalnie wybierz jeden Rezonans. ✓ bez wyboru wykonuje wersję podstawową.</p><div class="resonance-list">${card.resonances.map(r => `<button class="resonance-choice ${p.resonance === r.id ? 'selected' : ''}" data-slot="${slot(r.rune)}" ${canResonance(r) ? '' : 'disabled'}>${icon(r.rune)}<span><strong>${esc(r.rune)} · ${ownsResonance(r) ? 'własna runa' : eligibleSupport(r).length ? 'dostępna u sojusznika' : 'brak dostępnej runy'}</strong><small>${esc(r.description)}</small></span></button>`).join('')}</div>${p.resonance ? `<button data-slot="21" ${eligibleSupport().length ? '' : 'disabled'}>${icon(21)} Wsparcie sojusznika</button>` : ''}${paymentSummary()}${controls()}`;
    else if (state.phase === 'support') body = `${preview()}<p class="instruction">Wskaż figurkę sojusznika do <b>3 pól</b>. Płaci własną runą <b>${esc(resonanceFor()?.rune)}</b> i reakcją. Podstawę nadal opłaca ${h.name}.</p><p>Płatnik: <b>${esc(hero(p.payer)?.name || 'wybierz na planszy')}</b></p>${controls()}`;
    else if (state.phase === 'review') body = `${preview()}${paymentSummary()}${controls()}`;
    else if (state.phase === 'move') body = `<p class="instruction">Wskaż wolne pole, maksymalnie ${state.budgets.movement} pól od figurki. Przekątna to jedno pole.</p><p class="fine">${p.target ? `Wybrano ${p.target.x+1}, ${p.target.y+1}: koszt ${distance(actor(),p.target)} pól.` : 'Ruch zostanie wykonany dopiero po ✓.'}</p>${controls()}`;
    else if (state.phase === 'end_turn') body = `<p class="instruction">Następny bohater: <b>${esc(hero(state.party[(state.party.indexOf(state.active)+1)%state.party.length]).name)}</b>. Niewykorzystane akcje tej tury przepadną.</p><p class="fine">Reakcja odnawia się dopiero na granicy rundy. Runy pozostają w swoich koszykach.</p>${controls()}`;
    else if (state.phase === 'focus_pick') body = `<p class="instruction">${p.committed ? esc(actionLabel()) : 'Skupienie · koszt S'}: wybierz do ${p.limit} rozładowanych miejsc postaci <b>${esc(hero(p.recipient).name)}</b>. Możesz dwa razy wskazać tę samą kategorię.</p><div class="choices">${categories.map(c => { const available = Math.min(empty(p.recipient,c.id),p.allowed?.[c.id] ?? Infinity), n = p.selections.filter(x => x === c.id).length; return `<button data-slot="${slot(c.runes[0])}" ${n >= available || p.selections.length >= p.limit ? 'disabled' : ''}>${icon(c.runes[0])}${esc(c.name)} · ${n}/${available}</button>`; }).join('')}</div><p>Wybrano: ${p.selections.map(c => esc(category(c).name)).join(' + ') || '—'}</p><p class="fine">Symbole będą określone dopiero osobnymi fizycznymi rzutami k4. ${p.allowed ? 'Koszt tej mocy i Rezonansu nie tworzy miejsc dostępnych dla tego Odzysku.' : ''}</p>${controls()}`;
    else if (state.phase === 'recharge') { const q = state.rechargeQueue[0], c = category(q.category); body = `<p class="instruction"><b>${esc(hero(q.actor).name)} · ${esc(c.name)}</b><br>Rzuć fizyczną k4 i wpisz wynik. Pozostało: ${state.rechargeQueue.length}.</p><div class="roll-number">${state.die}</div><div class="stepper"><button data-slot="27">−</button><span>k4</span><button data-slot="26">+</button></div><div class="roll-map">${c.runes.map((r,i) => `<span class="${i+1 === state.die ? 'selected' : ''}">${i+1}: ${esc(r)}</span>`).join('')}</div><p class="fine">To wpisanie fizycznego wyniku, nie wybór symbolu. Odświeżenie strony zachowuje bieżący wynik i kolejkę.</p>${controls()}`; }
    else if (state.phase === 'resolution') body = `${preview()}<p class="fine">Zasoby opłacone. Wykonaj test i pozostałe efekty z karty przy stole. Wprowadź wynik; prototyp nie rzuca za graczy.</p><div class="choices"><button data-outcome="success" class="${p.success ? 'chosen' : ''}">Powodzenie / trafienie</button><button data-outcome="failure" class="${!p.success ? 'chosen' : ''}">Niepowodzenie / pudło</button></div><p>Faktyczne obrażenia / leczenie z rozstrzygnięcia:</p><div class="stepper"><button data-slot="27">−</button><input id="physical-amount" type="number" min="0" max="99" value="${p.amount}" aria-label="Obrażenia lub leczenie"><button data-slot="26">+</button></div><p class="fine">0 dla mocy bez zmiany PW. Efekty poza PW, odrzutem tarczy i Rezonansami Ataku z cienia śledź przy stole.</p>${controls()}`;
    else if (state.phase === 'push') body = `<div class="card-preview"><h2>Odrzut: do ${p.pushDistance} pól</h2><p>${esc(targetName())}. ${p.pushDistance > 1 ? 'Rezonans Oko zwiększył odrzut z 1 do 2 pól.' : 'Podstawowy odrzut Uderzenia tarczą.'}</p></div><p class="instruction">Wskaż wolne podświetlone pole w linii od siebie. Przeszkoda lub figurka zatrzymuje odrzut.</p>${controls()}<button data-skip-push>Potwierdź przy stole: cel odporny na przesunięcie</button>`;
    else if (state.phase === 'tune_pick' || state.phase === 'tune_symbol') { const runes = state.phase === 'tune_pick' ? categories.flatMap(c => [...new Set(bucket(p.recipient,c.id).charged)]) : runeCategory(p.tuneRune).runes; body = `<p class="instruction">Strojenie: ${esc(hero(p.recipient).name)}. ${state.phase === 'tune_pick' ? 'Wskaż jedną pozostałą naładowaną runę.' : 'Ustaw nowy symbol tej samej kategorii.'}</p><div class="choices">${runes.map(r => `<button data-slot="${slot(r)}" class="${r === (state.phase === 'tune_pick' ? p.tuneRune : p.tuneResult) ? 'chosen' : ''}">${icon(r)}${esc(r)}</button>`).join('')}</div>${controls()}`; }
    else if (state.phase === 'result') body = `<p class="instruction">${esc(state.lastResult || 'Runy naładowane. Możesz kontynuować turę.')}</p><p class="fine">Koszyki i dostępne budżety odzwierciedlają zakończoną akcję.</p>${controls()}`;
    return `<div class="turn-heading"><img class="avatar" src="${esc(h.portrait)}" alt=""><div><div class="eyebrow">Runda ${state.round} · ${esc(h.name)}</div><h1>${esc(phaseNames[state.phase])}</h1></div></div><div class="budgets"><span class="budget ${state.budgets.ordinary ? '' : 'spent'}">A · zwykła</span><span class="budget ${state.budgets.special ? '' : 'spent'}">S · specjalna</span><span class="budget ${actor().reaction ? '' : 'spent'}">R · reakcja</span><span class="budget ${state.budgets.movement ? '' : 'spent'}">Ruch ${state.budgets.movement}</span>${actor().hidden ? '<span class="budget">Ukryty</span>' : ''}</div>${body}`;
  }
  function renderCombat() {
    $('app').innerHTML = `<div class="play-layout"><aside class="sidebar"><div class="party-list">${state.party.map(id => `<button class="party-row ${id === state.active ? 'active' : ''}" data-info="${id}"><img class="avatar" src="${esc(hero(id).portrait)}" alt=""><span><strong>${esc(hero(id).name)}</strong><small>${actor(id).hp}/${actor(id).maxHp} PW · ${Object.values(state.resources[id]).reduce((a,b) => a+b.charged.length,0)} run</small></span><span class="reaction ${actor(id).reaction ? '' : 'spent'}">R</span></button>`).join('')}</div><div class="eyebrow">${esc(hero(state.active).name)} · osobiste koszyki</div><div class="buckets">${buckets(state.active)}</div></aside><section class="battlefield">${boardHtml()}</section><section class="decision">${decisionHtml()}</section></div>`;
  }
  function render() {
    if (state.phase === 'party') renderParty(); else if (state.phase === 'prepare') renderPreparation(); else renderCombat();
    const bs = bindings();
    $('controller-hint').textContent = `${hero(state.active)?.name || 'Drużyna'} · ${phaseNames[state.phase]}`;
    $('board-pads').innerHTML = panel.map(p => {
      if (p.name === 'Przerwa') return `<div class="board-gap" data-slot="${p.slot}" aria-hidden="true"></div>`;
      const b = bs.get(p.slot), light = b?.enabled ? b.selected ? 'selected' : b.light : 'off';
      return `<button class="board-pad" data-slot="${p.slot}" data-light="${light}" title="${esc(p.name)}${b ? ` · ${esc(b.title)}` : ''}" aria-label="${esc(p.name)}${b ? `: ${esc(b.title)}` : ''}" ${b?.enabled ? '' : 'disabled'}>${icon(p.slot)}${p.slot === 19 ? '<small>S</small>' : ''}</button>`;
    }).join('');
    document.querySelectorAll('[data-slot]').forEach(el => { if (el.tagName !== 'BUTTON') return; const revision = state.revision; el.addEventListener('click',() => press(Number(el.dataset.slot),revision)); });
    document.querySelectorAll('[data-field]').forEach(el => { const revision = state.revision; el.addEventListener('click',() => selectField(...el.dataset.field.split(',').map(Number),revision)); });
    document.querySelectorAll('[data-hero]').forEach(el => el.addEventListener('click',() => toggleHero(el.dataset.hero)));
    document.querySelectorAll('[data-info]').forEach(el => el.addEventListener('click',() => showInfo(el.dataset.info)));
    document.querySelectorAll('[data-prep-category]').forEach(el => el.addEventListener('click',() => run(() => { state.prepCategory = el.dataset.prepCategory; })));
    document.querySelectorAll('[data-prepare]').forEach(el => el.addEventListener('click',() => run(() => { state.prepCategory = el.dataset.category; const list = state.preparations[state.active][state.prepCategory]; if (list.length >= hero(state.active).capacities[state.prepCategory]) return false; list.push(el.dataset.prepare); })));
    document.querySelector('[data-preset]')?.addEventListener('click',() => run(() => { state.preparations[state.active] = clone(hero(state.active).preparation); }));
    document.querySelectorAll('[data-event]').forEach(el => el.addEventListener('click',() => recordEvent(state.active,el.dataset.event)));
    document.querySelector('[data-hidden]')?.addEventListener('click',() => run(() => { actor().hidden = !actor().hidden; log(`Przy stole potwierdzono: Mira ${actor().hidden ? 'Ukryta' : 'odkryta'}.`); }));
    document.querySelector('[data-injury]')?.addEventListener('click',() => run(() => { actor().hp = Math.max(0,actor().hp-1); log(`${hero(state.active).name}: 1 obrażenie potwierdzone przy stole.`); }));
    document.querySelectorAll('[data-outcome]').forEach(el => el.addEventListener('click',() => run(() => { state.pending.success = el.dataset.outcome === 'success'; })));
    $('physical-amount')?.addEventListener('change',e => run(() => { const n = Number(e.target.value); if (!Number.isInteger(n) || n < 0 || n > 99) throw new Error('Wpisz liczbę od 0 do 99.'); state.pending.amount = n; }));
    document.querySelector('[data-skip-push]')?.addEventListener('click',() => run(() => { log('Przy stole potwierdzono odporność celu na przesunięcie.'); finishAction(); }));
  }
  $('help-button').addEventListener('click',() => $('help-dialog').showModal());
  $('new-button').addEventListener('click',() => { if (window.confirm('Zakończyć tę próbę i przygotować nową drużynę? Bieżący stan koszyków zostanie zastąpiony.')) { state = fresh(); update(); } });
  document.querySelectorAll('[data-close-dialog]').forEach(el => el.addEventListener('click',() => el.closest('dialog').close()));
  document.addEventListener('keydown',event => { if (['INPUT','TEXTAREA','SELECT'].includes(event.target.tagName)) return; const key = {Enter:28,Escape:29,'+':26,'=':26,'-':27,'*':25}[event.key]; if (key !== undefined) { event.preventDefault(); press(key); } });
  restore(); render();
  window.RuneBaskets = {get state() { return state; },get data() { return D; },press,render,startCombat,selectField,chooseAction,recordEvent,toggleHero,slot,bindings,save,restore,validate,storageKey:KEY,
    resolvePhysical:(success,amount=0) => run(() => { if (state.phase !== 'resolution') return false; state.pending.success = !!success; state.pending.amount = amount; resolvePhysical(); }),
    reset:() => { state = fresh(); update(); }};
})();
