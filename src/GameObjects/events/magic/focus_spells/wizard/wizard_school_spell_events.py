from __future__ import annotations

from bonuses import BonusEffect, BonusType
from combat import effective_ac
from combat.degree_of_success import is_critical_success, is_hit, natural_shift_from_roll, resolve_outcome
from combat.hp_engine import apply_damage as hp_apply_damage
from damage_types import DamageType
from skills import Skill
from statuses import Status, StunnedStatus
from GameObjects.interactions_mixin import prompt_for_roll

from ....base import EventContext, EventResult
from ....registry import register_event
from ...focus_utils import focus_spell_rank
from ...magic_event import MagicEvent
from ...magic_utils import grid_distance_feet, pick_position_in_range, pick_target_in_range
from ...spell_types import SpellTradition


def _normalize(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _is_wizard(actor) -> bool:
    if actor is None:
        return False
    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            if bool(checker("wizard")):
                return True
        except Exception:
            pass
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) == "wizard":
            return True
    return _normalize(getattr(actor, "class_name", "")) == "wizard"


def _focus_points(actor) -> int:
    try:
        return max(0, int(getattr(actor, "focus_point", 0) or 0))
    except Exception:
        return 0


def _set_focus_points(actor, value: int) -> None:
    try:
        setattr(actor, "focus_point", max(0, int(value)))
    except Exception:
        pass


def _wizard_setup(actor) -> dict:
    if actor is None:
        return {}
    getter = getattr(actor, "get_status_data", None)
    if callable(getter):
        try:
            setup = getter("wizard", "wizard_setup", {})
            if isinstance(setup, dict):
                return dict(setup)
        except Exception:
            pass
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) != "wizard":
            continue
        data = getattr(status, "data", None) or {}
        setup = data.get("wizard_setup")
        if isinstance(setup, dict):
            return dict(setup)
    return {}


def _known_wizard_focus_spells(actor) -> set[str]:
    known: set[str] = set()
    setup = _wizard_setup(actor)

    school_spell = _normalize(setup.get("school_focus_spell") or setup.get("wizard_school_focus_spell"))
    if school_spell:
        known.add(school_spell)

    for source in (
        getattr(actor, "wizard_focus_spells", None),
        setup.get("wizard_focus_spells"),
        setup.get("focus_spells"),
    ):
        if isinstance(source, list):
            for item in source:
                normalized = _normalize(item)
                if normalized:
                    known.add(normalized)

    attr_school_spell = _normalize(getattr(actor, "wizard_school_focus_spell", None))
    if attr_school_spell:
        known.add(attr_school_spell)

    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            if bool(checker("hand_of_the_apprentice")):
                known.add("hand_of_the_apprentice")
        except Exception:
            pass

    return known


def _knows_focus_spell(actor, spell_id: str) -> bool:
    return _normalize(spell_id) in _known_wizard_focus_spells(actor)


def _focus_rank(actor) -> int:
    return max(1, int(focus_spell_rank(actor, minimum=1) or 1))


def _iter_enemy_candidates(game):
    for enemy in getattr(game, "enemies", []) or []:
        yield enemy, getattr(enemy, "position", None), "enemy"


def _iter_hero_candidates(game):
    for hero in getattr(game, "heroes", []) or []:
        yield hero, getattr(hero, "position", None), "hero"


def _pick_target(ctx: EventContext, actor, *, range_feet: int | None, kinds: tuple[str, ...], allow_self: bool = False):
    source_pos = getattr(actor, "position", None)
    if source_pos is None:
        return None

    candidates = []
    if "enemy" in kinds:
        candidates.extend(list(_iter_enemy_candidates(ctx.game)))
    if "hero" in kinds:
        candidates.extend(list(_iter_hero_candidates(ctx.game)))

    target, _target_pos = pick_target_in_range(
        ctx,
        source_pos,
        candidates,
        max_range_feet=range_feet,
        allowed_kinds=kinds,
        tags=["magic", "focus", "wizard"],
    )
    if target is not None:
        return target
    if allow_self:
        return actor
    return None


