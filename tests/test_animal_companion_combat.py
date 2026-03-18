from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401

from GameObjects.companions import build_animal_companion
from GameObjects.events.base import EventContext
from GameObjects.events.registry import dispatch_event, list_events
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from board_grid import BoardGrid
from states.combat import Combat
from statuses.base import Status
from statuses.classes.druid.feats.animal_companion import AnimalCompanionStatus
from statuses.classes.ranger.feats.animal_companion import AnimalCompanionStatus as RangerAnimalCompanionStatus


class DummyConn:
    def __init__(self):
        self.scan_queue = []
        self.read_queue = []
        self.last_scan_options = None

    def set_leds(self, *_args, **_kwargs):
        return None

    def leds_off(self):
        return None

    def scan_board(self, acceptable_responses=None):
        self.last_scan_options = list(acceptable_responses) if acceptable_responses is not None else None
        if self.scan_queue:
            return self.scan_queue.pop(0)
        if acceptable_responses:
            return acceptable_responses[0]
        return None

    def read_card(self, *_args, **_kwargs):
        if self.read_queue:
            return self.read_queue.pop(0)
        return "end"


class DummyUI:
    enabled = False
    allow_cli_fallback = False

    def __init__(self):
        self.info_calls = []

    def prompt_info(self, title, **kwargs):
        self.info_calls.append({"title": title, **kwargs})
        return "ok"


class FakeEvents:
    def safe_emit_action(self, **_payload):
        return True


@dataclass
class DummyOwner(StatusMixin):
    name: str = "Druid"
    object_id: str = "hero-druid"
    position: tuple[int, int] | None = (0, 0)
    level: int = 1
    class_name: str = "druid"
    initiative: int | None = 12
    messages: list[str] = field(default_factory=list)
    wounds: int = 0

    def __hash__(self):
        return hash(self.object_id)

    def set_position(self, position):
        self.position = position

    def ui_log(self, message: str):
        self.messages.append(str(message))

    def roll_for_initiative(self):
        self.initiative = int(self.initiative or 12)
        return self.initiative

    def reset_reactions(self):
        return None

    def heal(self, amount: int):
        self.wounds = max(0, int(self.wounds) - max(0, int(amount)))
        return self.wounds


@dataclass
class DummyBlocker:
    object_id: str
    position: tuple[int, int] | None = None

    def set_position(self, position):
        self.position = position


@dataclass
class DummyEnemy:
    name: str = "Enemy"
    object_id: str = "enemy-1"
    position: tuple[int, int] | None = (0, 0)
    hp: int = 20
    ac: int = 14

    def __hash__(self):
        return hash(self.object_id)

    def set_position(self, position):
        self.position = position

    def apply_damage(self, amount: int, _damage_type: str = "normal"):
        self.hp -= int(amount)
        return self.hp, self.hp <= 0


class DummyGame:
    def __init__(self, board: BoardGrid, conn: DummyConn, ui: DummyUI | None = None):
        self.board = board
        self.conn = conn
        self.ui = ui if ui is not None else DummyUI()
        self.events = FakeEvents()
        self.heroes = []
        self.enemies = []
        self.state = None

    def ui_log(self, _msg: str, **_kwargs):
        return None

    def ui_event(self, *_args, **_kwargs):
        return None

    def ui_hero(self, *_args, **_kwargs):
        return None

    def ui_active_actor(self, *_args, **_kwargs):
        return None

    def ui_idle_hint(self, *_args, **_kwargs):
        return None


def _add_druid_animal_setup(owner: DummyOwner) -> None:
    owner.add_status(
        Status(
            id="druid",
            data={"druid_setup": {"order": "animal"}},
        )
    )
    owner.add_status(AnimalCompanionStatus())


def _add_ranger_animal_setup(owner: DummyOwner) -> None:
    owner.add_status(RangerAnimalCompanionStatus())


def test_command_animal_companion_registered():
    assert "command_animal_companion" in list_events()


