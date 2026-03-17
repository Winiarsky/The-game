from __future__ import annotations

import logging
from typing import Iterable

from board import consts
from bonuses import BonusEffect, BonusType
from combat.damage_utils import burn_it_bonus, burn_it_prompt_note
from combat.hp_engine import apply_damage as hp_apply_damage
from damage_types import DamageType
from skills import Skill
from statuses import (
    EnfeebledStatus,
    ImmobilizedStatus,
    ShieldCantripStatus,
    SpeedPenaltyStatus,
    StunnedStatus,
    inspire_courage_damage_bonus,
    make_persistent_damage,
    shield_cantrip_ac_bonus,
)
from GameObjects.interactions_mixin import prompt_for_roll
from GameObjects.interactions_mixin.magical_mixin import MagicalMixin
from GameObjects.NPC.base_npc import BaseNPC

from ...base import EventContext, EventResult
from ...registry import register_event
from ..base_attack_magic_event import BaseMagicAttackEvent, prompt_spell_save_roll, spell_dc_details
from ..magic_utils import grid_distance_feet
from ..magic_event import MagicEvent
from ..magic_utils import pick_position_in_range, pick_target_in_range, positions_within_range
from ..spell_types import SpellTradition
from ..lighting_effects import (
    set_dancing_positions,
    set_light_source,
    refresh_lighting_on_board,
)

logger = logging.getLogger(__name__)
ALIGNMENT_KEYS = ("good", "evil", "lawful", "chaotic")


def _actor_id(actor) -> str | None:
    if actor is None:
        return None
    return getattr(actor, "object_id", None) or getattr(actor, "name", None) or str(actor)


