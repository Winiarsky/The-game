import logging
from typing import Optional

from GameObjects.base import GameObjectMeta
from interactable import Interaction
from GameObjects.Interactables.base_npc import BaseNPC
from interactions_mixin import WatchfulMixin, prompt_for_roll, resolve_skill_check, TradeItem

logger = logging.getLogger(__name__)


class GuardNPC(BaseNPC, WatchfulMixin):
    """Prosty strażnik z czujnością pokojową (WatchfulMixin)."""

    def __init__(
        self,
        *,
        name: str = "Strażnik",
        dialog: Optional[dict] = None,
        allow_same_cell_interact: bool = True,
        require_same_cell_interact: bool = False,
        blocks_movement: bool = True,
        attitude: int = 0,
        inventory: Optional[list[TradeItem]] = None,
        base_price_modifier: float = 1.0,
        pickpocket_dc: int = 16,
        pickpocket_loot: Optional[list[str]] = None,
        watch_disturbed: int = 0,
        watch_disabled: bool = False,
        perception_bonus: int = 4,
    ):
        super().__init__(
            name=name,
            dialog=dialog,
            allow_same_cell_interact=allow_same_cell_interact,
            require_same_cell_interact=require_same_cell_interact,
            blocks_movement=blocks_movement,
            attitude=attitude,
            inventory=inventory,
            base_price_modifier=base_price_modifier,
            pickpocket_dc=pickpocket_dc,
            pickpocket_loot=pickpocket_loot,
        )
        WatchfulMixin.__init__(
            self,
            watch_disturbed=watch_disturbed,
            watch_disabled=watch_disabled,
            perception_bonus=perception_bonus,
        )

    # --- Dialog jak w NPC ---
    def _default_dialog(self) -> dict:
        return {
            "start": {
                "text": "Strażnik obserwuje otoczenie.",
                "options": [{"id": "leave", "label": "Odejdź."}],
            }
        }

    def register_default_actions(self) -> None:
        self.register_action(
            Interaction(
                id="talk",
                label="Zagadaj",
                description="Krótka wymiana zdań.",
                handler=lambda _self, _actor, _game, _payload=None: "Strażnik kiwa głową.",
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="leave",
                label="Odejdź",
                description="Zakończ rozmowę.",
                handler=lambda _self, _actor, _game, _payload=None: "Kończysz rozmowę.",
            )
        )

    # --- Pickpocket jak w NPC ---
    def action_pickpocket(self, actor, _game, _payload=None) -> str:
        has_status = getattr(actor, "has_status", None)
        is_stealthed = has_status("stealth") if callable(has_status) else "stealth" in getattr(actor, "statuses", [])
        if not is_stealthed:
            return "Musisz być w ukryciu, aby spróbować podkraść."
        roll = prompt_for_roll("Rzut na Thievery (podkradanie): ")
        bonus = getattr(actor, "stealth_bonus", 0)
        roll += bonus
        outcome = resolve_skill_check(self.pickpocket_dc, roll)
        if outcome in ("success", "critical_success"):
            loot = (self.pickpocket_loot or ["drobne"])[0]
            return f"Udało się podkraść: {loot} (wynik: {outcome})."
        new_att, label = self.adjust_attitude(self.pickpocket_fail_attitude_delta)
        return (
            f"Przyłapany! Nastawienie spada do: {label} ({new_att}). "
            f"Wynik testu: {outcome}."
        )

    # --- Watchful hook ---
    def on_spot(self, hero, game) -> Optional[str]:
        return f"{self.name} zauważa ruch."


META = GameObjectMeta(
    object_id="guard_npc",
    label="Strażnik",
    color="#8b0000",
    category="Interactables",
    placement="cell",
    description="Strażnik z czujnością pokojową. watch_disturbed=0 blokuje stealth, >0 dodaje karę.",
    logic_cls=GuardNPC,
    default_config={
        "name": "Strażnik",
        "blocks_movement": True,
        "allow_same_cell_interact": True,
        "require_same_cell_interact": False,
        "attitude": 0,
        "inventory": [],
        "base_price_modifier": 1.0,
        "pickpocket_dc": 16,
        "pickpocket_loot": ["kilka monet"],
        "watch_disturbed": 0,
        "watch_disabled": False,
        "perception_bonus": 4,
    },
)
