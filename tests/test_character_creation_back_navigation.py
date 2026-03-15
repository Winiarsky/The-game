from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from character_creation.catalog import (
    ANCESTRY_FEAT_IDS_BY_ANCESTRY,
    CLASS_FEAT_CHOICES_MANUAL,
    HERITAGE_IDS_BY_ANCESTRY,
    list_background_status_ids,
    resolve_status,
)
from character_creation.pipeline import _BACK_OPTION_ID, _prompt_text, create_character
from character_creation.repository import CharacterRepository
from character_creation.pipeline import _run_starting_equipment_step
from economy import actor_total_cp
from hero import Hero


class _UiTextBackStub:
    enabled = True
    allow_cli_fallback = False

    def prompt_choice(self, *_args, **_kwargs):
        return "/back"


class _GameStub:
    def __init__(self):
        self.ui = None
        self.logs: list[str] = []

    def ui_log(self, message: str) -> None:
        self.logs.append(str(message))

    def ui_hero(self, *_args, **_kwargs):
        return None

    def ui_active_actor(self, *_args, **_kwargs):
        return None


def test_prompt_text_supports_back_token():
    game = _GameStub()
    game.ui = _UiTextBackStub()
    value = _prompt_text(
        game,
        title="Test",
        source="test",
        default="X",
        allow_back=True,
    )
    assert value == _BACK_OPTION_ID


def test_create_character_allows_back_from_heritage_to_ancestry(monkeypatch, tmp_path):
    repo = CharacterRepository(tmp_path / "heroes")
    game = _GameStub()

    elf_heritage = str(HERITAGE_IDS_BY_ANCESTRY["elf"][0])
    elf_feat = str(ANCESTRY_FEAT_IDS_BY_ANCESTRY["elf"][0])
    background_id = str(list_background_status_ids()[0])
    fighter_feat = str((CLASS_FEAT_CHOICES_MANUAL.get("fighter") or [""])[0] or "")

    ancestry_calls = {"count": 0}
    heritage_calls = {"count": 0}

    def _fake_pick_portrait(_game, **_kwargs):
        return "/static/placeholder.png"

    def _fake_prompt_text(_game, *, title, **_kwargs):
        if "imię" in title.lower() or "imię" in title.lower():
            return "Arnold"
        if "koncepcja" in title.lower():
            return "Wojownik zwiadowca"
        return "tekst"

    def _fake_pick_one(_game, *, title, **_kwargs):
        if title.startswith("KROK 2: Wybór Ancestry"):
            ancestry_calls["count"] += 1
            return "human" if ancestry_calls["count"] == 1 else "elf"
        if title.startswith("KROK 3: Wybór Heritage"):
            heritage_calls["count"] += 1
            return _BACK_OPTION_ID if heritage_calls["count"] == 1 else elf_heritage
        if title.startswith("KROK 4: Ancestry Feat"):
            return elf_feat
        if title.startswith("KROK 5: Background"):
            return background_id
        if title.startswith("KROK 6: Wybór Klasy"):
            return "fighter"
        if title.startswith("KROK 11: Class Feat"):
            return fighter_feat
        return None

    monkeypatch.setattr("character_creation.pipeline._pick_portrait_image", _fake_pick_portrait)
    monkeypatch.setattr("character_creation.pipeline._prompt_text", _fake_prompt_text)
    monkeypatch.setattr("character_creation.pipeline._pick_one", _fake_pick_one)
    monkeypatch.setattr("character_creation.pipeline._pick_ability", lambda *_a, **_k: "strength")
    monkeypatch.setattr("character_creation.pipeline._pick_additional_skills", lambda *_a, **_k: [])
    monkeypatch.setattr("character_creation.pipeline._resolve_background_training_choice", lambda *_a, **_k: (None, None))
    monkeypatch.setattr("character_creation.pipeline._run_starting_equipment_step", lambda *_a, **_k: None)
    monkeypatch.setattr("character_creation.pipeline._prompt_info", lambda *_a, **_k: None)

    result = create_character(game, repo)
    assert result is not None
    hero = result.hero
    assert hero.ancestry_id == "elf"
    assert hero.has_status("elf")
    assert not hero.has_status("human")
    assert ancestry_calls["count"] >= 2
    assert heritage_calls["count"] >= 2


