import pytest

from dnd_board_game.actors import (
    FeatureDefinition,
    FeatureGrant,
    FeatureSourceKind,
)


def test_feature_definition_builds_runtime_grant_with_provenance() -> None:
    definition = FeatureDefinition(
        id="second_wind",
        label="Second Wind",
        description="Regain hit points.",
        source_kind=FeatureSourceKind.CLASS,
        source_ref="fighter",
        resource_ids=("second_wind_uses",),
        action_ids=("second_wind",),
    )

    grant = definition.grant()

    assert grant == FeatureGrant(
        feature_id="second_wind",
        label="Second Wind",
        description="Regain hit points.",
        source_kind=FeatureSourceKind.CLASS,
        source_ref="fighter",
        resource_ids=("second_wind_uses",),
        action_ids=("second_wind",),
    )


def test_feature_grant_rejects_duplicate_component_ids() -> None:
    with pytest.raises(ValueError, match="duplicate ids"):
        FeatureGrant(
            feature_id="duplicate",
            label="Duplicate",
            source_kind=FeatureSourceKind.ITEM,
            source_ref="item",
            action_ids=("same", "same"),
        )
