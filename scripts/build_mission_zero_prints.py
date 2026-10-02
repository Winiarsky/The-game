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
    """The historical map command now publishes the canonical board PDFs."""
    from build_handout_maps import main as current_main
    current_main()

if __name__=='__main__':main()
