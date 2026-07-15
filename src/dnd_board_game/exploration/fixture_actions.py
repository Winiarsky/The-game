"""Deterministic state transitions for interactive scene fixtures."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .models import (
    ExplorationState,
    FixtureActionPolicy,
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
        FixtureRuntimeState(zone_id=zone_id, fixture_id=fixture.id, condition=fixture.condition),
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
        if current_plan.policy.release_yield_items
        else ()
    )
    updated = replace(
        previous,
        condition=current_plan.policy.result_condition,
        unavailable=current_plan.policy.makes_fixture_unavailable,
        detached=current_plan.policy.operation == FixtureOperation.DETACH,
        destroyed=current_plan.policy.operation == FixtureOperation.DESTROY,
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


__all__ = [
    "FixtureActionPlan",
    "FixtureActionResult",
    "apply_fixture_action",
    "fixture_runtime_state",
    "plan_fixture_action",
]
