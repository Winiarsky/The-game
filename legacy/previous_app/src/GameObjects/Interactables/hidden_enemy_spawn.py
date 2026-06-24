from __future__ import annotations

from typing import Any

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin import HiddenMixin
from GameObjects.interactions_mixin.base_interaction import InteractableMixin


def _ensure_hidden_spawn_runtime(game) -> dict[str, Any]:
    runtime = getattr(game, "_hidden_spawn_runtime", None)
    if not isinstance(runtime, dict):
        runtime = {
            "first_blood_seen": False,
            "processing": False,
        }
        setattr(game, "_hidden_spawn_runtime", runtime)
    return runtime


def _living_heroes(game) -> list[object]:
    heroes: list[object] = []
    for hero in getattr(game, "heroes", []) or []:
        if getattr(hero, "position", None) is None:
            continue
        try:
            if int(getattr(hero, "hp", 1) or 0) <= 0:
                continue
        except Exception:
            pass
        checker = getattr(hero, "is_dead", None)
        if callable(checker):
            try:
                if bool(checker()):
                    continue
            except Exception:
                pass
        heroes.append(hero)
    return heroes


def _event_action_id(action_event: dict[str, Any] | None) -> str:
    return str((action_event or {}).get("action_id") or "").strip().lower()


def _event_action_tags(action_event: dict[str, Any] | None) -> set[str]:
    return {
        str(tag).strip().lower()
        for tag in list((action_event or {}).get("action_tags") or [])
        if str(tag).strip()
    }


def _event_damage_amount(action_event: dict[str, Any] | None) -> int:
    event = dict(action_event or {})
    for key in ("hp_dealt", "damage_dealt", "damage"):
        try:
            value = int(event.get(key, 0) or 0)
        except Exception:
            value = 0
        if value > 0:
            return value
    return 0


def _actor_matches_side(game, actor, side: str) -> bool:
    side_name = str(side or "any").strip().lower()
    if side_name == "any":
        return True
    if side_name == "heroes":
        return actor in getattr(game, "heroes", [])
    if side_name == "enemies":
        return actor in getattr(game, "enemies", [])
    return False


def _event_trap_id(action_event: dict[str, Any] | None) -> str:
    event = dict(action_event or {})
    explicit = str(event.get("trap_id") or "").strip()
    if explicit:
        return explicit
    target = event.get("target")
    for attr_name in ("object_id", "trap_name", "name"):
        value = str(getattr(target, attr_name, "") or "").strip()
        if value:
            return value
    return ""


def _condition_positions(trigger_conditions: tuple[dict[str, Any], ...]) -> tuple[tuple[int, int], ...]:
    positions: list[tuple[int, int]] = []
    for condition in trigger_conditions:
        if str(condition.get("kind") or "").strip().lower() != "position":
            continue
        for raw_pos in list(condition.get("positions") or []):
            positions.append(tuple(map(int, raw_pos)))
    return tuple(positions)


def _unique_hidden_spawns(game, *, preferred_group_id: str | None = None) -> list["HiddenEnemySpawn"]:
    board = getattr(game, "board", None)
    if board is None:
        return []
    groups: dict[str, HiddenEnemySpawn] = {}
    for row in range(getattr(board, "rows", 0)):
        for col in range(getattr(board, "cols", 0)):
            pos = (col, row)
            try:
                interactables = list(board.interactables_at(pos))
            except Exception:
                continue
            for obj in interactables:
                if not isinstance(obj, HiddenEnemySpawn):
                    continue
                if obj.spawned:
                    continue
                groups.setdefault(obj._group_key(), obj)
    ordered = list(groups.values())
    ordered.sort(
        key=lambda spawn: (
            0 if preferred_group_id and spawn._group_key() == preferred_group_id else 1,
            tuple(map(int, spawn.spawn_position or (-1, -1))),
            str(spawn.enemy_object_id),
        )
    )
    return ordered


