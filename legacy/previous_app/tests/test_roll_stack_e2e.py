import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.interactions_mixin import prompt_utils
from GameObjects.interactions_mixin import skill_check_resolver
from GameObjects.interactions_mixin.prompt_utils import prompt_for_roll as prompt_for_roll_impl


class _FakeUI:
    enabled = True
    allow_cli_fallback = False

    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def prompt_roll(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, "kwargs": dict(kwargs)})
        return self.answer


class _Actor:
    def __init__(self):
        self.level = 1
        self.statuses = []
        self.bonuses = []
        self.ability_modifiers = {"wisdom": 2}
        self.perception_rank = "trained"
        self.skill_ranks = {}
        self.save_ranks = {}


def test_prompt_utils_roll_stack_roundtrip_with_modifier_delta(monkeypatch):
    ui = _FakeUI(
        {
            "roll": 12,
            "raw_roll": 20,
            "modifier_delta": 2,
            "computed_total": 17,
        }
    )
    monkeypatch.setattr(prompt_utils, "get_ui_client", lambda: ui)

    details = prompt_for_roll_impl(
        "Test rzutu",
        return_details=True,
        infer_natural_from_roll=True,
        layout="test",
        modifiers={
            "bonCirc": [{"label": "okoliczności", "value": 1}],
            "bonStat": [{"label": "status", "value": 1}],
            "bonItem": [{"label": "item", "value": 1}],
            "penCirc": [],
            "penStat": [],
            "penItem": [],
        },
        auto_total_modifier=3,
    )

    assert details["roll"] == 12
    assert details["raw_roll"] == 20
    assert details["natural_shift"] == 1
    assert details["modifier_delta"] == 2
    assert details["computed_total"] == 17

    sent = ui.calls[0]["kwargs"]
    roll_stack = sent.get("roll_stack", {})
    components = list(roll_stack.get("components", []) or [])
    ids = {str(item.get("id")) for item in components if isinstance(item, dict)}
    assert {"circumstance", "status", "item"}.issubset(ids)
    assert int(roll_stack.get("auto_total_modifier", 0) or 0) == 3


def test_skill_check_e2e_uses_roll_stack_and_manual_delta(monkeypatch):
    ui = _FakeUI(
        {
            "roll": 10,
            "raw_roll": 20,
            "modifier_delta": 2,
        }
    )
    monkeypatch.setattr(skill_check_resolver, "get_ui_client", lambda: ui)

    actor = _Actor()
    result = skill_check_resolver.resolve_skill_check_with_sources(
        skill_id="perception",
        dc=17,
        actor=actor,
        target=None,
        tags=["initiative", "perception"],
        apply_modifiers=True,
    )

    # base mod: level 1 + trained 2 + WIS 2 = +5; with manual delta +2 => total 17
    # raw_roll=20 should promote degree by +1 (success -> critical success)
    assert result.total == 17
    assert result.outcome == "critical_success"
    assert any("Korekta ręczna modyfikatora: +2." in note for note in result.notes)

    sent = ui.calls[0]["kwargs"]
    roll_stack = sent.get("roll_stack", {})
    components = list(roll_stack.get("components", []) or [])
    ids = {str(item.get("id")) for item in components if isinstance(item, dict)}
    assert {"level", "proficiency_step", "ability", "item", "status", "circumstance"}.issubset(ids)
    assert int(roll_stack.get("auto_total_modifier", 0) or 0) == 5


def test_prompt_utils_damage_layout_supports_roll_stack(monkeypatch):
    ui = _FakeUI(
        {
            "roll": 7,
            "raw_roll": 7,
            "modifier_delta": 1,
            "computed_total": 14,
        }
    )
    monkeypatch.setattr(prompt_utils, "get_ui_client", lambda: ui)

    details = prompt_for_roll_impl(
        "Obrażenia 1k8 + STR",
        return_details=True,
        layout="damage",
        roll_stack={
            "components": [
                {"id": "ability", "label": "Siła", "value": 4},
                {"id": "other", "label": "Inne", "value": 2},
            ],
            "auto_total_modifier": 6,
        },
        auto_total_modifier=6,
    )

    assert details["roll"] == 7
    assert details["computed_total"] == 14
    sent = ui.calls[0]["kwargs"]
    stack = sent.get("roll_stack", {})
    ids = {str(item.get("id")) for item in list(stack.get("components", []) or [])}
    assert {"ability", "other"}.issubset(ids)
    assert int(stack.get("auto_total_modifier", 0) or 0) == 6
