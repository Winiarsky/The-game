from __future__ import annotations

from typing import Any

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from old_mill_encounter import flag_enabled, reveal_hidden_route
from skills import Skill


class OldMillBackTrack(InteractableMixin):
    def __init__(self, *, dc: int = 15, label: str = "Tylne deski") -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.scenario_object_id = "old_mill_back_track"
        self.name = str(label or "Tylne deski")
        self.dc = int(dc or 15)
        self.register_action(
            Interaction(
                id="search_route",
                label="Szukaj traktu",
                description=f"Survival DC {self.dc}; podpowiedzi z Tovina/dowodow obnizaja ryzyko.",
                handler=OldMillBackTrack.action_search,
                end_interaction=False,
            )
        )
        self.register_action(Interaction(id="leave", label="Zakoncz", handler=lambda *_: "Koniec interakcji."))

    def action_search(self, actor, game, _payload: dict[str, Any] | None = None) -> str:
        if any(flag_enabled(game, flag) for flag in ("tovin_secured", "mill_hidden_route_hint", "false_ash_secured", "mill_ledger_secured")):
            return reveal_hidden_route(game)
        result = resolve_skill_check_with_sources(
            skill_id=Skill.SURVIVAL.value,
            dc=self.dc,
            actor=actor,
            target=self,
            tags=[Skill.SURVIVAL.value, "old_mill", "hidden_route"],
            game=game,
            apply_modifiers=True,
        )
        outcome = str(result.outcome or "")
        if outcome in {"success", "critical_success"}:
            return f"{reveal_hidden_route(game)} (wynik: {outcome}, suma: {result.total})"
        return f"Deski wygladaja podejrzanie, ale nie znajdujecie mechanizmu. (wynik: {outcome}, suma: {result.total})"


META = GameObjectMeta(
    object_id="old_mill_back_track",
    label="Tylne deski",
    color="#22c55e",
    category="Interactables",
    placement="cell",
    description="Interakcja odkrywajaca ukryty trakt do ruin.",
    logic_cls=OldMillBackTrack,
    default_config={"dc": 15, "label": "Tylne deski"},
)
