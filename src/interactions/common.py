from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


def prompt_for_roll(prompt: str) -> int:
    """Poproś o rzut i zwróć liczbę całkowitą."""
    while True:
        raw = input(prompt).strip()
        if not raw:
            continue
        try:
            return int(raw)
        except ValueError:
            continue


def resolve_skill_check(dc: int, roll: int) -> str:
    """Zwraca outcome: critical_success, success, failure, critical_failure."""
    if roll >= dc + 10:
        return "critical_success"
    if roll >= dc:
        return "success"
    if roll <= dc - 10:
        return "critical_failure"
    return "failure"


@dataclass
class DestructibleMixin:
    ac: int
    hp: int
    hardness: int
    destroyed: bool = False

    def apply_damage(self, roll: int, damage: int) -> tuple[bool, int, str]:
        """Zwraca (trafienie, dmg_po_hardness, komunikat)."""
        if self.destroyed:
            return False, 0, "Obiekt już zniszczony."
        if roll < self.ac:
            return False, 0, f"Atak ({roll}) nie trafia (AC {self.ac})."
        effective = max(0, damage - self.hardness)
        self.hp -= effective
        if self.hp <= 0:
            self.destroyed = True
            return True, effective, f"Obiekt rozsypuje się (zadano {effective})."
        return True, effective, f"Trafienie. Zadajesz {effective} (HP pozostalo: {self.hp})."


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


@dataclass
class HiddenMixin:
    hidden: bool = False
    revealed: bool = False
    reveal_dc: int = 18

    def try_reveal(self, roll: int) -> tuple[str, str]:
        if not self.hidden:
            return "info", "Tu nic nie jest ukryte."
        if self.revealed:
            return "info", "Sekret już odkryty."
        outcome = resolve_skill_check(self.reveal_dc, roll)
        if outcome in ("success", "critical_success"):
            self.revealed = True
            return outcome, "Zauważasz ukryty element."
        return outcome, "Nie dostrzegasz niczego niezwykłego."
