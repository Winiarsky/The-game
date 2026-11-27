"""Model fidelity and domain-wide properties of the Mission 0 balance tool."""
from __future__ import annotations

from dataclasses import replace
import json
import random

import pytest

from dnd_board_game.application.progress_confrontation import build
from dnd_board_game.rules import progress_confrontation as rules
from dnd_board_game.ui.training_arena import training_hero
from scripts.evaluate_mission_zero import POLICIES, simulate


def template(count: int = 3, modifier: int = 0, dc: int = 14) -> rules.Confrontation:
    return rules.Confrontation(tuple(
        rules.Participant(str(index), f"Hero {index}", (
            rules.Approach("repeat", "Repeat", "", "Siła", modifier, dc),
        )) for index in range(count)
    ), social=True)


def test_builder_applies_clue_to_scene_and_option_dcs_without_mutation() -> None:
    scene = dict(kind="object", progress_dc=14, progress_dc_adjustment=-2, approaches=[
        dict(id="search", name="Search", description="", ability="wisdom"),
        dict(id="lock", name="Lock", description="", ability="dexterity", progress_dc=17),
    ])
    before = json.dumps(scene)
    state = build((training_hero("garran"),), scene)
    assert [option.dc for option in state.actor.options] == [12, 15]
    assert json.dumps(scene) == before
    assert not state.social


@pytest.mark.parametrize("modifier", range(-3, 6))
def test_clue_adds_exactly_two_successful_faces_and_preserves_criticals(modifier: int) -> None:
    results = []
    for dc in (14, 12):
        state = rules.choose(rules.begin(template(modifier=modifier, dc=dc)), "repeat")
        results.append([rules.preview(rules.roll(state, die))["delta"] for die in range(1, 21)])
    before, after = results
    assert all(new >= old for old, new in zip(before, after))
    assert before[0] == after[0] == -1
    assert before[-1] == after[-1] == 2
    assert sum(new > old for old, new in zip(before, after)) == 2


def test_simulator_matches_hand_checked_seed_and_reputation_costs() -> None:
    # Seed 0: pairs (13,14), (2,9), (17,16), modifier 0, DC 14.
    ordinary = simulate(template(), 0)
    assert (ordinary.progress, ordinary.outcome, ordinary.tests, ordinary.reputation_spent) == (1, "compromise", 3, 0)
    supported = simulate(template(), 0, policy="best_minimum_reputation_v1")
    assert (supported.progress, supported.outcome, supported.reputation_spent) == (2, "success", 6)
    assert [row["reputation"] for row in supported.trace] == [19, 14, 14]
    assert [row["impact"] for row in supported.trace] == [1, 0, 1]


@pytest.mark.parametrize("count", [3, 4, 5, 6])
@pytest.mark.parametrize("policy", POLICIES)
def test_seeded_runs_terminate_preserve_bounds_and_ignore_global_rng(count: int, policy: str) -> None:
    state = template(count)
    global_rng = random.getstate()
    for seed in range(8):
        run = simulate(state, seed, policy=policy)
        assert -1 <= run.progress <= count and 1 <= run.tests <= count
        assert 0 <= run.reputation_spent <= 20
        assert len({row["actor"] for row in run.trace}) == run.tests
        assert simulate(rules.Confrontation.from_data(json.loads(json.dumps(state.to_data()))), seed, policy=policy) == run
    assert random.getstate() == global_rng


def test_policy_passes_when_all_exclusive_approaches_are_consumed() -> None:
    state = template()
    state = replace(state, participants=tuple(replace(person, options=(
        replace(person.options[0], repeatable=False),
    )) for person in state.participants))
    run = simulate(state, 0)
    assert run.tests == 1 and run.outcome == "failure"