class HiddenEnemySpawn(HiddenMixin, InteractableMixin):
    """Logiczny marker zasadzki, który po reveal tworzy realnego przeciwnika."""

    def __init__(
        self,
        *,
        enemy_object_id: str,
        enemy_config: dict[str, Any] | None = None,
        spawn_position: tuple[int, int] | list[int] | None = None,
        trigger_positions: list[list[int]] | list[tuple[int, int]] | tuple[tuple[int, int], ...] | None = None,
        trigger_conditions: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
        trigger_condition_mode: str = "any",
        ambush_mode: str = "join_end_of_round",
        spawn_group_id: str | None = None,
        reveal_dc: int = 18,
        reveal_tags: list[str] | tuple[str, ...] | None = None,
        trigger_mode: str = "seek",
        description_on_reveal: str | None = None,
    ) -> None:
        InteractableMixin.__init__(
            self,
            position=None,
            allow_same_cell_interact=False,
            allow_hidden_interaction=False,
            blocks_movement=False,
        )
        self.hidden = True
        self.revealed = False
        self.seekable = True
        self.enemy_object_id = str(enemy_object_id or "").strip()
        self.enemy_config = dict(enemy_config or {})
        raw_spawn = tuple(spawn_position or ())
        self.spawn_position = tuple(map(int, raw_spawn)) if raw_spawn else None
        self.trigger_positions = tuple(tuple(map(int, pos)) for pos in (trigger_positions or ()) if pos is not None)
        raw_conditions = list(trigger_conditions or ())
        if not raw_conditions and self.trigger_positions:
            raw_conditions = [
                {
                    "kind": "position",
                    "positions": [list(pos) for pos in self.trigger_positions],
                }
            ]
        self.trigger_conditions = tuple(dict(item) for item in raw_conditions)
        self.trigger_condition_mode = str(trigger_condition_mode or "any").strip().lower() or "any"
        self.ambush_mode = str(ambush_mode or "join_end_of_round").strip().lower() or "join_end_of_round"
        self.spawn_group_id = str(spawn_group_id or "").strip() or None
        self.reveal_dc = int(reveal_dc or 18)
        self.reveal_tags = tuple(reveal_tags or ())
        self.trigger_mode = str(trigger_mode or "seek")
        self.description_on_reveal = (
            str(description_on_reveal).strip()
            if description_on_reveal
            else "Zauważasz ukrytego przeciwnika gotowego do zasadzki."
        )
        self.spawned = False

    def _group_key(self) -> str:
        if self.spawn_group_id:
            return self.spawn_group_id
        if self.spawn_position is not None:
            return f"{self.enemy_object_id}:{self.spawn_position}"
        return f"{self.enemy_object_id}:{id(self)}"

    def _remove_group_aliases(self, game) -> None:
        board = getattr(game, "board", None)
        if board is None:
            return
        group_key = self._group_key()
        for row in range(getattr(board, "rows", 0)):
            for col in range(getattr(board, "cols", 0)):
                pos = (col, row)
                try:
                    interactables = list(board.interactables_at(pos))
                except Exception:
                    continue
                for obj in interactables:
                    if not isinstance(obj, HiddenEnemySpawn):
                        continue
                    if obj._group_key() != group_key:
                        continue
                    obj.hidden = False
                    obj.revealed = True
                    obj.spawned = True
                    try:
                        board.remove_interactable(obj, pos)
                    except Exception:
                        pass

    def _resolve_spawn_cell(self, game) -> tuple[int, int] | None:
        board = getattr(game, "board", None)
        if board is None or self.spawn_position is None:
            return None
        candidates = [self.spawn_position]
        try:
            neighbors = board.get_neighbors(self.spawn_position, include_position=False, diagonal=True)
        except Exception:
            neighbors = []
        candidates.extend(neighbors)
        for pos in candidates:
            try:
                if board.can_enter(pos, allow_occupied=False):
                    return pos
            except Exception:
                continue
        return None

    def _build_enemy(self, game):
        loader = getattr(game, "_encounter_build_object_instance", None)
        if callable(loader):
            return loader("Enemies", self.enemy_object_id, self.enemy_config)
        return None

    def _build_preview_enemy(self, game):
        enemy = self._build_enemy(game)
        if enemy is None:
            return None
        spawn_cell = self._resolve_spawn_cell(game)
        if spawn_cell is None:
            return None
        setter = getattr(enemy, "set_position", None)
        if callable(setter):
            try:
                setter(spawn_cell)
            except Exception:
                pass
        else:
            try:
                enemy.position = spawn_cell
            except Exception:
                pass
        return enemy

    def _active_weapon(self, enemy):
        from GameObjects.Enemies.behaviors.tactical_utils import best_weapon

        weapon_id = str(getattr(enemy, "active_weapon", "") or "").strip()
        if not weapon_id:
            return None
        return best_weapon(enemy, weapon_id=weapon_id)

    def _matches_condition(
        self,
        condition: dict[str, Any],
        game,
        *,
        source_actor=None,
        moved_position: tuple[int, int] | None = None,
        action_event: dict[str, Any] | None = None,
        first_blood_available: bool = False,
    ) -> bool:
        kind = str(condition.get("kind") or "").strip().lower()
        spawn_cell = self._resolve_spawn_cell(game)
        if spawn_cell is None:
            return False

        if kind == "position":
            targets = {
                tuple(map(int, pos))
                for pos in list(condition.get("positions") or [])
            }
            current_positions: set[tuple[int, int]] = set()
            if moved_position is not None:
                current_positions.add(tuple(map(int, moved_position)))
            if source_actor is not None and getattr(source_actor, "position", None) is not None:
                current_positions.add(tuple(map(int, source_actor.position)))
            event = dict(action_event or {})
            for key in ("to_pos", "pos"):
                raw = event.get(key)
                if isinstance(raw, (list, tuple)) and len(raw) == 2:
                    current_positions.add(tuple(map(int, raw)))
            return bool(targets & current_positions)

        if kind == "distance":
            from GameObjects.events.targeting import grid_distance_feet

            max_feet = int(condition.get("max_feet", 0) or 0)
            return any(grid_distance_feet(tuple(hero.position), spawn_cell) <= max_feet for hero in _living_heroes(game))

        if kind == "attackable":
            from GameObjects.Enemies.behaviors.tactical_utils import can_attack_from_position

            preview = self._build_preview_enemy(game)
            if preview is None:
                return False
            weapon = self._active_weapon(preview)
            if weapon is None:
                return False
            return any(can_attack_from_position(game, preview, hero, weapon, spawn_cell) for hero in _living_heroes(game))

        if kind == "walkable_distance":
            from GameObjects.Enemies.behaviors.tactical_utils import can_attack_from_position, reachable_positions

            preview = self._build_preview_enemy(game)
            if preview is None:
                return False
            weapon = self._active_weapon(preview)
            if weapon is None:
                return False
            move_actions = max(1, int(condition.get("max_move_actions", 0) or 0))
            stride_feet = int(getattr(preview, "distance", getattr(preview, "base_speed_feet", 25)) or 25)
            budget = max(5, move_actions * stride_feet)
            for hero in _living_heroes(game):
                if can_attack_from_position(game, preview, hero, weapon, spawn_cell):
                    return True
                reachable = reachable_positions(game, preview, max_feet=budget, include_current=True)
                for item in reachable:
                    pos = tuple(item.get("position"))
                    if can_attack_from_position(game, preview, hero, weapon, pos):
                        return True
            return False

        if kind == "first_blood":
            side = str(condition.get("side") or "any").strip().lower()
            if not first_blood_available:
                return False
            actor = (action_event or {}).get("actor")
            return _actor_matches_side(game, actor, side)

        if kind == "trap_activation":
            if _event_action_id(action_event) != "trap_activated":
                return False
            expected = str(condition.get("trap_id") or "").strip()
            return bool(expected) and _event_trap_id(action_event) == expected

        if kind == "action_id":
            return _event_action_id(action_event) == str(condition.get("value") or "").strip().lower()

        if kind == "action_tag":
            return str(condition.get("value") or "").strip().lower() in _event_action_tags(action_event)

        return False

    def conditions_satisfied(
        self,
        game,
        *,
        source_actor=None,
        moved_position: tuple[int, int] | None = None,
        action_event: dict[str, Any] | None = None,
        first_blood_available: bool = False,
    ) -> bool:
        if not self.trigger_conditions:
            return False
        results = [
            self._matches_condition(
                condition,
                game,
                source_actor=source_actor,
                moved_position=moved_position,
                action_event=action_event,
                first_blood_available=first_blood_available,
            )
            for condition in self.trigger_conditions
        ]
        if not results:
            return False
        if self.trigger_condition_mode == "all":
            return all(results)
        return any(results)

    def _prompt_physical_setup(self, game, position: tuple[int, int], enemy_name: str) -> None:
        try:
            from board import consts

            game.conn.set_leds([position], consts.HIDDEN_REVEAL_RGB)
            try:
                game.conn.scan_board([position])
            finally:
                game.conn.leds_off()
        except Exception:
            pass
        ui = getattr(game, "ui", None)
        prompt = f"Postaw figurkę {enemy_name} na polu {position}."
        if ui is not None and getattr(ui, "enabled", False) and hasattr(ui, "prompt_info"):
            try:
                ui.prompt_info("Zasadzka", prompt_long=prompt, source="hidden_enemy_spawn")
                return
            except Exception:
                pass
        try:
            game.ui_log(prompt)
        except Exception:
            pass

    def _attach_enemy_to_runtime(self, game, enemy, *, source_actor=None, reveal_reason: str = "trigger") -> None:
        state = getattr(game, "state", None)
        in_combat = getattr(state, "__class__", None).__name__ == "Combat"
        wants_interrupt = self.ambush_mode == "interrupt_action" and reveal_reason == "trigger"

        if not in_combat and wants_interrupt:
            starter = getattr(game, "start_combat", None)
            if callable(starter):
                try:
                    starter(trigger=enemy, preinitiative_pause=True)
                except TypeError:
                    starter(trigger=enemy)
            state = getattr(game, "state", None)
            in_combat = getattr(state, "__class__", None).__name__ == "Combat"

        if not in_combat:
            return

        resolver = getattr(state, "resolve_hidden_ambush_spawn", None)
        adder = getattr(state, "add_revealed_enemy", None)
        if wants_interrupt and callable(resolver):
            resolver(enemy, source_actor=source_actor)
            return
        if callable(adder):
            adder(enemy)

    def reveal_and_spawn(self, game, *, source_actor=None, reveal_reason: str = "trigger") -> str:
        group_key = self._group_key()
        already_spawned = getattr(game, "_hidden_spawn_groups_triggered", None)
        if already_spawned is None:
            already_spawned = set()
            setattr(game, "_hidden_spawn_groups_triggered", already_spawned)
        if group_key in already_spawned or self.spawned:
            self._remove_group_aliases(game)
            return "Zasadzka została już ujawniona."
        board = getattr(game, "board", None)
        if board is None:
            return "Brak planszy do ujawnienia przeciwnika."
        enemy = self._build_enemy(game)
        if enemy is None:
            return "Nie udało się utworzyć ukrytego przeciwnika."
        spawn_cell = self._resolve_spawn_cell(game)
        if spawn_cell is None:
            return "Brak wolnego pola do ujawnienia przeciwnika."
        try:
            board.place(enemy, spawn_cell)
        except Exception:
            return "Nie udało się ustawić przeciwnika na planszy."
        enemies = getattr(game, "enemies", None)
        if isinstance(enemies, list) and enemy not in enemies:
            enemies.append(enemy)
        self.hidden = False
        self.revealed = True
        self.spawned = True
        already_spawned.add(group_key)
        self._remove_group_aliases(game)
        enemy_name = str(getattr(enemy, "name", None) or self.enemy_object_id)
        self._prompt_physical_setup(game, spawn_cell, enemy_name)
        self._attach_enemy_to_runtime(game, enemy, source_actor=source_actor, reveal_reason=reveal_reason)
        return f"Zasadzka! {enemy_name} pojawia się na polu {spawn_cell}."

    def on_reveal(self, game, *, source_actor=None) -> str | None:
        return self.reveal_and_spawn(game, source_actor=source_actor, reveal_reason="seek")

    def on_enter(self, actor, game) -> str | None:
        if self.spawned:
            return None
        mode = str(self.trigger_mode or "").strip().lower()
        if mode not in {"on_enter", "seek_or_on_enter"}:
            return None
        outcome = evaluate_hidden_spawn_triggers(
            game,
            source_actor=actor,
            moved_position=getattr(self, "position", None) or getattr(actor, "position", None),
            preferred_group_id=self._group_key(),
        )
        if not outcome or outcome.get("group_key") != self._group_key():
            return None
        self.revealed = True
        return str(outcome.get("message") or "")


