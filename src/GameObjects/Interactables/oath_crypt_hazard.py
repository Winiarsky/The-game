from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from oath_crypt_encounter import reject_proof, update_leds


class OathCryptHazard(InteractableMixin):
    def __init__(self, *, hazard_id: str = "ash_fissure", label: str = "Pęknięcie Popiołu") -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.hazard_id = str(hazard_id or "ash_fissure").strip()
        self.scenario_object_id = f"oath_crypt_{self.hazard_id}"
        self.name = str(label or "Pęknięcie Popiołu")
        self.register_action(
            Interaction(
                id="inspect",
                label="Oceń zagrożenie",
                description="Opisuje wpływ tego punktu na ruch i presję Odrana.",
                handler=OathCryptHazard.action_inspect,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="trigger",
                label="Wejdź w strefę",
                description="Symuluje wejście lub koniec tury w hazardzie.",
                handler=OathCryptHazard.action_trigger,
                end_interaction=False,
            )
        )
        self.register_action(Interaction(id="leave", label="Zakończ", handler=lambda *_: "Koniec interakcji."))

    def action_inspect(self, actor, game, _payload=None) -> str:
        update_leds(game, "odran_pressure")
        return f"{self.name}: trudny teren finału. Wejście lub koniec tury może oznaczać małe obrażenia, slowed albo wzrost presji Odrana."

    def action_trigger(self, actor, game, _payload=None) -> str:
        return reject_proof(game, reason=self.hazard_id)


META = GameObjectMeta(
    object_id="oath_crypt_hazard",
    label="Hazard Krypty",
    color="#7f1d1d",
    category="Interactables",
    placement="cell",
    description="Interaktywny hazard finałowej krypty: pęknięcie, łańcuch, sarkofag albo fałszywe lustro.",
    logic_cls=OathCryptHazard,
    default_config={"hazard_id": "ash_fissure", "label": "Pęknięcie Popiołu"},
)
