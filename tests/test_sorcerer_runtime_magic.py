from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import GameObjects.events.all_events  # noqa: F401

from GameObjects.events.base import EventContext, EventResult
from GameObjects.events.magic.magic_event import MagicEvent, MagicEventResolver
from GameObjects.events.registry import dispatch_event, list_events
from GameObjects.events.magic.focus_spells.sorcerer import sorcerer_focus_spell_events
from GameObjects.interactions_mixin import prompt_for_roll
from GameObjects.interactions_mixin.status_mixin import StatusMixin
from combat.reactions.counterspell_reaction import CounterspellReaction
from combat.reactions.dispatcher import dispatch_reactions
from states.combat import Combat
from statuses.base import Status


@dataclass
class DummyActor(StatusMixin):
    name: str = "actor"
    object_id: str = "actor"
    position: tuple[int, int] | None = (0, 0)
    hp: int = 20
    statuses: list = field(default_factory=list)
    reactions: list = field(default_factory=list)
    reactions_left: int = 1
    reactions_max: int = 1
    bonuses: list = field(default_factory=list)
    focus_point: int = 0

    def __hash__(self):
        return id(self)

    def add_bonus(self, effect):
        self.bonuses.append(effect)

    def consume_reaction(self):
        if self.reactions_left <= 0:
            return False
        self.reactions_left -= 1
        return True

    def reset_reactions(self):
        self.reactions_left = self.reactions_max

    def apply_damage(self, amount: int, _damage_type: str = ""):
        self.hp -= int(amount)
        return self.hp, self.hp <= 0


class DummyConn:
    def __init__(self, choice_pos: tuple[int, int] | None = None):
        self.choice_pos = choice_pos

    def set_leds(self, *_args, **_kwargs):
        return None

    def scan_board(self, positions):
        if self.choice_pos in positions:
            return self.choice_pos
        return positions[0] if positions else None

    def leds_off(self):
        return None


class DummyUI:
    def __init__(self, *, choices: list[str] | None = None, rolls: list[int] | None = None):
        self.enabled = True
        self.allow_cli_fallback = False
        self._choices = list(choices or [])
        self._rolls = list(rolls or [])
        self.choice_prompts: list[str] = []

    def prompt_choice(self, prompt, choices=None, **_kwargs):
        self.choice_prompts.append(str(prompt))
        if self._choices:
            return self._choices.pop(0)
        if choices:
            return choices[0]
        return None

    def prompt_roll(self, _prompt, **_kwargs):
        if self._rolls:
            return int(self._rolls.pop(0))
        return 0

    def prompt_info(self, *_args, **_kwargs):
        return None


def _combat_game(*, heroes, enemies, ui):
    logs: list[str] = []
    game = SimpleNamespace(
        heroes=list(heroes),
        enemies=list(enemies),
        ui=ui,
        conn=DummyConn(),
        board=SimpleNamespace(),
        ui_log=lambda msg: logs.append(str(msg)),
        ui_event=lambda *_a, **_k: None,
        ui_hero=lambda *_a, **_k: None,
        ui_active_actor=lambda *_a, **_k: None,
        _logs=logs,
    )
    combat = Combat(game)
    game.state = combat
    return game


def _resolver_game(*, ui=None, events=None):
    return SimpleNamespace(
        state=object(),
        ui=ui,
        events=events,
        ui_log=lambda *_a, **_k: None,
    )


def test_counterspell_reaction_disrupts_enemy_spell(monkeypatch):
    ui = DummyUI(choices=["tak", "tak"], rolls=[23, 20])
    monkeypatch.setattr("GameObjects.interactions_mixin.prompt_utils.get_ui_client", lambda: ui)

    hero = DummyActor(name="hero", object_id="hero", position=(0, 0))
    hero.statuses = [Status(id="counterspell")]
    hero.reactions = [CounterspellReaction()]
    enemy = DummyActor(name="enemy", object_id="enemy", position=(2, 2))

    game = _combat_game(heroes=[hero], enemies=[enemy], ui=ui)
    event = {
        "actor": enemy,
        "action_id": "fireball_pre",
        "action_tags": ["magic", "spell"],
        "spell_name": "fireball",
        "event_uid": "spell-1",
    }

    dispatch_reactions(game, event)

    assert event.get("disrupted") is True
    assert event.get("disruption_reason") == "counterspell"
    assert hero.reactions_left == 0
    assert any("counterspell" in prompt.lower() and "fireball" in prompt.lower() for prompt in ui.choice_prompts)


def test_counterspell_triggers_without_known_spell_autocheck():
    actor = DummyActor()
    actor.statuses = [Status(id="counterspell")]
    reaction = CounterspellReaction()
    event = {"action_id": "magic_missile_pre", "action_tags": ["magic", "spell"], "spell_name": "magic_missile"}

    assert reaction.triggers(actor, event) is True


class _InterruptedSpell(MagicEvent):
    name = "interrupted_spell"
    spell_tags = ["rank1", "arcane"]

    def __init__(self):
        self.was_run = False

    def execute(self, ctx: EventContext) -> EventResult:
        _ = ctx
        self.was_run = True
        return EventResult(success=True, consumed_action=True, message="ok")


def test_magic_resolver_stops_cast_when_pre_event_is_disrupted():
    actor = DummyActor()
    fake_events = SimpleNamespace(safe_emit_action=lambda **_kwargs: {"disrupted": True, "disruption_reason": "counterspell"})
    ctx = EventContext(game=_resolver_game(events=fake_events), actor=actor)
    event = _InterruptedSpell()

    result = MagicEventResolver.resolve(event, ctx)

    assert result.success is False
    assert result.consumed_action is True
    assert event.was_run is False
    assert "przerwany" in str(result.message or "").lower()


