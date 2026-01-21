import logging
from typing import Optional, Callable, Iterable

from GameObjects.base import GameObjectMeta
from interactable import Interaction, Interactable
from interactions.common import (
    SocialMixin,
    TradeMixin,
    TradeItem,
    PickpocketMixin,
    prompt_for_roll,
    resolve_skill_check,
    attitude_label,
)

logger = logging.getLogger(__name__)


class BaseNPC(SocialMixin, TradeMixin, PickpocketMixin, Interactable):
    """Bazowy NPC z dialogiem, handlem i próbą kradzieży."""

    meta: Optional[GameObjectMeta] = None  # do ustawiania w klasach pochodnych

    def __init__(
        self,
        *,
        name: str = "NPC",
        dialog: Optional[dict | str] = None,
        allow_same_cell_interact: bool = True,
        require_same_cell_interact: bool = False,
        blocks_movement: bool = True,
        attitude: int = 0,
        inventory: Optional[list[TradeItem]] = None,
        base_price_modifier: float = 1.0,
        pickpocket_dc: int = 16,
        pickpocket_loot: Optional[list[str]] = None,
        enable_talk: bool = True,
        enable_trade: bool = True,
        enable_pickpocket: bool = True,
        on_pickpocket_fail: Optional[Callable[[object, object], Optional[str]]] = None,
        on_trade: Optional[Callable[[object, object], Optional[str]]] = None,
    ):
        Interactable.__init__(
            self,
            position=None,
            blocks_movement=blocks_movement,
            allow_same_cell_interact=allow_same_cell_interact,
            require_same_cell_interact=require_same_cell_interact,
        )

        self.attitude = attitude
        raw_inventory = inventory or []
        self.inventory = [
            item if isinstance(item, TradeItem) else TradeItem(**item) for item in raw_inventory
        ]
        self.base_price_modifier = base_price_modifier
        self.pickpocket_dc = pickpocket_dc
        self.pickpocket_loot = pickpocket_loot or ["kilka monet"]
        self._dialog_used: set[str] = set()
        self.enable_talk = enable_talk
        self.enable_trade = enable_trade
        self.enable_pickpocket = enable_pickpocket
        self._on_pickpocket_fail = on_pickpocket_fail
        self._on_trade = on_trade

        self.name = name
        self.dialog = self._normalize_dialog(dialog) or self._default_dialog()
        self.register_default_actions()

    # --- Dialog ---
    def _normalize_dialog(self, dialog: Optional[dict | str]) -> Optional[dict]:
        if dialog is None:
            return None
        if isinstance(dialog, dict):
            return dialog
        if isinstance(dialog, str):
            return {"start": {"text": dialog, "options": []}}
        return None

    def _default_dialog(self) -> dict:
        """Minimalny dialog, podmieniany w klasach pochodnych."""
        return {"start": {"text": f"{self.name} nie ma nic do powiedzenia.", "options": []}}

    def _run_dialog(self) -> str:
        """Przykładowa implementacja – klasy potomne mogą ją rozszerzyć."""
        node = self.dialog.get("start", {})
        return node.get("text", "...")

    def action_talk(self, _actor, _game, _payload=None) -> str:
        return self._run_dialog()

    # --- Handel ---
    def action_trade(self, _actor, _game, _payload=None) -> str:
        if not self.inventory:
            return "Nie mam nic na sprzedaż."
        mult = self.price_multiplier(self.attitude)
        lines = [f"Oferta ({attitude_label(self.attitude)}, mnożnik {mult:.2f}):"]
        for item in self.inventory:
            price = int(item.price * mult)
            lines.append(f"- {item.name}: {price} szt. złota")
        msg = "\n".join(lines)
        if callable(self._on_trade):
            extra = self._on_trade(self, _actor)
            if extra:
                msg = f"{msg}\n{extra}"
        return msg

    # --- Kradzież ---
    def action_pickpocket(self, actor, _game, _payload=None) -> str:
        statuses = set(getattr(actor, "statuses", []))
        if "stealth" not in statuses:
            return "Musisz być w ukryciu, aby spróbować podkraść."
        roll = prompt_for_roll("Rzut na Thievery (podkradanie): ")
        bonus = getattr(actor, "stealth_bonus", 0)
        if bonus:
            logger.info("Premia za ukrycie: +%s do testu.", bonus)
            roll += bonus
        outcome = resolve_skill_check(self.pickpocket_dc, roll)
        if outcome in ("success", "critical_success"):
            loot = (self.pickpocket_loot or ["drobne"])[0]
            return f"Udało się podkraść: {loot} (wynik: {outcome})."
        # porażka obniża nastawienie
        new_att, label = self.adjust_attitude(self.pickpocket_fail_attitude_delta)
        msg = (
            f"Przyłapany! Nastawienie spada do: {label} ({new_att}). "
            f"Wynik testu: {outcome}."
        )
        if callable(self._on_pickpocket_fail):
            extra = self._on_pickpocket_fail(self, actor)
            if extra:
                msg = f"{msg} {extra}"
        return msg

    def register_default_actions(self) -> None:
        """Tworzy standardowe akcje (dialog, handel, kradzież, wyjście) wg flag."""
        if self.enable_talk:
            self.register_action(
                Interaction(
                    id="talk",
                    label="Porozmawiaj",
                    description="Rozmowa.",
                    handler=type(self).action_talk,
                    end_interaction=False,
                )
            )
        if self.enable_trade:
            self.register_action(
                Interaction(
                    id="trade",
                    label="Handluj",
                    description="Zobacz, co oferuje.",
                    handler=type(self).action_trade,
                    end_interaction=False,
                )
            )
        if self.enable_pickpocket:
            self.register_action(
                Interaction(
                    id="pickpocket",
                    label="Podkradnij",
                    description="Próba kradzieży (Thievery).",
                    handler=type(self).action_pickpocket,
                    end_interaction=False,
                )
            )
        self.register_action(
            Interaction(
                id="leave",
                label="Zakończ",
                description="Zakończ rozmowę.",
                handler=lambda _self, _actor, _game, _payload=None: "Kończysz rozmowę.",
            )
        )
        for extra in self.extra_actions():
            self.register_action(extra)

    def extra_actions(self) -> Iterable[Interaction]:
        """Hook na dodatkowe akcje w klasach potomnych."""
        return []
