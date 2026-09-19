"""Mission-authored tile batches, sharing geometry with the physical cutouts."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from dnd_board_game.combat.setup import SetupStep, SetupStepKind
from dnd_board_game.hardware.led_palette import LedColor
from dnd_board_game.physical_cards.scenario_cutouts import Cutout, build_cutouts, tile_svg
from dnd_board_game.scenarios.mission_pack import asset_url, read_json
from dnd_board_game.world import Coordinate


def tiles(root: Path) -> dict[str, Cutout]:
    return {t.id: t for t in build_cutouts(read_json(root, 'maps/cutouts.json'),
                                         read_json(root, 'mechanics/battle.json'))}


def road_placement(root: Path) -> dict[str, Any]:
    """Road placement uses the printed cart's current rotated footprint."""
    spec = read_json(root, 'maps/setup.json')['road_placement']
    tile = replace(tiles(root)[spec['cutout_id']], origin=tuple(spec['origin']))
    return dict(positions=list(tile.positions), party_position=spec['party_position'])


def prepare(root: Path, spec: dict[str, Any]) -> dict[str, Any]:
    """Render the actual cutout, including its frame, caption and interaction mark."""
    catalog = tiles(root)
    selected = tuple(catalog[key] for key in spec.get('cutout_ids', ()))
    positions = [list(p) for tile in selected for p in tile.positions]
    focus = [list(tile.interaction) for tile in selected if tile.interaction]
    if spec.get('position') and spec['position'] not in focus:
        focus.append(spec['position'])
    positions.extend(p for p in focus if p not in positions)
    previews = []
    for tile in selected:
        artwork = asset_url(root, tile.artwork) if tile.artwork else ''
        w, h = (n * 25 for n in tile.size)
        picture = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
                   f'font-family="DejaVu Sans,Arial,sans-serif" aria-hidden="true">'
                   + tile_svg(tile, 25, artwork) + '</svg>')
        previews.append(dict(id=tile.id, name=tile.print_name or tile.name, size=list(tile.size),
                             board_size=list(tile.board_size), board_rotation=tile.board_rotation,
                             origin=list(tile.origin), svg=picture))
    return dict(spec, positions=positions, focus_positions=focus, tiles=previews)


def step_from_data(data: dict[str, Any]) -> SetupStep:
    return SetupStep(kind=SetupStepKind.ENVIRONMENT, label=data['title'],
                     message=data['body'],
                     positions=tuple(Coordinate(*p) for p in data['positions']),
                     color=LedColor.SETUP_FOOTPRINT,
                     focus_positions=tuple(Coordinate(*p) for p in data['focus_positions']),
                     cutout_ids=tuple(data.get('cutout_ids', ())))


def battle_steps(root: Path, original: tuple[SetupStep, ...]) -> tuple[SetupStep, ...]:
    """Whole terrain tiles first, then the native hero/enemy placement steps."""
    specs = read_json(root, 'maps/setup.json')['battle_setup']
    catalog = tiles(root)
    ids = [key for spec in specs for key in spec['cutout_ids']]
    expected = {tile.id for tile in catalog.values() if tile.environment_id}
    if len(set(ids)) != len(ids) or set(ids) != expected:
        raise ValueError('Setup walki musi zawierać każdy kafel terenu dokładnie raz.')
    terrain = tuple(step_from_data(prepare(root, spec)) for spec in specs)
    figures = tuple(step for step in original if step.kind != SetupStepKind.ENVIRONMENT)
    return (*terrain, *figures)


def enrich_combat_payload(root: Path, payload: dict[str, Any]) -> None:
    setup = payload.get('encounter_setup')
    current = (setup or {}).get('current_step')
    if not current or not current.get('cutout_ids'):
        return
    prepared = prepare(root, dict(title=current['label'], body=current['message'],
                                 cutout_ids=current['cutout_ids']))
    current['tiles'] = prepared['tiles']
