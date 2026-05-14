from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin


class ChapelConfessional(InteractableMixin):
    def __init__(self, *, confessional_id: str = "chapel_confessional") -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.confessional_id = str(confessional_id or "chapel_confessional")
        self.scenario_object_id = self.confessional_id
        self.name = "Nienaruszony konfesjonal"
        self.label = "Nienaruszony konfesjonal"
        self.interaction_label = "Nienaruszony konfesjonal"
        self.register_default_actions()

    def register_default_actions(self) -> None:
        self.register_action(Interaction(id="listen", label="Wejdz do konfesjonalu", description="Uslysz pytanie kaplicy.", handler=ChapelConfessional.action_listen, end_interaction=False))
        self.register_action(Interaction(id="answer_silence", label="Odpowiedz: Silence", description="Prawidlowa spowiedz miejsca.", handler=ChapelConfessional.action_answer_silence, end_interaction=False))
        self.register_action(Interaction(id="leave", label="Zakoncz", description="Zakoncz interakcje.", handler=lambda *_: "Koniec interakcji."))

    def action_listen(self, actor, game, _payload=None) -> str:
        from burned_chapel_encounter import prompt_info, update_leds

        text = "Wyznajcie, co spalilo ten dom."
        prompt_info(game, "Nienaruszony konfesjonal", text, source="confessional_prompt")
        update_leds(game, "confessional_idle")
        return text

    def action_answer_silence(self, actor, game, _payload=None) -> str:
        from burned_chapel_encounter import complete_confessional, prompt_info

        msg = complete_confessional(game)
        prompt_info(game, "Silence", msg, source="confessional_silence")
        return msg


META = GameObjectMeta(
    object_id="chapel_confessional",
    label="Nienaruszony konfesjonal",
    color="#e5e7eb",
    category="Interactables",
    placement="cell",
    description="Trop z konfesjonalu: ujawnia milczenie, pekniety symbol swietego i kolejnosc posagow.",
    logic_cls=ChapelConfessional,
    default_config={"confessional_id": "chapel_confessional"},
)


__all__ = ["ChapelConfessional", "META"]
