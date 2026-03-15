from __future__ import annotations

from combat import effective_ac
from combat.damage_utils import burn_it_bonus, burn_it_prompt_note
from combat.degree_of_success import is_critical_success, is_hit, natural_shift_from_roll, resolve_outcome
from combat.hp_engine import apply_damage as hp_apply_damage
from bonuses import BonusEffect, BonusType
from statuses import ClumsyStatus, EnfeebledStatus, Status
from GameObjects.interactions_mixin import prompt_for_roll

from ....base import EventContext, EventResult
from ....registry import register_event
from ...focus_utils import focus_spell_rank
from ...magic_event import MagicEvent
from ...magic_utils import pick_target_in_range
from ...spell_types import SpellTradition


def _normalize(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _is_sorcerer(actor) -> bool:
    if actor is None:
        return False
    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            if bool(checker("sorcerer")):
                return True
        except Exception:
            pass
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) == "sorcerer":
            return True
    return _normalize(getattr(actor, "class_name", "")) == "sorcerer"


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


def _sorcerer_setup(actor) -> dict:
    if actor is None:
        return {}
    getter = getattr(actor, "get_status_data", None)
    if callable(getter):
        try:
            setup = getter("sorcerer", "sorcerer_setup", {})
            if isinstance(setup, dict):
                return dict(setup)
        except Exception:
            pass
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) != "sorcerer":
            continue
        data = getattr(status, "data", None) or {}
        setup = data.get("sorcerer_setup")
        if isinstance(setup, dict):
            return dict(setup)
    return {}


def _known_focus_spells(actor) -> set[str]:
    known: set[str] = set()
    setup = _sorcerer_setup(actor)
    spell = _normalize(setup.get("bloodline_initial_focus_spell") or setup.get("sorcerer_bloodline_initial_focus_spell"))
    if spell:
        known.add(spell)
    for source in (
        getattr(actor, "sorcerer_focus_spells", None),
        setup.get("sorcerer_focus_spells"),
        setup.get("focus_spells"),
    ):
        if isinstance(source, list):
            for item in source:
                normalized = _normalize(item)
                if normalized:
                    known.add(normalized)
    return known


def _knows_focus_spell(actor, spell_id: str) -> bool:
    return _normalize(spell_id) in _known_focus_spells(actor)


def _iter_enemy_candidates(game):
    for enemy in getattr(game, "enemies", []) or []:
        yield enemy, getattr(enemy, "position", None), "enemy"


def _iter_any_targets(game):
    for hero in getattr(game, "heroes", []) or []:
        yield hero, getattr(hero, "position", None), "hero"
    for enemy in getattr(game, "enemies", []) or []:
        yield enemy, getattr(enemy, "position", None), "enemy"


def _pick_target(ctx: EventContext, actor, *, range_feet: int, kinds: tuple[str, ...]):
    source_pos = getattr(actor, "position", None)
    if source_pos is None:
        return None, None
    if kinds == ("enemy",):
        candidates = list(_iter_enemy_candidates(ctx.game))
    else:
        candidates = list(_iter_any_targets(ctx.game))
    return pick_target_in_range(
        ctx,
        source_pos,
        candidates,
        max_range_feet=range_feet,
        allowed_kinds=kinds,
        tags=["magic", "focus", "sorcerer"],
    )


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


def _add_bonus(actor, effect: BonusEffect) -> None:
    adder = getattr(actor, "add_bonus", None)
    if callable(adder):
        try:
            adder(effect)
            return
        except Exception:
            pass
    bonuses = getattr(actor, "bonuses", None)
    if isinstance(bonuses, list):
        bonuses.append(effect)


