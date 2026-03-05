"""Bazowe klasy dla czarów oraz wspólny resolver kontroli kosztów/trybów."""

from __future__ import annotations

import logging
from typing import Any

from bonuses import BonusEffect, BonusType
from combat.hp_engine import apply_damage as hp_apply_damage
from combat.hp_engine import grant_temp_hp
from statuses.base import Status
from ..base import EventContext, EventResult, ActionCostEvent
from .focus_utils import focus_spell_rank
from .magic_utils import grid_distance_feet
from .spell_types import SpellTradition

logger = logging.getLogger(__name__)


class MagicEvent(ActionCostEvent):
    """Bazowa klasa czarów z polami wspólnymi dla większości zaklęć."""

    # w jakich trybach można rzucać
    combat_allowed: bool = True
    hero_turn_allowed: bool = True  # eksploracja / tura bohaterów

    # koszt i znaczniki
    actions_cost: int = 1  # 1-3 akcje
    spell_tags: list[str] | None = None
    spell_tradition: SpellTradition | None = None
    magic_traditions: tuple[SpellTradition, ...] | None = None  # wiele tradycji naraz
    magic_types: list[str] | None = None  # np. szkoła (evocation), cantrip itp.

    # zasięg i UI
    range_feet: int | None = None
    prompt: str | None = None

    def _effective_tags(self, ctx: EventContext) -> list[str]:
        """Połącz tagi bazowe, tagi czaru i tagi z kontekstu."""
        tags: list[str] = []
        if self.default_tags:
            tags.extend(self.default_tags)
        if self.spell_tags:
            tags.extend([t for t in self.spell_tags if t not in tags])
        if ctx.tags:
            tags.extend([t for t in ctx.tags if t not in tags])
        return tags

    # --- helpers ---
    def distance_and_range_ok(self, source: Tuple[int, int], target: Tuple[int, int]) -> tuple[bool, int | None]:
        """Policz dystans i sprawdź limit range_feet (jeśli ustawiony)."""
        distance = grid_distance_feet(source, target)
        if self.range_feet is None:
            return True, distance
        return distance <= self.range_feet, distance


