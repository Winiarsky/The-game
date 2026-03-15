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
    def __init__(self, responses):
        self.responses = list(responses)
        self.read_calls = 0
        self.prompts = []
        self.acceptables = []
        self.kwargs = []

    def read_card(self, *args, **kwargs):
        self.read_calls += 1
        self.prompts.append(args[0] if args else "")
        self.acceptables.append(args[1] if len(args) > 1 else None)
        self.kwargs.append(dict(kwargs))
        if not self.responses:
            return ""
        return self.responses.pop(0)


class DummyGame:
    def __init__(self, conn):
        self.conn = conn
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
    conn = DummyConn(["2", "alchemists_fire", "juggernaut_mutagen"])
    game = DummyGame(conn)
    start = Start(game)
    hero = Hero()
    hero.add_status(Status(id="advanced_alchemy"))

    start._maybe_prompt_advanced_alchemy(hero)

    all_advanced = _advanced_items(hero)
    assert len(all_advanced) == 4
    assert len(_event_items(hero, "alchemists_fire")) == 2
    assert len(_event_items(hero, "juggernaut_mutagen")) == 2
    assert all(int(getattr(item, "preparation_counter", -1)) == 0 for item in all_advanced)


def test_advanced_alchemy_invalid_event_reprompts_same_reagent_slot():
    conn = DummyConn(["1", "attack", "alchemists_fire"])
    game = DummyGame(conn)
    start = Start(game)
    hero = Hero()
    hero.add_status(Status(id="advanced_alchemy"))

    start._maybe_prompt_advanced_alchemy(hero)

    assert conn.read_calls == 3
    items = _event_items(hero, "alchemists_fire")
    assert len(items) == 2
    assert all(bool(getattr(item, "prepared_by_advanced_alchemy", False)) for item in items)


def test_advanced_alchemy_end_on_budget_prompt_cancels_without_items():
    conn = DummyConn(["end"])
    game = DummyGame(conn)
    start = Start(game)
    hero = Hero()
    hero.add_status(Status(id="advanced_alchemy"))

    start._maybe_prompt_advanced_alchemy(hero)

    assert len(_advanced_items(hero)) == 0


def test_advanced_alchemy_end_during_crafting_stops_early_and_keeps_created_items():
    conn = DummyConn(["3", "alchemists_fire", "end"])
    game = DummyGame(conn)
    start = Start(game)
    hero = Hero()
    hero.add_status(Status(id="advanced_alchemy"))

    start._maybe_prompt_advanced_alchemy(hero)

    items = _event_items(hero, "alchemists_fire")
    assert len(items) == 2
    assert len(_advanced_items(hero)) == 2


def test_advanced_alchemy_without_status_does_not_prompt_or_create_items():
    conn = DummyConn(["2", "alchemists_fire"])
    game = DummyGame(conn)
    start = Start(game)
    hero = Hero()

    start._maybe_prompt_advanced_alchemy(hero)

    assert conn.read_calls == 0
    assert len(_advanced_items(hero)) == 0


def test_advanced_alchemy_budget_prompt_displays_available_reagents():
    conn = DummyConn(["end"])
    game = DummyGame(conn)
    start = Start(game)
    hero = Hero()
    hero.level = 4
    hero.intelligence_modifier = 3
    hero.add_status(Status(id="advanced_alchemy"))

    start._maybe_prompt_advanced_alchemy(hero)

    assert conn.prompts
    assert "dostępne: 7" in str(conn.prompts[0]).lower()


def test_advanced_alchemy_event_prompt_provides_choice_list_with_end():
    conn = DummyConn(["1", "alchemists_fire"])
    game = DummyGame(conn)
    start = Start(game)
    hero = Hero()
    hero.add_status(Status(id="advanced_alchemy"))

    start._maybe_prompt_advanced_alchemy(hero)

    assert conn.read_calls >= 2
    event_choices = conn.acceptables[1]
    assert isinstance(event_choices, list)
    assert "end" in event_choices
    assert "alchemists_fire" in event_choices


def test_advanced_alchemy_event_prompt_contains_polish_labels_and_mechanics():
    conn = DummyConn(["1", "cheetahs_elixir"])
    game = DummyGame(conn)
    start = Start(game)
    hero = Hero()
    hero.add_status(Status(id="advanced_alchemy"))

    start._maybe_prompt_advanced_alchemy(hero)

    assert conn.read_calls >= 2
    kwargs = conn.kwargs[1] if len(conn.kwargs) > 1 else {}
    meta = list(kwargs.get("choice_meta") or [])
    assert meta
    cheetah = next((item for item in meta if str(item.get("raw") or "").strip().lower() == "cheetahs_elixir"), None)
    assert cheetah is not None
    assert "Eliksir geparda" in str(cheetah.get("label") or "")
    desc = str(cheetah.get("desc") or "")
    assert "Mechanika:" in desc
    assert "zwieksza predko" in desc.lower()
