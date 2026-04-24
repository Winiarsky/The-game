from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from GameObjects.events.base import EventContext
from GameObjects.events.magic.level_1st import events as occ1
from GameObjects.events.magic.spell_types import SpellTradition
from bonuses import BonusEffect, BonusType
from statuses.base import Status


class DummyConn:
    def __init__(self):
        self.led_calls = []
        self.scan_inputs = []

    def set_leds(self, _positions, _colors):
        self.led_calls.append((list(_positions), list(_colors)))
        return None

    def scan_board(self, _positions):
        self.scan_inputs.append(None if _positions is None else list(_positions))
        return None

    def leds_off(self):
        return None


class ClickSequenceConn(DummyConn):
    def __init__(self, clicks):
        super().__init__()
        self.clicks = list(clicks)

    def scan_board(self, positions):
        self.scan_inputs.append(None if positions is None else list(positions))
        if self.clicks:
            return self.clicks.pop(0)
        return None


class DummyBoard:
    def __init__(self, rows=8, cols=8, interactables=None):
        self.rows = rows
        self.cols = cols
        self._interactables = dict(interactables or {})
        self._fields = {}
        self._occupants = {}
        self._walls = set()

    def interactables_at(self, pos):
        return list(self._interactables.get(pos, []))

    def cell_at(self, pos):
        return SimpleNamespace(
            field=self._fields.get(pos, SimpleNamespace(name="basic", walkable=True)),
            interactables=list(self._interactables.get(pos, [])),
            occupant=self._occupants.get(pos),
        )

    def set_field(self, pos, terrain):
        self._fields[pos] = terrain

    def add_wall(self, a, b):
        self._walls.add(frozenset((a, b)))

    def is_blocked(self, a, b):
        return frozenset((a, b)) in self._walls

    def edge_interactables_between(self, a, b):
        return []

    def in_bounds(self, pos):
        x, y = pos
        return 0 <= x < self.cols and 0 <= y < self.rows

    def get_neighbors(self, pos, include_position=False, diagonal=True):
        x, y = pos
        out = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                if not diagonal and abs(dx) + abs(dy) != 1:
                    continue
                cand = (x + dx, y + dy)
                if self.in_bounds(cand):
                    out.append(cand)
        if include_position:
            out.append(pos)
        return out

    def can_traverse(self, src, dst, allow_occupied=False):
        return self.in_bounds(src) and self.in_bounds(dst) and not self.is_blocked(src, dst) and self.can_enter(dst, allow_occupied=allow_occupied)

    def can_enter(self, pos, allow_occupied=False):
        if not self.in_bounds(pos):
            return False
        return bool(getattr(self._fields.get(pos, SimpleNamespace(walkable=True)), "walkable", True))

    def move(self, source, target):
        return None


class DummyActor:
    def __init__(self, name="actor", position=(0, 0), hp=20, object_id=None):
        self.name = name
        self.object_id = object_id or name
        self.position = position
        self.hp = hp
        self.wounds = 0
        self.statuses = []
        self.bonuses = []

    def __hash__(self):
        return hash(self.object_id)

    def add_status(self, status):
        self.statuses.append(status)
        return True

    def remove_status(self, status):
        sid = getattr(status, "id", status)
        for i, item in enumerate(list(self.statuses)):
            if getattr(item, "id", item) == sid:
                del self.statuses[i]
                return True
        return False

    def has_status(self, status):
        sid = getattr(status, "id", status)
        return any(getattr(s, "id", s) == sid for s in self.statuses)

    def add_bonus(self, effect):
        self.bonuses.append(effect)

    def remove_bonuses_with_prefix(self, prefix):
        self.bonuses = [b for b in self.bonuses if not (getattr(b, "source", "") or "").startswith(prefix)]

    def apply_damage(self, amount, _damage_type="normal"):
        self.hp -= int(amount)
        self.wounds += int(amount)
        return self.hp, self.hp <= 0

    def heal(self, amount):
        self.hp += int(amount)
        self.wounds = max(0, self.wounds - int(amount))
        return self.hp