class MagicEventResolver:
    """Waliduje możliwość rzucenia czaru i odpala lifecycle eventu."""

    @staticmethod
    def _has_status(actor, status_id: str) -> bool:
        if actor is None:
            return False
        checker = getattr(actor, "has_status", None)
        if callable(checker):
            try:
                return bool(checker(status_id))
            except Exception:
                return False
        for status in getattr(actor, "statuses", []) or []:
            if getattr(status, "id", status) == status_id:
                return True
        return False

    @staticmethod
    def _remove_status(actor, status_id: str) -> None:
        if actor is None:
            return
        remover = getattr(actor, "remove_status", None)
        if callable(remover):
            try:
                remover(status_id)
                return
            except Exception:
                pass
        statuses = getattr(actor, "statuses", None)
        if not isinstance(statuses, list):
            return
        for idx in range(len(statuses) - 1, -1, -1):
            if getattr(statuses[idx], "id", statuses[idx]) == status_id:
                del statuses[idx]
                return

    @staticmethod
    def _event_tags(event: MagicEvent, ctx: EventContext) -> list[str]:
        try:
            tags = list(event._effective_tags(ctx) or [])
        except Exception:
            tags = []
        if "magic" not in tags:
            tags.append("magic")
        if "spell" not in tags:
            tags.append("spell")
        return tags

    @staticmethod
    def _extract_sorcerer_setup(actor) -> dict[str, Any]:
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
        fallback: dict[str, Any] = {}
        for key in (
            "sorcerer_bloodline",
            "sorcerer_spell_tradition",
            "sorcerer_bloodline_initial_focus_spell",
            "sorcerer_bloodline_granted_spells",
            "sorcerer_blood_magic",
            "sorcerer_dragon_type",
            "sorcerer_dragon_damage_type",
            "sorcerer_elemental_type",
            "sorcerer_elemental_damage_type",
        ):
            value = getattr(actor, key, None)
            if value is not None:
                fallback[key.replace("sorcerer_", "")] = value
        return fallback

    @staticmethod
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

    @staticmethod
    def _is_yes(value: str | None) -> bool:
        return str(value or "").strip().lower() in {"t", "tak", "y", "yes", "1"}

    @staticmethod
    def _normalize(value: object) -> str:
        return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")

    @staticmethod
    def _bloodline_granted_spell_levels(setup: dict[str, Any]) -> dict[str, int]:
        levels: dict[str, int] = {}
        granted = setup.get("bloodline_granted_spells") or setup.get("sorcerer_bloodline_granted_spells") or {}
        if not isinstance(granted, dict):
            return levels
        for key, spell_id in granted.items():
            normalized_spell = MagicEventResolver._normalize(spell_id)
            if not normalized_spell:
                continue
            normalized_key = MagicEventResolver._normalize(key)
            if normalized_key == "cantrip":
                levels[normalized_spell] = 0
                continue
            if normalized_key.startswith("rank_"):
                try:
                    levels[normalized_spell] = max(0, int(normalized_key.split("_", 1)[1]))
                    continue
                except Exception:
                    pass
        return levels

    @staticmethod
    def _spell_rank_from_tags(tags: list[str]) -> int | None:
        for tag in tags:
            raw = MagicEventResolver._normalize(tag)
            if raw.startswith("rank"):
                suffix = raw[4:]
                try:
                    return max(0, int(suffix))
                except Exception:
                    continue
        return None

    @staticmethod
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
        class_name = MagicEventResolver._normalize(getattr(actor, "class_name", ""))
        return class_name == "wizard"

    @staticmethod
    def _wizard_cast_registry(actor) -> list[dict[str, Any]]:
        raw = getattr(actor, "wizard_cast_spells_registry", None)
        if isinstance(raw, list):
            normalized: list[dict[str, Any]] = []
            for item in raw:
                if isinstance(item, dict):
                    normalized.append(dict(item))
            return normalized
        return []

    @staticmethod
    def _set_wizard_cast_registry(actor, registry: list[dict[str, Any]]) -> None:
        if actor is None:
            return
        payload = [dict(item) for item in registry if isinstance(item, dict)]
        try:
            setattr(actor, "wizard_cast_spells_registry", payload)
        except Exception:
            pass

    @staticmethod
    def _record_spell_cast_if_needed(event: MagicEvent, ctx: EventContext, result: EventResult, *, tags: list[str]) -> None:
        actor = ctx.actor
        if actor is None:
            return
        if not result.success or not result.consumed_action:
            return
        if not MagicEventResolver._is_wizard(actor):
            return

        spell_id = MagicEventResolver._normalize(getattr(event, "name", ""))
        if not spell_id:
            return

        normalized_tags = [MagicEventResolver._normalize(tag) for tag in tags]
        is_focus = "focus" in normalized_tags
        is_cantrip = "cantrip" in normalized_tags
        rank = MagicEventResolver._spell_rank_from_tags(tags)
        if rank is None:
            if is_focus:
                try:
                    rank = max(1, int(focus_spell_rank(actor, minimum=1) or 1))
                except Exception:
                    rank = 1
            elif is_cantrip:
                rank = 0
            else:
                rank = 1

        registry = MagicEventResolver._wizard_cast_registry(actor)
        registry.append(
            {
                "spell_id": spell_id,
                "rank": int(max(0, rank)),
                "is_focus": bool(is_focus),
                "is_cantrip": bool(is_cantrip),
                "tags": [tag for tag in normalized_tags if tag],
            }
        )
        MagicEventResolver._set_wizard_cast_registry(actor, registry)

    @staticmethod
    def _add_bonus(actor, effect: BonusEffect) -> None:
        if actor is None:
            return
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

    @staticmethod
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

    @staticmethod
    def _pick_blood_magic_target(ctx: EventContext, actor, spell_target) -> object | None:
        if actor is None:
            return None
        if spell_target is None:
            return actor
        answer = MagicEventResolver._prompt_choice(
            ctx,
            "Blood Magic: wybierz odbiorce efektu",
            choices=["self", "target"],
            source="blood_magic",
        )
        if answer is None:
            return actor
        normalized = MagicEventResolver._normalize(answer)
        if normalized.startswith("target"):
            return spell_target
        return actor

    @staticmethod
    def _extract_primary_target(result: EventResult):
        data = getattr(result, "data", None)
        if not isinstance(data, dict):
            return None
        target = data.get("target")
        if target is not None:
            return target
        targets = data.get("targets")
        if isinstance(targets, list) and targets:
            return targets[0]
        return None

    @staticmethod
    def _blood_magic_spell_level(
        actor,
        event: MagicEvent,
        setup: dict[str, Any],
        tags: list[str],
        *,
        focus_trigger: bool,
    ) -> int:
        if focus_trigger:
            try:
                return max(1, int(focus_spell_rank(actor, minimum=1) or 1))
            except Exception:
                return 1

        spell_id = MagicEventResolver._normalize(getattr(event, "name", ""))
        granted_levels = MagicEventResolver._bloodline_granted_spell_levels(setup)
        if spell_id in granted_levels and int(granted_levels[spell_id]) > 0:
            return int(granted_levels[spell_id])
        ranked = MagicEventResolver._spell_rank_from_tags(tags)
        if ranked is not None and ranked > 0:
            return int(ranked)
        return 1

    @staticmethod
    def _add_temp_hp_for_round(actor, amount: int, *, source: str) -> None:
        if actor is None:
            return
        grant_temp_hp(actor, int(amount), source=source)
        adder = getattr(actor, "add_status", None)
        if not callable(adder):
            return
        try:
            adder(
                Status(
                    id="blood_magic_temp_hp",
                    label="Blood Magic Temp HP",
                    duration=1,
                    source=source,
                    data={"temp_hp_source": source},
                )
            )
        except Exception:
            pass

    @staticmethod
    def _emit_cast_start(ctx: EventContext, event: MagicEvent, *, tags: list[str]):
        events_bus = getattr(ctx.game, "events", None)
        emitter = getattr(events_bus, "safe_emit_action", None)
        if not callable(emitter):
            return None
        payload = {
            "return_event": True,
            "actor": ctx.actor,
            "action_id": f"{event.name}_pre",
            "action_tags": list(tags),
            "spell_name": str(getattr(event, "name", "spell")),
            "spell_tags": list(event.spell_tags or []),
            "spell_tradition": str(getattr(event, "spell_tradition", "") or ""),
            "is_focus_spell": "focus" in {MagicEventResolver._normalize(t) for t in tags},
            "is_cantrip_spell": "cantrip" in {MagicEventResolver._normalize(t) for t in tags},
        }
        try:
            return emitter(**payload)
        except Exception:
            return None

    @staticmethod
    def _apply_blood_magic_if_needed(event: MagicEvent, ctx: EventContext, result: EventResult, *, tags: list[str]) -> None:
        actor = ctx.actor
        if actor is None:
            return
        if not result.success or not result.consumed_action:
            return
        if not MagicEventResolver._has_status(actor, "sorcerer"):
            return

        setup = MagicEventResolver._extract_sorcerer_setup(actor)
        bloodline = MagicEventResolver._normalize(setup.get("bloodline") or setup.get("sorcerer_bloodline"))
        if not bloodline:
            return

        spell_id = MagicEventResolver._normalize(getattr(event, "name", ""))
        focus_spell = MagicEventResolver._normalize(
            setup.get("bloodline_initial_focus_spell") or setup.get("sorcerer_bloodline_initial_focus_spell")
        )
        granted_levels = MagicEventResolver._bloodline_granted_spell_levels(setup)
        focus_trigger = bool(focus_spell and spell_id == focus_spell)
        granted_trigger = spell_id in granted_levels and int(granted_levels[spell_id]) > 0
        if not (focus_trigger or granted_trigger):
            return

        spell_level = MagicEventResolver._blood_magic_spell_level(
            actor,
            event,
            setup,
            tags,
            focus_trigger=focus_trigger,
        )
        target = MagicEventResolver._extract_primary_target(result)
        target_or_self = MagicEventResolver._pick_blood_magic_target(ctx, actor, target)
        source = f"blood_magic:{bloodline}"

        if bloodline == "aberrant":
            recipient = target_or_self or actor
            MagicEventResolver._add_bonus(
                recipient,
                BonusEffect(type=BonusType.STATUS, value=2, tag="will", source=source, label="aberrant blood magic", duration_turns=1),
            )
            return

        if bloodline == "angelic":
            recipient = target_or_self or actor
            for save_tag in ("fortitude", "reflex", "will"):
                MagicEventResolver._add_bonus(
                    recipient,
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=1,
                        tag=save_tag,
                        source=source,
                        label="angelic blood magic",
                        duration_turns=1,
                    ),
                )
            return

        if bloodline == "demonic":
            answer = MagicEventResolver._prompt_choice(
                ctx,
                "Blood Magic (Demonic): wybierz efekt",
                choices=["target_ac_penalty", "self_intimidation_bonus"],
                source="blood_magic",
            )
            if MagicEventResolver._normalize(answer).startswith("target") and target is not None:
                MagicEventResolver._add_bonus(
                    target,
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=1,
                        tag="ac",
                        source=source,
                        label="demonic blood magic",
                        is_penalty=True,
                        duration_turns=1,
                    ),
                )
            else:
                MagicEventResolver._add_bonus(
                    actor,
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=1,
                        tag="intimidation",
                        source=source,
                        label="demonic blood magic",
                        duration_turns=1,
                    ),
                )
            return

        if bloodline == "diabolic":
            answer = MagicEventResolver._prompt_choice(
                ctx,
                "Blood Magic (Diabolic): wybierz efekt",
                choices=["target_fire_damage", "self_deception_bonus"],
                source="blood_magic",
            )
            if MagicEventResolver._normalize(answer).startswith("target") and target is not None:
                MagicEventResolver._apply_damage(
                    target,
                    max(1, int(spell_level)),
                    "fire",
                    source=source,
                )
            else:
                MagicEventResolver._add_bonus(
                    actor,
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=1,
                        tag="deception",
                        source=source,
                        label="diabolic blood magic",
                        duration_turns=1,
                    ),
                )
            return

        if bloodline == "draconic":
            recipient = target_or_self or actor
            MagicEventResolver._add_bonus(
                recipient,
                BonusEffect(type=BonusType.STATUS, value=1, tag="ac", source=source, label="draconic blood magic", duration_turns=1),
            )
            return

        if bloodline == "elemental":
            answer = MagicEventResolver._prompt_choice(
                ctx,
                "Blood Magic (Elemental): wybierz efekt",
                choices=["self_intimidation_bonus", "target_elemental_damage"],
                source="blood_magic",
            )
            elemental_damage = MagicEventResolver._normalize(
                setup.get("elemental_damage_type") or setup.get("sorcerer_elemental_damage_type")
            )
            if elemental_damage not in {"fire", "bludgeoning"}:
                elemental_damage = "fire"
            if MagicEventResolver._normalize(answer).startswith("target") and target is not None:
                MagicEventResolver._apply_damage(
                    target,
                    max(1, int(spell_level)),
                    elemental_damage,
                    source=source,
                )
            else:
                MagicEventResolver._add_bonus(
                    actor,
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=1,
                        tag="intimidation",
                        source=source,
                        label="elemental blood magic",
                        duration_turns=1,
                    ),
                )
            return

        if bloodline == "fey":
            recipient = target_or_self or actor
            adder = getattr(recipient, "add_status", None)
            if callable(adder):
                try:
                    adder(Status(id="concealed", label="Concealed", duration=1, source=source, data={"effect_tags": ["concealment"]}))
                except Exception:
                    pass
            return

        if bloodline == "hag":
            adder = getattr(actor, "add_status", None)
            if callable(adder):
                try:
                    adder(
                        Status(
                            id="hag_blood_magic_retaliation",
                            label="Hag Blood Magic",
                            duration=1,
                            source=source,
                            data={
                                "blood_magic_hag_damage": max(0, 2 * int(spell_level)),
                                "blood_magic_hag_save": "will_basic",
                            },
                        )
                    )
                except Exception:
                    pass
            try:
                ctx.game.ui_log(
                    "Blood Magic (Hag): pierwszy przeciwnik, ktory zada ci obrazenia do konca twojej nastepnej tury, "
                    f"otrzymuje {2 * int(spell_level)} mental (basic Will)."
                )
            except Exception:
                pass
            return

        if bloodline == "imperial":
            recipient = target_or_self or actor
            for skill_tag in (
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
                "perception",
            ):
                MagicEventResolver._add_bonus(
                    recipient,
                    BonusEffect(
                        type=BonusType.STATUS,
                        value=1,
                        tag=skill_tag,
                        source=source,
                        label="imperial blood magic",
                        duration_turns=1,
                    ),
                )
            return

        if bloodline == "undead":
            answer = MagicEventResolver._prompt_choice(
                ctx,
                "Blood Magic (Undead): wybierz efekt",
                choices=["self_temp_hp", "target_negative_damage"],
                source="blood_magic",
            )
            if MagicEventResolver._normalize(answer).startswith("target") and target is not None:
                MagicEventResolver._apply_damage(
                    target,
                    max(1, int(spell_level)),
                    "negative",
                    source=source,
                )
            else:
                MagicEventResolver._add_temp_hp_for_round(
                    actor,
                    max(1, int(spell_level)),
                    source=f"{source}:temp_hp",
                )

    @staticmethod
    def resolve(event: MagicEvent, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak aktora rzucającego czar.")

        try:
            cost = int(event.actions_cost)
        except Exception:
            cost = 1
        cost = min(3, max(1, cost))
        event.actions_cost = cost

        # tryb tury
        if ctx.in_combat and not event.combat_allowed:
            msg = f"Czar '{event.name}' niedostępny w walce."
            logger.info(msg)
            return EventResult.cancelled(message=msg)
        if ctx.in_exploration and not event.hero_turn_allowed:
            msg = f"Czar '{event.name}' niedostępny poza walką."
            logger.info(msg)
            return EventResult.cancelled(message=msg)

        reach_applied = False
        if event.range_feet is not None and MagicEventResolver._has_status(actor, "reach_spell_ready"):
            try:
                base_range = int(event.range_feet)
            except Exception:
                base_range = event.range_feet
            tags = {str(tag).strip().lower() for tag in (event.spell_tags or [])}
            is_touch = "touch" in tags
            if isinstance(base_range, int):
                if is_touch and base_range <= 5:
                    event.range_feet = 30
                else:
                    event.range_feet = base_range + 30
                reach_applied = True
                try:
                    game_ui_log = getattr(ctx.game, "ui_log", None)
                    if callable(game_ui_log):
                        game_ui_log(
                            f"Reach Spell: zasieg czaru '{event.name}' zwiekszony z {base_range} ft do {event.range_feet} ft."
                        )
                except Exception:
                    pass

        event_tags = MagicEventResolver._event_tags(event, ctx)
        emitted = MagicEventResolver._emit_cast_start(ctx, event, tags=event_tags)
        if isinstance(emitted, dict) and bool(emitted.get("disrupted", False)):
            if reach_applied:
                MagicEventResolver._remove_status(actor, "reach_spell_ready")
            if MagicEventResolver._has_status(actor, "widen_spell_ready"):
                MagicEventResolver._remove_status(actor, "widen_spell_ready")
            reason = str(emitted.get("disruption_reason", "") or "counterspell")
            return EventResult(
                success=False,
                consumed_action=True,
                actions_spent=cost,
                message=f"Czar '{event.name}' zostal przerwany ({reason}).",
            )

        try:
            from GameObjects.interactions_mixin.prompt_utils import (
                get_magic_prompt_context,
                set_magic_prompt_context,
            )
        except Exception:  # pragma: no cover - fallback defensywny
            get_magic_prompt_context = None  # type: ignore[assignment]
            set_magic_prompt_context = None  # type: ignore[assignment]

        prev_prompt_ctx = None
        if callable(get_magic_prompt_context):
            try:
                prev_prompt_ctx = get_magic_prompt_context()
            except Exception:
                prev_prompt_ctx = None
        if callable(set_magic_prompt_context):
            try:
                set_magic_prompt_context(
                    {
                        "game": getattr(ctx, "game", None),
                        "actor": actor,
                        "spell_name": str(getattr(event, "name", "spell") or "spell"),
                        "spell_tags": list(event_tags),
                        "is_focus_spell": "focus" in {MagicEventResolver._normalize(t) for t in event_tags},
                        "is_cantrip_spell": "cantrip" in {MagicEventResolver._normalize(t) for t in event_tags},
                        "dangerous_sorcery_applied": False,
                    }
                )
            except Exception:
                pass
        try:
            result = event.run(ctx)
        finally:
            if callable(set_magic_prompt_context):
                try:
                    set_magic_prompt_context(prev_prompt_ctx)
                except Exception:
                    pass
        if result.actions_spent is None and result.consumed_action:
            result.actions_spent = cost
        if reach_applied and result.consumed_action:
            MagicEventResolver._remove_status(actor, "reach_spell_ready")
        if MagicEventResolver._has_status(actor, "widen_spell_ready") and result.consumed_action:
            MagicEventResolver._remove_status(actor, "widen_spell_ready")
            try:
                game_ui_log = getattr(ctx.game, "ui_log", None)
                if callable(game_ui_log):
                    game_ui_log(
                        f"Widen Spell: czar '{event.name}' zuzywa przygotowany efekt "
                        "(rozlicz recznie zwiekszenie obszaru)."
                    )
            except Exception:
                pass
        try:
            MagicEventResolver._apply_blood_magic_if_needed(event, ctx, result, tags=event_tags)
        except Exception:
            logger.debug("Blood Magic hook failed for spell %s", getattr(event, "name", "spell"), exc_info=True)
        try:
            MagicEventResolver._record_spell_cast_if_needed(event, ctx, result, tags=event_tags)
        except Exception:
            logger.debug("Wizard cast registry hook failed for spell %s", getattr(event, "name", "spell"), exc_info=True)
        return result
