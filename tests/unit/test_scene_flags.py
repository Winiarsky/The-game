from dnd_board_game.combat import SceneFlags, scene_flag, set_scene_flag


def test_scene_flags_set_and_read_value():
    flags = set_scene_flag(SceneFlags(), "crate_secured", True)

    assert scene_flag(flags, "crate_secured") is True


def test_scene_flags_overwrite_deterministically():
    flags = set_scene_flag(SceneFlags(), "crate_secured", False)
    updated = set_scene_flag(flags, "crate_secured", True)

    assert scene_flag(updated, "crate_secured") is True
    assert updated.values == (("crate_secured", True),)


def test_scene_flag_returns_default_for_missing_key():
    assert scene_flag(SceneFlags(), "unknown", False) is False
