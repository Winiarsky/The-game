from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from GameObjects.items.inventory import get_equipped_weapons, set_equipped_weapons, toggle_item_activation


def _weapon(*, item_id: str, instance_id: str, traits: tuple[str, ...] = (), hands_required: int = 1):
    return SimpleNamespace(
        item_id=item_id,
        instance_id=instance_id,
        name=item_id,
        category="weapon",
        traits=tuple(traits),
        hands_required=hands_required,
        ranged=False,
    )


def _shield(*, instance_id: str):
    return SimpleNamespace(
        item_id="shield",
        instance_id=instance_id,
        name="shield",
        category="shield",
    )


@dataclass
class Actor:
    inventory: list[object] = field(default_factory=list)
    statuses: list[object] = field(default_factory=list)
    equipped_weapon_item_ids: list[str] = field(default_factory=list)
    equipped_shield: object | None = None
    weapon_loadout: list[str] = field(default_factory=list)

    def has_status(self, status_id: str) -> bool:
        return any(getattr(item, "id", item) == status_id for item in self.statuses)


def test_free_hand_weapon_allows_shield_with_one_h_weapon():
    sword = _weapon(item_id="sword", instance_id="w-sword")
    gauntlet = _weapon(item_id="gauntlet", instance_id="w-gauntlet", traits=("free_hand",))
    shield = _shield(instance_id="s-1")
    actor = Actor(inventory=[sword, gauntlet, shield], weapon_loadout=["sword", "gauntlet"])

    set_equipped_weapons(actor, [sword, gauntlet])
    ok, _msg = toggle_item_activation(actor, shield)

    assert ok is True
    assert actor.equipped_shield is shield


def test_two_hand_weapon_keeps_free_hand_weapon_active():
    greataxe = _weapon(item_id="greataxe", instance_id="w-greataxe", hands_required=2)
    gauntlet = _weapon(item_id="gauntlet", instance_id="w-gauntlet", traits=("free_hand",))
    actor = Actor(inventory=[greataxe, gauntlet], weapon_loadout=["greataxe", "gauntlet"])

    set_equipped_weapons(actor, [greataxe, gauntlet])
    equipped_ids = {getattr(item, "instance_id", "") for item in get_equipped_weapons(actor)}

    assert "w-greataxe" in equipped_ids
    assert "w-gauntlet" in equipped_ids


def test_can_activate_second_one_h_weapon_with_free_hand_active():
    sword = _weapon(item_id="sword", instance_id="w-sword")
    dagger = _weapon(item_id="dagger", instance_id="w-dagger")
    gauntlet = _weapon(item_id="gauntlet", instance_id="w-gauntlet", traits=("free_hand",))
    actor = Actor(inventory=[sword, dagger, gauntlet], weapon_loadout=["sword", "dagger", "gauntlet"])

    set_equipped_weapons(actor, [sword, gauntlet])
    ok, _msg = toggle_item_activation(actor, dagger)
    equipped_ids = {getattr(item, "instance_id", "") for item in get_equipped_weapons(actor)}

    assert ok is True
    assert equipped_ids == {"w-sword", "w-dagger", "w-gauntlet"}
