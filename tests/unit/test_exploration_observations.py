from dataclasses import replace

from dnd_board_game.exploration import (
    CheckAggregation,
    CheckParticipants,
    ExplorationObservation,
    ObservationFact,
    resolve_observation,
    match_exploration_observation,
)


def _observation() -> ExplorationObservation:
    return ExplorationObservation(
        id="watch_gate",
        zone_id="gate",
        challenge_id="closed_gate",
        label="Obserwacja bramy",
        description="Zaglądanie przez szczelinę.",
        ability="wisdom",
        skill="perception",
        failure_message="Nie uzyskujesz rozstrzygającej informacji.",
        participants=CheckParticipants.SINGLE_ACTOR,
        aggregation=CheckAggregation.LEAD_RESULT,
        facts=(
            ObservationFact("activity", 10, "Widać ślady ruchu.", "activity_seen"),
            ObservationFact("goblins", 15, "Widać gobliny.", "goblins_seen"),
            ObservationFact("positions", 20, "Widać ich pozycje.", "positions_seen"),
        ),
    )


def test_observation_reveals_every_information_tier_reached_by_total():
    result = resolve_observation(_observation(), 17)

    assert result.success is True
    assert [fact.id for fact in result.reached_facts] == ["activity", "goblins"]
    assert result.message == "Widać ślady ruchu. Widać gobliny."


def test_failed_observation_does_not_claim_that_threat_is_absent():
    result = resolve_observation(_observation(), 9)

    assert result.success is False
    assert result.reached_facts == ()
    assert result.message == "Nie uzyskujesz rozstrzygającej informacji."


def test_observation_intent_matches_natural_action_wording():
    observation = _observation()
    observation = replace(
        observation,
        zone_id="gate",
        challenge_id="closed_gate",
        intent_examples=(
            "zerkam przez szparę w deskach",
            "sprawdzam przez szparę czy nikt tam nie stoi",
        ),
    )

    matched = match_exploration_observation(
        (observation,),
        "najpierw chcę zerknąć przez szparę w deskach, czy nikt tam nie stoi",
        zone_id="gate",
        challenge_id="closed_gate",
    )

    assert matched == observation


def test_observation_intent_does_not_capture_unrelated_gate_action():
    observation = replace(
        _observation(),
        intent_examples=("zaglądam przez szczelinę w bramie",),
    )

    matched = match_exploration_observation(
        (observation,),
        "Przerzucamy linę z hakiem i wspinamy się nad bramę.",
        zone_id="gate",
        challenge_id="closed_gate",
    )

    assert matched is None


def test_observation_intent_does_not_capture_action_using_the_gate_gap():
    observation = replace(
        _observation(),
        intent_examples=(
            "zerkam przez szparę w deskach",
            "sprawdzam przez szparę czy nikt tam nie stoi",
        ),
    )

    matched = match_exploration_observation(
        (observation,),
        "szukam cienkiej deski i staram się zdjąć rygiel przez szparę",
        zone_id="gate",
        challenge_id="closed_gate",
    )

    assert matched is None
