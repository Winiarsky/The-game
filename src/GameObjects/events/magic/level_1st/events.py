from __future__ import annotations

import logging
import random

from bonuses import BonusEffect, BonusType
from actions.move_utils import adjusted_forced_movement_squares
from combat.hp_engine import apply_damage as hp_apply_damage
from combat.hp_engine import heal as hp_heal
from damage_types import DamageType
from skills import Skill
from statuses import (
    Status,
    BlindedStatus,
    CharmedStatus,
    EnfeebledStatus,
    FrightenedStatus,
    FloatingDiskStatus,
    ImmobilizedStatus,
    IllusoryDisguiseStatus,
    MageArmorStatus,
    MindlinkStatus,
    ProneStatus,
    SleepStatus,
    PoisonedStatus,
    SpeedBonusStatus,
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

from ...base import EventContext, EventResult
from ...registry import register_event
from ..base_attack_magic_event import BaseMagicAttackEvent
from ..magic_event import MagicEvent
from ..magic_utils import grid_distance_feet, pick_position_in_range, pick_target_in_range
from ..runtime_effects import add_alarm_ward
from ..spell_types import SpellTradition

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
            return bool(defeated)
        except Exception as exc:
            logger.error("Nie udalo sie zadac obrazen: %s", exc)
            return False
    try:
        info = hp_apply_damage(target, amount, damage_type, source=f"spell:{damage_type}")
        return bool(info.get("defeated", False))
    except Exception:
        return False


def _apply_heal(target, amount: int) -> None:
    heal = getattr(target, "heal", None)
    if callable(heal):
        try:
            heal(max(0, int(amount)))
            return
        except Exception:
            pass
    try:
        hp_heal(target, amount, source="spell:heal")
    except Exception:
        pass


def _is_undead_target(target) -> bool:
    if target is None:
        return False
    for status in getattr(target, "statuses", []) or []:
        data = getattr(status, "data", None) or {}
        if bool(data.get("treat_as_undead_for_heal_harm", False)):
            return True
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


def _harm_heal_bonus_for_target(target) -> int:
    if target is None:
        return 0
    best = 0
    for status in getattr(target, "statuses", []) or []:
        data = getattr(status, "data", None) or {}
        if not bool(data.get("treat_as_undead_for_heal_harm", False)):
            continue
        try:
            value = int(data.get("harm_heal_bonus", 0) or 0)
        except Exception:
            value = 0
        if value > best:
            best = value
    return max(0, best)


def _is_fiend_target(target) -> bool:
    if target is None:
        return False
    has_tag = getattr(target, "has_tag", None)
    if callable(has_tag):
        for tag in ("fiend", "demon", "devil"):
            try:
                if bool(has_tag(tag)):
                    return True
            except Exception:
                continue
    tags = {str(t).strip().lower() for t in (getattr(target, "tags", None) or [])}
    enemy_type = getattr(target, "enemy_type", None)
    if enemy_type is not None:
        tags.add(str(getattr(enemy_type, "value", enemy_type)).strip().lower())
    return any(tag in tags for tag in ("fiend", "demon", "devil"))


def _has_status_id(actor, status_id: str) -> bool:
    if actor is None:
        return False
    has_status = getattr(actor, "has_status", None)
    if callable(has_status):
        try:
            return bool(has_status(status_id))
        except Exception:
            pass
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) == status_id:
            return True
    return False


def _is_poisonous_target(target) -> bool:
    if target is None:
        return False
    statuses = getattr(target, "statuses", None) or []
    for status in statuses:
        sid = str(getattr(status, "id", "") or "").strip().lower()
        if "poison" in sid or sid in ("venom", "venomous", "poisoned"):
            return True
    tags = {str(t).strip().lower() for t in (getattr(target, "tags", None) or [])}
    for key in ("poison", "poisoned", "venom", "venomous", "toxic"):
        if key in tags:
            return True
    for attr in ("poisonous", "venomous", "toxic"):
        try:
            if bool(getattr(target, attr, False)):
                return True
        except Exception:
            pass
    return False


