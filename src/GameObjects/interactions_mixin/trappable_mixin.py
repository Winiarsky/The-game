from __future__ import annotations

from dataclasses import dataclass

from .prompt_utils import prompt_for_roll
from .skill_checks import resolve_skill_check


@dataclass
class TrappableMixin:
    trap_armed: bool = False
    trap_detected: bool = False
    trap_identified: bool = False
    trap_name: str = "Pułapka"
    trap_level: int = 0
    trap_detection_dc: int = 16
    trap_disable_dc: int = 18
    trap_identify_dc: int | None = None
    trap_disable_progress: int = 0
    trap_disable_successes_required: int = 1
    trap_effect: str = "Pułapka zadaje obrażenia lub uruchamia alarm."
    trap_trigger_description: str = "Wejście na pole."
    trap_attack_bonus: int | None = None
    trap_damage_prompt: str | None = None
    trap_damage_type: str = "piercing"

    @staticmethod
    def _actor_id(actor) -> str:
        return str(getattr(actor, "object_id", None) or getattr(actor, "name", None) or id(actor))

    @staticmethod
    def _has_status(actor, status_id: str) -> bool:
        checker = getattr(actor, "has_status", None)
        if callable(checker):
            try:
                return bool(checker(status_id))
            except Exception:
                return False
        for status in getattr(actor, "statuses", []) or []:
            if getattr(status, "id", status) == status_id:
                return True
        return False

    def _effective_identify_dc(self) -> int:
        try:
            if self.trap_identify_dc is not None:
                return int(self.trap_identify_dc)
        except Exception:
            pass
        return int(self.trap_disable_dc)

    def _effective_ac_vs_trap(self, actor) -> int:
        try:
            from combat import effective_ac
        except Exception:
            effective_ac = lambda _actor: int(getattr(_actor, "ac", 0) or 0)  # noqa: E731
        base_ac = int(effective_ac(actor) or 0)
        trap_finder_bonus = 1 if self._has_status(actor, "trap_finder") else 0
        return base_ac + trap_finder_bonus

    def _trap_summary(self) -> str:
        parts = [
            f"{self.trap_name} (lvl {int(self.trap_level)})",
            f"Trigger: {self.trap_trigger_description}",
            f"Disable DC: {int(self.trap_disable_dc)}",
        ]
        if self.trap_attack_bonus is not None and self.trap_damage_prompt:
            parts.append(f"Atak +{int(self.trap_attack_bonus)} vs AC, obrażenia {self.trap_damage_prompt}.")
        elif self.trap_effect:
            parts.append(str(self.trap_effect))
        return " ".join(parts)

    def detect_trap(self, roll: int) -> tuple[str, str]:
        if not self.trap_armed:
            return "info", "Nie ma tu pułapki."
        if self.trap_detected:
            return "info", "Pułapka już wykryta."
        outcome = resolve_skill_check(self.trap_detection_dc, roll)
        if outcome in ("success", "critical_success"):
            self.trap_detected = True
            return outcome, "Wyczuwasz mechanizm pułapki."
        return outcome, "Nic nie znajdujesz."

    def identify_trap(self, roll: int) -> tuple[str, str]:
        if not self.trap_armed:
            return "info", "Nie ma aktywnej pułapki do analizy."
        if not self.trap_detected:
            return "failure", "Najpierw wykryj pułapkę (Seek/Trap Finder)."
        outcome = resolve_skill_check(self._effective_identify_dc(), roll)
        if outcome in ("success", "critical_success"):
            self.trap_identified = True
            return outcome, self._trap_summary()
        if outcome == "critical_failure":
            return outcome, "Błędnie odczytujesz mechanizm pułapki."
        return outcome, "Nie potrafisz zidentyfikować mechanizmu."

    def disable_trap(self, roll: int, *, actor=None, game=None) -> tuple[str, str]:
        if not self.trap_armed:
            return "info", "Pułapka już rozbrojona/nieaktywna."
        if not self.trap_detected:
            return "failure", "Musisz najpierw wykryć pułapkę."
        outcome = resolve_skill_check(self.trap_disable_dc, roll)
        match outcome:
            case "critical_success":
                self.trap_armed = False
                self.trap_disable_progress = max(self.trap_disable_progress, int(self.trap_disable_successes_required))
                return outcome, "Krytyczny sukces – pułapka rozbrojona bez śladu."
            case "success":
                self.trap_disable_progress = int(self.trap_disable_progress) + 1
                if self.trap_disable_progress >= int(self.trap_disable_successes_required):
                    self.trap_armed = False
                    return outcome, "Sukces – pułapka rozbrojona."
                left = int(self.trap_disable_successes_required) - int(self.trap_disable_progress)
                return outcome, f"Sukces częściowy – potrzeba jeszcze {left} udanych prób."
            case "failure":
                return outcome, "Porażka – mechanizm wciąż gotowy."
            case "critical_failure":
                effect = self.trigger_trap(actor=actor, game=game)
                return outcome, f"Krytyczna porażka – aktywujesz pułapkę! {effect}"
        return outcome, "Nieoczekiwany rezultat."

    def try_auto_detect_with_trap_finder(self, actor, game) -> tuple[bool, str]:
        if not self.trap_armed or self.trap_detected:
            return False, ""
        if not self._has_status(actor, "trap_finder"):
            return False, ""
        try:
            from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources

            result = resolve_skill_check_with_sources(
                skill_id="perception",
                dc=int(self.trap_detection_dc),
                actor=actor,
                target=self,
                tags=["seek", "trap", "perception", "trap_finder", "auto_detect"],
                game=game,
                apply_modifiers=True,
            )
            outcome, msg = self.detect_trap(int(getattr(result, "total", 0) or 0))
            if outcome in ("success", "critical_success"):
                return True, f"Trap Finder: {msg}"
        except Exception:
            return False, ""
        return False, ""

    def trigger_trap(self, actor=None, game=None) -> str:
        try:
            from combat.degree_of_success import is_hit, natural_shift_from_roll, resolve_outcome
        except Exception:
            is_hit = lambda outcome: str(outcome) in ("success", "critical_success")  # noqa: E731
            resolve_outcome = lambda total, dc, natural_shift=0: "success" if int(total) >= int(dc) else "failure"  # noqa: E731
            natural_shift_from_roll = lambda _roll: 0  # noqa: E731
        self.trap_armed = False
        try:
            events = getattr(game, "events", None)
            if events is not None and hasattr(events, "safe_emit_action"):
                events.safe_emit_action(
                    actor=actor,
                    action_id="trap_activated",
                    action_tags=["trap", "trigger"],
                    target=self,
                    trap_id=str(getattr(self, "object_id", "") or getattr(self, "trap_name", "") or ""),
                )
        except Exception:
            pass
        if actor is None:
            return self.trap_effect
        attack_bonus = self.trap_attack_bonus
        damage_prompt = str(self.trap_damage_prompt or "").strip()
        if attack_bonus is None or not damage_prompt:
            return self.trap_effect
        target_ac = self._effective_ac_vs_trap(actor)
        roll_data = prompt_for_roll(
            f"{self.trap_name}: rzut ataku +{int(attack_bonus)} vs AC {target_ac}.",
            layout="test",
            roll_stack={
                "components": [
                    {
                        "id": "trap_attack",
                        "label": "Atak pułapki",
                        "value": int(attack_bonus),
                        "description": "Premia ataku pułapki.",
                        "editable": True,
                    }
                ],
                "auto_total_modifier": int(attack_bonus),
            },
            auto_total_modifier=int(attack_bonus),
            answer_placeholder="Wynik k20",
            return_details=True,
            infer_natural_from_roll=True,
        )
        if isinstance(roll_data, dict):
            roll = int(roll_data.get("roll", 0) or 0)
            natural_shift = int(roll_data.get("natural_shift", 0) or 0)
            if natural_shift == 0:
                raw_roll = int(roll_data.get("raw_roll", roll) or roll)
                natural_shift = natural_shift_from_roll(raw_roll)
            modifier_delta = int(roll_data.get("modifier_delta", 0) or 0)
        else:
            roll = int(roll_data or 0)
            natural_shift = natural_shift_from_roll(roll)
            modifier_delta = 0
        total = int(roll) + int(attack_bonus) + int(modifier_delta)
        outcome = resolve_outcome(total, int(target_ac), natural_shift=natural_shift)
        if not is_hit(outcome):
            return f"Pułapka pudłuje ({total} vs AC {target_ac})."
        dmg = prompt_for_roll(
            f"{self.trap_name}: obrażenia {damage_prompt}:",
            layout="damage",
            answer_placeholder="Suma obrażeń",
        )
        try:
            dealt = max(0, int(dmg or 0))
        except Exception:
            dealt = 0
        try:
            target_name = getattr(actor, "name", None) or self._actor_id(actor)
            apply = getattr(actor, "apply_damage", None)
            if callable(apply):
                apply(dealt, str(self.trap_damage_type or "piercing"))
            try:
                events = getattr(game, "events", None)
                if dealt > 0 and events is not None and hasattr(events, "safe_emit_action"):
                    events.safe_emit_action(
                        actor=actor,
                        action_id="damage_applied",
                        action_tags=["damage", "trap"],
                        target=actor,
                        source_action="trap_activated",
                        source_label=str(getattr(self, "trap_name", "") or "Pułapka"),
                        amount=int(dealt),
                        damage=int(dealt),
                        damage_type=str(self.trap_damage_type or "piercing"),
                        trap_id=str(getattr(self, "object_id", "") or getattr(self, "trap_name", "") or ""),
                    )
            except Exception:
                pass
            return f"Pułapka trafia {target_name} za {dealt} ({self.trap_damage_type})."
        except Exception:
            return f"Pułapka trafia za {dealt}."

    def on_enter_trap(self, actor, game) -> str | None:
        if not self.trap_armed:
            return None
        auto_found, auto_msg = self.try_auto_detect_with_trap_finder(actor, game)
        if auto_found:
            return auto_msg
        effect = self.trigger_trap(actor=actor, game=game)
        self.trap_detected = True
        return effect
