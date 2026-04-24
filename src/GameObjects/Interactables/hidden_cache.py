from typing import Optional

from board import consts
from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin import HiddenMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from skills import Skill


class HiddenCache(HiddenMixin, InteractableMixin):
    """Ukryty schowek/sekretne przejście do wykrycia lub ślepego trafienia."""

    def __init__(
        self,
        *,
        loot: Optional[list[str]] = None,
        hidden: bool = True,
        allow_hidden_interaction: bool = True,
        reveal_dc: int = 18,
        seekable: bool = True,
        reveal_tags: Optional[list[str]] = None,
        auto_reveal_on_enter: bool = False,
        auto_trigger_on_enter: bool = False,
        trap_effect: str | None = None,
        magical: bool = True,
        magical_description: str = "Wyczuwasz obecnosc magicznej skrytki",
    ):
        InteractableMixin.__init__(
            self,
            position=None,
            allow_same_cell_interact=True,
            allow_hidden_interaction=allow_hidden_interaction,
            blocks_movement=False,
        )
        self.hidden = hidden
        self.revealed = not hidden
        self.reveal_dc = reveal_dc
        self.seekable = seekable
        self.reveal_tags = tuple(reveal_tags or [])
        self.loot = list(loot or [])
        self.opened = False
        self.magical = magical
        self.magical_description = magical_description
        self.auto_reveal_on_enter = auto_reveal_on_enter
        self.auto_trigger_on_enter = auto_trigger_on_enter
        self.trap_effect = trap_effect or "Cichy alarm – czujesz niepokój."
        self.seek_color = list(consts.SEEK_CONTAINER_RGB)
        self.seek_color_name = "zielone"
        self.seek_label = "skrytka"
        self.register_default_actions()

    def register_default_actions(self) -> None:
        self.register_action(
            Interaction(
                id="search",
                label="Przeszukaj",
                description="Perception vs DC sekretu.",
                handler=HiddenCache.action_search,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="blind_probe",
                label="Ślepy strzał",
                description="Macanie bez podpowiedzi.",
                handler=HiddenCache.action_blind_probe,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="open",
                label="Otwórz",
                description="Otwórz, jeśli sekret odkryty.",
                handler=HiddenCache.action_open,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="loot",
                label="Zbierz",
                description="Weź zawartość schowka.",
                handler=HiddenCache.action_loot,
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

    def action_search(self, actor, game, _payload=None) -> str:
        tags = [Skill.PERCEPTION.value, "seek", "hidden_cache"]
        tags.extend([t for t in self.reveal_tags if t not in tags])
        result = resolve_skill_check_with_sources(
            skill_id=Skill.PERCEPTION.value,
            dc=self.reveal_dc,
            actor=actor,
            target=None,
            tags=tags,
            game=game,
            apply_modifiers=True,
        )
        outcome, msg = self.try_reveal(result.total)
        return f"{msg} (wynik: {outcome})"

    def action_blind_probe(self, actor, game, _payload=None) -> str:
        if not self.hidden:
            return "Ten element nie jest ukryty."
        if self.revealed:
            return "Sekret już odkryty."
        tags = [Skill.PERCEPTION.value, "seek", "hidden_cache"]
        tags.extend([t for t in self.reveal_tags if t not in tags])
        result = resolve_skill_check_with_sources(
            skill_id=Skill.PERCEPTION.value,
            dc=self.reveal_dc + 2,
            actor=actor,
            target=None,
            tags=tags,
            game=game,
            apply_modifiers=True,
        )
        roll = result.total
        # trudniej bez kontekstu
        if roll >= self.reveal_dc + 2:
            self.revealed = True
            return "Udaje się namacać ukryty mechanizm."
        return "Macasz na ślepo, nic nie znajdujesz."

    def action_open(self, actor, game, _payload=None) -> str:
        if not self.revealed:
            return "Nie widzisz tu nic do otwarcia."
        if self.opened:
            return "Sekret już otwarty."
        self.opened = True
        return "Odsuwasz panel, odkrywając skrytkę."

    def action_loot(self, actor, game, _payload=None) -> str:
        if not self.opened:
            return "Najpierw musisz otworzyć skrytkę."
        if not self.loot:
            return "W środku pusto."
        loot_items = self.loot[:]
        self.loot = []
        return f"Zabierasz: {', '.join(loot_items)}."

    def on_enter(self, actor, game) -> str | None:
        """Wejście na pole: opcjonalne auto-odkrycie/wyzwolenie efektu."""
        messages: list[str] = []
        if self.auto_reveal_on_enter and self.hidden and not self.revealed:
            tags = [Skill.PERCEPTION.value, "seek", "hidden_cache"]
            tags.extend([t for t in self.reveal_tags if t not in tags])
            result = resolve_skill_check_with_sources(
                skill_id=Skill.PERCEPTION.value,
                dc=self.reveal_dc,
                actor=actor,
                target=None,
                tags=tags,
                game=game,
                apply_modifiers=True,
            )
            outcome, msg = self.try_reveal(result.total)
            messages.append(f"{msg} (wynik: {outcome})")
        if self.auto_trigger_on_enter and self.trap_effect and self.hidden:
            # ukryty czujnik – odpala nawet jeśli nie odkryto
            messages.append(f"Wyzwalasz ukryty efekt: {self.trap_effect}")
            self.auto_trigger_on_enter = False
        return " ".join(messages) if messages else None


META = GameObjectMeta(
    object_id="hidden_cache",
    label="Ukryty element",
    color="#6ab",
    category="Interactables",
    placement="cell",
    description="Sekretny schowek lub przejście wymagające wykrycia.",
    logic_cls=HiddenCache,
    default_config={
        "loot": [],
        "hidden": True,
        "allow_hidden_interaction": True,
        "reveal_dc": 18,
        "seekable": True,
        "reveal_tags": [],
        "auto_reveal_on_enter": False,
        "auto_trigger_on_enter": False,
        "trap_effect": None,
    },
)
