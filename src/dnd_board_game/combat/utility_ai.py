from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Any, Mapping

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.world import BoardState, Coordinate, PathResult, movement_range

from .attack_flow import AttackSource, legal_attack_targets
from .enemy_ai import EnemyTurnPlan, plan_enemy_turn
from .scene import SceneObject
from .session import (
    CombatState,
    apply_enemy_ai_morale_delta,
    movement_remaining,
    use_dash,
    use_movement,
    use_turn_action,
)
from .stealth import actors_visible_for_pathfinding


@dataclass(frozen=True, slots=True)
class UtilityRolePolicy:
    base_scores: tuple[tuple[str, float], ...]
    weights: tuple[tuple[str, tuple[tuple[str, float], ...]], ...]

    def base_score(self, intent: str) -> float:
        return dict(self.base_scores).get(intent, 0.0)

    def intent_weights(self, intent: str) -> dict[str, float]:
        return dict(dict(self.weights).get(intent, ()))


@dataclass(frozen=True, slots=True)
class MoraleEventPolicy:
    event_id: str
    delta: int
    once: bool = True


@dataclass(frozen=True, slots=True)
class EnemyAiProfile:
    id: str
    model: str
    score_minimum: float
    score_maximum: float
    noise_minimum: float
    noise_maximum: float
    morale_minimum: int
    morale_maximum: int
    starting_morale_by_party_size: tuple[tuple[int, int], ...]
    morale_events: tuple[MoraleEventPolicy, ...]
    roles: tuple[tuple[str, UtilityRolePolicy], ...]
    guard_zone_tag: str = ""
    escape_zone_tag: str = ""
    hazard_zone_tag: str = ""

    def role(self, role_id: str) -> UtilityRolePolicy:
        try:
            return dict(self.roles)[role_id]
        except KeyError as exc:
            raise ValueError(f"AI profile {self.id} does not define role {role_id}.") from exc

    def starting_morale(self, party_size: int) -> int:
        try:
            return dict(self.starting_morale_by_party_size)[party_size]
        except KeyError as exc:
            raise ValueError(
                f"AI profile {self.id} does not define morale for party size {party_size}."
            ) from exc


def enemy_ai_profile_from_payload(payload: Mapping[str, Any]) -> EnemyAiProfile:
    model = str(payload.get("model", ""))
    if model not in {"weighted_utility_v1", "coordinated_pack_v1"}:
        raise ValueError(
            "Enemy AI profile must use weighted_utility_v1 or coordinated_pack_v1."
        )
    score_bounds = payload.get("score_bounds", [0.0, 100.0])
    noise = payload.get("noise", {})
    morale = payload.get("morale", {})
    raw_roles = payload.get("roles", {})
    if not isinstance(raw_roles, dict) or not raw_roles:
        raise ValueError("Enemy AI profile must define at least one role.")
    roles: list[tuple[str, UtilityRolePolicy]] = []
    for role_id, raw_role in raw_roles.items():
        if not isinstance(raw_role, dict):
            raise ValueError(f"Enemy AI role {role_id} must be an object.")
        raw_weights = raw_role.get("weights", {})
        roles.append(
            (
                str(role_id),
                UtilityRolePolicy(
                    base_scores=tuple(
                        (str(intent), float(value))
                        for intent, value in dict(raw_role.get("base_scores", {})).items()
                    ),
                    weights=tuple(
                        (
                            str(intent),
                            tuple(
                                (str(feature), float(value))
                                for feature, value in dict(feature_weights).items()
                            ),
                        )
                        for intent, feature_weights in dict(raw_weights).items()
                    ),
                ),
            )
        )
    raw_events = morale.get("events", {})
    zone_tags = payload.get("zone_tags", {})
    return EnemyAiProfile(
        id=str(payload.get("id", "")),
        model=model,
        score_minimum=float(score_bounds[0]),
        score_maximum=float(score_bounds[1]),
        noise_minimum=float(noise.get("minimum", 0.0)),
        noise_maximum=float(noise.get("maximum", 0.0)),
        morale_minimum=int(morale.get("minimum", 0)),
        morale_maximum=int(morale.get("maximum", 0)),
        starting_morale_by_party_size=tuple(
            (int(size), int(value))
            for size, value in dict(morale.get("starting_by_party_size", {})).items()
        ),
        morale_events=tuple(
            MoraleEventPolicy(
                event_id=str(event_id),
                delta=int(dict(raw_event).get("delta", 0)),
                once=bool(dict(raw_event).get("once", True)),
            )
            for event_id, raw_event in dict(raw_events).items()
        ),
        roles=tuple(roles),
        guard_zone_tag=str(dict(zone_tags).get("guard", "")),
        escape_zone_tag=str(dict(zone_tags).get("escape", "")),
        hazard_zone_tag=str(dict(zone_tags).get("hazard", "")),
    )


