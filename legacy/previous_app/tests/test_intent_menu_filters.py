from __future__ import annotations

from dataclasses import dataclass, field

from states.intent_menu import filter_events_for_actor, filter_player_events


@dataclass
class _Status:
    id: str


@dataclass
class _Actor:
    class_name: str = ""
    ancestry: str = ""
    statuses: list[_Status] = field(default_factory=list)
    status_payloads: dict[str, dict] = field(default_factory=dict)

    def has_status(self, status_id: str) -> bool:
        wanted = str(status_id or "").strip().lower()
        return any(str(getattr(s, "id", s)).strip().lower() == wanted for s in self.statuses)

    def get_status_data(self, status_id: str, field: str | None = None, default=None):
        payload = dict(self.status_payloads.get(str(status_id or "").strip().lower(), {}))
        if field is None:
            return payload
        return payload.get(field, default)

    def __hash__(self) -> int:
        return id(self)


def _event_cls(module: str, tags: list[str]):
    return type("DummyEvent", (), {"__module__": module, "default_tags": tags, "available_in_combat": True, "available_in_exploration": True})


def test_filter_player_events_hides_internal_attack_events_except_base_attack():
    events = {
        "attack": _event_cls("GameObjects.events.attack.attack_event", ["attack"]),
        "dagger": _event_cls("GameObjects.events.attack.attack_dagger_event", ["attack_melee"]),
        "move": _event_cls("GameObjects.events.move_event", ["move"]),
    }

    filtered = filter_player_events(events, actor_is_hero=True)

    assert "attack" in filtered
    assert "move" in filtered
    assert "dagger" not in filtered


def test_filter_player_events_hides_internal_cancel_and_skill_check():
    events = {
        "cancel": _event_cls("GameObjects.events.cancel_action_event", ["cancel"]),
        "skill_check": _event_cls("GameObjects.events.checks.skill_check_event", ["skill_check"]),
        "move": _event_cls("GameObjects.events.move_event", ["move"]),
    }

    filtered = filter_player_events(events, actor_is_hero=True)

    assert "cancel" not in filtered
    assert "skill_check" not in filtered
    assert "move" in filtered


def test_filter_player_events_hides_enemy_module_and_enemy_tag_actions():
    events = {
        "goblin_dog_scratch": _event_cls("GameObjects.events.enemy.goblin_dog_scratch_event", ["enemy", "disease"]),
        "move": _event_cls("GameObjects.events.move_event", ["move"]),
    }

    filtered = filter_player_events(events, actor_is_hero=True)

    assert "goblin_dog_scratch" not in filtered
    assert "move" in filtered


def test_filter_events_for_actor_hides_command_animal_without_status():
    events = {
        "command_animal_companion": _event_cls("GameObjects.events.command_animal_companion_event", ["companion", "command"]),
        "demoralize": _event_cls("GameObjects.events.demoralize_event", ["skill"]),
    }
    actor = _Actor(class_name="fighter")

    filtered = filter_events_for_actor(events, actor=actor, in_combat=True)

    assert "demoralize" in filtered
    assert "command_animal_companion" not in filtered


def test_filter_events_for_actor_keeps_command_animal_with_status():
    events = {
        "command_animal_companion": _event_cls("GameObjects.events.command_animal_companion_event", ["companion", "command"]),
    }
    actor = _Actor(class_name="ranger", statuses=[_Status("animal_companion")])

    filtered = filter_events_for_actor(events, actor=actor, in_combat=True)

    assert "command_animal_companion" in filtered


def test_filter_events_for_actor_hides_moment_of_clarity_without_rage():
    events = {
        "moment_of_clarity": _event_cls("GameObjects.events.moment_of_clarity_event", ["barbarian"]),
    }
    actor = _Actor(class_name="barbarian", statuses=[_Status("moment_of_clarity")])

    filtered = filter_events_for_actor(events, actor=actor, in_combat=True)

    assert "moment_of_clarity" not in filtered