class DummyInteractable:
    def __init__(self):
        self.locked = False
        self.is_open = True
        self.jammed = True
        self.thievery_dc = 15


def _game(*, actor, enemies=None, heroes=None, board=None):
    logs = []
    game = SimpleNamespace(
        board=board or DummyBoard(),
        conn=DummyConn(),
        heroes=list(heroes if heroes is not None else [actor]),
        enemies=list(enemies or []),
        ui=SimpleNamespace(prompt_choice=lambda *a, **k: None, enabled=False, allow_cli_fallback=False),
        ui_log=lambda msg: logs.append(str(msg)),
        _logs=logs,
    )
    actor.game = game
    for h in game.heroes:
        h.game = game
    for e in game.enemies:
        e.game = game
    return game


def test_bless_and_bane_apply_expected_bonuses():
    caster = DummyActor("caster", (0, 0))
    ally = DummyActor("ally", (1, 0))
    enemy = DummyActor("enemy", (1, 1))
    game = _game(actor=caster, heroes=[caster, ally], enemies=[enemy])

    bless = occ1.BlessEvent().execute(EventContext(game=game, actor=caster))
    bane = occ1.BaneEvent().execute(EventContext(game=game, actor=caster))

    assert bless.success is True
    assert bane.success is True
    assert any((getattr(b, "source", "") or "").startswith("bless:") for b in ally.bonuses)
    assert any((getattr(b, "source", "") or "").startswith("bane:") for b in enemy.bonuses)


