from dataclasses import replace

import pytest

from dnd_board_game.application.exploration_action_sources import (
    ExplorationActionSourceKind,
    action_sources_for_goal,
    selected_action_source,
)
from dnd_board_game.ui.exploration_app import ExplorationUiSession


def test_shared_source_registry_filters_resources_items_and_spells(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="action_source_registry_test",
        observation_dir=tmp_path,
    )
    cleric = next(
        actor for actor in session.exploration.actors if str(actor.id) == "cleric"
    )
    spell = replace(
        cleric.spells[0],
        exploration_tags=("damage_object",),
        exploration_target_tags=("object",),
        exploration_consequence_tags=("loud",),
    )
    cleric = replace(
        cleric,
        spells=(spell, *cleric.spells[1:]),
        spell_access=(
            replace(cleric.spell_access[0], casting_ability="wisdom"),
            *cleric.spell_access[1:],
        ),
    )

    sources = action_sources_for_goal(
        session.state,
        (*session.exploration.actors[:2], cleric),
        ("damage_object",),
    )

    spell_source = next(
        source
        for source in sources
        if source.id == f"actor:cleric:spell:{spell.id}"
    )
    assert spell_source.kind == ExplorationActionSourceKind.SPELL
    assert spell_source.available is True
    assert spell_source.target_tags == ("object",)
    assert spell_source.consequence_tags == ("loud",)
    assert spell_source.check_ability == "wisdom"
    assert any(source.kind == ExplorationActionSourceKind.WEAPON for source in sources)


def test_actor_owned_source_requires_its_owner_to_lead(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="action_source_owner_test",
        observation_dir=tmp_path,
    )

    with pytest.raises(ValueError, match="musi prowadzić"):
        selected_action_source(
            session.state,
            session.exploration.actors,
            ("unlock",),
            "actor:rogue:item:thieves_tools",
            lead_actor_id="hero",
            required=True,
        )

    selected = selected_action_source(
        session.state,
        session.exploration.actors,
        ("unlock",),
        "actor:rogue:item:thieves_tools",
        lead_actor_id="rogue",
        required=True,
    )

    assert selected is not None
    assert selected.reference_id == "thieves_tools"


def test_required_source_cannot_be_omitted(tmp_path):
    session = ExplorationUiSession(
        "content/scenarios/abandoned_watchtower.json",
        session_id="required_action_source_test",
        observation_dir=tmp_path,
    )

    with pytest.raises(ValueError, match="wymaga wybrania"):
        selected_action_source(
            session.state,
            session.exploration.actors,
            ("climbing_aid",),
            None,
            lead_actor_id="hero",
            required=True,
        )
