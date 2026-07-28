"""Deterministic multi-target spell damage such as Magic Missile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from dnd_board_game.actions import ActionResourceResolver
from dnd_board_game.actors import Actor, Faction
from dnd_board_game.combat import (
    ActionEconomyCost,
    AppliedDamageResult,
    AttackSource,
    AttackSourceType,
    CombatState,
    DamageComponentInput,
    DamageType,
    current_actor,
    legal_attack_targets,
    replace_actor,
)
from dnd_board_game.combat.damage import apply_damage_result, resolve_damage
from dnd_board_game.rules import D20RollRequest
from dnd_board_game.world import BoardState


class MultiTargetDamageSpellSpec(Protocol):
    id: str
    name: str
    action_type: str
    spell_level: int
    range_feet: int
    action_cost: ActionEconomyCost
    projectile_count: int
    upcast_projectiles_per_level: int
    damage_die_sides: int
    damage_modifier: int
    damage_type: str
    resource_pool_id: str | None
    resource_cost: int
    cast_flag: str
    projectile_attack_roll: bool
    projectile_damage_dice_count: int


@dataclass(frozen=True, slots=True)
class PendingMultiTargetDamageSpell:
    caster_id: str
    action_id: str
    cast_level: int
    legal_target_ids: tuple[str, ...]
    projectile_count: int
    selected_target_ids: tuple[str, ...] = ()
    projectile_attack_roll: bool = False
    damage_dice_count: int = 1
    damage_die_sides: int = 4


@dataclass(frozen=True, slots=True)
class ProjectileAllocation:
    target_id: str
    die_roll: int
    natural_roll: int | None = None


@dataclass(frozen=True, slots=True)
class MultiTargetDamageSpellTransition:
    state: CombatState
    pending: PendingMultiTargetDamageSpell | None
    applied_damages: tuple[AppliedDamageResult, ...]
    board_message: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]
    scene_flag_changes: tuple[tuple[str, object], ...] = ()


class PlayerMultiTargetSpellFlowService:
    def __init__(self) -> None:
        self._resources = ActionResourceResolver()

    def start(
        self,
        *,
        state: CombatState,
        board: BoardState,
        action: MultiTargetDamageSpellSpec,
        cast_level: int | None,
    ) -> MultiTargetDamageSpellTransition:
        caster = _active_hero(state)
        if action.action_type != "multi_target_damage":
            raise ValueError("To nie jest wielocelowy czar obrażeń.")
        selected_level = int(cast_level or action.spell_level)
        if selected_level < action.spell_level:
            raise ValueError("Poziom slotu jest niższy od poziomu czaru.")
        projectile_count = action.projectile_count + (
            selected_level - action.spell_level
        ) * action.upcast_projectiles_per_level
        source = AttackSource(
            id=action.id,
            name=action.name,
            source_type=AttackSourceType.SPELL,
            range_feet=action.range_feet,
            attack_roll_request=D20RollRequest(),
        )
        targets = legal_attack_targets(board, caster, state.actors, source)
        if not targets:
            raise ValueError("Brak widocznych przeciwników w zasięgu czaru.")
        pending = PendingMultiTargetDamageSpell(
            caster_id=str(caster.id),
            action_id=action.id,
            cast_level=selected_level,
            legal_target_ids=tuple(target.id for target in targets),
            projectile_count=projectile_count,
            projectile_attack_roll=bool(
                getattr(action, "projectile_attack_roll", False)
            ),
            damage_dice_count=int(
                getattr(action, "projectile_damage_dice_count", 1)
            ),
            damage_die_sides=action.damage_die_sides,
        )
        return MultiTargetDamageSpellTransition(
            state=state,
            pending=pending,
            applied_damages=(),
            board_message=(
                f"{action.name}: rozdziel {projectile_count} pocisków pomiędzy "
                "podświetlone cele."
            ),
            message_title=action.name,
            message_body=(
                f"Wybierz cele dla {projectile_count} pocisków. Każdy wymaga "
                f"fizycznego rzutu k{action.damage_die_sides}."
            ),
            event_type="ui_combat_multi_target_spell_started",
            event_payload=(
                ("caster_id", str(caster.id)),
                ("spell_id", action.id),
                ("cast_level", selected_level),
                ("projectile_count", projectile_count),
                ("legal_target_ids", list(pending.legal_target_ids)),
            ),
        )

    def confirm(
        self,
        *,
        state: CombatState,
        action: MultiTargetDamageSpellSpec,
        pending: PendingMultiTargetDamageSpell,
        allocations: tuple[ProjectileAllocation, ...],
    ) -> MultiTargetDamageSpellTransition:
        caster = _active_hero(state)
        if str(caster.id) != pending.caster_id or action.id != pending.action_id:
            raise ValueError("Oczekujący czar nie należy do aktywnego aktora.")
        if len(allocations) != pending.projectile_count:
            raise ValueError(
                f"Rozdziel dokładnie {pending.projectile_count} pocisków."
            )
        if tuple(item.target_id for item in allocations) != pending.selected_target_ids:
            raise ValueError("Wyniki kości nie odpowiadają wybranym celom pocisków.")
        legal_ids = set(pending.legal_target_ids)
        if any(allocation.target_id not in legal_ids for allocation in allocations):
            raise ValueError("Wybrano nielegalny cel pocisku.")
        maximum_damage_roll = (
            int(getattr(action, "projectile_damage_dice_count", 1))
            * action.damage_die_sides
        )
        minimum_damage_roll = int(
            getattr(action, "projectile_damage_dice_count", 1)
        )
        if any(
            not minimum_damage_roll <= allocation.die_roll <= maximum_damage_roll
            for allocation in allocations
        ):
            raise ValueError(
                f"Każdy wynik obrażeń musi mieścić się w zakresie "
                f"{minimum_damage_roll}–{maximum_damage_roll}."
            )
        requires_attack = bool(getattr(action, "projectile_attack_roll", False))
        if requires_attack and any(
            allocation.natural_roll is None
            or not 1 <= allocation.natural_roll <= 20
            for allocation in allocations
        ):
            raise ValueError("Każdy promień wymaga wyniku fizycznego d20.")
        resource = self._resources.consume_action_and_source_resource(
            state,
            caster,
            spell_level=action.spell_level,
            spell_id=action.id,
            cast_level=pending.cast_level,
            action_cost=action.action_cost,
            resource_pool_id=action.resource_pool_id,
            resource_cost=action.resource_cost,
        )
        damage_type = DamageType(action.damage_type)
        totals: dict[str, int] = {}
        attack_modifier = caster.spell_save_dc - 8
        hit_results: list[bool] = []
        for allocation in allocations:
            target = next(
                actor
                for actor in resource.state.actors
                if str(actor.id) == allocation.target_id
            )
            hit = not requires_attack or (
                allocation.natural_roll == 20
                or (
                    allocation.natural_roll != 1
                    and int(allocation.natural_roll or 0) + attack_modifier
                    >= target.ac
                )
            )
            hit_results.append(hit)
            if not hit:
                continue
            totals[allocation.target_id] = (
                totals.get(allocation.target_id, 0)
                + allocation.die_roll
                + action.damage_modifier
            )
        updated_state = resource.state
        applied: list[AppliedDamageResult] = []
        for target_id, amount in totals.items():
            target = next(
                actor
                for actor in updated_state.actors
                if str(actor.id) == target_id
            )
            result = apply_damage_result(
                target,
                resolve_damage((DamageComponentInput(amount, damage_type),)),
            )
            updated_state = replace_actor(updated_state, result.actor_after)
            applied.append(result)
        details = ", ".join(
            f"{result.actor_before.name}: {result.damage.total_applied}"
            for result in applied
        )
        return MultiTargetDamageSpellTransition(
            state=updated_state,
            pending=None,
            applied_damages=tuple(applied),
            board_message="",
            message_title=action.name,
            message_body=(
                f"{action.name}: {sum(hit_results)}/{len(hit_results)} "
                f"pocisków trafia. {details or 'Brak obrażeń'}."
                if requires_attack
                else f"{action.name} trafia automatycznie. {details}."
            ),
            event_type="ui_combat_multi_target_spell_resolved",
            event_payload=(
                ("caster_id", str(caster.id)),
                ("spell_id", action.id),
                ("cast_level", pending.cast_level),
                (
                    "allocations",
                    [
                        {
                            "target_id": allocation.target_id,
                            "die_roll": allocation.die_roll,
                            "natural_roll": allocation.natural_roll,
                            "hit": hit_results[index],
                            "damage": allocation.die_roll + action.damage_modifier,
                        }
                        for index, allocation in enumerate(allocations)
                    ],
                ),
                (
                    "target_totals",
                    [
                        {"target_id": target_id, "damage": amount}
                        for target_id, amount in totals.items()
                    ],
                ),
            ),
            scene_flag_changes=((action.cast_flag, True),),
        )

    def select_target(
        self,
        pending: PendingMultiTargetDamageSpell,
        target_id: str,
    ) -> PendingMultiTargetDamageSpell:
        if target_id not in pending.legal_target_ids:
            raise ValueError("Wybrano nielegalny cel pocisku.")
        if len(pending.selected_target_ids) >= pending.projectile_count:
            raise ValueError("Wszystkie pociski mają już wybrane cele.")
        return PendingMultiTargetDamageSpell(
            caster_id=pending.caster_id,
            action_id=pending.action_id,
            cast_level=pending.cast_level,
            legal_target_ids=pending.legal_target_ids,
            projectile_count=pending.projectile_count,
            selected_target_ids=(*pending.selected_target_ids, target_id),
            projectile_attack_roll=pending.projectile_attack_roll,
            damage_dice_count=pending.damage_dice_count,
            damage_die_sides=pending.damage_die_sides,
        )

    def clear_targets(
        self,
        pending: PendingMultiTargetDamageSpell,
    ) -> PendingMultiTargetDamageSpell:
        return PendingMultiTargetDamageSpell(
            caster_id=pending.caster_id,
            action_id=pending.action_id,
            cast_level=pending.cast_level,
            legal_target_ids=pending.legal_target_ids,
            projectile_count=pending.projectile_count,
            projectile_attack_roll=pending.projectile_attack_roll,
            damage_dice_count=pending.damage_dice_count,
            damage_die_sides=pending.damage_die_sides,
        )

    def cancel(
        self,
        *,
        state: CombatState,
        pending: PendingMultiTargetDamageSpell,
    ) -> MultiTargetDamageSpellTransition:
        return MultiTargetDamageSpellTransition(
            state=state,
            pending=None,
            applied_damages=(),
            board_message="Anulowano wybór celów czaru.",
            message_title="Czar anulowany",
            message_body="Nie zużyto akcji ani slotu.",
            event_type="ui_combat_multi_target_spell_cancelled",
            event_payload=(("spell_id", pending.action_id),),
        )


def _active_hero(state: CombatState) -> Actor:
    actor = current_actor(state)
    if actor.faction != Faction.ALLY:
        raise ValueError("To nie jest tura bohatera.")
    return actor


__all__ = [
    "MultiTargetDamageSpellTransition",
    "PendingMultiTargetDamageSpell",
    "PlayerMultiTargetSpellFlowService",
    "ProjectileAllocation",
]
