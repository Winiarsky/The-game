"""Deterministic rules for Mira's stealth-killer archetype."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence

from dnd_board_game.actors import (
    Actor,
    actor_has_feature,
    can_spend_actor_resource,
    spend_actor_resource,
)
from dnd_board_game.rules import (
    ActiveEffect,
    D20RollRequest,
    EffectDuration,
    EffectSource,
    EffectSourceType,
    EffectStackingPolicy,
    RollModifier,
    RollModifierType,
    RollMode,
    ability_modifier,
    apply_active_effect,
)
from dnd_board_game.world import BoardState, Coordinate
from dnd_board_game.actors.resources import uses_shared_mana
from .session import use_bonus_action

from .attack_flow import AttackKind, AttackSource, AttackSourceType
from .conditions import CombatCondition, ConditionApplicationResult, apply_condition
from .session import CombatState, current_actor, replace_actor, use_turn_action


MIRA_ATTACK_ACTION_IDS = frozenset(
    {"hamstring_cut", "piercing_attack", "guard_vault", "blade_mistress"}
)


@dataclass(frozen=True, slots=True)
class MiraFeatureResolution:
    state: CombatState
    active_effects: tuple[ActiveEffect, ...]
    action_id: str


def mira_trick_maximum(actor: Actor) -> int:
    return max(1, ability_modifier(actor.ability_scores.dexterity))


def smoke_screen_perception_penalty(actor: Actor) -> int:
    return -(max(0, ability_modifier(actor.ability_scores.dexterity)) // 2)


def is_mira_rapier_source(source: AttackSource) -> bool:
    return (
        source.source_type == AttackSourceType.WEAPON
        and source.attack_kind == AttackKind.MELEE
        and (source.source_item_id == "rapier" or source.proficiency_id == "rapier")
    )


def is_mira_throwing_knife_source(source: AttackSource) -> bool:
    return (
        source.source_type == AttackSourceType.WEAPON
        and source.attack_kind == AttackKind.RANGED
        and source.thrown
        and (
            source.source_item_id == "throwing_knife"
            or source.proficiency_id == "throwing_knife"
        )
    )


def prepare_mira_attack(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
    *,
    action_id: str,
) -> MiraFeatureResolution:
    """Prepare a named attack; action and Fortel are spent on resolution."""

    actor = current_actor(state)
    if action_id not in MIRA_ATTACK_ACTION_IDS or not actor_has_feature(actor, action_id):
        raise ValueError("Aktywna postać nie posiada tej techniki Miry.")
    if action_id != "guard_vault" and not can_spend_actor_resource(
        actor,
        "trick_uses",
        1,
    ):
        raise ValueError("Brak Forteli na tę technikę Miry.")
    effect = ActiveEffect(
        id=f"mira_attack_prepared:{actor.id}",
        actor_id=str(actor.id),
        kind="mira_attack_prepared",
        label=mira_action_label(action_id),
        object_id=f"class_feature:{action_id}",
        value=0,
        source_actor_id=str(actor.id),
        source=EffectSource(EffectSourceType.ACTION, action_id, mira_action_label(action_id)),
        duration=EffectDuration.UNTIL_TURN_END,
        expiration_actor_id=str(actor.id),
        stacking=EffectStackingPolicy.REPLACE,
        stacking_key=f"mira_attack_prepared:{actor.id}",
    )
    return MiraFeatureResolution(
        state,
        apply_active_effect(active_effects, effect).active_effects,
        action_id,
    )


def resolve_smoke_screen(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
) -> MiraFeatureResolution:
    actor = current_actor(state)
    if not actor_has_feature(actor, "smoke_screen"):
        raise ValueError("Aktywna postać nie posiada Zasłony dymnej.")
    from .runes import uses_runes
    if uses_runes(actor):
        from .smoke import SMOKE_AREA_KIND
        action = use_bonus_action(state)
        if not action.accepted:
            raise ValueError(action.message)
        smoke = ActiveEffect(
            id=f"smoke_screen_area:{actor.id}", actor_id=str(actor.id),
            kind=SMOKE_AREA_KIND, label="Zasłona dymna", object_id="class_feature:smoke_screen",
            value=0, anchor_position=actor.position, source_actor_id=str(actor.id),
            duration=EffectDuration.UNTIL_TURN_END, expiration_actor_id=str(actor.id),
            expiration_event_count=2,
        )
        return MiraFeatureResolution(action.state, apply_active_effect(active_effects, smoke).active_effects,
                                     "smoke_screen")
    action = use_bonus_action(state) if uses_shared_mana(actor) else use_turn_action(state)
    if not action.accepted:
        raise ValueError(action.message)
    spent = spend_actor_resource(actor, "trick_uses", 1)
    updated = replace_actor(action.state, spent.actor_after)
    updated = replace(
        updated,
        hidden_states=tuple(
            hidden for hidden in updated.hidden_states if hidden.actor_id != str(actor.id)
        ),
    )
    effects = tuple(
        effect
        for effect in active_effects
        if not (
            effect.actor_id == str(actor.id)
            and effect.kind in {"smoke_screen_hide_pending", "movement_speed_cap"}
        )
    )
    movement = 10 + 5 * dict(state.shared_mana.pending_boosts).get("move", 0) if state.shared_mana else 15
    for kind, label, value in (
        ("smoke_screen_hide_pending", "Zasłona dymna: nowe ukrycie", 2 if state.shared_mana and dict(state.shared_mana.pending_boosts).get("stealth", 0) else 1),
        ("movement_speed_cap", f"Zasłona dymna: ruch {movement} stóp", movement),
        ("disengage_until_turn_end", "Zasłona dymna: bez ataków okazyjnych", 0),
    ):
        effects = apply_active_effect(
            effects,
            ActiveEffect(
                id=f"{kind}:{actor.id}",
                actor_id=str(actor.id),
                kind=kind,
                label=label,
                object_id="class_feature:smoke_screen",
                value=value,
                source_actor_id=str(actor.id),
                duration=EffectDuration.UNTIL_TURN_END,
                expiration_actor_id=str(actor.id),
                stacking=EffectStackingPolicy.REPLACE,
                stacking_key=f"{kind}:{actor.id}",
            ),
        ).active_effects
    if updated.shared_mana:
        updated = replace(updated, shared_mana=replace(updated.shared_mana, smoke_movement=movement))
    return MiraFeatureResolution(updated, effects, "smoke_screen")


def prepared_mira_attack_source(
    actor: Actor,
    sources: Sequence[AttackSource],
    active_effects: Sequence[ActiveEffect],
) -> AttackSource | None:
    prepared = next(
        (
            effect
            for effect in active_effects
            if effect.actor_id == str(actor.id) and effect.kind == "mira_attack_prepared"
        ),
        None,
    )
    if prepared is None:
        return None
    action_id = prepared.object_id.removeprefix("class_feature:")
    from .runes import uses_runes
    rune_blade = action_id == "blade_mistress" and uses_runes(actor)
    throwing = action_id == "blade_mistress" and not rune_blade
    base = (
        next((source for source in sources
              if source.source_type == AttackSourceType.WEAPON
              and source.id not in MIRA_ATTACK_ACTION_IDS
              and any(item.equipped and item.kind == "weapon"
                      and source.source_item_id in {item.id, item.source_ref}
                      for item in actor.inventory)), None)
        if rune_blade else
        next(
            (source for source in sources if is_mira_throwing_knife_source(source)),
            None,
        )
        if throwing
        else next(
            (source for source in sources if is_mira_rapier_source(source)),
            None,
        )
    )
    if base is None:
        return None
    if rune_blade:
        from .damage import DamageComponentSpec
        from dnd_board_game.rules import DiceExpression
        extra = DamageComponentSpec('rune_blade_mistress', base.damage_components[0].damage_type,
                                    dice=DiceExpression(1, 6), label='Mistrzyni ostrzy: ukrycie')
        base = replace(base, damage_components=(*base.damage_components, extra),
                       damage_hint=base.damage_hint + ' + 1k6')
    request = base.attack_roll_request
    damage_bonus = 2 if action_id == "guard_vault" and not uses_shared_mana(actor) else 0
    if action_id == "guard_vault" and not uses_shared_mana(actor):
        request = replace(
            request,
            modifiers=(
                *request.modifiers,
                RollModifier(
                    "Przeskok przez gardę",
                    2,
                    RollModifierType.FEATURE,
                    stacking_key="guard_vault_attack",
                ),
            ),
        )
    return replace(
        base,
        id=action_id,
        name=mira_action_label(action_id),
        attack_roll_request=request,
        damage_modifier=base.damage_modifier + damage_bonus,
        damage_components=tuple(
            replace(component, modifier=component.modifier + damage_bonus)
            if index == 0 and damage_bonus
            else component
            for index, component in enumerate(base.damage_components)
        ),
        damage_hint=(f"{base.damage_hint} + 2" if damage_bonus else base.damage_hint),
        resource_pool_id=(None if action_id == "guard_vault" else "trick_uses"),
        resource_cost=1,
        tabletop_riders=(*base.tabletop_riders,
            "Wymaga ukrycia przed tym celem. +1k6 obrażeń; własna flanka dodaje kolejne +1k6."
            if rune_blade else _rider_text(action_id)),
    )


def mira_attack_action_id(source_id: str) -> str | None:
    action_id = source_id.partition(":")[0]
    return action_id if action_id in MIRA_ATTACK_ACTION_IDS else None


def blade_mistress_flank_damage(source: AttackSource, flanked: bool) -> AttackSource:
    """Apply the rune card's positional die once, including after revealing Mira."""
    base = next((c for c in source.damage_components if c.id == 'rune_blade_mistress'), None)
    if base is None:
        return source
    components = tuple(c for c in source.damage_components if c.id != 'rune_blade_flank')
    if flanked:
        components += (replace(base, id='rune_blade_flank', label='Mistrzyni ostrzy: flanka'),)
    return replace(source, damage_components=components,
                   damage_hint=' + '.join(c.hint() for c in components))


