from __future__ import annotations

from typing import Optional

from board import consts
from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin import HiddenMixin
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from skills import Skill


class ScenarioExit(HiddenMixin, InteractableMixin):
    """Przejście mapowe obsługiwane przez ScenarioSession."""

    def __init__(
        self,
        *,
        exit_id: str,
        label: str | None = None,
        interaction_mode: str = "on_enter",
        hidden: bool = False,
        allow_hidden_interaction: bool = True,
        reveal_dc: int = 18,
        seekable: bool = True,
        reveal_tags: Optional[list[str]] = None,
        auto_reveal_on_enter: bool = False,
        requires_confirmation: bool = False,
        reveal_message: str | None = None,
    ) -> None:
        InteractableMixin.__init__(
            self,
            position=None,
            allow_same_cell_interact=True,
            allow_hidden_interaction=allow_hidden_interaction,
            blocks_movement=False,
        )
        self.exit_id = str(exit_id or "").strip()
        self.exit_label = str(label or self.exit_id or "Scenario exit").strip()
        self.interaction_mode = str(interaction_mode or "on_enter").strip().lower() or "on_enter"
        self.hidden = bool(hidden)
        self.revealed = not self.hidden
        self.reveal_dc = int(reveal_dc or 18)
        self.seekable = bool(seekable)
        self.reveal_tags = tuple(reveal_tags or ())
        self.auto_reveal_on_enter = bool(auto_reveal_on_enter)
        self.requires_confirmation = bool(requires_confirmation)
        self.reveal_message = (
            str(reveal_message).strip()
            if reveal_message
            else "Odkrywasz przejście prowadzące dalej."
        )
        self.seek_color = list(consts.SEEK_EXIT_RGB)
        self.seek_color_name = "pomarańczowe"
        self.seek_label = "przejście"
        self.register_default_actions()

    def register_default_actions(self) -> None:
        self.register_action(
            Interaction(
                id="search",
                label="Przeszukaj",
                description="Perception vs DC sekretu.",
                handler=ScenarioExit.action_search,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="travel",
                label="Przejdź",
                description="Przenieś drużynę na docelową mapę.",
                handler=ScenarioExit.action_travel,
                end_interaction=True,
            )
        )
        self.register_action(
            Interaction(
                id="leave",
                label="Zakończ",
                description="Wyjdź z interakcji.",
                handler=lambda *_args, **_kwargs: "Kończysz oględziny przejścia.",
                end_interaction=True,
            )
        )

    def action_search(self, actor, game, _payload=None) -> str:
        tags = [Skill.PERCEPTION.value, "seek", "scenario_exit"]
        tags.extend([tag for tag in self.reveal_tags if tag not in tags])
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
        if self.revealed:
            self.on_reveal(game, source_actor=actor)
        return f"{msg} (wynik: {outcome})"

    def action_travel(self, actor, game, _payload=None) -> str:
        if self.hidden and not self.revealed:
            return "Nie widzisz tu żadnego przejścia."
        session = getattr(game, "scenario_session", None)
        if session is None:
            return "Brak aktywnej sesji scenariusza."
        ok, message = session.request_transition(
            exit_id=self.exit_id,
            trigger_type="exit_interact",
            source_map_id=getattr(session, "current_map_id", None),
            actor=actor,
            source_object=self,
        )
        return str(message or ("Przejście aktywowane." if ok else "Przejście jest niedostępne."))

    def on_enter(self, actor, game) -> str | None:
        if self.auto_reveal_on_enter and self.hidden and not self.revealed:
            tags = [Skill.PERCEPTION.value, "seek", "scenario_exit"]
            tags.extend([tag for tag in self.reveal_tags if tag not in tags])
            result = resolve_skill_check_with_sources(
                skill_id=Skill.PERCEPTION.value,
                dc=self.reveal_dc,
                actor=actor,
                target=None,
                tags=tags,
                game=game,
                apply_modifiers=True,
            )
            self.try_reveal(result.total)
            if self.revealed:
                extra = self.on_reveal(game, source_actor=actor)
                if extra:
                    return str(extra)
        if self.hidden and not self.revealed:
            return None
        if self.interaction_mode != "on_enter":
            return None
        session = getattr(game, "scenario_session", None)
        if session is None:
            return None
        ok, message = session.request_transition(
            exit_id=self.exit_id,
            trigger_type="exit_enter",
            source_map_id=getattr(session, "current_map_id", None),
            actor=actor,
            source_object=self,
        )
        return str(message) if (ok or message) else None

    def on_reveal(self, game, source_actor=None) -> str | None:
        session = getattr(game, "scenario_session", None)
        if session is not None:
            session.dispatch_trigger(
                "object_revealed",
                map_id=getattr(session, "current_map_id", None),
                target_id=self.exit_id,
                actor=source_actor,
                source_object=self,
            )
        return self.reveal_message


META = GameObjectMeta(
    object_id="scenario_exit",
    label="Scenario Exit",
    color="#f59e0b",
    category="Interactables",
    placement="cell",
    description="Logiczne przejście między mapami sterowane flow scenariusza.",
    logic_cls=ScenarioExit,
    default_config={
        "exit_id": "exit_default",
        "label": "",
        "interaction_mode": "on_enter",
        "hidden": False,
        "allow_hidden_interaction": True,
        "reveal_dc": 18,
        "seekable": True,
        "reveal_tags": [],
        "auto_reveal_on_enter": False,
        "requires_confirmation": False,
        "reveal_message": "",
    },
)
