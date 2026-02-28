from __future__ import annotations

import logging
import random

from bonuses import BonusEffect, BonusType
from damage_types import DamageType
from skills import Skill
from statuses import (
    BlindedStatus,
    CharmedStatus,
    EnfeebledStatus,
    FloatingDiskStatus,
    ImmobilizedStatus,
    IllusoryDisguiseStatus,
    MageArmorStatus,
    MindlinkStatus,
    ProneStatus,
    SleepStatus,
    SpeedPenaltyStatus,
    SpiritLinkCasterStatus,
    SpiritLinkTargetStatus,
    StunnedStatus,
    SummonedFeyStatus,
    TrueStrikeStatus,
    UnseenServantStatus,
    VentriloquismStatus,
    apply_prone_effects,
    clear_prone_effects,
    make_persistent_damage,
)
from GameObjects.NPC.base_npc import BaseNPC
from GameObjects.interactions_mixin import prompt_for_roll
from GameObjects.interactions_mixin.skill_check_resolver import compute_skill_modifier_with_sources

from ..base import EventContext, EventResult
from ..registry import register_event
from .base_attack_magic_event import BaseMagicAttackEvent
from .magic_event import MagicEvent
from .magic_utils import grid_distance_feet, pick_position_in_range, pick_target_in_range
from .runtime_effects import add_alarm_ward
from .spell_types import SpellTradition

logger = logging.getLogger(__name__)


def _actor_id(actor) -> str | None:
    if actor is None:
        return None
    return getattr(actor, "object_id", None) or getattr(actor, "name", None) or str(actor)


def _save_outcome(total: int, dc: int) -> str:
    diff = int(total) - int(dc)
    if diff >= 10:
        return "critical_success"
    if diff >= 0:
        return "success"
    if diff <= -10:
        return "critical_failure"
    return "failure"


def _roll_enemy_save(target, skill_id: str, dc: int, *, attacker=None, tags: list[str] | None = None) -> tuple[str, int, int]:
    tags = list(tags or [])
    base_bonus = 0
    if skill_id == Skill.WILL.value:
        base_bonus = int(getattr(target, "will_bonus", 0) or 0)
    elif skill_id == Skill.FORTITUDE.value:
        base_bonus = int(getattr(target, "fortitude_bonus", 0) or 0)
    elif skill_id == Skill.REFLEX.value:
        base_bonus = int(getattr(target, "reflex_bonus", 0) or 0)

    modifier, _breakdown, _notes = compute_skill_modifier_with_sources(
        skill_id=skill_id,
        actor=target,
        target=attacker,
        tags=tags,
        base_modifier=base_bonus,
    )
    roll = random.randint(1, 20)
    total = int(roll) + int(modifier)
    return _save_outcome(total, dc), roll, total


def _iter_enemy_candidates(game):
    for enemy in getattr(game, "enemies", []):
        yield enemy, getattr(enemy, "position", None), "enemy"


def _iter_hero_candidates(game):
    for hero in getattr(game, "heroes", []):
        yield hero, getattr(hero, "position", None), "hero"


def _iter_interactable_candidates(game, *, include_npc: bool):
    board = game.board
    rows = getattr(board, "rows", 0) or 0
    cols = getattr(board, "cols", 0) or 0
    seen: set[int] = set()
    for row in range(rows):
        for col in range(cols):
            pos = (col, row)
            for obj in board.interactables_at(pos):
                if id(obj) in seen:
                    continue
                seen.add(id(obj))
                is_npc = isinstance(obj, BaseNPC)
                if include_npc and not is_npc:
                    continue
                if not include_npc and is_npc:
                    continue
                yield obj, pos, "interactable"


def _remove_statuses(target, status_id: str) -> None:
    statuses = getattr(target, "statuses", None)
    if not isinstance(statuses, list) or not statuses:
        return
    keep = [s for s in statuses if getattr(s, "id", None) != status_id]
    try:
        target.statuses = keep
    except Exception:
        pass


def _remove_bonus_prefix(target, prefix: str) -> None:
    remover = getattr(target, "remove_bonuses_with_prefix", None)
    if callable(remover):
        try:
            remover(prefix)
        except Exception:
            pass
        return
    bonuses = getattr(target, "bonuses", None)
    if not isinstance(bonuses, list):
        return
    try:
        target.bonuses = [b for b in bonuses if not ((getattr(b, "source", "") or "").startswith(prefix))]
    except Exception:
        pass


def _apply_damage(target, amount: int, damage_type: str) -> bool:
    defeated = False
    apply = getattr(target, "apply_damage", None)
    if callable(apply):
        try:
            _, defeated = apply(max(0, int(amount)), damage_type)
        except Exception as exc:
            logger.error("Nie udalo sie zadac obrazen: %s", exc)
    return defeated


def _apply_heal(target, amount: int) -> None:
    heal = getattr(target, "heal", None)
    if callable(heal):
        try:
            heal(max(0, int(amount)))
            return
        except Exception:
            pass
    try:
        target.hp = int(getattr(target, "hp", 0)) + max(0, int(amount))
    except Exception:
        pass


def _prompt_choice(ctx: EventContext, prompt: str, choices: list[str], *, source: str) -> str | None:
    ui = getattr(ctx.game, "ui", None)
    answer = None
    if ui is not None and hasattr(ui, "prompt_choice"):
        try:
            answer = ui.prompt_choice(prompt, choices=choices, source=source)
        except Exception:
            answer = None
    if answer is None:
        if ui is not None and not getattr(ui, "allow_cli_fallback", False):
            return None
        try:
            answer = input(f"{prompt} {choices}: ").strip() or None
        except Exception:
            answer = None
    if answer is None:
        return None
    raw = str(answer).strip()
    if not raw:
        return None
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(choices):
            return choices[idx]
    for item in choices:
        if raw.lower() == item.lower():
            return item
    return None