def test_filter_events_for_actor_keeps_moment_of_clarity_with_rage():
    events = {
        "moment_of_clarity": _event_cls("GameObjects.events.moment_of_clarity_event", ["barbarian"]),
    }
    actor = _Actor(class_name="barbarian", statuses=[_Status("rage"), _Status("moment_of_clarity")])

    filtered = filter_events_for_actor(events, actor=actor, in_combat=True)

    assert "moment_of_clarity" in filtered


def test_filter_events_for_actor_hides_moment_of_clarity_without_feat():
    events = {
        "moment_of_clarity": _event_cls("GameObjects.events.moment_of_clarity_event", ["barbarian"]),
    }
    actor = _Actor(class_name="barbarian", statuses=[_Status("rage")])

    filtered = filter_events_for_actor(events, actor=actor, in_combat=True)

    assert "moment_of_clarity" not in filtered


def test_filter_events_for_actor_hides_raise_shield_without_equipped_shield():
    events = {
        "shield": _event_cls("GameObjects.events.raise_shield_event", ["raise_shield", "defense"]),
    }
    actor = _Actor(class_name="fighter")

    filtered = filter_events_for_actor(events, actor=actor, in_combat=True)

    assert "shield" not in filtered


def test_filter_events_for_actor_keeps_raise_shield_with_shield_data():
    events = {
        "shield": _event_cls("GameObjects.events.raise_shield_event", ["raise_shield", "defense"]),
    }
    actor = _Actor(class_name="fighter")
    setattr(actor, "shield_hardness", 5)
    setattr(actor, "shield_hp", 20)
    setattr(actor, "shield_bt", 10)

    filtered = filter_events_for_actor(events, actor=actor, in_combat=True)

    assert "shield" in filtered


def test_filter_events_for_actor_hides_rage_for_non_barbarian():
    events = {
        "rage": _event_cls("GameObjects.events.rage_event", ["rage", "stance"]),
    }
    actor = _Actor(class_name="fighter")

    filtered = filter_events_for_actor(events, actor=actor, in_combat=True)

    assert "rage" not in filtered


def test_filter_events_for_actor_keeps_rage_for_barbarian():
    events = {
        "rage": _event_cls("GameObjects.events.rage_event", ["rage", "stance"]),
    }
    actor = _Actor(class_name="barbarian")

    filtered = filter_events_for_actor(events, actor=actor, in_combat=True)

    assert "rage" in filtered


def test_filter_events_for_actor_hides_goblin_song_without_feat_status():
    events = {
        "goblin_song": _event_cls("GameObjects.events.goblin_song_event", ["performance", "sonic"]),
    }
    actor = _Actor(class_name="fighter", ancestry="human")

    filtered = filter_events_for_actor(events, actor=actor, in_combat=True)

    assert "goblin_song" not in filtered


def test_filter_events_for_actor_keeps_goblin_song_with_feat_status():
    events = {
        "goblin_song": _event_cls("GameObjects.events.goblin_song_event", ["performance", "sonic"]),
    }
    actor = _Actor(class_name="fighter", ancestry="goblin", statuses=[_Status("goblin_song")])

    filtered = filter_events_for_actor(events, actor=actor, in_combat=True)

    assert "goblin_song" in filtered


def test_filter_events_for_actor_hides_drain_bonded_item_for_non_wizard():
    events = {
        "drain_bonded_item": _event_cls("GameObjects.events.wizard_runtime_events", []),
    }
    actor = _Actor(class_name="fighter")

    filtered = filter_events_for_actor(events, actor=actor, in_combat=True)

    assert "drain_bonded_item" not in filtered


def test_filter_events_for_actor_hides_drain_action_not_matching_wizard_setup():
    events = {
        "drain_familiar": _event_cls("GameObjects.events.wizard_runtime_events", []),
    }
    actor = _Actor(
        class_name="wizard",
        status_payloads={"wizard": {"wizard_setup": {"drain_action": "drain_bonded_item"}}},
    )

    filtered = filter_events_for_actor(events, actor=actor, in_combat=True)

    assert "drain_familiar" not in filtered


