from __future__ import annotations

from combat.hp_engine import apply_damage as hp_apply_damage
from combat.hp_engine import heal as hp_heal
from damage_types import DamageType
from statuses import Status, make_persistent_damage
from statuses.clumsy import ClumsyStatus
from GameObjects.interactions_mixin import prompt_for_roll
from GameObjects.items.goodberry_item import GoodberryItem
from GameObjects.items.inventory import add_item

from ....base import EventContext, EventResult
from ....registry import register_event
from ...magic_event import MagicEvent
from ...focus_utils import focus_spell_rank
from ...magic_utils import pick_target_in_range
from ...spell_types import SpellTradition


def _is_druid(actor) -> bool:
    if actor is None:
        return False
    has_status = getattr(actor, "has_status", None)
    if callable(has_status):
        try:
            if bool(has_status("druid")):
                return True
        except Exception:
            pass
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) == "druid":
            return True
    class_name = str(getattr(actor, "class_name", "") or "").strip().lower()
    return class_name == "druid"


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


def _collect_known_druid_focus_spells(actor) -> set[str]:
    known: set[str] = set()
    if actor is None:
        return known

    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) != "druid":
            continue
        data = getattr(status, "data", None) or {}
        setup = data.get("druid_setup") or {}
        if isinstance(setup, dict):
            spell = str(setup.get("order_spell", "") or "").strip().lower()
            if spell:
                known.add(spell)
        for key in ("druid_order_spell",):
            spell = str(data.get(key, "") or "").strip().lower()
            if spell:
                known.add(spell)
        spell_list = data.get("druid_order_spells")
        if isinstance(spell_list, list):
            for spell in spell_list:
                normalized = str(spell or "").strip().lower()
                if normalized:
                    known.add(normalized)

    for key in ("druid_order_spell",):
        spell = str(getattr(actor, key, "") or "").strip().lower()
        if spell:
            known.add(spell)
    spell_list = getattr(actor, "druid_order_spells", None)
    if isinstance(spell_list, list):
        for spell in spell_list:
            normalized = str(spell or "").strip().lower()
            if normalized:
                known.add(normalized)

    # Wild Shape order spell can be known directly from feat.
    has_status = getattr(actor, "has_status", None)
    if callable(has_status):
        try:
            if bool(has_status("wild_shape")):
                known.add("wild_shape")
        except Exception:
            pass

    return known


def _knows_druid_focus_spell(actor, spell_id: str) -> bool:
    known = _collect_known_druid_focus_spells(actor)
    return str(spell_id or "").strip().lower() in known


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
        tags=["magic", "focus", "druid"],
    )
    return target


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


def _focus_rank(actor) -> int:
    return max(1, int(focus_spell_rank(actor, minimum=1) or 1))


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


def _apply_damage(target, amount: int, damage_type: str) -> bool:
    apply = getattr(target, "apply_damage", None)
    if callable(apply):
        try:
            _, defeated = apply(max(0, int(amount)), damage_type)
            return bool(defeated)
        except Exception:
            return False
    try:
        info = hp_apply_damage(target, amount, damage_type, source=f"order_spell:{damage_type}")
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
        hp_heal(target, healed, source="order_spell:heal")
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


def _remove_statuses(target, status_id: str) -> None:
    statuses = getattr(target, "statuses", None)
    if not isinstance(statuses, list):
        return
    try:
        target.statuses = [s for s in statuses if getattr(s, "id", None) != status_id]
    except Exception:
        pass


