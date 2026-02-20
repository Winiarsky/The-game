from __future__ import annotations

import logging

from bonuses import BonusEffect, BonusType, build_modifiers_grid
from damage_types import DamageType
from statuses import make_persistent_damage
from GameObjects.interactions_mixin import prompt_for_roll
from combat.damage_utils import apply_splash_damage

from .attack.attack_base import AttackEventBase, check_concealed
from .base import EventContext, EventResult
from .magic.magic_utils import pick_target_in_range
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class AcidFlaskEvent(AttackEventBase):
    name = "acidflask"
    actions_cost = 1
    range_feet = 20
    default_tags = ["attack_ranged", "ranged_attack", "bomb", "alchemical"]
    prompt = "Acid Flask – rzuć butelkę kwasu w cel."

    _TIERS = {
        "lesser": {"item_bonus": 0, "persistent": "1d6", "splash": 1},
        "moderate": {"item_bonus": 1, "persistent": "2d6", "splash": 2},
        "greater": {"item_bonus": 2, "persistent": "3d6", "splash": 3},
        "major": {"item_bonus": 3, "persistent": "4d6", "splash": 4},
    }

    _PROMPT_DESC = (
        "Type lesser; Level 1; Price 3 gp\n"
        "It deals 1d6 persistent acid damage and 1 acid splash damage.\n"
        "Type moderate; Level 3; Price 10 gp\n"
        "You gain a +1 item bonus to attack rolls. The bomb deals 2d6\n"
        "persistent acid damage and 2 acid splash damage.\n"
        "Type greater; Level 11; Price 250 gp\n"
        "You gain a +2 item bonus to attack rolls. The bomb deals\n"
        "3d6 persistent acid damage and 3 acid splash damage.\n"
        "Type major; Level 17; Price 2,500 gp\n"
        "You gain a +3 item bonus to attack rolls. The bomb deals\n"
        "4d6 persistent acid damage and 4 acid splash damage."
    )

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzutu Acid Flask.")
        source_pos = getattr(actor, "position", None)
        if source_pos is None:
            return EventResult.cancelled(message="Bohater nie stoi na planszy.")

        tier = self._prompt_level()
        if not tier:
            return EventResult.cancelled(message="Nie wybrano poziomu Acid Flask.")
        tier_data = self._TIERS.get(tier)
        if not tier_data:
            return EventResult.cancelled(message="Niepoprawny poziom Acid Flask.")

        candidates = [
            (enemy, getattr(enemy, "position", None), "enemy")
            for enemy in getattr(ctx.game, "enemies", [])
        ]
        target, target_pos = pick_target_in_range(
            ctx,
            source_pos,
            candidates,
            max_range_feet=self.range_feet,
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
        extra_effects = []
        item_bonus = int(tier_data["item_bonus"])
        if item_bonus:
            extra_effects.append(
                BonusEffect(
                    type=BonusType.ITEM,
                    value=item_bonus,
                    tag=action_tag,
                    source=f"acid_flask:{tier}",
                    label=f"acid flask ({tier})",
                )
            )
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
            f"Atak Acid Flask przeciwko AC {target_ac}",
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

        persistent_value = self._prompt_persistent(tier, tier_data["persistent"])
        if persistent_value and persistent_value > 0:
            try:
                target.add_status(make_persistent_damage(persistent_value, DamageType.ACID.value, source=self.name))
            except Exception as exc:
                logger.debug("Nie udało się dodać persistent acid: %s", exc)

        splash = int(tier_data["splash"])
        if splash > 0:
            apply_splash_damage(
                ctx.game,
                target_pos,
                splash,
                DamageType.ACID.value,
                exclude=target,
                info_title="Acid Splash",
                source="acid_flask",
            )

        message = f"Acid Flask trafia ({tier})."
        if critical:
            message = f"Acid Flask – krytyk! ({tier})."
        return EventResult(
            success=True,
            consumed_action=self.consumes_action,
            message=message,
            data={
                "tier": tier,
                "critical": critical,
                "persistent_damage": persistent_value,
                "splash_damage": splash,
            },
        )

    def _prompt_level(self) -> str | None:
        from ui_client import get_ui_client

        ui = get_ui_client()
        try:
            ui.prompt_info("Acid Flask", prompt_long=self._PROMPT_DESC, source="acid_flask")
        except Exception:
            pass
        choice = ui.prompt_choice(
            "Wybierz poziom Acid Flask:",
            choices=["lesser", "moderate", "greater", "major"],
            source="acid_flask",
        )
        if choice is None:
            return None
        raw = str(choice).strip().lower()
        if raw in self._TIERS:
            return raw
        if raw.startswith("l"):
            return "lesser"
        if raw.startswith("m"):
            return "moderate"
        if raw.startswith("g"):
            return "greater"
        if raw.startswith("maj"):
            return "major"
        return None

    def _prompt_persistent(self, tier: str, dice: str) -> int:
        from ui_client import get_ui_client

        ui = get_ui_client()
        val = ui.prompt_roll(
            f"Acid Flask ({tier}) – podaj obrażenia persistent acid ({dice}):",
            source="acid_flask",
            layout="damage",
            answer_placeholder="Persistent acid",
        )
        return int(val or 0)
