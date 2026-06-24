from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from hill_ruins_encounter import ensure_state, reconstruct_truth, flag_enabled


class HillRuinsCryptDescent(InteractableMixin):
    def __init__(self) -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.scenario_object_id = "hill_ruins_crypt_descent"
        self.name = "Zasypane zejście do Krypty Przysięgi"
        self.register_action(
            Interaction(
                id="inspect",
                label="Sprawdź zejście",
                description="Wyjaśnia, czego brakuje do otwarcia krypty.",
                handler=HillRuinsCryptDescent.action_inspect,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="force_memory",
                label="Przywołaj pełne wspomnienie",
                description="Działa dopiero, gdy rytuał jest ustabilizowany.",
                handler=HillRuinsCryptDescent.action_force_memory,
                end_interaction=False,
            )
        )
        self.register_action(Interaction(id="leave", label="Zakończ", handler=lambda *_: "Koniec interakcji."))

    def action_inspect(self, actor, game, _payload=None) -> str:
        state = ensure_state(game)
        if bool(state.get("crypt_descent_unsealed")) or flag_enabled(game, "crypt_descent_unsealed"):
            return "Zejście do krypty świeci zielono. Możecie przejść dalej."
        return "Kamienne schody są zasypane popiołem przysięgi. Otworzą się dopiero, gdy wspomnienie pokaże prawdę o relikwiarzu."

    def action_force_memory(self, actor, game, _payload=None) -> str:
        state = ensure_state(game)
        if int(state.get("ritual_stability", 0) or 0) < int(state.get("ritual_required", 4) or 4):
            return "Rytuał nie jest jeszcze stabilny. Same schody nie otworzą prawdy."
        return reconstruct_truth(game, method="crypt_descent")


META = GameObjectMeta(
    object_id="hill_ruins_crypt_descent",
    label="Zasypane zejście do krypty",
    color="#22c55e",
    category="Interactables",
    placement="cell",
    description="Fizyczny punkt zejścia do Krypty Przysięgi, otwierany po odtworzeniu prawdy.",
    logic_cls=HillRuinsCryptDescent,
    default_config={},
)
