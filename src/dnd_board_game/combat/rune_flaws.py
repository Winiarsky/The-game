"""Contextual rune surcharges; ordinary actions never spend runes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
from dnd_board_game.actors import Actor
from dnd_board_game.scenarios.rune_catalog import rune_card
from .session import CombatState
from .shared_mana import NON_OFFENSIVE, adjacent
from .spells import grid_distance_feet
from .conditions import CombatCondition


@dataclass(frozen=True, slots=True)
class RuneFlawCost:
    count: int = 0
    reminders: tuple[str, ...] = ()


def rune_flaw_cost(state: CombatState, actor: Actor, ability_id: str,
                   targets: Sequence[Actor] = ()) -> RuneFlawCost:
    mana = state.shared_mana
    card = rune_card(str(actor.id), ability_id, pool=mana.runes if mana else None)
    if mana is None or mana.runes is None or card is None:
        return RuneFlawCost()
    if card.free_first and (str(actor.id), ability_id + ":free") not in mana.runes.used_once:
        return RuneFlawCost()
    hero = str(actor.id)
    allies = tuple(a for a in state.actors if a.id != actor.id and a.faction == actor.faction and not a.is_dead())
    unconscious = {c.actor_id for c in state.condition_states if c.condition == CombatCondition.UNCONSCIOUS}
    conscious_allies = tuple(a for a in allies if not a.is_unconscious() and not a.is_defeated() and str(a.id) not in unconscious)
    if hero == "dagna" and (card.category == "offense" if card.category else ability_id not in NON_OFFENSIVE) and any(adjacent(actor, a) and 2*a.hp < a.max_hp for a in allies):
        return RuneFlawCost(1, ("Nikogo nie zostawiam: ranny sąsiad — dopłać 1 wybraną dowolną runę.",))
    if hero == "lorian" and len(mana.runes.heroes) > 1 and not any(
            grid_distance_feet(actor.position, a.position) <= 10 for a in conscious_allies):
        return RuneFlawCost(1, ("Potrzeba publiczności: brak przytomnego sojusznika do 2 pól — dopłać 1 wybraną dowolną runę.",))
    if hero == "nimra" and mana.echo_spell == ability_id:
        count = min(2, mana.echo_count)
        return RuneFlawCost(count, (f"Echo: powtórzenie mocy — dopłać {count} wybrane dowolne runy.",))
    shots = {"disrupting_arrow", "anchoring_arrow", "exposing_arrow", "double_shot", "arrow_rain"}
    if hero == "erynd" and ability_id in shots and any(
            adjacent(target, ally) for target in targets for ally in conscious_allies
            if str(ally.id) in mana.runes.heroes):
        return RuneFlawCost(1, ("Trauma bratobójczego strzału: bohater przy celu — dopłać 1 wybraną dowolną runę.",))
    return RuneFlawCost()
