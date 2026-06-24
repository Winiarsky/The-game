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
            getter = getattr(actor, "get_status_data", None)
            profile = None
            from_source = None

            def _profile_from_status(status_id: str):
                if callable(getter):
                    try:
                        status_profile = getter(status_id, "unarmed_profile", None)
                        if status_profile:
                            return status_profile
                    except Exception:
                        pass
                for item in getattr(actor, "statuses", []) or []:
                    if getattr(item, "id", None) != status_id:
                        continue
                    data = getattr(item, "data", None) or {}
                    status_profile = data.get("unarmed_profile")
                    if status_profile:
                        return status_profile
                return None

            profile = _profile_from_status("monk_stance_active")
            if profile:
                from_source = "monk_stance"
            if not profile:
                profile = _profile_from_status("wild_shape_active")
                if profile:
                    from_source = "wild_shape"
            if not profile:
                profile = _profile_from_status("wild_morph_active")
                if profile:
                    from_source = "wild_morph"

            if not profile:
                has_status = getattr(actor, "has_status", None)
                has_rage = False
                if callable(has_status):
                    try:
                        has_rage = bool(has_status("rage"))
                    except Exception:
                        has_rage = False
                else:
                    for item in getattr(actor, "statuses", []) or []:
                        if getattr(item, "id", None) == "rage" or item == "rage":
                            has_rage = True
                            break
                if has_rage:
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
                        from_source = "animal_instinct"

            if profile:
                original_prompt = self.damage_prompt
                original_type = self.damage_type
                original_label = self.weapon_label
                original_tags = list(getattr(ctx, "tags", []) or [])
                original_metadata = dict(getattr(ctx, "metadata", {}) or {})
                try:
                    ctx.metadata = dict(original_metadata)
                    if from_source == "animal_instinct":
                        ctx.metadata["skip_dragon_instinct"] = True
                        ctx.metadata["skip_spirit_instinct"] = True
                    label = profile.get("label")
                    dice = profile.get("damage_dice") or profile.get("damage_prompt")
                    dtype = profile.get("damage_type")
                    extra_tags = list(profile.get("tags", []) or profile.get("extra_tags", []) or [])
                    reach_feet = int(profile.get("reach_feet", 0) or 0)
                    persistent = profile.get("on_hit_persistent_damage")
                    if label:
                        self.weapon_label = str(label)
                    if dice:
                        text = str(dice).strip()
                        lowered = text.lower()
                        has_formula = any(token in lowered for token in ("+", "-", "str", "si", "dex", "zr"))
                        has_dice = ("k" in lowered) or ("d" in lowered)
                        if has_formula:
                            self.damage_prompt = text
                        elif has_dice:
                            self.damage_prompt = f"{text} + STR"
                        else:
                            self.damage_prompt = f"{text} + STR"
                    if dtype:
                        self.damage_type = dtype
                    if reach_feet >= 10:
                        extra_tags.append(f"reach:{reach_feet}")
                    if extra_tags:
                        ctx.tags = list(dict.fromkeys(original_tags + extra_tags))
                    if persistent:
                        ctx.metadata["on_hit_persistent_damage"] = persistent
                    return super().execute(ctx)
                finally:
                    self.damage_prompt = original_prompt
                    self.damage_type = original_type
                    self.weapon_label = original_label
                    ctx.tags = original_tags
                    ctx.metadata = original_metadata
        return super().execute(ctx)