class _DamageSpell(MagicEvent):
    name = "dangerous_test_spell"
    spell_tags = ["rank1", "arcane", "evocation"]

    def __init__(self):
        self.last_damage = None

    def execute(self, ctx: EventContext) -> EventResult:
        _ = ctx
        self.last_damage = int(
            prompt_for_roll(
                "Damage spell - podaj obrazenia:",
                layout="damage",
                answer_placeholder="Obrazenia",
            )
            or 0
        )
        return EventResult(success=True, consumed_action=True, data={"damage": self.last_damage})


def test_dangerous_sorcery_bonus_is_added_inside_damage_prompt(monkeypatch):
    ui = DummyUI(choices=["tak", "3"], rolls=[12])
    monkeypatch.setattr("GameObjects.interactions_mixin.prompt_utils.get_ui_client", lambda: ui)

    actor = DummyActor()
    actor.statuses = [Status(id="dangerous_sorcery", data={"dangerous_sorcery_damage_bonus_per_spell_level": 1})]
    ctx = EventContext(game=_resolver_game(ui=SimpleNamespace(enabled=True, allow_cli_fallback=False)), actor=actor)
    event = _DamageSpell()

    result = MagicEventResolver.resolve(event, ctx)

    assert result.success is True
    assert event.last_damage == 15


class _BloodlineGrantedSpell(MagicEvent):
    name = "magic_missile"
    spell_tags = ["rank1", "arcane", "evocation"]

    def execute(self, ctx: EventContext) -> EventResult:
        target = getattr(ctx, "metadata", {}).get("target")
        return EventResult(success=True, consumed_action=True, data={"target": target})


class _BloodlineFocusSpell(MagicEvent):
    name = "dragon_claws"
    spell_tags = ["focus", "arcane", "transmutation"]

    def execute(self, ctx: EventContext) -> EventResult:
        _ = ctx
        return EventResult(success=True, consumed_action=True)


def test_blood_magic_triggers_for_granted_bloodline_spell():
    target = DummyActor(name="target", object_id="target")
    actor = DummyActor()
    actor.statuses = [
        Status(
            id="sorcerer",
            data={
                "sorcerer_setup": {
                    "bloodline": "imperial",
                    "bloodline_granted_spells": {"rank_1": "magic_missile"},
                }
            },
        )
    ]
    ui = SimpleNamespace(enabled=False, allow_cli_fallback=False, prompt_choice=lambda *_a, **_k: None)
    ctx = EventContext(game=_resolver_game(ui=ui), actor=actor, metadata={"target": target})
    event = _BloodlineGrantedSpell()

    result = MagicEventResolver.resolve(event, ctx)

    assert result.success is True
    assert any(getattr(effect, "source", "") == "blood_magic:imperial" for effect in actor.bonuses)
    assert any(getattr(effect, "tag", "") == "arcana" for effect in actor.bonuses)


def test_blood_magic_triggers_for_focus_spell():
    actor = DummyActor()
    actor.statuses = [
        Status(
            id="sorcerer",
            data={
                "sorcerer_setup": {
                    "bloodline": "draconic",
                    "bloodline_initial_focus_spell": "dragon_claws",
                }
            },
        )
    ]
    ui = SimpleNamespace(enabled=False, allow_cli_fallback=False, prompt_choice=lambda *_a, **_k: None)
    ctx = EventContext(game=_resolver_game(ui=ui), actor=actor)
    event = _BloodlineFocusSpell()

    result = MagicEventResolver.resolve(event, ctx)

    assert result.success is True
    assert any(getattr(effect, "source", "") == "blood_magic:draconic" for effect in actor.bonuses)
    assert any(getattr(effect, "tag", "") == "ac" for effect in actor.bonuses)


def test_sorcerer_initial_focus_spells_are_registered():
    events = list_events()
    for spell_name in (
        "ancestral_memories",
        "angelic_halo",
        "diabolic_edict",
        "dragon_claws",
        "elemental_toss",
        "faerie_dust",
        "gluttons_jaws",
        "jealous_hex",
        "tentacular_limbs",
        "undeaths_blessing",
    ):
        assert spell_name in events


def test_elemental_toss_focus_event_spends_focus_and_deals_damage(monkeypatch):
    actor = DummyActor(name="sorc", object_id="sorc", position=(0, 0), hp=20)
    actor.class_name = "sorcerer"
    actor.focus_point = 1
    actor.statuses = [
        Status(
            id="sorcerer",
            data={
                "sorcerer_setup": {
                    "bloodline": "elemental",
                    "bloodline_initial_focus_spell": "elemental_toss",
                    "elemental_damage_type": "fire",
                }
            },
        )
    ]
    target = DummyActor(name="enemy", object_id="enemy", position=(1, 0), hp=20)
    game = SimpleNamespace(
        state=object(),
        heroes=[actor],
        enemies=[target],
        conn=DummyConn(choice_pos=(1, 0)),
        ui=SimpleNamespace(enabled=False, allow_cli_fallback=False, prompt_choice=lambda *_a, **_k: None),
        board=SimpleNamespace(),
        ui_log=lambda *_a, **_k: None,
    )

    rolls = iter([20, 8])
    monkeypatch.setattr(sorcerer_focus_spell_events, "prompt_for_roll", lambda *_a, **_k: next(rolls))

    result = dispatch_event("elemental_toss", EventContext(game=game, actor=actor))

    assert result.success is True
    assert actor.focus_point == 0
    assert target.hp == 4
