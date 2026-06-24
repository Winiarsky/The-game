from typing import Optional

from GameObjects.base import GameObjectMeta
from GameObjects.NPC.base_npc import BaseNPC
from GameObjects.interactions_mixin import TradeItem


class AlchemistNPC(BaseNPC):
    def __init__(
        self,
        *,
        name: str = "Alchemik",
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
                "text": "Sprzedaje bomby, eliksiry i odczynniki. Sprawdz zastosowanie mechaniczne w opisie.",
                "options": [{"id": "leave", "label": "Wroc pozniej."}],
            }
        }


META = GameObjectMeta(
    object_id="alchemist_npc",
    label="Alchemik",
    color="#4f7f4f",
    category="Interactables",
    placement="cell",
    description="NPC handlowy: alchemia i powiazane consumables.",
    logic_cls=AlchemistNPC,
    default_config={
        "name": "Alchemik",
        "blocks_movement": True,
        "allow_same_cell_interact": True,
        "require_same_cell_interact": False,
        "dialog_path": "default_npc_dialog.json",
        "attitude": 0,
        "inventory": [
            {"item_id": "alchemical:acid_flask", "name": "Fiolka kwasu", "price": 300, "kind": "alchemical", "stock": 6},
            {"item_id": "alchemical:alchemists_fire", "name": "Ognista mikstura", "price": 300, "kind": "alchemical", "stock": 6},
            {"item_id": "alchemical:bottled_lightning", "name": "Butelkowana blyskawica", "price": 300, "kind": "alchemical", "stock": 6},
            {"item_id": "alchemical:frost_vial", "name": "Mrozna fiolka", "price": 300, "kind": "alchemical", "stock": 6},
            {"item_id": "alchemical:tanglefoot_bag", "name": "Worek lepikuli", "price": 300, "kind": "alchemical", "stock": 6},
            {"item_id": "alchemical:thunderstone", "name": "Kamien gromu", "price": 300, "kind": "alchemical", "stock": 6},
            {"item_id": "alchemical:antidote", "name": "Antidotum", "price": 300, "kind": "alchemical", "stock": 6},
            {"item_id": "alchemical:antiplague", "name": "Antyplaga", "price": 300, "kind": "alchemical", "stock": 6},
            {"item_id": "alchemical:elixir_of_life", "name": "Eliksir zycia", "price": 300, "kind": "alchemical", "stock": 6},
            {"item_id": "alchemical:smokestick", "name": "Dymna fiolka", "price": 300, "kind": "alchemical", "stock": 6},
            {"item_id": "holy_water", "name": "Woda swiecona", "price": 300, "kind": "equipment", "stock": 4},
            {"item_id": "unholy_water", "name": "Woda plugawa", "price": 300, "kind": "equipment", "stock": 2, "min_tier": "adept"},
            {"item_id": "minor_healing_potion", "name": "Mikstura leczenia (slaba)", "price": 400, "kind": "equipment", "stock": 4},
        ],
        "trade_tier": "novice",
        "base_price_modifier": 1.0,
        "pickpocket_dc": 16,
        "pickpocket_loot": ["kilka monet"],
    },
)
