"""Deterministic planning for leaving one authored scenario for the next."""

from __future__ import annotations

from dataclasses import dataclass, replace

from dnd_board_game.actors import Actor
from dnd_board_game.combat import SceneFlags, scene_flag
from dnd_board_game.exploration import (
    ContinuationNavigationResult,
    ContinuationOutcomeKind,
    ScenarioContinuation,
    ScenarioContinuationOutcome,
)


@dataclass(frozen=True, slots=True)
class ScenarioContinuationPlan:
    continuation: ScenarioContinuation
    source_scenario_id: str
    source_zone_id: str

    def as_payload(self) -> dict[str, object]:
        return {
            **self.continuation.as_payload(),
            "source_scenario_id": self.source_scenario_id,
            "source_zone_id": self.source_zone_id,
            "available": True,
            "missing_flags": [],
            "requires_departure_zone": False,
        }


@dataclass(frozen=True, slots=True)
class ScenarioContinuationOutcomeResolution:
    outcome: ScenarioContinuationOutcome
    target_effects: tuple[dict[str, object], ...]
    propagated_flags: tuple[tuple[str, object], ...] = ()

    def as_payload(self) -> dict[str, object]:
        return {
            **self.outcome.as_payload(),
            "target_effects": [dict(effect) for effect in self.target_effects],
            "propagated_flags": [
                {"key": key, "value": value}
                for key, value in self.propagated_flags
            ],
        }


class ScenarioContinuationFlowService:
    """Validate authored continuation gates without loading campaign state."""

    def availability_payload(
        self,
        continuation: ScenarioContinuation | None,
        *,
        flags: SceneFlags,
        current_zone_id: str,
    ) -> dict[str, object] | None:
        if continuation is None:
            return None
        missing_flags = tuple(
            flag
            for flag in continuation.available_if_flags
            if not bool(scene_flag(flags, flag, False))
        )
        wrong_zone = current_zone_id != continuation.departure_zone_id
        return {
            **continuation.as_payload(),
            "available": not missing_flags and not wrong_zone,
            "missing_flags": list(missing_flags),
            "requires_departure_zone": wrong_zone,
            "departure_summary": [
                {
                    "label": item.label,
                    "known": (
                        item.required_flag is None
                        or bool(scene_flag(flags, item.required_flag, False))
                    ),
                }
                for item in continuation.departure_summary
            ],
        }

    def plan(
        self,
        continuation: ScenarioContinuation | None,
        *,
        source_scenario_id: str,
        flags: SceneFlags,
        current_zone_id: str,
    ) -> ScenarioContinuationPlan:
        if continuation is None:
            raise ValueError("Ten scenariusz nie definiuje dalszego przejścia.")
        missing_flags = tuple(
            flag
            for flag in continuation.available_if_flags
            if not bool(scene_flag(flags, flag, False))
        )
        if missing_flags:
            raise ValueError(
                "Drużyna nie jest jeszcze gotowa do przejścia do kolejnego "
                "scenariusza."
            )
        if current_zone_id != continuation.departure_zone_id:
            raise ValueError(
                "Aby wyruszyć dalej, drużyna musi znajdować się w lokacji wyjścia."
            )
        return ScenarioContinuationPlan(
            continuation=continuation,
            source_scenario_id=source_scenario_id,
            source_zone_id=current_zone_id,
        )

    def resolve_outcome(
        self,
        plan: ScenarioContinuationPlan,
        *,
        flags: SceneFlags,
        navigation_succeeded: bool,
    ) -> ScenarioContinuationOutcomeResolution:
        outcome = next(
            (
                candidate
                for candidate in plan.continuation.outcomes
                if _outcome_matches(
                    candidate,
                    flags=flags,
                    navigation_succeeded=navigation_succeeded,
                )
            ),
            None,
        )
        if outcome is None:
            if plan.continuation.outcomes:
                raise ValueError(
                    "Żaden autorski wynik przejścia nie pasuje do stanu scenariusza."
                )
            outcome = ScenarioContinuationOutcome(
                id=f"{plan.continuation.id}_completed",
                kind=ContinuationOutcomeKind.SUCCESS,
                label=plan.continuation.label,
                narration=plan.continuation.description,
            )
        propagated = tuple(
            (key, value)
            for key in dict.fromkeys((*plan.continuation.propagate_flags,
                                      *(key for key, _ in flags.values if key.startswith('campaign_'))))
            for value in (scene_flag(flags, key, None),)
            if value is not None
        )
        effects_by_key: dict[str, dict[str, object]] = {
            key: {
                "type": "set_flag",
                "parameters": {"key": key, "value": value},
            }
            for key, value in propagated
        }
        for effect in outcome.target_effects:
            parameters = effect["parameters"]
            assert isinstance(parameters, dict)
            effects_by_key[str(parameters["key"])] = effect
        return ScenarioContinuationOutcomeResolution(
            outcome=outcome,
            target_effects=tuple(effects_by_key.values()),
            propagated_flags=propagated,
        )


