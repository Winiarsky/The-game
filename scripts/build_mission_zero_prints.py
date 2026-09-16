"""Tile mission maps using the calibrated, existing arena print geometry."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from build_arena_print_pack import map_body, tile_svg, tiles, document
from dnd_board_game.physical_cards.mana_print_files import render_pdf


def main() -> None:
    pack=ROOT/'content/scenarios/misja_0_dzwon'
    output=pack/'maps/print';output.mkdir(exist_ok=True)
    panel=map_body({'board':{'cols':20,'rows':30}})
    panel=panel[panel.index('<rect y="475"'):]
    for name,title in [('guild','GILDIA'),('outpost','POSTERUNEK')]:
        source=(pack/'maps'/f'{name}.svg').read_text()
        inner=source[source.index('>')+1:source.rindex('</svg>')]
        body='<g transform="matrix(0 .8333333333 -.8333333333 0 750 0)">'+inner+'</g>'+panel
        html=document(''.join('<section class="sheet">'+tile_svg(t,body).replace('ARENA NESSY',title)+'</section>' for t in tiles()),'landscape')
        html=html.replace('Arena i karty — druk A4',title+' — Misja 0, mapa A4')
        path=output/f'{name}_A4.html';path.write_text(html)
        render_pdf(path,output/f'{name}_A4.pdf')
        print(title,output/f'{name}_A4.pdf',flush=True)

if __name__=='__main__':main()
