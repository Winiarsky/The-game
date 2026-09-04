"""Keyboard-first combat bindings for the seven curated board-game heroes.

Bindings point at stable action/source ids rather than list positions.  The combat
menu remains the authoritative source of what is currently available.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class _CombatOption(Protocol):
    id: str
    source_id: str | None
    action_id: str | None
    action: object
    category: object


@dataclass(frozen=True, slots=True)
class HeroShortcut:
    key: str
    action_ref: str


COMMON_SHORTCUTS: tuple[HeroShortcut, ...] = (
    HeroShortcut("M", "@move"),
    HeroShortcut("B", "@weapons"),
    HeroShortcut("I", "@items"),
    HeroShortcut("0", "@end_turn"),
)


HERO_SHORTCUTS: dict[str, tuple[HeroShortcut, ...]] = {
    "garran": (
        HeroShortcut("Q", "second_wind"),
        HeroShortcut("W", "action_surge"),
        HeroShortcut("E", "shield_bash"),
        HeroShortcut("R", "defensive_stance"),
        HeroShortcut("A", "garran_command_halt"),
        HeroShortcut("S", "garran_shield_wall"),
        HeroShortcut("D", "garran_rally"),
        HeroShortcut("F", "garran_guard_companion"),
    ),
    "brakka": (
        HeroShortcut("Q", "rage"),
        HeroShortcut("W", "reckless_attack"),
        HeroShortcut("E", "powerful_strike"),
        HeroShortcut("R", "shoulder_check"),
        HeroShortcut("A", "acceleration"),
        HeroShortcut("S", "deafening_roar"),
    ),
    "mira": (
        HeroShortcut("Q", "smoke_screen"),
        HeroShortcut("W", "guard_vault"),
        HeroShortcut("E", "combat_trap_detection"),
        HeroShortcut("R", "hamstring_cut"),
        HeroShortcut("A", "piercing_attack"),
        HeroShortcut("S", "blade_mistress"),
    ),
    "dagna": (
        HeroShortcut("Q", "sacred_flame"),
        HeroShortcut("W", "healing_word"),
        HeroShortcut("E", "bless"),
        HeroShortcut("R", "preserve_life"),
        HeroShortcut("A", "divine_care_aura"),
        HeroShortcut("S", "guiding_bolt"),
        HeroShortcut("D", "healing_grace_aura"),
        HeroShortcut("F", "lesser_restoration"),
        HeroShortcut("Z", "spiritual_weapon"),
    ),
    "lorian": (
        HeroShortcut("Q", "bardic_inspiration"),
        HeroShortcut("W", "optical_scope"),
        HeroShortcut("E", "mocking_shot"),
        HeroShortcut("R", "provoking_shot"),
        HeroShortcut("A", "entangling_shot"),
        HeroShortcut("S", "panic_whisper"),
        HeroShortcut("D", "thunderwave"),
        HeroShortcut("F", "faerie_fire"),
        HeroShortcut("Z", "hideous_laughter"),
        HeroShortcut("X", "stage_command"),
        HeroShortcut("C", "accelerated_refrain"),
    ),
    "nimra": (
        HeroShortcut("T", "nimra_sculpt_field"),
        HeroShortcut("Y", "nimra_distant_spell"),
        HeroShortcut("U", "nimra_overcharged_spell"),
        HeroShortcut("G", "nimra_forced_weave"),
        HeroShortcut("H", "nimra_energy_transmutation"),
        HeroShortcut("Q", "nimra_frost_pulse"),
        HeroShortcut("W", "nimra_acid_splash"),
        HeroShortcut("E", "nimra_mind_spike"),
        HeroShortcut("R", "nimra_flame_fan"),
        HeroShortcut("A", "nimra_force_wave"),
        HeroShortcut("S", "nimra_sticky_matrix"),
        HeroShortcut("D", "nimra_sleep"),
        HeroShortcut("F", "nimra_fog"),
        HeroShortcut("Z", "nimra_web"),
        HeroShortcut("X", "nimra_lightning_path"),
        HeroShortcut("C", "nimra_mind_break"),
        HeroShortcut("V", "nimra_stasis"),
        HeroShortcut("J", "misty_step"),
        HeroShortcut("K", "shatter"),
    ),
    "erynd": (
        HeroShortcut("Q", "hunters_mark"),
        HeroShortcut("W", "cunning_action"),
        HeroShortcut("E", "aim"),
        HeroShortcut("R", "anchoring_arrow"),
        HeroShortcut("A", "exposing_arrow"),
        HeroShortcut("S", "disrupting_arrow"),
        HeroShortcut("D", "double_shot"),
        HeroShortcut("F", "misty_step"),
        HeroShortcut("Z", "spike_growth"),
    ),
}


def shortcut_bindings(actor_id: str) -> tuple[HeroShortcut, ...]:
    """Return common and character-specific bindings for a curated hero."""

    return (*COMMON_SHORTCUTS, *HERO_SHORTCUTS.get(actor_id, ()))


def _option_matches_ref(option: _CombatOption, action_ref: str) -> bool:
    special_option_ids = {
        "@move": "turn:move",
        "@weapons": "menu:weapons",
        "@items": "menu:items",
        "@end_turn": "turn:end",
    }
    if action_ref in special_option_ids:
        return option.id == special_option_ids[action_ref]
    return action_ref in {option.source_id, option.action_id}


def shortcut_for_option(
    actor_id: str,
    option: _CombatOption,
    *,
    selected_attack_source_id: str | None = None,
) -> str | None:
    """Return the displayed shortcut for an option, if it has one."""

    for binding in shortcut_bindings(actor_id):
        if _option_matches_ref(option, binding.action_ref):
            return binding.key
    if (
        selected_attack_source_id
        and option.source_id == selected_attack_source_id
        and str(option.action) == "select_attack_source"
    ):
        return "SPACE"
    return None


__all__ = [
    "COMMON_SHORTCUTS",
    "HERO_SHORTCUTS",
    "HeroShortcut",
    "shortcut_bindings",
    "shortcut_for_option",
]