def _basic_save_damage(base_damage: int, outcome: str) -> int:
    base = max(0, int(base_damage))
    if outcome == "critical_success":
        return 0
    if outcome == "success":
        return max(0, base // 2)
    if outcome == "critical_failure":
        return max(0, base * 2)
    return base


def _persistent_bonus_for_rank(rank: int) -> str | None:
    if rank >= 10:
        return "4d6"
    if rank >= 6:
        return "2d6"
    return None


def _wild_morph_choice_profile(choice: str, *, rank: int) -> dict[str, object]:
    choice_id = str(choice or "").strip().lower()
    profile: dict[str, object] = {"choice": choice_id}
    if choice_id == "wild_claws":
        profile["unarmed_profile"] = {
            "label": "wild claws",
            "damage_prompt": "1k6 + STR",
            "damage_type": DamageType.SLASHING.value,
            "extra_tags": ["unarmed", "agile", "finesse"],
        }
        persistent = _persistent_bonus_for_rank(rank)
        if persistent:
            profile["on_hit_persistent_damage"] = {
                "formula": persistent,
                "damage_type": DamageType.BLEED.value,
            }
    elif choice_id == "wild_jaws":
        profile["unarmed_profile"] = {
            "label": "wild jaws",
            "damage_prompt": "1k8 + STR",
            "damage_type": DamageType.PIERCING.value,
            "extra_tags": ["unarmed"],
        }
        persistent = _persistent_bonus_for_rank(rank)
        if persistent:
            profile["on_hit_persistent_damage"] = {
                "formula": persistent,
                "damage_type": DamageType.POISON.value,
            }
    elif choice_id == "elemental_body":
        profile["precision_resistance"] = 5
        profile["critical_hit_resistance"] = 5
    elif choice_id == "vine_arms":
        profile["reach_feet"] = 10
    elif choice_id == "wings":
        profile["fly_speed_feet"] = 30
    return profile


def _build_wild_shape_profile(choice: str, *, rank: int) -> dict[str, object]:
    raw = str(choice or "").strip().lower()
    data: dict[str, object] = {"choice": raw}
    if raw.startswith("pest_form:"):
        form = raw.split(":", 1)[1] or "mouse"
        data.update(
            {
                "form_family": "pest_form",
                "form": form,
                "duration_turns": 100,
                "size": "tiny",
            }
        )
        return data

    form = "animal"
    if ":" in raw:
        _family, sub = raw.split(":", 1)
        if sub:
            form = sub
    data.update(
        {
            "form_family": "animal_form",
            "form": form,
            "duration_turns": 10,
            "size": "small",
            "attack_status_bonus": 2,
            "unarmed_profile": {
                "label": f"{form} form",
                "damage_prompt": "2k6 + STR" if rank >= 2 else "1k6 + STR",
                "damage_type": DamageType.SLASHING.value,
                "extra_tags": ["unarmed"],
            },
        }
    )
    if form in {"wolf", "snake"}:
        data["unarmed_profile"] = {
            "label": f"{form} jaws",
            "damage_prompt": "2k8 + STR" if rank >= 2 else "1k8 + STR",
            "damage_type": DamageType.PIERCING.value,
            "extra_tags": ["unarmed", "finesse"],
        }
    if form == "bird":
        data["unarmed_profile"] = {
            "label": "bird talon",
            "damage_prompt": "2k4 + STR" if rank >= 2 else "1k4 + STR",
            "damage_type": DamageType.SLASHING.value,
            "extra_tags": ["unarmed", "agile", "finesse"],
        }
        data["fly_speed_feet"] = 30
    return data


def _is_animal_target(target) -> bool:
    if target is None:
        return False
    has_tag = getattr(target, "has_tag", None)
    if callable(has_tag):
        try:
            if bool(has_tag("animal")):
                return True
        except Exception:
            pass
    tags = {str(t).strip().lower() for t in (getattr(target, "tags", None) or [])}
    return "animal" in tags or bool(getattr(target, "is_animal", False))


class DruidFocusSpellEvent(MagicEvent):
    actions_cost = 1
    default_tags = ["magic", "spell", "focus", "druid"]
    spell_tags = ["focus", "primal", "druid"]
    magic_traditions = (SpellTradition.PRIMAL,)
    magic_types = ["focus"]

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message=f"{self.name}: missing actor.")
        if not _is_druid(actor):
            return EventResult.cancelled(message=f"{self.name}: only Druid can cast this spell.")
        if not _knows_druid_focus_spell(actor, self.name):
            return EventResult.cancelled(message=f"{self.name}: spell is not known for this druid.")

        points = _focus_points(actor)
        if points <= 0:
            return EventResult.cancelled(message=f"{self.name}: no Focus Point.")

        result = self._execute_effect(ctx)
        if not result.success:
            return result

        _set_focus_points(actor, points - 1)
        base_msg = str(result.message or f"{self.name}: effect applied.")
        result.message = f"{base_msg} Focus Point: {_focus_points(actor)}."
        return result

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        raise NotImplementedError


