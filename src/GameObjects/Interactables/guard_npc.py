import logging
from typing import Optional

from GameObjects.base import GameObjectMeta
from interactable import Interaction, Interactable
from interactions.common import WatchfulMixin
from interactions.common import (
    SocialMixin,
    TradeMixin,
    TradeItem,
    PickpocketMixin,
    prompt_for_roll,
    resolve_skill_check,
)

logger = logging.getLogger(__name__)


class GuardNPC(WatchfulMixin, SocialMixin, TradeMixin, PickpocketMixin, Interactable):
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
        # Inicjalizacja Interactable (pozycja zostanie ustawiona przy dodaniu na planszę).
        Interactable.__init__(
            self,
            position=None,
            blocks_movement=blocks_movement,
            allow_same_cell_interact=allow_same_cell_interact,
            require_same_cell_interact=require_same_cell_interact,
        )

        # Inicjalizacja mixinów (brak dataclass init).
        self.watch_disturbed = watch_disturbed
        self.watch_disabled = watch_disabled
        self.perception_bonus = perception_bonus

        self.attitude = attitude
        SocialMixin.__init__(self)
        TradeMixin.__init__(self)
        PickpocketMixin.__init__(self)

        self.blocks_movement = blocks_movement
        self.allow_same_cell_interact = allow_same_cell_interact
        self.require_same_cell_interact = require_same_cell_interact

        raw_inventory = inventory or []
        self.inventory = [
            item if isinstance(item, TradeItem) else TradeItem(**item) for item in raw_inventory
        ]
        self.base_price_modifier = base_price_modifier
        self.pickpocket_dc = pickpocket_dc
        self.pickpocket_loot = pickpocket_loot or ["kilka monet"]
        self._dialog_used: set[str] = set()

        self.name = name
        self.dialog = dialog or self._default_dialog()
        self.register_default_actions()
        self.hidden = False
        self.revealed = False

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
        statuses = set(getattr(actor, "statuses", []))
        if "stealth" not in statuses:
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
