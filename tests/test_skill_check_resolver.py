import sys
from pathlib import Path
import types

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# --- Stuby brakujących modułów actions.* potrzebne przy imporcie eventów ---
try:
    import actions.move_utils as _move_utils_mod  # noqa: F401
    import actions.specials.magic_missile  # noqa: F401
    if not hasattr(_move_utils_mod, "terrain_move_bonus_feet"):
        raise ImportError("stubbed move_utils without terrain_move_bonus_feet")
except Exception:
    import importlib.util
    _actions = types.ModuleType("actions")
    _actions.__path__ = []
    _move_utils = types.ModuleType("actions.move_utils")
    _move_utils.find_path = lambda *a, **k: []
    _move_utils.path_cost_feet = lambda *a, **k: 0
    _move_utils.trim_path_to_feet = lambda *a, **k: []
    _move_utils.perform_movement = lambda *a, **k: None
    _move_utils.follow_path = lambda *a, **k: None
    _move_utils.terrain_move_bonus_feet = lambda *a, **k: 0
    _move_utils.movement_budget_feet = lambda *a, **k: 25
    _move_utils.adjusted_forced_movement_squares = lambda _target, squares, *a, **k: int(squares or 0)
    _move_utils.default_on_enter = lambda *a, **k: None
    _move_utils._maybe_dispatch_move_reactions = lambda *a, **k: None
    _specials = types.ModuleType("actions.specials")
    _specials.__path__ = []
    _magic = types.ModuleType("actions.specials.magic_missile")
    _magic.magic_missile_ability = lambda *a, **k: None
    sys.modules["actions"] = _actions
    sys.modules["actions.move_utils"] = _move_utils
    sys.modules["actions.specials"] = _specials
    sys.modules["actions.specials.magic_missile"] = _magic
    # jeśli realny move_utils istnieje, podmień stub by uniknąć braków importu
    try:
        MOVE_UTILS_PATH = SRC_ROOT / "actions" / "move_utils.py"
        spec = importlib.util.spec_from_file_location("actions.move_utils", MOVE_UTILS_PATH)
        move_utils = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(move_utils)  # type: ignore[arg-type]
        sys.modules["actions.move_utils"] = move_utils
    except Exception:
        pass

from bonuses import BonusEffect, BonusType  # noqa: E402
from GameObjects.interactions_mixin.skill_check_resolver import (  # noqa: E402
    resolve_skill_check_with_sources,
    resolve_skill_check_with_sources_from_roll,
)
from GameObjects.events.checks import skill_check_event  # noqa: F401  # rejestruje eventy
from statuses import NOBLE_PERSON_STATUS, SILVER_TONGUE_STATUS, STUBBORN_STATUS  # noqa: E402
from GameObjects.NPC.guard_npc import GuardNPC  # noqa: E402
from statuses.race.elfs.heritages.seer_elf import SEER_ELF_STATUS  # noqa: E402
from statuses.race.elfs.heritages.whisper_elf import WHISPER_ELF_STATUS  # noqa: E402
from statuses.race.elfs.feats.unwavering_mien import UNWAVERING_MIEN_STATUS  # noqa: E402
from statuses.race.goblin.heritages.irongut_goblin import IRONGUT_GOBLIN_STATUS  # noqa: E402


class DummyGame:
    def __init__(self):
        self.logged = []

    def ui_log(self, msg):
        self.logged.append(msg)


class Hero:
    def __init__(self, statuses=None, bonuses=None):
        self.statuses = statuses or []
        self.bonuses = bonuses or []


def test_source_bonus_and_target_penalty(monkeypatch):
    # gracz podaje wynik końcowy już z premią +2 (13+2=15)
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_, **__:15)

    actor = Hero(statuses=[NOBLE_PERSON_STATUS])
    target = Hero(statuses=[STUBBORN_STATUS])
    res = resolve_skill_check_with_sources(skill_id="diplomacy", dc=15, actor=actor, target=target, tags=["diplomacy", "noble"])
    assert res.modifier == 2  # bonus z noble_person (pokazywany w promptcie)
    # wejściowy success 15 -> demote o 1 (stubborn) => failure
    assert res.outcome == "failure"
    assert any("szlacheckie" in note or "oporny" in note for note in res.notes) or res.notes


