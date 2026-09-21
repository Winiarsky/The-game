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


def test_find_identify_and_ring_equip_only_at_base(tmp_path):
    s=party(tmp_path);stage(s,'explore',equipment_locked=True)
    send(s,'quarters');send(s,'search',room='quarters');finish(s,'success')
    assert 'identify_nimra' in {c['action'] for c in mission.payload(s)['choices']}
    assert any(i.id=='mission_ring' for i in s.state.party_loot.items)
    send(s,'identify_nimra');send(s,'roll',roll=20)
    assert mission.read(s)['ring_identified']
    with pytest.raises(ValueError):send(s,'equip_ring',target='garran')
    with pytest.raises(ValueError):send(s,'equipment_open')
    stage(s,'guild_return',equipment_locked=False);send(s,'equipment_open');send(s,'equipment_slots');send(s,'equipment_attach',gear_slot='ring')
    assert effective_ability_score(s.exploration.actors[0],'strength')==19
    assert not s.state.party_loot.items
    s.save_snapshot();s.load_snapshot()
    assert effective_ability_score(s.exploration.actors[0],'strength')==19
    assert mission.read(s)['stage']=='equipment'
    send(s,'equipment_source');data=mission.read(s)
    data['equipment_index']=next(j for j,i in enumerate(s.exploration.actors[0].inventory) if i.id=='mission_ring');mission.write(s,data)
    send(s,'equipment_stow')
    assert effective_ability_score(s.exploration.actors[0],'strength')==18
    assert len(s.state.party_loot.items)==1


def test_paid_identification_is_atomic_and_one_shot(tmp_path):
    s=party(tmp_path);data=mission.read(s);mission.grant(s,data,'ring');mission.write(s,data)
    stage(s,'guild_return');send(s,'ring')
    first=s.exploration.actors[0];mission._set_actor(s,replace(first,currency=CurrencyWallet()))
    with pytest.raises(ValueError,match='złota'):send(s,'identify_guild')
    assert not mission.read(s)['ring_identified'] and not s.state.party_loot.items[0].magic_effects
    mission._set_actor(s,replace(first,currency=CurrencyWallet(gp=5)))
    send(s,'identify_guild')
    assert s.exploration.actors[0].currency.total_cp==0
    with pytest.raises(ValueError):send(s,'identify_guild')
    assert len([e for e in mission.read(s)['ledger'] if e['id']=='identification'])==1


def test_preparation_sequence_board_paging_and_lock(tmp_path):
    from dnd_board_game.hardware.board_panel import panel_position
    s=party(tmp_path);stage(s,'brief');send(s,'depart')
    assert mission.read(s)['stage']=='equipment_intro'
    assert mission.payload(s)['reading'] and mission.payload(s)['equipment'] is None
    mission.select_position(s,panel_position(28))
    assert mission.read(s)['stage']=='equipment'
    send(s,'equipment_source')
    original=mission.payload(s)['equipment']['item']['id']
    mission.select_position(s,panel_position(27))
    assert mission.payload(s)['equipment']['item']['id']!=original
    mission.select_position(s,panel_position(26))
    assert mission.payload(s)['equipment']['item']['id']==original
    for _ in s.exploration.actors:mission.select_position(s,panel_position(28))
    assert mission.read(s)['stage']=='departure'
    send(s,'exit');assert preparation.locked(s)
    with pytest.raises(ValueError):send(s,'equipment_open')
    with pytest.raises(ValueError):s.change_actor_armor(actor_id='garran',armor_id='chain_mail',equip=False)
    with pytest.raises(ValueError):s._change_combat_weapon('crossbow')


def test_sale_confirmation_and_quest_item_protection(tmp_path):
    s=party(tmp_path);data=mission.read(s)
    mission.grant(s,data,'medallion');mission.grant(s,data,'documents');mission.write(s,data)
    stage(s,'guild_return');send(s,'equipment_open')
    before=s.exploration.actors[0].currency.total_cp
    send(s,'equipment_sell');send(s,'equipment_list')
    assert len(s.state.party_loot.items)==2
    send(s,'equipment_sell');send(s,'equipment_sell_confirm')
    assert s.exploration.actors[0].currency.total_cp==before+150
    assert [i.id for i in s.state.party_loot.items]==['mission_documents']
    with pytest.raises(ValueError):send(s,'equipment_sell_confirm')
    with pytest.raises(ValueError):sell(s.state.party_loot,'mission_documents')