def evaluate_hidden_spawn_triggers(
    game,
    *,
    source_actor=None,
    moved_position: tuple[int, int] | None = None,
    action_event: dict[str, Any] | None = None,
    preferred_group_id: str | None = None,
) -> dict[str, Any] | None:
    board = getattr(game, "board", None)
    if board is None:
        return None
    runtime = _ensure_hidden_spawn_runtime(game)
    if runtime.get("processing"):
        return None
    current_event_is_first_blood = _event_damage_amount(action_event) > 0 and not bool(runtime.get("first_blood_seen", False))
    runtime["processing"] = True
    try:
        for spawn in _unique_hidden_spawns(game, preferred_group_id=preferred_group_id):
            if not spawn.conditions_satisfied(
                game,
                source_actor=source_actor,
                moved_position=moved_position,
                action_event=action_event,
                first_blood_available=current_event_is_first_blood,
            ):
                continue
            message = spawn.reveal_and_spawn(game, source_actor=source_actor, reveal_reason="trigger")
            return {
                "triggered": True,
                "message": message,
                "group_key": spawn._group_key(),
            }
        return None
    finally:
        if current_event_is_first_blood:
            runtime["first_blood_seen"] = True
        runtime["processing"] = False


def hidden_spawn_action_listener(game, action_event: dict[str, Any]) -> None:
    evaluate_hidden_spawn_triggers(game, source_actor=(action_event or {}).get("actor"), action_event=action_event)


META = GameObjectMeta(
    object_id="hidden_enemy_spawn",
    label="Ukryty spawn przeciwnika",
    color="#9b1d1d",
    category="Interactables",
    placement="cell",
    description="Sekretny punkt zasadzki ujawniający przeciwnika po Seek lub triggerze.",
    logic_cls=HiddenEnemySpawn,
    default_config={
        "enemy_object_id": "goblin_warrior",
        "enemy_config": {},
        "spawn_position": [0, 0],
        "trigger_positions": [[0, 0]],
        "trigger_conditions": [
            {
                "kind": "position",
                "positions": [[0, 0]],
            }
        ],
        "trigger_condition_mode": "any",
        "ambush_mode": "join_end_of_round",
        "spawn_group_id": "hidden_spawn:default",
        "reveal_dc": 18,
        "reveal_tags": [],
        "trigger_mode": "seek",
        "description_on_reveal": "Zauważasz ślady zasadzki.",
    },
)