def test_promotion_from_silver_tongue(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_, **__:12)
    actor = Hero(statuses=[SILVER_TONGUE_STATUS])
    res = resolve_skill_check_with_sources(skill_id="diplomacy", dc=15, actor=actor, target=None, tags=["diplomacy"])
    # 12 vs 15 -> failure, promote +1 => success
    assert res.outcome == "success"
    assert "Rzuć 2k20" in " ".join(res.notes)


def test_conditional_promote_on_success(monkeypatch):
    from statuses.base import Status
    from statuses.check_effects import CheckEffect

    # promote tylko gdy bazowo success
    dwarven = Status(
        id="dwarven_resilience",
        check_effects=[
            CheckEffect(
                applies_to="source",
                skills=["fortitude"],
                tags_required=["necromancy"],
                promote=1,
                promote_on=["success"],
                prompt_notes=["Krasnoludzka odporność: success -> critical success vs nekromancja."],
            )
        ],
    )

    # bazowy success (roll 13 vs DC 13)
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_, **__:13)
    actor = Hero(statuses=[dwarven])
    res = resolve_skill_check_with_sources(skill_id="fortitude", dc=13, actor=actor, target=None, tags=["necromancy"])
    assert res.outcome == "critical_success"

    # bazowy failure (roll 10 vs DC 13) nie spełnia promote_on -> zostaje failure
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_, **__:10)
    res2 = resolve_skill_check_with_sources(skill_id="fortitude", dc=13, actor=actor, target=None, tags=["necromancy"])
    assert res2.outcome == "failure"


def test_guard_diplomacy_action(monkeypatch):
    # roll 17 ensures sukces (DC zależy od nastawienia=0 => 16)
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_, **__:17)
    game = DummyGame()
    guard = GuardNPC(enable_trade=False, enable_pickpocket=False, enable_talk=False, enable_diplomacy=True, attitude=0)
    hero = Hero(statuses=[NOBLE_PERSON_STATUS, SILVER_TONGUE_STATUS])

    msg = guard.action_diplomacy_guard(hero, game)
    assert "pismo" in msg.lower()
    assert guard.diplomacy_letter_given
    assert guard.attitude >= 0

    # krytyczna porażka blokuje (osobna instancja bez promujących statusów)
    guard2 = GuardNPC(enable_trade=False, enable_pickpocket=False, enable_talk=False, enable_diplomacy=True, attitude=0)
    hero_plain = Hero()
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_, **__:1)
    msg2 = guard2.action_diplomacy_guard(hero_plain, game)
    assert "Nie będzie dalszych" in msg2 or guard2.diplomacy_blocked


