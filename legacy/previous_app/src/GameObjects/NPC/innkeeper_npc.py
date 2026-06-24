import logging
from typing import Optional

from GameObjects.base import GameObjectMeta
from GameObjects.NPC.base_npc import BaseNPC
from GameObjects.interactions_mixin import TradeItem

logger = logging.getLogger(__name__)


class InnkeeperNPC(BaseNPC):
    """Karczmarz z oferta uslug i podstawowych zakupow."""

    def __init__(
        self,
        *,
        name: str = "Karczmarz",
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
                "text": "Witaj w karczmie. Mamy nocleg, jedzenie, transport i kontakty do uslug.",
                "options": [{"id": "leave", "label": "Do zobaczenia."}],
            }
        }


META = GameObjectMeta(
    object_id="innkeeper_npc",
    label="Karczmarz",
    color="#7a4a2f",
    category="Interactables",
    placement="cell",
    description="NPC handlowy: uslugi z CRB (karczma, nocleg, transport, spellcasting).",
    logic_cls=InnkeeperNPC,
    default_config={
        "name": "Karczmarz",
        "blocks_movement": True,
        "allow_same_cell_interact": True,
        "require_same_cell_interact": False,
        "dialog_path": "default_npc_dialog.json",
        "attitude": 0,
        "inventory": [
            {"item_id": "mug_of_ale", "name": "Kufel piwa", "price": 1, "kind": "service", "stock": -1},
            {"item_id": "pot_of_coffee_or_tea", "name": "Dzbanek kawy/herbaty", "price": 2, "kind": "service", "stock": -1},
            {"item_id": "bottle_of_wine", "name": "Butelka wina", "price": 10, "kind": "service", "stock": -1},
            {"item_id": "bottle_of_fine_wine", "name": "Butelka dobrego wina", "price": 100, "kind": "service", "stock": -1},
            {"item_id": "meal_poor", "name": "Posilek ubogi", "price": 1, "kind": "service", "stock": -1},
            {"item_id": "meal_square", "name": "Posilek syty", "price": 3, "kind": "service", "stock": -1},
            {"item_id": "meal_fine_dining", "name": "Posilek wykwintny", "price": 100, "kind": "service", "stock": -1},
            {"item_id": "lodging_floor_space_day", "name": "Nocleg: podloga (1 dzien)", "price": 3, "kind": "service", "stock": -1},
            {"item_id": "lodging_bed_day", "name": "Nocleg: lozko (1 dzien)", "price": 10, "kind": "service", "stock": -1},
            {"item_id": "lodging_private_room_day", "name": "Nocleg: pokoj prywatny (1 dzien)", "price": 80, "kind": "service", "stock": -1},
            {"item_id": "lodging_extravagant_suite_day", "name": "Nocleg: apartament (1 dzien)", "price": 1000, "kind": "service", "stock": -1},
            {"item_id": "stabling_day", "name": "Stajnia (1 dzien)", "price": 2, "kind": "service", "stock": -1},
            {"item_id": "transport_caravan_5_miles", "name": "Transport: karawana (5 mil)", "price": 3, "kind": "service", "stock": -1},
            {"item_id": "transport_carriage_5_miles", "name": "Transport: powoz (5 mil)", "price": 20, "kind": "service", "stock": -1},
            {"item_id": "transport_ferry_or_riverboat_5_miles", "name": "Transport: prom/lodz (5 mil)", "price": 4, "kind": "service", "stock": -1},
            {"item_id": "transport_sailing_ship_5_miles", "name": "Transport: statek (5 mil)", "price": 6, "kind": "service", "stock": -1},
            {"item_id": "hireling_unskilled_day", "name": "Najemnik niewykwalifikowany (1 dzien)", "price": 10, "kind": "service", "stock": -1},
            {"item_id": "hireling_skilled_day", "name": "Najemnik wykwalifikowany (1 dzien)", "price": 50, "kind": "service", "stock": -1},
            {"item_id": "spellcasting_service_cantrip", "name": "Usluga czaru cantrip", "price": 100, "kind": "service", "stock": 1},
            {"item_id": "spellcasting_service_rank_1", "name": "Usluga czaru 1. rangi", "price": 300, "kind": "service", "stock": 1},
            {"item_id": "cost_of_living_subsistence_week", "name": "Koszt zycia skromny (tydzien)", "price": 40, "kind": "service", "stock": -1},
            {"item_id": "cost_of_living_comfortable_week", "name": "Koszt zycia wygodny (tydzien)", "price": 100, "kind": "service", "stock": -1},
        ],
        "trade_tier": "novice",
        "spell_service_max_rank": 1,
        "spell_service_allow_cantrips": True,
        "base_price_modifier": 1.0,
        "pickpocket_dc": 16,
        "pickpocket_loot": ["kilka monet"],
    },
)