def _basic_save_damage(base_damage: int, outcome: str) -> int:
    base = max(0, int(base_damage))
    if outcome == "critical_success":
        return 0
    if outcome == "success":
        return max(0, base // 2)
    if outcome == "critical_failure":
        return max(0, base * 2)
    return base


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


def _direction_vec(direction: str) -> tuple[int, int] | None:
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
    return mapping.get(str(direction or "").upper())


def _push_target_linear(ctx: EventContext, target, *, from_pos: tuple[int, int], squares: int = 1) -> int:
    board = ctx.game.board
    pos = getattr(target, "position", None)
    if pos is None:
        return 0
    squares = adjusted_forced_movement_squares(target, squares)
    if squares <= 0:
        return 0
    dx = pos[0] - from_pos[0]
    dy = pos[1] - from_pos[1]
    step_x = 0 if dx == 0 else (1 if dx > 0 else -1)
    step_y = 0 if dy == 0 else (1 if dy > 0 else -1)
    if step_x == 0 and step_y == 0:
        return 0

    moved = 0
    current = pos
    for _ in range(max(0, int(squares))):
        nxt = (current[0] + step_x, current[1] + step_y)
        try:
            if not board.can_traverse(current, nxt, allow_occupied=False):
                break
            board.move(current, nxt)
            moved += 1
            current = nxt
        except Exception:
            break
    return moved


def _cone_positions(origin: tuple[int, int], direction: str, steps: int) -> set[tuple[int, int]]:
    vec = _direction_vec(direction)
    if vec is None:
        return set()
    dx, dy = vec
    out: set[tuple[int, int]] = set()
    for step in range(1, max(0, int(steps)) + 1):
        width = step - 1
        for side in range(-width, width + 1):
            if dx == 0:
                pos = (origin[0] + side, origin[1] + dy * step)
            elif dy == 0:
                pos = (origin[0] + dx * step, origin[1] + side)
            else:
                pos = (origin[0] + dx * step + side * -dy, origin[1] + dy * step + side * dx)
            out.add(pos)
    return out


def _runtime_state(game):
    data = getattr(game, "_arcane_runtime", None)
    if isinstance(data, dict):
        return data
    data = {}
    try:
        game._arcane_runtime = data
    except Exception:
        pass
    return data


@register_event
class MagicMissileEvent(MagicEvent):
    name = "magic_missile"
    actions_cost = 1
    default_tags = ["cast", "attack_ranged", "magic"]
    spell_tags = ["rank1", "occult", "arcane", "evocation", "force"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.OCCULT)
    magic_types = ["evocation"]
    range_feet = 120
    prompt = "Magic Missile - automatyczne trafienie, 1-3 pociski."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        missiles = _prompt_choice(
            ctx,
            "Magic Missile - wybierz liczbe pociskow",
            ["1", "2", "3"],
            source=self.name,
        )
        missiles_count = int(missiles or "1")
        missiles_count = max(1, min(3, missiles_count))

        candidates = list(_iter_enemy_candidates(ctx.game))
        if not candidates:
            return EventResult.cancelled(message="Brak celu dla Magic Missile.")

        spent = 0
        messages: list[str] = []
        for idx in range(missiles_count):
            target, _target_pos = pick_target_in_range(
                ctx,
                actor.position,
                candidates,
                max_range_feet=self.range_feet,
                allowed_kinds=("enemy",),
                tags=self._effective_tags(ctx),
            )
            if target is None:
                break
            dmg = int(
                prompt_for_roll(
                    f"Magic Missile [{idx + 1}/{missiles_count}] - podaj obrazenia (1d4+1):",
                    layout="damage",
                    answer_placeholder="Obrazenia",
                )
                or 0
            )
            defeated = _apply_damage(target, dmg, DamageType.FORCE.value)
            spent += 1
            msg = f"{getattr(target, 'name', 'cel')}: {dmg} force"
            if defeated:
                msg += ", cel pokonany"
            messages.append(msg)

        if spent == 0:
            return EventResult.cancelled(message="Magic Missile przerwane (brak wybranego celu).")

        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=spent,
            message=f"Magic Missile: {'; '.join(messages)}.",
        )


@register_event
class AlarmEvent(MagicEvent):
    name = "alarm"
    actions_cost = 2
    default_tags = ["magic", "spell", "abjuration", "ward"]
    spell_tags = ["rank1", "occult", "arcane", "divine", "abjuration"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA, SpellTradition.DIVINE)
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
    spell_tags = ["rank1", "occult", "enchantment"]
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
    spell_tags = ["rank1", "occult", "enchantment"]
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
    spell_tags = ["rank1", "occult", "arcane", "divine", "enchantment"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA, SpellTradition.DIVINE)
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
    spell_tags = ["rank1", "occult", "arcane", "illusion"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA)
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
    spell_tags = ["rank1", "occult", "arcane", "enchantment"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA)
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
    spell_tags = ["rank1", "occult", "divination"]
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
    spell_tags = ["rank1", "occult", "arcane", "divine", "enchantment"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA, SpellTradition.DIVINE)
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
            _remove_statuses(target, "frightened")
            try:
                target.add_status(FrightenedStatus(value=frightened, source=self.name, source_id=_actor_id(actor)))
            except Exception:
                pass
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
    spell_tags = ["rank1", "occult", "arcane", "conjuration"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA)
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
    spell_tags = ["rank1", "occult", "arcane", "necromancy"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA)
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
    spell_tags = ["rank1", "occult", "arcane", "illusion"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA)
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
    spell_tags = ["rank1", "occult", "arcane", "illusion"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA)
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
    spell_tags = ["rank1", "occult", "arcane", "illusion"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA)
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
    spell_tags = ["rank1", "occult", "arcane", "abjuration"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA)
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
    spell_tags = ["rank1", "occult", "arcane", "abjuration"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA)
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
    spell_tags = ["rank1", "occult", "arcane", "illusion"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA)
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
    spell_tags = ["rank1", "occult", "arcane", "transmutation"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA)
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
    spell_tags = ["rank1", "occult", "arcane", "divine", "transmutation"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA, SpellTradition.DIVINE)
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
    spell_tags = ["rank1", "occult", "divination"]
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
    spell_tags = ["rank1", "occult", "illusion"]
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
    spell_tags = ["rank1", "occult", "abjuration"]
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
    spell_tags = ["rank1", "occult", "arcane", "necromancy"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA)
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
    spell_tags = ["rank1", "occult", "arcane", "enchantment"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA)
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
    spell_tags = ["rank1", "occult", "necromancy"]
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
    spell_tags = ["rank1", "occult", "necromancy"]
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
    spell_tags = ["rank1", "occult", "divine", "conjuration"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.DIVINE)
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
    spell_tags = ["rank1", "occult", "arcane", "divination"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA)
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
    spell_tags = ["rank1", "occult", "arcane", "conjuration"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA)
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
    spell_tags = ["rank1", "occult", "arcane", "divine", "illusion"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA, SpellTradition.DIVINE)
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


