from dnd_board_game.combat import SceneFlags, set_scene_flag
from dnd_board_game.exploration import (
    NpcArgumentAssessment,
    NpcArgumentEvaluationPolicy,
    NpcArgumentLeverage,
    NpcArgumentLeverageClaim,
    evaluate_npc_argument,
)
from dnd_board_game.rules import RollMode


def _policy() -> NpcArgumentEvaluationPolicy:
    return NpcArgumentEvaluationPolicy(
        (
            NpcArgumentLeverage(
                id="nessa_priority",
                label="Nessie szczególnie zależy na skrzyniach z pyłem.",
                required_flags=("knowledge.nessa_true_priority_known",),
                compatible_skills=("persuasion", "deception", "intimidation"),
                max_strength=2,
            ),
        )
    )


def test_argument_evaluation_rejects_unearned_leverage_without_trusting_llm() -> None:
    result = evaluate_npc_argument(
        _policy(),
        NpcArgumentAssessment(
            intent_fit=1,
            specificity=1,
            credibility=0,
            leverage_claims=(NpcArgumentLeverageClaim("nessa_priority", 2),),
        ),
        selected_skill="persuasion",
        flags=SceneFlags(),
    )

    assert result.score == 2
    assert result.modifier == 1
    assert result.roll_mode == RollMode.NORMAL
    assert result.accepted_leverage_ids == ()


def test_argument_evaluation_maps_known_strong_leverage_to_advantage() -> None:
    flags = set_scene_flag(SceneFlags(), "knowledge.nessa_true_priority_known", True)

    result = evaluate_npc_argument(
        _policy(),
        NpcArgumentAssessment(
            intent_fit=1,
            specificity=1,
            credibility=0,
            leverage_claims=(NpcArgumentLeverageClaim("nessa_priority", 2),),
        ),
        selected_skill="deception",
        flags=flags,
    )

    assert result.score == 4
    assert result.modifier == 0
    assert result.roll_mode == RollMode.ADVANTAGE
    assert result.accepted_leverage_ids == ("nessa_priority",)


def test_argument_evaluation_maps_bad_argument_to_disadvantage() -> None:
    result = evaluate_npc_argument(
        _policy(),
        NpcArgumentAssessment(intent_fit=-2, specificity=0, credibility=-2),
        selected_skill="intimidation",
        flags=SceneFlags(),
    )

    assert result.score == -4
    assert result.roll_mode == RollMode.DISADVANTAGE
