from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace

from GameObjects.items.inventory import (
    add_alchemical_item,
    assign_item_to_hand,
    hand_slots_snapshot,
    get_equipped_weapons,
    set_equipped_weapons,
    toggle_item_activation,
)


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


def test_can_switch_from_two_hand_weapon_to_one_hand_weapon():
    longbow = _weapon(item_id="longbow", instance_id="w-longbow", hands_required=2)
    longsword = _weapon(item_id="longsword", instance_id="w-longsword", hands_required=1)
    actor = Actor(inventory=[longbow, longsword], weapon_loadout=["longbow", "longsword"])

    set_equipped_weapons(actor, [longbow])
    ok, _msg = toggle_item_activation(actor, longsword)
    equipped_ids = {getattr(item, "instance_id", "") for item in get_equipped_weapons(actor)}

    assert ok is True
    assert equipped_ids == {"w-longsword"}


def test_hand_slots_snapshot_for_weapon_and_shield():
    sword = _weapon(item_id="sword", instance_id="w-sword")
    shield = _shield(instance_id="s-1")
    actor = Actor(inventory=[sword, shield], weapon_loadout=["sword"])

    set_equipped_weapons(actor, [sword])
    ok, _msg = toggle_item_activation(actor, shield)
    assert ok is True

    slots = hand_slots_snapshot(actor)
    assert slots["mode"] == "weapon_and_shield"
    assert slots["left"]["kind"] == "weapon"
    assert slots["right"]["kind"] == "shield"
    assert slots["free_hands"] == 0


def test_hand_slots_snapshot_for_dual_wield():
    sword = _weapon(item_id="sword", instance_id="w-sword")
    dagger = _weapon(item_id="dagger", instance_id="w-dagger")
    actor = Actor(inventory=[sword, dagger], weapon_loadout=["sword", "dagger"])

    set_equipped_weapons(actor, [sword, dagger])
    slots = hand_slots_snapshot(actor)

    assert slots["mode"] == "dual_wield"
    assert slots["left"]["kind"] == "weapon"
    assert slots["right"]["kind"] == "weapon"
    assert slots["free_hands"] == 0


def test_hand_slots_snapshot_for_two_handed_weapon_with_free_hand_weapon():
    longbow = _weapon(item_id="longbow", instance_id="w-longbow", hands_required=2)
    gauntlet = _weapon(item_id="gauntlet", instance_id="w-gauntlet", traits=("free_hand",))
    actor = Actor(inventory=[longbow, gauntlet], weapon_loadout=["longbow", "gauntlet"])

    set_equipped_weapons(actor, [longbow, gauntlet])
    slots = hand_slots_snapshot(actor)

    assert slots["mode"] == "two_handed"
    assert slots["left"]["label"] == "longbow"
    assert slots["right"]["label"] == "longbow"
    assert "gauntlet" in slots["active_free_hand_weapons"]


def test_assign_item_to_right_hand_moves_weapon_and_updates_snapshot():
    sword = _weapon(item_id="sword", instance_id="w-sword")
    dagger = _weapon(item_id="dagger", instance_id="w-dagger")
    actor = Actor(inventory=[sword, dagger], weapon_loadout=["sword", "dagger"])

    set_equipped_weapons(actor, [sword])
    ok, _msg = assign_item_to_hand(actor, dagger, "right")
    slots = hand_slots_snapshot(actor)

    assert ok is True
    assert slots["left"]["label"] == "sword"
    assert slots["right"]["label"] == "dagger"


def test_assign_shield_to_left_hand_updates_snapshot():
    sword = _weapon(item_id="sword", instance_id="w-sword")
    shield = _shield(instance_id="s-1")
    actor = Actor(inventory=[sword, shield], weapon_loadout=["sword"])

    set_equipped_weapons(actor, [sword])
    ok, _msg = assign_item_to_hand(actor, shield, "left")
    slots = hand_slots_snapshot(actor)

    assert ok is True
    assert slots["left"]["kind"] == "shield"
    assert slots["right"]["kind"] == "weapon"
    assert slots["right"]["label"] == "sword"


def test_toggle_alchemical_item_returns_clear_usage_hint():
    actor = Actor()
    bomb = add_alchemical_item(actor, event_name="alchemists_fire", preparation_counter=0)

    ok, message = toggle_item_activation(actor, bomb)

    assert ok is False
    assert "Akcje -> Alchemia" in message
    assert "alchemists_fire" in message
    assert "gotowy" in message.lower()


def test_toggle_alchemical_item_hint_includes_not_ready_counter():
    actor = Actor()
    bomb = add_alchemical_item(actor, event_name="alchemists_fire", preparation_counter=1)

    ok, message = toggle_item_activation(actor, bomb)

    assert ok is False
    assert "Akcje -> Alchemia" in message
    assert "1 tur" in message.lower()
