from __future__ import annotations

import logging
import math

from led_fx import animate_area_wave, animate_projectile_line
from bonuses import BonusEffect, BonusType, build_modifiers_grid
from damage_types import DamageType
from GameObjects.interactions_mixin import prompt_for_roll
from GameObjects.items.inventory import (
    consume_item_instance,
    consume_ready_alchemical_item,
    consume_ready_event_item,
    has_ready_alchemical_item,
    has_ready_event_item,
    missing_alchemical_item_reason,
    missing_event_item_reason,
    ready_event_items,
)
from combat.damage_utils import apply_splash_damage
from combat.degree_of_success import is_critical_success, is_hit, natural_shift_from_roll, resolve_outcome
from statuses import inspire_courage_damage_bonus

from ..attack.attack_base import AttackEventBase, check_concealed
from ..base import ActionCostEvent, EventContext, EventResult
from ..magic.magic_utils import pick_target_in_range, grid_distance_feet
from ..targeting import is_target_blocked_by_tags

logger = logging.getLogger(__name__)


class BaseAlchemicalBombEvent(ActionCostEvent, AttackEventBase):
    """Wspólna logika dla bomb alchemicznych."""

    actions_cost = 2
    range_feet = 20
    default_tags = ["attack_ranged", "ranged_attack", "bomb", "alchemical"]
    target_kind = "enemy"
    max_range_increments = 1

    damage_type: str = DamageType.NORMAL.value
    splash_damage_type: str | None = None
    prompt_description: str | None = None
    tier_choices: tuple[str, ...] = ("lesser", "moderate", "greater", "major")
    required_inventory_event_name: str | None = None

    # per-tier: item_bonus, damage_dice, splash, extra
    tiers: dict[str, dict[str, object]] = {}
    TARGET_LED = [0, 80, 180]
    TARGET_SPLASH_LED = [0, 160, 80]
    TARGET_NO_SPLASH_LED = [200, 120, 0]
    CONFIRM_LED = [180, 180, 0]

    def pre(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzutu bombą.")
        if not self._has_required_item(actor):
            return EventResult.cancelled(message=self._missing_item_reason(actor))
        self._apply_quick_bomber_cost(ctx.actor)
        return super().pre(ctx)

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzutu bombą.")
        source_pos = getattr(actor, "position", None)
        if source_pos is None:
            return EventResult.cancelled(message="Bohater nie stoi na planszy.")

        tier, selected_item = self._resolve_tier_and_item(actor)
        if not tier:
            return EventResult.cancelled(message="Nie wybrano poziomu bomby.")
        tier_data = self.tiers.get(tier)
        if not tier_data:
            return EventResult.cancelled(message="Niepoprawny poziom bomby.")

        tags = self._effective_tags(ctx)
        action_tag = (tags or ["attack_ranged"])[0]
        state = self._get_attack_state(ctx, actor)
        attacks_this_turn = int(state.get("attacks_this_turn", 0) or 0)
        weapon_key = f"bomb:{self.name}"
        weapon_type = "bomb"

        candidates = [
            (enemy, getattr(enemy, "position", None), "enemy")
            for enemy in getattr(ctx.game, "enemies", [])
        ]
        range_increment = max(1, int(self._bomb_range_feet(actor) or 1))
        max_increments = max(1, int(getattr(self, "max_range_increments", 6) or 6))
        max_range = int(range_increment * max_increments)
        ctx.metadata["bomb_splash_target_only"] = False
        if self._sum_status_data(actor, "bomb_splash_primary_only"):
            self._prompt_splash_toggle_info()
            target, target_pos, splash_target_only = self._pick_target_with_splash_toggle(
                ctx,
                source_pos,
                candidates,
                max_range_feet=max_range,
                allowed_kinds=("enemy",),
                tags=tags,
            )
            if splash_target_only is not None:
                ctx.metadata["bomb_splash_target_only"] = splash_target_only
        else:
            target, target_pos = pick_target_in_range(
                ctx,
                source_pos,
                candidates,
                max_range_feet=max_range,
                allowed_kinds=("enemy",),
                tags=tags,
            )
        if target is None or target_pos is None:
            return EventResult.cancelled(message="Brak celu w zasięgu.")

        if selected_item is not None:
            if not consume_item_instance(actor, selected_item):
                return EventResult.cancelled(message=self._missing_item_reason(actor))
        elif not self._consume_required_item(actor):
            return EventResult.cancelled(message=self._missing_item_reason(actor))

        if not check_concealed(ctx, target):
            self._record_attack(
                ctx,
                actor,
                weapon_key=weapon_key,
                weapon_type=weapon_type,
                target=target,
                attack_count=1,
            )
            return EventResult(success=True, consumed_action=self.consumes_action, message="Atak chybia (concealed).")

        target_ac, base_ac, modifier = self._ac_with_bonuses(target, attacker=actor)
        modifier_note = ""
        if modifier:
            sign = "+" if modifier > 0 else ""
            modifier_note = f" (bazowe {base_ac}, modyfikatory {sign}{modifier})"

        distance_ft = max(0, int(grid_distance_feet(source_pos, target_pos) or 0))
        increments = max(1, int(math.ceil(distance_ft / float(range_increment)))) if range_increment > 0 else 1
        range_penalty = max(0, (increments - 1) * 2)

        map_penalty = 0
        if attacks_this_turn >= 1:
            if self._has_trait(tags, "agile"):
                map_penalty = 4 if attacks_this_turn == 1 else 8
            else:
                map_penalty = 5 if attacks_this_turn == 1 else 10
        ranger_map_penalty = self._ranger_map_penalty(
            actor,
            tags=tags,
            attacks_this_turn=attacks_this_turn,
            target=target,
        )
        if ranger_map_penalty is not None:
            map_penalty = int(ranger_map_penalty)

        extra_effects = self._item_bonus_effects(tier, action_tag)
        if range_penalty:
            extra_effects.append(
                BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=range_penalty,
                    tag=action_tag,
                    source="range_penalty",
                    label=f"zasięg {increments}x{range_increment}",
                    is_penalty=True,
                )
            )
        if map_penalty:
            extra_effects.append(
                BonusEffect(
                    type=BonusType.CIRCUMSTANCE,
                    value=map_penalty,
                    tag=action_tag,
                    source="map",
                    label=(
                        "MAP ranger flurry"
                        if ranger_map_penalty is not None
                        else f"MAP{' (agile)' if self._has_trait(tags, 'agile') else ''}"
                    ),
                    is_penalty=True,
                )
            )
        modifier, best_effects, log_lines = self._attack_modifier_details(
            actor, action_tag, target=target, extra_effects=extra_effects
        )
        tier_item_applied = 0
        tier_item_source = f"{self.name}:{tier}"
        for effect in best_effects or []:
            if (
                getattr(effect, "type", None) == BonusType.ITEM
                and str(getattr(effect, "source", "") or "") == tier_item_source
            ):
                try:
                    tier_item_applied = int(getattr(effect, "signed_value", 0) or 0)
                except Exception:
                    tier_item_applied = 0
                break

        weapon_attack_bonus = self._weapon_attack_roll_bonus(actor, tags, is_ranged=True)
        if tier_item_applied:
            weapon_attack_bonus["item_bonus"] = int(weapon_attack_bonus.get("item_bonus", 0) or 0) + int(
                tier_item_applied
            )
            weapon_attack_bonus["total"] = int(weapon_attack_bonus.get("total", 0) or 0) + int(tier_item_applied)
        weapon_roll_mod = int(weapon_attack_bonus.get("total", 0) or 0)
        situational_modifier = int(modifier or 0) - int(tier_item_applied or 0)

        if log_lines:
            try:
                ctx.game.ui_log(f"Modyfikatory ({action_tag}): {', '.join(log_lines)}.")
            except Exception:
                pass
        prompt_lines = self._attack_prompt_breakdown_lines(
            weapon_attack_bonus=weapon_attack_bonus,
            modifier=situational_modifier,
            log_lines=log_lines,
        )
        if range_penalty:
            prompt_lines.append(f"Kara za zasięg: -{range_penalty} ({increments}x{range_increment} stóp).")
        prompt_long = "\n".join(prompt_lines).strip()

        roll_data = self._prompt_for_roll(
            f"Atak {self._event_label()} przeciwko AC {target_ac}",
            layout="test",
            subtitle=f"bazowe {base_ac}{modifier_note}",
            prompt_long=prompt_long,
            modifiers=build_modifiers_grid(best_effects),
            roll_stack=self._attack_roll_stack_payload(
                weapon_attack_bonus=weapon_attack_bonus,
                modifier=situational_modifier,
            ),
            auto_total_modifier=int(weapon_roll_mod + situational_modifier),
            answer_placeholder="Wynik k20",
            return_details=True,
            infer_natural_from_roll=True,
        )
        if isinstance(roll_data, dict):
            roll = int(roll_data.get("roll", 0) or 0)
            natural_shift = int(roll_data.get("natural_shift", 0) or 0)
            if natural_shift == 0:
                raw_roll = int(roll_data.get("raw_roll", roll) or roll)
                natural_shift = natural_shift_from_roll(raw_roll)
            modifier_delta = int(roll_data.get("modifier_delta", 0) or 0)
        else:
            roll = int(roll_data or 0)
            natural_shift = natural_shift_from_roll(roll)
            modifier_delta = 0
        total_roll = roll + weapon_roll_mod + situational_modifier + modifier_delta
        outcome = resolve_outcome(total_roll, target_ac, natural_shift=natural_shift)
        critical = is_critical_success(outcome)
        hit = is_hit(outcome)
        impact_positions = self._bomb_impact_positions(
            ctx.game,
            target_pos,
            splash_enabled=bool(int(tier_data.get("splash", 0) or 0) > 0 and not ctx.metadata.get("bomb_splash_target_only")),
        )
        self._play_bomb_animation(ctx.game, source_pos, target_pos, impact_positions=impact_positions)
        self._record_attack(
            ctx,
            actor,
            weapon_key=weapon_key,
            weapon_type=weapon_type,
            target=target,
            attack_count=1,
        )
        if not hit:
            if str(outcome) == "failure":
                self._apply_splash_on_failure(ctx, target, target_pos, tier_data)
                return EventResult(
                    success=True,
                    consumed_action=self.consumes_action,
                    message="Atak chybia, ale rozprysk trafia.",
                    data={"tier": tier, "critical": False, "hit": False, "outcome": str(outcome)},
                )
            return EventResult(success=True, consumed_action=self.consumes_action, message="Atak chybia.")

        self._apply_on_hit(ctx, target, target_pos, tier, tier_data, critical=critical)

        message = f"{self._event_label()} trafia ({tier})."
        if critical:
            message = f"{self._event_label()} – krytyk! ({tier})."
        return EventResult(
            success=True,
            consumed_action=self.consumes_action,
            message=message,
            data={
                "tier": tier,
                "critical": critical,
            },
        )

    # --- hooks ---
    def _apply_on_hit(self, ctx: EventContext, target, target_pos, tier: str, tier_data: dict[str, object], *, critical: bool = False) -> None:
        self._apply_damage_and_splash(ctx, target, target_pos, tier, tier_data, critical=critical)

    # --- helpers ---
    def _prompt_for_roll(self, *args, **kwargs) -> int:
        return prompt_for_roll(*args, **kwargs)

    def _event_label(self) -> str:
        return getattr(self, "name", "bomba").replace("_", " ").title()

    def _bomb_fx_palette(self) -> list[list[int]]:
        damage_key = str(self.splash_damage_type or self.damage_type or "").strip().lower()
        mapping = {
            DamageType.FIRE.value: [[180, 70, 20], [240, 120, 45], [255, 205, 110]],
            DamageType.ACID.value: [[45, 120, 35], [80, 190, 55], [175, 255, 130]],
            DamageType.COLD.value: [[50, 110, 170], [110, 190, 255], [220, 245, 255]],
            DamageType.ELECTRIC.value: [[70, 90, 210], [170, 220, 255], [255, 245, 150]],
            DamageType.SONIC.value: [[120, 70, 180], [200, 120, 255], [255, 210, 255]],
            DamageType.PIERCING.value: [[130, 95, 40], [210, 155, 80], [255, 220, 150]],
            DamageType.BLUDGEONING.value: [[125, 95, 65], [185, 145, 110], [245, 220, 190]],
        }
        return [list(color) for color in mapping.get(damage_key, [[130, 95, 40], [210, 155, 80], [255, 220, 150]])]

    def _bomb_impact_positions(
        self,
        game,
        target_pos: tuple[int, int] | None,
        *,
        splash_enabled: bool,
    ) -> list[tuple[int, int]]:
        if target_pos is None:
            return []
        if not splash_enabled:
            return [tuple(target_pos)]
        board = getattr(game, "board", None)
        neighbors = getattr(board, "get_neighbors", None)
        if callable(neighbors):
            try:
                return [tuple(pos) for pos in neighbors(target_pos, include_position=True, diagonal=True)]
            except Exception:
                pass
        return [tuple(target_pos)]

    def _play_bomb_animation(
        self,
        game,
        start: tuple[int, int] | None,
        end: tuple[int, int] | None,
        *,
        impact_positions: list[tuple[int, int]] | None = None,
    ) -> None:
        conn = getattr(game, "conn", None)
        palette = self._bomb_fx_palette()
        try:
            animate_projectile_line(
                conn,
                start,
                end,
                trail_color=palette[0],
                head_color=palette[1],
                impact_color=palette[-1],
            )
        except Exception:
            logger.debug("Nie udało się odtworzyć lotu bomby.", exc_info=True)
        try:
            animate_area_wave(
                conn,
                end,
                impact_positions or [end] if end is not None else [],
                palette=palette,
            )
        except Exception:
            logger.debug("Nie udało się odtworzyć efektu rozprysku bomby.", exc_info=True)

    def _required_event_name(self) -> str:
        explicit = str(getattr(self, "required_inventory_event_name", "") or "").strip().lower()
        if explicit:
            return explicit
        return str(getattr(self, "name", "") or "").strip().lower()

    def _has_required_item(self, actor) -> bool:
        event_name = self._required_event_name()
        if getattr(self, "required_inventory_event_name", None):
            return bool(has_ready_event_item(actor, event_name))
        return bool(has_ready_alchemical_item(actor, event_name))

    def _missing_item_reason(self, actor) -> str:
        event_name = self._required_event_name()
        if getattr(self, "required_inventory_event_name", None):
            return str(missing_event_item_reason(actor, event_name))
        return str(missing_alchemical_item_reason(actor, event_name))

    def _consume_required_item(self, actor) -> bool:
        event_name = self._required_event_name()
        if getattr(self, "required_inventory_event_name", None):
            return bool(consume_ready_event_item(actor, event_name))
        return bool(consume_ready_alchemical_item(actor, event_name))

    def _ready_required_items(self, actor) -> list[object]:
        event_name = self._required_event_name()
        return list(ready_event_items(actor, event_name) or [])

    def _item_tier(self, item) -> str | None:
        allowed = set(self.tiers.keys())
        raw_tier = str(getattr(item, "alchemical_tier", "") or "").strip().lower()
        if raw_tier in allowed:
            return raw_tier
        for source in (
            getattr(item, "item_id", None),
            getattr(item, "name", None),
            getattr(item, "event_name", None),
        ):
            token = str(source or "").strip().lower().replace("-", "_").replace(" ", "_")
            if not token:
                continue
            if "major" in token and "major" in allowed:
                return "major"
            if "greater" in token and "greater" in allowed:
                return "greater"
            if "moderate" in token and "moderate" in allowed:
                return "moderate"
            if ("lesser" in token or "minor" in token) and "lesser" in allowed:
                return "lesser"
        return None

    def _resolve_tier_and_item(self, actor) -> tuple[str | None, object | None]:
        ready_items = self._ready_required_items(actor)
        if not ready_items:
            return self._prompt_level(), None

        grouped: dict[str, list[object]] = {}
        for item in ready_items:
            tier = self._item_tier(item)
            if tier and tier in self.tiers:
                grouped.setdefault(tier, []).append(item)

        available_tiers = [tier for tier in self.tier_choices if tier in grouped]
        if not available_tiers:
            return self._prompt_level(), None
        if len(available_tiers) == 1:
            tier = available_tiers[0]
            return tier, grouped.get(tier, [None])[0]

        tier = self._prompt_level_with_choices(available_tiers, grouped)
        if not tier:
            return None, None
        return tier, grouped.get(tier, [None])[0]

    def _bomb_range_feet(self, actor) -> int:
        try:
            base_range = int(self.range_feet)
        except Exception:
            base_range = 0
        bonus = self._sum_status_data(actor, "bomb_range_bonus")
        return max(0, base_range + bonus)

    def _apply_quick_bomber_cost(self, actor) -> None:
        try:
            base_cost = int(self.actions_cost)
        except Exception:
            base_cost = 1
        reduction = self._sum_status_data(actor, "bomb_action_cost_reduction")
        if reduction:
            self.actions_cost = max(1, base_cost - int(reduction))

    def _prompt_splash_toggle_info(self) -> None:
        try:
            from ui_client import get_ui_client

            get_ui_client().prompt_info(
                "Rozprysk bomby (Bomber)",
                prompt_long=(
                    "Kliknij cel aby wybrać (domyślnie ze splashem).\n"
                    "Kliknij ten sam cel, by przełączać splash on/off.\n"
                    "Kliknij swoje pole, aby zatwierdzić wybór."
                ),
                source=self.name,
            )
        except Exception:
            pass

    def _pick_target_with_splash_toggle(
        self,
        ctx: EventContext,
        source_pos: tuple[int, int],
        candidates: list[tuple[object, tuple[int, int], str]],
        *,
        max_range_feet: int | None,
        allowed_kinds: tuple[str, ...] = ("enemy",),
        tags: list[str] | None = None,
    ):
        if not source_pos:
            return None, None, None

        valid: list[tuple[object, tuple[int, int], str, int]] = []
        for obj, pos, kind in candidates:
            if pos is None or kind not in allowed_kinds:
                continue
            if is_target_blocked_by_tags(obj, tags):
                continue
            dist = grid_distance_feet(source_pos, pos)
            if max_range_feet is not None and dist > max_range_feet:
                continue
            valid.append((obj, pos, kind, dist))

        if not valid:
            return None, None, None

        pos_to_obj = {pos: obj for obj, pos, _kind, _dist in valid}
        selected_pos = None
        splash_enabled = True

        try:
            while True:
                positions: list[tuple[int, int]] = []
                colors: list[list[int]] = []
                for _obj, pos, _kind, _dist in valid:
                    positions.append(pos)
                    if selected_pos == pos:
                        colors.append(self.TARGET_SPLASH_LED if splash_enabled else self.TARGET_NO_SPLASH_LED)
                    else:
                        colors.append(self.TARGET_LED)
                positions.append(source_pos)
                colors.append(self.CONFIRM_LED)

                try:
                    ctx.game.conn.set_leds(positions, colors)
                except Exception:
                    pass

                try:
                    choice = ctx.game.conn.scan_board(positions)
                except Exception:
                    choice = None

                if choice is None:
                    return None, None, None
                if choice == source_pos:
                    if selected_pos is None:
                        return None, None, None
                    return pos_to_obj.get(selected_pos), selected_pos, not splash_enabled
                if choice not in pos_to_obj:
                    continue
                if selected_pos == choice:
                    splash_enabled = not splash_enabled
                    self._log_splash_mode(ctx, splash_enabled)
                else:
                    selected_pos = choice
                    splash_enabled = True
                    self._log_splash_mode(ctx, splash_enabled)
        finally:
            try:
                ctx.game.conn.leds_off()
            except Exception:
                pass

    @staticmethod
    def _sum_status_data(actor, key: str) -> int:
        total = 0
        if actor is None:
            return total
        for status in getattr(actor, "statuses", []) or []:
            data = getattr(status, "data", None) or {}
            try:
                total += int(data.get(key, 0) or 0)
            except Exception:
                continue
        return total

    def _log_splash_mode(self, ctx: EventContext, splash_enabled: bool) -> None:
        mode = "splash ON (obszar)" if splash_enabled else "splash OFF (tylko cel)"
        hint_text = "Kliknij cel, aby przełączyć; swoje pole = zatwierdź."
        try:
            ctx.game.ui_log(f"Bomber: {mode}. {hint_text}")
        except Exception:
            pass
        try:
            ui_idle_hint = getattr(ctx.game, "ui_idle_hint", None)
            if callable(ui_idle_hint):
                ui_idle_hint(f"Bomber: {mode}", hint_text)
        except Exception:
            pass

    def _item_bonus_effects(self, tier: str, action_tag: str) -> list[BonusEffect]:
        tier_data = self.tiers.get(tier, {})
        item_bonus = int(tier_data.get("item_bonus", 0) or 0)
        if not item_bonus:
            return []
        return [
            BonusEffect(
                type=BonusType.ITEM,
                value=item_bonus,
                tag=action_tag,
                source=f"{self.name}:{tier}",
                label=f"{self.name} ({tier})",
            )
        ]

    def _prompt_level(self) -> str | None:
        return self._prompt_level_with_choices(list(self.tier_choices), None)

    def _prompt_level_with_choices(
        self,
        choices: list[str],
        grouped_items: dict[str, list[object]] | None = None,
    ) -> str | None:
        from ui_client import get_ui_client

        ui = get_ui_client()
        if self.prompt_description:
            try:
                ui.prompt_info(self._event_label(), prompt_long=self.prompt_description, source=self.name)
            except Exception:
                pass
        normalized_choices = [str(choice).strip().lower() for choice in list(choices or []) if str(choice).strip()]
        if not normalized_choices:
            normalized_choices = list(self.tier_choices)
        display_choices = list(normalized_choices)
        if grouped_items:
            decorated: list[str] = []
            for choice in normalized_choices:
                count = len(list(grouped_items.get(choice) or []))
                decorated.append(f"{choice} ({count})")
            display_choices = decorated
        choice = ui.prompt_choice(
            f"Wybierz poziom {self._event_label()}:",
            choices=display_choices,
            source=self.name,
        )
        if choice is None:
            return None
        raw = str(choice).strip().lower().replace("-", "_").replace(" ", "_")
        if "(" in raw:
            raw = raw.split("(", 1)[0].strip()
        if raw in normalized_choices:
            return raw
        for option in normalized_choices:
            if raw.startswith(option[0]):
                return option
        return None

    def _prompt_damage(self, tier: str, dice: str) -> int:
        from ui_client import get_ui_client

        ui = get_ui_client()
        val = ui.prompt_roll(
            f"{self._event_label()} ({tier}) – podaj obrażenia ({dice}):",
            source=self.name,
            layout="damage",
            answer_placeholder="Obrażenia",
        )
        return int(val or 0)

    def _apply_damage_and_splash(
        self,
        ctx: EventContext,
        target,
        target_pos,
        tier: str,
        tier_data: dict[str, object],
        *,
        critical: bool = False,
    ) -> None:
        dmg_dice = tier_data.get("damage_dice")
        if dmg_dice:
            dmg = self._prompt_damage(tier, str(dmg_dice))
            if critical:
                dmg *= 2
            dmg += int(inspire_courage_damage_bonus(ctx.actor) or 0)
            self._apply_damage(target, dmg, self.damage_type)

        splash = int(tier_data.get("splash", 0) or 0)
        splash_type = self.splash_damage_type or self.damage_type
        if splash > 0:
            if ctx.metadata.get("bomb_splash_target_only"):
                self._apply_damage(target, splash, splash_type)
                return
            self._apply_damage(target, splash, splash_type)
            apply_splash_damage(
                ctx.game,
                target_pos,
                splash,
                splash_type,
                exclude=target,
                info_title=f"{self._event_label()} – splash",
                source=self.name,
            )

    def _apply_splash_on_failure(self, ctx: EventContext, target, target_pos, tier_data: dict[str, object]) -> None:
        splash = int(tier_data.get("splash", 0) or 0)
        if splash <= 0:
            return
        splash_type = self.splash_damage_type or self.damage_type
        if ctx.metadata.get("bomb_splash_target_only"):
            self._apply_damage(target, splash, splash_type)
            return
        self._apply_damage(target, splash, splash_type)
        apply_splash_damage(
            ctx.game,
            target_pos,
            splash,
            splash_type,
            exclude=target,
            info_title=f"{self._event_label()} – splash",
            source=self.name,
        )

    def _apply_damage(self, target, amount: int, damage_type: str) -> bool:
        defeated = False
        apply = getattr(target, "apply_damage", None)
        if callable(apply):
            try:
                _, defeated = apply(max(0, int(amount)), damage_type)
            except Exception as exc:
                logger.debug("Nie udało się zadać obrażeń (%s): %s", self.name, exc)
        return defeated
