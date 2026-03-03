from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from bonuses import BonusEffect, BonusType
from combat.hp_engine import apply_damage as hp_apply_damage
from combat.hp_engine import heal as hp_heal
from damage_types import DamageType
from statuses import Status, make_persistent_damage
from statuses.blinded import BLINDED_STATUS
from statuses.charmed import CharmedStatus
from statuses.sleep import SleepStatus
from statuses.speed_bonus import SpeedBonusStatus
from statuses.speed_penalty import SpeedPenaltyStatus
from statuses.stunned import StunnedStatus
from GameObjects.interactions_mixin import prompt_for_roll

from ....base import EventContext, EventResult
from ....registry import list_events, register_event
from ...magic_event import MagicEvent
from ...magic_utils import pick_position_in_range, pick_target_in_range
from ...spell_types import SpellTradition
from statuses.classes.cleric.cleric import CLERIC_DOMAIN_INITIAL_SPELLS


TOUCH_SPELL_IDS = {
    "charming_touch",
    "touch_of_obedience",
    "touch_of_undeath",
}


@dataclass(frozen=True)
class DomainSpellSpec:
    mode: str
    actions_cost: int = 1
    range_feet: int | None = 30
    damage_type: str = DamageType.FORCE.value
    bonus_tags: tuple[str, ...] = ()
    bonus_value: int = 1
    duration_turns: int = 1
    bonus_type: BonusType = BonusType.STATUS
    is_penalty: bool = False
    status_id: str | None = None
    status_label: str | None = None
    prompt_long: str | None = None
    move_range_feet: int | None = None
    add_speed_bonus_feet: int = 0
    add_speed_penalty_feet: int = 0
    persistent_damage_type: str | None = None
    persistent_damage_amount: int = 0
    save_type: str | None = None
    basic_save: bool = False
    status_apply_on: tuple[str, ...] = ("failure", "critical_failure")
    damage_apply_on: tuple[str, ...] = ("failure", "critical_failure")