def refresh_pack_morale(
    state: CombatState,
    profile: EnemyAiProfile,
    actor_roles: Mapping[str, str],
) -> CombatState:
    if state.enemy_ai.profile_id != profile.id:
        return state
    actors = {str(actor.id): actor for actor in state.actors}
    known_actor_ids = set(actors) | set(state.enemy_ai.escaped_actor_ids)
    leader_ids = tuple(
        actor_id
        for actor_id, role in actor_roles.items()
        if role == "leader" and actor_id in known_actor_ids
    )
    skirmisher_ids = tuple(
        actor_id
        for actor_id, role in actor_roles.items()
        if role != "leader" and actor_id in known_actor_ids
    )
    events: list[str] = []
    for leader_id in leader_ids:
        leader = actors.get(leader_id)
        if leader is not None and leader.max_hp > 0 and 0 < leader.hp * 2 <= leader.max_hp:
            events.append("leader_bloodied")
        if leader is not None and leader.hp <= 0:
            events.append("leader_defeated")
        if leader_id in state.enemy_ai.escaped_actor_ids:
            events.append("leader_escaped")
    defeated_skirmishers = sum(
        actor_id in state.enemy_ai.escaped_actor_ids
        or (actors.get(actor_id) is not None and actors[actor_id].hp <= 0)
        for actor_id in skirmisher_ids
    )
    if len(skirmisher_ids) == 1 and state.enemy_ai.starting_morale == 1:
        solo = actors.get(skirmisher_ids[0])
        if solo is not None and 0 < solo.hp * 2 <= solo.max_hp:
            defeated_skirmishers = 1
    if skirmisher_ids and defeated_skirmishers * 2 >= len(skirmisher_ids):
        events.append("half_skirmishers_defeated")
    updated = state
    for event_id in events:
        updated = apply_morale_event(updated, profile, event_id)
    return updated


def apply_morale_event(
    state: CombatState,
    profile: EnemyAiProfile,
    event_id: str,
) -> CombatState:
    policy = next(
        (event for event in profile.morale_events if event.event_id == event_id),
        None,
    )
    if policy is None:
        raise ValueError(f"Unknown morale event for profile {profile.id}: {event_id}.")
    if policy.once and event_id in state.enemy_ai.used_morale_events:
        return state
    return apply_enemy_ai_morale_delta(
        state,
        event_id=event_id,
        delta=policy.delta,
        minimum=profile.morale_minimum,
        maximum=profile.morale_maximum,
    )


