from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (PROJECT_ROOT, SRC_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from GameObjects.interactions_mixin.status_mixin import StatusMixin
from GameObjects.interactions_mixin.bonus_mixin import BonusMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources_from_roll
from GameObjects.events.attack import attack_base
from GameObjects.events.base import EventContext, EventResult, GameEvent
from combat.flanking import flat_footed_penalty
from combat.hp_engine import computed_max_hp
from GameObjects.items.shield import StandardShield
from skills import Skill
from statuses import (
    Status,
    BlindedStatus,
    BrokenStatus,
    ClumsyStatus,
    CONCEALED_STATUS,
    ConfusedStatus,
    ControlledStatus,
    DazzledStatus,
    DeafenedStatus,
    DoomedStatus,
    DrainedStatus,
    dying_value,
    on_reduced_to_zero,
    EncumberedStatus,
    EnfeebledStatus,
    enfeebled_attack_penalty_effects,
    FascinatedStatus,
    FatiguedStatus,
    OffGuardStatus,
    FleeingStatus,
    FrightenedStatus,
    frightened_value,
    decrement_end_of_turn_conditions,
    GrabbedStatus,
    apply_grabbed_effects,
    HiddenStatus,
    ImmobilizedStatus,
    InvisibleStatus,
    ParalyzedStatus,
    make_persistent_damage,
    process_persistent_damage,
    PetrifiedStatus,
    ProneStatus,
    apply_prone_effects,
    QuickenedStatus,
    RestrainedStatus,
    apply_restrained_effects,
    SickenedStatus,
    SlowedStatus,
    StunnedStatus,
    consume_stunned_actions,
    StupefiedStatus,
    UndetectedStatus,
    UnnoticedStatus,
    set_wounded,
    action_limit_modifier,
    attack_penalty_value,
    ac_penalty_value,
    skill_penalty_value,
    action_block_reason,
    visibility_block_reason,
)


class DummyActor(StatusMixin, BonusMixin):
    def __init__(self, name: str, *, level: int = 1, hp: int = 30, max_hp: int = 30):
        StatusMixin.__init__(self)
        BonusMixin.__init__(self)
        self.name = name
        self.object_id = name
        self.level = int(level)
        self.hp = int(hp)
        self.max_hp = int(max_hp)
        self.wounds = 0
        self.reactions = []

    def apply_damage(self, amount: int, _damage_type: str):
        self.hp = max(0, int(self.hp) - int(amount))


class DummyMoveEvent(GameEvent):
    name = "dummy_move"
    default_tags = ["move"]

    def execute(self, ctx: EventContext) -> EventResult:
        _ = ctx
        return EventResult(success=True, consumed_action=True, message="ok")


class DummyAttackEvent(GameEvent):
    name = "dummy_attack"
    default_tags = ["attack", "concentrate"]

    def execute(self, ctx: EventContext) -> EventResult:
        _ = ctx
        return EventResult(success=True, consumed_action=True, message="ok")


def cast_status_spell(caster: DummyActor, target: DummyActor, status: Status) -> None:
    assert caster is not None
    target.add_status(status)


def _ctx(attacker: DummyActor):
    return SimpleNamespace(actor=attacker, game=SimpleNamespace(ui_log=lambda *_a, **_k: None, ui=None))


def test_blinded_spell_requires_high_flat_check(monkeypatch):
    caster = DummyActor("wizard")
    attacker = DummyActor("fighter")
    target = DummyActor("enemy")
    cast_status_spell(caster, attacker, BlindedStatus())
    monkeypatch.setattr(attack_base, "prompt_for_roll", lambda *_a, **_k: 10)
    assert attack_base.check_concealed(_ctx(attacker), target) is False


def test_broken_spell_like_shatter_can_break_shield():
    caster = DummyActor("wizard")
    _ = BrokenStatus(source="spell:shatter", source_id=caster.object_id)
    shield = StandardShield()
    outcome = shield.apply_shield_block(15)
    assert outcome.became_broken is True


def test_clumsy_spell_applies_expected_penalties():
    caster = DummyActor("alchemist")
    target = DummyActor("rogue")
    cast_status_spell(caster, target, ClumsyStatus(value=2, source="spell:hex"))
    status = target.get_status("clumsy")
    assert status is not None
    assert (status.data or {}).get("clumsy_ac_penalty") == 2
    assert (status.data or {}).get("clumsy_reflex_penalty") == 2


def test_concealed_spell_forces_dc5_flat_check(monkeypatch):
    caster = DummyActor("illusionist")
    attacker = DummyActor("fighter")
    target = DummyActor("enemy")
    cast_status_spell(caster, target, CONCEALED_STATUS)
    monkeypatch.setattr(attack_base, "prompt_for_roll", lambda *_a, **_k: 4)
    assert attack_base.check_concealed(_ctx(attacker), target) is False


def test_confused_spell_blocks_controlled_action_choice():
    caster = DummyActor("sorcerer")
    target = DummyActor("barbarian")
    cast_status_spell(caster, target, ConfusedStatus(source="spell:confusion"))
    reason = action_block_reason(target, action_tags=["attack"], action_name="attack")
    assert reason and "confused" in reason.lower()


def test_controlled_spell_blocks_actions():
    caster = DummyActor("vampire")
    target = DummyActor("hero")
    cast_status_spell(caster, target, ControlledStatus(source="dominate", controller_id=caster.object_id))
    reason = action_block_reason(target, action_tags=["attack"], action_name="attack")
    assert reason and "controlled" in reason.lower()


def test_dazzled_spell_adds_dc5_flat_check(monkeypatch):
    caster = DummyActor("wizard")
    attacker = DummyActor("hero")
    target = DummyActor("enemy")
    cast_status_spell(caster, attacker, DazzledStatus(source="color_spray"))
    monkeypatch.setattr(attack_base, "prompt_for_roll", lambda *_a, **_k: 4)
    assert attack_base.check_concealed(_ctx(attacker), target) is False


def test_deafened_spell_auto_fails_auditory_checks():
    caster = DummyActor("bard")
    target = DummyActor("enemy")
    cast_status_spell(caster, target, DeafenedStatus(source="thunder"))
    result = resolve_skill_check_with_sources_from_roll(
        skill_id=Skill.PERCEPTION.value,
        dc=10,
        actor=target,
        tags=["auditory", Skill.PERCEPTION.value],
        roll=20,
        apply_modifiers=True,
    )
    assert result.outcome == "critical_failure"


def test_doomed_spell_reduces_death_threshold():
    actor = DummyActor("hero")
    actor.add_status(DoomedStatus(value=1, source="curse"))
    from statuses import death_threshold

    assert death_threshold(actor) == 3


def test_drained_spell_reduces_max_hp_by_level_multiplier():
    caster = DummyActor("wraith")
    target = DummyActor("hero", level=5, hp=30, max_hp=30)
    cast_status_spell(caster, target, DrainedStatus(value=2, source="drain_life"))
    assert computed_max_hp(target) == 20


def test_dying_spell_scenario_sets_dying_and_unconscious():
    target = DummyActor("hero", hp=0, max_hp=20)
    target.wounds = 20
    result = on_reduced_to_zero(target, source="death_touch")
    assert result["dead"] is False
    assert dying_value(target) == 1
    assert target.has_status("unconscious")


def test_encumbered_spell_applies_speed_penalty_and_clumsy():
    caster = DummyActor("giant")
    target = DummyActor("hero")
    cast_status_spell(caster, target, EncumberedStatus(source="burden"))
    assert target.has_status("encumbered")
    assert target.has_status("speed_penalty")
    assert target.has_status("clumsy")


def test_enfeebled_spell_penalizes_attack_rolls():
    caster = DummyActor("necromancer")
    target = DummyActor("fighter")
    cast_status_spell(caster, target, EnfeebledStatus(value=2, source="ray_of_enfeeblement"))
    effects = enfeebled_attack_penalty_effects(target, "attack_melee")
    assert effects and effects[0].value == 2 and effects[0].is_penalty


def test_fascinated_spell_blocks_concentrate_actions_away_from_focus():
    caster = DummyActor("fey")
    target = DummyActor("hero")
    cast_status_spell(caster, target, FascinatedStatus(source="glitter", focus_target_id="idol"))
    reason = action_block_reason(target, action_tags=["concentrate"], action_name="cast", target=DummyActor("enemy"))
    assert reason and "fascinated" in reason.lower()


def test_fatigued_spell_applies_general_penalty():
    caster = DummyActor("gm")
    target = DummyActor("hero")
    cast_status_spell(caster, target, FatiguedStatus(source="march"))
    assert attack_penalty_value(target, action_tag="attack_melee") == 1
    assert ac_penalty_value(target) == 1


def test_off_guard_spell_counts_as_flat_footed_penalty():
    caster = DummyActor("rogue")
    target = DummyActor("enemy")
    cast_status_spell(caster, target, OffGuardStatus(source="feint"))
    assert flat_footed_penalty(target) == 2


def test_fleeing_spell_blocks_non_move_actions():
    caster = DummyActor("dragon")
    target = DummyActor("goblin")
    cast_status_spell(caster, target, FleeingStatus(source="frightful_presence"))
    assert action_block_reason(target, action_tags=["attack"], action_name="attack") is not None
    assert action_block_reason(target, action_tags=["move"], action_name="move") is None


def test_frightened_spell_applies_penalty_and_decays_end_of_turn():
    caster = DummyActor("bard")
    target = DummyActor("enemy")
    cast_status_spell(caster, target, FrightenedStatus(value=2, source="fear"))
    assert frightened_value(target) == 2
    assert attack_penalty_value(target, action_tag="attack_ranged") == 2
    decrement_end_of_turn_conditions(target)
    assert frightened_value(target) == 1


def test_grabbed_spell_applies_off_guard_linked_status():
    caster = DummyActor("tentacle")
    target = DummyActor("hero")
    cast_status_spell(caster, target, GrabbedStatus(source_id=caster.object_id))
    apply_grabbed_effects(target, source_id=caster.object_id)
    assert target.has_status("grabbed")
    assert target.has_status("flat_footed")


def test_hidden_spell_requires_dc11_flat_check(monkeypatch):
    caster = DummyActor("rogue")
    attacker = DummyActor("hero")
    target = DummyActor("target")
    cast_status_spell(caster, target, HiddenStatus(source="hide"))
    monkeypatch.setattr(attack_base, "prompt_for_roll", lambda *_a, **_k: 10)
    assert attack_base.check_concealed(_ctx(attacker), target) is False


def test_immobilized_spell_blocks_move_event_execution():
    caster = DummyActor("wizard")
    target = DummyActor("hero")
    cast_status_spell(caster, target, ImmobilizedStatus(source="tangle"))
    event = DummyMoveEvent()
    res = event.run(EventContext(game=SimpleNamespace(state=None), actor=target))
    assert res.success is False and "immobilized" in str(res.message).lower()


def test_invisible_spell_requires_dc11_flat_check(monkeypatch):
    caster = DummyActor("wizard")
    attacker = DummyActor("hero")
    target = DummyActor("enemy")
    cast_status_spell(caster, target, InvisibleStatus(source="invisibility"))
    monkeypatch.setattr(attack_base, "prompt_for_roll", lambda *_a, **_k: 10)
    assert attack_base.check_concealed(_ctx(attacker), target) is False


def test_paralyzed_spell_blocks_actions():
    caster = DummyActor("ghoul")
    target = DummyActor("hero")
    cast_status_spell(caster, target, ParalyzedStatus(source="ghoul_touch"))
    reason = action_block_reason(target, action_tags=["attack"], action_name="attack")
    assert reason and "sparaliż" in reason.lower()


def test_persistent_damage_spell_deals_damage_each_turn(monkeypatch):
    caster = DummyActor("wizard")
    target = DummyActor("hero", hp=30)
    target.add_status(make_persistent_damage(4, source="fireball"))
    monkeypatch.setattr("statuses.persistent_damage.prompt_for_roll", lambda *_a, **_k: 1)
    game = SimpleNamespace(heroes=[target], ui_log=lambda *_a, **_k: None)
    process_persistent_damage(target, game)
    assert target.hp == 26


def test_petrified_spell_blocks_actions():
    caster = DummyActor("medusa")
    target = DummyActor("hero")
    cast_status_spell(caster, target, PetrifiedStatus(source="gaze"))
    reason = action_block_reason(target, action_tags=["attack"], action_name="attack")
    assert reason and "skamienia" in reason.lower()


def test_prone_spell_applies_attack_penalties():
    caster = DummyActor("fighter")
    target = DummyActor("hero")
    cast_status_spell(caster, target, ProneStatus())
    apply_prone_effects(target)
    assert any(getattr(eff, "source", "") == "prone" for eff in target.bonuses)


def test_quickened_spell_increases_action_limit_modifier():
    caster = DummyActor("wizard")
    target = DummyActor("hero")
    cast_status_spell(caster, target, QuickenedStatus(source="haste"))
    assert action_limit_modifier(target) == 1


def test_restrained_spell_applies_off_guard_and_attack_penalty():
    caster = DummyActor("spider")
    target = DummyActor("hero")
    cast_status_spell(caster, target, RestrainedStatus(source_id=caster.object_id))
    apply_restrained_effects(target, source_id=caster.object_id)
    assert target.has_status("restrained")
    assert target.has_status("flat_footed")
    assert any(getattr(eff, "source", "") == "restrained" for eff in target.bonuses)


def test_sickened_spell_penalizes_attacks_and_checks():
    caster = DummyActor("zombie")
    target = DummyActor("hero")
    cast_status_spell(caster, target, SickenedStatus(value=2, source="stench"))
    assert attack_penalty_value(target, action_tag="attack_melee") == 2
    assert skill_penalty_value(target, skill_id=Skill.DIPLOMACY.value, tags=[Skill.DIPLOMACY.value]) >= 2


def test_slowed_spell_reduces_action_limit_modifier():
    caster = DummyActor("wizard")
    target = DummyActor("hero")
    cast_status_spell(caster, target, SlowedStatus(value=1, source="slow"))
    assert action_limit_modifier(target) == -1


def test_stunned_spell_consumes_actions():
    caster = DummyActor("ogre")
    target = DummyActor("hero")
    cast_status_spell(caster, target, StunnedStatus(value=2, source="smash"))
    assert consume_stunned_actions(target) == 2


def test_stupefied_spell_penalizes_mental_and_magic():
    caster = DummyActor("psychic")
    target = DummyActor("hero")
    cast_status_spell(caster, target, StupefiedStatus(value=2, source="mind_blast"))
    assert skill_penalty_value(target, skill_id=Skill.ARCANA.value, tags=[Skill.ARCANA.value]) >= 2
    assert attack_penalty_value(target, action_tag="magic") >= 2


def test_unconscious_status_blocks_actions():
    target = DummyActor("hero")
    target.add_status(Status(id="unconscious", label="Unconscious"))
    reason = action_block_reason(target, action_tags=["attack"], action_name="attack")
    assert reason and "nieprzytom" in reason.lower()


def test_undetected_spell_requires_dc11_flat_check(monkeypatch):
    caster = DummyActor("rogue")
    attacker = DummyActor("hero")
    target = DummyActor("enemy")
    cast_status_spell(caster, target, UndetectedStatus(source="stealth"))
    monkeypatch.setattr(attack_base, "prompt_for_roll", lambda *_a, **_k: 10)
    assert attack_base.check_concealed(_ctx(attacker), target) is False


def test_unnoticed_spell_blocks_targeting():
    caster = DummyActor("rogue")
    target = DummyActor("enemy")
    cast_status_spell(caster, target, UnnoticedStatus(source="sneak"))
    blocker = visibility_block_reason(DummyActor("hero"), target)
    assert blocker and "unnoticed" in blocker.lower()


def test_wounded_state_increases_next_dying_value():
    actor = DummyActor("hero", hp=0, max_hp=20)
    actor.wounds = 20
    set_wounded(actor, 1, source="heal")
    result = on_reduced_to_zero(actor, source="damage")
    assert result["dying"] == 2