def rear_tile(attacker: Coordinate, target: Coordinate) -> Coordinate:
    return Coordinate(
        target.col + _sign(target.col - attacker.col),
        target.row + _sign(target.row - attacker.row),
    )


def legal_rear_tile(
    board: BoardState,
    attacker: Actor,
    target: Actor,
    actors: Sequence[Actor],
) -> Coordinate | None:
    destination = rear_tile(attacker.position, target.position)
    if not board.in_bounds(destination) or board.terrain_at(destination).blocks_movement:
        return None
    if board.blocks_edge(target.position, destination):
        return None
    if any(
        actor.position == destination and not actor.is_defeated()
        for actor in actors
        if actor.id not in {attacker.id, target.id}
    ):
        return None
    return destination


def collinear_second_target(
    attacker: Actor,
    first_target: Actor,
    actors: Sequence[Actor],
) -> Actor | None:
    destination = rear_tile(attacker.position, first_target.position)
    candidates = tuple(
        actor
        for actor in actors
        if actor.position == destination
        and actor.faction != attacker.faction
        and not actor.is_defeated()
        and actor.id != first_target.id
    )
    return candidates[0] if len(candidates) == 1 else None


def apply_mira_wound_rider(
    states,
    target: Actor,
    *,
    action_id: str,
    source_actor_id: str,
    applied_damage: int,
    physical_mana: bool = False,
    shared_mana: object | None = None,
) -> ConditionApplicationResult:
    condition = (
        CombatCondition.HAMSTRUNG
        if action_id == "hamstring_cut"
        else CombatCondition.BLEEDING
        if action_id == "blade_mistress"
        else None
    )
    if shared_mana is not None and action_id == "blade_mistress" and not dict(shared_mana.pending_boosts).get("bleed", 0):
        condition = None
    if condition is None or applied_damage < 1:
        return ConditionApplicationResult(tuple(states), False, None, "Brak raniącego trafienia.")
    return apply_condition(
        states,
        target,
        condition,
        source_actor_id=source_actor_id,
        source_label=mira_action_label(action_id),
        source_spell_id=action_id, source_spell_level=0,
        duration=(EffectDuration.UNTIL_DECK_REFRESH if action_id == "blade_mistress" else EffectDuration.UNTIL_TURN_START) if shared_mana is not None else (EffectDuration.UNTIL_TURN_START if action_id == "hamstring_cut" else EffectDuration.UNTIL_TURN_END)
                 if physical_mana else EffectDuration.PERMANENT,
        expiration_actor_id=source_actor_id if shared_mana is not None or action_id == "hamstring_cut" else str(target.id),
        expiration_event_count=2 if physical_mana and shared_mana is None and action_id == "blade_mistress" else 1,
    )


