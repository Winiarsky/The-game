"""Deterministic, graded information discovery during exploration."""

from __future__ import annotations

from dataclasses import dataclass

from dnd_board_game.combat import SceneFlags, scene_flag
from dnd_board_game.rules import RollMode

from .models import CheckAggregation, CheckParticipants, EncounterEdgeType


@dataclass(frozen=True, slots=True)
class ObservationEncounterEdge:
    edge_type: EncounterEdgeType
    encounter_trigger_id: str
    label: str

    def __post_init__(self) -> None:
        if not self.encounter_trigger_id.strip():
            raise ValueError("Observation encounter edge trigger id cannot be empty.")
        if not self.label.strip():
            raise ValueError("Observation encounter edge label cannot be empty.")


@dataclass(frozen=True, slots=True)
class ObservationFact:
    id: str
    minimum_total: int
    narration: str
    reveal_flag: str
    effects: tuple[dict[str, object], ...] = ()
    encounter_edge: ObservationEncounterEdge | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Observation fact id cannot be empty.")
        if not 1 <= self.minimum_total <= 40:
            raise ValueError("Observation fact minimum_total must be between 1 and 40.")
        if not self.narration.strip():
            raise ValueError(f"Observation fact {self.id} narration cannot be empty.")
        if not self.reveal_flag.strip():
            raise ValueError(f"Observation fact {self.id} reveal_flag cannot be empty.")


@dataclass(frozen=True, slots=True)
class ExplorationObservation:
    id: str
    zone_id: str
    label: str
    description: str
    ability: str
    skill: str | None
    failure_message: str
    facts: tuple[ObservationFact, ...]
    challenge_id: str | None = None
    participants: CheckParticipants = CheckParticipants.SINGLE_ACTOR
    aggregation: CheckAggregation = CheckAggregation.LEAD_RESULT
    roll_mode: RollMode = RollMode.NORMAL
    intent_examples: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.zone_id.strip():
            raise ValueError("Observation id and zone_id cannot be empty.")
        if not self.label.strip() or not self.description.strip():
            raise ValueError(f"Observation {self.id} requires a label and description.")
        if not self.ability.strip():
            raise ValueError(f"Observation {self.id} ability cannot be empty.")
        if not self.failure_message.strip():
            raise ValueError(f"Observation {self.id} failure_message cannot be empty.")
        if not self.facts:
            raise ValueError(f"Observation {self.id} requires at least one fact.")
        fact_ids = tuple(fact.id for fact in self.facts)
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError(f"Observation {self.id} fact ids must be unique.")
        thresholds = tuple(fact.minimum_total for fact in self.facts)
        if thresholds != tuple(sorted(thresholds)):
            raise ValueError(f"Observation {self.id} facts must be sorted by minimum_total.")

    @property
    def dc(self) -> int:
        return self.facts[0].minimum_total

    def as_prompt_payload(self, flags: SceneFlags) -> dict[str, object]:
        return {
            "id": self.id,
            "zone_id": self.zone_id,
            "challenge_id": self.challenge_id,
            "label": self.label,
            "description": self.description,
            "ability": self.ability,
            "skill": self.skill,
            "base_dc": self.dc,
            "intent_examples": list(self.intent_examples),
            "facts": [
                {
                    "id": fact.id,
                    "minimum_total": fact.minimum_total,
                    "revealed": bool(scene_flag(flags, fact.reveal_flag, False)),
                }
                for fact in self.facts
            ],
            "rules": {
                "one_roll_reveals_all_reached_thresholds": True,
                "failure_never_proves_absence": True,
            },
        }


@dataclass(frozen=True, slots=True)
class ObservationResolution:
    observation_id: str
    total: int
    reached_facts: tuple[ObservationFact, ...]
    message: str

    @property
    def success(self) -> bool:
        return bool(self.reached_facts)


def resolve_observation(observation: ExplorationObservation, total: int) -> ObservationResolution:
    """Reveal every information tier reached by a single final check total."""

    reached = tuple(fact for fact in observation.facts if total >= fact.minimum_total)
    message = " ".join(fact.narration for fact in reached) if reached else observation.failure_message
    return ObservationResolution(
        observation_id=observation.id,
        total=total,
        reached_facts=reached,
        message=message,
    )


def match_exploration_observation(
    observations: tuple[ExplorationObservation, ...],
    player_action: str,
    *,
    zone_id: str,
    challenge_id: str | None,
    allowed_observation_ids: tuple[str, ...] = (),
) -> ExplorationObservation | None:
    """Match an explicit observation declaration to authored intent examples."""

    if not _is_observation_focused_action(player_action):
        return None
    action_stems = _observation_intent_stems(player_action)
    allowed_ids = set(allowed_observation_ids)
    scored: list[tuple[int, ExplorationObservation]] = []
    for observation in observations:
        if allowed_ids and observation.id not in allowed_ids:
            continue
        if observation.zone_id != zone_id:
            continue
        if observation.challenge_id is not None and observation.challenge_id != challenge_id:
            continue
        score = max(
            (
                len(action_stems.intersection(_observation_intent_stems(example)))
                for example in observation.intent_examples
            ),
            default=0,
        )
        if score >= 2:
            scored.append((score, observation))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0], reverse=True)
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return None
    return scored[0][1]


def _is_observation_focused_action(value: str) -> bool:
    stems = _observation_intent_stems(value)
    observation_stems = {
        "bada",
        "nasl",
        "obse",
        "ogla",
        "patr",
        "rozg",
        "spra",
        "szuk",
        "zagl",
        "zerk",
    }
    world_change_stems = {
        "budu",
        "otwi",
        "podw",
        "posz",
        "uder",
        "uzyw",
        "wyko",
        "wywa",
        "zdja",
        "zdej",
    }
    return bool(stems.intersection(observation_stems)) and not bool(stems.intersection(world_change_stems))


def _observation_intent_stems(value: str) -> frozenset[str]:
    translation = str.maketrans(
        {"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ż": "z", "ź": "z"}
    )
    generic_stems = {
        "bram",
        "chce",
        "cich",
        "jaki",
        "jest",
        "najp",
        "prze",
        "robi",
        "spro",
    }
    return frozenset(
        token[:4]
        for token in value.strip().lower().translate(translation).replace("?", " ").replace(",", " ").split()
        if len(token) >= 4 and token[:4] not in generic_stems
    )
