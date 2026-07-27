"""Deterministic state transitions for interactive scene fixtures."""

from __future__ import annotations

from dataclasses import dataclass, replace

from dnd_board_game.combat import SceneObject, SetupVisibility

from .models import (
    ExplorationState,
    FixtureActionPolicy,
    FixtureKind,
    FixtureOperation,
    FixtureRuntimeState,
    SceneFixture,
)


@dataclass(frozen=True, slots=True)
class FixtureActionPlan:
    source_id: str
    zone_id: str
    fixture: SceneFixture
    policy: FixtureActionPolicy
    current_condition: str

    def as_payload(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "zone_id": self.zone_id,
            "fixture_id": self.fixture.id,
            "fixture_label": self.fixture.name,
            "operation": self.policy.operation.value,
            "current_condition": self.current_condition,
            "result_condition": self.policy.result_condition,
            "ability": self.policy.ability,
            "skill": self.policy.skill,
            "difficulty_tier": self.policy.difficulty_tier,
            "progress_on_success": self.policy.progress_on_success,
            "progress_on_failure": self.policy.progress_on_failure,
            "success_noise": self.policy.success_noise,
            "failure_noise": self.policy.failure_noise,
            "failure_complication": self.policy.failure_complication,
            "makes_fixture_unavailable": self.policy.makes_fixture_unavailable,
            "release_yield_item_ids": (
                [item.id for item in self.fixture.yield_items]
                if self.policy.release_yield_items
                else []
            ),
        }


@dataclass(frozen=True, slots=True)
class FixtureActionResult:
    state: ExplorationState
    plan: FixtureActionPlan
    changed: bool
    released_item_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FixtureDamageResult:
    state: ExplorationState
    fixture: SceneFixture
    previous_hit_points: int
    current_hit_points: int
    raw_damage: int
    applied_damage: int
    destroyed: bool
    released_item_ids: tuple[str, ...] = ()


def fixture_runtime_state(
    state: ExplorationState,
    *,
    zone_id: str,
    fixture: SceneFixture,
) -> FixtureRuntimeState:
    return next(
        (
            item
            for item in state.fixture_states
            if item.zone_id == zone_id and item.fixture_id == fixture.id
        ),
        FixtureRuntimeState(
            zone_id=zone_id,
            fixture_id=fixture.id,
            condition=fixture.condition,
            opened=fixture.initially_open,
            locked=fixture.initially_locked,
            current_hit_points=fixture.hit_points,
        ),
    )


def plan_fixture_action(
    state: ExplorationState,
    *,
    source_id: str,
    operation: FixtureOperation,
) -> FixtureActionPlan:
    for zone in state.zones:
        for fixture in zone.fixtures:
            expected_source_id = f"zone:{zone.id}:fixture:{fixture.id}"
            if expected_source_id != source_id:
                continue
            runtime = fixture_runtime_state(state, zone_id=zone.id, fixture=fixture)
            if runtime.unavailable or runtime.detached or runtime.destroyed:
                raise ValueError(f"{fixture.name} nie jest już dostępny dla tej operacji.")
            if operation == FixtureOperation.OPEN:
                if runtime.locked:
                    raise ValueError(f"{fixture.name} jest zamknięty na zamek.")
                if runtime.opened:
                    raise ValueError(f"{fixture.name} jest już otwarty.")
            elif operation == FixtureOperation.CLOSE and not runtime.opened:
                raise ValueError(f"{fixture.name} jest już zamknięty.")
            elif operation == FixtureOperation.UNLOCK and not runtime.locked:
                raise ValueError(f"{fixture.name} nie jest zamknięty na zamek.")
            elif operation == FixtureOperation.LOOT:
                if fixture.kind != FixtureKind.CONTAINER:
                    raise ValueError(f"{fixture.name} nie jest pojemnikiem.")
                if not runtime.opened:
                    raise ValueError(f"Najpierw otwórz: {fixture.name}.")
                if runtime.looted:
                    raise ValueError(f"{fixture.name} został już opróżniony.")
            elif operation in {FixtureOperation.DAMAGE, FixtureOperation.DESTROY}:
                if not fixture.destructible:
                    raise ValueError(f"{fixture.name} nie jest obiektem niszczalnym.")
            policy = next(
                (item for item in fixture.action_policies if item.operation == operation),
                None,
            )
            if policy is None:
                raise ValueError(
                    f"Operacja {operation.value} nie jest dozwolona dla elementu {fixture.name}."
                )
            if policy.allowed_conditions and runtime.condition not in policy.allowed_conditions:
                raise ValueError(
                    f"Operacja {operation.value} nie pasuje do obecnego stanu {runtime.condition}."
                )
            return FixtureActionPlan(
                source_id=source_id,
                zone_id=zone.id,
                fixture=fixture,
                policy=policy,
                current_condition=runtime.condition,
            )
    raise ValueError("Wskazany fixture nie istnieje w aktualnym scenariuszu.")


