from __future__ import annotations

from dataclasses import dataclass
import random
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


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


# --- Dialog / społeczności ---

AttitudeLabel = str


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def attitude_label(attitude: int) -> AttitudeLabel:
    """Mapuje liczbę na etykietę postawy."""
    if attitude <= -2:
        return "wrogi"
    if attitude == -1:
        return "podejrzliwy"
    if attitude == 0:
        return "neutralny"
    if attitude == 1:
        return "życzliwy"
    return "przyjacielski"


@dataclass
class SocialMixin:
    attitude: int = 0  # -2 wrogi, -1 podejrzliwy, 0 neutralny, 1 życzliwy, 2+ przyjacielski
    min_attitude: int = -2
    max_attitude: int = 2

    def adjust_attitude(self, delta: int) -> tuple[int, AttitudeLabel]:
        self.attitude = clamp(self.attitude + delta, self.min_attitude, self.max_attitude)
        return self.attitude, attitude_label(self.attitude)


@dataclass
class TradeItem:
    item_id: str
    name: str
    price: int


@dataclass
class TradeMixin:
    inventory: list[TradeItem] = None
    base_price_modifier: float = 1.0

    def price_multiplier(self, attitude: int) -> float:
        """Prosty mnożnik ceny zależny od nastawienia."""
        table = {
            -2: 1.6,
            -1: 1.3,
            0: 1.0,
            1: 0.9,
            2: 0.85,
        }
        return table.get(attitude, 1.0) * self.base_price_modifier


@dataclass
class PickpocketMixin:
    pickpocket_dc: int = 16
    pickpocket_loot: list[str] = None
    pickpocket_fail_attitude_delta: int = -1

    def resolve_pickpocket(self, roll: int) -> tuple[str, Optional[str]]:
        """Zwraca (outcome, zdobyty_przedmiot_lub_None)."""
        outcome = resolve_skill_check(self.pickpocket_dc, roll)
        if outcome in ("success", "critical_success"):
            loot = (self.pickpocket_loot or ["sakiewka"])[0]
            return outcome, loot
        return outcome, None


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
    seekable: bool = True

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


@dataclass(init=False)
class WatchfulMixin:
    watch_disturbed: int = 0  # 0 blokuje stealth w pokoju, >0 daje karę do testu
    watch_disabled: bool = False
    perception_bonus: int = 0

    def __init__(
        self,
        *,
        watch_disturbed: int = 0,
        watch_disabled: bool = False,
        perception_bonus: int = 0,
        **_kwargs,
    ) -> None:
        self.watch_disturbed = watch_disturbed
        self.watch_disabled = watch_disabled
        self.perception_bonus = perception_bonus

    def attempt_spot(self, hero, game) -> tuple[bool, str]:
        """Próba wykrycia ukrytego bohatera; zwraca (wykryto, komunikat)."""
        dc = getattr(hero, "stealth_detection_dc", None)
        statuses = set(getattr(hero, "statuses", []))
        if dc is None or "stealth" not in statuses:
            return False, "Cel nie jest ukryty."
        roll = random.randint(1, 20) + self.perception_bonus
        if roll >= dc:
            if "stealth" in hero.statuses:
                hero.statuses.remove("stealth")
            if "observable" not in hero.statuses:
                hero.statuses.append("observable")
            if hasattr(hero, "stealth_bonus"):
                hero.stealth_bonus = 0
            hero.stealth_detection_dc = None
            spotted_msg = f"Wykryto bohatera (r={roll} vs DC {dc})."
            try:
                extra = self.on_spot(hero, game)
                if extra:
                    spotted_msg = f"{spotted_msg} {extra}"
            except Exception:
                pass
            return True, spotted_msg
        return False, f"Nie dostrzegasz bohatera (r={roll} vs DC {dc})."

    def on_spot(self, hero, game) -> Optional[str]:
        """Hook wywoływany przy sukcesie wykrycia."""
        return None


@dataclass(init=False)
class HideInMixin:
    """Mixin dający możliwość ukrycia pasażera w obiekcie."""

    hide_status: str = "hide"
    hide_stealth_bonus: int = 2

    def __init__(
        self,
        *,
        hide_status: str = "hide",
        hide_stealth_bonus: int = 2,
        **_kwargs,
    ) -> None:
        self.hide_status = hide_status
        self.hide_stealth_bonus = hide_stealth_bonus
        # obiekty mogą mieć atrybut someone_inside; jeśli brak, ustawiany przy pierwszym użyciu

    def _hide_in_precheck(self, actor, game) -> Optional[str]:
        """Opcjonalne pre-checki; zwróć komunikat błędu by zablokować."""
        return None

    def hide_in(self, actor, game) -> str:
        """Umieść aktora w obiekcie, nadaj status hide i premię do stealth."""
        failure = self._hide_in_precheck(actor, game)
        if failure:
            return failure
        position = getattr(self, "position", None)
        if position is None:
            return "Obiekt nie jest na planszy."
        board = game.board
        occupant = board.occupant_at(position)
        passenger = getattr(self, "someone_inside", None)
        if passenger is not None and passenger is not actor:
            return "Obiekt jest już zajęty."
        if occupant is not None and occupant is not actor:
            return "Ktoś już zajmuje to pole."

        if actor.position is not None:
            board.remove(actor.position)
        board.place(actor, position)
        setattr(self, "someone_inside", actor)

        statuses = getattr(actor, "statuses", None)
        if isinstance(statuses, list) and self.hide_status not in statuses:
            statuses.append(self.hide_status)
        setattr(actor, "hide_stealth_bonus", getattr(actor, "hide_stealth_bonus", 0) + self.hide_stealth_bonus)
        return "Ukrywasz się w środku i zyskujesz osłonę."