def _prompt_choice(ctx: EventContext, prompt: str, choices: list[str], *, source: str) -> str | None:
    ui = getattr(ctx.game, "ui", None)
    if ui is None:
        return None
    chooser = getattr(ui, "prompt_choice", None)
    if callable(chooser):
        try:
            value = chooser(prompt, choices=choices, source=source)
            if value is not None:
                raw = str(value).strip()
                if raw:
                    return raw
        except Exception:
            pass
    if ui is not None and not getattr(ui, "allow_cli_fallback", False):
        return None
    try:
        raw = input(f"{prompt} {choices}: ").strip()
    except Exception:
        return None
    return raw or None


def _add_status(target, status: Status) -> None:
    if target is None:
        return
    adder = getattr(target, "add_status", None)
    if callable(adder):
        try:
            adder(status)
            return
        except Exception:
            pass
    statuses = getattr(target, "statuses", None)
    if isinstance(statuses, list):
        statuses.append(status)


def _remove_statuses(target, status_id: str) -> None:
    statuses = getattr(target, "statuses", None)
    if not isinstance(statuses, list):
        return
    try:
        target.statuses = [item for item in statuses if getattr(item, "id", None) != status_id]
    except Exception:
        pass


def _add_bonus(
    actor,
    *,
    tags: tuple[str, ...] | list[str],
    value: int,
    source: str,
    duration_turns: int = 1,
    bonus_type: BonusType = BonusType.STATUS,
    is_penalty: bool = False,
    target_id: str | None = None,
    label: str | None = None,
) -> int:
    if actor is None:
        return 0
    adder = getattr(actor, "add_bonus", None)
    if not callable(adder):
        bonuses = getattr(actor, "bonuses", None)
        if not isinstance(bonuses, list):
            return 0

        def _fallback_add(effect: BonusEffect):
            bonuses.append(effect)

        adder = _fallback_add

    count = 0
    for tag in tags:
        try:
            adder(
                BonusEffect(
                    type=bonus_type,
                    value=max(0, int(value)),
                    tag=str(tag),
                    source=source,
                    target_id=target_id,
                    label=label,
                    is_penalty=is_penalty,
                    duration_turns=max(1, int(duration_turns)),
                )
            )
            count += 1
        except Exception:
            continue
    return count


def _remove_bonus_prefix(actor, prefix: str) -> None:
    bonuses = getattr(actor, "bonuses", None)
    if not isinstance(bonuses, list):
        return
    normalized_prefix = str(prefix or "")
    try:
        actor.bonuses = [
            effect
            for effect in bonuses
            if not str(getattr(effect, "source", "") or "").startswith(normalized_prefix)
        ]
    except Exception:
        pass


def _apply_damage(target, amount: int, damage_type: str, *, source: str) -> bool:
    apply = getattr(target, "apply_damage", None)
    if callable(apply):
        try:
            _, defeated = apply(max(0, int(amount)), damage_type)
            return bool(defeated)
        except Exception:
            return False
    try:
        info = hp_apply_damage(target, amount, damage_type, source=source)
        return bool(info.get("defeated", False))
    except Exception:
        return False


def _actor_id(actor) -> str:
    return str(getattr(actor, "object_id", None) or getattr(actor, "name", None) or id(actor))


def _roll_int(prompt: str, *, layout: str = "test", answer_placeholder: str = "Wynik", prompt_long: str | None = None) -> int:
    try:
        value = prompt_for_roll(
            prompt,
            layout=layout,
            answer_placeholder=answer_placeholder,
            prompt_long=prompt_long,
        )
    except Exception:
        value = 0
    try:
        return int(value or 0)
    except Exception:
        return 0


def _actions_remaining(ctx: EventContext, actor) -> int | None:
    if not ctx.in_combat:
        return None
    state = getattr(ctx.game, "state", None)
    if state is None:
        return None
    getter = getattr(state, "actions_remaining", None)
    if callable(getter):
        try:
            return max(0, int(getter(actor)))
        except Exception:
            return None
    try:
        limit = int(getattr(state, "ACTION_LIMIT", 3) or 3)
        used = int((getattr(state, "actions_used", {}) or {}).get(actor, 0) or 0)
        return max(0, limit - used)
    except Exception:
        return None


def _apply_sickened(target, value: int, *, source: str) -> None:
    sickened = max(1, int(value))
    _remove_statuses(target, "sickened")
    _remove_bonus_prefix(target, f"{source}:sickened")

    _add_status(
        target,
        Status(
            id="sickened",
            label=f"Sickened {sickened}",
            duration=10,
            source=source,
            data={
                "sickened_value": sickened,
                "effect_tags": ["sickened", "status_penalty"],
            },
        ),
    )

    stat_tags = ["ac", "attack_melee", "attack_ranged", "magic", "damage"]
    stat_tags.extend([skill.value for skill in Skill])
    _add_bonus(
        target,
        tags=stat_tags,
        value=sickened,
        source=f"{source}:sickened",
        is_penalty=True,
        duration_turns=10,
        label=f"sickened {sickened}",
    )