DOMAIN_SPELL_SPECS: dict[str, DomainSpellSpec] = {
    "pushing_gust": DomainSpellSpec(
        mode="enemy_damage",
        actions_cost=2,
        range_feet=30,
        damage_type=DamageType.BLUDGEONING.value,
        add_speed_penalty_feet=10,
        save_type="fortitude",
        basic_save=True,
        status_apply_on=("failure", "critical_failure"),
        prompt_long="Simplified: also applies speed -10 ft for 1 round.",
    ),
    "blind_ambition": DomainSpellSpec(
        mode="ally_bonus",
        range_feet=30,
        bonus_tags=("attack_melee", "attack_ranged", "magic"),
        bonus_value=1,
        prompt_long="Simplified ambition buff.",
    ),
    "face_in_the_crowd": DomainSpellSpec(
        mode="self_bonus",
        range_feet=None,
        bonus_tags=("stealth",),
        bonus_value=2,
        bonus_type=BonusType.CIRCUMSTANCE,
        duration_turns=3,
    ),
    "veil_of_confidence": DomainSpellSpec(mode="ally_bonus", range_feet=30, bonus_tags=("will",), bonus_value=1, duration_turns=3),
    "splash_of_art": DomainSpellSpec(mode="ally_bonus", range_feet=30, bonus_tags=("crafting", "performance"), bonus_value=1, duration_turns=3),
    "cloak_of_shadow": DomainSpellSpec(mode="self_status", range_feet=None, status_id="concealed", status_label="Cloak of Shadow", duration_turns=2),
    "deaths_call": DomainSpellSpec(mode="enemy_damage", actions_cost=2, range_feet=30, damage_type=DamageType.NEGATIVE.value),
    "cry_of_destruction": DomainSpellSpec(mode="enemy_damage", actions_cost=2, range_feet=30, damage_type=DamageType.SONIC.value),
    "sweet_dream": DomainSpellSpec(
        mode="enemy_status",
        actions_cost=2,
        range_feet=30,
        status_id="sleep",
        status_label="Sweet Dream",
        duration_turns=1,
        save_type="will",
    ),
    "hurtling_stone": DomainSpellSpec(mode="enemy_damage", actions_cost=2, range_feet=30, damage_type=DamageType.BLUDGEONING.value),
    "soothing_words": DomainSpellSpec(mode="ally_heal", range_feet=30, prompt_long="Simplified: only applies healing."),
    "read_fate": DomainSpellSpec(mode="ally_bonus", range_feet=30, bonus_tags=("ac",), bonus_value=1, duration_turns=1),
    "fire_ray": DomainSpellSpec(
        mode="enemy_damage",
        actions_cost=2,
        range_feet=60,
        damage_type=DamageType.FIRE.value,
        persistent_damage_type=DamageType.FIRE.value,
        persistent_damage_amount=1,
    ),
    "unimpeded_stride": DomainSpellSpec(
        mode="self_speed_bonus",
        range_feet=None,
        add_speed_bonus_feet=10,
        prompt_long="Simplified: difficult terrain ignore is a manual reminder.",
    ),
    "healers_blessing": DomainSpellSpec(
        mode="ally_status",
        range_feet=30,
        status_id="healers_blessing",
        status_label="Healer's Blessing",
        duration_turns=1,
        prompt_long="Reminder: next Heal on this target gains +2 HP per spell level.",
    ),
    "overstuff": DomainSpellSpec(
        mode="enemy_status",
        actions_cost=2,
        range_feet=30,
        status_id="stunned",
        status_label="Overstuff",
        duration_turns=1,
        save_type="fortitude",
    ),
    "scholarly_recollection": DomainSpellSpec(mode="self_bonus", range_feet=None, bonus_tags=("arcana", "nature", "occultism", "religion"), bonus_value=1),
    "bit_of_luck": DomainSpellSpec(
        mode="ally_status",
        range_feet=30,
        status_id="bit_of_luck",
        status_label="Bit of Luck",
        duration_turns=1,
        prompt_long="Reminder: next d20 roll uses fortune (roll twice, keep better).",
    ),
    "magics_vessel": DomainSpellSpec(
        mode="ally_status",
        range_feet=30,
        status_id="magics_vessel",
        status_label="Magic's Vessel",
        duration_turns=2,
        prompt_long="Reminder: apply domain-specific magic vessel benefits manually.",
    ),
    "athletic_rush": DomainSpellSpec(mode="self_speed_bonus", range_feet=None, add_speed_bonus_feet=10, bonus_tags=("athletics",), bonus_value=2),
    "moonbeam": DomainSpellSpec(mode="enemy_damage", actions_cost=2, range_feet=60, damage_type=DamageType.FORCE.value),
    "vibrant_thorns": DomainSpellSpec(
        mode="self_status",
        range_feet=None,
        status_id="vibrant_thorns",
        status_label="Vibrant Thorns",
        duration_turns=3,
        prompt_long="Reminder: thorn retaliation damage is resolved manually.",
    ),
    "waking_nightmare": DomainSpellSpec(
        mode="enemy_damage",
        actions_cost=2,
        range_feet=30,
        damage_type=DamageType.MENTAL.value,
        save_type="will",
        basic_save=True,
    ),
    "savor_the_sting": DomainSpellSpec(
        mode="enemy_damage",
        actions_cost=2,
        range_feet=30,
        damage_type=DamageType.MENTAL.value,
        persistent_damage_type=DamageType.MENTAL.value,
        persistent_damage_amount=1,
        save_type="will",
        basic_save=True,
        status_apply_on=("failure", "critical_failure"),
    ),
    "charming_touch": DomainSpellSpec(
        mode="enemy_status",
        range_feet=5,
        status_id="charmed",
        status_label="Charming Touch",
        duration_turns=2,
        save_type="will",
    ),
    "perfected_mind": DomainSpellSpec(mode="self_bonus", range_feet=None, bonus_tags=("will",), bonus_value=2, duration_turns=3),
    "protectors_sacrifice": DomainSpellSpec(
        mode="ally_status",
        range_feet=30,
        status_id="protectors_sacrifice",
        status_label="Protector's Sacrifice",
        duration_turns=1,
        prompt_long="Reminder: damage transfer reaction must be resolved manually.",
    ),
    "forced_quiet": DomainSpellSpec(
        mode="enemy_status",
        actions_cost=2,
        range_feet=30,
        status_id="forced_quiet",
        status_label="Forced Quiet",
        duration_turns=2,
        save_type="will",
    ),
    "dazzling_flash": DomainSpellSpec(
        mode="enemy_status",
        actions_cost=2,
        range_feet=30,
        status_id="blinded",
        status_label="Dazzling Flash",
        duration_turns=1,
        save_type="fortitude",
    ),
    "agile_feet": DomainSpellSpec(
        mode="self_speed_bonus",
        range_feet=None,
        add_speed_bonus_feet=10,
        duration_turns=1,
        prompt_long="Reminder: difficult terrain ignore is manual.",
    ),
    "sudden_shift": DomainSpellSpec(mode="self_move", actions_cost=2, range_feet=None, move_range_feet=15),
    "word_of_truth": DomainSpellSpec(
        mode="enemy_status",
        actions_cost=2,
        range_feet=30,
        status_id="word_of_truth",
        status_label="Word of Truth",
        duration_turns=2,
        save_type="will",
        prompt_long="Reminder: lying restrictions are roleplay/UI tracked.",
    ),
    "touch_of_obedience": DomainSpellSpec(
        mode="enemy_status",
        range_feet=5,
        status_id="stunned",
        status_label="Touch of Obedience",
        duration_turns=1,
        save_type="will",
    ),
    "touch_of_undeath": DomainSpellSpec(mode="touch_of_undeath", actions_cost=2, range_feet=5),
    "tidal_surge": DomainSpellSpec(
        mode="enemy_damage",
        actions_cost=2,
        range_feet=30,
        damage_type=DamageType.BLUDGEONING.value,
        add_speed_penalty_feet=5,
        save_type="reflex",
        basic_save=True,
        status_apply_on=("failure", "critical_failure"),
    ),
    "appearance_of_wealth": DomainSpellSpec(mode="self_bonus", range_feet=None, bonus_tags=("diplomacy", "deception"), bonus_value=1, duration_turns=10),
    "weapon_surge": DomainSpellSpec(
        mode="ally_bonus",
        range_feet=30,
        bonus_tags=("attack_melee", "attack_ranged"),
        bonus_value=1,
        prompt_long="Reminder: extra weapon damage from surge may need manual add depending on attack implementation.",
    ),
    "custom_domain_spell_a": DomainSpellSpec(mode="utility", range_feet=None, prompt_long="Custom domain spell A: resolve manually."),
    "custom_domain_spell_b": DomainSpellSpec(mode="utility", range_feet=None, prompt_long="Custom domain spell B: resolve manually."),
    "custom_domain_spell_c": DomainSpellSpec(mode="utility", range_feet=None, prompt_long="Custom domain spell C: resolve manually."),
}