def attack_source_with_instinctive_dodge(source: AttackSource) -> AttackSource:
    request: D20RollRequest = source.attack_roll_request
    mode = RollMode.NORMAL if request.mode == RollMode.ADVANTAGE else RollMode.DISADVANTAGE
    return replace(
        source,
        attack_roll_request=replace(
            request,
            mode=mode,
            modifiers=(
                *request.modifiers,
                RollModifier(
                    "Unik instynktowny Miry",
                    0,
                    RollModifierType.FEATURE,
                    stacking_key="mira_instinctive_dodge",
                ),
            ),
        ),
    )


def mira_action_label(action_id: str) -> str:
    return {
        "hamstring_cut": "Cięcie ścięgna",
        "piercing_attack": "Przeszywający atak",
        "guard_vault": "Przeskok przez gardę",
        "blade_mistress": "Mistrzyni ostrzy",
    }[action_id]


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def _rider_text(action_id: str) -> str:
    return {
        "hamstring_cut": "Wymaga osobistej flanki; po raniącym trafieniu połowi szybkość do leczenia lub oczyszczenia.",
        "piercing_attack": "Wymaga osobistej flanki; po raniącym trafieniu pozwala zaatakować cel dokładnie za pierwszym.",
        "guard_vault": "Wymaga wolnego legalnego pola dokładnie za celem; po ataku Mira przeskakuje na to pole.",
        "blade_mistress": "Wymaga noża, aktywnego skradania i celu, który nie widzi Miry; raniące trafienie wywołuje Krwawienie.",
    }[action_id]


__all__ = [
    "MIRA_ATTACK_ACTION_IDS",
    "MiraFeatureResolution",
    "apply_mira_wound_rider",
    "attack_source_with_instinctive_dodge",
    "collinear_second_target",
    "is_mira_rapier_source",
    "is_mira_throwing_knife_source",
    "legal_rear_tile",
    "mira_attack_action_id",
    "mira_trick_maximum",
    "prepare_mira_attack",
    "prepared_mira_attack_source",
    "rear_tile",
    "resolve_smoke_screen",
    "smoke_screen_perception_penalty",
]
