from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    RollModifier,
    RollModifierType,
    SaveDamageOnSuccess,
    SavingThrowRequest,
    resolve_d20_roll,
    resolve_saving_throw_request,
)


def test_saving_throw_request_resolves_with_visible_modifier_breakdown() -> None:
    request = SavingThrowRequest(
        ability="dexterity",
        dc=13,
        source_label="Kamienny podmuch",
        dc_source_label="ST zdolności strażnika",
        damage_on_success=SaveDamageOnSuccess.HALF,
    )
    roll = resolve_d20_roll(
        D20RollInput(
            D20RollRequest(
                modifiers=(
                    RollModifier("Zręczność", 2, RollModifierType.ABILITY),
                    RollModifier("Biegłość", 2, RollModifierType.PROFICIENCY),
                )
            ),
            9,
        )
    )

    result = resolve_saving_throw_request(
        request,
        actor_id="hero",
        actor_name="Bohater",
        roll=roll,
    )

    assert result.success is True
    assert result.total == 13
    assert result.damage_multiplier == 0.5
    assert result.as_payload()["modifier_components"] == [
        {"label": "Zręczność", "value": 2, "modifier_type": "ability"},
        {"label": "Biegłość", "value": 2, "modifier_type": "proficiency"},
    ]
    assert request.as_payload()["success_effect_label"] == "połowa obrażeń"


def test_successful_save_with_none_policy_negates_damage() -> None:
    request = SavingThrowRequest("wisdom", 10, "Efekt", SaveDamageOnSuccess.NONE)
    roll = resolve_d20_roll(D20RollInput(D20RollRequest(), 10))

    result = resolve_saving_throw_request(
        request,
        actor_id="hero",
        actor_name="Bohater",
        roll=roll,
    )

    assert result.success is True
    assert result.damage_multiplier == 0.0