def plan_utility_enemy_turn(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    source: AttackSource,
    *,
    profile: EnemyAiProfile,
    role_id: str,
    actor_roles: Mapping[str, str],
    escape_positions: tuple[Coordinate, ...],
    guard_positions: tuple[Coordinate, ...] = (),
    hazard_positions: tuple[Coordinate, ...] = (),
    scene_objects: tuple[SceneObject, ...] = (),
) -> EnemyTurnPlan:
    state = refresh_pack_morale(state, profile, actor_roles)
    enemy = next(actor for actor in state.actors if actor.id == enemy.id)
    role = profile.role(role_id)
    fallback = plan_enemy_turn(board, state, enemy, source)
    fallback_intent = "engage" if fallback.target is not None else "advance"
    fallback = replace(fallback, intent=fallback_intent)
    fallback_variants = _attack_target_variants(board, fallback, source)
    candidates = [
        _score_plan(
            variant,
            profile,
            role,
            _features_for_plan(
                state,
                enemy,
                variant,
                fallback_intent,
                escape_positions=escape_positions,
                guard_positions=guard_positions,
                hazard_positions=hazard_positions,
                scene_objects=scene_objects,
                actor_roles=actor_roles,
            ),
        )
        for variant in fallback_variants
    ]
    # A fast melee predator that cannot attack after a normal move should be
    # able to spend its action on Dash.  Without this candidate the pack took
    # several turns to cross mud while ranged heroes attacked with impunity.
    if fallback.target is None:
        opponent_positions = tuple(
            actor.position
            for actor in state.actors
            if actor.faction not in {enemy.faction, Faction.NEUTRAL}
            and actor.can_take_combat_turn()
        )
        rush = _movement_plan_toward(
            board,
            state,
            enemy,
            opponent_positions,
            intent="advance",
            dash=True,
        )
        if rush is not None:
            candidates.append(
                _score_plan(
                    rush,
                    profile,
                    role,
                    _features_for_plan(
                        state,
                        enemy,
                        rush,
                        "advance",
                        escape_positions=escape_positions,
                        guard_positions=guard_positions,
                        hazard_positions=hazard_positions,
                        scene_objects=scene_objects,
                        actor_roles=actor_roles,
                    ),
                )
            )
    injured = enemy.max_hp > 0 and enemy.hp * 2 <= enemy.max_hp
    desperate = enemy.max_hp > 0 and enemy.hp * 4 <= enemy.max_hp
    morale_has_dropped = state.enemy_ai.morale < state.enemy_ai.starting_morale
    pack_under_fire = any(
        actor.faction == enemy.faction
        and actor.can_take_combat_turn()
        and actor.hp < actor.max_hp
        for actor in state.actors
    )
    defensive_positions = tuple(
        dict.fromkeys(
            position
            for scene in scene_objects
            if scene.cover_bonus > 0
            for position in scene.positions
        )
    )
    flee = (
        _movement_plan_toward(
            board,
            state,
            enemy,
            escape_positions,
            intent="flee",
            dash=True,
        )
        if desperate or state.enemy_ai.morale <= profile.morale_minimum + 1
        else None
    )
    if flee is not None:
        candidates.append(
            _score_plan(
                flee,
                profile,
                role,
                _features_for_plan(
                    state,
                    enemy,
                    flee,
                    "flee",
                    escape_positions=escape_positions,
                    guard_positions=guard_positions,
                    hazard_positions=hazard_positions,
                    scene_objects=scene_objects,
                    actor_roles=actor_roles,
                ),
            )
        )
    regroup_targets = _regroup_targets(state, enemy, actor_roles, guard_positions)
    regroup = (
        _movement_plan_toward(
            board,
            state,
            enemy,
            regroup_targets,
            intent="regroup",
            dash=False,
            source=source,
        )
        if (
            (injured or morale_has_dropped)
            and not desperate
            and state.enemy_ai.morale > profile.morale_minimum + 1
        )
        else None
    )
    if regroup is not None:
        candidates.append(
            _score_plan(
                regroup,
                profile,
                role,
                _features_for_plan(
                    state,
                    enemy,
                    regroup,
                    "regroup",
                    escape_positions=escape_positions,
                    guard_positions=guard_positions,
                    hazard_positions=hazard_positions,
                    scene_objects=scene_objects,
                    actor_roles=actor_roles,
                ),
            )
        )
    cover_response = (
        _movement_plan_toward(
            board,
            state,
            enemy,
            defensive_positions,
            intent="regroup",
            dash=False,
            source=source,
            message_override="szuka osłony przed ostrzałem",
        )
        if (
            pack_under_fire
            and not desperate
            and state.enemy_ai.morale > profile.morale_minimum + 1
            and fallback.target is None
            and enemy.position not in defensive_positions
        )
        else None
    )
    if (
        cover_response is not None
        and cover_response.movement_path is not None
        and cover_response.movement_path.destination in defensive_positions
    ):
        candidates.append(
            _score_plan(
                cover_response,
                profile,
                role,
                _features_for_plan(
                    state,
                    enemy,
                    cover_response,
                    "regroup",
                    escape_positions=escape_positions,
                    guard_positions=guard_positions,
                    hazard_positions=hazard_positions,
                    scene_objects=scene_objects,
                    actor_roles=actor_roles,
                ),
            )
        )
    guard = _movement_plan_toward(
        board,
        state,
        enemy,
        guard_positions,
        intent="guard",
        dash=False,
        source=source,
    )
    if role_id == "leader" and not pack_under_fire and guard is not None:
        candidates.append(
            _score_plan(
                guard,
                profile,
                role,
                _features_for_plan(
                    state,
                    enemy,
                    guard,
                    "guard",
                    escape_positions=escape_positions,
                    guard_positions=guard_positions,
                    hazard_positions=hazard_positions,
                    scene_objects=scene_objects,
                    actor_roles=actor_roles,
                ),
            )
        )
    if (
        state.enemy_ai.morale <= profile.morale_minimum
        or (
            state.enemy_ai.morale < state.enemy_ai.starting_morale
            and state.enemy_ai.morale <= profile.morale_minimum + 1
        )
    ):
        selected = (
            replace(flee, utility_score=profile.score_maximum)
            if flee is not None
            else replace(fallback, intent="cornered", utility_score=profile.score_maximum)
        )
    else:
        selected = max(
            candidates,
            key=lambda plan: (
                plan.utility_score if plan.utility_score is not None else -1.0,
                -(plan.movement_path.cost_feet if plan.movement_path is not None else 0),
                plan.intent,
            ),
        )
    return _remember_decision(selected)


