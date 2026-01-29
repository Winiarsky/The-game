import logging
from typing import Optional

from GameObjects.base import GameObjectMeta
from interactable import Interaction
from GameObjects.Interactables.base_npc import BaseNPC
from interactions_mixin import (
    prompt_for_roll,
    resolve_skill_check,
    attitude_label,
    TradeItem,
)

logger = logging.getLogger(__name__)


class NPC(BaseNPC):
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

    def _run_dialog(self, game=None) -> str:
        """Prosta pętla dialogowa; zwraca ostatni komunikat. Wysyła tekst i wybory do UI jeśli dostępny."""
        node_id = "start"
        last_msg = ""
        ui = getattr(game, "ui", None) if game else None
        while True:
            node = self.dialog.get(node_id)
            if not node:
                return "NPC milczy, coś jest nie tak z dialogiem."
            text = node.get("text", "")
            delta = node.get("attitude_delta")
            if delta:
                new_att, label = self.adjust_attitude(delta)
                logger.info(f"Nastawienie {self.name}: {label} ({new_att}).")
                if ui and ui.enabled:
                    game.ui_log(f"Nastawienie {self.name}: {label} ({new_att}).")
            options = [
                opt
                for opt in node.get("options", [])
                if not opt.get("once") or opt["id"] not in self._dialog_used
            ]

            if ui and ui.enabled:
                game.ui_log(text)
                if not options:
                    return text
                choices = [f"{idx}: {opt.get('label', '...')}" for idx, opt in enumerate(options, start=1)]
                ans = ui.prompt_choice("Wybierz opcję (Enter aby wyjść): ", choices=choices, source="dialog")
                if not ans:
                    return "Kończysz rozmowę."
                normalized = ans.strip()
                if normalized.isdigit():
                    idx = int(normalized) - 1
                else:
                    idx = None
                    for j, opt in enumerate(options):
                        if normalized.lower() == str(opt.get("label", "")).lower():
                            idx = j
                            break
                if idx is None or idx < 0 or idx >= len(options):
                    return "Kończysz rozmowę."
                chosen = options[idx]
            else:
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
                        if ui and ui.enabled:
                            game.ui_log(f"Nastawienie {self.name}: {label} ({new_att}).")
                    node_id = check.get("on_success") or node_id
                else:
                    if "attitude_delta_failure" in check:
                        new_att, label = self.adjust_attitude(check["attitude_delta_failure"])
                        logger.info(f"Nastawienie {self.name}: {label} ({new_att}).")
                        if ui and ui.enabled:
                            game.ui_log(f"Nastawienie {self.name}: {label} ({new_att}).")
                    node_id = check.get("on_failure") or node_id
                continue
            if "attitude_delta" in chosen:
                new_att, label = self.adjust_attitude(chosen["attitude_delta"])
                logger.info(f"Nastawienie {self.name}: {label} ({new_att}).")
                if ui and ui.enabled:
                    game.ui_log(f"Nastawienie {self.name}: {label} ({new_att}).")
            last_msg = chosen.get("label", "")
            node_id = chosen.get("id")
            if not node_id:
                return text
            # przejdź do kolejnego węzła
            continue

    def action_talk(self, _actor, _game, _payload=None) -> str:
        return self._run_dialog(_game)

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
        has_status = getattr(actor, "has_status", None)
        is_stealthed = has_status("stealth") if callable(has_status) else "stealth" in getattr(actor, "statuses", [])
        if not is_stealthed:
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
