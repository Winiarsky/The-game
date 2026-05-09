from __future__ import annotations

from typing import Any

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources


class SkillChallenge(InteractableMixin):
    """Small scenario skill check node for investigation and social beats."""

    def __init__(
        self,
        *,
        challenge_id: str = "",
        label: str = "Wyzwanie",
        skill_id: str = "perception",
        dc: int = 15,
        tags: list[str] | None = None,
        intro: str = "",
        success_flag: str | None = None,
        success_message: str = "Udaje się.",
        failure_message: str = "Nie udaje się uzyskać przewagi.",
        outcome_messages: dict[str, str] | None = None,
        outcome_flags: dict[str, list[str] | str] | None = None,
        allow_same_cell_interact: bool = True,
        require_same_cell_interact: bool = False,
        blocks_movement: bool = False,
    ) -> None:
        super().__init__(
            position=None,
            allow_same_cell_interact=allow_same_cell_interact,
            require_same_cell_interact=require_same_cell_interact,
            blocks_movement=blocks_movement,
        )
        self.challenge_id = str(challenge_id or "").strip()
        self.scenario_object_id = self.challenge_id
        self.challenge_label = str(label or "Wyzwanie").strip()
        self.name = self.challenge_label
        self.label = self.challenge_label
        self.interaction_label = self.challenge_label
        self.skill_id = str(skill_id or "perception").strip().lower()
        self.dc = int(dc or 15)
        self.tags = tuple(str(tag).strip().lower() for tag in (tags or []) if str(tag).strip())
        self.intro = str(intro or "").strip()
        self.success_flag = str(success_flag or "").strip()
        self.success_message = str(success_message or "Udaje się.").strip()
        self.failure_message = str(failure_message or "Nie udaje się uzyskać przewagi.").strip()
        self.outcome_messages = dict(outcome_messages or {})
        self.outcome_flags = dict(outcome_flags or {})
        self.completed = False
        self.register_default_actions()

    def register_default_actions(self) -> None:
        self.register_action(
            Interaction(
                id="attempt",
                label=self.challenge_label,
                description=f"{self.skill_id.title()} DC {self.dc}.",
                handler=SkillChallenge.action_attempt,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="leave",
                label="Zakończ",
                description="Zakończ interakcję.",
                handler=lambda *_args, **_kwargs: "Koniec interakcji.",
            )
        )

    def action_attempt(self, actor, game, _payload: dict[str, Any] | None = None) -> str:
        if self.intro:
            self._prompt_info(game, self.challenge_label, self.intro, source_suffix="intro")
        result = resolve_skill_check_with_sources(
            skill_id=self.skill_id,
            dc=self.dc,
            actor=actor,
            target=self,
            tags=[self.skill_id, "scenario_skill_challenge", *self.tags],
            game=game,
            apply_modifiers=True,
        )
        outcome = str(result.outcome or "")
        message = str(self.outcome_messages.get(outcome) or "").strip()
        if outcome in {"success", "critical_success"}:
            self.completed = True
            if self.success_flag:
                self._set_flag(game, self.success_flag)
            if not message:
                message = self.success_message
        elif not message:
            message = self.failure_message
        for flag in self._flags_for_outcome(outcome):
            self._set_flag(game, flag)
        final = f"{message} (wynik: {self._outcome_label(outcome)}, suma: {result.total})"
        self._prompt_info(game, self.challenge_label, final, source_suffix=outcome)
        return final

    def _outcome_label(self, outcome: str) -> str:
        return {
            "critical_success": "krytyczny sukces",
            "success": "sukces",
            "failure": "porażka",
            "critical_failure": "krytyczna porażka",
        }.get(str(outcome or "").strip().lower(), str(outcome or "wynik"))

    def _flags_for_outcome(self, outcome: str) -> list[str]:
        raw = self.outcome_flags.get(outcome)
        if raw is None and outcome == "critical_success":
            raw = self.outcome_flags.get("success")
        if raw is None:
            return []
        if isinstance(raw, str):
            return [raw]
        if isinstance(raw, list):
            return [str(item) for item in raw if str(item).strip()]
        return []

    def _set_flag(self, game, flag: str) -> None:
        key = str(flag or "").strip()
        if not key:
            return
        session = getattr(game, "scenario_session", None)
        flags = getattr(session, "global_flags", None)
        if isinstance(flags, dict):
            flags[key] = True
            return
        flags = getattr(game, "global_flags", None)
        if isinstance(flags, dict):
            flags[key] = True

    def _prompt_info(self, game, title: str, text: str, *, source_suffix: str) -> None:
        ui = getattr(game, "ui", None)
        if ui is None or not getattr(ui, "enabled", False) or not hasattr(ui, "prompt_info"):
            return
        try:
            ui.prompt_info(
                title,
                prompt_long=text,
                source=f"skill_challenge:{self.challenge_id or self.challenge_label}:{source_suffix}",
            )
        except Exception:
            return


META = GameObjectMeta(
    object_id="skill_challenge",
    label="Wyzwanie umiejętności",
    color="#38bdf8",
    category="Interactables",
    placement="cell",
    description="Fabularny test umiejętności przypięty do mapy scenariusza.",
    logic_cls=SkillChallenge,
    default_config={
        "challenge_id": "",
        "label": "Wyzwanie",
        "skill_id": "perception",
        "dc": 15,
        "tags": [],
        "intro": "",
        "success_flag": "",
        "success_message": "Udaje się.",
        "failure_message": "Nie udaje się uzyskać przewagi.",
        "outcome_messages": {},
        "outcome_flags": {},
        "allow_same_cell_interact": True,
        "require_same_cell_interact": False,
        "blocks_movement": False,
    },
)


__all__ = ["SkillChallenge", "META"]