def _is_cleric(actor) -> bool:
    if actor is None:
        return False
    has_status = getattr(actor, "has_status", None)
    if callable(has_status):
        try:
            if bool(has_status("cleric")):
                return True
        except Exception:
            pass
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) == "cleric":
            return True
    class_name = str(getattr(actor, "class_name", "") or "").strip().lower()
    return class_name == "cleric"


def _focus_points(actor) -> int:
    raw = getattr(actor, "focus_point", None)
    try:
        return max(0, int(raw or 0))
    except Exception:
        return 0


def _set_focus_points(actor, value: int) -> None:
    points = max(0, int(value))
    try:
        setattr(actor, "focus_point", points)
    except Exception:
        return


def _knows_domain_spell(actor, *, domain_id: str, spell_id: str) -> bool:
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) != "domain_initiate":
            continue
        data = getattr(status, "data", None) or {}
        known_domain = str(data.get("selected_domain", "") or "").strip().lower()
        known_spell = str(data.get("domain_spell", "") or "").strip().lower()
        if known_domain == domain_id and known_spell == spell_id:
            return True
    return False


def _is_undead(target) -> bool:
    if target is None:
        return False
    has_tag = getattr(target, "has_tag", None)
    if callable(has_tag):
        try:
            if bool(has_tag("undead")):
                return True
        except Exception:
            pass
    tags = {str(t).strip().lower() for t in (getattr(target, "tags", None) or [])}
    enemy_type = getattr(target, "enemy_type", None)
    if enemy_type is not None:
        tags.add(str(getattr(enemy_type, "value", enemy_type)).strip().lower())
    return "undead" in tags