@register_event
class GoodberryEvent(DruidFocusSpellEvent):
    name = "goodberry"
    actions_cost = 2
    default_tags = DruidFocusSpellEvent.default_tags + ["healing", "necromancy"]
    spell_tags = DruidFocusSpellEvent.spell_tags + ["healing", "necromancy"]
    prompt = "Goodberry: tworzysz jagody leczace (1d6+4 kazda)."

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        rank = _focus_rank(actor)
        berries = max(1, rank)
        for _ in range(berries):
            add_item(actor, GoodberryItem(cast_rank=rank))

        return EventResult(
            success=True,
            consumed_action=True,
            message=(
                f"Goodberry: utworzono {berries} item(ów) Goodberry w ekwipunku. "
                "Zużyj przez Ekwipunek -> 5 (leczenie 1d6+4)."
            ),
        )


@register_event
class HealAnimalEvent(DruidFocusSpellEvent):
    name = "heal_animal"
    actions_cost = 1
    default_tags = DruidFocusSpellEvent.default_tags + ["healing", "necromancy", "positive"]
    spell_tags = DruidFocusSpellEvent.spell_tags + ["healing", "necromancy", "positive"]
    prompt = "Heal Animal: leczy 1 zwierze (touch/ranged)."

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        mode = _prompt_choice(
            ctx,
            "Heal Animal - wybierz wariant",
            ["touch", "ranged"],
            source=self.name,
        ) or "touch"
        mode_actions = 2 if mode == "ranged" else 1
        remaining = _actions_remaining(ctx, actor)
        if remaining is not None and mode_actions > remaining:
            return EventResult.cancelled(
                message=f"Heal Animal: za malo akcji na wariant {mode} ({mode_actions}, masz {remaining})."
            )
        range_feet = 30 if mode == "ranged" else 5

        target = _pick_target(
            ctx,
            actor,
            range_feet=range_feet,
            allowed_kinds=("hero", "enemy"),
        )
        if target is None:
            return EventResult.cancelled(message="Heal Animal: target not selected.")
        if not _is_animal_target(target):
            return EventResult.cancelled(message="Heal Animal: target must be a living animal.")

        rank = _focus_rank(actor)
        bonus = 8 * rank if mode == "ranged" else 0
        prompt_long = (
            f"Rules hint: heal={rank}d8"
            + (f" + {bonus} (ranged)" if bonus else "")
            + ". Podaj final value."
        )
        heal_amount = int(
            prompt_for_roll(
                "Heal Animal - podaj final healing value:",
                layout="damage",
                answer_placeholder="Healing",
                prompt_long=prompt_long,
            )
            or 0
        )
        if heal_amount <= 0:
            return EventResult.cancelled(message="Heal Animal: healing must be > 0.")

        _apply_heal(target, heal_amount)
        target_name = getattr(target, "name", "target")
        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=mode_actions if ctx.in_combat else None,
            message=f"Heal Animal: {target_name} heals {heal_amount} HP ({mode}).",
        )


