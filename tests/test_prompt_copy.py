from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from prompt_copy import merge_menu_prompt, resolve_ui_prompt_copy


def test_merge_menu_prompt_overrides_title_subtitle_and_options():
    title, subtitle, options = merge_menu_prompt(
        "setup.hero_setup_next",
        title="Fallback",
        subtitle="Fallback subtitle",
        options=[
            {"id": "__start_game__", "label": "X", "desc": "Y"},
            {"id": "__add_hero__", "label": "A", "desc": "B"},
        ],
    )

    assert title == "Setup bohaterów"
    assert "Enter: graj" in subtitle
    assert options[0]["label"] == "Graj"
    assert "Rozpocznij grę" in options[0]["desc"]


def test_resolve_ui_prompt_copy_uses_source_based_prompt_id():
    resolved = resolve_ui_prompt_copy(
        kind="choice",
        source="intent",
        title="Fallback",
        subtitle="Fallback subtitle",
    )

    assert resolved["prompt_id"] == "ui.choice.intent"
    assert resolved["title"] == "Akcje"
    assert "8/2 nawigacja" in str(resolved["subtitle"] or "")
