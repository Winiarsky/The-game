from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.combat import (
    ActorSetupEntry,
    EncounterSetup,
    EnvironmentSetupEntry,
    EnvironmentSetupType,
    SetupVisibility,
    build_setup_steps,
)
from dnd_board_game.world import Coordinate


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


def test_encounter_setup_generates_polish_start_and_visible_actor_steps():
    hero = _actor("hero", "Bohater", Faction.ALLY, Coordinate(0, 0))
    enemy = _actor("goblin", "Goblin", Faction.ENEMY, Coordinate(4, 2))
    setup = EncounterSetup(
        name="Zasadzka goblinów",
        actors=(
            ActorSetupEntry(hero, "bohater", Coordinate(0, 0)),
            ActorSetupEntry(enemy, "przeciwnik", Coordinate(4, 2)),
        ),
    )

    steps = build_setup_steps(setup)
    messages = [step.message for step in steps]

    assert "Rozpoczyna się walka: Zasadzka goblinów" in messages[0]
    assert any("Ustaw bohaterów: Bohater" in message for message in messages)
    assert any("Ustaw jawnych przeciwników i NPC: Goblin" in message for message in messages)


def test_encounter_setup_batches_visible_environment_and_hides_secret_entries():
    hero = _actor("hero", "Bohater", Faction.ALLY, Coordinate(0, 0))
    hidden_enemy = _actor("ambusher", "Ukryty łucznik", Faction.ENEMY, Coordinate(5, 5))
    setup = EncounterSetup(
        name="Sala prób",
        actors=(
            ActorSetupEntry(hero, "bohater", Coordinate(0, 0)),
            ActorSetupEntry(hidden_enemy, "przeciwnik", Coordinate(5, 5), SetupVisibility.HIDDEN),
        ),
        environment=(
            EnvironmentSetupEntry(
                "rubble",
                "Rumowisko",
                EnvironmentSetupType.DIFFICULT_TERRAIN,
                (Coordinate(2, 1),),
                mechanics=("Każde 5 ft ruchu kosztuje 10 ft.",),
            ),
            EnvironmentSetupEntry("crate", "Skrzynia", EnvironmentSetupType.CONTAINER, (Coordinate(3, 1),)),
            EnvironmentSetupEntry(
                "secret",
                "Ukryta pułapka",
                EnvironmentSetupType.INTERACTABLE,
                (Coordinate(4, 4),),
                SetupVisibility.HIDDEN,
            ),
            EnvironmentSetupEntry(
                "later",
                "Warunkowy NPC",
                EnvironmentSetupType.NPC,
                (Coordinate(6, 6),),
                SetupVisibility.CONDITIONAL,
            ),
        ),
    )

    messages = "\n".join(step.message for step in build_setup_steps(setup))

    assert "trudny teren: Rumowisko" in messages
    assert "skrzynie i pojemniki: Skrzynia" in messages
    assert "Ukryty łucznik" not in messages
    assert "Ukryta pułapka" not in messages
    assert "Warunkowy NPC" not in messages

    difficult_step = next(
        step for step in build_setup_steps(setup) if step.label == "trudny teren"
    )
    assert difficult_step.mechanics == ("Każde 5 ft ruchu kosztuje 10 ft.",)


def test_encounter_setup_deduplicates_mechanics_in_a_group() -> None:
    shared_rule = "Figurka stojąca na tym polu otrzymuje +2 do KP."
    setup = EncounterSetup(
        name="Pola obronne",
        environment=(
            EnvironmentSetupEntry(
                "tree",
                "Zwalony pień",
                EnvironmentSetupType.COVER,
                (Coordinate(1, 1),),
                mechanics=(shared_rule,),
            ),
            EnvironmentSetupEntry(
                "crates",
                "Skrzynie",
                EnvironmentSetupType.COVER,
                (Coordinate(2, 1),),
                mechanics=(shared_rule,),
            ),
        ),
    )

    cover_step = next(
        step for step in build_setup_steps(setup) if step.label == "osłony"
    )

    assert cover_step.mechanics == (shared_rule,)


def test_encounter_setup_handles_actor_without_start_position():
    hero = _actor("hero", "Bohater", Faction.ALLY, Coordinate(0, 0))
    setup = EncounterSetup(
        name="Bez pozycji",
        actors=(ActorSetupEntry(hero, "bohater", None),),
    )

    messages = [step.message for step in build_setup_steps(setup)]

    assert any(message == "Ustaw bohaterów: Bohater." for message in messages)
