from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from hero import Hero
from states.start import Start
from statuses import Status


class DummyConn:
    def __init__(self):
        self.responses = []


class DummyUI:
    def __init__(self, responses):
        self.enabled = True
        self.allow_cli_fallback = False
        self.responses = list(responses)
        self.prompt_calls = []
        self.info_calls = []

    def prompt_choice(self, prompt, choices=None, **kwargs):
        self.prompt_calls.append(
            {
                "prompt": prompt,
                "choices": list(choices or []),
                "kwargs": dict(kwargs),
            }
        )
        if self.responses:
            return self.responses.pop(0)
        if choices:
            return choices[0]
        return None

    def prompt_info(self, title, **kwargs):
        self.info_calls.append({"title": title, "kwargs": dict(kwargs)})
        return "ok"


class DummyGame:
    def __init__(self, conn, ui):
        self.conn = conn
        self.ui = ui
        self.logs = []

    def ui_log(self, msg: str):
        self.logs.append(msg)


def _advanced_items(hero):
    return [
        item for item in (getattr(hero, "inventory", []) or [])
        if bool(getattr(item, "prepared_by_advanced_alchemy", False))
    ]


def _event_items(hero, event_name: str):
    key = str(event_name).strip().lower()
    return [
        item for item in (getattr(hero, "inventory", []) or [])
        if str(getattr(item, "event_name", "")).strip().lower() == key
    ]


def test_advanced_alchemy_creates_two_items_per_reagent_and_tags_them():
    ui = DummyUI(["2", "alchemists_fire", "juggernaut_mutagen"])
    game = DummyGame(DummyConn(), ui)
    start = Start(game)
    hero = Hero()
    hero.level = 2
    hero.add_status(Status(id="advanced_alchemy"))

    start._maybe_prompt_advanced_alchemy(hero)

    all_advanced = _advanced_items(hero)
    assert len(all_advanced) == 4
    assert len(_event_items(hero, "alchemists_fire")) == 2
    assert len(_event_items(hero, "juggernaut_mutagen")) == 2
    assert all(int(getattr(item, "preparation_counter", -1)) == 0 for item in all_advanced)


def test_advanced_alchemy_invalid_event_reprompts_same_reagent_slot():
    ui = DummyUI(["1", "attack", "alchemists_fire"])
    game = DummyGame(DummyConn(), ui)
    start = Start(game)
    hero = Hero()
    hero.add_status(Status(id="advanced_alchemy"))

    start._maybe_prompt_advanced_alchemy(hero)

    assert len(ui.prompt_calls) == 3
    items = _event_items(hero, "alchemists_fire")
    assert len(items) == 2
    assert all(bool(getattr(item, "prepared_by_advanced_alchemy", False)) for item in items)


def test_advanced_alchemy_end_on_budget_prompt_cancels_without_items():
    ui = DummyUI(["end"])
    game = DummyGame(DummyConn(), ui)
    start = Start(game)
    hero = Hero()
    hero.add_status(Status(id="advanced_alchemy"))

    start._maybe_prompt_advanced_alchemy(hero)

    assert len(_advanced_items(hero)) == 0


def test_advanced_alchemy_end_during_crafting_stops_early_and_keeps_created_items():
    ui = DummyUI(["3", "alchemists_fire", "end"])
    game = DummyGame(DummyConn(), ui)
    start = Start(game)
    hero = Hero()
    hero.level = 3
    hero.add_status(Status(id="advanced_alchemy"))

    start._maybe_prompt_advanced_alchemy(hero)

    items = _event_items(hero, "alchemists_fire")
    assert len(items) == 2
    assert len(_advanced_items(hero)) == 2


def test_advanced_alchemy_without_status_does_not_prompt_or_create_items():
    ui = DummyUI(["2", "alchemists_fire"])
    game = DummyGame(DummyConn(), ui)
    start = Start(game)
    hero = Hero()

    start._maybe_prompt_advanced_alchemy(hero)

    assert len(ui.prompt_calls) == 0
    assert len(_advanced_items(hero)) == 0


def test_advanced_alchemy_budget_prompt_displays_available_reagents():
    ui = DummyUI(["end"])
    game = DummyGame(DummyConn(), ui)
    start = Start(game)
    hero = Hero()
    hero.level = 4
    hero.intelligence_modifier = 3
    hero.add_status(Status(id="advanced_alchemy"))

    start._maybe_prompt_advanced_alchemy(hero)

    assert ui.prompt_calls
    assert "dostępne: 7" in str(ui.prompt_calls[0]["kwargs"].get("subtitle") or "").lower()


def test_advanced_alchemy_event_prompt_provides_choice_list_with_end():
    ui = DummyUI(["1", "alchemists_fire"])
    game = DummyGame(DummyConn(), ui)
    start = Start(game)
    hero = Hero()
    hero.add_status(Status(id="advanced_alchemy"))

    start._maybe_prompt_advanced_alchemy(hero)

    assert len(ui.prompt_calls) >= 2
    meta = list(ui.prompt_calls[1]["kwargs"].get("choice_meta") or [])
    raw_ids = {str(item.get("raw") or "").strip().lower() for item in meta}
    assert "end" in raw_ids
    assert "alchemists_fire" in raw_ids


def test_advanced_alchemy_event_prompt_contains_polish_labels_and_mechanics():
    ui = DummyUI(["1", "cheetahs_elixir"])
    game = DummyGame(DummyConn(), ui)
    start = Start(game)
    hero = Hero()
    hero.add_status(Status(id="advanced_alchemy"))

    start._maybe_prompt_advanced_alchemy(hero)

    assert len(ui.prompt_calls) >= 2
    kwargs = ui.prompt_calls[1]["kwargs"] if len(ui.prompt_calls) > 1 else {}
    meta = list(kwargs.get("choice_meta") or [])
    assert meta
    cheetah = next((item for item in meta if str(item.get("raw") or "").strip().lower() == "cheetahs_elixir"), None)
    assert cheetah is not None
    assert "Eliksir geparda" in str(cheetah.get("label") or "")
    desc = str(cheetah.get("desc") or "")
    assert "Mechanika:" in desc
    assert "zwiększa prędko" in desc.lower()
