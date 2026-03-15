from typing import Optional

from GameObjects.base import GameObjectMeta
from GameObjects.NPC.base_npc import BaseNPC
from GameObjects.interactions_mixin import TradeItem


class MageNPC(BaseNPC):
    def __init__(
        self,
        *,
        name: str = "Mag",
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
                "text": "Swiadczy uslugi magiczne: buffy i castowanie na zlecenie.",
                "options": [{"id": "leave", "label": "Wroc pozniej."}],
            }
        }


META = GameObjectMeta(
    object_id="mage_npc",
    label="Mag",
    color="#4e5fa8",
    category="Interactables",
    placement="cell",
    description="NPC handlowy: uslugi magiczne i zwoje.",
    logic_cls=MageNPC,
    default_config={
        "name": "Mag",
        "blocks_movement": True,
        "allow_same_cell_interact": True,
        "require_same_cell_interact": False,
        "dialog_path": "default_npc_dialog.json",
        "attitude": 0,
        "inventory": [
            {"item_id": "spellcasting_service_cantrip", "name": "Usluga czaru cantrip", "price": 100, "kind": "service", "stock": 3},
            {"item_id": "spellcasting_service_rank_1", "name": "Usluga czaru 1. rangi", "price": 300, "kind": "service", "stock": 2},
            {"item_id": "mage_service_mage_armor", "name": "Usluga: Mage Armor", "price": 300, "kind": "service", "stock": -1},
            {"item_id": "mage_service_magic_weapon", "name": "Usluga: Magic Weapon", "price": 300, "kind": "service", "stock": -1},
            {"item_id": "mage_service_longstrider", "name": "Usluga: Longstrider", "price": 300, "kind": "service", "stock": -1},
            {"item_id": "scroll_common_rank1", "name": "Zwoj czaru 1. rangi", "price": 400, "kind": "equipment", "stock": 4},
            {"item_id": "potency_crystal", "name": "Krysztal potencji", "price": 400, "kind": "equipment", "stock": 2},
        ],
        "trade_tier": "novice",
        "spell_service_traditions": ["arcana", "primal"],
        "spell_service_max_rank": 0,
        "spell_service_allow_cantrips": True,
        "spell_service_catalog_by_tier": {
            "novice": [
                "detect_magic",
                "shield_cantrip",
                "acid_splash",
                "magic_missile",
                "mage_armor",
                "magic_weapon",
                "grease",
                "longstrider",
                "shocking_grasp",
            ],
            "adept": [
                "burning_hands",
                "hydraulic_push",
                "feather_fall",
                "jump",
                "ant_haul",
                "fleet_step",
            ],
            "master": [
                "summon_construct",
                "summon_animal",
                "pest_form",
                "pass_without_trace",
            ],
        },
        "base_price_modifier": 1.0,
        "pickpocket_dc": 16,
        "pickpocket_loot": ["kilka monet"],
    },
)
