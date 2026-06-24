from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.interactions_mixin.status_mixin import StatusMixin
from GameObjects.interactions_mixin.skill_check_resolver import (
    resolve_skill_check_with_sources_from_roll,
)
from game import Game
from skills import Skill
from states.start import Start
from statuses.backgrounds.backgrounds import (
    ACOLYTE_BACKGROUND_STATUS,
    ARTISAN_BACKGROUND_STATUS,
    BACKGROUND_DEFINITIONS,
    BACKGROUND_STATUS_BY_KEY,
    MARTIAL_DISCIPLE_BACKGROUND_STATUS,
)


@dataclass
class DummyHero(StatusMixin):
    messages: list[str] = field(default_factory=list)

    def ui_log(self, message: str) -> None:
        self.messages.append(str(message))


class DummyUI:
    def __init__(self, answers: list[str]):
        self.answers = list(answers)
        self.enabled = True
        self.allow_cli_fallback = False

    def prompt_choice(self, _prompt: str, choices=None, **_kwargs):
        if self.answers:
            return self.answers.pop(0)
        if choices:
            return choices[0]
        return None

    def prompt_info(self, *_args, **_kwargs):
        return None


class SetupUI:
    def __init__(self, answers: list[str]):
        self.answers = list(answers)
        self.enabled = True
        self.allow_cli_fallback = False

    def prompt_choice(self, _prompt: str, choices=None, **_kwargs):
        if self.answers:
            return self.answers.pop(0)
        if choices:
            return choices[0]
        return None


@dataclass
class StartGameStub:
    ui: SetupUI
    logs: list[str] = field(default_factory=list)

    def ui_log(self, message: str) -> None:
        self.logs.append(str(message))


def test_background_module_contains_complete_background_list():
    assert len(BACKGROUND_STATUS_BY_KEY) == 35
    assert "acolyte" in BACKGROUND_STATUS_BY_KEY
    assert "warrior" in BACKGROUND_STATUS_BY_KEY

    for status in BACKGROUND_STATUS_BY_KEY.values():
        data = status.data or {}
        assert data.get("is_background") is True
        assert isinstance(data.get("ui_description"), str)
        assert isinstance(data.get("ui_prompt_long"), str)
        assert bool(data.get("background_skill_training_ui_only")) is True


def test_background_prompt_long_contains_short_feat_mechanics():
    status = BACKGROUND_STATUS_BY_KEY["acolyte"]
    data = status.data or {}
    text = str(data.get("ui_prompt_long") or "")
    assert "Mechanika featu (krotko):" in text
    assert "+2 status do testów Religii." in text


def test_every_background_with_feat_has_grants_status():
    for definition in BACKGROUND_DEFINITIONS:
        status = BACKGROUND_STATUS_BY_KEY[definition.key]
        data = status.data or {}
        if not definition.feat_id:
            continue
        grants = list(data.get("grants_statuses") or [])
        assert grants, f"Background '{definition.key}' should grant feat '{definition.feat_id}'."
        granted_ids = {getattr(item, "id", None) for item in grants}
        assert definition.feat_id in granted_ids


def test_background_adds_its_feat_as_status():
    hero = DummyHero()
    added = hero.add_status(ACOLYTE_BACKGROUND_STATUS)

    assert added is True
    assert hero.has_status("background_acolyte")
    assert hero.has_status("student_of_the_canon")
    assert hero.get_status_data("background_acolyte", "trained_skills", None) is None


def test_artisan_background_feat_applies_real_crafting_bonus():
    hero = DummyHero()
    hero.add_status(ARTISAN_BACKGROUND_STATUS)

    result = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.CRAFTING.value,
        dc=15,
        actor=hero,
        tags=["craft"],
        roll=10,
        apply_modifiers=True,
        base_modifier=0,
    )

    assert result.modifier == 2
    assert result.total == 12


def test_barkeep_background_feat_applies_real_diplomacy_bonus():
    hero = DummyHero()
    hero.add_status(BACKGROUND_STATUS_BY_KEY["barkeep"])

    result = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.DIPLOMACY.value,
        dc=15,
        actor=hero,
        tags=["social"],
        roll=10,
        apply_modifiers=True,
        base_modifier=0,
    )

    assert result.modifier == 2
    assert result.total == 12


