'use strict';
// Presentation adapter for the mock encounter, sharing the existing laptop shell.
(() => {
  const D=window.RESONANCE_DATA,M=window.ResonanceModel;
  const esc=s=>String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
  const field=p=>p?`${String.fromCharCode(65+p.x)}${p.y+1}`:'—';
  const names={strength:'Siły',dexterity:'Zręczności',constitution:'Kondycji',intelligence:'Inteligencji',wisdom:'Mądrości',charisma:'Charyzmy'};
  const damageNames={slashing:'cięte',piercing:'kłute',bludgeoning:'obuchowe',magic:'magiczne',force:'siłowe',psychic:'psychiczne',radiant:'promieniste',fire:'ogień'};
  const chainBonusText={
    'Wieża':n=>`+${n} KP, także poza własną turą.`,
    'Grot':n=>`+${n}k4 obrażeń na każdy cel, także przy zwykłych atakach i reakcjach.`,
    'Schody':n=>`+${2*n} pkt ruchu na początku tury; nowa kopia: +2 pkt.`,
    'Błysk':n=>`Leczenie ${n}k4 PW na początku tury; nowa kopia: +1k4 PW.`,
    'Hak':n=>`Po obrażeniach: przeniesienie każdego legalnego celu do ${n} pól; można pozostać w miejscu.`,
    'Oko':n=>`+${n} do własnych rzutów k20, nie do ST.`,
    'Kielich':n=>`Limit puli: ${2*n} tymczasowych PW; zużyta pula nie odnawia się co turę.`,
    'Węzeł':n=>`Wszyscy wrogowie: −${n} pkt ruchu, minimum 0.`,
    'Klepsydra':n=>`Limit osłony: ${2*n} pkt, nie chroni przed obrażeniami psychicznymi; bez odnowy co turę.`
  };
  const statusNames={rage:'Runiczny szał',prone:'Powalony',slow:'Więzy · połowa ruchu',root:'Korzenie · bez ruchu',roundRoot:'Więzy · blokada następnej rundy',fear:'Echo / Dysonans · najbliższy atak z utrudnieniem',arcane:'Tarcza splotu · +2 KP',bless:'Pieczęć łaski · +1 atak / obrona',broken:'Przełamanie · −2 KP'};
  function create(host){
    let model=null,info=null,labOpen=false,rollValue=1,rollRef=null,rollIndex=-1,previewActor=null,enemyFocusRef=null;
    const {bind,button,controls,icon,slot,render,notify}=host;
    const change=fn=>()=>{fn();render();};
    function start(party,focused=null){
      const ids=focused?[focused,...party.filter(id=>id!==focused)].slice(0,6):party;
      model=new M.Encounter(D,ids);info=null;rollRef=null;previewActor=null;
    }
    function statuses(a){
      const entries=a.statuses.map(s=>`${statusNames[s.type]??s.type}${s.remaining?` · ${s.remaining} tur`:''}${s.type==='roundRoot'?` (runda ${s.round})`:''}`);
      if(model.shielded(a))entries.push('Żywa osłona · +1 KP');
      if(a.hidden.length)entries.push(`Ukryta przed: ${a.hidden.map(id=>model.actor(id).name).join(', ')}`);
      if(a.hymn)entries.push('Hymn odwagi · 1k6 do wykorzystania');
      if(a.moveLocked)entries.push('Akcja ruchu zużyta');
      if(a.mark)entries.push(`Piętno → ${model.actor(a.mark).name}`);
      if(!a.hero&&model.counts()['Węzeł'])entries.push(`Węzeł · −${model.counts()['Węzeł']} ruchu`);
      if(a.hp<=0)entries.push('Nieprzytomny / wyłączony z próby');
      return entries;
    }
    function pools(a){
      return `<div class="charge-pools"><span>PW <b>${a.hp}/${a.maxHp}</b></span><span>KP <b>${model.ac(a)}</b></span>${a.hero?`<span class="charge-counter">Ładunki <b data-charges="${a.id}">${a.charges}/20</b></span>`:''}</div>`+
        (model.member(a)?`<div class="resonance-pools"><span>Kielich <b>${a.cup}/${model.bonus(a,'Kielich')*2}</b></span><span>Klepsydra <b>${a.shield}/${model.bonus(a,'Klepsydra')*2}</b></span><span>Oko <b>+${model.bonus(a,'Oko')}</b></span><span>Grot <b>${model.bonus(a,'Grot')}k4</b></span></div>`:'');
    }
    function chain(){
      const c=model.s.chain,counts=model.counts();
      return `<section class="resonance-chain ${c?'active':''}" aria-label="Ciągły Rezonans"><div class="chain-heading"><span class="eyebrow">Rezonans ${c?'aktywny':'nieaktywny'}</span><span>${c?`${c.members.length} uczestników · ${c.entries.length} run`:'Wzmocniona moc rozpoczyna łańcuch'}</span></div>`+
        (c?`<ol class="chain-entries">${c.entries.map((e,i)=>`<li title="${esc(model.actor(e.contributor).name)}"><span class="resonance-halo">${icon(slot(e.rune))}</span><span>${i+1}. ${esc(e.rune)}${e.rune==='Fala'?`<small>→ ${e.effective??'brak'}</small>`:''}</span></li>`).join('')}</ol><div class="chain-totals">${Object.entries(counts).map(([r,n])=>`<span title="${esc(D.runes.find(x=>x.name===r).description)}">${esc(r)} ×${n}</span>`).join('')}</div>`+
          `<div class="chain-bonus-summary"><span class="eyebrow">Podsumowanie bonusów</span>${Object.keys(counts).length?
            `<dl class="chain-bonuses">${Object.entries(counts).map(([r,n])=>`<div data-chain-bonus="${esc(r)}"><dt>${esc(r)}</dt><dd>${esc(chainBonusText[r]?.(n)??D.runes.find(x=>x.name===r)?.short)}</dd></div>`).join('')}</dl>`:
            '<p>Brak bonusów — Fala nie ma poprzedniej runy do skopiowania.</p>'}${c.entries.some(e=>e.rune==='Fala'&&e.effective)?'<p class="chain-bonus-note">Kopie z Fali są już wliczone w powyższe wartości.</p>':''}</div>`+
          `<p>Objęci: ${c.members.map(id=>esc(model.actor(id).name)).join(', ')}. Pozostali dołączą na początku swojej tury.</p>`:'<p>Podstawowa moc kończy łańcuch po rozpatrzeniu. Skupienie kończy go od razu; tura bez kontynuacji — na końcu.</p>')+'</section>';
    }
    function title(text,sub=''){
      const a=model.active,h=D.heroes[a.id];
      return `<div class="turn-line"><div class="turn-actor">${h?`<img class="avatar" src="${h.portrait}" alt="">`:''}<div><strong>${esc(a.name)}</strong><small>${a.hero?'Tura bohatera':'Tura przeciwnika · rzuca aplikacja'}</small></div></div><span class="turn-number">Runda ${model.s.round}</span></div><h1>${esc(text)}</h1>${sub?`<p class="intro">${esc(sub)}</p>`:''}`;
    }
    function budgets(){const a=model.active;return `<div class="phase-pills"><span class="phase-pill ${model.movement()?'':'used'}">Ruch ${model.movement()}${a.tempMove?` (w tym +${a.tempMove} Schody)`:''}</span><span class="phase-pill ${a.ordinary?'':'used'}">Atak / przedmiot</span><span class="phase-pill ${a.special?'':'used'}">Specjalna</span><span class="phase-pill ${a.reaction?'':'used'}">Reakcja</span></div>`;}
    function idle(){
      const a=model.active;
      bind(0,'Ruch',change(()=>model.choose('move')),!model.unavailable('move'));
      bind(1,`Atak · ${a.weapon.name}`,change(()=>model.choose('attack')),!model.unavailable('attack'));
      if(a.hero){
        bind(2,'Mikstura · akcja ataku / przedmiotu',change(()=>model.choose('item')),!model.unavailable('item'));
        for(const c of model.cards())bind(c.slot,`${c.name} · ${model.unavailable(c.id)||'4 / 8 ładunków'}`,change(()=>model.choose(c.id)),!model.unavailable(c.id));
        bind(slot('Spirala'),'Skupienie · 1k20 ładunków',change(()=>model.choose('focus')),!model.unavailable('focus'));
      }
      bind(3,'Koniec tury',change(()=>{model.s.phase='end-preview';}));
      const viewed=model.actor(previewActor??a.id);
      bind(26,'Następny uczestnik · podgląd',change(()=>cycle(1)));
      bind(27,'Poprzedni uczestnik · podgląd',change(()=>cycle(-1)));
      return title('Wybierz akcję',a.hero?'Wybierz podświetloną runę na panelu. Moc pokaże opis, legalne cele i koszt obu trybów.':'Możesz poruszyć przeciwnika, wykonać atak lub zakończyć turę. Rezonans drużyny nadal działa.')+
        budgets()+pools(a)+`<p class="combat-action-prompt">Mapa pozostaje na stole. W tym mocku pola wybierasz w rozwijanym symulatorze po lewej.</p>`+
        `<div class="charge-inspect"><small>Podgląd − / + · nie zmienia aktywnej tury</small>${viewed.id!==a.id?`<strong>${esc(viewed.name)}</strong>${pools(viewed)}`:''}${statuses(viewed).map(t=>`<p>${esc(t)}</p>`).join('')}</div>`;
    }
    function cycle(dir){const i=model.s.order.indexOf(previewActor??model.active.id);previewActor=model.s.order[(i+dir+model.s.order.length)%model.s.order.length];}
    function modes(p,c){
      const base=model.price(c,'base',p.targets),enhanced=model.price(c,'enhanced',p.targets),effective=c.rune==='Fala'?model.s.chain?.entries.at(-1)?.effective:c.rune;
      return '<div class="mode-grid">'+
        button(5,'Podstawowa',`${base} ładunków · kończy Rezonans po efektach`,change(()=>model.mode('base')),{selected:p.mode==='base',enabled:!model.unavailable(c.id,'base')})+
        button(8,'Wzmocniona',`${enhanced} ładunków · +${c.rune}${c.rune==='Fala'?` → ${effective??'brak poprzednika'}`:''}`,change(()=>model.mode('enhanced')),{selected:p.mode==='enhanced',enabled:!model.unavailable(c.id,'enhanced')})+
        `</div><p class="compact-note">${esc(D.runes.find(r=>r.name===c.rune).short)}${model.surcharge(c,p.targets)?` Dopłata skazy: +${model.surcharge(c,p.targets)}.`:''}</p>`;
    }
    function preview(){
      const p=model.s.preview,a=model.active,c=model.card(p.id);
      const actionNames={move:'Ruch',attack:a.weapon.name,item:'Mikstura',focus:'Skupienie'};
      let html=title(c?.name??actionNames[p.id])+budgets();
      if(c)html+=`<div class="power-description">${icon(c.slot)}<div><b>${esc(c.budget)} · ${esc(c.target)}</b><details class="power-copy"><summary>Treść karty i wymagania</summary><p>${esc(c.effect)}</p><small>${esc(c.requirements)}</small></details></div></div>`;
      else html+=`<p class="intro">${p.id==='focus'?'Odzyskaj 1k20 ładunków, do 20. Zużywa S i natychmiast wygasza Rezonans.':p.id==='move'?`Wybierz legalne pole w zasięgu ${model.movement()} punktów ruchu. Trudny teren kosztuje 2.`:p.id==='item'?'2k4 + 2 PW, do maksimum. Zużywa atak / przedmiot.':'Wskaż pole wroga w zasięgu broni. Atak nie kosztuje ładunków.'}</p>`;
      if(['flame_fan','force_wave'].includes(p.id)&&p.center&&p.exclude===undefined){
        html+=`<div class="weave-prompt"><h2>Precyzyjny splot</h2><p>Wskaż pole stworzenia do pominięcia albo wybierz „Nie pomijaj”.</p><p>Obszar: ${model.area().map(id=>`${esc(model.actor(id).name)} (${field(model.actor(id).pos)})`).join(', ')||'brak stworzeń'}</p></div>`;
        html+=button(5,'Nie pomijaj','Wszystkie stworzenia w obszarze otrzymają efekt',change(()=>model.exclude(null)));
        return html+controls('Najpierw zdecyduj o pominięciu',()=>{},false,change(()=>model.cancel()));
      }
      if(['flame_fan','force_wave'].includes(p.id)){
        html+=`<div class="board-action-preview">${p.center?`Obszar wokół ${field(p.center)}. Pominięcie: ${p.exclude?esc(model.actor(p.exclude).name):'nikt'}.`:'Wskaż środek obszaru 3×3 do 6 pól.'}</div>`;
        if(p.center)html+='<button class="text-btn" data-combat="area-reset">Zmień obszar / pominięcie</button>';
      }else if(p.center){html+=`<p class="compact-note">Obszar do 2 pól: ${model.area().map(id=>esc(model.actor(id).name)).join(', ')||'brak celów'}.</p>`;}
      else if(!['focus','item','rage','second_wind','hide','move','misty_step'].includes(p.id)){
        const legal=model.legalTargets(),shown=p.targets.length?legal.filter(b=>p.targets.includes(b.id)):legal;
        html+='<ul class="legal-targets">'+shown.map(b=>`<li class="${p.targets.includes(b.id)?'selected':''}"><strong>${esc(b.name)} · ${field(b.pos)}</strong><span>PW ${b.hp}/${b.maxHp} · KP ${model.ac(b)}${p.targets.includes(b.id)?` · wybrano ×${p.targets.filter(id=>id===b.id).length}`:''}${statuses(b).length?' · '+esc(statuses(b).join(' / ')):''}</span></li>`).join('')+'</ul>';
        if(p.targets.length&&legal.length>shown.length)html+=`<p class="compact-note">Pozostałe legalne cele: ${legal.filter(b=>!p.targets.includes(b.id)).map(b=>`${esc(b.name)} (${field(b.pos)})`).join(', ')}. Kliknij inne pole, by zmienić wybór.</p>`;
        if(!model.legalTargets().length)html+='<p class="notice">Brak legalnych celów. Możesz wrócić bez wydawania zasobów.</p>';
      }
      if(p.destination){
        const steps=p.path?.cells.length??0,dc=p.id==='bastion_charge'?D.rules.save_dc_base+a.abilities.strength+steps:null;
        html+=`<div class="board-action-preview destination-preview"><strong>Niebieskie pole: ${field(p.destination)}</strong><span>Droga: ${p.path?.cells.map(field).join(' → ')||'teleportacja'}${dc?` · ${steps} pól · ST 10 + Siła + ${steps} = ${dc}`:''}</span><span>Przestaw figurkę zgodnie z podglądem i zatwierdź ✓.${p.id==='bastion_charge'?' Ruch spadnie do 0.':''}</span></div>`;
      }else if(p.id==='guard_vault'&&p.targets.length)html+='<p class="notice">Teraz wskaż jedno z podświetlonych wolnych pól wokół wybranego wroga.</p>';
      if(p.id==='force_darts'||p.id==='double_shot')html+=`<p class="notice">Wskazano ${p.targets.length}/${p.id==='force_darts'?3:2}. Klikaj pola celów po kolei; ten sam wróg może otrzymać kilka trafień. Kolejne kliknięcie po komplecie zaczyna wybór od nowa.</p>`;
      if(c)html+=modes(p,c);
      const cost=c?model.price(c,p.mode,p.targets):0;
      return html+`<p class="compact-note">Podgląd niczego nie wydaje.${c?` Ładunki: ${a.charges} → ${a.charges-cost}.`:''}</p>`+
        controls(c?`Zatwierdź · ${cost} ładunków`:'Zatwierdź',change(()=>{if(!model.commit())notify('Podgląd nie jest już legalny. Wybierz ponownie.');}),model.ready(),change(()=>model.cancel()));
    }
    function enemyFocus(){const t=model.s.task;return model.isEnemyRoll(t)||t?.type==='enemy-result'?t.actor:null;}
    function enemyTaskView(t){
      const a=model.actor(t.actor),target=model.actor(t.target),result=t.type==='enemy-result';
      const attack=(result?t.rolls[0].outcome:t.outcome)==='attack',opportunity=t.power==='opportunity';
      const heading=opportunity?'Atak okazyjny przeciwnika':attack?'Atak przeciwnika':'Rzut przeciwnika';
      let html=title(result?`Wynik · ${heading.toLowerCase()}`:heading,
        `${a.name} · ${field(a.pos)}${target?` → ${target.name}`:''}. Przeciwnik jest wyróżniony na planszy.`);
      if(!result){
        html+=`<div class="enemy-roll-notice" role="status"><strong>${esc(t.label.replace(/strength|dexterity|constitution|intelligence|wisdom|charisma/g,m=>names[m]))}</strong><p>${opportunity?'Ruch zatrzymany przed opuszczeniem zasięgu przeciwnika. ':''}Naciśnij ✓. Aplikacja wykona ${attack?'rzut ataku i, po trafieniu, obrażeń':t.outcome==='damage'?'rzut obrażeń':'rzut obronny'} i pokaże wynik. Nie wpisujesz kości przeciwnika.</p>${t.dc!==undefined?`<p>${attack?'KP celu':'ST'} ${t.dc} · modyfikator ${t.modifier>=0?'+':''}${t.modifier}${t.mode==='advantage'?' · przewaga':t.mode==='disadvantage'?' · utrudnienie':''}</p>`:''}</div>`;
        return html+controls(attack?'Rozpatrz atak':'Rozpatrz rzut',change(()=>{
          if(model.s.task===t&&!model.confirmEnemyRoll(sides=>1+Math.floor(Math.random()*sides)))notify('Nie udało się rozpatrzyć rzutu. Spróbuj ponownie.');
        }),true,()=>{}, {enabled:false});
      }
      html+='<div class="enemy-roll-result" role="status">'+t.rolls.map(r=>{
        const damage=r.outcome==='damage';
        const outcome=damage?'Obrażenia':r.outcome==='attack'?(r.success?(r.natural===20?'Trafienie krytyczne':'Trafienie'):'Pudło'):r.outcome==='contest'?'Wynik przeciwstawny':r.success?'Obrona udana':'Obrona nieudana';
        const dice=r.parts.map((p,i)=>`${p.count}k${p.sides}: ${r.dice[i].join(' + ')}${damage&&p.modifier?` ${p.modifier>=0?'+':''}${p.modifier}`:''}`).join(' · ');
        return `<section><h2>${outcome}</h2><p>${esc(dice)}${damage?'':` ${r.modifier>=0?'+':''}${r.modifier} = <b>${r.total}</b>${r.dc!==undefined?` / ${r.outcome==='attack'?'KP':'ST'} ${r.dc}`:''}`}${r.mode==='advantage'?' · wyższa k20':r.mode==='disadvantage'?' · niższa k20':''}</p>${damage?`<p>Obrażenia przed osłonami / odpornością: ${r.components.map(c=>`${c.value} ${damageNames[c.damage_type]??c.damage_type}`).join(' + ')}.</p><strong>Utrata PW: ${r.loss.hp}${r.loss.cup?` · Kielich: −${r.loss.cup}`:''}${r.loss.shield?` · Klepsydra pochłonęła: ${r.loss.shield}`:''}</strong>`:''}</section>`;
      }).join('')+'</div>';
      if(target)html+=pools(target);
      if(opportunity)html+='<p class="compact-note">✓ zamyka wynik i kontynuuje ruch albo pokazuje kolejną reakcję. Przy 0 PW ruch zostanie przerwany.</p>';
      return html+controls('Dalej',change(()=>{if(model.s.task===t)model.acknowledgeEnemyResult();}),true,()=>{}, {enabled:false});
    }
    function taskView(){
      const t=model.s.task;if(!t)return title('Rozpatrywanie…');
      if(model.isEnemyRoll(t)||t.type==='enemy-result')return enemyTaskView(t);
      if(t.type==='roll'){
        const dice=model.rollDice(),confirmed=t.diceResults??[],index=confirmed.length,p=dice[index];
        if(rollRef!==t||rollIndex!==index){rollRef=t;rollIndex=index;rollValue=p?Math.floor((p.sides+1)/2):1;}
        let html=title(t.label.replace(/strength|dexterity|constitution|intelligence|wisdom|charisma/g,m=>names[m]),'Koszt został już rozliczony. Wprowadź rzeczywiste wyniki kości; nie można cofnąć opłaconej akcji.');
        const mode=t.mode==='advantage'?'Przewaga · po obu rzutach wybierzemy wyższą k20':t.mode==='disadvantage'?'Utrudnienie · po obu rzutach wybierzemy niższą k20':'';
        html+=`<p class="roll-formula">${esc(mode)}${t.modifier!==undefined?` · modyfikator ${t.modifier>=0?'+':''}${t.modifier} (bez biegłości)`:''}${t.dc!==undefined?` · ST / KP ${t.dc}`:''}</p>`;
        if(p)html+=`<p class="compact-note" data-dice-progress>Kość ${index+1} z ${dice.length} · k${p.sides}</p><div class="physical-dice"><label>${esc(p.label)}<span>${p.count}k${p.sides}${p.modifier?` ${p.modifier>=0?'+':''}${p.modifier}`:''}${p.damage_type?' · '+damageNames[p.damage_type]:''}<br>Wpisz wynik tej kości: 1–${p.sides}. ✓ zatwierdza i przechodzi dalej.</span><div><button data-die-step="${index}" data-delta="-1" aria-label="Zmniejsz ${esc(p.label)}">−</button><input data-die="${index}" aria-label="${esc(p.label)}" type="number" min="1" max="${p.sides}" value="${rollValue}"><button data-die-step="${index}" data-delta="1" aria-label="Zwiększ ${esc(p.label)}">+</button></div></label></div>`;
        if(confirmed.length)html+=`<p class="compact-note" data-confirmed-dice>Zatwierdzone: ${confirmed.map((value,i)=>`${esc(dice[i].label)} · k${dice[i].sides}: ${value}`).join('; ')}.</p>`;
        if(t.outcome==='damage')html+=`<p class="compact-note">${t.components.filter(c=>!c.count).map(c=>`Wspólne obrażenia: ${c.value} ${damageNames[c.damage_type]}.`).join(' ')}${t.divisor===2?' Udana obrona: połowa całości, łącznie z Grotem, zaokrąglona w dół.':''}</p>`;
        if(!t.parts.length)html+='<p class="notice">Wspólna kość mocy jest już znana. Potwierdź obrażenia tego celu po jego obronie.</p>';
        if(p){
          bind(26,'Zwiększ wynik kości',()=>stepDie(index,1));bind(27,'Zmniejsz wynik kości',()=>stepDie(index,-1));
        }
        return html+controls(p&&index<dice.length-1?'Zatwierdź · następna kość':'Zatwierdź wynik',change(()=>{
          if(model.s.task!==t)return;
          if(p)model.submitDie(rollValue,index);else model.submit([]);
        }),!p||(Number.isInteger(rollValue)&&rollValue>=1&&rollValue<=p.sides),()=>notify('Dokończ rozpoczęte rozpatrzenie; koszt nie jest zwracany.'),{enabled:false});
      }
      if(t.type==='hymn')return title('Hymn odwagi',`${model.actor(t.actor).name}: wynik ${t.total}${t.roll.dc?` / ST ${t.roll.dc}`:''} · ${t.success?'sukces':'porażka'}`)+
        '<div class="weave-prompt"><h2>Czy chcesz dodać 1k6 z Hymnu odwagi do wyniku?</h2><p>Decyzja przed skutkami rzutu. Kość zostaje zużyta także wtedy, gdy nie wystarczy. Zachowanie nie ma limitu czasu.</p></div>'+
        button(5,'Użyj Hymnu','Dodaj wynik fizycznej 1k6',change(()=>model.decideHymn(true)))+
        button(8,'Zachowaj','Rozpatrz pierwotny wynik',change(()=>model.decideHymn(false)));
      if(t.type==='recover'){
        const a=model.actor(t.actor);return title('Odzysk klasowy',`${a.name} · ${a.regenReason}`)+pools(a)+
          button(5,'Odzyskaj 1k4','Raz na rundę; zgłoszenie zużywa limit',change(()=>model.recover(true)),{enabled:a.charges<20})+
          button(8,'Pomiń odzysk','Nie zużywa limitu; możesz zgłosić po kolejnym zdarzeniu',change(()=>model.recover(false)));
      }
      if(t.type==='opportunity')return title('Atak okazyjny',`${model.actor(t.actor).name}: ${model.actor(t.target).name} opuszcza twój zasięg.`)+
        button(1,'Wykorzystaj reakcję','Atak bronią · 0 ładunków · aktywny Rezonans działa',change(()=>model.opportunity(true)))+
        button(8,'Nie reaguj','Zachowaj reakcję na później',change(()=>model.opportunity(false)));
      if(t.type==='relocate'){
        const a=model.actor(t.target);return title(`${t.label}: ${a.name}`,`Wskaż legalne pole do ${t.radius} pól od ${field(a.pos)}, przestaw figurkę i potwierdź.`)+
          `<div class="destination-preview board-action-preview"><strong>${t.destination?`Wybrano ${field(t.destination)}`:'Oczekuję na pole planszy'}</strong><span>${t.label==='Impuls egidy'?'Wybierz inne pole w odległości 1.':'Aktualne pole i ✓ pozwalają pozostać w miejscu.'} ↩ czyści tylko bieżący wybór.</span></div>`+
          controls('Zatwierdź pozycję',change(()=>model.confirmRelocation()),Boolean(t.destination),change(()=>model.cancel()));
      }
      return title('Rozpatrywanie efektów');
    }
    function stepDie(i,delta){const p=model.rollDice()[i];if(!p||i!==(model.s.task?.diceResults?.length??0))return;rollValue=Math.max(1,Math.min(p.sides,rollValue+delta));render();}
    function infoView(){
      const a=model.actor(info),h=D.heroes[a.id],equipment=window.RUNE_DATA.heroes.find(h=>h.id===a.id)?.equipment??[];
      return `<div class="eyebrow">Informacja o uczestniku · tylko podgląd</div><h1>${esc(a.name)}</h1>`+pools(a)+(a===model.active?budgets():'')+
        `<ul class="hero-status-list">${statuses(a).map(s=>`<li>${esc(s)}</li>`).join('')||'<li>Brak dodatkowych stanów.</li>'}</ul>`+
        (h?`<div class="section-label">${esc(h.passive.name)}</div><p>${esc(h.passive.description)}</p><div class="section-label">Odzysk klasowy · 1k4</div><ol>${h.regeneration.map(s=>`<li>${esc(s)}</li>`).join('')}</ol><p class="compact-note">${a.regenRound===model.s.round?'Wykorzystany w tej rundzie':'Dostępny w tej rundzie'}.</p><div class="section-label">Skaza · ${esc(h.flaw.name)}</div><p>${esc(h.flaw.description)}</p><div class="hero-state-grid">${Object.entries(a.abilities).map(([k,v])=>`<span>${names[k]}<strong>${v>=0?'+':''}${v}</strong></span>`).join('')}</div>`:'')+
        (h?'<div class="section-label">Wyposażenie</div><ul class="hero-equipment-list">'+equipment.map(item=>`<li><strong>${esc(item.name)}</strong><span>${esc(item.slot)}</span></li>`).join('')+'</ul>':'')+
        controls('Wróć do decyzji',change(()=>info=null),true,change(()=>info=null));
    }
    function right(){
      if(enemyFocus()&&enemyFocusRef!==model.s.task){enemyFocusRef=model.s.task;labOpen=true;}
      if(info){bind(slot('Gwiazda'),'Zamknij informacje',change(()=>info=null),true,true);host.getBindings().get(slot('Gwiazda')).kind='info';return infoView();}
      bind(slot('Gwiazda'),'Informacja o bohaterze',change(()=>info=previewActor??model.active.id));
      let html=chain();
      if(model.s.phase==='idle')html+=idle();
      else if(model.s.phase==='preview')html+=preview();
      else if(model.s.phase==='task')html+=taskView();
      else if(model.s.phase==='result')html+=title('Rozpatrzono działanie')+pools(model.active)+`<div class="combat-results">${model.s.history.slice(0,8).reverse().map(s=>`<p>${esc(s)}</p>`).join('')}</div>`+controls('Wróć do tury',change(()=>model.acknowledge()),true,change(()=>model.acknowledge()));
      else if(model.s.phase==='end-preview')html+=title('Zakończyć turę?',model.active.hero&&!model.active.continued&&model.s.chain?'Brak mocy wzmocnionej w tej turze wygasi cały Rezonans.':'Rezonans i niewykorzystane osłony przechodzą dalej.')+controls('Zakończ turę',change(()=>{model.s.phase='idle';model.endTurn();previewActor=null;}),true,change(()=>model.s.phase='idle'));
      else html+=title('Koniec próbnej walki','Rezonans wygaszony. Uruchom nową próbę z górnego paska.');
      const b=host.getBindings().get(slot('Gwiazda'));if(b)b.kind='info';
      return html;
    }
    function selectable(p){
      if(model.s.phase==='task'&&model.s.task?.type==='relocate')return model.relocationFields(model.s.task).some(q=>M.same(q,p));
      if(model.s.phase!=='preview')return false;
      const v=model.s.preview,a=model.active;
      if(['force_wave','flame_fan'].includes(v.id)&&v.center&&v.exclude===undefined)return model.area().some(id=>M.same(model.actor(id).pos,p));
      if(v.id==='flame_fan')return M.distance(a.pos,p)<=6;
      if(v.id==='move')return Boolean(model.path(a,p,model.movement()));
      if(v.id==='misty_step')return model.free(p,a.id)&&M.distance(a.pos,p)<=6&&model.visible(a,p);
      if(v.id==='skirmish_shot')return Boolean(model.path(a,p,2))||Boolean(v.destination&&model.legalTargets().some(b=>M.same(b.pos,p)));
      if(v.id==='guard_vault'&&v.targets.length&&model.free(p,a.id)&&M.distance(model.actor(v.targets[0]).pos,p)===1)return true;
      return model.legalTargets().some(b=>M.same(b.pos,p));
    }
    function grid(){
      const v=model.s.preview,t=model.s.task,destination=v?.destination??t?.destination;
      let html='<div class="mock-grid" role="group" aria-label="Symulator pól planszy">';
      for(let y=0;y<model.s.board.height;y++)for(let x=0;x<model.s.board.width;x++){
        const p={x,y},a=Object.values(model.s.actors).find(a=>a.hp>0&&M.same(a.pos,p)),blocked=model.s.board.blocked.some(q=>M.same(q,p)),rough=model.s.board.difficult.some(q=>M.same(q,p));
        const legal=selectable(p),area=v?.center&&M.distance(v.center,p)<=(v.id==='flame_fan'?1:2),path=v?.path?.cells.some(q=>M.same(q,p));
        const focused=Boolean(a&&a.id===enemyFocus());
        html+=`<button class="mock-cell ${a?a.hero?'ally':'enemy':''} ${focused?'enemy-focus':''} ${blocked?'blocked':''} ${rough?'rough':''} ${legal?'legal':''} ${area?'area':''} ${path?'path':''} ${M.same(destination,p)?'destination':''}" data-field="${x},${y}" ${legal?'':'disabled'} aria-label="${field(p)}${a?' · '+esc(a.name):blocked?' · przeszkoda':''}${focused?' · rozpatrywany przeciwnik':''}${legal?' · legalne pole':''}" title="${field(p)}${a?' · '+esc(a.name):''}"><small>${field(p)}</small><b>${a?a.name.slice(0,2):blocked?'▧':rough?'≈':''}</b></button>`;
      }
      return html+'</div><p class="compact-note">Złote: legalne · niebieskie: cel / droga · czerwone: wróg · jasna czerwona ramka: rozpatrywany przeciwnik · ▧ przeszkoda · ≈ trudny teren. To testowa arena, nie mapa Misji 0.</p>';
    }
    function left(){
      return `<aside class="prototype-combat-list charge-initiative" data-enemy-focus="${enemyFocus()??''}"><div class="eyebrow">Kolejność tur</div><h2>Próba przy posterunku</h2>`+
        `<details class="combat-lab" ${labOpen?'open':''}><summary>Symulator pól · panel testowy</summary>${labOpen?grid():''}<label>Nowa próba od bohatera<select data-demo-hero><option value="">Wybierz…</option>${Object.values(D.heroes).map(h=>`<option value="${h.id}">${h.name}</option>`).join('')}</select></label><div class="lab-tools"><button data-combat="save">Zapisz próbę</button><button data-combat="load">Wczytaj próbę</button><button data-combat="finish">Zakończ próbę</button></div><p class="compact-note">Zapis dotyczy wyłącznie tej makiety w przeglądarce. Nie zmienia zapisów gry.</p></details>`+
        model.s.order.map(id=>{const a=model.actor(id),h=D.heroes[id];return `<article class="initiative-entry ${a===model.active?'active':''} ${id===previewActor?'inspected':''} ${id===enemyFocus()?'enemy-focus':''}">${h?`<img class="avatar" src="${h.portrait}" alt="">`:'<span class="enemy-avatar">◆</span>'}<div><strong>${esc(a.name)}</strong>${id===enemyFocus()?'<small class="enemy-focus-label">Rozpatrywany przeciwnik</small>':''}<small>${a.hp}/${a.maxHp} PW · KP ${model.ac(a)}${a.hero?` · ${a.charges}/20 ład.`:` · ruch ${model.movement(a)}`}</small><small class="membership ${model.member(a)?'joined':''}">${a.hero?(model.member(a)?'◉ W Rezonansie':model.s.chain?'○ Oczekuje na swoją turę':'○ Poza Rezonansem'):''}</small>${statuses(a).map(s=>`<small class="state-chip">${esc(s)}</small>`).join('')}</div><span class="field-label">${field(a.pos)}</span></article>`;}).join('')+
        '</aside>';
    }
    function selectField(x,y){
      const p={x,y},v=model.s.preview;
      let ok;
      if(v&&['force_wave','flame_fan'].includes(v.id)&&v.center&&v.exclude===undefined){const id=model.area().find(id=>M.same(model.actor(id).pos,p));ok=id?model.exclude(id):false;}
      else if(v?.id==='skirmish_shot'&&v.destination){const target=model.legalTargets().find(a=>M.same(a.pos,p));ok=target?model.selectTarget(target.id):model.select(p);}
      else ok=model.select(p);
      if(ok)render();return ok;
    }
    document.addEventListener('toggle',event=>{if(event.target.matches?.('.combat-lab')&&event.target.open!==labOpen){labOpen=event.target.open;render();}},true);
    document.addEventListener('click',event=>{
      if(!host.isActive()||!model)return;
      const fieldButton=event.target.closest('[data-field]');if(fieldButton){const [x,y]=fieldButton.dataset.field.split(',').map(Number);selectField(x,y);return;}
      const die=event.target.closest('[data-die-step]');if(die){stepDie(Number(die.dataset.dieStep),Number(die.dataset.delta));return;}
      const action=event.target.closest('[data-combat]')?.dataset.combat;
      if(action==='area-reset'){delete model.s.preview.exclude;if(model.s.preview.id==='flame_fan')model.s.preview.center=null;render();}
      if(action==='save'){try{localStorage.setItem('resonance-mock-v1',model.snapshot());notify('Zapisano lokalną próbę mocka.');}catch{notify('Przeglądarka nie pozwala zapisać próby.');}}
      if(action==='load'){try{const raw=localStorage.getItem('resonance-mock-v1');if(!raw)throw Error();model.restore(raw);info=null;rollRef=null;render();}catch{notify('Brak poprawnego zapisu tej makiety.');}}
      if(action==='finish'){model.endChain('koniec próbnej walki');model.s.queue=[];model.s.task=null;model.s.action=null;model.s.phase='finished';render();}
    });
    document.addEventListener('change',event=>{
      if(!host.isActive()||!model)return;
      if(event.target.matches('[data-demo-hero]')&&event.target.value){start(model.s.party,event.target.value);render();}
    });
    document.addEventListener('input',event=>{
      if(!host.isActive()||model?.s.task?.type!=='roll'||!event.target.matches('[data-die]'))return;
      const index=model.s.task.diceResults?.length??0,p=model.rollDice()[index];
      if(!p||Number(event.target.dataset.die)!==index)return;
      rollValue=Number(event.target.value);
      const valid=Number.isInteger(rollValue)&&rollValue>=1&&rollValue<=p.sides;
      const confirm=host.getBindings().get(28);if(confirm)confirm.enabled=valid;
      // Keep the input and clicked confirmation in the DOM; rerendering on blur loses clicks.
      document.querySelectorAll('button[data-slot="28"]').forEach(b=>{b.disabled=!valid;if(b.classList.contains('board-pad'))b.dataset.light=valid?'control':'off';});
    });
    return {start,right,left,selectField,flowKey:()=>`${info??''}:${model?.s.phase}:${model?.s.preview?.id??''}:${model?.s.task?.type??''}:${model?.s.task?.actor??''}:${model?.s.task?.label??''}:${model?.s.task?.diceResults?.length??0}`,get model(){return model;},get state(){return model?.s;},setRoll:values=>{rollValue=values[0];},openLab:()=>{labOpen=true;render();},showHero:id=>{info=id;render();},back:()=>{if(info){info=null;render();return true;}if(model.cancel()){render();return true;}return false;}};
  }
  window.ResonancePrototype={create};
})();
