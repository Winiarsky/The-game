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

    def run(self, ctx: ActionContext):
        source = ctx.game.conn.scan_board() if self.prompt_source else None
        target = ctx.game.conn.scan_board() if self.prompt_target else None
        self.execute(ctx, source, target)

    @abstractmethod
    def execute(self, ctx: ActionContext, source, target): ...
