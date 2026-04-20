from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import random
from types import SimpleNamespace
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.Enemies.goblin_warrior import GoblinWarrior
from GameObjects.Interactables.hidden_enemy_spawn import HiddenEnemySpawn, evaluate_hidden_spawn_triggers
from GameObjects.events.base import EventContext
from GameObjects.events.seek_event import SeekEvent
from board_grid import BoardGrid
from encounters import EncounterDirectives, EncounterRequest, FixedEnemyDirective, generate_encounter, preset_directives
from encounters.generator import (
    PRESETS_DIR,
    FormationShape,
    _choose_formations,
    _layout_templates,
    _stamp_formation_geometry,
)
from game import Game
from states.combat import Combat
from states.encounter_setup import EncounterSetupState
from states.encounter_finished import EncounterFinished


@dataclass(eq=False)
class DummyHero:
    name: str = "Cedric"
    object_id: str = "hero-enc"
    position: tuple[int, int] | None = None
    initiative: int | None = None
    ac: int = 16
    hp: int = 20
    max_hp: int = 20
    statuses: list = field(default_factory=list)
    bonuses: list = field(default_factory=list)

    def set_position(self, position):
        self.position = position

    def roll_for_initiative(self):
        self.initiative = 15
        return self.initiative

    def has_status(self, status_id: str) -> bool:
        return any(getattr(item, "id", item) == status_id for item in self.statuses)

    def add_status(self, status):
        self.statuses.append(status)
        return True

    def remove_status(self, status_id: str):
        before = len(self.statuses)
        self.statuses = [item for item in self.statuses if getattr(item, "id", item) != status_id]
        return len(self.statuses) != before


class DummyConn:
    def __init__(self, *, clicks=None):
        self.clicks = list(clicks or [])
        self.led_calls = []

    def set_leds(self, positions, colors):
        self.led_calls.append((list(positions), colors))

    def scan_board(self, positions=None):
        if self.clicks:
            return self.clicks.pop(0)
        if isinstance(positions, list) and positions:
            return positions[0]
        return None

    def leds_off(self):
        return None


class DummyEvents:
    def safe_emit_action(self, **_kwargs):
        return None


@pytest.fixture(autouse=True)
def _disable_debug_trace(monkeypatch):
    monkeypatch.setenv("GAME_DEBUG_TRACE", "0")


def test_generate_encounter_is_deterministic_budgeted_and_respects_directives():
    request = EncounterRequest(
        biome="forest",
        threat="moderate",
        seed=1234,
        formation_pack="fortifications",
        directives=EncounterDirectives(
            must_include=("goblin_warrior",),
            fixed_enemies=(FixedEnemyDirective(enemy_object_id="goblin_dog", position=(18, 10)),),
            forbidden_cells=((19, 14),),
            preferred_layout="open_field",
        ),
    )

    first = generate_encounter(request)
    second = generate_encounter(request)

    assert first.scenario_payload == second.scenario_payload
    assert first.metadata["xp_total"] <= first.metadata["xp_budget"]
    assert first.metadata["formation_pack"] == "fortifications"
    assert first.metadata["formations_used"] == second.metadata["formations_used"]

    enemies = [
        obj for obj in first.scenario_payload["objects"]
        if obj.get("category") == "Enemies"
    ]
    enemy_instances = {
        obj["object_id"]: [tuple(inst["position"]) for inst in obj.get("instances") or []]
        for obj in enemies
    }
    assert (18, 10) in enemy_instances["goblin_dog"]
    assert enemy_instances["goblin_warrior"]
    all_positions = {pos for positions in enemy_instances.values() for pos in positions}
    assert (19, 14) not in all_positions


def test_stamp_formation_geometry_translates_and_rotates_consistently():
    shape = FormationShape(
        shape_id="test_shape",
        obstacles=((0, 0), (1, 0), (1, 1)),
        walls=(((0, 0), (0, 1)),),
    )

    stamped = _stamp_formation_geometry(shape, anchor=(5, 6), rotation=1)

    assert set(stamped["obstacles"]) == {(5, 7), (5, 6), (6, 6)}
    assert stamped["walls"] == (((5, 7), (6, 7)),)


