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

def _stub_status_data(actor):
    for status in getattr(actor, "statuses", []) or []:
        data = getattr(status, "data", {}) or {}
        if isinstance(data, dict):
            yield data

def _stub_first_status_int(actor, key):
    for data in _stub_status_data(actor):
        if key in data:
            try:
                return int(data.get(key) or 0)
            except Exception:
                return None
    return None

def _stub_sum_status_int(actor, key):
    total = 0
    for data in _stub_status_data(actor):
        try:
            total += int(data.get(key) or 0)
        except Exception:
            continue
    return total

def _stub_max_status_int(actor, key):
    best = 0
    for data in _stub_status_data(actor):
        try:
            best = max(best, int(data.get(key) or 0))
        except Exception:
            continue
    return best

def _stub_status_any_true(actor, key):
    return any(bool(data.get(key)) for data in _stub_status_data(actor))

def _stub_movement_budget_feet(mover, *, default_feet=25):
    base = None
    for attr in ("base_speed_feet", "speed_feet", "speed"):
        raw = getattr(mover, attr, None)
        if raw is not None:
            try:
                val = int(raw or 0)
            except Exception:
                val = 0
            if val > 0:
                base = val
                break
    if base is None:
        status_speed = _stub_first_status_int(mover, "base_speed_feet")
        if status_speed is not None and status_speed > 0:
            base = status_speed
    if base is None:
        distance = getattr(mover, "distance", None)
        if distance is not None:
            try:
                val = int(distance or 0)
            except Exception:
                val = 0
            if val > 0:
                base = val
    if base is None:
        move_points = getattr(mover, "move_points", None)
        if move_points is not None:
            try:
                val = int(move_points or 0) * 5
            except Exception:
                val = 0
            if val > 0:
                base = val
    if base is None:
        base = max(0, int(default_feet or 25))
    base += max(0, _stub_sum_status_int(mover, "base_speed_bonus_feet"))
    bonus = max(0, _stub_sum_status_int(mover, "speed_bonus_feet"))
    penalty = max(0, _stub_sum_status_int(mover, "speed_penalty_feet"))
    armor_penalty = 0
    for attr in ("armor_speed_penalty_feet", "speed_penalty_armor_feet"):
        raw = getattr(mover, attr, None)
        if raw is not None:
            try:
                armor_penalty = max(armor_penalty, max(0, int(raw or 0)))
            except Exception:
                continue
    if _stub_status_any_true(mover, "ignore_armor_move_penalty"):
        armor_penalty = 0
    reduction = _stub_max_status_int(mover, "magical_slow_reduction_feet")
    if reduction > 0 and penalty > 0:
        penalty = max(0, penalty - reduction)
    return max(0, int(base + bonus - penalty - armor_penalty))

_move_utils.movement_budget_feet = _stub_movement_budget_feet

def _stub_adjusted_forced_movement_squares(target, squares, *a, **k):
    base = max(0, int(squares or 0))
    if target is None or base <= 0:
        return base
    base_feet = base * 5
    multiplier = 1.0
    for status in getattr(target, "statuses", []) or []:
        data = getattr(status, "data", {}) or {}
        if "forced_movement_multiplier" not in data:
            continue
        threshold = int(data.get("forced_movement_threshold_feet", 0) or 0)
        if threshold > 0 and base_feet < threshold:
            continue
        multiplier = min(multiplier, float(data.get("forced_movement_multiplier", 1.0) or 1.0))
    return max(0, int(base_feet * multiplier) // 5)

_move_utils.adjusted_forced_movement_squares = _stub_adjusted_forced_movement_squares
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