def _auto_cantrip_rank(actor) -> int:
    try:
        level = int(getattr(actor, "level", 1) or 1)
    except Exception:
        level = 1
    return max(1, (max(1, level) + 1) // 2)


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
        info = hp_apply_damage(target, amount, damage_type, source=f"cantrip:{damage_type}")
        return bool(info.get("defeated", False))
    except Exception:
        return False


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


def _roll_enemy_save(target, skill_id: str, dc: int, *, attacker=None, tags: list[str] | None = None) -> tuple[str, int, int]:
    return prompt_spell_save_roll(
        target=target,
        skill_id=skill_id,
        dc=dc,
        attacker=attacker,
        tags=tags,
    )


def _spell_dc_for_actor(actor, *, action_tag: str = "magic") -> int:
    dc, _modifier, _best_effects, _log_lines = spell_dc_details(actor, action_tag=action_tag)
    return int(dc)


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
    chooser = getattr(ui, "prompt_choice", None)
    if not callable(chooser):
        return None
    try:
        value = chooser(prompt, choices=choices, source=source)
    except Exception:
        return None
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _remove_statuses(target, status_id: str) -> None:
    statuses = getattr(target, "statuses", None)
    if not isinstance(statuses, list) or not statuses:
        return
    keep = [s for s in statuses if getattr(s, "id", None) != status_id]
    try:
        target.statuses = keep
    except Exception:
        pass


def _level_range(actor) -> int:
    try:
        level = int(getattr(actor, "level", 1) or 1)
    except Exception:
        level = 1
    return max(1, level // 2)


def _is_magical(obj) -> bool:
    if obj is None:
        return False
    if getattr(obj, "magical", False):
        return True
    tags = getattr(obj, "tags", None) or []
    return "magical" in tags or "magic" in tags


def _magical_description(obj) -> str:
    desc = getattr(obj, "magical_description", "") or ""
    if desc:
        return desc
    name = getattr(obj, "name", None) or getattr(obj, "label", None)
    if name:
        return f"Magiczny obiekt: {name}"
    return "Magiczna aura."


def _iter_room_objects(ctx: EventContext, rooms: set[str]) -> list[tuple[object, tuple[int, int]]]:
    board = ctx.game.board
    positions = board.positions_in_rooms(rooms) if rooms else set()
    seen: set[int] = set()
    result: list[tuple[object, tuple[int, int]]] = []
    for pos in positions:
        occ = board.occupant_at(pos)
        if occ is not None and id(occ) not in seen:
            seen.add(id(occ))
            result.append((occ, pos))
        for obj in board.interactables_at(pos):
            if id(obj) in seen:
                continue
            seen.add(id(obj))
            result.append((obj, pos))
    return result


def _is_undead_target(target) -> bool:
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


def _extract_alignment_values(raw) -> list[str]:
    values: list[str] = []
    if raw is None:
        return values
    if isinstance(raw, (list, tuple, set)):
        for item in raw:
            for value in _extract_alignment_values(item):
                if value not in values:
                    values.append(value)
        return values

    text = str(raw).strip().lower()
    shorthand = {
        "lg": ["lawful", "good"],
        "ln": ["lawful"],
        "le": ["lawful", "evil"],
        "ng": ["good"],
        "n": [],
        "ne": ["evil"],
        "cg": ["chaotic", "good"],
        "cn": ["chaotic"],
        "ce": ["chaotic", "evil"],
    }
    if text in shorthand:
        return list(shorthand[text])

    tokens = (
        text.replace("_", " ")
        .replace("-", " ")
        .replace("/", " ")
        .replace(",", " ")
        .split()
    )
    for key in ALIGNMENT_KEYS:
        if key in tokens and key not in values:
            values.append(key)
    return values


def _alignment_values_from_target(target) -> set[str]:
    values: set[str] = set()
    if target is None:
        return values
    for value in _extract_alignment_values(getattr(target, "alignment", None)):
        values.add(value)
    for value in _extract_alignment_values(getattr(target, "deity_alignment", None)):
        values.add(value)
    for value in _extract_alignment_values(getattr(target, "tags", None) or []):
        values.add(value)
    return values


def _is_opposed_alignment(target, damage_alignment: str) -> bool:
    alignment = str(damage_alignment or "").strip().lower()
    opposites = {
        "good": "evil",
        "evil": "good",
        "lawful": "chaotic",
        "chaotic": "lawful",
    }
    needed = opposites.get(alignment)
    if not needed:
        return False
    return needed in _alignment_values_from_target(target)


def _resolve_divine_lance_alignment(ctx: EventContext, actor) -> str:
    if actor is None:
        return "good"
    stored = str(getattr(actor, "divine_lance_alignment", "") or "").strip().lower()
    if stored in ALIGNMENT_KEYS:
        return stored

    for source in (
        getattr(actor, "deity_alignment", None),
        getattr(actor, "alignment", None),
        getattr(actor, "tags", None),
    ):
        values = _extract_alignment_values(source)
        if values:
            choice = values[0]
            try:
                setattr(actor, "divine_lance_alignment", choice)
            except Exception:
                pass
            return choice

    choice = _prompt_choice(
        ctx,
        "Divine Lance - wybierz aspekt bostwa",
        ["good", "evil", "lawful", "chaotic"],
        source="divine_lance",
    )
    choice_norm = str(choice or "").strip().lower()
    if choice_norm not in ALIGNMENT_KEYS:
        choice_norm = "good"
    try:
        setattr(actor, "divine_lance_alignment", choice_norm)
    except Exception:
        pass
    return choice_norm


@register_event
class ChillTouchEvent(MagicEvent):
    name = "chill_touch"
    actions_cost = 2
    range_feet = 5
    default_tags = ["magic", "spell"]
    spell_tags = ["cantrip", "occult", "arcane", "divine", "necromancy", "touch"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA, SpellTradition.DIVINE)
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

        spell_dc = _spell_dc_for_actor(actor)
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
    spell_tags = ["cantrip", "occult", "arcane", "primal", "evocation"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA, SpellTradition.PRIMAL)
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
    spell_tags = ["cantrip", "occult", "arcane", "divine", "enchantment"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA, SpellTradition.DIVINE)
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

        spell_dc = _spell_dc_for_actor(actor)
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
    spell_tags = ["cantrip", "occult", "divine", "abjuration"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.DIVINE)
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
    spell_tags = ["cantrip", "occult", "divine", "primal", "divination"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.DIVINE, SpellTradition.PRIMAL)
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
    spell_tags = ["cantrip", "occult", "arcane", "divine", "primal", "evocation"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA, SpellTradition.DIVINE, SpellTradition.PRIMAL)
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
    spell_tags = ["cantrip", "occult", "arcane", "evocation"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA)
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
    spell_tags = ["cantrip", "occult", "arcane", "divine", "illusion"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA, SpellTradition.DIVINE)
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
    spell_tags = ["cantrip", "occult", "arcane", "divine", "primal", "evocation"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA, SpellTradition.DIVINE, SpellTradition.PRIMAL)
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
    spell_tags = ["cantrip", "occult", "arcane", "divine", "primal", "divination"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA, SpellTradition.DIVINE, SpellTradition.PRIMAL)
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
    spell_tags = ["cantrip", "occult", "arcane", "divine", "abjuration"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA, SpellTradition.DIVINE)
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
    spell_tags = ["cantrip", "occult", "arcane", "evocation"]
    magic_traditions = (SpellTradition.OCCULT, SpellTradition.ARCANA)
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
        damage += int(inspire_courage_damage_bonus(ctx.actor) or 0)
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


@register_event
class AcidSplashEvent(BaseMagicAttackEvent):
    name = "acidsplash"
    actions_cost = 2
    range_feet = 30
    default_tags = ["magic", "spell", "attack_ranged"]
    spell_tags = ["acid", "cantrip", "arcane", "primal", "evocation"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL)
    magic_types = ["evocation"]
    prompt = "Acid Splash - wystrzel bryzg kwasu w zasiegu 30 stop."

    def _resolve_on_target(self, target, pos, ctx: EventContext, *, critical: bool = False) -> EventResult:
        spell_rank = _auto_cantrip_rank(ctx.actor)
        dmg = self._prompt_damage()
        dmg += int(inspire_courage_damage_bonus(ctx.actor) or 0)
        defeated = _apply_damage(target, dmg, DamageType.ACID.value)

        persistent_value = None
        if critical:
            persistent_value = self._prompt_persistent(ctx.actor, DamageType.ACID.value, spell_rank=spell_rank)
            if persistent_value and persistent_value > 0:
                try:
                    target.add_status(make_persistent_damage(persistent_value, DamageType.ACID.value, source=self.name))
                except Exception as exc:
                    logger.debug("Nie udalo sie dodac persistent acid: %s", exc)

        message = f"Acid Splash trafia za {dmg} acid."
        if critical:
            message = f"Acid Splash - krytyk! {dmg} acid."
            if persistent_value:
                message += f" Persistent acid {persistent_value}."
        if defeated:
            message += " Cel pokonany."

        return EventResult(
            success=True,
            consumed_action=self.consumes_action,
            message=message,
            data={
                "critical": critical,
                "damage": dmg,
                "damage_type": DamageType.ACID.value,
                "persistent_damage": persistent_value,
            },
        )

    def _prompt_damage(self) -> int:
        from ui_client import get_ui_client

        ui = get_ui_client()
        val = ui.prompt_roll(
            "Acid Splash - podaj obrazenia kwasowe:",
            source="game",
            layout="damage",
            answer_placeholder="Obrazenia kwasowe",
        )
        return int(val or 0)

    def _prompt_persistent(self, actor, damage_type: str, *, spell_rank: int | None = None) -> int:
        from ui_client import get_ui_client

        ui = get_ui_client()
        note = burn_it_prompt_note(
            actor,
            damage_type,
            persistent=True,
            source_kind="spell",
            spell_rank=spell_rank,
        )
        val = ui.prompt_roll(
            "Krytyk! Podaj wartosc persistent acid:",
            source="game",
            layout="damage",
            answer_placeholder="Persistent acid",
            prompt_long=note,
        )
        bonus = burn_it_bonus(
            actor,
            damage_type,
            persistent=True,
            source_kind="spell",
            spell_rank=spell_rank,
        )
        return int(val or 0) + int(bonus)


@register_event
class AcidSplashAliasEvent(AcidSplashEvent):
    name = "acid_splash"


@register_event
class DetectMagicEvent(MagicEvent):
    name = "detect_magic"
    default_tags = ["cast", "magic", "detect"]
    actions_cost = 2
    magic_traditions = (
        SpellTradition.ARCANA,
        SpellTradition.DIVINE,
        SpellTradition.OCCULT,
        SpellTradition.PRIMAL,
    )
    spell_tags = ["cantrip", "arcane", "divine", "occult", "primal", "divination", "detect"]
    magic_types = ["divination"]
    prompt = "Detect Magic - wyczuj magiczne aury w poblizu."

    def execute(self, ctx: EventContext) -> EventResult:
        hero = ctx.actor or self._choose_hero(ctx)
        if hero is None or getattr(hero, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        board = ctx.game.board
        hero_pos = hero.position
        rooms_here = board.rooms_at(hero_pos) if hero_pos else set()
        in_room = _iter_room_objects(ctx, rooms_here) if rooms_here else []

        magical_in_room: list[tuple[object, tuple[int, int]]] = [(obj, pos) for (obj, pos) in in_room if _is_magical(obj)]

        detect_range_feet = _level_range(hero) * 5
        in_range: list[tuple[object, tuple[int, int]]] = []
        out_of_range_count = 0
        newly_revealed: list[object] = []

        for obj, pos in magical_in_room:
            if hero_pos is None or pos is None:
                out_of_range_count += 1
                continue
            if grid_distance_feet(hero_pos, pos) <= detect_range_feet:
                in_range.append((obj, pos))
                if getattr(obj, "hidden", False) and not getattr(obj, "revealed", False):
                    try:
                        obj.revealed = True
                        newly_revealed.append(obj)
                    except Exception:
                        pass
            else:
                out_of_range_count += 1

        highlight_positions = [
            pos
            for obj, pos in in_range
            if isinstance(obj, MagicalMixin)
            or hasattr(obj, "magical_description")
            or getattr(obj, "magical", False)
        ]

        if highlight_positions:
            try:
                ctx.game.conn.set_leds(highlight_positions, [consts.MAGIC_DETECT_RGB] * len(highlight_positions))
            except Exception:
                pass

        lines: list[str] = []
        if magical_in_room:
            lines.append("Wyczuwasz magię w pomieszczeniu.")
            lines.append(f"Zasięg wykrywania: {detect_range_feet} stóp.")
            if in_range:
                lines.append("Zlokalizowane aury:")
                for obj, _pos in in_range:
                    lines.append(f"- {_magical_description(obj)}")
            if out_of_range_count:
                lines.append(f"Poza zasięgiem wyczuwasz jeszcze {out_of_range_count} magicznych aur.")
        else:
            lines.append("Nie wyczuwasz magii w tym pomieszczeniu.")

        if newly_revealed:
            lines.append("Odkryto ukryte magiczne obiekty w zasięgu.")

        info_text = "\n".join(lines)
        try:
            ui = getattr(ctx.game, "ui", None)
            if ui and getattr(ui, "prompt_info", None):
                ui.prompt_info("Detect Magic", prompt_long=info_text, source="detect_magic")
            else:
                ctx.game.ui_log(info_text)
        except Exception:
            pass

        try:
            in_combat = getattr(ctx.game, "state", None).__class__.__name__ == "Combat"
        except Exception:
            in_combat = False
        if in_combat:
            has_status = getattr(hero, "has_status", None)
            if callable(has_status) and has_status("recognize_spell"):
                try:
                    add_bonus = getattr(hero, "add_bonus", None)
                    if callable(add_bonus):
                        add_bonus(
                            BonusEffect(
                                type=BonusType.CIRCUMSTANCE,
                                value=1,
                                tag="ac_magic",
                                source="status:recognize_spell",
                                label="recognize spell +1",
                                duration_turns=1,
                            )
                        )
                        ctx.game.ui_log("Recognize Spell: +1 AC vs magic attacks (1 tura).")
                except Exception:
                    pass

        try:
            ctx.game.conn.scan_board(None)
        except Exception:
            pass
        finally:
            try:
                ctx.game.conn.leds_off()
            except Exception:
                pass

        return EventResult(success=True, consumed_action=self.consumes_action, message="Detect Magic zakończone.")

    def _choose_hero(self, ctx: EventContext):
        heroes_positions = [h.position for h in getattr(ctx.game, "heroes", []) if getattr(h, "position", None) is not None]
        if not heroes_positions:
            logger.info("Brak bohaterów na planszy.")
            return None
        ctx.game.conn.set_leds(heroes_positions, consts.HERO_HIGHLIGHT_RGB)
        try:
            pos = ctx.game.conn.scan_board(heroes_positions)
        finally:
            try:
                ctx.game.conn.leds_off()
            except Exception:
                pass
        return ctx.game.board.occupant_at(pos)


@register_event
class DetectMagicAliasEvent(DetectMagicEvent):
    name = "detectmagic"


@register_event
class DisruptUndeadEvent(MagicEvent):
    name = "disrupt_undead"
    actions_cost = 2
    default_tags = ["magic", "spell"]
    spell_tags = ["cantrip", "divine", "primal", "necromancy", "positive"]
    magic_traditions = (SpellTradition.DIVINE, SpellTradition.PRIMAL)
    magic_types = ["necromancy"]
    range_feet = 30
    prompt = "Disrupt Undead - positive damage tylko przeciw undead."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        candidates = [item for item in _iter_enemy_candidates(ctx.game) if _is_undead_target(item[0])]
        if not candidates:
            return EventResult.cancelled(message="Brak undead w zasiegu.")

        target, target_pos = pick_target_in_range(
            ctx,
            actor.position,
            candidates,
            max_range_feet=self.range_feet,
            allowed_kinds=("enemy",),
            tags=self._effective_tags(ctx),
        )
        if target is None or target_pos is None:
            return EventResult.cancelled(message="Nie wybrano undead.")

        spell_dc = _spell_dc_for_actor(actor)
        base_damage = int(
            prompt_for_roll(
                "Disrupt Undead - podaj obrazenia positive:",
                layout="damage",
                answer_placeholder="Obrazenia",
            )
            or 0
        )

        outcome, roll, total = _roll_enemy_save(
            target,
            Skill.FORTITUDE.value,
            spell_dc,
            attacker=actor,
            tags=["save", Skill.FORTITUDE.value, "magic", "positive"],
        )
        damage = _basic_save_damage(base_damage, outcome)
        defeated = _apply_damage(target, damage, DamageType.POSITIVE.value)

        try:
            ctx.game.ui_log(
                f"Disrupt Undead: Fort save k20={roll}, suma={total} vs DC {spell_dc}: {outcome}. "
                f"Obrazenia: {damage}."
            )
        except Exception:
            pass

        msg = f"Disrupt Undead: {outcome}, obrazenia {damage} positive."
        if defeated:
            msg += " Cel pokonany."
        return EventResult(success=True, consumed_action=self.consumes_action, message=msg)


@register_event
class DivineLanceEvent(BaseMagicAttackEvent):
    name = "divine_lance"
    actions_cost = 2
    range_feet = 30
    default_tags = ["magic", "spell", "attack_ranged"]
    spell_tags = ["cantrip", "divine", "evocation", "alignment"]
    magic_traditions = (SpellTradition.DIVINE,)
    magic_types = ["evocation"]
    prompt = "Divine Lance - alignment damage zalezne od bostwa."

    def _resolve_on_target(self, target, pos, ctx: EventContext, *, critical: bool = False) -> EventResult:
        actor = ctx.actor
        damage_alignment = _resolve_divine_lance_alignment(ctx, actor)
        if not _is_opposed_alignment(target, damage_alignment):
            return EventResult(
                success=True,
                consumed_action=self.consumes_action,
                message=f"Divine Lance trafia, ale cel nie ma przeciwnej aury ({damage_alignment}).",
            )

        damage = int(
            prompt_for_roll(
                "Divine Lance - podaj obrazenia:",
                layout="damage",
                answer_placeholder="Obrazenia",
            )
            or 0
        )
        damage += int(inspire_courage_damage_bonus(actor) or 0)
        if critical:
            damage *= 2

        defeated = _apply_damage(target, damage, damage_alignment)
        msg = f"Divine Lance trafia za {damage} {damage_alignment}."
        if critical:
            msg = f"Divine Lance - krytyk! {damage} {damage_alignment}."
        if defeated:
            msg += " Cel pokonany."
        return EventResult(success=True, consumed_action=self.consumes_action, message=msg)


@register_event
class KnowDirectionEvent(MagicEvent):
    name = "know_direction"
    actions_cost = 1
    default_tags = ["magic", "spell", "utility"]
    spell_tags = ["cantrip", "divine", "primal", "divination"]
    magic_traditions = (SpellTradition.DIVINE, SpellTradition.PRIMAL)
    magic_types = ["divination"]
    prompt = "Know Direction - wyznacza prawdziwa polnoc."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        x, y = actor.position
        north_pos = (x, y - 1)
        in_bounds = True
        try:
            in_bounds = bool(ctx.game.board.in_bounds(north_pos))
        except Exception:
            pass

        if in_bounds:
            text = f"Know Direction: polnoc jest w kierunku pola {north_pos}."
        else:
            text = "Know Direction: polnoc jest powyzej aktualnej pozycji."
        try:
            ctx.game.ui_log(text)
        except Exception:
            pass
        return EventResult(
            success=True,
            consumed_action=self.consumes_action,
            message="Know Direction zakonczone.",
            data={"north_vector": (0, -1)},
        )


@register_event
class StabilizeEvent(MagicEvent):
    name = "stabilize"
    actions_cost = 2
    default_tags = ["magic", "spell", "healing"]
    spell_tags = ["cantrip", "divine", "primal", "necromancy"]
    magic_traditions = (SpellTradition.DIVINE, SpellTradition.PRIMAL)
    magic_types = ["necromancy"]
    range_feet = 30
    prompt = "Stabilize - stabilizuje dying creature."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        candidates = list(_iter_hero_candidates(ctx.game)) + list(_iter_enemy_candidates(ctx.game))
        target, target_pos = pick_target_in_range(
            ctx,
            actor.position,
            candidates,
            max_range_feet=self.range_feet,
            allowed_kinds=("hero", "enemy"),
            tags=self._effective_tags(ctx),
        )
        if target is None or target_pos is None:
            return EventResult.cancelled(message="Brak celu dla Stabilize.")

        try:
            from statuses import dying_value, lose_dying

            before = int(dying_value(target) or 0)
            if before > 0:
                lose_dying(target, source=self.name, keep_unconscious=True)
                msg = f"Stabilize: usunieto dying {before}, cel jest stable i wounded."
            else:
                msg = "Stabilize: brak statusu dying - efekt UI-only."
        except Exception:
            msg = "Stabilize: brak statusu dying - efekt UI-only."
        try:
            ctx.game.ui_log(msg)
        except Exception:
            pass
        return EventResult(success=True, consumed_action=self.consumes_action, message=msg)


@register_event
class ElectricArcEvent(MagicEvent):
    name = "electric_arc"
    actions_cost = 2
    default_tags = ["magic", "spell"]
    spell_tags = ["cantrip", "arcane", "primal", "evocation", "electric"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL)
    magic_types = ["evocation"]
    range_feet = 30
    prompt = "Electric Arc - 1 lub 2 cele, Reflex save na kazdy cel."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        candidates = list(_iter_enemy_candidates(ctx.game))
        first, first_pos = pick_target_in_range(
            ctx,
            actor.position,
            candidates,
            max_range_feet=self.range_feet,
            allowed_kinds=("enemy",),
            tags=self._effective_tags(ctx),
        )
        if first is None or first_pos is None:
            return EventResult.cancelled(message="Brak celu w zasiegu.")

        targets: list[tuple[object, tuple[int, int]]] = [(first, first_pos)]
        second_choice = _prompt_choice(
            ctx,
            "Electric Arc - drugi cel?",
            ["Nie", "Tak"],
            source=self.name,
        )
        if str(second_choice or "").strip().lower() == "tak":
            second_candidates: list[tuple[object, tuple[int, int], str]] = []
            for cand, cand_pos, kind in candidates:
                if cand is first or cand_pos is None:
                    continue
                if grid_distance_feet(first_pos, cand_pos) <= self.range_feet:
                    second_candidates.append((cand, cand_pos, kind))
            if second_candidates:
                second, second_pos = pick_target_in_range(
                    ctx,
                    first_pos,
                    second_candidates,
                    max_range_feet=self.range_feet,
                    allowed_kinds=("enemy",),
                    tags=self._effective_tags(ctx),
                )
                if second is not None and second_pos is not None:
                    targets.append((second, second_pos))

        spell_dc = _spell_dc_for_actor(actor)
        base_damage = int(
            prompt_for_roll(
                "Electric Arc - podaj obrazenia electric:",
                layout="damage",
                answer_placeholder="Obrazenia",
            )
            or 0
        )

        messages: list[str] = []
        for target, _pos in targets:
            outcome, roll, total = _roll_enemy_save(
                target,
                Skill.REFLEX.value,
                spell_dc,
                attacker=actor,
                tags=["save", Skill.REFLEX.value, "magic", "electric"],
            )
            damage = _basic_save_damage(base_damage, outcome)
            defeated = _apply_damage(target, damage, DamageType.ELECTRIC.value)
            name = getattr(target, "name", "cel")
            messages.append(f"{name}: {outcome}, {damage} electric")
            try:
                ctx.game.ui_log(
                    f"Electric Arc [{name}]: Reflex save k20={roll}, suma={total} vs DC {spell_dc}: {outcome}. "
                    f"Obrazenia: {damage}."
                )
            except Exception:
                pass
            if defeated:
                messages[-1] += ", cel pokonany"

        return EventResult(success=True, consumed_action=self.consumes_action, message="Electric Arc: " + "; ".join(messages) + ".")


@register_event
class GhostSoundEvent(MagicEvent):
    name = "ghost_sound"
    actions_cost = 2
    default_tags = ["magic", "spell", "illusion", "auditory"]
    spell_tags = ["cantrip", "arcane", "illusion"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.OCCULT, SpellTradition.PRIMAL)
    magic_types = ["illusion"]
    range_feet = 30
    prompt = "Ghost Sound - wybierz pole i typ falszywego dzwieku."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        pos = pick_position_in_range(ctx, actor.position, max_range_feet=self.range_feet, color=[90, 90, 220])
        if pos is None:
            return EventResult.cancelled(message="Nie wybrano pola dla Ghost Sound.")

        sound = _prompt_choice(
            ctx,
            "Ghost Sound - wybierz dzwiek",
            ["szept", "kroki", "krzyk", "stukot"],
            source=self.name,
        )
        sound = sound or "dziwny dzwiek"

        state = getattr(ctx.game, "_arcane_runtime", None)
        if not isinstance(state, dict):
            state = {}
            try:
                ctx.game._arcane_runtime = state
            except Exception:
                pass
        sounds = state.setdefault("ghost_sounds", [])
        sounds.append({"pos": pos, "sound": sound, "source_id": _actor_id(actor)})

        try:
            ctx.game.ui_log(f"Ghost Sound: '{sound}' na polu {pos}.")
        except Exception:
            pass
        return EventResult(success=True, consumed_action=self.consumes_action, message=f"Ghost Sound aktywne na {pos}.")


@register_event
class ProduceFlameEvent(BaseMagicAttackEvent):
    name = "produce_flame"
    actions_cost = 2
    range_feet = 30
    default_tags = ["magic", "spell", "attack_ranged"]
    spell_tags = ["cantrip", "arcane", "primal", "evocation", "fire"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL)
    magic_types = ["evocation"]
    prompt = "Produce Flame - atak ogniem (melee lub ranged)."

    def execute(self, ctx: EventContext) -> EventResult:
        mode = _prompt_choice(ctx, "Produce Flame - wybierz tryb ataku", ["ranged", "melee"], source=self.name) or "ranged"
        current_range = self.range_feet
        try:
            self.range_feet = 5 if str(mode).strip().lower() == "melee" else 30
            return super().execute(ctx)
        finally:
            self.range_feet = current_range

    def _resolve_on_target(self, target, pos, ctx: EventContext, *, critical: bool = False) -> EventResult:
        spell_rank = _auto_cantrip_rank(ctx.actor)
        damage = int(
            prompt_for_roll(
                "Produce Flame - podaj obrazenia fire:",
                layout="damage",
                answer_placeholder="Obrazenia",
            )
            or 0
        )
        damage += int(inspire_courage_damage_bonus(ctx.actor) or 0)
        damage += int(
            burn_it_bonus(
                ctx.actor,
                DamageType.FIRE.value,
                persistent=False,
                source_kind="spell",
                spell_rank=spell_rank,
            )
            or 0
        )
        if critical:
            damage *= 2

        defeated = _apply_damage(target, damage, DamageType.FIRE.value)
        persistent = None
        if critical:
            persistent = self._prompt_persistent(ctx.actor, spell_rank=spell_rank)
            if persistent and persistent > 0:
                try:
                    target.add_status(make_persistent_damage(persistent, DamageType.FIRE.value, source=self.name))
                except Exception:
                    pass

        msg = f"Produce Flame trafia za {damage} fire."
        if critical:
            msg = f"Produce Flame - krytyk! {damage} fire."
            if persistent:
                msg += f" Persistent fire {persistent}."
        if defeated:
            msg += " Cel pokonany."
        return EventResult(success=True, consumed_action=self.consumes_action, message=msg)

    def _prompt_persistent(self, actor, *, spell_rank: int | None = None) -> int:
        note = burn_it_prompt_note(
            actor,
            DamageType.FIRE.value,
            persistent=True,
            source_kind="spell",
            spell_rank=spell_rank,
        )
        val = int(
            prompt_for_roll(
                "Produce Flame - podaj persistent fire na krytyku:",
                layout="damage",
                answer_placeholder="Persistent fire",
                prompt_long=note,
            )
            or 0
        )
        return val + int(
            burn_it_bonus(
                actor,
                DamageType.FIRE.value,
                persistent=True,
                source_kind="spell",
                spell_rank=spell_rank,
            )
            or 0
        )


@register_event
class RayOfFrostEvent(BaseMagicAttackEvent):
    name = "ray_of_frost"
    actions_cost = 2
    range_feet = 120
    default_tags = ["magic", "spell", "attack_ranged"]
    spell_tags = ["cantrip", "arcane", "primal", "evocation", "cold"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL)
    magic_types = ["evocation"]
    prompt = "Ray of Frost - atak zimnem; krytyk spowalnia cel."

    def _resolve_on_target(self, target, pos, ctx: EventContext, *, critical: bool = False) -> EventResult:
        damage = int(
            prompt_for_roll(
                "Ray of Frost - podaj obrazenia cold:",
                layout="damage",
                answer_placeholder="Obrazenia",
            )
            or 0
        )
        damage += int(inspire_courage_damage_bonus(ctx.actor) or 0)
        if critical:
            damage *= 2
        defeated = _apply_damage(target, damage, DamageType.COLD.value)

        slowed = False
        if critical:
            if target in getattr(ctx.game, "heroes", []):
                try:
                    from ui_client import get_ui_client

                    get_ui_client().prompt_info(
                        "Ray of Frost",
                        prompt_long="Krytyk: kara do szybkosci -10 stop na 1 ture (zapisz recznie).",
                        source=self.name,
                    )
                    slowed = True
                except Exception:
                    pass
            else:
                try:
                    target.add_status(
                        SpeedPenaltyStatus(
                            penalty_feet=10,
                            source=self.name,
                            source_id=_actor_id(ctx.actor),
                            source_turns_left=1,
                            label="ray of frost -10ft",
                        )
                    )
                    slowed = True
                except Exception:
                    pass

        msg = f"Ray of Frost trafia za {damage} cold."
        if critical:
            msg = f"Ray of Frost - krytyk! {damage} cold."
            if slowed:
                msg += " Cel ma -10ft speed."
        if defeated:
            msg += " Cel pokonany."
        return EventResult(success=True, consumed_action=self.consumes_action, message=msg)


@register_event
class SigilEvent(MagicEvent):
    name = "sigil"
    actions_cost = 2
    default_tags = ["magic", "spell", "transmutation"]
    spell_tags = ["cantrip", "arcane", "occult", "divine", "primal", "transmutation"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.OCCULT, SpellTradition.DIVINE, SpellTradition.PRIMAL)
    magic_types = ["transmutation"]
    range_feet = 30
    prompt = "Sigil - oznacz obiekt lub stworzenie magicznym znakiem."

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        candidates = list(_iter_enemy_candidates(ctx.game)) + list(_iter_hero_candidates(ctx.game)) + list(
            _iter_interactable_candidates(ctx.game, include_npc=False)
        )
        target, target_pos = pick_target_in_range(
            ctx,
            actor.position,
            candidates,
            max_range_feet=self.range_feet,
            allowed_kinds=("enemy", "hero", "interactable"),
            tags=self._effective_tags(ctx),
        )
        if target is None or target_pos is None:
            return EventResult.cancelled(message="Brak celu dla Sigil.")

        mark = _prompt_choice(
            ctx,
            "Sigil - wybierz typ znaku",
            ["runa", "pieczec", "znak"],
            source=self.name,
        )
        mark = mark or "runa"

        sigils = list(getattr(target, "sigils", []) or [])
        sigils.append({"mark": mark, "source_id": _actor_id(actor)})
        try:
            setattr(target, "sigils", sigils)
        except Exception:
            pass

        try:
            ctx.game.ui_log(f"Sigil: {getattr(target, 'name', 'cel')} otrzymuje znak '{mark}'.")
        except Exception:
            pass
        return EventResult(success=True, consumed_action=self.consumes_action, message=f"Sigil nalozony ({mark}).")


@register_event
class TanglefootEvent(BaseMagicAttackEvent):
    name = "tanglefoot"
    actions_cost = 2
    range_feet = 30
    default_tags = ["magic", "spell", "attack_ranged"]
    spell_tags = ["cantrip", "arcane", "primal", "conjuration"]
    magic_traditions = (SpellTradition.ARCANA, SpellTradition.PRIMAL)
    magic_types = ["conjuration"]
    prompt = "Tanglefoot - trafiony cel traci szybkosc, krytyk unieruchamia."

    def _resolve_on_target(self, target, pos, ctx: EventContext, *, critical: bool = False) -> EventResult:
        penalty = 10
        source_id = _actor_id(ctx.actor)
        applied_penalty = False
        applied_immobilized = False

        if target in getattr(ctx.game, "heroes", []):
            try:
                from ui_client import get_ui_client

                extra = " Krytyk: immobilized 1." if critical else ""
                get_ui_client().prompt_info(
                    "Tanglefoot",
                    prompt_long=f"Otrzymujesz kare do szybkosci -{penalty} stop na 1 ture.{extra} Zapisz recznie.",
                    source=self.name,
                )
                applied_penalty = True
                applied_immobilized = critical
            except Exception:
                pass
        else:
            try:
                target.add_status(
                    SpeedPenaltyStatus(
                        penalty_feet=penalty,
                        source=self.name,
                        source_id=source_id,
                        source_turns_left=1,
                        label=f"tanglefoot -{penalty}ft",
                    )
                )
                applied_penalty = True
            except Exception:
                pass
            if critical:
                try:
                    target.add_status(
                        ImmobilizedStatus(
                            source=self.name,
                            source_id=source_id,
                            source_turns_left=1,
                        )
                    )
                    applied_immobilized = True
                except Exception:
                    pass

        msg = "Tanglefoot trafia."
        if applied_penalty:
            msg += f" Cel ma -{penalty}ft speed."
        if critical and applied_immobilized:
            msg += " Cel immobilized 1."
        return EventResult(success=True, consumed_action=self.consumes_action, message=msg)