def _movement_plan_toward(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    targets: tuple[Coordinate, ...],
    *,
    intent: str,
    dash: bool,
    source: AttackSource | None = None,
    message_override: str | None = None,
) -> EnemyTurnPlan | None:
    if not targets:
        return None
    planning_state = state
    if dash:
        dash_result = use_dash(planning_state, enemy)
        if dash_result.accepted:
            planning_state = dash_result.state
    budget = movement_remaining(planning_state, enemy)
    movement_actor = replace(enemy, speed_feet=budget)
    active_actors = tuple(
        actor
        for actor in planning_state.actors
        if str(actor.id) not in planning_state.enemy_ai.escaped_actor_ids
    )
    reachable = movement_range(
        board,
        movement_actor,
        actors_visible_for_pathfinding(
            active_actors,
            planning_state.hidden_states,
            str(enemy.id),
        ),
    )
    destinations = tuple(
        position
        for position in reachable.reachable_tiles
        if position != enemy.position
    )
    if not destinations:
        return None
    destination = min(
        destinations,
        key=lambda position: (
            min(_tile_distance(position, target) for target in targets),
            reachable.costs_by_tile.get(position, 0),
            position.col,
            position.row,
        ),
    )
    path = PathResult(
        enemy.position,
        destination,
        reachable.paths_by_tile[destination],
        reachable.costs_by_tile[destination],
        True,
    )
    moved = use_movement(planning_state, enemy, path)
    moved_enemy = next(actor for actor in moved.state.actors if actor.id == enemy.id)
    updated_state = moved.state
    escaped = intent == "flee" and destination in targets
    target = None
    if not escaped and not dash and source is not None:
        legal_targets = legal_attack_targets(
            board,
            moved_enemy,
            updated_state.actors,
            source,
            updated_state.hidden_states,
        )
        target = min(
            legal_targets,
            key=lambda candidate: (
                _tile_distance(moved_enemy.position, candidate.position),
                candidate.id,
            ),
            default=None,
        )
    if not escaped and not dash and target is None:
        action = use_turn_action(updated_state)
        updated_state = action.state
    verb = (
        "ucieka"
        if intent == "flee"
        else "pędzi ku przeciwnikowi"
        if intent == "advance"
        else "zajmuje pozycję przy legowisku"
        if intent == "guard"
        else "cofa się ku stadu"
    )
    if message_override is not None:
        verb = message_override
    ending = " i opuszcza planszę" if escaped else ""
    attack_ending = f" i atakuje {target.name}" if target is not None else ""
    return EnemyTurnPlan(
        state=updated_state,
        enemy=moved_enemy,
        target=target,
        message=(
            f"{enemy.name} {verb} na {destination.as_tuple()}"
            f"{attack_ending}{ending}."
        ),
        movement_path=path,
        moved_enemy=moved_enemy,
        action_used=dash or target is None,
        intent=intent,
        escaped=escaped,
    )


