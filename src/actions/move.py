import logging

from .base import ActionContext, BaseAction
from .actions_registy import register

logger = logging.getLogger(__name__)


@register
class MoveAction(BaseAction):
    name = "move"
    prompt_source = "Wybierz bohatera do przesunięcia"
    prompt_target = "Wybierz pole docelowe"

    def execute(self, ctx: ActionContext, source, target):
        pass
        # Tutaj docelowo możesz wywołać logikę odpowiedzialną za ruch.
