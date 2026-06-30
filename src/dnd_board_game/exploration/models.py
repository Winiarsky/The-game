from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from dnd_board_game.actors import Actor
from dnd_board_game.combat import SceneAbilityCheck, SceneFlags, SetupVisibility, scene_flag, set_scene_flag
from dnd_board_game.hardware import LedColor, LedFeedback, LedFrame, LedRole
from dnd_board_game.rules import D20RollInput, D20RollRequest, D20RollResult, resolve_ability_check, resolve_d20_roll
from dnd_board_game.world import Coordinate


class SceneMode(StrEnum):
    ENCOUNTER = "encounter"
    EXPLORATION = "exploration"


class ExplorationOptionKind(StrEnum):
    MESSAGE = "message"
    SEARCH = "search"
    CHECK = "check"


class ExplorationMenuOptionKind(StrEnum):
    CHALLENGE = "challenge"
    ZONE_OPTION = "zone_option"
    LOOK_AROUND = "look_around"
    CANCEL = "cancel"


@dataclass(frozen=True, slots=True)
class LlmContext:
    summary: str = ""
    available_materials: tuple[str, ...] = ()
    forbidden_assumptions: tuple[str, ...] = ()
    reasonable_approaches: tuple[str, ...] = ()
    impossible_approaches: tuple[str, ...] = ()
    risk_notes: tuple[str, ...] = ()

    def as_payload(self) -> dict[str, object]:
        return {
            "summary": self.summary,
            "available_materials": list(self.available_materials),
            "forbidden_assumptions": list(self.forbidden_assumptions),
            "reasonable_approaches": list(self.reasonable_approaches),
            "impossible_approaches": list(self.impossible_approaches),
            "risk_notes": list(self.risk_notes),
        }


@dataclass(frozen=True, slots=True)
class LlmDcTier:
    id: str
    dc: int
    label: str = ""
    guidance: str = ""

    def as_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "dc": self.dc,
            "label": self.label,
            "guidance": self.guidance,
        }


@dataclass(frozen=True, slots=True)
class LlmChallengePolicy:
    allowed_local_skills: tuple[str, ...] = ("crafting",)
    allowed_approach_tags: tuple[str, ...] = (
        "arcane",
        "bribe",
        "climbing",
        "crafting",
        "fire",
        "heavy_force",
        "lever",
        "light",
        "lockpicking",
        "medicine",
        "nature",
        "noise",
        "picket",
        "quiet",
        "religious",
        "saw",
        "scouting",
        "social",
    )
    allowed_complications: tuple[str, ...] = (
        "alarm_w_strażnicy",
        "bolesny_upadek",
        "drzazgi",
        "guards_alerted",
        "jammed_gate",
        "lost_resource",
        "minor_injury",
        "narastający_hałas",
        "ryzyko_upadku",
        "stracony_czas",
        "time_cost",
        "uszkodzony_mechanizm",
        "zaklinowana_sztacheta",
        "ślepy_trop",
    )
    allowed_consequence_types: tuple[str, ...] = ("add_noise", "add_complication", "none")
    allowed_preparation_effect_types: tuple[str, ...] = ("modifier", "reduce_negative_effect")
    allowed_grant_resource_ids: tuple[str, ...] = ()
    allowed_unlock_option_ids: tuple[str, ...] = ()
    max_resources_per_attempt: int = 1
    dc_min: int = 5
    dc_max: int = 25
    progress_success_min: int = 1
    progress_success_max: int = 3
    progress_failure_min: int = 0
    progress_failure_max: int = 1
    preparation_modifier_min: int = 1
    preparation_modifier_max: int = 2
    negative_effect_reduction_min: int = 1
    negative_effect_reduction_max: int = 1
    effect_boost_min: int = 1
    effect_boost_max: int = 1
    dc_tiers: tuple[LlmDcTier, ...] = ()
    allowed_difficulty_tiers: tuple[str, ...] = ()
    default_difficulty_tier: str | None = None
    difficulty_guidance: tuple[str, ...] = ()

    def as_payload(self) -> dict[str, object]:
        return {
            "allowed_local_skills": list(self.allowed_local_skills),
            "allowed_approach_tags": list(self.allowed_approach_tags),
            "allowed_complications": list(self.allowed_complications),
            "allowed_consequence_types": list(self.allowed_consequence_types),
            "allowed_preparation_effect_types": list(self.allowed_preparation_effect_types),
            "allowed_grant_resource_ids": list(self.allowed_grant_resource_ids),
            "allowed_unlock_option_ids": list(self.allowed_unlock_option_ids),
            "max_resources_per_attempt": self.max_resources_per_attempt,
            "dc_range": [self.dc_min, self.dc_max],
            "progress_on_success_range": [self.progress_success_min, self.progress_success_max],
            "progress_on_failure_range": [self.progress_failure_min, self.progress_failure_max],
            "preparation_modifier_range": [self.preparation_modifier_min, self.preparation_modifier_max],
            "negative_effect_reduction_range": [self.negative_effect_reduction_min, self.negative_effect_reduction_max],
            "effect_boost_range": [self.effect_boost_min, self.effect_boost_max],
            "dc_policy": {
                "tiers": [tier.as_payload() for tier in self.dc_tiers],
                "allowed_tiers": list(self.allowed_difficulty_tiers),
                "default_tier": self.default_difficulty_tier,
                "guidance": list(self.difficulty_guidance),
            },
        }

    def dc_for_tier(self, tier_id: str) -> int | None:
        return next((tier.dc for tier in self.dc_tiers if tier.id == tier_id), None)