def test_lock_spell_locks_target(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    chest = DummyInteractable()
    board = DummyBoard(interactables={(1, 0): [chest]})
    game = _game(actor=caster, board=board)

    monkeypatch.setattr(occ1, "pick_target_in_range", lambda *_a, **_k: (chest, (1, 0)))

    result = occ1.LockSpellEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert chest.locked is True
    assert chest.is_open is False
    assert chest.jammed is False
    assert chest.thievery_dc == 17


def test_sleep_targets_low_hp_enemies(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    low = DummyActor("low", (1, 0), hp=3)
    high = DummyActor("high", (1, 1), hp=8)
    game = _game(actor=caster, enemies=[low, high])

    monkeypatch.setattr(occ1, "pick_position_in_range", lambda *_a, **_k: (1, 0))
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: 5)

    result = occ1.SleepEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert low.has_status("sleep")
    assert low.has_status("prone")
    assert not high.has_status("sleep")


def test_directional_spell_requires_confirm_click_on_caster(monkeypatch):
    caster = DummyActor("caster", (2, 2))
    game = _game(actor=caster, board=DummyBoard(rows=6, cols=6))
    game.conn = ClickSequenceConn(clicks=[(3, 2), (2, 2)])
    animation_calls = []

    monkeypatch.setattr(occ1, "_ui_narration", lambda *args, **kwargs: None)
    monkeypatch.setattr(occ1, "_ui_log", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        occ1,
        "_play_area_spell_animation",
        lambda _game, origin, area_positions, *, vibe: animation_calls.append((origin, list(area_positions), vibe)),
    )

    direction, area_positions = occ1._pick_directional_area_from_caster(
        EventContext(game=game, actor=caster),
        caster.position,
        steps=3,
        prompt_name="Burning Hands",
        source="burning_hands",
        area_kind="cone",
        vibe="fire",
    )

    assert direction == "E"
    assert area_positions
    assert len(game.conn.scan_inputs) == 2
    assert caster.position not in game.conn.scan_inputs[0]
    assert caster.position in game.conn.scan_inputs[1]
    assert len(animation_calls) == 1


def test_command_prone_applies_prone(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    caster.add_bonus(BonusEffect(BonusType.STATUS, 5, "magic", source="spell_dc", label="spell dc"))
    enemy = DummyActor("enemy", (1, 0), hp=15)
    game = _game(actor=caster, enemies=[enemy])

    monkeypatch.setattr(occ1, "pick_target_in_range", lambda *_a, **_k: (enemy, enemy.position))
    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.prompt_for_roll", lambda *_a, **_k: 1)
    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: "prone")

    result = occ1.CommandEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert enemy.has_status("prone")


def test_alarm_triggers_on_enemy_enter(monkeypatch):
    caster = DummyActor("caster", (0, 0), object_id="caster-id")
    enemy = DummyActor("enemy", (5, 5), object_id="enemy-id")
    game = _game(actor=caster, enemies=[enemy])

    monkeypatch.setattr(occ1, "pick_position_in_range", lambda *_a, **_k: (2, 2))

    placed = occ1.AlarmEvent().execute(EventContext(game=game, actor=caster))
    assert placed.success is True

    from GameObjects.events.magic.runtime_effects import process_alarm_wards_for_move

    messages = process_alarm_wards_for_move(game, enemy, (2, 2))

    assert messages
    assert "Alarm" in messages[0]


def test_rank1_arcane_tradition_added_for_shared_spells():
    events = [
        occ1.AlarmEvent(),
        occ1.CharmEvent(),
        occ1.ColorSprayEvent(),
        occ1.CommandEvent(),
        occ1.FearEvent(),
        occ1.FloatingDiskEvent(),
        occ1.GrimTendrilsEvent(),
        occ1.IllusoryDisguiseEvent(),
        occ1.IllusoryObjectEvent(),
        occ1.ItemFacadeEvent(),
        occ1.LockSpellEvent(),
        occ1.MageArmorEvent(),
        occ1.MagicAuraEvent(),
        occ1.MagicWeaponEvent(),
        occ1.MendingEvent(),
        occ1.RayOfEnfeeblementEvent(),
        occ1.SleepEvent(),
        occ1.TrueStrikeEvent(),
        occ1.UnseenServantEvent(),
        occ1.VentriloquismEvent(),
    ]
    for event in events:
        assert SpellTradition.ARCANA in tuple(getattr(event, "magic_traditions", ()) or ())


def test_rank1_divine_tradition_added_for_listed_spells():
    events = [
        occ1.AirBubbleEvent(),
        occ1.AlarmEvent(),
        occ1.AntHaulEvent(),
        occ1.BurningHandsEvent(),
        occ1.CharmEvent(),
        occ1.CreateWaterEvent(),
        occ1.DetectPoisonEvent(),
        occ1.FearEvent(),
        occ1.FeatherFallEvent(),
        occ1.FleetStepEvent(),
        occ1.GoblinPoxEvent(),
        occ1.GreaseEvent(),
        occ1.GustOfWindEvent(),
        occ1.HealEvent(),
        occ1.HydraulicPushEvent(),
        occ1.JumpEvent(),
        occ1.LongstriderEvent(),
        occ1.MagicFangEvent(),
        occ1.MendingEvent(),
        occ1.NegateAromaEvent(),
        occ1.PassWithoutTraceEvent(),
        occ1.PestFormEvent(),
        occ1.PurifyFoodAndDrinkEvent(),
        occ1.ShillelaghEvent(),
        occ1.ShockingGraspEvent(),
        occ1.SpiderStingEvent(),
        occ1.SummonAnimalEvent(),
        occ1.SummonFeyEvent(),
        occ1.SummonPlantOrFungusEvent(),
        occ1.VentriloquismEvent(),
    ]
    for event in events:
        assert SpellTradition.DIVINE in tuple(getattr(event, "magic_traditions", ()) or ())


def test_rank1_divine_tag_present_for_listed_spells():
    events = [
        occ1.AirBubbleEvent(),
        occ1.AlarmEvent(),
        occ1.AntHaulEvent(),
        occ1.BurningHandsEvent(),
        occ1.CharmEvent(),
        occ1.CreateWaterEvent(),
        occ1.DetectPoisonEvent(),
        occ1.FearEvent(),
        occ1.FeatherFallEvent(),
        occ1.FleetStepEvent(),
        occ1.GoblinPoxEvent(),
        occ1.GreaseEvent(),
        occ1.GustOfWindEvent(),
        occ1.HealEvent(),
        occ1.HydraulicPushEvent(),
        occ1.JumpEvent(),
        occ1.LongstriderEvent(),
        occ1.MagicFangEvent(),
        occ1.MendingEvent(),
        occ1.NegateAromaEvent(),
        occ1.PassWithoutTraceEvent(),
        occ1.PestFormEvent(),
        occ1.PurifyFoodAndDrinkEvent(),
        occ1.ShillelaghEvent(),
        occ1.ShockingGraspEvent(),
        occ1.SpiderStingEvent(),
        occ1.SummonAnimalEvent(),
        occ1.SummonFeyEvent(),
        occ1.SummonPlantOrFungusEvent(),
        occ1.VentriloquismEvent(),
    ]
    for event in events:
        assert "divine" in tuple(getattr(event, "spell_tags", ()) or ())


def test_magic_missile_spends_actions_by_missiles(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    enemy = DummyActor("enemy", (1, 0), hp=20)
    game = _game(actor=caster, enemies=[enemy])

    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: "2")
    monkeypatch.setattr(occ1, "pick_target_in_range", lambda *_a, **_k: (enemy, enemy.position))
    damage_rolls = iter([3, 4])
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: next(damage_rolls))

    result = occ1.MagicMissileEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert result.actions_spent == 2
    assert enemy.hp == 13


