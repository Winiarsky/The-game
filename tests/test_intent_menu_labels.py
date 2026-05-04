from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from states.intent_menu import build_intent_options, choose_event_from_bucket, group_events


class _Actor:
    def __init__(self, statuses: list[str] | None = None):
        self.statuses = [type("_Status", (), {"id": sid})() for sid in list(statuses or [])]

    def has_status(self, status_id: str) -> bool:
        wanted = str(status_id or "").strip().lower()
        return any(str(getattr(item, "id", item)).strip().lower() == wanted for item in self.statuses)


def _grouped_with_stealth() -> dict:
    return {
        "direct": {"move": object(), "stealth": object()},
        "attack": [],
        "magic": [],
        "alchemy": [],
        "special": [],
        "special_by_source": {"generic": [], "heritage": [], "class": []},
    }


def _event_cls(module: str, tags: list[str]):
    return type("DummyEvent", (), {"__module__": module, "default_tags": tags, "available_in_combat": True, "available_in_exploration": True})


class _UI:
    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def prompt_choice(self, *args, choices=None, choice_meta=None, **kwargs):
        title = args[0] if args else kwargs.get("title")
        self.calls.append({"title": title, "choices": list(choices or []), "choice_meta": list(choice_meta or []), "kwargs": dict(kwargs)})
        return self.answer


def test_intent_uses_stealth_entry_when_actor_not_hidden():
    options = build_intent_options(_grouped_with_stealth(), in_combat=True, actor=_Actor([]))
    stealth = next(item for item in options if item.get("id") == "stealth")
    assert stealth["label"] == "Skradanie"


def test_intent_uses_sneak_move_entry_when_actor_already_stealth():
    options = build_intent_options(_grouped_with_stealth(), in_combat=True, actor=_Actor(["stealth"]))
    stealth = next(item for item in options if item.get("id") == "stealth")
    assert stealth["label"] == "Poruszaj sie skrycie"


def test_seek_intent_describes_grid_range_and_wall_blocking():
    grouped = {
        "direct": {"seek": object()},
        "attack": [],
        "magic": [],
        "alchemy": [],
        "special": [],
        "special_by_source": {"generic": [], "heritage": [], "class": []},
    }

    options = build_intent_options(grouped, in_combat=True, actor=_Actor([]))
    seek = next(item for item in options if item.get("id") == "seek")

    assert "30 ft" in seek["desc"]
    assert "gridowo" in seek["desc"]
    assert "sciany" in seek["desc"]


def test_alchemy_bucket_exposes_cancel_option():
    events = {"smokestick": _event_cls("GameObjects.events.elixirs.smokestick_event", ["alchemical", "tool"])}
    game = type("_Game", (), {"ui": _UI("cancel")})()

    answer = choose_event_from_bucket(
        game,
        bucket_id="alchemy",
        available_events=events,
        event_names=["smokestick"],
        source="intent:alchemy",
        actor=_Actor([]),
    )

    assert answer == "cancel"
    meta = game.ui.calls[0]["choice_meta"]
    assert meta[0]["raw"] == "cancel"
    assert meta[0]["label"] == "Anuluj"


def test_group_events_splits_special_actions_by_source():
    actor = _Actor(["animal_companion", "hunt_prey", "hunted_shot", "goblin_song", "ranger", "goblin"])
    setattr(actor, "class_name", "ranger")
    setattr(actor, "ancestry", "goblin")
    events = {
        "grapple": _event_cls("GameObjects.events.grapple_event", ["attack", "athletics", "grapple"]),
        "hunt_prey": _event_cls("GameObjects.events.ranger_feat_events", ["ranger", "concentrate"]),
        "command_animal_companion": _event_cls("GameObjects.events.command_animal_companion_event", ["companion", "command"]),
        "goblin_song": _event_cls("GameObjects.events.goblin_song_event", ["performance", "sonic"]),
    }

    grouped = group_events(events, actor=actor)

    assert grouped["special_by_source"]["generic"] == ["grapple"]
    assert grouped["special_by_source"]["heritage"] == ["goblin_song"]
    assert grouped["special_by_source"]["class"] == ["command_animal_companion", "hunt_prey"]


def test_intent_expands_special_actions_into_source_sections():
    actor = _Actor(["animal_companion", "hunt_prey", "goblin_song", "ranger", "goblin"])
    setattr(actor, "class_name", "ranger")
    setattr(actor, "ancestry", "goblin")
    events = {
        "grapple": _event_cls("GameObjects.events.grapple_event", ["attack", "athletics", "grapple"]),
        "hunt_prey": _event_cls("GameObjects.events.ranger_feat_events", ["ranger", "concentrate"]),
        "goblin_song": _event_cls("GameObjects.events.goblin_song_event", ["performance", "sonic"]),
    }

    grouped = group_events(events, actor=actor)
    options = build_intent_options(grouped, in_combat=True, actor=actor, available_events=events)

    by_id = {item["id"]: item for item in options}
    assert "special" not in by_id
    assert by_id["grapple"]["category"] == "generic"
    assert by_id["goblin_song"]["category"] == "heritage"
    assert by_id["hunt_prey"]["category"] == "class"


def test_ranger_special_action_descriptions_include_hunt_prey_persistence_and_companion_details():
    actor = _Actor(["animal_companion", "hunt_prey", "hunted_shot", "ranger"])
    setattr(actor, "class_name", "ranger")
    setattr(actor, "animal_companion_type", "wolf")
    events = {
        "command_animal_companion": _event_cls("GameObjects.events.command_animal_companion_event", ["companion", "command"]),
        "hunt_prey": _event_cls("GameObjects.events.ranger_feat_events", ["ranger", "concentrate"]),
        "hunted_shot": _event_cls("GameObjects.events.ranger_feat_events", ["ranger", "attack", "attack_ranged"]),
    }

    grouped = group_events(events, actor=actor)
    options = build_intent_options(grouped, in_combat=True, actor=actor, available_events=events)

    by_id = {item["id"]: item for item in options}
    assert "nie odnawia się co turę" in by_id["hunt_prey"]["desc"]
    assert "Support" in by_id["command_animal_companion"]["desc"]
    assert "1d8" in by_id["command_animal_companion"]["desc"]
    assert "Jeśli poprzedni cel zginął" in by_id["hunted_shot"]["desc"]
