import requests
import json
import logging
from . import consts

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
        leds_to_light = [(self.led_config[str(row)][str(col)], rgb_color) for row, col in positions]
        payload = {
            "leds": [{"i": i+1, "rgb": rgb} for i, rgb in leds_to_light]
        }
        r = requests.post(f"{self.esp_ip}/set", json=payload)
        logger.info(f"Set LEDs response: {r.status_code}, {r.text}")

    def leds_off(self):
        r = requests.get(f"{self.esp_ip}/off")
        logger.info(f"LEDs off response: {r.status_code}, {r.text}")
        
    def read_card(self, msg: str = "Zeskanuj karte", acceptable_responses: list[str] | None = None) -> str:
        while True:
            card = input(msg) #trzeba bedze dodac slownik do mapowania
            if acceptable_responses and card not in acceptable_responses:
                logger.warning(f"Nieakceptowalna odpowiedz: {card}")
                continue
            return card