def test_burning_hands_hits_targets_in_cone(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    caster.add_bonus(BonusEffect(BonusType.STATUS, 5, "magic", source="spell_dc", label="spell dc"))
    e1 = DummyActor("e1", (1, 0), hp=20)
    e2 = DummyActor("e2", (2, 0), hp=20)
    game = _game(actor=caster, enemies=[e1, e2])

    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: "E")
    save_rolls = iter([5, 5])
    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.prompt_for_roll", lambda *_a, **_k: next(save_rolls))
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: 6)

    result = occ1.BurningHandsEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert e1.hp == 8
    assert e2.hp == 8


def test_burning_hands_burn_it_bonus_applies(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    caster.add_status(Status(id="burn_it"))
    caster.add_bonus(BonusEffect(BonusType.STATUS, 5, "magic", source="spell_dc", label="spell dc"))
    e1 = DummyActor("e1", (1, 0), hp=20)
    e2 = DummyActor("e2", (2, 0), hp=20)
    game = _game(actor=caster, enemies=[e1, e2])

    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: "E")
    save_rolls = iter([5, 5])
    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.prompt_for_roll", lambda *_a, **_k: next(save_rolls))
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: 6)

    result = occ1.BurningHandsEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert e1.hp == 6
    assert e2.hp == 6


def test_burning_hands_board_cone_selection_respects_adjacent_walls(monkeypatch):
    caster = DummyActor("caster", (2, 2))
    caster.add_bonus(BonusEffect(BonusType.STATUS, 5, "magic", source="spell_dc", label="spell dc"))
    enemy = DummyActor("enemy", (2, 4), hp=20)
    board = DummyBoard()
    board.add_wall((2, 2), (3, 2))
    game = _game(actor=caster, enemies=[enemy], board=board)

    def _scan_board(positions):
        game.conn.scan_inputs.append(list(positions))
        return (2, 3) if len(game.conn.scan_inputs) == 1 else caster.position

    game.conn.scan_board = _scan_board
    game.ui = SimpleNamespace(enabled=False, allow_cli_fallback=False)

    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.prompt_for_roll", lambda *_a, **_k: 5)
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: 6)

    result = occ1.BurningHandsEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert (3, 2) not in game.conn.scan_inputs[0]
    assert (2, 3) in game.conn.scan_inputs[0]
    assert enemy.hp == 8


def test_burning_hands_uses_automatic_spell_dc_from_caster_stats(monkeypatch):
    caster = DummyActor("Freya", (0, 0))
    caster.class_name = "sorcerer"
    caster.level = 1
    caster.ability_modifiers = {"charisma": 4}
    e1 = DummyActor("e1", (1, 0), hp=20)
    e2 = DummyActor("e2", (2, 0), hp=20)
    e1.reflex_bonus = 5
    e2.reflex_bonus = 5
    game = _game(actor=caster, enemies=[e1, e2])
    captured_prompts = []

    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: "E")

    def _save_prompt(prompt, **kwargs):
        captured_prompts.append((str(prompt), dict(kwargs)))
        return {"roll": 5, "raw_roll": 5}

    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.prompt_for_roll", _save_prompt)
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: 6)

    result = occ1.BurningHandsEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert e1.hp == 14
    assert e2.hp == 14
    assert len(captured_prompts) == 2
    assert all("reflex save przeciw dc 17" in prompt.lower() for prompt, _kwargs in captured_prompts)