def test_starting_equipment_allows_undo_last_purchase(monkeypatch):
    game = _GameStub()
    hero = Hero()
    picks = iter(["longsword", _BACK_OPTION_ID, "__finish_equipment__"])

    monkeypatch.setattr("character_creation.pipeline._pick_one", lambda *_a, **_k: next(picks))
    monkeypatch.setattr("character_creation.pipeline._prompt_info", lambda *_a, **_k: None)

    _run_starting_equipment_step(game, hero, class_id="fighter", image=None)

    assert actor_total_cp(hero) == 1500  # 15 gp
    item_ids = [str(getattr(item, "item_id", "") or "").strip().lower() for item in list(getattr(hero, "inventory", []) or [])]
    assert "longsword" not in item_ids


def test_create_character_barbarian_requires_instinct_step(monkeypatch, tmp_path):
    repo = CharacterRepository(tmp_path / "heroes")
    game = _GameStub()

    heritage_id = str((HERITAGE_IDS_BY_ANCESTRY.get("elf") or [""])[0] or "")
    ancestry_feat_candidates = list(ANCESTRY_FEAT_IDS_BY_ANCESTRY.get("elf") or [])
    ancestry_feat_id = ""
    for candidate in ancestry_feat_candidates:
        status = resolve_status(candidate)
        data = getattr(status, "data", None) or {}
        if not data.get("ui_choice_kind"):
            ancestry_feat_id = str(candidate)
            break
    if not ancestry_feat_id and ancestry_feat_candidates:
        ancestry_feat_id = str(ancestry_feat_candidates[0])
    background_id = str(list_background_status_ids()[0])
    barbarian_feat = "sudden_charge"
    if barbarian_feat not in set(CLASS_FEAT_CHOICES_MANUAL.get("barbarian") or []):
        barbarian_feat = str((CLASS_FEAT_CHOICES_MANUAL.get("barbarian") or [""])[0] or "")

    seen_titles: list[str] = []

    def _fake_pick_portrait(_game, **_kwargs):
        return "/static/placeholder.png"

    def _fake_prompt_text(_game, *, title, **_kwargs):
        if "imię" in title.lower():
            return "Grog"
        return "tekst"

    def _fake_pick_one(_game, *, title, **_kwargs):
        seen_titles.append(str(title))
        if title.startswith("KROK 2: Wybór Ancestry"):
            return "elf"
        if title.startswith("KROK 3: Wybór Heritage"):
            return heritage_id
        if title.startswith("KROK 4: Ancestry Feat"):
            return ancestry_feat_id
        if title.startswith("KROK 5: Background"):
            return background_id
        if title.startswith("KROK 6: Wybór Klasy"):
            return "barbarian"
        if title.startswith("KROK 6B: Instynkt Barbarzyńcy"):
            return "giant_instinct"
        if title.startswith("KROK 11: Class Feat"):
            return barbarian_feat
        return None

    monkeypatch.setattr("character_creation.pipeline._pick_portrait_image", _fake_pick_portrait)
    monkeypatch.setattr("character_creation.pipeline._prompt_text", _fake_prompt_text)
    monkeypatch.setattr("character_creation.pipeline._pick_one", _fake_pick_one)
    monkeypatch.setattr("character_creation.pipeline._pick_ability", lambda *_a, **_k: "strength")
    monkeypatch.setattr("character_creation.pipeline._pick_additional_skills", lambda *_a, **_k: [])
    monkeypatch.setattr("character_creation.pipeline._resolve_background_training_choice", lambda *_a, **_k: (None, None))
    monkeypatch.setattr("character_creation.pipeline._run_starting_equipment_step", lambda *_a, **_k: None)
    monkeypatch.setattr("character_creation.pipeline._prompt_info", lambda *_a, **_k: None)

    result = create_character(game, repo)
    assert result is not None
    assert any(title.startswith("KROK 6B: Instynkt Barbarzyńcy") for title in seen_titles)
    assert result.hero.has_status("barbarian")
    assert result.hero.has_status("giant_instinct")
    assert result.hero.has_status(barbarian_feat)


def test_barbarian_can_receive_sudden_charge_status():
    hero = Hero()
    barbarian_status = resolve_status("barbarian")
    sudden_charge_status = resolve_status("sudden_charge")
    assert barbarian_status is not None
    assert sudden_charge_status is not None
    assert hero.add_status(barbarian_status)
    assert hero.add_status(sudden_charge_status)
    assert hero.has_status("sudden_charge")
