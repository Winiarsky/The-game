"""Board-driven preparation adapter; inventory rules remain in party_equipment."""
from __future__ import annotations

from dataclasses import replace
from typing import Any, TYPE_CHECKING

from dnd_board_game.inventory import CurrencyWallet, InventoryItem, hands_required
from dnd_board_game.inventory.party_equipment import SLOTS, occupied, slots_for, equip, stow, sell
from .exploration_mana_board import choice

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession
    from dnd_board_game.actors import Actor

STAGES = ('equipment', 'equipment_item', 'equipment_sell')


def begin(m: dict[str, Any], home: str) -> None:
    m.pop('equipment_help_return', None)
    m.update(stage='equipment_intro' if home == 'departure' else 'equipment', equipment_home=home, equipment_hero=0, equipment_index=0,
             equipment_source='stash', equipment_notice='')


def actor(s: ExplorationUiSession, m: dict[str, Any]) -> Actor:
    return s.exploration.actors[m['equipment_hero']]


def items(s: ExplorationUiSession, m: dict[str, Any]) -> tuple[InventoryItem, ...]:
    return s.state.party_loot.items if m['equipment_source'] == 'stash' else actor(s,m).inventory


def selected(s: ExplorationUiSession, m: dict[str, Any]) -> InventoryItem | None:
    rows = items(s,m)
    return rows[min(m['equipment_index'],len(rows)-1)] if rows else None


