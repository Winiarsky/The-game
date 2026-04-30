from __future__ import annotations

from collections import OrderedDict

from board import consts
from bonuses import BonusEffect, BonusType
from combat import refresh_flanking_statuses
from combat.damage_utils import remove_defeated_enemy
from combat.hp_engine import apply_damage as hp_apply_damage
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from GameObjects.items.inventory import get_equipped_weapons
from GameObjects.items.weapon import normalize_weapon_id
from skills import Skill
from statuses.classes.ranger.ranger_utils import (
    hunter_edge,
    hunted_prey_id,
    mark_monster_hunter_used,
    monster_hunter_used_targets,
    refresh_outwit_bonus,
    set_crossbow_ace_ready,
    set_hunted_prey,
)

from .attack.attack_event import _select_weapon_from_equipped, _weapon_event_name
from .base import ActionCostEvent, EventContext, EventResult, mapping_get_actor, mapping_setdefault_actor
from .registry import dispatch_event, list_events, register_event


def _actor_id(actor) -> str:
    return str(getattr(actor, "object_id", None) or getattr(actor, "name", None) or id(actor))


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


def _remove_status(actor, status_id: str) -> None:
    if actor is None:
        return
    remover = getattr(actor, "remove_status", None)
    if callable(remover):
        try:
            remover(status_id)
        except Exception:
            pass


def _hunted_target(ctx: EventContext, actor):
    target_id = hunted_prey_id(actor)
    if not target_id:
        return None
    for item in list(getattr(ctx.game, "enemies", []) or []) + list(getattr(ctx.game, "heroes", []) or []):
        if _actor_id(item) == target_id and getattr(item, "position", None) is not None:
            return item
    return None


def _prompt_info(ctx: EventContext, title: str, text: str, *, source: str) -> None:
    ui = getattr(ctx.game, "ui", None)
    if ui is not None and hasattr(ui, "prompt_info"):
        try:
            ui.prompt_info(title, prompt_long=text, source=source)
            return
        except Exception:
            pass
    try:
        ctx.game.ui_log(text)
    except Exception:
        pass


def _equipped_melee_weapons(actor) -> list[object]:
    equipped = list(get_equipped_weapons(actor) or [])
    out: list[object] = []
    for weapon in equipped:
        if bool(getattr(weapon, "ranged", False)):
            continue
        out.append(weapon)
    return out


def _equipped_ranged_weapons(actor) -> list[object]:
    equipped = list(get_equipped_weapons(actor) or [])
    out: list[object] = []
    for weapon in equipped:
        if not bool(getattr(weapon, "ranged", False)):
            continue
        reload_value = getattr(weapon, "reload", 0)
        try:
            reload_value = int(reload_value)
        except Exception:
            reload_value = 0
        if reload_value > 0:
            continue
        out.append(weapon)
    return out


def _weapon_hands(weapon: object) -> int:
    try:
        return 2 if int(getattr(weapon, "hands_required", 1) or 1) >= 2 else 1
    except Exception:
        return 1


def _current_attacks_this_turn(ctx: EventContext, actor) -> int:
    state = getattr(ctx.game, "state", None)
    if not ctx.in_combat or state is None:
        return 0
    attack_state = getattr(state, "attack_state", None)
    if not isinstance(attack_state, dict):
        return 0
    payload = mapping_get_actor(attack_state, actor, {}) or {}
    if not isinstance(payload, dict):
        return 0
    try:
        return max(0, int(payload.get("attacks_this_turn", 0) or 0))
    except Exception:
        return 0


def _event_weapon_key(event_name: str) -> str:
    cls = list_events().get(str(event_name).strip().lower())
    if cls is None:
        return str(event_name)
    return str(getattr(cls, "action_id_base", event_name) or event_name)


