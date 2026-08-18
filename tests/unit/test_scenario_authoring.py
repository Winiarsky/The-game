import json

import pytest
from PIL import Image

from dnd_board_game.scenarios import (
    discover_scenarios,
    load_scenario,
    preflight_scenario,
)
from scripts import generate_print_maps as print_maps
from scripts.generate_print_maps import PrintMapSpec, load_manifest
from scripts.scaffold_scenario import scaffold_scenario


def test_scaffold_creates_loadable_component_scenario(tmp_path) -> None:
    scenario_path = scaffold_scenario(
        "test_adventure",
        "Testowa przygoda",
        output_root=tmp_path,
    )

    loaded = load_scenario(scenario_path)

    assert loaded.definition.id == "test_adventure"
    assert loaded.definition.party_start_zone_id == "start"
    assert len(loaded.definition.exploration_zones) == 1
    assert (scenario_path.parent / "print_maps.json").is_file()


def test_scaffold_never_overwrites_existing_package(tmp_path) -> None:
    scaffold_scenario("test_adventure", "Test", output_root=tmp_path)

    with pytest.raises(FileExistsError):
        scaffold_scenario("test_adventure", "Inna nazwa", output_root=tmp_path)


def test_preflight_reports_missing_image_and_bad_pad(tmp_path) -> None:
    scenario_path = scaffold_scenario("bad_adventure", "Test", output_root=tmp_path)
    zones_path = scenario_path.parent / "exploration" / "zones.json"
    zones = json.loads(zones_path.read_text(encoding="utf-8"))
    zones["zones"][0]["image"] = "assets/missing.png"
    zones["zones"][0]["interaction_pad_positions"] = [[50, 50]]
    zones_path.write_text(
        json.dumps(zones, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    issues = preflight_scenario(
        load_scenario(scenario_path),
        game_asset_root=tmp_path / "assets",
    )

    assert {issue.code for issue in issues} >= {
        "scenario_image_missing",
        "interaction_pad_out_of_bounds",
    }


def test_catalog_lists_only_exploration_scenarios() -> None:
    entries = discover_scenarios("content/scenarios")

    assert [entry.id for entry in entries] == [
        "mechanics_playground",
        "ostatni_transport_00_gildia",
        "village_square_mvp",
    ]
    guild = next(
        entry for entry in entries if entry.id == "ostatni_transport_00_gildia"
    )
    assert guild.continuation_scene_names == (
        "Ostatni transport — Zawalona droga",
    )
    assert guild.scene_count == 2
    village = next(entry for entry in entries if entry.id == "village_square_mvp")
    assert village.continuation_scene_names == ("Opuszczona strażnica",)
    assert village.scene_count == 2


def test_print_map_manifest_resolves_sources_from_manifest_directory(
    tmp_path,
) -> None:
    manifest = tmp_path / "print_maps.json"
    manifest.write_text(
        json.dumps(
            {
                "schema": "dnd_board_game.print_map_manifest",
                "schema_version": 1,
                "output_root": str(tmp_path / "generated"),
                "maps": [
                    {
                        "id": "village",
                        "title": "Wioska",
                        "source": "assets/village.png",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    specs, output_root = load_manifest(manifest)

    assert output_root == tmp_path / "generated"
    assert specs[0].source_path == tmp_path / "assets" / "village.png"


def test_print_map_generator_writes_all_three_outputs(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (120, 180), "white").save(source)
    monkeypatch.setattr(print_maps, "DPI", 30)
    monkeypatch.setattr(print_maps, "MAP_SIZE_PX", (120, 180))
    monkeypatch.setattr(print_maps, "A4_LANDSCAPE_PX", (160, 110))
    monkeypatch.setattr(print_maps, "PAGE_MARGIN_PX", 5)
    monkeypatch.setattr(print_maps, "TILE_OVERLAP_PX", 2)

    written = print_maps.generate_print_maps(
        (PrintMapSpec("test_map", "Mapa testowa", source),),
        tmp_path / "generated",
    )

    assert len(written) == 3
    assert all(path.is_file() for path in written)