def test_grants_shared_potions_and_documents(tmp_path):
    s=party(tmp_path);data=mission.read(s)
    for key in ('potion','medallion','documents'):mission.grant(s,data,key);mission.grant(s,data,key)
    mission.write(s,data)
    assert len(s.state.party_loot.items)==3
    assert mission.available_potions(s)[0][0] is None
    assert not any(i.id.startswith('mission_') for a in s.exploration.actors for i in a.inventory)
    s.save_snapshot();s.load_snapshot();assert len(s.state.party_loot.items)==3


def test_spell_focus_keeps_working_after_shared_transfer():
    from dnd_board_game.rules.spellcasting import _usable_focus
    a=training_hero('nimra');a,stash=stow(a,LootBundle('party','Zapas'),'component_pouch')
    assert _usable_focus(a.inventory,['component_pouch']) is None
    a,stash=equip(a,stash,'component_pouch','focus')
    assert _usable_focus(a.inventory,['component_pouch']).id=='component_pouch'
    assert occupied(next(i for i in a.inventory if i.id=='component_pouch'))==('focus',)


def test_large_stash_paging_and_stale_command_are_safe(tmp_path):
    s=party(tmp_path);s.state=replace(s.state,party_loot=replace(s.state.party_loot,items=tuple(InventoryItem(f'loot_{i}',f'Znalezisko {i}','gear',equipped=False) for i in range(80))))
    stage(s,'guild_return');send(s,'equipment_open')
    send(s,'equipment_previous')
    assert mission.payload(s)['equipment']['item']['id']=='loot_79'
    send(s,'equipment_slots');revision=mission.read(s)['revision']
    send(s,'equipment_attach',gear_slot='pack')
    with pytest.raises(ValueError):mission.command(s,dict(action='equipment_attach',gear_slot='pack',revision=revision))
    assert len(s.state.party_loot.items)==79
    assert len([i for a in s.exploration.actors for i in a.inventory if i.id=='loot_79'])==1


def test_preparation_intro_save_back_and_help_preserve_selection(tmp_path):
    from dnd_board_game.hardware.board_panel import panel_position
    s=party(tmp_path);stage(s,'brief');send(s,'depart')
    inventory=tuple(a.inventory for a in s.exploration.actors)
    stash=s.state.party_loot
    s.save_snapshot();s.load_snapshot()
    assert mission.payload(s)['stage']=='equipment_intro'
    assert {panel_position(i) for i in (26,27,28,29)} <= set(mission.scan_target(s).positions)
    assert mission.select_position(s,panel_position(27))['panel_event']['slot']==27
    with pytest.raises(ValueError):send(s,'equipment_accept')
    mission.select_position(s,panel_position(29))
    assert mission.read(s)['stage']=='brief'
    send(s,'depart');send(s,'equipment_continue')
    send(s,'equipment_accept');send(s,'equipment_source');send(s,'equipment_next')
    before=mission.payload(s)['equipment']
    mission.select_position(s,panel_position(25))
    s.save_snapshot();s.load_snapshot()
    mission.select_position(s,panel_position(29))
    assert mission.payload(s)['equipment']==before
    mission.select_position(s,panel_position(25))
    mission.select_position(s,panel_position(28))
    assert mission.payload(s)['equipment']==before
    assert tuple(a.inventory for a in s.exploration.actors)==inventory
    assert s.state.party_loot==stash


def test_preparation_portrait_tracks_hero_and_previous(tmp_path):
    s=party(tmp_path);stage(s,'brief');send(s,'depart');send(s,'equipment_continue')
    for hero in s.exploration.actors:
        view=mission.payload(s)['equipment']
        assert view['hero_id']==str(hero.id) and view['hero']==hero.name
        assert f'/{hero.id}.png?' in view['portrait_url']
        send(s,'equipment_accept')
    stage(s,'guild_return');send(s,'equipment_open')
    send(s,'equipment_accept');send(s,'equipment_back')
    assert mission.payload(s)['equipment']['hero_id']=='garran'