def _bump_attack_state(ctx: EventContext, actor, *, event_name: str, count: int = 1) -> None:
    if not ctx.in_combat:
        return
    state = getattr(ctx.game, "state", None)
    if state is None:
        return
    attack_state = getattr(state, "attack_state", None)
    if not isinstance(attack_state, dict):
        return
    try:
        amount = max(0, int(count))
    except Exception:
        amount = 0
    if amount <= 0:
        return
    payload = mapping_setdefault_actor(attack_state, actor, dict)
    if not isinstance(payload, dict):
        return
    payload["attacks_this_turn"] = int(payload.get("attacks_this_turn", 0) or 0) + amount
    weapon_counts = payload.setdefault("weapon_counts", {})
    weapon_key = _event_weapon_key(event_name)
    weapon_counts[weapon_key] = int(weapon_counts.get(weapon_key, 0) or 0) + amount


def _merge_damage_components(*groups: list[tuple[str, int]]) -> list[tuple[str, int]]:
    merged: "OrderedDict[str, int]" = OrderedDict()
    for group in groups:
        for dmg_type, amount in group:
            dtype = str(dmg_type or "").strip().lower()
            if not dtype:
                continue
            try:
                value = max(0, int(amount or 0))
            except Exception:
                value = 0
            if value <= 0:
                continue
            merged[dtype] = int(merged.get(dtype, 0) or 0) + value
    return [(dtype, amount) for dtype, amount in merged.items() if amount > 0]


def _apply_merged_damage(target, damage_components: list[tuple[str, int]], *, source: str) -> bool:
    defeated = False
    applier = getattr(target, "apply_damage", None)
    for dmg_type, amount in damage_components:
        if defeated:
            break
        value = max(0, int(amount or 0))
        if value <= 0:
            continue
        if callable(applier):
            try:
                _, defeated = applier(value, str(dmg_type))
                continue
            except Exception:
                pass
        info = hp_apply_damage(target, value, str(dmg_type), source=source)
        defeated = bool((info or {}).get("defeated", False))
    return bool(defeated)


def _remove_defeated_target(game, target, target_pos) -> None:
    pos = target_pos if isinstance(target_pos, tuple) else getattr(target, "position", None)
    if target in getattr(game, "enemies", []):
        try:
            remove_defeated_enemy(game, target, position=pos, source="ranger_feat")
            return
        except Exception:
            pass
    if isinstance(pos, tuple):
        try:
            game.board.remove(pos)
        except Exception:
            pass
    try:
        if target in getattr(game, "heroes", []):
            game.heroes.remove(target)
    except Exception:
        pass
    try:
        target.position = None
    except Exception:
        pass


def _apply_monster_hunter_attack_bonus(ctx: EventContext, target) -> None:
    target_id = _actor_id(target)
    for ally in list(getattr(ctx.game, "heroes", []) or []):
        adder = getattr(ally, "add_bonus", None)
        if not callable(adder):
            continue
        for tag in ("attack_melee", "attack_ranged"):
            try:
                adder(
                    BonusEffect(
                        type=BonusType.CIRCUMSTANCE,
                        value=1,
                        tag=tag,
                        source="ranger:monster_hunter:attack",
                        target_id=target_id,
                        label="monster hunter",
                    )
                )
            except Exception:
                continue


def _target_tags(target) -> set[str]:
    tags: set[str] = set()
    if target is None:
        return tags
    has_tag = getattr(target, "has_tag", None)
    if callable(has_tag):
        for key in (
            "undead",
            "construct",
            "dragon",
            "aberration",
            "ooze",
            "beast",
            "animal",
            "plant",
            "fungus",
            "elemental",
            "fiend",
            "celestial",
            "spirit",
            "humanoid",
            "magical",
        ):
            try:
                if bool(has_tag(key)):
                    tags.add(key)
            except Exception:
                continue
    raw_tags = getattr(target, "tags", None)
    if isinstance(raw_tags, (list, tuple, set)):
        for item in raw_tags:
            raw = str(item or "").strip().lower()
            if raw:
                tags.add(raw)
    enemy_type = str(getattr(target, "enemy_type", "") or "").strip().lower()
    if enemy_type:
        tags.add(enemy_type)
    return tags


