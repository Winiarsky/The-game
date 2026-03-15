from typing import Optional

from GameObjects.base import GameObjectMeta
from GameObjects.NPC.base_npc import BaseNPC
from GameObjects.interactions_mixin import TradeItem


class WeaponMerchantNPC(BaseNPC):
    def __init__(
        self,
        *,
        name: str = "Kupiec broni",
        dialog: Optional[dict] = None,
        dialog_path: Optional[str] = None,
        allow_same_cell_interact: bool = True,
        require_same_cell_interact: bool = False,
        blocks_movement: bool = True,
        attitude: int = 0,
        inventory: Optional[list[TradeItem]] = None,
        base_price_modifier: float = 1.0,
        pickpocket_dc: int = 16,
        pickpocket_loot: Optional[list[str]] = None,
        **kwargs,
    ):
        super().__init__(
            name=name,
            dialog=dialog,
            dialog_path=dialog_path,
            allow_same_cell_interact=allow_same_cell_interact,
            require_same_cell_interact=require_same_cell_interact,
            blocks_movement=blocks_movement,
            attitude=attitude,
            inventory=inventory,
            base_price_modifier=base_price_modifier,
            pickpocket_dc=pickpocket_dc,
            pickpocket_loot=pickpocket_loot,
            **kwargs,
        )

    def _default_dialog(self) -> dict:
        return {
            "start": {
                "text": "Sprzedaje bronie i amunicje. Dobierz bron pod biegłość i styl walki.",
                "options": [{"id": "leave", "label": "Wroc pozniej."}],
            }
        }


META = GameObjectMeta(
    object_id="weapon_merchant_npc",
    label="Kupiec Broni",
    color="#8f5a2a",
    category="Interactables",
    placement="cell",
    description="NPC handlowy: bronie i amunicja.",
    logic_cls=WeaponMerchantNPC,
    default_config={
        "name": "Kupiec Broni",
        "blocks_movement": True,
        "allow_same_cell_interact": True,
        "require_same_cell_interact": False,
        "dialog_path": "default_npc_dialog.json",
        "attitude": 0,
        "inventory": [
            {"item_id": "dagger", "name": "Sztylet", "price": 20, "kind": "weapon", "stock": -1},
            {"item_id": "shortsword", "name": "Krotki miecz", "price": 90, "kind": "weapon", "stock": -1},
            {"item_id": "longsword", "name": "Dlugi miecz", "price": 100, "kind": "weapon", "stock": -1},
            {"item_id": "rapier", "name": "Rapier", "price": 200, "kind": "weapon", "stock": -1, "min_tier": "adept"},
            {"item_id": "warhammer", "name": "Mlot bojowy", "price": 100, "kind": "weapon", "stock": -1},
            {"item_id": "spear", "name": "Wlocznia", "price": 10, "kind": "weapon", "stock": -1},
            {"item_id": "shortbow", "name": "Krotki luk", "price": 300, "kind": "weapon", "stock": -1},
            {"item_id": "longbow", "name": "Dlugi luk", "price": 600, "kind": "weapon", "stock": -1, "min_tier": "adept"},
            {"item_id": "crossbow", "name": "Kusza", "price": 300, "kind": "weapon", "stock": -1},
            {"item_id": "arrows", "name": "Strzaly (10)", "price": 10, "kind": "equipment", "stock": -1},
            {"item_id": "bolts", "name": "Belty (10)", "price": 10, "kind": "equipment", "stock": -1},
            {"item_id": "sling_bullets", "name": "Pociski do procy (10)", "price": 1, "kind": "equipment", "stock": -1},
        ],
        "trade_tier": "novice",
        "base_price_modifier": 1.0,
        "pickpocket_dc": 16,
        "pickpocket_loot": ["kilka monet"],
    },
)
