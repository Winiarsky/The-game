from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FeatureSourceKind(StrEnum):
    MONSTER = "monster"
    ITEM = "item"
    RACE = "race"
    SPECIES = "species"
    BACKGROUND = "background"
    CLASS = "class"
    SUBCLASS = "subclass"
    FEAT = "feat"
    SCENARIO = "scenario"


@dataclass(frozen=True, slots=True)
class FeatureGrant:
    """Runtime provenance for mechanics granted to one actor by content."""

    feature_id: str
    label: str
    source_kind: FeatureSourceKind
    source_ref: str
    description: str = ""
    resource_ids: tuple[str, ...] = ()
    action_ids: tuple[str, ...] = ()
    trigger_ids: tuple[str, ...] = ()
    aura_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.feature_id.strip():
            raise ValueError("Feature id cannot be empty.")
        if not self.label.strip():
            raise ValueError("Feature label cannot be empty.")
        if not self.source_ref.strip():
            raise ValueError("Feature source reference cannot be empty.")
        for field_name, values in (
            ("resource_ids", self.resource_ids),
            ("action_ids", self.action_ids),
            ("trigger_ids", self.trigger_ids),
            ("aura_ids", self.aura_ids),
        ):
            if any(not value.strip() for value in values):
                raise ValueError(f"Feature {field_name} cannot contain empty ids.")
            if len(values) != len(set(values)):
                raise ValueError(f"Feature {field_name} cannot contain duplicate ids.")


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    """Content-facing feature metadata and the ids of its granted mechanics."""

    id: str
    label: str
    source_kind: FeatureSourceKind
    source_ref: str
    description: str = ""
    resource_ids: tuple[str, ...] = ()
    action_ids: tuple[str, ...] = ()
    trigger_ids: tuple[str, ...] = ()
    aura_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        FeatureGrant(
            feature_id=self.id,
            label=self.label,
            source_kind=self.source_kind,
            source_ref=self.source_ref,
            description=self.description,
            resource_ids=self.resource_ids,
            action_ids=self.action_ids,
            trigger_ids=self.trigger_ids,
            aura_ids=self.aura_ids,
        )

    def grant(self) -> FeatureGrant:
        return FeatureGrant(
            feature_id=self.id,
            label=self.label,
            source_kind=self.source_kind,
            source_ref=self.source_ref,
            description=self.description,
            resource_ids=self.resource_ids,
            action_ids=self.action_ids,
            trigger_ids=self.trigger_ids,
            aura_ids=self.aura_ids,
        )


def validate_unique_feature_grants(grants: tuple[FeatureGrant, ...]) -> None:
    feature_ids = tuple(grant.feature_id for grant in grants)
    if len(feature_ids) != len(set(feature_ids)):
        raise ValueError("Actor feature ids cannot contain duplicates.")


__all__ = [
    "FeatureDefinition",
    "FeatureGrant",
    "FeatureSourceKind",
    "validate_unique_feature_grants",
]
