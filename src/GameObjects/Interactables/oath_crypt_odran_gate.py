from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from oath_crypt_encounter import confront_odran, ensure_state, flag_enabled


class OathCryptOdranGate(InteractableMixin):
    def __init__(self) -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.scenario_object_id = "oath_crypt_odran_gate"
        self.name = "Brama Odrana"
        self.register_action(
            Interaction(
                id="inspect",
                label="Sprawdź bramę",
                description="Wyjaśnia status kosztownego finałowego wyboru.",
                handler=OathCryptOdranGate.action_inspect,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="name_bargain",
                label="Nazwij układ Odrana",
                description="Odblokowuje świadomą opcję kosztownego zakończenia.",
                handler=lambda obj, actor, game, payload: confront_odran(game),
                end_interaction=False,
            )
        )
        self.register_action(Interaction(id="leave", label="Zakończ", handler=lambda *_: "Koniec interakcji."))

    def action_inspect(self, actor, game, _payload=None) -> str:
        state = ensure_state(game)
        if bool(state.get("bargain_unlocked")) or flag_enabled(game, "bargain_unlocked"):
            return "Brama Odrana pulsuje czerwono. Pozwolenie mu odejść jest finałową decyzją: relikwiarz zostanie utracony."
        return "Brama nie jest jeszcze finałowym wyborem. Najpierw trzeba skonfrontować Odrana albo przedstawić komplet dowodów."


META = GameObjectMeta(
    object_id="oath_crypt_odran_gate",
    label="Brama Odrana",
    color="#991b1b",
    category="Interactables",
    placement="cell",
    description="Fizyczny punkt kosztownego finałowego wyboru.",
    logic_cls=OathCryptOdranGate,
    default_config={},
)