def test_commando_ambush_preset_is_loaded_from_json():
    assert (PRESETS_DIR / "commando_ambush.json").exists()
    directives = preset_directives("commando_ambush")

    assert directives.preset_id == "commando_ambush"
    assert directives.must_include == ("goblin_commando",)
    assert directives.fixed_enemies
    assert directives.fixed_enemies[0].enemy_object_id == "goblin_commando"
    assert directives.fixed_enemies[0].hidden is True
    assert directives.fixed_enemies[0].trigger_positions == ()
    assert directives.fixed_enemies[0].ambush_mode == "interrupt_action"
    assert directives.fixed_enemies[0].trigger_conditions == (
        {"kind": "attackable", "weapon_scope": "active"},
    )


@pytest.mark.parametrize("layout_id", ["open_field", "split_lanes", "chokepoints"])
@pytest.mark.parametrize("formation_pack", ["fortifications", "ruins", "serpentine"])
def test_every_formation_pack_works_on_every_layout(layout_id, formation_pack):
    resolved = generate_encounter(
        EncounterRequest(
            biome="ruined_village" if formation_pack == "ruins" else "forest",
            threat="moderate",
            seed=20260406,
            formation_pack=formation_pack,
            directives=EncounterDirectives(preferred_layout=layout_id),
        )
    )

    assert resolved.metadata["layout"] == layout_id
    assert resolved.metadata["formation_pack"] == formation_pack
    assert len(resolved.metadata["formations_used"]) == 2


def test_formations_do_not_overlap_hero_or_enemy_slots():
    request = EncounterRequest(
        biome="forest",
        threat="moderate",
        seed=777,
        formation_pack="serpentine",
        directives=EncounterDirectives(preferred_layout="split_lanes"),
    )
    layout = _layout_templates()["split_lanes"]
    formations = _choose_formations(request, layout, "serpentine", random.Random(request.seed))

    occupied = set(layout.hero_starts) | set(layout.enemy_positions) | set(layout.hidden_enemy_positions)
    formation_cells = set()
    for formation in formations:
        formation_cells.update(formation.obstacles)
        formation_cells.update(formation.cover)
        formation_cells.update(formation.difficult)
        formation_cells.update(formation.rubble)
        formation_cells.update(point for edge in formation.walls for point in edge)

    assert formation_cells.isdisjoint(occupied)


def test_hidden_enemy_spawn_reveals_via_seek_and_joins_combat_queue(monkeypatch):
    board = BoardGrid(rows=5, cols=5)
    board.apply_rooms([{"id": "encounter_zone", "positions": [(col, row) for row in range(5) for col in range(5)]}])
    hero = DummyHero(position=(1, 1))
    visible_enemy = GoblinWarrior(name="Visible Warrior", position=(4, 4))
    board.place(hero, hero.position)
    board.place(visible_enemy, visible_enemy.position)
    hidden_spawn = HiddenEnemySpawn(
        enemy_object_id="goblin_warrior",
        enemy_config={"name": "Ambusher"},
        spawn_position=(3, 1),
        reveal_dc=18,
        reveal_tags=("undetected",),
        trigger_mode="seek_or_on_enter",
        description_on_reveal="Ślady zasadzki.",
    )
    board.add_interactable(hidden_spawn, (3, 1))

    game = SimpleNamespace(
        board=board,
        conn=DummyConn(clicks=[(3, 1)]),
        heroes=[hero],
        enemies=[visible_enemy],
        events=DummyEvents(),
        ui=None,
        ui_log=lambda *_args, **_kwargs: None,
        ui_event=lambda *_args, **_kwargs: None,
        ui_hero=lambda *_args, **_kwargs: None,
        ui_active_actor=lambda *_args, **_kwargs: None,
    )
    game._build_object_registry = Game._build_object_registry.__get__(game, SimpleNamespace)
    game._encounter_build_object_instance = Game._encounter_build_object_instance.__get__(game, SimpleNamespace)
    combat = Combat(game)
    game.state = combat
    combat._initiatives_ready = True
    combat.base_initiative = {visible_enemy: 12, hero: 15}
    combat.base_order = [hero, visible_enemy]
    combat.round_queue = [hero, visible_enemy]
    combat.initiative_order = list(combat.round_queue)

    monkeypatch.setattr(
        "GameObjects.events.seek_event.check_resolver.resolve_skill_check_with_sources",
        lambda **_k: SimpleNamespace(outcome="success", roll=14, total=23),
    )
    monkeypatch.setattr(
        "GameObjects.events.seek_event.check_resolver.resolve_skill_check_with_sources_from_roll",
        lambda **_k: SimpleNamespace(outcome="success", total=23),
    )

    result = SeekEvent().run(EventContext(game=game, actor=hero))

    assert result.success is True
    assert any(getattr(enemy, "name", "") == "Ambusher" for enemy in game.enemies)
    assert hidden_spawn.spawned is True
    assert combat.round_queue[-1] in game.enemies


