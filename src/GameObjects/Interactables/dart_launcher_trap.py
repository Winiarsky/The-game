from __future__ import annotations

from GameObjects.base import GameObjectMeta

from .trap_tile import TrapTile


class DartLauncherTrap(TrapTile):
    """Przykładowa pułapka PF2e: płyta naciskowa + wyrzutnia strzałek."""

    def __init__(self, **kwargs) -> None:
        defaults = {
            "trap_armed": True,
            "trap_name": "Wyrzutnia strzałek",
            "trap_level": 2,
            "trap_detection_dc": 22,  # Stealth +12
            "trap_disable_dc": 20,
            "trap_identify_dc": 20,
            "trap_trigger_description": "Nadepnięcie na płytę naciskową.",
            "trap_effect": "Mechanizm odpala wyrzutnię strzałek ze ściany.",
            "trap_attack_bonus": 10,
            "trap_damage_prompt": "2k6",
            "trap_damage_type": "piercing",
            "trap_disable_successes_required": 1,
        }
        defaults.update(dict(kwargs or {}))
        super().__init__(**defaults)


META = GameObjectMeta(
    object_id="dart_launcher_trap",
    label="Wyrzutnia strzałek",
    color="#e44",
    category="Interactables",
    placement="cell",
    description="Pułapka poziomu 2: Stealth DC 22, Disable DC 20, +10 vs AC, 2k6 piercing.",
    logic_cls=DartLauncherTrap,
    default_config={
        "trap_armed": True,
        "trap_name": "Wyrzutnia strzałek",
        "trap_level": 2,
        "trap_detection_dc": 22,
        "trap_disable_dc": 20,
        "trap_identify_dc": 20,
        "trap_trigger_description": "Nadepnięcie na płytę naciskową.",
        "trap_effect": "Mechanizm odpala wyrzutnię strzałek ze ściany.",
        "trap_attack_bonus": 10,
        "trap_damage_prompt": "2k6",
        "trap_damage_type": "piercing",
        "trap_disable_successes_required": 1,
    },
)

