"""Slot-first preparation; the same choices drive the sheet, runes and LEDs."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, TYPE_CHECKING

from dnd_board_game.inventory import CurrencyWallet, InventoryItem, hands_required
from dnd_board_game.inventory.party_equipment import (
    SLOTS, POCKETS_PER_PAGE, change_slot, pockets, slot_items, quest_item,
    needs_identification, ready_for_use, identify_item, release_identified, sell,
)
from .board_panel_symbols import panel_icon, rune_slot
from .exploration_mana_board import choice

if TYPE_CHECKING:
    from .exploration_app import ExplorationUiSession
    from dnd_board_game.actors import Actor

STAGES = ('equipment', 'equipment_item', 'equipment_stash', 'equipment_sell')
BODY_RUNES = (('neck', 'Kielich'), ('head', 'Korona'), ('ring', 'Romb'),
              ('main_hand', 'Grot'), ('armor', 'Wieża'), ('off_hand', 'Kotwica'), ('focus', 'Trójząb'))
PACK_RUNES = ('Rozwidlenie', 'Klepsydra', 'Brama', 'Hak', 'Błysk', 'Oko', 'Schody', 'Węzeł')


@dataclass(frozen=True)
class EquipmentOption:
    item: InventoryItem | None
    source: str
    current: bool = False


def normalize(m: dict[str, Any]) -> None:
    """Old snapshots open on the new sheet without changing their equipment."""
    if m.get('equipment_ui_version') != 2:
        if m['stage'] in ('equipment_item', 'equipment_sell'):
            m['stage'] = 'equipment'
        m.update(equipment_ui_version=2, equipment_slot='', equipment_index=0, equipment_page=0)
    m.setdefault('equipment_group', 'available')
    m.setdefault('equipment_notice', '')


def begin(m: dict[str, Any], home: str) -> None:
    m.pop('equipment_help_return', None)
    m.update(stage='equipment', equipment_home=home, equipment_hero=0,
             equipment_index=0, equipment_page=0, equipment_slot='',
             equipment_group='available', equipment_notice='', equipment_ui_version=2)


def actor(s: ExplorationUiSession, m: dict[str, Any]) -> Actor:
    return s.exploration.actors[m['equipment_hero']]


def sheet_slots(s: ExplorationUiSession, m: dict[str, Any]) -> tuple[tuple[str, int], ...]:
    rows = pockets(actor(s, m))
    page = min(m.get('equipment_page', 0), len(rows) // POCKETS_PER_PAGE - 1)
    return (*((key, rune_slot(rune)) for key, rune in BODY_RUNES),
            *((f'pack_{page * POCKETS_PER_PAGE + n}', rune_slot(rune)) for n, rune in enumerate(PACK_RUNES, 1)))


def slot_label(slot: str) -> str:
    return f'Plecak · miejsce {slot[5:]}' if slot.startswith('pack_') else SLOTS[slot]


def options(s: ExplorationUiSession, m: dict[str, Any]) -> tuple[EquipmentOption, ...]:
    a = actor(s, m)
    slot = m['equipment_slot']
    current = slot_items(a, slot)
    result = [EquipmentOption(i, 'hero', True) for i in current]
    for source, rows in (('stash', s.state.party_loot.items), ('hero', a.inventory)):
        for item in rows:
            if source == 'hero' and item in current:
                continue
            try:
                change_slot(a, s.state.party_loot, slot, item.id, source=source)
            except ValueError:
                continue
            result.append(EquipmentOption(item, source))
    result.append(EquipmentOption(None, 'empty', not current))
    return tuple(result)


def stash_groups(s: ExplorationUiSession) -> dict[str, tuple[InventoryItem, ...]]:
    items = s.state.party_loot.items
    return dict(available=tuple(i for i in items if not quest_item(i) and ready_for_use(i)),
                found=tuple(i for i in items if not quest_item(i) and not ready_for_use(i)),
                quest=tuple(i for i in items if quest_item(i)))


def selected(s: ExplorationUiSession, m: dict[str, Any]) -> InventoryItem | None:
    rows = options(s, m) if m['stage'] == 'equipment_item' else stash_groups(s)[m['equipment_group']]
    if not rows:
        return None
    row = rows[min(m['equipment_index'], len(rows) - 1)]
    return row.item if isinstance(row, EquipmentOption) else row


def choices(s: ExplorationUiSession, m: dict[str, Any]) -> list[dict[str, Any]]:
    from . import mission_zero as mission
    result: list[dict[str, Any]] = []
    def add(slot: int, action: str, label: str, **extra: Any) -> None:
        result.append(choice(slot, action, label, **extra))
    if m['stage'] == 'equipment_intro':
        add(28, 'equipment_continue', 'Wróć do wyposażenia')
        add(29, 'equipment_intro_back', 'Wróć do wyposażenia')
        return result
    if m['stage'] == 'equipment_sell':
        add(28, 'equipment_sell_confirm', 'Potwierdź sprzedaż')
        add(29, 'equipment_stash_back', 'Zachowaj przedmiot')
    elif m['stage'] == 'equipment_item':
        rows = options(s, m)
        selected_option = rows[min(m['equipment_index'], len(rows) - 1)]
        if len(rows) > 1:
            add(27, 'equipment_previous', 'Poprzedni przedmiot')
            add(26, 'equipment_next', 'Następny przedmiot')
        label = 'Zachowaj' if selected_option.current else 'Odłóż do zapasu' if selected_option.item is None else 'Załóż' if not m['equipment_slot'].startswith('pack_') else 'Włóż do plecaka'
        add(28, 'equipment_confirm', label)
        add(29, 'equipment_list', 'Anuluj zmianę')
    elif m['stage'] == 'equipment_stash':
        for slot, group, label in ((5, 'available', 'Zapas w bazie'), (6, 'found', 'Znaleziska'), (7, 'quest', 'Przedmioty drużyny')):
            add(slot, 'equipment_group', label, group=group)
        item = selected(s, m)
        if len(stash_groups(s)[m['equipment_group']]) > 1:
            add(27, 'equipment_previous', 'Poprzedni przedmiot')
            add(26, 'equipment_next', 'Następny przedmiot')
        if item and m['equipment_group'] == 'found' and m['equipment_home'] == 'guild_return':
            price = mission.read_json(mission.root(s), 'mechanics/rewards.json')['identification_gp'] if (item.source_ref or item.id) == 'mission_ring' and not item.magic_effects else 0
            add(28, 'equipment_identify', f'Identyfikacja — {price} sz' if price else 'Sprawdź i zidentyfikuj')
        if item and m['equipment_group'] == 'available' and item.value_cp > 0:
            add(8, 'equipment_sell', f'Sprzedaj za {item.value_cp * item.quantity / 200:g} sz')
        add(29, 'equipment_list', 'Wróć do postaci')
    else:
        for key, slot in sheet_slots(s, m):
            add(slot, 'equipment_slot', slot_label(key), gear_slot=key)
        pages = len(pockets(actor(s, m))) // POCKETS_PER_PAGE
        if pages > 1:
            add(21, 'equipment_pack_previous', 'Poprzednie miejsca plecaka')
            add(22, 'equipment_pack_next', 'Dalsze miejsca plecaka')
        add(23, 'equipment_stash', 'Zapas i przedmioty drużyny')
        add(25, 'equipment_help', mission.label(s, 'equipment_help'))
        add(28, 'equipment_accept', 'Gotowe — następna postać' if m['equipment_hero'] + 1 < len(s.exploration.actors) else 'Gotowe — ruszamy')
        add(29, 'equipment_back', 'Poprzednia postać' if m['equipment_hero'] else 'Wróć do odprawy' if m['equipment_home'] == 'departure' else 'Wróć do Gildii')
    return result


def item_payload(item: InventoryItem | None) -> dict[str, Any] | None:
    if item is None:
        return None
    from dnd_board_game.physical_cards.equipment_art import item_art
    return dict(id=item.id, name=item.name, description=item.description, quantity=item.quantity,
                art=item_art(item), two_handed=hands_required(item) == 2,
                needs_identification=needs_identification(item))


def payload(s: ExplorationUiSession, m: dict[str, Any]) -> dict[str, Any] | None:
    if m['stage'] not in STAGES:
        return None
    from dnd_board_game.inventory import effective_armor_class
    from dnd_board_game.inventory.magic_items import effective_ability_score
    from .exploration_app import _actor_portrait_url
    from . import mission_zero as mission
    from dnd_board_game.scenarios.mission_pack import asset_url
    a = actor(s, m)
    portrait_path = f'assets/images/{a.id}.png'
    portrait = asset_url(mission.root(s), portrait_path) if (mission.root(s) / portrait_path).is_file() else _actor_portrait_url(a)
    groups = stash_groups(s)
    picker = None
    item = None
    if m['stage'] == 'equipment_item':
        rows = options(s, m)
        index = min(m['equipment_index'], len(rows) - 1)
        option = rows[index]
        item = item_payload(option.item)
        picker = dict(slot=m['equipment_slot'], label=slot_label(m['equipment_slot']), index=index + 1, count=len(rows),
                      current=option.current, source=option.source,
                      names=[o.item.name if o.item else 'Puste miejsce' for o in rows])
    elif m['stage'] in ('equipment_stash', 'equipment_sell'):
        item = item_payload(selected(s, m))
    loadout = []
    for key, slot in sheet_slots(s, m):
        equipped = slot_items(a, key)
        loadout.append(dict(id=key, label=slot_label(key), slot=slot, icon=panel_icon(slot),
                            item=item_payload(equipped[0]) if equipped else None,
                            linked=bool(equipped and key == 'off_hand' and hands_required(equipped[0]) == 2)))
    return dict(hero=a.name, hero_id=str(a.id), portrait_url=portrait, hero_index=m['equipment_hero'] + 1,
                hero_count=len(s.exploration.actors), party=[dict(id=str(h.id), name=h.name) for h in s.exploration.actors],
                view=m['stage'], loadout=loadout, picker=picker, item=item, group=m['equipment_group'],
                groups={key: len(rows) for key, rows in groups.items()},
                stash_index=min(m['equipment_index'] + 1, len(groups[m['equipment_group']])),
                pack_page=m['equipment_page'] + 1, pack_pages=len(pockets(a)) // POCKETS_PER_PAGE,
                notice=m.get('equipment_notice', ''), gold=s.exploration.actors[0].currency.total_cp / 100,
                ac=effective_armor_class(a), strength=effective_ability_score(a, 'strength'),
                can_identify=m['equipment_home'] == 'guild_return')


def handle(s: ExplorationUiSession, m: dict[str, Any], action: str, data: dict[str, Any]) -> bool:
    if not action.startswith('equipment_'):
        return False
    from . import mission_zero as mission
    from . import mission_zero_recovery as recovery
    require_unlocked(s)
    if action == 'equipment_open':
        s.state = replace(s.state, party_loot=release_identified(s.state.party_loot))
        begin(m, 'guild_return')
        return True
    if action == 'equipment_help':
        m.update(equipment_help_return=m['stage'], stage='equipment_intro')
        return True
    if action in ('equipment_continue', 'equipment_intro_back'):
        m['stage'] = m.pop('equipment_help_return', None) or 'equipment'
        return True
    a = actor(s, m)
    if action == 'equipment_slot':
        slot = str(data.get('gear_slot', ''))
        if slot not in {key for key, _ in sheet_slots(s, m)}:
            raise ValueError('Wybierz widoczne miejsce wyposażenia.')
        m.update(stage='equipment_item', equipment_slot=slot, equipment_index=0, equipment_notice='')
    elif action in ('equipment_previous', 'equipment_next'):
        count = len(options(s, m)) if m['stage'] == 'equipment_item' else len(stash_groups(s)[m['equipment_group']])
        m['equipment_index'] = (m['equipment_index'] + (-1 if action == 'equipment_previous' else 1)) % count
    elif action in ('equipment_pack_previous', 'equipment_pack_next'):
        count = len(pockets(a)) // POCKETS_PER_PAGE
        m['equipment_page'] = (m['equipment_page'] + (-1 if action == 'equipment_pack_previous' else 1)) % count
    elif action == 'equipment_confirm':
        rows = options(s, m)
        option = rows[min(m['equipment_index'], len(rows) - 1)]
        updated, stash = change_slot(a, s.state.party_loot, m['equipment_slot'], option.item.id if option.item else None,
                                     source=option.source if option.item else 'stash')
        mission._set_actor(s, updated)
        s.state = replace(s.state, party_loot=stash)
        m.update(stage='equipment', equipment_notice=f'{slot_label(m["equipment_slot"])}: {option.item.name if option.item else "puste"}.', equipment_index=0,
                 equipment_page=min(m['equipment_page'], len(pockets(updated)) // POCKETS_PER_PAGE - 1))
    elif action == 'equipment_list':
        m.update(stage='equipment', equipment_index=0)
    elif action == 'equipment_stash':
        m.update(stage='equipment_stash', equipment_group='available', equipment_index=0)
    elif action == 'equipment_group':
        group = str(data.get('group', ''))
        if group not in stash_groups(s):
            raise ValueError('Nieznana grupa przedmiotów.')
        m.update(equipment_group=group, equipment_index=0)
    elif action == 'equipment_identify':
        item = selected(s, m)
        if item is None or m['equipment_home'] != 'guild_return':
            raise ValueError('Znaleziska identyfikujemy po powrocie do Gildii.')
        if (item.source_ref or item.id) == 'mission_ring' and not item.magic_effects:
            recovery.identify_paid(s, m)
        else:
            s.state = replace(s.state, party_loot=replace(s.state.party_loot, items=tuple(
                identify_item(i, at_base=True) if i.id == item.id else i for i in s.state.party_loot.items)))
        m.update(equipment_notice=f'{item.name}: gotowe w zapasie na kolejną wyprawę.', equipment_index=0)
    elif action == 'equipment_sell':
        m['stage'] = 'equipment_sell'
    elif action == 'equipment_stash_back':
        m['stage'] = 'equipment_stash'
    elif action == 'equipment_sell_confirm':
        item = selected(s, m)
        if item is None:
            raise ValueError('Nie ma przedmiotu do sprzedaży.')
        stash, price = sell(s.state.party_loot, item.id)
        owner = s.exploration.actors[0]
        mission._set_actor(s, replace(owner, currency=owner.currency.add(CurrencyWallet(cp=price))))
        s.state = replace(s.state, party_loot=stash)
        m['ledger'].extend((dict(kind='item', id=item.id, name=item.name, amount=-item.quantity),
                            dict(kind='money', id='sale:' + item.id, name='Sprzedaż: ' + item.name, amount=price / 100)))
        m.update(stage='equipment_stash', equipment_index=0, equipment_notice=f'Sprzedano {item.name}.')
    elif action in ('equipment_accept', 'equipment_back'):
        m['equipment_hero'] += 1 if action == 'equipment_accept' else -1
        m.update(equipment_index=0, equipment_page=0, equipment_slot='', equipment_notice='')
        if m['equipment_hero'] >= len(s.exploration.actors):
            m.update(stage=m['equipment_home'], equipment_ready=True)
        elif m['equipment_hero'] < 0:
            m.update(stage='brief' if m['equipment_home'] == 'departure' else m['equipment_home'], equipment_hero=0)
    else:
        return False
    return True


def locked(s: ExplorationUiSession) -> bool:
    from . import mission_zero as mission
    from dnd_board_game.combat.runes import uses_runes
    if s.combat_state is not None and any(uses_runes(actor) for actor in s.combat_state.actors):
        return True
    return mission.enabled(s) and bool(mission.read(s).get('equipment_locked'))


def require_unlocked(s: ExplorationUiSession) -> None:
    if locked(s):
        raise ValueError('Wyposażenie ustalono przed wyprawą. Zmieńcie je po powrocie do Gildii.')
