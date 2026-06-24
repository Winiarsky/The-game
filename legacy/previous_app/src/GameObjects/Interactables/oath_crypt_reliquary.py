from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from oath_crypt_encounter import ensure_state, flag_enabled, unlock_restore


class OathCryptReliquary(InteractableMixin):
    def __init__(self) -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.scenario_object_id = "oath_crypt_reliquary"
        self.name = "Relikwiarz Przysięgi"
        self.register_action(
            Interaction(
                id="inspect",
                label="Sprawdź relikwiarz",
                description="Pokazuje, ile dowodów brakuje do przywrócenia przysięgi.",
                handler=OathCryptReliquary.action_inspect,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="stabilize",
                label="Stabilizuj relikwiarz",
                description="Działa dopiero po przyjęciu czterech dowodów.",
                handler=OathCryptReliquary.action_stabilize,
                end_interaction=False,
            )
        )
        self.register_action(Interaction(id="leave", label="Zakończ", handler=lambda *_: "Koniec interakcji."))

    def action_inspect(self, actor, game, _payload=None) -> str:
        state = ensure_state(game)
        if bool(state.get("restore_oath_unlocked")) or flag_enabled(game, "restore_oath_unlocked"):
            return "Relikwiarz świeci pełnym białym światłem. Interakcja Przywróć Przysięgę jest gotowa."
        progress = int(state.get("proof_score", 0) or 0)
        required = int(state.get("proof_required", 4) or 4)
        return f"Relikwiarz jest zimny. Serai potrzebuje czterech przyjętych dowodów: {progress}/{required}."

    def action_stabilize(self, actor, game, _payload=None) -> str:
        state = ensure_state(game)
        if int(state.get("proof_score", 0) or 0) < int(state.get("proof_required", 4) or 4):
            return self.action_inspect(actor, game)
        return unlock_restore(game)


META = GameObjectMeta(
    object_id="oath_crypt_reliquary",
    label="Relikwiarz Przysięgi",
    color="#f8fafc",
    category="Interactables",
    placement="cell",
    description="Centralny punkt dobrego zakończenia, odblokowany po przedstawieniu dowodów.",
    logic_cls=OathCryptReliquary,
    default_config={},
)
