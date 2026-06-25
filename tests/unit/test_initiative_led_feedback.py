from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.combat import build_enemy_initiative_prompt, build_player_initiative_prompts, initiative_prompt_led_feedback
from dnd_board_game.hardware import BoardLedAdapter, LedRole
from dnd_board_game.world import Coordinate


class FakeConnection:
    def __init__(self):
        self.events = []

    def set_leds(self, positions, rgb_color):
        self.events.append(("set_leds", list(positions), list(rgb_color)))

    def leds_off(self):
        self.events.append(("leds_off",))


def _actor(actor_id: str, name: str, faction: Faction, position: Coordinate) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=name,
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=position,
        faction=faction,
    )


def test_initiative_prompt_led_feedback_marks_only_current_actor_and_can_clear_sequence():
    hero = _actor("hero", "Bohater", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("enemy", "Goblin", Faction.ENEMY, Coordinate(4, 2))
    hero_prompt = build_player_initiative_prompts((hero,))[0]
    enemy_prompt = build_enemy_initiative_prompt(enemy)
    connection = FakeConnection()
    adapter = BoardLedAdapter(connection)

    hero_feedback = initiative_prompt_led_feedback(hero_prompt)
    enemy_feedback = initiative_prompt_led_feedback(enemy_prompt)
    adapter.show_feedback(hero_feedback)
    adapter.clear()
    adapter.show_feedback(enemy_feedback)
    adapter.clear()

    assert hero_feedback.frames[0].role == LedRole.ACTIVE_ACTOR
    assert hero_feedback.frames[0].positions == (Coordinate(0, 0),)
    assert enemy_feedback.frames[0].positions == (Coordinate(4, 2),)
    assert connection.events == [
        ("set_leds", [(0, 0)], [255, 255, 255]),
        ("leds_off",),
        ("set_leds", [(4, 2)], [255, 255, 255]),
        ("leds_off",),
    ]
