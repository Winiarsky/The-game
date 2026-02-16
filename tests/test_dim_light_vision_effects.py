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

from GameObjects.events.attack import attack_base  # noqa: E402
from GameObjects.interactions_mixin.status_mixin import StatusMixin  # noqa: E402
from GameObjects.interactions_mixin.skill_check_resolver import (  # noqa: E402
    resolve_skill_check_with_sources_from_roll,
)
from skills import Skill  # noqa: E402
from statuses import (  # noqa: E402
    CONCEALED_STATUS,
    DIM_LIGHT_VISION_STATUS,
    IN_DIM_LIGHT_STATUS,
)


class DummyHero(StatusMixin):
    def __init__(self, position=None):
        self.position = position
        self.statuses = []

    def set_position(self, position):
        self.position = position


def test_dim_light_vision_perception_bonus_vs_in_dim_light_target():
    actor = DummyHero()
    actor.add_status(DIM_LIGHT_VISION_STATUS)
    target = DummyHero()
    target.add_status(IN_DIM_LIGHT_STATUS)

    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.PERCEPTION.value,
        dc=10,
        actor=actor,
        target=target,
        tags=[Skill.PERCEPTION.value, "seek"],
        roll=10,
        apply_modifiers=True,
    )
    assert res.modifier == 2
    assert res.total == 12
    assert any("Ignorujesz efekty polmroku" in note for note in res.notes)


def test_dim_light_vision_ignores_concealed_target(monkeypatch):
    actor = DummyHero()
    actor.add_status(DIM_LIGHT_VISION_STATUS)
    target = DummyHero()
    target.add_status(IN_DIM_LIGHT_STATUS)
    target.add_status(CONCEALED_STATUS)

    def _fail(*_args, **_kwargs):
        raise AssertionError("prompt_for_roll should not be called for dim light vision")

    monkeypatch.setattr(attack_base, "prompt_for_roll", _fail)
    ctx = types.SimpleNamespace(actor=actor, game=types.SimpleNamespace(ui_log=lambda *_a, **_k: None, ui=None))
    assert attack_base.check_concealed(ctx, target) is True


def test_dim_light_vision_requires_flat_check_without_in_dim_light(monkeypatch):
    actor = DummyHero()
    actor.add_status(DIM_LIGHT_VISION_STATUS)
    target = DummyHero()
    target.add_status(CONCEALED_STATUS)

    monkeypatch.setattr(attack_base, "prompt_for_roll", lambda *_a, **_k: 4)
    ctx = types.SimpleNamespace(actor=actor, game=types.SimpleNamespace(ui_log=lambda *_a, **_k: None, ui=None))
    assert attack_base.check_concealed(ctx, target) is False


def test_no_dim_light_vision_no_perception_bonus_vs_in_dim_light_target():
    actor = DummyHero()
    target = DummyHero()
    target.add_status(IN_DIM_LIGHT_STATUS)

    res = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.PERCEPTION.value,
        dc=10,
        actor=actor,
        target=target,
        tags=[Skill.PERCEPTION.value, "seek"],
        roll=10,
        apply_modifiers=True,
    )
    assert res.modifier == 0


def test_no_dim_light_vision_requires_concealed_flat_check(monkeypatch):
    actor = DummyHero()
    target = DummyHero()
    target.add_status(IN_DIM_LIGHT_STATUS)
    target.add_status(CONCEALED_STATUS)

    monkeypatch.setattr(attack_base, "prompt_for_roll", lambda *_a, **_k: 4)
    ctx = types.SimpleNamespace(actor=actor, game=types.SimpleNamespace(ui_log=lambda *_a, **_k: None, ui=None))
    assert attack_base.check_concealed(ctx, target) is False