@register_event
class TempestSurgeEvent(DruidFocusSpellEvent):
    name = "tempest_surge"
    actions_cost = 2
    default_tags = DruidFocusSpellEvent.default_tags + ["air", "electric", "evocation"]
    spell_tags = DruidFocusSpellEvent.spell_tags + ["air", "electricity", "evocation"]
    prompt = "Tempest Surge: basic Reflex save + clumsy/persistent on failure."

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        target = _pick_target(
            ctx,
            actor,
            range_feet=30,
            allowed_kinds=("hero", "enemy"),
        )
        if target is None:
            return EventResult.cancelled(message="Tempest Surge: target not selected.")

        rank = _focus_rank(actor)
        outcome = _prompt_choice(
            ctx,
            "Tempest Surge - wybierz wynik Reflex save celu",
            ["critical_success", "success", "failure", "critical_failure"],
            source=self.name,
        ) or "failure"

        base_damage = int(
            prompt_for_roll(
                "Tempest Surge - podaj bazowe obrazenia (przed save):",
                layout="damage",
                answer_placeholder="Damage",
                prompt_long=f"Rules hint: base damage {rank}d12. Podaj final base value.",
            )
            or 0
        )
        if base_damage <= 0:
            return EventResult.cancelled(message="Tempest Surge: damage must be > 0.")

        final_damage = _basic_save_damage(base_damage, outcome)
        defeated = False
        if final_damage > 0:
            defeated = _apply_damage(target, final_damage, DamageType.ELECTRIC.value)

        if outcome in {"failure", "critical_failure"}:
            _add_status(
                target,
                ClumsyStatus(
                    ac_penalty=2,
                    reflex_penalty=2,
                    ranged_penalty=2,
                    finesse_penalty=2,
                    stealth_penalty=2,
                    duration=1,
                    source=self.name,
                    label="Tempest Surge: Clumsy 2",
                ),
            )
            _add_status(
                target,
                make_persistent_damage(
                    rank,
                    DamageType.ELECTRIC.value,
                    source=self.name,
                ),
            )

        target_name = getattr(target, "name", "target")
        msg = (
            f"Tempest Surge: {target_name} -> save={outcome}, "
            f"damage={final_damage} electric."
        )
        if defeated:
            msg += " Target defeated."
        return EventResult(success=True, consumed_action=True, message=msg)


@register_event
class WildMorphEvent(DruidFocusSpellEvent):
    name = "wild_morph"
    actions_cost = 1
    default_tags = DruidFocusSpellEvent.default_tags + ["morph", "transmutation"]
    spell_tags = DruidFocusSpellEvent.spell_tags + ["morph", "transmutation"]
    prompt = "Wild Morph: wybierz dostepny efekt morfowania."

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        rank = _focus_rank(actor)
        has_status = getattr(actor, "has_status", None)

        available: list[str] = []
        if callable(has_status):
            try:
                if has_status("wild_shape"):
                    available.append("wild_claws")
            except Exception:
                pass
            try:
                if has_status("insect_shape"):
                    available.append("wild_jaws")
            except Exception:
                pass
            try:
                if has_status("elemental_shape"):
                    available.append("elemental_body")
            except Exception:
                pass
            try:
                if has_status("plant_shape"):
                    available.append("vine_arms")
            except Exception:
                pass
            try:
                if has_status("soaring_shape"):
                    available.append("wings")
            except Exception:
                pass

        if not available:
            return EventResult.cancelled(
                message="Wild Morph: brak dostepnych efektow (wymagane featy wild shape/insect/elemental/plant/soaring)."
            )

        max_effects = 1
        if rank >= 10:
            max_effects = 3
        elif rank >= 6:
            max_effects = 2
        picked: list[str] = []
        while available and len(picked) < max_effects:
            choice = _prompt_choice(
                ctx,
                "Wild Morph - wybierz efekt",
                available,
                source=self.name,
            ) or available[0]
            if choice not in picked:
                picked.append(choice)
            available = [item for item in available if item != choice]
            if not available:
                break
            more = _prompt_choice(
                ctx,
                "Wild Morph - dodać kolejny efekt?",
                ["nie", "tak"],
                source=self.name,
            )
            if more != "tak":
                break
        if not picked:
            return EventResult.cancelled(message="Wild Morph: nie wybrano efektu.")
        actions = 2 if "wings" in picked else 1
        remaining = _actions_remaining(ctx, actor)
        if remaining is not None and actions > remaining:
            return EventResult.cancelled(
                message=f"Wild Morph: wybrane efekty wymagaja {actions} akcji, a masz {remaining}."
            )
        _remove_statuses(actor, "wild_morph_active")

        profiles = [_wild_morph_choice_profile(choice, rank=rank) for choice in picked]
        combined_unarmed = next((p.get("unarmed_profile") for p in profiles if p.get("unarmed_profile")), None)
        combined_reach = max([int(p.get("reach_feet", 0) or 0) for p in profiles] + [0])
        combined_fly = max([int(p.get("fly_speed_feet", 0) or 0) for p in profiles] + [0])
        persistent = next((p.get("on_hit_persistent_damage") for p in profiles if p.get("on_hit_persistent_damage")), None)
        precision_res = max([int(p.get("precision_resistance", 0) or 0) for p in profiles] + [0])
        crit_res = max([int(p.get("critical_hit_resistance", 0) or 0) for p in profiles] + [0])

        data: dict[str, object] = {
            "effect": picked[0],
            "effects": list(picked),
            "cast_rank": rank,
            "form_engine": True,
        }
        if combined_unarmed:
            data["unarmed_profile"] = combined_unarmed
        if combined_reach:
            data["reach_feet"] = combined_reach
        if combined_fly:
            data["fly_speed_feet"] = combined_fly
        if persistent:
            data["on_hit_persistent_damage"] = persistent
        if precision_res:
            data["precision_resistance"] = precision_res
            data["damage_resistance"] = {"precision": {"value": precision_res}}
        if crit_res:
            data["critical_hit_resistance"] = crit_res

        _add_status(
            actor,
            Status(
                id="wild_morph_active",
                label=f"Wild Morph ({', '.join(picked)})",
                duration=10,
                source=self.name,
                data=data,
            ),
        )

        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=actions if ctx.in_combat else None,
            message=f"Wild Morph: aktywowano efekty {', '.join(picked)}.",
        )


