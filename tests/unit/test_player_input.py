import pytest

from dnd_board_game.actions import PlayerIntentHint, parse_player_input, slash_commands_payload


def test_plain_player_input_keeps_automatic_intent_detection():
    parsed = parse_player_input("  Przyglądam się bramie.  ")

    assert parsed.content == "Przyglądam się bramie."
    assert parsed.command is None
    assert parsed.intent_hint is None


def test_slash_command_is_parsed_as_explicit_intent_hint():
    parsed = parse_player_input("/zbuduj prowizoryczną drabinę z gałęzi")

    assert parsed.raw_text == "/zbuduj prowizoryczną drabinę z gałęzi"
    assert parsed.content == "prowizoryczną drabinę z gałęzi"
    assert parsed.command is not None
    assert parsed.command.name == "zbuduj"
    assert parsed.intent_hint == PlayerIntentHint.BUILD


def test_slash_command_requires_content_except_for_help():
    with pytest.raises(ValueError, match="dopisz treść"):
        parse_player_input("/pytaj")

    assert parse_player_input("/pomoc").intent_hint == PlayerIntentHint.HELP


def test_take_command_is_an_explicit_collection_intent():
    parsed = parse_player_input("/wez drewnianą deskę")

    assert parsed.content == "drewnianą deskę"
    assert parsed.intent_hint == PlayerIntentHint.TAKE


def test_unknown_slash_command_is_rejected_with_help_hint():
    with pytest.raises(ValueError, match="/pomoc"):
        parse_player_input("/wywaz bramę")


def test_slash_command_payload_has_unique_names_for_ui_filtering():
    payload = slash_commands_payload()

    assert [command["name"] for command in payload] == [
        "pytaj",
        "szukaj",
        "zbuduj",
        "uzyj",
        "wez",
        "akcja",
        "pomoc",
    ]
    assert len({command["name"] for command in payload}) == len(payload)


def test_removed_hint_command_is_not_kept_as_an_alias():
    with pytest.raises(ValueError, match="Nieznana komenda /podpowiedz"):
        parse_player_input("/podpowiedz czy bramę można wyważyć?")
