from dataclasses import dataclass


@dataclass(slots=True)
class BasicTerrain:
    name: str = "basic"
    walkable: bool = True
    room: str = "basic room"
    stealth_impact: int = 0
    move_cost_bonus_feet: int = 0

    def on_critical_stealth_fail(self):
        return None

    def on_enter(self, _actor, _game):
        return None