def _iter_enemy_candidates(game):
    for enemy in getattr(game, "enemies", []) or []:
        yield enemy, getattr(enemy, "position", None), "enemy"


def _iter_hero_candidates(game):
    for hero in getattr(game, "heroes", []) or []:
        yield hero, getattr(hero, "position", None), "hero"


def _pick_target(ctx: EventContext, actor, *, range_feet: int | None, allowed_kinds: tuple[str, ...]):
    source_pos = getattr(actor, "position", None)
    if source_pos is None:
        return None
    candidates = []
    if "enemy" in allowed_kinds:
        candidates.extend(list(_iter_enemy_candidates(ctx.game)))
    if "hero" in allowed_kinds:
        candidates.extend(list(_iter_hero_candidates(ctx.game)))
    target, _target_pos = pick_target_in_range(
        ctx,
        source_pos,
        candidates,
        max_range_feet=range_feet,
        allowed_kinds=allowed_kinds,
        tags=["magic", "focus", "domain"],
    )
    return target


def _source_id(actor) -> str:
    return str(getattr(actor, "object_id", None) or getattr(actor, "name", None) or "cleric")


def _show_info(ctx: EventContext, title: str, detail: str | None, *, source: str) -> None:
    if not detail:
        return
    ui = getattr(ctx.game, "ui", None)
    info = getattr(ui, "prompt_info", None)
    if callable(info):
        try:
            info(title, prompt_long=detail, source=source)
            return
        except Exception:
            pass
    log = getattr(ctx.game, "ui_log", None)
    if callable(log):
        try:
            log(f"{title}: {detail}")
        except Exception:
            pass


def _prompt_choice(ctx: EventContext, prompt: str, choices: list[str], *, source: str) -> str | None:
    ui = getattr(ctx.game, "ui", None)
    answer = None
    chooser = getattr(ui, "prompt_choice", None)
    if callable(chooser):
        try:
            answer = chooser(prompt, choices=choices, source=source)
        except Exception:
            answer = None
    if answer is None:
        conn = getattr(ctx.game, "conn", None)
        reader = getattr(conn, "read_card", None)
        if callable(reader):
            try:
                answer = reader(prompt, choices)
            except Exception:
                answer = None
    if answer is None:
        return None
    raw = str(answer).strip().lower().replace(" ", "_")
    if not raw:
        return None
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(choices):
            return choices[idx]
    for option in choices:
        if raw == str(option).strip().lower().replace(" ", "_"):
            return option
    return None


def _apply_damage(target, amount: int, damage_type: str) -> bool:
    apply = getattr(target, "apply_damage", None)
    if callable(apply):
        try:
            _, defeated = apply(max(0, int(amount)), damage_type)
            return bool(defeated)
        except Exception:
            return False
    try:
        info = hp_apply_damage(target, amount, damage_type, source=f"domain_spell:{damage_type}")
        return bool(info.get("defeated", False))
    except Exception:
        return False


def _apply_heal(target, amount: int) -> None:
    healed = max(0, int(amount))
    healer = getattr(target, "heal", None)
    if callable(healer):
        try:
            healer(healed)
            return
        except Exception:
            pass
    try:
        hp_heal(target, healed, source="domain_spell:heal")
    except Exception:
        pass


def _add_status(target, status: Status) -> None:
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


