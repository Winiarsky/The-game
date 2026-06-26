from dnd_board_game.combat import (
    CombatTarget,
    CombatTargetType,
    attack_result_led_feedback,
    attack_targets_led_feedback,
    selected_attack_target_led_feedback,
)
from dnd_board_game.hardware import BoardLedAdapter, LedColor
from dnd_board_game.rules import AttackRollOutcome
from dnd_board_game.world import Coordinate


class FakeConnection:
    def __init__(self):
        self.events = []

    def set_leds(self, positions, rgb_color):
        self.events.append(("set_leds", list(positions), list(rgb_color)))

    def leds_off(self):
        self.events.append(("leds_off",))


def _target(target_id: str, position: Coordinate) -> CombatTarget:
    return CombatTarget(target_id, target_id, position, 13, 10, CombatTargetType.ACTOR)


def test_attack_target_feedback_colors_and_clear_sequence():
    targets = (_target("a", Coordinate(1, 0)), _target("b", Coordinate(0, 1)))
    connection = FakeConnection()
    adapter = BoardLedAdapter(connection)

    adapter.show_feedback(attack_targets_led_feedback(targets))
    adapter.clear()
    adapter.show_feedback(selected_attack_target_led_feedback(targets[0]))
    adapter.clear()

    assert connection.events == [
        ("set_leds", [(0, 1), (1, 0)], list(LedColor.LEGAL_ATTACK_TARGET)),
        ("leds_off",),
        ("set_leds", [(1, 0)], list(LedColor.SELECTED_ATTACK_TARGET)),
        ("leds_off",),
    ]


def test_attack_result_feedback_uses_expected_colors():
    target = _target("goblin", Coordinate(1, 0))

    assert attack_result_led_feedback(target, AttackRollOutcome.HIT).frames[0].color == LedColor.ATTACK_HIT
    assert attack_result_led_feedback(target, AttackRollOutcome.MISS).frames[0].color == LedColor.ATTACK_MISS
    assert attack_result_led_feedback(target, AttackRollOutcome.CRITICAL_HIT).frames[0].color == LedColor.ATTACK_CRITICAL_HIT
