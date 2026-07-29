from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Sequence

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.rules import D20RollRequest, RollMode, RollModifier, RollModifierType
from dnd_board_game.world import BoardState, Coordinate, bresenham_line, line_of_sight_clear

from .attack_flow import AttackKind, AttackSource, effective_attack_kind
from .conditions import ConditionState, condition_blocks_actions
from .scene import SceneObject


class CoverLevel(StrEnum):
    NONE = "none"
    HALF = "half"
    THREE_QUARTERS = "three_quarters"
    TOTAL = "total"


@dataclass(frozen=True, slots=True)
class AttackPositioning:
    cover_level: CoverLevel = CoverLevel.NONE
    cover_bonus: int = 0
    cover_sources: tuple[str, ...] = ()
    ranged_threat_actor_ids: tuple[str, ...] = ()
    flanking_ally_ids: tuple[str, ...] = ()
    long_range: bool = False
    lance_close_range: bool = False

    @property
    def total_cover(self) -> bool:
        return self.cover_level == CoverLevel.TOTAL


def evaluate_attack_positioning(
    board: BoardState,
    attacker: Actor,
    target: Actor,
    source: AttackSource,
    actors: Sequence[Actor],
    scene_objects: Sequence[SceneObject] = (),
    condition_states: Sequence[ConditionState] = (),
    *,
    flanking_enabled: bool = True,
) -> AttackPositioning:
    cover = evaluate_cover_from_origin(
        board,
        attacker.position,
        target,
        actors,
        scene_objects,
    )
    if cover.total_cover:
        return cover
    if source.save_ability is not None or source.area is not None:
        return cover if source.save_ability == "dexterity" else AttackPositioning()

    cover_level = cover.cover_level
    cover_bonus = cover.cover_bonus
    cover_sources = cover.cover_sources

    ranged_threats: tuple[str, ...] = ()
    if effective_attack_kind(source) == AttackKind.RANGED:
        ranged_threats = tuple(
            str(actor.id)
            for actor in actors
            if actor.id not in {attacker.id, target.id}
            and _hostile(actor, attacker)
            and not actor.is_defeated()
            and _adjacent(actor, attacker)
            and line_of_sight_clear(board, actor.position, attacker.position)
        )
        if (
            _hostile(target, attacker)
            and not target.is_defeated()
            and _adjacent(target, attacker)
            and line_of_sight_clear(board, target.position, attacker.position)
        ):
            ranged_threats = (*ranged_threats, str(target.id))

    flanking_allies: tuple[str, ...] = ()
    if (
        flanking_enabled
        and effective_attack_kind(source) == AttackKind.MELEE
        and _adjacent(attacker, target)
    ):
        flanking_allies = tuple(
            str(actor.id)
            for actor in actors
            if actor.id not in {attacker.id, target.id}
            and actor.faction == attacker.faction
            and actor.faction != Faction.NEUTRAL
            and not actor.is_defeated()
            and not condition_blocks_actions(
                condition_states,
                str(actor.id),
            )
            and _adjacent(actor, target)
            and _opposite_sides(attacker, actor, target)
            and line_of_sight_clear(board, actor.position, target.position)
        )

    return AttackPositioning(
        cover_level=cover_level,
        cover_bonus=cover_bonus,
        cover_sources=cover_sources,
        ranged_threat_actor_ids=tuple(dict.fromkeys(ranged_threats)),
        flanking_ally_ids=tuple(dict.fromkeys(flanking_allies)),
        long_range=(
            effective_attack_kind(source) == AttackKind.RANGED
            and source.long_range_feet is not None
            and _distance_feet(attacker.position, target.position) > source.range_feet
        ),
        lance_close_range=(
            source.weapon_special_rule is not None
            and source.weapon_special_rule.value == "lance"
            and _distance_feet(attacker.position, target.position) <= 5
        ),
    )


def evaluate_cover_from_origin(
    board: BoardState,
    origin: Coordinate,
    target: Actor,
    actors: Sequence[Actor],
    scene_objects: Sequence[SceneObject] = (),
) -> AttackPositioning:
    """Evaluate cover between an effect's point of origin and one target."""

    if origin == target.position:
        return AttackPositioning()
    if not line_of_sight_clear(board, origin, target.position):
        return AttackPositioning(
            cover_level=CoverLevel.TOTAL,
            cover_sources=("pełna przeszkoda",),
        )

    intermediate = frozenset(bresenham_line(origin, target.position)[1:-1])
    cover_candidates: list[tuple[int, str]] = []
    for actor in actors:
        if actor.id == target.id or actor.is_defeated():
            continue
        if actor.position in intermediate:
            cover_candidates.append((2, actor.name))
    for scene_object in scene_objects:
        if scene_object.projectile_cover_bonus <= 0:
            continue
        if intermediate.intersection(scene_object.positions):
            cover_candidates.append((scene_object.projectile_cover_bonus, scene_object.name))

    cover_bonus = max((candidate[0] for candidate in cover_candidates), default=0)
    cover_sources = tuple(
        dict.fromkeys(label for value, label in cover_candidates if value == cover_bonus)
    )
    cover_level = {
        0: CoverLevel.NONE,
        2: CoverLevel.HALF,
        5: CoverLevel.THREE_QUARTERS,
    }.get(cover_bonus, CoverLevel.THREE_QUARTERS if cover_bonus > 2 else CoverLevel.HALF)

    return AttackPositioning(
        cover_level=cover_level,
        cover_bonus=cover_bonus,
        cover_sources=cover_sources,
    )