def _add_bonus(
    target,
    *,
    tags: tuple[str, ...],
    value: int,
    source: str,
    duration_turns: int,
    bonus_type: BonusType,
    is_penalty: bool,
) -> int:
    applied = 0
    adder = getattr(target, "add_bonus", None)
    bonuses = getattr(target, "bonuses", None)
    if not isinstance(bonuses, list):
        try:
            setattr(target, "bonuses", [])
            bonuses = getattr(target, "bonuses", None)
        except Exception:
            bonuses = None

    for tag in tags:
        if not tag:
            continue
        effect = BonusEffect(
            type=bonus_type,
            value=abs(int(value)),
            tag=str(tag),
            source=source,
            label=source,
            is_penalty=is_penalty,
            duration_turns=duration_turns,
        )
        try:
            if callable(adder):
                adder(effect)
                applied += 1
                continue
            if isinstance(bonuses, list):
                bonuses.append(effect)
                applied += 1
        except Exception:
            continue
    return applied


def _roll_amount(prompt: str, *, prompt_long: str | None = None) -> int:
    value = prompt_for_roll(
        prompt,
        layout="damage",
        answer_placeholder="Value",
        prompt_long=prompt_long,
    )
    try:
        return max(0, int(value or 0))
    except Exception:
        return 0


