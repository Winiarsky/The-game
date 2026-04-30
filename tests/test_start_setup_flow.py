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
from src.states.encounter_setup import run_setup_batches
from src.states.start import Start


class _ConnStub:
    def __init__(self, timeline: list[str]):
        self.calls: list[str] = []
        self.timeline = timeline
        self.led_payloads: list[tuple[object, object]] = []
        self.cancel_calls = 0

    def set_leds(self, *args, **_kwargs):
        self.calls.append("set_leds")
        self.timeline.append("set_leds")
        if len(args) >= 2:
            self.led_payloads.append((args[0], args[1]))
        return True

    def scan_board(self, *_args, **_kwargs):
        self.calls.append("scan_board")
        self.timeline.append("scan_board")
        return (1, 1)

    def leds_off(self, *_args, **_kwargs):
        self.calls.append("leds_off")
        self.timeline.append("leds_off")
        return True

    def cancel_scan(self, *_args, **_kwargs):
        self.cancel_calls += 1
        self.calls.append("cancel_scan")
        self.timeline.append("cancel_scan")
        return True


class _BoardStub:
    def __init__(self):
        self.placed: list[tuple[object, tuple[int, int]]] = []

    def place(self, obj, pos):
        obj.position = pos
        self.placed.append((obj, pos))

    def occupant_at(self, pos):
        for obj, placed_pos in self.placed:
            if placed_pos == pos:
                return obj
        return None


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


