"""Pure loadout transactions between one hero and the shared expedition stash."""
from __future__ import annotations

from dataclasses import replace

from dnd_board_game.actors import Actor
from . import InventoryItem, LootBundle, HandSlot, hands_required, plan_hand_equip

SLOTS = {'armor': 'Pancerz', 'head': 'Głowa', 'main_hand': 'Pierwsza ręka',
         'off_hand': 'Druga ręka', 'neck': 'Szyja', 'focus': 'Przybory magiczne / instrument', 'ring': 'Pierścień', 'pack': 'Plecak'}


def worn_slot(item: InventoryItem) -> str:
    explicit = next((p.split(':', 1)[1] for p in item.properties if p.startswith('equipment_slot:')), '')
    if explicit: return explicit
    if item.kind == 'armor': return 'armor'
    if item.source_ref == 'holy_symbol_amulet' or item.id == 'mission_medallion': return 'neck'
    if item.id == 'mission_ring': return 'ring'
    if item.kind == 'helmet': return 'head'
    if item.spellcasting_focus_kind is not None or item.kind == 'instrument': return 'focus'
    return 'pack'


def slots_for(item: InventoryItem) -> tuple[str, ...]:
    if not item.available or not item.portable: return ()
    if item.id == 'mission_ring' and not item.magic_effects: return ()
    if item.id in ('mission_documents', 'mission_key'): return ()
    if hands_required(item): return ('main_hand', 'off_hand', 'pack')
    slot = worn_slot(item)
    return (slot, 'pack') if slot != 'pack' else ('pack',)


def occupied(item: InventoryItem) -> tuple[str, ...]:
    if item.equipped and item.held_in: return tuple(str(h) for h in item.held_in)
    return (worn_slot(item),) if item.equipped else ('pack',)


def deposit(stash: LootBundle, item: InventoryItem) -> LootBundle:
    """Preserve physical instance identity; never silently merge unique equipment."""
    ids = {i.id for i in stash.items}
    new_id = item.id
    n = 2
    while new_id in ids:
        new_id = f'{item.id}:{n}'; n += 1
    return replace(stash, items=(*stash.items, replace(item, id=new_id, source_ref=item.source_ref or item.id,
                                                     equipped=False, held_in=())))


def stow(actor: Actor, stash: LootBundle, item_id: str) -> tuple[Actor, LootBundle]:
    item = next((i for i in actor.inventory if i.id == item_id), None)
    if item is None: raise ValueError('Przedmiot nie należy już do tej postaci.')
    return replace(actor, inventory=tuple(i for i in actor.inventory if i.id != item_id)), deposit(stash, item)


def equip(actor: Actor, stash: LootBundle, item_id: str, slot: str) -> tuple[Actor, LootBundle]:
    item = next((i for i in stash.items if i.id == item_id), None)
    if item is None or slot not in slots_for(item): raise ValueError('Przedmiot nie pasuje do wybranego slotu.')
    if slot == 'armor' and not actor.proficiencies.is_armor_proficient(item.armor_proficiency or item.armor_category.value):
        raise ValueError('Ta postać nie może używać tego pancerza.')
    if item.kind == 'shield' and slot != 'pack' and not actor.proficiencies.is_armor_proficient('shield'):
        raise ValueError('Ta postać nie może używać tarczy.')
    new_id = item.id
    n = 2
    while any(i.id == new_id for i in actor.inventory):
        new_id = f'{item.id}:{n}'; n += 1
    incoming = replace(item, id=new_id, source_ref=item.source_ref or item.id, equipped=slot != 'pack', held_in=())
    stash = replace(stash, items=tuple(i for i in stash.items if i.id != item_id))
    if slot in ('main_hand', 'off_hand'):
        plan = plan_hand_equip((*actor.inventory, incoming), incoming.id, preferred_slot=HandSlot(slot))
        displaced = tuple(i for i in actor.inventory if i.id in plan.replaced_item_ids)
        inventory = tuple(i for i in plan.inventory if i.id not in plan.replaced_item_ids)
    else:
        displaced = tuple(i for i in actor.inventory if slot != 'pack' and i.equipped and worn_slot(i) == slot)
        displaced_ids = {i.id for i in displaced}
        inventory = (*tuple(i for i in actor.inventory if i.id not in displaced_ids), incoming)
    for old in displaced: stash = deposit(stash, old)
    updated=replace(actor, inventory=inventory)
    from .economy import carried_weight_lb, carrying_capacity_lb
    if carried_weight_lb(updated)>carrying_capacity_lb(updated):
        raise ValueError('Przedmiot przekroczyłby udźwig postaci.')
    return updated, stash


def sell(stash: LootBundle, item_id: str) -> tuple[LootBundle, int]:
    item = next((i for i in stash.items if i.id == item_id), None)
    if item is None or item.value_cp <= 0 or item.id in ('mission_documents', 'mission_key'):
        raise ValueError('Tego przedmiotu nie można sprzedać.')
    price = item.value_cp * item.quantity // 2
    if price <= 0: raise ValueError('Brak oferty kupna.')
    return replace(stash, items=tuple(i for i in stash.items if i.id != item_id)), price