def _regroup_targets(
    state: CombatState,
    enemy: Actor,
    actor_roles: Mapping[str, str],
    guard_positions: tuple[Coordinate, ...],
) -> tuple[Coordinate, ...]:
    leaders = tuple(
        actor.position
        for actor in state.actors
        if actor.faction == Faction.ENEMY
        and actor.id != enemy.id
        and actor.can_take_combat_turn()
        and actor_roles.get(str(actor.id)) == "leader"
    )
    allies = tuple(
        actor.position
        for actor in state.actors
        if actor.faction == Faction.ENEMY
        and actor.id != enemy.id
        and actor.can_take_combat_turn()
    )
    return leaders or allies or guard_positions


def _attack_target_variants(
    board: BoardState,
    plan: EnemyTurnPlan,
    source: AttackSource,
) -> tuple[EnemyTurnPlan, ...]:
    """Expose each currently legal prey as a utility-scored engage candidate."""

    targets = legal_attack_targets(
        board,
        plan.enemy,
        plan.state.actors,
        source,
        plan.state.hidden_states,
    )
    if len(targets) <= 1:
        return (plan,)
    destination = (
        plan.movement_path.destination.as_tuple()
        if plan.movement_path is not None
        else plan.enemy.position.as_tuple()
    )
    return tuple(
        replace(
            plan,
            target=target,
            message=(
                f"{plan.enemy.name} zajmuje pozycję {destination} "
                f"i atakuje {target.name}."
            ),
        )
        for target in targets
    )