def _targets_in_radius(candidates, center: tuple[int, int], radius_feet: int):
    result = []
    for target, pos, _kind in candidates:
        if pos is None:
            continue
        if grid_distance_feet(center, pos) <= radius_feet:
            result.append(target)
    return result


def _move_target_by_command(ctx: EventContext, target, anchor_pos: tuple[int, int], *, toward: bool) -> bool:
    board = ctx.game.board
    pos = getattr(target, "position", None)
    if pos is None:
        return False
    neighbors = board.get_neighbors(pos, include_position=False, diagonal=True)
    valid = []
    for cand in neighbors:
        try:
            if not board.can_traverse(pos, cand, allow_occupied=False):
                continue
        except Exception:
            continue
        valid.append(cand)
    if not valid:
        return False
    if toward:
        ordered = sorted(valid, key=lambda p: grid_distance_feet(p, anchor_pos))
    else:
        ordered = sorted(valid, key=lambda p: grid_distance_feet(p, anchor_pos), reverse=True)
    destination = ordered[0]
    try:
        board.move(pos, destination)
        return True
    except Exception:
        return False


def _command_release_holds(ctx: EventContext, commander) -> int:
    commander_id = _actor_id(commander)
    if not commander_id:
        return 0
    removed = 0
    actors = list(getattr(ctx.game, "heroes", []) or []) + list(getattr(ctx.game, "enemies", []) or [])
    for target in actors:
        statuses = getattr(target, "statuses", None)
        if not isinstance(statuses, list) or not statuses:
            continue
        remaining = []
        for status in statuses:
            sid = getattr(status, "id", None)
            data = getattr(status, "data", None) or {}
            if sid in ("grabbed", "restrained") and data.get("source_id") == commander_id:
                removed += 1
                if sid == "grabbed":
                    try:
                        from statuses import clear_grabbed_effects

                        clear_grabbed_effects(target)
                    except Exception:
                        pass
                if sid == "restrained":
                    try:
                        from statuses import clear_restrained_effects

                        clear_restrained_effects(target)
                    except Exception:
                        pass
                continue
            remaining.append(status)
        try:
            target.statuses = remaining
        except Exception:
            pass
    return removed


def _direction_line(center: tuple[int, int], direction: str, steps: int) -> list[tuple[int, int]]:
    mapping = {
        "N": (0, -1),
        "NE": (1, -1),
        "E": (1, 0),
        "SE": (1, 1),
        "S": (0, 1),
        "SW": (-1, 1),
        "W": (-1, 0),
        "NW": (-1, -1),
    }
    vec = mapping.get(direction.upper())
    if vec is None:
        return []
    dx, dy = vec
    out = []
    for idx in range(1, max(0, int(steps)) + 1):
        out.append((center[0] + dx * idx, center[1] + dy * idx))
    return out


