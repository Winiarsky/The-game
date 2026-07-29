from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def scaffold_scenario(
    scenario_id: str,
    name: str,
    *,
    output_root: str | Path = ROOT / "content" / "scenarios",
) -> Path:
    target = Path(output_root) / scenario_id
    if target.exists():
        raise FileExistsError(f"Paczka scenariusza już istnieje: {target}")
    (target / "exploration").mkdir(parents=True)
    (target / "assets").mkdir()

    header = {
        "schema": "dnd_board_game.scenario",
        "schema_version": 1,
        "ruleset_id": "dnd_5e_2014",
        "source_pack_ids": ["project_original"],
    }
    _write(
        target / "scenario.json",
        {
            **header,
            "id": scenario_id,
            "name": name,
            "scene_mode": "exploration",
            "board": {"cols": 20, "rows": 30},
            "parts": {
                "actors": "actors.json",
                "environment": "environment.json",
                "objectives": "objectives.json",
                "llm_context": "llm_context.json",
                "exploration": {
                    key: f"exploration/{key}.json"
                    for key in (
                        "party_start_zone",
                        "zones",
                        "points",
                        "challenges",
                        "encounter_triggers",
                        "npc_transitions",
                        "observations",
                        "flows",
                        "traps",
                        "resources",
                        "initial_resources",
                    )
                },
            },
        },
    )
    _write(
        target / "actors.json",
        {
            "actors": [
                {
                    "id": "placeholder_hero",
                    "name": "Bohater testowy",
                    "kind": "player_character",
                    "faction": "ally",
                    "uses_death_saves": True,
                    "ac": 12,
                    "hp": 10,
                    "speed_feet": 30,
                    "position": [1, 1],
                    "ability_scores": {
                        ability: 10
                        for ability in (
                            "strength",
                            "dexterity",
                            "constitution",
                            "intelligence",
                            "wisdom",
                            "charisma",
                        )
                    },
                    "proficiency_bonus": 2,
                    "item_refs": ["dagger"],
                }
            ]
        },
    )
    _write(target / "environment.json", {"environment": []})
    _write(target / "objectives.json", {"objectives": []})
    _write(
        target / "llm_context.json",
        {
            "llm_context": {
                "summary": f"Scenariusz {name}. Uzupełnij fakty świata przed pisaniem interakcji.",
                "available_materials": [],
                "forbidden_assumptions": [],
                "risk_notes": [],
            }
        },
    )
    _write(target / "exploration" / "party_start_zone.json", {"party_start_zone": "start"})
    _write(
        target / "exploration" / "zones.json",
        {
            "zones": [
                {
                    "id": "start",
                    "name": "Lokacja startowa",
                    "positions": [[1, 1]],
                    "anchor_position": [1, 1],
                    "interaction_pad_positions": [[3, 1], [5, 1], [7, 1], [9, 1]],
                    "color": "marker",
                    "description": "Uzupełnij opis lokacji startowej.",
                    "adjacent_zone_ids": [],
                }
            ]
        },
    )
    for filename, key in (
        ("points", "points"),
        ("challenges", "challenges"),
        ("encounter_triggers", "encounter_triggers"),
        ("npc_transitions", "npc_transitions"),
        ("observations", "observations"),
        ("flows", "flows"),
        ("traps", "traps"),
        ("resources", "resources"),
        ("initial_resources", "initial_resources"),
    ):
        _write(target / "exploration" / f"{filename}.json", {key: []})
    _write(
        target / "print_maps.json",
        {
            "schema": "dnd_board_game.print_map_manifest",
            "schema_version": 1,
            "output_root": f"assets/print_maps/{scenario_id}",
            "maps": [],
        },
    )
    return target / "scenario.json"


def _write(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Utwórz kompletny, minimalny szkielet scenariusza eksploracyjnego."
    )
    parser.add_argument("scenario_id", help="Stabilne id, np. popiol_i_stal")
    parser.add_argument("name", help="Polska nazwa wyświetlana graczom")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=ROOT / "content" / "scenarios",
    )
    args = parser.parse_args()
    if not args.scenario_id.replace("_", "").isalnum() or args.scenario_id.lower() != args.scenario_id:
        parser.error("scenario_id może zawierać małe litery, cyfry i podkreślenia")
    print(scaffold_scenario(args.scenario_id, args.name, output_root=args.output_root))


if __name__ == "__main__":
    main()