@dataclass(frozen=True, slots=True)
class ExplorationOption:
    id: str
    label: str
    kind: ExplorationOptionKind
    color: tuple[int, int, int]
    description: str = ""
    message: str = ""
    success_message: str = ""
    failure_message: str = ""
    ability_check: SceneAbilityCheck | None = None
    allow_help: bool = False
    success_flag: str | None = None
    failure_flag: str | None = None
    reveals: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ExplorationZone:
    id: str
    name: str
    positions: tuple[Coordinate, ...]
    color: tuple[int, int, int]
    anchor_position: Coordinate | None = None
    description: str = ""
    visibility: SetupVisibility = SetupVisibility.VISIBLE
    available_if_flag: str | None = None
    available_if_value: object = True
    options: tuple[ExplorationOption, ...] = ()
    adjacent_zone_ids: tuple[str, ...] = ()
    search_dc: int | None = None
    search_ability: str = "wisdom"
    search_skill: str | None = "perception"
    search_reveals: tuple[str, ...] = ()
    search_success_flag: str | None = None
    search_failure_flag: str | None = None
    llm_context: LlmContext = LlmContext()

    @property
    def marker_position(self) -> Coordinate:
        if self.anchor_position is not None:
            return self.anchor_position
        if not self.positions:
            raise ValueError(f"Exploration zone {self.id} has no positions.")
        return self.positions[0]


@dataclass(frozen=True, slots=True)
class ExplorationPoint:
    id: str
    name: str
    zone_id: str
    positions: tuple[Coordinate, ...]
    color: tuple[int, int, int]
    visibility: SetupVisibility = SetupVisibility.VISIBLE
    description: str = ""
    requires_setup: bool = True


@dataclass(frozen=True, slots=True)
class PartyPosition:
    zone_id: str
    marker_position: Coordinate | None = None


@dataclass(frozen=True, slots=True)
class PartyCheckInput:
    actor: Actor
    natural_roll: int
    request: D20RollRequest


@dataclass(frozen=True, slots=True)
class PartyCheckResult:
    rolls: tuple[tuple[Actor, D20RollResult], ...]
    winner: Actor
    winning_roll: D20RollResult
    dc: int
    success: bool


@dataclass(frozen=True, slots=True)
class SearchResult:
    state: ExplorationState
    party_check: PartyCheckResult
    revealed_points: tuple[ExplorationPoint, ...]
    message: str


@dataclass(frozen=True, slots=True)
class ExplorationChallengeOption:
    id: str
    label: str
    ability_check: SceneAbilityCheck
    progress_on_success: int
    progress_on_failure: int
    color: tuple[int, int, int]
    description: str = ""
    success_message: str = ""
    failure_message: str = ""
    critical_failure_message: str = ""
    tags: tuple[str, ...] = ()
    unlocks_if_flag: str | None = None
    unlocks_if_resource_id: str | None = None
    success_noise: int = 0
    failure_noise: int = 0
    critical_failure_noise: int = 0
    quiet_success_margin: int | None = None
    quiet_on_natural_20: bool = False
    success_complication: str | None = None
    failure_complication: str | None = None
    critical_failure_complication: str | None = None


