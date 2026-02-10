import json
import logging
from pathlib import Path
from typing import Optional, Callable, Iterable

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin import (
    SocialMixin,
    TradeMixin,
    TradeItem,
    PickpocketMixin,
    prompt_for_roll,
    resolve_skill_check,
    attitude_label,
)
from GameObjects.events.base import EventContext
from GameObjects.events.registry import dispatch_event
from skills import Skill

logger = logging.getLogger(__name__)

DIALOGS_DIR = Path(__file__).resolve().parents[1] / "dialogs"


class BaseNPC(SocialMixin, TradeMixin, PickpocketMixin, InteractableMixin):
    """Bazowy NPC z dialogiem, handlem i próbą kradzieży."""

    meta: Optional[GameObjectMeta] = None  # do ustawiania w klasach pochodnych

    def __init__(
        self,
        *,
        name: str = "NPC",
        dialog: Optional[dict | str] = None,
        dialog_path: Optional[str] = None,
        allow_same_cell_interact: bool = True,
        require_same_cell_interact: bool = False,
        blocks_movement: bool = True,
        attitude: int = 0,
        inventory: Optional[list[TradeItem]] = None,
        base_price_modifier: float = 1.0,
        pickpocket_dc: int = 16,
        pickpocket_loot: Optional[list[str]] = None,
        enable_diplomacy: bool = True,
        is_noble: bool = False,
        enable_talk: bool = True,
        enable_trade: bool = True,
        enable_pickpocket: bool = True,
        on_pickpocket_fail: Optional[Callable[[object, object], Optional[str]]] = None,
        on_trade: Optional[Callable[[object, object], Optional[str]]] = None,
    ):
        InteractableMixin.__init__(
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
        self.enable_diplomacy = enable_diplomacy
        self.is_noble = is_noble
        self.enable_talk = enable_talk
        self.enable_trade = enable_trade
        self.enable_pickpocket = enable_pickpocket
        self._on_pickpocket_fail = on_pickpocket_fail
        self._on_trade = on_trade

        self.name = name
        self.dialog = self._load_dialog(dialog, dialog_path) or self._default_dialog()
        self.register_default_actions()

    def _load_dialog(self, dialog: Optional[dict | str], dialog_path: Optional[str]) -> Optional[dict]:
        """Normalizuj dialog, próbując wczytać z pliku jeśli podano dialog_path."""
        normalized = self._normalize_dialog(dialog)
        if normalized:
            return normalized
        if dialog_path:
            loaded = self._load_dialog_from_path(dialog_path)
            if loaded:
                return loaded
        # fallback: bazowy plik domyślny, jeśli istnieje
        fallback = self._load_dialog_from_path("default_npc_dialog.json")
        return fallback

    def _load_dialog_from_path(self, dialog_path: str) -> Optional[dict]:
        path = Path(dialog_path)
        if not path.is_absolute():
            path = DIALOGS_DIR / path
        try:
            if not path.exists():
                return None
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception as exc:
            logger.warning("Nie udało się wczytać dialogu z %s: %s", path, exc)
        return None

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
        has_status = getattr(actor, "has_status", None)
        is_stealthed = has_status(Skill.STEALTH.value) if callable(has_status) else Skill.STEALTH.value in getattr(actor, "statuses", [])
        if not is_stealthed:
            return "Musisz być w ukryciu, aby spróbować podkraść."
        result = dispatch_event(
            "skill_check",
            EventContext(
                game=None,
                actor=actor,
                tags=[Skill.THIEVERY.value, "pickpocket"],
                metadata={
                    "dc": self.pickpocket_dc,
                    "skill_id": Skill.THIEVERY.value,
                    "skill_label": "Thievery",
                    "apply_modifiers": False,
                },
            ),
        )
        outcome = result.data.get("outcome") if result.data else resolve_skill_check(self.pickpocket_dc, 0)
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

    # --- Diplomacy check (tagowy SkillCheckEvent) ---
    def _diplomacy_dc(self) -> int:
        """DC zależne od nastawienia (-2..2): wrogi trudniej, przyjacielski łatwiej."""
        base_dc = 15
        # niższe DC dla pozytywnego nastawienia, wyższe dla negatywnego
        return base_dc - 2 * self.attitude

    def action_diplomacy(self, actor, game, _payload=None) -> str:
        dc = self._diplomacy_dc()
        tags = [Skill.DIPLOMACY.value, "convince"]
        if self.is_noble:
            tags.append("noble")

        ctx = EventContext(
            game=game,
            actor=actor,
            tags=tags,
            metadata={"dc": dc, "skill_id": Skill.DIPLOMACY.value, "skill_label": "Diplomacy"},
        )
        result = dispatch_event("skill_check", ctx)

        outcome = result.data.get("outcome") if result.data else None
        if outcome in ("success", "critical_success"):
            delta = 2 if outcome == "critical_success" else 1
            new_att, label = self.adjust_attitude(delta)
            return (
                f"Udana perswazja ({outcome}). Nastawienie rośnie do: {label} ({new_att}). "
                f"{result.message or ''}"
            ).strip()

        if outcome in ("failure", "critical_failure"):
            delta = -2 if outcome == "critical_failure" else -1
            new_att, label = self.adjust_attitude(delta)
            return (
                f"Nie udało się przekonać ({outcome}). Nastawienie spada do: {label} ({new_att}). "
                f"{result.message or ''}"
            ).strip()

        return result.message or "Test dyplomacji nie został przeprowadzony."

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
        if self.enable_diplomacy:
            self.register_action(
                Interaction(
                    id="diplomacy",
                    label="Przekonaj (Diplomacy)",
                    description="Próba perswazji zależna od nastawienia.",
                    handler=type(self).action_diplomacy,
                    end_interaction=False,
                    tags=["diplomacy", "convince"],
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