@register_event
class AirBubbleEvent(MagicEvent):
    name = "air_bubble"
    actions_cost = 1
    consumes_action = False
    default_tags = ["magic", "spell", "conjuration", "reaction"]
    spell_tags = ["rank1", "arcane", "divine", "conjuration"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL, SpellTradition.DIVINE)
    magic_types = ["conjuration"]
    range_feet = 30
    prompt = "Air Bubble (reaction): cel moze oddychac przez chwile."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        candidates = list(_iter_hero_candidates(ctx.game)) + list(_iter_enemy_candidates(ctx.game))
        target, _target_pos = pick_target_in_range(
            ctx,
            actor.position,
            candidates,
            max_range_feet=self.range_feet,
            allowed_kinds=("hero", "enemy"),
            tags=self._effective_tags(ctx),
        )
        if target is None:
            return EventResult.cancelled(message="Brak celu dla Air Bubble.")
        _remove_statuses(target, "air_bubble")
        try:
            target.add_status(Status(id="air_bubble", label="Air Bubble", duration=1, source=self.name, data={"can_breathe": True}))
        except Exception:
            pass
        try:
            ctx.game.ui_log("Air Bubble: cel moze oddychac (uproszczenie).")
        except Exception:
            pass
        return EventResult(success=True, consumed_action=self.consumes_action, message="Air Bubble aktywne.")


@register_event
class AntHaulEvent(MagicEvent):
    name = "ant_haul"
    actions_cost = 2
    default_tags = ["magic", "spell", "transmutation", "buff"]
    spell_tags = ["rank1", "arcane", "divine", "transmutation"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL, SpellTradition.DIVINE)
    magic_types = ["transmutation"]
    range_feet = 30
    prompt = "Ant Haul: cel moze niesc wiecej (uproszczenie)."

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
            return EventResult.cancelled(message="Brak celu dla Ant Haul.")
        _remove_statuses(target, "ant_haul")
        try:
            target.add_status(
                Status(
                    id="ant_haul",
                    label="Ant Haul",
                    duration=10,
                    source=self.name,
                    data={"carry_multiplier": 3},
                )
            )
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Ant Haul aktywne.")