@dataclass(frozen=True, slots=True)
class ExplorationChallenge:
    id: str
    zone_id: str
    name: str
    progress_required: int
    completed_flag: str
    options: tuple[ExplorationChallengeOption, ...]
    llm_context: LlmContext = LlmContext()
    llm_policy: LlmChallengePolicy = LlmChallengePolicy()


@dataclass(frozen=True, slots=True)
class ExplorationChallengeAttempt:
    challenge_id: str
    option_id: str
    approach_label: str
    approach_tags: tuple[str, ...]
    resource_id: str | None
    natural_roll: int
    total: int
    success: bool
    critical_failure: bool
    progress_added: int
    noise_added: int
    complications_added: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExplorationChallengeState:
    challenge_id: str
    current_progress: int = 0
    noise: int = 0
    complications: tuple[str, ...] = ()
    completed: bool = False
    attempts: tuple[ExplorationChallengeAttempt, ...] = ()


@dataclass(frozen=True, slots=True)
class ExplorationResource:
    id: str
    label: str
    bonus_tags: tuple[str, ...]
    modifier: int = 0
    advantage: bool = False
    mitigates_complications: tuple[str, ...] = ()
    mitigates_noise: int = 0
    unlocks_flags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ChallengeResult:
    state: ExplorationState
    challenge: ExplorationChallenge
    option: ExplorationChallengeOption
    roll: D20RollResult
    success: bool
    critical_failure: bool
    progress_added: int
    noise_added: int
    complications_added: tuple[str, ...]
    completed: bool
    message: str
    resource_used: ExplorationResource | None = None


@dataclass(frozen=True, slots=True)
class ExplorationMenuOption:
    id: str
    label: str
    color: tuple[int, int, int]
    kind: ExplorationMenuOptionKind
    slot_position: Coordinate
    source_id: str | None = None


@dataclass(frozen=True, slots=True)
class ExplorationMenu:
    zone: ExplorationZone
    options: tuple[ExplorationMenuOption, ...]


@dataclass(frozen=True, slots=True)
class ExplorationState:
    zones: tuple[ExplorationZone, ...]
    points: tuple[ExplorationPoint, ...]
    party_position: PartyPosition
    flags: SceneFlags = SceneFlags()
    exhausted_search_zones: tuple[str, ...] = ()
    challenges: tuple[ExplorationChallenge, ...] = ()
    challenge_states: tuple[ExplorationChallengeState, ...] = ()
    resources: tuple[ExplorationResource, ...] = ()
    inventory_resource_ids: tuple[str, ...] = ()


def visible_exploration_zones(zones: tuple[ExplorationZone, ...]) -> tuple[ExplorationZone, ...]:
    return tuple(zone for zone in zones if zone.visibility == SetupVisibility.VISIBLE and zone.positions)


def available_exploration_zones(state: ExplorationState) -> tuple[ExplorationZone, ...]:
    return tuple(zone for zone in visible_exploration_zones(state.zones) if zone_is_available(state, zone))


def zone_is_available(state: ExplorationState, zone: ExplorationZone) -> bool:
    if zone.available_if_flag is None:
        return True
    return scene_flag(state.flags, zone.available_if_flag) == zone.available_if_value


def challenge_for_zone(state: ExplorationState, zone_id: str) -> ExplorationChallenge | None:
    for challenge in state.challenges:
        if challenge.zone_id == zone_id:
            return challenge
    return None


def challenge_state_for(state: ExplorationState, challenge_id: str) -> ExplorationChallengeState:
    for challenge_state in state.challenge_states:
        if challenge_state.challenge_id == challenge_id:
            return challenge_state
    return ExplorationChallengeState(challenge_id)


def available_challenge_options(
    state: ExplorationState,
    challenge: ExplorationChallenge,
) -> tuple[ExplorationChallengeOption, ...]:
    if challenge_state_for(state, challenge.id).completed:
        return ()
    result: list[ExplorationChallengeOption] = []
    for option in challenge.options:
        llm_unlocked = scene_flag(state.flags, f"llm_unlocked_option:{option.id}", False)
        if option.unlocks_if_flag is not None and not scene_flag(state.flags, option.unlocks_if_flag, False) and not llm_unlocked:
            continue
        if (
            option.unlocks_if_resource_id is not None
            and option.unlocks_if_resource_id not in state.inventory_resource_ids
            and not llm_unlocked
        ):
            continue
        result.append(option)
    return tuple(result)


