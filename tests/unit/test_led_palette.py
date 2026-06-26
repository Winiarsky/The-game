from dnd_board_game.hardware import DEFAULT_COLORS, LedColor, LedRole


def test_default_role_colors_use_semantic_palette():
    assert DEFAULT_COLORS[LedRole.ACTIVE_ACTOR] == LedColor.ACTIVE_ACTOR
    assert DEFAULT_COLORS[LedRole.MOVEMENT_RANGE] == LedColor.MOVEMENT_RANGE
    assert DEFAULT_COLORS[LedRole.SELECTED_PATH] == LedColor.PLAYER_MOVEMENT_PATH
    assert DEFAULT_COLORS[LedRole.DESTINATION] == LedColor.MOVEMENT_DESTINATION
    assert DEFAULT_COLORS[LedRole.ALLY] == LedColor.ALLY
    assert DEFAULT_COLORS[LedRole.ENEMY] == LedColor.ENEMY


def test_combat_palette_documents_expected_board_meaning():
    assert LedColor.LEGAL_ATTACK_TARGET == (0, 80, 220)
    assert LedColor.INTERACTIVE_OBJECT == (0, 255, 120)
    assert LedColor.MULTI_OPTION_TILE == (180, 120, 40)
    assert LedColor.ENEMY_MOVEMENT_PATH == (220, 0, 0)
    assert LedColor.ENEMY_MOVEMENT_DESTINATION == (255, 120, 0)
