import json
import sys
from pathlib import Path
from enum import Enum, auto

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from board import Connection
import json
import sys
from pathlib import Path
from enum import Enum, auto

class GameState(Enum):
    START = auto()
    SETUP = auto()