def build_exploration_menu(
    state: ExplorationState,
    zone: ExplorationZone,
) -> ExplorationMenu:
    menu_items: list[tuple[str, str, tuple[int, int, int] | None, ExplorationMenuOptionKind, str | None]] = []
    challenge = challenge_for_zone(state, zone.id)
    if challenge is not None and not challenge_state_for(state, challenge.id).completed:
        for option in available_challenge_options(state, challenge):
            menu_items.append((option.id, option.label, None, ExplorationMenuOptionKind.CHALLENGE, option.id))
    for option in zone.options:
        if not _zone_option_available(state, zone, option):
            continue
        menu_items.append((option.id, option.label, None, ExplorationMenuOptionKind.ZONE_OPTION, option.id))
    menu_items.append(("look_around", "Rozejrzyj się po okolicy", None, ExplorationMenuOptionKind.LOOK_AROUND, None))
    menu_items.append(("cancel", "Wycofaj", LedColor.ACTIVE_ACTOR, ExplorationMenuOptionKind.CANCEL, None))
    slots = _menu_slots_for_zone(zone, len(menu_items))
    options = tuple(
        ExplorationMenuOption(
            id=item_id,
            label=label,
            color=color or _basic_menu_color(item_id),
            kind=kind,
            slot_position=slot,
            source_id=source_id,
        )
        for (item_id, label, color, kind, source_id), slot in zip(menu_items, slots, strict=True)
    )
    return ExplorationMenu(zone, options)


def menu_option_for_position(menu: ExplorationMenu, position: Coordinate) -> ExplorationMenuOption | None:
    for option in menu.options:
        if option.slot_position == position:
            return option
    return None


def _menu_slots_for_zone(zone: ExplorationZone, count: int) -> tuple[Coordinate, ...]:
    anchor = zone.marker_position
    preferred_offsets = (
        (0, -1),
        (1, 0),
        (0, 1),
        (-1, 0),
        (1, -1),
        (1, 1),
        (-1, 1),
        (-1, -1),
        (2, 0),
        (-2, 0),
        (0, 2),
        (0, -2),
    )
    zone_positions = set(zone.positions)
    slots: list[Coordinate] = []
    for col_offset, row_offset in preferred_offsets:
        candidate = Coordinate(anchor.col + col_offset, anchor.row + row_offset)
        if candidate in zone_positions and candidate not in slots:
            slots.append(candidate)
        if len(slots) == count:
            return tuple(slots)
    fallback = sorted(
        (position for position in zone.positions if position != anchor and position not in slots),
        key=lambda position: (abs(position.col - anchor.col) + abs(position.row - anchor.row), position.row, position.col),
    )
    slots.extend(fallback[: max(0, count - len(slots))])
    if len(slots) < count:
        raise ValueError(f"Exploration zone {zone.id} does not have enough tiles for {count} menu options.")
    return tuple(slots[:count])


def _basic_menu_color(option_id: str) -> tuple[int, int, int]:
    stable_colors = {
        "force_gate": LedColor.ATTACK_MISS,
        "vault_gate": LedColor.MOVEMENT_RANGE,
        "lever_gate": LedColor.INTERACTIVE_OBJECT,
        "find_way_around": LedColor.MARKER,
        "break_picket": LedColor.ENEMY_MOVEMENT_DESTINATION,
        "saw_picket": LedColor.MENU_PINK,
        "inspect_gate_area": LedColor.MENU_PURPLE,
        "look_around": LedColor.PLAYER_START_ZONE,
    }
    if option_id in stable_colors:
        return stable_colors[option_id]
    palette = (
        LedColor.ATTACK_MISS,
        LedColor.MOVEMENT_RANGE,
        LedColor.INTERACTIVE_OBJECT,
        LedColor.MARKER,
        LedColor.ENEMY_MOVEMENT_DESTINATION,
        LedColor.MENU_PURPLE,
        LedColor.PLAYER_START_ZONE,
        LedColor.MENU_PINK,
    )
    index = sum(ord(character) for character in option_id) % len(palette)
    return palette[index]