def test_hidden_enemy_spawn_trigger_positions_can_share_one_spawn_group():
    board = BoardGrid(rows=5, cols=5)
    hero = DummyHero(position=(1, 1))
    board.place(hero, hero.position)

    first_trigger = HiddenEnemySpawn(
        enemy_object_id="goblin_warrior",
        enemy_config={"name": "Shared Ambusher"},
        spawn_position=(3, 1),
        trigger_positions=((2, 1), (2, 2)),
        spawn_group_id="ambush:test",
        trigger_mode="seek_or_on_enter",
    )
    second_trigger = HiddenEnemySpawn(
        enemy_object_id="goblin_warrior",
        enemy_config={"name": "Shared Ambusher"},
        spawn_position=(3, 1),
        trigger_positions=((2, 1), (2, 2)),
        spawn_group_id="ambush:test",
        trigger_mode="seek_or_on_enter",
    )
    board.add_interactable(first_trigger, (2, 1))
    board.add_interactable(second_trigger, (2, 2))

    game = SimpleNamespace(
        board=board,
        conn=DummyConn(),
        heroes=[hero],
        enemies=[],
        events=DummyEvents(),
        ui=None,
        ui_log=lambda *_args, **_kwargs: None,
        ui_event=lambda *_args, **_kwargs: None,
        ui_hero=lambda *_args, **_kwargs: None,
        ui_active_actor=lambda *_args, **_kwargs: None,
    )
    game._build_object_registry = Game._build_object_registry.__get__(game, SimpleNamespace)
    game._encounter_build_object_instance = Game._encounter_build_object_instance.__get__(game, SimpleNamespace)

    message = second_trigger.on_enter(hero, game)

    assert message
    assert len(game.enemies) == 1
    assert game.enemies[0].position == (3, 1)
    assert board.interactables_at((2, 1)) == []
    assert board.interactables_at((2, 2)) == []


def test_hidden_enemy_spawn_attackable_uses_active_weapon_only():
    board = BoardGrid(rows=8, cols=8)
    hero = DummyHero(position=(6, 1))
    board.place(hero, hero.position)
    game = SimpleNamespace(
        board=board,
        conn=DummyConn(),
        heroes=[hero],
        enemies=[],
        events=DummyEvents(),
        ui=None,
        ui_log=lambda *_args, **_kwargs: None,
        ui_event=lambda *_args, **_kwargs: None,
        ui_hero=lambda *_args, **_kwargs: None,
        ui_active_actor=lambda *_args, **_kwargs: None,
    )
    game._build_object_registry = Game._build_object_registry.__get__(game, SimpleNamespace)
    game._encounter_build_object_instance = Game._encounter_build_object_instance.__get__(game, SimpleNamespace)

    melee_only = HiddenEnemySpawn(
        enemy_object_id="goblin_warrior",
        enemy_config={"active_weapon": "dogslicer"},
        spawn_position=(1, 1),
        trigger_conditions=({"kind": "attackable", "weapon_scope": "active"},),
    )
    ranged_active = HiddenEnemySpawn(
        enemy_object_id="goblin_warrior",
        enemy_config={"active_weapon": "shortbow"},
        spawn_position=(1, 1),
        trigger_conditions=({"kind": "attackable", "weapon_scope": "active"},),
    )

    assert melee_only.conditions_satisfied(game) is False
    assert ranged_active.conditions_satisfied(game) is True


