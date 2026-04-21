from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import InteractableMixin


class EntryAnchor(InteractableMixin):
    """Logiczny marker wejścia na mapę używany przez sesję scenariusza."""

    def __init__(
        self,
        *,
        entry_anchor_id: str,
        label: str | None = None,
    ) -> None:
        InteractableMixin.__init__(
            self,
            position=None,
            allow_same_cell_interact=True,
            allow_hidden_interaction=False,
            blocks_movement=False,
        )
        self.entry_anchor_id = str(entry_anchor_id or "").strip()
        self.anchor_label = str(label or self.entry_anchor_id or "Entry anchor").strip()

    def can_interact(self, actor, game) -> bool:
        return False


META = GameObjectMeta(
    object_id="entry_anchor",
    label="Entry Anchor",
    color="#0ea5e9",
    category="Interactables",
    placement="cell",
    description="Logiczny punkt wejścia drużyny po przejściu między mapami.",
    logic_cls=EntryAnchor,
    default_config={
        "entry_anchor_id": "entry_default",
        "label": "",
    },
)
