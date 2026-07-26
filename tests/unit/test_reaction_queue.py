import pytest

from dnd_board_game.combat import (
    ReactionKind,
    ReactionOption,
    ReactionStage,
    advance_reaction_window,
    open_reaction_window,
    record_current_reaction_attack,
    start_current_reaction,
)


def _option(
    option_id: str,
    reactor_id: str,
    *,
    kind: ReactionKind = ReactionKind.OPPORTUNITY_ATTACK,
) -> ReactionOption:
    return ReactionOption(
        id=option_id,
        kind=kind,
        reactor_actor_id=reactor_id,
        target_actor_id="enemy",
        trigger_event="enemy_moves",
    )


def test_reaction_window_preserves_declared_order_and_roll_stage() -> None:
    window = open_reaction_window(
        interrupted_actor_id="enemy",
        trigger_event="enemy_moves",
        options=(
            _option("ready:hero", "hero", kind=ReactionKind.READY_ATTACK),
            _option("opportunity:rogue", "rogue"),
        ),
    )
    assert window is not None
    assert window.current_option.id == "ready:hero"

    started = start_current_reaction(window)
    rolled = record_current_reaction_attack(
        started,
        natural_roll=20,
        natural_rolls=(20,),
        total=25,
        hit=True,
        critical=True,
    )
    assert rolled.stage == ReactionStage.DAMAGE_ROLL
    assert rolled.critical

    advanced = advance_reaction_window(rolled)
    assert advanced is not None
    assert advanced.current_option.id == "opportunity:rogue"
    assert advanced.stage == ReactionStage.CHOICE
    assert advanced.natural_roll is None


def test_reaction_window_skips_reactors_without_an_available_reaction() -> None:
    window = open_reaction_window(
        interrupted_actor_id="enemy",
        trigger_event="enemy_moves",
        options=(
            _option("ready:hero", "hero", kind=ReactionKind.READY_ATTACK),
            _option("opportunity:hero", "hero"),
            _option("opportunity:rogue", "rogue"),
        ),
    )
    assert window is not None

    advanced = advance_reaction_window(
        window,
        available_reactor_ids={"rogue"},
    )

    assert advanced is not None
    assert advanced.current_option.id == "opportunity:rogue"


def test_reaction_window_finishes_after_last_option() -> None:
    window = open_reaction_window(
        interrupted_actor_id="enemy",
        trigger_event="enemy_moves",
        options=(_option("opportunity:hero", "hero"),),
    )
    assert window is not None

    assert advance_reaction_window(window) is None


def test_reaction_window_rejects_duplicate_option_ids() -> None:
    with pytest.raises(ValueError, match="unique"):
        open_reaction_window(
            interrupted_actor_id="enemy",
            trigger_event="enemy_moves",
            options=(
                _option("same", "hero"),
                _option("same", "rogue"),
            ),
        )
