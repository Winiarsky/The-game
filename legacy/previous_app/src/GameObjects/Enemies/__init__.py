"""Pakiet wrogów z metadanymi do edytora."""

from .basic_enemy import BasicEnemy  # noqa: F401
from .enemy_types import EnemyType  # noqa: F401

_LAZY_EXPORTS = {
    "SimpleEnemy": (".simple_enemy", "SimpleEnemy"),
    "Enemy": (".simple_enemy", "Enemy"),
    "META": (".simple_enemy", "META"),
    "GoblinWarrior": (".goblin_warrior", "GoblinWarrior"),
    "GoblinCommando": (".goblin_commando", "GoblinCommando"),
    "GoblinDog": (".goblin_dog", "GoblinDog"),
    "ValeGuard": (".vale_guard", "ValeGuard"),
    "MillEnforcer": (".mill_enforcer", "MillEnforcer"),
    "AshenWatcher": (".ashen_watcher", "AshenWatcher"),
    "AshenKnight": (".ashen_knight", "AshenKnight"),
    "AshCinder": (".ash_cinder", "AshCinder"),
    "CharredDeacon": (".charred_deacon", "CharredDeacon"),
    "OdransChampion": (".odrans_champion", "OdransChampion"),
}


def __getattr__(name: str):
    if name not in _LAZY_EXPORTS:
        raise AttributeError(name)
    module_name, attr_name = _LAZY_EXPORTS[name]
    from importlib import import_module

    value = getattr(import_module(module_name, __name__), attr_name)
    globals()[name] = value
    return value


__all__ = [
    "BasicEnemy",
    "SimpleEnemy",
    "Enemy",
    "GoblinWarrior",
    "GoblinCommando",
    "GoblinDog",
    "ValeGuard",
    "MillEnforcer",
    "AshenWatcher",
    "AshenKnight",
    "AshCinder",
    "CharredDeacon",
    "OdransChampion",
    "META",
    "EnemyType",
]