def _basic_save_damage(base_damage: int, outcome: str) -> int:
    base = max(0, int(base_damage or 0))
    if outcome == "critical_success":
        return 0
    if outcome == "success":
        return max(0, base // 2)
    if outcome == "critical_failure":
        return max(0, base * 2)
    return base


def _normalize_outcomes(values: Iterable[str] | None, *, default: tuple[str, ...]) -> tuple[str, ...]:
    collected: list[str] = []
    for raw in values or []:
        item = str(raw or "").strip().lower()
        if item and item not in collected:
            collected.append(item)
    return tuple(collected) if collected else tuple(default)


def _pick_save_outcome(
    ctx: EventContext,
    *,
    spell_label: str,
    save_type: str,
    source: str,
    default: str = "failure",
) -> str:
    outcome = _prompt_choice(
        ctx,
        f"{spell_label}: wybierz wynik save ({save_type})",
        ["critical_success", "success", "failure", "critical_failure"],
        source=source,
    )
    normalized = str(outcome or "").strip().lower()
    if normalized in {"critical_success", "success", "failure", "critical_failure"}:
        return normalized
    fallback = str(default or "failure").strip().lower()
    if fallback in {"critical_success", "success", "failure", "critical_failure"}:
        return fallback
    return "failure"


def _move_actor(ctx: EventContext, actor, *, max_range_feet: int) -> bool:
    pos = getattr(actor, "position", None)
    if pos is None:
        return False
    destination = pick_position_in_range(ctx, pos, max_range_feet=max_range_feet)
    if destination is None or destination == pos:
        return False
    board = getattr(ctx.game, "board", None)
    mover = getattr(board, "move", None)
    if callable(mover):
        try:
            mover(pos, destination)
            return True
        except Exception:
            return False
    try:
        setattr(actor, "position", destination)
        return True
    except Exception:
        return False


def _status_from_spec(spec: DomainSpellSpec, spell_id: str, source: str, actor, fallback_label: str) -> Status:
    if spec.status_id == "sleep":
        return SleepStatus(
            source_id=_source_id(actor),
            source_turns_left=spec.duration_turns,
            duration=spec.duration_turns,
            source=source,
        )
    if spec.status_id == "stunned":
        return StunnedStatus(
            value=1,
            duration=spec.duration_turns,
            source=source,
            source_id=_source_id(actor),
            source_turns_left=spec.duration_turns,
        )
    if spec.status_id == "charmed":
        return CharmedStatus(duration=spec.duration_turns, source=source)
    if spec.status_id == "blinded":
        return Status(
            id=BLINDED_STATUS.id,
            label=BLINDED_STATUS.label,
            duration=spec.duration_turns,
            source=source,
            data=dict(BLINDED_STATUS.data or {}),
            check_effects=BLINDED_STATUS.check_effects,
        )
    status_id = str(spec.status_id or spell_id)
    return Status(
        id=status_id,
        label=spec.status_label or fallback_label,
        duration=spec.duration_turns,
        source=source,
        data={"effect_tags": ["domain_spell", status_id]},
    )


class ClericDomainSpellEvent(MagicEvent):
    actions_cost = 1
    default_tags = ["magic", "spell", "focus", "cleric", "domain"]
    spell_tags = ["focus", "divine", "cleric", "domain"]
    magic_traditions = (SpellTradition.DIVINE,)
    magic_types = ["focus"]
    domain_id = ""
    spell_label = ""

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message=f"{self.spell_label}: missing actor.")
        if not _is_cleric(actor):
            return EventResult.cancelled(message=f"{self.spell_label}: only Cleric can cast this spell.")
        if not _knows_domain_spell(actor, domain_id=self.domain_id, spell_id=self.name):
            return EventResult.cancelled(message=f"{self.spell_label}: this domain spell is not known.")

        points = _focus_points(actor)
        if points <= 0:
            return EventResult.cancelled(message=f"{self.spell_label}: no Focus Point.")

        result = self._execute_effect(ctx)
        if not result.success:
            return result

        _set_focus_points(actor, points - 1)
        base_msg = str(result.message or f"{self.spell_label}: effect applied.")
        result.message = f"{base_msg} Focus Point: {_focus_points(actor)}."
        return result

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        spell_id = str(getattr(self, "name", "") or "").strip().lower()
        spec = DOMAIN_SPELL_SPECS.get(spell_id)
        actions_spent = max(1, int(getattr(self, "actions_cost", 1) or 1))
        if spec is None:
            msg = f"{self.spell_label}: no implementation spec, resolve manually."
            _show_info(ctx, self.spell_label, msg, source=spell_id)
            return EventResult(
                success=True,
                consumed_action=ctx.in_combat,
                actions_spent=actions_spent if ctx.in_combat else None,
                message=msg,
            )

        mode = spec.mode
        source = f"domain:{spell_id}"
        status_on = _normalize_outcomes(spec.status_apply_on, default=("failure", "critical_failure"))
        damage_on = _normalize_outcomes(spec.damage_apply_on, default=("failure", "critical_failure"))

        if mode == "enemy_damage":
            target = _pick_target(ctx, actor, range_feet=spec.range_feet, allowed_kinds=("enemy",))
            if target is None:
                return EventResult.cancelled(message=f"{self.spell_label}: target not selected.")
            save_outcome = None
            if spec.save_type:
                save_outcome = _pick_save_outcome(
                    ctx,
                    spell_label=self.spell_label,
                    save_type=spec.save_type,
                    source=spell_id,
                    default="failure",
                )
            if spec.basic_save:
                base_amount = _roll_amount(
                    f"{self.spell_label}: enter base damage (before save)",
                    prompt_long=spec.prompt_long,
                )
                if base_amount <= 0:
                    return EventResult.cancelled(message=f"{self.spell_label}: base damage must be > 0.")
                amount = _basic_save_damage(base_amount, save_outcome or "failure")
            elif save_outcome and save_outcome not in damage_on:
                amount = 0
            else:
                amount = _roll_amount(f"{self.spell_label}: enter final damage", prompt_long=spec.prompt_long)
                if amount <= 0:
                    return EventResult.cancelled(message=f"{self.spell_label}: damage must be > 0.")

            defeated = False
            if amount > 0:
                defeated = _apply_damage(target, amount, spec.damage_type)

            can_apply_status_side_effect = (save_outcome is None) or (save_outcome in status_on)
            if spec.add_speed_penalty_feet > 0 and can_apply_status_side_effect:
                _add_status(
                    target,
                    SpeedPenaltyStatus(
                        penalty_feet=spec.add_speed_penalty_feet,
                        duration=spec.duration_turns,
                        source=source,
                        source_id=_source_id(actor),
                    ),
                )
            if spec.persistent_damage_amount > 0 and spec.persistent_damage_type and can_apply_status_side_effect:
                _add_status(
                    target,
                    make_persistent_damage(
                        spec.persistent_damage_amount,
                        spec.persistent_damage_type,
                        source=source,
                    ),
                )
            target_name = getattr(target, "name", "target")
            if amount > 0:
                msg = f"{self.spell_label}: {target_name} takes {amount} {spec.damage_type} damage."
            else:
                msg = f"{self.spell_label}: no damage dealt."
            if save_outcome:
                msg += f" Save: {save_outcome} ({spec.save_type})."
            if defeated:
                msg += " Target defeated."
            _show_info(ctx, self.spell_label, spec.prompt_long, source=spell_id)
            return EventResult(
                success=True,
                consumed_action=ctx.in_combat,
                actions_spent=actions_spent if ctx.in_combat else None,
                message=msg,
            )

        if mode == "ally_heal":
            target = _pick_target(ctx, actor, range_feet=spec.range_feet, allowed_kinds=("hero",))
            if target is None:
                return EventResult.cancelled(message=f"{self.spell_label}: target not selected.")
            amount = _roll_amount(f"{self.spell_label}: enter healing amount", prompt_long=spec.prompt_long)
            if amount <= 0:
                return EventResult.cancelled(message=f"{self.spell_label}: healing must be > 0.")
            _apply_heal(target, amount)
            target_name = getattr(target, "name", "target")
            _show_info(ctx, self.spell_label, spec.prompt_long, source=spell_id)
            return EventResult(
                success=True,
                consumed_action=ctx.in_combat,
                actions_spent=actions_spent if ctx.in_combat else None,
                message=f"{self.spell_label}: {target_name} heals {amount} HP.",
            )

        if mode in {"ally_bonus", "self_bonus"}:
            target = actor if mode == "self_bonus" else _pick_target(ctx, actor, range_feet=spec.range_feet, allowed_kinds=("hero",))
            if target is None:
                return EventResult.cancelled(message=f"{self.spell_label}: target not selected.")
            applied = _add_bonus(
                target,
                tags=spec.bonus_tags,
                value=spec.bonus_value,
                source=source,
                duration_turns=spec.duration_turns,
                bonus_type=spec.bonus_type,
                is_penalty=spec.is_penalty,
            )
            if mode == "self_bonus" and spec.add_speed_bonus_feet > 0:
                _add_status(
                    target,
                    SpeedBonusStatus(
                        bonus_feet=spec.add_speed_bonus_feet,
                        duration=spec.duration_turns,
                        source=source,
                        label=f"{self.spell_label} speed",
                    ),
                )
            _show_info(ctx, self.spell_label, spec.prompt_long, source=spell_id)
            if applied <= 0 and not spec.add_speed_bonus_feet:
                msg = f"{self.spell_label}: no bonus backend on target, reminder only."
            else:
                msg = f"{self.spell_label}: bonus applied ({applied} tag(s))."
            return EventResult(
                success=True,
                consumed_action=ctx.in_combat,
                actions_spent=actions_spent if ctx.in_combat else None,
                message=msg,
            )

        if mode == "self_speed_bonus":
            _add_status(
                actor,
                SpeedBonusStatus(
                    bonus_feet=max(5, int(spec.add_speed_bonus_feet or 10)),
                    duration=spec.duration_turns,
                    source=source,
                    label=f"{self.spell_label} speed",
                ),
            )
            if spec.bonus_tags:
                _add_bonus(
                    actor,
                    tags=spec.bonus_tags,
                    value=spec.bonus_value,
                    source=source,
                    duration_turns=spec.duration_turns,
                    bonus_type=spec.bonus_type,
                    is_penalty=spec.is_penalty,
                )
            _show_info(ctx, self.spell_label, spec.prompt_long, source=spell_id)
            return EventResult(
                success=True,
                consumed_action=ctx.in_combat,
                actions_spent=actions_spent if ctx.in_combat else None,
                message=f"{self.spell_label}: mobility buff applied.",
            )

        if mode in {"enemy_status", "ally_status", "self_status"}:
            if mode == "enemy_status":
                target = _pick_target(ctx, actor, range_feet=spec.range_feet, allowed_kinds=("enemy",))
            elif mode == "ally_status":
                target = _pick_target(ctx, actor, range_feet=spec.range_feet, allowed_kinds=("hero",))
            else:
                target = actor
            if target is None:
                return EventResult.cancelled(message=f"{self.spell_label}: target not selected.")
            if mode == "enemy_status" and spec.save_type:
                save_outcome = _pick_save_outcome(
                    ctx,
                    spell_label=self.spell_label,
                    save_type=spec.save_type,
                    source=spell_id,
                    default="failure",
                )
                if save_outcome not in status_on:
                    return EventResult(
                        success=True,
                        consumed_action=ctx.in_combat,
                        actions_spent=actions_spent if ctx.in_combat else None,
                        message=f"{self.spell_label}: no effect ({save_outcome} on {spec.save_type} save).",
                    )

            status = _status_from_spec(spec, spell_id, source, actor, self.spell_label)
            _add_status(target, status)
            _show_info(ctx, self.spell_label, spec.prompt_long, source=spell_id)
            return EventResult(
                success=True,
                consumed_action=ctx.in_combat,
                actions_spent=actions_spent if ctx.in_combat else None,
                message=f"{self.spell_label}: status '{status.label or status.id}' applied.",
            )

        if mode == "touch_of_undeath":
            target = _pick_target(ctx, actor, range_feet=spec.range_feet, allowed_kinds=("hero", "enemy"))
            if target is None:
                return EventResult.cancelled(message=f"{self.spell_label}: target not selected.")
            amount = _roll_amount(
                f"{self.spell_label}: enter final value",
                prompt_long="Simplified: living takes negative damage, undead is healed.",
            )
            if amount <= 0:
                return EventResult.cancelled(message=f"{self.spell_label}: value must be > 0.")
            if _is_undead(target):
                _apply_heal(target, amount)
                msg = f"{self.spell_label}: undead target heals {amount} HP."
            else:
                _apply_damage(target, amount, DamageType.NEGATIVE.value)
                msg = f"{self.spell_label}: target takes {amount} negative damage."
            return EventResult(
                success=True,
                consumed_action=ctx.in_combat,
                actions_spent=actions_spent if ctx.in_combat else None,
                message=msg,
            )

        if mode == "self_move":
            move_range = int(spec.move_range_feet or 10)
            moved = _move_actor(ctx, actor, max_range_feet=move_range)
            if not moved:
                return EventResult.cancelled(message=f"{self.spell_label}: movement failed.")
            return EventResult(
                success=True,
                consumed_action=ctx.in_combat,
                actions_spent=actions_spent if ctx.in_combat else None,
                message=f"{self.spell_label}: movement completed.",
            )

        msg = spec.prompt_long or f"{self.spell_label}: resolve manually."
        _show_info(ctx, self.spell_label, msg, source=spell_id)
        return EventResult(
            success=True,
            consumed_action=ctx.in_combat,
            actions_spent=actions_spent if ctx.in_combat else None,
            message=msg,
        )


