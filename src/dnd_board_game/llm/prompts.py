from __future__ import annotations

from enum import StrEnum
from pathlib import Path


class PromptId(StrEnum):
    GM_DECLARATION_ANALYZER = "gm_declaration_analyzer"
    GM_CHALLENGE_CLASSIFIER = "gm_challenge_classifier"


PROMPT_PATHS: dict[PromptId, Path] = {
    PromptId.GM_DECLARATION_ANALYZER: Path("content/prompts/gm_declaration_analyzer_pl.md"),
    PromptId.GM_CHALLENGE_CLASSIFIER: Path("content/prompts/gm_challenge_classifier_pl.md"),
}


def load_prompt(prompt_id: PromptId) -> str:
    return PROMPT_PATHS[prompt_id].read_text(encoding="utf-8")
