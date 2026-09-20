"""Distinct exploration passives; no IO and no additional player prompts."""
from __future__ import annotations

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .confrontation import Confrontation

KINDS = frozenset({
    'garran_follow', 'garran_guard', 'garran_line', 'garran_rally', 'garran_example',
    'brakka_pressure', 'brakka_stubborn', 'brakka_force', 'brakka_defiance', 'brakka_persistence',
    'mira_opening', 'mira_slip', 'mira_precision', 'mira_shortcut', 'mira_switch',
    'dagna_care', 'dagna_cooperate', 'dagna_recover', 'dagna_shelter', 'dagna_patience',
    'lorian_ensemble', 'lorian_echo', 'lorian_refrain', 'lorian_tempo', 'lorian_recycle',
    'nimra_exact', 'nimra_pattern', 'nimra_stability', 'nimra_focus', 'nimra_deduction',
    'erynd_finish', 'erynd_scout', 'erynd_prepare', 'erynd_signal', 'erynd_track',
})
STACKING = frozenset({'garran_follow', 'brakka_pressure', 'mira_precision', 'dagna_care', 'lorian_ensemble', 'nimra_focus', 'erynd_finish'})


def count(state: Confrontation, hero: str, kind: str) -> int:
    if state.mana.phase in {'setup', 'drain'} or state.stage == 'result':
        return 0
    participant = next(p for p in state.participants if p.id == hero)
    kinds = dict(participant.passives)
    return sum(kinds[c] == kind for c in state.mana.hand(hero))


def enabled(state: Confrontation, hero: str, kind: str) -> bool:
    return count(state, hero, kind) > 0


def test_bonus(state: Confrontation, hero: str) -> int:
    on = lambda kind: enabled(state, hero, kind)
    hand = state.mana.hand(hero)
    value = 2 * (on('brakka_defiance') and not dict(state.aids).get(hero, 0))
    value += 2 * (on('mira_opening') and state.last_action_actor != hero
                  and state.last_action_kind == 'test' and state.last_action_success)
    if on('nimra_pattern'):
        value += 2 if len(set(hand)) == 5 else int(len(set(hand)) >= 3)
    value += 2 * (on('erynd_prepare') and len(state.mana.deck) <= 2 * len(state.participants))
    return value


def impact_bonus(state: Confrontation, hero: str) -> int:
    actor = next(p for p in state.participants if p.id == hero)
    value = min(2, count(state, hero, 'garran_follow')) if dict(state.aids).get(hero, 0) else 0
    value += min(3, count(state, hero, 'brakka_pressure')) if actor.dc >= 22 else 0
    if state.last_action_actor != hero and state.last_action_kind == 'test' and not state.last_action_success:
        value += min(2, count(state, hero, 'dagna_care'))
    colors = set(state.mana.hand(hero))
    if any(p.id != hero and colors.intersection(state.mana.hand(p.id)) for p in state.participants):
        value += min(2, count(state, hero, 'lorian_ensemble'))
    trump = max(state.mana.point_values(hero), key=state.mana.point_values(hero).get)
    if state.mana.hand(hero).count(trump) >= 2:
        value += min(2, count(state, hero, 'nimra_focus'))
    if state.resistance * 3 <= state.maximum:
        value += min(2, count(state, hero, 'erynd_finish'))
    return value


def guard(state: Confrontation, hero: str) -> bool:
    return (enabled(state, hero, 'garran_guard')
            or (enabled(state, hero, 'mira_slip') and dict(state.hero_actions).get(hero) == 'peek')
            or any(p.id != hero and enabled(state, p.id, 'dagna_shelter') for p in state.participants))


def received_aid(state: Confrontation, hero: str, amount: int) -> int:
    return amount + int(enabled(state, hero, 'lorian_refrain'))


def support_cost(state: Confrontation) -> int:
    return 0 if enabled(state, state.actor.id, 'lorian_tempo') else 1
