import requests
import json
import logging
import sys
from pathlib import Path
from . import consts
from time import sleep

PROJECT_ROOT = Path(__file__).resolve().parents[1].parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from src.ui_client import get_ui_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Connection:
    def __init__(self, esp_ip:str = consts.ESP_IP):
        self.led_config = json.load(open('board/led_positions.json', 'r'))
        self.esp_ip = esp_ip

    def scan_board(self, acceptable_responses: list[tuple[int, int]] | None = None) -> tuple[int, int]:
        """Scan the board for activit."""
        while True:
            try:
                r = requests.get(f"{self.esp_ip}/scan_board")
                r.raise_for_status()
                sleep(consts.RESPONSE_DELAY)  # wait for esp to process
                data = r.json()
                response = (int(data['col']-1), int(data['row']-1)) # to fix on board
                if acceptable_responses and response not in acceptable_responses:
                    logger.warning(f"Nieakceptowalna odpowiedz: {response}")
                    logger.warning(f"Acceptable responses: {acceptable_responses}")
                    continue
                logger.info(f"Scanned board data: {json.dumps(data, indent=2)}")
                return response
            except Exception as e:
                logger.error(f"Error scanning board: {e}")
                raise RuntimeError("Failed to scan board") from e

    def set_leds(self, positions: list[tuple[int, int]], rgb_color: list[int]):
        logger.info(positions)
        leds_to_light = [(self.led_config[str(col)][str(row)], rgb_color) for col, row in positions]
        logger.info(f"Setting LEDs: {leds_to_light}")
        payload = {
            "leds": [{"i": i+1, "rgb": rgb} for i, rgb in leds_to_light]
        }
        r = requests.post(f"{self.esp_ip}/set", json=payload)
        logger.info(f"Set LEDs response: {r.status_code}, {r.text}")

    def leds_off(self):
        r = requests.get(f"{self.esp_ip}/off")
        logger.info(f"LEDs off response: {r.status_code}, {r.text}")
        
    def read_card(self, msg: str = "Zeskanuj karte", acceptable_responses: list[str] | None = None) -> str:
        translate_map = {
            "+": "ACCEPT",
            "-": "DECLINE",
            "1": "move",
            "2": "interact",
            "3": "seek",
            "4": "stealth",
            "5": "test_attack",
        }
        
        while True:
            # UI prompt (jeśli dostępny)
            ui = get_ui_client()
            if ui.enabled:
                ui_answer = ui.prompt_choice(msg, choices=acceptable_responses, source="card")
                if ui_answer:
                    card_response = translate_map.get(ui_answer, ui_answer)
                    if acceptable_responses and card_response not in acceptable_responses:
                        logger.warning(f"Nieakceptowalna odpowiedz (UI): {card_response}")
                    else:
                        logger.info(f"Scanned via UI {ui_answer}: {card_response}")
                        return card_response

            card = input(msg) #trzeba bedze dodac slownik do mapowania
            card_response = translate_map.get(card, card)
            logger.info(f"Scanned {card}: {card_response}")
            if acceptable_responses and card_response not in acceptable_responses:
                logger.warning(f"Nieakceptowalna odpowiedz: {card_response}")
                continue
            return card_response