def _zone_option_available(state: ExplorationState, zone: ExplorationZone, option: ExplorationOption) -> bool:
    if option.kind == ExplorationOptionKind.SEARCH and zone.id in state.exhausted_search_zones:
        return False
    if option.success_flag is not None and scene_flag(state.flags, option.success_flag, False):
        return False
    if option.failure_flag is not None and scene_flag(state.flags, option.failure_flag, False):
        return False
    return True


def matching_resources(
    state: ExplorationState,
    option: ExplorationChallengeOption,
) -> tuple[ExplorationResource, ...]:
    option_tags = set(option.tags)
    owned = set(state.inventory_resource_ids)
    return tuple(
        resource
        for resource in state.resources
        if resource.id in owned
        and (option_tags.intersection(resource.bonus_tags) or resource.id == option.unlocks_if_resource_id)
    )


def grant_resource(state: ExplorationState, resource_id: str) -> ExplorationState:
    if resource_id in state.inventory_resource_ids:
        return state
    resource = next((candidate for candidate in state.resources if candidate.id == resource_id), None)
    if resource is None:
        raise ValueError(f"Unknown exploration resource: {resource_id}.")
    flags = state.flags
    for flag in resource.unlocks_flags:
        flags = set_scene_flag(flags, flag, True)
    return replace(state, flags=flags, inventory_resource_ids=tuple(sorted((*state.inventory_resource_ids, resource_id))))


def resolve_challenge_option(
    state: ExplorationState,
    challenge: ExplorationChallenge,
    option: ExplorationChallengeOption,
    roll: D20RollResult,
    resource: ExplorationResource | None = None,
    negative_effect_reduction: int = 0,
    progress_boost_on_success: int = 0,
) -> ChallengeResult:
    if option not in available_challenge_options(state, challenge):
        raise ValueError(f"Challenge option {option.id} is not available.")
    current = challenge_state_for(state, challenge.id)
    if current.completed:
        raise ValueError(f"Challenge {challenge.id} is already completed.")
    check = resolve_ability_check(roll, option.ability_check.dc)
    success = check.success
    critical_failure = roll.is_natural_1 and not success
    raw_progress_added = option.progress_on_success + max(0, progress_boost_on_success) if success else option.progress_on_failure
    progress_added = min(challenge.progress_required - current.current_progress, raw_progress_added)
    progress = min(challenge.progress_required, current.current_progress + progress_added)
    completed = progress >= challenge.progress_required
    noise_added = _challenge_noise(option, roll, success, critical_failure)
    complications_added = _challenge_complications(option, success, critical_failure)
    if resource is not None:
        noise_added = max(0, noise_added - resource.mitigates_noise)
        mitigated = set(resource.mitigates_complications)
        complications_added = tuple(complication for complication in complications_added if complication not in mitigated)
    if negative_effect_reduction:
        noise_added = max(0, noise_added - negative_effect_reduction)

    complications = tuple(dict.fromkeys((*current.complications, *complications_added)))
    flags = state.flags
    if completed:
        flags = set_scene_flag(flags, challenge.completed_flag, True)
    if resource is not None:
        for flag in resource.unlocks_flags:
            flags = set_scene_flag(flags, flag, True)
    updated = ExplorationChallengeState(
        challenge_id=challenge.id,
        current_progress=progress,
        noise=current.noise + noise_added,
        complications=complications,
        completed=completed,
        attempts=(
            *current.attempts,
            ExplorationChallengeAttempt(
                challenge_id=challenge.id,
                option_id=option.id,
                approach_label=option.label,
                approach_tags=option.tags,
                resource_id=resource.id if resource is not None else None,
                natural_roll=roll.natural_roll,
                total=roll.total,
                success=success,
                critical_failure=critical_failure,
                progress_added=progress_added,
                noise_added=noise_added,
                complications_added=complications_added,
            ),
        ),
    )
    new_state = replace(state, flags=flags, challenge_states=_replace_challenge_state(state, updated))
    message = _challenge_result_message(challenge, option, roll, success, critical_failure, progress_added, updated, resource)
    return ChallengeResult(
        state=new_state,
        challenge=challenge,
        option=option,
        roll=roll,
        success=success,
        critical_failure=critical_failure,
        progress_added=progress_added,
        noise_added=noise_added,
        complications_added=complications_added,
        completed=completed,
        message=message,
        resource_used=resource,
    )