@register_event
class AlarmEvent(MagicEvent):
    name = "alarm"
    actions_cost = 2
    default_tags = ["magic", "spell", "abjuration", "ward"]
    spell_tags = ["rank1", "abjuration"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["abjuration"]
    range_feet = 30
    prompt = "Alarm - wybierz pole wardu (promien 10 stop, trigger na enemy)."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        pos = getattr(actor, "position", None)
        if actor is None or pos is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        ward_pos = pick_position_in_range(ctx, pos, max_range_feet=self.range_feet, color=[200, 80, 20])
        if ward_pos is None:
            return EventResult.cancelled(message="Nie wybrano pola wardu.")

        add_alarm_ward(
            ctx.game,
            source_id=_actor_id(actor),
            source_name=getattr(actor, "name", "Caster"),
            center=ward_pos,
            radius_feet=10,
            trigger_kind="enemy",
        )
        return EventResult(success=True, consumed_action=True, message=f"Alarm aktywny na {ward_pos}.")


@register_event
class BaneEvent(MagicEvent):
    name = "bane"
    actions_cost = 2
    default_tags = ["magic", "spell", "enchantment", "aura"]
    spell_tags = ["rank1", "enchantment"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["enchantment"]
    prompt = "Bane - enemy w aurze 10 stop otrzymuja -1 do atakow (1 tura)."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        affected = 0
        for target in _targets_in_radius(_iter_enemy_candidates(ctx.game), actor.position, 10):
            _remove_bonus_prefix(target, "bane:")
            for tag in ("attack_melee", "attack_ranged", "magic"):
                try:
                    target.add_bonus(
                        BonusEffect(
                            type=BonusType.STATUS,
                            value=1,
                            tag=tag,
                            source="bane:attack",
                            label="bane",
                            is_penalty=True,
                            duration_turns=1,
                        )
                    )
                except Exception:
                    pass
            affected += 1
        return EventResult(success=True, consumed_action=True, message=f"Bane aktywne ({affected} celow).")


@register_event
class BlessEvent(MagicEvent):
    name = "bless"
    actions_cost = 2
    default_tags = ["magic", "spell", "enchantment", "aura"]
    spell_tags = ["rank1", "enchantment"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["enchantment"]
    prompt = "Bless - sojusznicy w aurze 10 stop otrzymuja +1 do atakow (1 tura)."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        affected = 0
        for target in _targets_in_radius(_iter_hero_candidates(ctx.game), actor.position, 10):
            _remove_bonus_prefix(target, "bless:")
            for tag in ("attack_melee", "attack_ranged", "magic"):
                try:
                    target.add_bonus(
                        BonusEffect(
                            type=BonusType.STATUS,
                            value=1,
                            tag=tag,
                            source="bless:attack",
                            label="bless",
                            duration_turns=1,
                        )
                    )
                except Exception:
                    pass
            affected += 1
        return EventResult(success=True, consumed_action=True, message=f"Bless aktywne ({affected} celow).")


@register_event
class CharmEvent(MagicEvent):
    name = "charm"
    actions_cost = 2
    default_tags = ["magic", "spell", "enchantment", "mental"]
    spell_tags = ["rank1", "enchantment"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["enchantment"]
    range_feet = 30

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        target, _target_pos = pick_target_in_range(
            ctx,
            actor.position,
            list(_iter_interactable_candidates(ctx.game, include_npc=True)),
            max_range_feet=self.range_feet,
            allowed_kinds=("interactable",),
            tags=self._effective_tags(ctx),
        )
        if target is None:
            return EventResult.cancelled(message="Brak NPC w zasiegu.")

        adjust = getattr(target, "adjust_attitude", None)
        if callable(adjust):
            try:
                value, label = adjust(1)
                msg = f"Charm: nastawienie celu -> {label} ({value})."
            except Exception:
                msg = "Charm: cel staje sie bardziej przyjazny."
        else:
            try:
                target.add_status(CharmedStatus(duration=3, source=self.name))
            except Exception:
                pass
            msg = "Charm: cel staje sie bardziej przyjazny."
        return EventResult(success=True, consumed_action=True, message=msg)


@register_event
class ColorSprayEvent(MagicEvent):
    name = "color_spray"
    actions_cost = 2
    default_tags = ["magic", "spell", "illusion", "visual"]
    spell_tags = ["rank1", "illusion"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["illusion"]
    range_feet = 15

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        spell_dc = int(prompt_for_roll("Color Spray - podaj Spell DC:", layout="test", answer_placeholder="Spell DC") or 0)
        affected = 0
        for target in _targets_in_radius(_iter_enemy_candidates(ctx.game), actor.position, self.range_feet):
            outcome, _roll, _total = _roll_enemy_save(
                target,
                Skill.WILL.value,
                spell_dc,
                attacker=actor,
                tags=["save", Skill.WILL.value, "visual", "illusion", "mental"],
            )
            if outcome in ("success", "critical_success"):
                continue
            _remove_bonus_prefix(target, "color_spray:")
            for tag in ("attack_melee", "attack_ranged", "magic"):
                try:
                    target.add_bonus(
                        BonusEffect(
                            type=BonusType.STATUS,
                            value=1,
                            tag=tag,
                            source="color_spray:dazzled",
                            label="dazzled",
                            is_penalty=True,
                            duration_turns=1,
                        )
                    )
                except Exception:
                    pass
            if outcome == "critical_failure":
                _remove_statuses(target, "stunned")
                try:
                    target.add_status(StunnedStatus(value=1, source=self.name, source_id=_actor_id(actor), source_turns_left=2))
                except Exception:
                    pass
                try:
                    target.add_status(BlindedStatus())
                except Exception:
                    pass
            affected += 1
        return EventResult(success=True, consumed_action=True, message=f"Color Spray: dotknieto {affected} celow.")


@register_event
class CommandEvent(MagicEvent):
    name = "command"
    actions_cost = 2
    default_tags = ["magic", "spell", "enchantment", "mental"]
    spell_tags = ["rank1", "enchantment"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["enchantment"]
    range_feet = 30

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        target, _target_pos = pick_target_in_range(
            ctx,
            actor.position,
            list(_iter_enemy_candidates(ctx.game)),
            max_range_feet=self.range_feet,
            allowed_kinds=("enemy",),
            tags=self._effective_tags(ctx),
        )
        if target is None:
            return EventResult.cancelled(message="Brak celu w zasiegu.")

        spell_dc = int(prompt_for_roll("Command - podaj Spell DC:", layout="test", answer_placeholder="Spell DC") or 0)
        outcome, _roll, _total = _roll_enemy_save(
            target,
            Skill.WILL.value,
            spell_dc,
            attacker=actor,
            tags=["save", Skill.WILL.value, "mental", "enchantment"],
        )
        if outcome in ("success", "critical_success"):
            return EventResult(success=True, consumed_action=True, message=f"Command: {outcome}, brak efektu.")

        choice = _prompt_choice(
            ctx,
            "Command - wybierz komende",
            ["approach", "run", "prone", "stand", "release"],
            source="command_spell",
        )
        if not choice:
            return EventResult(success=True, consumed_action=True, message="Command: cel opiera sie (brak komendy).")

        performed = False
        if choice == "approach":
            performed = _move_target_by_command(ctx, target, actor.position, toward=True)
        elif choice == "run":
            performed = _move_target_by_command(ctx, target, actor.position, toward=False)
        elif choice == "prone":
            _remove_statuses(target, "prone")
            try:
                target.add_status(ProneStatus())
                apply_prone_effects(target)
                performed = True
            except Exception:
                performed = False
        elif choice == "stand":
            _remove_statuses(target, "prone")
            try:
                clear_prone_effects(target)
            except Exception:
                pass
            performed = True
        elif choice == "release":
            performed = _command_release_holds(ctx, target) > 0

        if outcome == "critical_failure":
            _remove_statuses(target, "stunned")
            try:
                target.add_status(StunnedStatus(value=1, source=self.name, source_id=_actor_id(actor), source_turns_left=2))
            except Exception:
                pass

        suffix = "wykonane" if performed else "brak efektu"
        return EventResult(success=True, consumed_action=True, message=f"Command ({choice}): {suffix}.")


@register_event
class DetectAlignmentEvent(MagicEvent):
    name = "detect_alignment"
    actions_cost = 2
    default_tags = ["magic", "spell", "divination", "detect"]
    spell_tags = ["rank1", "divination"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["divination"]
    range_feet = 30

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        alignment = _prompt_choice(
            ctx,
            "Detect Alignment - wybierz aura",
            ["good", "evil", "lawful", "chaotic"],
            source="detect_alignment",
        )
        if not alignment:
            return EventResult.cancelled(message="Nie wybrano alignment.")

        lines = []
        candidates = list(_iter_enemy_candidates(ctx.game)) + list(_iter_hero_candidates(ctx.game))
        candidates += list(_iter_interactable_candidates(ctx.game, include_npc=False))
        for obj, pos, _kind in candidates:
            if pos is None:
                continue
            if grid_distance_feet(actor.position, pos) > self.range_feet:
                continue
            raw = getattr(obj, "alignment", None)
            tags = {str(t).strip().lower() for t in (getattr(obj, "tags", None) or [])}
            aura = str(raw or "").strip().lower()
            if alignment.lower() in tags or alignment.lower() == aura:
                lines.append(f"- {getattr(obj, 'name', getattr(obj, 'object_id', str(obj)))}: {alignment}")

        if not lines:
            lines = [f"Brak wykrytych aur {alignment} w zasiegu."]
        try:
            ctx.game.ui_log("Detect Alignment:\n" + "\n".join(lines))
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Detect Alignment zakonczone.")


@register_event
class FearEvent(MagicEvent):
    name = "fear"
    actions_cost = 2
    default_tags = ["magic", "spell", "enchantment", "mental"]
    spell_tags = ["rank1", "enchantment"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["enchantment"]
    range_feet = 30

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        target, _target_pos = pick_target_in_range(
            ctx,
            actor.position,
            list(_iter_enemy_candidates(ctx.game)),
            max_range_feet=self.range_feet,
            allowed_kinds=("enemy",),
            tags=self._effective_tags(ctx),
        )
        if target is None:
            return EventResult.cancelled(message="Brak celu w zasiegu.")

        spell_dc = int(prompt_for_roll("Fear - podaj Spell DC:", layout="test", answer_placeholder="Spell DC") or 0)
        outcome, _roll, _total = _roll_enemy_save(
            target,
            Skill.WILL.value,
            spell_dc,
            attacker=actor,
            tags=["save", Skill.WILL.value, "fear", "mental"],
        )

        frightened = 0
        if outcome == "failure":
            frightened = 1
        elif outcome == "critical_failure":
            frightened = 2

        if frightened > 0:
            _remove_bonus_prefix(target, "fear:")
            duration = 2 if frightened >= 2 else 1
            for tag in ("attack_melee", "attack_ranged", "magic"):
                try:
                    target.add_bonus(
                        BonusEffect(
                            type=BonusType.STATUS,
                            value=frightened,
                            tag=tag,
                            source="fear:attack",
                            label=f"fear {frightened}",
                            is_penalty=True,
                            duration_turns=duration,
                        )
                    )
                except Exception:
                    pass
            for skill in Skill:
                try:
                    target.add_bonus(
                        BonusEffect(
                            type=BonusType.STATUS,
                            value=frightened,
                            tag=skill.value,
                            source="fear:skill",
                            label=f"fear {frightened}",
                            is_penalty=True,
                            duration_turns=duration,
                        )
                    )
                except Exception:
                    pass
            if frightened >= 2:
                _remove_statuses(target, "speed_penalty")
                try:
                    target.add_status(
                        SpeedPenaltyStatus(
                            penalty_feet=10,
                            source=self.name,
                            source_id=_actor_id(actor),
                            source_turns_left=2,
                            label="fear: flee",
                        )
                    )
                except Exception:
                    pass

        return EventResult(success=True, consumed_action=True, message=f"Fear: {outcome}.")


@register_event
class FloatingDiskEvent(MagicEvent):
    name = "floating_disk"
    actions_cost = 2
    default_tags = ["magic", "spell", "conjuration", "utility"]
    spell_tags = ["rank1", "conjuration"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["conjuration"]

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        _remove_statuses(actor, "floating_disk")
        try:
            actor.add_status(FloatingDiskStatus(duration=10, source=self.name))
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Floating Disk aktywny (uproszczenie).")


@register_event
class GrimTendrilsEvent(MagicEvent):
    name = "grim_tendrils"
    actions_cost = 2
    default_tags = ["magic", "spell", "necromancy", "negative"]
    spell_tags = ["rank1", "necromancy"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["necromancy"]

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        direction = _prompt_choice(ctx, "Grim Tendrils - wybierz kierunek", ["N", "NE", "E", "SE", "S", "SW", "W", "NW"], source="grim_tendrils")
        if not direction:
            return EventResult.cancelled(message="Nie wybrano kierunku.")

        line_positions = _direction_line(actor.position, direction, 6)
        if not line_positions:
            return EventResult.cancelled(message="Nie udalo sie wyznaczyc linii.")

        targets = []
        pos_set = set(line_positions)
        for enemy, pos, _kind in _iter_enemy_candidates(ctx.game):
            if pos in pos_set:
                targets.append(enemy)
        if not targets:
            return EventResult.cancelled(message="Brak celow na linii.")

        spell_dc = int(prompt_for_roll("Grim Tendrils - podaj Spell DC:", layout="test", answer_placeholder="Spell DC") or 0)
        base_damage = int(prompt_for_roll("Grim Tendrils - podaj obrazenia negative:", layout="damage", answer_placeholder="Obrazenia") or 0)

        hit_count = 0
        for target in targets:
            outcome, _roll, _total = _roll_enemy_save(
                target,
                Skill.FORTITUDE.value,
                spell_dc,
                attacker=actor,
                tags=["save", Skill.FORTITUDE.value, "negative", "necromancy"],
            )
            if outcome == "critical_success":
                damage = 0
                bleed = 0
            elif outcome == "success":
                damage = max(0, base_damage // 2)
                bleed = 0
            elif outcome == "failure":
                damage = max(0, base_damage)
                bleed = 1
            else:
                damage = max(0, base_damage * 2)
                bleed = 2

            _apply_damage(target, damage, DamageType.NEGATIVE.value)
            if bleed > 0:
                try:
                    target.add_status(make_persistent_damage(bleed, DamageType.BLEED.value, source=self.name))
                except Exception:
                    pass
            if damage > 0 or bleed > 0:
                hit_count += 1

        return EventResult(success=True, consumed_action=True, message=f"Grim Tendrils trafia {hit_count} celow.")


@register_event
class IllusoryDisguiseEvent(MagicEvent):
    name = "illusory_disguise"
    actions_cost = 2
    default_tags = ["magic", "spell", "illusion"]
    spell_tags = ["rank1", "illusion"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["illusion"]

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        persona = _prompt_choice(
            ctx,
            "Illusory Disguise - wybierz styl",
            ["guard", "merchant", "villager", "noble"],
            source="illusory_disguise",
        )
        persona = persona or "masked"
        _remove_statuses(actor, "illusory_disguise")
        try:
            actor.add_status(IllusoryDisguiseStatus(persona=persona, duration=10, source=self.name))
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message=f"Illusory Disguise: {persona}.")


@register_event
class IllusoryObjectEvent(MagicEvent):
    name = "illusory_object"
    actions_cost = 2
    default_tags = ["magic", "spell", "illusion"]
    spell_tags = ["rank1", "illusion"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["illusion"]
    range_feet = 30

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        pos = pick_position_in_range(ctx, actor.position, max_range_feet=self.range_feet)
        if pos is None:
            return EventResult.cancelled(message="Nie wybrano pozycji iluzji.")
        state = getattr(ctx.game, "_occult_runtime", None)
        if not isinstance(state, dict):
            state = {}
            try:
                ctx.game._occult_runtime = state
            except Exception:
                pass
        illusions = state.setdefault("illusory_objects", [])
        illusions.append({"pos": pos, "source_id": _actor_id(actor)})
        return EventResult(success=True, consumed_action=True, message=f"Illusory Object utworzony na {pos}.")


@register_event
class ItemFacadeEvent(MagicEvent):
    name = "item_facade"
    actions_cost = 2
    default_tags = ["magic", "spell", "illusion"]
    spell_tags = ["rank1", "illusion"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["illusion"]
    range_feet = 30

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        target, _target_pos = pick_target_in_range(
            ctx,
            actor.position,
            list(_iter_interactable_candidates(ctx.game, include_npc=False)),
            max_range_feet=self.range_feet,
            allowed_kinds=("interactable",),
            tags=self._effective_tags(ctx),
        )
        if target is None:
            return EventResult.cancelled(message="Brak przedmiotu w zasiegu.")
        style = _prompt_choice(ctx, "Item Facade - wybierz wyglad", ["perfect", "shoddy"], source="item_facade")
        style = style or "perfect"
        try:
            target.item_facade = style
        except Exception:
            pass
        try:
            target.magical_description = f"Wyglada na {style}."
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message=f"Item Facade: {style}.")


@register_event
class LockSpellEvent(MagicEvent):
    name = "lock"
    actions_cost = 2
    default_tags = ["magic", "spell", "abjuration", "manipulate"]
    spell_tags = ["rank1", "abjuration"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["abjuration"]
    range_feet = 30

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        target, _target_pos = pick_target_in_range(
            ctx,
            actor.position,
            list(_iter_interactable_candidates(ctx.game, include_npc=False)),
            max_range_feet=self.range_feet,
            allowed_kinds=("interactable",),
            tags=self._effective_tags(ctx),
        )
        if target is None:
            return EventResult.cancelled(message="Brak obiektu z zamkiem.")

        if not hasattr(target, "locked"):
            return EventResult.cancelled(message="Wybrany obiekt nie obsluguje zamka.")

        try:
            target.locked = True
        except Exception:
            pass
        try:
            target.is_open = False
        except Exception:
            pass
        try:
            target.jammed = False
        except Exception:
            pass
        try:
            target.thievery_dc = int(getattr(target, "thievery_dc", 15) or 15) + 2
        except Exception:
            pass

        return EventResult(success=True, consumed_action=True, message="Lock: zamek magicznie zabezpieczony.")


@register_event
class MageArmorEvent(MagicEvent):
    name = "mage_armor"
    actions_cost = 2
    default_tags = ["magic", "spell", "abjuration", "defense"]
    spell_tags = ["rank1", "abjuration"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["abjuration"]

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        _remove_bonus_prefix(actor, "mage_armor:")
        try:
            actor.add_bonus(
                BonusEffect(
                    type=BonusType.ITEM,
                    value=1,
                    tag="ac",
                    source="mage_armor:ac",
                    label="mage armor",
                    duration_turns=10,
                )
            )
        except Exception:
            pass
        _remove_statuses(actor, "mage_armor")
        try:
            actor.add_status(MageArmorStatus(duration=10, source=self.name))
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Mage Armor aktywne.")


@register_event
class MagicAuraEvent(MagicEvent):
    name = "magic_aura"
    actions_cost = 2
    default_tags = ["magic", "spell", "illusion"]
    spell_tags = ["rank1", "illusion"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["illusion"]
    range_feet = 30

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        target, _target_pos = pick_target_in_range(
            ctx,
            actor.position,
            list(_iter_interactable_candidates(ctx.game, include_npc=False)),
            max_range_feet=self.range_feet,
            allowed_kinds=("interactable",),
            tags=self._effective_tags(ctx),
        )
        if target is None:
            return EventResult.cancelled(message="Brak obiektu w zasiegu.")

        aura = _prompt_choice(ctx, "Magic Aura - wybierz wyglad aury", ["magical", "mundane"], source="magic_aura")
        aura = aura or "magical"
        try:
            target.magical = aura == "magical"
        except Exception:
            pass
        try:
            target.magical_description = "Fałszywa aura magiczna." if aura == "magical" else "Aura ukryta jako niemagiczna."
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message=f"Magic Aura: {aura}.")


@register_event
class MagicWeaponEvent(MagicEvent):
    name = "magic_weapon"
    actions_cost = 2
    default_tags = ["magic", "spell", "transmutation", "buff"]
    spell_tags = ["rank1", "transmutation"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["transmutation"]
    range_feet = 30

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        target, _target_pos = pick_target_in_range(
            ctx,
            actor.position,
            list(_iter_hero_candidates(ctx.game)),
            max_range_feet=self.range_feet,
            allowed_kinds=("hero",),
            tags=self._effective_tags(ctx),
        )
        if target is None:
            return EventResult.cancelled(message="Brak sojusznika w zasiegu.")

        _remove_bonus_prefix(target, "magic_weapon:")
        for tag in ("attack_melee", "attack_ranged"):
            try:
                target.add_bonus(
                    BonusEffect(
                        type=BonusType.ITEM,
                        value=1,
                        tag=tag,
                        source="magic_weapon:attack",
                        label="magic weapon",
                        duration_turns=1,
                    )
                )
            except Exception:
                pass
        return EventResult(success=True, consumed_action=True, message="Magic Weapon aktywne (1 tura).")


@register_event
class MendingEvent(MagicEvent):
    name = "mending"
    actions_cost = 2
    default_tags = ["magic", "spell", "transmutation", "manipulate"]
    spell_tags = ["rank1", "transmutation"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["transmutation"]
    range_feet = 30

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        target, _target_pos = pick_target_in_range(
            ctx,
            actor.position,
            list(_iter_interactable_candidates(ctx.game, include_npc=False)),
            max_range_feet=self.range_feet,
            allowed_kinds=("interactable",),
            tags=self._effective_tags(ctx),
        )
        if target is None:
            return EventResult.cancelled(message="Brak obiektu do naprawy.")

        repaired = 0
        if hasattr(target, "hp"):
            repaired = int(prompt_for_roll("Mending - podaj liczbe naprawionych HP:", layout="damage", answer_placeholder="HP") or 0)
            try:
                target.hp = int(getattr(target, "hp", 0)) + max(0, repaired)
            except Exception:
                pass
            try:
                if getattr(target, "destroyed", False) and int(getattr(target, "hp", 0)) > 0:
                    target.destroyed = False
            except Exception:
                pass
        if hasattr(target, "jammed"):
            try:
                target.jammed = False
            except Exception:
                pass

        return EventResult(success=True, consumed_action=True, message=f"Mending: naprawiono {max(0, repaired)} HP (jezeli dotyczy).")


@register_event
class MindlinkEvent(MagicEvent):
    name = "mindlink"
    actions_cost = 2
    default_tags = ["magic", "spell", "divination", "mental"]
    spell_tags = ["rank1", "divination"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["divination"]
    range_feet = 30

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        target, _target_pos = pick_target_in_range(
            ctx,
            actor.position,
            list(_iter_hero_candidates(ctx.game)),
            max_range_feet=self.range_feet,
            allowed_kinds=("hero",),
            tags=self._effective_tags(ctx),
        )
        if target is None:
            return EventResult.cancelled(message="Brak sojusznika w zasiegu.")

        _remove_statuses(target, "mindlink")
        try:
            target.add_status(
                MindlinkStatus(
                    source_id=_actor_id(actor),
                    source_turns_left=3,
                    duration=3,
                    source=self.name,
                )
            )
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Mindlink aktywny.")


@register_event
class PhantomPainEvent(MagicEvent):
    name = "phantom_pain"
    actions_cost = 2
    default_tags = ["magic", "spell", "illusion", "mental"]
    spell_tags = ["rank1", "illusion"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["illusion"]
    range_feet = 30

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        target, _target_pos = pick_target_in_range(
            ctx,
            actor.position,
            list(_iter_enemy_candidates(ctx.game)),
            max_range_feet=self.range_feet,
            allowed_kinds=("enemy",),
            tags=self._effective_tags(ctx),
        )
        if target is None:
            return EventResult.cancelled(message="Brak celu w zasiegu.")

        spell_dc = int(prompt_for_roll("Phantom Pain - podaj Spell DC:", layout="test", answer_placeholder="Spell DC") or 0)
        base_damage = int(prompt_for_roll("Phantom Pain - podaj obrazenia mental:", layout="damage", answer_placeholder="Obrazenia") or 0)

        outcome, _roll, _total = _roll_enemy_save(
            target,
            Skill.WILL.value,
            spell_dc,
            attacker=actor,
            tags=["save", Skill.WILL.value, "mental", "illusion"],
        )
        if outcome == "critical_success":
            damage = 0
            sickened_like = 0
            duration = 0
        elif outcome == "success":
            damage = max(0, base_damage // 2)
            sickened_like = 0
            duration = 0
        elif outcome == "failure":
            damage = max(0, base_damage)
            sickened_like = 1
            duration = 1
        else:
            damage = max(0, base_damage * 2)
            sickened_like = 1
            duration = 2

        _apply_damage(target, damage, DamageType.MENTAL.value)
        if sickened_like > 0:
            _remove_bonus_prefix(target, "phantom_pain:")
            for tag in ("attack_melee", "attack_ranged", "magic"):
                try:
                    target.add_bonus(
                        BonusEffect(
                            type=BonusType.STATUS,
                            value=sickened_like,
                            tag=tag,
                            source="phantom_pain:attack",
                            label="phantom pain",
                            is_penalty=True,
                            duration_turns=duration,
                        )
                    )
                except Exception:
                    pass
            for skill in Skill:
                try:
                    target.add_bonus(
                        BonusEffect(
                            type=BonusType.STATUS,
                            value=sickened_like,
                            tag=skill.value,
                            source="phantom_pain:skill",
                            label="phantom pain",
                            is_penalty=True,
                            duration_turns=duration,
                        )
                    )
                except Exception:
                    pass

        return EventResult(success=True, consumed_action=True, message=f"Phantom Pain: {outcome}, obrazenia {damage}.")


@register_event
class ProtectionEvent(MagicEvent):
    name = "protection"
    actions_cost = 1
    default_tags = ["magic", "spell", "abjuration", "defense"]
    spell_tags = ["rank1", "abjuration"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["abjuration"]
    range_feet = 30

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        target, _target_pos = pick_target_in_range(
            ctx,
            actor.position,
            list(_iter_hero_candidates(ctx.game)),
            max_range_feet=self.range_feet,
            allowed_kinds=("hero",),
            tags=self._effective_tags(ctx),
        )
        if target is None:
            return EventResult.cancelled(message="Brak sojusznika w zasiegu.")

        alignment = _prompt_choice(ctx, "Protection - wybierz alignment", ["good", "evil", "lawful", "chaotic"], source="protection")
        alignment = alignment or "evil"
        _remove_bonus_prefix(target, "protection:")
        try:
            target.add_bonus(
                BonusEffect(
                    type=BonusType.STATUS,
                    value=1,
                    tag="ac",
                    source="protection:ac",
                    label=f"protection vs {alignment}",
                    duration_turns=1,
                )
            )
        except Exception:
            pass
        for skill in (Skill.FORTITUDE.value, Skill.REFLEX.value, Skill.WILL.value):
            try:
                target.add_bonus(
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=1,
                        tag=skill,
                        source=f"protection:save:{skill}",
                        label=f"protection vs {alignment}",
                        duration_turns=1,
                    )
                )
            except Exception:
                pass
        return EventResult(success=True, consumed_action=True, message=f"Protection ({alignment}) aktywne.")


@register_event
class RayOfEnfeeblementEvent(BaseMagicAttackEvent):
    name = "ray_of_enfeeblement"
    actions_cost = 2
    range_feet = 30
    default_tags = ["magic", "spell", "necromancy", "attack_ranged"]
    spell_tags = ["rank1", "necromancy"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["necromancy"]

    def _resolve_on_target(self, target, pos, ctx: EventContext, *, critical: bool = False) -> EventResult:
        value = 2 if critical else 1
        _remove_statuses(target, "enfeebled")
        try:
            target.add_status(
                EnfeebledStatus(
                    value=value,
                    source=self.name,
                    source_id=_actor_id(ctx.actor),
                    source_turns_left=2,
                )
            )
        except Exception:
            pass
        msg = f"Ray of Enfeeblement: Enfeebled {value}."
        if critical:
            msg = "Ray of Enfeeblement - krytyk! Enfeebled 2."
        return EventResult(success=True, consumed_action=True, message=msg)


@register_event
class SleepEvent(MagicEvent):
    name = "sleep"
    actions_cost = 2
    default_tags = ["magic", "spell", "enchantment", "mental"]
    spell_tags = ["rank1", "enchantment"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["enchantment"]
    range_feet = 30

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        center = pick_position_in_range(ctx, actor.position, max_range_feet=self.range_feet)
        if center is None:
            return EventResult.cancelled(message="Nie wybrano punktu Sleep.")

        hp_pool = int(prompt_for_roll("Sleep - podaj pule HP czaru:", layout="damage", answer_placeholder="Pula HP") or 0)
        if hp_pool <= 0:
            return EventResult.cancelled(message="Pula Sleep musi byc > 0.")

        enemies = []
        for enemy, pos, _kind in _iter_enemy_candidates(ctx.game):
            if pos is None:
                continue
            if grid_distance_feet(center, pos) <= 10:
                enemies.append(enemy)
        enemies.sort(key=lambda e: int(getattr(e, "hp", 0) or 0))

        affected = 0
        for enemy in enemies:
            hp = int(getattr(enemy, "hp", 0) or 0)
            if hp <= 0 or hp > hp_pool:
                continue
            hp_pool -= hp
            _remove_statuses(enemy, "sleep")
            try:
                enemy.add_status(
                    SleepStatus(
                        source_id=_actor_id(actor),
                        source_turns_left=2,
                        duration=1,
                        source=self.name,
                    )
                )
            except Exception:
                pass
            try:
                enemy.add_status(StunnedStatus(value=1, source=self.name, source_id=_actor_id(actor), source_turns_left=2))
            except Exception:
                pass
            _remove_statuses(enemy, "prone")
            try:
                enemy.add_status(ProneStatus())
                apply_prone_effects(enemy)
            except Exception:
                pass
            _remove_statuses(enemy, "immobilized")
            try:
                enemy.add_status(ImmobilizedStatus(source=self.name, source_id=_actor_id(actor), source_turns_left=2))
            except Exception:
                pass
            affected += 1

        return EventResult(success=True, consumed_action=True, message=f"Sleep: uspiono {affected} celow.")


@register_event
class SootheEvent(MagicEvent):
    name = "soothe"
    actions_cost = 2
    default_tags = ["magic", "spell", "necromancy", "healing"]
    spell_tags = ["rank1", "necromancy"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["necromancy"]
    range_feet = 30

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        target, _target_pos = pick_target_in_range(
            ctx,
            actor.position,
            list(_iter_hero_candidates(ctx.game)),
            max_range_feet=self.range_feet,
            allowed_kinds=("hero",),
            tags=self._effective_tags(ctx),
        )
        if target is None:
            return EventResult.cancelled(message="Brak celu w zasiegu.")

        heal_amount = int(prompt_for_roll("Soothe - podaj wartosc leczenia:", layout="damage", answer_placeholder="Leczenie") or 0)
        _apply_heal(target, heal_amount)
        _remove_bonus_prefix(target, "soothe:")
        try:
            target.add_bonus(
                BonusEffect(
                    type=BonusType.STATUS,
                    value=2,
                    tag=Skill.WILL.value,
                    source="soothe:will",
                    label="soothe",
                    duration_turns=1,
                )
            )
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message=f"Soothe: leczysz {max(0, heal_amount)} HP.")


@register_event
class SpiritLinkEvent(MagicEvent):
    name = "spirit_link"
    actions_cost = 2
    default_tags = ["magic", "spell", "necromancy", "healing"]
    spell_tags = ["rank1", "necromancy"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["necromancy"]
    range_feet = 30

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        target, _target_pos = pick_target_in_range(
            ctx,
            actor.position,
            list(_iter_hero_candidates(ctx.game)),
            max_range_feet=self.range_feet,
            allowed_kinds=("hero",),
            tags=self._effective_tags(ctx),
        )
        if target is None:
            return EventResult.cancelled(message="Brak celu w zasiegu.")

        transfer = int(prompt_for_roll("Spirit Link - podaj natychmiastowy transfer HP:", layout="damage", answer_placeholder="HP") or 0)
        transfer = max(0, transfer)
        if transfer > 0:
            try:
                actor.apply_damage(transfer, DamageType.NORMAL.value)
            except Exception:
                pass
            _apply_heal(target, transfer)

        _remove_statuses(actor, "spirit_link_caster")
        _remove_statuses(target, "spirit_link_target")
        try:
            actor.add_status(
                SpiritLinkCasterStatus(
                    target_id=_actor_id(target),
                    duration=1,
                    source=self.name,
                )
            )
        except Exception:
            pass
        try:
            target.add_status(
                SpiritLinkTargetStatus(
                    source_id=_actor_id(actor),
                    duration=1,
                    source=self.name,
                )
            )
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message=f"Spirit Link: transfer {transfer} HP.")


@register_event
class SummonFeyEvent(MagicEvent):
    name = "summon_fey"
    actions_cost = 3
    default_tags = ["magic", "spell", "conjuration", "summon"]
    spell_tags = ["rank1", "conjuration"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["conjuration"]

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        _remove_bonus_prefix(actor, "summon_fey:")
        for tag in ("attack_melee", "attack_ranged", "magic"):
            try:
                actor.add_bonus(
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=1,
                        tag=tag,
                        source="summon_fey:aid",
                        label="summoned fey",
                        duration_turns=1,
                    )
                )
            except Exception:
                pass
        _remove_statuses(actor, "summoned_fey")
        try:
            actor.add_status(SummonedFeyStatus(duration=1, source=self.name))
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Summon Fey: przyzwany sojusznik wspiera ataki (uproszczenie).")


@register_event
class TrueStrikeEvent(MagicEvent):
    name = "true_strike"
    actions_cost = 1
    default_tags = ["magic", "spell", "divination", "fortune"]
    spell_tags = ["rank1", "divination"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["divination"]

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        _remove_bonus_prefix(actor, "true_strike:")
        for tag in ("attack_melee", "attack_ranged", "magic"):
            try:
                actor.add_bonus(
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=2,
                        tag=tag,
                        source="true_strike:attack",
                        label="true strike",
                        duration_turns=1,
                    )
                )
            except Exception:
                pass
        _remove_statuses(actor, "true_strike")
        try:
            actor.add_status(TrueStrikeStatus(duration=1, source=self.name))
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="True Strike aktywne (+2 do nastepnego ataku, uproszczenie).")


@register_event
class UnseenServantEvent(MagicEvent):
    name = "unseen_servant"
    actions_cost = 2
    default_tags = ["magic", "spell", "conjuration", "utility"]
    spell_tags = ["rank1", "conjuration"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["conjuration"]

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        _remove_statuses(actor, "unseen_servant")
        try:
            actor.add_status(UnseenServantStatus(duration=3, source=self.name))
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Unseen Servant aktywny (uproszczenie).")


@register_event
class VentriloquismEvent(MagicEvent):
    name = "ventriloquism"
    actions_cost = 2
    default_tags = ["magic", "spell", "illusion", "auditory"]
    spell_tags = ["rank1", "illusion"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["illusion"]

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        _remove_bonus_prefix(actor, "ventriloquism:")
        for skill in (Skill.DECEPTION.value, Skill.STEALTH.value):
            try:
                actor.add_bonus(
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=2,
                        tag=skill,
                        source="ventriloquism:skill",
                        label="ventriloquism",
                        duration_turns=1,
                    )
                )
            except Exception:
                pass
        _remove_statuses(actor, "ventriloquism")
        try:
            actor.add_status(VentriloquismStatus(duration=1, source=self.name))
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Ventriloquism aktywne (+2 Deception/Stealth).")