def test_hidden_spawn_first_blood_triggers_only_once():
    board = BoardGrid(rows=6, cols=6)
    hero = DummyHero(position=(1, 1))
    board.place(hero, hero.position)
    first = HiddenEnemySpawn(
        enemy_object_id="goblin_warrior",
        enemy_config={"name": "First Blood A"},
        spawn_position=(3, 1),
        trigger_conditions=({"kind": "first_blood", "side": "heroes"},),
        spawn_group_id="blood:a",
    )
    second = HiddenEnemySpawn(
        enemy_object_id="goblin_warrior",
        enemy_config={"name": "First Blood B"},
        spawn_position=(4, 1),
        trigger_conditions=({"kind": "first_blood", "side": "heroes"},),
        spawn_group_id="blood:b",
    )
    board.add_interactable(first, (3, 1))
    board.add_interactable(second, (4, 1))
    game = SimpleNamespace(
        board=board,
        conn=DummyConn(),
        heroes=[hero],
        enemies=[],
        events=DummyEvents(),
        ui=None,
        ui_log=lambda *_args, **_kwargs: None,
        ui_event=lambda *_args, **_kwargs: None,
        ui_hero=lambda *_args, **_kwargs: None,
        ui_active_actor=lambda *_args, **_kwargs: None,
    )
    game._build_object_registry = Game._build_object_registry.__get__(game, SimpleNamespace)
    game._encounter_build_object_instance = Game._encounter_build_object_instance.__get__(game, SimpleNamespace)

    first_event = {"action_id": "damage_applied", "actor": hero, "damage": 4, "action_tags": ["damage"]}
    second_event = {"action_id": "damage_applied", "actor": hero, "damage": 3, "action_tags": ["damage"]}

    first_result = evaluate_hidden_spawn_triggers(game, source_actor=hero, action_event=first_event)
    second_result = evaluate_hidden_spawn_triggers(game, source_actor=hero, action_event=second_event)

    assert first_result is not None
    assert len(game.enemies) == 1
    assert second_result is None


def test_hidden_spawn_trap_activation_matches_trap_id():
    board = BoardGrid(rows=6, cols=6)
    hero = DummyHero(position=(1, 1))
    board.place(hero, hero.position)
    hidden = HiddenEnemySpawn(
        enemy_object_id="goblin_warrior",
        enemy_config={"name": "Trap Ambusher"},
        spawn_position=(3, 1),
        trigger_conditions=({"kind": "trap_activation", "trap_id": "dart_launcher_trap"},),
    )
    board.add_interactable(hidden, (3, 1))
    game = SimpleNamespace(
        board=board,
        conn=DummyConn(),
        heroes=[hero],
        enemies=[],
        events=DummyEvents(),
        ui=None,
        ui_log=lambda *_args, **_kwargs: None,
        ui_event=lambda *_args, **_kwargs: None,
        ui_hero=lambda *_args, **_kwargs: None,
        ui_active_actor=lambda *_args, **_kwargs: None,
    )
    game._build_object_registry = Game._build_object_registry.__get__(game, SimpleNamespace)
    game._encounter_build_object_instance = Game._encounter_build_object_instance.__get__(game, SimpleNamespace)

    miss = evaluate_hidden_spawn_triggers(
        game,
        source_actor=hero,
        action_event={"action_id": "trap_activated", "actor": hero, "trap_id": "other_trap", "action_tags": ["trap", "trigger"]},
    )
    hit = evaluate_hidden_spawn_triggers(
        game,
        source_actor=hero,
        action_event={"action_id": "trap_activated", "actor": hero, "trap_id": "dart_launcher_trap", "action_tags": ["trap", "trigger"]},
    )

    assert miss is None
    assert hit is not None
    assert len(game.enemies) == 1