def _monster_hunter_recall_profile(target) -> tuple[str, int]:
    tags = _target_tags(target)
    skill = Skill.NATURE.value
    if tags.intersection({"undead", "fiend", "celestial", "spirit"}):
        skill = Skill.RELIGION.value
    elif "construct" in tags:
        skill = Skill.CRAFTING.value
    elif tags.intersection({"dragon", "magical"}):
        skill = Skill.ARCANA.value
    elif tags.intersection({"aberration", "ooze"}):
        skill = Skill.OCCULTISM.value
    elif tags.intersection({"humanoid", "human", "orc", "goblin"}):
        skill = Skill.SOCIETY.value
    elif tags.intersection({"animal", "beast", "plant", "fungus", "elemental"}):
        skill = Skill.NATURE.value

    dc = 15
    level = getattr(target, "level", None)
    try:
        if level is not None:
            dc = max(10, min(45, 14 + int(level)))
        else:
            ac = int(getattr(target, "ac", 0) or 0)
            if ac > 0:
                dc = max(10, min(45, ac + 2))
    except Exception:
        dc = 15
    return skill, dc


def _refresh_companion_outwit_bonus(companion, target) -> None:
    if companion is None:
        return
    source = "ranger:outwit:companion:ac"
    remove_bonus = getattr(companion, "remove_bonuses_by_source", None)
    if callable(remove_bonus):
        try:
            remove_bonus(source)
        except Exception:
            pass
    if str(getattr(companion, "ranger_hunter_edge", "") or "").strip().lower() != "outwit":
        return
    target_id = _actor_id(target)
    if not target_id:
        return
    adder = getattr(companion, "add_bonus", None)
    if not callable(adder):
        return
    try:
        adder(
            BonusEffect(
                type=BonusType.CIRCUMSTANCE,
                value=1,
                tag="ac",
                source=source,
                target_id=target_id,
                label="outwit companion",
            )
        )
    except Exception:
        pass


def _equipped_crossbow_id(actor) -> str | None:
    for weapon in list(get_equipped_weapons(actor) or []):
        if not bool(getattr(weapon, "ranged", False)):
            continue
        normalized_id = normalize_weapon_id(getattr(weapon, "item_id", None))
        traits = {str(item or "").strip().lower() for item in (getattr(weapon, "traits", None) or ())}
        if "crossbow" in traits:
            return normalized_id or str(getattr(weapon, "item_id", None) or "crossbow")
        if normalized_id and "crossbow" in normalized_id:
            return normalized_id
    return None