def test_filter_events_for_actor_keeps_matching_drain_action_for_wizard_setup():
    events = {
        "drain_familiar": _event_cls("GameObjects.events.wizard_runtime_events", []),
    }
    actor = _Actor(
        class_name="wizard",
        status_payloads={"wizard": {"wizard_setup": {"drain_action": "drain_familiar"}}},
    )

    filtered = filter_events_for_actor(events, actor=actor, in_combat=True)

    assert "drain_familiar" in filtered


def test_filter_events_for_actor_hides_wizard_spell_substitution_without_matching_thesis():
    events = {
        "wizard_spell_substitution": _event_cls("GameObjects.events.wizard_runtime_events", []),
    }
    actor = _Actor(
        class_name="wizard",
        status_payloads={"wizard": {"wizard_setup": {"thesis": "spell_blending"}}},
    )

    filtered = filter_events_for_actor(events, actor=actor, in_combat=False)

    assert "wizard_spell_substitution" not in filtered


def test_filter_events_for_actor_keeps_wizard_spell_substitution_for_matching_thesis():
    events = {
        "wizard_spell_substitution": _event_cls("GameObjects.events.wizard_runtime_events", []),
    }
    actor = _Actor(
        class_name="wizard",
        status_payloads={"wizard": {"wizard_setup": {"thesis": "spell_substitution"}}},
    )

    filtered = filter_events_for_actor(events, actor=actor, in_combat=False)

    assert "wizard_spell_substitution" in filtered


def test_filter_events_for_actor_hides_wizard_spell_substitution_after_scenario_use():
    events = {
        "wizard_spell_substitution": _event_cls("GameObjects.events.wizard_runtime_events", []),
    }
    actor = _Actor(
        class_name="wizard",
        status_payloads={"wizard": {"wizard_setup": {"thesis": "spell_substitution"}}},
    )
    setattr(actor, "object_id", "wiz-1")
    game = type("GameStub", (), {"_wizard_spell_substitution_used": {"actor:wiz-1"}})()

    filtered = filter_events_for_actor(events, actor=actor, in_combat=False, game=game)

    assert "wizard_spell_substitution" not in filtered


def test_filter_events_for_actor_keeps_retrain_sorcerer_spell_with_eligible_swap():
    events = {
        "retrain_sorcerer_spell": _event_cls("GameObjects.events.sorcerer_runtime_events", ["sorcerer"]),
    }
    actor = _Actor(
        class_name="sorcerer",
        statuses=[_Status("sorcerer")],
        status_payloads={
            "sorcerer": {
                "sorcerer_setup": {
                    "spell_tradition": "arcane",
                    "bloodline_granted_spells": {"rank_1": "magic_missile"},
                }
            }
        },
    )
    setattr(actor, "sorcerer_spell_tradition", "arcane")
    setattr(actor, "sorcerer_known_cantrips", [])
    setattr(actor, "sorcerer_known_rank_1_spells", ["magic_missile", "fear"])
    setattr(
        actor,
        "spell_state",
        {
            "enabled": True,
            "enforce": True,
            "class_name": "sorcerer",
            "known": {"cantrip": [], "rank_1": ["magic_missile", "fear"]},
            "slot_total": {"rank_1": 3},
            "slot_remaining": {"rank_1": 3},
        },
    )

    filtered = filter_events_for_actor(events, actor=actor, in_combat=False)

    assert "retrain_sorcerer_spell" in filtered


def test_filter_events_for_actor_hides_retrain_sorcerer_spell_without_eligible_swap():
    events = {
        "retrain_sorcerer_spell": _event_cls("GameObjects.events.sorcerer_runtime_events", ["sorcerer"]),
    }
    actor = _Actor(
        class_name="sorcerer",
        statuses=[_Status("sorcerer")],
        status_payloads={
            "sorcerer": {
                "sorcerer_setup": {
                    "spell_tradition": "arcane",
                    "bloodline_granted_spells": {"rank_1": "magic_missile"},
                }
            }
        },
    )
    setattr(actor, "sorcerer_spell_tradition", "arcane")
    setattr(actor, "sorcerer_known_cantrips", [])
    setattr(actor, "sorcerer_known_rank_1_spells", ["magic_missile"])
    setattr(
        actor,
        "spell_state",
        {
            "enabled": True,
            "enforce": True,
            "class_name": "sorcerer",
            "known": {"cantrip": [], "rank_1": ["magic_missile"]},
            "slot_total": {"rank_1": 3},
            "slot_remaining": {"rank_1": 3},
        },
    )

    filtered = filter_events_for_actor(events, actor=actor, in_combat=False)

    assert "retrain_sorcerer_spell" not in filtered


