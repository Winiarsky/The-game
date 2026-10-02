'use strict';
// Deterministic, serializable simulation for the standalone mock. No game API/hardware.
(() => {
  const copy = value => JSON.parse(JSON.stringify(value));
  const distance = (a,b) => Math.max(Math.abs(a.x-b.x),Math.abs(a.y-b.y));
  const same = (a,b) => a && b && a.x===b.x && a.y===b.y;
  const key = p => `${p.x},${p.y}`;
  const neighbors = p => [-1,0,1].flatMap(y=>[-1,0,1].map(x=>({x:p.x+x,y:p.y+y}))).filter(q=>!same(p,q));
  const rollResult = (t,values) => {
    const isCheck=['attack','hide','bash','contest','save'].includes(t.outcome);
    const natural=isCheck&&t.parts[0]?.sides===20?(t.mode==='advantage'?Math.max(...values):t.mode==='disadvantage'?Math.min(...values):values[0]):null;
    const total=(natural??values.reduce((sum,n)=>sum+n,0))+(t.modifier??0);
    const success=t.outcome==='attack'?(natural===20||(natural!==1&&total>=t.dc)):total>=(t.dc??0);
    return {natural,total,success};
  };
  const damageComponents = (t,values) => {
    let index=0;const groups={};
    for(const c of t.components)groups[c.damage_type]=(groups[c.damage_type]??0)+(c.count?values[index++]+(c.modifier??0):c.value);
    return Object.entries(groups).map(([damage_type,value])=>({damage_type,value:Math.max(0,Math.floor(value/t.divisor))}));
  };
  class Encounter {
    constructor(data,party=['garran','mira','lorian','nimra']) {
      this.data=data;
      const positions=[{x:2,y:4},{x:2,y:6},{x:1,y:5},{x:2,y:2},{x:1,y:3},{x:1,y:7}];
      const actors={};
      party.forEach((id,i)=>{
        const h=data.heroes[id];
        actors[id]={id,name:h.name,hero:true,pos:positions[i],hp:h.maxHp,maxHp:h.maxHp,
          ac:h.ac,speed:h.speed,abilities:copy(h.abilities),weapon:copy(h.weapon),
          charges:data.rules.start_charges,turn:0,statuses:[],hidden:[],hymn:null,
          cup:0,shield:0,reaction:true,regenRound:0,regenReason:null,lastPower:null,
          powerStreak:0,lastRune:null,mark:null,hasShield:id==='garran'};
      });
      [[4,4,'Strażnik',45,14,2],[6,3,'Kusznik',35,13,1],[6,6,'Łowca',40,14,3]].forEach(([x,y,name,hp,ac,per],i)=>{
        const id=`enemy${i+1}`;
        actors[id]={id,name,hero:false,pos:{x,y},hp,maxHp:hp,ac,speed:6,turn:0,statuses:[],hidden:[],
          abilities:{strength:2,dexterity:2,constitution:2,wisdom:per,intelligence:0,charisma:0},
          perception:10+per,weapon:{name:i===1?'Kusza':'Włócznia',ability:i===1?'dexterity':'strength',kind:i===1?'ranged':'melee',count:1,sides:6,damage_type:'piercing',range:i===1?8:1},
          reaction:true,cup:0,shield:0};
      });
      this.s={version:3,party:[...party],order:Object.keys(actors),actors,index:0,round:1,chain:null,
        serial:0,phase:'idle',preview:null,action:null,queue:[],task:null,history:[],
        board:{width:12,height:10,blocked:[{x:5,y:4},{x:5,y:5}],difficult:[{x:3,y:6},{x:4,y:6}]}};
      this.beginTurn();
    }
    get active(){return this.s.actors[this.s.order[this.s.index]];}
    actor(id){return this.s.actors[id];}
    heroes(){return Object.values(this.s.actors).filter(a=>a.hero);}
    enemies(a=this.active){return Object.values(this.s.actors).filter(b=>b.hero!==a.hero&&b.hp>0);}
    allies(a=this.active){return Object.values(this.s.actors).filter(b=>b.hero===a.hero);}
    note(text){this.s.history.unshift(text);}
    counts(){return Object.fromEntries((this.s.chain?.entries??[]).map(e=>[e.rune,1]));}
    nextRunes(rune=this.s.chain?.entries.at(-1)?.rune){
      if(!rune||rune==='Fala')return [...this.data.rules.starter_runes];
      return [...new Set([...(this.data.rules.rune_relations?.[rune]??[]),'Fala'])];
    }
    resonancePreview(cardOrId,targets=[]){
      const card=typeof cardOrId==='string'?this.card(cardOrId):cardOrId;
      const memoryBefore=copy(this.s.chain?.entries??[]),last=memoryBefore.at(-1)?.rune;
      if(!card)return {transition:'start',memoryBefore,eligibleMemory:[],memoryAfter:memoryBefore,
        allowedNext:this.nextRunes(),activeBonuses:[],missingBonuses:[],missingRequiredRunes:[],continuityAllowed:true,blockedReasons:[]};
      const continuityAllowed=!last||this.nextRunes(last).includes(card.rune);
      const eligibleMemory=continuityAllowed?memoryBefore:[];
      const symbols=new Set(eligibleMemory.map(e=>e.rune));
      const activeBonuses=[],missingBonuses=[];
      for(const bonus of card.resonance_bonuses??[]){
        const missing=(bonus.requires??[]).filter(rune=>!symbols.has(rune));
        if(!missing.length)activeBonuses.push(copy(bonus));else missingBonuses.push({...copy(bonus),missing});
      }
      const oldSymbols=new Set(memoryBefore.map(e=>e.rune));
      const missingRequiredRunes=(card.requires_resonance??[]).filter(rune=>!oldSymbols.has(rune));
      const blockedReasons=[];
      if(missingRequiredRunes.length)blockedReasons.push(`Wymaga Rezonansu: ${missingRequiredRunes.join(' + ')}`);
      if((card.requires_resonance?.length||card.ends_resonance)&&(!last||!continuityAllowed))blockedReasons.push('Wymaga legalnej kontynuacji Rezonansu');
      const transition=card.ends_resonance?'finisher':!last?'start':continuityAllowed?'continue':'reset';
      const memoryAfter=card.ends_resonance?[]:[...eligibleMemory,{rune:card.rune,effective:card.rune,contributor:this.active.id}].slice(-(this.data.rules.memory_limit??3));
      return {transition,memoryBefore,eligibleMemory,memoryAfter,allowedNext:this.nextRunes(),activeBonuses,missingBonuses,
        missingRequiredRunes,continuityAllowed,blockedReasons};
    }
    effectModifiers(cardOrId=this.s.preview?.id){
      const card=typeof cardOrId==='string'?this.card(cardOrId):cardOrId;
      const modifiers=copy(card?.base_modifiers??{});
      for(const bonus of this.resonancePreview(card).activeBonuses){
        for(const [name,value] of Object.entries(bonus.modifiers??{})){
          if(Array.isArray(value))modifiers[name]=[...(modifiers[name]??[]),...copy(value)];
          else if(typeof value==='boolean')modifiers[name]=Boolean(modifiers[name]||value);
          else if(['hymn_sides'].includes(name))modifiers[name]=Math.max(modifiers[name]??0,value);
          else modifiers[name]=(modifiers[name]??0)+value;
        }
      }
      return modifiers;
    }
    actionModifiers(actor,power){return this.s.action?.actor===actor&&this.s.action.id===power?this.s.action.modifiers??{}:{};}
    turnDuration(source){return {source:source.id,untilStart:source.id,turn:source.turn+1};}
    grantPool(target,kind,value,source){
      const field=kind==='temporary'?'cup':'shield';
      if(value<target[field])return;
      target[field]=value;
      this.addStatus(target,kind,{name:kind==='temporary'?'Tymczasowe PW':'Osłona obrażeń',value,...this.turnDuration(source)});
    }
    grantAc(target,value,source,power){this.addStatus(target,`ward:${power}`,{name:`Ochrona · +${value} KP`,value,...this.turnDuration(source)});}

    status(a,type){return a.statuses.find(s=>s.type===type);}
    shielded(a){const g=this.actor('garran');return a.hero&&a.id!=='garran'&&a.hp>0&&g?.hp>0&&g.hasShield&&distance(a.pos,g.pos)===1;}
    ac(a){return a.ac+(this.shielded(a)?1:0)+(this.status(a,'arcane')?.value??(this.status(a,'arcane')?2:0))+a.statuses.filter(s=>s.type.startsWith('ward:')).reduce((n,s)=>n+s.value,0)-(this.status(a,'broken')?.value??(this.status(a,'broken')?2:0));}
    movement(a=this.active){
      if(a.moveLocked||this.status(a,'root')||a.statuses.some(s=>s.type==='roundRoot'&&s.round===this.s.round))return 0;
      let limit=a.turnBase??a.speed;
      if(this.status(a,'slow'))limit=Math.floor(limit/2);
      limit=Math.max(0,limit-(this.status(a,'movePenalty')?.value??0));
      return Math.max(0,limit-(a.baseSpent??0))+Math.max(0,a.tempMove??0);
    }
    addStatus(a,type,extra={}){a.statuses=a.statuses.filter(s=>s.type!==type);a.statuses.push({type,...extra});}
    flanking(a,target){return distance(a.pos,target.pos)===1&&this.allies(a).some(b=>b.id!==a.id&&b.hp>0&&distance(b.pos,target.pos)===1&&(a.pos.x-target.pos.x)*(b.pos.x-target.pos.x)+(a.pos.y-target.pos.y)*(b.pos.y-target.pos.y)<0);}
    inBounds(p){return Number.isInteger(p?.x)&&Number.isInteger(p?.y)&&p.x>=0&&p.y>=0&&p.x<this.s.board.width&&p.y<this.s.board.height;}
    free(p,ignoreId=null){return this.inBounds(p)&&!this.s.board.blocked.some(b=>same(p,b))&&!Object.values(this.s.actors).some(a=>a.hp>0&&a.id!==ignoreId&&same(a.pos,p));}
    visible(a,p){
      const n=distance(a.pos,p);for(let i=1;i<n;i++){
        const q={x:Math.round(a.pos.x+(p.x-a.pos.x)*i/n),y:Math.round(a.pos.y+(p.y-a.pos.y)*i/n)};
        if(this.s.board.blocked.some(b=>same(q,b)))return false;
      }return true;
    }
    path(a,destination,limit=100,parkour=false){
      if(!this.free(destination,a.id))return null;
      const paths=new Map([[key(a.pos),{cells:[],cost:0}]]),open=[{pos:a.pos,cost:0}];
      while(open.length){
        open.sort((a,b)=>a.cost-b.cost||a.pos.y-b.pos.y||a.pos.x-b.pos.x);
        const item=open.shift(),previous=paths.get(key(item.pos));
        if(item.cost!==previous.cost)continue;
        if(same(item.pos,destination))return previous;
        for(const p of neighbors(item.pos)){
          const occupied=Object.values(this.s.actors).find(b=>b.hp>0&&b.id!==a.id&&same(b.pos,p));
          const legal=parkour?this.inBounds(p)&&(!occupied||occupied.hero!==a.hero):this.free(p,a.id);
          if(!legal)continue;
          if(!parkour&&p.x!==item.pos.x&&p.y!==item.pos.y&&(!this.free({x:p.x,y:item.pos.y},a.id)||!this.free({x:item.pos.x,y:p.y},a.id)))continue;
          const cost=previous.cost+(!parkour&&this.s.board.difficult.some(d=>same(d,p))?2:1);
          if(cost>limit||cost>=(paths.get(key(p))?.cost??Infinity))continue;
          paths.set(key(p),{cells:[...previous.cells,p],cost});open.push({pos:p,cost});
        }
      }return null;
    }
    adjacentPath(a,target,limit){
      return neighbors(target.pos).filter(p=>this.free(p,a.id)).map(p=>({destination:p,path:this.path(a,p,limit)})).filter(o=>o.path)
        .sort((a,b)=>a.path.cost-b.path.cost||a.path.cells.length-b.path.cells.length||a.destination.y-b.destination.y||a.destination.x-b.destination.x)[0]??null;
    }
    addRune(a,rune){
      if(!this.s.chain)this.s.chain={id:++this.s.serial,entries:[]};
      this.s.chain.entries.push({rune,effective:rune,contributor:a.id});
      this.s.chain.entries=this.s.chain.entries.slice(-(this.data.rules.memory_limit??3));
      this.note(`${a.name}: ${rune} do Rezonansu.`);
    }
    endChain(reason){
      if(!this.s.chain)return;
      this.s.chain=null;this.note(`Rezonans wygaszony: ${reason}.`);
    }
    expireTurnStart(a){
      for(const b of Object.values(this.s.actors)){
        const expired=b.statuses.filter(s=>s.untilStart===a.id&&s.turn<=a.turn);
        if(expired.some(s=>s.type==='temporary'))b.cup=0;
        if(expired.some(s=>s.type==='prevention'))b.shield=0;
        b.statuses=b.statuses.filter(s=>!expired.includes(s));
      }
    }
    skipTurn(a){
      a.turn++;this.expireTurnStart(a);
      for(const b of Object.values(this.s.actors))b.statuses=b.statuses.filter(s=>!(s.untilEnd===a.id&&s.turn<=a.turn));
    }
    beginTurn(){
      const a=this.active;a.turn++;a.ordinary=true;a.special=true;a.reaction=true;a.baseSpent=0;a.tempMove=0;a.moved=false;a.offensive=false;a.continued=false;a.sneakUsed=false;a.shot=false;
      a.moveLocked=Boolean(this.status(a,'prone'));
      a.statuses=a.statuses.filter(s=>s.type!=='prone'&&!(s.type==='roundRoot'&&s.round<this.s.round));
      this.expireTurnStart(a);
      a.turnBase=a.id==='garran'&&this.enemies(a).some(b=>distance(a.pos,b.pos)===1)?Math.floor(a.speed/2):a.speed;
      a.startAdjacent=this.enemies(a).filter(b=>distance(a.pos,b.pos)===1).map(b=>b.id);

      this.s.phase='idle';this.advance();
    }
    endTurn(){
      if(this.s.phase!=='idle')return false;
      const a=this.active;
      if(a.hero&&!a.continued)this.endChain('koniec tury bez mocy runicznej');
      const rage=this.status(a,'rage');if(rage&&(!a.offensive||--rage.remaining<=0))a.statuses=a.statuses.filter(s=>s!==rage);
      for(const b of Object.values(this.s.actors))b.statuses=b.statuses.filter(s=>!(s.untilEnd===a.id&&s.turn<=a.turn));
      a.tempMove=0;
      let searched=0;
      do{
        this.s.index=(this.s.index+1)%this.s.order.length;if(!this.s.index)this.s.round++;searched++;
        if(this.active.hp<=0)this.skipTurn(this.active);
      }while(this.active.hp<=0&&searched<this.s.order.length);
      if(searched>=this.s.order.length||!this.heroes().some(h=>h.hp>0)||!this.enemies(this.heroes()[0]).length){this.endChain('koniec walki');this.s.phase='finished';return true;}
      this.beginTurn();return true;
    }
    cards(a=this.active){return a.hero?this.data.heroes[a.id].cards:[];}
    card(id){return this.cards().find(c=>c.id===id);}
    surcharge(card,targets=[]){
      const a=this.active;
      if(a.id==='nimra'&&a.lastPower===card.id)return a.powerStreak>=2?4:2;
      if(a.id==='lorian'&&!this.allies().some(b=>b.id!==a.id&&b.hp>0&&distance(a.pos,b.pos)<=2))return 2;
      if(a.id==='dagna'&&card.id==='sacred_flame'&&this.allies().some(b=>b.id!==a.id&&b.hp>0&&b.hp<b.maxHp/2&&distance(a.pos,b.pos)===1))return 2;
      if(a.id==='erynd'&&['double_shot','skirmish_shot','anchoring_arrow'].includes(card.id)&&targets.some(id=>this.allies().some(b=>b.id!==a.id&&b.hp>0&&distance(this.actor(id).pos,b.pos)===1)))return 2;
      return 0;
    }
    price(card,targets=[]){return card.cost+this.surcharge(card,targets);}
    unavailable(id){
      const a=this.active,c=this.card(id);
      if(a.hp<=0)return 'Postać nieprzytomna';
      if(id==='move')return this.movement()>0?'':'Brak ruchu';
      if(id==='attack'||id==='item')return a.ordinary?'':'Atak / przedmiot wykorzystany';
      if(id==='focus')return a.hero&&a.special?'':'Specjalna wykorzystana';
      if(!c)return 'Brak tej mocy';
      if(!a.special)return 'Specjalna wykorzystana';
      if(c.budget.includes('A')&&!a.ordinary)return 'Wymaga ataku i specjalnej';
      if(id==='bastion_charge'&&(a.moved||a.moveLocked||this.movement()<=0))return 'Wymaga pełnego, niewykorzystanego ruchu';
      if(id==='rage'&&this.status(a,'rage'))return 'Szał już aktywny';
      if(id==='shield_bash'&&!a.hasShield)return 'Wymaga tarczy';
      const blocked=this.resonancePreview(c).blockedReasons;if(blocked.length)return blocked.join(' · ');
      return a.charges<this.price(c,this.s.preview?.targets??[])?'Za mało ładunków':'';
    }
    choose(id){
      if(this.s.phase!=='idle'||this.unavailable(id))return false;
      this.s.preview={id,targets:[],destination:null,path:null,center:null,exclude:undefined};
      this.s.phase='preview';
      if(['rage','second_wind','hide','focus','item'].includes(id))this.s.preview.targets=[this.active.id];
      if(['roar','force_wave','preserve_life'].includes(id))this.s.preview.center=copy(this.active.pos);
      return true;
    }
    area(p=this.s.preview){
      if(!p?.center)return [];
      const radius=(p.id==='flame_fan'?1:2)+(this.effectModifiers(p.id).range_bonus??0);
      return Object.values(this.s.actors).filter(a=>a.hp>0&&distance(a.pos,p.center)<=radius&&
        (p.id==='flame_fan'||(p.id==='preserve_life'?a.hero===this.active.hero:a.hero!==this.active.hero))).map(a=>a.id);
    }
    legalTargets(p=this.s.preview){
      if(!p)return [];
      const a=this.active,id=p.id,mods=this.effectModifiers(id),range=mods.range_bonus??0;
      if(['bless','healing_word','inspiration','passage_song','energy_recovery','arcane_shield'].includes(id))return this.allies().filter(b=>distance(a.pos,b.pos)<=6+range&&(b.hp>0||id==='healing_word')&&(!['inspiration','energy_recovery'].includes(id)||b.id!==a.id)&&!(id==='inspiration'&&b.hymn));
      return this.enemies().filter(b=>{
        const d=distance(a.pos,b.pos);
        if(id==='guard_vault')return d<=4+range&&neighbors(b.pos).some(q=>this.free(q,a.id));
        if(id==='bastion_charge'||id==='charge')return Boolean(this.adjacentPath(a,b,id==='charge'?3+(mods.move_bonus??0):this.movement()+(mods.move_bonus??0)));
        if(['shield_bash','hamstring_cut','breaking_strike','powerful_strike'].includes(id))return d===1;
        if(id==='shadow_attack'&&!a.hidden.includes(b.id))return false;
        if(id==='hunters_mark')return d<=12+range&&this.visible(a,b.pos);
        if(['sacred_flame','mockery','force_darts'].includes(id))return d<=6+range&&(id==='mockery'||this.visible(a,b.pos));
        const from=id==='skirmish_shot'&&p.destination?{...a,pos:p.destination}:a;
        return distance(from.pos,b.pos)<=a.weapon.range+range&&this.visible(from,b.pos);
      });
    }
    select(p){
      if(this.s.phase==='task'&&this.s.task?.type==='bonusTarget'){
        const task=this.s.task,target=task.targets.map(id=>this.actor(id)).find(a=>a.hp>0&&same(a.pos,p));
        if(!target)return false;task.target=target.id;return true;
      }
      if(this.s.phase==='task'&&this.s.task?.type==='relocate'){
        if(!this.relocationFields(this.s.task).some(q=>same(q,p)))return false;
        this.s.task.destination=copy(p);return true;
      }
      if(this.s.phase!=='preview'||!this.inBounds(p))return false;
      const v=this.s.preview,a=this.active,mods=this.effectModifiers(v.id);
      if(v.id==='flame_fan'){
        if(distance(a.pos,p)>6+(mods.range_bonus??0))return false;
        v.center=copy(p);delete v.exclude;return true;
      }
      if(['move','misty_step','skirmish_shot'].includes(v.id)){
        if(!this.free(p,a.id))return false;
        const limit=v.id==='move'?this.movement():v.id==='skirmish_shot'?2+(mods.move_bonus??0):6+(mods.range_bonus??0);
        const path=v.id==='misty_step'?distance(a.pos,p)<=limit&&this.visible(a,p)?{cells:[p],cost:0}:null:this.path(a,p,limit);
        if(!path)return false;v.destination=copy(p);v.path=path;v.targets=[];return true;
      }
      const target=this.legalTargets(v).find(b=>same(b.pos,p));
      if(v.id==='guard_vault'&&v.targets.length&&this.free(p,a.id)&&distance(this.actor(v.targets[0]).pos,p)===1){
        const path=this.path(a,p,100,true);if(!path)return false;v.destination=copy(p);v.path=path;return true;
      }
      if(!target)return false;
      if(['bless','passage_song'].includes(v.id)){
        if(v.targets.includes(target.id))v.targets=v.targets.filter(id=>id!==target.id);
        else if(v.targets.length<2)v.targets.push(target.id);
      }else if(['double_shot','force_darts'].includes(v.id)){
        const max=v.id==='force_darts'?3:2;if(v.targets.length===max)v.targets=[];v.targets.push(target.id);
      }else v.targets=[target.id];
      if(['bastion_charge','charge'].includes(v.id))Object.assign(v,this.adjacentPath(a,target,v.id==='charge'?3+(mods.move_bonus??0):this.movement()+(mods.move_bonus??0)));
      if(v.id==='guard_vault'){v.destination=null;v.path=null;}
      return true;
    }
    selectTarget(id){
      // Skirmish needs a second, figure-selection phase after the movement preview.
      if(this.s.phase==='preview'&&this.s.preview.id==='skirmish_shot'&&this.s.preview.destination){
        if(!this.legalTargets().some(a=>a.id===id))return false;this.s.preview.targets=[id];return true;
      }
      return this.actor(id)?this.select(this.actor(id).pos):false;
    }
    exclude(id){
      const p=this.s.preview;if(this.s.phase!=='preview'||!['flame_fan','force_wave'].includes(p.id)||!p.center)return false;
      if(id!==null&&!this.area().includes(id))return false;p.exclude=id;return true;
    }
    ready(){
      const p=this.s.preview;if(!p||this.s.phase!=='preview'||this.unavailable(p.id))return false;
      if(['force_wave','flame_fan'].includes(p.id))return Boolean(p.center)&&p.exclude!==undefined;
      if(['roar','preserve_life'].includes(p.id))return true;
      if(['move','misty_step'].includes(p.id))return Boolean(p.destination);
      if(['guard_vault','bastion_charge','charge','skirmish_shot'].includes(p.id))return Boolean(p.destination)&&p.targets.length===1;
      return p.targets.length>=(p.id==='double_shot'?2:p.id==='force_darts'?3:1);
    }
    cancel(){
      if(this.s.phase==='preview'){this.s.preview=null;this.s.phase='idle';return true;}
      if(this.s.task?.type==='relocate'){this.s.task.destination=null;return true;}
      return false;
    }
    revalidate(p){
      const mods=this.effectModifiers(p.id);
      if(p.center&&(!this.inBounds(p.center)||(p.id==='flame_fan'&&distance(this.active.pos,p.center)>6+(mods.range_bonus??0))))return false;
      if(p.exclude!==undefined&&p.exclude!==null&&!this.area(p).includes(p.exclude))return false;
      if(p.destination&&!this.free(p.destination,this.active.id))return false;
      if(p.id==='misty_step'&&(distance(this.active.pos,p.destination)>6+(mods.range_bonus??0)||!this.visible(this.active,p.destination)))return false;
      if(p.targets.some(id=>id!==this.active.id&&!this.legalTargets(p).some(a=>a.id===id)))return false;
      if(['bastion_charge','charge'].includes(p.id)){
        const found=this.adjacentPath(this.active,this.actor(p.targets[0]),p.id==='charge'?3+(mods.move_bonus??0):this.movement()+(mods.move_bonus??0));
        if(!found||!same(found.destination,p.destination)||JSON.stringify(found.path)!==JSON.stringify(p.path))return false;
      }
      if(p.path&&['move','guard_vault','skirmish_shot'].includes(p.id)){
        const path=this.path(this.active,p.destination,p.id==='move'?this.movement():p.id==='skirmish_shot'?2+(mods.move_bonus??0):100,p.id==='guard_vault');
        if(JSON.stringify(path)!==JSON.stringify(p.path))return false;
      }
      return true;
    }
    commit(){
      if(!this.ready()||!this.revalidate(this.s.preview))return false;
      const p=copy(this.s.preview),a=this.active,c=this.card(p.id),resonance=this.resonancePreview(c),modifiers=this.effectModifiers(c);
      this.s.preview=null;this.s.phase='task';this.s.action={...p,serial:++this.s.serial,actor:a.id,harmed:[],damageGroups:{},handledHooks:[],results:[],hadChain:Boolean(this.s.chain),card:Boolean(c),closed:false,resonance,modifiers};
      if(c){
        const cost=this.price(c,p.targets);a.charges-=cost;a.special=false;if(c.budget.includes('A'))a.ordinary=false;
        if(resonance.transition==='reset')this.endChain('runa nie podtrzymuje poprzedniej');
        a.continued=true;
        if(a.id==='nimra'&&a.lastRune&&a.lastRune!==c.rune)this.offerRegen(a,'Inna runa niż poprzednia moc');
        a.powerStreak=a.lastPower===p.id?a.powerStreak+1:1;a.lastPower=p.id;a.lastRune=c.rune;
        this.note(`${a.name}: ${c.name}, −${cost} ładunków.`);
      }else if(p.id==='focus'){a.special=false;this.endChain('Skupienie');}
      else if(['attack','item'].includes(p.id))a.ordinary=false;
      this.plan(p,a);this.s.queue.push({type:'finish'});this.advance();return true;
    }
    diceTask(label,actor,count,sides,outcome,extra={}){return {type:'roll',label,actor,parts:[{count,sides,label}],outcome,...extra};}
    saveTask(target,ability,dc,effect){return {type:'save',target,ability,dc,effect};}
    plan(p,a){
      const q=this.s.queue,id=p.id,t=p.targets[0],dc=this.data.rules.save_dc_base,mods=this.s.action.modifiers;
      const attack=()=>p.targets.forEach(target=>q.push({type:'attack',actor:a.id,target,power:id}));
      const heal=(sides,modifier=0,targets=p.targets)=>{
        const task=this.diceTask('Leczenie',a.id,1,sides,'healGroup',{targets,modifier:modifier+(mods.heal_flat??0),power:true});
        for(const die of mods.heal_dice??[])task.parts.push({...die,label:'Rezonans · leczenie'});
        q.push(task);
      };
      if(id==='focus')q.push(this.diceTask('Skupienie · odzysk ładunków',a.id,1,20,'charges',{target:a.id}));
      else if(id==='item')q.push(this.diceTask('Mikstura · 2k4 + 2 PW',a.id,2,4,'heal',{target:a.id,modifier:2}));
      else if(id==='second_wind')heal(10,this.data.heroes[a.id].level);
      else if(id==='rage')q.push({type:'status',target:a.id,status:'rage',extra:{remaining:Math.max(1,a.abilities.strength+a.abilities.constitution+(mods.duration_bonus??0))}});
      else if(id==='hide'){
        const advantage=Boolean(mods.hide_advantage||mods.check_advantage);
        const task=this.diceTask('Całun cienia · Zręczność',a.id,1,20,'hide',{modifier:a.abilities.dexterity,dc:Math.min(...this.enemies().map(b=>b.perception))-(mods.perception_penalty??0)+1,perceptionPenalty:mods.perception_penalty??0,mode:advantage?'advantage':'normal'});
        if(advantage)task.parts.push({count:1,sides:20,label:'Druga k20'});q.push(task);
      }else if(id==='shield_bash'){
        a.offensive=true;q.push(this.diceTask('Impuls egidy · obrona przeciwnika',t,1,20,'contest',{source:a.id,modifier:Math.max(this.actor(t).abilities.strength,this.actor(t).abilities.dexterity)}));
      }else if(['move','bastion_charge','charge','guard_vault','skirmish_shot'].includes(id)){
        const normal=id==='move',steps=p.path.cells;let prev=a.pos;
        if(id==='bastion_charge'){a.moveLocked=true;a.tempMove=0;a.offensive=true;}
        for(const pos of steps){q.push({type:'moveStep',actor:a.id,from:copy(prev),pos,cost:normal?(this.s.board.difficult.some(d=>same(d,pos))?2:1):0,opportunities:id!=='skirmish_shot'&&!mods.no_opportunity});prev=pos;}
        if(id==='bastion_charge')q.push(this.saveTask(t,'constitution',dc+a.abilities.strength+steps.length,{kind:'prone',source:a.id,savePenalty:mods.enemy_save_penalty??0}));
        if(['charge','skirmish_shot'].includes(id))attack();
      }else if(id==='misty_step')q.push({type:'moveStep',actor:a.id,pos:p.destination,cost:0,opportunities:false});
      else if(['attack','breaking_strike','powerful_strike','shadow_attack','hamstring_cut','double_shot','anchoring_arrow'].includes(id))attack();
      else if(id==='hunters_mark'){
        a.mark=t;
        if(mods.enemy_move_penalty)this.addStatus(this.actor(t),'movePenalty',{name:`−${mods.enemy_move_penalty} pola ruchu`,value:mods.enemy_move_penalty,untilEnd:t,turn:this.actor(t).turn+1});
        this.note(`${a.name}: Piętno łowcy → ${this.actor(t).name}.`);
      }else if(id==='inspiration'){
        const sides=mods.hymn_sides??6;
        this.actor(t).hymn={source:a.id,sides};this.note(`${this.actor(t).name}: Hymn odwagi 1k${sides}, do wykorzystania.`);
      }else if(id==='energy_recovery')q.push(this.diceTask('Akord odnowy · odzysk ładunków',a.id,1,6,'charges',{target:t,modifier:mods.charge_bonus_flat??0}));
      else if(id==='healing_word')heal(6,a.abilities.wisdom);
      else if(id==='preserve_life')heal(6,0,this.area(p));
      else if(['bless','arcane_shield'].includes(id))p.targets.forEach(target=>q.push({type:'status',target,status:id==='bless'?'bless':'arcane',extra:{value:(id==='bless'?1:2)+(id==='bless'?mods.bless_bonus??0:mods.target_ac_next_turn??0),...this.turnDuration(a)}}));
      else if(id==='passage_song')p.targets.forEach(target=>q.push({type:'relocate',target,source:a.id,radius:2+(mods.move_bonus??0),walk:true,opportunities:false,label:'Pieśń przejścia',destination:null}));
      else if(id==='force_darts')p.targets.forEach((target,index)=>q.push({type:'damage',actor:a.id,target,power:id,components:[{count:1,sides:4,modifier:1,damage_type:'force',label:'Pocisk eteru'},...(index===0?copy(mods.first_damage_dice??[]).map(d=>({...d,modifier:d.modifier??0,label:d.label??'Rezonans · pierwszy pocisk'})):[])]}));
      else if(id==='roar'){
        const targets=this.area(p);if(targets.length)a.offensive=true;
        targets.forEach(target=>q.push(this.saveTask(target,'wisdom',dc+a.abilities.strength,{kind:'fear',source:a.id,savePenalty:mods.enemy_save_penalty??0,movePenalty:mods.enemy_move_penalty??0})));
      }else if(['sacred_flame','mockery','force_wave','flame_fan'].includes(id)){
        a.offensive=true;
        const config={sacred_flame:['dexterity','wisdom',6,'radiant',false],mockery:['wisdom','charisma',4,'psychic',false],force_wave:['strength','intelligence',6,'force',true],flame_fan:['dexterity','intelligence',6,'fire',true]}[id];
        const targets=['force_wave','flame_fan'].includes(id)?this.area(p).filter(id=>id!==p.exclude):p.targets;
        const task=this.diceTask('Obrażenia mocy · jeden rzut dla obszaru',a.id,2,config[2],'areaDamage',{targets,saveAbility:config[0],dc:dc+a.abilities[config[1]],damage_type:config[3],half:config[4],fear:id==='mockery',savePenalty:mods.enemy_save_penalty??0,movePenalty:mods.enemy_move_penalty??0});
        for(const die of mods.damage_dice_extra??[])task.parts.push({...die,label:die.label??'Rezonans · obrażenia'});
        q.push(task);
      }
    }
    offerRegen(a,reason){if(a?.hero&&a.regenRound!==this.s.round)a.regenReason=reason;}
    heal(a,amount,source=null,power=false){
      const before=a.hp,low=before<a.maxHp/2;
      const bonus=power&&source?.id==='dagna'&&a.id!==source.id?2:0;
      a.hp=Math.min(a.maxHp,a.hp+Math.max(1,amount+bonus));
      if(power&&source?.id==='dagna'&&a.id!==source.id&&low&&a.hp>before)this.offerRegen(source,'Leczenie sojusznika poniżej połowy PW');
      this.note(`${a.name}: +${a.hp-before} PW (${a.hp}/${a.maxHp}).`);
    }
    damage(a,components,source){
      let prevented=0,temporary=0,hp=0;
      for(const part of components){
        let value=part.value;
        if(this.status(a,'rage')&&['slashing','piercing','bludgeoning'].includes(part.damage_type))value=Math.floor(value/2);
        const shield=part.damage_type==='psychic'?0:Math.min(a.shield,value);a.shield-=shield;value-=shield;prevented+=shield;
        const cup=Math.min(a.cup,value);a.cup-=cup;value-=cup;temporary+=cup;
        const lost=Math.min(a.hp,value);a.hp-=lost;hp+=lost;
      }
      if(temporary+hp>0){
        if(this.s.action&&!this.s.action.harmed.includes(a.id))this.s.action.harmed.push(a.id);
        if(this.s.action&&source){
          const groups=this.s.action.damageGroups;
          if(!groups[source.id])groups[source.id]=[];
          if(!groups[source.id].includes(a.id))groups[source.id].push(a.id);
        }
        if(a.id==='brakka'&&this.status(a,'rage')&&source&&!source.hero)this.offerRegen(a,'Obrażenia podczas Szału');
      }
      this.note(`${a.name}: −${hp} PW${temporary?`, −${temporary} tymczasowych PW`:''}${prevented?`, osłona zapobiega ${prevented}`:''}.`);
      return {prevented,temporary,hp};
    }
    attackTask(t){
      const a=this.actor(t.actor),b=this.actor(t.target);if(a.hp<=0||b.hp<=0)return;
      a.offensive=true;
      const melee=a.weapon.kind==='melee',hidden=a.hidden.includes(b.id);
      const mods=this.actionModifiers(a.id,t.power);
      const advantage=Boolean(hidden||(melee&&this.status(b,'prone'))||mods.attack_advantage||mods.check_advantage||this.status(a,'nextAttack'));
      a.statuses=a.statuses.filter(s=>s.type!=='nextAttack');
      const disadvantage=Boolean(this.status(a,'fear'))||(!melee&&this.enemies(a).some(e=>distance(a.pos,e.pos)===1));
      a.statuses=a.statuses.filter(s=>s.type!=='fear');
      const mode=advantage===disadvantage?'normal':advantage?'advantage':'disadvantage';
      const precision=a.id==='erynd'&&!a.shot&&!a.moved?1:0;a.shot=true;
      const modifier=a.abilities[a.weapon.ability]+(this.status(a,'bless')?.value??0)+precision-(!melee&&this.status(b,'prone')?2:0);
      const task=this.diceTask(`${a.name} → ${b.name} · ${a.weapon.name}`,a.id,1,20,'attack',{target:b.id,modifier,dc:this.ac(b),mode,power:t.power,hidden,melee,reactionPending:Boolean(t.reactionPending)});
      if(mode!=='normal')task.parts.push({count:1,sides:20,label:'Druga k20'});
      this.s.queue.unshift(task);
    }
    damageTask(t){
      const a=this.actor(t.actor),b=this.actor(t.target);if(a.hp<=0||b.hp<=0)return;
      const components=copy(t.components);
      const parts=components.filter(c=>c.count).map(c=>({count:c.count,sides:c.sides,label:c.label,modifier:c.modifier??0,damage_type:c.damage_type}));
      this.s.queue.unshift({type:'roll',label:`Obrażenia → ${b.name}`,actor:a.id,parts,outcome:'damage',target:b.id,components,divisor:t.divisor??1,power:t.power,hit:t.hit,hidden:t.hidden});
    }
    relocationFields(t){
      const a=this.actor(t.target);if(!a||a.hp<=0)return [];
      const fields=[];
      for(let y=0;y<this.s.board.height;y++)for(let x=0;x<this.s.board.width;x++){
        const p={x,y};if(distance(a.pos,p)>t.radius||!this.free(p,a.id)||(!t.walk&&t.label==='Impuls egidy'&&same(p,a.pos)))continue;
        if(!t.walk||this.path(a,p,t.radius))fields.push(p);
      }return fields;
    }
    moveStep(t){
      const a=this.actor(t.actor);
      if(a.hp<=0){
        this.note(`${a.name}: ruch przerwany. Ustaw figurkę na rzeczywistym polu ${a.pos.x},${a.pos.y}.`);
        this.s.queue=this.s.queue.filter(next=>next.type!=='moveStep'||next.actor!==a.id);return;
      }
      if(t.opportunities&&!t.checked){
        const responders=this.enemies(a).filter(b=>b.reaction&&b.weapon.kind==='melee'&&distance(b.pos,a.pos)<=1&&distance(b.pos,t.pos)>1&&!a.hidden.includes(b.id));
        if(responders.length){
          this.s.queue.unshift(...responders.map(b=>({type:'opportunity',actor:b.id,target:a.id})),{...t,checked:true});return;
        }
      }
      const previousFlanks=this.enemies(a).filter(b=>this.flanking(a,b)).map(b=>b.id);
      a.pos=copy(t.pos);a.moved=true;
      const bonusSpent=Math.min(a.tempMove??0,t.cost);a.tempMove-=bonusSpent;a.baseSpent+=t.cost-bonusSpent;
      if(a.id==='mira'&&this.enemies(a).some(b=>!previousFlanks.includes(b.id)&&this.flanking(a,b)))this.offerRegen(a,'Wejście na flankę własnym ruchem');
    }
    advance(){
      if(this.s.task)return;
      while(this.s.queue.length){
        const t=this.s.queue.shift();
        if(t.type==='attack'){this.attackTask(t);continue;}
        if(t.type==='damage'){this.damageTask(t);continue;}
        if(t.type==='status'){this.addStatus(this.actor(t.target),t.status,t.extra);continue;}
        if(t.type==='moveStep'){this.moveStep(t);continue;}
        if(t.type==='save'){
          const a=this.actor(t.target);if(a.hp<=0||this.actor(t.effect.source).hp<=0)continue;
          const disadvantage=a.id==='mira'&&a.hidden.length;
          const roll=this.diceTask(`${a.name} · obrona ${t.ability}`,a.id,1,20,'save',{dc:t.dc,modifier:a.abilities[t.ability]+(this.status(a,'bless')?.value??0)-(t.effect.savePenalty??0),effect:t.effect,mode:disadvantage?'disadvantage':'normal'});
          if(disadvantage)roll.parts.push({count:1,sides:20,label:'Druga k20'});
          this.s.queue.unshift(roll);continue;
        }
        if(t.type==='finish'){this.finish();continue;}
        if(t.type==='closeAction'){this.closeAction();continue;}
        if(t.type==='opportunity'){
          const source=this.actor(t.actor),target=this.actor(t.target);
          if(!source.reaction||source.hp<=0||target.hp<=0)continue;
          if(!source.hero){this.s.queue.unshift({type:'attack',actor:source.id,target:target.id,power:'opportunity',reactionPending:true});continue;}
        }
        if(t.type==='relocate'&&!this.relocationFields(t).length)continue;
        if(t.type==='recover'&&(this.actor(t.actor).regenRound===this.s.round||!this.actor(t.actor).regenReason))continue;
        this.s.task=t;this.s.phase='task';return;
      }
      this.s.phase=this.s.action?'result':'idle';
    }
    finish(){
      const action=this.s.action;if(!action||action.closed)return;
      const a=this.actor(action.actor),mods=action.modifiers??{};
      if(a.id==='nimra'&&action.card&&action.harmed.filter(id=>!this.actor(id).hero).length>=2)this.offerRegen(a,'Moc zraniła co najmniej dwóch wrogów');
      action.closed=true;
      if(action.card&&a.hp>0){
        if(mods.self_ac_next_turn)this.grantAc(a,mods.self_ac_next_turn,a,action.id);
        if(mods.self_temp_hp)this.grantPool(a,'temporary',mods.self_temp_hp,a);
        if(mods.next_attack_advantage)this.addStatus(a,'nextAttack',{name:'Przewaga w najbliższym ataku',...this.turnDuration(a)});
        const targets=action.id==='preserve_life'?this.area(action):action.targets;
        for(const id of targets){
          const target=this.actor(id);if(!target?.hero||target.hp<=0)continue;
          if(mods.target_temp_hp)this.grantPool(target,'temporary',mods.target_temp_hp,a);
          if(mods.shield_pool)this.grantPool(target,'prevention',mods.shield_pool,a);
          if(mods.target_ac_next_turn&&action.id!=='arcane_shield')this.grantAc(target,mods.target_ac_next_turn,a,action.id);
        }
        if(mods.bonus_move&&action.successful&&!a.moveLocked&&!this.status(a,'root'))this.s.queue.push({type:'relocate',target:a.id,source:a.id,radius:mods.bonus_move,walk:true,opportunities:!mods.no_opportunity,label:'Ruch po mocy',destination:null});
        if(mods.adjacent_ally_heal_dice){
          const targets=this.allies(a).filter(b=>b.id!==a.id&&b.hp>0&&distance(a.pos,b.pos)===1).map(b=>b.id);
          if(targets.length)this.s.queue.push({type:'bonusTarget',source:a.id,targets,dice:copy(mods.adjacent_ally_heal_dice),label:'Żar odnowy · wybierz sojusznika',target:null});
        }
      }
      this.s.queue.push({type:'closeAction'});
    }
    closeAction(){
      const action=this.s.action,a=this.actor(action.actor);
      if(action.card){
        const card=this.data.heroes[a.id].cards.find(c=>c.id===action.id);
        if(a.id==='lorian'&&action.hadChain&&action.resonance.transition!=='reset'&&action.resonance.memoryBefore.at(-1)?.contributor!==a.id){
          a.charges=Math.min(this.data.rules.max_charges,a.charges+1);this.note('Zgrana drużyna: Lorian +1 ładunek.');
        }
        if(card.ends_resonance)this.endChain('wyładowanie rozpatrzone w całości');
        else this.addRune(a,card.rune);
      }
      for(const h of this.heroes())if(h.regenReason&&h.regenRound!==this.s.round)this.s.queue.push({type:'recover',actor:h.id});
    }
    rollDice(){
      const t=this.s.task;if(t?.type!=='roll')return [];
      return t.parts.flatMap((part,partIndex)=>Array.from({length:part.count},(_,dieIndex)=>({...part,partIndex,dieIndex})));
    }
    isEnemyRoll(t=this.s.task){return t?.type==='roll'&&this.actor(t.actor)?.hero===false;}
    confirmEnemyRoll(rollDie){
      const t=this.s.task;if(!this.isEnemyRoll(t)||typeof rollDie!=='function')return false;
      // Randomness is supplied by the UI. Store every die and pause before resuming
      // movement/the next reaction; rendering and restoring never generate a roll.
      const checkpoint=copy(this.s),rolls=[];
      const resolveRoll=roll=>{
        let index=0;
        const dice=roll.parts.map(p=>Array.from({length:p.count},()=>{
          const value=roll.diceResults?.[index]??rollDie(p.sides);index++;
          if(!Number.isInteger(value)||value<1||value>p.sides)throw Error('Nieprawidłowy wynik kości przeciwnika');
          return value;
        }));
        const values=dice.map(part=>part.reduce((sum,value)=>sum+value,0)),result=rollResult(roll,values);
        const target=this.actor(roll.target),before=target?{hp:target.hp,cup:target.cup,shield:target.shield}:null;
        this.resolve(roll,values,result.natural,result.total,result.success);
        rolls.push({label:roll.label,outcome:roll.outcome,mode:roll.mode,parts:copy(roll.parts),dice,values,...result,
          modifier:roll.modifier??0,dc:roll.dc,
          ...(roll.outcome==='damage'?{components:damageComponents(roll,values),loss:{hp:before.hp-target.hp,cup:before.cup-target.cup,shield:before.shield-target.shield}}:{})});
      };
      try{
        this.s.task=null;
        if(t.reactionPending)this.actor(t.actor).reaction=false;
        resolveRoll(t);
        const next=this.s.queue[0];
        if(t.outcome==='attack'&&next?.type==='damage'&&next.actor===t.actor&&next.target===t.target){
          this.damageTask(this.s.queue.shift());
          resolveRoll(this.s.queue.shift());
        }
        this.s.task={type:'enemy-result',actor:t.actor,target:t.target,power:t.power,label:t.label,rolls};
        this.s.phase='task';return true;
      }catch{this.s=checkpoint;return false;}
    }
    acknowledgeEnemyResult(){
      if(this.s.task?.type!=='enemy-result')return false;
      this.s.task=null;this.pump();return true;
    }
    submitDie(value,index=this.s.task?.diceResults?.length??0){
      const t=this.s.task,dice=this.rollDice(),confirmed=t?.diceResults??[];
      if(t?.type!=='roll'||this.isEnemyRoll(t)||index!==confirmed.length||!dice[index])return false;
      if(!Number.isInteger(value)||value<1||value>dice[index].sides)return false;
      t.diceResults=[...confirmed,value];
      if(t.diceResults.length<dice.length)return true;
      const totals=t.parts.map(()=>0);
      t.diceResults.forEach((result,i)=>totals[dice[i].partIndex]+=result);
      return this.submit(totals);
    }
    submit(values){
      const t=this.s.task;if(t?.type!=='roll'||this.isEnemyRoll(t)||!Array.isArray(values)||values.length!==t.parts.length)return false;
      if(values.some((value,i)=>!Number.isInteger(value)||value<t.parts[i].count||value>t.parts[i].count*t.parts[i].sides))return false;
      this.s.task=null;
      const {natural,total,success}=rollResult(t,values);
      if(natural!==null&&this.actor(t.actor)?.hymn){
        this.s.task={type:'hymn',actor:t.actor,roll:t,values,natural,total,success};this.s.phase='task';return true;
      }
      this.resolve(t,values,natural,total,success);this.pump();return true;
    }
    decideHymn(use){
      const t=this.s.task;if(t?.type!=='hymn')return false;this.s.task=null;
      if(use){const owner=this.actor(t.actor);t.source=owner.hymn.source;const sides=owner.hymn.sides??6;owner.hymn=null;this.s.queue.unshift(this.diceTask('Hymn odwagi · dodatkowa kość',t.actor,1,sides,'hymn',{pending:t}));}
      else this.resolve(t.roll,t.values,t.natural,t.total,t.success);
      this.pump();return true;
    }
    resolve(t,values,natural,total,success){
      const a=this.actor(t.actor),target=this.actor(t.target),q=this.s.queue;
      if(t.outcome==='hymn'){
        const p=t.pending,sum=p.total+values[0],ok=p.roll.outcome==='attack'?(p.natural===20||(p.natural!==1&&sum>=p.roll.dc)):sum>=(p.roll.dc??0);
        if(ok&&p.roll.outcome==='attack')this.offerRegen(this.actor(p.source),'Sojusznik trafił, wykorzystując Hymn');
        this.resolve(p.roll,p.values,p.natural,sum,ok);return;
      }
      this.note(`${t.label}: ${values.join(', ')}${t.modifier?` ${t.modifier>=0?'+':''}${t.modifier}`:''} = ${total}${t.dc!==undefined?` / ST ${t.dc} · ${success?'sukces':'porażka'}`:''}.`);
      if(t.outcome==='heal')this.heal(target,total);
      else if(t.outcome==='healGroup')t.targets.forEach(id=>this.heal(this.actor(id),total,a,t.power));
      else if(t.outcome==='charges')target.charges=Math.min(20,target.charges+total);
      else if(t.outcome==='regenerate'){a.charges=Math.min(20,a.charges+total);a.regenReason=null;}
      else if(t.outcome==='hide'){
        const previous=a.hidden;a.hidden=this.enemies(a).filter(b=>total>b.perception-(t.perceptionPenalty??0)).map(b=>b.id);
        if(a.hidden.length&&this.s.action)this.s.action.successful=true;
        if(a.hidden.some(id=>!previous.includes(id)))this.offerRegen(a,'Ukrycie przed nowym wrogiem');
      }else if(t.outcome==='contest'){
        const source=this.actor(t.source),mods=this.actionModifiers(source.id,'shield_bash'),roll=this.diceTask('Impuls egidy · test Siły',source.id,1,20,'bash',{target:a.id,modifier:source.abilities.strength,dc:total+1,mode:mods.check_advantage?'advantage':'normal'});
        if(mods.check_advantage)roll.parts.push({count:1,sides:20,label:'Druga k20'});q.unshift(roll);
      }else if(t.outcome==='bash'){
        if(success){if(this.s.action)this.s.action.successful=true;q.unshift({type:'damage',actor:a.id,target:target.id,power:'shield_bash',components:[{count:1,sides:6,modifier:a.abilities.strength,damage_type:'bludgeoning',label:'Impuls egidy'}]});}
      }else if(t.outcome==='areaDamage'){
        q.unshift(...t.targets.map(target=>this.saveTask(target,t.saveAbility,t.dc,{kind:'damage',value:total,damage_type:t.damage_type,half:t.half,fear:t.fear,source:a.id,savePenalty:t.savePenalty,movePenalty:t.movePenalty})));
      }else if(t.outcome==='save'){
        const e=t.effect;
        if(e.kind==='damage'){
          if(!success||e.half)q.unshift({type:'damage',actor:e.source,target:a.id,divisor:success?2:1,components:[{value:e.value,count:0,damage_type:e.damage_type,label:'Moc'}]});
          if(!success&&e.fear)this.addStatus(a,'fear',{untilEnd:a.id,turn:a.turn+1});
        }else if(!success)this.addStatus(a,e.kind,{untilEnd:a.id,turn:a.turn+1});
        if(!success&&e.movePenalty)this.addStatus(a,'movePenalty',{name:`−${e.movePenalty} pola ruchu`,value:e.movePenalty,untilEnd:a.id,turn:a.turn+1});
      }else if(t.outcome==='attack'){
        if(success){
          const crit=natural===20,w=a.weapon;
          const parts=[{count:crit?(a.id==='brakka'?w.count+2:w.count*2):w.count,sides:w.sides,modifier:a.abilities[w.ability],damage_type:w.damage_type,label:w.name}];
          const extra=(sides,label,type=w.damage_type)=>parts.push({count:crit?2:1,sides,modifier:0,damage_type:type,label});
          const mods=this.actionModifiers(a.id,t.power);
          if(t.power==='breaking_strike')extra(6,'Ostrze przełamania','magic');
          for(const die of mods.attack_bonus_dice??[])parts.push({count:die.count*(crit?2:1),sides:die.sides,modifier:die.modifier??0,damage_type:die.damage_type==='weapon'?w.damage_type:die.damage_type,label:die.label??'Rezonans · moc'});
          if(this.status(a,'rage')&&t.melee)extra(6,'Runiczny szał');
          if(a.mark===target.id)extra(4,'Piętno łowcy');
          if(a.id==='mira'&&a===this.active&&!a.sneakUsed&&(t.hidden||this.flanking(a,target))){extra(6,'Cios z zaskoczenia');a.sneakUsed=true;}
          if(a.id==='brakka'&&t.melee&&!a.startAdjacent.includes(target.id))this.offerRegen(a,'Trafienie nowego sąsiada bronią wręcz');
          if(a.id==='erynd'&&(a.mark===target.id||(!a.moved&&distance(a.pos,target.pos)>=4)))this.offerRegen(a,'Cel oznaczony lub daleki strzał bez ruchu');
          q.unshift({type:'damage',actor:a.id,target:target.id,components:parts,critical:crit,power:t.power,hit:true,hidden:t.hidden});
        }else if(!a.hero){
          if(target.id==='garran'||this.shielded(target))this.offerRegen(this.actor('garran'),'Wróg chybił Garrana / Żywą osłonę');
          const blessing=this.status(target,'bless');if(blessing)this.offerRegen(this.actor(blessing.source),'Wróg chybił Pieczęć łaski');
        }
        a.hidden=[];
      }else if(t.outcome==='damage'){
        const loss=this.damage(target,damageComponents(t,values),a);
        if(t.hit&&target.hp>0){
          if(t.power==='powerful_strike')this.addStatus(target,'broken',{untilStart:a.id,turn:a.turn+1});
          if(t.power==='hamstring_cut'){this.addStatus(target,'slow',{untilEnd:target.id,turn:target.turn+1});if(t.hidden)this.addStatus(target,'roundRoot',{round:this.s.round+1});}
          if(t.power==='anchoring_arrow')this.addStatus(target,'root',{untilEnd:target.id,turn:target.turn+1});
        }
        if(t.power==='shield_bash'&&target.hp>0)q.unshift({type:'relocate',target:target.id,radius:1,label:'Impuls egidy',destination:null});
        const mods=this.actionModifiers(a.id,t.power);
        if(mods.push&&target.hp>0&&t.hit)q.unshift({type:'relocate',target:target.id,radius:mods.push,label:'Odepchnięcie mocy',destination:null});
        if(mods.enemy_move_penalty&&target.hp>0&&t.hit)this.addStatus(target,'movePenalty',{name:`−${mods.enemy_move_penalty} pola ruchu`,value:mods.enemy_move_penalty,untilEnd:target.id,turn:target.turn+1});

      }
    }
    pump(){
      // Automatic steps contain no callbacks, so an in-flight snapshot can be restored.
      while(!this.s.task&&this.s.queue[0]?.type==='closeAction'){this.s.queue.shift();this.closeAction();}
      this.advance();
      if(this.s.task?.type==='closeAction'){this.s.task=null;this.closeAction();this.advance();}
    }
    recover(use){
      const t=this.s.task;if(t?.type!=='recover')return false;
      const a=this.actor(t.actor);this.s.task=null;
      if(use&&a.charges<20&&a.regenRound!==this.s.round){a.regenRound=this.s.round;this.s.queue.unshift(this.diceTask('Odzysk klasowy',a.id,1,4,'regenerate'));}
      a.regenReason=null;this.pump();return true;
    }
    opportunity(use){
      const t=this.s.task;if(t?.type!=='opportunity')return false;this.s.task=null;
      if(use&&this.actor(t.actor).reaction){this.actor(t.actor).reaction=false;this.s.queue.unshift({type:'attack',actor:t.actor,target:t.target,power:'opportunity'});}
      this.pump();return true;
    }
    confirmRelocation(){
      const t=this.s.task;if(t?.type!=='relocate'||!t.destination||!this.relocationFields(t).some(p=>same(p,t.destination)))return false;
      const a=this.actor(t.target),wasAdjacent=this.enemies(a).some(b=>distance(a.pos,b.pos)===1);
      if(t.walk&&t.opportunities){
        const path=this.path(a,t.destination,t.radius);let previous=a.pos;
        const moves=path.cells.map(pos=>{
          const step={type:'moveStep',actor:a.id,from:copy(previous),pos,cost:0,opportunities:true};previous=pos;return step;
        });
        this.s.queue.unshift(...moves);
      }else{a.pos=copy(t.destination);if(t.walk)a.moved=true;}
      if(t.walk&&t.label==='Pieśń przejścia'&&wasAdjacent&&!this.enemies(a).some(b=>distance(a.pos,b.pos)===1))this.offerRegen(this.actor(t.source),'Pieśń przejścia wyprowadziła sojusznika z zagrożenia');
      this.note(`${t.label}: ${a.name} → ${t.destination.x},${t.destination.y}.`);this.s.task=null;this.pump();return true;
    }
    confirmBonusTarget(){
      const t=this.s.task;if(t?.type!=='bonusTarget'||!t.target||!t.targets.includes(t.target))return false;
      const source=this.actor(t.source),target=this.actor(t.target);
      if(!target?.hero||target.hp<=0||distance(source.pos,target.pos)!==1)return false;
      this.s.task=null;
      this.s.queue.unshift({type:'roll',label:'Żar odnowy · leczenie sojusznika',actor:source.id,parts:t.dice.map(d=>({...d,label:'Leczenie sojusznika'})),outcome:'healGroup',targets:[target.id],power:true});
      this.pump();return true;
    }
    acknowledge(){
      if(this.s.phase!=='result')return false;this.s.action=null;this.s.phase='idle';
      if(!this.heroes().some(h=>h.hp>0)||!this.enemies(this.heroes()[0]).length){this.endChain('koniec walki');this.s.phase='finished';}
      return true;
    }
    snapshot(){return JSON.stringify(this.s);}
    restore(raw){const state=JSON.parse(raw);if(state.version!==3||!Array.isArray(state.order)||!state.actors)throw Error('Nieprawidłowy zapis makiety');this.s=state;}
  }
  window.ResonanceModel={Encounter,distance,same,neighbors};
})();
