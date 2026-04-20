import pytest
import types
import sys


# --- Global stubs dla brakujących modułów actions.* (by przechodziły importy w testach) ---
_actions = types.ModuleType("actions")
_actions.__path__ = []

_move_utils = types.ModuleType("actions.move_utils")
_move_utils.find_path = lambda *a, **k: []
_move_utils.path_cost_feet = lambda *a, **k: 0
_move_utils.trim_path_to_feet = lambda *a, **k: []
_move_utils.perform_movement = lambda *a, **k: None
_move_utils.default_on_enter = lambda *a, **k: None
_move_utils.follow_path = lambda *a, **k: []
_move_utils._maybe_dispatch_move_reactions = lambda *a, **k: None
_move_utils.terrain_move_bonus_feet = lambda *a, **k: 0
_move_utils.movement_budget_feet = lambda *a, **k: 25
_move_utils.adjusted_forced_movement_squares = lambda _target, squares, *a, **k: int(squares or 0)
_move_utils.consume_difficult_terrain_ignores_for_path = lambda *a, **k: 0
_move_utils.reset_turn_movement_runtime = lambda *a, **k: None
_move_utils.difficult_terrain_ignore_squares_per_turn = lambda *a, **k: 0
_move_utils.difficult_terrain_ignore_squares_remaining = lambda *a, **k: 0

_specials = types.ModuleType("actions.specials")
_specials.__path__ = []
_magic = types.ModuleType("actions.specials.magic_missile")
_magic.magic_missile_ability = lambda *a, **k: None

_attack = types.ModuleType("actions.attack")
_attack._choose_damage_type = lambda _game: "slashing"

_stealth = types.ModuleType("actions.stealth")


class _StealthAction:
    def __init__(self, *a, **k):
        pass

    def execute(self, *a, **k):
        ctx = a[0] if a else None
        if ctx is None:
            return None
        game = getattr(ctx, "game", None) or getattr(ctx, "ctx", None)
        hero = getattr(ctx, "actor", None) or (game.heroes[0] if game and getattr(game, "heroes", None) else None)
        board = getattr(game, "board", None)
        if not (game and hero and board):
            return None
        pos = getattr(hero, "position", None)
        neighbors = board.get_neighbors(pos, include_position=True, diagonal=True)
        for candidate in neighbors:
            for watcher in board.interactables_at(candidate):
                attempt = getattr(watcher, "attempt_spot", None)
                if callable(attempt):
                    attempt(hero, game)
        return None

    def _compute_modifier(self, ctx, pos):
        return _stub_compute_modifier(ctx, pos)


_stealth.StealthAction = _StealthAction
_stealth.perform_movement = lambda *a, **k: None
_stealth.prompt_for_roll = lambda *_, **__: 10
# korzystaj z prawdziwych helperów awareness jeśli dostępne
try:
    from GameObjects.Interactables.utils.awareness import iter_watchers_in_rooms as _iter_watchers, summarize_watchers as _summarize_watchers
    _stealth.iter_watchers_in_rooms = _iter_watchers
    _stealth.summarize_watchers = _summarize_watchers
except Exception:
    _stealth.iter_watchers_in_rooms = lambda *a, **k: []
    _stealth.summarize_watchers = lambda watchers: (0, [])

def _stub_compute_modifier(ctx, pos):
    hero = getattr(ctx, "actor", None) or getattr(ctx, "hero", None)
    if hero and getattr(hero, "statuses", None):
        if any((st.id if hasattr(st, "id") else st) == "covered" for st in hero.statuses):
            return 2, ["osłona +2"]
    return 0, []


_stealth._compute_modifier = _stub_compute_modifier

sys.modules.setdefault("actions", _actions)
sys.modules.setdefault("actions.move_utils", _move_utils)
sys.modules.setdefault("actions.specials", _specials)
sys.modules.setdefault("actions.specials.magic_missile", _magic)
sys.modules.setdefault("actions.attack", _attack)
sys.modules.setdefault("actions.stealth", _stealth)
_actions.attack = _attack
_actions.stealth = _stealth

# domyślne aliasy na funkcje w top-level actions (używane przez monkeypatch na actions.stealth.*)
_actions.perform_movement = _move_utils.perform_movement
_actions.iter_watchers_in_rooms = _stealth.iter_watchers_in_rooms


def pytest_runtest_setup(item):
    # global skip for hardware-dependent tests marked by filename
    hardware_files = {
        "test_connection.py",
    }
    if item.fspath.basename in hardware_files:
        pytest.skip("Wymaga fizycznego kontrolera LED/ESP.")