def test_color_spray_uses_cone_not_radius(monkeypatch):
    caster = DummyActor("caster", (2, 2))
    caster.add_bonus(BonusEffect(BonusType.STATUS, 5, "magic", source="spell_dc", label="spell dc"))
    east_enemy = DummyActor("east", (3, 2), hp=20)
    north_enemy = DummyActor("north", (2, 1), hp=20)
    game = _game(actor=caster, enemies=[east_enemy, north_enemy])

    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: "E")
    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.prompt_for_roll", lambda *_a, **_k: 5)

    result = occ1.ColorSprayEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert any((getattr(b, "source", "") or "").startswith("color_spray:") for b in east_enemy.bonuses)
    assert not any((getattr(b, "source", "") or "").startswith("color_spray:") for b in north_enemy.bonuses)


def test_hydraulic_push_deals_damage_and_pushes(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    enemy = DummyActor("enemy", (1, 0), hp=20)
    game = _game(actor=caster, enemies=[enemy])

    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.pick_target_in_range", lambda *_a, **_k: (enemy, enemy.position))
    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.prompt_for_roll", lambda *_a, **_k: 20)
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: 5)

    result = occ1.HydraulicPushEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert enemy.hp == 10
    assert "Odepchniecie" in (result.message or "")


def test_hydraulic_push_prompt_includes_formula(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    enemy = DummyActor("enemy", (1, 0), hp=20)
    game = _game(actor=caster, enemies=[enemy])
    captured = {}

    def _prompt(prompt, **kwargs):
        captured["prompt"] = str(prompt)
        captured["kwargs"] = dict(kwargs)
        return 5

    monkeypatch.setattr(occ1, "prompt_for_roll", _prompt)
    monkeypatch.setattr(occ1, "_push_target_linear", lambda *_a, **_k: 1)

    result = occ1.HydraulicPushEvent()._resolve_on_target(
        enemy,
        enemy.position,
        EventContext(game=game, actor=caster),
    )

    assert result.success is True
    assert "3k6" in captured["prompt"]
    assert "3k6" in str(captured["kwargs"].get("prompt_long") or "")


def test_gust_of_wind_uses_board_line_selection_with_reselect(monkeypatch):
    caster = DummyActor("caster", (2, 2))
    caster.add_bonus(BonusEffect(BonusType.STATUS, 5, "magic", source="spell_dc", label="spell dc"))
    north_enemy = DummyActor("north", (2, 1), hp=20)
    east_enemy = DummyActor("east", (4, 2), hp=20)
    north_fire = SimpleNamespace(on_fire=True)
    east_fire = SimpleNamespace(on_fire=True)
    board = DummyBoard(interactables={(2, 0): [north_fire], (5, 2): [east_fire]})
    board.set_field((5, 2), SimpleNamespace(name="blocked", walkable=False))
    game = _game(actor=caster, enemies=[north_enemy, east_enemy], board=board)

    selections = iter([(3, 2), caster.position])

    def _scan_board(positions):
        game.conn.scan_inputs.append(list(positions))
        return next(selections)

    game.conn.scan_board = _scan_board
    game.ui = SimpleNamespace(enabled=False, allow_cli_fallback=False)

    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.prompt_for_roll", lambda *_a, **_k: 1)
    pushed: list[tuple[str, tuple[int, int], int]] = []
    monkeypatch.setattr(
        occ1,
        "_push_target_linear",
        lambda _ctx, target, *, from_pos, squares=1: pushed.append((target.name, from_pos, squares)) or squares,
    )

    result = occ1.GustOfWindEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert sorted(game.conn.scan_inputs[0]) == sorted(
        [(1, 1), (2, 1), (3, 1), (1, 2), (3, 2), (1, 3), (2, 3), (3, 3)]
    )
    assert caster.position in game.conn.scan_inputs[1]
    assert ("east", caster.position, 2) in pushed
    assert all(name != "north" for name, _origin, _squares in pushed)
    assert east_fire.on_fire is True
    assert north_fire.on_fire is True
    preview_positions, preview_colors = game.conn.led_calls[-1]
    preview_map = {tuple(pos): color for pos, color in zip(preview_positions, preview_colors)}
    assert (5, 2) not in preview_map
    assert preview_map[(3, 2)] != preview_map[caster.position]
    assert "odepchnieto 1" in (result.message or "").lower()


def test_gust_of_wind_falls_back_to_direction_prompt(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    caster.add_bonus(BonusEffect(BonusType.STATUS, 5, "magic", source="spell_dc", label="spell dc"))
    enemy = DummyActor("enemy", (1, 0), hp=20)
    game = _game(actor=caster, enemies=[enemy])

    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: "E")
    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.prompt_for_roll", lambda *_a, **_k: 1)
    pushed: list[tuple[str, tuple[int, int], int]] = []
    monkeypatch.setattr(
        occ1,
        "_push_target_linear",
        lambda _ctx, target, *, from_pos, squares=1: pushed.append((target.name, from_pos, squares)) or squares,
    )

    result = occ1.GustOfWindEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert pushed == [("enemy", caster.position, 2)]


def test_gust_of_wind_direction_choices_respect_adjacent_walls(monkeypatch):
    caster = DummyActor("caster", (2, 2))
    caster.add_bonus(BonusEffect(BonusType.STATUS, 5, "magic", source="spell_dc", label="spell dc"))
    enemy = DummyActor("enemy", (4, 2), hp=20)
    board = DummyBoard()
    board.add_wall((2, 2), (2, 1))
    game = _game(actor=caster, enemies=[enemy], board=board)

    def _scan_board(positions):
        game.conn.scan_inputs.append(list(positions))
        return (3, 2) if len(game.conn.scan_inputs) == 1 else caster.position

    game.conn.scan_board = _scan_board
    game.ui = SimpleNamespace(enabled=False, allow_cli_fallback=False)

    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.prompt_for_roll", lambda *_a, **_k: 1)
    monkeypatch.setattr(occ1, "_push_target_linear", lambda *_a, **_k: 1)

    result = occ1.GustOfWindEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert (2, 1) not in game.conn.scan_inputs[0]
    assert (3, 2) in game.conn.scan_inputs[0]
    assert caster.position in game.conn.scan_inputs[1]


def test_grease_surface_prones_enemy_and_creates_zone(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    caster.add_bonus(BonusEffect(BonusType.STATUS, 5, "magic", source="spell_dc", label="spell dc"))
    enemy = DummyActor("enemy", (1, 0), hp=20)
    game = _game(actor=caster, enemies=[enemy])

    choices = iter(["surface"])
    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: next(choices))
    monkeypatch.setattr(occ1, "pick_position_in_range", lambda *_a, **_k: (1, 0))
    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.prompt_for_roll", lambda *_a, **_k: 5)

    result = occ1.GreaseEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert enemy.has_status("prone")
    assert game._arcane_runtime["grease_zones"]


def test_sleep_center_selection_reports_out_of_range_and_confirms_center(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    low = DummyActor("low", (2, 0), hp=3)
    board = DummyBoard(rows=8, cols=8)
    game = _game(actor=caster, enemies=[low], board=board)

    selections = iter([(7, 0), (2, 0), (2, 0)])

    def _scan_board(_positions):
        game.conn.scan_inputs.append(None if _positions is None else list(_positions))
        return next(selections)

    game.conn.scan_board = _scan_board
    game.ui = SimpleNamespace(enabled=False, allow_cli_fallback=False)

    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: 5)
    result = occ1.SleepEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert low.has_status("sleep")
    assert any("Przekroczona odleglosc czarowania" in msg for msg in game._logs)


def test_grease_center_selection_blocks_centers_behind_wall(monkeypatch):
    caster = DummyActor("caster", (1, 1))
    caster.add_bonus(BonusEffect(BonusType.STATUS, 5, "magic", source="spell_dc", label="spell dc"))
    enemy = DummyActor("enemy", (3, 1), hp=20)
    board = DummyBoard(rows=8, cols=8)
    board.add_wall((1, 1), (2, 1))
    game = _game(actor=caster, enemies=[enemy], board=board)

    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: "surface")
    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.prompt_for_roll", lambda *_a, **_k: 5)

    selections = iter([(3, 1), (2, 2), (2, 2)])

    def _scan_board(_positions):
        game.conn.scan_inputs.append(None if _positions is None else list(_positions))
        return next(selections)

    game.conn.scan_board = _scan_board
    game.ui = SimpleNamespace(enabled=False, allow_cli_fallback=False)

    result = occ1.GreaseEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert enemy.has_status("prone")
    assert any("Brak linii efektu" in msg for msg in game._logs)