def test_animal_companion_deploy_expands_radius_when_adjacent_blocked():
    board = BoardGrid(7, 7)
    conn = DummyConn()
    game = DummyGame(board=board, conn=conn)
    owner = DummyOwner(position=(3, 3), initiative=18)
    _add_druid_animal_setup(owner)
    game.heroes = [owner]
    board.place(owner, owner.position)

    ring1 = board.get_neighbors(owner.position, include_position=False, diagonal=True)
    for idx, pos in enumerate(ring1, start=1):
        board.place(DummyBlocker(object_id=f"b-{idx}"), pos)

    radius2_candidate = (5, 3)
    conn.scan_queue = [radius2_candidate]

    combat = Combat(game)
    game.state = combat
    combat._deploy_animal_companion_for_owner(owner)

    companion = combat.get_animal_companion(owner)
    assert companion is not None
    assert companion.position == radius2_candidate
    assert conn.last_scan_options is not None
    assert radius2_candidate in conn.last_scan_options
    assert all(
        max(abs(pos[0] - owner.position[0]), abs(pos[1] - owner.position[1])) >= 2
        for pos in conn.last_scan_options
    )


def test_command_animal_companion_strike_damages_enemy(monkeypatch):
    board = BoardGrid(6, 6)
    conn = DummyConn()
    game = DummyGame(board=board, conn=conn)
    owner = DummyOwner(position=(1, 1), initiative=17)
    _add_druid_animal_setup(owner)
    enemy = DummyEnemy(position=(2, 1), hp=20, ac=14)
    game.heroes = [owner]
    game.enemies = [enemy]
    board.place(owner, owner.position)
    board.place(enemy, enemy.position)

    combat = Combat(game)
    game.state = combat
    companion = build_animal_companion(owner, "wolf")
    board.place(companion, (1, 2))
    combat.animal_companions[owner.object_id] = companion

    conn.read_queue = ["strike", "end"]
    rolls = iter([24, 7])  # attack total, damage
    monkeypatch.setattr(
        "GameObjects.events.command_animal_companion_event.prompt_for_roll",
        lambda *_a, **_k: next(rolls),
    )

    result = dispatch_event("command_animal_companion", EventContext(game=game, actor=owner))

    assert result.success is True
    assert enemy.hp == 6
    assert owner.has_status("animal_companion_commanded")


def test_command_animal_companion_stride_moves_on_board(monkeypatch):
    board = BoardGrid(8, 8)
    conn = DummyConn()
    game = DummyGame(board=board, conn=conn)
    owner = DummyOwner(position=(1, 1), initiative=17)
    _add_druid_animal_setup(owner)
    game.heroes = [owner]
    board.place(owner, owner.position)

    combat = Combat(game)
    game.state = combat
    companion = build_animal_companion(owner, "wolf")
    board.place(companion, (1, 2))
    combat.animal_companions[owner.object_id] = companion
    conn.scan_queue = [(4, 2), (4, 2)]  # stride target + confirmation click

    from GameObjects.events.command_animal_companion_event import CommandAnimalCompanionEvent

    monkeypatch.setattr(
        "GameObjects.events.command_animal_companion_event.find_path",
        lambda *_a, **_k: [(1, 2), (2, 2), (3, 2), (4, 2)],
    )
    monkeypatch.setattr(
        "GameObjects.events.command_animal_companion_event.trim_path_to_feet",
        lambda path, *_a, **_k: list(path),
    )

    def _follow_path(_ctx, mover, path, **_kwargs):
        for prev, step in zip(path, path[1:]):
            board.move(prev, step)
        return True, path[-1], None

    monkeypatch.setattr(
        "GameObjects.events.command_animal_companion_event.follow_path",
        _follow_path,
    )

    result_ok, message = CommandAnimalCompanionEvent()._companion_stride(
        EventContext(game=game, actor=owner),
        owner,
        companion,
    )

    assert result_ok is True, message
    assert companion.position == (4, 2)