@pytest.mark.parametrize("skill_id", ["arcana", "nature", "occultism", "religion"])
def test_seer_elf_bonus_for_identify_magic(monkeypatch, skill_id):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_, **__:10)
    actor = Hero(statuses=[SEER_ELF_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id=skill_id,
        dc=15,
        actor=actor,
        target=None,
        tags=[skill_id, "identify_magic"],
        apply_modifiers=True,
    )
    assert res.modifier == 1


def test_seer_elf_no_bonus_without_identify_or_decipher_tags(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_, **__:10)
    actor = Hero(statuses=[SEER_ELF_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id="arcana",
        dc=15,
        actor=actor,
        target=None,
        tags=["arcana"],
        apply_modifiers=True,
    )
    assert res.modifier == 0


def test_whisper_elf_audio_seek_bonus_for_undetected(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_, **__:10)
    actor = Hero(statuses=[WHISPER_ELF_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id="perception",
        dc=15,
        actor=actor,
        target=None,
        tags=["perception", "seek", "undetected", "auditory"],
        apply_modifiers=True,
    )
    assert res.modifier == 2
    assert any("Whisper Elf" in note for note in res.notes)


def test_unwavering_mien_promote_on_sleep_save(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_, **__:15)
    actor = Hero(statuses=[UNWAVERING_MIEN_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id="will",
        dc=15,
        actor=actor,
        target=None,
        tags=["sleep", "mental", "will"],
        apply_modifiers=True,
    )
    # 15 vs 15 => success, Unwavering Mien promuje do critical_success dla sleep.
    assert res.modifier == 0
    assert res.outcome == "critical_success"


def test_irongut_goblin_ingested_bonus_and_promote(monkeypatch):
    captured = {}

    def _prompt(_prompt, **kwargs):
        captured.update(kwargs)
        return 13

    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", _prompt)
    actor = Hero(statuses=[IRONGUT_GOBLIN_STATUS])
    res = resolve_skill_check_with_sources(
        skill_id="fortitude",
        dc=13,
        actor=actor,
        target=None,
        tags=["ingested", "fortitude"],
        apply_modifiers=True,
    )

    assert res.modifier == 2
    assert res.outcome == "critical_success"
    modifiers = captured.get("modifiers", {})
    bon_circ = modifiers.get("bonCirc", [])
    assert any(item.get("label") == "irongut" and item.get("value") == 2 for item in bon_circ)


def test_natural_20_promotes_degree_from_ui_payload(monkeypatch):
    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll",
        lambda *_, **__: {"roll": 10, "natural_mode": "nat20", "natural_shift": 1},
    )
    actor = Hero()
    res = resolve_skill_check_with_sources(
        skill_id="perception",
        dc=15,
        actor=actor,
        target=None,
        tags=["perception"],
        apply_modifiers=True,
    )
    # 10 vs 15 = failure, nat20 => +1 degree => success.
    assert res.outcome == "success"


def test_natural_1_demotes_degree_from_ui_payload(monkeypatch):
    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll",
        lambda *_, **__: {"roll": 10, "natural_mode": "nat1", "natural_shift": -1},
    )
    actor = Hero()
    res = resolve_skill_check_with_sources(
        skill_id="perception",
        dc=10,
        actor=actor,
        target=None,
        tags=["perception"],
        apply_modifiers=True,
    )
    # 10 vs 10 = success, nat1 => -1 degree => failure.
    assert res.outcome == "failure"


def test_no_natural_inference_when_total_is_entered(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_, **__: 20)
    actor = Hero()
    res = resolve_skill_check_with_sources(
        skill_id="perception",
        dc=20,
        actor=actor,
        target=None,
        tags=["perception"],
        apply_modifiers=False,
    )
    # Wynik końcowy 20 nie może sam z siebie liczyć się jako nat20.
    assert res.outcome == "success"


def test_explicit_natural_mode_still_applies_for_final_total(monkeypatch):
    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll",
        lambda *_, **__: {"roll": 20, "natural_mode": "nat20", "natural_shift": 1},
    )
    actor = Hero()
    res = resolve_skill_check_with_sources(
        skill_id="perception",
        dc=20,
        actor=actor,
        target=None,
        tags=["perception"],
        apply_modifiers=False,
    )
    assert res.outcome == "critical_success"


def test_raw_roll_is_used_for_natural_inference(monkeypatch):
    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll",
        lambda *_, **__: {"roll": 27, "raw_roll": 20, "modifier_delta": 7},
    )
    actor = Hero()
    res = resolve_skill_check_with_sources(
        skill_id="perception",
        dc=25,
        actor=actor,
        target=None,
        tags=["perception"],
        apply_modifiers=True,
    )
    assert res.outcome == "critical_success"


def test_modifier_delta_adjusts_final_total(monkeypatch):
    monkeypatch.setattr(
        "GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll",
        lambda *_, **__: {"roll": 10, "raw_roll": 10, "modifier_delta": 2},
    )
    actor = Hero()
    res = resolve_skill_check_with_sources(
        skill_id="perception",
        dc=12,
        actor=actor,
        target=None,
        tags=["perception"],
        apply_modifiers=True,
    )
    assert res.total == 12
    assert res.outcome == "success"
    assert any("Korekta ręczna modyfikatora" in note for note in res.notes)


def test_auto_base_modifier_from_level_rank_and_ability(monkeypatch):
    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", lambda *_, **__: 10)
    actor = Hero()
    actor.level = 1
    actor.perception_rank = "trained"
    actor.ability_modifiers = {"wisdom": 2}
    res = resolve_skill_check_with_sources(
        skill_id="perception",
        dc=15,
        actor=actor,
        target=None,
        tags=["initiative", "perception"],
        apply_modifiers=True,
    )
    assert res.modifier == 5
    assert res.total == 15
    assert res.outcome == "success"