def test_filter_events_for_actor_shows_refocus_for_focus_pool_not_full():
    events = {
        "refocus": _event_cls("GameObjects.events.wizard_runtime_events", []),
    }
    actor = _Actor(class_name="champion")
    setattr(actor, "focus_point", 0)
    setattr(actor, "focus_pool_max", 1)

    filtered = filter_events_for_actor(events, actor=actor, in_combat=False)

    assert "refocus" in filtered


def test_filter_events_for_actor_hides_refocus_for_full_focus_pool():
    events = {
        "refocus": _event_cls("GameObjects.events.wizard_runtime_events", []),
    }
    actor = _Actor(class_name="champion")
    setattr(actor, "focus_point", 1)
    setattr(actor, "focus_pool_max", 1)

    filtered = filter_events_for_actor(events, actor=actor, in_combat=False)

    assert "refocus" not in filtered


def test_filter_events_for_actor_hides_trap_actions_without_detected_traps():
    events = {
        "identify_trap": _event_cls("GameObjects.events.trap_events", ["trap", "identify", "skill", "thievery"]),
        "disable_device": _event_cls("GameObjects.events.trap_events", ["trap", "disable", "skill", "thievery"]),
    }
    actor = _Actor(class_name="rogue")
    board = type("BoardStub", (), {"rows": 1, "cols": 1, "interactables_at": lambda self, _pos: []})()
    game = type("GameStub", (), {"board": board})()

    filtered = filter_events_for_actor(events, actor=actor, in_combat=True, game=game)

    assert "identify_trap" not in filtered
    assert "disable_device" not in filtered


def test_filter_events_for_actor_keeps_trap_actions_with_detected_armed_trap():
    events = {
        "identify_trap": _event_cls("GameObjects.events.trap_events", ["trap", "identify", "skill", "thievery"]),
        "disable_device": _event_cls("GameObjects.events.trap_events", ["trap", "disable", "skill", "thievery"]),
    }
    actor = _Actor(class_name="rogue")
    trap = type(
        "TrapStub",
        (),
        {
            "trap_armed": True,
            "trap_detected": True,
            "detect_trap": lambda self, *_args, **_kwargs: None,
            "disable_trap": lambda self, *_args, **_kwargs: None,
        },
    )()
    board = type("BoardStub", (), {"rows": 1, "cols": 1, "interactables_at": lambda self, _pos: [trap]})()
    game = type("GameStub", (), {"board": board})()

    filtered = filter_events_for_actor(events, actor=actor, in_combat=True, game=game)

    assert "identify_trap" in filtered
    assert "disable_device" in filtered


def test_filter_events_for_actor_hides_exacting_strike_before_first_attack():
    events = {
        "exacting_strike": _event_cls("GameObjects.events.fighter_feat_events", ["fighter", "attack", "press"]),
    }
    actor = _Actor(class_name="fighter", statuses=[_Status("exacting_strike")])
    game = type("GameStub", (), {"state": type("CombatStateStub", (), {"attack_state": {actor: {"attacks_this_turn": 0}}})()})()

    filtered = filter_events_for_actor(events, actor=actor, in_combat=True, game=game)

    assert "exacting_strike" not in filtered


def test_filter_events_for_actor_keeps_exacting_strike_after_first_attack():
    events = {
        "exacting_strike": _event_cls("GameObjects.events.fighter_feat_events", ["fighter", "attack", "press"]),
    }
    actor = _Actor(class_name="fighter", statuses=[_Status("exacting_strike")])
    game = type("GameStub", (), {"state": type("CombatStateStub", (), {"attack_state": {actor: {"attacks_this_turn": 1}}})()})()

    filtered = filter_events_for_actor(events, actor=actor, in_combat=True, game=game)

    assert "exacting_strike" in filtered
