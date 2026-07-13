import pytest

from dnd_board_game.actors import (
    PreparableSpell,
    SpellPreparationProfile,
    prepare_spells,
    spell_is_prepared,
)


def _profile() -> SpellPreparationProfile:
    return SpellPreparationProfile(
        source_label="lista próbna",
        preparation_limit=2,
        available_spells=(
            PreparableSpell("healing_word", "Słowo leczenia", 1),
            PreparableSpell("bless", "Błogosławieństwo", 1),
            PreparableSpell("restoration", "Pomniejsze przywrócenie", 2),
            PreparableSpell("shield", "Tarcza wiary", 1),
        ),
        prepared_spell_ids=("healing_word",),
        always_prepared_spell_ids=("bless",),
    )


def test_prepare_spells_confirms_selection_without_counting_always_prepared() -> None:
    prepared = prepare_spells(_profile(), ("healing_word", "restoration"))

    assert prepared.confirmed is True
    assert prepared.prepared_spell_ids == ("healing_word", "restoration")
    assert spell_is_prepared(prepared, "bless", casting_kind="leveled") is True


def test_prepare_spells_rejects_unknown_duplicate_and_over_limit_selection() -> None:
    with pytest.raises(ValueError, match="not in the preparation pool"):
        prepare_spells(_profile(), ("unknown",))
    with pytest.raises(ValueError, match="non-empty and unique"):
        prepare_spells(_profile(), ("healing_word", "healing_word"))
    with pytest.raises(ValueError, match="exceeds"):
        prepare_spells(_profile(), ("healing_word", "restoration", "shield"))
    with pytest.raises(ValueError, match="Exactly 2"):
        prepare_spells(_profile(), ("healing_word",))


def test_cantrips_do_not_require_preparation_and_leveled_spells_do() -> None:
    profile = _profile()

    assert spell_is_prepared(profile, "sacred_flame", casting_kind="cantrip") is True
    assert spell_is_prepared(profile, "restoration", casting_kind="leveled") is False
    assert spell_is_prepared(profile, "healing_word", casting_kind="leveled") is True


def test_profile_payload_keeps_always_prepared_spells_visible_outside_limit() -> None:
    payload = _profile().as_payload()

    assert payload["selected_count"] == 1
    bless = next(spell for spell in payload["spells"] if spell["id"] == "bless")
    assert bless["prepared"] is True
    assert bless["always_prepared"] is True