def test_hidden_enemy_spawn_interrupt_action_adds_enemy_next_round(monkeypatch):
    board = BoardGrid(rows=6, cols=6)
    hero = DummyHero(position=(1, 1))
    visible_enemy = GoblinWarrior(name="Visible Warrior", position=(4, 4))
    board.place(hero, hero.position)
    board.place(visible_enemy, visible_enemy.position)
    hidden_spawn = HiddenEnemySpawn(
        enemy_object_id="goblin_warrior",
        enemy_config={"name": "Ambusher"},
        spawn_position=(3, 1),
        ambush_mode="interrupt_action",
        trigger_conditions=({"kind": "position", "positions": [[2, 1]]},),
        trigger_mode="seek_or_on_enter",
    )
    board.add_interactable(hidden_spawn, (2, 1))

    game = SimpleNamespace(
        board=board,
        conn=DummyConn(),
        heroes=[hero],
        enemies=[visible_enemy],
        events=DummyEvents(),
        ui=None,
        ui_log=lambda *_args, **_kwargs: None,
        ui_event=lambda *_args, **_kwargs: None,
        ui_hero=lambda *_args, **_kwargs: None,
        ui_active_actor=lambda *_args, **_kwargs: None,
    )
    game._build_object_registry = Game._build_object_registry.__get__(game, SimpleNamespace)
    game._encounter_build_object_instance = Game._encounter_build_object_instance.__get__(game, SimpleNamespace)
    combat = Combat(game)
    game.state = combat
    combat._initiatives_ready = True
    combat.base_initiative = {visible_enemy: 12, hero: 15}
    combat.base_order = [hero, visible_enemy]
    combat.round_queue = [hero, visible_enemy]
    combat.initiative_order = list(combat.round_queue)

    def _fake_behavior(enemy, _game, _combat_state, actions_left=1):
        enemy.ai_memory["ambush_used"] = actions_left
        return 1

    monkeypatch.setattr("states.combat.get_behavior", lambda _behavior_id: _fake_behavior)

    message = hidden_spawn.on_enter(hero, game)
    spawned_enemy = next(enemy for enemy in game.enemies if getattr(enemy, "name", "") == "Ambusher")

    assert message
    assert spawned_enemy.ai_memory["ambush_used"] == 1
    assert spawned_enemy in combat.base_order
    assert spawned_enemy not in combat.round_queue


def test_generated_encounter_game_flows_setup_to_combat_and_finish(monkeypatch):
    resolved = generate_encounter(
        EncounterRequest(
            biome="ruined_village",
            threat="low",
            seed=2024,
            formation_pack="ruins",
            directives=EncounterDirectives(preferred_layout="split_lanes"),
        )
    )
    payload = dict(resolved.scenario_payload)
    payload["setup_plan"] = []
    start_pos = tuple(payload["starting_positions"][0])
    conn = DummyConn(clicks=[start_pos, start_pos])
    game = Game(conn=conn, scenario="__procedural__", scenario_payload=payload, scenario_label="test encounter")
    game.ui_log = lambda *_args, **_kwargs: None
    game.ui_event = lambda *_args, **_kwargs: False
    game.ui_hero = lambda *_args, **_kwargs: None
    game.ui_active_actor = lambda *_args, **_kwargs: None

    monkeypatch.setattr(
        "states.start.Start._pick_or_create_hero",
        lambda self, _used: DummyHero(),
    )
    monkeypatch.setattr(
        "states.start.Start._prompt_menu_choice",
        lambda self, **kwargs: "__start_game__" if kwargs.get("source") == "hero_setup_next" else None,
    )

    game.run_action("run_encounter_setup")

    assert isinstance(game.state, Combat)
    assert game.heroes

    game.enemies.clear()
    game.run_action("choose_action")

    assert isinstance(game.state, EncounterFinished)


def test_combine_positions_deduplicates_cells_preserving_order():
    from encounters.generator import _combine_positions

    formations = (
        SimpleNamespace(cover=((3, 4), (1, 2)), difficult=(), rubble=(), obstacles=()),
        SimpleNamespace(cover=((5, 6),), difficult=(), rubble=(), obstacles=()),
    )

    combined = _combine_positions(((1, 2), (3, 4), (1, 2)), formations, "cover")

    assert combined == [[1, 2], [3, 4], [5, 6]]


def test_encounter_setup_click_all_removes_all_duplicate_pending_cells():
    state = EncounterSetupState.__new__(EncounterSetupState)

    positions = state._unique_positions([(10, 2), (10, 2), (11, 10), (10, 1), (11, 10)])

    assert positions == [(10, 2), (11, 10), (10, 1)]


def test_commando_ambush_remains_compatible_with_formation_packs():
    directives = preset_directives("commando_ambush")
    resolved = generate_encounter(
        EncounterRequest(
            biome="forest",
            threat="severe",
            seed=4242,
            formation_pack="fortifications",
            directives=EncounterDirectives(
                must_include=directives.must_include,
                fixed_enemies=directives.fixed_enemies,
                forbidden_cells=directives.forbidden_cells,
                preferred_layout="chokepoints",
                preset_id=directives.preset_id,
            ),
        )
    )

    assert resolved.metadata["formation_pack"] == "fortifications"
    assert any(spec.enemy_object_id == "goblin_commando" for spec in resolved.hidden_spawns)
