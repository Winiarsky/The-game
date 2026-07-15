"""Deterministic matching of player wording to visible exploration sources."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .crafting_sources import CraftingSource, CraftingSourceKind, CraftingSourceRegistry
from .models import ExplorationState, SceneSourceDiscovery


@dataclass(frozen=True, slots=True)
class SceneSourceMatch:
    source: CraftingSource
    direct_label_match: bool
    matched_preferred_properties: tuple[str, ...] = ()

_SEARCH_STEMS = frozenset({"szuk", "znal", "rozg", "wido", "lezy", "jest"})
_WORLD_CHANGE_STEMS = frozenset(
    {
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
)


def match_visible_scene_sources(
    registry: CraftingSourceRegistry,
    player_text: str,
) -> tuple[SceneSourceMatch, ...]:
    """Return visible scene items/fixtures explicitly named by a player."""

    return match_available_sources(
        registry,
        player_text,
        allowed_kinds=frozenset(
            {CraftingSourceKind.SCENE_ITEM, CraftingSourceKind.SCENE_FIXTURE}
        ),
    )


def match_available_sources(
    registry: CraftingSourceRegistry,
    player_text: str,
    *,
    allowed_kinds: frozenset[CraftingSourceKind] | None = None,
) -> tuple[SceneSourceMatch, ...]:
    """Match explicit source names across scene, party resources and inventory."""

    query_stems = _word_stems(player_text)
    scored: list[tuple[int, SceneSourceMatch]] = []
    for source in registry.available_sources:
        if allowed_kinds is not None and source.kind not in allowed_kinds:
            continue
        label_stems = _word_stems(f"{source.label} {source.reference_id} {source.definition_id or ''}")
        direct_overlap = query_stems.intersection(label_stems)
        direct = bool(direct_overlap)
        if not direct:
            continue
        score = 100 + len(direct_overlap)
        scored.append((score, SceneSourceMatch(source=source, direct_label_match=True)))
    if not scored:
        return ()
    scored.sort(key=lambda item: (-item[0], item[1].source.label, item[1].source.id))
    return tuple(match for _score, match in scored)


def match_scene_sources_by_properties(
    registry: CraftingSourceRegistry,
    *,
    required_properties: tuple[str, ...],
    preferred_properties: tuple[str, ...] = (),
) -> tuple[SceneSourceMatch, ...]:
    """Choose existing visible sources satisfying an abstract functional need."""

    required = frozenset(required_properties)
    preferred = frozenset(preferred_properties)
    scored: list[tuple[int, SceneSourceMatch]] = []
    for source in registry.available_sources:
        if source.kind not in {CraftingSourceKind.SCENE_ITEM, CraftingSourceKind.SCENE_FIXTURE}:
            continue
        if not required.issubset(source.properties):
            continue
        matched_preferred = tuple(sorted(preferred.intersection(source.properties)))
        if not required and preferred and not matched_preferred:
            continue
        scored.append(
            (
                len(matched_preferred),
                SceneSourceMatch(
                    source=source,
                    direct_label_match=False,
                    matched_preferred_properties=matched_preferred,
                ),
            )
        )
    if not scored:
        return ()
    scored.sort(key=lambda item: (-item[0], item[1].source.label, item[1].source.id))
    best_score = scored[0][0]
    return tuple(match for score, match in scored if score == best_score)


def validate_source_property_query(
    *,
    required_properties: tuple[str, ...],
    preferred_properties: tuple[str, ...],
    allowed_property_ids: tuple[str, ...],
) -> None:
    """Reject an LLM query that escaped the data-driven property vocabulary."""

    requested = frozenset((*required_properties, *preferred_properties))
    if not requested:
        raise ValueError("Zapytanie o źródło musi wskazywać co najmniej jedną właściwość.")
    unknown = requested - frozenset(allowed_property_ids)
    if unknown:
        raise ValueError(
            "Zapytanie o źródło zawiera nieznane właściwości: " + ", ".join(sorted(unknown)) + "."
        )


def discover_scene_source(
    state: ExplorationState,
    source: CraftingSource,
    *,
    requested_as: str = "",
    purpose: str = "",
    matched_properties: tuple[str, ...] = (),
    semantic_substitution: bool = False,
) -> ExplorationState:
    """Persist player knowledge without moving a scene object into inventory."""

    if source.kind not in {CraftingSourceKind.SCENE_ITEM, CraftingSourceKind.SCENE_FIXTURE}:
        raise ValueError("Only scene items and fixtures can become scene discoveries.")
    if source.zone_id is None:
        raise ValueError("A discovered scene source must belong to a zone.")
    discovery = SceneSourceDiscovery(
        source_id=source.id,
        zone_id=source.zone_id,
        requested_as=requested_as.strip(),
        purpose=purpose.strip(),
        matched_properties=tuple(dict.fromkeys(matched_properties)),
        semantic_substitution=semantic_substitution,
    )
    remaining = tuple(item for item in state.source_discoveries if item.source_id != source.id)
    return replace(state, source_discoveries=(*remaining, discovery))


def is_source_lookup_only(player_text: str, *, explicit_search: bool) -> bool:
    """Separate asking for an existing source from using it to change the scene."""

    stems = _word_stems(player_text)
    if stems.intersection(_WORLD_CHANGE_STEMS):
        return False
    return explicit_search or bool(stems.intersection(_SEARCH_STEMS))


def describes_direct_source_use(player_text: str) -> bool:
    return bool(_word_stems(player_text).intersection(_WORLD_CHANGE_STEMS))


def _word_stems(value: str) -> frozenset[str]:
    translation = str.maketrans(
        {"ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ż": "z", "ź": "z"}
    )
    normalized = value.lower().translate(translation)
    for marker in "?.,:;!()[]/\\-_":
        normalized = normalized.replace(marker, " ")
    stems: set[str] = set()
    ignored_stems = {"chce", "jaki", "star", "tego", "taki"}
    for token in normalized.split():
        if len(token) < 3:
            continue
        stem = "kij" if token.startswith("kij") else token[:4]
        if stem not in ignored_stems:
            stems.add(stem)
    return frozenset(stems)


__all__ = [
    "SceneSourceMatch",
    "discover_scene_source",
    "describes_direct_source_use",
    "is_source_lookup_only",
    "match_available_sources",
    "match_scene_sources_by_properties",
    "match_visible_scene_sources",
    "validate_source_property_query",
]
