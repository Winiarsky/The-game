from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin import TrappableMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources


class TrapTile(TrappableMixin, InteractableMixin):
    """Prosta pułapka wolnostojąca: wykryj/rozbrój/aktywuj."""

    def __init__(
        self,
        *,
        trap_armed: bool = True,
        trap_detection_dc: int = 16,
        trap_disable_dc: int = 18,
        trap_effect: str = "Obrażenia lub efekt statusu.",
    ) -> None:
        InteractableMixin.__init__(self, position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.trap_armed = trap_armed
        self.trap_detected = False
        self.trap_detection_dc = trap_detection_dc
        self.trap_disable_dc = trap_disable_dc
        self.trap_effect = trap_effect
        self.register_default_actions()

    def register_default_actions(self) -> None:
        self.register_action(
            Interaction(
                id="inspect",
                label="Obejrzyj",
                description="Rzut oka na potencjalną pułapkę.",
                handler=TrapTile.action_inspect,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="search",
                label="Szukaj",
                description="Perception vs DC wykrycia.",
                handler=TrapTile.action_search,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="disable",
                label="Rozbrój",
                description="Thievery vs DC rozbrojenia.",
                handler=TrapTile.action_disable,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="trigger",
                label="Aktywuj celowo",
                description="Bezpiecznie wyzwól pułapkę.",
                handler=TrapTile.action_trigger,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="leave",
                label="Zakończ",
                description="Zakończ interakcję.",
                handler=lambda *_: "Koniec interakcji.",
            )
        )

    def action_inspect(self, actor, game, _payload=None) -> str:
        if not self.trap_armed:
            return "Mechanizm wygląda na rozbrojony."
        if self.trap_detected:
            return "Widzisz elementy pułapki."
        return "Wygląda zwyczajnie... chyba że to pułapka."

    def action_search(self, actor, game, _payload=None) -> str:
        result = resolve_skill_check_with_sources(
            skill_id="perception",
            dc=self.trap_detection_dc,
            actor=actor,
            target=None,
            tags=["perception", "trap", "search"],
            game=game,
            apply_modifiers=False,
        )
        outcome, msg = self.detect_trap(result.total)
        return f"{msg} (wynik: {outcome})"

    def action_disable(self, actor, game, _payload=None) -> str:
        result = resolve_skill_check_with_sources(
            skill_id="thievery",
            dc=self.trap_disable_dc,
            actor=actor,
            target=None,
            tags=["thievery", "trap", "disable"],
            game=game,
            apply_modifiers=False,
        )
        outcome, msg = self.disable_trap(result.total)
        return f"{msg} (wynik: {outcome})"

    def action_trigger(self, actor, game, _payload=None) -> str:
        if not self.trap_armed:
            return "Pułapka nieaktywna."
        effect = self.trigger_trap()
        return f"Celowo aktywujesz pułapkę: {effect}"

    # --- auto trigger przy wejściu ---
    def on_enter(self, actor, game) -> str | None:
        """Automatyczne odpalenie, gdy ktoś wejdzie na pole."""
        if not self.trap_armed:
            return None
        effect = self.trigger_trap()
        # Po odpaleniu uznajemy, że pułapka została wykryta i nieaktywna.
        self.trap_detected = True
        return f"Pułapka aktywuje się pod stopami! {effect}"


META = GameObjectMeta(
    object_id="trap_tile",
    label="Pułapka",
    color="#e85",
    category="Interactables",
    placement="cell",
    description="Wolnostojąca pułapka do wykrycia/rozbrojenia/aktywacji.",
    logic_cls=TrapTile,
    default_config={
        "trap_armed": True,
        "trap_detection_dc": 16,
        "trap_disable_dc": 18,
        "trap_effect": "Pułapka zadaje 2k6 obrażeń.",
    },
)