@register_event
class BurningHandsEvent(MagicEvent):
    name = "burning_hands"
    actions_cost = 2
    default_tags = ["magic", "spell", "evocation", "fire"]
    spell_tags = ["rank1", "arcane", "divine", "evocation"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL, SpellTradition.DIVINE)
    magic_types = ["evocation"]
    range_feet = 15
    prompt = "Burning Hands: stozek ognia (15 stop), Reflex basic save."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        direction = _prompt_choice(
            ctx,
            "Burning Hands - wybierz kierunek",
            ["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
            source=self.name,
        )
        if not direction:
            return EventResult.cancelled(message="Nie wybrano kierunku.")
        cone_positions = _cone_positions(actor.position, direction, 3)
        targets = [enemy for enemy, pos, _kind in _iter_enemy_candidates(ctx.game) if pos in cone_positions]
        if not targets:
            return EventResult.cancelled(message="Brak celow w stozku.")

        spell_dc = int(prompt_for_roll("Burning Hands - podaj Spell DC:", layout="test", answer_placeholder="Spell DC") or 0)
        base_damage = int(prompt_for_roll("Burning Hands - podaj obrazenia fire:", layout="damage", answer_placeholder="Obrazenia") or 0)

        hit_count = 0
        for target in targets:
            outcome, _roll, _total = _roll_enemy_save(
                target,
                Skill.REFLEX.value,
                spell_dc,
                attacker=actor,
                tags=["save", Skill.REFLEX.value, "fire", "evocation"],
            )
            damage = _basic_save_damage(base_damage, outcome)
            _apply_damage(target, damage, DamageType.FIRE.value)
            if damage > 0:
                hit_count += 1
        return EventResult(success=True, consumed_action=True, message=f"Burning Hands trafia {hit_count} celow.")


@register_event
class CreateWaterEvent(MagicEvent):
    name = "create_water"
    actions_cost = 2
    default_tags = ["magic", "spell", "conjuration", "utility"]
    spell_tags = ["rank1", "arcane", "divine", "conjuration"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL, SpellTradition.DIVINE)
    magic_types = ["conjuration"]
    range_feet = 30
    prompt = "Create Water: tworzysz 2 galony wody (uproszczenie)."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        pos = pick_position_in_range(ctx, actor.position, max_range_feet=self.range_feet, color=[30, 120, 200])
        if pos is None:
            return EventResult.cancelled(message="Nie wybrano miejsca dla Create Water.")
        state = _runtime_state(ctx.game)
        buckets = state.setdefault("created_water", [])
        buckets.append({"pos": pos, "gallons": 2, "source_id": _actor_id(actor)})
        return EventResult(success=True, consumed_action=True, message=f"Create Water: utworzono wode na {pos}.")


@register_event
class FeatherFallEvent(MagicEvent):
    name = "feather_fall"
    actions_cost = 1
    consumes_action = False
    default_tags = ["magic", "spell", "abjuration", "reaction"]
    spell_tags = ["rank1", "arcane", "divine", "abjuration"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL, SpellTradition.DIVINE)
    magic_types = ["abjuration"]
    range_feet = 60
    prompt = "Feather Fall (reaction): spowolnij spadanie celu (uproszczenie)."

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
            return EventResult.cancelled(message="Brak celu dla Feather Fall.")
        _remove_statuses(target, "feather_fall")
        try:
            target.add_status(Status(id="feather_fall", label="Feather Fall", duration=1, source=self.name, data={"slow_fall": True}))
        except Exception:
            pass
        return EventResult(success=True, consumed_action=self.consumes_action, message="Feather Fall aktywne.")


@register_event
class FleetStepEvent(MagicEvent):
    name = "fleet_step"
    actions_cost = 1
    default_tags = ["magic", "spell", "transmutation", "buff"]
    spell_tags = ["rank1", "arcane", "divine", "transmutation"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL, SpellTradition.DIVINE)
    magic_types = ["transmutation"]
    prompt = "Fleet Step: +30 stop Speed (uproszczenie)."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        _remove_statuses(actor, "speed_bonus")
        try:
            actor.add_status(SpeedBonusStatus(bonus_feet=30, duration=2, source=self.name, label="fleet step +30ft"))
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Fleet Step aktywne.")


@register_event
class GoblinPoxEvent(MagicEvent):
    name = "goblin_pox"
    actions_cost = 2
    default_tags = ["magic", "spell", "necromancy", "poison"]
    spell_tags = ["rank1", "arcane", "divine", "necromancy"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.OCCULT, SpellTradition.DIVINE)
    magic_types = ["necromancy"]
    range_feet = 30
    prompt = "Goblin Pox: zaraza oslabia cel i zatruwa go."

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
        spell_dc = int(prompt_for_roll("Goblin Pox - podaj Spell DC:", layout="test", answer_placeholder="Spell DC") or 0)
        base_damage = int(prompt_for_roll("Goblin Pox - podaj obrazenia poison:", layout="damage", answer_placeholder="Obrazenia") or 0)
        outcome, _roll, _total = _roll_enemy_save(
            target,
            Skill.FORTITUDE.value,
            spell_dc,
            attacker=actor,
            tags=["save", Skill.FORTITUDE.value, "poison", "necromancy"],
        )
        damage = _basic_save_damage(base_damage, outcome)
        _apply_damage(target, damage, DamageType.POISON.value)
        if outcome in ("failure", "critical_failure"):
            try:
                target.add_status(
                    PoisonedStatus(
                        duration=4 if outcome == "critical_failure" else 3,
                        damage=2 if outcome == "critical_failure" else 1,
                        dc=spell_dc,
                        source=self.name,
                    )
                )
            except Exception:
                pass
        if outcome == "critical_failure":
            _remove_statuses(target, "enfeebled")
            try:
                target.add_status(EnfeebledStatus(value=1, source=self.name, source_id=_actor_id(actor), source_turns_left=2))
            except Exception:
                pass
        return EventResult(success=True, consumed_action=True, message=f"Goblin Pox: {outcome}, obrazenia {damage}.")


@register_event
class GreaseEvent(MagicEvent):
    name = "grease"
    actions_cost = 2
    default_tags = ["magic", "spell", "conjuration", "control"]
    spell_tags = ["rank1", "arcane", "divine", "conjuration"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL, SpellTradition.DIVINE)
    magic_types = ["conjuration"]
    range_feet = 30
    prompt = "Grease: sliska powierzchnia lub obiekt (uproszczenie)."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        mode = _prompt_choice(ctx, "Grease - wybierz tryb", ["surface", "object"], source=self.name) or "surface"
        if mode == "object":
            target, _target_pos = pick_target_in_range(
                ctx,
                actor.position,
                list(_iter_interactable_candidates(ctx.game, include_npc=False)),
                max_range_feet=self.range_feet,
                allowed_kinds=("interactable",),
                tags=self._effective_tags(ctx),
            )
            if target is None:
                return EventResult.cancelled(message="Brak obiektu dla Grease.")
            try:
                setattr(target, "greased", True)
            except Exception:
                pass
            return EventResult(success=True, consumed_action=True, message="Grease: obiekt pokryty smarem.")

        center = pick_position_in_range(ctx, actor.position, max_range_feet=self.range_feet, color=[190, 150, 40])
        if center is None:
            return EventResult.cancelled(message="Nie wybrano pola Grease.")
        spell_dc = int(prompt_for_roll("Grease - podaj Spell DC:", layout="test", answer_placeholder="Spell DC") or 0)
        affected = 0
        for enemy, pos, _kind in _iter_enemy_candidates(ctx.game):
            if pos is None or grid_distance_feet(center, pos) > 5:
                continue
            outcome, _roll, _total = _roll_enemy_save(
                enemy,
                Skill.REFLEX.value,
                spell_dc,
                attacker=actor,
                tags=["save", Skill.REFLEX.value, "grease", "conjuration"],
            )
            if outcome in ("failure", "critical_failure"):
                _remove_statuses(enemy, "prone")
                try:
                    enemy.add_status(ProneStatus())
                    apply_prone_effects(enemy)
                    affected += 1
                except Exception:
                    pass
        state = _runtime_state(ctx.game)
        zones = state.setdefault("grease_zones", [])
        zones.append({"center": center, "radius_feet": 5, "source_id": _actor_id(actor)})
        return EventResult(success=True, consumed_action=True, message=f"Grease aktywne ({affected} celow prone).")


@register_event
class GustOfWindEvent(MagicEvent):
    name = "gust_of_wind"
    actions_cost = 2
    default_tags = ["magic", "spell", "evocation", "air"]
    spell_tags = ["rank1", "arcane", "divine", "evocation"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL, SpellTradition.DIVINE)
    magic_types = ["evocation"]
    prompt = "Gust of Wind: podmuch w linii, odpycha cele."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        direction = _prompt_choice(
            ctx,
            "Gust of Wind - wybierz kierunek",
            ["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
            source=self.name,
        )
        if not direction:
            return EventResult.cancelled(message="Nie wybrano kierunku.")
        line = set(_direction_line(actor.position, direction, 12))
        if not line:
            return EventResult.cancelled(message="Nie udalo sie wyznaczyc linii.")
        spell_dc = int(prompt_for_roll("Gust of Wind - podaj Spell DC:", layout="test", answer_placeholder="Spell DC") or 0)

        pushed = 0
        for enemy, pos, _kind in _iter_enemy_candidates(ctx.game):
            if pos not in line:
                continue
            outcome, _roll, _total = _roll_enemy_save(
                enemy,
                Skill.FORTITUDE.value,
                spell_dc,
                attacker=actor,
                tags=["save", Skill.FORTITUDE.value, "air", "evocation"],
            )
            squares = 0
            if outcome == "failure":
                squares = 1
            elif outcome == "critical_failure":
                squares = 2
            if squares > 0:
                moved = _push_target_linear(ctx, enemy, from_pos=actor.position, squares=squares)
                if moved > 0:
                    pushed += 1

        extinguished = 0
        board = ctx.game.board
        for pos in line:
            for obj in board.interactables_at(pos):
                try:
                    if getattr(obj, "on_fire", False):
                        obj.on_fire = False
                        extinguished += 1
                except Exception:
                    pass
        return EventResult(
            success=True,
            consumed_action=True,
            message=f"Gust of Wind: odepchnieto {pushed} celow, zgaszono {extinguished} zrodel ognia.",
        )


@register_event
class HydraulicPushEvent(BaseMagicAttackEvent):
    name = "hydraulic_push"
    actions_cost = 2
    range_feet = 60
    default_tags = ["magic", "spell", "evocation", "attack_ranged"]
    spell_tags = ["rank1", "arcane", "divine", "evocation"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL, SpellTradition.DIVINE)
    magic_types = ["evocation"]
    prompt = "Hydraulic Push: obrazenia i odrzut celu."

    def _resolve_on_target(self, target, pos, ctx: EventContext, *, critical: bool = False) -> EventResult:
        damage = int(prompt_for_roll("Hydraulic Push - podaj obrazenia:", layout="damage", answer_placeholder="Obrazenia") or 0)
        if critical:
            damage *= 2
        defeated = _apply_damage(target, damage, DamageType.BLUDGEONING.value)
        squares = 2 if critical else 1
        moved = _push_target_linear(ctx, target, from_pos=getattr(ctx.actor, "position", (0, 0)), squares=squares)
        msg = f"Hydraulic Push trafia za {damage} bludgeoning."
        if moved > 0:
            msg += f" Odepchniecie: {moved} pola."
        if defeated:
            msg += " Cel pokonany."
        return EventResult(success=True, consumed_action=True, message=msg)


@register_event
class JumpEvent(MagicEvent):
    name = "jump"
    actions_cost = 1
    default_tags = ["magic", "spell", "transmutation", "movement"]
    spell_tags = ["rank1", "arcane", "divine", "transmutation"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL, SpellTradition.DIVINE)
    magic_types = ["transmutation"]
    prompt = "Jump: wzmacnia nastepny leap/skok (uproszczenie)."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        _remove_statuses(actor, "jump_spell")
        try:
            actor.add_status(
                Status(
                    id="jump_spell",
                    label="Jump",
                    duration=1,
                    source=self.name,
                    data={"jump_bonus_feet": 15},
                )
            )
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Jump aktywne.")


@register_event
class LongstriderEvent(MagicEvent):
    name = "longstrider"
    actions_cost = 2
    default_tags = ["magic", "spell", "transmutation", "buff"]
    spell_tags = ["rank1", "arcane", "divine", "transmutation"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL, SpellTradition.DIVINE)
    magic_types = ["transmutation"]
    range_feet = 30
    prompt = "Longstrider: +10 stop Speed (uproszczenie)."

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
            return EventResult.cancelled(message="Brak celu dla Longstrider.")
        try:
            target.add_status(SpeedBonusStatus(bonus_feet=10, duration=10, source=self.name, label="longstrider +10ft"))
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Longstrider aktywne.")


@register_event
class NegateAromaEvent(MagicEvent):
    name = "negate_aroma"
    actions_cost = 2
    default_tags = ["magic", "spell", "abjuration", "utility"]
    spell_tags = ["rank1", "arcane", "divine", "abjuration"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL, SpellTradition.DIVINE)
    magic_types = ["abjuration"]
    range_feet = 30
    prompt = "Negate Aroma: tlumi zapach celu (uproszczenie)."

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
            return EventResult.cancelled(message="Brak celu dla Negate Aroma.")
        _remove_statuses(target, "negate_aroma")
        try:
            target.add_status(Status(id="negate_aroma", label="Negate Aroma", duration=10, source=self.name, data={"no_scent": True}))
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Negate Aroma aktywne.")


@register_event
class PestFormEvent(MagicEvent):
    name = "pest_form"
    actions_cost = 2
    default_tags = ["magic", "spell", "transmutation", "polymorph"]
    spell_tags = ["rank1", "arcane", "divine", "transmutation"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL, SpellTradition.DIVINE)
    magic_types = ["transmutation"]
    prompt = "Pest Form: przemiana w male zwierze (uproszczenie UI)."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        form = _prompt_choice(ctx, "Pest Form - wybierz forme", ["mouse", "rat", "cat", "bird"], source=self.name) or "mouse"
        _remove_statuses(actor, "pest_form")
        try:
            actor.add_status(Status(id="pest_form", label="Pest Form", duration=5, source=self.name, data={"form": form}))
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message=f"Pest Form: {form}.")


@register_event
class ShockingGraspEvent(BaseMagicAttackEvent):
    name = "shocking_grasp"
    actions_cost = 2
    range_feet = 5
    default_tags = ["magic", "spell", "evocation", "touch"]
    spell_tags = ["rank1", "arcane", "divine", "evocation"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.DIVINE)
    magic_types = ["evocation"]
    prompt = "Shocking Grasp: dotykowy atak elektryczny."

    def _resolve_on_target(self, target, pos, ctx: EventContext, *, critical: bool = False) -> EventResult:
        damage = int(prompt_for_roll("Shocking Grasp - podaj obrazenia electric:", layout="damage", answer_placeholder="Obrazenia") or 0)
        metal = _prompt_choice(ctx, "Shocking Grasp - cel ma metalowa zbroje?", ["nie", "tak"], source=self.name) or "nie"
        if metal == "tak":
            damage += 2
        if critical:
            damage *= 2
        defeated = _apply_damage(target, damage, DamageType.ELECTRIC.value)
        msg = f"Shocking Grasp trafia za {damage} electric."
        if defeated:
            msg += " Cel pokonany."
        return EventResult(success=True, consumed_action=True, message=msg)


@register_event
class SpiderStingEvent(BaseMagicAttackEvent):
    name = "spider_sting"
    actions_cost = 2
    range_feet = 5
    default_tags = ["magic", "spell", "necromancy", "poison", "touch"]
    spell_tags = ["rank1", "arcane", "divine", "necromancy"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.DIVINE)
    magic_types = ["necromancy"]
    prompt = "Spider Sting: jad pajeczy i obrazenia poison."

    def _resolve_on_target(self, target, pos, ctx: EventContext, *, critical: bool = False) -> EventResult:
        damage = int(prompt_for_roll("Spider Sting - podaj obrazenia poison:", layout="damage", answer_placeholder="Obrazenia") or 0)
        if critical:
            damage *= 2
        dc = int(prompt_for_roll("Spider Sting - podaj DC jadu:", layout="test", answer_placeholder="DC") or 15)
        defeated = _apply_damage(target, damage, DamageType.POISON.value)
        try:
            target.add_status(
                PoisonedStatus(
                    duration=3 if critical else 2,
                    damage=2 if critical else 1,
                    dc=dc,
                    source=self.name,
                )
            )
        except Exception:
            pass
        msg = f"Spider Sting trafia za {damage} poison i naklada jad."
        if defeated:
            msg += " Cel pokonany."
        return EventResult(success=True, consumed_action=True, message=msg)


@register_event
class SummonAnimalEvent(MagicEvent):
    name = "summon_animal"
    actions_cost = 3
    default_tags = ["magic", "spell", "conjuration", "summon"]
    spell_tags = ["rank1", "arcane", "divine", "conjuration"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL, SpellTradition.DIVINE)
    magic_types = ["conjuration"]
    prompt = "Summon Animal: uproszczone wsparcie bojowe."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        _remove_bonus_prefix(actor, "summon_animal:")
        for tag in ("attack_melee", "attack_ranged"):
            try:
                actor.add_bonus(
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=1,
                        tag=tag,
                        source="summon_animal:aid",
                        label="summon animal",
                        duration_turns=1,
                    )
                )
            except Exception:
                pass
        _remove_statuses(actor, "summon_animal")
        try:
            actor.add_status(Status(id="summon_animal", label="Summon Animal", duration=1, source=self.name))
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Summon Animal aktywne (uproszczenie).")


