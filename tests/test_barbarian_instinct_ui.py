import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from hero import Hero
from statuses.classes.barbarian.instincts.animal_instinct import (
    AnimalInstinctStatus,
    ANIMAL_INSTINCT_PROFILES,
)
from statuses.classes.barbarian.instincts.dragon_instinct import (
    DragonInstinctStatus,
    DRAGON_INSTINCT_TYPES,
)
from statuses.classes.barbarian.instincts.fury_instinct import FuryInstinctStatus, FURY_INSTINCT_FEAT_CHOICES


class DummyUI:
    def __init__(self, answer: str):
        self.answer = answer
        self.enabled = True
        self.last_choices = None
        self.last_prompt = None

    def prompt_choice(self, prompt: str, choices=None, **_kwargs):
        self.last_prompt = prompt
        self.last_choices = list(choices or [])
        return self.answer

    def prompt_info(self, *_a, **_k):
        return None


def test_animal_instinct_ui_choice_sets_profile(monkeypatch):
    choice_key = "ape"
    ui = DummyUI("Ape")
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = Hero()
    hero.add_status(AnimalInstinctStatus())

    assert ui.last_prompt is not None and "Animal Instinct" in ui.last_prompt
    assert "Ape" in (ui.last_choices or [])
    assert hero.get_status_data("animal_instinct", "animal_instinct") == choice_key
    profile = hero.get_status_data("animal_instinct", "animal_instinct_profile")
    assert profile == ANIMAL_INSTINCT_PROFILES[choice_key]


def test_dragon_instinct_ui_choice_sets_type(monkeypatch):
    ui = DummyUI("Fire")
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = Hero()
    hero.add_status(DragonInstinctStatus())

    assert ui.last_prompt is not None and "Dragon Instinct" in ui.last_prompt
    assert "Fire" in (ui.last_choices or [])
    assert hero.get_status_data("dragon_instinct", "dragon_instinct_type") == "fire"


def test_fury_instinct_ui_choice_sets_feat(monkeypatch):
    ui = DummyUI("Cute Vision")
    monkeypatch.setattr("ui_client.get_ui_client", lambda: ui)

    hero = Hero()
    hero.add_status(FuryInstinctStatus())

    assert ui.last_prompt is not None and "Fury Instinct" in ui.last_prompt
    assert "Cute Vision" in (ui.last_choices or [])
    assert hero.get_status_data("fury_instinct", "fury_instinct_feat") == "cute_vision"
    assert hero.has_status("cute_vision")