def test_longstrider_adds_speed_bonus(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    ally = DummyActor("ally", (1, 0))
    game = _game(actor=caster, heroes=[caster, ally])

    monkeypatch.setattr(occ1, "pick_target_in_range", lambda *_a, **_k: (ally, ally.position))
    result = occ1.LongstriderEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert any(getattr(s, "id", "") == "speed_bonus" for s in ally.statuses)


def test_air_bubble_reaction_style(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    ally = DummyActor("ally", (1, 0))
    game = _game(actor=caster, heroes=[caster, ally])

    monkeypatch.setattr(occ1, "pick_target_in_range", lambda *_a, **_k: (ally, ally.position))
    result = occ1.AirBubbleEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert result.consumed_action is False
    assert ally.has_status("air_bubble")


def test_shocking_grasp_critical_damage(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    enemy = DummyActor("enemy", (1, 0), hp=20)
    game = _game(actor=caster, enemies=[enemy])

    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.pick_target_in_range", lambda *_a, **_k: (enemy, enemy.position))
    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.prompt_for_roll", lambda *_a, **_k: 30)
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: 4)
    choices = iter(["nie"])
    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: next(choices))

    result = occ1.ShockingGraspEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert enemy.hp == 12


def test_goblin_pox_applies_poisoned_on_failure(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    caster.add_bonus(BonusEffect(BonusType.STATUS, 5, "magic", source="spell_dc", label="spell dc"))
    enemy = DummyActor("enemy", (1, 0), hp=20)
    game = _game(actor=caster, enemies=[enemy])

    monkeypatch.setattr(occ1, "pick_target_in_range", lambda *_a, **_k: (enemy, enemy.position))
    monkeypatch.setattr("GameObjects.events.magic.base_attack_magic_event.prompt_for_roll", lambda *_a, **_k: 5)
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: 6)

    result = occ1.GoblinPoxEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert enemy.hp == 8
    assert enemy.has_status("poisoned")


def test_summon_animal_and_construct_add_status():
    caster = DummyActor("caster", (0, 0))
    game = _game(actor=caster, heroes=[caster], enemies=[])

    res_animal = occ1.SummonAnimalEvent().execute(EventContext(game=game, actor=caster))
    res_construct = occ1.SummonConstructEvent().execute(EventContext(game=game, actor=caster))

    assert res_animal.success is True
    assert res_construct.success is True
    assert caster.has_status("summon_animal")
    assert caster.has_status("summon_construct")


def test_pest_form_sets_form_status(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    game = _game(actor=caster, heroes=[caster], enemies=[])

    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: "rat")
    result = occ1.PestFormEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    status = [s for s in caster.statuses if getattr(s, "id", "") == "pest_form"]
    assert status and status[0].data.get("form") == "rat"


def test_heal_single_heals_living_target(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    ally = DummyActor("ally", (1, 0), hp=10)
    game = _game(actor=caster, heroes=[caster, ally], enemies=[])

    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: "1")
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: 6)
    monkeypatch.setattr(occ1, "pick_target_in_range", lambda *_a, **_k: (ally, ally.position))

    result = occ1.HealEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert ally.hp == 16
    assert result.actions_spent == 1