def _features_for_plan(
    state: CombatState,
    enemy: Actor,
    plan: EnemyTurnPlan,
    intent: str,
    *,
    escape_positions: tuple[Coordinate, ...],
    guard_positions: tuple[Coordinate, ...],
    hazard_positions: tuple[Coordinate, ...],
    scene_objects: tuple[SceneObject, ...],
    actor_roles: Mapping[str, str],
) -> dict[str, float]:
    injury = 1.0 - max(0.0, min(1.0, enemy.hp / max(1, enemy.max_hp)))
    morale_pressure = (
        1.0 - state.enemy_ai.morale / state.enemy_ai.starting_morale
        if state.enemy_ai.starting_morale > 0
        else 0.0
    )
    destination = (
        plan.movement_path.destination
        if plan.movement_path is not None and plan.movement_path.valid
        else enemy.position
    )
    living_allies = tuple(
        actor
        for actor in state.actors
        if actor.faction == enemy.faction
        and actor.id != enemy.id
        and actor.can_take_combat_turn()
    )
    living_opponents = tuple(
        actor
        for actor in state.actors
        if actor.faction not in {enemy.faction, Faction.NEUTRAL}
        and actor.can_take_combat_turn()
    )
    target_injury = 0.0
    target_isolation = 0.0
    ally_support = 0.0
    repeats_target = 0.0
    target_saturation = 0.0
    target_prone = 0.0
    target_actor = None
    if plan.target is not None:
        target_actor = next(
            (actor for actor in state.actors if str(actor.id) == plan.target.id),
            None,
        )
        if target_actor is not None:
            target_injury = 1.0 - target_actor.hp / max(1, target_actor.max_hp)
            nearest_target_ally = min(
                (
                    _tile_distance(target_actor.position, actor.position)
                    for actor in living_opponents
                    if actor.id != target_actor.id
                ),
                default=99,
            )
            target_isolation = (
                0.0
                if nearest_target_ally <= 1
                else 0.5
                if nearest_target_ally <= 2
                else 1.0
            )
            nearest_pack_support = min(
                (
                    _tile_distance(target_actor.position, actor.position)
                    for actor in living_allies
                ),
                default=99,
            )
            ally_support = (
                1.0
                if nearest_pack_support <= 1
                else 0.5
                if nearest_pack_support <= 2
                else 0.0
            )
        repeats_target = float(
            dict(state.enemy_ai.previous_targets).get(str(enemy.id)) == plan.target.id
        )
        pack_target_count = sum(
            actor_id != str(enemy.id) and target_id == plan.target.id
            for actor_id, target_id in state.enemy_ai.previous_targets
        )
        target_saturation = min(1.0, pack_target_count / 2.0)
        target_prone = float(
            any(
                condition.actor_id == plan.target.id
                and condition.condition.value == "prone"
                for condition in state.condition_states
            )
        )
    movement_tiles = max(1.0, enemy.speed_feet / 5.0)
    progress_targets = (
        (target_actor.position,)
        if target_actor is not None
        else tuple(actor.position for actor in living_opponents)
    )
    distance_progress = _normalized_progress(
        enemy.position,
        destination,
        progress_targets,
        movement_tiles,
    )
    idle_advance = float(
        intent == "advance"
        and plan.movement_path is not None
        and distance_progress <= 0.0
    )
    pack_distance_before = min(
        (_tile_distance(enemy.position, actor.position) for actor in living_allies),
        default=0,
    )
    pack_distance_after = min(
        (_tile_distance(destination, actor.position) for actor in living_allies),
        default=0,
    )
    pack_separation = min(1.0, pack_distance_after / 6.0) if living_allies else 0.0
    cohesion_gain = max(
        0.0,
        min(1.0, (pack_distance_before - pack_distance_after) / movement_tiles),
    )
    leader_distance = min(
        (
            _tile_distance(destination, actor.position)
            for actor in living_allies
            if actor_roles.get(str(actor.id)) == "leader"
        ),
        default=99,
    )
    end_near_leader = 1.0 if leader_distance <= 2 else 0.5 if leader_distance <= 4 else 0.0
    threat_distance = min(
        (
            _tile_distance(opponent.position, guard)
            for opponent in living_opponents
            for guard in guard_positions
        ),
        default=99,
    )
    threat_to_guard_zone = 1.0 if threat_distance == 0 else 0.5 if threat_distance <= 2 else 0.0
    guard_distance = min(
        (_tile_distance(destination, guard) for guard in guard_positions),
        default=99,
    )
    guard_position_quality = 1.0 if guard_distance == 0 else 0.5 if guard_distance == 1 else 0.0
    cover_bonus = max(
        (
            max(scene.cover_bonus, scene.projectile_cover_bonus)
            for scene in scene_objects
            if destination in scene.positions
        ),
        default=0,
    )
    end_in_cover = min(1.0, cover_bonus / 4.0)
    pack_under_fire = any(
        actor.faction == enemy.faction
        and actor.can_take_combat_turn()
        and actor.hp < actor.max_hp
        for actor in state.actors
    )
    opportunity_count = sum(
        _tile_distance(enemy.position, opponent.position) <= 1
        and _tile_distance(destination, opponent.position) > 1
        for opponent in living_opponents
    )
    opportunity_risk = min(1.0, opportunity_count / 2.0)
    path_positions = (
        plan.movement_path.path
        if plan.movement_path is not None and plan.movement_path.valid
        else ()
    )
    hazard_exposure = (
        sum(position in set(hazard_positions) for position in path_positions)
        / len(path_positions)
        if path_positions
        else 0.0
    )
    escape_progress = _normalized_progress(
        enemy.position,
        destination,
        escape_positions,
        movement_tiles,
    )
    return {
        "can_attack": float(plan.target is not None),
        "distance_progress": distance_progress,
        "target_isolation": target_isolation,
        "target_injury": max(0.0, min(1.0, target_injury)),
        "target_saturation": target_saturation,
        "target_prone": target_prone,
        "ally_support": ally_support,
        "threat_to_guard_zone": threat_to_guard_zone,
        "end_in_cover": end_in_cover,
        "ranged_cover_response": float(
            intent == "regroup" and pack_under_fire and end_in_cover > 0
        ),
        "end_near_leader": end_near_leader,
        "pack_separation": pack_separation,
        "cohesion_gain": cohesion_gain,
        "guard_position_quality": guard_position_quality,
        "self_injury": injury,
        "opportunity_risk": opportunity_risk,
        "hazard_exposure": hazard_exposure,
        "escape_progress": escape_progress if intent == "flee" else 0.0,
        "morale_pressure": max(0.0, min(1.0, morale_pressure)),
        "repeats_target": repeats_target,
        "idle_advance": idle_advance,
    }