@register_event
class HuntPreyEvent(ActionCostEvent):
    name = "hunt_prey"
    default_tags = ["ranger", "concentrate"]
    actions_cost = 1
    consumes_action = True
    available_in_combat = True
    available_in_exploration = False

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Wyznacz ofiare: brak aktora.")
        if not _has_status(actor, "hunt_prey"):
            return EventResult.cancelled(message="Wyznacz ofiare: wymaga cechy klasowej Wyznacz ofiare.")

        candidates = []
        for enemy in list(getattr(ctx.game, "enemies", []) or []):
            pos = getattr(enemy, "position", None)
            if pos is None:
                continue
            candidates.append((enemy, pos))
        if not candidates:
            return EventResult.cancelled(message="Wyznacz ofiare: brak celu do oznaczenia.")

        target = None
        target_pos = None
        if len(candidates) == 1:
            target, target_pos = candidates[0]
        else:
            positions = [pos for _enemy, pos in candidates]
            selected = None
            _prompt_info(
                ctx,
                "Wyznacz ofiarę",
                (
                    "Wskaż na planszy przeciwnika, którego oznaczasz jako hunted prey.\n"
                    "Ten wybór nie odnawia się co turę. Trwa, dopóki nie oznaczysz nowej ofiary albo obecny cel przestanie być ważny."
                ),
                source=self.name,
            )
            ui_idle_hint = getattr(ctx.game, "ui_idle_hint", None)
            if callable(ui_idle_hint):
                ui_idle_hint(
                    "Wyznacz ofiarę",
                    "Kliknij podświetlonego przeciwnika na planszy.",
                )
            try:
                ctx.game.conn.set_leds(positions, [0, 120, 20])
                selected = ctx.game.conn.scan_board(positions)
            finally:
                try:
                    ctx.game.conn.leds_off()
                except Exception:
                    pass
            for enemy, pos in candidates:
                if pos == selected:
                    target = enemy
                    target_pos = pos
                    break
            if target is None:
                return EventResult.cancelled(message="Wyznacz ofiare: nie wybrano poprawnego celu.")

        set_hunted_prey(actor, target, position=target_pos)
        refresh_outwit_bonus(actor)

        try:
            combat_state = getattr(ctx.game, "state", None)
            getter = getattr(combat_state, "get_animal_companion", None)
            if callable(getter):
                companion = getter(actor)
                if companion is not None:
                    setattr(companion, "ranger_hunted_prey_target_id", _actor_id(target))
                    setattr(companion, "ranger_hunter_edge", hunter_edge(actor))
                    _refresh_companion_outwit_bonus(companion, target)
        except Exception:
            pass

        messages = [f"Wyznacz ofiare: oznaczono cel ({getattr(target, 'name', 'cel')})."]

        if _has_status(actor, "crossbow_ace"):
            crossbow_id = _equipped_crossbow_id(actor)
            if crossbow_id:
                set_crossbow_ace_ready(actor, crossbow_id, source="hunt_prey")
                messages.append("Crossbow Ace: +2 dmg do następnego Strike kuszą (simple crossbow: +1 die step).")

        if _has_status(actor, "monster_hunter"):
            used_targets = monster_hunter_used_targets(actor)
            target_id = _actor_id(target)
            if target_id in used_targets:
                messages.append("Monster Hunter: bonus dla tego celu został już użyty dzisiaj.")
            else:
                skill_id, dc = _monster_hunter_recall_profile(target)
                resolution = resolve_skill_check_with_sources(
                    skill_id=skill_id,
                    dc=dc,
                    actor=actor,
                    target=target,
                    tags=["knowledge", "recall_knowledge", "monster_hunter"],
                    game=ctx.game,
                    apply_modifiers=True,
                    consume_statuses=True,
                )
                outcome = str(getattr(resolution, "outcome", "") or "")
                if outcome == "critical_success":
                    mark_monster_hunter_used(actor, target)
                    _apply_monster_hunter_attack_bonus(ctx, target)
                    messages.append("Monster Hunter: krytyczny sukces, +1 do następnego ataku przeciw celowi.")
                else:
                    messages.append(
                        f"Monster Hunter: Recall Knowledge ({skill_id}, DC {dc}) = {outcome or 'brak'}."
                    )

        try:
            ctx.game.events.safe_emit_action(
                actor=actor,
                action_id=self.name,
                action_tags=self._effective_tags(ctx),
                target=target,
                target_pos=target_pos,
                summary=" ".join(messages).strip(),
            )
        except Exception:
            pass

        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=1,
            message=" ".join(messages).strip(),
            data={
                "target": target,
                "target_pos": target_pos,
                "target_id": _actor_id(target),
            },
        )


