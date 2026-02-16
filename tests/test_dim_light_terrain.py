import sys
from pathlib import Path
import types
import importlib.util

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# podmień stub z conftest na realny move_utils
MOVE_UTILS_PATH = SRC_ROOT / "actions" / "move_utils.py"
spec = importlib.util.spec_from_file_location("actions.move_utils", MOVE_UTILS_PATH)
move_utils = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(move_utils)  # type: ignore[arg-type]
sys.modules["actions.move_utils"] = move_utils

from board_grid import BoardGrid  # noqa: E402
from GameObjects.Terrains.dim_light_terrain import DimLightTerrain  # noqa: E402
from GameObjects.interactions_mixin.skill_check_resolver import (  # noqa: E402
    resolve_skill_check_with_sources_from_roll,
)
from skills import Skill  # noqa: E402
from statuses import IN_DIM_LIGHT_STATUS  # noqa: E402
from GameObjects.interactions_mixin.status_mixin import StatusMixin  # noqa: E402


class DummyHero(StatusMixin):
    def __init__(self, position):
        self.position = position
        self.statuses = []

    def set_position(self, position):
        self.position = position


def test_dim_light_status_prompt_and_removal():
    board = BoardGrid(rows=1, cols=2)
    board.set_field((1, 0), DimLightTerrain())

    hero = DummyHero((0, 0))
    board.place(hero, (0, 0))

    ctx = types.SimpleNamespace(game=types.SimpleNamespace(board=board))

    # move into dim light -> status should be applied
    path = [(0, 0), (1, 0)]
    completed, stop_pos, reason = move_utils.follow_path(
        ctx,
        hero,
        path,
        on_enter=move_utils.default_on_enter,
        allow_occupied=True,
    )
    assert completed and reason is None
    assert hero.has_status(IN_DIM_LIGHT_STATUS)

    # status should add prompt note (manual bonus)
    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.STEALTH.value,
        dc=10,
        actor=hero,
        tags=[Skill.STEALTH.value, "try_stealth"],
        roll=10,
        apply_modifiers=True,
    )
    assert res.modifier == 0
    assert any("Półmrok" in note for note in res.notes)

    # move back to basic terrain -> status should be removed
    path_back = [(1, 0), (0, 0)]
    completed, stop_pos, reason = move_utils.follow_path(
        ctx,
        hero,
        path_back,
        on_enter=move_utils.default_on_enter,
        allow_occupied=True,
    )
    assert completed and reason is None
    assert not hero.has_status(IN_DIM_LIGHT_STATUS)
