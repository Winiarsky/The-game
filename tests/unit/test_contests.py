import pytest

from dnd_board_game.rules import (
    ContestantRollInput,
    ContestOutcome,
    D20RollInput,
    D20RollRequest,
    RollModifier,
    RollModifierType,
    resolve_contest,
)


def _contestant(actor_id: str, natural_roll: int, modifier: int) -> ContestantRollInput:
    request = D20RollRequest(
        modifiers=(
            RollModifier(
                "Modyfikator testu",
                modifier,
                RollModifierType.ABILITY,
            ),
        )
    )
    return ContestantRollInput(
        actor_id,
        actor_id.title(),
        D20RollInput(request, natural_roll),
    )


def test_contest_returns_initiator_or_defender_winner_from_totals() -> None:
    initiator_wins = resolve_contest(_contestant("hero", 14, 5), _contestant("goblin", 12, 2))
    defender_wins = resolve_contest(_contestant("hero", 5, 5), _contestant("goblin", 12, 2))

    assert initiator_wins.outcome == ContestOutcome.INITIATOR_WINS
    assert initiator_wins.winner_actor_id == "hero"
    assert defender_wins.outcome == ContestOutcome.DEFENDER_WINS
    assert defender_wins.winner_actor_id == "goblin"


def test_tied_contest_has_no_winner_and_preserves_status_quo() -> None:
    result = resolve_contest(_contestant("hero", 10, 4), _contestant("goblin", 12, 2))

    assert result.outcome == ContestOutcome.TIE
    assert result.winner_actor_id is None


def test_actor_cannot_contest_itself() -> None:
    with pytest.raises(ValueError, match="cannot contest itself"):
        resolve_contest(_contestant("hero", 10, 2), _contestant("hero", 12, 1))
