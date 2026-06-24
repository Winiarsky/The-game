from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from board.connection import Connection

if __name__ == "__main__":
    conn = Connection("http://127.0.0.1:5000/")
    while True:
        pos = conn.scan_board()
        print("Scanned position:", pos)
        conn.set_leds([pos], [0,255,0])
        # input("Press Enter to continue...")
        # conn.leds_off()