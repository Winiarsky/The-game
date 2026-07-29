from dnd_board_game.rules import ActiveEffect
from dnd_board_game.ui.exploration_app import _enhance_ability_applies


def test_enhance_ability_applies_only_to_selected_actor_and_ability() -> None:
    effect = ActiveEffect(
        id="enhance:hero:wisdom",
        actor_id="hero",
        kind="ability_check_advantage:wisdom",
        label="Wzmocnienie cechy: Mądrość",
        object_id="spell:enhance_ability",
        value=0,
    )

    assert _enhance_ability_applies("hero", "wisdom", (effect,)) is True
    assert _enhance_ability_applies("hero", "strength", (effect,)) is False
    assert _enhance_ability_applies("ally", "wisdom", (effect,)) is False
