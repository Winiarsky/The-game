"""Pure projection of legal physical cards into subtle player reminders."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable, Mapping

from dnd_board_game.physical_cards.action_catalog import (
    CARD_ACTION_CATALOG,
    CURATED_CARD_OWNERS,
    CardPhase,
    CardTriggerWindow,
)


@dataclass(frozen=True, slots=True)
class PhysicalCardReminder:
    source_id: str
    label: str
    owner_actor_id: str
    owner_actor_name: str
    trigger_window: CardTriggerWindow

    def as_payload(self) -> dict[str, str]:
        return {
            "source_id": self.source_id,
            "label": self.label,
            "owner_actor_id": self.owner_actor_id,
            "owner_actor_name": self.owner_actor_name,
            "trigger_window": self.trigger_window.value,
        }


def action_selection_card_reminders(
    *,
    owner_actor_id: str,
    owner_actor_name: str,
    available_action_ids: Iterable[str],
    labels_by_action_id: Mapping[str, str] | None = None,
) -> tuple[PhysicalCardReminder, ...]:
    """Return owned combat cards backed by an action legal in this turn state."""

    available = frozenset(available_action_ids)
    labels = labels_by_action_id or {}
    reminders: list[PhysicalCardReminder] = []
    for source_id, definition in CARD_ACTION_CATALOG.items():
        if definition.phase not in {CardPhase.COMBAT, CardPhase.BOTH}:
            continue
        if CardTriggerWindow.ACTION_SELECTION not in definition.trigger_windows:
            continue
        declared_owners = CURATED_CARD_OWNERS.get(source_id, ())
        if declared_owners and owner_actor_id not in declared_owners:
            continue
        if definition.action_id not in available and source_id not in available:
            continue
        reminders.append(
            PhysicalCardReminder(
                source_id=source_id,
                label=(
                    labels.get(source_id)
                    or labels.get(definition.action_id)
                    or source_id.replace("_", " ").title()
                ),
                owner_actor_id=owner_actor_id,
                owner_actor_name=owner_actor_name,
                trigger_window=CardTriggerWindow.ACTION_SELECTION,
            )
        )
    return tuple(reminders)


def reaction_card_reminder(
    *,
    source_id: str | None,
    owner_actor_id: str,
    owner_actor_name: str,
    trigger_event: str,
    label: str = "",
) -> PhysicalCardReminder | None:
    """Project the currently legal ordered reaction, if it has a physical card."""

    if not source_id:
        return None
    definition = CARD_ACTION_CATALOG.get(source_id)
    if definition is None or definition.phase not in {CardPhase.COMBAT, CardPhase.BOTH}:
        return None
    declared_owners = CURATED_CARD_OWNERS.get(source_id, ())
    if declared_owners and owner_actor_id not in declared_owners:
        return None
    try:
        trigger = CardTriggerWindow(trigger_event)
    except ValueError:
        return None
    if trigger not in definition.trigger_windows:
        return None
    return PhysicalCardReminder(
        source_id=source_id,
        label=label or source_id.replace("_", " ").title(),
        owner_actor_id=owner_actor_id,
        owner_actor_name=owner_actor_name,
        trigger_window=trigger,
    )


__all__ = [
    "PhysicalCardReminder",
    "action_selection_card_reminders",
    "reaction_card_reminder",
]