def test_heal_touch_prompt_includes_formula_and_auto_modifier_note(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    ally = DummyActor("ally", (1, 0), hp=10)
    game = _game(actor=caster, heroes=[caster, ally], enemies=[])
    captured = {}

    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: "1")

    def _prompt(prompt, **kwargs):
        captured["prompt"] = str(prompt)
        captured["kwargs"] = dict(kwargs)
        return 6

    monkeypatch.setattr(occ1, "prompt_for_roll", _prompt)
    monkeypatch.setattr(occ1, "pick_target_in_range", lambda *_a, **_k: (ally, ally.position))

    result = occ1.HealEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert "1k8" in captured["prompt"]
    assert "Modyfikator spellcastingu zostanie doliczony automatycznie." in str(captured["kwargs"].get("prompt_long") or "")


def test_heal_two_actions_adds_flat_bonus(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    ally = DummyActor("ally", (5, 0), hp=10)
    game = _game(actor=caster, heroes=[caster, ally], enemies=[])

    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: "2")
    monkeypatch.setattr(occ1, "pick_target_in_range", lambda *_a, **_k: (ally, ally.position))

    result = occ1.HealEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert ally.hp == 18  # stale 8 HP
    assert result.actions_spent == 2


def test_heal_three_actions_burst_heals_living_and_harms_undead(monkeypatch):
    caster = DummyActor("caster", (0, 0), hp=20)
    ally = DummyActor("ally", (1, 0), hp=10)
    undead = DummyActor("undead", (1, 1), hp=12)
    undead.tags = ["undead"]
    game = _game(actor=caster, heroes=[caster, ally], enemies=[undead])
    game.conn.scan_board = lambda _positions: caster.position

    monkeypatch.setattr(occ1, "_prompt_choice", lambda *_a, **_k: "3")
    monkeypatch.setattr(occ1, "prompt_for_roll", lambda *_a, **_k: 5)

    result = occ1.HealEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert caster.hp == 25
    assert ally.hp == 15
    assert undead.hp == 7
    assert result.actions_spent == 3


