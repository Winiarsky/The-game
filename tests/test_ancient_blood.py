from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from skills import Skill
from statuses.race.dwarf.heritages.ancient_blooded import ANCIENT_BLOOD_STATUS
from hero import Hero


class DummyUI:
    def __init__(self):
        self.last_prompt_long = None
        self.last_prompt = None

    def prompt_roll(self, prompt, *args, **kwargs):
        self.last_prompt = prompt
        self.last_prompt_long = kwargs.get("prompt_long")
        return 10


def test_ancient_blood_prompt_includes_circumstance_bonus(monkeypatch):
    dummy_ui = DummyUI()

    def _get_ui_client():
        return dummy_ui

    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.get_ui_client",
        _get_ui_client,
    )

    hero = Hero()
    hero.add_status(ANCIENT_BLOOD_STATUS)

    resolve_skill_check_with_sources(
        skill_id=Skill.WILL.value,
        dc=15,
        actor=hero,
        tags=["magic", Skill.WILL.value],
        apply_modifiers=False,
    )

    assert dummy_ui.last_prompt_long is not None
    assert "circumstance" in dummy_ui.last_prompt_long
    assert "ancient blood" in dummy_ui.last_prompt_long.lower()


def test_ancient_blood_prompt_without_status_has_no_bonus(monkeypatch):
    dummy_ui = DummyUI()

    def _get_ui_client():
        return dummy_ui

    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.get_ui_client",
        _get_ui_client,
    )

    hero = Hero()

    resolve_skill_check_with_sources(
        skill_id=Skill.REFLEX.value,
        dc=15,
        actor=hero,
        tags=["magic", Skill.REFLEX.value],
        apply_modifiers=False,
    )

    assert dummy_ui.last_prompt_long is not None
    assert "circumstance" not in dummy_ui.last_prompt_long
    assert "ancient blood" not in dummy_ui.last_prompt_long.lower()
    assert "brak" in dummy_ui.last_prompt_long


def test_ancient_blood_consumed_on_use(monkeypatch):
    dummy_ui = DummyUI()

    def _get_ui_client():
        return dummy_ui

    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.get_ui_client",
        _get_ui_client,
    )

    hero = Hero()
    hero.add_status(ANCIENT_BLOOD_STATUS)

    resolve_skill_check_with_sources(
        skill_id=Skill.FORTITUDE.value,
        dc=15,
        actor=hero,
        tags=["magic", Skill.FORTITUDE.value],
        apply_modifiers=False,
    )

    assert hero.get_status("ancient_blood") is None