def merge_handoff_actor(source: Actor, target: Actor) -> Actor:
    """Carry mutable campaign state onto the target scenario's actor definition.

    Scenario content remains authoritative for capabilities and rules metadata.
    Matching inventory/resource entries retain their mutable counters, while
    source-only acquisitions are appended to the target loadout.
    """

    if source.id != target.id:
        raise ValueError("Handoff actors must have the same stable id.")
    return replace(
        target,
        hp=min(source.hp, target.max_hp),
        temp_hp=source.temp_hp,
        position=target.position,
        inventory=_merge_inventory(source, target),
        active_light=source.active_light,
        currency=source.currency,
        spell_slots=_merge_by_key(
            source.spell_slots,
            target.spell_slots,
            key=lambda slot: slot.level,
            merge=lambda old, canonical: replace(
                canonical,
                remaining=min(old.remaining, canonical.maximum),
            ),
        ),
        spell_preparation=_merge_spell_preparation(source, target),
        hit_dice=_merge_by_key(
            source.hit_dice,
            target.hit_dice,
            key=lambda pool: pool.die_sides,
            merge=lambda old, canonical: replace(
                canonical,
                remaining=min(old.remaining, canonical.maximum),
            ),
        ),
        resource_pools=_merge_by_key(
            source.resource_pools,
            target.resource_pools,
            key=lambda pool: pool.id,
            merge=lambda old, canonical: replace(
                canonical,
                current=min(old.current, canonical.maximum),
            ),
        ),
        exhaustion_level=source.exhaustion_level,
        death_saves=source.death_saves,
        portrait=source.portrait or target.portrait,
    )


def _merge_inventory(source: Actor, target: Actor):
    target_by_id = {item.id: item for item in target.inventory}
    merged = []
    seen: set[str] = set()
    for source_item in source.inventory:
        canonical = target_by_id.get(source_item.id)
        if canonical is None:
            merged.append(source_item)
        else:
            merged.append(
                replace(
                    canonical,
                    quantity=source_item.quantity,
                    equipped=source_item.equipped,
                    broken=source_item.broken,
                    held_in=source_item.held_in,
                    charges_current=source_item.charges_current,
                    attuned=source_item.attuned,
                )
            )
        seen.add(source_item.id)
    merged.extend(item for item in target.inventory if item.id not in seen)
    return tuple(merged)


def _merge_by_key(source_items, target_items, *, key, merge):
    source_by_key = {key(item): item for item in source_items}
    merged = [
        merge(source_by_key[item_key], target_item)
        if (item_key := key(target_item)) in source_by_key
        else target_item
        for target_item in target_items
    ]
    target_keys = {key(item) for item in target_items}
    merged.extend(item for item in source_items if key(item) not in target_keys)
    return tuple(merged)


def _merge_spell_preparation(source: Actor, target: Actor):
    source_profile = source.spell_preparation
    target_profile = target.spell_preparation
    if source_profile is None or target_profile is None:
        return target_profile
    available_ids = {spell.id for spell in target_profile.available_spells}
    prepared_ids = tuple(
        spell_id
        for spell_id in source_profile.prepared_spell_ids
        if spell_id in available_ids
        and spell_id not in target_profile.always_prepared_spell_ids
    )
    if len(prepared_ids) > target_profile.preparation_limit:
        prepared_ids = prepared_ids[: target_profile.preparation_limit]
    return replace(
        target_profile,
        prepared_spell_ids=prepared_ids,
        confirmed=source_profile.confirmed,
    )


def _outcome_matches(
    outcome: ScenarioContinuationOutcome,
    *,
    flags: SceneFlags,
    navigation_succeeded: bool,
) -> bool:
    if any(
        not bool(scene_flag(flags, flag, False))
        for flag in outcome.required_flags
    ):
        return False
    if any(
        bool(scene_flag(flags, flag, False))
        for flag in outcome.forbidden_flags
    ):
        return False
    if (
        outcome.navigation_result == ContinuationNavigationResult.SUCCESS
        and not navigation_succeeded
    ):
        return False
    if (
        outcome.navigation_result == ContinuationNavigationResult.FAILURE
        and navigation_succeeded
    ):
        return False
    return True
