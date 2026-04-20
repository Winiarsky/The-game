from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from src.states.heroes_turns import HeroesTurn
from src.states.start import Start


class _ConnStub:
    def __init__(self, timeline: list[str]):
        self.calls: list[str] = []
        self.timeline = timeline

    def set_leds(self, *_args, **_kwargs):
        self.calls.append("set_leds")
        self.timeline.append("set_leds")
        return True

    def scan_board(self, *_args, **_kwargs):
        self.calls.append("scan_board")
        self.timeline.append("scan_board")
        return (1, 1)

    def leds_off(self, *_args, **_kwargs):
        self.calls.append("leds_off")
        self.timeline.append("leds_off")
        return True


class _BoardStub:
    def __init__(self):
        self.placed: list[tuple[object, tuple[int, int]]] = []

    def place(self, obj, pos):
        obj.position = pos
        self.placed.append((obj, pos))


class _HeroStub:
    def __init__(self, name: str):
        self.name = name
        self.position = None
        self.character_id = ""


class _GameStub:
    def __init__(self):
        self.timeline: list[str] = []
        self.heroes = []
        self.scenario = {"starting_positions": [(1, 1), (2, 2)]}
        self.conn = _ConnStub(self.timeline)
        self.board = _BoardStub()
        self.logs: list[str] = []
        self.hints: list[tuple[str, str | None]] = []
        self.snapshots: list[tuple[object, str | None]] = []
        self.preselected_character_ids = []
        self.preselected_hero_count = 0
        self.ui = None

    def ui_log(self, message: str) -> None:
        self.logs.append(str(message))

    def ui_idle_hint(self, title: str, text: str | None = None) -> None:
        self.hints.append((str(title), text))

    def ui_hero(self, hero, note: str | None = None) -> None:
        self.snapshots.append((hero, note))


def test_start_setup_selects_hero_before_board_scan_and_shows_place_hint():
    game = _GameStub()
    start = Start(game)  # type: ignore[arg-type]

    hero = _HeroStub("Grog")

    def _pick(_used):
        game.timeline.append("pick_hero")
        return hero

    start._pick_or_create_hero = _pick  # type: ignore[method-assign]
    start._maybe_prompt_chameleon_gnome = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prompt_familiar_owner = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prompt_advanced_alchemy = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prepare_spells = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._prompt_menu_choice = lambda **_kwargs: "__start_game__"  # type: ignore[method-assign]

    result = start.set_heroes_starting_positions()

    assert isinstance(result, HeroesTurn)
    assert game.board.placed and game.board.placed[0][1] == (1, 1)
    assert game.heroes and game.heroes[0] is hero
    assert hero.position == (1, 1)

    # Kolejność: po ACCEPT najpierw wybór bohatera, dopiero potem scan pola.
    # pick_hero musi wystąpić przed podświetleniem pól i scanem pola.
    assert game.timeline.index("pick_hero") < game.timeline.index("set_leds")
    assert game.timeline.index("pick_hero") < game.timeline.index("scan_board")

    # Hint oczekiwania powinien zawierać imię bohatera i instrukcję ustawienia figurki.
    place_hints = [text for title, text in game.hints if title == "Czekam na działanie" and text]
    assert place_hints
    assert any("Grog" in hint and "podświetlonych pól" in hint for hint in place_hints)


def test_start_setup_offers_play_after_first_hero_without_second_card_scan():
    game = _GameStub()
    start = Start(game)  # type: ignore[arg-type]

    hero = _HeroStub("Grog")

    def _pick(_used):
        return hero

    start._pick_or_create_hero = _pick  # type: ignore[method-assign]
    start._maybe_prompt_chameleon_gnome = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prompt_familiar_owner = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prompt_advanced_alchemy = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prepare_spells = lambda *_a, **_k: None  # type: ignore[method-assign]

    original_prompt_menu_choice = start._prompt_menu_choice

    def _prompt_menu_choice(*, title, subtitle, source, options, layout="dialog"):  # noqa: ARG001
        if source == "hero_setup_next":
            return "__start_game__"
        return original_prompt_menu_choice(
            title=title,
            subtitle=subtitle,
            source=source,
            options=options,
            layout=layout,
        )

    start._prompt_menu_choice = _prompt_menu_choice  # type: ignore[method-assign]

    result = start.set_heroes_starting_positions()

    assert isinstance(result, HeroesTurn)
    assert len(game.heroes) == 1 and game.heroes[0] is hero
    assert "read_card" not in game.conn.calls
    assert any("Setup bohaterów zakończony. Start gry." in msg for msg in game.logs)


def test_start_setup_uses_preselected_heroes_without_card_scan():
    from collections import deque

    game = _GameStub()
    game.preselected_character_ids = deque(["cedric"])
    game.preselected_hero_count = 1
    start = Start(game)  # type: ignore[arg-type]

    hero = _HeroStub("Cedric")
    hero.character_id = "cedric"

    def _consume(_used):
        if game.preselected_character_ids:
            game.preselected_character_ids.popleft()
            return hero
        return None

    start._consume_preselected_hero = _consume  # type: ignore[method-assign]
    start._maybe_prompt_chameleon_gnome = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prompt_familiar_owner = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prompt_advanced_alchemy = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prepare_spells = lambda *_a, **_k: None  # type: ignore[method-assign]

    result = start.set_heroes_starting_positions()

    assert isinstance(result, HeroesTurn)
    assert len(game.heroes) == 1 and game.heroes[0] is hero
    assert "read_card" not in game.conn.calls
    assert any("automatycznie" in msg for msg in game.logs)
