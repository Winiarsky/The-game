from typing import Optional

from GameObjects.base import GameObjectMeta
from GameObjects.NPC.base_npc import BaseNPC
from GameObjects.interactions_mixin import TradeItem


class ArmorerNPC(BaseNPC):
    def __init__(
        self,
        *,
        name: str = "Płatnerz",
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
                "text": "Sprzedaje zbroje i tarcze. Sprawdz biegłość i wymagania STR.",
                "options": [{"id": "leave", "label": "Wroc pozniej."}],
            }
        }


META = GameObjectMeta(
    object_id="armorer_npc",
    label="Płatnerz",
    color="#5a6a7a",
    category="Interactables",
    placement="cell",
    description="NPC handlowy: pancerze i tarcze.",
    logic_cls=ArmorerNPC,
    default_config={
        "name": "Płatnerz",
        "blocks_movement": True,
        "allow_same_cell_interact": True,
        "require_same_cell_interact": False,
        "dialog_path": "default_npc_dialog.json",
        "attitude": 0,
        "inventory": [
            {"item_id": "padded_armor", "name": "Pancerz pikowany", "price": 20, "kind": "armor", "stock": -1},
            {"item_id": "leather_armor", "name": "Zbroja skorzana", "price": 200, "kind": "armor", "stock": -1},
            {"item_id": "studded_leather", "name": "Zbroja nabijana", "price": 300, "kind": "armor", "stock": -1},
            {"item_id": "chain_shirt", "name": "Kolczuga lekka", "price": 500, "kind": "armor", "stock": -1},
            {"item_id": "hide_armor", "name": "Zbroja ze skor", "price": 200, "kind": "armor", "stock": -1},
            {"item_id": "scale_mail", "name": "Zbroja luska", "price": 400, "kind": "armor", "stock": -1},
            {"item_id": "chain_mail", "name": "Kolczuga", "price": 600, "kind": "armor", "stock": -1, "min_tier": "adept"},
            {"item_id": "breastplate", "name": "Napierśnik", "price": 800, "kind": "armor", "stock": -1, "min_tier": "adept"},
            {"item_id": "splint_mail", "name": "Pancerz lamelkowy", "price": 1300, "kind": "armor", "stock": -1, "min_tier": "adept"},
            {"item_id": "half_plate", "name": "Polpancerz", "price": 1800, "kind": "armor", "stock": -1, "min_tier": "master"},
            {"item_id": "full_plate", "name": "Pelna plyta", "price": 3000, "kind": "armor", "stock": -1, "min_tier": "master"},
            {"item_id": "buckler", "name": "Puklerz", "price": 100, "kind": "shield", "stock": -1},
            {"item_id": "wooden_shield", "name": "Tarcza drewniana", "price": 100, "kind": "shield", "stock": -1},
            {"item_id": "steel_shield", "name": "Tarcza stalowa", "price": 200, "kind": "shield", "stock": -1},
            {"item_id": "tower_shield", "name": "Tarcza wiezowa", "price": 1000, "kind": "shield", "stock": -1, "min_tier": "adept"},
        ],
        "trade_tier": "novice",
        "base_price_modifier": 1.0,
        "pickpocket_dc": 16,
        "pickpocket_loot": ["kilka monet"],
    },
)
