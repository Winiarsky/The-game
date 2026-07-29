from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dnd_board_game.exploration import SceneMode

from .loader import load_scenario


@dataclass(frozen=True, slots=True)
class ScenarioCatalogEntry:
    id: str
    name: str
    path: Path
    has_paper_map: bool


def discover_scenarios(root: str | Path) -> tuple[ScenarioCatalogEntry, ...]:
    scenario_root = Path(root)
    paths = [
        path
        for path in sorted(scenario_root.glob("*.json"))
        if not (scenario_root / path.stem / "scenario.json").exists()
    ]
    paths.extend(sorted(scenario_root.glob("*/scenario.json")))
    entries: list[ScenarioCatalogEntry] = []
    seen_ids: set[str] = set()
    for path in paths:
        loaded = load_scenario(path)
        definition = loaded.definition
        if (
            definition.scene_mode != SceneMode.EXPLORATION
            or not definition.exploration_zones
            or definition.id in seen_ids
        ):
            continue
        seen_ids.add(definition.id)
        entries.append(
            ScenarioCatalogEntry(
                id=definition.id,
                name=definition.name,
                path=path,
                has_paper_map=any(
                    zone.paper_map is not None
                    for zone in definition.exploration_zones
                ),
            )
        )
    return tuple(sorted(entries, key=lambda entry: entry.name.casefold()))
