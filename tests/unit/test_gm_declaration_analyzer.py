from dnd_board_game.llm import GmDeclarationAnalysis, GmDeclarationAnalysisType, PromptId, load_prompt


def test_declaration_analyzer_prompt_is_centralized():
    prompt = load_prompt(PromptId.GM_DECLARATION_ANALYZER)

    assert "pistoletem laserowym" in prompt
    assert "wyważam bramę mocnym dmuchnięciem" in prompt
    assert "player_question" in prompt


def test_declaration_analysis_accepts_unsupported_fantasy_breaking_action():
    analysis = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "unsupported",
            "player_message": "Laserowy pistolet nie pasuje do tej sceny fantasy i nie ma go w zasobach drużyny.",
            "normalized_intent": "Użycie broni technologicznej spoza sceny.",
            "reason": "Deklaracja łamie założenia gatunku i dostępne zasoby.",
            "confidence": 0.95,
        }
    )

    assert analysis.analysis_type == GmDeclarationAnalysisType.UNSUPPORTED


def test_declaration_analysis_accepts_plausible_climbing_interpretation():
    analysis = GmDeclarationAnalysis.model_validate(
        {
            "analysis_type": "plausible",
            "player_message": "Rozumiem to jako próbę przejścia górą po uszkodzonych przęsłach.",
            "normalized_intent": "Wspinaczka po bramie na drugą stronę.",
            "reason": "Deklaracja pasuje do aktywnego wyzwania i lokalnego kontekstu.",
            "confidence": 0.78,
        }
    )

    assert analysis.analysis_type == GmDeclarationAnalysisType.PLAUSIBLE