class SorcererFocusSpellEvent(MagicEvent):
    actions_cost = 1
    default_tags = ["magic", "spell", "focus", "sorcerer"]
    spell_tags = ["focus", "sorcerer"]
    magic_types = ["focus"]
    magic_traditions = (
        SpellTradition.ARCANA,
        SpellTradition.DIVINE,
        SpellTradition.OCCULT,
        SpellTradition.PRIMAL,
    )
    required_focus_spell_id: str = ""

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message=f"{self.name}: missing actor.")
        if not _is_sorcerer(actor):
            return EventResult.cancelled(message=f"{self.name}: tylko Sorcerer moze rzucic ten focus spell.")
        if self.required_focus_spell_id and not _knows_focus_spell(actor, self.required_focus_spell_id):
            return EventResult.cancelled(message=f"{self.name}: focus spell nie jest znany.")

        points = _focus_points(actor)
        if points <= 0:
            return EventResult.cancelled(message=f"{self.name}: brak Focus Point.")

        result = self._execute_effect(ctx)
        if not result.success:
            return result

        _set_focus_points(actor, points - 1)
        result.message = f"{result.message or f'{self.name}: effect applied.'} Focus Point: {_focus_points(actor)}."
        return result

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        raise NotImplementedError


@register_event
class AncestralMemoriesEvent(SorcererFocusSpellEvent):
    name = "ancestral_memories"
    required_focus_spell_id = "ancestral_memories"
    spell_tags = SorcererFocusSpellEvent.spell_tags + ["divination", "occult", "arcane"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        rank = max(1, int(focus_spell_rank(actor, minimum=1) or 1))
        bonus = 4 if rank >= 6 else 2
        skills = [
            "athletics",
            "acrobatics",
            "arcana",
            "crafting",
            "deception",
            "diplomacy",
            "intimidation",
            "medicine",
            "nature",
            "occultism",
            "performance",
            "religion",
            "society",
            "stealth",
            "survival",
            "thievery",
        ]
        chosen = _prompt_choice(
            ctx,
            "Ancestral Memories: wybierz skill",
            choices=skills,
            source=self.name,
        ) or "arcana"
        chosen = _normalize(chosen) or "arcana"
        _add_bonus(
            actor,
            BonusEffect(
                type=BonusType.STATUS,
                value=bonus,
                tag=chosen,
                source=self.name,
                label="ancestral memories",
                duration_turns=10,
            ),
        )
        return EventResult(success=True, consumed_action=True, message=f"Ancestral Memories: +{bonus} do {chosen} na 1 minute.")


@register_event
class AngelicHaloEvent(SorcererFocusSpellEvent):
    name = "angelic_halo"
    required_focus_spell_id = "angelic_halo"
    spell_tags = SorcererFocusSpellEvent.spell_tags + ["abjuration", "divine", "aura"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        adder = getattr(actor, "add_status", None)
        if callable(adder):
            try:
                adder(
                    Status(
                        id="angelic_halo_active",
                        label="Angelic Halo",
                        duration=10,
                        source=self.name,
                        data={"halo_radius_feet": 15, "heal_bonus_per_spell_level": 2},
                    )
                )
            except Exception:
                pass
        return EventResult(
            success=True,
            consumed_action=True,
            message="Angelic Halo aktywne 1 minute (heal w aurze: +2 HP per poziom Heal; rozliczane ręcznie).",
        )


@register_event
class DiabolicEdictEvent(SorcererFocusSpellEvent):
    name = "diabolic_edict"
    required_focus_spell_id = "diabolic_edict"
    range_feet = 30
    spell_tags = SorcererFocusSpellEvent.spell_tags + ["enchantment", "divine"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        target, _target_pos = _pick_target(ctx, actor, range_feet=30, kinds=("hero", "enemy"))
        if target is None:
            return EventResult.cancelled(message="Diabolic Edict: brak celu w zasiegu.")
        obeys = _prompt_choice(
            ctx,
            "Diabolic Edict: czy cel wykonuje zadanie?",
            choices=["tak", "nie"],
            source=self.name,
        )
        is_penalty = _normalize(obeys) not in {"tak", "t", "yes", "y", "1"}
        for tag in (
            "attack_melee",
            "attack_ranged",
            "magic",
            "athletics",
            "acrobatics",
            "arcana",
            "deception",
            "diplomacy",
            "intimidation",
            "occultism",
            "performance",
            "religion",
            "society",
            "stealth",
            "survival",
            "thievery",
        ):
            _add_bonus(
                target,
                BonusEffect(
                    type=BonusType.STATUS,
                    value=1,
                    tag=tag,
                    source=self.name,
                    label="diabolic edict",
                    is_penalty=is_penalty,
                    duration_turns=1,
                ),
            )
        if is_penalty:
            msg = "Diabolic Edict: cel odmawia i otrzymuje -1 status do atakow/skill checks na 1 runde."
        else:
            msg = "Diabolic Edict: cel zyskuje +1 status do atakow/skill checks zwiazanych z zadaniem (uogolnienie) na 1 runde."
        return EventResult(success=True, consumed_action=True, message=msg)


@register_event
class DragonClawsEvent(SorcererFocusSpellEvent):
    name = "dragon_claws"
    required_focus_spell_id = "dragon_claws"
    spell_tags = SorcererFocusSpellEvent.spell_tags + ["transmutation", "morph", "arcane"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        setup = _sorcerer_setup(actor)
        rank = max(1, int(focus_spell_rank(actor, minimum=1) or 1))
        if rank >= 9:
            extra = "3d6"
            resistance = 15
        elif rank >= 5:
            extra = "2d6"
            resistance = 10
        else:
            extra = "1d6"
            resistance = 5
        damage_type = _normalize(setup.get("dragon_damage_type") or setup.get("sorcerer_dragon_damage_type") or "fire")
        adder = getattr(actor, "add_status", None)
        if callable(adder):
            try:
                adder(
                    Status(
                        id="dragon_claws_active",
                        label="Dragon Claws",
                        duration=10,
                        source=self.name,
                        data={
                            "dragon_claws_damage_die": "1d4",
                            "dragon_claws_extra_damage": extra,
                            "dragon_claws_damage_type": damage_type,
                            "dragon_claws_resistance": resistance,
                        },
                    )
                )
            except Exception:
                pass
        return EventResult(
            success=True,
            consumed_action=True,
            message=(
                "Dragon Claws aktywne na 1 minute: unarmed claws 1d4 + "
                f"{extra} {damage_type}, resistance {resistance} {damage_type} "
                "(atak i resistance rozliczane wg statusu)."
            ),
        )


@register_event
class ElementalTossEvent(SorcererFocusSpellEvent):
    name = "elemental_toss"
    required_focus_spell_id = "elemental_toss"
    range_feet = 30
    spell_tags = SorcererFocusSpellEvent.spell_tags + ["evocation", "attack", "primal"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        target, _target_pos = _pick_target(ctx, actor, range_feet=30, kinds=("enemy",))
        if target is None:
            return EventResult.cancelled(message="Elemental Toss: brak celu.")

        target_ac = int(getattr(target, "ac", effective_ac(target)) or 10)
        roll = int(
            prompt_for_roll(
                f"Elemental Toss: atak przeciw AC {target_ac}",
                layout="test",
                answer_placeholder="Wynik k20",
            )
            or 0
        )
        outcome = resolve_outcome(roll, target_ac, natural_shift=natural_shift_from_roll(roll))
        if not is_hit(outcome):
            return EventResult(success=True, consumed_action=True, message="Elemental Toss: pudlo.")

        rank = max(1, int(focus_spell_rank(actor, minimum=1) or 1))
        setup = _sorcerer_setup(actor)
        damage_type = _normalize(setup.get("elemental_damage_type") or setup.get("sorcerer_elemental_damage_type") or "fire")
        if damage_type not in {"fire", "bludgeoning"}:
            damage_type = "fire"
        burn_note = burn_it_prompt_note(
            actor,
            damage_type,
            source_kind="spell",
            spell_rank=rank,
        )
        damage = int(
            prompt_for_roll(
                f"Elemental Toss: podaj obrazenia ({rank}d8 {damage_type})",
                layout="damage",
                answer_placeholder="Obrazenia",
                prompt_long=burn_note,
            )
            or 0
        )
        damage += int(
            burn_it_bonus(
                actor,
                damage_type,
                source_kind="spell",
                spell_rank=rank,
            )
            or 0
        )
        if is_critical_success(outcome):
            damage *= 2
        defeated = _apply_damage(target, damage, damage_type, source=self.name)
        msg = f"Elemental Toss: zadano {damage} {damage_type}."
        if defeated:
            msg += " Cel pokonany."
        return EventResult(
            success=True,
            consumed_action=True,
            message=msg,
            data={"target": target, "damage": int(damage), "damage_type": damage_type},
        )


@register_event
class FaerieDustEvent(SorcererFocusSpellEvent):
    name = "faerie_dust"
    required_focus_spell_id = "faerie_dust"
    range_feet = 30
    spell_tags = SorcererFocusSpellEvent.spell_tags + ["enchantment", "mental", "primal"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        target, _target_pos = _pick_target(ctx, actor, range_feet=30, kinds=("enemy",))
        if target is None:
            return EventResult.cancelled(message="Faerie Dust: brak celu.")

        outcome = _prompt_choice(
            ctx,
            "Faerie Dust: wynik save celu",
            choices=["critical_success", "success", "failure", "critical_failure"],
            source=self.name,
        ) or "failure"
        normalized = _normalize(outcome)
        if normalized in {"critical_success", "success"}:
            return EventResult(success=True, consumed_action=True, message="Faerie Dust: cel odparl efekt.")

        # Failure: no reactions, -2 Perception/Will for 1 round.
        try:
            if hasattr(target, "reactions_left"):
                target.reactions_left = 0
        except Exception:
            pass
        for tag in ("perception", "will"):
            _add_bonus(
                target,
                BonusEffect(
                    type=BonusType.STATUS,
                    value=2,
                    tag=tag,
                    source=self.name,
                    label="faerie dust",
                    is_penalty=True,
                    duration_turns=1,
                ),
            )
        # Critical failure: additional -1 for 1 minute.
        if normalized == "critical_failure":
            for tag in ("perception", "will"):
                _add_bonus(
                    target,
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=1,
                        tag=tag,
                        source=f"{self.name}:linger",
                        label="faerie dust (linger)",
                        is_penalty=True,
                        duration_turns=10,
                    ),
                )
        return EventResult(
            success=True,
            consumed_action=True,
            message="Faerie Dust: cel traci reakcje i ma kary do Perception/Will.",
            data={"target": target},
        )


@register_event
class GluttonsJawsEvent(SorcererFocusSpellEvent):
    name = "gluttons_jaws"
    required_focus_spell_id = "gluttons_jaws"
    spell_tags = SorcererFocusSpellEvent.spell_tags + ["morph", "necromancy", "divine"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        rank = max(1, int(focus_spell_rank(actor, minimum=1) or 1))
        temp_hp_dice = 1 + max(0, (rank - 1) // 2)
        adder = getattr(actor, "add_status", None)
        if callable(adder):
            try:
                adder(
                    Status(
                        id="gluttons_jaws_active",
                        label="Glutton's Jaws",
                        duration=10,
                        source=self.name,
                        data={
                            "jaws_damage_die": "1d8",
                            "jaws_damage_type": "piercing",
                            "jaws_forceful": True,
                            "jaws_temp_hp_on_hit": f"{temp_hp_dice}d6",
                        },
                    )
                )
            except Exception:
                pass
        return EventResult(
            success=True,
            consumed_action=True,
            message=f"Glutton's Jaws aktywne: jaw attack 1d8 piercing, temp HP on hit {temp_hp_dice}d6 (1 minuta).",
        )


@register_event
class JealousHexEvent(SorcererFocusSpellEvent):
    name = "jealous_hex"
    required_focus_spell_id = "jealous_hex"
    range_feet = 30
    spell_tags = SorcererFocusSpellEvent.spell_tags + ["curse", "necromancy", "occult"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        target, _target_pos = _pick_target(ctx, actor, range_feet=30, kinds=("enemy",))
        if target is None:
            return EventResult.cancelled(message="Jealous Hex: brak celu.")

        condition = _prompt_choice(
            ctx,
            "Jealous Hex: wybierz condition (na podstawie najwyzszego atrybutu celu)",
            choices=["enfeebled", "clumsy", "drained", "stupefied"],
            source=self.name,
        ) or "enfeebled"
        outcome = _prompt_choice(
            ctx,
            "Jealous Hex: wynik save celu",
            choices=["success", "failure", "critical_failure"],
            source=self.name,
        ) or "failure"
        normalized = _normalize(outcome)
        if normalized == "success":
            return EventResult(success=True, consumed_action=True, message="Jealous Hex: brak efektu.")
        value = 2 if normalized == "critical_failure" else 1
        condition_id = _normalize(condition) or "enfeebled"
        adder = getattr(target, "add_status", None)
        if callable(adder):
            try:
                if condition_id == "enfeebled":
                    adder(EnfeebledStatus(value=value, duration=10))
                elif condition_id == "clumsy":
                    adder(ClumsyStatus(value=value, duration=10))
                else:
                    adder(
                        Status(
                            id=condition_id,
                            label=condition_id.replace("_", " ").title(),
                            duration=10,
                            source=self.name,
                            data={"value": value},
                        )
                    )
            except Exception:
                pass
        return EventResult(
            success=True,
            consumed_action=True,
            message=f"Jealous Hex: cel otrzymuje {condition_id} {value} (up to 1 minute).",
            data={"target": target},
        )


@register_event
class TentacularLimbsEvent(SorcererFocusSpellEvent):
    name = "tentacular_limbs"
    required_focus_spell_id = "tentacular_limbs"
    spell_tags = SorcererFocusSpellEvent.spell_tags + ["morph", "transmutation", "occult"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        rank = max(1, int(focus_spell_rank(actor, minimum=1) or 1))
        extended_reach = 20 if rank < 3 else 30
        adder = getattr(actor, "add_status", None)
        if callable(adder):
            try:
                adder(
                    Status(
                        id="tentacular_limbs_active",
                        label="Tentacular Limbs",
                        duration=10,
                        source=self.name,
                        data={
                            "touch_spell_reach_feet": 10,
                            "arm_unarmed_reach_feet": 10,
                            "extended_cast_reach_feet": extended_reach,
                        },
                    )
                )
            except Exception:
                pass
        return EventResult(
            success=True,
            consumed_action=True,
            message=(
                "Tentacular Limbs aktywne: touch/unarmed reach 10 ft; "
                f"przy dodatkowej akcji cast reach do {extended_reach} ft (1 minuta)."
            ),
        )


@register_event
class UndeathsBlessingEvent(SorcererFocusSpellEvent):
    name = "undeaths_blessing"
    required_focus_spell_id = "undeaths_blessing"
    range_feet = 5
    spell_tags = SorcererFocusSpellEvent.spell_tags + ["necromancy", "negative", "divine"]

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        target, _target_pos = _pick_target(ctx, actor, range_feet=5, kinds=("hero", "enemy"))
        if target is None:
            return EventResult.cancelled(message="Undeath's Blessing: brak celu dotyku.")

        rank = max(1, int(focus_spell_rank(actor, minimum=1) or 1))
        harm_bonus = 2 * rank
        adder = getattr(target, "add_status", None)
        if callable(adder):
            try:
                adder(
                    Status(
                        id="undeaths_blessing_active",
                        label="Undeath's Blessing",
                        duration=10,
                        source=self.name,
                        data={
                            "treat_as_undead_for_heal_harm": True,
                            "harm_heal_bonus": harm_bonus,
                        },
                    )
                )
            except Exception:
                pass
        return EventResult(
            success=True,
            consumed_action=True,
            message=(
                "Undeath's Blessing aktywne 1 minute: Heal/Harm traktuje cel jak undead; "
                f"Harm heal bonus +{harm_bonus}."
            ),
            data={"target": target},
        )
