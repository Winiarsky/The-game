from __future__ import annotations

from GameObjects.interactions_mixin.status_mixin import StatusMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll
from statuses.general.adopted_ancestry import ADOPTED_ANCESTRY_STATUS
from statuses.general.dubious_knowledge import DubiousKnowledgeStatus
from statuses.general.trick_magic_item import TrickMagicItemStatus
from statuses.general.recognize_spell import RECOGNIZE_SPELL_STATUS
from statuses.race.halfling.feats.halfling_luck import HALFLING_LUCK_STATUS
from skills import Skill
from hero import Hero
from board_grid import BoardGrid
from GameObjects.Interactables.hidden_cache import HiddenCache
from GameObjects.events.base import EventContext
from GameObjects.events.magic.cantrips.events import DetectMagicEvent
from combat.hp_engine import computed_max_hp
from statuses.general.assurance import ASSURANCE_STATUS
from statuses.general.fleet import FLEET_STATUS
from statuses.general.skill_training import SKILL_TRAINING_STATUS
from statuses.general.toughness import TOUGHNESS_STATUS
from statuses.race.human.feats.general_training import GENERAL_TRAINING_CHOICES


class DummyHero(StatusMixin):
    pass


class DummyUI:
    def __init__(self, answers: list[str]):
        self.answers = list(answers)
        self.enabled = True

    def prompt_choice(self, _prompt: str, choices=None, **_kwargs):
        if self.answers:
            return self.answers.pop(0)
        if choices:
            return choices[0]
        return None


def test_adopted_ancestry_adds_selected_feat(monkeypatch):
    dummy_ui = DummyUI(["Halfling", "Halfling Luck"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: dummy_ui)

    hero = DummyHero()
    added = hero.add_status(ADOPTED_ANCESTRY_STATUS)
    assert added is True

    adopted = hero.get_status("adopted_ancestry")
    assert adopted is not None
    choice = (adopted.data or {}).get("adopted_ancestry_choice")
    assert choice == {"race": "halfling", "feat": "halfling_luck"}

    assert hero.has_status(HALFLING_LUCK_STATUS)


def test_dubious_knowledge_promotes_success_on_knowledge_tag():
    actor = DummyHero()
    actor.add_status(DubiousKnowledgeStatus())

    result = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.ARCANA.value,
        dc=15,
        actor=actor,
        tags=["knowledge"],
        roll=15,
        apply_modifiers=True,
    )

    assert result.outcome == "critical_success"


def test_trick_magic_item_bonus_applies_on_magic_item():
    actor = DummyHero()
    actor.add_status(TrickMagicItemStatus())

    result = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.ARCANA.value,
        dc=12,
        actor=actor,
        tags=["magic_item"],
        roll=10,
        apply_modifiers=True,
    )

    assert result.modifier == 2
    assert result.total == 12


def test_recognize_spell_adds_ac_magic_bonus_in_combat():
    class DummyConn:
        def set_leds(self, _positions, _colors):
            return None

        def scan_board(self, _positions):
            return None

        def leds_off(self):
            return None

    class DummyUIInfo:
        def prompt_info(self, _title, *, prompt_long=None, **_kwargs):
            return prompt_long

    class Combat:
        pass

    board = BoardGrid(rows=3, cols=3)
    board.apply_rooms([{"id": "room1", "positions": [(0, 0)]}])
    game = type("G", (), {})()
    game.board = board
    game.conn = DummyConn()
    game.ui = DummyUIInfo()
    game.ui_log = lambda _msg: None
    game.heroes = []
    game.enemies = []
    game.state = Combat()

    hero = Hero()
    hero.add_status(RECOGNIZE_SPELL_STATUS)
    board.place(hero, (0, 0))
    game.heroes.append(hero)

    cache = HiddenCache(hidden=False)
    board.add_interactable(cache, (0, 0))

    event = DetectMagicEvent()
    ctx = EventContext(game=game, actor=hero)
    event.run(ctx)

    bonuses = getattr(hero, "bonuses", [])
    assert any(
        b.tag == "ac_magic" and b.value == 1 and b.duration_turns == 1
        for b in bonuses
    )


def test_general_training_choices_include_new_general_feats():
    for feat_id in (
        "arcane_sense",
        "additional_lore",
        "alchemical_crafting",
        "quick_repair",
        "terrain_stalker",
        "virtuosic_performer",
    ):
        assert feat_id in GENERAL_TRAINING_CHOICES


def test_skill_training_prompts_and_records_selected_skill(monkeypatch):
    dummy_ui = DummyUI(["Stealth"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: dummy_ui)

    hero = DummyHero()
    hero.add_status(SKILL_TRAINING_STATUS)

    assert hero.get_status_data("skill_training", "skill_training_skill", None) == "stealth"
    assert hero.get_status_data("skill_training", "trained_skills", []) == ["stealth"]


def test_assurance_prompts_and_records_selected_skill(monkeypatch):
    dummy_ui = DummyUI(["Arcana"])
    monkeypatch.setattr("ui_client.get_ui_client", lambda: dummy_ui)

    hero = DummyHero()
    hero.add_status(ASSURANCE_STATUS)

    assert hero.get_status_data("assurance", "assurance_skill", None) == "arcana"


def test_fleet_and_toughness_apply_runtime_mechanics():
    hero = DummyHero()
    hero.level = 3
    hero.max_hp = 20
    hero.add_status(FLEET_STATUS)
    hero.add_status(TOUGHNESS_STATUS)

    assert hero.get_status_data("fleet", "base_speed_bonus_feet", 0) == 5
    assert computed_max_hp(hero) == 23
