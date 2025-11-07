from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from board.connection import Connection
from time import sleep


def test_connection(conn):
    assert conn is not None
    assert conn.esp_ip == "http://192.168.1.50"

def test_scan_board(conn):
    data = conn.scan_board()
    assert data is not None
    print("Scanned board data:", data)

def test_leds_set_and_off(conn):
    leds = [
        (0, [255, 0, 0]),     # LED 1 - czerwony
        (1, [0, 255, 0]),     # LED 2 - zielony
        (2, [0, 0, 255]),     # LED 3 - niebieski
        (3, [255, 255, 0]),   # LED 4 - żółty
        (4, [255, 0, 255]),   # LED 5 - fioletowy
    ]
    conn.set_leds(leds)
    sleep(5)
    conn.leds_off()

if __name__ == "__main__":
    conn = Connection("http://192.168.1.50")
    test_connection(conn)
    test_scan_board(conn)
    test_leds_set_and_off(conn)
