"""Atomic equipment swaps, shared discoveries and the expedition preparation gate."""
from dataclasses import replace

import pytest

from dnd_board_game.inventory import InventoryItem, LootBundle, CurrencyWallet, effective_armor_class
from dnd_board_game.inventory.party_equipment import equip, stow, sell, occupied
from dnd_board_game.inventory.magic_items import effective_ability_score
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.ui import mission_zero as mission, mission_zero_recovery as recovery
from dnd_board_game.ui import party_preparation as preparation
from tests.unit.test_mission_recovery import party, finish
from tests.unit.test_mission_zero import stage, send


def test_two_hands_displace_both_without_losing_or_duplicating_items():
    g=training_hero('garran'); b=training_hero('brakka')
    axe=next(i for i in b.inventory if i.id=='greataxe')
    stash=LootBundle('party','Zapas',(replace(axe,equipped=False,held_in=()),))
    updated,stash=equip(g,stash,'greataxe','main_hand')
    assert {i.id for i in stash.items}=={'longsword','shield'}
    assert next(i for i in updated.inventory if i.id=='greataxe').held_in==('main_hand','off_hand')
    assert effective_armor_class(updated)==effective_armor_class(g)-2
    updated,stash=equip(updated,stash,'shield','off_hand')
    assert {i.id for i in stash.items}=={'longsword','greataxe'}
    assert not any(i.id=='greataxe' for i in updated.inventory)
    assert effective_armor_class(updated)==effective_armor_class(g)


def test_invalid_slot_and_armor_do_not_change_inventories():
    nimra=training_hero('nimra');armor=next(i for i in training_hero('garran').inventory if i.id=='chain_mail')
    stash=LootBundle('party','Zapas',(replace(armor,equipped=False),))
    with pytest.raises(ValueError):equip(nimra,stash,armor.id,'head')
    with pytest.raises(ValueError):equip(nimra,stash,armor.id,'armor')
    assert len(stash.items)==1 and not stash.items[0].equipped


def test_duplicate_ids_preserve_sources_and_item_count():
    a=training_hero('mira');b=training_hero('garran');stash=LootBundle('party','Zapas')
    a,stash=stow(a,stash,'pouch');b,stash=stow(b,stash,'pouch')
    assert len({i.id for i in stash.items})==2
    a,stash=equip(a,stash,'pouch:2','pack')
    assert next(i for i in a.inventory if i.id=='pouch:2').source_ref=='pouch'
    assert len(stash.items)==1


def choose_item(s, slot: str, item_id: str | None) -> None:
    send(s, 'equipment_slot', gear_slot=slot)
    for _ in range(200):
        item = mission.payload(s)['equipment']['item']
        if (item['id'] if item else None) == item_id:
            send(s, 'equipment_confirm')
            return
        send(s, 'equipment_next')
    raise AssertionError(f'Missing choice {item_id}')


def test_find_identify_and_ring_equip_only_at_base(tmp_path):
    s=party(tmp_path);stage(s,'explore',equipment_locked=True)
    send(s,'quarters');send(s,'search',room='quarters');finish(s,'success')
    send(s,'identify_nimra');send(s,'roll',roll=20)
    from dnd_board_game.inventory.party_equipment import slots_for
    assert mission.read(s)['ring_identified']
    assert not slots_for(s.state.party_loot.items[0])
    with pytest.raises(ValueError):send(s,'equipment_open')
    stage(s,'guild_return',equipment_locked=False);send(s,'equipment_open')
    choose_item(s, 'ring', 'mission_ring')
    assert effective_ability_score(s.exploration.actors[0],'strength')==19
    assert not s.state.party_loot.items
    s.save_snapshot();s.load_snapshot()
    assert effective_ability_score(s.exploration.actors[0],'strength')==19
    assert mission.read(s)['stage']=='equipment'
    choose_item(s, 'ring', None)
    assert effective_ability_score(s.exploration.actors[0],'strength')==18
    assert len(s.state.party_loot.items)==1


def test_paid_identification_is_atomic_and_one_shot(tmp_path):
    s=party(tmp_path);data=mission.read(s);mission.grant(s,data,'ring');mission.write(s,data)
    stage(s,'guild_return');send(s,'equipment_open');send(s,'equipment_stash');send(s,'equipment_group',group='found')
    first=s.exploration.actors[0];mission._set_actor(s,replace(first,currency=CurrencyWallet()))
    with pytest.raises(ValueError,match='złota'):send(s,'equipment_identify')
    assert not mission.read(s)['ring_identified'] and not s.state.party_loot.items[0].magic_effects
    mission._set_actor(s,replace(first,currency=CurrencyWallet(gp=5)))
    send(s,'equipment_identify')
    assert s.exploration.actors[0].currency.total_cp==0
    assert mission.payload(s)['equipment']['groups']==dict(available=1,found=0,quest=0)
    with pytest.raises(ValueError):send(s,'equipment_identify')
    assert len([e for e in mission.read(s)['ledger'] if e['id']=='identification'])==1