def test_roll_stack_for_initiative_has_pf2_components(monkeypatch):
    captured = {}

    def _prompt(_prompt, **kwargs):
        captured.update(kwargs)
        return 10

    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", _prompt)
    actor = Hero()
    actor.level = 1
    actor.perception_rank = "trained"
    actor.ability_modifiers = {"wisdom": 2}
    resolve_skill_check_with_sources(
        skill_id="perception",
        dc=15,
        actor=actor,
        target=None,
        tags=["initiative", "perception"],
        apply_modifiers=True,
    )
    stack = captured.get("roll_stack", {})
    components = list(stack.get("components", []) or [])
    ids = {str(row.get("id")) for row in components if isinstance(row, dict)}
    assert {"level", "proficiency_step", "ability", "item", "status", "circumstance"}.issubset(ids)
    assert len(components) == 6
    assert int(stack.get("auto_total_modifier", 0) or 0) == 5


@pytest.mark.parametrize(
    "skill_id,level,ability_mods,skill_ranks,save_ranks,expected_modifier,tags",
    [
        ("athletics", 4, {"strength": 4}, {"athletics": "expert"}, {}, 12, ["athletics"]),
        ("diplomacy", 5, {"charisma": 4}, {"diplomacy": "expert"}, {}, 13, ["diplomacy"]),
        ("reflex", 7, {"dexterity": 3}, {}, {"reflex": "expert"}, 14, ["save", "reflex"]),
        ("stealth", 6, {"dexterity": 4}, {"stealth": "expert"}, {}, 14, ["stealth"]),
        ("perception", 5, {"wisdom": 3}, {"perception": "expert"}, {}, 12, ["seek", "perception"]),
    ],
)
def test_pf2_core_formula_for_skills_and_saves(
    skill_id,
    level,
    ability_mods,
    skill_ranks,
    save_ranks,
    expected_modifier,
    tags,
):
    actor = Hero()
    actor.level = level
    actor.ability_modifiers = dict(ability_mods)
    actor.skill_ranks = dict(skill_ranks)
    actor.save_ranks = dict(save_ranks)
    if skill_id == "perception":
        actor.perception_rank = skill_ranks.get("perception", "untrained")
    result = resolve_skill_check_with_sources_from_roll(
        skill_id=skill_id,
        dc=10_000,
        actor=actor,
        target=None,
        tags=tags,
        roll=10,
        apply_modifiers=True,
    )
    assert result.modifier == expected_modifier
    assert result.total == 10 + expected_modifier


def test_pf2_untrained_skill_does_not_add_level():
    actor = Hero()
    actor.level = 5
    actor.ability_modifiers = {"intelligence": 4}
    actor.skill_ranks = {"arcana": "untrained"}
    result = resolve_skill_check_with_sources_from_roll(
        skill_id="arcana",
        dc=10_000,
        actor=actor,
        target=None,
        tags=["arcana"],
        roll=10,
        apply_modifiers=True,
    )
    assert result.modifier == 4
    assert result.total == 14


def test_thievery_formula_with_item_bonus_from_tools(monkeypatch):
    captured = {}

    def _prompt(_prompt, **kwargs):
        captured.update(kwargs)
        return 10

    monkeypatch.setattr("GameObjects.interactions_mixin.skill_check_resolver.prompt_for_roll", _prompt)
    actor = Hero(
        bonuses=[
            BonusEffect(BonusType.ITEM, 1, "thievery", source="thieves_tools", label="thieves tools"),
        ]
    )
    actor.level = 3
    actor.ability_modifiers = {"dexterity": 4}
    actor.skill_ranks = {"thievery": "trained"}
    result = resolve_skill_check_with_sources(
        skill_id="thievery",
        dc=20,
        actor=actor,
        target=None,
        tags=["thievery", "disable_device"],
        apply_modifiers=True,
    )
    assert result.modifier == 10
    assert result.total == 20

    stack = captured.get("roll_stack", {})
    components = {str(item.get("id")): int(item.get("value", 0) or 0) for item in list(stack.get("components", []) or [])}
    assert components.get("level") == 3
    assert components.get("proficiency_step") == 2
    assert components.get("ability") == 4
    assert components.get("item") == 1
    assert components.get("status") == 0
    assert components.get("circumstance") == 0
