import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import player_ui.app as player_ui_app_module  # noqa: E402
from GameObjects.interactions_mixin.prompt_utils import _parse_roll_details  # noqa: E402
from player_prompting import PromptDirector  # noqa: E402
from ui_client import UIClient  # noqa: E402


def test_ui_client_normalize_roll_answer_preserves_stack_fields():
    payload = {
        "roll": 15,
        "raw_roll": 12,
        "natural_mode": "nat20",
        "modifier_delta": 3,
        "computed_total": 21,
        "roll_stack_values": [{"id": "d20", "value": 12, "base_value": 0}],
    }
    normalized = UIClient._normalize_roll_answer(payload)
    assert normalized["roll"] == 15
    assert normalized["raw_roll"] == 12
    assert normalized["natural_mode"] == "nat20"
    assert normalized["modifier_delta"] == 3
    assert normalized["computed_total"] == 21
    assert isinstance(normalized.get("roll_stack_values"), list)


def test_parse_roll_details_uses_raw_roll_for_natural_inference():
    details = _parse_roll_details(
        {"roll": 27, "raw_roll": 20, "modifier_delta": 7},
        infer_natural_from_roll=True,
    )
    assert details["roll"] == 27
    assert details["raw_roll"] == 20
    assert details["natural_shift"] == 1
    assert details["natural_mode"] == "nat20"
    assert details["modifier_delta"] == 7


def test_prompt_api_roundtrip_keeps_roll_stack_payload():
    app = player_ui_app_module.app
    prompt_director = PromptDirector(session_id=player_ui_app_module.current_session_id)
    prompt_director.set_publisher(player_ui_app_module._publish)
    original_prompt_director = player_ui_app_module.prompt_director
    player_ui_app_module.prompt_director = prompt_director

    roll_stack = {
        "auto_total_modifier": 9,
        "components": [
            {
                "id": "proficiency",
                "label": "Biegłość",
                "value": 5,
                "description": "Poziom +2",
                "editable": True,
            }
        ],
    }
    try:
        with app.test_client() as client:
            create = client.post(
                "/api/prompts",
                json={
                    "prompt": "Test rzutu",
                    "kind": "roll",
                    "layout": "test",
                    "roll_stack": roll_stack,
                },
            )
            assert create.status_code == 200
            prompt_id = create.get_json()["id"]

            fetched = client.get(f"/api/prompts/{prompt_id}")
            assert fetched.status_code == 200
            payload = fetched.get_json()
            assert payload["roll_stack"]["auto_total_modifier"] == 9
            assert payload["roll_stack"]["components"][0]["label"] == "Biegłość"
            assert payload["communication"]["channel"] == "prompt"
            assert payload["communication"]["blocking"] is True
            assert payload["communication"]["body_markdown"] == "Test rzutu"
    finally:
        player_ui_app_module.prompt_director = original_prompt_director
