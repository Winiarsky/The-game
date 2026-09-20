"""Mission-zero orchestration over the existing combat, cards and board services."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from dnd_board_game.actors import Faction
from dnd_board_game.combat.scene import scene_flag, set_scene_flag, SceneResult, SceneConclusionType
from dnd_board_game.scenarios.mission_pack import MISSION_ID, read_json, text_entry, asset_url
from dnd_board_game.hardware.board_panel import panel_position, panel_feedback
from dnd_board_game.hardware.led_feedback import LedFeedback, LedFrame, LedRole
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.world import Coordinate
from .exploration_mana_board import choice
from dnd_board_game.application import party_ethos

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession, BoardScanTarget

KEY = 'mission_zero_v1'


def enabled(s: ExplorationUiSession) -> bool:
    return s.exploration.scenario_id == MISSION_ID


def root(s: ExplorationUiSession) -> Path:
    return s._scenario_asset_root()


def read(s: ExplorationUiSession) -> dict[str, Any]:
    raw = scene_flag(s.state.flags, KEY, '')
    data = json.loads(str(raw)) if raw else dict(version=2, revision=0, stage='world', index=0,
        fatigue=0, fatigue_applied=False, offered=False, outcome='', debt='', flags=[], ledger=[], visited=[])
    defaults = dict(cargo={}, searches={}, search_result='', bell='', compliment='', repair_used=False,
                    ring_identified=False, identify_attempted=False, ring_home='explore')
    for key, value in defaults.items(): data.setdefault(key, value)
    if data['stage']=='ring_equip':data['stage']='ring_identified' if data['ring_identified'] else 'ring'
    return data


def write(s: ExplorationUiSession, m: dict[str, Any]) -> None:
    m['revision'] += 1
    s.state = replace(s.state, flags=set_scene_flag(s.state.flags, KEY, json.dumps(m, ensure_ascii=False)))
    s.board_panel_context = None
    s.board_selection_revision += 1


def initialize(s: ExplorationUiSession) -> None:
    from .exploration_app import UiFlowStage
    s.exploration_setup_flow = None
    s.ui_flow_stage = UiFlowStage.LOCATION_ACTIVE
    write(s, read(s))


def label(s: ExplorationUiSession, key: str) -> str:
    return read_json(root(s), 'text/ui.json')[key]


def active_panel(s: ExplorationUiSession) -> bool:
    if not enabled(s): return False
    from .confrontation import active
    return not active(s) and read(s)['stage'] != 'battle'


def autosave(s: ExplorationUiSession) -> bool:
    """Persist a completed mission step, never an unfinished combat operation.

    Checkpoints remain separate starting positions for replaying a scene.
    The latest snapshot includes rewards and decisions from repeated visits.
    """
    from .confrontation import read_store
    from dnd_board_game.save import write_snapshot
    if not enabled(s) or s.combat_state is not None or s._snapshot_blocker() is not None:
        return False
    confrontation = read_store(s)
    if confrontation['active'] and confrontation['current']['state']['stage'] != 'result':
        return False
    write_snapshot(s.snapshot_path, s.create_snapshot())
    s._record('mission_autosaved', dict(stage=read(s)['stage'], path=str(s.snapshot_path)))
    return True


def checkpoint(s: ExplorationUiSession, m: dict[str, Any]) -> None:
    from dnd_board_game.save import write_snapshot
    if m['stage'] in ('brief', 'road', 'arrival', 'explore'):
        path = s.save_dir / (MISSION_ID + '.' + m['stage'] + '.checkpoint.json')
        if not path.exists() or m['stage'] not in m['visited']:
            if m['stage'] not in m['visited']: m['visited'].append(m['stage'])
            write(s, m)
            write_snapshot(path, s.create_snapshot())
    autosave(s)


def _set_actor(s: ExplorationUiSession, actor: Any) -> None:
    s.exploration = replace(s.exploration, actors=tuple(actor if a.id == actor.id else a for a in s.exploration.actors))
    if s.combat_state is not None:
        from dnd_board_game.combat.session import replace_actor
        s.combat_state = replace_actor(s.combat_state, actor)


def grant(s: ExplorationUiSession, m: dict[str, Any], item_id: str) -> None:
    from dnd_board_game.inventory import InventoryItem
    key = 'item:' + item_id
    if key in m['flags']: return
    data = read_json(root(s), 'mechanics/items.json')[item_id]
    item = InventoryItem(id='mission_' + item_id, name=data['name'], kind='consumable' if 'potion' in item_id else 'gear',
        equipped=False, description=data['description'], value_cp=data.get('value_cp', 0),
        armor_class_bonus=data.get('armor_class_bonus',0))
    s.state = replace(s.state, party_loot=replace(s.state.party_loot, items=(*s.state.party_loot.items, item)))
    m['flags'].append(key)
    m['ledger'].append(dict(kind='item', id=item_id, name=data['name'], amount=1, owner='party'))


def money(s: ExplorationUiSession, m: dict[str, Any], key: str, gp: int) -> None:
    from dnd_board_game.inventory.economy import CurrencyWallet
    if 'money:' + key in m['flags']: return
    owner = s.exploration.actors[0]
    _set_actor(s, replace(owner, currency=owner.currency.add(CurrencyWallet(gp=gp))))
    m['flags'].append('money:' + key)
    m['ledger'].append(dict(kind='money', id=key, name=label(s,key), amount=gp, owner=str(owner.id)))


def narrative(s: ExplorationUiSession, key: str, **values: object) -> dict[str, str]:
    """Resolve optional authored paragraphs for the actual party."""
    from . import mission_zero_recovery as recovery
    entries = read_json(root(s), 'text/index.json')
    if key == 'road':
        from .mission_setup import road_placement
        layout = road_placement(root(s))
        values['cart_fields'] = ', '.join(f'({col},{row})' for col,row in layout['positions'])
        values['party_field'] = '(' + ','.join(map(str, layout['party_position'])) + ')'
    for hero in ('mira', 'nimra'):
        fragment = key + '_' + hero
        values[hero + '_option'] = (text_entry(root(s), fragment)['body']
            if fragment in entries and recovery.has_hero(s, hero) else '')
    return text_entry(root(s), key, **values)


def scene(s: ExplorationUiSession, name: str) -> dict[str, Any]:
    data = read_json(root(s), 'mechanics/confrontations.json')[name]
    refs = ({'description':'negotiate','success':'neg_success','compromise':'neg_compromise','failure':'neg_failure'} if name == 'nessa' else {'description':'cart_confrontation','success':'road_success','failure':'fatigue_roll'} if name == 'cart' else {'description':name,'success':name+'_success','failure':name+'_failure'})
    for field,key in refs.items(): data[field] = narrative(s,key)['body']
    m = read(s)
    if name == 'quarters' and 'rumor_known' in m['flags']:
        for approach in data['approaches']: approach['dc'] -= 2
    if name == 'nessa':
        compliments = read_json(root(s), 'mechanics/compliments.json')
        if m['compliment'] == compliments['success']:
            data.update(first_test_bonus=compliments['bonus'], first_test_label='Przychylność Nessy')
    return data


def launch_confrontation(s: ExplorationUiSession, name: str) -> None:
    from . import confrontation as c
    from dnd_board_game.application.confrontation import build
    actors = tuple(a for a in s.exploration.actors if a.faction == Faction.ALLY)
    data = c.read_store(s); spec = scene(s,name)
    s.state=replace(s.state,party_position=replace(s.state.party_position,marker_position=Coordinate(*spec['party_position'])))
    previous = data.get('current') or {}
    if previous.get('mode') == 'mission' and previous.get('mission_scene') == name:
        data['active'] = True
        c.write(s,data)
        return
    data.update(active=True, current=dict(hero=str(actors[0].id), lesson='mission_'+name, mode='mission',
        mission_scene=name, members=[str(a.id) for a in actors], token=uuid4().hex, scene=spec,
        state=build(actors,spec,excluded=party_ethos.read(s.state.flags).excluded).to_data(), committed=False, roll_rules_version=2))
    s._exploration_mana_confirmed = data['current']['token']
    c.write(s,data)


def finish_confrontation(s: ExplorationUiSession, current: dict[str, Any]) -> None:
    m=read(s); name=current['mission_scene']; outcome=current['state']['outcome']
    if name == 'nessa':
        m['flags'].append('negotiated')
        if outcome == 'success': grant(s,m,'potion')
        elif outcome == 'compromise': grant(s,m,'weak_potion')
        m['stage']='brief'
    elif name == 'cart':
        m['stage']='road_success' if outcome=='success' else 'fatigue_roll'
    else:
        from .mission_zero_recovery import finish_search
        finish_search(s,m,current)
    write(s,m);checkpoint(s,m)


def synchronize(s: ExplorationUiSession) -> None:
    if not enabled(s): return
    m=read(s)
    if not m.get('shared_inventory_v1'):
        from dnd_board_game.inventory.party_equipment import deposit
        for actor in s.exploration.actors:
            discoveries=tuple(i for i in actor.inventory if i.id.startswith('mission_'))
            for item in discoveries:s.state=replace(s.state,party_loot=deposit(s.state.party_loot,item))
            if discoveries:_set_actor(s,replace(actor,inventory=tuple(i for i in actor.inventory if i not in discoveries)))
        m['shared_inventory_v1']=True;write(s,m)
    if s.combat_state is not None and m['stage'] in ('battle','surrender'):
        if not m['fatigue_applied']:
            if m['fatigue']:
                from dnd_board_game.combat.mission_effects import road_fatigue
                s.active_combat_effects += road_fatigue(tuple(str(a.id) for a in s.combat_state.actors if a.faction==Faction.ALLY),m['fatigue'],label(s,'fatigue'))
            m['fatigue_applied']=True;write(s,m)
        from dnd_board_game.combat.mission_effects import surrender_available
        remaining=sum(a.faction==Faction.ENEMY and not a.is_defeated() for a in s.combat_state.actors)
        size=sum(a.faction==Faction.ENEMY for a in s.combat_state.actors)
        if surrender_available(size,remaining,m['offered']) and not s._combat_has_pending_resolution() and not (s.combat_state.shared_mana and s.combat_state.shared_mana.pooled and s.combat_state.shared_mana.pooled.phase not in ('ready',)):
            m.update(stage='surrender',offered=True);write(s,m)
    if m['stage']=='battle' and s.combat_state is None and 'bell_battle' in s.resolved_encounter_trigger_ids:
        m['stage']='post_battle';write(s,m);autosave(s)


def combat_finished(s: ExplorationUiSession, conclusion: str) -> None:
    if not enabled(s):return
    m=read(s)
    if conclusion in ('defeat','retreat','surrender'):
        m['outcome']='defeated'
    elif not m['outcome']:
        m['outcome']='no_offer'
    m['stage']='post_battle'
    s.state=replace(s.state,flags=set_scene_flag(s.state.flags,'mission_battle_ready',False))
    from .exploration_app import UiFlowStage
    s.ui_flow_stage=UiFlowStage.LOCATION_ACTIVE
    if m['outcome']=='defeated':
        # This authored loss is capture, not death; recover to 1 HP after the encounter.
        from dnd_board_game.actors.models import DeathSaveState
        for a in s.exploration.actors:
            if a.hp<=0:_set_actor(s,replace(a,hp=1,death_saves=DeathSaveState()))
    write(s,m)
    autosave(s)


def available_potions(s: ExplorationUiSession) -> list[tuple[Any, Any]]:
    actors=s.combat_state.actors if s.combat_state else s.exploration.actors
    return [(None,i) for i in s.state.party_loot.items if i.id in ('mission_potion','mission_weak_potion') and i.quantity>0] + [(a,i) for a in actors if a.faction==Faction.ALLY for i in a.inventory
            if i.id in ('mission_potion','mission_weak_potion') and i.quantity>0]


def potion_targets(s: ExplorationUiSession) -> tuple[Any, ...]:
    if s.combat_state is None:return ()
    from dnd_board_game.combat.session import current_actor, use_turn_action
    actor=current_actor(s.combat_state)
    if actor.faction!=Faction.ALLY or actor.is_defeated() or not use_turn_action(s.combat_state).accepted:return ()
    if s._combat_has_pending_resolution():return ()
    pool=s.combat_state.shared_mana.pooled if s.combat_state.shared_mana else None
    if pool and pool.phase!='ready':return ()
    return tuple(a for a in s.combat_state.actors if a.faction==Faction.ALLY and not a.death_saves.dead
        and max(abs(a.position.col-actor.position.col),abs(a.position.row-actor.position.row))<=1)


def guild_points(s: ExplorationUiSession) -> dict[str, list[int]]:
    """Keep destination fields aligned with the printable guild tiles."""
    from .mission_setup import tiles
    catalog = tiles(root(s))
    references = read_json(root(s), 'flow.json')['guild_points']
    return {action: list(catalog[key].interaction) for action, key in references.items()}


def payload(s: ExplorationUiSession) -> dict[str, Any] | None:
    if not enabled(s):return None
    m=read(s); stage=m['stage']; controls=[]; textkey=stage; marker=None; image='assets/images/posterunek.png'; setup=None
    def opt(slot: int, action: str, key: str, **extra: object) -> None:
        controls.append(choice(slot,action,label(s,key),**extra))
    if stage=='heroes':
        hero_id=str(s.exploration.actors[m['index']].id)
        textkey='hero_'+hero_id
        image='assets/images/'+hero_id+'.png'
    if stage=='explore':marker=[s.state.party_position.marker_position.col,s.state.party_position.marker_position.row]
    if stage=='post_battle':textkey='after_'+(m['outcome'] or 'no_offer')
    if stage=='return':textkey='return_'+m['debt']
    if stage in ('guild_setup','post_setup'):
        from .mission_setup import prepare
        setup=prepare(root(s),read_json(root(s),'maps/setup.json')[stage][m['index']])
        textkey=None;marker=setup.get('position');image=''
    if stage in ('brief','why','road_info','departure','negotiate') or stage=='guild_setup':image='assets/images/nessa_desk_interaction.png' if stage!='guild_setup' else image
    if stage in ('road','road_success','fatigue_roll','fatigue_result'):image='assets/images/road.png'
    if stage=='guild_hub':
        pass  # Destinations are selected with the party figure on map fields.
    elif stage=='arena_unavailable':opt(29,'guild_back','guild_back')
    elif stage=='brief':
        opt(6,'why','why');opt(7,'road_info','road_info')
        if 'negotiated' not in m['flags']:opt(8,'negotiate','negotiate')
        opt(28,'depart','depart')
    elif stage=='departure':marker=[9,24];opt(28,'exit','exit')
    elif stage=='road':
        opt(6,'cart','cart')
        from .confrontation import read_store
        current = read_store(s).get('current') or {}
        if not m.get('cart_started') and not (current.get('mode')=='mission' and current.get('mission_scene')=='cart'):
            opt(7,'cart_coerce','cart_coerce')
    elif stage=='arrival':opt(28,'battle','battle')
    elif stage=='surrender':opt(6,'accept','accept');opt(7,'refuse','refuse')
    elif stage=='rumor':opt(28,'back','back')
    elif stage=='load':opt(28,'loaded','loaded')
    elif stage=='summary':opt(28,'finish','finish')
    elif stage=='battle':
        if available_potions(s) and potion_targets(s):opt(24,'potion','potion')
    elif stage=='potion_target':
        for i,a in enumerate(potion_targets(s)):controls.append(choice(6+i,'potion_target',a.name,target=str(a.id)))
        opt(29,'potion_cancel','cancel')
    elif stage=='potion_roll':opt(29,'potion_cancel','cancel')
    elif stage=='fatigue_roll':pass
    else:opt(28,'next','next')
    from . import mission_zero_recovery as recovery
    from . import party_preparation as preparation
    revised_choices=preparation.choices(s,m) if stage in preparation.STAGES else recovery.choices(s,m)
    if revised_choices is not None:controls=revised_choices
    textkey=recovery.presentation(s,m,textkey)
    entries=read_json(root(s),'text/index.json')
    presentation=entries.get(textkey,{})
    image=presentation.get('image',image)
    image_layout=presentation.get('image_layout','landscape')
    if image_layout not in ('landscape','portrait'):
        image_layout='landscape'
    text=narrative(s,textkey,fatigue=m['fatigue'],fatigue_duration=f"{m['fatigue']} " + ('pełną rundę' if m['fatigue']==1 else 'pełne rundy')) if textkey in entries else dict(title=setup['title'] if setup else label(s,'mission'),body=setup['body'] if setup else '',speaker='Narrator')
    checkpoints=[dict(id=k,label=label(s,'checkpoint_'+k)) for k in m['visited'] if (s.save_dir/(MISSION_ID+'.'+k+'.checkpoint.json')).exists()]
    potion_data=read_json(root(s),'mechanics/items.json').get(m.get('potion_id',''),{})
    if stage=='identify_roll':potion_data=dict(sides=20,dice=1,bonus=recovery.identification_modifier(s))
    point_positions=read_json(root(s),'flow.json')['point_positions']
    combat_tip=''
    if s.combat_state and s.combat_state.shared_mana and s.combat_state.shared_mana.pooled:
        pool=s.combat_state.shared_mana.pooled
        from dnd_board_game.combat.session import current_actor
        actor=current_actor(s.combat_state)
        combat_tip=label(s,'combat_drain' if pool.phase=='drain' else 'combat_loaded' if str(actor.id) in pool.heroes and pool.full(str(actor.id)) else 'combat_charge')
    return dict(print_cutouts=asset_url(root(s),'maps/print/elements_A4.pdf') if (root(s)/'maps/print/elements_A4.pdf').exists() else '',roll_bonus=potion_data.get('bonus',0),print_map=asset_url(root(s),'maps/print/'+('guild' if stage=='guild_setup' else 'outpost')+'_A4.pdf'),combat_tip=combat_tip,point_positions=point_positions,roll_count=potion_data.get('dice',1),roll_sides=potion_data.get('sides',4),active=active_panel(s),stage=stage,revision=m['revision'],text=text,image=asset_url(root(s),image) if image and (root(s)/image).is_file() else '',
        equipment=preparation.payload(s,m),identification_dc=recovery.identification_dc(s),recovery=recovery.status_payload(s,m),reading=active_panel(s) and stage not in ('fatigue_roll','potion_roll','identify_roll',*preparation.STAGES),guild_points=guild_points(s) if stage=='guild_hub' else {},image_layout=image_layout,choices=controls,marker=marker,setup=setup,ledger=m['ledger'],debt=m['debt'],fatigue=m['fatigue'],checkpoints=checkpoints,
        ui=read_json(root(s),'text/ui.json'),rolling=stage in ('fatigue_roll','potion_roll','identify_roll'), can_save=s._snapshot_blocker() is None)


def command(s: ExplorationUiSession, data: dict[str, Any]) -> dict[str, object]:
    if not enabled(s):raise ValueError('Ta misja nie jest aktywna.')
    m=read(s);action=str(data.get('action',''));stage=m['stage']
    if type(data.get('revision')) is not int or data['revision']!=m['revision']:raise ValueError('Nieaktualny krok misji.')
    if action=='checkpoint':
        key=str(data.get('id',''))
        if key not in m['visited']:raise ValueError('Nieznany punkt kontrolny.')
        return s._load_snapshot_from_path(s.save_dir/(MISSION_ID+'.'+key+'.checkpoint.json'))
    allowed={c['action'] for c in payload(s)['choices']}
    if stage=='guild_hub':allowed.update(guild_points(s))
    if stage=='explore':allowed.update(('leader','armory','quarters','store'))
    if action not in allowed and not (action=='roll' and stage in ('fatigue_roll','potion_roll','identify_roll')):raise ValueError('Działanie niedostępne w tym etapie.')
    from . import mission_zero_recovery as recovery
    from . import party_preparation as preparation
    if preparation.handle(s,m,action,data):pass
    elif recovery.handle(s,m,action,data):pass
    elif action=='next':
        if stage=='world':m.update(stage='heroes',index=0)
        elif stage=='heroes':
            m['index']+=1
            if m['index']>=len(s.exploration.actors):m.update(stage='party',index=0)
        elif stage=='party':m.update(stage='guild_setup',index=0)
        elif stage in ('guild_setup','post_setup'):
            step=read_json(root(s),'maps/setup.json')[stage][m['index']]
            if step.get('party'):
                s.state=replace(s.state,party_position=replace(s.state.party_position,marker_position=Coordinate(*step['position'])))
            m['index']+=1
            if m['index']>=len(read_json(root(s),'maps/setup.json')[stage]):m.update(stage='guild_hub' if stage=='guild_setup' else 'explore',index=0)
        elif stage in read_json(root(s),'flow.json')['simple_next']:
            m['stage']=read_json(root(s),'flow.json')['simple_next'][stage]
        elif stage=='post_battle':m.update(stage='post_setup',index=0)
        else:raise ValueError('Brak przejścia.')
    elif action in ('talk_nessa','visit_arena'):
        position=Coordinate(*guild_points(s)[action])
        s.state=replace(s.state,party_position=replace(s.state.party_position,marker_position=position))
        m['stage']='brief' if action=='talk_nessa' else 'arena_unavailable'
        if action=='talk_nessa':grant(s,m,'key')
    elif action=='guild_back':m['stage']='guild_hub'
    elif action in ('why','road_info'):m['stage']=action
    elif action in ('negotiate','cart'):
        if action=='cart':m['cart_started']=True
        write(s,m);launch_confrontation(s,'nessa' if action=='negotiate' else 'cart');return s.state_payload()
    elif action=='cart_coerce':
        event=read_json(root(s),'mechanics/ethos.json')['cart_coerce']
        s.state=replace(s.state,flags=party_ethos.apply_choice(s.state.flags,event['id'],event['direction']))
        m.update(stage='cart_coerced',fatigue=0,cart_started=True)
        m['flags'].append('cart_exchanged')
    elif action=='depart':
        preparation.begin(m,'departure')
    elif action=='exit':
        s.state=replace(s.state,party_position=replace(s.state.party_position,marker_position=Coordinate(9,24)))
        m['stage']='road';m['equipment_locked']=True
    elif action=='roll' and stage=='fatigue_roll':
        value=data.get('roll')
        if type(value) is not int or not 1<=value<=4:raise ValueError('Podaj naturalny wynik k4 od 1 do 4.')
        m.update(fatigue=value,stage='fatigue_result')
    elif action=='potion':
        if not potion_targets(s) or not available_potions(s):raise ValueError('Mikstura nie jest teraz dostępna.')
        m.update(stage='potion_target',potion_id=available_potions(s)[0][1].id.removeprefix('mission_'))
    elif action=='potion_target':
        target=str(data.get('target',''))
        if target not in {str(a.id) for a in potion_targets(s)}:raise ValueError('Cel poza zasięgiem.')
        m.update(stage='potion_roll',potion_target=target)
    elif action=='potion_cancel':m['stage']='battle'
    elif action=='roll' and stage=='potion_roll':
        from dnd_board_game.combat.session import use_turn_action
        from dnd_board_game.combat.healing import HealingSource, HealingSourceType, apply_healing_result
        item=read_json(root(s),'mechanics/items.json')[m['potion_id']]
        rolls=data.get('rolls')
        if not isinstance(rolls,list) or len(rolls)!=item['dice'] or any(type(r) is not int or not 1<=r<=item['sides'] for r in rolls):raise ValueError('Podaj wszystkie naturalne wyniki kości leczenia.')
        target=next((a for a in potion_targets(s) if str(a.id)==m['potion_target']),None)
        owned=next(((a,i) for a,i in available_potions(s) if i.id=='mission_'+m['potion_id']),None)
        if target is None or owned is None:raise ValueError('Cel lub mikstura nie są już dostępne.')
        consumed=use_turn_action(s.combat_state)
        if not consumed.accepted:raise ValueError(consumed.message)
        s.combat_state=consumed.state
        owner,potion=owned
        if owner is None:
            items=tuple(replace(i,quantity=i.quantity-1) if i.id==potion.id else i for i in s.state.party_loot.items if i.id!=potion.id or i.quantity>1)
            s.state=replace(s.state,party_loot=replace(s.state.party_loot,items=items))
        else:
            _set_actor(s,replace(owner,inventory=tuple(replace(i,quantity=i.quantity-1) for i in owner.inventory if i.id==potion.id and i.quantity>1) + tuple(i for i in owner.inventory if i.id!=potion.id)))
        target=next(a for a in s.combat_state.actors if str(a.id)==m['potion_target'])
        healed=apply_healing_result(target,HealingSource(potion.id,item['name'],HealingSourceType.ITEM,5),sum(rolls)+item['bonus'],condition_states=s.combat_state.condition_states)
        _set_actor(s,healed.actor_after)
        m['ledger'].append(dict(kind='item',id=m['potion_id'],name=label(s,'potion_used'),amount=-1))
        m['stage']='battle'
    elif action=='finish':
        from dnd_board_game.save import write_snapshot
        from dnd_board_game.application.campaign_rewards import complete_mission
        flags, actors, _ = complete_mission(s.state.flags, s.exploration.actors, MISSION_ID)
        s.state=replace(s.state, flags=flags)
        s.exploration=replace(s.exploration, actors=actors)
        write(s,m)
        write_snapshot(s.snapshot_path,s.create_snapshot())
        write_snapshot(s.save_dir/(MISSION_ID+'.completed.json'),s.create_snapshot())
        return dict(redirect='/')
    elif action=='battle':
        m.update(stage='battle',fatigue_applied=False);write(s,m)
        s.state=replace(s.state,flags=set_scene_flag(s.state.flags,'mission_battle_ready',True))
        s._refresh_pending_encounter()
        if s.pending_encounter:s.pending_encounter=replace(s.pending_encounter,precombat_stealth_completed=True)
        return s.start_encounter_setup()
    elif action=='accept':
        event=read_json(root(s),'mechanics/ethos.json')['accept_truce']
        s.state=replace(s.state,flags=party_ethos.apply_choice(s.state.flags,event['id'],event['direction']))
        m.update(stage='battle',outcome='accepted');write(s,m)
        s.pending_encounter_result=SceneResult(True,label(s,'accepted'),SceneConclusionType.VICTORY,Faction.ALLY)
        return s.resolve_active_combat()
    elif action=='refuse':
        event=read_json(root(s),'mechanics/ethos.json')['refuse_truce']
        s.state=replace(s.state,flags=party_ethos.apply_choice(s.state.flags,event['id'],event['direction']))
        m.update(stage='battle',outcome='refused')
    elif action=='back':m['stage']='explore'
    elif action=='dilemma':m['stage']='dilemma'
    elif action=='loaded':m['stage']='return'
    position=read_json(root(s),'flow.json')['point_positions'].get(action)
    if position:s.state=replace(s.state,party_position=replace(s.state.party_position,marker_position=Coordinate(*position)))
    s._record('mission_zero_action',dict(action=action,stage=m['stage'],debt=m['debt']))
    write(s,m);checkpoint(s,m)
    if m['stage']=='summary':
        from dnd_board_game.save import write_snapshot
        write_snapshot(s.snapshot_path,s.create_snapshot())
        write_snapshot(s.save_dir/(MISSION_ID+'.completed.json'),s.create_snapshot())
    s._sync_board_leds()
    return s.state_payload()


def scan_target(s: ExplorationUiSession) -> BoardScanTarget:
    from .exploration_app import BoardScanTarget
    p=payload(s)
    if p['rolling']:
        from .board_panel import browser_dice_target
        return browser_dice_target(s)
    slots=tuple(c['slot'] for c in p['choices']);marker=Coordinate(*p['marker']) if p['marker'] else None
    if p['reading']:
        slots=(*slots,26,27)
    feedback=LedFeedback((LedFrame((marker,),LedColor.PLAYER_START_ZONE,LedRole.MARKER),)) if marker else LedFeedback()
    if p.get('setup'):
        from .mission_setup import step_from_data
        from dnd_board_game.combat.setup import setup_led_feedback
        feedback=setup_led_feedback(step_from_data(p['setup']))
    positions=tuple(panel_position(i) for i in slots)
    if p['stage']=='departure':positions=(*positions,Coordinate(9,24))
    elif p['stage']=='guild_hub':
        points=tuple(Coordinate(*v) for v in p['guild_points'].values())
        positions=(*positions,*points)
        feedback=LedFeedback((*feedback.frames,*(LedFrame((Coordinate(*v),),
            LedColor.INTERACTIVE_OBJECT if k=='talk_nessa' else LedColor.PANEL_BACK,LedRole.MARKER)
            for k,v in p['guild_points'].items())))
    elif p['stage']=='explore':
        points=tuple(Coordinate(*v) for k,v in p['point_positions'].items() if k in ('leader','armory','quarters','store'))
        positions=(*positions,*points)
        feedback=LedFeedback((*feedback.frames,LedFrame(points,LedColor.INTERACTIVE_OBJECT,LedRole.MARKER)))
    return BoardScanTarget(positions=positions,feedback=panel_feedback(tuple(i for i in slots if i<26),control_slots=tuple(i for i in slots if i>=26),base=feedback),empty_message=label(s,'board_hint'))


def select_position(s: ExplorationUiSession, position: Coordinate) -> dict[str, object]:
    p=payload(s)
    if p['rolling']:
        from .board_panel import select_browser_die
        return select_browser_die(s,position)
    if p['reading'] and position in (panel_position(26),panel_position(27)):
        s.board_selection_revision += 1
        return dict(panel_event=dict(slot=29-position.row,context=f"mission-scroll:{p['revision']}"),
                    board_selection=s._board_selection_payload())
    if p['stage']=='departure' and position==Coordinate(9,24):return command(s,dict(action='exit',revision=p['revision']))
    if p['stage']=='guild_hub':
        action=next((k for k,v in p['guild_points'].items() if Coordinate(*v)==position),None)
        if action:return command(s,dict(action=action,revision=p['revision']))
    if p['stage']=='explore':
        action=next((k for k,v in p['point_positions'].items() if k in ('leader','armory','quarters','store') and Coordinate(*v)==position),None)
        if action:return command(s,dict(action=action,revision=p['revision']))
    c=next((c for c in p['choices'] if panel_position(c['slot'])==position),None)
    if c is None:raise ValueError(label(s,'board_hint'))
    return command(s,dict(action=c['action'],revision=p['revision'],**c['extra']))


def apply_pack_portraits(s: ExplorationUiSession, view: dict[str, Any]) -> None:
    """Use the local narrative copies without changing persisted actor identity."""
    actors = [*view.get('actors',()), *((view.get('combat') or {}).get('actors',()))]
    for actor in actors:
        path='assets/images/'+str(actor['id'])+'.png'
        if (root(s)/path).is_file():
            actor['portrait_url']=asset_url(root(s),path)