@register_event
class WildShapeEvent(DruidFocusSpellEvent):
    name = "wild_shape"
    actions_cost = 2
    default_tags = DruidFocusSpellEvent.default_tags + ["polymorph", "transmutation"]
    spell_tags = DruidFocusSpellEvent.spell_tags + ["polymorph", "transmutation"]
    prompt = "Wild Shape: wybierz forme przemiany."

    def _execute_effect(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        rank = _focus_rank(actor)

        choices = ["pest_form:mouse", "pest_form:rat", "pest_form:cat", "pest_form:bird"]
        if rank >= 2:
            choices.extend(
                [
                    "animal_form:wolf",
                    "animal_form:bear",
                    "animal_form:cat",
                    "animal_form:snake",
                    "animal_form:bird",
                ]
            )

        choice = _prompt_choice(
            ctx,
            "Wild Shape - wybierz forme",
            choices,
            source=self.name,
        ) or choices[0]

        profile = _build_wild_shape_profile(choice, rank=rank)
        _remove_statuses(actor, "wild_shape_active")
        form = str(profile.get("form", "unknown") or "unknown")
        form_family = str(profile.get("form_family", "wild_shape") or "wild_shape")
        duration = int(profile.get("duration_turns", 10) or 10)
        data = {
            "form_family": form_family,
            "form": form,
            "cast_rank": rank,
            "form_engine": True,
            "attack_status_bonus": int(profile.get("attack_status_bonus", 2) or 2),
        }
        for key in ("unarmed_profile", "fly_speed_feet", "size"):
            if key in profile:
                data[key] = profile[key]

        _add_status(
            actor,
            Status(
                id="wild_shape_active",
                label=f"Wild Shape ({form})",
                duration=duration,
                source=self.name,
                data=data,
            ),
        )
        return EventResult(
            success=True,
            consumed_action=True,
            message=(
                f"Wild Shape: forma '{form}' aktywna. "
                "Automatycznie dodawany jest +2 status do atakow."
            ),
        )


__all__ = [
    "DruidFocusSpellEvent",
    "GoodberryEvent",
    "HealAnimalEvent",
    "TempestSurgeEvent",
    "WildMorphEvent",
    "WildShapeEvent",
]
