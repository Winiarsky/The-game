from abc import ABC, abstractmethod
from typing import NamedTuple, TYPE_CHECKING

if TYPE_CHECKING:
    from src.game import Game
    from src.states.heroes_turns import HeroesTurn


class ActionContext(NamedTuple):
    game: "Game"
    heroes_turn: "HeroesTurn"


class BaseAction(ABC):
    prompt_source = "Wybierz bohatera"
    prompt_target = None  # akcje nie zawsze potrzebują celu
    name = "base_action"
    
    @abstractmethod
    def on_choose_info(self, ctx: ActionContext): ...
    
    @abstractmethod
    def execute(self, ctx: ActionContext): ...