def _replace_challenge_state(
    state: ExplorationState,
    updated: ExplorationChallengeState,
) -> tuple[ExplorationChallengeState, ...]:
    replaced = False
    result: list[ExplorationChallengeState] = []
    for challenge_state in state.challenge_states:
        if challenge_state.challenge_id == updated.challenge_id:
            result.append(updated)
            replaced = True
        else:
            result.append(challenge_state)
    if not replaced:
        result.append(updated)
    return tuple(sorted(result, key=lambda item: item.challenge_id))


def _challenge_noise(
    option: ExplorationChallengeOption,
    roll: D20RollResult,
    success: bool,
    critical_failure: bool,
) -> int:
    if success:
        if option.quiet_on_natural_20 and roll.is_natural_20:
            return 0
        if option.quiet_success_margin is not None and roll.total >= option.ability_check.dc + option.quiet_success_margin:
            return 0
        return max(0, option.success_noise)
    if critical_failure and option.critical_failure_noise:
        return max(0, option.critical_failure_noise)
    return max(0, option.failure_noise)


def _challenge_complications(
    option: ExplorationChallengeOption,
    success: bool,
    critical_failure: bool,
) -> tuple[str, ...]:
    if success:
        return (option.success_complication,) if option.success_complication else ()
    if critical_failure and option.critical_failure_complication:
        return (option.critical_failure_complication,)
    return (option.failure_complication,) if option.failure_complication else ()


def _challenge_result_message(
    challenge: ExplorationChallenge,
    option: ExplorationChallengeOption,
    roll: D20RollResult,
    success: bool,
    critical_failure: bool,
    progress_added: int,
    updated: ExplorationChallengeState,
    resource: ExplorationResource | None,
) -> str:
    if critical_failure and option.critical_failure_message:
        base = option.critical_failure_message
    elif success:
        base = option.success_message or "Podejście działa."
    else:
        base = option.failure_message or "Podejście nie wychodzi czysto, ale sytuacja idzie naprzód."
    resource_text = f" Użyty zasób: {resource.label}." if resource is not None else ""
    noise_text = f" Hałas: {updated.noise}." if updated.noise else " Bez dodatkowego hałasu."
    complications_text = f" Komplikacje: {', '.join(updated.complications)}." if updated.complications else ""
    completed_text = " Wyzwanie zakończone." if updated.completed else ""
    return (
        f"{base}{resource_text} Wynik testu: {roll.total}. "
        f"Dodany postęp: {progress_added}. Postęp {challenge.name}: "
        f"{updated.current_progress}/{challenge.progress_required}.{noise_text}{complications_text}{completed_text}"
    )


def visible_exploration_points(points: tuple[ExplorationPoint, ...]) -> tuple[ExplorationPoint, ...]:
    return tuple(point for point in points if point.visibility == SetupVisibility.VISIBLE and point.positions)


def zone_for_position(zones: tuple[ExplorationZone, ...], position: Coordinate) -> ExplorationZone | None:
    for zone in zones:
        if position in zone.positions:
            return zone
    return None


def set_party_zone(state: ExplorationState, zone: ExplorationZone) -> ExplorationState:
    return replace(state, party_position=PartyPosition(zone.id, zone.marker_position))


def resolve_party_check(inputs: tuple[PartyCheckInput, ...], dc: int) -> PartyCheckResult:
    if not inputs:
        raise ValueError("Party check requires at least one roll.")
    rolls = tuple((item.actor, resolve_d20_roll(D20RollInput(item.request, item.natural_roll))) for item in inputs)
    winner, winning_roll = max(rolls, key=lambda item: (item[1].total, item[1].natural_roll, item[0].name))
    return PartyCheckResult(rolls, winner, winning_roll, dc, resolve_ability_check(winning_roll, dc).success)


