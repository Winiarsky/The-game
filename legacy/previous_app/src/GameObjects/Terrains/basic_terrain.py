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

    def on_enter(self, actor, _game):
        if actor is None:
            return None
        try:
            from statuses import BLINDED_STATUS, CONCEALED_STATUS, IN_DARK_STATUS, IN_DIM_LIGHT_STATUS
        except Exception:
            return None
        remover = getattr(actor, "remove_status", None)
        if callable(remover):
            remover(BLINDED_STATUS)
            remover(CONCEALED_STATUS)
            remover(IN_DARK_STATUS)
            remover(IN_DIM_LIGHT_STATUS)
            return None
        statuses = getattr(actor, "statuses", None)
        if isinstance(statuses, list):
            blinded_id = getattr(BLINDED_STATUS, "id", "blinded")
            concealed_id = getattr(CONCEALED_STATUS, "id", "concealed")
            dark_id = getattr(IN_DARK_STATUS, "id", "in_dark")
            status_id = getattr(IN_DIM_LIGHT_STATUS, "id", "in_dim_light")
            for idx in range(len(statuses) - 1, -1, -1):
                item = statuses[idx]
                item_id = getattr(item, "id", None) if item is not None else None
                if item_id == blinded_id or item == blinded_id:
                    del statuses[idx]
                    continue
                if item_id == concealed_id or item == concealed_id:
                    del statuses[idx]
                    continue
                if item_id == dark_id or item == dark_id:
                    del statuses[idx]
                    continue
                if item_id == status_id or item == status_id:
                    del statuses[idx]
        return None
