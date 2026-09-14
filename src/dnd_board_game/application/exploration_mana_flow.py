"""Actor-bound exploration checks, independent of presentation and persistence."""
from __future__ import annotations

from dataclasses import replace

from dnd_board_game.actors import Actor
from dnd_board_game.core.player_labels_pl import ABILITY_LABELS_PL, SKILL_LABELS_PL
from dnd_board_game.rules import (
    D20RollInput, D20RollRequest, RollMode, RollModifier, RollModifierType,
    ability_modifier, resolve_d20_roll, resolve_ability_check,
)
from dnd_board_game.rules.exploration_mana import ManaAttempt
from dnd_board_game.rules.exploration_mana_catalog import ExplorationMethod, method_by_id


def method_modifiers(actor: Actor, method: ExplorationMethod) -> tuple[RollModifier, ...]:
    if str(actor.id) != method.hero_id:
        raise ValueError("Tę metodę wykonuje przypisany do niej bohater.")
    modifiers = [RollModifier(ABILITY_LABELS_PL[method.ability],
                  ability_modifier(getattr(actor.ability_scores, method.ability)), RollModifierType.ABILITY)]
    trained = method.proficiency in (*actor.proficiencies.skills, *actor.proficiencies.tools)
    if trained:
        expert = method.proficiency in actor.proficiencies.expertise
        modifiers.append(RollModifier(SKILL_LABELS_PL.get(method.proficiency, "Narzędzia złodziejskie"),
                         actor.proficiency_bonus * (2 if expert else 1),
                         RollModifierType.EXPERTISE if expert else RollModifierType.PROFICIENCY))
    if method.hero_id == "lorian" and method.ability == "charisma":
        modifiers.append(RollModifier("Obycie i targowanie", 2, RollModifierType.FEATURE))
    if method.hero_id == "erynd" and method.kind == "object":
        modifiers.append(RollModifier("Praktyka terenowa", 2, RollModifierType.FEATURE))
    return tuple(modifiers)


def check_request(actor: Actor, attempt: ManaAttempt) -> D20RollRequest:
    method = method_by_id(attempt.method_id)
    modifiers = (*method_modifiers(actor, method), RollModifier("Mana", attempt.bonus, RollModifierType.SITUATIONAL))
    return D20RollRequest(mode=RollMode.DISADVANTAGE if attempt.busted else RollMode.NORMAL,
                          modifiers=modifiers, ability=method.ability)


def resolve_attempt(actor: Actor, attempt: ManaAttempt, dc: int, rolls: tuple[int, ...], *,
                    improvisation_available: bool = False) -> ManaAttempt:
    if attempt.phase != "roll":
        raise ValueError("Ta próba nie oczekuje na rzut.")
    request = check_request(actor, attempt)
    count = 2 if request.mode == RollMode.DISADVANTAGE else 1
    if len(rolls) != count or any(type(r) is not int or not 1 <= r <= 20 for r in rolls):
        raise ValueError(f"Wpisz {count} wynik(i) k20 od 1 do 20.")
    result = resolve_d20_roll(D20RollInput(request, rolls[0], rolls[1] if count == 2 else None))
    success = resolve_ability_check(result, dc).success
    method = method_by_id(attempt.method_id)
    may_reroll = (not success and improvisation_available and not attempt.reroll_used
                  and method.kind == "npc" and method.hero_id == "lorian" and method.ability == "charisma")
    return replace(attempt, phase="reroll_choice" if may_reroll else "result", success=success,
                   rolls=rolls, roll_total=result.total, revision=attempt.revision + 1)