def resolve_zone_search(
    state: ExplorationState,
    zone: ExplorationZone,
    inputs: tuple[PartyCheckInput, ...],
) -> SearchResult:
    if zone.id in state.exhausted_search_zones:
        raise ValueError(f"Zone {zone.id} has already been searched.")
    if zone.search_dc is None:
        raise ValueError(f"Zone {zone.id} has no search configured.")
    party_check = resolve_party_check(inputs, zone.search_dc)
    exhausted = tuple(sorted((*state.exhausted_search_zones, zone.id)))
    flags = state.flags
    revealed: tuple[ExplorationPoint, ...] = ()
    points = state.points
    if party_check.success:
        if zone.search_success_flag:
            flags = set_scene_flag(flags, zone.search_success_flag, True)
        revealed_ids = set(zone.search_reveals)
        points = tuple(
            replace(point, visibility=SetupVisibility.VISIBLE) if point.id in revealed_ids else point
            for point in state.points
        )
        revealed = tuple(point for point in points if point.id in revealed_ids)
        if revealed:
            message = f"Sukces. {party_check.winner.name} osiąga wynik {party_check.winning_roll.total}. Odkrywacie ukryty element w strefie: {zone.name}."
        else:
            message = f"Sukces. {party_check.winner.name} osiąga wynik {party_check.winning_roll.total}. Uważnie sprawdzacie strefę: {zone.name}."
    else:
        if zone.search_failure_flag:
            flags = set_scene_flag(flags, zone.search_failure_flag, True)
        message = f"Porażka. Najwyższy wynik to {party_check.winning_roll.total}. Nie znajdujecie nic nowego w strefie: {zone.name}."
    return SearchResult(replace(state, points=points, flags=flags, exhausted_search_zones=exhausted), party_check, revealed, message)


def dim_color(color: tuple[int, int, int], factor: float = 0.3) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(round(component * factor)))) for component in color)


def exploration_setup_feedback(
    positions: tuple[Coordinate, ...],
    color: tuple[int, int, int],
    anchor_position: Coordinate | None = None,
) -> LedFeedback:
    if not positions:
        return LedFeedback()
    anchor = anchor_position if anchor_position in positions else None
    area_positions = tuple(position for position in positions if position != anchor)
    frames: list[LedFrame] = []
    if area_positions:
        frames.append(LedFrame(area_positions, dim_color(color), LedRole.DESTINATION))
    if anchor is not None:
        frames.append(LedFrame((anchor,), color, LedRole.DESTINATION))
    if anchor is None:
        frames.append(LedFrame(positions, dim_color(color), LedRole.DESTINATION))
    return LedFeedback(tuple(frames))


def exploration_zone_feedback(state: ExplorationState) -> LedFeedback:
    frames: list[LedFrame] = []
    for zone in available_exploration_zones(state):
        frames.append(LedFrame((zone.marker_position,), zone.color, LedRole.DESTINATION))
    for point in visible_exploration_points(state.points):
        frames.append(LedFrame(point.positions, point.color, LedRole.DESTINATION))
    return LedFeedback(tuple(frames))


def party_position_feedback(state: ExplorationState) -> LedFeedback:
    current = next((zone for zone in state.zones if zone.id == state.party_position.zone_id), None)
    if current is None:
        return LedFeedback()
    return LedFeedback((LedFrame((current.marker_position,), LedColor.ACTIVE_ACTOR, LedRole.ACTIVE_ACTOR),))


def option_feedback(zone: ExplorationZone, option: ExplorationOption) -> LedFeedback:
    area_positions = tuple(position for position in zone.positions if position != zone.marker_position)
    frames: list[LedFrame] = []
    if area_positions:
        frames.append(LedFrame(area_positions, dim_color(zone.color), LedRole.DESTINATION))
    frames.append(LedFrame((zone.marker_position,), option.color, LedRole.DESTINATION))
    return LedFeedback(tuple(frames))


def exploration_menu_feedback(menu: ExplorationMenu) -> LedFeedback:
    return LedFeedback(
        tuple(LedFrame((option.slot_position,), option.color, LedRole.DESTINATION) for option in menu.options)
    )


def look_around_feedback(zone: ExplorationZone) -> LedFeedback:
    area_positions = tuple(position for position in zone.positions if position != zone.marker_position)
    frames: list[LedFrame] = []
    if area_positions:
        frames.append(LedFrame(area_positions, dim_color(zone.color), LedRole.DESTINATION))
    frames.append(LedFrame((zone.marker_position,), zone.color, LedRole.DESTINATION))
    return LedFeedback(tuple(frames))
