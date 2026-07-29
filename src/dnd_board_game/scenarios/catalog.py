from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dnd_board_game.exploration import SceneMode

from .loader import ScenarioDefinition, load_scenario


@dataclass(frozen=True, slots=True)
class ScenarioCatalogEntry:
    id: str
    name: str
    path: Path
    has_paper_map: bool
    continuation_scene_names: tuple[str, ...] = ()

    @property
    def scene_count(self) -> int:
        return 1 + len(self.continuation_scene_names)


def discover_scenarios(root: str | Path) -> tuple[ScenarioCatalogEntry, ...]:
    scenario_root = Path(root)
    paths = [
        path
        for path in sorted(scenario_root.glob("*.json"))
        if not (scenario_root / path.stem / "scenario.json").exists()
    ]
    paths.extend(sorted(scenario_root.glob("*/scenario.json")))
    candidates: dict[str, tuple[Path, ScenarioDefinition]] = {}
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
        candidates[definition.id] = (path, definition)

    continuation_target_ids = {
        definition.exploration_continuation.target_scenario_id
        for _path, definition in candidates.values()
        if definition.exploration_continuation is not None
    }
    entries: list[ScenarioCatalogEntry] = []
    for scenario_id, (path, definition) in candidates.items():
        if scenario_id in continuation_target_ids:
            continue
        entries.append(
            ScenarioCatalogEntry(
                id=definition.id,
                name=definition.name,
                path=path,
                has_paper_map=any(
                    zone.paper_map is not None
                    for zone in definition.exploration_zones
                ),
                continuation_scene_names=_continuation_scene_names(
                    definition.id,
                    candidates,
                ),
            )
        )
    return tuple(sorted(entries, key=lambda entry: entry.name.casefold()))


def _continuation_scene_names(
    scenario_id: str,
    candidates: dict[str, tuple[Path, ScenarioDefinition]],
) -> tuple[str, ...]:
    names: list[str] = []
    visited = {scenario_id}
    current_id = scenario_id
    while current_id in candidates:
        definition = candidates[current_id][1]
        continuation = definition.exploration_continuation
        if continuation is None or continuation.target_scenario_id in visited:
            break
        target_id = continuation.target_scenario_id
        target = candidates.get(target_id)
        if target is None:
            break
        visited.add(target_id)
        names.append(target[1].name)
        current_id = target_id
    return tuple(names)
