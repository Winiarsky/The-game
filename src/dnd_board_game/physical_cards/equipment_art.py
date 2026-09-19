"""Generated ink illustrations shared by equipment UI and printable cards."""
from __future__ import annotations

from html import escape
import os
from pathlib import Path
from urllib.parse import quote

from dnd_board_game.inventory import InventoryItem

ROOT = Path(__file__).resolve().parents[3]
COMMON_ART = ROOT / 'content/print/equipment/illustrations/ink_v2'
MISSION_ART = ROOT / 'content/scenarios/misja_0_dzwon/assets/items/ink_v2'
MISSION_MOTIFS = frozenset(('ring', 'medallion', 'potion', 'scroll', 'key'))

MOTIFS = {'mace':'mace','longsword':'sword','rapier':'rapier','dagger':'knife','hunting_knife':'knife',
 'throwing_knife':'knife','small_knife':'knife','greataxe':'axe','handaxe':'hatchet',
 'javelin':'spear','quarterstaff':'staff','longbow':'bow','crossbow':'crossbow','hand_crossbow':'crossbow',
 'arrow':'arrow','crossbow_bolt':'arrow','shield':'shield','chain_mail':'armor','scale_mail':'scale_armor',
 'leather_armor':'leather','studded_leather_armor':'leather','holy_symbol_amulet':'holy_symbol',
 'mission_medallion':'medallion','mission_ring':'ring','pouch':'pouch','component_pouch':'pouch',
 'dice_set':'dice','playing_card_set':'cards','lute':'lute','drum':'drum','spellbook':'book',
 'hunting_trap':'trap','shovel':'shovel','iron_pot':'pot','crowbar':'crowbar','ink':'ink','ink_pen':'quill',
 'woodcarvers_tools':'tools','thieves_tools':'lockpicks','mission_potion':'potion','mission_weak_potion':'potion',
 'mission_key':'key','mission_documents':'scroll'}


def motif(item: InventoryItem) -> str:
    key=item.source_ref or item.id
    if key in MOTIFS:return MOTIFS[key]
    if item.kind=='equipment_pack':return 'pack'
    if item.kind=='clothing':return 'clothes'
    return 'pack'


ART_NAMES = frozenset((*MOTIFS.values(), 'pack', 'clothes'))


def artwork_path(name: str) -> Path:
    if name not in ART_NAMES:
        raise ValueError('Nieznana ilustracja wyposażenia.')
    return (MISSION_ART if name in MISSION_MOTIFS else COMMON_ART) / (name + '.png')


def item_art(item: InventoryItem, *, print_root: Path | None = None) -> str:
    name = motif(item)
    path = artwork_path(name)
    if print_root is not None:
        # Relative links keep exported HTML usable after moving the repository.
        source = quote(os.path.relpath(path, print_root), safe='/')
    else:
        version = path.stat().st_mtime_ns if path.is_file() else 0
        source = f'/equipment-art/{name}.png?v={version}'
    return f'<img src="{escape(source, quote=True)}" alt="{escape(item.name, quote=True)}">'
