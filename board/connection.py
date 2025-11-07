import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Connection:
    def __init__(self, esp_ip:str = "http://192.168.0.77"):
        self.led_config = json.load(open('board/led_positions.json', 'r'))
        self.esp_ip = esp_ip

    def scan_board(self):
        """Scan the board for activit."""
        try:
            r = requests.get(f"{self.esp_ip}/scan_board")
            r.raise_for_status()
            data = r.json()
            logger.info(f"Scanned board data: {json.dumps(data, indent=2)}")
            return data

        except Exception as e:
            logger.error(f"Error scanning board: {e}")
    
    def set_leds(self, leds:list[tuple[int,list[int]]]):
        payload = {
            "leds": [{"i": i+1, "rgb": rgb} for i, rgb in leds]
            }
        r = requests.post(f"{self.esp_ip}/set", json=payload)
        logger.info(f"Set LEDs response: {r.status_code}, {r.text}")

    def leds_off(self):
        r = requests.get(f"{self.esp_ip}/off")
        logger.info(f"LEDs off response: {r.status_code}, {r.text}")