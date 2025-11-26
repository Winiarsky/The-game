from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from board.connection import Connection
from time import sleep


def test_connection(conn):
    assert conn is not None
    assert conn.esp_ip == "http://127.0.0.1:5000/"

def test_scan_board(conn):
    data = conn.scan_board()
    assert data is not None
    print("Scanned board data:", data)

def test_leds_set_and_off(conn):
    fields = [
        (0, 0),     # LED 1 - czerwony
        (1, 1),     # LED 2 - zielony
        (2, 2),     # LED 3 - niebieski
        (3, 3),   # LED 4 - żółty
        (4, 4),
    ]
    conn.set_leds(fields, [0,200,0])
    sleep(5)
    conn.leds_off()
    sleep(5)
    conn.set_leds(fields, [200,0,0])
    sleep(5)
    conn.leds_off()
    sleep(5)
    conn.set_leds(fields, [0,0,200])
    sleep(5)
    conn.leds_off()

def test_read_card(conn):
    card = conn.read_card("Please scan your card: ")
    print("Scanned card:", card)

if __name__ == "__main__":
    conn = Connection("http://127.0.0.1:5000/")
    test_connection(conn)
    test_scan_board(conn)
    test_leds_set_and_off(conn)
    test_read_card(conn)