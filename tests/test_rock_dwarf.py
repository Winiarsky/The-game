from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from actions.move_utils import adjusted_forced_movement_squares
from hero import Hero
from skills import Skill
from statuses.race.dwarf.heritages.rock_dwarf import ROCK_DWARF_STATUS


class DummyUI:
    def __init__(self):
        self.last_prompt_long = None
        self.last_prompt = None

    def prompt_roll(self, prompt, *args, **kwargs):
        self.last_prompt = prompt
        self.last_prompt_long = kwargs.get("prompt_long")
        return 10


def _set_dummy_ui(monkeypatch):
    dummy = DummyUI()

    def _get_ui_client():
        return dummy

    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.get_ui_client",
        _get_ui_client,
    )
    return dummy


def test_rock_dwarf_bonus_applies_on_shove_reflex(monkeypatch):
    _set_dummy_ui(monkeypatch)
    actor = Hero()
    target = Hero()
    target.add_status(ROCK_DWARF_STATUS)

    result = resolve_skill_check_with_sources(
        skill_id=Skill.REFLEX.value,
        dc=15,
        actor=actor,
        target=target,
        tags=["shove", Skill.REFLEX.value],
        apply_modifiers=True,
    )

    assert result.modifier == 2
    assert result.total == result.roll + 2


def test_rock_dwarf_bonus_applies_on_trip_fortitude(monkeypatch):
    _set_dummy_ui(monkeypatch)
    actor = Hero()
    target = Hero()
    target.add_status(ROCK_DWARF_STATUS)

    result = resolve_skill_check_with_sources(
        skill_id=Skill.FORTITUDE.value,
        dc=15,
        actor=actor,
        target=target,
        tags=["trip", Skill.FORTITUDE.value],
        apply_modifiers=True,
    )

    assert result.modifier == 2
    assert result.total == result.roll + 2


def test_rock_dwarf_no_bonus_without_tags(monkeypatch):
    _set_dummy_ui(monkeypatch)
    actor = Hero()
    target = Hero()
    target.add_status(ROCK_DWARF_STATUS)

    result = resolve_skill_check_with_sources(
        skill_id=Skill.REFLEX.value,
        dc=15,
        actor=actor,
        target=target,
        tags=["push", Skill.REFLEX.value],
        apply_modifiers=True,
    )

    assert result.modifier == 0
    assert result.total == result.roll


def test_rock_dwarf_no_bonus_without_status(monkeypatch):
    _set_dummy_ui(monkeypatch)
    actor = Hero()
    target = Hero()

    result = resolve_skill_check_with_sources(
        skill_id=Skill.REFLEX.value,
        dc=15,
        actor=actor,
        target=target,
        tags=["shove", Skill.REFLEX.value],
        apply_modifiers=True,
    )

    assert result.modifier == 0
    assert result.total == result.roll


def test_rock_dwarf_forced_movement_multiplier_threshold():
    target = Hero()
    target.add_status(ROCK_DWARF_STATUS)

    # 5 ft shove zostaje 5 ft, bo redukcja działa od 10 ft.
    assert adjusted_forced_movement_squares(target, 1) == 1
    # 10 ft forced movement -> 5 ft.
    assert adjusted_forced_movement_squares(target, 2) == 1
