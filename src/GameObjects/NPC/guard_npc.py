import logging
from typing import Optional

from GameObjects.base import GameObjectMeta
from GameObjects.NPC.base_npc import BaseNPC
from GameObjects.interactions_mixin import WatchfulMixin, TradeItem, Interaction
from GameObjects.events.base import EventContext
from GameObjects.events.registry import dispatch_event

logger = logging.getLogger(__name__)


class GuardNPC(BaseNPC, WatchfulMixin):
    """Prosty strażnik z czujnością pokojową (WatchfulMixin)."""

    def __init__(
        self,
        *,
        name: str = "Strażnik",
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
        watch_disturbed: int = 0,
        watch_disabled: bool = False,
        perception_bonus: int = 4,
        enable_diplomacy: bool = True,
        **kwargs,
    ):
        # ustaw zanim BaseNPC wywoła extra_actions
        self.enable_diplomacy = enable_diplomacy
        self.diplomacy_blocked = False
        self.diplomacy_letter_given = False

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

    # --- Diplomacy dla strażnika ---
    def _diplomacy_dc(self) -> int:
        base_dc = 16
        return base_dc - 2 * self.attitude

    def action_diplomacy_guard(self, actor, game, _payload=None) -> str:
        if self.diplomacy_blocked:
            return "Strażnik nie chce już słuchać twoich argumentów."

        tags = ["diplomacy", "convince", "noble"]
        ctx = EventContext(game=game, actor=actor, tags=tags, metadata={"dc": self._diplomacy_dc(), "target": self})
        result = dispatch_event("diplomacy_check", ctx)

        outcome = result.data.get("outcome") if result.data else None
        if outcome == "critical_success":
            self.diplomacy_letter_given = True
            att, label = self.adjust_attitude(1)
            return f"Otrzymujesz pismo od strażnika. Nastawienie: {label} ({att})."
        if outcome == "success":
            self.diplomacy_letter_given = True
            return "Otrzymujesz pismo od strażnika."
        if outcome == "failure":
            return "Strażnik nie daje się przekonać."
        if outcome == "critical_failure":
            self.diplomacy_blocked = True
            return "Zdenerwowałeś strażnika. Nie będzie dalszych rozmów."

        return result.message or "Nie udało się przeprowadzić testu."

    def extra_actions(self):
        actions = super().extra_actions()
        if self.enable_diplomacy:
            actions.append(
                Interaction(
                    id="diplomacy",
                    label="Perswazja (Diplomacy)",
                    description="Spróbuj przekonać strażnika.",
                    handler=type(self).action_diplomacy_guard,
                    end_interaction=False,
                    tags=["diplomacy", "convince"],
                )
            )
        return actions


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
        "dialog_path": "guard_dialog.json",
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
