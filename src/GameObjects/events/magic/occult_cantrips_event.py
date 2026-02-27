from __future__ import annotations

import logging
import random
from typing import Iterable

from board import consts
from bonuses import BonusEffect, BonusType
from damage_types import DamageType
from skills import Skill
from statuses import EnfeebledStatus, StunnedStatus, ShieldCantripStatus, shield_cantrip_ac_bonus
from GameObjects.interactions_mixin import prompt_for_roll
from GameObjects.interactions_mixin.skill_check_resolver import compute_skill_modifier_with_sources
from GameObjects.NPC.base_npc import BaseNPC

from ..base import EventContext, EventResult
from ..registry import register_event
from .base_attack_magic_event import BaseMagicAttackEvent
from .magic_event import MagicEvent
from .magic_utils import pick_target_in_range, positions_within_range
from .spell_types import SpellTradition
from .lighting_effects import (
    set_dancing_positions,
    set_light_source,
    refresh_lighting_on_board,
)

logger = logging.getLogger(__name__)


def _actor_id(actor) -> str | None:
    if actor is None:
        return None
    return getattr(actor, "object_id", None) or getattr(actor, "name", None) or str(actor)


def _apply_damage(target, amount: int, damage_type: str) -> bool:
    defeated = False
    apply = getattr(target, "apply_damage", None)
    if callable(apply):
        try:
            _, defeated = apply(max(0, int(amount)), damage_type)
        except Exception as exc:
            logger.error("Nie udalo sie zadac obrazen: %s", exc)
    return defeated


def _iter_enemy_candidates(game) -> Iterable[tuple[object, tuple[int, int] | None, str]]:
    for enemy in getattr(game, "enemies", []):
        yield enemy, getattr(enemy, "position", None), "enemy"


def _iter_hero_candidates(game) -> Iterable[tuple[object, tuple[int, int] | None, str]]:
    for hero in getattr(game, "heroes", []):
        yield hero, getattr(hero, "position", None), "hero"


def _iter_interactable_candidates(game, *, include_npc: bool) -> Iterable[tuple[object, tuple[int, int] | None, str]]:
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


def _remove_statuses(target, status_id: str) -> None:
    statuses = getattr(target, "statuses", None)
    if not isinstance(statuses, list) or not statuses:
        return
    keep = [s for s in statuses if getattr(s, "id", None) != status_id]
    try:
        target.statuses = keep
    except Exception:
        pass


