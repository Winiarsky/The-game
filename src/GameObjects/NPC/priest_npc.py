from typing import Optional

from GameObjects.base import GameObjectMeta
from GameObjects.NPC.base_npc import BaseNPC
from GameObjects.interactions_mixin import TradeItem


class PriestNPC(BaseNPC):
    def __init__(
        self,
        *,
        name: str = "Kaplan",
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
                "text": "Swiadczy boskie uslugi: leczenie, blogoslawienstwo i oczyszczanie strachu.",
                "options": [{"id": "leave", "label": "Wroc pozniej."}],
            }
        }


META = GameObjectMeta(
    object_id="priest_npc",
    label="Kaplan",
    color="#d4c26a",
    category="Interactables",
    placement="cell",
    description="NPC handlowy: leczenie i buffy boskie.",
    logic_cls=PriestNPC,
    default_config={
        "name": "Kaplan",
        "blocks_movement": True,
        "allow_same_cell_interact": True,
        "require_same_cell_interact": False,
        "dialog_path": "default_npc_dialog.json",
        "attitude": 0,
        "inventory": [
            {"item_id": "spellcasting_service_cantrip", "name": "Usluga czaru cantrip", "price": 100, "kind": "service", "stock": 3},
            {"item_id": "spellcasting_service_rank_1", "name": "Usluga czaru 1. rangi", "price": 300, "kind": "service", "stock": 2},
            {"item_id": "priest_service_heal_minor", "name": "Usluga: Leczenie mniejsze", "price": 300, "kind": "service", "stock": -1},
            {"item_id": "priest_service_heal_major", "name": "Usluga: Leczenie wieksze", "price": 700, "kind": "service", "stock": -1},
            {"item_id": "priest_service_bless", "name": "Usluga: Bless", "price": 300, "kind": "service", "stock": -1},
            {"item_id": "priest_service_remove_fear", "name": "Usluga: Usuniecie strachu", "price": 300, "kind": "service", "stock": -1},
            {"item_id": "holy_water", "name": "Woda swiecona", "price": 300, "kind": "equipment", "stock": 4},
            {"item_id": "minor_healing_potion", "name": "Mikstura leczenia (slaba)", "price": 400, "kind": "equipment", "stock": 3},
        ],
        "trade_tier": "novice",
        "spell_service_traditions": ["divine", "occult"],
        "spell_service_max_rank": 0,
        "spell_service_allow_cantrips": True,
        "spell_service_catalog_by_tier": {
            "novice": [
                "guidance",
                "light",
                "daze",
                "heal",
                "harm",
                "fear",
                "command",
                "bless",
            ],
            "adept": [
                "soothe",
                "true_strike",
                "air_bubble",
                "detect_poison",
                "magic_fang",
                "pass_without_trace",
                "purify_food_and_drink",
            ],
            "master": [
                "summon_animal",
                "summon_plant_or_fungus",
                "goblin_pox",
            ],
        },
        "base_price_modifier": 1.0,
        "pickpocket_dc": 16,
        "pickpocket_loot": ["kilka monet"],
    },
)
