from __future__ import annotations

from types import SimpleNamespace

from bonuses import BonusEffect, BonusType, build_modifiers_grid
from GameObjects.NPC.base_npc import BaseNPC
from GameObjects.Interactables.skill_challenge import SkillChallenge
from GameObjects.interactions_mixin import prompt_utils
from GameObjects.interactions_mixin.skill_check_resolver import _skill_roll_stack_payload
from prompt_audio import default_roll_audio


class _Conn:
    def __init__(self):
        self.led_calls = []
        self.off_calls = 0

    def set_leds(self, positions, colors):
        self.led_calls.append((list(positions), list(colors)))

    def leds_off(self):
        self.off_calls += 1


class _UI:
    enabled = True

    def __init__(self):
        self.choice_calls = []
        self.info_calls = []

    def prompt_choice(self, title, *, choices, **kwargs):
        self.choice_calls.append({"title": title, "choices": list(choices), "kwargs": dict(kwargs)})
        return "ask"

    def prompt_info(self, title, *, prompt_long=None, **kwargs):
        self.info_calls.append({"title": title, "prompt_long": prompt_long, "kwargs": dict(kwargs)})
        return "ok"


def test_modifier_tiles_keep_specific_source_label():
    modifiers = build_modifiers_grid(
        [
            BonusEffect(
                type=BonusType.STATUS,
                value=2,
                tag="diplomacy",
                source="status:group_impression",
                label="Group Impression +2",
            )
        ]
    )

    payload = _skill_roll_stack_payload(
        base_components=[],
        modifiers_grid=modifiers,
        total_modifier=2,
    )

    components = list(payload["components"])
    status_component = next(item for item in components if item["id"] == "status")
    assert status_component == {
        "id": "status",
        "label": "Group Impression +2",
        "value": 2,
        "description": "status bonus",
        "type": "status",
        "editable": True,
    }


def test_dialog_prompts_get_runtime_audio_image_context_and_scoped_led_highlight():
    ui = _UI()
    conn = _Conn()
    game = SimpleNamespace(
        ui=ui,
        conn=conn,
        scenario_session=SimpleNamespace(current_map_id="brindleford_square"),
    )
    npc = BaseNPC(
        name="Nila Ashwick",
        npc_id="nila_ashwick",
        portrait_image="/assets/ui_v2/ashen_oath/images/characters/nila_ashwick.png",
        dialog={
            "start": {
                "title": "Nila Ashwick",
                "text": "Nila patrzy ku studni.",
                "options": [
                    {
                        "id": "ask",
                        "label": "Zapytaj.",
                        "text": "Wskazuje miejsce przy studni.",
                        "board_highlights": [{"position": [7, 10], "color": [80, 170, 255]}],
                    }
                ],
            }
        },
    )

    npc.action_talk(None, game)

    choice_kwargs = ui.choice_calls[0]["kwargs"]
    assert choice_kwargs["image"].endswith("/nila_ashwick.png")
    assert choice_kwargs["audio"] == "audio/voiceover/runtime_dialogue/brindleford_square_nila_ashwick_start_opening_001.mp3"
    assert choice_kwargs["communication"]["context"]["npc_id"] == "nila_ashwick"

    info_kwargs = ui.info_calls[0]["kwargs"]
    assert info_kwargs["audio"] == "audio/voiceover/runtime_dialogue/brindleford_square_nila_ashwick_start_ask_text_001.mp3"
    assert info_kwargs["communication"]["context"]["board_highlights"] == [{"position": [7, 10], "color": [80, 170, 255]}]
    assert conn.led_calls == [([(7, 10)], [[80, 170, 255]])]
    assert conn.off_calls == 1


def test_generic_roll_audio_paths_cover_skills_attacks_saves_and_damage():
    assert default_roll_audio("Test Diplomacy (DC 14).", layout="test") == (
        "audio/voiceover/runtime_prompts/roll_diplomacy_prompt_001.mp3"
    )
    assert default_roll_audio("Reflex save przeciw DC 17", layout="test") == (
        "audio/voiceover/runtime_prompts/roll_reflex_prompt_001.mp3"
    )
    assert default_roll_audio("Atak zaklęciem przeciwko AC 18", layout="test") == (
        "audio/voiceover/runtime_prompts/roll_spell_attack_prompt_001.mp3"
    )
    assert default_roll_audio("Atak mieczem przeciwko AC 16", layout="test") == (
        "audio/voiceover/runtime_prompts/roll_attack_prompt_001.mp3"
    )
    assert default_roll_audio("Longsword: obrażenia 1d8+4", layout="damage") == (
        "audio/voiceover/runtime_prompts/roll_damage_prompt_001.mp3"
    )


def test_prompt_utils_attaches_generic_audio_to_roll_prompt(monkeypatch):
    class _RollUI:
        enabled = True

        def __init__(self):
            self.calls = []

        def prompt_roll(self, prompt, **kwargs):
            self.calls.append({"prompt": prompt, "kwargs": dict(kwargs)})
            return {"roll": 12, "raw_roll": 12, "natural_mode": "none"}

    ui = _RollUI()
    monkeypatch.setattr(prompt_utils, "get_ui_client", lambda: ui)

    result = prompt_utils.prompt_for_roll(
        "Atak zaklęciem przeciwko AC 18",
        layout="test",
        return_details=True,
    )

    assert result["roll"] == 12
    assert ui.calls[0]["kwargs"]["audio"] == "audio/voiceover/runtime_prompts/roll_spell_attack_prompt_001.mp3"


def test_skill_challenge_intro_gets_runtime_voiceover_path():
    ui = _UI()
    game = SimpleNamespace(
        ui=ui,
        scenario_session=SimpleNamespace(current_map_id="brindleford_square"),
    )
    challenge = SkillChallenge(
        challenge_id="market_speech_crowd_anchor",
        label="Ustaw punkt przy mieszkańcach",
        intro="Przy piecu chlebowym stoi kilku mieszkańców.",
    )

    challenge._prompt_info(game, challenge.challenge_label, challenge.intro, source_suffix="intro")

    kwargs = ui.info_calls[0]["kwargs"]
    assert kwargs["audio"] == "audio/voiceover/runtime_dialogue/brindleford_square_market_speech_crowd_anchor_intro_001.mp3"
    assert kwargs["prompt_id"] == "skill_challenge.market_speech_crowd_anchor.intro"


def test_skill_challenge_can_be_gated_by_required_flag():
    game = SimpleNamespace(
        scenario_session=SimpleNamespace(global_flags={}),
    )
    challenge = SkillChallenge(
        challenge_id="clean_water_spigot",
        label="Znajdź czystą wodę dla Brena",
        conditions={"all_flags": ["bren_examined"]},
    )

    assert challenge.can_interact(None, game) is False
    game.scenario_session.global_flags["bren_examined"] = True
    assert challenge.can_interact(None, game) is True


def test_hidden_skill_challenge_requires_seek_reveal_before_attempt():
    game = SimpleNamespace(
        scenario_session=SimpleNamespace(global_flags={"bren_examined": True}),
    )
    challenge = SkillChallenge(
        challenge_id="clean_water_spigot",
        label="Znajdź czystą wodę dla Brena",
        conditions={"all_flags": ["bren_examined"]},
        hidden=True,
        reveal_dc=14,
        description_on_reveal="Odnajdujecie mały odpływ.",
    )

    assert challenge.can_interact(None, game) is True
    assert challenge.action_attempt(None, game) == "Najpierw trzeba odkryć to miejsce."
    outcome, message = challenge.try_reveal(14)
    assert outcome == "success"
    assert "odpływ" in message
    assert challenge.revealed is True
