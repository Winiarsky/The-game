from __future__ import annotations

from ..registry import register_event
from .basic_melee_attack_event import BasicMeleeAttackEvent
from damage_types import DamageType


@register_event
class UnarmedAttackEvent(BasicMeleeAttackEvent):
    name = "unarmed"
    weapon_label = "pięścią"
    damage_prompt = "1k4 + STR"
    action_id_base = "attack_unarmed"
    default_tags = ["attack_melee", "finesse", "agile", "unarmed"]
    damage_type = DamageType.BLUDGEONING.value

    def execute(self, ctx):  # type: ignore[override]
        actor = getattr(ctx, "actor", None)
        tags = self._effective_tags(ctx)
        if actor is not None and "unarmed" in tags:
            has_status = getattr(actor, "has_status", None)
            has_rage = False
            if callable(has_status):
                try:
                    has_rage = has_status("rage")
                except Exception:
                    has_rage = False
            else:
                for item in getattr(actor, "statuses", []) or []:
                    if getattr(item, "id", None) == "rage" or item == "rage":
                        has_rage = True
                        break
            if has_rage:
                getter = getattr(actor, "get_status_data", None)
                if callable(getter):
                    profile = getter("animal_instinct_active", "animal_instinct_profile", None)
                else:
                    profile = None
                    for item in getattr(actor, "statuses", []) or []:
                        if getattr(item, "id", None) != "animal_instinct_active":
                            continue
                        data = getattr(item, "data", None) or {}
                        profile = data.get("animal_instinct_profile")
                        break
                if profile:
                    original_prompt = self.damage_prompt
                    original_type = self.damage_type
                    original_tags = list(getattr(ctx, "tags", []) or [])
                    try:
                        ctx.metadata = dict(getattr(ctx, "metadata", {}) or {})
                        ctx.metadata["skip_dragon_instinct"] = True
                        ctx.metadata["skip_spirit_instinct"] = True
                        dice = profile.get("damage_dice")
                        dtype = profile.get("damage_type")
                        extra_tags = list(profile.get("tags", []) or [])
                        if dice:
                            self.damage_prompt = f"{dice} + STR"
                        if dtype:
                            self.damage_type = dtype
                        if extra_tags:
                            ctx.tags = list(dict.fromkeys(original_tags + extra_tags))
                        return super().execute(ctx)
                    finally:
                        self.damage_prompt = original_prompt
                        self.damage_type = original_type
                        ctx.tags = original_tags
                        ctx.metadata.pop("skip_dragon_instinct", None)
                        ctx.metadata.pop("skip_spirit_instinct", None)
        return super().execute(ctx)
