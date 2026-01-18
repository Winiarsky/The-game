import logging
from typing import Optional

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


class NPC(SocialMixin, TradeMixin, PickpocketMixin, Interactable):
    """Podstawowy NPC z dialogiem, handlem i próbą kradzieży."""

    def __init__(
        self,
        *,
        name: str = "NPC",
        dialog: Optional[dict] = None,
        allow_same_cell_interact: bool = True,
        require_same_cell_interact: bool = False,
        blocks_movement: bool = True,
        attitude: int = 0,
        inventory: Optional[list[TradeItem]] = None,
        base_price_modifier: float = 1.0,
        pickpocket_dc: int = 16,
        pickpocket_loot: Optional[list[str]] = None,
    ):
        Interactable.__init__(
            self,
            position=None,
            blocks_movement=blocks_movement,
            allow_same_cell_interact=allow_same_cell_interact,
            require_same_cell_interact=require_same_cell_interact,
        )
        # mixiny
        self.attitude = attitude
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

    def register_default_actions(self) -> None:
        self.register_action(
            Interaction(
                id="talk",
                label="Porozmawiaj",
                description="Rozmowa z NPC.",
                handler=NPC.action_talk,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="trade",
                label="Handluj",
                description="Zobacz, co oferuje.",
                handler=NPC.action_trade,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="pickpocket",
                label="Podkradnij",
                description="Próba kradzieży (Thievery).",
                handler=NPC.action_pickpocket,
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

    # --- Dialog ---
    def _default_dialog(self) -> dict:
        """Prosty dialog przykładowy dla barmana."""
        return {
            "start": {
                "text": "Witaj w mojej karczmie. Czego szukasz?",
                "options": [
                    {"id": "rumors", "label": "Słyszałem plotki..."},
                    {"id": "compliment", "label": "Świetne piwo, stary! (pochwała)"},
                ],
            },
            "rumors": {
                "text": "Mówią, że w starych ruinach ktoś widział smoka. Uważaj na siebie.",
                "options": [
                    {"id": "thanks", "label": "Dzięki za info.", "attitude_delta": 1},
                    {"id": "start", "label": "Wracamy do rozmowy."},
                ],
            },
            "compliment": {
                "text": "Tanie pochwały? Nie każdy zna się na piwie. Chcesz zaimponować, pokaż kunszt. Rzuć na Charyzmę/Przekonywanie.",
                "options": [
                    {
                        "id": "compliment_check",
                        "label": "Spróbuj go przekonać",
                        "check": {
                            "skill": "Charyzma/Przekonywanie",
                            "dc": 17,
                            "on_success": "compliment_success",
                            "on_failure": "compliment_fail",
                            "attitude_delta_success": 1,
                            "attitude_delta_failure": -1,
                        },
                        "once": True,
                    },
                    {"id": "start", "label": "Nie, dzięki."},
                ],
            },
            "compliment_success": {
                "text": "No proszę, wiesz coś o piwie. Szanuję. Masz u mnie zniżkę.",
                "options": [
                    {"id": "start", "label": "Wracamy do rozmowy."}
                ],
            },
            "compliment_fail": {
                "text": "Ha! Nie masz pojęcia. Może kiedyś się nauczysz.",
                "options": [
                    {"id": "start", "label": "Wracamy do rozmowy."}
                ],
            },
            "thanks": {
                "text": "Nie ma sprawy. Pomagajcie sobie nawzajem, a świat będzie lepszy.",
                "options": [],
            },
        }

    def _run_dialog(self) -> str:
        """Prosta pętla dialogowa; zwraca ostatni komunikat."""
        node_id = "start"
        last_msg = ""
        while True:
            node = self.dialog.get(node_id)
            if not node:
                return "NPC milczy, coś jest nie tak z dialogiem."
            text = node.get("text", "")
            # ewentualna zmiana nastawienia na wejściu
            delta = node.get("attitude_delta")
            if delta:
                new_att, label = self.adjust_attitude(delta)
                logger.info(f"Nastawienie {self.name}: {label} ({new_att}).")
            options = [
                opt
                for opt in node.get("options", [])
                if not opt.get("once") or opt["id"] not in self._dialog_used
            ]
            print(text)
            if not options:
                return text
            for idx, opt in enumerate(options, start=1):
                print(f"{idx}. {opt.get('label', '...')}")
            choice_raw = input("Wybierz opcję (Enter aby wyjść): ").strip()
            if not choice_raw or not choice_raw.isdigit():
                return "Kończysz rozmowę."
            idx = int(choice_raw) - 1
            if idx < 0 or idx >= len(options):
                return "Kończysz rozmowę."
            chosen = options[idx]
            if chosen.get("once"):
                self._dialog_used.add(chosen["id"])
            if "check" in chosen:
                check = chosen["check"]
                roll = prompt_for_roll(
                    f"Rzut na {check.get('skill', 'test')} (DC {check.get('dc', 0)}): "
                )
                outcome = resolve_skill_check(check.get("dc", 0), roll)
                if outcome in ("success", "critical_success"):
                    if "attitude_delta_success" in check:
                        new_att, label = self.adjust_attitude(check["attitude_delta_success"])
                        logger.info(f"Nastawienie {self.name}: {label} ({new_att}).")
                    node_id = check.get("on_success") or node_id
                else:
                    if "attitude_delta_failure" in check:
                        new_att, label = self.adjust_attitude(check["attitude_delta_failure"])
                        logger.info(f"Nastawienie {self.name}: {label} ({new_att}).")
                    node_id = check.get("on_failure") or node_id
                continue
            if "attitude_delta" in chosen:
                new_att, label = self.adjust_attitude(chosen["attitude_delta"])
                logger.info(f"Nastawienie {self.name}: {label} ({new_att}).")
            last_msg = chosen.get("label", "")
            node_id = chosen.get("id")
            if not node_id:
                return text

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
        return "\n".join(lines)

    # --- Kradzież ---
    def action_pickpocket(self, actor, _game, _payload=None) -> str:
        roll = prompt_for_roll("Rzut na Thievery (podkradanie): ")
        outcome = resolve_skill_check(self.pickpocket_dc, roll)
        if outcome in ("success", "critical_success"):
            loot = (self.pickpocket_loot or ["drobne"])[0]
            return f"Udało się podkraść: {loot} (wynik: {outcome})."
        # porażka obniża nastawienie
        new_att, label = self.adjust_attitude(self.pickpocket_fail_attitude_delta)
        return (
            f"Przyłapany! Nastawienie spada do: {label} ({new_att}). "
            f"Wynik testu: {outcome}."
        )


META = GameObjectMeta(
    object_id="npc",
    label="NPC",
    color="#075f07",
    category="Interactables",
    placement="cell",
    description="Podstawowy NPC z dialogiem, handlem i kradzieżą.",
    logic_cls=NPC,
    default_config={
        "name": "Barman",
        "allow_same_cell_interact": True,
        "require_same_cell_interact": False,
        "blocks_movement": True,
        "attitude": 0,
        "inventory": [
            {"item_id": "ale", "name": "Kufel piwa", "price": 2},
            {"item_id": "rumor", "name": "Plotka o okolicy", "price": 1},
            {"item_id": "meal", "name": "Talerz gulaszu", "price": 4},
        ],
        "base_price_modifier": 1.0,
        "pickpocket_dc": 17,
        "pickpocket_loot": ["sakiewka z drobniakami"],
    },
)
