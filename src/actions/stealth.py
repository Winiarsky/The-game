from __future__ import annotations

from actions.move_utils import perform_movement  # re-export stub
from GameObjects.interactions_mixin.prompt_utils import prompt_for_roll

def iter_watchers_in_rooms(*_args, **_kwargs):
    return []

def summarize_watchers(_watchers):
    return 0, []

class StealthAction:
    """Stub klasy używanej w testach/awareness."""

    def __init__(self, *a, **k):
        pass

    def execute(self, ctx):
        return None

# prosty helper do zgodności z testami
def _compute_modifier(ctx, pos):
    return 0, []