def test_detect_poison_recognizes_poisoned_target(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    enemy = DummyActor("enemy", (1, 0))
    enemy.tags = ["poison"]
    game = _game(actor=caster, enemies=[enemy])

    monkeypatch.setattr(occ1, "pick_target_in_range", lambda *_a, **_k: (enemy, enemy.position))
    result = occ1.DetectPoisonEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert "trucizny/jadu" in (result.message or "")


def test_magic_fang_applies_status_and_bonus(monkeypatch):
    caster = DummyActor("caster", (0, 0))
    ally = DummyActor("ally", (1, 0))
    game = _game(actor=caster, heroes=[caster, ally], enemies=[])

    monkeypatch.setattr(occ1, "pick_target_in_range", lambda *_a, **_k: (ally, ally.position))
    result = occ1.MagicFangEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert ally.has_status("magic_fang")
    assert any((getattr(b, "source", "") or "").startswith("magic_fang:") for b in ally.bonuses)


def test_pass_without_trace_applies_group_stealth_bonus():
    caster = DummyActor("caster", (0, 0))
    ally = DummyActor("ally", (1, 0))
    game = _game(actor=caster, heroes=[caster, ally], enemies=[])

    result = occ1.PassWithoutTraceEvent().execute(EventContext(game=game, actor=caster))

    assert result.success is True
    assert caster.has_status("pass_without_trace")
    assert ally.has_status("pass_without_trace")
    assert any((getattr(b, "source", "") or "").startswith("pass_without_trace:") for b in caster.bonuses)
    assert any((getattr(b, "source", "") or "").startswith("pass_without_trace:") for b in ally.bonuses)


def test_summon_plant_or_fungus_and_alias_apply_status():
    caster = DummyActor("caster", (0, 0))
    game = _game(actor=caster, heroes=[caster], enemies=[])

    res_full = occ1.SummonPlantOrFungusEvent().execute(EventContext(game=game, actor=caster))
    res_alias = occ1.SummonPlantEvent().execute(EventContext(game=game, actor=caster))

    assert res_full.success is True
    assert res_alias.success is True
    assert caster.has_status("summon_plant_or_fungus")
