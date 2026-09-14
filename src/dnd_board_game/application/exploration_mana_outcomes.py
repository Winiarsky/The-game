"""Choose a single authored result for presentation and consequences."""
from dataclasses import asdict
from typing import Any

from dnd_board_game.rules.exploration_mana import ManaAttempt
from dnd_board_game.scenarios.exploration_mana import ManaOption


def resolve_outcome(attempt: ManaAttempt, option: ManaOption) -> dict[str, Any]:
    if attempt.phase != 'result':
        raise ValueError('Próba nie ma jeszcze końcowego wyniku.')
    variant = attempt.outcome_kind
    if variant == 'success':
        if attempt.sensitive_used:
            variant = 'sensitive_success'
        elif attempt.goal_met:
            variant = 'goal_success'
    spec = next((v for v in option.variants if v.kind == variant), None)
    if option.variants and spec is None:
        raise ValueError('Brak obiecanego wariantu wyniku.')
    flags = list(spec.flags) if spec else [option.success_flag if attempt.success else option.failure_flag]
    return dict(kind=attempt.outcome_kind, variant=variant, success=attempt.success,
                message=spec.message if spec else option.success if attempt.success else option.failure,
                cost=spec.cost if spec else option.cost if attempt.success else '', flags=flags, flag=flags[0],
                followups=[asdict(f) for f in spec.followups] if spec else [])