def test_command_animal_companion_precision_edge_applies_bonus_once(monkeypatch):
    board = BoardGrid(6, 6)
    conn = DummyConn()
    game = DummyGame(board=board, conn=conn)
    owner = DummyOwner(position=(1, 1), initiative=17)
    _add_druid_animal_setup(owner)
    enemy = DummyEnemy(position=(2, 1), hp=20, ac=14)
    game.heroes = [owner]
    game.enemies = [enemy]
    board.place(owner, owner.position)
    board.place(enemy, enemy.position)

    combat = Combat(game)
    game.state = combat
    companion = build_animal_companion(owner, "wolf")
    companion.ranger_hunter_edge = "precision"
    companion.ranger_hunted_prey_target_id = enemy.object_id
    board.place(companion, (1, 2))
    combat.animal_companions[owner.object_id] = companion

    conn.read_queue = ["strike", "end"]
    rolls = iter([18, 7, 4])  # attack total, base damage, precision damage
    monkeypatch.setattr(
        "GameObjects.events.command_animal_companion_event.prompt_for_roll",
        lambda *_a, **_k: next(rolls),
    )

    result = dispatch_event("command_animal_companion", EventContext(game=game, actor=owner))

    assert result.success is True
    assert enemy.hp == 9


def test_combat_cleanup_removes_companion_and_prompts_pickup():
    board = BoardGrid(6, 6)
    conn = DummyConn()
    ui = DummyUI()
    game = DummyGame(board=board, conn=conn, ui=ui)
    owner = DummyOwner(position=(1, 1), initiative=17)
    _add_druid_animal_setup(owner)
    game.heroes = [owner]
    board.place(owner, owner.position)

    combat = Combat(game)
    game.state = combat
    companion = build_animal_companion(owner, "wolf")
    board.place(companion, (2, 1))
    combat.animal_companions[owner.object_id] = companion

    combat._cleanup_animal_companions()

    assert companion.position is None
    assert len(ui.info_calls) == 1
    assert "zabierz figurke" in str(ui.info_calls[0].get("prompt_long") or "").lower()


def test_combat_deploys_two_animal_companions_for_distinct_owners():
    board = BoardGrid(8, 8)
    conn = DummyConn()
    game = DummyGame(board=board, conn=conn)
    druid = DummyOwner(name="Druid", object_id="hero-druid", position=(1, 1), initiative=18, class_name="druid")
    ranger = DummyOwner(name="Ranger", object_id="hero-ranger", position=(5, 1), initiative=16, class_name="ranger")
    _add_druid_animal_setup(druid)
    _add_ranger_animal_setup(ranger)
    game.heroes = [druid, ranger]
    board.place(druid, druid.position)
    board.place(ranger, ranger.position)
    conn.scan_queue = [(1, 2), (5, 2)]

    combat = Combat(game)
    game.state = combat
    combat._deploy_pending_animal_companions()

    druid_companion = combat.get_animal_companion(druid)
    ranger_companion = combat.get_animal_companion(ranger)

    assert druid_companion is not None
    assert ranger_companion is not None
    assert druid_companion is not ranger_companion
    assert druid_companion.owner_id == druid.object_id
    assert ranger_companion.owner_id == ranger.object_id
    assert druid_companion.position == (1, 2)
    assert ranger_companion.position == (5, 2)
    assert len(combat.animal_companions) == 2