def _labelize_spell(spell_id: str) -> str:
    return str(spell_id or "").replace("_", " ").strip().title()


def _register_domain_spell_events() -> None:
    existing = list_events()
    for domain_id, spell_id in sorted(CLERIC_DOMAIN_INITIAL_SPELLS.items()):
        domain = str(domain_id or "").strip().lower()
        spell = str(spell_id or "").strip().lower()
        if not domain or not spell:
            continue
        if spell in existing and issubclass(existing[spell], ClericDomainSpellEvent):
            continue

        spec = DOMAIN_SPELL_SPECS.get(spell)
        spell_tags = list(ClericDomainSpellEvent.spell_tags)
        if spell in TOUCH_SPELL_IDS and "touch" not in spell_tags:
            spell_tags.append("touch")

        attrs = {
            "name": spell,
            "domain_id": domain,
            "spell_label": _labelize_spell(spell),
            "prompt": f"{_labelize_spell(spell)} (domain {domain}).",
            "spell_tags": spell_tags,
            "range_feet": spec.range_feet if spec is not None else None,
            "actions_cost": int(getattr(spec, "actions_cost", 1) or 1) if spec is not None else 1,
        }
        event_cls = type(f"{_labelize_spell(spell).replace(' ', '')}Event", (ClericDomainSpellEvent,), attrs)
        register_event(event_cls)


_register_domain_spell_events()

__all__ = [
    "DOMAIN_SPELL_SPECS",
    "ClericDomainSpellEvent",
]
