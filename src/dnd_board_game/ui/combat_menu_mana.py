"""Structured reminders for action tiles; never checks physical card payment."""

from typing import Sequence

from dnd_board_game.actors.resources import uses_physical_mana
from dnd_board_game.combat.context_menu import CombatMenuAction, CombatMenuOption
from dnd_board_game.combat.physical_mana_movement import movement_mana_notice
from dnd_board_game.combat.session import CombatState, current_actor
from dnd_board_game.rules import ActiveEffect
from dnd_board_game.rules.physical_mana import mana_ability


def distinct_action_options(
    options: tuple[CombatMenuOption, ...]
) -> tuple[CombatMenuOption, ...]:
    """A source selector already exposes the corresponding class feature."""
    sources = {
        o.source_id
        for o in options
        if o.source_id
        and o.action
        in {
            CombatMenuAction.SELECT_ATTACK_SOURCE,
            CombatMenuAction.SELECT_HEALING_SOURCE,
        }
    }
    return tuple(
        o
        for o in options
        if not (o.action == CombatMenuAction.CLASS_FEATURE and o.action_id in sources)
    )


def menu_mana_payload(
    option: CombatMenuOption, state: CombatState, effects: Sequence[ActiveEffect]
) -> dict[str, object]:
    actor = current_actor(state)
    if not uses_physical_mana(actor):
        return {}
    if option.action == CombatMenuAction.MOVE:
        notice = movement_mana_notice(state, effects)
        assert notice is not None
        return {
            "mana_cost": [] if notice.started else ["*"] * notice.cost,
            "mana_cost_note": (
                "bez kolejnej dopłaty" if notice.started else "raz na turę"
            ),
        }
    if (
        option.id
        in {
            "turn:end",
            "menu:weapons",
            "menu:items",
            "nimra-metamagic:cancel",
            "combat-action:hunters_mark:transfer",
        }
        or option.action == CombatMenuAction.END_HIDE
    ):
        return {"mana_cost": [], "mana_cost_note": "bez many"}
    ability = mana_ability(str(actor.id), option.action_id or option.source_id or "")
    cost = list(ability.cost) if ability else ([] if state.shared_mana else ["*"])
    note = ""
    if ability and ability.timing == "MOD":
        note = (
            "dopłata do ataku"
            if ability.id == "reckless_attack"
            else "dopłata do czaru"
        )
    if option.provider.startswith("nimra_metamagic:"):
        meta_id = option.provider.split(":", 1)[1].split("@")[0]
        meta = mana_ability(str(actor.id), meta_id)
        if meta:
            cost.extend(meta.cost)
            note = "z Metamagią"
    if not ability and option.action == CombatMenuAction.SELECT_ATTACK_SOURCE:
        note = "bez many; skaza może wymagać dopłaty" if state.shared_mana else "za atak"
    # Already-declared techniques include all attacks in their initial price.
    locked = next(
        (
            e.object_id
            for e in effects
            if e.actor_id == str(actor.id) and e.kind == "mana_series_source"
        ),
        "",
    )
    if ability and state.turn_action.attack_action_active and locked == ability.id:
        cost, note = [], "w cenie techniki"
    return {"mana_cost": cost, "mana_cost_note": note}
