from __future__ import annotations

from dataclasses import dataclass

from interactions_mixin.skill_checks import resolve_skill_check


@dataclass
class TrappableMixin:
    trap_armed: bool = False
    trap_detected: bool = False
    trap_detection_dc: int = 16
    trap_disable_dc: int = 18
    trap_effect: str = "Pułapka zadaje obrażenia lub uruchamia alarm."

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

    def disable_trap(self, roll: int) -> tuple[str, str]:
        if not self.trap_armed:
            return "info", "Pułapka już rozbrojona/nieaktywna."
        if not self.trap_detected:
            return "failure", "Musisz najpierw wykryć pułapkę."
        outcome = resolve_skill_check(self.trap_disable_dc, roll)
        match outcome:
            case "critical_success":
                self.trap_armed = False
                return outcome, "Krytyczny sukces – pułapka rozbrojona bez śladu."
            case "success":
                self.trap_armed = False
                return outcome, "Sukces – pułapka rozbrojona."
            case "failure":
                return outcome, "Porażka – mechanizm wciąż gotowy."
            case "critical_failure":
                effect = self.trigger_trap()
                return outcome, f"Krytyczna porażka – aktywujesz pułapkę! {effect}"
        return outcome, "Nieoczekiwany rezultat."

    def trigger_trap(self) -> str:
        self.trap_armed = False
        return self.trap_effect