def choices(s: ExplorationUiSession, m: dict[str, Any]) -> list[dict[str, Any]]:
    from . import mission_zero as mission
    result: list[dict[str, Any]] = []
    def add(slot: int, action: str, label: str, **extra: Any) -> None:
        result.append(choice(slot,action,label,**extra))
    if m['stage'] == 'equipment_intro':
        reviewing = bool(m.get('equipment_help_return'))
        add(28, 'equipment_continue', mission.label(s, 'equipment_help_close' if reviewing else 'equipment_begin'))
        add(29, 'equipment_intro_back', mission.label(s, 'equipment_help_close' if reviewing else 'equipment_intro_back'))
        return result
    item=selected(s,m)
    if m['stage'] == 'equipment_sell':
        add(28,'equipment_sell_confirm','Potwierdź sprzedaż')
        add(29,'equipment_list','Zachowaj przedmiot')
    elif m['stage'] == 'equipment_item':
        if item:
            for n, slot in enumerate(slots_for(item)):
                if hands_required(item)==2 and slot=='off_hand': continue
                label='Obie ręce' if hands_required(item)==2 and slot=='main_hand' else SLOTS[slot]
                add(5+n,'equipment_attach',label,gear_slot=slot)
        add(29,'equipment_list','Wróć do listy')
    else:
        if item:
            if m['equipment_source']=='stash':
                if slots_for(item): add(5,'equipment_slots','Wybierz slot')
                if item.value_cp > 0 and item.id not in ('mission_key','mission_documents'):
                    add(7,'equipment_sell','Sprzedaj za '+format((item.value_cp*item.quantity//2)/100,'.2f')+' sz')
                if item.id=='mission_ring' and not item.magic_effects:
                    from . import mission_zero as mission
                    from dnd_board_game.scenarios.mission_pack import read_json
                    price=read_json(mission.root(s),'mechanics/rewards.json')['identification_gp']
                    add(8,'equipment_identify',f'Identyfikacja — {price} sz')
            else: add(5,'equipment_stow','Odłóż do wspólnego zapasu')
        add(6,'equipment_source','Pokaż wyposażenie postaci' if m['equipment_source']=='stash' else 'Pokaż wspólny zapas')
        add(24,'equipment_help',mission.label(s,'equipment_help'))
        if len(items(s,m))>1:
            add(27,'equipment_previous','Poprzedni przedmiot');add(26,'equipment_next','Następny przedmiot')
        add(28,'equipment_accept','Gotowe — następna postać' if m['equipment_hero']+1<len(s.exploration.actors) else 'Gotowe — cała drużyna')
        add(29,'equipment_back','Poprzednia postać' if m['equipment_hero'] else 'Wróć do odprawy' if m['equipment_home']=='departure' else 'Wróć do Gildii')
    return result


def payload(s: ExplorationUiSession,m: dict[str, Any]) -> dict[str, Any] | None:
    if m['stage'] not in STAGES: return None
    from dnd_board_game.physical_cards.equipment_art import item_art
    a=actor(s,m); item=selected(s,m)
    from dnd_board_game.inventory import effective_armor_class
    from dnd_board_game.inventory.magic_items import effective_ability_score
    from .exploration_app import _actor_portrait_url
    from . import mission_zero as mission
    from dnd_board_game.scenarios.mission_pack import asset_url
    portrait_path = f'assets/images/{a.id}.png'
    portrait = asset_url(mission.root(s), portrait_path) if (mission.root(s) / portrait_path).is_file() else _actor_portrait_url(a)
    return dict(hero=a.name,hero_id=str(a.id),portrait_url=portrait,hero_index=m['equipment_hero']+1,hero_count=len(s.exploration.actors),
        source='Wspólny zapas' if m['equipment_source']=='stash' else 'Wyposażenie postaci',
        index=min(m['equipment_index']+1,len(items(s,m))),count=len(items(s,m)),
        item=dict(id=item.id,name=item.name,description=item.description,quantity=item.quantity,art=item_art(item),
                  usage='Zajmuje obie ręce; odłoży przedmioty z obu slotów.' if hands_required(item)==2 else '',
                  slots=', '.join(SLOTS[k] for k in occupied(item))) if item else None,
        loadout=[dict(slot=label,items=', '.join(i.name for i in a.inventory if key in occupied(i)) or '—') for key,label in SLOTS.items()],
        notice=m.get('equipment_notice',''),gold=s.exploration.actors[0].currency.total_cp/100,
        ac=effective_armor_class(a),strength=effective_ability_score(a,'strength'))


def handle(s: ExplorationUiSession,m: dict[str, Any], action: str,data: dict[str, Any]) -> bool:
    if not action.startswith('equipment_'): return False
    from . import mission_zero as mission
    from . import mission_zero_recovery as recovery
    if action=='equipment_open': begin(m,'guild_return');return True
    if action == 'equipment_help':
        m.update(equipment_help_return=m['stage'], stage='equipment_intro')
        return True
    if action in ('equipment_continue', 'equipment_intro_back'):
        previous = m.pop('equipment_help_return', None)
        m['stage'] = previous or ('equipment' if action == 'equipment_continue' else 'brief')
        return True
    a=actor(s,m); item=selected(s,m)
    if action=='equipment_source':
        m.update(equipment_source='hero' if m['equipment_source']=='stash' else 'stash',equipment_index=0)
    elif action in ('equipment_previous','equipment_next'):
        m['equipment_index']=(m['equipment_index']+(-1 if action=='equipment_previous' else 1))%len(items(s,m))
    elif action=='equipment_slots':m['stage']='equipment_item'
    elif action=='equipment_list':m['stage']='equipment'
    elif action=='equipment_attach':
        updated,stash=equip(a,s.state.party_loot,item.id,str(data.get('gear_slot','')))
        mission._set_actor(s,updated);s.state=replace(s.state,party_loot=stash)
        m.update(stage='equipment',equipment_notice=f'{a.name} bierze: {item.name}. Przekażcie kartę przedmiotu.',equipment_index=0)
    elif action=='equipment_stow':
        updated,stash=stow(a,s.state.party_loot,item.id)
        mission._set_actor(s,updated);s.state=replace(s.state,party_loot=stash)
        m.update(equipment_index=0,equipment_notice=f'{item.name} wraca do wspólnego zapasu razem z kartą.')
    elif action=='equipment_identify':
        recovery.identify_paid(s,m)
        m.update(equipment_notice='Rozpoznano Pierścień Siły. Wymieńcie jego kartę na zidentyfikowaną.')
    elif action=='equipment_sell': m['stage']='equipment_sell'
    elif action=='equipment_sell_confirm':
        stash,price=sell(s.state.party_loot,item.id)
        owner=s.exploration.actors[0]
        mission._set_actor(s,replace(owner,currency=owner.currency.add(CurrencyWallet(cp=price))))
        s.state=replace(s.state,party_loot=stash)
        m['ledger'].extend((dict(kind='item',id=item.id,name=item.name,amount=-item.quantity),dict(kind='money',id='sale:'+item.id,name='Sprzedaż: '+item.name,amount=price/100)))
        m.update(stage='equipment',equipment_index=0,equipment_notice=f'Sprzedano {item.name}. Odłóżcie kartę poza zapas.')
    elif action=='equipment_accept':
        m['equipment_hero']+=1;m['equipment_index']=0
        if m['equipment_hero']>=len(s.exploration.actors): m.update(stage=m['equipment_home'],equipment_ready=True)
    elif action=='equipment_back':
        if m['equipment_hero']:m['equipment_hero']-=1;m['equipment_index']=0
        else:m['stage']='brief' if m['equipment_home']=='departure' else m['equipment_home']
    else:return False
    return True


def locked(s: ExplorationUiSession) -> bool:
    from . import mission_zero as mission
    from dnd_board_game.combat.runes import uses_runes
    if s.combat_state is not None and any(uses_runes(actor) for actor in s.combat_state.actors):
        return True
    return mission.enabled(s) and bool(mission.read(s).get('equipment_locked'))


def require_unlocked(s: ExplorationUiSession) -> None:
    if locked(s): raise ValueError('Wyposażenie ustalono przed wyprawą. Zmieńcie je po powrocie do Gildii.')