class WizardFocusSpellEvent(MagicEvent):
    actions_cost = 1
    default_tags = ["magic", "spell", "focus", "wizard"]
    spell_tags = ["focus", "arcane", "wizard"]
    magic_traditions = (SpellTradition.ARCANA,)
    magic_types = ["focus"]
    required_focus_spell_id: str = ""

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message=f"{self.name}: missing actor.")
        if not _is_wizard(actor):
            return EventResult.cancelled(message=f"{self.name}: only Wizard can cast this focus spell.")
        if self.required_focus_spell_id and not _knows_focus_spell(actor, self.required_focus_spell_id):
            return EventResult.cancelled(message=f"{self.name}: focus spell is not known.")

        points = _focus_points(actor)
        if points <= 0:
            return EventResult.cancelled(message=f"{self.name}: no Focus Point.")

        result = self._execute_effect(ctx)
        if not result.success:
            return result

        _set_focus_points(actor, points - 1)
        result.message = f"{result.message or f'{self.name}: effect applied.'} Focus Point: {_focus_points(actor)}."
        return result

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        raise NotImplementedError


@register_event
class AugmentSummoningEvent(WizardFocusSpellEvent):
    name = "augment_summoning"
    required_focus_spell_id = "augment_summoning"
    range_feet = 30
    spell_tags = WizardFocusSpellEvent.spell_tags + ["conjuration"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        target = _pick_target(ctx, actor, range_feet=30, kinds=("hero", "enemy"))
        if target is None:
            return EventResult.cancelled(message="Augment Summoning: target not selected.")

        _add_status(
            target,
            Status(
                id="augment_summoning_active",
                label="Augment Summoning",
                duration=10,
                source=self.name,
                data={
                    "bonus": 1,
                    "summoned_only": True,
                    "effect_tags": ["summon", "status_bonus"],
                },
            ),
        )
        tags = ["ac", "attack_melee", "attack_ranged", "magic"]
        tags.extend([skill.value for skill in Skill])
        _add_bonus(
            target,
            tags=tags,
            value=1,
            source=self.name,
            duration_turns=10,
            label="augment summoning",
        )
        target_name = getattr(target, "name", "target")
        return EventResult(
            success=True,
            consumed_action=True,
            message=f"Augment Summoning: {target_name} gets +1 status to checks/DCs (up to 1 minute).",
            data={"target": target},
        )


@register_event
class CallOfTheGraveEvent(WizardFocusSpellEvent):
    name = "call_of_the_grave"
    required_focus_spell_id = "call_of_the_grave"
    actions_cost = 2
    range_feet = 30
    spell_tags = WizardFocusSpellEvent.spell_tags + ["attack", "necromancy", "negative"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        target = _pick_target(ctx, actor, range_feet=30, kinds=("enemy",))
        if target is None:
            return EventResult.cancelled(message="Call of the Grave: target not selected.")

        target_ac = int(getattr(target, "ac", effective_ac(target)) or 10)
        roll = _roll_int(
            f"Call of the Grave: spell attack vs AC {target_ac}",
            layout="test",
            answer_placeholder="d20",
        )
        outcome = resolve_outcome(roll, target_ac, natural_shift=natural_shift_from_roll(roll))
        if not is_hit(outcome):
            return EventResult(success=True, consumed_action=True, message="Call of the Grave: miss, no effect.")

        if is_critical_success(outcome):
            _apply_sickened(target, 2, source=self.name)
            _remove_statuses(target, "slowed")
            _add_status(
                target,
                Status(
                    id="slowed",
                    label="Slowed 1",
                    duration=10,
                    source=self.name,
                    data={
                        "slowed_value": 1,
                        "while_status": "sickened",
                        "effect_tags": ["slowed"],
                    },
                ),
            )
            msg = "Call of the Grave: critical success, target becomes sickened 2 and slowed 1 while sickened."
        else:
            _apply_sickened(target, 1, source=self.name)
            msg = "Call of the Grave: success, target becomes sickened 1."
        return EventResult(success=True, consumed_action=True, message=msg, data={"target": target, "outcome": outcome})


@register_event
class CharmingWordsEvent(WizardFocusSpellEvent):
    name = "charming_words"
    required_focus_spell_id = "charming_words"
    range_feet = 30
    spell_tags = WizardFocusSpellEvent.spell_tags + [
        "auditory",
        "enchantment",
        "incapacitation",
        "linguistic",
        "mental",
    ]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        target = _pick_target(ctx, actor, range_feet=30, kinds=("enemy",))
        if target is None:
            return EventResult.cancelled(message="Charming Words: target not selected.")

        outcome = _normalize(
            _prompt_choice(
                ctx,
                "Charming Words: choose Will save outcome",
                ["critical_success", "success", "failure", "critical_failure"],
                source=self.name,
            )
            or "success"
        )
        target_name = getattr(target, "name", "target")
        actor_target_id = _actor_id(actor)

        if outcome == "critical_success":
            return EventResult(success=True, consumed_action=True, message=f"Charming Words: {target_name} unaffected.")

        if outcome == "success":
            _add_bonus(
                target,
                tags=("attack_melee", "attack_ranged", "magic", "damage"),
                value=1,
                source=self.name,
                duration_turns=1,
                bonus_type=BonusType.CIRCUMSTANCE,
                is_penalty=True,
                target_id=actor_target_id,
                label="charming words",
            )
            _add_status(
                target,
                Status(
                    id="charming_words_distracted",
                    label="Charming Words",
                    duration=1,
                    source=self.name,
                    data={
                        "penalty_vs_target_id": actor_target_id,
                        "effect_tags": ["enchantment", "mental"],
                    },
                ),
            )
            return EventResult(
                success=True,
                consumed_action=True,
                message=f"Charming Words: {target_name} gets -1 circumstance vs caster until start of your next turn.",
            )

        _add_status(
            target,
            Status(
                id="charming_words_pacified",
                label="Charming Words Pacified",
                duration=1,
                source=self.name,
                data={
                    "cannot_use_hostile_actions_against": actor_target_id,
                    "effect_tags": ["mental", "enchantment", "pacified"],
                },
            ),
        )
        if outcome == "critical_failure":
            _add_status(target, StunnedStatus(value=1, duration=1, source=self.name))
            return EventResult(
                success=True,
                consumed_action=True,
                message=f"Charming Words: {target_name} is stunned 1 and cannot use hostile actions against you.",
            )
        return EventResult(
            success=True,
            consumed_action=True,
            message=f"Charming Words: {target_name} cannot use hostile actions against you.",
        )


@register_event
class DivinersSightEvent(WizardFocusSpellEvent):
    name = "diviners_sight"
    required_focus_spell_id = "diviners_sight"
    range_feet = 30
    spell_tags = WizardFocusSpellEvent.spell_tags + ["concentrate", "divination", "fortune"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        target = _pick_target(ctx, actor, range_feet=30, kinds=("hero",), allow_self=True)
        if target is None:
            return EventResult.cancelled(message="Diviner's Sight: target not selected.")

        stored_roll = _roll_int(
            "Diviner's Sight: roll d20 to store",
            layout="test",
            answer_placeholder="d20",
        )
        if stored_roll <= 0:
            return EventResult.cancelled(message="Diviner's Sight: invalid stored roll.")

        # Recasting ends old instances on caster and on target.
        _remove_statuses(actor, "diviners_sight_active")
        if target is not actor:
            _remove_statuses(target, "diviners_sight_active")

        _add_status(
            target,
            Status(
                id="diviners_sight_active",
                label="Diviner's Sight",
                duration=1,
                source=self.name,
                data={
                    "stored_d20": stored_roll,
                    "source_wizard_id": _actor_id(actor),
                    "effect_tags": ["fortune", "divination"],
                },
            ),
        )
        target_name = getattr(target, "name", "target")
        return EventResult(
            success=True,
            consumed_action=True,
            message=f"Diviner's Sight: stored d20={stored_roll} on {target_name} until end of next turn.",
            data={"target": target, "stored_d20": stored_roll},
        )


@register_event
class ForceBoltEvent(WizardFocusSpellEvent):
    name = "force_bolt"
    required_focus_spell_id = "force_bolt"
    range_feet = 30
    spell_tags = WizardFocusSpellEvent.spell_tags + ["evocation", "force"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        target = _pick_target(ctx, actor, range_feet=30, kinds=("enemy", "hero"))
        if target is None:
            return EventResult.cancelled(message="Force Bolt: target not selected.")

        rank = _focus_rank(actor)
        packets = 1 + max(0, (rank - 1) // 2)
        damage = _roll_int(
            "Force Bolt: enter damage",
            layout="damage",
            answer_placeholder="Damage",
            prompt_long=f"Rules hint: {packets}d4+{packets} force (auto-hit).",
        )
        if damage <= 0:
            return EventResult.cancelled(message="Force Bolt: damage must be > 0.")

        defeated = _apply_damage(target, damage, DamageType.FORCE.value, source=self.name)
        target_name = getattr(target, "name", "target")
        msg = f"Force Bolt: auto-hit {target_name} for {damage} force damage."
        if defeated:
            msg += " Target defeated."
        return EventResult(success=True, consumed_action=True, message=msg, data={"target": target, "damage": damage})


@register_event
class HandOfTheApprenticeEvent(WizardFocusSpellEvent):
    name = "hand_of_the_apprentice"
    required_focus_spell_id = "hand_of_the_apprentice"
    range_feet = 500
    spell_tags = WizardFocusSpellEvent.spell_tags + ["attack", "evocation"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        target = _pick_target(ctx, actor, range_feet=500, kinds=("enemy",))
        if target is None:
            return EventResult.cancelled(message="Hand of the Apprentice: target not selected.")

        target_ac = int(getattr(target, "ac", effective_ac(target)) or 10)
        roll = _roll_int(
            f"Hand of the Apprentice: spell attack vs AC {target_ac}",
            layout="test",
            answer_placeholder="d20",
        )
        outcome = resolve_outcome(roll, target_ac, natural_shift=natural_shift_from_roll(roll))
        if not is_hit(outcome):
            return EventResult(success=True, consumed_action=True, message="Hand of the Apprentice: miss.")

        damage = _roll_int(
            "Hand of the Apprentice: enter weapon damage on hit",
            layout="damage",
            answer_placeholder="Damage",
            prompt_long=(
                "Rules hint: use held trained melee weapon damage; replace STR with spellcasting modifier. "
                "Critical success doubles damage and adds critical specialization."
            ),
        )
        if damage <= 0:
            return EventResult.cancelled(message="Hand of the Apprentice: damage must be > 0.")
        if is_critical_success(outcome):
            damage *= 2

        defeated = _apply_damage(target, damage, DamageType.NORMAL.value, source=self.name)
        target_name = getattr(target, "name", "target")
        msg = f"Hand of the Apprentice: hit {target_name} for {damage} normal damage."
        if is_critical_success(outcome):
            msg += " Critical specialization effect: resolve manually."
        msg += " Weapon returns to your hand."
        if defeated:
            msg += " Target defeated."
        return EventResult(
            success=True,
            consumed_action=True,
            message=msg,
            data={"target": target, "damage": damage, "outcome": outcome},
        )


@register_event
class PhysicalBoostEvent(WizardFocusSpellEvent):
    name = "physical_boost"
    required_focus_spell_id = "physical_boost"
    range_feet = 5
    spell_tags = WizardFocusSpellEvent.spell_tags + ["touch", "transmutation"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        target = _pick_target(ctx, actor, range_feet=5, kinds=("hero", "enemy"), allow_self=True)
        if target is None:
            return EventResult.cancelled(message="Physical Boost: target not selected.")

        _add_status(
            target,
            Status(
                id="physical_boost_active",
                label="Physical Boost",
                duration=1,
                source=self.name,
                data={
                    "boost_value": 2,
                    "boost_tags": ["acrobatics", "athletics", "fortitude", "reflex"],
                    "effect_tags": ["transmutation", "status_bonus"],
                },
            ),
        )
        _add_bonus(
            target,
            tags=("acrobatics", "athletics", "fortitude", "reflex"),
            value=2,
            source=self.name,
            duration_turns=1,
            label="physical boost",
        )
        target_name = getattr(target, "name", "target")
        return EventResult(
            success=True,
            consumed_action=True,
            message=f"Physical Boost: {target_name} gets +2 status to next Acrobatics/Athletics/Fortitude/Reflex check.",
            data={"target": target},
        )


@register_event
class ProtectiveWardEvent(WizardFocusSpellEvent):
    name = "protective_ward"
    required_focus_spell_id = "protective_ward"
    range_feet = None
    spell_tags = WizardFocusSpellEvent.spell_tags + ["abjuration", "aura"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        actor_pos = getattr(actor, "position", None)
        if actor_pos is None:
            return EventResult.cancelled(message="Protective Ward: missing actor position.")

        _remove_statuses(actor, "protective_ward_active")
        _add_status(
            actor,
            Status(
                id="protective_ward_active",
                label="Protective Ward",
                duration=10,
                source=self.name,
                data={
                    "radius_feet": 5,
                    "max_radius_feet": 30,
                    "radius_step_on_sustain": 5,
                    "ac_bonus": 1,
                    "sustained": True,
                    "effect_tags": ["aura", "abjuration"],
                },
            ),
        )

        _add_bonus(
            actor,
            tags=("ac",),
            value=1,
            source=self.name,
            duration_turns=1,
            label="protective ward",
        )

        allies_buffed = 0
        for ally in getattr(ctx.game, "heroes", []) or []:
            if ally is actor:
                continue
            pos = getattr(ally, "position", None)
            if pos is None:
                continue
            if grid_distance_feet(actor_pos, pos) <= 5:
                _add_bonus(
                    ally,
                    tags=("ac",),
                    value=1,
                    source=self.name,
                    duration_turns=1,
                    label="protective ward",
                )
                allies_buffed += 1

        return EventResult(
            success=True,
            consumed_action=True,
            message=(
                f"Protective Ward: +1 status AC aura (5 ft), allies currently affected: {allies_buffed}. "
                "Sustain to grow aura by +5 ft (max 30 ft) is tracked by status data."
            ),
            data={"allies_buffed": allies_buffed},
        )


@register_event
class WarpedTerrainEvent(WizardFocusSpellEvent):
    name = "warped_terrain"
    required_focus_spell_id = "warped_terrain"
    range_feet = 60
    spell_tags = WizardFocusSpellEvent.spell_tags + ["illusion", "visual"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        source_pos = getattr(actor, "position", None)
        if source_pos is None:
            return EventResult.cancelled(message="Warped Terrain: missing actor position.")

        actions_raw = _prompt_choice(
            ctx,
            "Warped Terrain: choose cast actions",
            ["1", "2", "3"],
            source=self.name,
        ) or "1"
        try:
            actions = int(str(actions_raw).strip().split()[0])
        except Exception:
            actions = 1
        actions = min(3, max(1, actions))

        remaining = _actions_remaining(ctx, actor)
        if remaining is not None and actions > remaining:
            return EventResult.cancelled(
                message=f"Warped Terrain: not enough actions ({actions} needed, {remaining} remaining)."
            )

        center = pick_position_in_range(ctx, source_pos, max_range_feet=60, color=[180, 60, 220])
        if center is None:
            center = source_pos

        radius = 5 + min(10, 5 * max(0, actions - 1))
        rank = _focus_rank(actor)
        airborne = False
        if rank >= 4:
            airborne_choice = _normalize(
                _prompt_choice(
                    ctx,
                    "Warped Terrain (Heightened 4th+): apply to flying creatures?",
                    ["no", "yes"],
                    source=self.name,
                )
                or "no"
            )
            airborne = airborne_choice in {"yes", "y", "tak", "t", "1"}

        _add_status(
            actor,
            Status(
                id="warped_terrain_active",
                label="Warped Terrain",
                duration=10,
                source=self.name,
                data={
                    "center_position": center,
                    "radius_feet": radius,
                    "airborne": airborne,
                    "difficult_terrain": True,
                    "effect_tags": ["illusion", "difficult_terrain"],
                },
            ),
        )

        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=actions if ctx.in_combat else None,
            message=(
                f"Warped Terrain: created {radius}-ft difficult terrain burst at {center} for 1 minute."
                + (" Includes flying creatures." if airborne else "")
            ),
            data={"center": center, "radius_feet": radius, "airborne": airborne},
        )


__all__ = [
    "WizardFocusSpellEvent",
    "AugmentSummoningEvent",
    "CallOfTheGraveEvent",
    "CharmingWordsEvent",
    "DivinersSightEvent",
    "ForceBoltEvent",
    "HandOfTheApprenticeEvent",
    "PhysicalBoostEvent",
    "ProtectiveWardEvent",
    "WarpedTerrainEvent",
]
