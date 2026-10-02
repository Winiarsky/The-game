"""Build illustrated A4 equipment cards from runtime inventories and mission data."""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from dnd_board_game.ui.training_arena import training_hero
from dnd_board_game.inventory import InventoryItem
from dnd_board_game.inventory.party_equipment import SLOTS, slots_for
from dnd_board_game.physical_cards.equipment_art import item_art
from dnd_board_game.physical_cards.mana_print_files import render_pdf

HEROES=('garran','brakka','dagna','erynd','lorian','mira','nimra')


def card(item: InventoryItem, origin: str, *, print_root: Path, identified: bool=False) -> str:
    slots=', '.join(SLOTS[k] for k in slots_for(item))
    if item.id=='mission_ring':slots='Pierścień' if identified else 'Zapas — wymaga identyfikacji'
    details=[]
    if item.kind=='weapon':details.append(f'{item.hands_required or 1} ręka' if (item.hands_required or 1)==1 else '2 ręce')
    if item.armor_base_ac is not None:
        dex=' + Zręczność' if item.armor_dexterity_cap is None else f' + Zręczność (maks. {item.armor_dexterity_cap})' if item.armor_dexterity_cap else ''
        details.append(f'KP {item.armor_base_ac}{dex}')
    if item.armor_class_bonus:details.append(f'+{item.armor_class_bonus} KP')
    if item.quantity>1:details.append(f'Stos: {item.quantity} szt.')
    return f'<article><header>{escape(origin)}</header><div class="art">{item_art(item, print_root=print_root)}</div><h2>{escape(item.name)}</h2><p class="slots">{escape(slots or "Przedmiot zadania — wspólny zapas")}</p><b>{escape(" · ".join(details))}</b><p>{escape(item.description or "Zwykły przedmiot wyposażenia. Nie daje dodatkowej premii do testów.")}</p><footer>Przekaż kartę razem z przedmiotem.</footer></article>'


def document(cards: list[str], title: str) -> str:
    pages=['<section>'+''.join(cards[i:i+9])+'</section>' for i in range(0,len(cards),9)]
    return '''<!doctype html><html lang="pl"><meta charset="utf-8"><title>'''+escape(title)+'''</title><style>
@page{size:A4;margin:9mm}*{box-sizing:border-box}body{margin:0;color:#111;font:8pt Arial,sans-serif}section{display:grid;grid-template-columns:repeat(3,63mm);grid-auto-rows:88mm;gap:1mm;break-after:page}section:last-child{break-after:auto}article{border:.25mm dashed #666;padding:3mm;position:relative;overflow:hidden;break-inside:avoid}header{font-size:7pt;border-bottom:.3mm solid #111;padding-bottom:1mm}.art{height:34mm;text-align:center;padding:1mm 0}.art img{height:100%;width:100%;object-fit:contain}h2{font: bold 12pt Georgia,serif;margin:1mm 0}p{margin:1.5mm 0;line-height:1.2}.slots{font-weight:bold;font-size:7pt}footer{position:absolute;bottom:2mm;left:3mm;right:3mm;font-size:6pt;border-top:.2mm solid #aaa;padding-top:1mm}b{font-size:8pt}</style>'''+''.join(pages)+'</html>'


def mission_item_cards(pack: Path, print_root: Path) -> tuple[list[str], str]:
    """Normal handouts and the replacement card revealed after identification."""
    data=json.loads((pack/'mechanics/items.json').read_text())
    found=[]
    for key in ('ring','medallion','potion','weak_potion','key','documents'):
        spec=data[key];item=InventoryItem(id='mission_'+key,name=spec['name'],description=spec['description'],kind='gear',equipped=False)
        found.append(card(item,'Misja 0 · znalezisko / przedmiot zadania',print_root=print_root))
    spec=data['ring_identified']
    known=InventoryItem(id='mission_ring',name=spec['name'],description=spec['description'],kind='gear',equipped=False)
    # A separate page/card is handed over only after identifying; it is the same physical item.
    known_card=card(known,'Po identyfikacji — zastępuje kartę pierścienia',print_root=print_root,identified=True)
    return found, known_card


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--html-only',action='store_true');args=parser.parse_args()
    # Starting equipment is already on page five of each current character set.
    from build_handouts import build_mission
    for path in build_mission(html_only=args.html_only).values():
        print(path, flush=True)


if __name__=='__main__':main()