@register_event
class ChillTouchEvent(MagicEvent):
    name = "chill_touch"
    actions_cost = 2
    range_feet = 5
    default_tags = ["magic", "spell"]
    spell_tags = ["cantrip", "necromancy", "touch"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["necromancy"]
    prompt = "Chill Touch - 1k4 negative, Fortitude save, Enfeebled przy porazce."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        candidates = list(_iter_enemy_candidates(ctx.game))
        target, target_pos = pick_target_in_range(
            ctx,
            actor.position,
            candidates,
            max_range_feet=self.range_feet,
            allowed_kinds=("enemy",),
            tags=self._effective_tags(ctx),
        )
        if target is None or target_pos is None:
            return EventResult.cancelled(message="Brak celu w zasiegu dotyku.")

        spell_dc = int(prompt_for_roll("Chill Touch - podaj Spell DC:", layout="test", answer_placeholder="Spell DC") or 0)
        base_damage = int(
            prompt_for_roll(
                "Chill Touch - obrazenia negative (podaj wynik 1k4):",
                layout="damage",
                answer_placeholder="1k4",
            )
            or 0
        )

        outcome, roll, total = _roll_enemy_save(
            target,
            Skill.FORTITUDE.value,
            spell_dc,
            attacker=actor,
            tags=["save", Skill.FORTITUDE.value, "magic", "negative"],
        )

        if outcome == "critical_success":
            damage = 0
            enfeebled = 0
        elif outcome == "success":
            damage = max(0, base_damage // 2)
            enfeebled = 0
        elif outcome == "failure":
            damage = max(0, base_damage)
            enfeebled = 1
        else:
            damage = max(0, base_damage * 2)
            enfeebled = 2

        defeated = _apply_damage(target, damage, DamageType.NEGATIVE.value)
        if enfeebled > 0:
            _remove_statuses(target, "enfeebled")
            try:
                target.add_status(
                    EnfeebledStatus(
                        value=enfeebled,
                        source=self.name,
                        source_id=_actor_id(actor),
                        source_turns_left=2,
                    )
                )
            except Exception:
                pass

        try:
            ctx.game.ui_log(
                f"Chill Touch: Fort save k20={roll}, suma={total} vs DC {spell_dc}: {outcome}. "
                f"Obrazenia: {damage}."
            )
        except Exception:
            pass

        msg = f"Chill Touch: {outcome}, obrazenia {damage} negative."
        if enfeebled > 0:
            msg += f" Enfeebled {enfeebled}."
        if defeated:
            msg += " Cel pokonany."
        return EventResult(success=True, consumed_action=self.consumes_action, message=msg)


@register_event
class DancingLightsEvent(MagicEvent):
    name = "dancing_lights"
    actions_cost = 2
    default_tags = ["magic", "spell"]
    spell_tags = ["cantrip", "evocation"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["evocation"]
    range_feet = 30
    prompt = "Dancing Lights - wybierz do 4 pol darkness/dim light i zatwierdz klikajac na bohatera."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        board = ctx.game.board
        in_range = positions_within_range(board, actor.position, self.range_feet)
        dark_positions: list[tuple[int, int]] = []
        dim_positions: list[tuple[int, int]] = []
        for pos in in_range:
            try:
                terrain_name = str(getattr(board.cell_at(pos).field, "name", "")).strip().lower()
            except Exception:
                terrain_name = ""
            if terrain_name == "darkness":
                dark_positions.append(pos)
            elif terrain_name == "dim_light":
                dim_positions.append(pos)

        valid = set(dark_positions + dim_positions)
        if not valid:
            return EventResult.cancelled(message="Brak pol darkness/dim light w zasiegu.")

        selected: set[tuple[int, int]] = set()
        valid_list = list(valid)

        while True:
            colors = []
            for pos in valid_list:
                if pos in selected:
                    colors.append([180, 180, 40])
                elif pos in dark_positions:
                    colors.append([120, 20, 120])
                else:
                    colors.append([20, 20, 150])
            try:
                ctx.game.conn.set_leds(valid_list + [actor.position], colors + [consts.HERO_HIGHLIGHT_RGB])
                choice = ctx.game.conn.scan_board(valid_list + [actor.position])
            finally:
                try:
                    ctx.game.conn.leds_off()
                except Exception:
                    pass

            if choice == actor.position:
                break
            if choice not in valid:
                continue
            if choice in selected:
                selected.remove(choice)
            elif len(selected) < 4:
                selected.add(choice)

        set_dancing_positions(ctx.game, list(selected))
        refresh_lighting_on_board(ctx.game)

        try:
            ctx.game.ui_log(f"Dancing Lights: aktywne pola {sorted(selected)}.")
        except Exception:
            pass
        return EventResult(success=True, consumed_action=self.consumes_action, message="Dancing Lights aktywne.")


@register_event
class DazeEvent(MagicEvent):
    name = "daze"
    actions_cost = 2
    default_tags = ["magic", "spell"]
    spell_tags = ["cantrip", "enchantment"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["enchantment"]
    range_feet = 60
    prompt = "Daze - enemy robi Will save."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        candidates = list(_iter_enemy_candidates(ctx.game))
        target, target_pos = pick_target_in_range(
            ctx,
            actor.position,
            candidates,
            max_range_feet=self.range_feet,
            allowed_kinds=("enemy",),
            tags=self._effective_tags(ctx),
        )
        if target is None or target_pos is None:
            return EventResult.cancelled(message="Brak celu w zasiegu.")

        spell_dc = int(prompt_for_roll("Daze - podaj Spell DC:", layout="test", answer_placeholder="Spell DC") or 0)
        base_damage = int(
            prompt_for_roll(
                "Daze - podaj obrazenia mental:",
                layout="damage",
                answer_placeholder="Obrazenia",
            )
            or 0
        )

        outcome, roll, total = _roll_enemy_save(
            target,
            Skill.WILL.value,
            spell_dc,
            attacker=actor,
            tags=["save", Skill.WILL.value, "mental", "magic"],
        )

        if outcome == "critical_success":
            damage = 1
            stunned = 0
        elif outcome == "success":
            damage = max(0, base_damage // 2)
            stunned = 0
        elif outcome == "failure":
            damage = max(0, base_damage)
            stunned = 0
        else:
            damage = max(0, base_damage)
            stunned = 1

        defeated = _apply_damage(target, damage, DamageType.MENTAL.value)
        if stunned > 0:
            _remove_statuses(target, "stunned")
            try:
                target.add_status(StunnedStatus(value=stunned, source=self.name))
            except Exception:
                pass

        try:
            ctx.game.ui_log(
                f"Daze: Will save k20={roll}, suma={total} vs DC {spell_dc}: {outcome}. "
                f"Obrazenia: {damage}."
            )
        except Exception:
            pass

        msg = f"Daze: {outcome}, obrazenia {damage} mental."
        if stunned > 0:
            msg += " Cel stunned 1."
        if defeated:
            msg += " Cel pokonany."
        return EventResult(success=True, consumed_action=self.consumes_action, message=msg)


@register_event
class ForbiddingWardEvent(MagicEvent):
    name = "forbidding_ward"
    actions_cost = 2
    default_tags = ["magic", "spell", "ward"]
    spell_tags = ["cantrip", "abjuration"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["abjuration"]
    range_feet = 30
    prompt = "Forbidding Ward - +1 AC i save tylko wzgledem wybranego przeciwnika."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        ally_candidates = list(_iter_hero_candidates(ctx.game))
        enemy_candidates = list(_iter_enemy_candidates(ctx.game))

        ally, ally_pos = pick_target_in_range(
            ctx,
            actor.position,
            ally_candidates,
            max_range_feet=self.range_feet,
            allowed_kinds=("hero",),
            tags=self._effective_tags(ctx),
        )
        if ally is None or ally_pos is None:
            return EventResult.cancelled(message="Nie wybrano sojusznika.")

        enemy, enemy_pos = pick_target_in_range(
            ctx,
            actor.position,
            enemy_candidates,
            max_range_feet=self.range_feet,
            allowed_kinds=("enemy",),
            tags=self._effective_tags(ctx),
        )
        if enemy is None or enemy_pos is None:
            return EventResult.cancelled(message="Nie wybrano przeciwnika.")

        ally_id = _actor_id(ally)
        enemy_id = _actor_id(enemy)
        if ally_id is None or enemy_id is None:
            return EventResult.cancelled(message="Nie mozna okreslic target_id.")

        remove_ally = getattr(ally, "remove_bonuses_with_prefix", None)
        if callable(remove_ally):
            try:
                remove_ally("forbidding_ward:")
            except Exception:
                pass
        remove_enemy = getattr(enemy, "remove_bonuses_with_prefix", None)
        if callable(remove_enemy):
            try:
                remove_enemy("forbidding_ward:")
            except Exception:
                pass

        try:
            ally.add_bonus(
                BonusEffect(
                    type=BonusType.STATUS,
                    value=1,
                    tag="ac",
                    source="forbidding_ward:ac",
                    label="forbidding ward",
                    target_id=enemy_id,
                    duration_turns=1,
                )
            )
        except Exception:
            pass

        for skill_id in (Skill.FORTITUDE.value, Skill.REFLEX.value, Skill.WILL.value):
            try:
                ally.add_bonus(
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=1,
                        tag=skill_id,
                        source=f"forbidding_ward:save:{skill_id}",
                        label="forbidding ward",
                        target_id=enemy_id,
                        duration_turns=1,
                    )
                )
            except Exception:
                pass

        for attack_tag in ("attack_melee", "attack_ranged", "magic"):
            try:
                enemy.add_bonus(
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=1,
                        tag=attack_tag,
                        source="forbidding_ward:penalty",
                        label="forbidding ward",
                        target_id=ally_id,
                        is_penalty=True,
                        duration_turns=1,
                    )
                )
            except Exception:
                pass

        try:
            ctx.game.ui_log("Forbidding Ward: aktywne +1 AC/save i -1 atak dla pary celow.")
        except Exception:
            pass
        return EventResult(success=True, consumed_action=self.consumes_action, message="Forbidding Ward aktywne.")


@register_event
class GuidanceEvent(MagicEvent):
    name = "guidance"
    actions_cost = 1
    default_tags = ["magic", "spell", "support"]
    spell_tags = ["cantrip", "divination"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["divination"]
    range_feet = 30
    prompt = "Guidance - +1 status do atakow i testow (1 tura)."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        target, target_pos = pick_target_in_range(
            ctx,
            actor.position,
            list(_iter_hero_candidates(ctx.game)),
            max_range_feet=self.range_feet,
            allowed_kinds=("hero",),
            tags=self._effective_tags(ctx),
        )
        if target is None or target_pos is None:
            return EventResult.cancelled(message="Nie wybrano sojusznika.")

        remover = getattr(target, "remove_bonuses_with_prefix", None)
        if callable(remover):
            try:
                remover("guidance:")
            except Exception:
                pass

        for tag in ("attack_melee", "attack_ranged", "magic"):
            try:
                target.add_bonus(
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=1,
                        tag=tag,
                        source="guidance:attack",
                        label="guidance",
                        duration_turns=1,
                    )
                )
            except Exception:
                pass
        for skill in Skill:
            try:
                target.add_bonus(
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=1,
                        tag=skill.value,
                        source="guidance:skill",
                        label="guidance",
                        duration_turns=1,
                    )
                )
            except Exception:
                pass
        return EventResult(success=True, consumed_action=self.consumes_action, message="Guidance aktywne.")


@register_event
class LightEvent(MagicEvent):
    name = "light"
    actions_cost = 2
    default_tags = ["magic", "spell"]
    spell_tags = ["cantrip", "evocation"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["evocation"]
    prompt = "Light - aura 30 stop od castera do konca walki."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        set_light_source(ctx.game, actor, radius_feet=30)
        refresh_lighting_on_board(ctx.game)
        try:
            ctx.game.ui_log("Light: aura 30 stop aktywna do konca walki.")
        except Exception:
            pass
        return EventResult(success=True, consumed_action=self.consumes_action, message="Light aktywne.")


@register_event
class MageHandEvent(MagicEvent):
    name = "mage_hand"
    actions_cost = 2
    default_tags = ["magic", "spell", "manipulate"]
    spell_tags = ["cantrip", "evocation"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["evocation"]
    range_feet = 30
    prompt = "Mage Hand - interakcja z interactable (bez NPC) do 30 stop."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        candidates = list(_iter_interactable_candidates(ctx.game, include_npc=False))
        target, target_pos = pick_target_in_range(
            ctx,
            actor.position,
            candidates,
            max_range_feet=self.range_feet,
            allowed_kinds=("interactable",),
            tags=self._effective_tags(ctx),
        )
        if target is None or target_pos is None:
            return EventResult.cancelled(message="Brak obiektu interactable w zasiegu.")

        message = ""
        try:
            if hasattr(target, "actions") and isinstance(getattr(target, "actions", None), dict) and "interact" in target.actions:
                message = str(target.interact(actor, ctx.game, action_id="interact"))
            else:
                message = str(target.interact(actor, ctx.game))
        except Exception as exc:
            return EventResult(success=False, consumed_action=False, message=f"Mage Hand nie powiodlo sie: {exc}")

        try:
            if message:
                ctx.game.ui_log(message)
        except Exception:
            pass
        return EventResult(success=True, consumed_action=self.consumes_action, message="Mage Hand wykonane.")


@register_event
class MessageEvent(MagicEvent):
    name = "message"
    actions_cost = 1
    default_tags = ["magic", "spell"]
    spell_tags = ["cantrip", "illusion"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["illusion"]
    range_feet = 120
    prompt = "Message - rozmowa z NPC na odleglosc."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        candidates = list(_iter_interactable_candidates(ctx.game, include_npc=True))
        target, target_pos = pick_target_in_range(
            ctx,
            actor.position,
            candidates,
            max_range_feet=self.range_feet,
            allowed_kinds=("interactable",),
            tags=self._effective_tags(ctx),
        )
        if target is None or target_pos is None:
            return EventResult.cancelled(message="Brak NPC w zasiegu.")

        message = ""
        try:
            if hasattr(target, "actions") and isinstance(getattr(target, "actions", None), dict) and "talk" in target.actions:
                message = str(target.interact(actor, ctx.game, action_id="talk"))
            else:
                message = str(target.interact(actor, ctx.game))
        except Exception as exc:
            return EventResult(success=False, consumed_action=False, message=f"Message nie powiodlo sie: {exc}")

        try:
            if message:
                ctx.game.ui_log(message)
        except Exception:
            pass
        return EventResult(success=True, consumed_action=self.consumes_action, message="Message wykonane.")


@register_event
class PrestidigitationEvent(MagicEvent):
    name = "prestidigitation"
    actions_cost = 2
    default_tags = ["magic", "spell"]
    spell_tags = ["cantrip", "evocation"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["evocation"]

    def execute(self, ctx: EventContext) -> EventResult:
        try:
            ctx.game.ui_log("Prestidigitation: drobny efekt magiczny (opisowy).")
        except Exception:
            pass
        return EventResult(success=True, consumed_action=self.consumes_action, message="Prestidigitation wykonane.")


@register_event
class ReadAuraEvent(MagicEvent):
    name = "read_aura"
    actions_cost = 2
    default_tags = ["magic", "spell", "detect"]
    spell_tags = ["cantrip", "divination"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["divination"]
    range_feet = 30
    prompt = "Read Aura - pokaz statusy enemy w zasiegu 30 stop."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        target, target_pos = pick_target_in_range(
            ctx,
            actor.position,
            list(_iter_enemy_candidates(ctx.game)),
            max_range_feet=self.range_feet,
            allowed_kinds=("enemy",),
            tags=self._effective_tags(ctx),
        )
        if target is None or target_pos is None:
            return EventResult.cancelled(message="Brak enemy w zasiegu.")

        statuses = getattr(target, "statuses", None) or []
        lines = []
        for status in statuses:
            sid = getattr(status, "id", None)
            if not sid:
                continue
            label = getattr(status, "label", None) or sid
            lines.append(f"- {label} ({sid})")
        if not lines:
            lines = ["- brak statusow"]
        text = f"Read Aura [{getattr(target, 'name', 'enemy')}]:\n" + "\n".join(lines)
        try:
            ctx.game.ui_log(text)
        except Exception:
            pass
        return EventResult(success=True, consumed_action=self.consumes_action, message="Read Aura wykonane.")


@register_event
class ShieldCantripEvent(MagicEvent):
    name = "shield_cantrip"
    actions_cost = 1
    default_tags = ["magic", "spell", "defense"]
    spell_tags = ["cantrip", "abjuration"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["abjuration"]
    prompt = "Shield Cantrip - +1 AC i absorpcja 5 obrazen."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        remove_bonus = getattr(actor, "remove_bonuses_with_prefix", None)
        if callable(remove_bonus):
            try:
                remove_bonus("shield_cantrip:")
            except Exception:
                pass
        _remove_statuses(actor, "shield_cantrip")

        try:
            actor.add_bonus(shield_cantrip_ac_bonus())
            actor.add_status(ShieldCantripStatus(value=5, duration=1))
        except Exception:
            return EventResult(success=False, consumed_action=False, message="Nie udalo sie aktywowac Shield Cantrip.")

        try:
            ctx.game.ui_log("Shield Cantrip: +1 AC, absorpcja 5 obrazen do poczatku nastepnej tury.")
        except Exception:
            pass
        return EventResult(success=True, consumed_action=True, message="Shield Cantrip aktywne.")


@register_event
class TelekineticProjectileEvent(BaseMagicAttackEvent):
    name = "telekinetic_projectile"
    actions_cost = 2
    range_feet = 30
    default_tags = ["magic", "spell", "attack_ranged"]
    spell_tags = ["cantrip", "evocation"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["evocation"]

    def _resolve_on_target(self, target, pos, ctx: EventContext, *, critical: bool = False) -> EventResult:
        damage = int(
            prompt_for_roll(
                "Telekinetic Projectile - podaj obrazenia:",
                layout="damage",
                answer_placeholder="Obrazenia",
            )
            or 0
        )
        if critical:
            damage *= 2

        dtype = DamageType.BLUDGEONING.value
        try:
            ui = getattr(ctx.game, "ui", None)
            if ui and hasattr(ui, "prompt_choice"):
                choice = str(
                    ui.prompt_choice(
                        "Telekinetic Projectile - wybierz typ obrazen",
                        choices=["bludgeoning", "piercing", "slashing"],
                        source="telekinetic_projectile",
                    )
                    or ""
                ).strip().lower()
                if choice in ("bludgeoning", "piercing", "slashing"):
                    dtype = choice
        except Exception:
            pass

        defeated = _apply_damage(target, damage, dtype)
        msg = f"Telekinetic Projectile trafia za {damage} {dtype}."
        if critical:
            msg = f"Telekinetic Projectile - krytyk! {damage} {dtype}."
        if defeated:
            msg += " Cel pokonany."
        return EventResult(success=True, consumed_action=self.consumes_action, message=msg)

