from abc import ABC, abstractmethod
from typing import NamedTuple, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.game import Game
    from src.states.base import State


class ActionContext(NamedTuple):
    game: "Game"
    heroes_turn: "State"
    actor: Optional[object] = None
    action_tags: Optional[list[str]] = None  # opcjonalne: wstępnie znane tagi


class BaseAction(ABC):
    prompt_source = "Wybierz bohatera"
    prompt_target = None  # akcje nie zawsze potrzebują celu
    name = "base_action"
    
    @abstractmethod
    def on_choose_info(self, ctx: ActionContext): ...
    
    @abstractmethod
    def execute(self, ctx: ActionContext): ...