@pytest.mark.parametrize('hero', ('garran','brakka','mira','dagna','lorian','nimra','erynd'))
def test_starter_sheet_is_filled_and_every_place_has_its_own_rune(tmp_path, hero):
    from dnd_board_game.inventory.party_equipment import pockets
    s=party(tmp_path, heroes=(hero,));before=s.exploration.actors[0].inventory
    data=mission.read(s);mission.grant(s,data,'key');mission.write(s,data)
    stage(s,'brief');send(s,'depart')
    view=mission.payload(s)['equipment']
    assert mission.read(s)['stage']=='equipment'
    assert s.exploration.actors[0].inventory==before
    assert len({row['slot'] for row in view['loadout']})==15
    assert view['groups']==dict(available=0,found=0,quest=1)
    visible={row['item']['id'] for row in view['loadout'] if row['item']}
    assert visible=={i.id for i in before}
    assert 'mission_key' not in visible
    assert sum(item is not None for item in pockets(s.exploration.actors[0]))==sum(occupied(i)==('pack',) for i in before)
    two_handed=hero in ('brakka','erynd')
    assert next(row for row in view['loadout'] if row['id']=='off_hand')['linked']==two_handed


def test_preparation_sequence_board_paging_cancel_and_lock(tmp_path):
    from dnd_board_game.hardware.board_panel import panel_position
    from tests.unit.test_initiative_panel import Board
    s=party(tmp_path);stage(s,'brief');send(s,'depart')
    board=Board();s.attach_board_connection(board,backend='simulator');s._sync_board_leds()
    assert set(board.leds)=={panel_position(c['slot']).as_tuple() for c in mission.payload(s)['choices']}
    assert panel_position(26).as_tuple() not in board.leds
    before=tuple(a.inventory for a in s.exploration.actors),s.state.party_loot
    mission.select_position(s,panel_position(17))
    assert mission.payload(s)['equipment']['picker']['slot']=='main_hand'
    original=mission.payload(s)['equipment']['item']['id']
    mission.select_position(s,panel_position(26))
    assert mission.payload(s)['equipment']['item']['id']!=original
    mission.select_position(s,panel_position(27))
    assert mission.payload(s)['equipment']['item']['id']==original
    mission.select_position(s,panel_position(29))
    assert (tuple(a.inventory for a in s.exploration.actors),s.state.party_loot)==before
    for _ in s.exploration.actors:mission.select_position(s,panel_position(28))
    assert mission.read(s)['stage']=='departure'
    send(s,'exit');assert preparation.locked(s)
    with pytest.raises(ValueError):send(s,'equipment_open')
    with pytest.raises(ValueError):s.change_actor_armor(actor_id='garran',armor_id='chain_mail',equip=False)
    with pytest.raises(ValueError):s._change_combat_weapon('crossbow')


def test_sale_confirmation_and_quest_item_protection(tmp_path):
    s=party(tmp_path);data=mission.read(s)
    mission.grant(s,data,'medallion');mission.grant(s,data,'documents');mission.write(s,data)
    stage(s,'guild_return');send(s,'equipment_open');send(s,'equipment_stash')
    send(s,'equipment_group',group='found');send(s,'equipment_identify')
    send(s,'equipment_group',group='available')
    before=s.exploration.actors[0].currency.total_cp
    send(s,'equipment_sell');send(s,'equipment_stash_back')
    assert len(s.state.party_loot.items)==2
    send(s,'equipment_sell');send(s,'equipment_sell_confirm')
    assert s.exploration.actors[0].currency.total_cp==before+150
    assert [i.id for i in s.state.party_loot.items]==['mission_documents']
    with pytest.raises(ValueError):send(s,'equipment_sell_confirm')
    with pytest.raises(ValueError):sell(s.state.party_loot,'mission_documents')


def test_grants_shared_supplies_and_seals_field_consumables(tmp_path):
    from dnd_board_game.inventory.party_equipment import ready_for_use
    s=party(tmp_path);data=mission.read(s)
    for key in ('potion','medallion','documents'):mission.grant(s,data,key);mission.grant(s,data,key)
    mission.write(s,data)
    assert len(s.state.party_loot.items)==3
    assert mission.available_potions(s)[0][0] is None
    stage(s,'explore',equipment_locked=True)
    data=mission.read(s);mission.grant(s,data,'weak_potion');mission.write(s,data)
    found=next(i for i in s.state.party_loot.items if i.id=='mission_weak_potion')
    assert not ready_for_use(found)
    assert [i.id for _,i in mission.available_potions(s)]==['mission_potion']
    assert not any(i.id.startswith('mission_') for a in s.exploration.actors for i in a.inventory)
    s.save_snapshot();s.load_snapshot()
    assert not ready_for_use(next(i for i in s.state.party_loot.items if i.id==found.id))
    stage(s,'guild_return',equipment_locked=False);send(s,'equipment_open');send(s,'equipment_stash');send(s,'equipment_group',group='found')
    while mission.payload(s)['equipment']['item']['id']!=found.id:send(s,'equipment_next')
    send(s,'equipment_identify')
    assert ready_for_use(next(i for i in s.state.party_loot.items if i.id==found.id))