def apply_fixture_action(
    state: ExplorationState,
    plan: FixtureActionPlan,
    *,
    success: bool,
) -> FixtureActionResult:
    current_plan = plan_fixture_action(
        state,
        source_id=plan.source_id,
        operation=plan.policy.operation,
    )
    if not success:
        return FixtureActionResult(state=state, plan=current_plan, changed=False)
    previous = fixture_runtime_state(
        state,
        zone_id=current_plan.zone_id,
        fixture=current_plan.fixture,
    )
    released = (
        tuple(item.id for item in current_plan.fixture.yield_items)
        if (
            current_plan.policy.release_yield_items
            or current_plan.policy.operation == FixtureOperation.LOOT
        )
        else ()
    )
    operation = current_plan.policy.operation
    destroyed = operation == FixtureOperation.DESTROY
    updated = replace(
        previous,
        condition=current_plan.policy.result_condition,
        unavailable=(
            current_plan.policy.makes_fixture_unavailable
            or operation in {FixtureOperation.DETACH, FixtureOperation.DESTROY}
        ),
        detached=operation == FixtureOperation.DETACH,
        destroyed=destroyed,
        opened=(
            False
            if operation in {FixtureOperation.CLOSE, FixtureOperation.DESTROY}
            else True
            if operation == FixtureOperation.OPEN
            else previous.opened
        ),
        locked=(
            False
            if operation in {
                FixtureOperation.UNLOCK,
                FixtureOperation.DESTROY,
            }
            else previous.locked
        ),
        looted=previous.looted or operation == FixtureOperation.LOOT,
        current_hit_points=0 if destroyed else previous.current_hit_points,
        released_item_ids=tuple(dict.fromkeys((*previous.released_item_ids, *released))),
    )
    remaining = tuple(
        item
        for item in state.fixture_states
        if not (item.zone_id == updated.zone_id and item.fixture_id == updated.fixture_id)
    )
    return FixtureActionResult(
        state=replace(state, fixture_states=(*remaining, updated)),
        plan=current_plan,
        changed=True,
        released_item_ids=released,
    )


def apply_fixture_damage(
    state: ExplorationState,
    *,
    source_id: str,
    raw_damage: int,
) -> FixtureDamageResult:
    if raw_damage < 0:
        raise ValueError("Fixture damage cannot be negative.")
    zone_id, fixture = _fixture_from_source_id(state, source_id)
    if not fixture.destructible or fixture.hit_points is None:
        raise ValueError(f"{fixture.name} nie jest obiektem niszczalnym.")
    previous = fixture_runtime_state(state, zone_id=zone_id, fixture=fixture)
    if previous.destroyed:
        raise ValueError(f"{fixture.name} jest już zniszczony.")
    previous_hp = (
        fixture.hit_points
        if previous.current_hit_points is None
        else previous.current_hit_points
    )
    applied_damage = raw_damage if raw_damage >= fixture.damage_threshold else 0
    current_hp = max(0, previous_hp - applied_damage)
    destroyed = current_hp == 0
    released = (
        tuple(item.id for item in fixture.yield_items)
        if destroyed
        else ()
    )
    updated = replace(
        previous,
        condition="destroyed" if destroyed else "damaged",
        unavailable=destroyed,
        destroyed=destroyed,
        opened=False if destroyed else previous.opened,
        locked=False if destroyed else previous.locked,
        current_hit_points=current_hp,
        released_item_ids=tuple(
            dict.fromkeys((*previous.released_item_ids, *released))
        ),
    )
    return FixtureDamageResult(
        state=_replace_fixture_runtime_state(state, updated),
        fixture=fixture,
        previous_hit_points=previous_hp,
        current_hit_points=current_hp,
        raw_damage=raw_damage,
        applied_damage=applied_damage,
        destroyed=destroyed,
        released_item_ids=released,
    )


def fixture_scene_objects(
    state: ExplorationState,
    *,
    zone_id: str,
) -> tuple[SceneObject, ...]:
    objects: list[SceneObject] = []
    zone = next((item for item in state.zones if item.id == zone_id), None)
    if zone is None:
        raise ValueError(f"Unknown exploration zone: {zone_id}.")
    for fixture in zone.fixtures:
        if not fixture.positions:
            continue
        runtime = fixture_runtime_state(state, zone_id=zone_id, fixture=fixture)
        if runtime.unavailable or runtime.detached or runtime.destroyed:
            continue
        blocks_movement = fixture.blocks_movement_when_closed and not runtime.opened
        cover_active = not runtime.opened
        objects.append(
            SceneObject(
                id=f"fixture:{zone_id}:{fixture.id}",
                name=fixture.name,
                positions=fixture.positions,
                interaction_label=f"Użyj: {fixture.name}",
                visibility=(
                    SetupVisibility.VISIBLE
                    if fixture.visible
                    else SetupVisibility.HIDDEN
                ),
                description=fixture.description,
                blocks_movement=blocks_movement,
                cover_bonus=fixture.cover_bonus if cover_active else 0,
                projectile_cover_bonus=(
                    fixture.projectile_cover_bonus if cover_active else 0
                ),
            )
        )
    return tuple(objects)


def _fixture_from_source_id(
    state: ExplorationState,
    source_id: str,
) -> tuple[str, SceneFixture]:
    for zone in state.zones:
        for fixture in zone.fixtures:
            if source_id == f"zone:{zone.id}:fixture:{fixture.id}":
                return zone.id, fixture
    raise ValueError("Wskazany fixture nie istnieje w aktualnym scenariuszu.")


def _replace_fixture_runtime_state(
    state: ExplorationState,
    updated: FixtureRuntimeState,
) -> ExplorationState:
    remaining = tuple(
        item
        for item in state.fixture_states
        if not (
            item.zone_id == updated.zone_id
            and item.fixture_id == updated.fixture_id
        )
    )
    return replace(state, fixture_states=(*remaining, updated))


__all__ = [
    "FixtureActionPlan",
    "FixtureActionResult",
    "FixtureDamageResult",
    "apply_fixture_damage",
    "apply_fixture_action",
    "fixture_scene_objects",
    "fixture_runtime_state",
    "plan_fixture_action",
]
