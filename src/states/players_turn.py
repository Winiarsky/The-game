from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from board import Connection, consts
from hero import Hero
from player import Player

from .base import State


logger = logging.getLogger(__name__)


class PlayersTurn(State):

    def on_enter(self):
        logger.info("Tura graczy!")

    def on_exit(self):
        logger.info("Koniec tury graczy.")
