from __future__ import annotations

import re
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
        flag_modifiers: list[dict[str, Any]] | None = None,
        conditions: dict[str, Any] | None = None,
        required_flags: list[str] | None = None,
        hidden: bool = False,
        allow_hidden_interaction: bool = False,
        reveal_dc: int = 15,
        seekable: bool = True,
        reveal_tags: list[str] | None = None,
        description_on_reveal: str | None = None,
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
        self.flag_modifiers = self._normalize_flag_modifiers(flag_modifiers)
        self.conditions = dict(conditions or {})
        if required_flags:
            merged = list(self.conditions.get("all_flags") or self.conditions.get("flags") or [])
            merged.extend(str(flag) for flag in required_flags if str(flag).strip())
            self.conditions["all_flags"] = merged
        self.hidden = bool(hidden)
        self.revealed = not self.hidden
        self.allow_hidden_interaction = bool(allow_hidden_interaction)
        self.reveal_dc = int(reveal_dc or 15)
        self.seekable = bool(seekable)
        self.reveal_tags = tuple(str(tag).strip().lower() for tag in (reveal_tags or []) if str(tag).strip())
        self.description_on_reveal = str(description_on_reveal or "").strip()
        self.revealed_by_seek = False
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

    def can_interact(self, actor, game) -> bool:
        return self._conditions_pass(game)

    def try_reveal(self, roll: int) -> tuple[str, str]:
        total = int(roll or 0)
        if self.revealed:
            return "success", f"{self.challenge_label} jest już odkryte."
        if total >= self.reveal_dc + 10:
            self.revealed = True
            self.revealed_by_seek = True
            return "critical_success", self.description_on_reveal or f"Odkrywacie {self.challenge_label}."
        if total >= self.reveal_dc:
            self.revealed = True
            self.revealed_by_seek = True
            return "success", self.description_on_reveal or f"Odkrywacie {self.challenge_label}."
        if total <= self.reveal_dc - 10:
            return "critical_failure", "Nie znajdujecie właściwego miejsca."
        return "failure", "Nie znajdujecie właściwego miejsca."

    def on_reveal(self, game, *, source_actor=None) -> str | None:
        return self.description_on_reveal or None

    def action_attempt(self, actor, game, _payload: dict[str, Any] | None = None) -> str:
        if not self.can_interact(actor, game):
            return "Ta interakcja nie jest jeszcze dostępna."
        if self.hidden and not self.revealed:
            return "Najpierw trzeba odkryć to miejsce."
        if self.intro:
            self._prompt_info(game, self.challenge_label, self.intro, source_suffix="intro")
        base_modifier, modifier_notes = self._active_flag_modifier_bonus(game)
        result = resolve_skill_check_with_sources(
            skill_id=self.skill_id,
            dc=self.dc,
            actor=actor,
            target=self,
            tags=[self.skill_id, "scenario_skill_challenge", *self.tags],
            game=game,
            base_modifier=base_modifier,
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
        if modifier_notes:
            message = f"{message} Premie z przygotowania: {', '.join(modifier_notes)}."
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

    def _normalize_flag_modifiers(self, raw: list[dict[str, Any]] | None) -> tuple[dict[str, Any], ...]:
        modifiers: list[dict[str, Any]] = []
        for item in list(raw or []):
            if not isinstance(item, dict):
                continue
            flag = str(item.get("flag") or "").strip()
            if not flag:
                continue
            try:
                value = int(item.get("value", 0) or 0)
            except Exception:
                value = 0
            if value == 0:
                continue
            note = str(item.get("note") or flag).strip()
            modifiers.append({"flag": flag, "value": value, "note": note})
        return tuple(modifiers)

    def _active_flag_modifier_bonus(self, game) -> tuple[int, list[str]]:
        total = 0
        notes: list[str] = []
        for item in self.flag_modifiers:
            if not self._flag_enabled(game, str(item.get("flag") or "")):
                continue
            value = int(item.get("value", 0) or 0)
            total += value
            note = str(item.get("note") or item.get("flag") or "").strip()
            if note:
                notes.append(f"{note} {value:+d}")
        return total, notes

    def _flag_enabled(self, game, flag: str) -> bool:
        key = str(flag or "").strip()
        if not key:
            return False
        session = getattr(game, "scenario_session", None)
        flags = getattr(session, "global_flags", None)
        if isinstance(flags, dict):
            return bool(flags.get(key))
        flags = getattr(game, "global_flags", None)
        if isinstance(flags, dict):
            return bool(flags.get(key))
        return False

    def _conditions_pass(self, game) -> bool:
        conditions = self.conditions
        if not isinstance(conditions, dict) or not conditions:
            return True
        for flag in list(conditions.get("flags") or conditions.get("all_flags") or []):
            if not self._flag_enabled(game, str(flag)):
                return False
        for flag in list(conditions.get("not_flags") or []):
            if self._flag_enabled(game, str(flag)):
                return False
        any_flags = [str(flag) for flag in list(conditions.get("any_flags") or []) if str(flag).strip()]
        if any_flags and not any(self._flag_enabled(game, flag) for flag in any_flags):
            return False
        return True

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

    def _map_id(self, game) -> str:
        session = getattr(game, "scenario_session", None)
        raw = getattr(session, "current_map_id", "") or getattr(game, "current_map_id", "")
        return str(raw or "scenario").strip() or "scenario"

    def _voiceover_path(self, game, source_suffix: str) -> str | None:
        challenge = str(self.challenge_id or self.challenge_label or "skill_challenge").strip()
        suffix = str(source_suffix or "info").strip()
        slug = "_".join(
            part
            for part in (
                self._map_id(game),
                challenge,
                suffix,
            )
            if part
        )
        slug = re.sub(r"[^a-zA-Z0-9_]+", "_", slug).strip("_").lower()
        return f"audio/voiceover/runtime_dialogue/{slug}_001.mp3" if slug else None

    def _prompt_info(self, game, title: str, text: str, *, source_suffix: str) -> None:
        ui = getattr(game, "ui", None)
        if ui is None or not getattr(ui, "enabled", False) or not hasattr(ui, "prompt_info"):
            return
        challenge = str(self.challenge_id or self.challenge_label or "skill_challenge").strip()
        try:
            ui.prompt_info(
                title,
                prompt_long=text,
                source=f"skill_challenge:{self.challenge_id or self.challenge_label}:{source_suffix}",
                prompt_id=f"skill_challenge.{challenge}.{source_suffix}",
                audio=self._voiceover_path(game, source_suffix),
                communication={
                    "context": {
                        "challenge_id": self.challenge_id,
                        "asset_id": self.challenge_id,
                    }
                },
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
        "flag_modifiers": [],
        "conditions": {},
        "required_flags": [],
        "hidden": False,
        "allow_hidden_interaction": False,
        "reveal_dc": 15,
        "seekable": True,
        "reveal_tags": [],
        "description_on_reveal": "",
        "allow_same_cell_interact": True,
        "require_same_cell_interact": False,
        "blocks_movement": False,
    },
)


__all__ = ["SkillChallenge", "META"]