@register_event
class SummonConstructEvent(MagicEvent):
    name = "summon_construct"
    actions_cost = 3
    default_tags = ["magic", "spell", "conjuration", "summon"]
    spell_tags = ["rank1", "arcane", "conjuration"]
    magic_traditions = (SpellTradition.ARCANA,)
    magic_types = ["conjuration"]
    prompt = "Summon Construct: uproszczone wsparcie bojowe."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        _remove_bonus_prefix(actor, "summon_construct:")
        try:
            actor.add_bonus(
                BonusEffect(
                    type=BonusType.STATUS,
                    value=1,
                    tag="ac",
                    source="summon_construct:ac",
                    label="summon construct",
                    duration_turns=1,
                )
            )
        except Exception:
            pass
        _remove_statuses(actor, "summon_construct")
        try:
            actor.add_status(Status(id="summon_construct", label="Summon Construct", duration=1, source=self.name))
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Summon Construct aktywne (uproszczenie).")


@register_event
class DetectPoisonEvent(MagicEvent):
    name = "detect_poison"
    actions_cost = 2
    default_tags = ["magic", "spell", "divination", "detect"]
    spell_tags = ["rank1", "divine", "primal", "divination", "detect", "poison"]
    magic_traditions = (SpellTradition.DIVINE, SpellTradition.PRIMAL)
    magic_types = ["divination"]
    range_feet = 30
    prompt = "Detect Poison: sprawdz, czy cel jest trujacy/zatruty."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        candidates = list(_iter_hero_candidates(ctx.game)) + list(_iter_enemy_candidates(ctx.game))
        candidates += list(_iter_interactable_candidates(ctx.game, include_npc=False))
        target, _target_pos = pick_target_in_range(
            ctx,
            actor.position,
            candidates,
            max_range_feet=self.range_feet,
            allowed_kinds=("hero", "enemy", "interactable"),
            tags=self._effective_tags(ctx),
        )
        if target is None:
            return EventResult.cancelled(message="Brak celu dla Detect Poison.")

        poisonous = _is_poisonous_target(target)
        target_name = getattr(target, "name", getattr(target, "object_id", "cel"))
        if poisonous:
            msg = f"Detect Poison: {target_name} wykazuje slady trucizny/jadu."
        else:
            msg = f"Detect Poison: {target_name} nie wykazuje oznak trucizny."
        try:
            ctx.game.ui_log(msg)
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message=msg)


