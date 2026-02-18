import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.seek_event  # noqa: F401
from GameObjects.interactions_mixin.hidden_mixin import HiddenMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll
from hero import Hero
from skills import Skill
from statuses.race.gnome.heritages.sensate_gnome import SENSATE_GNOME_STATUS


class DummyHidden(HiddenMixin):
    def __init__(self, *, reveal_tags=(), reveal_dc=16):
        super().__init__()
        self.hidden = True
        self.revealed = False
        self.reveal_dc = reveal_dc
        self.seekable = True
        self.reveal_tags = tuple(reveal_tags)


def test_sensate_gnome_has_prompt_note_only_for_matching_tags():
    hero = Hero()
    hero.position = (1, 1)
    hero.add_status(SENSATE_GNOME_STATUS)

    resolution = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.PERCEPTION.value,
        dc=10,
        actor=hero,
        target=DummyHidden(reveal_tags=("nature",)),
        tags=["seek", Skill.PERCEPTION.value, "nature"],
        roll=10,
        game=None,
        apply_modifiers=True,
    )

    assert resolution.modifier == 4
    assert any("sensate gnome" in note.lower() for note in resolution.notes)

    resolution_no_tag = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.PERCEPTION.value,
        dc=10,
        actor=hero,
        target=DummyHidden(reveal_tags=("stone",)),
        tags=["seek", Skill.PERCEPTION.value, "stone"],
        roll=10,
        game=None,
        apply_modifiers=True,
    )

    assert resolution_no_tag.modifier == 0
    assert not any("sensate gnome" in note.lower() for note in resolution_no_tag.notes)