def test_spell_focus_keeps_working_after_shared_transfer():
    from dnd_board_game.rules.spellcasting import _usable_focus
    a=training_hero('nimra');a,stash=stow(a,LootBundle('party','Zapas'),'component_pouch')
    assert _usable_focus(a.inventory,['component_pouch']) is None
    a,stash=equip(a,stash,'component_pouch','focus')
    assert _usable_focus(a.inventory,['component_pouch']).id=='component_pouch'
    assert occupied(next(i for i in a.inventory if i.id=='component_pouch'))==('focus',)


def test_large_stash_filters_slot_and_stale_command_is_safe(tmp_path):
    s=party(tmp_path);s.state=replace(s.state,party_loot=replace(s.state.party_loot,items=tuple(InventoryItem(f'loot_{i}',f'Znalezisko {i}','gear',equipped=False) for i in range(80))))
    stage(s,'guild_return');send(s,'equipment_open');send(s,'equipment_slot',gear_slot='armor')
    assert not any(o.item and o.item.id.startswith('loot_') for o in preparation.options(s,mission.read(s)))
    send(s,'equipment_list');send(s,'equipment_slot',gear_slot='pack_8')
    send(s,'equipment_previous')  # Empty place is the last option.
    send(s,'equipment_previous')  # Hero's own gear is offered after the stash.
    while mission.payload(s)['equipment']['item']['id']!='loot_79':send(s,'equipment_previous')
    revision=mission.read(s)['revision'];send(s,'equipment_confirm')
    with pytest.raises(ValueError):mission.command(s,dict(action='equipment_confirm',revision=revision))
    assert len(s.state.party_loot.items)==79
    assert len([i for a in s.exploration.actors for i in a.inventory if i.id=='loot_79'])==1


def test_help_save_and_back_preserve_hero_and_equipment(tmp_path):
    from dnd_board_game.hardware.board_panel import panel_position
    s=party(tmp_path);stage(s,'brief');send(s,'depart');send(s,'equipment_accept')
    inventory=tuple(a.inventory for a in s.exploration.actors);stash=s.state.party_loot
    before=mission.payload(s)['equipment']
    mission.select_position(s,panel_position(25))
    assert mission.read(s)['stage']=='equipment_intro'
    s.save_snapshot();s.load_snapshot()
    mission.select_position(s,panel_position(29))
    assert mission.payload(s)['equipment']==before
    mission.select_position(s,panel_position(25));mission.select_position(s,panel_position(28))
    assert mission.payload(s)['equipment']==before
    assert tuple(a.inventory for a in s.exploration.actors)==inventory and s.state.party_loot==stash
    send(s,'equipment_back');assert mission.payload(s)['equipment']['hero_id']=='garran'


def test_pocket_assignment_persists_and_has_no_artificial_capacity_limit(tmp_path):
    from dnd_board_game.inventory.party_equipment import change_slot,pockets
    s=party(tmp_path);a=s.exploration.actors[0];stash=LootBundle('party','Zapas',tuple(InventoryItem(f'extra{i}',f'Rzecz {i}','gear',equipped=False) for i in range(10)))
    for n in range(10):a,stash=change_slot(a,stash,f'pack_{n+5}',f'extra{n}')
    assert len(pockets(a))==16
    first=pockets(a)[0]
    a,stash=change_slot(a,stash,'pack_2',None)
    assert pockets(a)[0]==first and pockets(a)[1] is None
    assert pockets(a)[13].id=='extra9'
    mission._set_actor(s,a);s.state=replace(s.state,party_loot=stash)
    stage(s,'guild_return');send(s,'equipment_open');send(s,'equipment_pack_next')
    assert mission.payload(s)['equipment']['loadout'][-1]['id']=='pack_16'
    s.save_snapshot();s.load_snapshot()
    assert pockets(s.exploration.actors[0])[13].id=='extra9'
    assert pockets(s.exploration.actors[0])[1] is None


def test_own_item_can_move_between_pack_and_hand_atomically():
    from dnd_board_game.inventory.party_equipment import change_slot,pockets
    a=training_hero('garran');stash=LootBundle('party','Zapas')
    before=len(a.inventory)
    a,stash=change_slot(a,stash,'pack_1','longsword',source='hero')
    assert not any('main_hand' in occupied(i) for i in a.inventory)
    assert pockets(a)[0].id=='longsword'
    assert len(a.inventory)+len(stash.items)==before
    a,stash=change_slot(a,stash,'main_hand','longsword',source='hero')
    assert next(i for i in a.inventory if i.id=='longsword').held_in==('main_hand',)
    assert pockets(a)[0] is None
    assert len(a.inventory)+len(stash.items)==before


def test_old_preparation_snapshot_opens_new_sheet_without_resetting_loadout(tmp_path):
    s=party(tmp_path);stage(s,'brief');send(s,'depart')
    data=mission.read(s);data.pop('equipment_ui_version');data.update(stage='equipment_item',equipment_source='stash',equipment_index=65)
    mission.write(s,data);before=s.exploration.actors
    s.save_snapshot();s.load_snapshot()
    assert mission.read(s)['stage']=='equipment'
    assert mission.payload(s)['equipment']['picker'] is None
    assert s.exploration.actors==before
