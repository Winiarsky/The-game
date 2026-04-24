from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from prompt_text_catalog import render_prompt_text


def test_render_prompt_text_reads_external_catalog_entry():
    result = render_prompt_text(
        "interaction.loot_drop",
        enemy_name="Bandit Sharpshot",
        position_text="(15, 6)",
        loot_summary="shortbow, monety: 6 sp",
    )

    assert result["title"] == "Loot po Bandit Sharpshot"
    assert "Na polu (15, 6) zostaje loot." in result["summary"]
    assert "shortbow, monety: 6 sp" in result["body_markdown"]
    assert "Jak zebrać loot" in result["details_markdown"]


def test_render_prompt_text_formats_nested_option_entries():
    result = render_prompt_text(
        "setup.hero_setup_place_figure",
        hero_name="Cedric",
        position="(2, 3)",
    )

    assert result["title"] == "Ustaw figurkę: Cedric"
    assert "Cedric" in result["body_markdown"]
    assert "(2, 3)" in result["body_markdown"]