@register_event
class HealEvent(MagicEvent):
    name = "heal"
    actions_cost = 1
    default_tags = ["magic", "spell", "necromancy", "healing"]
    spell_tags = ["rank1", "divine", "primal", "necromancy", "healing", "positive"]
    magic_traditions = (SpellTradition.DIVINE, SpellTradition.PRIMAL)
    magic_types = ["necromancy"]
    range_feet = 30
    prompt = "Heal: leczy zywych, rani undead (uproszczenie single/burst)."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        has_healing_hands = _has_status_id(actor, "healing_hands")
        has_holy_castigation = _has_status_id(actor, "holy_castigation")
        mode = _prompt_choice(ctx, "Heal - wybierz tryb", ["single", "burst"], source=self.name) or "single"
        prompt_hint_parts: list[str] = []
        if has_healing_hands:
            prompt_hint_parts.append("Healing Hands: rozlicz Heal na kosciach d10 zamiast d8.")
        if has_holy_castigation:
            prompt_hint_parts.append("Holy Castigation: Heal moze raniac fiendy jak undead.")
        prompt_hint = "\n".join(prompt_hint_parts) if prompt_hint_parts else None
        amount = int(
            prompt_for_roll(
                "Heal - podaj wartosc leczenia/obrazen positive:",
                layout="damage",
                answer_placeholder="Wartosc",
                prompt_long=prompt_hint,
            )
            or 0
        )
        if amount <= 0:
            return EventResult.cancelled(message="Heal: wartosc musi byc > 0.")

        if mode == "single":
            candidates = list(_iter_hero_candidates(ctx.game)) + list(_iter_enemy_candidates(ctx.game))
            target, _target_pos = pick_target_in_range(
                ctx,
                actor.position,
                candidates,
                max_range_feet=self.range_feet,
                allowed_kinds=("hero", "enemy"),
                tags=self._effective_tags(ctx),
            )
            if target is None:
                return EventResult.cancelled(message="Brak celu dla Heal.")
            if _is_undead_target(target) or (has_holy_castigation and _is_fiend_target(target)):
                defeated = _apply_damage(target, amount, DamageType.POSITIVE.value)
                target_kind = "undead/fiend" if has_holy_castigation else "undead"
                msg = f"Heal: {target_kind} otrzymuje {amount} positive."
                if defeated:
                    msg += " Cel pokonany."
                return EventResult(success=True, consumed_action=True, message=msg)
            _apply_heal(target, amount)
            return EventResult(success=True, consumed_action=True, message=f"Heal: przywrocono {amount} HP.")

        healed = 0
        harmed = 0
        for hero in _targets_in_radius(_iter_hero_candidates(ctx.game), actor.position, self.range_feet):
            if _is_undead_target(hero):
                continue
            _apply_heal(hero, amount)
            healed += 1
        for enemy in _targets_in_radius(_iter_enemy_candidates(ctx.game), actor.position, self.range_feet):
            if not (_is_undead_target(enemy) or (has_holy_castigation and _is_fiend_target(enemy))):
                continue
            _apply_damage(enemy, amount, DamageType.POSITIVE.value)
            harmed += 1
        return EventResult(
            success=True,
            consumed_action=True,
            message=f"Heal (burst): uleczono {healed}, zraniono cele positive {harmed}.",
        )


