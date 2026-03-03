from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


def _new_instance_id() -> str:
    return f"item-{uuid4().hex[:10]}"


@dataclass
class ShieldBlockOutcome:
    incoming_damage: int
    blocked_damage: int
    damage_to_bearer: int
    damage_to_shield: int
    shield_hp_before: int
    shield_hp_after: int
    became_broken: bool
    became_destroyed: bool
    can_block: bool


@dataclass
class BaseShield:
    item_id: str = "base_shield"
    name: str = "Shield"
    category: str = "shield"
    description: str = "Tarcza."
    hands_required: int = 1
    traits: tuple[str, ...] = ()
    instance_id: str = field(default_factory=_new_instance_id)
    hardness: int = 0
    max_hp: int = 1
    broken_threshold: int = 1
    current_hp: int | None = None

    def __post_init__(self) -> None:
        self.hardness = max(0, int(self.hardness))
        self.max_hp = max(1, int(self.max_hp))
        self.broken_threshold = max(1, min(int(self.broken_threshold), self.max_hp))
        if self.current_hp is None:
            self.current_hp = self.max_hp
        self.current_hp = max(0, min(int(self.current_hp), self.max_hp))

    @property
    def is_destroyed(self) -> bool:
        return int(self.current_hp or 0) <= 0

    @property
    def is_broken(self) -> bool:
        hp = int(self.current_hp or 0)
        return hp > 0 and hp <= int(self.broken_threshold)

    @property
    def can_block(self) -> bool:
        # Broken shield cannot use Shield Block.
        return (not self.is_destroyed) and (not self.is_broken)

    def repair_full(self) -> None:
        self.current_hp = self.max_hp

    def ui_description(self) -> str:
        state = "destroyed" if self.is_destroyed else ("broken" if self.is_broken else "ready")
        traits = ", ".join(self.traits) if self.traits else "brak"
        return (
            f"{self.name}\n"
            f"Hardness: {self.hardness} | HP: {self.current_hp}/{self.max_hp} | BT: {self.broken_threshold}\n"
            f"State: {state} | Traits: {traits}"
        )

    def apply_shield_block(self, incoming_damage: int) -> ShieldBlockOutcome:
        try:
            incoming = max(0, int(incoming_damage))
        except Exception:
            incoming = 0

        hp_before = int(self.current_hp or 0)
        was_broken = self.is_broken
        can_block = self.can_block and incoming > 0
        if not can_block:
            return ShieldBlockOutcome(
                incoming_damage=incoming,
                blocked_damage=0,
                damage_to_bearer=incoming,
                damage_to_shield=0,
                shield_hp_before=hp_before,
                shield_hp_after=hp_before,
                became_broken=False,
                became_destroyed=False,
                can_block=False,
            )

        blocked = min(incoming, int(self.hardness))
        remaining = max(0, incoming - blocked)
        self.current_hp = max(0, hp_before - remaining)
        hp_after = int(self.current_hp or 0)
        became_destroyed = hp_before > 0 and hp_after <= 0
        became_broken = (not was_broken) and hp_after > 0 and hp_after <= int(self.broken_threshold)
        return ShieldBlockOutcome(
            incoming_damage=incoming,
            blocked_damage=blocked,
            damage_to_bearer=remaining,
            damage_to_shield=remaining,
            shield_hp_before=hp_before,
            shield_hp_after=hp_after,
            became_broken=became_broken,
            became_destroyed=became_destroyed,
            can_block=True,
        )
