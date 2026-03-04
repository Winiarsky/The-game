from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin import TrappableMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from skills import Skill


class TrapTile(TrappableMixin, InteractableMixin):
    """Prosta pułapka wolnostojąca: wykryj/rozbrój/aktywuj."""

    def __init__(
        self,
        *,
        trap_armed: bool = True,
        trap_name: str = "Pułapka",
        trap_level: int = 1,
        trap_detection_dc: int = 16,
        trap_disable_dc: int = 18,
        trap_identify_dc: int | None = None,
        trap_trigger_description: str = "Wejście na pole.",
        trap_effect: str = "Obrażenia lub efekt statusu.",
        trap_attack_bonus: int | None = None,
        trap_damage_prompt: str | None = None,
        trap_damage_type: str = "piercing",
        trap_disable_successes_required: int = 1,
    ) -> None:
        InteractableMixin.__init__(self, position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.trap_armed = trap_armed
        self.trap_detected = False
        self.trap_identified = False
        self.trap_name = str(trap_name or "Pułapka")
        self.trap_level = int(trap_level or 0)
        self.trap_detection_dc = trap_detection_dc
        self.trap_disable_dc = trap_disable_dc
        self.trap_identify_dc = trap_identify_dc
        self.trap_trigger_description = str(trap_trigger_description or "Wejście na pole.")
        self.trap_effect = trap_effect
        self.trap_attack_bonus = trap_attack_bonus
        self.trap_damage_prompt = trap_damage_prompt
        self.trap_damage_type = str(trap_damage_type or "piercing")
        self.trap_disable_successes_required = max(1, int(trap_disable_successes_required or 1))
        self.trap_disable_progress = 0
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
                id="identify",
                label="Zidentyfikuj",
                description="Thievery vs DC identyfikacji mechanizmu.",
                handler=TrapTile.action_identify,
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
            if self.trap_identified:
                return self._trap_summary()
            return "Widzisz elementy pułapki."
        return "Wygląda zwyczajnie... chyba że to pułapka."

    def action_search(self, actor, game, _payload=None) -> str:
        result = resolve_skill_check_with_sources(
            skill_id=Skill.PERCEPTION.value,
            dc=self.trap_detection_dc,
            actor=actor,
            target=None,
            tags=[Skill.PERCEPTION.value, "trap", "search"],
            game=game,
            apply_modifiers=True,
        )
        outcome, msg = self.detect_trap(result.total)
        return f"{msg} (wynik: {outcome})"

    def action_identify(self, actor, game, _payload=None) -> str:
        result = resolve_skill_check_with_sources(
            skill_id=Skill.THIEVERY.value,
            dc=self._effective_identify_dc(),
            actor=actor,
            target=self,
            tags=[Skill.THIEVERY.value, "trap", "identify"],
            game=game,
            apply_modifiers=True,
        )
        outcome, msg = self.identify_trap(result.total)
        return f"{msg} (wynik: {outcome})"

    def action_disable(self, actor, game, _payload=None) -> str:
        result = resolve_skill_check_with_sources(
            skill_id=Skill.THIEVERY.value,
            dc=self.trap_disable_dc,
            actor=actor,
            target=self,
            tags=[Skill.THIEVERY.value, "trap", "disable"],
            game=game,
            apply_modifiers=True,
        )
        outcome, msg = self.disable_trap(result.total, actor=actor, game=game)
        return f"{msg} (wynik: {outcome})"

    def action_trigger(self, actor, game, _payload=None) -> str:
        if not self.trap_armed:
            return "Pułapka nieaktywna."
        effect = self.trigger_trap(actor=actor, game=game)
        return f"Celowo aktywujesz pułapkę: {effect}"

    # --- auto trigger przy wejściu ---
    def on_enter(self, actor, game) -> str | None:
        """Automatyczne odpalenie, gdy ktoś wejdzie na pole."""
        effect = self.on_enter_trap(actor, game)
        if not effect:
            return None
        if str(effect).lower().startswith("trap finder"):
            return effect
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
        "trap_name": "Pułapka",
        "trap_level": 1,
        "trap_detection_dc": 16,
        "trap_disable_dc": 18,
        "trap_identify_dc": 18,
        "trap_trigger_description": "Wejście na pole.",
        "trap_effect": "Pułapka zadaje 2k6 obrażeń.",
        "trap_attack_bonus": None,
        "trap_damage_prompt": None,
        "trap_damage_type": "piercing",
        "trap_disable_successes_required": 1,
    },
)
