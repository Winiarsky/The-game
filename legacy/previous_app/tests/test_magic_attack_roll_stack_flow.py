import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from bonuses import BonusEffect, BonusType
from GameObjects.events.base import EventContext, EventResult
from GameObjects.events.magic import base_attack_magic_event
from GameObjects.events.magic.base_attack_magic_event import BaseMagicAttackEvent


class _DummySpellAttack(BaseMagicAttackEvent):
    name = "test_spell_attack_flow"
    default_tags = ["spell_attack"]
    range_feet = 30

    def _resolve_on_target(self, target, pos, ctx, *, critical=False):
        return EventResult(success=True, consumed_action=self.consumes_action, message="trafienie")


class _DummyTarget:
    def __init__(self):
        self.position = (1, 0)
        self.ac = 10
        self.bonuses = []
        self.statuses = []


class _DummyGame:
    def __init__(self, actor, target, *, choice_pos=None):
        self.heroes = [actor]
        self.enemies = [target]
        self.events = SimpleNamespace(safe_emit_action=lambda **_k: None)
        self.ui_log = lambda *_a, **_k: None
        self.board = SimpleNamespace(rows=8, cols=8)
        self.conn = SimpleNamespace(
            set_leds=lambda *_a, **_k: None,
            scan_board=lambda positions: choice_pos if choice_pos in positions else (positions[0] if positions else None),
            leds_off=lambda: None,
        )


def test_magic_attack_roll_stack_contains_auto_modifier(monkeypatch):
    target = _DummyTarget()
    actor = SimpleNamespace(
        position=(0, 0),
        class_name="sorcerer",
        level=1,
        ability_modifiers={"charisma": 4},
        bonuses=[BonusEffect(BonusType.STATUS, 1, "spell_attack", source="inspire_courage", label="inspire courage")],
        statuses=[],
    )
    game = _DummyGame(actor, target)
    ctx = EventContext(game=game, actor=actor)
    captured = {}

    monkeypatch.setattr(base_attack_magic_event, "pick_target_in_range", lambda *_a, **_k: (target, target.position))
    monkeypatch.setattr(base_attack_magic_event, "check_concealed", lambda *_a, **_k: True)

    def _prompt(_prompt, **kwargs):
        captured.update(kwargs)
        return {"roll": 10, "raw_roll": 10}

    monkeypatch.setattr(base_attack_magic_event, "prompt_for_roll", _prompt)

    result = _DummySpellAttack().execute(ctx)
    assert result.success

    stack = captured.get("roll_stack", {})
    components = list(stack.get("components", []) or [])
    component_ids = [str(component.get("id")) for component in components]
    assert "spellcasting_proficiency" in component_ids
    assert "spellcasting_key_ability" in component_ids
    assert any(str(component.get("label", "")).startswith("Status:") for component in components)
    proficiency = next(component for component in components if str(component.get("id")) == "spellcasting_proficiency")
    key_ability = next(component for component in components if str(component.get("id")) == "spellcasting_key_ability")
    assert int(proficiency.get("value", 0) or 0) == 3
    assert int(key_ability.get("value", 0) or 0) == 4
    assert int(stack.get("auto_total_modifier", 0) or 0) == 8


def test_spell_dc_details_include_spellcasting_proficiency_and_key_ability():
    actor = SimpleNamespace(
        class_name="wizard",
        level=1,
        ability_modifiers={"intelligence": 4},
        bonuses=[],
        statuses=[],
    )

    dc, modifier, _best_effects, _log_lines = base_attack_magic_event.spell_dc_details(actor)

    assert modifier == 7
    assert dc == 17


def test_spell_save_roll_stack_contains_auto_modifier(monkeypatch):
    target = SimpleNamespace(name="target", reflex_bonus=9, statuses=[], bonuses=[])
    captured = {}

    def _prompt(_prompt, **kwargs):
        captured.update(kwargs)
        return {"roll": 5, "raw_roll": 5}

    monkeypatch.setattr(base_attack_magic_event, "prompt_for_roll", _prompt)

    outcome, roll, total = base_attack_magic_event.prompt_spell_save_roll(
        target=target,
        skill_id="reflex",
        dc=19,
        tags=["save", "reflex", "spell"],
    )

    assert outcome == "failure"
    assert roll == 5
    assert total == 14
    stack = captured.get("roll_stack", {})
    components = list(stack.get("components", []) or [])
    assert len(components) == 1
    assert str(components[0].get("id")) == "reflex"
    assert int(components[0].get("value", 0) or 0) == 9
    assert int(stack.get("auto_total_modifier", 0) or 0) == 9


def test_spell_attack_can_hit_undetected_target_after_guessing_correct_square(monkeypatch):
    target = _DummyTarget()
    target.statuses.append(SimpleNamespace(id="undetected"))
    actor = SimpleNamespace(
        position=(0, 0),
        class_name="wizard",
        level=1,
        ability_modifiers={"intelligence": 4},
        bonuses=[],
        statuses=[],
    )
    game = _DummyGame(actor, target, choice_pos=target.position)
    ctx = EventContext(game=game, actor=actor)

    monkeypatch.setattr(base_attack_magic_event, "check_concealed", lambda *_a, **_k: True)
    monkeypatch.setattr(base_attack_magic_event, "prompt_for_roll", lambda *_a, **_k: {"roll": 10, "raw_roll": 10})

    result = _DummySpellAttack().execute(ctx)

    assert result.success is True
    assert (result.data or {}).get("target") is target
    assert bool((result.data or {}).get("spell_attack_hit", False)) is True
