from pathlib import Path

import pytest

from dnd_board_game.llm.content_config import load_llm_condition_catalog, load_llm_effect_catalog


def test_load_llm_effect_catalog_contains_known_primitives():
    catalog = load_llm_effect_catalog()

    assert {"set_flag", "grant_resource", "unlock_option", "reveal_point", "add_noise"}.issubset(catalog.ids)
    assert catalog.definition("grant_resource").parameters == {"resource_id": "string"}


def test_load_llm_condition_catalog_contains_known_primitives():
    catalog = load_llm_condition_catalog()

    assert {"flag_equals", "has_resource", "point_revealed", "challenge_completed"}.issubset(catalog.ids)
    assert catalog.definition("challenge_noise_at_least").parameters == {"challenge_id": "string", "value": "integer"}


def test_llm_primitive_catalog_rejects_unknown_parameter_type(tmp_path):
    path = tmp_path / "bad_effect_catalog.json"
    path.write_text(
        """
        {
          "version": 1,
          "effects": {
            "bad": {
              "label": "Bad",
              "description": "Bad primitive.",
              "parameters": {"value": "dragon"}
            }
          }
        }
        """,
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown type"):
        load_llm_effect_catalog.__wrapped__(Path(path))
