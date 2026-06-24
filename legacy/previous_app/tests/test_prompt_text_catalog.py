from pathlib import Path
import json
import re
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from prompt_text_catalog import render_prompt_text


PROMPT_TEXTS_DIR = PROJECT_ROOT / "prompt_texts" / "pl"
PLACEHOLDER_RE = re.compile(r"\{([^{}]+)\}")


def _iter_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _iter_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _iter_strings(nested)


def test_render_prompt_text_reads_external_catalog_entry():
    result = render_prompt_text(
        "interaction.loot_drop",
        enemy_name="Bandit Sharpshot",
        position_text="(15, 6)",
        loot_summary="shortbow, monety: 6 sp",
    )

    assert result["title"] == "Łup po Bandit Sharpshot"
    assert "Na polu (15, 6) zostaje łup." in result["summary"]
    assert "shortbow, monety: 6 sp" in result["body_markdown"]
    assert "Jak zebrać łup" in result["details_markdown"]


def test_render_prompt_text_formats_nested_option_entries():
    result = render_prompt_text(
        "setup.hero_setup_place_figure",
        hero_name="Cedric",
        position="(2, 3)",
    )

    assert result["title"] == "Ustaw figurkę: Cedric"
    assert "Cedric" in result["body_markdown"]
    assert "(2, 3)" in result["body_markdown"]


def test_player_facing_action_prompts_expose_guidance_metadata():
    intent = render_prompt_text("ui.choice.intent")
    assert intent["cta"] == "Wybierz akcję i potwierdź."
    assert "Po wyborze akcji" in intent["next_hint"]
    assert "Sterowanie" in intent["details_markdown"]

    setup = render_prompt_text(
        "setup.hero_setup_select_position",
        hero_name="Cedric",
    )
    assert "Kliknij pole startowe" in setup["cta"]
    assert "ustawisz figurkę" in setup["next_hint"]


def test_prompt_catalog_player_facing_text_has_no_unrendered_placeholders_without_context():
    allowed_template_fields = {
        "actor_name",
        "alternative_suffix",
        "body",
        "confirmation_suffix",
        "damage_breakdown",
        "damage_total",
        "damage_type_line",
        "defeat_details",
        "destination_list",
        "dying_line",
        "enemy_name",
        "hero_name",
        "hp_damage",
        "hp_summary",
        "legend_block",
        "loot_line",
        "loot_list",
        "loot_summary",
        "position",
        "position_text",
        "prompt_long",
        "range_suffix",
        "recovery_message_block",
        "remove_line",
        "source_label",
        "stable_line",
        "status_line",
        "state_summary",
        "subject",
        "target_name",
        "threshold",
        "title",
        "total_wounds_line",
        "unconscious_line",
        "wounded_line",
    }
    for path in sorted(PROMPT_TEXTS_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for prompt_id, entry in payload.items():
            rendered = render_prompt_text(prompt_id)
            placeholders = {
                match.group(1)
                for text in _iter_strings(rendered)
                for match in PLACEHOLDER_RE.finditer(text)
            }
            assert placeholders <= allowed_template_fields, prompt_id


def test_choice_option_descriptions_are_action_oriented():
    prompt_ids = ("turns.intent_options", "setup.hero_setup_next", "setup.hero_select_menu")
    action_words = (
        "dobierz",
        "dodaj",
        "kliknij",
        "podejrzyj",
        "przejdź",
        "przesuń",
        "rozpocznij",
        "sprawdź",
        "stwórz",
        "uruchamia",
        "uruchom",
        "użyj",
        "wybierz",
        "wykonaj",
        "wskaż",
        "zakończ",
    )
    for prompt_id in prompt_ids:
        rendered = render_prompt_text(prompt_id)
        for option_key, option in rendered.get("options", {}).items():
            desc = str(option.get("desc") or "").strip().lower()
            assert desc, f"{prompt_id}.{option_key} lacks desc"
            assert any(word in desc for word in action_words), f"{prompt_id}.{option_key}: {desc}"


def test_player_facing_glossary_avoids_raw_technical_terms():
    blocked_terms = (
        ("prompt", {"prompt_long"}),
        ("pipeline", set()),
        ("outcome", set()),
        ("loot", {"loot_summary", "loot_list", "loot_line", "Party Stash"}),
        ("seek", {"Scent/Seek"}),
    )
    for path in sorted(PROMPT_TEXTS_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for prompt_id in payload:
            rendered = render_prompt_text(prompt_id)
            for text in _iter_strings(rendered):
                lowered = text.lower()
                for term, exceptions in blocked_terms:
                    if any(exception.lower() in lowered for exception in exceptions):
                        continue
                    assert term not in lowered, f"{prompt_id}: {term!r} in {text!r}"


def test_guided_action_prompts_keep_short_summaries_and_cta_next_hint():
    guided_prompt_ids = (
        "events.default_prompt_body.info",
        "events.default_prompt_body.choice",
        "turns.active_hero_board_scan",
        "turns.intent_menu",
        "ui.choice.intent",
        "setup.hero_setup_select_position",
        "setup.hero_setup_place_figure",
        "interaction.loot_pickup_prompt",
        "interaction.seek_preview",
        "combat.player_wounds",
        "combat.damage_applied_summary",
        "ui.roll.game",
        "ui.choice.attack",
        "ui.info.reaction:opportunity_attack_enemy_result",
    )
    for prompt_id in guided_prompt_ids:
        rendered = render_prompt_text(prompt_id)
        summary = str(rendered.get("summary") or "").strip()
        if summary:
            assert len(summary) <= 160, prompt_id
        assert str(rendered.get("cta") or "").strip(), f"{prompt_id} lacks cta"
        assert str(rendered.get("next_hint") or "").strip(), f"{prompt_id} lacks next_hint"
