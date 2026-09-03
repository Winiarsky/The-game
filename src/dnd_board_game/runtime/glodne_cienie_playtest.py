"""Deterministic automated playtests for the Głodne Cienie encounter.

The runner deliberately uses the same board, attack resolution and configured
enemy AI as the application.  The player policy is intentionally
small: move to a legal attack position and use the strongest currently usable
attack.  It is a balance/regression probe, not a replacement for human play.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from random import Random
from typing import Iterable

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.application import (
    CombatTurnFinalizationService,
    EnemyTurnFlowService,
    PlayerCombatActionFlowService,
)
from dnd_board_game.character_creation import (
    all_default_character_drafts,
    apply_boardgame_archetype,
    build_character,
    load_character_catalog,
    load_character_resources,
)
from dnd_board_game.combat import (
    AttackSource,
    AttackSourceType,
    CombatCondition,
    CombatStatus,
    InitiativeEntry,
    build_initiative_order,
    combat_winner,
    current_actor,
    finish_turn,
    grid_distance_feet,
    has_condition,
    initialize_enemy_ai,
    legal_attack_targets,
    stand_up,
    stow_weapon,
    start_combat,
    use_movement,
)
from dnd_board_game.rules import D20RollInput, D20RollRequest, resolve_d20_roll
from dnd_board_game.inventory import free_hand_count
from dnd_board_game.scenarios import (
    LoadedEncounter,
    build_encounter_from_scenario,
    compile_actor_combat_content,
    encounter_for_party_size,
    load_scenario,
)
from dnd_board_game.world import Coordinate, PathResult, movement_range


SCENARIO_PATH = "content/scenarios/ostatni_transport_01_glodne_cienie.json"
PLAYABLE_IDS = frozenset({"garran", "brakka", "mira", "dagna", "lorian", "nimra", "erynd"})


@dataclass(frozen=True, slots=True)
class PlaytestCase:
    id: str
    hero_ids: tuple[str, ...]
    runs: int = 20


@dataclass(frozen=True, slots=True)
class PlaytestResult:
    case_id: str
    seed: int
    hero_ids: tuple[str, ...]
    party_size: int
    outcome: str
    rounds: int
    turns: int
    hero_casualties: int
    hero_hp_remaining: int
    hero_hp_maximum: int
    enemies_dead: int
    enemies_escaped: int
    enemy_intents: tuple[tuple[str, int], ...]
    morale_events: tuple[str, ...]

    def as_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["hero_ids"] = list(self.hero_ids)
        payload["enemy_intents"] = dict(self.enemy_intents)
        payload["morale_events"] = list(self.morale_events)
        return payload


def default_playtest_cases(runs: int = 20) -> tuple[PlaytestCase, ...]:
    """Cover every supported party size and contrasting team shapes."""

    return (
        PlaytestCase("solo_frontliner", ("garran",), runs),
        PlaytestCase("duo_frontline_support", ("brakka", "dagna"), runs),
        PlaytestCase("duo_mobile", ("mira", "erynd"), runs),
        PlaytestCase("trio_balanced", ("garran", "dagna", "erynd"), runs),
        PlaytestCase("trio_fragile", ("lorian", "mira", "nimra"), runs),
        PlaytestCase("four_mixed", ("brakka", "dagna", "erynd", "nimra"), runs),
        PlaytestCase(
            "five_balanced",
            ("garran", "brakka", "dagna", "mira", "erynd"),
            runs,
        ),
        PlaytestCase(
            "five_ranged",
            ("lorian", "dagna", "mira", "nimra", "erynd"),
            runs,
        ),
    )


def run_playtest_case(
    case: PlaytestCase,
    *,
    seed: int,
    max_rounds: int = 15,
) -> tuple[PlaytestResult, tuple[dict[str, object], ...]]:
    rng = Random(seed)
    encounter = encounter_for_party_size(
        build_encounter_from_scenario(load_scenario(SCENARIO_PATH)),
        len(case.hero_ids),
    )
    heroes = _build_heroes(case.hero_ids, encounter.player_start_zones[0])
    enemies = tuple(actor for actor in encounter.actors if actor.faction == Faction.ENEMY)
    actors = (*heroes, *enemies)
    sources_by_actor = _combat_sources(heroes, encounter)
    state = start_combat(actors, _initiative_order(actors, rng))
    profile = encounter.enemy_ai_profile
    if profile is None:
        raise ValueError("Encounter Głodnych Cieni nie ma profilu AI.")
    state = initialize_enemy_ai(
        state,
        profile_id=profile.id,
        starting_morale=profile.starting_morale(len(heroes)),
        encounter_seed=seed,
    )
    roles = dict(encounter.enemy_ai_roles)
    zones = dict(encounter.enemy_ai_zone_positions)
    events: list[dict[str, object]] = []
    intent_counts: dict[str, int] = {}
    active_effects = ()
    enemy_flow = EnemyTurnFlowService()
    primary_sources = {
        actor_id: sources[0]
        for actor_id, sources in sources_by_actor.items()
        if sources
    }
    turns = 0

    while state.status == CombatStatus.ACTIVE and state.round_number <= max_rounds:
        actor = current_actor(state)
        turns += 1
        before = _actor_snapshot(state.actors)
        if actor.faction == Faction.ALLY:
            state, detail = _resolve_player_turn(
                state,
                encounter,
                sources_by_actor.get(actor.id, ()),
                rng,
            )
        else:
            planned = enemy_flow.plan(
                state=state,
                board=encounter.board,
                attack_sources_by_actor=primary_sources,
                attack_source_options_by_actor=sources_by_actor,
                scene_objects=encounter.scene_objects,
                ai_profile=profile,
                ai_roles=roles,
                ai_zone_positions=zones,
            )
            plan = planned.intent
            intent_counts[plan.intent] = intent_counts.get(plan.intent, 0) + 1
            result = enemy_flow.resolve(
                state=state,
                intent=plan,
                board=encounter.board,
                attack_sources_by_actor=primary_sources,
                attack_source_options_by_actor=sources_by_actor,
                active_effects=active_effects,
                rng=rng,
                scene_objects=encounter.scene_objects,
            ).result
            save_payload: dict[str, object] | None = None
            if result.saving_throw_request is not None:
                save_transition = EnemyTurnFlowService().resolve_player_saving_throw(
                    result=result,
                    natural_roll=rng.randint(1, 20),
                    natural_roll_2=rng.randint(1, 20),
                    active_effects=active_effects,
                )
                result = save_transition.result
                save_payload = save_transition.saving_throw.as_payload()
            committed = CombatTurnFinalizationService().commit_enemy_result(
                result=result,
                active_effects=active_effects,
            )
            state = committed.state
            active_effects = committed.active_effects
            detail = {
                "kind": "enemy_ai",
                "intent": plan.intent,
                "utility_score": plan.utility_score,
                "utility_breakdown": dict(plan.utility_breakdown),
                "target_id": result.target.id if result.target else None,
                "attack_total": result.attack_roll.total if result.attack_roll else None,
                "hit": result.attack_resolution.hit if result.attack_resolution else None,
                "damage": result.damage.total_applied if result.damage else 0,
                "saving_throw": save_payload,
                "escaped": result.escaped,
            }
        after = _actor_snapshot(state.actors)
        events.append(
            {
                "case_id": case.id,
                "seed": seed,
                "turn": turns,
                "round": state.round_number,
                "actor_id": str(actor.id),
                "before": before,
                "after": after,
                **detail,
            }
        )
        if state.status == CombatStatus.ACTIVE:
            state = finish_turn(state)

    winner = combat_winner(state)
    outcome = (
        "victory"
        if winner == Faction.ALLY
        else "defeat"
        if winner == Faction.ENEMY
        else "timeout"
    )
    final_heroes = tuple(actor for actor in state.actors if str(actor.id) in case.hero_ids)
    outcomes = state.enemy_ai.outcomes
    result = PlaytestResult(
        case_id=case.id,
        seed=seed,
        hero_ids=case.hero_ids,
        party_size=len(case.hero_ids),
        outcome=outcome,
        rounds=min(state.round_number, max_rounds),
        turns=turns,
        hero_casualties=sum(actor.hp <= 0 for actor in final_heroes),
        hero_hp_remaining=sum(max(0, actor.hp) for actor in final_heroes),
        hero_hp_maximum=sum(actor.max_hp for actor in final_heroes),
        enemies_dead=sum(item.outcome == "dead" for item in outcomes),
        enemies_escaped=sum(item.outcome == "escaped" for item in outcomes),
        enemy_intents=tuple(sorted(intent_counts.items())),
        morale_events=state.enemy_ai.used_morale_events,
    )
    events.append({"kind": "result", **result.as_payload()})
    return result, tuple(events)


def run_playtest_matrix(
    cases: Iterable[PlaytestCase],
    *,
    base_seed: int = 41000,
    max_rounds: int = 15,
) -> tuple[tuple[PlaytestResult, ...], tuple[dict[str, object], ...]]:
    results: list[PlaytestResult] = []
    events: list[dict[str, object]] = []
    offset = 0
    for case in cases:
        for run_index in range(case.runs):
            result, log = run_playtest_case(
                case,
                seed=base_seed + offset + run_index,
                max_rounds=max_rounds,
            )
            results.append(result)
            events.extend(log)
        offset += 1000
    return tuple(results), tuple(events)


def _build_heroes(hero_ids: tuple[str, ...], start_zone: tuple[Coordinate, ...]) -> tuple[Actor, ...]:
    if not hero_ids or len(hero_ids) > len(start_zone):
        raise ValueError("Liczba bohaterów musi mieścić się w polach startowych encountera.")
    if len(set(hero_ids)) != len(hero_ids) or not set(hero_ids) <= PLAYABLE_IDS:
        raise ValueError("Nieznany albo powtórzony bohater w macierzy playtestu.")
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    drafts = {draft.id: draft for draft in all_default_character_drafts()}
    return tuple(
        replace(
            apply_boardgame_archetype(
                build_character(drafts[hero_id], catalog, resources).actor,
                spell_definitions=tuple(spell for _, spell in resources.spells),
            ),
            position=start_zone[index],
        )
        for index, hero_id in enumerate(hero_ids)
    )


def _combat_sources(
    heroes: tuple[Actor, ...],
    encounter: LoadedEncounter,
) -> dict[ActorId, tuple[AttackSource, ...]]:
    sources = {
        actor.id: _unique_sources(compile_actor_combat_content(actor).attack_sources)
        for actor in heroes
    }
    for actor in encounter.actors:
        if actor.faction == Faction.ENEMY:
            sources[actor.id] = encounter.attack_source_options_by_actor.get(
                actor.id,
                (encounter.attack_sources_by_actor[actor.id],),
            )
    return sources


def _unique_sources(sources: tuple[AttackSource, ...]) -> tuple[AttackSource, ...]:
    by_id: dict[str, AttackSource] = {}
    for source in sources:
        by_id.setdefault(source.id, source)
    return tuple(by_id.values())


def _initiative_order(actors: tuple[Actor, ...], rng: Random):
    entries = []
    for index, actor in enumerate(actors):
        modifier = (actor.ability_scores.dexterity - 10) // 2
        roll = resolve_d20_roll(
            D20RollInput(
                D20RollRequest(),
                rng.randint(1, 20),
            )
        )
        roll = replace(roll, total=roll.natural_roll + modifier)
        entries.append(InitiativeEntry(actor, roll, modifier, index))
    return build_initiative_order(entries)


def _resolve_player_turn(
    state,
    encounter: LoadedEncounter,
    sources: tuple[AttackSource, ...],
    rng: Random,
):
    actor = current_actor(state)
    notes: list[str] = []
    if has_condition(state.condition_states, str(actor.id), CombatCondition.PRONE):
        stood = stand_up(state, actor)
        if stood.accepted:
            state = stood.state
            actor = current_actor(state)
            notes.append("stand_up")
    state, moved = _move_player_for_attack(state, encounter, sources)
    actor = current_actor(state)
    if moved:
        notes.append(f"move:{actor.position.col},{actor.position.row}")
    options = _legal_player_attacks(state, encounter, sources)
    errors: list[str] = []
    for source, target_id in options:
        natural = rng.randint(1, 20)
        try:
            if (
                source.source_type == AttackSourceType.SPELL
                and free_hand_count(current_actor(state).inventory) == 0
            ):
                held_weapon = next(
                    (
                        item
                        for item in current_actor(state).inventory
                        if item.kind == "weapon" and item.equipped and item.held_in
                    ),
                    None,
                )
                if held_weapon is not None:
                    stowed = stow_weapon(state, held_weapon.id)
                    if stowed.accepted:
                        state = stowed.state
                        notes.append(f"stow:{held_weapon.id}")
            if source.save_ability is not None:
                flow = PlayerCombatActionFlowService()
                target = next(item for item in state.actors if str(item.id) == target_id)
                selected = flow.select_attack_target(
                    state=state,
                    board=encounter.board,
                    source=source,
                    position=target.position,
                    active_effects=(),
                    scene_objects=encounter.scene_objects,
                )
                assert selected.pending is not None
                confirmed = flow.confirm_attack_target(
                    state=selected.state,
                    board=encounter.board,
                    source=source,
                    pending=selected.pending,
                    active_effects=selected.active_effects,
                    rng=rng,
                    scene_objects=encounter.scene_objects,
                )
                transition = (
                    flow.submit_damage(
                        state=confirmed.state,
                        source=source,
                        pending=confirmed.pending,
                        active_effects=confirmed.active_effects,
                        damage=_roll_source_damage(source, rng, critical=False),
                    )
                    if confirmed.pending is not None
                    else confirmed
                )
                payload = dict(transition.event_payload)
                return transition.state, {
                    "kind": "player_policy",
                    "source_id": source.id,
                    "target_id": target_id,
                    "attack_total": None,
                    "hit": (
                        confirmed.pending is not None
                        or bool(payload.get("damage", 0))
                    ),
                    "damage": payload.get("damage", 0),
                    "notes": notes + ["target_save"],
                    "rejected_sources": errors,
                }
            transition = PlayerCombatActionFlowService().resolve_direct_attack(
                state=state,
                board=encounter.board,
                source=source,
                target_id=target_id,
                active_effects=(),
                natural_roll=natural,
                natural_roll_2=rng.randint(1, 20),
                damage=_roll_source_damage(source, rng, critical=natural == 20),
                scene_objects=encounter.scene_objects,
            )
        except ValueError as exc:
            errors.append(f"{source.id}:{exc}")
            continue
        payload = dict(transition.event_payload)
        return transition.state, {
            "kind": "player_policy",
            "source_id": source.id,
            "target_id": target_id,
            "attack_total": payload.get("total"),
            "hit": payload.get("hit"),
            "damage": payload.get("damage", 0),
            "notes": notes,
            "rejected_sources": errors,
        }
    return state, {
        "kind": "player_policy",
        "source_id": None,
        "target_id": None,
        "damage": 0,
        "notes": notes + ["no_legal_attack"],
        "rejected_sources": errors,
    }


def _move_player_for_attack(state, encounter: LoadedEncounter, sources: tuple[AttackSource, ...]):
    actor = current_actor(state)
    if _legal_player_attacks(state, encounter, sources):
        return state, False
    movement = movement_range(encounter.board, actor, state.actors)
    enemies = tuple(
        candidate
        for candidate in state.actors
        if candidate.faction == Faction.ENEMY and not candidate.is_defeated()
    )
    best: tuple[tuple[int, float, int, int, int], Coordinate] | None = None
    for tile in movement.reachable_tiles:
        hypothetical = replace(actor, position=tile)
        hypothetical_actors = tuple(
            hypothetical if candidate.id == actor.id else candidate
            for candidate in state.actors
        )
        attack_value = max(
            (
                _expected_damage(source)
                for source in sources
                if _source_available_for_policy(hypothetical, source)
                and legal_attack_targets(
                    encounter.board,
                    hypothetical,
                    hypothetical_actors,
                    source,
                    state.hidden_states,
                )
            ),
            default=0.0,
        )
        nearest = min(
            (grid_distance_feet(tile, enemy.position) for enemy in enemies),
            default=9999,
        )
        key = (
            1 if attack_value > 0 else 0,
            attack_value,
            -nearest,
            -movement.costs_by_tile[tile],
            -(tile.col * 100 + tile.row),
        )
        if best is None or key > best[0]:
            best = (key, tile)
    if best is None or best[1] == actor.position:
        return state, False
    destination = best[1]
    path = PathResult(
        actor.position,
        destination,
        movement.paths_by_tile[destination],
        movement.costs_by_tile[destination],
        True,
    )
    used = use_movement(state, actor, path)
    return (used.state, used.accepted)


def _legal_player_attacks(state, encounter: LoadedEncounter, sources: tuple[AttackSource, ...]):
    actor = current_actor(state)
    options: list[tuple[AttackSource, str]] = []
    for source in sources:
        if not _source_available_for_policy(actor, source):
            continue
        targets = legal_attack_targets(
            encounter.board,
            actor,
            state.actors,
            source,
            state.hidden_states,
        )
        for target in sorted(targets, key=lambda item: (item.hp, item.id)):
            options.append((source, target.id))
    return tuple(
        sorted(
            options,
            key=lambda item: (-_expected_damage(item[0]), item[1], item[0].id),
        )
    )


def _source_available_for_policy(actor: Actor, source: AttackSource) -> bool:
    if source.source_item_id is None:
        return True
    return any(
        item.available
        and item.equipped
        and (item.id == source.source_item_id or item.source_ref == source.source_item_id)
        for item in actor.inventory
    )


def _expected_damage(source: AttackSource) -> float:
    total = 0.0
    for component in source.damage_components:
        total += float(component.fixed or 0) + component.modifier
        if component.dice is not None:
            total += component.dice.count * (component.dice.sides + 1) / 2
    return max(0.0, total)


def _roll_source_damage(source: AttackSource, rng: Random, *, critical: bool) -> int:
    total = 0
    for component in source.damage_components:
        total += int(component.fixed or 0) + component.modifier
        if component.dice is not None:
            count = component.dice.count * (2 if critical else 1)
            total += sum(rng.randint(1, component.dice.sides) for _ in range(count))
    return max(0, total)


def _actor_snapshot(actors: tuple[Actor, ...]) -> dict[str, dict[str, object]]:
    return {
        str(actor.id): {
            "hp": actor.hp,
            "max_hp": actor.max_hp,
            "faction": actor.faction.value,
            "position": [actor.position.col, actor.position.row],
        }
        for actor in actors
    }