@register_event
class HuntedShotEvent(ActionCostEvent):
    name = "hunted_shot"
    default_tags = ["ranger", "attack_ranged", "attack", "flourish"]
    actions_cost = 1
    consumes_action = True
    available_in_combat = True
    available_in_exploration = False

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Strzal na cel: brak aktora.")
        if not _has_status(actor, "hunted_shot"):
            return EventResult.cancelled(message="Strzal na cel: wymaga featu Strzal na cel.")
        prey = _hunted_target(ctx, actor)
        if prey is None:
            return EventResult.cancelled(
                message="Strzal na cel: brak aktywnej oznaczonej ofiary. Jesli poprzedni cel padl, uzyj ponownie Wyznacz ofiare."
            )

        ranged_weapons = _equipped_ranged_weapons(actor)
        if not ranged_weapons:
            return EventResult.cancelled(message="Strzal na cel: wymaga aktywnej broni dystansowej z reload 0.")
        chosen = _select_weapon_from_equipped(ctx, ranged_weapons)
        if chosen is None:
            return EventResult.cancelled(message="Strzal na cel: nie wybrano broni dystansowej.")
        event_name = _weapon_event_name(chosen)
        if not event_name:
            return EventResult.cancelled(message="Strzal na cel: brak eventu ataku dla wybranej broni.")

        initial_attacks = _current_attacks_this_turn(ctx, actor)
        base_metadata = dict(ctx.metadata or {})
        forced_pos = getattr(prey, "position", None)

        first_result = dispatch_event(
            str(event_name),
            EventContext(
                game=ctx.game,
                actor=actor,
                tags=list(ctx.tags or []),
                metadata={
                    **base_metadata,
                    "fixed_attacks_this_turn": initial_attacks,
                    "forced_target": prey,
                    "forced_target_pos": forced_pos,
                    "suppress_attack_record": True,
                    "roll_only": True,
                },
            ),
        )
        if not first_result.success:
            return EventResult.cancelled(message=first_result.message or "Strzal na cel: pierwszy atak przerwany.")
        second_result = dispatch_event(
            str(event_name),
            EventContext(
                game=ctx.game,
                actor=actor,
                tags=list(ctx.tags or []),
                metadata={
                    **base_metadata,
                    "fixed_attacks_this_turn": initial_attacks,
                    "forced_target": prey,
                    "forced_target_pos": forced_pos,
                    "suppress_attack_record": True,
                    "roll_only": True,
                },
            ),
        )
        if not second_result.success:
            return EventResult.cancelled(message=second_result.message or "Strzal na cel: drugi atak przerwany.")

        _bump_attack_state(ctx, actor, event_name=str(event_name), count=2)

        first_data = dict(first_result.data or {})
        second_data = dict(second_result.data or {})
        first_hit = bool(first_data.get("hit", False))
        second_hit = bool(second_data.get("hit", False))
        hit_count = int(first_hit) + int(second_hit)

        target = prey
        target_pos = getattr(prey, "position", None)
        defeated = False
        if first_hit and second_hit:
            merged = _merge_damage_components(
                list(first_data.get("damage_components") or []),
                list(second_data.get("damage_components") or []),
            )
            if merged:
                defeated = _apply_merged_damage(target, merged, source="ranger:hunted_shot")
                if defeated:
                    _remove_defeated_target(ctx.game, target, target_pos)
                try:
                    refresh_flanking_statuses(ctx.game)
                except Exception:
                    pass
                ctx.game.events.safe_emit_action(
                    actor=actor,
                    action_id=self.name,
                    action_tags=self._effective_tags(ctx),
                    target=target,
                    target_pos=target_pos,
                    damage=sum(max(0, int(amount or 0)) for _dtype, amount in merged),
                    damage_components=merged,
                    defeated=defeated,
                )
        else:
            for payload in (first_data, second_data):
                if not bool(payload.get("hit", False)):
                    continue
                components = list(payload.get("damage_components") or [])
                if not components:
                    continue
                this_defeated = _apply_merged_damage(target, components, source="ranger:hunted_shot")
                defeated = defeated or this_defeated
                if this_defeated:
                    _remove_defeated_target(ctx.game, target, target_pos)
                ctx.game.events.safe_emit_action(
                    actor=actor,
                    action_id=self.name,
                    action_tags=self._effective_tags(ctx),
                    target=target,
                    target_pos=target_pos,
                    damage=sum(max(0, int(amount or 0)) for _dtype, amount in components),
                    damage_components=components,
                    defeated=this_defeated,
                )

        msg = f"Strzal na cel: trafienia {hit_count}/2."
        if defeated:
            msg += " Przeciwnik pokonany."

        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=1,
            message=msg,
            data={"first": first_data, "second": second_data, "defeated": defeated},
        )