def dexterity_save_cover_modifiers(
    ability: str | None,
    positioning: AttackPositioning,
) -> tuple[RollModifier, ...]:
    if ability != "dexterity" or positioning.cover_bonus <= 0:
        return ()
    label = (
        "3/4 osłony"
        if positioning.cover_level == CoverLevel.THREE_QUARTERS
        else "Połowa osłony"
    )
    return (
        RollModifier(
            label,
            positioning.cover_bonus,
            RollModifierType.SITUATIONAL,
            stacking_key="dexterity_save_cover",
        ),
    )


def attack_source_with_positioning(source: AttackSource, positioning: AttackPositioning) -> AttackSource:
    if (
        not positioning.ranged_threat_actor_ids
        and not positioning.flanking_ally_ids
        and not positioning.long_range
        and not positioning.lance_close_range
    ):
        return source
    request = source.attack_roll_request
    mode = request.mode
    modifiers = list(request.modifiers)
    if positioning.ranged_threat_actor_ids:
        mode = _with_disadvantage(mode)
        modifiers.append(
            RollModifier(
                "Atak dystansowy w zwarciu",
                0,
                RollModifierType.SITUATIONAL,
                stacking_key="ranged_attack_in_melee",
            )
        )
    if positioning.long_range:
        mode = _with_disadvantage(mode)
        modifiers.append(
            RollModifier(
                "Daleki zasięg broni",
                0,
                RollModifierType.SITUATIONAL,
                stacking_key="weapon_long_range",
            )
        )
    if positioning.lance_close_range:
        mode = _with_disadvantage(mode)
        modifiers.append(
            RollModifier(
                "Lanca przeciw celowi w odległości 5 stóp",
                0,
                RollModifierType.SITUATIONAL,
                stacking_key="lance_close_range",
            )
        )
    if positioning.flanking_ally_ids:
        mode = _with_advantage(mode)
        modifiers.append(
            RollModifier(
                "Flankowanie",
                0,
                RollModifierType.SITUATIONAL,
                stacking_key="flanking_advantage",
            )
        )
    return replace(
        source,
        attack_roll_request=replace(
            source.attack_roll_request,
            mode=mode,
            modifiers=tuple(modifiers),
        ),
    )


def attack_source_with_hidden_advantage(source: AttackSource, hidden_from_target: bool) -> AttackSource:
    if not hidden_from_target:
        return source
    request = source.attack_roll_request
    return replace(
        source,
        attack_roll_request=replace(
            request,
            mode=_with_advantage(request.mode),
            modifiers=(
                *request.modifiers,
                RollModifier(
                    "Atak z ukrycia",
                    0,
                    RollModifierType.SITUATIONAL,
                    stacking_key="hidden_attacker_advantage",
                ),
            ),
        ),
    )


def _with_disadvantage(mode: RollMode) -> RollMode:
    if mode == RollMode.ADVANTAGE:
        return RollMode.NORMAL
    return RollMode.DISADVANTAGE


def _with_advantage(mode: RollMode) -> RollMode:
    if mode == RollMode.DISADVANTAGE:
        return RollMode.NORMAL
    return RollMode.ADVANTAGE


def _adjacent(first: Actor, second: Actor) -> bool:
    return max(
        abs(first.position.col - second.position.col),
        abs(first.position.row - second.position.row),
    ) == 1


def _distance_feet(first: Coordinate, second: Coordinate) -> int:
    return max(
        abs(first.col - second.col),
        abs(first.row - second.row),
    ) * 5


def _hostile(first: Actor, second: Actor) -> bool:
    return {first.faction, second.faction} == {Faction.ALLY, Faction.ENEMY}


def _opposite_sides(attacker: Actor, ally: Actor, target: Actor) -> bool:
    attacker_vector = (
        attacker.position.col - target.position.col,
        attacker.position.row - target.position.row,
    )
    ally_vector = (
        ally.position.col - target.position.col,
        ally.position.row - target.position.row,
    )
    return ally_vector == (-attacker_vector[0], -attacker_vector[1])
