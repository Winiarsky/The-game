from __future__ import annotations

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
