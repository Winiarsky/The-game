import json
from pathlib import Path

from dnd_board_game.character_creation.spell_effect_consumers import (
    consumer_for_combat_effect,
)
from dnd_board_game.character_creation.srd_manifest import SRD_SPELL_IDS_BY_LEVEL


def test_every_srd_combat_spell_effect_has_registered_runtime_consumer() -> None:
    missing: list[str] = []
    spell_ids = set().union(*map(set, SRD_SPELL_IDS_BY_LEVEL.values()))
    for spell_id in sorted(spell_ids):
        payload = json.loads(
            Path(f"content/spells/{spell_id}.json").read_text(encoding="utf-8")
        )
        effect = payload.get("effect", {})
        if effect.get("kind") != "combat_action":
            continue
        if consumer_for_combat_effect(effect) is None:
            missing.append(
                f"{spell_id}:{effect.get('action_type')}:{effect.get('effect_kind')}"
            )

    assert missing == []
