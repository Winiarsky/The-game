"""Pure loadout transactions between one hero and the shared expedition stash."""
from __future__ import annotations

from dataclasses import replace

from dnd_board_game.actors import Actor
from . import InventoryItem, LootBundle, HandSlot, hands_required, plan_hand_equip

SLOTS = {'armor': 'Pancerz', 'head': 'Głowa', 'main_hand': 'Pierwsza ręka',
         'off_hand': 'Druga ręka', 'neck': 'Szyja', 'focus': 'Przybory magiczne / instrument', 'ring': 'Pierścień', 'pack': 'Plecak'}

UNIDENTIFIED = 'party_loot:unidentified'
SEALED = 'party_loot:expedition'
POCKET_PREFIX = 'pack_slot:'
POCKETS_PER_PAGE = 8


def quest_item(item: InventoryItem) -> bool:
    return (item.source_ref or item.id).split(':')[0] in ('mission_key', 'mission_documents') or 'quest_item' in item.properties


def needs_identification(item: InventoryItem) -> bool:
    return UNIDENTIFIED in item.properties or ((item.source_ref or item.id) == 'mission_ring' and not item.magic_effects)


def ready_for_use(item: InventoryItem) -> bool:
    return item.available and not needs_identification(item) and SEALED not in item.properties


def found_item(item: InventoryItem) -> InventoryItem:
    """Seal a discovery until it is checked at base; quest objects stay shared."""
    if quest_item(item):
        return item
    return replace(item, equipped=False, held_in=(), properties=tuple(dict.fromkeys((*item.properties, UNIDENTIFIED, SEALED))))


def identify_item(item: InventoryItem, *, at_base: bool) -> InventoryItem:
    if (item.source_ref or item.id) == 'mission_ring' and not item.magic_effects:
        raise ValueError('Najpierw rozpoznaj właściwości pierścienia.')
    removed = (UNIDENTIFIED, SEALED) if at_base else (UNIDENTIFIED,)
    return replace(item, properties=tuple(p for p in item.properties if p not in removed))


def release_identified(stash: LootBundle) -> LootBundle:
    return replace(stash, items=tuple(identify_item(i, at_base=True) if not needs_identification(i) else i for i in stash.items))


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
    if not ready_for_use(item) or not item.portable or quest_item(item): return ()
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
                                                     equipped=False, held_in=(),
                                                     properties=tuple(p for p in item.properties if not p.startswith(POCKET_PREFIX)))))


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
    if item is None or item.value_cp <= 0 or quest_item(item) or not ready_for_use(item):
        raise ValueError('Tego przedmiotu nie można sprzedać.')
    price = item.value_cp * item.quantity // 2
    if price <= 0: raise ValueError('Brak oferty kupna.')
    return replace(stash, items=tuple(i for i in stash.items if i.id != item_id)), price


def pockets(actor: Actor) -> tuple[InventoryItem | None, ...]:
    """Stable numbered places, with more pages rather than an inventory limit."""
    placed: dict[int, InventoryItem] = {}
    remaining: list[InventoryItem] = []
    for item in actor.inventory:
        if occupied(item) != ('pack',):
            continue
        number = next((int(p[len(POCKET_PREFIX):]) for p in item.properties
                       if p.startswith(POCKET_PREFIX) and p[len(POCKET_PREFIX):].isdigit()), 0)
        if 0 < number <= 1000 and number not in placed:
            placed[number] = item
        else:
            remaining.append(item)
    for item in remaining:
        number = next(n for n in range(1, len(placed) + 2) if n not in placed)
        placed[number] = item
    count = max(placed, default=0)
    # Keep an empty place available even when every existing place is filled.
    size = ((count // POCKETS_PER_PAGE) + 1) * POCKETS_PER_PAGE
    return tuple(placed.get(n) for n in range(1, size + 1))


def slot_items(actor: Actor, slot: str) -> tuple[InventoryItem, ...]:
    if slot.startswith('pack_'):
        try:
            number = int(slot[5:])
        except ValueError:
            raise ValueError('Nieznane miejsce w plecaku.') from None
        rows = pockets(actor)
        if not 1 <= number <= len(rows):
            raise ValueError('Nieznane miejsce w plecaku.')
        return (rows[number - 1],) if rows[number - 1] else ()
    if slot not in SLOTS or slot == 'pack':
        raise ValueError('Nieznane miejsce wyposażenia.')
    return tuple(i for i in actor.inventory if slot in occupied(i))


def change_slot(actor: Actor, stash: LootBundle, slot: str, item_id: str | None, *, source: str = 'stash') -> tuple[Actor, LootBundle]:
    """Atomically fill/empty one place, including moves from the hero's own gear."""
    current = slot_items(actor, slot)
    if source not in ('hero', 'stash'):
        raise ValueError('Nieznane źródło przedmiotu.')
    if item_id is not None and source == 'hero' and any(i.id == item_id for i in current):
        return actor, stash
    numbers = {item.id: n for n, item in enumerate(pockets(actor), 1) if item}
    actor = replace(actor, inventory=tuple(replace(i, properties=(
        *tuple(p for p in i.properties if not p.startswith(POCKET_PREFIX)), f'{POCKET_PREFIX}{numbers[i.id]}'))
        if i.id in numbers else i for i in actor.inventory))
    if item_id is None:
        for old in current:
            actor, stash = stow(actor, stash, old.id)
        return actor, stash
    if source == 'hero':
        previous_ids = {i.id for i in stash.items}
        actor, stash = stow(actor, stash, item_id)
        item_id = next(i.id for i in stash.items if i.id not in previous_ids)
    if slot.startswith('pack_'):
        for old in current:
            actor, stash = stow(actor, stash, old.id)
    before_ids = {i.id for i in actor.inventory}
    actor, stash = equip(actor, stash, item_id, 'pack' if slot.startswith('pack_') else slot)
    if slot.startswith('pack_'):
        actor = replace(actor, inventory=tuple(replace(i, properties=(
            *tuple(p for p in i.properties if not p.startswith(POCKET_PREFIX)), f'{POCKET_PREFIX}{slot[5:]}'))
            if i.id not in before_ids else i for i in actor.inventory))
    return actor, stash