class _ChoiceUiStub:
    def __init__(self, answer: str):
        self.answer = answer
        self.calls: list[dict[str, object]] = []

    def prompt_choice(self, prompt, choices=None, source=None, **extra):
        self.calls.append(
            {
                "prompt": prompt,
                "choices": list(choices or []),
                "source": source,
                "extra": dict(extra),
            }
        )
        return self.answer


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
    place_hints = [text for title, text in game.hints if "Wskaż miejsce dla figurki" in title and text]
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

    def _prompt_menu_choice(*, title, subtitle, source, options, layout="dialog", prompt_id=None):  # noqa: ARG001
        if source == "hero_setup_next":
            return "__start_game__"
        return original_prompt_menu_choice(
            title=title,
            subtitle=subtitle,
            source=source,
            options=options,
            layout=layout,
            prompt_id=prompt_id,
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


def test_start_setup_retries_same_preselected_hero_after_cancel_without_manual_menu():
    from collections import deque

    game = _GameStub()
    game.preselected_character_ids = deque(["cedric"])
    game.preselected_hero_count = 1
    start = Start(game)  # type: ignore[arg-type]

    hero = _HeroStub("Cedric")
    hero.character_id = "cedric"
    consume_calls = {"count": 0}
    scan_calls = {"count": 0}
    menu_calls: list[str] = []

    def _consume(_used):
        consume_calls["count"] += 1
        if game.preselected_character_ids:
            game.preselected_character_ids.popleft()
            return hero
        return None

    def _scan(_choices):
        scan_calls["count"] += 1
        if scan_calls["count"] == 1:
            return None
        return (1, 1)

    def _prompt_menu_choice(**kwargs):
        menu_calls.append(str(kwargs.get("source") or ""))
        return "__start_game__"

    start._consume_preselected_hero = _consume  # type: ignore[method-assign]
    start._maybe_prompt_chameleon_gnome = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prompt_familiar_owner = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prompt_advanced_alchemy = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prepare_spells = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._prompt_menu_choice = _prompt_menu_choice  # type: ignore[method-assign]
    game.conn.scan_board = _scan  # type: ignore[method-assign]

    result = start.set_heroes_starting_positions()

    assert isinstance(result, HeroesTurn)
    assert hero.position == (1, 1)
    assert consume_calls["count"] == 1
    assert scan_calls["count"] == 2
    assert "hero_setup_next" not in menu_calls
    assert any("Ponów ustawienie figurki" in msg for msg in game.logs)


def test_start_setup_filters_out_already_occupied_start_positions():
    game = _GameStub()
    start = Start(game)  # type: ignore[arg-type]

    first_hero = _HeroStub("Cedric")
    second_hero = _HeroStub("Freya")
    picks = iter([first_hero, second_hero])
    scan_choices = iter([(1, 1), (2, 2)])

    def _pick(_used):
        return next(picks)

    def _scan(_choices):
        return next(scan_choices)

    def _prompt_menu_choice(**_kwargs):
        return "__add_hero__" if len(game.heroes) == 1 else "__start_game__"

    start._pick_or_create_hero = _pick  # type: ignore[method-assign]
    start._maybe_prompt_chameleon_gnome = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prompt_familiar_owner = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prompt_advanced_alchemy = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prepare_spells = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._prompt_menu_choice = _prompt_menu_choice  # type: ignore[method-assign]
    game.conn.scan_board = _scan  # type: ignore[method-assign]

    result = start.set_heroes_starting_positions()

    assert isinstance(result, HeroesTurn)
    assert len(game.conn.led_payloads) >= 2
    first_led_positions, _first_colors = game.conn.led_payloads[0]
    second_led_positions, _second_colors = game.conn.led_payloads[1]
    assert list(first_led_positions) == [(1, 1), (2, 2)]
    assert list(second_led_positions) == [(2, 2)]
    assert [hero.position for hero in game.heroes] == [(1, 1), (2, 2)]


def test_heroes_turn_stays_on_board_selection_when_cancelled():
    game = _GameStub()
    cedric = _HeroStub("Cedric")
    freya = _HeroStub("Freya")
    cedric.class_id = "ranger"
    freya.class_id = "sorcerer"
    game.heroes = [cedric, freya]
    game.board.place(cedric, (1, 1))
    game.board.place(freya, (2, 2))
    def _scan_board(*_args, **_kwargs):
        return None

    game.conn.scan_board = _scan_board  # type: ignore[method-assign]

    state = HeroesTurn(game)  # type: ignore[arg-type]

    picked = state._choose_active_hero()

    assert picked is None
    assert any("został anulowany" in msg for msg in game.logs)


def test_start_setup_retries_when_board_selection_is_cancelled():
    game = _GameStub()
    start = Start(game)  # type: ignore[arg-type]

    hero = _HeroStub("Grog")

    def _pick(_used):
        return hero

    scan_calls = {"count": 0}

    def _scan_board(*_args, **_kwargs):
        scan_calls["count"] += 1
        if scan_calls["count"] == 1:
            return None
        return (2, 2)

    game.conn.scan_board = _scan_board  # type: ignore[method-assign]
    start._pick_or_create_hero = _pick  # type: ignore[method-assign]
    start._maybe_prompt_chameleon_gnome = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prompt_familiar_owner = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prompt_advanced_alchemy = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prepare_spells = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._prompt_menu_choice = lambda **_kwargs: "__start_game__"  # type: ignore[method-assign]

    result = start.set_heroes_starting_positions()

    assert isinstance(result, HeroesTurn)
    assert hero.position == (2, 2)
    assert any("Nie wybrano pola startowego" in msg for msg in game.logs)


def test_start_setup_waits_on_board_without_timeout_or_ui_fallback():
    game = _GameStub()
    game.ui = _ChoiceUiStub("(2, 2)")
    start = Start(game)  # type: ignore[arg-type]

    hero = _HeroStub("Grog")
    scan_kwargs: list[dict[str, object]] = []

    def _pick(_used):
        return hero

    def _scan_board(_choices, **kwargs):
        scan_kwargs.append(dict(kwargs))
        return (2, 2)

    game.conn.scan_board = _scan_board  # type: ignore[method-assign]
    start._pick_or_create_hero = _pick  # type: ignore[method-assign]
    start._maybe_prompt_chameleon_gnome = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prompt_familiar_owner = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prompt_advanced_alchemy = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._maybe_prepare_spells = lambda *_a, **_k: None  # type: ignore[method-assign]
    start._prompt_menu_choice = lambda **_kwargs: "__start_game__"  # type: ignore[method-assign]

    result = start.set_heroes_starting_positions()

    assert isinstance(result, HeroesTurn)
    assert hero.position == (2, 2)
    assert scan_kwargs == [{}]
    assert game.conn.cancel_calls == 0
    assert game.ui.calls == []
    assert not any("Plansza nie zwróciła pola startowego" in msg for msg in game.logs)


def test_wall_setup_uses_two_endpoint_colors_and_explains_them():
    game = _GameStub()

    run_setup_batches(
        game,
        [
            {
                "kind": "wall",
                "positions": [(0, 0), (1, 0), (0, 1), (1, 1)],
                "edges": [{"a": [0, 0], "b": [1, 0]}],
                "prompt": "Ustaw ściany zgodnie z podświetlonymi krawędziami i potwierdź w UI.",
                "confirmation_mode": "confirm_only",
                "color": [255, 140, 0],
            }
        ],
    )

    assert game.conn.led_payloads
    positions, colors = game.conn.led_payloads[0]
    assert list(positions) == [(0, 0), (1, 0), (0, 1), (1, 1)]
    assert colors == [
        [0, 160, 0],
        [255, 140, 0],
        [255, 140, 0],
        [0, 160, 0],
    ]
    assert any("zielony" in msg and "pomarańczowy" in msg for msg in game.logs)
