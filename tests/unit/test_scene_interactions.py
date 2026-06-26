from dnd_board_game.combat import (
    SceneAbilityCheck,
    SceneInteraction,
    SceneObject,
    available_scene_interactions,
    resolve_scene_interaction,
)
from dnd_board_game.rules import RollModifier, RollModifierType
from dnd_board_game.world import Coordinate


def test_interaction_without_check_sets_success_flag():
    interaction = SceneInteraction(
        "open_crate",
        "Otwórz skrzynię",
        success_flag="crate_opened",
        success_message="Skrzynia została otwarta.",
    )

    result = resolve_scene_interaction(interaction)

    assert result.success is True
    assert result.flag_key == "crate_opened"
    assert result.message == "Skrzynia została otwarta."


def test_interaction_with_ability_check_succeeds_on_total_at_least_dc():
    interaction = SceneInteraction(
        "inspect_crate",
        "Zbadaj skrzynię",
        ability_check=SceneAbilityCheck(
            ability="wisdom",
            skill="perception",
            dc=12,
            modifiers=(RollModifier("Biegłość w Percepcji", 2, RollModifierType.PROFICIENCY, "proficiency"),),
        ),
        success_flag="crate_secured",
        failure_flag="crate_trap_missed",
        success_message="Zabezpieczasz skrzynię.",
        failure_message="Nie dostrzegasz mechanizmu.",
    )

    result = resolve_scene_interaction(interaction, natural_roll=10)

    assert result.success is True
    assert result.flag_key == "crate_secured"
    assert result.roll is not None
    assert result.roll.total == 12


def test_interaction_with_ability_check_failure_sets_failure_flag():
    interaction = SceneInteraction(
        "inspect_crate",
        "Zbadaj skrzynię",
        ability_check=SceneAbilityCheck("wisdom", 12),
        success_flag="crate_secured",
        failure_flag="crate_trap_missed",
        failure_message="Nie dostrzegasz niczego podejrzanego.",
    )

    result = resolve_scene_interaction(interaction, natural_roll=5)

    assert result.success is False
    assert result.flag_key == "crate_trap_missed"
    assert result.message == "Nie dostrzegasz niczego podejrzanego."


def test_scene_object_without_explicit_interactions_gets_default_interaction():
    scene_object = SceneObject("crate", "Skrzynia", (Coordinate(1, 0),), "Zbadaj")

    interactions = available_scene_interactions(scene_object)

    assert len(interactions) == 1
    assert interactions[0].id == "interact_crate"
    assert interactions[0].label == "Zbadaj"
