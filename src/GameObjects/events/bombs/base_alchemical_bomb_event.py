from __future__ import annotations

import logging

from bonuses import BonusEffect, BonusType, build_modifiers_grid
from damage_types import DamageType
from GameObjects.interactions_mixin import prompt_for_roll
from combat.damage_utils import apply_splash_damage

from ..attack.attack_base import AttackEventBase, check_concealed
from ..base import ActionCostEvent, EventContext, EventResult
from ..magic.magic_utils import pick_target_in_range

logger = logging.getLogger(__name__)


class BaseAlchemicalBombEvent(ActionCostEvent, AttackEventBase):
    """Wspólna logika dla bomb alchemicznych."""

    actions_cost = 2
    range_feet = 20
    default_tags = ["attack_ranged", "ranged_attack", "bomb", "alchemical"]
    target_kind = "enemy"

    damage_type: str = DamageType.NORMAL.value
    splash_damage_type: str | None = None
    prompt_description: str | None = None
    tier_choices: tuple[str, ...] = ("lesser", "moderate", "greater", "major")

    # per-tier: item_bonus, damage_dice, splash, extra
    tiers: dict[str, dict[str, object]] = {}

    def pre(self, ctx: EventContext) -> EventResult:
        self._apply_quick_bomber_cost(ctx.actor)
        return super().pre(ctx)

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzutu bombą.")
        source_pos = getattr(actor, "position", None)
        if source_pos is None:
            return EventResult.cancelled(message="Bohater nie stoi na planszy.")

        tier = self._prompt_level()
        if not tier:
            return EventResult.cancelled(message="Nie wybrano poziomu bomby.")
        tier_data = self.tiers.get(tier)
        if not tier_data:
            return EventResult.cancelled(message="Niepoprawny poziom bomby.")

        candidates = [
            (enemy, getattr(enemy, "position", None), "enemy")
            for enemy in getattr(ctx.game, "enemies", [])
        ]
        max_range = self._bomb_range_feet(actor)
        target, target_pos = pick_target_in_range(
            ctx,
            source_pos,
            candidates,
            max_range_feet=max_range,
            allowed_kinds=("enemy",),
            tags=self._effective_tags(ctx),
        )
        if target is None or target_pos is None:
            return EventResult.cancelled(message="Brak celu w zasięgu.")

        if not check_concealed(ctx, target):
            return EventResult(success=True, consumed_action=self.consumes_action, message="Atak chybia (concealed).")

        target_ac, base_ac, modifier = self._ac_with_bonuses(target, attacker=actor)
        modifier_note = ""
        if modifier:
            sign = "+" if modifier > 0 else ""
            modifier_note = f" (bazowe {base_ac}, modyfikatory {sign}{modifier})"

        action_tag = (self._effective_tags(ctx) or ["attack_ranged"])[0]
        extra_effects = self._item_bonus_effects(tier, action_tag)
        modifier, best_effects, log_lines = self._attack_modifier_details(
            actor, action_tag, target=target, extra_effects=extra_effects
        )
        if log_lines:
            try:
                ctx.game.ui_log(f"Modyfikatory ({action_tag}): {', '.join(log_lines)}.")
            except Exception:
                pass
        prompt_long = f"Modyfikator łączny: {modifier:+d} (doliczany automatycznie)."

        roll = prompt_for_roll(
            f"Atak {self._event_label()} przeciwko AC {target_ac}",
            layout="test",
            subtitle=f"bazowe {base_ac}{modifier_note}",
            prompt_long=prompt_long,
            modifiers=build_modifiers_grid(best_effects),
            answer_placeholder="Wynik k20",
        )
        total_roll = roll + modifier
        critical = total_roll >= target_ac + 10
        hit = total_roll >= target_ac
        if not hit:
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
        self._apply_damage_and_splash(ctx, target, target_pos, tier, tier_data)

    # --- helpers ---
    def _event_label(self) -> str:
        return getattr(self, "name", "bomba").replace("_", " ").title()

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
        from ui_client import get_ui_client

        ui = get_ui_client()
        if self.prompt_description:
            try:
                ui.prompt_info(self._event_label(), prompt_long=self.prompt_description, source=self.name)
            except Exception:
                pass
        choice = ui.prompt_choice(
            f"Wybierz poziom {self._event_label()}:",
            choices=list(self.tier_choices),
            source=self.name,
        )
        if choice is None:
            return None
        raw = str(choice).strip().lower()
        if raw in self.tiers:
            return raw
        for option in self.tier_choices:
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

    def _apply_damage_and_splash(self, ctx: EventContext, target, target_pos, tier: str, tier_data: dict[str, object]) -> None:
        dmg_dice = tier_data.get("damage_dice")
        if dmg_dice:
            dmg = self._prompt_damage(tier, str(dmg_dice))
            self._apply_damage(target, dmg, self.damage_type)

        splash = int(tier_data.get("splash", 0) or 0)
        splash_type = self.splash_damage_type or self.damage_type
        if splash > 0:
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