def test_command_animal_companion_uses_owner_specific_companion_when_multiple_exist(monkeypatch):
    board = BoardGrid(8, 8)
    conn = DummyConn()
    game = DummyGame(board=board, conn=conn)
    monkeypatch.setattr("ui_client.get_ui_client", lambda: DummyUI())
    druid = DummyOwner(name="Druid", object_id="hero-druid", position=(1, 1), initiative=18, class_name="druid")
    ranger = DummyOwner(name="Ranger", object_id="hero-ranger", position=(5, 1), initiative=16, class_name="ranger")
    _add_druid_animal_setup(druid)
    _add_ranger_animal_setup(ranger)
    enemy = DummyEnemy(position=(5, 3), hp=20, ac=14)
    game.heroes = [druid, ranger]
    game.enemies = [enemy]
    board.place(druid, druid.position)
    board.place(ranger, ranger.position)
    board.place(enemy, enemy.position)

    combat = Combat(game)
    game.state = combat
    druid_companion = build_animal_companion(druid, "wolf")
    ranger_companion = build_animal_companion(ranger, "wolf")
    board.place(druid_companion, (1, 2))
    board.place(ranger_companion, (5, 2))
    combat.animal_companions[druid.object_id] = druid_companion
    combat.animal_companions[ranger.object_id] = ranger_companion

    conn.read_queue = ["strike", "end", "strike", "end"]
    rolls = iter([24, 7])
    monkeypatch.setattr(
        "GameObjects.events.command_animal_companion_event.prompt_for_roll",
        lambda *_a, **_k: next(rolls),
    )

    ranger_result = dispatch_event("command_animal_companion", EventContext(game=game, actor=ranger))
    druid_result = dispatch_event("command_animal_companion", EventContext(game=game, actor=druid))

    assert ranger_result.success is True
    assert enemy.hp == 6
    assert ranger.has_status("animal_companion_commanded")
    assert druid.has_status("animal_companion_commanded") is False
    assert druid_result.success is False
    assert "nie wykonal zadnej akcji" in str(druid_result.message or "").lower()


def test_round_based_wolf_support_ticks_once_per_combat_round():
    board = BoardGrid(6, 6)
    conn = DummyConn()
    game = DummyGame(board=board, conn=conn)
    owner = DummyOwner(name="Druid", object_id="hero-druid", position=(1, 1), initiative=18, class_name="druid")
    enemy = DummyOwner(name="Enemy", object_id="enemy-1", position=(2, 1), initiative=12, class_name="enemy")
    game.heroes = [owner]
    game.enemies = [enemy]
    board.place(owner, owner.position)
    board.place(enemy, enemy.position)

    combat = Combat(game)
    game.state = combat
    combat.base_order = [owner, enemy]
    combat.round_queue = [owner, enemy]
    combat.initiative_order = [owner, enemy]

    enemy.add_status(
        Status(
            id="speed_penalty",
            label="Wolf Support -5ft",
            source="animal_companion_support:wolf",
            stacks=True,
            data={
                "speed_penalty_feet": 5,
                "source_id": owner.object_id,
                "effect_tags": ["speed_penalty"],
                "combat_rounds_left": 10,
                "expire_on_combat_end": True,
            },
        )
    )

    combat._advance_turn()
    penalty = enemy.get_status("speed_penalty")
    assert penalty is not None
    assert int((penalty.data or {}).get("combat_rounds_left", 0) or 0) == 10

    combat._advance_turn()
    penalty = enemy.get_status("speed_penalty")
    assert penalty is not None
    assert int((penalty.data or {}).get("combat_rounds_left", 0) or 0) == 9

    for _ in range(9):
        combat._tick_combat_round_statuses()

    assert enemy.get_status("speed_penalty") is None


def test_combat_exit_clears_round_based_wolf_support_status():
    board = BoardGrid(6, 6)
    conn = DummyConn()
    game = DummyGame(board=board, conn=conn)
    owner = DummyOwner(name="Druid", object_id="hero-druid", position=(1, 1), initiative=18, class_name="druid")
    enemy = DummyOwner(name="Enemy", object_id="enemy-1", position=(2, 1), initiative=12, class_name="enemy")
    game.heroes = [owner]
    game.enemies = [enemy]
    board.place(owner, owner.position)
    board.place(enemy, enemy.position)

    combat = Combat(game)
    game.state = combat

    enemy.add_status(
        Status(
            id="speed_penalty",
            label="Wolf Support -5ft",
            source="animal_companion_support:wolf",
            stacks=True,
            data={
                "speed_penalty_feet": 5,
                "source_id": owner.object_id,
                "effect_tags": ["speed_penalty"],
                "combat_rounds_left": 10,
                "expire_on_combat_end": True,
            },
        )
    )

    combat.on_exit()

    assert enemy.get_status("speed_penalty") is None
