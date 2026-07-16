import pytest

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    Faction,
    ProficiencyProfile,
    ability_check_roll_modifiers,
    saving_throw_modifier,
    saving_throw_roll_modifiers,
    skill_roll_modifiers,
)
from dnd_board_game.combat import (
    AttackSource,
    AttackSourceType,
    attack_source_for_actor,
    resolve_spell_save,
)
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    RollModifierType,
    build_modifier_breakdown,
    resolve_d20_roll,
)
from dnd_board_game.world import Coordinate


def _actor(*, proficiencies: ProficiencyProfile = ProficiencyProfile()) -> Actor:
    return Actor(
        id=ActorId("hero"),
        name="Bohater",
        ac=14,
        hp=20,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        ability_scores=AbilityScores(dexterity=16, constitution=14, wisdom=12),
        proficiency_bonus=3,
        proficiencies=proficiencies,
    )


def test_profile_validates_saves_and_expertise() -> None:
    with pytest.raises(ValueError, match="Unknown saving throw"):
        ProficiencyProfile(saving_throws=("luck",))
    with pytest.raises(ValueError, match="requires proficiency"):
        ProficiencyProfile(expertise=("stealth",))


def test_saving_throw_builds_separate_ability_and_proficiency_modifiers() -> None:
    actor = _actor(proficiencies=ProficiencyProfile(saving_throws=("constitution",)))

    modifiers = saving_throw_roll_modifiers(actor, "constitution")
    roll = resolve_d20_roll(D20RollInput(D20RollRequest(modifiers=modifiers), 10))

    assert saving_throw_modifier(actor, "constitution") == 5
    assert [(item.label, item.value, item.modifier_type) for item in modifiers] == [
        ("Kondycja", 2, RollModifierType.ABILITY),
        ("Biegłość", 3, RollModifierType.PROFICIENCY),
    ]
    assert roll.total == 15


def test_nonproficient_save_only_uses_ability_modifier() -> None:
    actor = _actor()

    assert saving_throw_modifier(actor, "constitution") == 2
    assert len(saving_throw_roll_modifiers(actor, "constitution")) == 1


def test_spell_save_payload_exposes_modifier_components() -> None:
    actor = _actor(proficiencies=ProficiencyProfile(saving_throws=("dexterity",)))

    result = resolve_spell_save(
        actor,
        ability="dexterity",
        dc=15,
        natural_roll=9,
    )

    assert result.modifier == 6
    assert result.total == 15
    assert result.success
    assert result.as_payload()["modifier_components"] == [
        {"label": "Zręczność", "value": 3, "modifier_type": "ability"},
        {"label": "Biegłość", "value": 3, "modifier_type": "proficiency"},
    ]


def test_skill_expertise_uses_one_double_proficiency_component() -> None:
    actor = _actor(
        proficiencies=ProficiencyProfile(
            skills=("stealth",),
            expertise=("stealth",),
        )
    )

    modifiers = skill_roll_modifiers(actor, "stealth")

    assert [(item.label, item.value) for item in modifiers] == [
        ("Zręczność", 3),
        ("Expertise", 6),
    ]


def test_skill_check_can_use_scenario_selected_alternate_ability() -> None:
    actor = _actor(proficiencies=ProficiencyProfile(skills=("intimidation",)))

    modifiers = skill_roll_modifiers(actor, "intimidation", ability="constitution")

    assert [(item.label, item.value) for item in modifiers] == [
        ("Kondycja", 2),
        ("Biegłość", 3),
    ]


def test_transferred_weapon_source_is_rebound_to_current_wielder() -> None:
    source = AttackSource(
        "Kusza",
        AttackSourceType.WEAPON,
        80,
        D20RollRequest(),
        id="crossbow_shot",
        ability="dexterity",
        source_item_id="found_crossbow",
        proficiency_id="crossbow",
    )
    proficient = _actor(proficiencies=ProficiencyProfile(weapons=("crossbow",)))
    untrained = _actor()

    proficient_source = attack_source_for_actor(source, proficient)
    untrained_source = attack_source_for_actor(source, untrained)

    assert [(item.label, item.value) for item in proficient_source.attack_roll_request.modifiers] == [
        ("Zręczność", 3),
        ("Biegłość", 3),
    ]
    assert [(item.label, item.value) for item in untrained_source.attack_roll_request.modifiers] == [
        ("Zręczność", 3),
    ]


def test_tool_proficiency_applies_to_ability_check() -> None:
    actor = _actor(proficiencies=ProficiencyProfile(tools=("thieves_tools",)))

    modifiers = ability_check_roll_modifiers(
        actor,
        "dexterity",
        tool="thieves_tools",
    )

    assert [(item.label, item.value) for item in modifiers] == [
        ("Zręczność", 3),
        ("Biegłość: thieves_tools", 3),
    ]


def test_skill_and_tool_proficiency_do_not_stack_twice() -> None:
    actor = _actor(
        proficiencies=ProficiencyProfile(
            skills=("sleight_of_hand",),
            tools=("thieves_tools",),
        )
    )

    breakdown = build_modifier_breakdown(
        ability_check_roll_modifiers(
            actor,
            "dexterity",
            skill="sleight_of_hand",
            tool="thieves_tools",
        )
    )

    assert breakdown.modifier_total == 6
    assert len(breakdown.active_modifiers) == 2
    assert len(breakdown.ignored_modifiers) == 1


def test_ability_check_accepts_scenario_local_skill_with_explicit_ability() -> None:
    actor = _actor()

    modifiers = ability_check_roll_modifiers(actor, "intelligence", skill="crafting")

    assert build_modifier_breakdown(modifiers).modifier_total == 0