def _score_plan(
    plan: EnemyTurnPlan,
    profile: EnemyAiProfile,
    role: UtilityRolePolicy,
    features: Mapping[str, float],
) -> EnemyTurnPlan:
    weights = role.intent_weights(plan.intent)
    components = tuple(
        (feature, value * weights.get(feature, 0.0))
        for feature, value in features.items()
        if weights.get(feature, 0.0) != 0.0
    )
    raw_score = role.base_score(plan.intent) + sum(value for _feature, value in components)
    noise = _seeded_noise(plan, profile)
    score = max(profile.score_minimum, min(profile.score_maximum, raw_score + noise))
    breakdown = (
        ("base", role.base_score(plan.intent)),
        *tuple(sorted(components, key=lambda item: -abs(item[1]))[:3]),
        ("noise", noise),
    )
    return replace(plan, utility_score=score, utility_breakdown=breakdown)


def _seeded_noise(plan: EnemyTurnPlan, profile: EnemyAiProfile) -> float:
    state = plan.state.enemy_ai
    count = dict(state.decision_counts).get(str(plan.enemy.id), 0)
    key = (
        f"{state.encounter_seed}:{plan.state.round_number}:{plan.enemy.id}:"
        f"{count}:{plan.intent}:{plan.movement_path.destination if plan.movement_path else '-'}"
    )
    value = int.from_bytes(sha256(key.encode("utf-8")).digest()[:8], "big") / (2**64 - 1)
    return profile.noise_minimum + value * (profile.noise_maximum - profile.noise_minimum)


def _remember_decision(plan: EnemyTurnPlan) -> EnemyTurnPlan:
    enemy_id = str(plan.enemy.id)
    ai = plan.state.enemy_ai
    counts = dict(ai.decision_counts)
    counts[enemy_id] = counts.get(enemy_id, 0) + 1
    targets = dict(ai.previous_targets)
    if plan.target is not None:
        targets[enemy_id] = plan.target.id
    return replace(
        plan,
        state=replace(
            plan.state,
            enemy_ai=replace(
                ai,
                decision_counts=tuple(sorted(counts.items())),
                previous_targets=tuple(sorted(targets.items())),
            ),
        ),
    )


def _tile_distance(first: Coordinate, second: Coordinate) -> int:
    return max(abs(first.col - second.col), abs(first.row - second.row))


def _normalized_progress(
    origin: Coordinate,
    destination: Coordinate,
    targets: tuple[Coordinate, ...],
    movement_tiles: float,
) -> float:
    if not targets:
        return 0.0
    before = min(_tile_distance(origin, target) for target in targets)
    after = min(_tile_distance(destination, target) for target in targets)
    return max(0.0, min(1.0, (before - after) / movement_tiles))