@register_event
class HarmEvent(MagicEvent):
    name = "harm"
    actions_cost = 1
    default_tags = ["magic", "spell", "necromancy", "negative"]
    spell_tags = ["rank1", "divine", "necromancy", "negative"]
    magic_traditions = (SpellTradition.DIVINE,)
    magic_types = ["necromancy"]
    range_feet = 30
    prompt = "Harm: rani zywych, leczy undead (uproszczenie single/burst)."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        has_harming_hands = _has_status_id(actor, "harming_hands")

        mode = _prompt_choice(ctx, "Harm - wybierz tryb", ["single", "burst"], source=self.name) or "single"
        prompt_hint = "Harming Hands: rozlicz Harm na kosciach d10 zamiast d8." if has_harming_hands else None
        amount = int(
            prompt_for_roll(
                "Harm - podaj wartosc leczenia/obrazen negative:",
                layout="damage",
                answer_placeholder="Wartosc",
                prompt_long=prompt_hint,
            )
            or 0
        )
        if amount <= 0:
            return EventResult.cancelled(message="Harm: wartosc musi byc > 0.")

        if mode == "single":
            candidates = list(_iter_hero_candidates(ctx.game)) + list(_iter_enemy_candidates(ctx.game))
            target, _target_pos = pick_target_in_range(
                ctx,
                actor.position,
                candidates,
                max_range_feet=self.range_feet,
                allowed_kinds=("hero", "enemy"),
                tags=self._effective_tags(ctx),
            )
            if target is None:
                return EventResult.cancelled(message="Brak celu dla Harm.")
            if _is_undead_target(target):
                bonus = _harm_heal_bonus_for_target(target)
                healed = int(amount) + int(bonus)
                _apply_heal(target, healed)
                if bonus > 0:
                    return EventResult(
                        success=True,
                        consumed_action=True,
                        message=f"Harm: undead odzyskuje {healed} HP ({amount} + {bonus} bonus).",
                    )
                return EventResult(success=True, consumed_action=True, message=f"Harm: undead odzyskuje {healed} HP.")
            defeated = _apply_damage(target, amount, DamageType.NEGATIVE.value)
            msg = f"Harm: cel otrzymuje {amount} negative."
            if defeated:
                msg += " Cel pokonany."
            return EventResult(success=True, consumed_action=True, message=msg)

        harmed = 0
        healed_undead = 0
        for hero in _targets_in_radius(_iter_hero_candidates(ctx.game), actor.position, self.range_feet):
            if _is_undead_target(hero):
                _apply_heal(hero, int(amount) + int(_harm_heal_bonus_for_target(hero)))
                healed_undead += 1
                continue
            _apply_damage(hero, amount, DamageType.NEGATIVE.value)
            harmed += 1
        for enemy in _targets_in_radius(_iter_enemy_candidates(ctx.game), actor.position, self.range_feet):
            if _is_undead_target(enemy):
                _apply_heal(enemy, int(amount) + int(_harm_heal_bonus_for_target(enemy)))
                healed_undead += 1
                continue
            _apply_damage(enemy, amount, DamageType.NEGATIVE.value)
            harmed += 1

        return EventResult(
            success=True,
            consumed_action=True,
            message=f"Harm (burst): zraniono zywych {harmed}, uleczono undead {healed_undead}.",
        )


