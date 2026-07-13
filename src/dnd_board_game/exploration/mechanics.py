"""Named exploration mechanic tools selected by GM interpretation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .models import CheckAggregation, CheckParticipants, ExplorationChallengeOption


class ExplorationMechanicId(StrEnum):
    SINGLE_ACTOR_CHECK = "single_actor_check"
    LEAD_WITH_HELP_CHECK = "lead_with_help_check"
    GROUP_CHECK = "group_check"
    USE_ITEM_CHECK = "use_item_check"
    USE_SPELL_CHECK = "use_spell_check"
    IMPROVISED_TOOL_CHECK = "improvised_tool_check"
    PREPARATION_EFFECT = "preparation_effect"


@dataclass(frozen=True, slots=True)
class ExplorationMechanicTool:
    id: ExplorationMechanicId
    label: str
    description: str
    participants: CheckParticipants | None
    aggregations: tuple[CheckAggregation, ...]
    requires_item: bool = False
    requires_spell: bool = False
    requires_gm_approval: bool = False

    def as_payload(self) -> dict[str, object]:
        return {
            "id": self.id.value,
            "label": self.label,
            "description": self.description,
            "participants": self.participants.value if self.participants is not None else None,
            "aggregations": [aggregation.value for aggregation in self.aggregations],
            "requires_item": self.requires_item,
            "requires_spell": self.requires_spell,
            "requires_gm_approval": self.requires_gm_approval,
        }


MECHANIC_TOOLS: dict[ExplorationMechanicId, ExplorationMechanicTool] = {
    ExplorationMechanicId.SINGLE_ACTOR_CHECK: ExplorationMechanicTool(
        id=ExplorationMechanicId.SINGLE_ACTOR_CHECK,
        label="Jedna postać",
        description="Jedna postać wykonuje test, a wynik tej postaci rozstrzyga próbę.",
        participants=CheckParticipants.SINGLE_ACTOR,
        aggregations=(CheckAggregation.LEAD_RESULT,),
    ),
    ExplorationMechanicId.LEAD_WITH_HELP_CHECK: ExplorationMechanicTool(
        id=ExplorationMechanicId.LEAD_WITH_HELP_CHECK,
        label="Prowadzący z pomocą",
        description="Jedna postać prowadzi działanie, a druga pomaga; docelowo pomoc daje przewagę prowadzącemu.",
        participants=CheckParticipants.LEAD_WITH_HELP,
        aggregations=(CheckAggregation.LEAD_RESULT,),
    ),
    ExplorationMechanicId.GROUP_CHECK: ExplorationMechanicTool(
        id=ExplorationMechanicId.GROUP_CHECK,
        label="Test grupowy",
        description="Kilka postaci albo cała drużyna rzuca, a wynik jest agregowany według typu próby.",
        participants=CheckParticipants.WHOLE_PARTY,
        aggregations=(
            CheckAggregation.HIGHEST,
            CheckAggregation.LOWEST,
            CheckAggregation.MAJORITY,
            CheckAggregation.ALL_MUST_SUCCEED,
            CheckAggregation.ANY_SUCCESS,
            CheckAggregation.SUM_PROGRESS,
        ),
    ),
    ExplorationMechanicId.USE_ITEM_CHECK: ExplorationMechanicTool(
        id=ExplorationMechanicId.USE_ITEM_CHECK,
        label="Użycie przedmiotu",
        description="Postać używa dostępnego itemu jako wymogu, premii, kosztu albo ryzyka testu.",
        participants=CheckParticipants.SINGLE_ACTOR,
        aggregations=(CheckAggregation.LEAD_RESULT,),
        requires_item=True,
    ),
    ExplorationMechanicId.USE_SPELL_CHECK: ExplorationMechanicTool(
        id=ExplorationMechanicId.USE_SPELL_CHECK,
        label="Użycie czaru",
        description="Postać używa znanego/przygotowanego czaru; cantrip nie zużywa slotu, czar poziomu 1+ wymaga slotu.",
        participants=CheckParticipants.SINGLE_ACTOR,
        aggregations=(CheckAggregation.LEAD_RESULT,),
        requires_spell=True,
    ),
    ExplorationMechanicId.IMPROVISED_TOOL_CHECK: ExplorationMechanicTool(
        id=ExplorationMechanicId.IMPROVISED_TOOL_CHECK,
        label="Improwizowane narzędzie",
        description="MG dopuszcza prowizoryczny zamiennik wymaganego itemu, zwykle z karą lub większym ryzykiem.",
        participants=CheckParticipants.SINGLE_ACTOR,
        aggregations=(CheckAggregation.LEAD_RESULT,),
        requires_gm_approval=True,
    ),
    ExplorationMechanicId.PREPARATION_EFFECT: ExplorationMechanicTool(
        id=ExplorationMechanicId.PREPARATION_EFFECT,
        label="Przygotowanie",
        description="Deklaracja przygotowuje przyszłą próbę przez modyfikator, przewagę, redukcję kosztu albo odblokowanie opcji.",
        participants=None,
        aggregations=(),
    ),
}


def mechanic_tool(mechanic_id: ExplorationMechanicId | str) -> ExplorationMechanicTool:
    return MECHANIC_TOOLS[ExplorationMechanicId(str(mechanic_id))]


def infer_mechanic_id(
    *,
    participants: CheckParticipants | None,
    aggregation: CheckAggregation | None,
    option: ExplorationChallengeOption | None = None,
    action_flow_is_preparation: bool = False,
) -> ExplorationMechanicId:
    if action_flow_is_preparation:
        return ExplorationMechanicId.PREPARATION_EFFECT
    if option is not None:
        if option.improvised_tool is not None:
            return ExplorationMechanicId.IMPROVISED_TOOL_CHECK
        if option.requires_spell_ids or any(bonus.source_type == "spell" for bonus in option.bonuses):
            return ExplorationMechanicId.USE_SPELL_CHECK
        if option.requires_item_ids or any(bonus.source_type == "item" for bonus in option.bonuses):
            return ExplorationMechanicId.USE_ITEM_CHECK
    if participants == CheckParticipants.LEAD_WITH_HELP:
        return ExplorationMechanicId.LEAD_WITH_HELP_CHECK
    if participants in {CheckParticipants.WHOLE_PARTY, CheckParticipants.SELECTED_ACTORS}:
        return ExplorationMechanicId.GROUP_CHECK
    return ExplorationMechanicId.SINGLE_ACTOR_CHECK


def mechanic_payload_for_option(option: ExplorationChallengeOption) -> dict[str, object]:
    participants = option.check_participants or CheckParticipants.SINGLE_ACTOR
    aggregation = option.check_aggregation or CheckAggregation.LEAD_RESULT
    mechanic_id = (
        ExplorationMechanicId(option.mechanic_id)
        if option.mechanic_id is not None
        else infer_mechanic_id(participants=participants, aggregation=aggregation, option=option)
    )
    payload = mechanic_tool(mechanic_id).as_payload()
    payload["selected_by"] = "option"
    return payload


def validate_mechanic_selection(
    mechanic_id: ExplorationMechanicId,
    *,
    participants: CheckParticipants | None,
    aggregation: CheckAggregation | None,
) -> None:
    tool = mechanic_tool(mechanic_id)
    allowed_participants = (tool.participants,) if tool.participants is not None else ()
    if mechanic_id == ExplorationMechanicId.GROUP_CHECK:
        allowed_participants = (CheckParticipants.WHOLE_PARTY, CheckParticipants.SELECTED_ACTORS)
    if allowed_participants and participants is not None and participants not in allowed_participants:
        raise ValueError(f"Mechanika {mechanic_id.value} nie pasuje do uczestników {participants.value}.")
    if aggregation is not None and tool.aggregations and aggregation not in tool.aggregations:
        raise ValueError(f"Mechanika {mechanic_id.value} nie obsługuje agregacji {aggregation.value}.")


__all__ = [
    "ExplorationMechanicId",
    "ExplorationMechanicTool",
    "MECHANIC_TOOLS",
    "infer_mechanic_id",
    "mechanic_payload_for_option",
    "mechanic_tool",
    "validate_mechanic_selection",
]
