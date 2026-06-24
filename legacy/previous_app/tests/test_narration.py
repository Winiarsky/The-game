from __future__ import annotations

from GameObjects.events.enemy.enemy_strike_event import goblin_pox_description
from narration import narrate_action_event


def test_narration_localizes_spell_pre_action_ids():
    message = narrate_action_event(
        {
            "actor": {"name": "Freya"},
            "action_id": "acidsplash_pre",
        }
    )

    assert message == "Freya wykonuje akcję: Kwasowy rozprysk."


def test_narration_keeps_attack_family_as_attack():
    message = narrate_action_event(
        {
            "actor": {"name": "Freya"},
            "action_id": "attack_sword_pre",
            "target": {"name": "Goblin"},
        }
    )

    assert message == "Freya atakuje Goblin."


def test_goblin_pox_description_mentions_stages_and_sickened():
    text = goblin_pox_description()

    assert "Etap 1" in text
    assert "Sickened 1" in text
    assert "Slowed 1" in text
