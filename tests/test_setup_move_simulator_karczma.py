from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
    
from src.game import Game
from board import Connection
from time import sleep
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

simulator_conn = Connection(esp_ip="http://127.0.0.1:5000/")
game = Game(conn=simulator_conn, scenario="karczma_pop")
game.conn.leds_off()
game.run_action('set_heroes_starting_positions')
# check the positions
for hero in game.heroes:
    position = hero.position
    if position is None:
        continue
    print(f"Hero at position: {position}")
    game.conn.set_leds([position], [150, 0, 0])  # Red for hero position
    sleep(5)
    game.conn.leds_off()
# trzeba zmienic logike zapalania ledow, gra powinna trymac ledy ktore sa do zapalania a funkcja set leds, po prostu powinna wyolywac zapalanie tych ledow, ta lista powinna dosyc dynamiczna, czyli powinnismy miec mozliwosc doawania i usuwania ledow oraz zapalania roznych sekcji
# set_leds(move) albo set_leds(goal) itp
stop = False
while True:
    goal_pos = (8, 9)
    game.conn.set_leds([goal_pos], [0, 0, 255])
    game.run_action('choose_action')
    game.conn.set_leds([goal_pos], [0, 0, 255])
    for hero in game.heroes:
        pos = hero.position
        if pos is None:
            continue
        if pos == goal_pos:
            logger.info(f"Hero reached the goal at position: {pos}")
            game.conn.set_leds([pos], [255, 0, 0])
            sleep(5)
            game.conn.leds_off()
            stop = True
            break
    if stop:
        break
logger.info("Simulation ended.")
        

