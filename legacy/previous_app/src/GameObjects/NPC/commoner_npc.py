from __future__ import annotations

from typing import Optional

from GameObjects.base import GameObjectMeta
from GameObjects.NPC.base_npc import BaseNPC


class CommonerNPC(BaseNPC):
    """Scenario villager/commoner driven by BaseNPC dialog data."""

    def __init__(
        self,
        *,
        name: str = "Mieszkaniec",
        npc_id: str | None = None,
        dialog: Optional[dict | str] = None,
        dialog_path: Optional[str] = None,
        allow_same_cell_interact: bool = True,
        require_same_cell_interact: bool = False,
        blocks_movement: bool = True,
        attitude: int = 0,
        enable_diplomacy: bool = False,
        enable_trade: bool = False,
        enable_pickpocket: bool = False,
        **kwargs,
    ):
        super().__init__(
            name=name,
            npc_id=npc_id,
            dialog=dialog,
            dialog_path=dialog_path,
            allow_same_cell_interact=allow_same_cell_interact,
            require_same_cell_interact=require_same_cell_interact,
            blocks_movement=blocks_movement,
            attitude=attitude,
            enable_diplomacy=enable_diplomacy,
            enable_trade=enable_trade,
            enable_pickpocket=enable_pickpocket,
            **kwargs,
        )

    def _default_dialog(self) -> dict:
        return {
            "start": {
                "text": f"{self.name} patrzy nerwowo na rynek i czeka, az ktos inny odezwie sie pierwszy.",
                "options": [{"id": "leave", "label": "Odejdz."}],
            }
        }


META = GameObjectMeta(
    object_id="commoner_npc",
    label="Mieszkaniec",
    color="#d97706",
    category="Interactables",
    placement="cell",
    description="Zwykly NPC scenariuszowy oparty o drzewo dialogowe.",
    logic_cls=CommonerNPC,
    default_config={
        "name": "Mieszkaniec",
        "blocks_movement": True,
        "allow_same_cell_interact": True,
        "require_same_cell_interact": False,
        "attitude": 0,
        "enable_diplomacy": False,
        "enable_trade": False,
        "enable_pickpocket": False,
    },
)


__all__ = ["CommonerNPC", "META"]