def test_second_background_is_blocked():
    hero = DummyHero()
    assert hero.add_status(ACOLYTE_BACKGROUND_STATUS) is True

    added_second = hero.add_status(ARTISAN_BACKGROUND_STATUS)
    assert added_second is False
    assert hero.has_status("background_acolyte")
    assert hero.has_status("background_artisan") is False
    assert any("tylko jeden background" in msg.lower() for msg in hero.messages)


def test_martial_disciple_prompts_and_grants_matching_feat(monkeypatch):
    ui = DummyUI(["Athletics"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = DummyHero()
    added = hero.add_status(MARTIAL_DISCIPLE_BACKGROUND_STATUS)

    assert added is True
    assert hero.has_status("background_martial_disciple")
    assert hero.get_status_data("background_martial_disciple", "martial_disciple_skill_choice", None) == "athletics"
    assert hero.get_status_data("background_martial_disciple", "martial_disciple_feat_choice", None) == "quick_jump"
    assert hero.has_status("quick_jump")
    assert hero.has_status("cat_fall") is False


def test_start_background_prompt_adds_background_and_feat(monkeypatch):
    game = StartGameStub(ui=SetupUI(["Acolyte"]))
    start = Start(game)  # type: ignore[arg-type]
    hero = DummyHero()
    monkeypatch.setattr("ui_client.get_ui_client", lambda: DummyUI([]))

    start._maybe_prompt_background(hero)

    assert hero.has_status("background_acolyte")
    assert hero.has_status("student_of_the_canon")
    assert any("wybrano Akolita" in msg for msg in game.logs)


def test_start_background_prompt_handles_invalid_choice(monkeypatch):
    game = StartGameStub(ui=SetupUI(["Unknown Background"]))
    start = Start(game)  # type: ignore[arg-type]
    hero = DummyHero()
    monkeypatch.setattr("ui_client.get_ui_client", lambda: DummyUI([]))

    start._maybe_prompt_background(hero)

    assert hero.has_status("background_acolyte") is False
    assert hero.has_status("background_martial_disciple") is False
    assert any("nie wybrano poprawnej opcji" in msg.lower() for msg in game.logs)


def test_start_background_prompt_martial_disciple_grants_matching_feat(monkeypatch):
    game = StartGameStub(ui=SetupUI(["Martial Disciple"]))
    start = Start(game)  # type: ignore[arg-type]
    hero = DummyHero()
    monkeypatch.setattr("ui_client.get_ui_client", lambda: DummyUI(["Athletics"]))

    start._maybe_prompt_background(hero)

    assert hero.has_status("background_martial_disciple")
    assert hero.get_status_data("background_martial_disciple", "martial_disciple_skill_choice", None) == "athletics"
    assert hero.has_status("quick_jump")


def test_game_ui_hero_includes_background_payload():
    emitted: list[tuple[str, dict]] = []

    class GameUiStub:
        def ui_event(self, event_type: str, payload: dict) -> bool:
            emitted.append((event_type, payload))
            return True

    @dataclass
    class HeroUiStub(StatusMixin):
        object_id: str = "hero-1"
        name: str = "Test Hero"
        image: str = "/static/portraits/portrait_warrior.svg"
        position: tuple[int, int] | None = (1, 2)
        wounds: int = 0
        initiative: int = 17

        def status_labels(self):
            return [getattr(status, "display_label", status.id) for status in self.statuses]

    hero = HeroUiStub()
    hero.add_status(ACOLYTE_BACKGROUND_STATUS)

    Game.ui_hero(GameUiStub(), hero, note="snapshot")

    assert emitted
    event_type, payload = emitted[-1]
    assert event_type == "hero_snapshot"
    assert payload["image"] == "/static/portraits/portrait_warrior.svg"
    assert payload["background_label"] == "Akolita"
    assert payload["background_feat_id"] == "student_of_the_canon"
    assert payload["background_ability_boosts_ui"]
    assert payload["background_skill_training_ui"]
    assert isinstance(payload.get("hand_slots"), dict)
    assert "left" in payload["hand_slots"]
    assert "right" in payload["hand_slots"]
