from dnd_board_game.actors import AbilityScores
from dnd_board_game.character_creation import (
    CLASS_CHOICE_GROUP_HELP,
    FIGHTING_STYLE_HELP,
    POINT_BUY_BUDGET,
    POINT_BUY_COSTS,
    SKILL_CHOICE_HELP,
    audit_level_one_class_feature_help,
    load_character_catalog,
    summarize_point_buy,
)


def test_point_buy_uses_2014_cost_table_and_full_budget():
    assert POINT_BUY_BUDGET == 27
    assert POINT_BUY_COSTS == {
        8: 0,
        9: 1,
        10: 2,
        11: 3,
        12: 4,
        13: 5,
        14: 7,
        15: 9,
    }

    standard_array = summarize_point_buy(AbilityScores(15, 14, 13, 12, 10, 8))
    three_high_scores = summarize_point_buy(AbilityScores(15, 15, 15, 8, 8, 8))

    assert standard_array.complete
    assert standard_array.spent == 27
    assert three_high_scores.complete


def test_point_buy_reports_unspent_budget_and_out_of_range_scores():
    unspent = summarize_point_buy(AbilityScores(13, 13, 13, 12, 12, 11))
    out_of_range = summarize_point_buy(AbilityScores(16, 8, 8, 8, 8, 8))

    assert unspent.complete is False
    assert unspent.remaining == 1
    assert out_of_range.scores_in_range is False
    assert out_of_range.complete is False


def test_every_level_one_class_feature_has_help_and_runtime_contract():
    catalog = load_character_catalog("content/character_creation/catalog.json")

    coverage = audit_level_one_class_feature_help(catalog)

    assert coverage.complete
    assert len(coverage.feature_ids) == 21


def test_every_class_skill_style_and_level_one_group_has_player_guidance():
    catalog = load_character_catalog("content/character_creation/catalog.json")
    skill_ids = {
        skill_id
        for character_class in catalog.classes
        for skill_id in character_class.skill_choices
    }
    style_ids = {
        style_id
        for character_class in catalog.classes
        for style_id in character_class.fighting_style_choices
    }
    group_ids = {
        group.id
        for character_class in catalog.classes
        for group in character_class.choice_groups
        if group.level == 1
    }

    assert skill_ids == SKILL_CHOICE_HELP.keys()
    assert style_ids == FIGHTING_STYLE_HELP.keys()
    assert group_ids == CLASS_CHOICE_GROUP_HELP.keys()
