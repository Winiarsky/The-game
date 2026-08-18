from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .loader import LoadedScenario


@dataclass(frozen=True, slots=True)
class ScenarioPreflightIssue:
    code: str
    path: str
    message: str


def preflight_scenario(
    loaded: LoadedScenario,
    *,
    game_asset_root: str | Path,
) -> tuple[ScenarioPreflightIssue, ...]:
    """Validate the physical-board and asset contract of a loaded scenario."""
    definition = loaded.definition
    scenario_root = _scenario_asset_root(loaded.path)
    assets_root = Path(game_asset_root)
    issues: list[ScenarioPreflightIssue] = []

    occupied_markers = {zone.marker_position for zone in definition.exploration_zones}
    occupied_points = {
        position
        for point in definition.exploration_points
        for position in point.positions
    }
    interactive_point_positions_by_zone = {
        zone.id: {
            position
            for point in definition.exploration_points
            if point.zone_id == zone.id
            and (point.npc_interaction is not None or point.merchant_id is not None)
            for position in point.positions
        }
        for zone in definition.exploration_zones
    }
    for zone in definition.exploration_zones:
        pads = zone.interaction_pad_positions
        for position in pads:
            if not definition.board_dimensions.in_bounds(position):
                issues.append(
                    ScenarioPreflightIssue(
                        "interaction_pad_out_of_bounds",
                        f"exploration.zones.{zone.id}.interaction_pad_positions",
                        f"Pole {position.as_tuple()} leży poza planszą.",
                    )
                )
            if position in occupied_markers or (
                position in occupied_points
                and position not in interactive_point_positions_by_zone[zone.id]
            ):
                issues.append(
                    ScenarioPreflightIssue(
                        "interaction_pad_overlaps_marker",
                        f"exploration.zones.{zone.id}.interaction_pad_positions",
                        f"Pole {position.as_tuple()} pokrywa się z polem lokacji lub punktu.",
                    )
                )
        required_slots = _required_interaction_slots(loaded, zone.id)
        if required_slots > len(pads):
            issues.append(
                ScenarioPreflightIssue(
                    "interaction_pad_capacity_exceeded",
                    f"exploration.zones.{zone.id}.interaction_pad_positions",
                    f"Potrzeba do {required_slots} pól interakcji, dostępnych jest {len(pads)}.",
                )
            )
        if len(pads) > 8:
            issues.append(
                ScenarioPreflightIssue(
                    "interaction_pad_color_capacity_exceeded",
                    f"exploration.zones.{zone.id}.interaction_pad_positions",
                    "UI i paleta planszy obsługują maksymalnie 8 pól interakcji.",
                )
            )

        _check_image(issues, scenario_root, zone.image, f"exploration.zones.{zone.id}.image")
        if zone.paper_map is not None:
            for field, value in (
                ("preview_path", zone.paper_map.preview_path),
                ("a4_pdf_path", zone.paper_map.a4_pdf_path),
                ("full_size_pdf_path", zone.paper_map.full_size_pdf_path),
            ):
                if not (assets_root / value).is_file():
                    issues.append(
                        ScenarioPreflightIssue(
                            "paper_map_asset_missing",
                            f"exploration.zones.{zone.id}.paper_map.{field}",
                            f"Brakuje pliku mapy: {value}.",
                        )
                    )

    for point in definition.exploration_points:
        _check_image(
            issues,
            scenario_root,
            point.image,
            f"exploration.points.{point.id}.image",
        )
        if point.npc_interaction is not None:
            for goal in point.npc_interaction.goals:
                _check_image(
                    issues,
                    scenario_root,
                    goal.image,
                    f"exploration.points.{point.id}.goals.{goal.id}.image",
                )
    for challenge in definition.exploration_challenges:
        for goal in challenge.goals:
            _check_image(
                issues,
                scenario_root,
                goal.image,
                f"exploration.challenges.{challenge.id}.goals.{goal.id}.image",
            )
    return tuple(issues)


def _required_interaction_slots(loaded: LoadedScenario, zone_id: str) -> int:
    definition = loaded.definition
    candidates = [
        len(challenge.goals) or len(challenge.options)
        for challenge in definition.exploration_challenges
        if challenge.zone_id == zone_id
    ]
    candidates.extend(
        len(point.npc_interaction.goals)
        for point in definition.exploration_points
        if point.zone_id == zone_id and point.npc_interaction is not None
    )
    return max(candidates, default=0)


def _check_image(
    issues: list[ScenarioPreflightIssue],
    scenario_root: Path,
    value: str,
    field: str,
) -> None:
    if value and not (scenario_root / value).is_file():
        issues.append(
            ScenarioPreflightIssue(
                "scenario_image_missing",
                field,
                f"Brakuje grafiki scenariusza: {value}.",
            )
        )


def _scenario_asset_root(path: Path) -> Path:
    if path.is_dir():
        return path
    sibling = path.with_suffix("")
    return sibling if sibling.is_dir() else path.parent
