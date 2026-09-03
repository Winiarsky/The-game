"""Deterministic exploration-card reactions to application prompts.

The module deliberately knows nothing about Flask, QR scanners or scenario files.
It answers one question: may this actor declare this card while the current
prompt is waiting, and which authored handler should take over the flow?
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ExplorationPromptKind(StrEnum):
    FREE_ACTION = "free_action"
    INTERACTION = "interaction"
    BEFORE_ROLL = "before_roll"
    AFTER_RESULT = "after_result"
    REST = "rest"


class CardRetryPolicy(StrEnum):
    ONCE_PER_PROMPT = "once_per_prompt"
    ONCE_PER_INSTANCE = "once_per_instance"
    UNTIL_STATE_CHANGES = "until_state_changes"
    REPEATABLE_WITH_COST = "repeatable_with_cost"


class ExplorationCardEffectKind(StrEnum):
    ADD_OPTION = "add_option"
    MODIFY_CHECK = "modify_check"
    REPLACE_RESULT = "replace_result"
    SET_FLAG = "set_flag"
    START_CHECK = "start_check"
    REST_PREPARATION = "rest_preparation"


@dataclass(frozen=True, slots=True)
class ExplorationPrompt:
    id: str
    kind: ExplorationPromptKind
    tags: frozenset[str]
    eligible_actor_ids: tuple[str, ...]
    instance_id: str
    interaction_id: str | None = None
    handler_ids: frozenset[str] = frozenset({"*"})


@dataclass(frozen=True, slots=True)
class ExplorationCardHandler:
    card_action_id: str
    prompt_kinds: frozenset[ExplorationPromptKind]
    effect_kind: ExplorationCardEffectKind
    required_any_tags: frozenset[str] = frozenset()
    retry_policy: CardRetryPolicy = CardRetryPolicy.ONCE_PER_PROMPT
    result_flag: str | None = None
    player_label: str = ""

    def accepts(self, prompt: ExplorationPrompt) -> bool:
        if "*" not in prompt.handler_ids and self.card_action_id not in prompt.handler_ids:
            return False
        if prompt.kind not in self.prompt_kinds:
            return False
        return not self.required_any_tags or bool(
            self.required_any_tags.intersection(prompt.tags)
        )


@dataclass(frozen=True, slots=True)
class PendingExplorationCard:
    card_action_id: str
    actor_id: str
    prompt_id: str
    handler: ExplorationCardHandler
    attempt_key: str


def card_attempt_key(
    handler: ExplorationCardHandler,
    prompt: ExplorationPrompt,
    actor_id: str,
) -> str:
    if handler.retry_policy is CardRetryPolicy.ONCE_PER_INSTANCE:
        scope = prompt.instance_id
    elif handler.retry_policy is CardRetryPolicy.UNTIL_STATE_CHANGES:
        scope = f"{prompt.instance_id}:{prompt.id}"
    else:
        scope = prompt.id
    return f"{scope}:{actor_id}:{handler.card_action_id}"


def declare_exploration_card(
    *,
    handler: ExplorationCardHandler,
    prompt: ExplorationPrompt,
    actor_id: str,
    spent_attempt_keys: frozenset[str] = frozenset(),
) -> PendingExplorationCard:
    if actor_id not in prompt.eligible_actor_ids:
        raise ValueError("Ta postać nie uczestniczy w aktualnym prompcie.")
    if not handler.accepts(prompt):
        raise ValueError("Ta karta nie pasuje do aktualnej decyzji.")
    attempt_key = card_attempt_key(handler, prompt, actor_id)
    if (
        handler.retry_policy is not CardRetryPolicy.REPEATABLE_WITH_COST
        and attempt_key in spent_attempt_keys
    ):
        raise ValueError("Ta karta została już wykorzystana w tej sytuacji.")
    return PendingExplorationCard(
        card_action_id=handler.card_action_id,
        actor_id=actor_id,
        prompt_id=prompt.id,
        handler=handler,
        attempt_key=attempt_key,
    )


_FREE_OR_INTERACTION = frozenset(
    {ExplorationPromptKind.FREE_ACTION, ExplorationPromptKind.INTERACTION}
)


EXPLORATION_CARD_HANDLERS: dict[str, ExplorationCardHandler] = {
    "guard_duty": ExplorationCardHandler(
        "guard_duty",
        frozenset({ExplorationPromptKind.REST}),
        ExplorationCardEffectKind.REST_PREPARATION,
        frozenset({"short_rest"}),
        CardRetryPolicy.ONCE_PER_PROMPT,
        "short_rest_alarm_active",
        "Warta",
    ),
    "alarm": ExplorationCardHandler(
        "alarm",
        frozenset({ExplorationPromptKind.REST}),
        ExplorationCardEffectKind.REST_PREPARATION,
        frozenset({"short_rest"}),
        CardRetryPolicy.ONCE_PER_PROMPT,
        "short_rest_alarm_active",
        "Alarm",
    ),
    "tactical_assessment": ExplorationCardHandler(
        "tactical_assessment", _FREE_OR_INTERACTION,
        ExplorationCardEffectKind.ADD_OPTION,
        frozenset({"tactical", "guard", "route", "hazard", "location"}),
        CardRetryPolicy.ONCE_PER_INSTANCE,
        "tactical_assessment",
        "Taktyczna ocena",
    ),
    "intimidation": ExplorationCardHandler(
        "intimidation", frozenset({ExplorationPromptKind.INTERACTION}),
        ExplorationCardEffectKind.ADD_OPTION,
        frozenset({"conversation", "npc", "negotiation"}),
        CardRetryPolicy.ONCE_PER_PROMPT,
        "intimidation_attempt",
        "Zastraszanie siłą",
    ),
    "brutal_effort": ExplorationCardHandler(
        "brutal_effort", frozenset({ExplorationPromptKind.BEFORE_ROLL}),
        ExplorationCardEffectKind.MODIFY_CHECK,
        frozenset({"strength", "athletics"}),
        CardRetryPolicy.REPEATABLE_WITH_COST,
        player_label="Brutalny wysiłek",
    ),
    "break_in": ExplorationCardHandler(
        "break_in", frozenset({ExplorationPromptKind.INTERACTION}),
        ExplorationCardEffectKind.ADD_OPTION,
        frozenset({"lock", "security", "closed", "pickpocket", "npc"}),
        CardRetryPolicy.ONCE_PER_PROMPT,
        "break_in_attempt",
        "Włamanie",
    ),
    "tracking": ExplorationCardHandler(
        "tracking", _FREE_OR_INTERACTION,
        ExplorationCardEffectKind.START_CHECK,
        frozenset({"tracks", "trail", "travel", "target", "location"}),
        CardRetryPolicy.ONCE_PER_INSTANCE,
        "tracking_attempt",
        "Tropienie",
    ),
    "guidance": ExplorationCardHandler(
        "guidance", frozenset({ExplorationPromptKind.BEFORE_ROLL}),
        ExplorationCardEffectKind.MODIFY_CHECK,
        retry_policy=CardRetryPolicy.REPEATABLE_WITH_COST,
        player_label="Wskazówki",
    ),
    "bardic_inspiration": ExplorationCardHandler(
        "bardic_inspiration", frozenset({ExplorationPromptKind.BEFORE_ROLL}),
        ExplorationCardEffectKind.MODIFY_CHECK,
        retry_policy=CardRetryPolicy.REPEATABLE_WITH_COST,
        player_label="Inspiracja bardowska",
    ),
    "charm_person": ExplorationCardHandler(
        "charm_person", frozenset({ExplorationPromptKind.INTERACTION}),
        ExplorationCardEffectKind.ADD_OPTION,
        frozenset({"conversation", "npc"}),
        CardRetryPolicy.ONCE_PER_PROMPT,
        "charm_person_attempt",
        "Zauroczenie osoby",
    ),
    "suggestion": ExplorationCardHandler(
        "suggestion", frozenset({ExplorationPromptKind.INTERACTION}),
        ExplorationCardEffectKind.ADD_OPTION,
        frozenset({"conversation", "npc"}),
        CardRetryPolicy.ONCE_PER_PROMPT,
        "suggestion_attempt",
        "Sugestia",
    ),
    "calm_emotions": ExplorationCardHandler(
        "calm_emotions", frozenset({ExplorationPromptKind.AFTER_RESULT}),
        ExplorationCardEffectKind.REPLACE_RESULT,
        frozenset({"charisma_failure", "charisma_critical_failure"}),
        CardRetryPolicy.REPEATABLE_WITH_COST,
        player_label="Uspokojenie emocji",
    ),
    "detect_magic": ExplorationCardHandler(
        "detect_magic", _FREE_OR_INTERACTION,
        ExplorationCardEffectKind.SET_FLAG,
        frozenset({"magic", "location", "object"}),
        CardRetryPolicy.UNTIL_STATE_CHANGES,
        "detect_magic",
        "Wykrycie magii",
    ),
    "find_traps": ExplorationCardHandler(
        "find_traps", _FREE_OR_INTERACTION,
        ExplorationCardEffectKind.SET_FLAG,
        frozenset({"trap", "hazard", "location"}),
        CardRetryPolicy.ONCE_PER_INSTANCE,
        "detect_traps",
        "Wykrycie pułapek",
    ),
    "locate_object": ExplorationCardHandler(
        "locate_object", _FREE_OR_INTERACTION,
        ExplorationCardEffectKind.START_CHECK,
        frozenset({"search", "object", "location"}),
        CardRetryPolicy.ONCE_PER_INSTANCE,
        "locate_object",
        "Zlokalizowanie przedmiotu",
    ),
    "mage_hand": ExplorationCardHandler(
        "mage_hand", frozenset({ExplorationPromptKind.INTERACTION}),
        ExplorationCardEffectKind.ADD_OPTION,
        frozenset({"object", "fixture", "mechanism"}),
        CardRetryPolicy.REPEATABLE_WITH_COST,
        player_label="Magiczna dłoń",
    ),
    "identify": ExplorationCardHandler(
        "identify", frozenset({ExplorationPromptKind.REST, ExplorationPromptKind.INTERACTION}),
        ExplorationCardEffectKind.SET_FLAG,
        frozenset({"safe_break", "inventory_item", "object"}),
        CardRetryPolicy.ONCE_PER_INSTANCE,
        "identified_item",
        "Identyfikacja",
    ),
    "pass_without_trace": ExplorationCardHandler(
        "pass_without_trace", _FREE_OR_INTERACTION,
        ExplorationCardEffectKind.MODIFY_CHECK,
        frozenset({"travel", "infiltration", "stealth"}),
        CardRetryPolicy.REPEATABLE_WITH_COST,
        player_label="Przejście bez śladu",
    ),
}


def exploration_card_handler(action_id: str) -> ExplorationCardHandler | None:
    return EXPLORATION_CARD_HANDLERS.get(action_id)


__all__ = [
    "CardRetryPolicy",
    "EXPLORATION_CARD_HANDLERS",
    "ExplorationCardEffectKind",
    "ExplorationCardHandler",
    "ExplorationPrompt",
    "ExplorationPromptKind",
    "PendingExplorationCard",
    "card_attempt_key",
    "declare_exploration_card",
    "exploration_card_handler",
]
