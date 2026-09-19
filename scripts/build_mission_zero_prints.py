"""Tile mission maps using the calibrated, existing arena print geometry."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from build_arena_print_pack import map_body, tile_svg, tiles, document
from dnd_board_game.physical_cards.mana_print_files import render_pdf
from dnd_board_game.physical_cards.scenario_cutouts import Cutout, build_cutouts, tile_svg as cutout_svg


def overview_svg(cutouts: tuple[Cutout, ...], scene: str) -> str:
    """Generate map outlines from the same rotated geometry used by setup LEDs."""
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="600" height="900" viewBox="0 0 600 900">',
             '<defs><pattern id="g" width="30" height="30" patternUnits="userSpaceOnUse"><path d="M30 0H0V30" fill="none" stroke="#aaa" stroke-width=".5"/></pattern></defs>',
             '<rect width="600" height="900" fill="white"/><rect width="600" height="900" fill="url(#g)"/>',
             '<rect x="570" width="30" height="900" fill="#ddd"/>']
    for tile in cutouts:
        if tile.scene != scene:
            continue
        x, y = (v*30 for v in tile.origin)
        w, h = (v*30 for v in tile.size)
        transform = {0: f'translate({x} {y})', 90: f'translate({x+h} {y}) rotate(90)',
                     180: f'translate({x+w} {y+h}) rotate(180)',
                     270: f'translate({x} {y+w}) rotate(-90)'}[tile.board_rotation % 360]
        parts.append(f'<g data-cutout="{tile.id}" transform="{transform}">{cutout_svg(tile, 30)}</g>')
    return ''.join(parts) + '</svg>'


def main() -> None:
    pack=ROOT/'content/scenarios/misja_0_dzwon'
    output=pack/'maps/print';output.mkdir(exist_ok=True)
    panel=map_body({'board':{'cols':20,'rows':30}})
    panel=panel[panel.index('<rect y="475"'):]
    cutouts=build_cutouts(json.loads((pack/'maps/cutouts.json').read_text()),
                          json.loads((pack/'mechanics/battle.json').read_text()))
    for name,title in [('guild','GILDIA'),('outpost','POSTERUNEK')]:
        source=overview_svg(cutouts,name)
        (pack/'maps'/f'{name}.svg').write_text(source)
        inner=source[source.index('>')+1:source.rindex('</svg>')]
        body='<g transform="matrix(0 .8333333333 -.8333333333 0 750 0)">'+inner+'</g>'+panel
        html=document(''.join('<section class="sheet">'+tile_svg(t,body).replace('ARENA NESSY',title)+'</section>' for t in tiles()),'landscape')
        html=html.replace('Arena i karty — druk A4',title+' — Misja 0, mapa A4')
        path=output/f'{name}_A4.html';path.write_text(html)
        render_pdf(path,output/f'{name}_A4.pdf')
        print(title,output/f'{name}_A4.pdf',flush=True)

if __name__=='__main__':main()