@register_event
class MagicFangEvent(MagicEvent):
    name = "magic_fang"
    actions_cost = 2
    default_tags = ["magic", "spell", "transmutation", "buff"]
    spell_tags = ["rank1", "divine", "primal", "transmutation"]
    magic_traditions = (SpellTradition.DIVINE, SpellTradition.PRIMAL)
    magic_types = ["transmutation"]
    range_feet = 30
    prompt = "Magic Fang: unarmed ataki celu staja sie magiczne (uproszczenie)."

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
            return EventResult.cancelled(message="Brak celu dla Magic Fang.")
        _remove_bonus_prefix(target, "magic_fang:")
        try:
            target.add_bonus(
                BonusEffect(
                    type=BonusType.STATUS,
                    value=1,
                    tag="attack_melee",
                    source="magic_fang:attack",
                    label="magic fang",
                    duration_turns=10,
                )
            )
        except Exception:
            pass
        _remove_statuses(target, "magic_fang")
        try:
            target.add_status(
                Status(
                    id="magic_fang",
                    label="Magic Fang",
                    duration=10,
                    source=self.name,
                    data={"unarmed_magical": True, "unnatural_damage_bonus": 1},
                )
            )
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Magic Fang aktywne.")


@register_event
class PassWithoutTraceEvent(MagicEvent):
    name = "pass_without_trace"
    actions_cost = 2
    default_tags = ["magic", "spell", "abjuration", "stealth"]
    spell_tags = ["rank1", "divine", "primal", "abjuration", "stealth"]
    magic_traditions = (SpellTradition.DIVINE, SpellTradition.PRIMAL)
    magic_types = ["abjuration"]
    range_feet = 30
    prompt = "Pass without Trace: utrudnia tropienie i poprawia skradanie (uproszczenie)."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        affected = 0
        for target in _targets_in_radius(_iter_hero_candidates(ctx.game), actor.position, self.range_feet):
            _remove_bonus_prefix(target, "pass_without_trace:")
            try:
                target.add_bonus(
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=2,
                        tag=Skill.STEALTH.value,
                        source="pass_without_trace:stealth",
                        label="pass without trace",
                        duration_turns=10,
                    )
                )
            except Exception:
                pass
            _remove_statuses(target, "pass_without_trace")
            try:
                target.add_status(
                    Status(
                        id="pass_without_trace",
                        label="Pass without Trace",
                        duration=10,
                        source=self.name,
                        data={"tracks_hidden": True},
                    )
                )
            except Exception:
                pass
            affected += 1
        return EventResult(success=True, consumed_action=True, message=f"Pass without Trace aktywne ({affected} celow).")


@register_event
class PurifyFoodAndDrinkEvent(MagicEvent):
    name = "purify_food_and_drink"
    actions_cost = 2
    default_tags = ["magic", "spell", "necromancy", "utility"]
    spell_tags = ["rank1", "divine", "primal", "necromancy", "purify"]
    magic_traditions = (SpellTradition.DIVINE, SpellTradition.PRIMAL)
    magic_types = ["necromancy"]
    range_feet = 10
    prompt = "Purify Food and Drink: oczyszcza jedzenie i napoje (uproszczenie)."

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
            return EventResult(success=True, consumed_action=True, message="Purify Food and Drink: efekt UI-only (brak obiektu).")
        try:
            setattr(target, "purified", True)
        except Exception:
            pass
        for attr, value in (("poisonous", False), ("venomous", False), ("toxic", False)):
            try:
                setattr(target, attr, value)
            except Exception:
                pass
        try:
            target.magical_description = "Pozywienie/napoj zostaly oczyszczone magicznie."
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Purify Food and Drink: oczyszczono cel.")


@register_event
class ShillelaghEvent(MagicEvent):
    name = "shillelagh"
    actions_cost = 2
    default_tags = ["magic", "spell", "transmutation", "buff"]
    spell_tags = ["rank1", "divine", "primal", "transmutation"]
    magic_traditions = (SpellTradition.DIVINE, SpellTradition.PRIMAL)
    magic_types = ["transmutation"]
    range_feet = 30
    prompt = "Shillelagh: wzmacnia bron obuchowa (uproszczenie)."

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
            return EventResult.cancelled(message="Brak celu dla Shillelagh.")
        _remove_bonus_prefix(target, "shillelagh:")
        try:
            target.add_bonus(
                BonusEffect(
                    type=BonusType.STATUS,
                    value=1,
                    tag="attack_melee",
                    source="shillelagh:attack",
                    label="shillelagh",
                    duration_turns=10,
                )
            )
        except Exception:
            pass
        _remove_statuses(target, "shillelagh")
        try:
            target.add_status(
                Status(
                    id="shillelagh",
                    label="Shillelagh",
                    duration=10,
                    source=self.name,
                    data={"weapon_magical": True, "unnatural_damage_bonus": 1},
                )
            )
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Shillelagh aktywne.")


@register_event
class SummonPlantOrFungusEvent(MagicEvent):
    name = "summon_plant_or_fungus"
    actions_cost = 3
    default_tags = ["magic", "spell", "conjuration", "summon"]
    spell_tags = ["rank1", "divine", "primal", "conjuration"]
    magic_traditions = (SpellTradition.DIVINE, SpellTradition.PRIMAL)
    magic_types = ["conjuration"]
    prompt = "Summon Plant or Fungus: przyzwanie wsparcia bojowego (uproszczenie)."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        _remove_bonus_prefix(actor, "summon_plant_or_fungus:")
        for tag in ("attack_melee", "attack_ranged"):
            try:
                actor.add_bonus(
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=1,
                        tag=tag,
                        source="summon_plant_or_fungus:aid",
                        label="summon plant/fungus",
                        duration_turns=1,
                    )
                )
            except Exception:
                pass
        _remove_statuses(actor, "summon_plant_or_fungus")
        try:
            actor.add_status(Status(id="summon_plant_or_fungus", label="Summon Plant/Fungus", duration=1, source=self.name))
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Summon Plant or Fungus aktywne (uproszczenie).")


@register_event
class SummonPlantEvent(SummonPlantOrFungusEvent):
    name = "summon_plant"
