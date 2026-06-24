import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from hero import Hero


def test_hero_roll_for_initiative_uses_perception_formula(monkeypatch):
    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll",
        lambda *_a, **_k: 10,
    )
    hero = Hero()
    hero.level = 1
    hero.ability_modifiers = {"wisdom": 2}
    hero.perception_rank = "trained"

    initiative = hero.roll_for_initiative()

    # d20=10 + level 1 + trained 2 + WIS 2 = 15
    assert initiative == 15
    assert hero.initiative == 15