@register_event
class TwinTakedownEvent(ActionCostEvent):
    name = "twin_takedown"
    default_tags = ["ranger", "attack_melee", "attack", "flourish"]
    actions_cost = 1
    consumes_action = True
    available_in_combat = True
    available_in_exploration = False

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Twin Takedown: brak aktora.")
        if not _has_status(actor, "twin_takedown"):
            return EventResult.cancelled(message="Twin Takedown: wymaga featu Twin Takedown.")
        prey = _hunted_target(ctx, actor)
        if prey is None:
            return EventResult.cancelled(message="Twin Takedown: brak aktywnego hunted prey.")

        melee_weapons = [weapon for weapon in _equipped_melee_weapons(actor) if _weapon_hands(weapon) == 1]
        if len(melee_weapons) < 2:
            return EventResult.cancelled(message="Twin Takedown: wymagane dwie bronie melee 1H.")

        first_weapon = melee_weapons[0]
        second_weapon = melee_weapons[1]
        first_event = _weapon_event_name(first_weapon)
        second_event = _weapon_event_name(second_weapon)
        if not first_event or not second_event:
            return EventResult.cancelled(message="Twin Takedown: brak eventu ataku dla aktywnych broni.")

        initial_attacks = _current_attacks_this_turn(ctx, actor)
        base_metadata = dict(ctx.metadata or {})
        forced_pos = getattr(prey, "position", None)

        first_result = dispatch_event(
            str(first_event),
            EventContext(
                game=ctx.game,
                actor=actor,
                tags=list(ctx.tags or []),
                metadata={
                    **base_metadata,
                    "fixed_attacks_this_turn": initial_attacks,
                    "forced_target": prey,
                    "forced_target_pos": forced_pos,
                    "suppress_attack_record": True,
                    "roll_only": True,
                },
            ),
        )
        if not first_result.success:
            return EventResult.cancelled(message=first_result.message or "Twin Takedown: pierwszy atak przerwany.")
        second_result = dispatch_event(
            str(second_event),
            EventContext(
                game=ctx.game,
                actor=actor,
                tags=list(ctx.tags or []),
                metadata={
                    **base_metadata,
                    "fixed_attacks_this_turn": initial_attacks + 1,
                    "forced_target": prey,
                    "forced_target_pos": forced_pos,
                    "suppress_attack_record": True,
                    "roll_only": True,
                },
            ),
        )
        if not second_result.success:
            return EventResult.cancelled(message=second_result.message or "Twin Takedown: drugi atak przerwany.")

        _bump_attack_state(ctx, actor, event_name=str(first_event), count=1)
        _bump_attack_state(ctx, actor, event_name=str(second_event), count=1)

        first_data = dict(first_result.data or {})
        second_data = dict(second_result.data or {})
        first_hit = bool(first_data.get("hit", False))
        second_hit = bool(second_data.get("hit", False))
        hit_count = int(first_hit) + int(second_hit)

        target = prey
        target_pos = getattr(prey, "position", None)
        defeated = False
        if first_hit and second_hit:
            merged = _merge_damage_components(
                list(first_data.get("damage_components") or []),
                list(second_data.get("damage_components") or []),
            )
            if merged:
                defeated = _apply_merged_damage(target, merged, source="ranger:twin_takedown")
                if defeated:
                    _remove_defeated_target(ctx.game, target, target_pos)
                try:
                    refresh_flanking_statuses(ctx.game)
                except Exception:
                    pass
                ctx.game.events.safe_emit_action(
                    actor=actor,
                    action_id=self.name,
                    action_tags=self._effective_tags(ctx),
                    target=target,
                    target_pos=target_pos,
                    damage=sum(max(0, int(amount or 0)) for _dtype, amount in merged),
                    damage_components=merged,
                    defeated=defeated,
                )
        else:
            for payload in (first_data, second_data):
                if not bool(payload.get("hit", False)):
                    continue
                components = list(payload.get("damage_components") or [])
                if not components:
                    continue
                this_defeated = _apply_merged_damage(target, components, source="ranger:twin_takedown")
                defeated = defeated or this_defeated
                if this_defeated:
                    _remove_defeated_target(ctx.game, target, target_pos)
                ctx.game.events.safe_emit_action(
                    actor=actor,
                    action_id=self.name,
                    action_tags=self._effective_tags(ctx),
                    target=target,
                    target_pos=target_pos,
                    damage=sum(max(0, int(amount or 0)) for _dtype, amount in components),
                    damage_components=components,
                    defeated=this_defeated,
                )

        msg = f"Twin Takedown: trafienia {hit_count}/2."
        if defeated:
            msg += " Przeciwnik pokonany."

        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=1,
            message=msg,
            data={"first": first_data, "second": second_data, "defeated": defeated},
        )
