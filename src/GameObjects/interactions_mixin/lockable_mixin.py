from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .skill_checks import resolve_skill_check


@dataclass
class LockableMixin:
    locked: bool = True
    working_keys: Optional[list[str]] = None
    thievery_dc: int = 15
    force_open_dc: int = 18
    jammed: bool = False

    def try_key(self, key_name: str) -> tuple[bool, str]:
        if not self.locked:
            return False, "Zamek już odblokowany."
        if self.jammed:
            return False, "Zamek zablokowany/zaklinowany."
        keys = self.working_keys or []
        if key_name in keys:
            self.locked = False
            return True, f"Używasz {key_name}. Zamek klika."
        return False, f"{key_name} nie pasuje."

    def pick_lock(self, roll: int) -> tuple[str, str]:
        if not self.locked:
            return "success", "Zamek już odblokowany."
        if self.jammed:
            return "failure", "Zamek zaklinowany, nie da się działać wytrychem."
        outcome = resolve_skill_check(self.thievery_dc, roll)
        match outcome:
            case "critical_success":
                self.locked = False
                return outcome, "Kryt! Zamek cicho ustępuje."
            case "success":
                self.locked = False
                return outcome, "Sukces, zamek odblokowany."
            case "failure":
                return outcome, "Porażka, zamek pozostaje zamknięty."
            case "critical_failure":
                self.jammed = True
                return outcome, "Krytyczna porażka – zamek się klinuje."
        return outcome, "Nieoczekiwany rezultat."

    def force_lock(self, roll: int) -> tuple[str, str]:
        if not self.locked:
            return "success", "Zamek już odblokowany."
        outcome = resolve_skill_check(self.force_open_dc, roll)
        match outcome:
            case "critical_success":
                self.locked = False
                return outcome, "Kryt! Siłą wyrywasz zamek."
            case "success":
                self.locked = False
                return outcome, "Wyważasz, zamek puszcza."
            case "failure":
                return outcome, "Porażka – zamek trzyma."
            case "critical_failure":
                self.jammed = True
                return outcome, "Krytyczna porażka – zamek zacięty, będzie trudniej."
        return outcome, "Nieoczekiwany rezultat."
